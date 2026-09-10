"""RECETTE-11 — verrous sans base : le §3 potentiel n'imprime aucun verdict de surélévation (A6),
la date de survol accompagne la mesure LiDAR (A3), et un permis postérieur au survol est signalé (A4).

Le rendu du bloc lit un `potentiel_verdict` (le dict servi par l'API). On le fabrique de toutes pièces
et on vérifie le HTML produit — mécanique, aucune base."""
from __future__ import annotations

from labuse.exports.blocs import potentiel
from labuse.faisabilite.hauteur_lidar import survol_libelle
from labuse.registre.valeur import Valeur


def _V(cid, valeur, **kw):
    return Valeur(valeur=valeur, chiffre_id=cid, version_def="x", run=kw.pop("run", None), **kw)


def _valeurs(**pv):
    base = {"niveau": "faible", "libelle": "Potentiel faible", "hauteur_nature": "sourcé",
            "hauteur_base": "faîtage mesuré (LiDAR HD)", "hauteur_faitage_lidar_m": 6.9,
            "hauteur_egout_lidar_m": 3.0, "hauteur_marge_m": 3.1, "hauteur_contrainte": "faîtage",
            "hauteur_contraintes": [
                {"base": "égout", "mesure_m": 3.0, "regle_m": 7.0, "marge_m": 4.0},
                {"base": "faîtage", "mesure_m": 6.9, "regle_m": 10.0, "marge_m": 3.1}],
            "hauteur_survol": "septembre 2023", "sdp_residuelle_m2": 97, "pct_consomme": 79}
    base.update(pv)
    return {"potentiel_verdict": _V("potentiel_verdict", base)}


def test_a6_aucun_verdict_de_surelevation():
    """A6 — plus de « surélévation possible »/« pas de marge »/« non identifiée » : que la marge,
    la règle, la contrainte qui mord."""
    html = potentiel.rendu(_valeurs())
    bas = html.lower()
    for interdit in ("surélévation possible", "non identifiée", "pas de marge de surélévation",
                     "surélévation à confirmer"):
        assert interdit not in bas, interdit
    # ce qui DOIT rester : marge + contrainte + les deux calculs mesurés (égout ET faîtage)
    assert "sous la hauteur réglementaire" in bas
    assert "contrainte qui mord : le faîtage" in bas
    assert bas.count("mesuré contre") == 2 and "réglementaires (marge" in bas


def test_a3_date_de_survol_avec_la_mesure():
    """A3 — la mesure LiDAR HD ne s'affiche jamais sans sa date de survol."""
    html = potentiel.rendu(_valeurs())
    assert "mesuré au LiDAR HD, survol de septembre 2023" in html
    assert "LiDAR HD — IGN / Géoplateforme" in html  # cité dans les sources du §3


def test_a4_permis_posterieur_signale():
    """A4 — un permis autorisé APRÈS le survol : la mesure le dit ; comparé à la date de survol."""
    sans = potentiel.rendu(_valeurs())
    assert "possiblement dépassée" not in sans
    avec = potentiel.rendu(_valeurs(hauteur_permis_posterieur="15/03/2024"))
    assert "mesure antérieure au permis du 15/03/2024, possiblement dépassée" in avec


def test_a2_survol_libelle_mois_annee():
    """A2 — la date de survol est formatée « mois année » depuis la métadonnée, None si absente."""
    from datetime import date
    assert survol_libelle(date(2023, 9, 3)) == "septembre 2023"
    assert survol_libelle(date(2023, 8, 14)) == "août 2023"
    assert survol_libelle(None) is None


def test_a5_sentinelle_lidar_974():
    """A5 — la veille LiDAR HD surveille le CANAL RÉELLEMENT INGÉRÉ (grille de dalles WFS IGN) borné à
    la Réunion, par témoin sur la dernière édition ; une nouvelle diffusion 974 est détectée."""
    import json as _json
    from labuse import sentinelle
    entree = next(e for e in sentinelle.SEED if e["name"] == "LiDAR HD — MNH 50 cm (IGN)")
    assert entree["methode"] == "temoin"
    assert "data.geopf.fr/wfs" in entree["url"] and "IGNF_LIDAR-HD_METADONNEE" in entree["url"]
    # borné à l'emprise Réunion (pas national) + lit la dernière édition
    assert "BBOX=-21.40,55.20,-20.80,55.85" in entree["url"]
    assert entree["selecteur"] == "features.0.properties.date_edition"

    # sonde mécanique, sans réseau : baseline puis changement d'édition → « la donnée amont a changé »
    def http_faux(url, *, methode_http="GET"):
        corps = _json.dumps({"numberMatched": 2665,
                             "features": [{"properties": {"date_edition": "2025-03-13Z"}}]})
        return 200, {}, corps
    row = {"methode": "temoin", "url_version": entree["url"], "selecteur": entree["selecteur"],
           "dernier_entete": None}
    base = sentinelle.sonder_ligne(row, None, http=http_faux)
    assert base.statut == "ok" and base.vu == "2025-03-13Z"
    change = sentinelle.sonder_ligne({**row, "dernier_entete": "2024-01-01"}, None, http=http_faux)
    assert change.statut == "nouvelle_version"
