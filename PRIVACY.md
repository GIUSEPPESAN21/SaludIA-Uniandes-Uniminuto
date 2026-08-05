# Política de Privacidad y Manejo de Datos

Última actualización: 5 de agosto de 2026

Este documento describe, de forma honesta y verificada contra el código actual del
repositorio, las prácticas de privacidad del prototipo "SaludIA — Doctor at Home".

## 1. Compromiso con la Privacidad

La confidencialidad y seguridad de los datos de salud son una prioridad de este proyecto.
El sistema busca cumplir con la Ley 1581 de 2012 de Colombia (Habeas Data) y aplicar
medidas de seguridad razonables para un prototipo académico. Esta versión del documento
corrige una versión anterior que afirmaba, de forma incorrecta, que no se almacenaba
Información de Identificación Personal (PII).

## 2. Qué datos se recolectan y almacenan

La plataforma **sí almacena PII** de los pacientes, introducida por el médico tratante,
porque el flujo clínico (historial por paciente, generación de recetas y reportes en PDF)
lo requiere:

- **Identificación del paciente:** nombre completo y número de documento (cédula), en
  texto plano. La cédula se usa además como identificador del registro del paciente en
  la base de datos.
- **Datos de contacto:** teléfono del paciente.
- **Datos clínicos:** motivo de consulta, signos vitales (presión arterial, frecuencia
  cardíaca, glucemia, peso, altura, IMC), síntomas marcados en la revisión por sistemas,
  documentos de laboratorio adjuntos y los análisis generados (por el motor de reglas
  clínicas local y, opcionalmente, por la IA de Gemini).
- **Identificación del médico tratante:** correo electrónico institucional, usado como
  clave de acceso a sus propios pacientes.

Estos datos se almacenan en texto plano (no cifrados ni pseudonimizados) en la base de
datos del proyecto. **No se aplica ningún proceso de hashing o anonimización** a nombres,
cédulas o teléfonos en la versión actual del sistema.

## 3. Separación de datos por médico

Cada médico solo puede ver y gestionar los pacientes que él mismo ha registrado. Esta
separación se aplica en la capa de aplicación (Streamlit + Firebase Admin SDK). El acceso
al panel requiere verificación real de contraseña contra Firebase Authentication, y el
autorregistro de nuevas cuentas de médico está restringido a dominios de correo
institucionales autorizados.

## 4. Seguridad de la Base de Datos (Firebase Firestore)

La conexión a la base de datos se realiza mediante credenciales de servicio gestionadas
exclusivamente a través del sistema de "Secrets" de Streamlit Community Cloud; estas
credenciales nunca se exponen en el código público del repositorio.

## 5. Uso de Inteligencia Artificial (Google Gemini)

Cuando el médico solicita una redacción en lenguaje natural del veredicto clínico, se
envían a la API de Google Gemini los datos de la consulta actual, un resumen del
historial del paciente y el resultado ya calculado por el motor de reglas local. Estos
datos están sujetos, adicionalmente, a las políticas de privacidad de Google para la API
de Gemini. Si Gemini no está disponible, el sistema sigue entregando una evaluación de
riesgo completa calculada localmente, sin enviar ningún dato a servicios externos.

## 6. Derechos del paciente y del médico

Cualquier paciente puede solicitar al médico tratante la corrección o eliminación de sus
datos registrados en el sistema. El médico, como responsable del tratamiento de los datos
que introduce, es quien debe canalizar estas solicitudes.

## 7. Consentimiento Informado

La plataforma requiere que el usuario acepte explícitamente estos términos antes de poder
enviar cualquier dato.

**Advertencia:** Este sistema es una herramienta de apoyo a la decisión clínica (CDSS) y
de tamizaje. **No sustituye, bajo ninguna circunstancia, un diagnóstico o consulta médica
profesional.**
