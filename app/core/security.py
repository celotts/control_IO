from fastapi import Header, HTTPException, status
from typing import Optional

from app.core.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> bool:
    if settings.API_KEY and settings.API_KEY != "dev-key-change-me":
        if not x_api_key or x_api_key != settings.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
    return True
