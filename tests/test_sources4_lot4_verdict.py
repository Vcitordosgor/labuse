"""SOURCES-4 lot 4 — verdict final + verrou G2 étendu.

Le mandat clôt sur : SCHEMAS.csv sans plus AUCUN champ « à voir » nu (tout champ porte un verdict
définitif — MAXIMUM, PARTIEL — producteur, ou à ingérer — session dédiée à rang conservé), et le
verrou G2 s'étend pour l'enforcer (une source servie ne porte aucun champ « à voir » de plus de
30 jours → opérationnalisé : plus aucun « à voir » nu).
"""
from __future__ import annotations

import csv
from pathlib import Path

_SCHEMAS = Path(__file__).resolve().parents[1] / "docs" / "audit-2026-09" / "SOURCES" / "SCHEMAS.csv"


def test_schemas_aucun_a_voir_nu():
    """Plus aucun champ au verdict « à voir » nu — tout est tranché (LOT 4)."""
    nus = [f"{r['source']} / {r['champ_ingere']}"
           for r in csv.DictReader(_SCHEMAS.open(encoding="utf-8"))
           if (r.get("verdict") or "").strip() == "à voir"]
    assert nus == [], f"{len(nus)} champ(s) « à voir » nu restant(s) : {nus[:5]}"


def test_verrou_g2_etendu_lit_schemas():
    """Le verrou G2 étendu détecte bien un « à voir » nu (garde mordante) et n'en voit aucun ici."""
    from labuse.circuit_garanties import _schemas_a_voir_nus
    assert _schemas_a_voir_nus() == []
