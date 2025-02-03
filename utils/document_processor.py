import logging
import zipfile
import xml.etree.ElementTree as ET
from app import db, bedrock
from models import TranslationJob
import json
import os
import shutil
from utils.bedrock_translator import BedrockTranslator

logger = logging.getLogger(__name__)

def process_document(job_id):
    """Process and translate a document by directly manipulating the word/document.xml content"""
    job = TranslationJob.query.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    translator = BedrockTranslator()
    try:
        job.status = 'processing'
        db.session.commit()

        # Create a temporary directory for working with the ZIP contents
        temp_dir = f"temp/job_{job_id}"
        os.makedirs(temp_dir, exist_ok=True)

        # Copy the original file to work with
        temp_docx = os.path.join(temp_dir, "temp.docx")
        shutil.copy2(job.file_path, temp_docx)

        with zipfile.ZipFile(temp_docx, 'r') as doc_zip:
            # Read the main document XML
            xml_content = doc_zip.read('word/document.xml')
            tree = ET.fromstring(xml_content)

            # Find all text elements in the document
            # Namespace for Word XML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text_elements = tree.findall('.//w:t', ns)
            total_elements = len(text_elements)

            # Process each text element
            for i, elem in enumerate(text_elements):
                if elem.text and elem.text.strip():
                    # Translate the text
                    translated_text = translator.translate_text(
                        elem.text,
                        job.source_language,
                        job.target_language
                    )
                    elem.text = translated_text

                    # Update progress
                    progress = (i + 1) / total_elements * 100
                    job.progress = progress
                    db.session.commit()

            # Create a new ZIP file with the translated content
            translated_path = f"temp/translated_{job.original_filename}"
            with zipfile.ZipFile(temp_docx, 'r') as src_zip:
                with zipfile.ZipFile(translated_path, 'w') as dest_zip:
                    # Copy all files from original ZIP
                    for item in src_zip.filelist:
                        if item.filename != 'word/document.xml':
                            # Copy original file
                            dest_zip.writestr(item.filename, src_zip.read(item.filename))
                        else:
                            # Write the modified XML content
                            dest_zip.writestr('word/document.xml', 
                                           ET.tostring(tree, encoding='UTF-8', 
                                                     xml_declaration=True))

        # Update job with translated file path
        job.translated_file_path = translated_path
        job.status = 'completed'
        job.message = 'Translation completed successfully'

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        job.status = 'failed'
        job.message = f'Translation failed: {str(e)}'

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        db.session.commit()