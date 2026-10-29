from fastapi import APIRouter, HTTPException, status
from pathlib import Path
from app.services.extraction_service import extraction_service

router = APIRouter()

@router.post("/leer/{filename}", status_code=status.HTTP_200_OK)
async def leer_planilla_por_nombre(filename: str):
    """
    Procesa directamente una imagen existente en el directorio de almacenamiento
    utilizando inteligencia artificial multimodal (Gemini).
    """
    # Definir la ruta donde se guardan los archivos (ajusta según tu configuración)
    file_path = Path("uploads") / filename
    if not file_path.exists():
        file_path = Path("storage") / filename
        
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El archivo '{filename}' no fue encontrado en el servidor."
        )

    try:
        # Llamar al servicio de extracción con Gemini
        resultado = await extraction_service.extract_from_image(str(file_path))
        return {
            "status": "success",
            "file": filename,
            "data": resultado
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando la planilla con IA: {str(e)}"
        )