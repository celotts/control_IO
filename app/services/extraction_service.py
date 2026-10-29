import os
import logging
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Cargar automáticamente el archivo .env
load_dotenv()

logger = logging.getLogger(__name__)

class ExtractionService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("No API key was provided. Please configure GEMINI_API_KEY in .env")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def extract_from_image(self, file_path: str) -> dict:
        logger.info(f"Enviando imagen a Gemini para extracción: {file_path}")
        uploaded_file = self.client.files.upload(file=file_path)

        prompt = """
        Eres un experto en digitalización de documentos y control de asistencia laboral.
        Analiza esta plantilla de asistencia manuscrita y extrae la información en un JSON estructurado con el siguiente formato exacto:
        {
            "turno": "Matutino / Vespertino / Nocturno (o null)",
            "fecha": "YYYY-MM-DD (o null si no se detecta)",
            "firmas_supervisor_presente": true/false,
            "firmas_coordinador_presente": true/false,
            "confianza_global": 0.95,
            "secciones": [
                {
                    "nombre_seccion": "Nombre del área o turno",
                    "registros": [
                        {
                            "nombre_trabajador": "Nombre completo detectado",
                            "entrada": "HH:MM (o null)",
                            "salida": "HH:MM (o null)",
                            "firma_entrada_presente": true/false,
                            "firma_salida_presente": true/false
                        }
                    ]
                }
            ]
        }
        Devuelve estrictamente un JSON válido sin texto adicional alrededor.
        """

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        try:
            parsed_data = json.loads(response.text)
            return parsed_data
        except Exception as e:
            logger.error(f"Error decodificando la respuesta JSON de Gemini: {response.text}")
            raise ValueError(f"La respuesta de la IA no devolvió un JSON válido: {e}")

extraction_service = ExtractionService()
