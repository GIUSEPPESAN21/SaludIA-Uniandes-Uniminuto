# SaludIA — Doctor at Home
Versión: 8.0
Desarrollado por: Joseph Javier Sánchez Acuña | Universidad de los Andes / Uniminuto — Proyecto SAVA

## Descripción
Herramienta de soporte a la decisión clínica (CDSS) y tamizaje para médicos que hacen
seguimiento domiciliario de pacientes. El sistema calcula el riesgo clínico de cada
consulta con un **motor de reglas local y determinista** (`clinical_engine.py`), basado en
guías publicadas (ACC/AHA 2017 para presión arterial, ADA 2025 para glucemia, OMS para
IMC, NEWS2 parcial para alerta temprana). Google Gemini es **opcional**: cuando está
disponible, redacta en lenguaje natural el veredicto que el motor local ya calculó; si no
está disponible, el médico igual recibe una evaluación de riesgo completa y explicable.

⚠️ **Este proyecto está pensado para ejecutarse desplegado en Streamlit Community Cloud**,
con las credenciales de Firebase y Gemini configuradas como *Secrets*. No está pensado
para correr en local sin esa configuración.

## Arquitectura
El código está organizado en módulos, no en un único archivo:

* `app.py` — vistas de Streamlit (login, panel de control, dashboard de paciente),
  enrutador y generación de PDF (reporte clínico y receta).
* `clinical_engine.py` — motor de reglas clínicas local: clasifica signos vitales,
  detecta alertas rojas combinando síntomas y signos, analiza tendencias del historial y
  calcula un score de riesgo (0-100) con nivel BAJO/MODERADO/ALTO/CRÍTICO. Cubierto por
  55 pruebas unitarias (`test_clinical_engine.py`).
* `gemini_utils.py` — capa opcional de redacción en lenguaje natural sobre el veredicto
  del motor local; no decide el riesgo, lo explica.
* `firebase_utils.py` — acceso a Firestore (pacientes, consultas) y verificación real de
  contraseña contra Firebase Authentication vía el endpoint REST de Identity Toolkit.
* `ui_components.py` — estilos y componentes de interfaz reutilizables (tarjetas,
  timeline, badges de riesgo).

## Seguridad
* El login verifica la contraseña real contra Firebase Authentication (no solo la
  existencia de la cuenta).
* El autorregistro de médicos está restringido a dominios de correo institucionales
  (configurable en `st.secrets["allowed_email_domains"]`).
* Todo dato de paciente/médico insertado en bloques HTML se escapa (`html.escape`) para
  evitar inyección de HTML almacenada.

Ver [`PRIVACY.md`](PRIVACY.md) para el detalle de qué datos se almacenan.

## Cómo Desplegar
1. **Crea un repositorio en GitHub** con todos los archivos de este proyecto.
2. **Conéctalo a Streamlit Cloud** y despliega la aplicación.
3. **Configura los Secrets de Streamlit** con:
   - `firebase_credentials` — credenciales del Admin SDK (cuenta de servicio) de tu
     proyecto de Firebase.
   - `firebase_web_api_key` — la **Web API Key** del proyecto de Firebase (Configuración
     del proyecto → General), necesaria para verificar contraseñas vía Identity Toolkit.
   - `gemini_api_key` — API Key de Google Generative AI (opcional; sin ella, el sistema
     sigue funcionando solo con el motor de reglas local).
   - `allowed_email_domains` — (opcional) lista de dominios institucionales autorizados
     para autorregistro de médicos. Por defecto: `uniandes.edu.co`, `uniminuto.edu.co`.

## Pruebas
El motor de reglas clínicas tiene su propia batería de pruebas, independiente de la
disponibilidad de Firebase o Gemini:

```bash
python -m pytest test_clinical_engine.py -v
```
