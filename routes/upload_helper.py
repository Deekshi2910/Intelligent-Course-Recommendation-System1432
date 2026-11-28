"""
Profile Photo Upload Helper Module
Handles image verification, format checking, size validation, and safe storage.
Supports persistent cloud storage via Cloudinary as well as secure local disk storage.
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


def is_cloudinary_configured():
    """Checks whether Cloudinary credentials are provided via environment variables."""
    return bool(
        os.getenv("CLOUDINARY_URL")
        or (
            os.getenv("CLOUDINARY_CLOUD_NAME")
            and os.getenv("CLOUDINARY_API_KEY")
            and os.getenv("CLOUDINARY_API_SECRET")
        )
    )


def validate_and_save_profile_photo(file_storage, user_id):
    """
    Validates uploaded file size, extension, and binary content using Pillow.
    If Cloudinary credentials exist, uploads to Cloudinary for permanent hosting.
    Otherwise, saves the image with a generated secure filename in static/uploads/profiles/.
    
    Returns:
        tuple (saved_path_or_url, error_message)
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

    # 3. Persistent Cloud Storage via Cloudinary (if configured)
    if is_cloudinary_configured():
        try:
            import cloudinary
            import cloudinary.uploader

            if os.getenv("CLOUDINARY_URL"):
                cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))
            else:
                cloudinary.config(
                    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                    api_key=os.getenv("CLOUDINARY_API_KEY"),
                    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                    secure=True,
                )

            file_storage.seek(0)
            upload_result = cloudinary.uploader.upload(
                file_storage,
                folder="course_recommender/profiles",
                public_id=f"profile_{user_id}_{uuid.uuid4().hex[:8]}",
                overwrite=True,
                resource_type="image",
                transformation=[
                    {"width": 400, "height": 400, "crop": "fill", "gravity": "face"}
                ],
            )
            secure_url = upload_result.get("secure_url")
            if secure_url:
                return secure_url, None
        except Exception:
            # Fall back cleanly to local disk storage if Cloudinary fails
            pass

    # 4. Fallback: Save to Local Disk (static/uploads/profiles/)
    safe_name = f"profile_{user_id}_{uuid.uuid4().hex[:10]}.{ext}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "profiles")
    os.makedirs(upload_dir, exist_ok=True)
    full_path = os.path.join(upload_dir, safe_name)

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


def delete_profile_photo(photo_path):
    """
    Safely deletes a student profile photo from Cloudinary or local disk.
    Prevents directory traversal by enforcing base directory checks.
    """
    if not photo_path:
        return False

    # Handle Cloudinary remote URLs
    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        if is_cloudinary_configured() and "cloudinary.com" in photo_path:
            try:
                import cloudinary
                import cloudinary.uploader

                if os.getenv("CLOUDINARY_URL"):
                    cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))
                else:
                    cloudinary.config(
                        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                        api_key=os.getenv("CLOUDINARY_API_KEY"),
                        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                        secure=True,
                    )

                if "course_recommender/profiles" in photo_path:
                    idx = photo_path.find("course_recommender/profiles")
                    public_id_with_ext = photo_path[idx:]
                    public_id = public_id_with_ext.rsplit(".", 1)[0]
                    cloudinary.uploader.destroy(public_id)
                    return True
            except Exception:
                pass
        return True

    # Handle local disk path
    clean_path = photo_path.lstrip("/\\")
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
