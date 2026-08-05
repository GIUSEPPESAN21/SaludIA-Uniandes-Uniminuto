# -*- coding: utf-8 -*-
"""
Módulo de Componentes UI - v8.0
Componentes de UI/UX + presentación del veredicto del motor de reglas
clínicas local (clinical_engine.py), fuente única de verdad para
umbrales clínicos: nada de esto debe duplicar umbrales por su cuenta.
"""
import html as _html

import streamlit as st
import pandas as pd

import clinical_engine as ce

# Colores por nivel de riesgo, consistentes con clinical_engine.ResultadoRiesgo.nivel_riesgo
_RISK_COLORS = {
    "BAJO": {"bg": "#ECFDF5", "fg": "#059669"},
    "MODERADO": {"bg": "#FEF3C7", "fg": "#D97706"},
    "ALTO": {"bg": "#FFEDD5", "fg": "#EA580C"},
    "CRITICO": {"bg": "#FEE2E2", "fg": "#DC2626"},
}


def _esc(value) -> str:
    """Escapa datos de usuario antes de insertarlos en HTML renderizado
    con unsafe_allow_html=True, para prevenir inyección de HTML/JS
    almacenada."""
    return _html.escape(str(value), quote=True)

# ==============================================================================
# CSS PREMIUM - CORREGIDO
# ==============================================================================
def load_custom_css():
    """CSS pulido con todas las correcciones."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        :root {
            /* Paleta Médica SOBRIA - más clínica y calmada */
            --primary: #0A6DC2;           /* Azul más sobrio/profesional */
            --primary-dark: #085A9E;
            --primary-light: #E8F4FC;
            --primary-gradient: linear-gradient(135deg, #0A6DC2 0%, #0891B2 100%); /* Azul a Cian */
            
            --success: #059669;
            --warning: #D97706;
            --danger: #DC2626;
            
            --bg-primary: #F8FAFC;
            --bg-card: #FFFFFF;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --border: #E2E8F0;
            --border-focus: #0A6DC2;
            
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
            
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }
        
        .stApp {
            background: linear-gradient(180deg, #F0F9FF 0%, #F8FAFC 100%) !important;
        }

        h1 {
            font-size: 2rem !important;
            font-weight: 800 !important;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        h2, h3 { font-weight: 700; color: var(--text-primary); }

        /* === TABS - Línea AZUL en vez de roja === */
        button[data-baseweb="tab"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-secondary);
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 3px solid var(--primary) !important;
            background: transparent !important;
        }
        
        button[data-baseweb="tab"]:hover {
            color: var(--primary);
        }
        
        /* Eliminar cualquier línea roja residual */
        div[data-baseweb="tab-highlight"] {
            background-color: var(--primary) !important;
        }
        
        div[data-baseweb="tab-border"] {
            background-color: var(--border) !important;
        }

        /* === INPUTS - Fondo BLANCO con borde suave === */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] > div > div {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background: #FFFFFF !important;
            border: 1.5px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            padding: 0.75rem 1rem !important;
            font-size: 0.9375rem !important;
            color: var(--text-primary) !important;
            transition: all 0.2s ease !important;
        }
        
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(10, 109, 194, 0.12) !important;
            outline: none !important;
        }
        
        div[data-testid="stTextInput"] input::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder {
            color: var(--text-muted) !important;
        }

        /* === BOTONES === */
        div[data-testid="stButton"] > button {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-weight: 600;
            border-radius: var(--radius-md);
            transition: all 0.2s ease;
            font-size: 0.875rem;
        }
        
        div[data-testid="stButton"] > button[kind="primary"] {
            background: var(--primary-gradient);
            color: white;
            border: none;
            box-shadow: 0 4px 12px rgba(10, 109, 194, 0.25);
        }
        
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(10, 109, 194, 0.35);
        }
        
        /* Ghost Button - Para "Ver" */
        div[data-testid="stButton"] > button[kind="secondary"] {
            background: transparent !important;
            color: var(--primary) !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
        }
        
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background: var(--primary-light) !important;
        }

        /* === CARDS === */
        .card-container, .medical-card {
            background: var(--bg-card);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        /* === BADGES === */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge-blue { background: var(--primary-light); color: var(--primary); }
        .badge-green { background: #ECFDF5; color: #059669; }

        /* === Mejora general del espaciado === */
        section[data-testid="stSidebar"] { display: none; }
        
        /* Hacer que los dividers sean más sutiles */
        hr {
            border: none;
            height: 1px;
            background: var(--border);
            margin: 1.25rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# COMPONENTES
# ==============================================================================

def render_hero_header_with_logout(physician_email, on_logout):
    """Header Hero con logout INTEGRADO dentro de la barra azul."""
    # Limpiar nombre: quitar punto, capitalizar
    if physician_email:
        name_part = physician_email.split('@')[0]
        name_clean = _esc(name_part.replace('.', ' ').replace('_', ' ').title())
    else:
        name_clean = "Doctor"

    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #0A6DC2 0%, #0891B2 100%);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 30px rgba(10, 109, 194, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div>
                <p style="margin: 0; font-size: 0.85rem; opacity: 0.9; font-weight: 500;">👋 Bienvenido de nuevo</p>
                <h2 style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 800; color: white;">Dr. {name_clean}</h2>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; opacity: 0.85;">Panel de Control | SaludIA</p>
            </div>
            <div id="logout-placeholder"></div>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón de logout usando Streamlit (se renderiza después del HTML)
    cols = st.columns([6, 1])
    with cols[1]:
        if st.button("🚪 Salir", key="logout_integrated", type="secondary"):
            on_logout()

def render_hero_header(physician_email):
    """Header simple sin logout."""
    if physician_email:
        name_part = physician_email.split('@')[0]
        name_clean = _esc(name_part.replace('.', ' ').replace('_', ' ').title())
    else:
        name_clean = "Doctor"

    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #0A6DC2 0%, #0891B2 100%);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 30px rgba(10, 109, 194, 0.2);
        ">
            <p style="margin: 0; font-size: 0.85rem; opacity: 0.9;">👋 Bienvenido de nuevo</p>
            <h2 style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 800; color: white;">Dr. {name_clean}</h2>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; opacity: 0.85;">Panel de Control | SaludIA</p>
        </div>
    """, unsafe_allow_html=True)

def card_metric(label, value, delta=None, color_hex="#0A6DC2"):
    """Tarjeta KPI."""
    delta_html = f"<div style='font-size:0.8rem; color:#059669; margin-top:6px;'>▲ {delta}</div>" if delta else ""
    st.markdown(f"""
        <div style="
            background: white;
            padding: 1.25rem;
            border-radius: 14px;
            border: 1px solid #E2E8F0;
            border-left: 4px solid {color_hex};
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        ">
            <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748B; font-weight: 600;">{label}</div>
            <div style="font-size: 1.75rem; font-weight: 800; color: #1E293B; margin-top: 4px;">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

def render_patient_card_item(patient, on_click):
    """Tarjeta de paciente LIMPIA - sin markdown visible."""
    # Limpiar nombre de asteriscos y markdown, luego escapar antes de HTML
    nombre = str(patient.get('nombre', 'Sin nombre'))
    nombre_limpio = _esc(nombre.replace('**', '').replace('*', '').strip())

    edad = _esc(patient.get('edad', '?'))
    cedula = _esc(patient.get('cedula', 'N/A'))
    
    with st.container():
        col1, col2, col3 = st.columns([3.5, 1.2, 0.8])
        with col1:
            st.markdown(f"""
                <div style="padding: 8px 0;">
                    <div style="font-weight: 700; font-size: 0.95rem; color: #1E293B;">{nombre_limpio}</div>
                    <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 2px;">ID: {cedula}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div style="display: flex; align-items: center; height: 100%; padding: 8px 0;">
                    <span style="background: #E8F4FC; color: #0A6DC2; padding: 4px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;">{edad} años</span>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            if st.button("→", key=f"p_{patient['id']}", type="secondary", help="Ver historial"):
                on_click(patient['id'])
        
        st.markdown("<hr style='margin: 4px 0; border: 0; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)

def render_consultation_timeline_item(consultation, on_ai_click):
    """Timeline item limpio.

    Los badges de presión arterial usan clinical_engine (fuente única de
    verdad de umbrales clínicos) en vez de umbrales hardcodeados aquí, y
    si la consulta ya trae un veredicto del motor de reglas
    (riesgo_nivel), se muestra como badge principal.
    """
    ts = consultation.get('timestamp')
    try:
        if ts is None or str(ts) == 'NaT':
            date_str = "Sin fecha"
        elif hasattr(ts, 'strftime'):
            date_str = ts.strftime('%d %b %Y • %H:%M')
        else:
            date_str = str(ts)[:16]
    except Exception:
        date_str = "Fecha desconocida"

    # Badge de riesgo global (si esta consulta ya fue evaluada por el motor local)
    badges = ""
    riesgo_nivel = consultation.get('riesgo_nivel')
    if riesgo_nivel and riesgo_nivel != 'N/A':
        colors = _RISK_COLORS.get(riesgo_nivel, {"bg": "#F1F5F9", "fg": "#64748B"})
        badges += (
            f"<span style='background:{colors['bg']}; color:{colors['fg']}; padding:3px 10px; "
            f"border-radius:999px; font-size:0.7rem; font-weight:600; margin-left:6px;'>"
            f"⚕️ Riesgo {_esc(riesgo_nivel)}</span>"
        )
    else:
        # Registros legados sin veredicto guardado: mostrar al menos la
        # clasificación de presión arterial, vía clinical_engine (no
        # umbrales duplicados aquí).
        pa_clas = ce.clasificar_presion_arterial(
            consultation.get('presion_sistolica'), consultation.get('presion_diastolica')
        )
        if pa_clas.nivel >= 2:
            colors = _RISK_COLORS.get(
                "ALTO" if pa_clas.nivel >= 3 else "MODERADO", {"bg": "#F1F5F9", "fg": "#64748B"}
            )
            badges += (
                f"<span style='background:{colors['bg']}; color:{colors['fg']}; padding:3px 10px; "
                f"border-radius:999px; font-size:0.7rem; font-weight:600;'>⚠️ {_esc(pa_clas.categoria)}</span>"
            )

    # Limpiar motivo de asteriscos y escapar antes de insertar en HTML
    motivo_raw = str(consultation.get('motivo_consulta', 'Sin motivo'))
    motivo_corto = motivo_raw.replace('**', '').replace('*', '')[:80]
    if len(motivo_raw) > 80:
        motivo_corto += "..."
    motivo = _esc(motivo_corto)

    pa_s = _esc(consultation.get('presion_sistolica', 'N/A'))
    pa_d = _esc(consultation.get('presion_diastolica', 'N/A'))
    fc = _esc(consultation.get('frec_cardiaca', 'N/A'))
    glu = _esc(consultation.get('glucemia', 'N/A'))
    imc = _esc(consultation.get('imc', 'N/A'))

    # Síntomas capturados en la Revisión por Sistemas (antes se guardaban
    # pero nunca se volvían a mostrar).
    sintomas_html = ""
    todos_sintomas = []
    for campo in ("sintomas_cardio", "sintomas_resp", "sintomas_gi", "sintomas_neuro"):
        valores = consultation.get(campo)
        if isinstance(valores, (list, tuple)):
            todos_sintomas.extend(valores)
    if todos_sintomas:
        chips = "".join(
            f"<span style='background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:999px; "
            f"font-size:0.7rem; margin:2px 4px 0 0; display:inline-block;'>{_esc(s)}</span>"
            for s in todos_sintomas
        )
        sintomas_html = f"<div style='margin-top:8px;'>{chips}</div>"

    st.markdown(f"""
    <div style="display: flex; gap: 15px; margin-bottom: 1.25rem;">
        <div style="width: 12px; display: flex; flex-direction: column; align-items: center;">
            <div style="width:12px; height:12px; background:#0A6DC2; border:3px solid white; border-radius:50%; box-shadow:0 0 0 3px #E8F4FC;"></div>
            <div style="width:2px; flex:1; background:linear-gradient(180deg, #0A6DC2, #E8F4FC);"></div>
        </div>
        <div style="flex:1;">
            <div style="font-size:0.8rem; color:#64748B; font-weight:600; margin-bottom:6px; font-family: monospace;">{date_str}</div>
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:10px;">
                    <div style="font-weight:600; color:#1E293B; font-size:0.95rem;">{motivo}</div>
                    <div>{badges}</div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: #F8FAFC; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.85rem;">
                    <div><span style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">PA</span><br><b style="color:#1E293B;">{pa_s}/{pa_d}</b></div>
                    <div><span style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">FC</span><br><b style="color:#1E293B;">{fc}</b></div>
                    <div><span style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">GLU</span><br><b style="color:#1E293B;">{glu}</b></div>
                    <div><span style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">IMC</span><br><b style="color:#1E293B;">{imc}</b></div>
                </div>
                {sintomas_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    ai = consultation.get('ai_analysis')
    if ai and ai != "N/A":
        with st.expander("🤖 Ver Análisis de IA"):
            st.markdown(ai)
    else:
        c1, _ = st.columns([1, 4])
        if c1.button("⚡ Analizar", key=f"ai_{consultation.get('id', 'x')}", type="secondary"):
            on_ai_click(consultation['id'])


def render_risk_card(resultado):
    """Muestra el veredicto del motor de reglas clínicas local
    (clinical_engine.ResultadoRiesgo) de inmediato tras guardar una
    consulta, sin depender de que Gemini esté disponible.
    """
    colors = _RISK_COLORS.get(resultado.nivel_riesgo, {"bg": "#F1F5F9", "fg": "#64748B"})
    icono = {"BAJO": "✅", "MODERADO": "⚠️", "ALTO": "🚨", "CRITICO": "🆘"}.get(resultado.nivel_riesgo, "ℹ️")

    st.markdown(f"""
        <div style="
            background: {colors['bg']};
            border: 1px solid {colors['fg']}33;
            border-left: 5px solid {colors['fg']};
            border-radius: 14px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:800; font-size:1.1rem; color:{colors['fg']};">{icono} Riesgo {_esc(resultado.nivel_riesgo)}</span>
                <span style="font-size:0.8rem; color:{colors['fg']}; font-weight:600;">Score {resultado.score}/100 · Motor local</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Nota: de aquí en adelante se usa st.markdown SIN unsafe_allow_html, y
    # todo el texto proviene de clinical_engine (cadenas fijas, no datos de
    # usuario), así que no requiere escape HTML.
    anormales = [c for c in resultado.clasificaciones if c.es_anormal()]
    if anormales:
        st.markdown("**Hallazgos:**")
        for c in anormales:
            st.markdown(f"- **{c.parametro.replace('_', ' ').title()}**: {c.categoria} — {c.detalle} _( {c.fuente} )_")

    if resultado.alertas_rojas:
        st.markdown("**🚩 Alertas rojas:**")
        for a in resultado.alertas_rojas:
            st.warning(a)

    if resultado.tendencias:
        st.markdown("**📈 Tendencias en el historial:**")
        for t in resultado.tendencias:
            st.markdown(f"- {t['columna']}: **{t['tendencia']}** (últimos valores: {t['ultimos_valores']})")

    if resultado.recomendaciones:
        st.markdown("**Recomendaciones:**")
        for r in resultado.recomendaciones:
            st.markdown(f"- {r}")

    st.caption(
        "⚕️ Evaluación generada por un motor de reglas determinista basado en guías clínicas "
        "publicadas (ACC/AHA, ADA, OMS, NEWS2). Es una herramienta de apoyo a la decisión y "
        "tamizaje; no reemplaza el juicio clínico profesional."
    )

def render_about_section():
    """Sección Acerca de - Interactiva."""
    st.markdown("""
        <div style="text-align:center; padding:1.5rem 0;">
            <h2 style="color:#0A6DC2; margin-bottom:0.5rem;">🩺 SaludIA</h2>
            <p style="color:#64748B; font-size:1rem;">Sistema de Soporte a la Decisión Clínica</p>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    features = [
        ("🧠", "IA Gemini", "Análisis clínico"),
        ("📊", "Visualización", "Tendencias vitales"),
        ("📄", "PDF", "Reportes y recetas"),
        ("🔒", "Seguro", "Datos en Firebase"),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], features):
        with col:
            st.markdown(f"""
                <div style="text-align:center; background:white; padding:1rem; border-radius:12px; border:1px solid #E2E8F0;">
                    <div style="font-size:1.75rem;">{icon}</div>
                    <div style="font-weight:700; color:#1E293B; margin-top:0.5rem;">{title}</div>
                    <div style="font-size:0.8rem; color:#64748B;">{desc}</div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align:center; color:#94A3B8; font-size:0.85rem;">
            <p>Desarrollado por <b>Joseph Javier Sánchez Acuña</b> | CEO de SAVA</p>
            <p>Universidad de los Andes | 2024</p>
        </div>
    """, unsafe_allow_html=True)
