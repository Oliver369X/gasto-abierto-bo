"""F4 golden bank — ≥50 phrases for fire classifier coverage."""
from __future__ import annotations

from decimal import Decimal

import pytest

from common.fire.classify import classify_fire_text, is_fire_related

# (text, expected_attribution, must_fire_related)
GOLDEN: list[tuple[str, str, bool]] = [
    # directo
    ("Alquiler de aeronave para la lucha de incendios forestales", "directo", True),
    ("Alquiler de helicóptero para sofocación de incendios", "directo", True),
    ("Combate de incendios forestales en Santa Cruz", "directo", True),
    ("Movilización de bomberos forestales", "directo", True),
    ("Brigadas forestales para liquidación de incendios", "directo", True),
    ("Adquisición de Bambi Bucket para avión cisterna", "directo", True),
    ("Sistema Guardian — contenedores aéreos contraincendios", "directo", True),
    ("Cajas Guardian para descarga de agua", "directo", True),
    ("Monitoreo de focos de calor DGF-SIMB", "directo", True),
    ("Emergencia ígnea nacional 2024", "directo", True),
    ("Desastre forestal Beni — operaciones aéreas de combate", "directo", True),
    ("Construcción de cortafuegos y línea de defensa", "directo", True),
    ("Mochilas forestales aspersoras para brigadistas", "directo", True),
    ("Quemas controladas preventivas", "directo", True),
    ("Lucha contra el incendio en área protegida", "directo", True),
    ("Plan Nacional Emergencias — incendio forestal", "directo", True),
    ("Sofocación de incendios en Parque Nacional", "directo", True),
    ("Aviación cisterna contra incendios forestales", "directo", True),
    ("Brigadistas forestales SERNAP", "directo", True),
    ("Contenedores aéreos contraincendios Guardian", "directo", True),
    # probable
    ("Adquisición de cisterna para operaciones de emergencia", "probable", True),
    ("Compra de EPP y motobomba", "probable", True),
    ("Equipo forestal y batefuego", "probable", True),
    ("Combustible para maquinaria de emergencia", "probable", True),
    ("Víveres para bomberos en campaña", "probable", True),
    ("Alimentación de brigadistas en terreno", "directo", True),
    ("Operaciones aéreas de apoyo logístico", "probable", True),
    ("Helicóptero para traslado de personal", "probable", True),
    ("Aeronave de apoyo a desastres", "probable", True),
    ("Maquinaria pesada para emergencia territorial", "probable", True),
    ("Equipo de protección personal para campaña", "probable", True),
    ("Mochila forestal estándar", "directo", True),
    ("Motobomba portátil para respuesta rural", "probable", True),
    ("Batefuegos para cuadrillas municipales", "probable", True),
    ("Cisterna de apoyo operativo", "probable", True),
    ("Aeronave para reconocimiento territorial", "probable", True),
    ("Combustible aéreo para despliegue logístico", "probable", True),
    # parcial — pool o programa explícitamente multi-evento
    ("Atención conjunta de incendios e inundaciones", "parcial", True),
    ("Programa para fuego, sequía y heladas", "parcial", True),
    ("Pool multiamenaza: quemas e inundación", "parcial", True),
    ("Respuesta a fuego y deslizamientos", "parcial", True),
    ("Emergencias por quemadas, sequía y granizo", "parcial", True),
    ("Logística compartida para fuego e inundaciones", "parcial", True),
    ("Plan multi-evento con componente fuego y sismo", "parcial", True),
    ("Fondo para quemadas y emergencia sanitaria", "parcial", True),
    ("Atención de fuego más sequía agrícola", "parcial", True),
    ("Operativo mixto por quemadas e inundación", "parcial", True),
    # indirecto — capacidad general relacionada, sin operación de fuego concreta
    ("Fortalecimiento institucional de gestión de riesgos", "indirecto", True),
    ("Sistema de alerta temprana multiamenaza", "indirecto", True),
    ("Centro de monitoreo de riesgos ambientales", "indirecto", True),
    ("Equipamiento de unidad de gestión de riesgo", "indirecto", True),
    ("Plataforma de coordinación para emergencias", "indirecto", True),
    ("Base logística multipropósito de respuesta", "indirecto", True),
    ("Capacidad municipal para reducción de riesgos", "indirecto", True),
    ("Fortalecimiento del centro de operaciones de emergencia", "indirecto", True),
    ("Comunicaciones para gestión integral de riesgos", "indirecto", True),
    ("Infraestructura institucional de respuesta multiamenaza", "indirecto", True),
    # no_relacionado — genéricos / otros desastres
    ("Contratación por emergencia y desastres — ayuda humanitaria", "no_relacionado", False),
    ("Atención de emergencia por inundaciones en Beni", "no_relacionado", False),
    ("Declaratoria de desastre por sequía agrícola", "no_relacionado", False),
    ("Compra de alimentos para emergencia general", "no_relacionado", False),
    ("Reparación de caminos tras inundación", "no_relacionado", False),
    ("Ayuda humanitaria post-inundación", "no_relacionado", False),
    ("Servicio de limpieza urbana ordinaria", "no_relacionado", False),
    ("Compra de útiles de oficina", "no_relacionado", False),
    ("Mantenimiento de flota vehicular administrativa", "no_relacionado", False),
    ("Construcción de escuela rural", "no_relacionado", False),
    ("Compra de medicamentos hospitalarios", "no_relacionado", False),
    ("Servicio de internet institucional", "no_relacionado", False),
    ("Alquiler de salón para evento cultural", "no_relacionado", False),
    ("Combustible para vehículos administrativos", "no_relacionado", False),
    ("Emergencia sanitaria COVID-19", "no_relacionado", False),
    ("Desastre por sismo — reconstrucción de viviendas", "no_relacionado", False),
    ("Contratación por emergencia sin especificar evento", "no_relacionado", False),
    ("Pool de emergencias y desastres multi-evento", "no_relacionado", False),
    ("Adquisición de mobiliario escolar", "no_relacionado", False),
    ("Consultoría para catastro urbano", "no_relacionado", False),
    ("Mantenimiento preventivo de computadoras", "no_relacionado", False),
    ("Impresión de material educativo", "no_relacionado", False),
    ("Servicio de seguridad privada", "no_relacionado", False),
    ("Construcción de cancha deportiva", "no_relacionado", False),
    ("Compra de semillas para producción agrícola", "no_relacionado", False),
    ("Auditoría financiera institucional", "no_relacionado", False),
    ("Seguro de salud para funcionarios", "no_relacionado", False),
    ("Refrigerios para taller administrativo", "no_relacionado", False),
    ("Rehabilitación de alcantarillado sanitario", "no_relacionado", False),
    ("Estudio de movilidad urbana", "no_relacionado", False),
]


@pytest.mark.parametrize("text,expected,related", GOLDEN)
def test_golden_phrase(text: str, expected: str, related: bool):
    r = classify_fire_text(object_description=text)
    assert r.attribution == expected, f"{text!r} → {r.attribution} ({r.reason})"
    assert is_fire_related(r) is related
    assert r.rules_fired
    if expected == "directo":
        assert r.confidence_score >= Decimal("0.9")
        assert r.evidence_span or r.matched_terms


def test_golden_bank_size():
    assert len(GOLDEN) >= 80
    counts = {label: sum(expected == label for _, expected, _ in GOLDEN) for label in {
        "directo", "probable", "parcial", "indirecto", "no_relacionado"
    }}
    assert counts["directo"] >= 15
    assert counts["probable"] >= 15
    assert counts["parcial"] >= 10
    assert counts["indirecto"] >= 10
    assert counts["no_relacionado"] >= 30


def test_coverage_threshold():
    """Gate F4: ≥90% of golden bank must match expected attribution."""
    ok = 0
    for text, expected, _ in GOLDEN:
        r = classify_fire_text(object_description=text)
        if r.attribution == expected:
            ok += 1
    ratio = ok / len(GOLDEN)
    assert ratio >= 0.90, f"coverage {ratio:.0%} < 90% ({ok}/{len(GOLDEN)})"
