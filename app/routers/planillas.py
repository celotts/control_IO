import logging
from fastapi import APIRouter, HTTPException, status
from pathlib import Path
from app.services.extraction_service import extraction_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.api_route("/leer/{filename:path}", methods=["GET", "POST"], status_code=status.HTTP_200_OK)
async def leer_planilla_por_nombre(filename: str):
    """
    Procesa directamente una imagen buscando en planilla/sinprocesar/, uploads/ o storage/
    utilizando inteligencia artificial multimodal (Gemini).
    """
    base_dir = Path(__file__).resolve().parents[2]
    
    # Rutas prioritarias donde podría estar el archivo
    possible_paths = [
        base_dir / "planilla" / "sinprocesar" / filename,
        base_dir / filename,
        base_dir / "uploads" / filename,
        base_dir / "storage" / filename,
        Path("planilla") / "sinprocesar" / filename,
        Path(filename),
        Path("uploads") / filename,
        Path("storage") / filename,
    ]

    file_path = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            file_path = p
            break

    # Si no se encontró directamente, buscar de forma recursiva por nombre de archivo
    if not file_path:
        for found in base_dir.glob(f"**/{Path(filename).name}"):
            if found.is_file():
                file_path = found
                break

    if not file_path or not file_path.exists():
        logger.error(f"Archivo no encontrado: {filename}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El archivo '{filename}' no fue encontrado en la carpeta planilla/sinprocesar/ ni en el servidor."
        )

    try:
        logger.info(f"Procesando archivo encontrado en: {file_path}")
        resultado = await extraction_service.extract_from_image(str(file_path))
        return {
            "status": "success",
            "file": filename,
            "path_used": str(file_path),
            "data": resultado
        }
    except Exception as e:
        logger.exception(f"Error procesando la planilla con IA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando la planilla con IA: {str(e)}"
        )
