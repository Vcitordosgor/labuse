"""Droits fonciers complets des personnes morales (OUTIL-SCAN-FIX-1, bloquant 1).

Le fichier DGFiP « parcelles des personnes morales » restitue UNE LIGNE PAR (parcelle, titulaire,
droit) — col. 17 « CODE DROIT RÉEL OU PARTICULIER » (P propriétaire, G gérant/mandataire/
gestionnaire, B bailleur à construction, U/N usufruit/nue-propriété, E emphytéote, F/D/T foncier,
S syndic, Z gestion d'un bien de l'État…). Le loader historique (`personnes_morales.py`) dédoublonne
par idu et JETTE le droit → une société seulement gestionnaire d'une parcelle apparaît « propriétaire ».

Ce module charge TOUS les titulaires et TOUS leurs droits dans `parcelle_pm_droit` (table COMPLÈTE,
plusieurs lignes par idu), SANS toucher les lecteurs existants. La table de prod
`parcelle_personne_morale` (une ligne / idu, lue par tout le socle) est, elle, recalculée à part comme
« TITULAIRE PRINCIPAL » par une règle déterministe (propriétaire d'abord, gestionnaire en dernier) :
`recompute_principal`. Deux exécutions donnent le même principal (tri total, aucun aléa).

Idempotent : chargement par (millesime, idu, siren, droit_code) ; purge du millésime avant réinsertion.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants

SOURCE = "DGFiP — parcelles des personnes morales (droits complets)"
_BASE = ("https://data.economie.gouv.fr/api/v2/catalog/datasets/"
         "fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/")

#: attachment data.economie 2026 — la tranche « 61 à 976 » contient le 974 (graphie réelle du catalogue).
ATTACHMENT_2026_61_976 = "fichiers_des_parcelles_dpts_61_a_976_situation_2026zip"

#: positions (0-indexées) du CSV DGFiP 2026 — 24 colonnes, séparateur ';', VÉRIFIÉES sur l'entête réel
#: (descriptif officiel 2026). Nouveauté vs loader historique : `droit` = col. 17 (était sautée).
_COL = {"dep": 0, "direction": 1, "commune": 2, "prefixe": 4, "section": 5, "nplan": 6,
        "droit": 17, "siren": 19, "groupe": 20, "forme": 22, "denomination": 23}
_NB_COLONNES_ATTENDU = 24

#: Priorité du droit pour choisir le « titulaire principal » d'une parcelle (1 = gagne).
#: Ordre validé (LOT 0) : propriétaire d'abord → gestionnaire en dernier, autres droits ensuite.
#: Codes du descriptif DGFiP 2026 + Z (« gestion d'un bien de l'État », auto-décrit, hors tableau).
_RANG_DROIT = {
    "P": 1, "X": 1,              # propriétaire (X = La Poste occupant ET propriétaire)
    "U": 2,                      # usufruitier
    "N": 3,                      # nu-propriétaire
    "B": 4,                      # bailleur à construction
    "E": 5,                      # emphytéote
    "F": 6, "D": 6, "T": 6,      # foncier / domanier / ténuyer (domaine congéable)
    "V": 7,                      # bailleur d'un bail à réhabilitation
    "S": 8,                      # syndic de copropriété
    "G": 9, "Q": 9, "Z": 9,      # gérant / mandataire / gestionnaire
}
_RANG_AUTRE = 10                 # R, W, A, K, L, H, O, J, Y, vide… (non titulaires de propriété)

#: familles servies à l'écran Possession (comptes + liste séparés).
FAMILLE_PROPRIETE = {"P", "X", "U", "N"}
FAMILLE_GESTION = {"G", "Q", "Z", "S"}
# tout le reste = « autres droits » (B, E, F, D, T, V, R, W, A, K, L, H, O, J, Y…)


def rang_droit(code: str | None) -> int:
    return _RANG_DROIT.get((code or "").strip().upper(), _RANG_AUTRE)


def famille_droit(code: str | None) -> str:
    c = (code or "").strip().upper()
    if c in FAMILLE_PROPRIETE:
        return "propriete"
    if c in FAMILLE_GESTION:
        return "gestion"
    return "autres"


def _split_code(v: str | None) -> tuple[str, str]:
    """« P - Propriétaire » → ('P', 'Propriétaire'). Garde la valeur nue si pas de séparateur."""
    v = (v or "").strip()
    if " - " in v:
        c, lib = v.split(" - ", 1)
        return c.strip()[:4], lib.strip()[:80]
    return v[:4], ""


def url_2026() -> str:
    return _BASE + ATTACHMENT_2026_61_976


def _est_974(r: list[str]) -> bool:
    dep = (r[_COL["dep"]] or "").strip()
    return dep == "974" or (dep == "97" and (r[_COL["direction"]] or "").strip() == "4")


def _build_idu(insee: str, prefixe: str, section: str, nplan: str) -> str | None:
    section = (section or "").strip()
    nplan = (nplan or "").strip()
    if not section or not nplan:
        return None
    pref = (prefixe or "").strip() or "000"
    return f"{insee}{pref.zfill(3)}{section.zfill(2)}{nplan.zfill(4)}"


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def fetch_974_csv(dest_dir: str | Path = "/tmp/dgfip_pm_2026") -> Path:
    """Télécharge le ZIP 2026 (tranche 61→976, ~149 Mo, cache disque) et extrait le CSV 974."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / f"{ATTACHMENT_2026_61_976}.zip"
    csv_path = dest / "PM_26_NB_974.csv"
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return csv_path
    if not (zip_path.exists() and zip_path.stat().st_size > 0):
        with httpx.Client(timeout=1800.0, follow_redirects=True,
                          headers={"User-Agent": constants.USER_AGENT}) as c, \
             zip_path.open("wb") as f:
            with c.stream("GET", url_2026()) as r:
                r.raise_for_status()
                for chunk in r.iter_bytes():
                    f.write(chunk)
    zf = zipfile.ZipFile(zip_path)
    membre = next((n for n in zf.namelist() if "974" in n and n.lower().endswith(".csv")), None)
    if membre is None:
        raise RuntimeError(f"2026 : aucun CSV 974 dans le ZIP ({len(zf.namelist())} membres)")
    csv_path.write_bytes(zf.read(membre))
    return csv_path


def ensure_table(session: Session) -> None:
    session.execute(text(
        "CREATE TABLE IF NOT EXISTS parcelle_pm_droit ("
        " id bigserial PRIMARY KEY,"
        " idu varchar(14) NOT NULL,"
        " siren varchar(20), denomination varchar(200), forme_juridique varchar(20),"
        " groupe smallint, groupe_label varchar(80),"
        " droit_code varchar(4), droit_label varchar(80), ordre_titulaire smallint,"
        " millesime varchar(8), source varchar(120), url_source text,"
        " date_import timestamptz NOT NULL DEFAULT now(),"
        " CONSTRAINT uq_pm_droit UNIQUE (millesime, idu, siren, droit_code))"))
    session.execute(text("CREATE INDEX IF NOT EXISTS ix_pm_droit_idu ON parcelle_pm_droit(idu)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS ix_pm_droit_siren ON parcelle_pm_droit(siren)"))
    session.commit()


def _sniff_header(txt: str) -> list[str]:
    header = next(csv.reader(io.StringIO(txt), delimiter=";"))
    if len(header) != _NB_COLONNES_ATTENDU:
        raise RuntimeError(f"{len(header)} colonnes (≠ {_NB_COLONNES_ATTENDU}) — schéma divergent : "
                           f"{header}")
    return header


def ingest_droits(session: Session, csv_path: str | Path, millesime: str = "2026",
                  log=print) -> dict:
    """Charge 974 ENTIER → `parcelle_pm_droit`, TOUS titulaires et TOUS droits conservés.
    Dédoublonnage par (idu, siren, droit_code) seulement (les répétitions de SUF sont fusionnées,
    les droits et titulaires distincts sont GARDÉS). `ordre_titulaire` = rang de priorité du droit
    sur la parcelle (1 = principal). Idempotent : purge du millésime puis réinsertion."""
    ensure_table(session)
    txt = _decode(Path(csv_path).read_bytes())
    _sniff_header(txt)
    session.execute(text("DELETE FROM parcelle_pm_droit WHERE millesime = :m"), {"m": millesime})
    reader = csv.reader(io.StringIO(txt), delimiter=";")
    next(reader, None)
    seen: set[tuple[str, str, str]] = set()
    lignes = {}  # idu -> list of dict (pour calcul ordre_titulaire par parcelle)
    n_lignes = 0
    for r in reader:
        if len(r) <= _COL["denomination"] or not _est_974(r):
            continue
        n_lignes += 1
        insee = "97" + (r[_COL["commune"]] or "").strip().zfill(3)
        idu = _build_idu(insee, r[_COL["prefixe"]], r[_COL["section"]], r[_COL["nplan"]])
        if not idu:
            continue
        siren = (r[_COL["siren"]] or "").strip()[:20]
        droit_code, droit_label = _split_code(r[_COL["droit"]])
        key = (idu, siren, droit_code)
        if key in seen:
            continue
        seen.add(key)
        groupe_raw = (r[_COL["groupe"]] or "").strip()
        groupe = int(groupe_raw[0]) if groupe_raw[:1].isdigit() else None
        groupe_label = groupe_raw.split(" - ", 1)[-1].strip() if " - " in groupe_raw else groupe_raw
        lignes.setdefault(idu, []).append({
            "idu": idu, "siren": siren, "droit_code": droit_code, "droit_label": droit_label,
            "groupe": groupe, "groupe_label": groupe_label[:80],
            "forme": (r[_COL["forme"]] or "").strip()[:20],
            "denomination": (r[_COL["denomination"]] or "").strip()[:200]})

    batch: list[dict] = []

    def flush():
        if batch:
            session.execute(text(
                """INSERT INTO parcelle_pm_droit
                     (idu, siren, denomination, forme_juridique, groupe, groupe_label,
                      droit_code, droit_label, ordre_titulaire, millesime, source, url_source)
                   VALUES (:idu,:s,:d,:f,:g,:gl,:dc,:dl,:ord,:m,:src,:url)"""), batch)
            batch.clear()

    for idu, lst in lignes.items():
        # rang de priorité par parcelle : (rang du droit, groupe, siren numérique d'abord)
        ordre = {id(x): i + 1 for i, x in enumerate(sorted(
            lst, key=lambda x: (rang_droit(x["droit_code"]), x["groupe"] if x["groupe"] is not None
                                else 99, 0 if (x["siren"] or "").isdigit() else 1, x["siren"] or "")))}
        for x in lst:
            batch.append({"idu": idu, "s": x["siren"], "d": x["denomination"], "f": x["forme"],
                          "g": x["groupe"], "gl": x["groupe_label"], "dc": x["droit_code"],
                          "dl": x["droit_label"], "ord": ordre[id(x)], "m": millesime,
                          "src": SOURCE, "url": url_2026()})
            if len(batch) >= 5000:
                flush()
    flush()
    session.commit()
    n_droits = sum(len(v) for v in lignes.values())
    log(f"parcelle_pm_droit {millesime} : {n_lignes} lignes 974 → {len(lignes)} parcelles, "
        f"{n_droits} (parcelle,titulaire,droit) distincts")
    return {"millesime": millesime, "lignes_csv": n_lignes, "parcelles": len(lignes),
            "droits": n_droits}


def archive_2025_courant(session: Session, log=print) -> int:
    """Condition 1 : AVANT tout écrasement, archive la situation 2025 SERVIE (table de prod
    `parcelle_personne_morale`) dans `pm_proprietaires_millesimes` (millesime 2025), pour que la
    timeline des changements de propriétaires (Communes) garde 2025. Idempotent (purge 2025 puis
    ré-insertion depuis la table servie). Ne touche PAS parcelle_personne_morale."""
    session.execute(text("DELETE FROM pm_proprietaires_millesimes WHERE millesime = 2025"))
    n = session.execute(text(
        """INSERT INTO pm_proprietaires_millesimes
             (millesime, idu, groupe, groupe_label, forme_juridique, denomination, siren, url_source)
           SELECT 2025, idu, groupe, groupe_label, forme_juridique, denomination, siren, url_source
           FROM parcelle_personne_morale""")).rowcount
    session.commit()
    log(f"archive 2025 → pm_proprietaires_millesimes : {n} parcelles")
    return n


def recompute_principal(session: Session, millesime: str = "2026", log=print) -> dict:
    """FLIP (à exécuter sous fenêtre contrôlée) : recalcule `parcelle_personne_morale` = TITULAIRE
    PRINCIPAL de chaque parcelle (ordre_titulaire = 1 dans parcelle_pm_droit), au millésime donné.
    Conserve l'invariante « une ligne par idu » (garde-fou bascule_gardes vert) et ajoute
    droit_code/droit_label du principal (colonnes nullable, additives).

    INJECTION-SOLIDE — la table servie n'est JAMAIS vidée à vif : on passe par `remplacer_servie`
    (staging LIKE servie remplie, contrôles comptes/doublons, SWAP ATOMIQUE dans la transaction →
    les lecteurs ne voient jamais une table à moitié remplie ; refus = table servie intacte)."""
    from .injection_sure import remplacer_servie

    def preparer(s):
        s.execute(text("ALTER TABLE parcelle_personne_morale ADD COLUMN IF NOT EXISTS droit_code varchar(4)"))
        s.execute(text("ALTER TABLE parcelle_personne_morale ADD COLUMN IF NOT EXISTS droit_label varchar(80)"))

    def charger_staging(s, staging):
        s.execute(text(
            f'INSERT INTO "{staging}" (idu, groupe, groupe_label, forme_juridique, denomination, '
            " siren, droit_code, droit_label, millesime, source, url_source, date_import) "
            "SELECT idu, groupe, groupe_label, forme_juridique, denomination, siren, droit_code, "
            "       droit_label, millesime, source, url_source, now() "
            "FROM parcelle_pm_droit WHERE millesime = :m AND ordre_titulaire = 1"), {"m": millesime})

    remplacer_servie(session, table="parcelle_personne_morale", charger_staging=charger_staging,
                     preparer=preparer, a_geometrie=False, dedup_cols=["idu"], log=log)
    session.commit()
    n = int(session.execute(text("SELECT count(*) FROM parcelle_personne_morale")).scalar() or 0)
    log(f"recompute principal {millesime} : {n} parcelles (1 ligne/idu)")
    return {"millesime": millesime, "parcelles": n}
