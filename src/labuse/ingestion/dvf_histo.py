"""M3.5 LOT A — profondeur historique DVF 2014-2020 (974) → table dvf_mutations_histo.

Les millésimes géo-DVF ≤ 2020 sont RETIRÉS de la distribution officielle (fenêtre
glissante 5 ans DGFiP) mais les publications semestrielles brutes « Demandes de valeurs
foncières » restent archivées sur le mirror communautaire cquest (data.cquest.org/dgfip_dvf,
reconnaissance M3.5 lot A — voir reports/m35-histo/RECONNAISSANCE.md). Ce module peuple la
table SÉPARÉE `dvf_mutations_histo` ; la table de prod `dvf_mutations_parcelle` (2021-2025)
reste STRICTEMENT INTACTE et fait foi : toute année ≥ 2021 est REFUSÉE ici.

Harmonisation brut DGFiP (43 colonnes pipe, UTF-8 sur le mirror cquest — repli latin-1,
dates JJ/MM/AAAA, décimales à virgule) → schéma prod, champ par champ :
  · id_parcelle : '974' + commune zfill(2) + préfixe zfill(3) + section zfill(2)
    + n° plan zfill(4) — même convention IDU que pm_millesimes ;
  · id_mutation : le brut n'a PAS d'identifiant d'acte → reconstruit par la même
    heuristique que geo-DVF Etalab : regroupement (date, n° disposition, valeur),
    séquence par millésime, préfixe 'H' (ex. H2014-000042) — jamais de collision prod ;
  · nature_culture : code → libellé (table officielle DGFiP « tables-cultures »,
    identique aux libellés servis par geo-DVF, donc à la prod) ;
  · longitude/latitude : NULL — les archives brutes ne sont pas géolocalisées ;
  · provenance : source_archive (URL exacte) + millesime_source (édition AAAAMM).

Tout écart d'entête est LEVÉ, jamais deviné (même règle que pm_millesimes).
Idempotent : DELETE du millésime puis ré-insertion.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE = "DGFiP — Demandes de valeurs foncières (publications archivées, mirror cquest)"

#: entêtes EXACTES des publications brutes — 43 colonnes, positions identiques sur
#: toutes les éditions utilisées ; SEULE la colonne 1 (vide, non exploitée) diffère :
#: « Code service CH » (éditions ≤ 202110) → « Identifiant de document » (≥ 202204).
#: C'est l'unique évolution de format constatée (diff champ à champ, lot A).
_ENTETE_ATTENDUE = (
    "Code service CH|Reference document|1 Articles CGI|2 Articles CGI|3 Articles CGI|"
    "4 Articles CGI|5 Articles CGI|No disposition|Date mutation|Nature mutation|"
    "Valeur fonciere|No voie|B/T/Q|Type de voie|Code voie|Voie|Code postal|Commune|"
    "Code departement|Code commune|Prefixe de section|Section|No plan|No Volume|"
    "1er lot|Surface Carrez du 1er lot|2eme lot|Surface Carrez du 2eme lot|3eme lot|"
    "Surface Carrez du 3eme lot|4eme lot|Surface Carrez du 4eme lot|5eme lot|"
    "Surface Carrez du 5eme lot|Nombre de lots|Code type local|Type local|"
    "Identifiant local|Surface reelle bati|Nombre pieces principales|Nature culture|"
    "Nature culture speciale|Surface terrain")

_ENTETES_VALIDES = (
    _ENTETE_ATTENDUE,
    "Identifiant de document|" + _ENTETE_ATTENDUE.split("|", 1)[1],
)

#: positions 0-based dans la ligne brute
_COL = {"disposition": 7, "date": 8, "nature": 9, "valeur": 10, "dep": 18,
        "commune": 19, "prefixe": 20, "section": 21, "nplan": 22,
        "type_local": 36, "srb": 38, "culture": 40, "terrain": 42}

#: table officielle DGFiP « nature de culture » code → libellé (mêmes libellés que
#: geo-DVF/prod ; source : tables-de-reference-nature-de-culture, mirror cquest).
CULTURES = {
    "AB": "terrains a bâtir", "AG": "terrains d'agrément", "B": "bois",
    "BF": "futaies feuillues", "BM": "futaies mixtes", "BO": "oseraies",
    "BP": "peupleraies", "BR": "futaies résineuses", "BS": "taillis sous futaie",
    "BT": "taillis simples", "CA": "carrières", "CH": "chemin de fer", "E": "eaux",
    "J": "jardins", "L": "landes", "LB": "landes boisées", "P": "prés",
    "PA": "pâtures", "PC": "pacages", "PE": "prés d'embouche", "PH": "herbages",
    "PP": "prés plantes", "S": "sols", "T": "terres", "TP": "terres plantées",
    "VE": "vergers", "VI": "vignes",
}

DDL = text(
    """
    CREATE TABLE IF NOT EXISTS dvf_mutations_histo (
      id                  bigserial PRIMARY KEY,
      id_mutation         text        NOT NULL,   -- 'H<annee>-<seq>' (reconstruit, cf. docstring)
      date_mutation       date,
      nature_mutation     text,
      valeur_fonciere     double precision,
      code_commune        text,
      id_parcelle         varchar(14) NOT NULL,
      type_local          text,
      surface_reelle_bati double precision,
      surface_terrain     double precision,
      nature_culture      text,
      longitude           double precision,       -- NULL : archives brutes non géolocalisées
      latitude            double precision,
      millesime           smallint    NOT NULL,   -- année des mutations (aligné prod)
      source_archive      text        NOT NULL,   -- URL exacte de l'archive ingérée
      millesime_source    integer     NOT NULL    -- édition DGFiP AAAAMM (ex. 202104)
    )""")

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_dvfh_parcelle ON dvf_mutations_histo (id_parcelle)",
    "CREATE INDEX IF NOT EXISTS ix_dvfh_date ON dvf_mutations_histo (date_mutation)",
    "CREATE INDEX IF NOT EXISTS ix_dvfh_millesime ON dvf_mutations_histo (millesime)",
)


def ensure_table(engine) -> None:
    with engine.begin() as c:
        c.execute(DDL)
        for ddl in _INDEXES:
            c.execute(text(ddl))


def _num(v: str) -> float | None:
    v = (v or "").strip()
    return float(v.replace(",", ".")) if v else None


def _parse_date(v: str) -> date:
    j, m, a = v.strip().split("/")
    return date(int(a), int(m), int(j))


def parse_fichier(path: str | Path, annee: int) -> tuple[list[dict], dict]:
    """Fichier brut (pré-filtré 974 ou national) → lignes harmonisées du millésime.

    Contrôles : entête strictement conforme (levée sinon), département 974 seul,
    date dans l'année du millésime (les lignes hors année sont écartées et comptées —
    jamais réaffectées à un autre millésime)."""
    lignes: list[dict] = []
    hors_annee = 0
    raw = Path(path).read_bytes()
    try:
        contenu = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        contenu = raw.decode("latin-1")
    with io.StringIO(contenu) as f:
        entete = f.readline().rstrip("\n\r")
        if entete not in _ENTETES_VALIDES:
            raise RuntimeError(
                f"millésime {annee} : entête divergente du format ≥ 2019 — schéma à "
                f"documenter avant ingestion, jamais deviné. Entête : {entete[:200]}…")
        for raw in f:
            r = raw.rstrip("\n\r").split("|")
            if len(r) != 43 or (r[_COL["dep"]] or "").strip() != "974":
                continue
            d = _parse_date(r[_COL["date"]])
            if d.year != annee:
                hors_annee += 1
                continue
            insee = "974" + (r[_COL["commune"]] or "").strip().zfill(2)
            pref = (r[_COL["prefixe"]] or "").strip() or "000"
            section = (r[_COL["section"]] or "").strip()
            nplan = (r[_COL["nplan"]] or "").strip()
            if not section or not nplan:
                continue
            culture = (r[_COL["culture"]] or "").strip()
            lignes.append({
                "cle_mutation": (d, (r[_COL["disposition"]] or "").strip(),
                                 _num(r[_COL["valeur"]])),
                "date_mutation": d,
                "nature_mutation": (r[_COL["nature"]] or "").strip() or None,
                "valeur_fonciere": _num(r[_COL["valeur"]]),
                "code_commune": insee,
                "id_parcelle": f"{insee}{pref.zfill(3)}{section.zfill(2)}{nplan.zfill(4)}",
                "type_local": (r[_COL["type_local"]] or "").strip() or None,
                "surface_reelle_bati": _num(r[_COL["srb"]]),
                "surface_terrain": _num(r[_COL["terrain"]]),
                "nature_culture": CULTURES.get(culture) if culture else None,
            })
    return lignes, {"lignes": len(lignes), "hors_annee": hors_annee}


def _assigner_id_mutation(lignes: list[dict], annee: int) -> int:
    """Heuristique geo-DVF : une mutation = (date, n° disposition, valeur)."""
    ids: dict[tuple, str] = {}
    for lg in sorted(lignes, key=lambda x: (x["date_mutation"], str(x["cle_mutation"]))):
        cle = lg.pop("cle_mutation")
        if cle not in ids:
            ids[cle] = f"H{annee}-{len(ids) + 1:06d}"
        lg["id_mutation"] = ids[cle]
    return len(ids)


def ingest_millesime(session: Session, annee: int, path: str | Path,
                     source_archive: str, millesime_source: int, log=print) -> dict:
    """Ingestion d'un millésime archive → dvf_mutations_histo (idempotent).

    Garde-fou : les années ≥ 2021 sont en prod (dvf_mutations_parcelle) et REFUSÉES."""
    if annee >= 2021:
        raise ValueError(f"millésime {annee} ≥ 2021 : la prod fait foi, ingestion refusée")
    lignes, stats = parse_fichier(path, annee)
    n_mutations = _assigner_id_mutation(lignes, annee)
    session.execute(text("DELETE FROM dvf_mutations_histo WHERE millesime = :m"),
                    {"m": annee})
    for i in range(0, len(lignes), 5000):
        session.execute(text(
            """INSERT INTO dvf_mutations_histo
                 (id_mutation, date_mutation, nature_mutation, valeur_fonciere,
                  code_commune, id_parcelle, type_local, surface_reelle_bati,
                  surface_terrain, nature_culture, millesime, source_archive,
                  millesime_source)
               VALUES (:id_mutation, :date_mutation, :nature_mutation, :valeur_fonciere,
                       :code_commune, :id_parcelle, :type_local, :surface_reelle_bati,
                       :surface_terrain, :nature_culture, :millesime, :source_archive,
                       :millesime_source)"""),
            [{**lg, "millesime": annee, "source_archive": source_archive,
              "millesime_source": millesime_source} for lg in lignes[i:i + 5000]])
    session.commit()
    log(f"millésime {annee} (éd. {millesime_source}) : {stats['lignes']} lignes 974, "
        f"{n_mutations} mutations, {stats['hors_annee']} hors année écartées")
    return {"annee": annee, **stats, "mutations": n_mutations}
