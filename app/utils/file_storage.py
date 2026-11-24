"""
File Storage and Media Utilities Module
=======================================
Handles secure file uploads, UUID naming, and extension categorization.
"""

import os
import uuid
from werkzeug.utils import secure_filename


def save_uploaded_file(file_storage, target_folder: str, prefix: str = "file") -> tuple[str, str, int]:
    """
    Save uploaded file to disk with secure UUID prefix.
    Returns: (stored_filename, original_filename, file_size_bytes)
    """
    os.makedirs(target_folder, exist_ok=True)
    original_filename = secure_filename(file_storage.filename)
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "dat"

    unique_filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}"
    destination_path = os.path.join(target_folder, unique_filename)
    file_storage.save(destination_path)

    file_size = os.path.getsize(destination_path)
    return unique_filename, original_filename, file_size
