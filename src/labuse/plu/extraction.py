"""PLU-CALIBRAGE-1 lot 3 — L'AGENT D'EXTRACTION DES RÈGLES CHIFFRÉES.

`labuse plu extraire <insee>` : télécharge le règlement OPPOSABLE depuis le GPU (URL + md5
gravés dans `config/plu_destinations/<insee>_*.yaml`), le découpe par CHAPITRE DE ZONE, et pour
chaque zone U demande à l'agent les cinq rubriques (hauteur · emprise_sol · retraits ·
stationnement · mixite). L'agent n'écrit QUE ce que le texte dit :

  · valeur lue     → {valeur…, article, page_pdf, citation, statut: propose} ;
  · silence prouvé → {absent: true, article, page_pdf, citation, statut: propose} ;
  · rien trouvé    → la feuille est OMISE (jamais devinée).

Anti-invention (garde dure, `_valider_regles`) : une feuille SANS citation (ou sans article,
ou sans page_pdf) est REJETÉE — jamais écrite. Mixité : cherchée dans la zone ET les
dispositions générales (les OAP sont une pièce GPU distincte, non fournie dans ce pilote).

Zones A et N : HORS PÉRIMÈTRE (mandat pilote Saint-Denis). Le branchement dans le calcul de
capacité est le mandat 2 ; la revue humaine (`labuse plu revue`) tranche `propose` → `valide`.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from hashlib import md5 as _md5
from pathlib import Path

from . import destinations as D

_REGLEMENTS_DIR = D._CONFIG_DIR.parents[0] / "data" / "plu_reglements"

# ── modèle & prompt ─────────────────────────────────────────────────────────────────────────
SYSTEM = (
    "Tu es un AGENT DE CALIBRAGE de PLU. On te donne le texte du chapitre d'UNE zone d'un "
    "règlement d'urbanisme (pages marquées « [p.N] ») puis le texte des DISPOSITIONS GÉNÉRALES. "
    "Tu extrais UNIQUEMENT les règles CHIFFRÉES écrites, en cinq rubriques :\n"
    "  · hauteur : faîtage, égout, niveaux (R+n) — les trois SÉPARÉMENT ;\n"
    "  · emprise_sol : pourcentage d'emprise au sol (CES) ;\n"
    "  · retraits : par rapport aux voies, et par rapport aux limites séparatives — pour chacun "
    "la formule (texte, ex. « H/2 minimum 3 m ») et le minimum en mètres ;\n"
    "  · stationnement : par logement, par m² de surface de plancher, par typologie ;\n"
    "  · mixite : seuil de déclenchement (en logements ou en m²), quota en %, et la portée "
    "(zone / oap / dispositions_generales).\n\n"
    "RÈGLES ABSOLUES :\n"
    "1. Tu n'écris QUE ce que le texte dit. La citation est le texte EXACT, mot pour mot, entre "
    "guillemets. Rien de déduit, rien d'arrondi, rien d'inventé.\n"
    "2. Chaque feuille porte OBLIGATOIREMENT : `article` (ex. « Ud 10 »), `page_pdf` (le numéro "
    "de la balise [p.N] où tu l'as lue), `citation`. Une feuille SANS citation est INTERDITE — "
    "ne la produis pas.\n"
    "3. Si le règlement dit EXPLICITEMENT qu'une règle n'est pas fixée (« non réglementé », "
    "« non réglementée », « néant »), écris {\"absent\": true} AVEC la citation qui le prouve, "
    "l'article et la page_pdf.\n"
    "4. Si tu ne trouves NI valeur NI mention explicite d'absence, N'ÉCRIS PAS la feuille "
    "(omets-la). Ne devine jamais.\n"
    "5. Mixité : cherche dans le chapitre de zone ET dans les dispositions générales ; renseigne "
    "la portée réelle (`portee`).\n\n"
    "Réponds UNIQUEMENT par un objet JSON, sans texte autour, de la forme :\n"
    "{\n"
    '  "hauteur": {"faitage": {"m": 15, "article": "Ud 10", "page_pdf": 45, "citation": "..."},\n'
    '              "egout": {"m": 12, "article": "Ud 10", "page_pdf": 45, "citation": "..."},\n'
    '              "niveaux": {"r_plus": 3, "article": "Ud 10", "page_pdf": 45, "citation": "..."}},\n'
    '  "emprise_sol": {"ces": {"pct": 60, "article": "Ud 9", "page_pdf": 44, "citation": "..."}},\n'
    '  "retraits": {"voie": {"formule": "H/2 min 3 m", "min_m": 3, "article": "Ud 6", "page_pdf": 42, "citation": "..."},\n'
    '               "limites_separatives": {"formule": "H/2 min 3 m", "min_m": 3, "article": "Ud 7", "page_pdf": 43, "citation": "..."}},\n'
    '  "stationnement": {"par_logement": {"places": 2, "article": "Ud 12", "page_pdf": 46, "citation": "..."},\n'
    '                    "par_m2_sdp": {"places": 1, "par_m2": 25, "article": "Ud 12", "page_pdf": 46, "citation": "..."},\n'
    '                    "par_typologie": {"detail": [{"typologie": "T1-T2", "places": 1}], "article": "Ud 12", "page_pdf": 46, "citation": "..."}},\n'
    '  "mixite": {"seuil_logements": 30, "seuil_m2": null, "quota_pct": 15, "portee": "zone", "article": "Ud 2", "page_pdf": 39, "citation": "..."}\n'
    "}\n"
    "OMETS toute rubrique ou feuille non trouvée. N'ajoute aucune clé hors de ce schéma."
)

# feuilles attendues (mêmes que destinations.REGLES_RUBRIQUES ; mixite = feuille plate)
_FEUILLES = {
    "hauteur": ("faitage", "egout", "niveaux"),
    "emprise_sol": ("ces",),
    "retraits": ("voie", "limites_separatives"),
    "stationnement": ("par_logement", "par_m2_sdp", "par_typologie"),
    "mixite": (None,),   # None = la rubrique EST la feuille
}


@dataclass
class RapportZone:
    zone: str
    proposees: int = 0
    absentes: int = 0
    rejetees: list[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    secondes: float = 0.0


# ── PDF : téléchargement & découpe par zone ───────────────────────────────────────────────────

def telecharger_reglement(meta: dict, *, forcer: bool = False) -> Path:
    """Le règlement opposable, en cache local (`data/plu_reglements/`), vérifié au md5 gravé.
    urllib d'abord, `curl` en repli (certains environnements bloquent les sockets Python)."""
    url = meta.get("url")
    nom = meta.get("document") or (url.rsplit("/", 1)[-1] if url else None)
    if not url or not nom:
        raise ValueError("meta sans url/document — impossible de télécharger le règlement")
    _REGLEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _REGLEMENTS_DIR / nom
    attendu = meta.get("md5")
    if dest.is_file() and not forcer and (not attendu or _md5(dest.read_bytes(), usedforsecurity=False).hexdigest() == attendu):
        return dest
    data = None
    try:
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 (URL du GPU, gravée)
            data = r.read()
    except Exception:  # noqa: BLE001 — repli curl
        subprocess.run(["curl", "-sS", "-m", "180", "-o", str(dest), url], check=True)
        data = dest.read_bytes()
    else:
        dest.write_bytes(data)
    if attendu:
        vu = _md5(dest.read_bytes(), usedforsecurity=False).hexdigest()
        if vu != attendu:
            raise ValueError(f"md5 du règlement téléchargé ({vu}) ≠ md5 gravé ({attendu})")
    return dest


_ZONE_HDR = re.compile(r"^Zone\s+([A-Za-z0-9]+)\s*$")


def segmenter_chapitres(pdf_path: Path) -> list[tuple[str, int, int]]:
    """Découpe le PDF en chapitres de zone → [(code, page_debut, page_fin)] (pages 1-based,
    fin exclue). Repère les entêtes « Zone <Code> » ; borne les zones urbaines avant les
    dispositions générales / zones AU-A-N."""
    import fitz
    doc = fitz.open(str(pdf_path))
    debuts: list[tuple[str, int]] = []
    fin_zones = doc.page_count + 1
    for i in range(doc.page_count):
        texte = doc.load_page(i).get_text()
        for ligne in texte.splitlines():
            m = _ZONE_HDR.match(ligne.strip())
            if m:
                debuts.append((m.group(1), i + 1))
                break
        if re.search(r"TITRE\s+III\s*[–-]\s*DISPOSITIONS\s+GENERALES", texte, re.I):
            fin_zones = min(fin_zones, i + 1)
    doc.close()
    chapitres: list[tuple[str, int, int]] = []
    for idx, (code, p0) in enumerate(debuts):
        p1 = debuts[idx + 1][1] if idx + 1 < len(debuts) else fin_zones
        chapitres.append((code, p0, p1))
    return chapitres


def _pages_texte(pdf_path: Path) -> list[str]:
    import fitz
    doc = fitz.open(str(pdf_path))
    pages = [doc.load_page(i).get_text() for i in range(doc.page_count)]
    doc.close()
    return pages


def _texte_marque(pages: list[str], p0: int, p1: int) -> str:
    """Texte des pages [p0, p1) avec balises « [p.N] » (N = page PDF, pour les citations)."""
    bouts = []
    for n in range(p0, p1):
        if 1 <= n <= len(pages):
            bouts.append(f"[p.{n}]\n{pages[n - 1]}")
    return "\n".join(bouts)


def zones_u(chapitres: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """Les chapitres de zone U (commencent par U, hors AU) — A/N/AU hors périmètre."""
    return [c for c in chapitres if c[0][0] in ("U", "u") and not c[0].lower().startswith("au")]


def _texte_dispositions_generales(pages: list[str]) -> str:
    """Le texte du TITRE III — DISPOSITIONS GÉNÉRALES (mixité éventuelle) jusqu'à la fin."""
    for i, t in enumerate(pages):
        if re.search(r"TITRE\s+III\s*[–-]\s*DISPOSITIONS\s+GENERALES", t, re.I):
            return _texte_marque(pages, i + 1, len(pages) + 1)
    return ""


# ── l'agent ───────────────────────────────────────────────────────────────────────────────────

def _appel_reel(db, zone: str, texte_zone: str, texte_dg: str) -> tuple[str, int, int, str]:
    """L'appel API réel (texte du règlement en entrée, pas de web_search). Injectable en test."""
    import anthropic

    from ..ai import core
    from ..ai_models import model_for
    model = model_for("traducteur-plu")
    client = anthropic.Anthropic(timeout=180, max_retries=1)
    contenu = (f"ZONE : {zone}\n\n=== CHAPITRE DE LA ZONE {zone} ===\n{texte_zone}\n\n"
               f"=== DISPOSITIONS GÉNÉRALES (pour la mixité) ===\n{texte_dg}")
    msg = client.messages.create(
        model=model, max_tokens=2000, system=SYSTEM,
        messages=[{"role": "user", "content": contenu}])
    texte = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    tin, tout = msg.usage.input_tokens, msg.usage.output_tokens
    try:
        core._log_cost(db, "traducteur-plu", model, False, tin, tout)
    except Exception:  # noqa: BLE001 — le ledger ne bloque jamais l'agent
        pass
    return texte, tin, tout, model


def _valider_regles(brut: str) -> tuple[dict, list[str]]:
    """Parse le JSON de l'agent → bloc `regles` PROPRE. Anti-invention : toute feuille sans
    citation OU sans article OU sans page_pdf est REJETÉE (jamais écrite), avec sa raison.
    Statut forcé à `propose`. Renvoie (regles, rejets)."""
    regles: dict = {}
    rejets: list[str] = []
    m = re.search(r"\{.*\}", brut, re.S)
    if not m:
        return {}, ["sortie non-JSON (aucun objet trouvé)"]
    try:
        d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return {}, ["JSON invalide"]

    def _feuille_ok(chemin: str, leaf: dict) -> dict | None:
        if not isinstance(leaf, dict):
            rejets.append(f"{chemin} : feuille non-objet")
            return None
        manque = []
        if not str(leaf.get("citation") or "").strip():
            manque.append("citation")
        if not str(leaf.get("article") or "").strip():
            manque.append("article")
        if leaf.get("page_pdf") in (None, ""):
            manque.append("page_pdf")
        if manque:
            rejets.append(f"{chemin} : rejetée (manque {', '.join(manque)})")
            return None
        out = dict(leaf)
        try:
            out["page_pdf"] = int(out["page_pdf"])
        except (TypeError, ValueError):
            rejets.append(f"{chemin} : page_pdf non entière ({leaf.get('page_pdf')!r})")
            return None
        out["statut"] = "propose"
        return out

    for rub, feuilles in _FEUILLES.items():
        bloc = d.get(rub)
        if not isinstance(bloc, dict):
            continue
        if feuilles == (None,):  # feuille plate (mixite)
            leaf = _feuille_ok(rub, bloc)
            if leaf is not None:
                regles[rub] = leaf
            continue
        garde: dict = {}
        for f in feuilles:
            if f in bloc:
                leaf = _feuille_ok(f"{rub}.{f}", bloc[f])
                if leaf is not None:
                    garde[f] = leaf
        if garde:
            regles[rub] = garde
    return regles, rejets


def _compter(regles: dict) -> tuple[int, int]:
    """(proposées lues, absences prouvées) dans un bloc regles validé."""
    prop = absent = 0
    for _chemin, leaf in D.iter_regles_feuilles(regles):
        if leaf.get("absent"):
            absent += 1
        else:
            prop += 1
    return prop, absent


# ── écriture YAML (chirurgie de lignes : la calibration existante reste intacte) ────────────────

def _bloc_regles_yaml(regles: dict) -> list[str]:
    """Le bloc `regles:` dumpé, indenté 4 espaces, ordre canonique préservé."""
    import yaml
    txt = yaml.safe_dump({"regles": regles}, allow_unicode=True, sort_keys=False,
                         default_flow_style=False, width=100)
    return ["    " + l if l.strip() else l for l in txt.rstrip("\n").split("\n")]


def _ecrire_regles(path: Path, regles_par_zone: dict[str, dict]) -> None:
    """Insère (ou remplace) le bloc `regles:` de chaque zone visée, SANS toucher au reste du
    fichier (sous_destinations, silence, meta…). Idempotent : un `regles:` existant est retiré
    avant réinsertion."""
    lignes = path.read_text(encoding="utf-8").split("\n")

    def _est_cle_zone(i: int) -> str | None:
        m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", lignes[i])
        return m.group(1) if m else None

    for zone, regles in regles_par_zone.items():
        if not regles:
            continue
        # localiser la ligne-clé de la zone
        zi = next((i for i in range(len(lignes))
                   if _est_cle_zone(i) == zone), None)
        if zi is None:
            continue
        # borne du bloc de zone : prochaine clé à 2 espaces, ou clé de niveau 0
        zfin = len(lignes)
        for j in range(zi + 1, len(lignes)):
            if re.match(r"^  \S", lignes[j]) and re.match(r"^  [A-Za-z0-9_]+:\s*$", lignes[j]) \
                    or re.match(r"^\S", lignes[j]):
                zfin = j
                break
        # retirer un éventuel `    regles:` déjà présent dans le bloc
        rstart = next((j for j in range(zi + 1, zfin)
                       if re.match(r"^    regles:\s*$", lignes[j])), None)
        if rstart is not None:
            rend = zfin
            for j in range(rstart + 1, zfin):
                if re.match(r"^    \S", lignes[j]) or re.match(r"^  \S", lignes[j]) \
                        or re.match(r"^\S", lignes[j]):
                    rend = j
                    break
            del lignes[rstart:rend]
            zfin -= (rend - rstart)
        # insérer le nouveau bloc juste après la ligne-clé de la zone
        lignes[zi + 1:zi + 1] = _bloc_regles_yaml(regles)
    path.write_text("\n".join(lignes), encoding="utf-8")
    D._load_yaml.cache_clear()


# ── orchestration ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Rapport:
    insee: str
    commune: str
    document: str
    zones: list[RapportZone] = field(default_factory=list)
    modele: str = ""

    @property
    def n_proposees(self) -> int:
        return sum(z.proposees for z in self.zones)

    @property
    def n_absentes(self) -> int:
        return sum(z.absentes for z in self.zones)

    @property
    def n_rejetees(self) -> int:
        return sum(len(z.rejetees) for z in self.zones)

    @property
    def tokens_in(self) -> int:
        return sum(z.tokens_in for z in self.zones)

    @property
    def tokens_out(self) -> int:
        return sum(z.tokens_out for z in self.zones)

    @property
    def secondes(self) -> float:
        return sum(z.secondes for z in self.zones)

    @property
    def cout_eur(self) -> float:
        from ..ai.core import PRICE
        pin, pout = PRICE.get(self.modele, (0, 0))
        return (self.tokens_in * pin + self.tokens_out * pout) / 1_000_000


def extraire(insee: str, *, db=None, par: str = "cli", appel=None,
             zones_voulues: list[str] | None = None) -> Rapport:
    """Extrait les règles chiffrées des zones U d'une commune et les écrit en `propose` dans le
    YAML. `appel` injectable (tests). `zones_voulues` restreint (défaut : toutes les zones U)."""
    appel = appel or _appel_reel
    path = D._fichier_commune(insee)
    if path is None:
        raise ValueError(f"commune {insee} non calibrée (aucun YAML plu_destinations)")
    doc = D._load_yaml(str(path))
    meta = doc.get("meta") or {}
    rap = Rapport(insee=str(meta.get("insee") or insee),
                  commune=str(meta.get("commune") or insee),
                  document=str(meta.get("document") or ""))
    pdf = telecharger_reglement(meta)
    pages = _pages_texte(pdf)
    chapitres = zones_u(segmenter_chapitres(pdf))
    texte_dg = _texte_dispositions_generales(pages)
    cles_yaml = set((doc.get("zones") or {}).keys())
    regles_par_zone: dict[str, dict] = {}
    for code, p0, p1 in chapitres:
        if code not in cles_yaml:
            continue  # on n'écrit que dans une zone déclarée
        if zones_voulues and code not in zones_voulues:
            continue
        rz = RapportZone(zone=code)
        t0 = time.time()
        brut, tin, tout, model = appel(db, code, _texte_marque(pages, p0, p1), texte_dg)
        rz.secondes = time.time() - t0
        rz.tokens_in, rz.tokens_out = tin, tout
        rap.modele = model or rap.modele
        regles, rejets = _valider_regles(brut)
        rz.rejetees = rejets
        rz.proposees, rz.absentes = _compter(regles)
        rap.zones.append(rz)
        if regles:
            regles_par_zone[code] = regles
    _ecrire_regles(path, regles_par_zone)
    return rap
