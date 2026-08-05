# -*- coding: utf-8 -*-
"""
Módulo de Utilidades de Firebase
Descripción: Centraliza toda la lógica para interactuar con Firestore y con
Firebase Authentication, incluyendo la inicialización de la conexión y las
operaciones CRUD (Crear, Leer, Actualizar, Borrar) para los datos de
médicos y pacientes.
"""
# --- LIBRERÍAS ---
import logging

import requests
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger(__name__)

# Dominios institucionales autorizados para autorregistro de médicos.
# Se puede sobreescribir en st.secrets["allowed_email_domains"] (lista de
# strings, sin '@', en minúsculas) sin tocar el código.
DEFAULT_ALLOWED_EMAIL_DOMAINS = ["uniandes.edu.co", "uniminuto.edu.co"]

# Endpoint público de Identity Toolkit (Google Identity Platform) usado para
# verificar contraseñas de verdad. El Admin SDK (firebase_admin.auth) NO
# puede hacer esto: solo administra cuentas, no valida credenciales.
_IDENTITY_TOOLKIT_SIGNIN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
)

_CACHE_TTL_SECONDS = 45


# --- CONEXIÓN INICIAL ---
@st.cache_resource
def init_firebase():
    """Inicializa y retorna el cliente de la base de datos Firestore."""
    try:
        creds_dict = dict(st.secrets["firebase_credentials"])
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        if not firebase_admin._apps:
            creds = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(creds)
        db_client = firestore.client()
        return db_client
    except Exception:
        logger.exception("Error crítico al conectar con Firebase")
        st.error(
            "🔥 No se pudo conectar con la base de datos. Verifique la configuración "
            "de 'firebase_credentials' en los Secrets de Streamlit.",
            icon="🔥",
        )
        return None


DB = init_firebase()


# --- AUTENTICACIÓN ---
def is_physician_email_allowed(email: str) -> bool:
    """Valida si un correo pertenece a un dominio institucional autorizado
    para autorregistrarse como médico. Configurable vía
    st.secrets['allowed_email_domains']; si no se define, usa
    DEFAULT_ALLOWED_EMAIL_DOMAINS.
    """
    if not email or "@" not in email:
        return False
    domain = email.strip().lower().split("@")[-1]
    allowed = st.secrets.get("allowed_email_domains", DEFAULT_ALLOWED_EMAIL_DOMAINS)
    return domain in {d.strip().lower() for d in allowed}


def verify_password(email: str, password: str):
    """Verifica la contraseña de un médico contra Firebase Authentication
    usando el endpoint REST de Identity Toolkit (signInWithPassword).

    El Admin SDK (firebase_admin.auth.get_user_by_email) NO valida
    contraseñas: solo confirma que existe una cuenta con ese correo. Este
    endpoint sí valida la contraseña real, usando la Web API Key del
    proyecto (st.secrets['firebase_web_api_key']).

    Devuelve (ok: bool, message: str). `message` es apto para mostrarse
    directamente al usuario (nunca incluye detalles internos).
    """
    api_key = st.secrets.get("firebase_web_api_key")
    if not api_key:
        logger.error("firebase_web_api_key no configurada en st.secrets.")
        return False, (
            "⚠️ El inicio de sesión no está configurado correctamente "
            "(falta la Web API Key de Firebase). Contacte al administrador."
        )

    try:
        response = requests.post(
            _IDENTITY_TOOLKIT_SIGNIN_URL,
            params={"key": api_key},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Error de red verificando credenciales en Identity Toolkit.")
        return False, "⚠️ No se pudo contactar el servicio de autenticación. Intente de nuevo."

    if response.status_code == 200:
        return True, "OK"

    try:
        error_code = response.json().get("error", {}).get("message", "")
    except ValueError:
        error_code = ""

    logger.warning("Login fallido para %s: %s", email, error_code)

    if error_code in ("INVALID_PASSWORD", "EMAIL_NOT_FOUND", "INVALID_LOGIN_CREDENTIALS"):
        return False, "❌ Credenciales inválidas"
    if error_code == "USER_DISABLED":
        return False, "❌ Esta cuenta ha sido deshabilitada."
    if error_code == "TOO_MANY_ATTEMPTS_TRY_LATER":
        return False, "⚠️ Demasiados intentos fallidos. Intente de nuevo en unos minutos."
    return False, "⚠️ No se pudo verificar el inicio de sesión. Intente de nuevo."


# --- FUNCIONES DE PACIENTES ---
@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def get_physician_patients(physician_email):
    """Obtiene una lista de todos los pacientes asociados a un médico.
    Cacheado con TTL corto para no golpear Firestore en cada rerun de
    Streamlit; se invalida explícitamente al guardar un paciente nuevo.
    """
    if not DB:
        return []
    patients_ref = DB.collection('physicians').document(physician_email).collection('patients').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in patients_ref]


def get_patient_details(physician_email, patient_id):
    """Obtiene los detalles de un paciente específico."""
    if not DB:
        return {}
    try:
        patient_ref = DB.collection('physicians').document(physician_email).collection('patients').document(patient_id)
        patient_doc = patient_ref.get()
        if patient_doc.exists:
            return patient_doc.to_dict()
        st.warning("No se encontró el registro del paciente.")
        return {}
    except Exception:
        logger.exception("Error cargando detalles del paciente %s", patient_id)
        st.error("No se pudieron cargar los datos del paciente. Intente de nuevo.")
        return {}


def save_new_patient(physician_email, patient_data) -> bool:
    """Guarda un nuevo paciente en la base de datos."""
    if not DB:
        return False
    try:
        DB.collection('physicians').document(physician_email).collection('patients').document(
            patient_data['cedula']
        ).set(patient_data)
    except Exception:
        logger.exception("Error guardando paciente nuevo")
        st.error("No se pudo registrar el paciente. Intente de nuevo.")
        return False
    st.success(f"Paciente {patient_data['nombre']} registrado exitosamente.")
    get_physician_patients.clear()
    return True


# --- FUNCIONES DE CONSULTAS ---
def save_consultation(physician_email, patient_id, consultation_data):
    """Guarda una nueva consulta para un paciente. Devuelve el id del
    documento creado, o None si la escritura falló."""
    if not DB:
        return None
    timestamp = datetime.now(timezone.utc)
    doc_id = timestamp.strftime('%Y-%m-%d_%H-%M-%S')
    consultation_data['timestamp_utc'] = timestamp.isoformat()
    clean_data = {k: v for k, v in consultation_data.items() if v is not None and v != ''}
    try:
        DB.collection('physicians').document(physician_email).collection('patients').document(
            patient_id
        ).collection('consultations').document(doc_id).set(clean_data)
    except Exception:
        logger.exception("Error guardando consulta para paciente %s", patient_id)
        st.error("⚠️ No se pudo guardar la consulta. Verifique su conexión e intente de nuevo.")
        return None
    st.toast("Consulta guardada.", icon="✅")
    load_patient_history.clear()
    return doc_id


def update_consultation_with_ai_analysis(physician_email, patient_id, consultation_id, ai_report,
                                          extra_fields=None):
    """Actualiza una consulta existente con el análisis de la IA y,
    opcionalmente, otros campos (por ejemplo, el veredicto del motor de
    reglas clínicas si no se había calculado/guardado antes)."""
    if not DB:
        return False
    try:
        consultation_ref = DB.collection('physicians').document(physician_email).collection('patients').document(
            patient_id
        ).collection('consultations').document(consultation_id)
        update_data = {"ai_analysis": ai_report}
        if extra_fields:
            update_data.update(extra_fields)
        consultation_ref.update(update_data)
    except Exception:
        logger.exception("Error guardando análisis de IA para consulta %s", consultation_id)
        st.error("⚠️ No se pudo guardar el análisis de IA. Intente de nuevo.")
        return False
    st.toast("Análisis de IA guardado en el historial.", icon="🧠")
    load_patient_history.clear()
    return True


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def load_patient_history(physician_email, patient_id):
    """Carga el historial completo de consultas de un paciente. Cacheado
    con TTL corto; se invalida explícitamente al guardar una consulta o un
    análisis de IA nuevo."""
    if not DB:
        return pd.DataFrame()
    consultations_ref = DB.collection('physicians').document(physician_email).collection('patients').document(
        patient_id
    ).collection('consultations').order_by('timestamp_utc', direction=firestore.Query.DESCENDING).stream()
    records = []
    for doc in consultations_ref:
        record = doc.to_dict()
        record['id'] = doc.id
        records.append(record)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    return df
