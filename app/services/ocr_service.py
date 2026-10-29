import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import pytesseract

logger = logging.getLogger(__name__)


class OCRService:
    """OCR auxiliar. No se usa como verdad absoluta: sirve como evidencia
    para calcular confianza y detectar discrepancias, porque Tesseract lee
    bien el texto impreso pero no la letra manuscrita."""

    def _to_gray(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Imagen vacía")
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def preprocess_image(self, image_path: str) -> np.ndarray:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("No se pudo leer la imagen")
        return self.preprocess_array(img)

    def preprocess_array(self, image: np.ndarray) -> np.ndarray:
        gray = self._to_gray(image)
        # Aumentar resolución mejora mucho el OCR de texto impreso pequeño.
        scale = max(1.0, 1600 / gray.shape[1])
        if scale > 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.fastNlMeansDenoising(gray, h=10)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )
        return thresh

    def extract_raw_text(self, image_path: str) -> str:
        processed = self.preprocess_image(image_path)
        return self.extract_text_from_processed(processed)

    def extract_text_from_array(self, image: np.ndarray) -> str:
        processed = self.preprocess_array(image)
        return self.extract_text_from_processed(processed)

    def extract_text_from_processed(self, processed: np.ndarray) -> str:
        try:
            text = pytesseract.image_to_string(
                processed, lang="spa+eng", config="--oem 3 --psm 6"
            )
            return text.strip()
        except Exception as exc:  # pragma: no cover - depende del binario de tesseract
            logger.warning("OCR no disponible: %s", exc)
            return ""

    def extract_with_boxes(self, image_path: str) -> Dict[str, Any]:
        processed = self.preprocess_image(image_path)
        data = pytesseract.image_to_data(
            processed,
            lang="spa+eng",
            config="--oem 3 --psm 6",
            output_type=pytesseract.Output.DICT,
        )
        return data

    def extract_words_from_array(self, image: np.ndarray) -> List[Dict[str, Any]]:
        processed = self.preprocess_array(image)
        try:
            data = pytesseract.image_to_data(
                processed,
                lang="spa+eng",
                config="--oem 3 --psm 6",
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("OCR no disponible: %s", exc)
            return []

        words: List[Dict[str, Any]] = []
        for idx, raw in enumerate(data.get("text", [])):
            text = (raw or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][idx])
            except (TypeError, ValueError):
                conf = -1.0
            words.append(
                {
                    "text": text,
                    "conf": conf,
                    "left": int(data["left"][idx]),
                    "top": int(data["top"][idx]),
                    "width": int(data["width"][idx]),
                    "height": int(data["height"][idx]),
                }
            )
        return words


ocr_service = OCRService()
