import os
import io
import json
import uuid
import tempfile
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, send_file, current_app, abort, session
)
from flask_login import login_required, current_user
from extensions import db, csrf
from models.document import Document
from models.import_log import ImportLog
from services.file_validator import (
    validate_uploaded_file,
    FileValidationError,
    TABULAR_EXTENSIONS,
    DOCUMENT_EXTENSIONS
)
from services.storage_service import StorageService
from services.import_service import ImportService, ENTITY_FIELDS

uploads_bp = Blueprint('uploads', __name__, url_prefix='/uploads')

# In-memory or temp cache for previewed files awaiting confirmation
TEMP_IMPORT_DIR = os.path.join(tempfile.gettempdir(), 'smart_library_import_previews')
os.makedirs(TEMP_IMPORT_DIR, exist_ok=True)

@uploads_bp.route('/', methods=['GET'])
@login_required
def index():
    """
    Main Upload & Import Hub:
    Displays Tabular Data Importer, Document Management Library, and Import Logs.
    """
    category_filter = request.args.get('category', '').strip()
    search_query = request.args.get('q', '').strip()

    # Query Documents with search and category filters
    doc_query = Document.query
    if category_filter:
        doc_query = doc_query.filter_by(file_category=category_filter)
    if search_query:
        doc_query = doc_query.filter(
            (Document.title.ilike(f'%{search_query}%')) |
            (Document.original_filename.ilike(f'%{search_query}%')) |
            (Document.description.ilike(f'%{search_query}%'))
        )
    documents = doc_query.order_by(Document.created_at.desc()).all()

    # Query Import History
    import_logs = ImportLog.query.order_by(ImportLog.created_at.desc()).limit(20).all()

    # Categories list for document uploads
    categories = ['Policy', 'Guide', 'Report', 'Academic', 'Catalog', 'General']

    # Storage backend status info
    active_backend = StorageService.get_configured_backend()

    return render_template(
        'uploads/index.html',
        documents=documents,
        import_logs=import_logs,
        categories=categories,
        entity_fields=ENTITY_FIELDS,
        active_backend=active_backend,
        selected_category=category_filter,
        search_query=search_query
    )

@uploads_bp.route('/template/<string:entity_type>', methods=['GET'])
@login_required
def download_template(entity_type):
    """Generate and stream a sample CSV template for data imports."""
    if entity_type not in ENTITY_FIELDS:
        flash(f"Invalid template entity '{entity_type}'.", "danger")
        return redirect(url_for('uploads.index'))

    csv_content = ImportService.get_template_csv(entity_type)
    buffer = io.BytesIO(csv_content.encode('utf-8'))
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"{entity_type}_import_template.csv"
    )

@uploads_bp.route('/preview', methods=['POST'])
@login_required
def preview_tabular():
    """
    Parse uploaded CSV or Excel file, extract sample preview rows,
    and generate automated column mapping suggestions.
    """
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file was submitted.'}), 400

    file_storage = request.files['file']
    target_entity = request.form.get('target_entity', 'books')

    if not file_storage.filename:
        return jsonify({'status': 'error', 'message': 'No file selected.'}), 400

    try:
        preview_data = ImportService.preview_file(file_storage, target_entity)

        # Cache file bytes temporarily to allow subsequent execution step
        token = str(uuid.uuid4())
        temp_path = os.path.join(TEMP_IMPORT_DIR, f"{token}_{file_storage.filename}")
        file_storage.stream.seek(0)
        file_storage.save(temp_path)

        preview_data['preview_token'] = token
        preview_data['temp_path'] = temp_path
        
        return jsonify({
            'status': 'success',
            'data': preview_data
        })
    except FileValidationError as fve:
        return jsonify({'status': 'error', 'message': str(fve)}), 400
    except Exception as ex:
        current_app.logger.exception("Tabular preview error:")
        return jsonify({'status': 'error', 'message': f"Failed to parse file: {str(ex)}"}), 500

@uploads_bp.route('/import-execute', methods=['POST'])
@login_required
def execute_import():
    """
    Execute batch database import with confirmed column mappings,
    duplicate handling strategy, and transaction protection.
    """
    preview_token = request.form.get('preview_token')
    target_entity = request.form.get('target_entity', 'books')
    duplicate_strategy = request.form.get('duplicate_strategy', 'skip')
    raw_mapping = request.form.get('column_mapping', '{}')

    try:
        column_mapping = json.loads(raw_mapping)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Malformed column mapping payload.'}), 400

    # Locate cached preview file or read freshly uploaded file
    file_bytes = None
    filename = "imported_data"

    if preview_token:
        matching_files = [f for f in os.listdir(TEMP_IMPORT_DIR) if f.startswith(preview_token)]
        if matching_files:
            cached_filename = matching_files[0]
            temp_path = os.path.join(TEMP_IMPORT_DIR, cached_filename)
            with open(temp_path, 'rb') as f:
                file_bytes = f.read()
            filename = cached_filename.split('_', 1)[1] if '_' in cached_filename else cached_filename
            # Clean up cached file
            try:
                os.remove(temp_path)
            except OSError:
                pass

    if file_bytes is None and 'file' in request.files:
        f = request.files['file']
        filename = f.filename
        file_bytes = f.read()

    if not file_bytes:
        return jsonify({'status': 'error', 'message': 'Import data payload or token missing.'}), 400

    try:
        log_entry = ImportService.execute_import(
            file_bytes=file_bytes,
            filename=filename,
            target_entity=target_entity,
            column_mapping=column_mapping,
            duplicate_strategy=duplicate_strategy,
            user=current_user
        )

        return jsonify({
            'status': 'success',
            'summary': {
                'total_rows': log_entry.total_rows,
                'successful_imports': log_entry.successful_imports,
                'skipped_duplicates': log_entry.skipped_duplicates,
                'failed_rows': log_entry.failed_rows,
                'log_id': log_entry.id,
                'status': log_entry.status,
                'errors': log_entry.error_details
            }
        })
    except FileValidationError as fve:
        return jsonify({'status': 'error', 'message': str(fve)}), 400
    except Exception as ex:
        current_app.logger.exception("Import execution error:")
        return jsonify({'status': 'error', 'message': f"Import failed: {str(ex)}"}), 500

@uploads_bp.route('/document', methods=['POST'])
@login_required
def upload_document():
    """Upload and store managed documents (PDF, Word) with metadata."""
    if 'file' not in request.files:
        flash("Please choose a file to upload.", "warning")
        return redirect(url_for('uploads.index'))

    file = request.files['file']
    if not file.filename:
        flash("No file was selected.", "warning")
        return redirect(url_for('uploads.index'))

    title = request.form.get('title', '').strip()
    category = request.form.get('file_category', 'General').strip()
    description = request.form.get('description', '').strip()

    try:
        doc = StorageService.save_document(
            file_storage=file,
            title=title,
            category=category,
            description=description,
            user=current_user
        )
        flash(f"Document '{doc.title}' uploaded successfully! ({doc.file_size_formatted})", "success")
    except FileValidationError as fve:
        flash(f"Validation Error: {str(fve)}", "danger")
    except Exception as ex:
        current_app.logger.exception("Document upload error:")
        flash(f"Upload failed: {str(ex)}", "danger")

    return redirect(url_for('uploads.index', _anchor='documents'))

@uploads_bp.route('/documents/<int:doc_id>/download', methods=['GET'])
@login_required
def download_document(doc_id):
    """
    Secure authenticated download route for documents.
    Protects private files, verifies existence, and sets download headers.
    """
    doc = Document.query.get_or_404(doc_id)

    try:
        stream, mime_type, filename = StorageService.get_document_content(doc)
        
        response = send_file(
            stream,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
        # Security header: prevent MIME-sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except FileNotFoundError:
        flash("The requested document file could not be found on storage.", "danger")
        return redirect(url_for('uploads.index'))
    except Exception as ex:
        current_app.logger.exception("Document download error:")
        flash(f"Could not retrieve document: {str(ex)}", "danger")
        return redirect(url_for('uploads.index'))

@uploads_bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete document content and metadata with strict role permissions."""
    doc = Document.query.get_or_404(doc_id)

    if not doc.can_delete(current_user):
        flash("You do not have permission to delete this document.", "danger")
        return redirect(url_for('uploads.index'))

    try:
        title = doc.title
        StorageService.delete_document(doc)
        flash(f"Document '{title}' was deleted successfully.", "info")
    except Exception as ex:
        current_app.logger.exception("Document deletion error:")
        flash(f"Failed to delete document: {str(ex)}", "danger")

    return redirect(url_for('uploads.index', _anchor='documents'))
