"""INJECTION-SOLIDE-2 — la GARDE : aucune ingestion ne doit remplacer une table SERVIE « à vif ».

Le mandat : « un test refuse toute nouvelle ingestion qui écrirait directement dans une table servie ».
Ici « écrire directement » = le REMPLACEMENT EN PLACE d'une table servie — `TRUNCATE <servie>` ou
`DELETE FROM <servie>` SANS `WHERE` — au lieu de passer par `injection_sure` (staging + contrôles +
swap atomique + retour arrière). Ces deux motifs sont exactement le « vider puis recharger » qui, en
cas de livraison vide / à moitié / hors territoire, laisse la table servie cassée jusqu'au lendemain.

Le scanner lit chaque module d'ingestion, EXTRAIT LES SQL LITTÉRAUX passés à `text(...)` (donc ignore
les docstrings, commentaires et la prose) et repère ces deux motifs sur une table non temporaire.

- Une ingestion CONVERTIE à `injection_sure` n'a plus de `TRUNCATE`/`DELETE`-sans-`WHERE` : son
  remplacement se fait dans `injection_sure` (exclu du scan), via une STAGING. Elle DISPARAÎT du scan.
- Les motifs restants doivent être DÉCLARÉS dans `DETTE` (héritage à convertir, avec raison) ou
  `EXCLUS` (table non servie au client : démo, snapshot de revue interne). TOUT motif NON déclaré →
  VIOLATION. Donc une ingestion NEUVE qui ferait `TRUNCATE`/`DELETE` à vif échoue au test, tout de
  suite. C'est un cliquet : on ne régresse pas, et la dette est explicite et bornée.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

#: préfixes/suffixes des tables de TRAVAIL (jamais servies) — remplacer l'une d'elles est bénin.
_TEMP = ("tmp", "tmp_", "_", "zzz", "stg_")
_TEMP_SUFFIXES = ("__inj_staging", "__rebuild", "_staging", "_tmp")


def _est_temporaire(table: str) -> bool:
    t = table.strip().strip('"').lower()
    if not t or "{" in t:                      # placeholder f-string (ex. "{staging}") → travail
        return True
    if t.endswith(_TEMP_SUFFIXES):
        return True
    return t.startswith(("tmp", "zzz", "stg_", "_"))


_TRUNCATE = re.compile(
    r'\bTRUNCATE\s+(?:TABLE\s+)?"?([a-z][a-z0-9_]{2,})"?\s*(?:;|$|\bRESTART\b|\bCASCADE\b|")', re.I)
_DELETE = re.compile(r'\bDELETE\s+FROM\s+"?([a-z][a-z0-9_]{2,})"?', re.I)


@dataclass(frozen=True)
class Site:
    module: str          # nom de fichier (ex. "anc.py")
    operation: str       # "TRUNCATE" | "DELETE-sans-WHERE"
    table: str
    ligne: int

    def cle(self) -> tuple[str, str]:
        return (self.module, self.table)


def _sql_litteraux(arbre: ast.AST):
    """Rend (ligne, sql) pour chaque littéral chaîne passé à `text(...)` (concaténations `+` et parties
    littérales de f-strings incluses ; les `{…}` d'une f-string sont ignorés — ils ne portent pas de
    nom de table servie). Les docstrings/commentaires ne sont JAMAIS des arguments de `text(...)`."""
    def _litteral(n: ast.AST) -> str:
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return n.value
        if isinstance(n, ast.JoinedStr):              # f-string : garder les morceaux littéraux
            return "".join(p.value for p in n.values
                           if isinstance(p, ast.Constant) and isinstance(p.value, str))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return _litteral(n.left) + " " + _litteral(n.right)
        return ""

    for node in ast.walk(arbre):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        nom = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if nom != "text" or not node.args:
            continue
        sql = _litteral(node.args[0])
        if sql:
            yield node.lineno, sql


def _sites_d_un_sql(module: str, ligne: int, sql: str) -> list[Site]:
    out: list[Site] = []
    for m in _TRUNCATE.finditer(sql):
        if not _est_temporaire(m.group(1)):
            out.append(Site(module, "TRUNCATE", m.group(1).lower(), ligne))
    for m in _DELETE.finditer(sql):
        table = m.group(1)
        if _est_temporaire(table):
            continue
        # SANS WHERE dans le MÊME ordre (jusqu'au prochain ';' ou la fin) → remplacement en place.
        reste = sql[m.end():]
        ordre = reste.split(";", 1)[0]
        if not re.search(r'\bWHERE\b', ordre, re.I):
            out.append(Site(module, "DELETE-sans-WHERE", table.lower(), ligne))
    return out


def scanner(racine: Path | str) -> list[Site]:
    """Tous les remplacements-en-place de table servie dans les modules d'ingestion (`injection_sure`
    et `garde_injection` exclus : l'un EST le chemin sûr, l'autre est le garde)."""
    dossier = Path(racine)
    sites: list[Site] = []
    for f in sorted(dossier.glob("*.py")):
        if f.name in ("injection_sure.py", "garde_injection.py", "_rebuild.py", "__init__.py"):
            continue
        try:
            arbre = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for ligne, sql in _sql_litteraux(arbre):
            sites.extend(_sites_d_un_sql(f.name, ligne, sql))
    # dédoublonne par (module, opération, table)
    vus, uniques = set(), []
    for s in sites:
        k = (s.module, s.operation, s.table)
        if k not in vus:
            vus.add(k)
            uniques.append(s)
    return uniques


def scanner_texte(module: str, texte: str) -> list[Site]:
    """Scanne une SOURCE Python en mémoire (pour le test positif : « un nouvel offenseur est pris »)."""
    sites: list[Site] = []
    for ligne, sql in _sql_litteraux(ast.parse(texte)):
        sites.extend(_sites_d_un_sql(module, ligne, sql))
    return sites


# ════════════════════════════════ LE REGISTRE (cliquet + dette bornée) ════════════════════════════
#
# CONVERTIES (plus aucun motif ; passent par injection_sure.remplacer_servie) — pour mémoire/liste :
MODULES_CONVERTIS = {
    "trafic_rn.py": "trafic_rn",
    "rnic.py": "rnic_coproprietes",
    "dvf_marche.py": "dvf_secteur_medianes",
    "etablissement_parcelle.py": "etablissement_parcelle",
    "surface_d.py": "surface_d_events",
    "dvf_prix_neuf.py": "dvf_prix_sortie_neuf",
    "ban_plus.py": "ban_plus_liens",
    "ocsge.py": "parcel_ocsge",
}

#: SOURCES SÛRES — noms `data_sources.name` dont l'ingestion passe par `injection_sure` (staging + swap
#: atomique + retour arrière + alerte). injection-nuit s'en sert pour annoncer, par source lancée, si
#: elle est sur le CHEMIN SÛR (un échec gardera la version servie et ouvrira une alerte) ou HÉRITÉE
#: (chemin direct, à convertir — SOLIDE-3, sous le filet de la cohérence du lendemain).
SOURCES_SURES: frozenset[str] = frozenset({
    "Trafic RN (Région Réunion — SIR)",          # trafic_rn.py (géométries)
    "RNIC — copropriétés (ANAH)",                 # rnic.py (fichier manuel)
    "BAN PLUS — lien adresse ↔ bâtiment (IGN)",   # ban_plus.py (moisson WFS)
})


def source_sur_chemin_sur(nom: str) -> bool:
    """La source `nom` est-elle injectée par le CHEMIN SÛR (`injection_sure`) ?"""
    return nom in SOURCES_SURES


#: EXCLUS : la table n'est PAS servie au client (démo/test, ou snapshot de revue interne). Remplacer
#: en place y est sans danger pour la donnée servie.
EXCLUS: dict[tuple[str, str], str] = {
    ("demo_saint_paul.py", "*"): "jeu de DÉMO (reset_demo) — données fabriquées, jamais servies au client",
    ("division_or.py", "division_or_revue_snapshot"):
        "snapshot de REVUE interne (workflow Vic), pas une table servie ; préservé si rien à "
        "photographier (garde `if not src`)",
}

#: DETTE assumée : remplacement-en-place d'une table SERVIE hérité, à convertir à injection_sure
#: (INJECTION-SOLIDE-3). Le garde les TOLÈRE (cliquet : pas de régression) mais INTERDIT tout NOUVEAU
#: motif non déclaré. Chaque entrée dit pourquoi elle n'a pas été convertie dans CE mandat.
_RAISON_DELETE_DERIVEE = ("remplacement-en-place hérité (DELETE sans WHERE) d'une table dérivée/"
                          "référentielle ; à router via injection_sure.remplacer_servie (SOLIDE-3)")
DETTE: dict[tuple[str, str], str] = {
    ("anc.py", "anc_maille_taux"): _RAISON_DELETE_DERIVEE,
    ("arcep_fibre.py", "arcep_immeubles"): _RAISON_DELETE_DERIVEE + " — géométrie, moissonnée",
    ("azi_tri.py", "azi_communes"): _RAISON_DELETE_DERIVEE,
    ("ban_adresses.py", "adresse_parcelles"): _RAISON_DELETE_DERIVEE,
    ("ban_adresses.py", "adresses"): _RAISON_DELETE_DERIVEE + " — gros volume, moissonnée",
    ("bd_nyme.py", "lieux_dits"): _RAISON_DELETE_DERIVEE,
    ("bdnb.py", "*"): "BDNB RETIRÉE (DEPLOY-TABLEAU-1) — DROP+to_sql dormant, source inactive",
    ("catnat.py", "catnat_arretes"): _RAISON_DELETE_DERIVEE,
    ("dfi.py", "dfi_filiation"): _RAISON_DELETE_DERIVEE,
    ("mobpro.py", "mobpro_commune"): _RAISON_DELETE_DERIVEE,
    ("ocsge.py", "ocsge_evolution"): _RAISON_DELETE_DERIVEE + " — géométrie (parcel_ocsge converti)",
    ("ort.py", "commune_ort"): _RAISON_DELETE_DERIVEE,
    ("piscines_fusion.py", "piscines"): _RAISON_DELETE_DERIVEE + " — géométrie, fusion",
    ("rnb.py", "rnb_rattachement_bdtopo"): _RAISON_DELETE_DERIVEE,
    ("rp_logement.py", "rp_logement_commune"): _RAISON_DELETE_DERIVEE,
    ("sirene_etablissements.py", "sirene_etablissements"): _RAISON_DELETE_DERIVEE + " — moissonnée",
    ("solaire.py", "solar_grid"): _RAISON_DELETE_DERIVEE + " — géométrie",
    ("taxe_amenagement_delta.py", "taxe_amenagement_taux"): _RAISON_DELETE_DERIVEE,
    ("taxe_amenagement_delta.py", "taxe_amenagement_secteur"): _RAISON_DELETE_DERIVEE,
}


def _declare(site: Site) -> bool:
    """Un site est DÉCLARÉ s'il est dans EXCLUS ou DETTE (clé exacte ou joker module `*`)."""
    for registre in (EXCLUS, DETTE):
        if (site.module, site.table) in registre or (site.module, "*") in registre:
            return True
    return False


def violations(racine: Path | str) -> list[Site]:
    """Les remplacements-en-place de table servie NI convertis NI déclarés (dette/exclu) → à refuser.
    Un module CONVERTI qui ré-introduirait un `TRUNCATE`/`DELETE`-à-vif retomberait ici (régression)."""
    return [s for s in scanner(racine) if not _declare(s)]
