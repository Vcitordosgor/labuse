"""LOGEMENTS-SOURCE-UNIQUE — toutes les surfaces tirent le « nombre de logements » de la MÊME
source que la fiche.

Décision Vic (18/10/2026, généralisée) : seul le moteur d'implantation de l'Étude de faisabilité
compte des logements (dessinés, contrôlés). AUCUNE surface n'imprime plus la fourchette de l'ancien
calcul de capacité (`estimate_capacity` : SDP ÷ logement moyen) — chacune imprime LE renvoi de la
fiche (`capacite_max.RENVOI_ETUDE`) + la mention « maximum réglementaire » (volet D,
`capacite_max.MENTION`/`MENTION_COURTE`) quand une capacité (SDP max) est affichée.

Deux volets :
  1. STATIQUE (hook) — plus aucun lecteur d'affichage des champs logements d'`estimate_capacity`
     (allowlist fermée : producteur, accesseur unique, gardes/calculs internes documentés) ; textes
     uniques ; bandes du Comparatif au vocabulaire de la fiche.
  2. RÉEL (local+reel) — sur 3 parcelles vivantes, chaque surface rend le MÊME renvoi et la même
     mention que la fiche, et aucun nombre de logements.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from labuse.capacite_max import MENTION_COURTE, RENVOI_ETUDE, RENVOI_ETUDE_PHRASE

RACINE = Path(__file__).resolve().parents[1]

#: Témoins vivants (les mêmes que test_a05_1 / test_docs1) : Le Tampon R+6, Saint-Denis R+3,
#: Saint-Paul gabarit calculable.
TEMOINS = ("97422000BX1106", "97411000AT0427", "97415000BW0102")


def _lire(rel: str) -> str:
    return (RACINE / rel).read_text()


# ══ Volet 1 — STATIQUE (tourne au hook, sans base) ═══════════════════════════════════════════

#: SEULS fichiers autorisés à nommer les champs logements d'`estimate_capacity` dans du CODE
#: (hors commentaires) — chacun pour une raison écrite, AUCUN n'affiche un nombre :
_LECTEURS_AUTORISES = {
    "src/labuse/faisabilite/engine.py",          # PRODUCTEUR (les champs restent pour les calculs)
    "src/labuse/exports/robinet_fiche.py",       # accesseur UNIQUE (_fourchette_logements, présence)
    "src/labuse/faisabilite/scenarios.py",       # garde interne « rien à bâtir » (aucun affichage)
    "src/labuse/faisabilite/bilan.py",           # calcul interne (mixité, VRD, places) — pas d'affichage
    "src/labuse/verite_terrain_capacite.py",     # module d'AUDIT lecture seule (mesure le moteur)
    "frontend/src/components/fiche/constructibilite.tsx",  # garde front (« rien à bâtir »), aucun nombre
}
_RX_CHAMPS = re.compile(r"logements_au_sol|logements_sous_sol")
_RX_COMMENT = re.compile(r"^\s*(#|//|/?\*|\{#)")


def _fichiers_lecteurs() -> set[str]:
    out: set[str] = set()
    for base in ("src/labuse", "frontend/src"):
        for p in (RACINE / base).rglob("*"):
            if p.suffix not in (".py", ".ts", ".tsx", ".j2", ".html"):
                continue
            try:
                txt = p.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if "logements_au_sol" not in txt and "logements_sous_sol" not in txt:
                continue
            for line in txt.splitlines():
                if _RX_CHAMPS.search(line) and not _RX_COMMENT.match(line):
                    out.add(str(p.relative_to(RACINE)))
                    break
    return out


def test_plus_aucun_lecteur_affichage_des_logements_ancien_moteur():
    """Le grep final du mandat, FIGÉ en test : hors producteur/accesseur/gardes-calculs documentés,
    plus personne ne lit `logements_au_sol`/`logements_sous_sol`. Un nouveau lecteur = échec ici
    (il devra passer par le renvoi de la fiche, jamais réimprimer la fourchette)."""
    lecteurs = _fichiers_lecteurs()
    assert lecteurs == _LECTEURS_AUTORISES, (
        f"lecteurs inattendus des champs logements d'estimate_capacity : "
        f"{sorted(lecteurs - _LECTEURS_AUTORISES)} ; disparus : {sorted(_LECTEURS_AUTORISES - lecteurs)}")


def test_textes_uniques_renvoi_et_mention():
    """Chaque surface utilise LES constantes (`RENVOI_ETUDE`/`MENTION*`) — pas un 3ᵉ texte."""
    assert RENVOI_ETUDE == "voir l'Étude de faisabilité"
    assert RENVOI_ETUDE in RENVOI_ETUDE_PHRASE
    # Financier : renvoi si non saisi, « Logements (projet) » si saisi — plus de « (maximum) ».
    fin = _lire("src/labuse/exports/blocs/financier.py")
    assert "RENVOI_ETUDE" in fin and "Logements (projet)" in fin and "Logements (maximum)" not in fin
    # builder : plus de lecture de la fourchette (saisie du porteur seule).
    assert "_fourchette_logements" not in _lire("src/labuse/exports/builder.py")
    # Flash : renvoi + mention servis, gabarit sans fourchette.
    assert "RENVOI_ETUDE" in _lire("src/labuse/flash/data.py")
    assert "logements_renvoi" in _lire("src/labuse/flash/templates/rapport.html.j2")
    # Copilote (faits + résumé + explication) : renvoi + mention.
    assistant = _lire("src/labuse/api/assistant.py")
    assert "RENVOI_ETUDE" in assistant and "MENTION_COURTE" in assistant
    assert "RENVOI_ETUDE_PHRASE" in _lire("src/labuse/api/modules.py")
    # Calculette (panneau scénarios) : renvoi (étape 7) + mention servis.
    scen = _lire("src/labuse/faisabilite/scenarios.py")
    assert "RENVOI_ETUDE" in scen and "MENTION_COURTE" in scen
    # Assemblage : ne sert plus de logements (le front renvoie déjà vers l'Étude).
    assert '"logements"' not in _lire("src/labuse/assemblage.py")
    assert "logements_combine" not in _lire("src/labuse/api/moteurs.py")


def test_dossier_et_miroir_renvoient_sans_nombre():
    """Le Dossier (miroir) imprime le renvoi ; l'extracteur ne sert plus {min, max}."""
    miroir = _lire("src/labuse/exports/miroir.py")
    assert "voir l'Étude de faisabilité" in miroir
    robinet = _lire("src/labuse/exports/robinet_fiche.py")
    assert '"renvoi": RENVOI_ETUDE' in robinet and '"min": lo' not in robinet


def test_extracteur_capacite_rend_le_renvoi_jamais_un_nombre(monkeypatch):
    """`capacite_logements` (la donnée de la fiche/du Dossier) = renvoi pur, sans nombre."""
    from labuse.exports import robinet_fiche as rf
    monkeypatch.setattr(rf, "_fourchette_logements", lambda db, idu: (2, 6))
    v = rf.EXTRACTEURS["capacite_logements"](object(), "97400000XX0001", {})
    assert v == {"renvoi": RENVOI_ETUDE, "texte": RENVOI_ETUDE}
    assert not re.search(r"\d", v["texte"])
    monkeypatch.setattr(rf, "_fourchette_logements", lambda db, idu: None)
    assert rf.EXTRACTEURS["capacite_logements"](object(), "97400000XX0001", {}) is None


# ══ Volet 2 — RÉEL : chaque écran = la fiche, sur 3 parcelles vivantes ═══════════════════════

pytestmark_reel = [pytest.mark.local, pytest.mark.reel]


@pytest.fixture()
def _base_reelle():
    """Rebranche l'engine sur la base APPLICATIVE réelle (même patron que test_a05_1)."""
    from labuse import db as db_mod
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not app_url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent — base applicative réelle inconnue")
    ancien_eng, ancien_sess = db_mod._engine, db_mod._Session
    db_mod._engine = db_mod.make_engine(app_url)
    db_mod._Session = None
    try:
        yield
    finally:
        db_mod._engine, db_mod._Session = ancien_eng, ancien_sess


def _temoin(s, idu):
    from sqlalchemy import text
    pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"témoin {idu} absent de la base aujourd'hui")
    from labuse.faisabilite.db import parcel_faisabilite
    fz = parcel_faisabilite(s, pid)
    if fz is None or not fz[1].constructible:
        pytest.skip(f"témoin {idu} non constructible aujourd'hui (données évoluées)")
    return pid, fz


_RX_N_LOGTS = re.compile(r"\d[\d  –-]*\s*(logement|logts)", re.IGNORECASE)


@pytest.mark.local
@pytest.mark.reel
@pytest.mark.parametrize("idu", TEMOINS)
def test_chaque_ecran_egale_la_fiche(idu, _base_reelle):
    """Sur une parcelle réelle : Dossier, Financier, Flash, Copilote, calculette et Assemblage
    rendent LE renvoi de la fiche (RENVOI_ETUDE) et la mention volet D — JAMAIS un nombre de
    logements (l'ancien calcul). Même source ⇒ même texte, partout."""
    from labuse.api.app import parcel_fiche
    from labuse.db import session_scope
    from labuse.exports import builder

    with session_scope() as s:
        pid, fz = _temoin(s, idu)
        fiche = parcel_fiche(idu, db=s, request=None)

        # 1 · Dossier (PDF/miroir) — le renvoi, aucun nombre sur la ligne (doctrine test_a05_1).
        #     (l'apostrophe du renvoi est échappée &#x27; dans le HTML — on compare dé-échappé)
        dossier = builder.construire(s, idu, "dossier", fiche=fiche).html.replace("&#x27;", "'")
        assert "Nombre de logements" in dossier and RENVOI_ETUDE in dossier
        assert "Capacité (logements)" not in dossier

        # 2 · Financier — plus de « Logements (maximum) » : saisie du porteur (« Logements
        #     (projet) », chip projet) OU renvoi. Le document exige un questionnaire complet —
        #     non établissable (TVA/programme manquants) ⇒ rien d'imprimé, sous-contrôle sans objet.
        try:
            financier = builder.construire(s, idu, "financier", fiche=fiche).html.replace("&#x27;", "'")
        except builder.DocumentNonEtablissable:
            financier = None
        if financier is not None:
            assert "Logements (maximum)" not in financier
            # la LIGNE du programme (cellule exacte, pas « Nombre de logements visés » des
            # hypothèses saisies) : renvoi sans aucun nombre — sauf si le porteur a saisi.
            if "Logements (projet)" not in financier:
                assert "Nombre de logements</td>" in financier
                seg = financier.split("Nombre de logements</td>", 1)[1][:160]
                assert "Étude de faisabilité" in seg and not _RX_N_LOGTS.search(seg)
            assert "maximum" in financier.lower()       # mention capacité maximale (volet D)

        # 3 · Flash — payload : renvoi + mention, plus de fourchette.
        from labuse.flash.data import _constructibilite, _existing_tables
        avail = _existing_tables(s, {"dryrun_parcel_evaluations", "parcel_residuel"})
        cons = _constructibilite(s, idu, avail) or {}
        fa = cons.get("faisa") or {}
        assert "logements_au_sol" not in fa
        if fa:
            assert fa["logements_renvoi"] == RENVOI_ETUDE and fa["capacite_mention"] == MENTION_COURTE
        pot = cons.get("potentiel") or {}
        assert "logements" not in (pot.get("table_rase") or {})
        assert not _RX_N_LOGTS.search(pot.get("verdict") or "")

        # 4 · Copilote — faits : renvoi (jamais une fourchette citable) ; résumé : mention + renvoi.
        from labuse.api.assistant import assistant_facts, rules_summary
        facts = assistant_facts(fiche)
        fab = facts.get("faisabilite") or {}
        assert "logements_au_sol" not in fab
        if fab:
            assert fab["nombre_logements"] == RENVOI_ETUDE
        md = rules_summary(facts)
        if fab.get("surface_plancher_m2"):
            assert RENVOI_ETUDE_PHRASE in md and MENTION_COURTE in md
        assert not _RX_N_LOGTS.search(md)

        # 5 · Calculette (panneau scénarios) — renvoi (étape 7) + mention, verdict sans logements.
        from labuse.faisabilite.scenarios import faisabilite_scenario
        pan = faisabilite_scenario(s, pid, "terrain_libere")
        assert pan is not None and "logements" not in pan
        assert pan["logements_renvoi"] == RENVOI_ETUDE and pan["capacite_mention"] == MENTION_COURTE
        e7 = next(e for e in pan["etapes"] if e["n"] == 7)
        assert e7["valeur"] == RENVOI_ETUDE
        assert not _RX_N_LOGTS.search(pan["verdict"])

        # 6 · Assemblage — plus de logements servis (le front renvoie vers l'Étude).
        from labuse.assemblage import aggregate_assiette
        from labuse import models
        from sqlalchemy import select
        p = s.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one()
        agg = aggregate_assiette(s, [p])
        assert "logements" not in agg

        # 7 · Comparer — la ligne est un renvoi (décision Vic, déjà en place) : rien n'est servi.
        from labuse.api.app import _compare_row
        row = _compare_row({"idu": idu, "surface_m2": p.surface_m2, "lines": []}, None)
        assert "logements_possibles" not in row and "logements_min" not in row
