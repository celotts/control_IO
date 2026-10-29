import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SectionSpec:
    name: str
    keywords: Tuple[str, ...]
    ratio: float


# Orden fijo de la plantilla SFSD0001. Los ratios son una referencia
# proporcional para estimar encabezados que el OCR no logre detectar.
SECTION_SPECS: Tuple[SectionSpec, ...] = (
    SectionSpec("SUPERVISOR YSUP JUNIOR (TEC DE QUIMICOS)", ("SUPERVISOR",), 0.225),
    SectionSpec("GARRAFONEROS", ("GARRAFONEROS",), 0.272),
    SectionSpec("MOLINEROS", ("MOLINEROS",), 0.336),
    SectionSpec("TAPIALES, OSCYR Y DEEP DIVE", ("TAPIALES",), 0.391),
    SectionSpec("ALTURAS Y PROFUNDA", ("ALTURAS",), 0.451),
    SectionSpec("AUX DE LIMPIEZA", ("AUX",), 0.532),
    SectionSpec("ADMINISTRATIVO", ("ADMINISTRATIVO",), 0.727),
)

RATIOS = tuple(spec.ratio for spec in SECTION_SPECS)


@dataclass
class SectionRegion:
    name: str
    y0: int
    y1: int
    image: np.ndarray


@dataclass
class RowRegion:
    index: int
    y0: int
    y1: int
    image: np.ndarray


@dataclass
class Layout:
    header: np.ndarray
    sections: List[SectionRegion]
    footer: np.ndarray
    ocr_text: str
    vision_items: List[Dict[str, Any]] = field(default_factory=list)
    detected_sections: int = 0
    header_y1: int = 0
    footer_y0: int = 0


def _normalize(text: str) -> str:
    """Mayúsculas sin acentos ni signos, para comparar texto de OCR."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.upper()
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in ascii_text)
    return " ".join(cleaned.split())


def _matches_section(text: str, keyword: str) -> bool:
    """Coincidencia por palabra, no por substring. Evita que 'A' o 'E'
    coincidan con todos los títulos y que 'OLINEROS' coincida con
    'GARRAFONEROS'."""
    tokens = text.split()
    if not tokens:
        return False
    if keyword == "AUX":
        return "AUX" in tokens
    if keyword in tokens:
        return True
    return any(
        len(token) >= max(5, int(len(keyword) * 0.6))
        and fuzz.ratio(token, keyword) >= 88
        for token in tokens
    )


def _add_candidates(
    candidates: Dict[int, List[int]],
    text: str,
    y: int,
    height: int,
    confidence: float,
) -> None:
    if not text or confidence < 20 or y >= height * 0.85:
        return
    for sec_idx, spec in enumerate(SECTION_SPECS):
        if any(_matches_section(text, keyword) for keyword in spec.keywords):
            candidates.setdefault(sec_idx, []).append(y)


def detect_section_positions(
    image: np.ndarray,
    vision_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[int, int]:
    """Devuelve {índice_sección: y}. Usa primero Vision (macOS), que lee
    mejor los títulos impresos, y Tesseract como respaldo."""
    height = image.shape[0]
    candidates: Dict[int, List[int]] = {}

    for item in vision_items or []:
        _add_candidates(
            candidates,
            _normalize(item.get("text", "")),
            int(item.get("y", 0)),
            height,
            float(item.get("confidence", 0) or 0),
        )

    # Si Vision no está disponible o no encontró suficientes secciones,
    # completamos con Tesseract.
    if len(candidates) < len(SECTION_SPECS):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        scale = 2.0
        upscaled = cv2.resize(
            gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )
        try:
            data = pytesseract.image_to_data(
                upscaled, lang="spa", config="--psm 6", output_type=Output.DICT
            )
            for idx, raw in enumerate(data.get("text", [])):
                try:
                    confidence = float(data["conf"][idx])
                except (TypeError, ValueError):
                    confidence = -1
                _add_candidates(
                    candidates,
                    _normalize(raw),
                    int(data["top"][idx] / scale),
                    height,
                    confidence,
                )
        except Exception as exc:  # pragma: no cover - depende de tesseract
            logger.warning("No se pudo detectar secciones con Tesseract: %s", exc)

    return {idx: int(np.median(values)) for idx, values in candidates.items()}


def _estimate_positions(detected: Dict[int, int], height: int) -> Dict[int, int]:
    positions: Dict[int, int] = {}
    for idx, ratio in enumerate(RATIOS):
        if idx in detected:
            positions[idx] = detected[idx]
            continue

        previous = max((k for k in detected if k < idx), default=None)
        following = min((k for k in detected if k > idx), default=None)

        if previous is not None and following is not None:
            span_ratio = RATIOS[following] - RATIOS[previous]
            if span_ratio > 0:
                y = detected[previous] + (
                    (detected[following] - detected[previous])
                    * (ratio - RATIOS[previous])
                    / span_ratio
                )
            else:
                y = detected[previous]
        elif previous is not None:
            y = detected[previous] * (ratio / RATIOS[previous])
        elif following is not None:
            y = detected[following] * (ratio / RATIOS[following])
        else:
            y = ratio * height
        positions[idx] = int(round(y))

    # Asegura orden vertical y límites razonables.
    last = 0
    for idx in range(len(RATIOS)):
        positions[idx] = max(positions[idx], last + 30)
        positions[idx] = min(positions[idx], int(height * 0.88))
        last = positions[idx]
    return positions


def _prepare_for_model(image: np.ndarray, target_width: int) -> np.ndarray:
    if image.size == 0:
        return image
    scale = max(1.0, target_width / image.shape[1])
    if scale <= 1.0:
        return image
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _enhance_for_second_pass(image: np.ndarray) -> np.ndarray:
    if image.size == 0:
        return image
    try:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lightness = clahe.apply(lightness)
        return cv2.cvtColor(
            cv2.merge([lightness, a_channel, b_channel]), cv2.COLOR_LAB2BGR
        )
    except cv2.error:
        return image


def make_image_variants(
    image: np.ndarray,
    widths: Tuple[int, int] = (1800, 2400),
    *,
    enhance_second: bool = True,
) -> List[np.ndarray]:
    """Dos vistas de la misma región con resolución/contraste distintos.
    Sirven para que las dos lecturas del modelo no compartan el mismo sesgo."""
    if image.size == 0:
        return [image]
    variants = [_prepare_for_model(image, width) for width in widths]
    if enhance_second and len(variants) > 1:
        variants[-1] = _enhance_for_second_pass(variants[-1])
    return variants


def _horizontal_line_centers(section_image: np.ndarray) -> List[int]:
    """Centros (relativos) de las líneas horizontales de una sección."""
    if section_image.size == 0:
        return []
    gray = cv2.cvtColor(section_image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        10,
    )
    kernel_width = max(12, section_image.shape[1] // 4)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    projection = np.mean(horizontal, axis=1)
    indexes = np.where(projection > 10)[0]
    if len(indexes) == 0:
        return []

    groups: List[Tuple[int, int]] = []
    start = previous = int(indexes[0])
    for value in indexes[1:]:
        value = int(value)
        if value - previous <= 3:
            previous = value
            continue
        groups.append((start, previous))
        start = previous = value
    groups.append((start, previous))
    return [int((first + last) / 2) for first, last in groups]


def build_row_regions(
    image: np.ndarray,
    section: SectionRegion,
    *,
    max_rows: int = 20,
    count_hint: Optional[int] = None,
) -> List[RowRegion]:
    """Divide una sección en filas usando las líneas de la tabla.

    Si faltan líneas (habitual en escaneos pobres), estima la altura de fila
    con las líneas disponibles y reparte el área de datos en bandas iguales.
    """
    section_crop = image[section.y0 : section.y1, :]
    if section_crop.size == 0:
        return []

    height = section_crop.shape[0]
    lines = _horizontal_line_centers(section_crop)
    data_start = lines[2] if len(lines) >= 3 else min(max(10, height - 2), 35)
    data_end = max(data_start + 6, height - 3)
    data_height = data_end - data_start
    if data_height < 8:
        return []

    header_height = lines[2] - lines[1] if len(lines) >= 3 else 16
    gaps = [
        second - first
        for first, second in zip(lines[2:], lines[3:])
        if 4 < second - first < 80
    ]

    if len(gaps) >= 2:
        row_height = float(np.median(gaps))
    elif len(gaps) == 1:
        row_height = float(min(gaps[0], max(10, header_height)))
    else:
        row_height = 30.0

    row_height = max(10.0, min(row_height, 40.0))
    if count_hint is not None and 1 <= count_hint <= max_rows:
        # La lectura de nombres por sección devuelve una entrada por fila,
        # incluidas las vacías. Es más fiable que las líneas de la tabla,
        # que a veces faltan en escaneos pobres.
        count = count_hint
    else:
        count = int(round(data_height / row_height))
    count = max(1, min(count, max_rows))

    rows: List[RowRegion] = []
    image_height = image.shape[0]
    for index in range(count):
        start_rel = int(round(data_start + index * data_height / count))
        end_rel = int(round(data_start + (index + 1) * data_height / count))
        if end_rel - start_rel < 5:
            continue
        y0 = max(0, section.y0 + start_rel - 1)
        y1 = min(image_height, section.y0 + end_rel + 1)
        rows.append(
            RowRegion(
                index=index + 1,
                y0=y0,
                y1=y1,
                image=image[y0:y1, :],
            )
        )
    return rows


def build_layout(
    image: np.ndarray,
    ocr_text: str,
    *,
    vision_items: Optional[List[Dict[str, Any]]] = None,
    target_width: int = 1800,
    pad_before: int = 8,
) -> Layout:
    height, _ = image.shape[:2]
    detected = detect_section_positions(image, vision_items=vision_items)
    positions = _estimate_positions(detected, height)

    sections: List[SectionRegion] = []
    for idx, spec in enumerate(SECTION_SPECS):
        y0 = max(0, positions[idx] - pad_before)
        if idx + 1 < len(SECTION_SPECS):
            y1 = min(height, positions[idx + 1])
        else:
            y1 = min(height, int(height * 0.94))

        if y1 <= y0:
            y1 = min(height, y0 + 40)

        crop = image[y0:y1, :]
        sections.append(
            SectionRegion(
                name=spec.name,
                y0=y0,
                y1=y1,
                image=_prepare_for_model(crop, target_width),
            )
        )

    header_end = max(40, positions[0] - 2)
    header = _prepare_for_model(image[0:header_end, :], target_width)

    footer_start = max(0, int(height * 0.84))
    footer = _prepare_for_model(image[footer_start:height, :], target_width)

    return Layout(
        header=header,
        sections=sections,
        footer=footer,
        ocr_text=ocr_text,
        vision_items=vision_items or [],
        detected_sections=len(detected),
        header_y1=header_end,
        footer_y0=footer_start,
    )
