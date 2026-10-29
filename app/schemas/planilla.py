from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, time, datetime
from uuid import UUID

from app.models.enums import EstadoPlanilla, TipoSeccion


class RegistroAsistenciaBase(BaseModel):
    numero_fila: Optional[int] = None
    nombre_trabajador_texto: Optional[str] = None
    entrada_texto: Optional[str] = None
    salida_texto: Optional[str] = None
    firma_entrada_presente: bool = False
    firma_salida_presente: bool = False
    confianza_nombre: Optional[float] = None
    confianza_entrada: Optional[float] = None
    confianza_salida: Optional[float] = None


class RegistroAsistenciaCreate(RegistroAsistenciaBase):
    pass


class RegistroAsistenciaUpdate(BaseModel):
    nombre_trabajador_texto: Optional[str] = None
    entrada_texto: Optional[str] = None
    salida_texto: Optional[str] = None
    firma_entrada_presente: Optional[bool] = None
    firma_salida_presente: Optional[bool] = None


class RegistroAsistenciaSchema(RegistroAsistenciaBase):
    id: UUID
    seccion_id: UUID
    planilla_id: Optional[UUID] = None
    nombre_trabajador_texto_crudo: Optional[str] = None
    entrada_normalizada: Optional[time] = None
    salida_normalizada: Optional[time] = None
    imagen_firma_url: Optional[str] = None
    requiere_revision: bool = False
    texto_normalizado_entrada: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeccionBase(BaseModel):
    tipo_seccion: TipoSeccion
    numero_en_plantilla: Optional[int] = None


class SeccionCreate(SeccionBase):
    registros: List[RegistroAsistenciaCreate] = []


class SeccionSchema(SeccionBase):
    id: UUID
    planilla_id: UUID
    registros: List[RegistroAsistenciaSchema] = []

    class Config:
        from_attributes = True


class PlanillaCreate(BaseModel):
    turno: Optional[str] = None
    fecha: Optional[date] = None


class PlanillaSchema(BaseModel):
    id: UUID
    fecha: Optional[date] = None
    turno: Optional[str] = None
    archivo_original_url: Optional[str] = None
    estado: EstadoPlanilla
    confianza_global: Optional[float] = None
    fecha_procesamiento: Optional[datetime] = None
    firmas_supervisor_presente: bool = False
    firmas_coordinador_presente: bool = False
    error_mensaje: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    secciones: List[SeccionSchema] = []

    class Config:
        from_attributes = True


class PlanillaResumen(BaseModel):
    id: UUID
    fecha: Optional[date] = None
    turno: Optional[str] = None
    archivo_original_url: Optional[str] = None
    estado: EstadoPlanilla
    confianza_global: Optional[float] = None
    fecha_procesamiento: Optional[datetime] = None
    firmas_supervisor_presente: bool = False
    firmas_coordinador_presente: bool = False
    total_secciones: int = 0
    total_registros: int = 0
    registros_requieren_revision: int = 0
    created_at: datetime
    updated_at: datetime


class PlanillaDetalle(BaseModel):
    planilla: PlanillaSchema
    resumen: PlanillaResumen


class PlanillaListResponse(BaseModel):
    items: List[PlanillaResumen]
    total: int
    page: int
    size: int


class ExtractionResult(BaseModel):
    turno: Optional[str] = None
    fecha: Optional[str] = None
    secciones: List[Any] = []
    firma_supervisor: Optional[bool] = None
    firma_coordinador: Optional[bool] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
