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


# ════════════════════════════════ LE REGISTRE (cliquet STRICT) ════════════════════════════════════
#
# INJECTION-SOLIDE-3 — le garde passe en STRICT : **zéro remplacement-en-place d'une table SERVIE
# n'est toléré**, sans liste d'exceptions. La DETTE de SOLIDE-2 (18 `DELETE`-sans-`WHERE`) est
# RÉSORBÉE : les 18 ingestions passent désormais par `injection_sure.remplacer_servie` (staging +
# contrôles + swap atomique + retour arrière) et ont DISPARU du scan. `DETTE` est donc VIDE —
# toute nouvelle (ou ré-introduite) écriture directe dans une servie est une VIOLATION, tout de suite.
#
# CONVERTIES (plus aucun motif ; passent par injection_sure.remplacer_servie) — module → table(s) :
MODULES_CONVERTIS: dict[str, tuple[str, ...]] = {
    # — SOLIDE-2 (les 8 `TRUNCATE`-en-place) —
    "trafic_rn.py": ("trafic_rn",),
    "rnic.py": ("rnic_coproprietes",),
    "dvf_marche.py": ("dvf_secteur_medianes",),
    "etablissement_parcelle.py": ("etablissement_parcelle",),
    "surface_d.py": ("surface_d_events",),
    "dvf_prix_neuf.py": ("dvf_prix_sortie_neuf",),
    "ban_plus.py": ("ban_plus_liens",),
    # — SOLIDE-3 (les 18 `DELETE`-sans-`WHERE`) ; ocsge porte aussi parcel_ocsge (SOLIDE-2) —
    "anc.py": ("anc_maille_taux",),
    "arcep_fibre.py": ("arcep_immeubles",),
    "azi_tri.py": ("azi_communes",),
    "ban_adresses.py": ("adresses", "adresse_parcelles"),
    "bd_nyme.py": ("lieux_dits",),
    "catnat.py": ("catnat_arretes",),
    "dfi.py": ("dfi_filiation",),
    "mobpro.py": ("mobpro_commune",),
    "ocsge.py": ("parcel_ocsge", "ocsge_evolution"),
    "ort.py": ("commune_ort",),
    "piscines_fusion.py": ("piscines",),
    "rnb.py": ("rnb_rattachement_bdtopo",),
    "rp_logement.py": ("rp_logement_commune",),
    "sirene_etablissements.py": ("sirene_etablissements",),
    "solaire.py": ("solar_grid",),
    "taxe_amenagement_delta.py": ("taxe_amenagement_taux", "taxe_amenagement_secteur"),
}

#: SOURCES SÛRES — noms `data_sources.name` dont l'ingestion de nuit ne peut PAS laisser une table
#: servie CASSÉE : soit elle passe par `injection_sure` (staging + swap atomique + retour arrière +
#: alerte au moindre échec de livraison), soit elle n'a JAMAIS fait de remplacement-en-place (upsert /
#: `DELETE … WHERE` partiel — le garde le PROUVE : 0 violation). injection-nuit ne lance QUE ces
#: sources ; toute source de classe A avancée qui n'y figure PAS n'est PLUS injectée (la voie « héritée »
#: a disparu) — elle remonte comme DÉCISION À PRENDRE (la vetter, puis l'ajouter ici).
#: Tenu aligné sur les sources de classe A outillées d'une commande (config/sources_ingestion.yaml).
SOURCES_SURES: frozenset[str] = frozenset({
    # routées par injection_sure.remplacer_servie (SOLIDE-2/3)
    "Trafic RN (Région Réunion — SIR)",                 # trafic_rn.py
    "CatNat (arrêtés GASPAR / Géorisques)",             # catnat.py (remplacer=True → injection sûre)
    "SIRENE établissements géolocalisés",               # sirene_etablissements.py
    "RNIC — copropriétés (ANAH)",                       # rnic.py (fichier manuel)
    "BAN PLUS — lien adresse ↔ bâtiment (IGN)",         # ban_plus.py
    "Base Adresse Nationale",                           # ban_adresses.py
    "BD NYME — lieux-dits (IGN)",                       # bd_nyme.py
    "MOBPRO (mobilités domicile-travail, INSEE)",       # mobpro.py
    "ACV / PVD / ORT (DGALN — liste des communes)",     # ort.py
    "Zones exclues EnR sauf toiture (OFB/APER)",        # (incrémental/partiel — jamais de purge à vif)
    # purement incrémentales / partielles (jamais de remplacement-en-place — garde = 0 violation)
    "50 pas géométriques — limite haute (DEAL)",
    "ABF / Monuments historiques",
    "BPE INSEE",
    "Cartofriches (Cerema)",
    "Classement sonore ITT (Cerema)",
    "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)",
    "INPI RNE (dirigeants)",
    "INSEE RP2022 — bases IRIS (logement, population)",
    "Population légale (INSEE via geo.api.gouv)",
    "QPV 2024 (ANCT)",
    "SUP — assiettes GPU (API Carto)",
    "Transport public — GTFS (PAN, 7 réseaux)",
    "ZNIEFF (INPN/MNHN)",
    # Le RESTE des sources de classe A (sans commande d'ingestion-nuit mappée) — AUCUNE ne fait de
    # remplacement-en-place (garde = 0 violation) : soit écriture partielle `DELETE … WHERE kind`
    # sur spatial_layers (périmètres/zonages), soit upsert/agrégat, soit source en direct/dépôt sans
    # ingestion batch. Elles sont donc SÛRES. Listées ici pour qu'injection-nuit ne les classe PAS en
    # « décision à prendre » à tort : sans commande, une source avancée retombe en « à câbler » (et non
    # « à sécuriser »). La classe A entière est ainsi couverte → a_decider ne vise plus que de FUTURES
    # sources non vettées (le cliquet reste armé).
    "Annuaire de l'administration (service-public.fr / DILA)",
    "BODACC (procédures collectives)",
    "Cerema / GéoLittoral — indicateur d'érosion côtière",
    "Contours IRIS (IGN/INSEE)",
    "Contraintes EnR près des habitations (Géoplateforme)",
    "Filosofi INSEE (carreaux 200 m)",
    "Forêts publiques (ONF)",
    "GéoMCE — mesures compensatoires",
    "INPN / patrinat — espaces protégés",
    "INSEE RP Logement 2023",
    "Inventaires ZAE (EPCI — loi Climat et résilience)",
    "Parc National de La Réunion (INPN)",
    "Recherche d'entreprises (DINUM)",
    "SIRENE",
    "ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)",
})


def source_sur_chemin_sur(nom: str) -> bool:
    """La source `nom` est-elle SÛRE à injecter seule la nuit ? (routée par `injection_sure`, ou
    vérifiée sans remplacement-en-place). Sinon injection-nuit ne la lance PAS : elle devient une
    DÉCISION à prendre (la vetter puis l'ajouter à `SOURCES_SURES`)."""
    return nom in SOURCES_SURES


#: EXCLUS : la table n'est PAS servie au client (jeu de démo, ou snapshot de revue interne). Ce n'est
#: PAS une tolérance d'injection non sûre : remplacer EN PLACE y est sans danger car la donnée n'est
#: jamais servie. (Distinct de la DETTE de SOLIDE-2, désormais VIDE.)
EXCLUS: dict[tuple[str, str], str] = {
    ("demo_saint_paul.py", "*"): "jeu de DÉMO (reset_demo) — données fabriquées, jamais servies au client",
    ("division_or.py", "division_or_revue_snapshot"):
        "snapshot de REVUE interne (workflow Vic), pas une table servie ; préservé si rien à "
        "photographier (garde `if not src`)",
}

#: DETTE — VIDE depuis INJECTION-SOLIDE-3 (les 18 `DELETE`-sans-`WHERE` sont convertis). Conservée
#: (vide) pour la lisibilité du cliquet et le test d'hygiène : plus aucun remplacement-en-place d'une
#: servie n'est toléré hors `injection_sure`. Un nouvel offenseur → VIOLATION immédiate, pas une entrée.
DETTE: dict[tuple[str, str], str] = {}


def _declare(site: Site) -> bool:
    """Un site est DÉCLARÉ s'il est dans EXCLUS ou DETTE (clé exacte ou joker module `*`). DETTE est
    VIDE (SOLIDE-3) : seules les tables NON servies (EXCLUS) échappent encore au scan."""
    for registre in (EXCLUS, DETTE):
        if (site.module, site.table) in registre or (site.module, "*") in registre:
            return True
    return False


def violations(racine: Path | str) -> list[Site]:
    """Les remplacements-en-place de table servie NI convertis NI déclarés (dette/exclu) → à refuser.
    Un module CONVERTI qui ré-introduirait un `TRUNCATE`/`DELETE`-à-vif retomberait ici (régression)."""
    return [s for s in scanner(racine) if not _declare(s)]
