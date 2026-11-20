# -*- coding: utf-8 -*-
"""
Módulo de Utilidades de Gemini AI - v5.0
Gemini ya NO decide el riesgo clínico: el motor de reglas local
(clinical_engine.py) calcula un veredicto determinista y este módulo,
opcionalmente, lo redacta en lenguaje natural para el médico. Si Gemini no
está disponible, el veredicto local sigue siendo válido y completo.
"""
import streamlit as st
import google.generativeai as genai
import logging
import time
from pypdf import PdfReader
from google.api_core import exceptions

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = 8000


class GeminiUtils:
    def __init__(self):
        self.api_key = st.secrets.get('gemini_api_key')
        self.model = None
        self.active_model_name = None
        if not self.api_key:
            logger.error("API Key de Gemini no encontrada en st.secrets.")
            return

        genai.configure(api_key=self.api_key)

        # MODELOS ACTUALIZADOS DICIEMBRE 2024
        # Basado en: https://ai.google.dev/gemini-api/docs/models/gemini
        self.models_priority = [
            "gemini-flash-latest",      # Alias oficial de Google: siempre apunta al Flash vigente
            "gemini-flash-lite-latest", # Alias oficial: Flash-Lite vigente (fallback)
        ]
        self._init_best_model()

    def _init_best_model(self):
        """Intenta inicializar el mejor modelo disponible."""
        for model_name in self.models_priority:
            try:
                self.model = genai.GenerativeModel(model_name)
                # Quick test
                self.model.generate_content("test", generation_config={'max_output_tokens': 5})
                logger.info(f"✅ Modelo activo: {model_name}")
                self.active_model_name = model_name
                return
            except Exception as e:
                logger.warning(f"❌ {model_name}: {str(e)[:60]}")
                continue

        logger.error("No se pudo conectar a ningún modelo de IA.")
        self.model = None

    def _fallback_order(self):
        """Devuelve models_priority reordenada para empezar por el modelo
        que ya se sabe que funciona (self.active_model_name), en vez de
        reintentar siempre desde el primero de la lista. Evita pagar la
        latencia de un modelo saturado en cada llamada cuando ya existe
        uno que responde."""
        if not self.active_model_name:
            return self.models_priority
        return [self.active_model_name] + [
            m for m in self.models_priority if m != self.active_model_name
        ]

    def _generate_with_fallback(self, prompt, config=None):
        """Genera contenido con fallback automático entre modelos,
        empezando por el modelo que ya se sabe que funciona."""
        if not self.model:
            return "⚠️ Servicio de IA no disponible. Verifique la API Key de Gemini en los Secrets."

        last_error_kind = None
        for model_name in self._fallback_order():
            try:
                active = genai.GenerativeModel(model_name)
                response = active.generate_content(prompt, generation_config=config)
                return response.text
            except exceptions.ResourceExhausted:
                logger.warning(f"429 (cuota) en {model_name}, probando siguiente...")
                last_error_kind = "quota"
                time.sleep(0.5)
                continue
            except (exceptions.Unauthenticated, exceptions.PermissionDenied):
                logger.error(f"Credenciales inválidas para {model_name}.")
                return "⚠️ La API Key de Gemini es inválida o no tiene permisos. Verifique la configuración."
            except exceptions.InvalidArgument as e:
                logger.error(f"Solicitud rechazada por Gemini ({model_name}): {str(e)[:100]}")
                last_error_kind = "invalid"
                continue
            except Exception as e:
                logger.warning(f"Error en {model_name}: {str(e)[:80]}")
                last_error_kind = "other"
                continue

        if last_error_kind == "quota":
            return "⚠️ Todos los modelos de IA están saturados (límite de cuota). Intente en 1 minuto."
        if last_error_kind == "invalid":
            return "⚠️ Gemini rechazó la solicitud (contenido no permitido o entrada inválida)."
        return "⚠️ El servicio de IA no está disponible en este momento (error de red o del proveedor)."

    def extract_text_from_pdf(self, uploaded_file):
        try:
            reader = PdfReader(uploaded_file)
            return "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception as e:
            return f"[Error leyendo PDF: {e}]"

    def analyze_clinical_document(self, text_content):
        truncated = len(text_content) > MAX_DOCUMENT_CHARS
        excerpt = text_content[:MAX_DOCUMENT_CHARS]
        prompt = f"""Analiza este reporte médico y lista SOLO los hallazgos anormales:

{excerpt}

Formato: - ⚠️ [Hallazgo]: [Interpretación breve]
Si todo es normal: "✅ Sin hallazgos patológicos"
"""
        result = self._generate_with_fallback(prompt)
        if truncated:
            result += (
                f"\n\n> ⚠️ *Nota: el documento tiene más de {MAX_DOCUMENT_CHARS} caracteres; "
                "solo se analizó la primera parte. Revise el resto manualmente.*"
            )
        return result

    @st.cache_data(show_spinner=False, ttl=600)
    def generate_ai_holistic_review(_self, patient_info, latest_consultation, history_summary,
                                     risk_summary=None):
        """Redacta en lenguaje natural el veredicto clínico que YA calculó
        el motor de reglas local (clinical_engine.evaluar_riesgo_clinico).

        Gemini deja de decidir el riesgo desde cero: recibe `risk_summary`
        (el texto de ResultadoRiesgo.resumen_texto()) como contexto y su
        única tarea es explicarlo con empatía y claridad para el médico,
        sin contradecir el veredicto local salvo que tenga una
        justificación clínica explícita que debe declarar.
        """
        veredicto = risk_summary or (
            "No se calculó un veredicto local para esta consulta (datos insuficientes)."
        )
        prompt = f"""**CASO CLÍNICO:**
Paciente: {patient_info.get('nombre', 'N/A')} ({patient_info.get('edad', '?')} años)
Motivo de consulta: {latest_consultation.get('motivo_consulta', 'Sin datos')}
Signos vitales: PA {latest_consultation.get('presion_sistolica')}/{latest_consultation.get('presion_diastolica')}, \
FC {latest_consultation.get('frec_cardiaca')}, Glucemia {latest_consultation.get('glucemia')}, \
IMC {latest_consultation.get('imc')}

**HISTORIAL CLÍNICO DEL PACIENTE:**
{history_summary}

**VEREDICTO YA CALCULADO POR EL MOTOR DE REGLAS CLÍNICAS LOCAL (determinista, basado en guías publicadas):**
{veredicto}

**TU TAREA COMO MÉDICO INTERNISTA:**
Redacta una nota clínica breve y empática para el médico tratante que EXPLIQUE el
veredicto anterior en lenguaje natural. NO generes un nivel de riesgo distinto al
indicado arriba salvo que exista una razón clínica clara que debas declarar
explícitamente. Estructura tu respuesta así:
1. **Interpretación clínica:** (explica los hallazgos del veredicto en contexto del caso)
2. **Diagnóstico(s) probable(s):** (justificación breve)
3. **Plan sugerido:** 3 acciones concretas
"""
        config = genai.types.GenerationConfig(temperature=0.3, max_output_tokens=1024)
        return _self._generate_with_fallback(prompt, config)
