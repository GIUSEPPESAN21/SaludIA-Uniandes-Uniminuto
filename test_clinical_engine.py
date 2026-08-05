# -*- coding: utf-8 -*-
"""
Pruebas unitarias del motor de reglas clinicas (clinical_engine.py).

Verifican, con valores limite exactos, que las clasificaciones respeten
las guias clinicas citadas en el modulo (ACC/AHA 2017, ADA 2025, OMS,
NEWS2). Esto es lo que permite decir que el algoritmo es "verificable":
cualquier cambio futuro en los umbrales rompera estas pruebas si se
desvia de la evidencia clinica.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import pytest

import clinical_engine as ce


# --------------------------------------------------------------------
# Presion arterial (ACC/AHA 2017)
# --------------------------------------------------------------------

@pytest.mark.parametrize("s,d,esperado", [
    (110, 70, "Normal"),
    (119, 79, "Normal"),
    (120, 75, "Presion Elevada"),
    (129, 79, "Presion Elevada"),
    (130, 79, "Hipertension Etapa 1"),
    (125, 85, "Hipertension Etapa 1"),
    (140, 85, "Hipertension Etapa 2"),
    (135, 95, "Hipertension Etapa 2"),
    (185, 100, "Crisis Hipertensiva"),
    (150, 125, "Crisis Hipertensiva"),
    (85, 55, "Hipotension"),
])
def test_clasificar_presion_arterial(s, d, esperado):
    resultado = ce.clasificar_presion_arterial(s, d)
    assert resultado.categoria == esperado


def test_presion_arterial_sin_datos():
    resultado = ce.clasificar_presion_arterial(None, None)
    assert resultado.categoria == "Sin datos"
    assert resultado.nivel == 0


# --------------------------------------------------------------------
# Glucemia (ADA 2025)
# --------------------------------------------------------------------

@pytest.mark.parametrize("g,contexto,esperado", [
    (95, "ayunas", "Normal"),
    (99, "ayunas", "Normal"),
    (100, "ayunas", "Glucemia Alterada en Ayunas (Prediabetes)"),
    (125, "ayunas", "Glucemia Alterada en Ayunas (Prediabetes)"),
    (126, "ayunas", "Hiperglucemia compatible con Diabetes"),
    (199, "aleatoria", "Hiperglucemia - sugiere tamizaje adicional"),
    (200, "aleatoria", "Hiperglucemia compatible con Diabetes"),
    (53, "ayunas", "Hipoglucemia Severa (Nivel 2 ADA)"),
    (60, "ayunas", "Hipoglucemia (valor de alerta)"),
])
def test_clasificar_glucemia(g, contexto, esperado):
    resultado = ce.clasificar_glucemia(g, contexto)
    assert resultado.categoria == esperado


def test_glucemia_contexto_no_especificado_usa_ayunas():
    resultado = ce.clasificar_glucemia(130)
    assert resultado.categoria == "Hiperglucemia compatible con Diabetes"
    assert "no especificado" in resultado.detalle


# --------------------------------------------------------------------
# IMC (OMS)
# --------------------------------------------------------------------

@pytest.mark.parametrize("imc,esperado", [
    (17.0, "Bajo Peso"),
    (18.4, "Bajo Peso"),
    (18.5, "Normal"),
    (24.9, "Normal"),
    (25.0, "Sobrepeso"),
    (29.9, "Sobrepeso"),
    (30.0, "Obesidad Grado I"),
    (35.0, "Obesidad Grado II"),
    (40.0, "Obesidad Grado III (Morbida)"),
])
def test_clasificar_imc(imc, esperado):
    resultado = ce.clasificar_imc(imc)
    assert resultado.categoria == esperado


# --------------------------------------------------------------------
# Frecuencia cardiaca (bandas NEWS2)
# --------------------------------------------------------------------

@pytest.mark.parametrize("fc,esperado", [
    (35, "Bradicardia Severa"),
    (45, "Bradicardia"),
    (75, "Normal"),
    (100, "Taquicardia Leve"),
    (120, "Taquicardia"),
    (140, "Taquicardia Severa"),
])
def test_clasificar_fc(fc, esperado):
    resultado = ce.clasificar_frecuencia_cardiaca(fc)
    assert resultado.categoria == esperado


# --------------------------------------------------------------------
# NEWS2 parcial
# --------------------------------------------------------------------

def test_news2_parcial_normal():
    r = ce.news2_parcial(115, 75)
    assert r["total_parcial"] == 0
    assert r["completo"] is False


def test_news2_parcial_critico():
    r = ce.news2_parcial(85, 135)
    assert r["sbp_score"] == 3
    assert r["hr_score"] == 3
    assert r["total_parcial"] == 6


# --------------------------------------------------------------------
# Alertas rojas
# --------------------------------------------------------------------

def test_alerta_dolor_toracico_con_hta_severa():
    sintomas = {"cardio": ["Dolor Torácico"], "resp": [], "gi": [], "neuro": []}
    alertas = ce.detectar_alertas_rojas(sintomas, sistolica=150, diastolica=95, fc=110, glucemia=90)
    assert any("sindrome coronario agudo" in a for a in alertas)


def test_sin_alertas_en_paciente_sano():
    sintomas = {"cardio": [], "resp": [], "gi": [], "neuro": []}
    alertas = ce.detectar_alertas_rojas(sintomas, sistolica=115, diastolica=75, fc=70, glucemia=90)
    assert alertas == []


def test_alerta_crisis_hipertensiva_con_cefalea():
    sintomas = {"cardio": [], "resp": [], "gi": [], "neuro": ["Cefalea"]}
    alertas = ce.detectar_alertas_rojas(sintomas, sistolica=190, diastolica=125, fc=90, glucemia=90)
    assert any("emergencia hipertensiva" in a or "urgencia" in a for a in alertas)


def test_alerta_hipoglucemia_severa():
    sintomas = {"cardio": [], "resp": [], "gi": [], "neuro": []}
    alertas = ce.detectar_alertas_rojas(sintomas, sistolica=115, diastolica=75, fc=90, glucemia=45)
    assert any("Hipoglucemia severa" in a for a in alertas)


# --------------------------------------------------------------------
# Tendencias historicas
# --------------------------------------------------------------------

def _history_df(valores_sistolica):
    fechas = pd.date_range("2026-01-01", periods=len(valores_sistolica), freq="D")
    return pd.DataFrame({"timestamp": fechas, "presion_sistolica": valores_sistolica})


def test_tendencia_ascendente():
    df = _history_df([120, 130, 145])
    t = ce.analizar_tendencia(df, "presion_sistolica", n=3)
    assert t["tendencia"] == "ascendente"


def test_tendencia_estable():
    df = _history_df([120, 121, 120])
    t = ce.analizar_tendencia(df, "presion_sistolica", n=3)
    assert t["tendencia"] == "estable"


def test_tendencia_insuficientes_datos():
    df = _history_df([120])
    t = ce.analizar_tendencia(df, "presion_sistolica", n=3)
    assert t is None


def test_tendencia_sin_historial():
    assert ce.analizar_tendencia(None, "presion_sistolica") is None
    assert ce.analizar_tendencia(pd.DataFrame(), "presion_sistolica") is None


def test_resumen_historial_para_ia_sin_historial():
    resumen = ce.resumen_historial_para_ia(pd.DataFrame())
    assert "Sin historial previo" in resumen


def test_resumen_historial_para_ia_con_datos():
    df = _history_df([120, 130, 145])
    df["frec_cardiaca"] = [70, 75, 80]
    df["glucemia"] = [90, 95, 100]
    df["imc"] = [24, 24, 24]
    df["presion_diastolica"] = [80, 82, 85]
    resumen = ce.resumen_historial_para_ia(df, n=3)
    assert "Ultimas 3 consulta(s)" in resumen
    assert "PA 145/85" in resumen  # el registro mas reciente aparece primero


# --------------------------------------------------------------------
# Evaluacion compuesta (integracion)
# --------------------------------------------------------------------

def test_evaluar_riesgo_paciente_sano_es_bajo():
    consulta = {"presion_sistolica": 115, "presion_diastolica": 75,
                "frec_cardiaca": 70, "glucemia": 85, "imc": 22}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas={})
    assert resultado.nivel_riesgo == "BAJO"
    assert resultado.alertas_rojas == []


def test_evaluar_riesgo_crisis_hipertensiva_es_critico():
    consulta = {"presion_sistolica": 190, "presion_diastolica": 125,
                "frec_cardiaca": 95, "glucemia": 90, "imc": 24}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas={})
    assert resultado.nivel_riesgo == "CRITICO"


def test_evaluar_riesgo_con_alerta_roja_escala_al_menos_a_alto():
    consulta = {"presion_sistolica": 150, "presion_diastolica": 95,
                "frec_cardiaca": 110, "glucemia": 90, "imc": 24}
    sintomas = {"cardio": ["Dolor Torácico"], "resp": [], "gi": [], "neuro": []}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas=sintomas)
    assert resultado.nivel_riesgo in ("ALTO", "CRITICO")
    assert len(resultado.alertas_rojas) > 0


def test_evaluar_riesgo_con_tendencia_ascendente_de_pa():
    historial = _history_df([125, 132, 138])
    consulta = {"presion_sistolica": 138, "presion_diastolica": 88,
                "frec_cardiaca": 78, "glucemia": 90, "imc": 24}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas={}, history_df=historial)
    columnas_con_tendencia = [t["columna"] for t in resultado.tendencias]
    assert "presion_sistolica" in columnas_con_tendencia


def test_resumen_texto_incluye_nivel_y_fuentes():
    consulta = {"presion_sistolica": 145, "presion_diastolica": 92,
                "frec_cardiaca": 88, "glucemia": 90, "imc": 24}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas={})
    texto = resultado.resumen_texto()
    assert "NIVEL DE RIESGO" in texto
    assert "ACC/AHA" in texto


def test_valores_faltantes_no_rompen_el_motor():
    consulta = {"presion_sistolica": None, "presion_diastolica": None,
                "frec_cardiaca": "", "glucemia": "N/A", "imc": 0}
    resultado = ce.evaluar_riesgo_clinico(consulta, sintomas=None, history_df=None)
    assert resultado.nivel_riesgo == "BAJO"
    assert resultado.score == 0
