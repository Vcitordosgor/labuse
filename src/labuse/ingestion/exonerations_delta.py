"""Synchronisation du relevé des exonérations DELTA pour La Réunion."""
import fcntl
import json
import os
import tempfile
from datetime import date
from functools import lru_cache
from pathlib import Path

import httpx

from ..config import load_yaml_config
from ..tz import today_reunion

DATASET = "delta_deliberation_tam_17_01_23"
CATALOGUE = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/" + DATASET
SOURCE = "https://data.economie.gouv.fr/explore/dataset/" + DATASET + "/"
FICHIER = Path("/var/lib/labuse-taxe/exonerations.json")
CHAMPS = {
    "locaux_habitation": "social",
    "locaux_finances_a_l_aide_du_pret_ne_portant_pas_interet": "ptz",
    "immeubles_classes": "monument",
    **{regle["champ"]: regle["vote"] for regle in
       load_yaml_config("taxe_amenagement")["formules_locales"].values()},
}
COMMUNES = {f"974{i:02}" for i in range(1, 25)}


def compiler(rows, reference):
    # Un secteur peut déroger à la règle générale, y compris en la supprimant.
    scopes = {}
    for row in rows:
        if row["departement"] != "974":
            raise ValueError("Export hors département")
        effet = date.fromisoformat(row["date_effet"])
        fin = date.fromisoformat(row["date_fin"]) if row["date_fin"] else None
        if effet > reference or (fin and fin < reference):
            continue
        if row["def_prov"] != "DEFINITIF":
            raise ValueError("Délibération active non définitive")
        if row["zone_application"] == "Départementale" and not row["commune"]:
            cle = "974"
        elif row["zone_application"] == "Communale":
            cle = "974" + row["commune"]
            if cle not in COMMUNES:
                raise ValueError("Commune DELTA inconnue")
            if row["parcelle"]:
                section, numero, prefixe = row["section"], row["parcelle"], row["prefixe"] or "000"
                if not (section and section.isalnum() and len(section) <= 2 and numero.isdigit()
                        and len(numero) <= 4 and len(prefixe) == 3):
                    raise ValueError("Référence cadastrale invalide")
                cle += prefixe + section.zfill(2) + numero.zfill(4)
            elif row["section"] or row["prefixe"]:
                raise ValueError("Secteur sans parcelle")
        else:
            raise ValueError("Périmètre DELTA inconnu")
        votes = {}
        for champ, nom in CHAMPS.items():
            pct = row[champ]
            if pct is None:
                continue
            if type(pct) not in (int, float) or not 0 <= pct <= (50 if nom == "ptz" else 100):
                raise ValueError(f"Quotité invalide pour {champ}")
            if pct:
                votes[nom] = pct
        precedent = scopes.get(cle)
        if precedent and precedent[0] == effet and votes != precedent[1]:
            raise ValueError(f"Délibérations contradictoires pour {cle}")
        if precedent is None or effet >= precedent[0]:
            scopes[cle] = (effet, votes)

    if not (COMMUNES | {"974"}).issubset(scopes):
        raise ValueError("Couverture des 24 communes et du département incomplète")
    def dater(cle):
        effet, votes = scopes[cle]
        return {**votes, "effet": effet.isoformat()} if votes else {}
    return {
        "communes": {cle: dater(cle) for cle in sorted(COMMUNES) if scopes[cle][1]},
        "departement": dater("974"),
        "secteurs": {cle: dater(cle) for cle in scopes
                     if len(cle) == 14 and scopes[cle][1] != scopes[cle[:5]][1]},
    }


@lru_cache(maxsize=1)
def _lire(path, inode, mtime):
    return json.loads(path.read_bytes())


def releve(path=None):
    path = path or FICHIER
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return _lire(path, st.st_ino, st.st_mtime_ns)


def _json(client, suffix="", **params):
    r = client.get(CATALOGUE + suffix, params=params)
    r.raise_for_status()
    return r.json()


def _version(client):
    meta = _json(client)["metas"]["default"]
    if not meta["data_processed"]:
        raise ValueError("Version de publication DELTA absente")
    return [meta["data_processed"], meta["modified"], meta["records_count"]]


def synchroniser(client, path, jour, annee):
    path.parent.mkdir(exist_ok=True, parents=True)
    with (path.parent / ".sync.lock").open("a") as verrou:
        fcntl.flock(verrou, fcntl.LOCK_EX)
        formules = load_yaml_config("taxe_amenagement")["formules_locales"]
        version = _version(client)
        ancien = releve(path) or {}
        if (ancien.get("version") == version and ancien.get("releve_le") == jour.isoformat()
                and ancien.get("annee") == annee and ancien.get("formules_locales") == formules):
            return "Publication inchangée"
        filtre = {"where": 'departement="974"'}
        attendu = _json(client, "/records", **filtre, limit=1)["total_count"]
        rows = _json(client, "/exports/json", **filtre)
        if not isinstance(rows, list) or len(rows) != attendu:
            raise ValueError("Export DELTA incomplet")
        date_effet = min(jour, date(annee, 12, 31))
        nouveau = compiler(rows, date_effet)
        if _version(client) != version:
            raise ValueError("Publication modifiée pendant la lecture")
        nouveau.update(formules_locales=formules, source=SOURCE, version=version, annee=annee, releve_le=jour.isoformat(),
                       lignes=len(rows), date_application=date_effet.isoformat())
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            try:
                tmp.write(json.dumps(nouveau, ensure_ascii=False, sort_keys=True).encode())
                tmp.flush()
                os.fsync(tmp.fileno())
                os.chmod(tmp.name, 0o644)
                os.replace(tmp.name, path)
            finally:
                Path(tmp.name).unlink(missing_ok=True)
        return f"Relevé validé : {len(rows)} lignes, 24 communes et département, publication {version[0]}"


if __name__ == "__main__":
    from ..config import load_yaml_config
    annee = load_yaml_config("taxe_amenagement")["meta"]["annee"]
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        print(synchroniser(client, FICHIER, today_reunion(), annee))
