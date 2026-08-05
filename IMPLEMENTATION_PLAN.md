# Plan de Modernización y Escalamiento - Doctor at Home (SaludIA)

## 1. Diagnóstico Actual
El sistema actual es funcional pero monolítico.
- **Puntos Fuertes:** Integración clara con Firebase y Gemini. Uso de Streamlit para rapidez de desarrollo.
- **Debilidades:**
  - **Código Monolítico:** `app.py` contiene lógica de vista, controlador, estilos y ruteo. Difícil de mantener.
  - **UI Limitada:** Depende de inyección de CSS básica y componentes estándar de Streamlit que lucen "genéricos".
  - **Falta de Visualización:** Muchos datos (presión, glucosa) se ven como texto, perdiendo valor clínico.
  - **Validación de Datos:** No hay validación robusta (Pydantic) antes de enviar a la DB.

## 2. Propuesta de Arquitectura (MVC)
Para aumentar la "lógica del programa" y hacerlo eficiente, reestructuraremos el código:

```text
/
├── .streamlit/
│   └── config.toml      # Configuración de tema
├── assets/
│   ├── style.css        # CSS profesional centralizado
│   └── logo.png
├── components/          # Componentes de UI reutilizables
│   ├── cards.py         # Tarjetas de pacientes personalizadas
│   ├── charts.py        # Gráficos de tendencias (Plotly)
│   └── navigation.py    # Menú lateral moderno
├── models/
│   ├── patient.py       # Modelos de datos (Pydantic)
│   └── consultation.py
├── services/
│   ├── auth_service.py  # Lógica de Login/Registro
│   ├── db_service.py    # Abstracción de Firebase
│   └── ai_service.py    # Lógica avanzada de Gemini
├── views/
│   ├── dashboard.py     # Vista principal de doctor
│   ├── patient_detail.py# Vista detalle paciente
│   └── login.py
└── app.py               # Punto de entrada limpio
```

## 3. Mejoras Visuales (UI/UX Premium)
- **Tema Unificado:** Paleta de colores clínicos (Azul Profundo, Verde Menta, Blanco Puro) con soporte robusto de Dark Mode.
- **Dashboard Interactivo:**
  - Uso de **Gráficos Interactivos (Plotly)** para ver la evolución de la presión arterial y glucosa.
  - **Tarjetas de Estadísticas (Kpis):** Total pacientes, Consultas hoy, Alertas de riesgo.
- **Navegación:** Barra lateral colapsable y limpia.

## 4. Potenciales Nuevas Funcionalidades
1.  **Analítica Visual:** Gráficas de tendencias para cada signo vital.
2.  **Consulta por Voz:** Integración de reconocimiento de voz para dictar la anamnesis.
3.  **Análisis Multimodal:** Subir foto de un examen o radiografía para análisis preliminar de IA.
4.  **Generación de Recetas:** Módulo para crear y exportar recetas médicas PDF formales.
5.  **Asistente de Triaje:** IA sugiere prioridad de atención basada en síntomas ingresados.

## 5. Plan de Ejecución
1.  **Fase 1: Refactorización (Logic Boost):** Separar lógica en servicios y modelos. Implementar validaciones.
2.  **Fase 2: UI Overhaul:** Implementar CSS avanzado y componentes visuales nuevos.
3.  **Fase 3: Features:** Añadir gráficas y carga de documentos.
