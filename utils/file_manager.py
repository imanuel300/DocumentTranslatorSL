import os
import uuid
from werkzeug.utils import secure_filename
from app import app

def save_uploaded_file(file):
    """Save uploaded file with a unique name"""
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    return file_path

def cleanup_old_files():
    """Clean up temporary files older than 24 hours"""
    import time
    from datetime import datetime, timedelta
    
    cleanup_time = datetime.now() - timedelta(hours=24)
    
    for root, _, files in os.walk(app.config['UPLOAD_FOLDER']):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getctime(file_path) < cleanup_time.timestamp():
                try:
                    os.remove(file_path)
                except Exception as e:
                    app.logger.error(f"Failed to remove file {file_path}: {str(e)}")
