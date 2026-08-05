# -*- coding: utf-8 -*-
"""
clinical_engine.py
Motor de reglas clinicas local para SaludIA.

OBJETIVO
--------
Sustituir la dependencia PRIMARIA en la API de Gemini para la tarea de
clasificar el riesgo clinico de un paciente. Este motor es:

  - Determinista:   mismas entradas -> misma salida, siempre.
  - Instantaneo:    no requiere red, ni cuota de API, ni conexion.
  - Explicable:     cada conclusion cita la regla/guia clinica que la origina.
  - Verificable:    cubierto por pruebas unitarias (test_clinical_engine.py).
  - Gratuito:       cero costo marginal por evaluacion.

Con este modulo, Gemini deja de ser el "motor de decision" y pasa a ser,
opcionalmente, una capa de REDACCION en lenguaje natural que explica al
medico un veredicto que YA fue calculado aqui. Si Gemini falla, esta
totalmente saturado o no hay API key configurada, el sistema sigue
entregando una evaluacion de riesgo completa y correcta.

FUENTES CLINICAS
-----------------
- Presion arterial:
  Whelton PK, et al. "2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA
  Guideline for the Prevention, Detection, Evaluation, and Management of
  High Blood Pressure in Adults." Hypertension. 2018;71(6):e13-e115.
- Glucemia (diagnostico de diabetes/prediabetes):
  American Diabetes Association. "Standards of Care in Diabetes-2025."
  Diabetes Care 2025;48(Suppl.1):S27-S49. Seccion 2 (criterios de
  diagnostico) y Seccion 6 (definiciones de hipoglucemia).
- Indice de Masa Corporal:
  World Health Organization. BMI classification for adults.
- Alerta temprana (parcial):
  Royal College of Physicians (UK). "National Early Warning Score (NEWS) 2:
  Standardising the assessment of acute-illness severity in the NHS." 2017.
  NOTA: aqui solo se implementa un SUB-CONJUNTO de NEWS2 (presion sistolica
  y frecuencia cardiaca) porque la app aun no captura frecuencia
  respiratoria, saturacion de oxigeno, temperatura ni nivel de conciencia.
  Ver seccion "Fase 2" de la propuesta para el plan de ampliacion.

ADVERTENCIA
-----------
Este motor es una herramienta de apoyo a la decision clinica (CDSS) y de
tamizaje. NO reemplaza el juicio clinico profesional ni constituye un
diagnostico definitivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

try:
    import pandas as pd
except ImportError:  # pragma: no cover - pandas es una dependencia del proyecto
    pd = None


# ==========================================================================
# UTILIDADES INTERNAS
# ==========================================================================

def _to_float(valor) -> Optional[float]:
    """Convierte de forma segura a float. Devuelve None si no es posible
    o si el valor esta vacio / es un marcador de dato faltante."""
    if valor is None:
        return None
    if isinstance(valor, str) and valor.strip().upper() in ("", "N/A", "NA", "NONE"):
        return None
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    if pd is not None:
        try:
            if pd.isna(f):
                return None
        except (TypeError, ValueError):
            pass
    return f


# ==========================================================================
# 1. CLASIFICACIONES INDIVIDUALES POR SIGNO VITAL
# ==========================================================================

@dataclass
class Clasificacion:
    """Resultado de clasificar un unico parametro clinico."""
    parametro: str
    valor: Optional[float]
    categoria: str
    nivel: int              # 0=normal, 1=leve, 2=moderado, 3=alto, 4=critico
    detalle: str
    fuente: str

    def es_anormal(self) -> bool:
        return self.nivel > 0


def clasificar_presion_arterial(sistolica, diastolica) -> Clasificacion:
    """Clasifica la presion arterial segun ACC/AHA 2017.

    Cuando sistolica y diastolica caen en categorias distintas, se usa
    la categoria MAS ALTA de las dos (regla explicita de la guia).
    """
    s = _to_float(sistolica)
    d = _to_float(diastolica)
    fuente = "ACC/AHA 2017 Guideline for High Blood Pressure in Adults"

    if s is None or d is None:
        return Clasificacion("presion_arterial", None, "Sin datos", 0,
                              "No hay valores suficientes de presion arterial.", fuente)

    if s >= 180 or d >= 120:
        return Clasificacion("presion_arterial", s, "Crisis Hipertensiva", 4,
                              f"PA {s:.0f}/{d:.0f} mmHg. Requiere atencion inmediata: "
                              "descartar emergencia hipertensiva (dano de organo blanco).",
                              fuente)
    if s < 90 or d < 60:
        return Clasificacion("presion_arterial", s, "Hipotension", 2,
                              f"PA {s:.0f}/{d:.0f} mmHg, por debajo del rango habitual.",
                              fuente)
    if s >= 140 or d >= 90:
        return Clasificacion("presion_arterial", s, "Hipertension Etapa 2", 3,
                              f"PA {s:.0f}/{d:.0f} mmHg.", fuente)
    if s >= 130 or d >= 80:
        return Clasificacion("presion_arterial", s, "Hipertension Etapa 1", 2,
                              f"PA {s:.0f}/{d:.0f} mmHg.", fuente)
    if s >= 120:
        return Clasificacion("presion_arterial", s, "Presion Elevada", 1,
                              f"PA {s:.0f}/{d:.0f} mmHg.", fuente)
    return Clasificacion("presion_arterial", s, "Normal", 0,
                          f"PA {s:.0f}/{d:.0f} mmHg dentro de rango normal.", fuente)


def clasificar_glucemia(glucemia, contexto: str = "no_especificado") -> Clasificacion:
    """Clasifica la glucemia segun criterios ADA 2025.

    contexto: "ayunas" | "aleatoria" | "no_especificado"
    Si el contexto no se especifica, se aplican los umbrales de glucemia
    en ayunas (mas conservadores) y se anota la limitacion en el detalle.
    """
    g = _to_float(glucemia)
    fuente = "American Diabetes Association, Standards of Care in Diabetes-2025 (Sec. 2 y 6)"

    if g is None:
        return Clasificacion("glucemia", None, "Sin datos", 0,
                              "No hay valor de glucemia.", fuente)

    # Hipoglucemia (aplica sin importar el contexto)
    if g < 54:
        return Clasificacion("glucemia", g, "Hipoglucemia Severa (Nivel 2 ADA)", 4,
                              f"Glucemia {g:.0f} mg/dL. Requiere manejo inmediato.", fuente)
    if g < 70:
        return Clasificacion("glucemia", g, "Hipoglucemia (valor de alerta)", 2,
                              f"Glucemia {g:.0f} mg/dL, por debajo de 70 mg/dL.", fuente)

    nota_contexto = ""
    if contexto not in ("ayunas", "aleatoria"):
        nota_contexto = (" (contexto de toma no especificado: se asumen criterios de "
                          "glucemia en ayunas; se recomienda registrar si el paciente "
                          "estaba en ayuno para mayor precision)")
        contexto = "ayunas"

    if contexto == "ayunas":
        if g >= 126:
            categoria, nivel = "Hiperglucemia compatible con Diabetes", 3
        elif g >= 100:
            categoria, nivel = "Glucemia Alterada en Ayunas (Prediabetes)", 2
        else:
            categoria, nivel = "Normal", 0
    else:  # aleatoria
        if g >= 200:
            categoria, nivel = "Hiperglucemia compatible con Diabetes", 3
        elif g >= 140:
            categoria, nivel = "Hiperglucemia - sugiere tamizaje adicional", 1
        else:
            categoria, nivel = "Normal", 0

    return Clasificacion("glucemia", g, categoria, nivel,
                          f"Glucemia {g:.0f} mg/dL ({contexto}){nota_contexto}.", fuente)


def clasificar_imc(imc) -> Clasificacion:
    """Clasifica el Indice de Masa Corporal segun la OMS."""
    v = _to_float(imc)
    fuente = "World Health Organization, BMI classification"

    if v is None or v <= 0:
        return Clasificacion("imc", None, "Sin datos", 0, "No hay IMC valido.", fuente)

    if v < 18.5:
        categoria, nivel = "Bajo Peso", 1
    elif v < 25:
        categoria, nivel = "Normal", 0
    elif v < 30:
        categoria, nivel = "Sobrepeso", 1
    elif v < 35:
        categoria, nivel = "Obesidad Grado I", 2
    elif v < 40:
        categoria, nivel = "Obesidad Grado II", 3
    else:
        categoria, nivel = "Obesidad Grado III (Morbida)", 4

    return Clasificacion("imc", v, categoria, nivel, f"IMC {v:.1f} kg/m2.", fuente)


def clasificar_frecuencia_cardiaca(fc) -> Clasificacion:
    """Clasifica la frecuencia cardiaca usando las mismas bandas que NEWS2."""
    v = _to_float(fc)
    fuente = "Bandas de frecuencia cardiaca de NEWS2 (RCP UK, 2017)"

    if v is None or v <= 0:
        return Clasificacion("frecuencia_cardiaca", None, "Sin datos", 0,
                              "No hay FC valida.", fuente)

    if v <= 40:
        categoria, nivel = "Bradicardia Severa", 3
    elif v <= 50:
        categoria, nivel = "Bradicardia", 2
    elif v <= 90:
        categoria, nivel = "Normal", 0
    elif v <= 110:
        categoria, nivel = "Taquicardia Leve", 1
    elif v <= 130:
        categoria, nivel = "Taquicardia", 2
    else:
        categoria, nivel = "Taquicardia Severa", 3

    return Clasificacion("frecuencia_cardiaca", v, categoria, nivel,
                          f"FC {v:.0f} lpm.", fuente)


# ==========================================================================
# 2. NEWS2 PARCIAL
# ==========================================================================

def news2_parcial(sistolica, fc) -> Dict[str, Any]:
    """Sub-score de NEWS2 usando UNICAMENTE presion sistolica y frecuencia
    cardiaca (las 2 de las 6 variables de NEWS2 que la app captura hoy).

    Puntaje maximo posible de este sub-score: 6 (el NEWS2 completo llega a 20
    porque tambien incluye frecuencia respiratoria, SpO2, temperatura y
    nivel de conciencia). Por eso se llama "parcial" y NO debe interpretarse
    como un NEWS2 completo ni usarse para decisiones de triage hospitalario.
    """
    s = _to_float(sistolica)
    v = _to_float(fc)

    sbp_score = 0
    if s is not None:
        if s <= 90 or s >= 220:
            sbp_score = 3
        elif s <= 100:
            sbp_score = 2
        elif s <= 110:
            sbp_score = 1
        else:
            sbp_score = 0

    hr_score = 0
    if v is not None:
        if v <= 40 or v >= 131:
            hr_score = 3
        elif v <= 50 or (111 <= v <= 130):
            hr_score = 2
        elif 91 <= v <= 110:
            hr_score = 1
        else:
            hr_score = 0

    total = sbp_score + hr_score
    return {
        "sbp_score": sbp_score,
        "hr_score": hr_score,
        "total_parcial": total,
        "maximo_parcial": 6,
        "completo": False,
        "variables_faltantes": ["frecuencia_respiratoria", "spo2", "temperatura", "conciencia"],
        "fuente": "NEWS2 (Royal College of Physicians, 2017) - subconjunto parcial",
    }


# ==========================================================================
# 3. ALERTAS ROJAS (reglas sintoma + signo)
# ==========================================================================

def detectar_alertas_rojas(sintomas: Dict[str, List[str]],
                            sistolica=None, diastolica=None,
                            fc=None, glucemia=None) -> List[str]:
    """Aplica reglas heuristicas combinando la revision por sistemas
    (checklist de sintomas) con los signos vitales para detectar posibles
    urgencias. Cada regla es explicita e independiente; todas requieren
    confirmacion clinica y no son diagnosticos.
    """
    sintomas = sintomas or {}
    cardio = set(sintomas.get("cardio", []) or [])
    resp = set(sintomas.get("resp", []) or [])
    gi = set(sintomas.get("gi", []) or [])
    neuro = set(sintomas.get("neuro", []) or [])

    pa = clasificar_presion_arterial(sistolica, diastolica)
    fc_clas = clasificar_frecuencia_cardiaca(fc)
    glu_clas = clasificar_glucemia(glucemia)

    alertas: List[str] = []

    if "Dolor Torácico" in cardio and (pa.nivel >= 3 or fc_clas.nivel >= 2 or "Disnea" in resp):
        alertas.append(
            "Dolor toracico con signos de alarma (PA muy elevada, FC anormal o disnea "
            "asociada): descartar sindrome coronario agudo de forma urgente."
        )

    if "Disnea" in resp and fc_clas.nivel >= 2:
        alertas.append(
            "Disnea con frecuencia cardiaca anormal: evaluar causa cardiopulmonar aguda "
            "(insuficiencia cardiaca, tromboembolismo, arritmia)."
        )

    if pa.categoria == "Crisis Hipertensiva" and (neuro & {"Cefalea", "Mareo", "Debilidad"}):
        alertas.append(
            "Crisis hipertensiva con sintomas neurologicos: riesgo de urgencia/emergencia "
            "hipertensiva; descartar dano agudo de organo blanco (SNC, retina, rinon)."
        )

    if "Debilidad" in neuro and (cardio or "Cefalea" in neuro or "Mareo" in neuro):
        alertas.append(
            "Debilidad asociada a otros sintomas: si el inicio fue subito, activar "
            "protocolo de evento cerebrovascular agudo (ACV)."
        )

    if glu_clas.nivel >= 3 and (gi & {"Náuseas", "Dolor Abdominal"}):
        alertas.append(
            "Hiperglucemia marcada con sintomas gastrointestinales: descartar "
            "cetoacidosis diabetica o estado hiperosmolar, especialmente si hay "
            "taquicardia asociada."
        )

    if glu_clas.categoria.startswith("Hipoglucemia Severa"):
        alertas.append("Hipoglucemia severa: manejo inmediato (glucosa/glucagon) y reevaluacion.")

    return alertas


# ==========================================================================
# 4. ANALISIS DE TENDENCIA HISTORICA (reemplaza "razonamiento" ad-hoc de la IA)
# ==========================================================================

def analizar_tendencia(history_df, columna: str, n: int = 3,
                        umbral_alto: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Analiza los ultimos `n` valores numericos de `columna` en el
    historial del paciente para detectar tendencias sostenidas.
    Devuelve None si no hay suficientes datos.
    """
    if pd is None or history_df is None or getattr(history_df, "empty", True):
        return None
    if columna not in history_df.columns or "timestamp" not in history_df.columns:
        return None

    df_ordenado = history_df.sort_values("timestamp")
    serie = pd.to_numeric(df_ordenado[columna], errors="coerce").dropna()
    if len(serie) < n:
        return None

    ultimos = serie.tail(n).tolist()
    ascendente = all(ultimos[i] <= ultimos[i + 1] for i in range(len(ultimos) - 1)) and ultimos[-1] > ultimos[0]
    descendente = all(ultimos[i] >= ultimos[i + 1] for i in range(len(ultimos) - 1)) and ultimos[-1] < ultimos[0]
    sostenido_alto = umbral_alto is not None and all(x >= umbral_alto for x in ultimos)

    if ascendente:
        tendencia = "ascendente"
    elif descendente:
        tendencia = "descendente"
    else:
        tendencia = "estable"

    return {
        "columna": columna,
        "ultimos_valores": ultimos,
        "tendencia": tendencia,
        "sostenido_alto": sostenido_alto,
    }


def resumen_historial_para_ia(history_df, n: int = 5) -> str:
    """Construye un resumen textual compacto y real del historial clinico
    del paciente, para usarse como contexto de la IA generativa.

    Corrige un defecto del sistema original: el analisis de IA se
    invocaba con el texto literal "Analisis" en lugar del historial real
    del paciente, por lo que el modelo nunca tenia contexto longitudinal.
    """
    if pd is None or history_df is None or getattr(history_df, "empty", True):
        return "Sin historial previo registrado (primera consulta)."

    columnas = ["timestamp", "presion_sistolica", "presion_diastolica", "frec_cardiaca", "glucemia", "imc"]
    disponibles = [c for c in columnas if c in history_df.columns]
    df_ordenado = history_df.sort_values("timestamp", ascending=False).head(n)

    lineas = []
    for _, fila in df_ordenado.iterrows():
        ts = fila.get("timestamp")
        fecha = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        partes = [fecha]
        if "presion_sistolica" in disponibles and "presion_diastolica" in disponibles:
            partes.append(f"PA {fila.get('presion_sistolica', '?')}/{fila.get('presion_diastolica', '?')}")
        if "frec_cardiaca" in disponibles:
            partes.append(f"FC {fila.get('frec_cardiaca', '?')}")
        if "glucemia" in disponibles:
            partes.append(f"Glu {fila.get('glucemia', '?')}")
        if "imc" in disponibles:
            partes.append(f"IMC {fila.get('imc', '?')}")
        lineas.append(" | ".join(partes))

    return f"Ultimas {len(lineas)} consulta(s) registradas:\n" + "\n".join(lineas)


# ==========================================================================
# 5. EVALUACION COMPUESTA (punto de entrada principal del motor)
# ==========================================================================

_PESOS = {"presion_arterial": 8, "glucemia": 8, "imc": 3, "frecuencia_cardiaca": 5}
_PUNTOS_POR_ALERTA_ROJA = 15
_PUNTOS_POR_TENDENCIA_ADVERSA = 10
_MAX_SCORE = 100


@dataclass
class ResultadoRiesgo:
    nivel_riesgo: str                       # BAJO | MODERADO | ALTO | CRITICO
    score: int                              # 0-100
    clasificaciones: List[Clasificacion] = field(default_factory=list)
    alertas_rojas: List[str] = field(default_factory=list)
    tendencias: List[Dict[str, Any]] = field(default_factory=list)
    recomendaciones: List[str] = field(default_factory=list)
    news2_parcial: Optional[Dict[str, Any]] = None

    def resumen_texto(self) -> str:
        lineas = [f"NIVEL DE RIESGO (motor local, determinista): {self.nivel_riesgo} (score {self.score}/100)"]
        anormales = [c for c in self.clasificaciones if c.es_anormal()]
        if anormales:
            lineas.append("Hallazgos:")
            for c in anormales:
                lineas.append(f"  - {c.parametro}: {c.categoria} ({c.detalle}) [{c.fuente}]")
        if self.alertas_rojas:
            lineas.append("Alertas rojas:")
            for a in self.alertas_rojas:
                lineas.append(f"  - {a}")
        if self.tendencias:
            lineas.append("Tendencias en el historial:")
            for t in self.tendencias:
                lineas.append(f"  - {t['columna']}: {t['tendencia']} (ultimos valores: {t['ultimos_valores']})")
        if self.recomendaciones:
            lineas.append("Recomendaciones sugeridas:")
            for r in self.recomendaciones:
                lineas.append(f"  - {r}")
        return "\n".join(lineas)


def _recomendaciones_por_clasificacion(clasificaciones: List[Clasificacion]) -> List[str]:
    recs = []
    for c in clasificaciones:
        if c.parametro == "presion_arterial" and c.nivel >= 3:
            recs.append("Repetir toma de PA en reposo; si se confirma, considerar ajuste "
                        "terapeutico y/o monitoreo ambulatorio (MAPA).")
        if c.parametro == "presion_arterial" and c.categoria == "Crisis Hipertensiva":
            recs.append("Evaluacion medica inmediata / remitir a urgencias.")
        if c.parametro == "glucemia" and "Diabetes" in c.categoria:
            recs.append("Confirmar con HbA1c o nueva glucemia en ayunas en dias distintos "
                        "antes de establecer diagnostico definitivo (criterio ADA).")
        if c.parametro == "glucemia" and "Prediabetes" in c.categoria:
            recs.append("Reforzar cambios de estilo de vida y repetir tamizaje en 3-6 meses.")
        if c.parametro == "imc" and c.nivel >= 2:
            recs.append("Remitir a valoracion nutricional; evaluar comorbilidades metabolicas asociadas.")
    return recs


def evaluar_riesgo_clinico(consulta: Dict[str, Any],
                            sintomas: Optional[Dict[str, List[str]]] = None,
                            history_df=None) -> ResultadoRiesgo:
    """Punto de entrada principal del motor. Recibe los datos de la
    consulta actual (signos vitales), el checklist de sintomas y,
    opcionalmente, el historial del paciente (DataFrame de pandas) para
    detectar tendencias. Devuelve un ResultadoRiesgo completo y explicable.
    """
    sistolica = consulta.get("presion_sistolica")
    diastolica = consulta.get("presion_diastolica")
    fc = consulta.get("frec_cardiaca")
    glucemia = consulta.get("glucemia")
    imc = consulta.get("imc")
    contexto_glucemia = consulta.get("contexto_glucemia", "no_especificado")

    clasificaciones = [
        clasificar_presion_arterial(sistolica, diastolica),
        clasificar_glucemia(glucemia, contexto_glucemia),
        clasificar_imc(imc),
        clasificar_frecuencia_cardiaca(fc),
    ]

    alertas_rojas = detectar_alertas_rojas(sintomas or {}, sistolica, diastolica, fc, glucemia)

    tendencias = []
    for columna, umbral in (("presion_sistolica", 130), ("glucemia", 126)):
        t = analizar_tendencia(history_df, columna, n=3, umbral_alto=umbral)
        if t and (t["tendencia"] != "estable" or t["sostenido_alto"]):
            tendencias.append(t)

    news2 = news2_parcial(sistolica, fc)

    score = 0
    for c in clasificaciones:
        score += c.nivel * _PESOS.get(c.parametro, 0)
    score += news2["total_parcial"] * 3
    score += min(len(alertas_rojas), 3) * _PUNTOS_POR_ALERTA_ROJA
    score += min(len(tendencias), 2) * _PUNTOS_POR_TENDENCIA_ADVERSA
    score = max(0, min(_MAX_SCORE, score))

    if score >= 70:
        nivel = "CRITICO"
    elif score >= 40:
        nivel = "ALTO"
    elif score >= 15:
        nivel = "MODERADO"
    else:
        nivel = "BAJO"

    # Escalamiento de seguridad ("fail-safe"): ciertos hallazgos aislados
    # deben forzar nivel CRITICO aunque el puntaje ponderado no lo alcance,
    # para nunca minimizar un hallazgo peligroso por promediarlo con datos
    # normales.
    if any(c.nivel == 4 for c in clasificaciones):
        nivel = "CRITICO"
    elif alertas_rojas and nivel not in ("CRITICO",):
        nivel = "ALTO" if nivel in ("BAJO", "MODERADO") else nivel

    recomendaciones = _recomendaciones_por_clasificacion(clasificaciones)
    if not recomendaciones and nivel == "BAJO":
        recomendaciones.append("Sin hallazgos que requieran accion inmediata; continuar seguimiento habitual.")

    return ResultadoRiesgo(
        nivel_riesgo=nivel,
        score=score,
        clasificaciones=clasificaciones,
        alertas_rojas=alertas_rojas,
        tendencias=tendencias,
        recomendaciones=recomendaciones,
        news2_parcial=news2,
    )
