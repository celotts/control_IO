import logging
import os
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EstadoPlanilla
from app.models.planilla import Planilla, RegistroAsistencia, Seccion
from app.services.extraction_service import extraction_service

logger = logging.getLogger(__name__)


class ProcessingService:
    async def process_planilla(self, db: AsyncSession, planilla_id: UUID):
        try:
            # 1. Buscar la planilla en la base de datos
            result = await db.execute(select(Planilla).where(Planilla.id == planilla_id))
            planilla = result.scalar_one_or_none()

            if not planilla or not planilla.archivo_original_url:
                logger.error(f"Planilla {planilla_id} no encontrada o sin archivo asociado.")
                return

            # Resolver la ruta física del archivo guardado
            file_path = planilla.archivo_original_url
            if not os.path.exists(file_path):
                BASE_DIR = Path(__file__).resolve().parents[2]
                file_path = str(BASE_DIR / planilla.archivo_original_url.lstrip("/"))

            # 2. Ejecutar la extracción inteligente con el servicio de IA (GPT-4o)
            data_extraida = await extraction_service.extract_from_image(file_path)

            # 3. Mapear datos principales de la cabecera
            planilla.turno = data_extraida.get("turno")

            fecha_str = data_extraida.get("fecha")
            if fecha_str:
                try:
                    planilla.fecha = date.fromisoformat(fecha_str)
                except Exception:
                    pass

            planilla.firmas_supervisor_presente = data_extraida.get(
                "firmas_supervisor_presente", False
            )
            planilla.firmas_coordinador_presente = data_extraida.get(
                "firmas_coordinador_presente", False
            )
            planilla.confianza_global = data_extraida.get("confianza_global", 1.0)
            planilla.estado = EstadoPlanilla.PENDIENTE_REVISION

            # 4. Guardar Secciones y Registros de Asistencia en la BD
            secciones_data = data_extraida.get("secciones", [])

            for sec_data in secciones_data:
                seccion_obj = Seccion(
                    planilla_id=planilla.id, nombre_seccion=sec_data.get("nombre_seccion")
                )
                db.add(seccion_obj)
                await db.flush()  # Para obtener el ID generado de la sección

                for reg_data in sec_data.get("registros", []):
                    nombre = reg_data.get("nombre_trabajador", "").strip()
                    if not nombre:
                        continue

                    entrada_txt = reg_data.get("entrada")
                    salida_txt = reg_data.get("salida")

                    # Marcar revisión si faltan datos clave
                    requiere_rev = not entrada_txt or not salida_txt

                    registro_obj = RegistroAsistencia(
                        planilla_id=planilla.id,
                        seccion_id=seccion_obj.id,
                        nombre_trabajador_texto=nombre,
                        entrada_texto=entrada_txt,
                        salida_texto=salida_txt,
                        firma_entrada_presente=reg_data.get("firma_entrada_presente", False),
                        firma_salida_presente=reg_data.get("firma_salida_presente", False),
                        requiere_revision=requiere_rev,
                    )
                    db.add(registro_obj)

            await db.commit()
            logger.info(f"Planilla {planilla_id} procesada y digitalizada exitosamente con IA.")

        except Exception as e:
            logger.exception(f"Error crítico procesando la planilla en segundo plano: {e!s}")
            if planilla:
                planilla.estado = EstadoPlanilla.RECHAZADA
                await db.commit()


processing_service = ProcessingService()
