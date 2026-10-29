import logging
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VisionOCR:
    """OCR nativo de macOS (Vision). Lee mucho mejor números y texto impreso
    que Tesseract y es local. Si no está disponible, el llamador usa Tesseract."""

    def __init__(self) -> None:
        self._source = Path(__file__).with_name("vision_ocr.swift")
        self._binary: Optional[Path] = None
        self._checked = False
        self._available = False

    def is_available(self) -> bool:
        if self._checked:
            return self._available
        self._checked = True
        self._available = (
            platform.system() == "Darwin"
            and shutil.which("swiftc") is not None
            and self._source.is_file()
        )
        return self._available

    def _compile(self) -> Optional[Path]:
        if not self.is_available():
            return None
        if self._binary is not None and self._binary.is_file():
            return self._binary

        cache_dir = Path(tempfile.gettempdir()) / "control_io_native_ocr"
        cache_dir.mkdir(parents=True, exist_ok=True)
        binary = cache_dir / "vision_ocr"
        try:
            if (
                not binary.is_file()
                or binary.stat().st_mtime < self._source.stat().st_mtime
            ):
                result = subprocess.run(
                    ["swiftc", "-O", str(self._source), "-o", str(binary)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode != 0:
                    logger.warning(
                        "No se pudo compilar Vision OCR: %s", result.stderr[:800]
                    )
                    self._available = False
                    return None
            self._binary = binary
            return binary
        except Exception as exc:  # pragma: no cover
            logger.warning("Error compilando Vision OCR: %s", exc)
            self._available = False
            return None

    def recognize_file(self, image_path: str) -> List[Dict[str, Any]]:
        binary = self._compile()
        if binary is None:
            return []
        try:
            result = subprocess.run(
                [str(binary), image_path],
                capture_output=True,
                text=True,
                timeout=90,
            )
            if result.returncode != 0:
                logger.warning("Vision OCR falló: %s", result.stderr[:500])
                return []
            return self._parse(result.stdout)
        except Exception as exc:  # pragma: no cover
            logger.warning("Vision OCR error: %s", exc)
            return []

    def recognize_array(self, image: np.ndarray) -> List[Dict[str, Any]]:
        if not self.is_available() or image is None or image.size == 0:
            return []
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = Path(tmp.name)
        try:
            tmp.close()
            if not cv2.imwrite(str(tmp_path), image):
                return []
            return self.recognize_file(str(tmp_path))
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    @staticmethod
    def _parse(stdout: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for line in stdout.splitlines():
            parts = line.split("\t", 5)
            if len(parts) != 6:
                continue
            try:
                x, y, width, height = (int(part) for part in parts[:4])
                confidence = float(parts[4])
            except ValueError:
                continue
            text = parts[5].strip()
            if not text:
                continue
            items.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                }
            )
        return items


vision_ocr = VisionOCR()
