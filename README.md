# API REST - Digitalización Lista de Asistencia SFSD0001

API REST en FastAPI para digitalizar plantillas físicas "LISTA DE ASISTENCIA - PLANTILLA SFERA SOLUTIONS" (código SFSD0001, REVISION A) usando IA para extracción OCR+visión.

## Características

- Recepción de imágenes (JPG/PNG/PDF)
- Extracción con IA (configurable para modelo local)
- Normalización de horas manuscritas
- Persistencia en PostgreSQL con SQLAlchemy async
- Flujo de revisión humana
- Reportes de asistencia
- Autenticación con API Key

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

## Instalación y ejecución con Docker Compose

```bash
# Copiar variables de entorno
cp .env.example .env

# Levantar servicios
docker-compose up --build
```

La API estará disponible en `http://localhost:8000`
- Documentación Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Variables de entorno

Ver `.env.example` para todas las variables. Las principales:
- `DATABASE_URL`: Conexión a PostgreSQL
- `AI_PROVIDER`, `AI_BASE_URL`, `AI_MODEL`: Configuración del proveedor de IA
- `API_KEY`: Clave para autenticación
- `CONFIDENCE_THRESHOLD`: Umbral para marcar revisión (default 0.7)

## Endpoints

### Health
```bash
curl http://localhost:8000/health
```

### Subir planilla
```bash
curl -X POST http://localhost:8000/api/v1/planillas/ \
  -H "X-API-Key: dev-key-change-me" \
  -F "file=@plantilla.jpg"
```

### Listar planillas
```bash
curl "http://localhost:8000/api/v1/planillas/?page=1&size=10" \
  -H "X-API-Key: dev-key-change-me"
```

### Obtener planilla
```bash
curl http://localhost:8000/api/v1/planillas/{id} \
  -H "X-API-Key: dev-key-change-me"
```

### Obtener detalle completo
```bash
curl http://localhost:8000/api/v1/planillas/{id}/detalle \
  -H "X-API-Key: dev-key-change-me"
```

### Corregir registro
```bash
curl -X PATCH http://localhost:8000/api/v1/planillas/{id}/registros/{registro_id} \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"nombre_trabajador_texto": "JUAN PEREZ", "entrada_texto": "08:00"}'
```

### Validar planilla
```bash
curl -X POST http://localhost:8000/api/v1/planillas/{id}/validar \
  -H "X-API-Key: dev-key-change-me"
```

### Rechazar planilla
```bash
curl -X POST http://localhost:8000/api/v1/planillas/{id}/rechazar \
  -H "X-API-Key: dev-key-change-me"
```

### Reporte de asistencia
```bash
curl "http://localhost:8000/api/v1/reportes/asistencia?fecha=2026-10-22&turno=2b" \
  -H "X-API-Key: dev-key-change-me"
```

## Migraciones

```bash
# Crear migración
alembic revision --autogenerate -m "Initial migration"

# Aplicar migraciones
alembic upgrade head
```

## Tests

```bash
pytest -v
```

## Estructura

```
app/
├── core/          # Configuración, BD, seguridad
├── models/        # Modelos SQLAlchemy
├── schemas/       # Schemas Pydantic
├── routers/       # Endpoints
├── services/      # Lógica de negocio (extracción, procesamiento)
└── utils/         # Utilidades
alembic/           # Migraciones
prompts/           # Prompts para IA
tests/             # Pruebas
uploads/           # Archivos subidos
```
