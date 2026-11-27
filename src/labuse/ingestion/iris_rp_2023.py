"""Lecture des bases harmonisées à l'IRIS, RP2023 (INSEE, 15 octobre 2026)."""
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb


LOGEMENT = "https://api.insee.fr/melodi/file/DS_RP_LOGEMENT_PRINC_IRIS_2023/PARQUET"
POPULATION = "https://api.insee.fr/melodi/file/DS_RP_POPULATION_PRINC_IRIS_2023/PARQUET"

# Tables de passage officielles INSEE 9061352 et 9054332. Toutes les dimensions
# qui ne participent pas à un indicateur restent sur la modalité ensemble (_T).
DIMENSIONS = ("OCS", "TDW", "RP_MEASURE", "L_STAY", "NRG_SRC", "CARS", "CARPARK",
              "NOR", "TSH", "BUILD_END", "UFS")
PRINCIPALE = {"OCS": "DW_MAIN"}
LOGEMENTS = {
    "log": {}, "rp": PRINCIPALE, "men": PRINCIPALE, "logvac": {"OCS": "DW_VAC"},
    "maison": {"TDW": "1"}, "appart": {"TDW": "2"},
    "rp_prop": {**PRINCIPALE, "TSH": "100"}, "rp_loc": {**PRINCIPALE, "TSH": "200"},
    "rp_lochlmv": {**PRINCIPALE, "TSH": "221"},
    "nper_rp": {**PRINCIPALE, "RP_MEASURE": "DWELLINGS_POPSIZE"},
}
CONSTRUCTION = {
    "ach_tot": "Y_LT2021", "ach_1919": "Y_LT1919", "ach_1945": "Y1919T1945",
    "ach_1970": "Y1946T1970", "ach_1990": "Y1971T1990", "ach_2005": "Y1991T2005",
    "ach_2020": "Y2006TAAAA",
}
AGES = {
    "pop": "_T", "pop_0014": "Y_LT15", "pop_1517": "Y15T17", "pop_1824": "Y18T24",
    "pop_2539": "Y25T39", "pop_4054": "Y40T54", "pop_5564": "Y55T64",
    "pop_6579": "Y65T79", "pop_80p": "Y_GE80", "pop_65p": "Y_GE65",
}
NOUVELLES_COLONNES = ("ach_2020", "pop_1517", "pop_1824", "pop_2539", "pop_4054",
                      "pop_5564", "pop_6579", "pop_80p", "pop_65p")
ANCIENNES_TRANCHES = ("ach_2019", "pop_1529", "pop_3044", "pop_4559", "pop_6074", "pop_75p")


def lire_fichiers(logement, population, millesime):
    donnees = {}
    logement_dims = {**LOGEMENTS, **{k: {**PRINCIPALE, "BUILD_END": v} for k, v in CONSTRUCTION.items()}}
    with duckdb.connect(":memory:") as connexion:
        def lire(fichier, colonne, filtres):
            where = " AND ".join(f"{k}=?" for k in filtres)
            positions = connexion.execute(
                "SELECT GEO,GEO_OBJECT,OBS_VALUE FROM read_parquet(?) "
                "WHERE GEO LIKE '974%' AND TIME_PERIOD=DATE '2023-01-01' AND " + where,
                [str(fichier), *filtres.values()]).fetchall()
            codes_vus = set()
            for geo, objet, valeur in positions:
                code = geo + "0000" if objet == "COM" else geo
                if len(code) != 9 or code in codes_vus or valeur is None or valeur < 0:
                    raise ValueError(f"RP2023 — valeur ou identifiant invalide pour {colonne} et {geo}")
                codes_vus.add(code)
                donnees.setdefault(code, {"iris": code, "insee": code[:5], "millesime": millesime})[colonne] = valeur
            if len(codes_vus) != 344:
                raise ValueError(f"RP2023 — {len(codes_vus)} territoires pour {colonne}, 344 attendus")

        for colonne, dimensions in logement_dims.items():
            filtres = dict.fromkeys(DIMENSIONS, "_T")
            filtres.update(RP_MEASURE="DWELLINGS")
            filtres.update(dimensions)
            lire(logement, colonne, filtres)
        for colonne, age in AGES.items():
            lire(population, colonne, {"AGE": age, "SEX": "_T", "IMMI": "_T",
                 "NATIONALITY_TYPE": "_T", "HAR": "_T", "RP_MEASURE": "POP"})

    for r in donnees.values():
        if set(logement_dims) - r.keys() or set(AGES) - r.keys():
            raise ValueError(f"RP2023 — logement et population incomplets pour {r['iris']}")
        total = sum(r[c] for c in AGES if c not in ("pop", "pop_65p"))
        if abs(total-r["pop"]) > .002 or abs(r["pop_65p"]-r["pop_6579"]-r["pop_80p"]) > .002:
            raise ValueError(f"RP2023 — classes d’âge incohérentes pour {r['iris']}")
        r.update(dict.fromkeys(ANCIENNES_TRANCHES))
    return list(donnees.values())


def telecharger(client, logement, population, millesime):
    with TemporaryDirectory(prefix="labuse-iris-") as repertoire:
        chemins = []
        for libelle, url in (("logement", logement), ("population", population)):
            chemin = Path(repertoire) / f"{libelle}.parquet"
            with client.stream("GET", url) as reponse, chemin.open("wb") as fichier:
                reponse.raise_for_status()
                for bloc in reponse.iter_bytes(1_048_576):
                    fichier.write(bloc)
            chemins.append(chemin)
        return lire_fichiers(*chemins, millesime)
