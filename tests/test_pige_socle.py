"""RADAR V0 · P0 — socle données + GARDE LÉGALE (recette permanente).

Le test le plus important du mandat : la doctrine « collecte 100 % humaine » gravée en pierre.
Aucun code du dépôt ne requête / fetch / parse / capture un portail d'annonces. Les noms de portails
n'existent QUE comme constantes d'affichage (pige/portails.py + composants d'écran Radar) ou en
commentaire — JAMAIS dans un appel réseau.

Vérifie aussi : schéma pige_* présent et isolé, événements journalisables, répertoire captures privé.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from labuse.db import session_scope

pytestmark = pytest.mark.db

_ROOT = Path(__file__).resolve().parents[1]

# les portails cités par le mandat (recette : grep -ri ... ne doit remonter QUE de l'affichage).
_TOKENS = ("leboncoin", "seloger", "pap.fr", "logic-immo", "bienici", "bien’ici", "bien'ici")
# indices d'un APPEL RÉSEAU (le péché capital : du code qui contacte un portail).
_HTTP = re.compile(r"httpx|requests\.|aiohttp|urllib|urlopen|\bfetch\(|axios|\.get\(|\.post\(", re.I)

# fichiers OÙ un nom de portail a le droit de vivre = affichage seulement (étendu par P3).
_ALLOWLIST_AFFICHAGE = (
    "src/labuse/pige/portails.py",
    "frontend/src/components/radar/",     # écrans client Radar (P3) — affichage du bouton sortant
    "frontend/src/components/admin/Radar",  # page admin Radar (P1)
)

_EXTS = (".py", ".js", ".ts", ".tsx")
_DIRS = ("src", "frontend/src")


def _fichiers():
    for d in _DIRS:
        for p in (_ROOT / d).rglob("*"):
            if p.suffix in _EXTS and "node_modules" not in p.parts and "__pycache__" not in p.parts:
                yield p


def _est_commentaire(ligne: str, idx: int) -> bool:
    """Le token à la position idx est-il dans un commentaire (mention, pas du code) ?"""
    avant = ligne[:idx]
    s = ligne.lstrip()
    return ("#" in avant or "//" in avant or s.startswith("*") or s.startswith("/*")
            or s.startswith("--"))


def _allowliste(p: Path) -> bool:
    rel = str(p.relative_to(_ROOT))
    return any(a in rel for a in _ALLOWLIST_AFFICHAGE)


def test_aucune_requete_portail_dans_le_depot():
    """DOCTRINE §2 — collecte 100 % humaine : aucun token portail sur une ligne d'APPEL RÉSEAU,
    et hors commentaire un token n'apparaît QUE dans un fichier d'affichage allowlisté."""
    fautes_reseau: list[str] = []
    fautes_code: list[str] = []
    for p in _fichiers():
        for n, ligne in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            bas = ligne.lower()
            for tok in _TOKENS:
                idx = bas.find(tok)
                if idx < 0:
                    continue
                rel = f"{p.relative_to(_ROOT)}:{n}"
                if _HTTP.search(ligne):                       # péché capital : requête + portail
                    fautes_reseau.append(f"{rel}  {ligne.strip()[:100]}")
                elif not _est_commentaire(ligne, idx) and not _allowliste(p):
                    fautes_code.append(f"{rel}  {ligne.strip()[:100]}")
                break
    assert not fautes_reseau, "APPEL RÉSEAU vers un portail détecté :\n" + "\n".join(fautes_reseau)
    assert not fautes_code, ("nom de portail en CODE hors affichage (doit être constante d'affichage "
                             "ou commentaire) :\n" + "\n".join(fautes_code))


def test_le_paquet_pige_ne_fait_aucun_appel_reseau():
    """Ceinture + bretelles : le paquet pige/ ne contient AUCUN crawler de portail.

    Doctrine « collecte 100 % humaine » : pige/ n'ouvre le réseau QUE pour la lecture ONE-SHOT
    d'une URL COLLÉE PAR UN HUMAIN (RETOURS-3 R3, décision Vic 31/08 — l'agence colle son propre
    lien, le serveur le lit une fois, sans retry ni boucle). Ce point d'entrée unique et audité est
    `_fetch_page_oneshot` dans `pige/api.py`. Le test le tolère NOMMÉMENT et interdit tout autre
    import d'un client HTTP dans le paquet — un crawler de portail (import HTTP ailleurs, ou boucle
    de requêtes) reste un échec bruyant."""
    fautes: list[str] = []
    for p in (_ROOT / "src" / "labuse" / "pige").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        if "import httpx" not in src and "import requests" not in src:
            continue
        if p.name != "api.py":
            fautes.append(f"{p.name} importe un client HTTP (seul le one-shot humain de api.py est toléré)")
            continue
        # Dans api.py : l'import HTTP ne vit QUE dans `_fetch_page_oneshot`, et sans boucle de requêtes.
        assert "def _fetch_page_oneshot" in src, "api.py importe un client HTTP hors du one-shot audité"
        bloc = src.split("def _fetch_page_oneshot", 1)[1].split("\ndef ", 1)[0]
        assert "import requests" in bloc, ("l'import HTTP de api.py doit rester confiné à "
                                           "_fetch_page_oneshot (lecture humaine one-shot)")
        avant = src.split("def _fetch_page_oneshot", 1)[0]
        assert "import requests" not in avant and "import httpx" not in avant, (
            "api.py importe un client HTTP au niveau module — le one-shot doit l'importer localement")
        for mot in (" while ", "\nwhile ", " for "):
            assert not (mot in bloc and ".get(" in bloc.split(mot, 1)[1][:200]), (
                "boucle de requêtes détectée dans le one-shot — un one-shot ne réessaie jamais")
    assert not fautes, "client HTTP hors du one-shot humain :\n" + "\n".join(fautes)


def test_schema_pige_present_et_isole(engine):
    tables = set(inspect(engine).get_table_names())
    attendues = {"pige_biens", "pige_annonces", "pige_faits", "pige_prix_historique",
                 "pige_captures", "pige_clics"}
    assert attendues <= tables, f"tables pige manquantes : {attendues - tables}"


def test_evenement_journalise_dans_event_log():
    from labuse.pige import tables as pg
    with session_scope() as db:
        bid = db.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut) "
            "VALUES ('Saint-Paul','terrain','active') RETURNING bien_id")).scalar()
        eid = pg.journaliser(db, pg.EV_NOUVELLE, "[RADAR-TEST] nouveau bien",
                             detail="terrain Saint-Paul", dedup=f"radar-test:{bid}")
        assert eid > 0
        row = db.execute(text("SELECT kind, source FROM event_log WHERE id = :i"),
                         {"i": eid}).mappings().first()
        assert row["kind"] == "pige.nouvelle" and row["source"] == "Radar"
        # nettoyage [RADAR-TEST]
        db.execute(text("DELETE FROM event_log WHERE id = :i"), {"i": eid})
        db.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": bid})
        db.commit()


def test_repertoire_captures_est_prive_et_hors_racine_publique():
    from labuse.pige.tables import captures_dir
    d = str(captures_dir())
    # jamais sous une racine servie par le web (frontend/ , static/ , public/) ni dans le dépôt app.
    assert "frontend" not in d and "/static" not in d and "/public" not in d
    assert str(_ROOT) not in d, "les captures ne doivent pas vivre dans le dépôt applicatif"
