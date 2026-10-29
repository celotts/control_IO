from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RegistroExtraido(BaseModel):
    """Una fila leída de una sección de la planilla."""

    fila: Optional[int] = None
    nombre: Optional[str] = None
    entrada: Optional[str] = None
    firma_entrada: Optional[bool] = None
    salida: Optional[str] = None
    firma_salida: Optional[bool] = None
    confianza_por_campo: Dict[str, Optional[float]] = Field(default_factory=dict)


class SeccionExtraida(BaseModel):
    nombre: str
    registros: List[RegistroExtraido] = Field(default_factory=list)


class RegistrosExtraidos(BaseModel):
    """Respuesta del modelo para una sola sección."""

    registros: List[RegistroExtraido] = Field(default_factory=list)


class FilaLeida(BaseModel):
    """Respuesta del modelo para una sola fila recortada."""

    nombre: Optional[str] = None
    entrada: Optional[str] = None
    salida: Optional[str] = None


class NombresSeccion(BaseModel):
    """Nombres leídos de una sección completa, en orden de fila."""

    nombres: List[Optional[str]] = Field(default_factory=list)


class EncabezadoExtraido(BaseModel):
    turno: Optional[str] = None
    fecha: Optional[str] = None


class FirmasExtraidas(BaseModel):
    firma_supervisor: Optional[bool] = None
    firma_coordinador: Optional[bool] = None



class ExtraccionPlanilla(BaseModel):
    """Resultado de extracción listo para el endpoint /leer y para procesamiento."""

    turno: Optional[str] = None
    fecha: Optional[str] = None
    secciones: List[SeccionExtraida] = Field(default_factory=list)
    firma_supervisor: Optional[bool] = None
    firma_coordinador: Optional[bool] = None
    advertencias: List[str] = Field(default_factory=list)
    ocr_texto: Optional[str] = None


class LecturaPlanillaResponse(BaseModel):
    archivo: str
    resultado: ExtraccionPlanilla
