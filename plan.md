# PLAN: API REST para digitalización de "Lista de Asistencia" (SFSD0001) con IA

## 1. Objetivo
Construir una API REST en Python (FastAPI) que reciba fotos/escaneos de la plantilla
física "LISTA DE ASISTENCIA — PLANTILLA SFERA SOLUTIONS" (código SFSD0001, REVISION A),
extraiga la información manuscrita mediante IA (OCR + LLM de visión) y la persista en
PostgreSQL, dejando los datos listos para consulta y reportes. Usando modelo local, no usar internet

## 2. Contexto de la plantilla (estructura a reconocer)
- Encabezado: TURNO (ej. "2b"), FECHA (manuscrita, ej. "22/10/2026"), logotipo, número de forma SFSD0001.
- Cuerpo: secciones con filas numeradas. Cada sección tiene el formato:
  NOMBRE DEL TRABAJADOR | ENTRADA | FIRMA | SALIDA | FIRMA
- Secciones fijas (pueden faltar o venir vacías):
  1. SUPERVISOR YSUP JUNIOR (TEC DE QUIMICOS)
  2. GARRAFONEROS
  3. MOLINEROS
  4. TAPIALES, OSCYR Y DEEP DIVE
  5. ALTURAS Y PROFUNDA
  6. AUX DE LIMPIEZA
  7. ADMINISTRATIVO
- Pie de página: FIRMA SUPERVISOR y FIRMA COORDINADOR (presencia de rúbrica).
- Reglas de datos reales:
  - Horas manuscritas variadas: "13:00", "14:00", "2:00", "10.00", "11:50" → normalizar a HH:MM.
  - ENTRADA suele ser PM y SALIDA AM del día siguiente; no inventar, guardar tal cual + flag de AMB/PM si es inferible.
  - Un mismo trabajador puede aparecer en varias secciones (ej. Feranda Rosendo Moreno en Supervisor y Aux de Limpieza).
  - FIRMA: registrar booleano "firma_presente" y, opcionalmente, recorte de la imagen de la rúbrica.
  - Tachaduras, celdas vacías y filas sin usar (sección ADMINISTRATIVO vacía) deben ignorarse o marcarse como vacías.

## 3. Stack técnico
- Lenguaje: Python 3.11+
- Framework: FastAPI + Uvicorn, validación con Pydantic v2
- BD: PostgreSQL 15+ con SQLAlchemy 2.0 (async) + Alembic para migraciones
- IA de extracción (elegir una, con proveedor configurable por settings):
  - Opción A: LLM de visión (Azure OpenAI GPT-4o / OpenAI / Gemini) con salida JSON estructurada (structured output / function calling)
  - Opción B: Azure Document Intelligence (custom model) + post-proceso con LLM para nombres y horas
  - Fallback opcional: Tesseract + OpenCV (deskew, binarización) para preprocesado
- Upload de archivos: almacenamiento local o Azure Blob Storage (configurable)
- Tests: pytest + httpx; cobertura de parseo con imágenes de ejemplo
- Docker/docker-compose para levantar API + Postgres

## 4. Modelo de datos (PostgreSQL)
- planillas (sheets): id, fecha, turno, archivo_original_url, estado (PENDIENTE_REVISION, VALIDADA, RECHAZADA), confianza_global, fecha_procesamiento, firmas_supervisor_presente, firmas_coordinador_presente, created_at, updated_at
- secciones (sections): id, planilla_id FK, tipo_seccion (enum con los 7 nombres fijos), numero_en_plantilla
- registros_asistencia (entries): id, seccion_id FK, numero_fila, nombre_trabajador_texto, entrada_texto, salida_texto, entrada_normalizada (time), salida_normalizada (time), firma_entrada_presente (bool), firma_salida_presente (bool), imagen_firma_url (opcional), confianza_nombre, confianza_entrada, confianza_salida, requiere_revision (bool), texto_normalizado_entrada (candidatos matching)
- cat_trabajadores (opcional, fase 2): id, nombre_canonico, activo — para matching difuso (fuzzy matching con rapidfuzz) entre lo manuscrito y el catálogo.
- Regla: guardar SIEMPRE el texto crudo de la IA y el valor normalizado; nunca sobrescribir el crudo.

## 5. Pipeline de procesamiento
1. Recepción de imagen (JPG/PNG/PDF, máx. 15 MB), validación y guardado.
2. Preprocesado con OpenCV: corregir rotación/inclinación (la foto llega torcida), recorte de tabla, mejora de contraste.
3. Extracción IA: enviar la imagen con un prompt que imponga el esquema JSON:
   { turno, fecha, secciones: [ { nombre, registros: [ { fila, nombre, entrada, firma_entrada, salida, firma_salida, confianza_por_campo } ] } ], firma_supervisor, firma_coordinador }
   - Temperatura baja (≤0.1), indicar explícitamente devolver null en celdas vacías o ilegibles, nunca inventar nombres/horas.
4. Normalización: horas → HH:MM (manejar "13.00", "2:00", "14OO"); fechas múltiples formatos; nombres en mayúsculas/título.
5. Cálculo de confianza: si algún registro tiene confianza < umbral (config, ej. 0.7) → marcar requiere_revision.
6. Persistencia transaccional en Postgres.
7. Cola de revisión humana: endpoints para corregir campo por campo; al validar, estado → VALIDADA.

## 6. Endpoints REST
- POST /api/v1/planillas — multipart upload; crea planilla en estado PENDIENTE y dispara procesamiento (BackgroundTasks o worker). Devuelve id + estado.
- GET /api/v1/planillas/{id} — estado y resumen (conteo por sección,置信, requiere_revision).
- GET /api/v1/planillas/{id}/detalle — JSON completo normalizado + crudo + confianza por campo.
- GET /api/v1/planillas — listado con filtros (fecha, turno, estado, requiere_revision) + paginación.
- PATCH /api/v1/planillas/{id}/registros/{registro_id} — corrección manual de campos (nombre, horas, firma).
- POST /api/v1/planillas/{id}/validar | /rechazar — cierre del flujo de revisión.
- GET /api/v1/reportes/asistencia?fecha=&turno= — agrupado por sección.
- GET /health
- Autenticación: API Key (header X-API-Key) en fase 1; JWT en fase 2.

## 7. Requisitos no funcionales
- Config por variables de entorno (pydantic-settings): DATABASE_URL, proveedor IA + clave + modelo, umbral de confianza, tamaño máx. de archivo.
- Logging estructurado con request-id; no loguear contenido sensible del trabajador en DEBUG.
- Idempotencia: re-procesar la misma imagen no duplica planilla (hash SHA-256 del archivo).
- Reintentos y timeout en llamadas al proveedor de IA; si falla, planilla queda PENDIENTE con error registrable.
- Migraciones versionadas; seeds no necesarios.

## 8. Entregables
- Código fuente de la API con estructura: app/(routers, services, models, schemas, core), alembic/, tests/, docker-compose.yml, README.
- Prompt de extracción versiónado (prompts/extraccion_v1.txt) con instrucciones del esquema de la plantilla.
- README con: cómo correr con docker-compose, variables de entorno y ejemplos curl de todos los endpoints.
- Colección de pruebas: al menos 3 imágenes de ejemplo de la plantilla (una limpia, una rotada, una con secciones vacías) y sus tests end-to-end del parseo.

## 9. Criterios de aceptación
- Dada una foto del formato SFSD0001, la API devuelve JSON con turno, fecha y los 7 tipos de sección con sus registros.
- Horas manuscritas "13:00" y "2:00" quedan normalizadas y conservan el texto crudo.
- Registros con confianza baja aparecen marcados requiere_revision=true y son corregibles vía PATCH.
- No se inventan datos: celdas vacías/devueltas null no crean registros.
- docker-compose up deja la API y Postgres operativas; /health responde 200.
- Migraciones de Alembic crean el esquema completo desde cero.