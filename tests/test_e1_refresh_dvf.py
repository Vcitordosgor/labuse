"""FRAICHEUR-FIX-1 (point 1) — refresh_dvf lit le FORMAT ETALAB ACTUEL (ressources `full-AAAA[-sN]`
du jeu data.gouv, full-France filtré 974), recharge la fenêtre de la période SANS doublon, garde
l'historique, et ne grave la version qu'après succès. Test au premier semestre 2026 (full-2026-s1).

CORRECTIFS-1 E1 (conservé) — la table rechargée est bien `dvf_mutations` (la table SERVIE)."""
import gzip
import io
import json

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_HEADER = ("id_mutation,date_mutation,numero_disposition,nature_mutation,valeur_fonciere,"
           "adresse_numero,adresse_suffixe,adresse_nom_voie,code_postal,code_commune,nom_commune,"
           "code_departement,id_parcelle,ancien_id_parcelle,lot1_numero,nombre_lots,code_type_local,"
           "type_local,surface_reelle_bati,nombre_pieces_principales,surface_terrain,longitude,latitude")


def _row(idm, insee, dep, idp, val, surf, lon, lat, tl="Maison"):
    return (f"{idm},2026-02-10,000001,Vente,{val},12,,RUE TEST,{insee[:5]},{insee},Ville,{dep},"
            f"{idp},,1,1,1,{tl},{surf},4,500,{lon},{lat}")


def _csv_s1_2026() -> bytes:
    # deux ventes 974 (Saint-Denis 97411) + une vente hors-974 (Paris 75056) à écarter par le filtre.
    lignes = [
        _HEADER,
        _row("2026-900001", "97411", "974", "97411000AB0001", "250000.00", "90", "55.45", "-20.88"),
        _row("2026-900002", "97411", "974", "97411000AB0002", "310000.00", "110", "55.46", "-20.89"),
        _row("2026-700000", "75056", "75", "75056000XX0001", "900000.00", "80", "2.35", "48.85"),
    ]
    return gzip.compress(("\n".join(lignes) + "\n").encode("utf-8"))


_DS_META = {
    "last_update": "2026-11-07T19:46:13+00:00",
    "resources": [
        {"title": "DVF 2025", "format": "csv.gz", "filesize": 1,
         "url": "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/"
                "20261020-114721/full-2025.csv.gz"},
        {"title": "DVF 2026 (1er semestre)", "format": "csv.gz", "filesize": 1,
         "url": "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/"
                "20261020-114825/full-2026-s1.csv.gz"},
        # le fichier unique et l'archive legacy NE DOIVENT PAS être pris pour des périodes.
        {"title": "fichier unique", "format": "csv.gz",
         "url": "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/"
                "20261021-085741/dvf.csv.gz"},
        {"title": "[ARCHIVE] legacy", "format": "url",
         "url": "https://files.data.gouv.fr/geo-dvf/latest/csv/"},
    ],
}


def _fake_get(ferme_s1=False):
    """http_get(url)->bytes : rend le JSON du jeu et les .csv.gz des ressources. `ferme_s1` simule
    une période 2025 inchangée (pas de rechargement)."""
    def get(url: str) -> bytes:
        if url.endswith("/datasets/demandes-de-valeurs-foncieres-geolocalisees/"):
            return json.dumps(_DS_META).encode("utf-8")
        if "full-2026-s1" in url:
            return _csv_s1_2026()
        if "full-2025" in url:
            return _csv_s1_2026()  # peu importe : on ne le recharge que si sa version a changé
        raise AssertionError(f"URL inattendue : {url}")
    return get


def _seed_parcelle_sd(s):
    """Une parcelle Saint-Denis (insee 97411) pour que insert_muts rattache l'INSEE à la commune."""
    s.execute(text("DELETE FROM dvf_mutations WHERE commune = 'Saint-Denis' "
                   "AND date_mutation::date BETWEEN '2026-01-01' AND '2026-06-30'"))
    existe = s.execute(text("SELECT 1 FROM parcels WHERE idu LIKE '97411%' LIMIT 1")).scalar()
    if not existe:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, geom) VALUES ('97411000AB0001', 'Saint-Denis', "
            "ST_SetSRID(ST_MakePoint(55.45, -20.88), 4326))"))


def test_refresh_dvf_charge_le_s1_2026(db_session):
    from labuse.ingestion import fraicheur
    s = db_session
    fraicheur._ensure(s)
    _seed_parcelle_sd(s)
    # on PART d'un état où 2025 est déjà à jour mais 2026-S1 jamais vu (le vrai cas FRAICHEUR-1).
    fraicheur._etat_set(s, "dvf:res:2025", "20261020-114721")

    res = fraicheur.refresh_dvf(s, commit=False, http_get=_fake_get())

    assert res["no_op"] is False
    assert res["dernier_millesime"] == "2026-S1"
    tokens = {r["token"] for r in res["recharges"]}
    assert tokens == {"2026-S1"}, "seule la période jamais vue est rechargée"
    rech = res["recharges"][0]
    assert rech["apres"] == 2, "les 2 ventes 974 chargées (la vente parisienne écartée)"
    assert rech["ajoutees"] == 2
    # les ventes sont bien en base, dans la fenêtre S1 2026
    n = s.execute(text("SELECT count(*) FROM dvf_mutations WHERE commune='Saint-Denis' "
                       "AND date_mutation::date BETWEEN '2026-01-01' AND '2026-06-30'")).scalar()
    assert n == 2
    # la version n'est gravée qu'APRÈS succès
    assert fraicheur._etat_get(s, "dvf:res:2026-S1") == "20261020-114825"


def test_refresh_dvf_idempotent_sans_doublon(db_session):
    """Deux passages de suite = le même état (DELETE de la fenêtre avant réinsertion)."""
    from labuse.ingestion import fraicheur
    s = db_session
    fraicheur._ensure(s)
    _seed_parcelle_sd(s)
    fraicheur.refresh_dvf(s, commit=False, http_get=_fake_get())
    # second passage : la version 2026-S1 est désormais connue → no-op
    res2 = fraicheur.refresh_dvf(s, commit=False, http_get=_fake_get())
    assert res2["no_op"] is True
    n = s.execute(text("SELECT count(*) FROM dvf_mutations WHERE commune='Saint-Denis' "
                       "AND date_mutation::date BETWEEN '2026-01-01' AND '2026-06-30'")).scalar()
    assert n == 2, "pas de doublon après un second passage"


def test_refresh_dvf_version_pas_gravee_si_download_leve(db_session):
    """Si le téléchargement d'une période lève, sa version n'est pas enregistrée (re-tenté)."""
    from labuse.ingestion import fraicheur
    s = db_session
    fraicheur._ensure(s)
    _seed_parcelle_sd(s)

    def get_boom(url: str) -> bytes:
        if url.endswith("/datasets/demandes-de-valeurs-foncieres-geolocalisees/"):
            return json.dumps(_DS_META).encode("utf-8")
        raise RuntimeError("téléchargement coupé")

    fraicheur._etat_set(s, "dvf:res:2025", "20261020-114721")
    try:
        fraicheur.refresh_dvf(s, commit=False, http_get=get_boom)
    except RuntimeError:
        pass
    assert fraicheur._etat_get(s, "dvf:res:2026-S1") is None
