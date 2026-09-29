"""CIRCUIT-2 lot 6 (mis à jour EXPORTS-2 lot 8) — les exports sur le registre : le BUILDER UNIQUE
`src/labuse/exports/` reçoit des objets `Valeur` (origine portée : run, millésimes, couverture,
état), le prix du neuf des PDF est l'OBSERVÉ (jamais l'id VEFA à l'acte réservé au scoring —
arbitrage Q3), les millésimes des sources sont LUS de la fiche (data_sources), jamais en dur."""
from __future__ import annotations

from pathlib import Path

import pytest

from labuse.registre.valeur import Valeur, valeurs_pour

pytestmark = pytest.mark.db

RACINE = Path(__file__).resolve().parents[1]

#: EXPORTS-2 lot 8 — les anciennes chaînes (briques_pdf, banquier, argumentaire, pdf_zone,
#: pdf_projet) sont éteintes. Tous les documents client (Dossier · Résumé · Financier · Apporteur ·
#: Pré-dossier PC · Flash) sont désormais servis par le BUILDER UNIQUE `src/labuse/exports/`.
BUILDERS = sorted(str(p.relative_to(RACINE))
                  for p in (RACINE / "src/labuse/exports").rglob("*.py")
                  if "__pycache__" not in p.parts)


def test_valeurs_pour_construit_des_valeurs_tamponnees(db_session):
    v = valeurs_pour(db_session,
                     {"prix_neuf_observe_eur_m2": 4730, "ventes_100m_n": 3},
                     couvertures={"ventes_100m_n": {"n": 3, "non_couvert": False}})
    assert set(v) == {"prix_neuf_observe_eur_m2", "ventes_100m_n"}
    neuf = v["prix_neuf_observe_eur_m2"]
    assert isinstance(neuf, Valeur) and neuf.valeur == 4730
    assert "dvf" in neuf.reservoirs, "le tampon porte les réservoirs (millésimes)"
    assert v["ventes_100m_n"].tampon()["couverture"] == {"n": 3, "non_couvert": False}


def test_valeurs_pour_jamais_une_valeur_inventee(db_session):
    """Un id non fourni ne reçoit RIEN (pas de Valeur creuse) ; un id inconnu est ignoré."""
    v = valeurs_pour(db_session, {"id_inconnu_xyz": 1})
    assert v == {}


def test_prix_neuf_vefa_a_l_acte_seulement_sous_sa_notion_labellisee():
    """Arbitrage Q3, MIS À JOUR (PRE-DEPLOY-1 lot B, confirmé Vic) — la scission EXPORTS-FIX-1 C5.

    Q3 interdisait de servir le VEFA à l'acte MAQUILLÉ en neuf observé. EXPORTS-FIX-1 C5 a depuis
    SCINDÉ la notion : le VEFA à l'acte est servi comme une donnée DISTINCTE, DÉCLARÉE au registre et
    LABELLISÉE « VEFA à l'acte » (`prix_neuf_vefa_acte_eur_m2`, Comparateur communes), à côté du neuf
    OBSERVÉ (`prix_neuf_observe_eur_m2`, `resolve_prix_sortie_servi`). L'invariant réel devient donc :
    le moteur de l'acte (`neuf_vefa_commune`) n'est lu QUE sous l'extracteur de sa notion labellisée —
    JAMAIS sous celui du neuf observé (sinon on re-maquillerait l'acte en observé, le vrai danger Q3)."""
    from labuse.registre.donnees import DONNEES
    # 1) la notion de l'acte est bien DÉCLARÉE et LABELLISÉE « à l'acte » (scission assumée, pas un slip)
    d = DONNEES.get("prix_neuf_vefa_acte_eur_m2")
    assert d is not None, "la notion VEFA à l'acte doit être déclarée au registre"
    assert "acte" in getattr(d, "libelle", "").lower(), "son libellé doit dire « à l'acte » (distinct de l'observé)"
    # 2) dans chaque builder, `neuf_vefa_commune` n'apparaît QUE sous l'extracteur de l'acte.
    import re
    deco = re.compile(r'@extracteur\(\s*["\']([^"\']+)["\']')
    for b in BUILDERS:
        courant = None
        for ligne in (RACINE / b).read_text().splitlines():
            m = deco.search(ligne)
            if m:
                courant = m.group(1)
            if "neuf_vefa_commune" in ligne:
                assert courant == "prix_neuf_vefa_acte_eur_m2", (
                    f"{b} lit `neuf_vefa_commune` sous l'extracteur « {courant} » — le VEFA à l'acte "
                    "n'est admis que sous sa notion labellisée `prix_neuf_vefa_acte_eur_m2`, jamais "
                    "confondu avec le neuf observé (`prix_neuf_observe_eur_m2`).")


def test_collectes_attachent_les_valeurs_registre():
    """EXPORTS-2 lot 8 : la collecte du builder unique n'assemble QUE des objets `Valeur`
    tamponnés (`valeurs_pour`) — les blocs ne reçoivent ni calcul ni requête, seulement des
    Valeur. La mise en page (blocs/*.py) lit ces Valeur, jamais la base."""
    collecte = (RACINE / "src/labuse/exports/robinet_fiche.py").read_text()
    assert "valeurs_pour" in collecte, "la collecte doit tamponner via le registre"
    assert "dict[str, Valeur]" in collecte, "la collecte rend {id → Valeur}, rien d'autre"


def test_sources_des_pdf_sans_millesime():
    """EXPORTS-REBRANCHEMENT-1 lot 2 (doctrine PAGE-SOURCES-1 18/09) : le bloc Sources des PDF
    n'imprime PLUS de millésime — noms de sources et producteurs seuls, aucune date en dur."""
    src = (RACINE / "src/labuse/exports/blocs/sources.py").read_text()
    assert "millesime']}" not in src and 'millesime"]}' not in src, "plus de millésime imprimé"
    # aucune année gravée dans le bloc
    import re
    assert not re.search(r"\b(19|20)\d{2}\b", src), "aucun millésime en dur dans le bloc Sources"
