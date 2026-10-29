import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, DateTime, Float, Boolean, Integer, ForeignKey, Enum, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import EstadoPlanilla, TipoSeccion


class Planilla(Base):
    __tablename__ = "planillas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha = Column(Date, nullable=True)
    turno = Column(String(50), nullable=True)
    archivo_original_url = Column(String(512), nullable=True)
    archivo_hash_sha256 = Column(String(64), unique=True, nullable=True)
    estado = Column(Enum(EstadoPlanilla), default=EstadoPlanilla.PENDIENTE_REVISION, nullable=False)
    confianza_global = Column(Float, nullable=True)
    fecha_procesamiento = Column(DateTime(timezone=True), nullable=True)
    firmas_supervisor_presente = Column(Boolean, default=False)
    firmas_coordinador_presente = Column(Boolean, default=False)
    error_mensaje = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    secciones = relationship("Seccion", back_populates="planilla", cascade="all, delete-orphan")
    registros_asistencia = relationship("RegistroAsistencia", back_populates="planilla", cascade="all, delete-orphan")


class Seccion(Base):
    __tablename__ = "secciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planilla_id = Column(UUID(as_uuid=True), ForeignKey("planillas.id", ondelete="CASCADE"), nullable=False)
    tipo_seccion = Column(Enum(TipoSeccion), nullable=False)
    numero_en_plantilla = Column(Integer, nullable=True)

    planilla = relationship("Planilla", back_populates="secciones")
    registros = relationship("RegistroAsistencia", back_populates="seccion", cascade="all, delete-orphan")


class RegistroAsistencia(Base):
    __tablename__ = "registros_asistencia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planilla_id = Column(UUID(as_uuid=True), ForeignKey("planillas.id", ondelete="CASCADE"), nullable=True)
    seccion_id = Column(UUID(as_uuid=True), ForeignKey("secciones.id", ondelete="CASCADE"), nullable=False)
    numero_fila = Column(Integer, nullable=True)
    nombre_trabajador_texto = Column(Text, nullable=True)
    nombre_trabajador_texto_crudo = Column(Text, nullable=True)
    entrada_texto = Column(String(50), nullable=True)
    salida_texto = Column(String(50), nullable=True)
    entrada_normalizada = Column(Time, nullable=True)
    salida_normalizada = Column(Time, nullable=True)
    firma_entrada_presente = Column(Boolean, default=False)
    firma_salida_presente = Column(Boolean, default=False)
    imagen_firma_url = Column(String(512), nullable=True)
    confianza_nombre = Column(Float, nullable=True)
    confianza_entrada = Column(Float, nullable=True)
    confianza_salida = Column(Float, nullable=True)
    requiere_revision = Column(Boolean, default=False)
    texto_normalizado_entrada = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    planilla = relationship("Planilla", back_populates="registros_asistencia")
    seccion = relationship("Seccion", back_populates="registros")


class CatTrabajador(Base):
    __tablename__ = "cat_trabajadores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_canonico = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
