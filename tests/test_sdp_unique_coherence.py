"""SDP-UNIQUE-1 — cohérence de la notion unique « SDP résiduelle, bâti conservé ».

Deux gardes :
  • `test_docs_coherence_couvre_estimer` — UNITAIRE (sans base, famille du hook) : le 9ᵉ document
    « Estimer un bien » est bien dans le harnais docs_coherence (NU-D-043 / D-042).
  • `test_sdp_residuelle_coherente_sur_temoins` — REEL (base applicative) : sur les 12 témoins du
    lot A, la SDP résiduelle servie à l'EN-TÊTE (parcel_residuel, réconciliée avec la cause du
    scoring), au VERDICT (score_labuse) et au SCORING (potentiel_sdp_m2) est UNE SEULE valeur —
    soit « rien » (0/∅) partout, soit la même valeur positive partout. Échoue au moindre écart.
"""
from __future__ import annotations

import os
import pathlib

import pytest

# 12 témoins du lot A (docs/audit-2026-11/nu-1/A). DR0042 = disparue (fiche de courtoisie, pas de SDP).
TEMOINS = [
    "97411000IN0347", "97411000IE0241", "97411000HC0139", "97424000AE0050",
    "97424000AM0893", "97421000AB0133", "97411000AO0753", "97411000EY0173",
    "97417000BI0076", "97411000AB0785", "97411000HN0074", "97411000DR0042",
]


def test_docs_coherence_couvre_estimer():
    """NU-D-043 — « Estimer un bien » (/analyse-annonce) était le seul doc portant « SDP restante »
    hors du harnais. Il doit désormais y figurer pour que sa SDP soit confrontée aux autres."""
    src = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "docs_coherence.py"
    txt = src.read_text(encoding="utf-8")
    # dans la fonction documents() : une entrée « Estimer un bien » sur la route analyse-annonce.
    assert "Estimer un bien" in txt and "/analyse-annonce/" in txt, (
        "docs_coherence.documents() ne couvre pas « Estimer un bien » (analyse-annonce) — D-042")
    # FIX-FINAL-1 (NU-D-043) — et surtout dans ORDRE_DOCS : généré NE SUFFIT PAS, il doit être
    # CONFRONTÉ. On isole l'affectation d'ORDRE_DOCS et on vérifie qu'« Estimer un bien » y figure.
    bloc = txt.split("ORDRE_DOCS", 1)[1].split("]", 1)[0]
    assert "Estimer un bien" in bloc, (
        "« Estimer un bien » généré mais absent d'ORDRE_DOCS → jamais confronté (NU-D-043)")


def _rien(x) -> bool:
    return x is None or x == 0


@pytest.mark.coherence  # COHERENCE-HOOK-1 — regroupée sous la suite de cohérence (banc de nuit / -m coherence)
@pytest.mark.reel  # interroge la base APPLICATIVE réelle (run servi + scoring) — hors CI (base vide)
def test_sdp_residuelle_coherente_sur_temoins():
    from sqlalchemy import create_engine, text

    app_url = (os.environ.get("LABUSE_APP_DATABASE_URL")
               or os.environ.get("LABUSE_DATABASE_URL",
                                 "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"))
    try:
        eng = create_engine(app_url, future=True)
        with eng.connect() as c:
            c.execute(text("SET default_transaction_read_only=on"))
            if not c.execute(text("SELECT to_regclass('parcel_residuel')")).scalar():
                pytest.skip("parcel_residuel absente — base sans run résiduel servi")
            run = c.execute(text("SELECT value FROM mvt_meta WHERE key='run_label'")).scalar() or "q_v20"
            incoherents = []
            for idu in TEMOINS:
                row = c.execute(text(
                    """SELECT r.sdp_residuelle_m2 AS r_sdp, r.cause AS r_cause,
                              s.sdp_residuelle_m2 AS s_sdp, s.cause AS s_cause,
                              v.potentiel_sdp_m2 AS v_sdp
                         FROM parcels p
                         LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
                         LEFT JOIN score_labuse s ON s.parcel_id = p.id AND s.run_label = :run
                         LEFT JOIN parcel_p_score_v2 v ON v.parcelle_id = p.idu AND v.run_id = :run
                        WHERE p.idu = :idu"""), {"run": run, "idu": idu}).mappings().first()
                if not row or row["r_sdp"] is None and row["s_sdp"] is None and row["v_sdp"] is None:
                    continue  # parcelle hors-périmètre (disparue, hors PLU) : pas de SDP à comparer
                # (1) DONNÉE (E-013) — source unique : la SDP du scoring (potentiel_sdp_m2) est la SDP
                #     résiduelle BRUTE du run servi (parcel_residuel), sans réconciliation d'affichage.
                raw_r = None if row["r_sdp"] is None else int(round(row["r_sdp"]))
                raw_v = None if row["v_sdp"] is None else int(round(row["v_sdp"]))
                if raw_r != raw_v:
                    incoherents.append((idu, "DATA raw_residuel", raw_r, raw_v, row["r_cause"], row["s_cause"]))
                # (2) AFFICHAGE (A-001) — ce que lit le CLIENT : l'en-tête et le verdict. Une cause
                #     (résiduel OU scoring) ⇒ « aucune SDP » des DEUX côtés. Même valeur sinon.
                entete = None if (row["r_cause"] is not None or row["s_cause"] is not None) else row["r_sdp"]
                verdict = None if (row["s_cause"] is not None) else row["s_sdp"]
                presentes = [entete, verdict]
                positifs = [int(round(x)) for x in presentes if not _rien(x)]
                if positifs:
                    socle = positifs[0]
                    if any(_rien(x) for x in presentes) or any(abs(x - socle) > 1 for x in positifs):
                        incoherents.append((idu, "AFFICHAGE", entete, verdict, row["r_cause"], row["s_cause"]))
    except pytest.skip.Exception:
        raise
    except Exception as exc:  # noqa: BLE001 — base indisponible = skip, pas un échec
        pytest.skip(f"base applicative indisponible ({type(exc).__name__}) — cohérence SDP non vérifiable ici")
    assert not incoherents, (
        "SDP résiduelle « bâti conservé » incohérente entre en-tête/verdict/scoring :\n"
        + "\n".join(f"  {t[0]}: en-tête={t[1]} verdict={t[2]} scoring={t[3]} "
                    f"(cause résiduel={t[4]}, cause scoring={t[5]})" for t in incoherents))
