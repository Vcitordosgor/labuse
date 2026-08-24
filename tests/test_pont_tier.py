"""FIX-PONT-TIER — le compte ANNONCÉ par le Copilote (compter_parcelles) == le compte que
« Voir sur la carte » demanderait pour les MÊMES tiers.

Le pont carte traduit les critères via `_criteres_vers_filtres` puis (analyseLabuse armé) les sert
tels quels à `/filtre`. On éprouve la CHAÎNE réelle : alias de tier → critères → traduction front
→ même `FiltreCriteres` → même SQL. Le tier réserve foncière est le piège : l'ancien alias
`"reserve"` n'existait pas en base et comptait 0 EN SILENCE (carte et compte à 0 → faux accord).

Les comptes réels vivent dans le run servi (q_v10_m129) : on interroge la base de l'app via
`session_scope()` (lecture seule), comme les tests de fiche (le fixture `db_session` pointe une base
d'essai plus creuse où réserve foncière = 0 → l'égalité y serait vacante).
"""
from __future__ import annotations

import pytest

from labuse.db import session_scope
from labuse.copilote_v2.outils import compter_parcelles, _TIER_ALIAS, RUN
from labuse.copilote_v2.answering import _criteres_vers_filtres
from labuse.api.app import FiltreCriteres, filtre

#: les seuls tiers qui EXISTENT en base (mvt_parcels.tier_v2), côté back ET front (TierV2).
TIERS_CANONIQUES = {"brulante", "chaude", "reserve_fonciere", "a_creuser"}


# ── locks PURS (sans base) : ce qui échouait EN SILENCE ────────────────────────────────────────

def test_alias_ne_sert_que_des_tiers_reels():
    """Aucune valeur d'alias ne peut pointer vers un tier absent de la base (« reserve » comptait 0)."""
    for cle, valeur in _TIER_ALIAS.items():
        for t in valeur.split(","):
            assert t in TIERS_CANONIQUES, f"alias {cle!r} → {t!r} n'existe pas en base"


def test_reserve_resout_vers_reserve_fonciere():
    """Le piège nommé du mandat : « reserve » DOIT résoudre vers le tier canonique `reserve_fonciere`."""
    assert _TIER_ALIAS["reserve"] == "reserve_fonciere"


def test_traduction_front_rejoue_a_l_identique():
    """`_criteres_vers_filtres` (ce que `ouvrirCarte` pose dans filters.tiers) resert EXACTEMENT le
    tier compté — sinon la carte demanderait autre chose que le compte annoncé."""
    for canonique in ("brulante", "brulante,chaude", "reserve_fonciere", "a_creuser"):
        assert _criteres_vers_filtres({"tier": canonique})["tiers"] == canonique.split(",")


def test_non_tier_ne_pose_pas_de_tier():
    """Cas NON-TIER (signaux) : aucune clé `tiers` produite → le front NE PEUT PAS armer analyseLabuse
    → la carte reste FACTUELLE (parade M137-I). Le correctif ne touche QUE le chemin par tier."""
    assert "tiers" not in _criteres_vers_filtres({"signaux": "procedure"})


# ── lock d'ÉGALITÉ sur la base servie (le compte annoncé == le compte carte) ────────────────────

def _compte_carte(db, tiers: str) -> int:
    """Le compte que la carte demanderait avec CES tiers (analyseLabuse armé → tiersParam les sert
    tels quels) : même FiltreCriteres que le comptage du Copilote."""
    return filtre(c=FiltreCriteres(source=RUN, tiers=tiers), limit=0, offset=0,
                  sort=None, idus=0, groupes=0, db=db)["compte"]


@pytest.mark.parametrize("cle, canonique", [
    ("brulante", "brulante"),
    ("chaude", "chaude"),
    ("opportunites", "brulante,chaude"),
    ("reserve_fonciere", "reserve_fonciere"),
    ("reserve", "reserve_fonciere"),          # alias historique → doit résoudre au tier RÉEL
])
def test_compte_annonce_egale_compte_carte(cle, canonique):
    with session_scope() as db:
        r = compter_parcelles(db, tier=cle)
        tiers_carte = ",".join(_criteres_vers_filtres(r.data["criteres"])["tiers"])
        # tiers_carte == canonique est le lock DATA-INDÉPENDANT : il traverse l'alias complet
        # (compter → _TIER_ALIAS → crit → traduction) et ÉCHOUE sur l'ancien « reserve » (≠ canonique).
        assert tiers_carte == canonique                       # la carte demandera le tier canonique
        assert r.valeur == _compte_carte(db, tiers_carte)     # annoncé == carte (mêmes tiers, même SQL)
        assert r.valeur == _compte_carte(db, canonique)       # et « reserve » rend le compte du VRAI tier
        # NB : sur le run servi (q_v10_m129) réserve foncière = 8738 (mesuré). La base d'essai est
        # creuse (0) — l'égalité reste vraie (même SQL des deux côtés), la non-vacuité est vérifiée
        # hors CI comme le gap connu des tuiles.
