import hashlib
import os
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
from fastapi import UploadFile, HTTPException

from app.core.config import settings


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


async def validate_and_save_file(upload_file: UploadFile) -> Tuple[str, str, str]:
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(upload_file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension")

    if upload_file.content_type and upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")

    content = await upload_file.read()
    await upload_file.seek(0)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    file_hash = hashlib.sha256(content).hexdigest()

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    file_url = f"/uploads/{filename}"
    return file_url, file_hash, str(file_path)
