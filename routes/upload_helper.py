"""
Profile Photo Upload Helper Module
Handles image verification, format checking, size validation, and safe storage.
Strictly prevents executable files and path traversal.
"""

import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 Megabytes


def allowed_file(filename):
    """Checks whether the file extension is among permitted image formats."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_and_save_profile_photo(file_storage, user_id):
    """
    Validates uploaded file size, extension, and binary content using Pillow.
    Saves the image with a generated secure filename in static/uploads/profiles/.
    
    Returns:
        tuple (saved_relative_path, error_message)
    """
    if not file_storage or not file_storage.filename:
        return None, "No file selected."

    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename):
        return None, "Invalid file format. Allowed formats: JPG, JPEG, PNG, WEBP."

    ext = filename.rsplit(".", 1)[1].lower()

    # 1. Size Validation (Max 2MB)
    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
        if size > MAX_FILE_SIZE:
            return None, "File size exceeds the 2 MB limit. Please upload a smaller image."
        if size == 0:
            return None, "The uploaded file is empty."
    except Exception:
        return None, "Could not determine file size."

    # 2. Binary Verification using Pillow
    try:
        image = Image.open(file_storage)
        image.verify()  # Verifies file integrity and detects spoofed files
        file_storage.seek(0)
        # Re-open for format check
        image = Image.open(file_storage)
        fmt = (image.format or "").upper()
        if fmt not in {"JPEG", "JPG", "PNG", "WEBP"}:
            return None, f"Unsupported image content format ({fmt})."
    except Exception as exc:
        return None, "The file could not be verified as a valid image."

    # 3. Generate Secure Unique Filename
    safe_name = f"profile_{user_id}_{uuid.uuid4().hex[:10]}.{ext}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "profiles")
    os.makedirs(upload_dir, exist_ok=True)
    full_path = os.path.join(upload_dir, safe_name)

    # 4. Save Image
    try:
        file_storage.seek(0)
        # Re-save through Pillow to strip harmful EXIF/metadata and ensure clean file
        if fmt in {"JPEG", "JPG"}:
            rgb_im = image.convert("RGB")
            rgb_im.save(full_path, "JPEG", quality=90, optimize=True)
        elif fmt == "PNG":
            image.save(full_path, "PNG", optimize=True)
        elif fmt == "WEBP":
            image.save(full_path, "WEBP", quality=90)
        else:
            file_storage.save(full_path)

        relative_path = f"uploads/profiles/{safe_name}"
        return relative_path, None
    except Exception as exc:
        return None, f"Failed to save image file: {exc}"


def delete_profile_photo(relative_path):
    """
    Safely deletes a student profile photo from disk.
    Prevents directory traversal by enforcing base directory checks.
    """
    if not relative_path:
        return False

    clean_path = relative_path.lstrip("/\\")
    full_path = os.path.join(current_app.root_path, "static", clean_path)
    base_dir = os.path.abspath(os.path.join(current_app.root_path, "static", "uploads", "profiles"))

    # Ensure full_path resides inside base_dir
    if not os.path.abspath(full_path).startswith(base_dir):
        return False

    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
            return True
    except Exception:
        pass
    return False
