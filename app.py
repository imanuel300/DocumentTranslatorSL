import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import boto3

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "translation-service-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "temp/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)

# Initialize AWS Bedrock client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.docx'):
        return jsonify({'error': 'Only Word documents (.docx) are supported'}), 400

    try:
        # Save file and create translation job
        from utils.file_manager import save_uploaded_file
        from models import TranslationJob
        
        file_path = save_uploaded_file(file)
        job = TranslationJob(
            original_filename=file.filename,
            file_path=file_path,
            status='pending',
            source_language=request.form.get('source_language', 'en'),
            target_language=request.form.get('target_language', 'es')
        )
        db.session.add(job)
        db.session.commit()

        # Start async translation process
        from utils.document_processor import process_document
        process_document(job.id)

        return jsonify({
            'job_id': job.id,
            'status': 'pending',
            'message': 'Translation job created successfully'
        })

    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({'error': 'Failed to process document'}), 500

@app.route('/api/jobs/<int:job_id>/status')
def get_job_status(job_id):
    from models import TranslationJob
    job = TranslationJob.query.get_or_404(job_id)
    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'message': job.message
    })

@app.route('/api/jobs/<int:job_id>/download')
def download_translation(job_id):
    from models import TranslationJob
    job = TranslationJob.query.get_or_404(job_id)
    
    if job.status != 'completed':
        return jsonify({'error': 'Translation not ready'}), 400

    return send_file(
        job.translated_file_path,
        as_attachment=True,
        download_name=f"translated_{job.original_filename}"
    )

@app.route('/api/jobs/history')
def get_translation_history():
    from models import TranslationJob
    jobs = TranslationJob.query.order_by(TranslationJob.created_at.desc()).all()
    return jsonify([{
        'id': job.id,
        'original_filename': job.original_filename,
        'status': job.status,
        'progress': job.progress,
        'created_at': job.created_at.isoformat(),
        'source_language': job.source_language,
        'target_language': job.target_language
    } for job in jobs])

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'})

with app.app_context():
    import models
    db.create_all()
