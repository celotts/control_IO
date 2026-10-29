import logging
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
PDF_SUFFIXES = {".pdf"}


class DocumentError(RuntimeError):
    pass


def _render_pdf_with_pymupdf(path: str, target_width: int) -> Optional[np.ndarray]:
    try:
        import fitz  # type: ignore
    except Exception:
        return None

    try:
        document = fitz.open(path)
        if document.page_count == 0:
            raise DocumentError("El PDF no tiene páginas")
        page = document.load_page(0)
        zoom = max(1.0, target_width / max(1.0, page.rect.width))
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, pixmap.n
        )
        if pixmap.n == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image
    except DocumentError:
        raise
    except Exception as exc:
        logger.warning("PyMuPDF no pudo renderizar el PDF: %s", exc)
        return None


def _compile_pdf_renderer() -> Optional[Path]:
    if platform.system() != "Darwin" or shutil.which("swiftc") is None:
        return None
    source = Path(__file__).with_name("pdf_render.swift")
    if not source.is_file():
        return None
    cache_dir = Path(tempfile.gettempdir()) / "control_io_native_ocr"
    cache_dir.mkdir(parents=True, exist_ok=True)
    binary = cache_dir / "pdf_render"
    try:
        if not binary.is_file() or binary.stat().st_mtime < source.stat().st_mtime:
            result = subprocess.run(
                ["swiftc", "-O", str(source), "-o", str(binary)],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                logger.warning("No se pudo compilar el renderizador PDF: %s", result.stderr[:500])
                return None
        return binary
    except Exception as exc:  # pragma: no cover
        logger.warning("Error compilando el renderizador PDF: %s", exc)
        return None


def _render_pdf_with_swift(path: str, target_width: int) -> Optional[np.ndarray]:
    binary = _compile_pdf_renderer()
    if binary is None:
        return None

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    try:
        result = subprocess.run(
            [str(binary), path, str(output), str(target_width)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode != 0:
            logger.warning("Renderizador PDF falló: %s", result.stderr[:500])
            return None
        image = cv2.imread(str(output))
        return image
    except Exception as exc:  # pragma: no cover
        logger.warning("Error renderizando PDF: %s", exc)
        return None
    finally:
        try:
            output.unlink()
        except OSError:
            pass


def load_document(path: str, target_width: int = 2200) -> Tuple[np.ndarray, List[str]]:
    """Carga una imagen o la primera página de un PDF como BGR.

    Devuelve (imagen, advertencias). Para PDFs multi-página se procesa la
    primera página y se avisa, porque la planilla es de una página.
    """
    suffix = Path(path).suffix.lower()
    warnings: List[str] = []

    if suffix in IMAGE_SUFFIXES:
        image = cv2.imread(path)
        if image is None:
            raise DocumentError("No se pudo leer la imagen")
        return image, warnings

    if suffix in PDF_SUFFIXES:
        try:
            import fitz  # type: ignore

            document = fitz.open(path)
            pages = document.page_count
            document.close()
            if pages > 1:
                warnings.append(
                    f"El PDF tiene {pages} páginas; se procesó solo la primera. "
                    "Sube una planilla por archivo para evitar mezclar datos."
                )
        except Exception:
            pass

        image = _render_pdf_with_pymupdf(path, target_width)
        if image is None:
            image = _render_pdf_with_swift(path, target_width)
        if image is None:
            raise DocumentError(
                "No se pudo convertir el PDF. Instala 'pymupdf' o ejecuta en macOS "
                "con las herramientas de Swift disponibles."
            )
        return image, warnings

    raise DocumentError(f"Formato no soportado: {suffix or 'sin extensión'}")
