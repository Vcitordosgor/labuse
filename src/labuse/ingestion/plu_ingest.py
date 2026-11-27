"""M51-P1b — Ingestion du règlement écrit en extraits ARTICLE, indexés full-text (Postgres FTS
french). Sert du VERBATIM SOURCÉ : chaque extrait porte commune, document, article, PAGE PDF,
millésime, lien. Le doute (page quasi vide → scan/illisible possible) est un CHAMP SERVI, pas
interne. La pagination ambiguë (double numérotation, ex. Saint-Benoît) est détectée et DITE.

Granularité = article (unité naturelle, regex-détectable). On cite la PAGE PDF (fiable) — jamais la
page imprimée seule (noyée dans les en-têtes, ambiguë en double numérotation)."""
from __future__ import annotations

import json as _json
import re
import unicodedata as _ud
from pathlib import Path

import fitz
from sqlalchemy import text
from sqlalchemy.orm import Session

_DDL = """
CREATE TABLE IF NOT EXISTS plu_reglement_extrait (
    id                 serial PRIMARY KEY,
    insee              varchar(5) NOT NULL,
    commune            text NOT NULL,
    idurba             text NOT NULL,
    millesime          date,
    document           text NOT NULL,
    zone               text,
    article_ref        text,
    page_pdf           int  NOT NULL,
    page_debut         int,
    page_fin           int,
    page_map           jsonb,
    texte_verbatim     text NOT NULL,
    doute              boolean NOT NULL DEFAULT false,
    doute_motif        text,
    pagination_ambigue boolean NOT NULL DEFAULT false,
    source_url         text NOT NULL,
    pdf_url            text,
    fetched_at         timestamptz,
    tsv                tsvector
);
-- OUTIL-PLU-FIX-1 (LOT 2) — pdf_url = lien DIRECT vers le règlement écrit (.pdf), distinct du pack
-- intégral .zip (source_url). Le bouton « PDF ↗ » doit ouvrir un PDF (+ #page=N), jamais un .zip.
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS pdf_url text;
-- OUTIL-PLU-FIX-2 (B1) — page_debut/page_fin : bornes de page de l'extrait (égales, borné à la page).
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS page_debut int;
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS page_fin   int;
-- OUTIL-PLU-FIX-3 — page_map = [[offset_dans_texte, page_pdf], …] : situe le mot cité à sa page réelle
-- dans un article multi-pages (l'article n'est plus coupé par page).
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS page_map jsonb;
-- OUTIL-PLU-FIX-10 (LOT 3) — livret/bassin de vie du règlement de Saint-Paul : les mêmes articles d'une
-- zone (Usdu…) sont RÉÉDITÉS par bassin (La Plaine–Bois de Nèfles p.200, La Saline p.246, Guillaume
-- p.306). On garde CHAQUE réédition (accessible avec son livret et sa page), au lieu de les dédoublonner.
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS livret text;
-- OUTIL-PLU-FIX-11 (LOT 2) — secteurs régis par un chapitre MUTUALISÉ dont la bannière énumère plusieurs
-- zones (« ZONES UA, UB, UC et UD » → « UA,UB,UC,UD »). L'étiquette `zone` ne garde que le préfixe « U » ;
-- cette colonne permet de NE PAS servir cet article sous une zone sœur (UE) qui a son propre article.
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS secteurs text;
-- OUTIL-PLU-FIX-13 — un PDF peut CONCATÉNER des dossiers de modification après le règlement (La Plaine :
-- p.118-217). `dossier` = étiquette du dossier (NULL = article du règlement de base) → affiché à part,
-- classé APRÈS le règlement. `modif_note` = sur un article du règlement de base, signale une modification
-- POSTÉRIEURE non encore intégrée (ex. ouverture AUs1 de mai 2023).
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS dossier text;
ALTER TABLE plu_reglement_extrait ADD COLUMN IF NOT EXISTS modif_note text;
CREATE INDEX IF NOT EXISTS ix_plu_extrait_tsv    ON plu_reglement_extrait USING gin(tsv);
CREATE INDEX IF NOT EXISTS ix_plu_extrait_insee  ON plu_reglement_extrait(insee);
CREATE INDEX IF NOT EXISTS ix_plu_extrait_doc    ON plu_reglement_extrait(insee, document);
"""

# En-tête d'article ou de zone. Formats rencontrés sur l'île : mutualisé « Article U 4 »,
# classique « Article Ua 1 », NUMÉROTÉ « Article 1- » / « ARTICLE 1 - » (dispositions générales),
# code « Article R111-2 », titres « ZONE UE » / « CHAPITRE|TITRE|SECTION … ».
# OUTIL-PLU-FIX-2 (B3) — un en-tête est une LIGNE DE TITRE, pas une référence dans une phrase. On NE
# matche plus en minuscule (« voir article 13.3 », « la zone n'ont pas », « sous le titre IV » sont de
# la prose, pas des titres) : le mot-clé doit commencer par une MAJUSCULE (ARTICLE/Article, ZONE/Zone,
# CHAPITRE/Chapitre…). Le drapeau `i` est retiré ; un garde anti-renvoi (`_looks_cross_ref`) écarte en
# plus les « (voir Article … » capitalisés. Supprime les 76 extraits bidon et rend les articles entiers.
# OUTIL-PLU-FIX-14 (LOT 2) — forme canonique d'un code de zone réunionnais : préfixe de phase optionnel
# (1AU, 2AU), classe U/AU/A/N, puis secteur (U3, U2e, AUst, Npnr…). Partagé par les en-têtes d'article.
_ZCODE = r'[0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,4}'
_HEADER = re.compile(
    # OUTIL-PLU-FIX-6 (point 2, La Possession) — un en-tête peut suivre une FIN DE PHRASE sur la même
    # ligne : « …Sans objet. ARTICLE UB 10 - … » (extraction PDF qui colle la suite) → sinon UB 10 est
    # fondu dans UB 9. On ancre en DÉBUT DE LIGNE ou juste après « . ».
    # OUTIL-PLU-FIX-10 (LOT 3) — …ni point ni saut de ligne : le PDF de Saint-Paul colle l'en-tête à la
    # phrase précédente (« …augmentée d'un mètre maximum Article 11- \n Aspect extérieur… ») → l'article 11
    # de Usdu était fondu dans l'article 10. On accepte aussi un en-tête collé à un MOT, à la condition
    # STRICTE que ce soit la forme numérotée « Article <n>- » (tiret) — jamais un « article 11 » de prose
    # (minuscule, exclu par la casse) ; les renvois « voir/cf. Article… » restent écartés par _looks_cross_ref.
    r'(?m)(?:^[ \t]*|(?<=\.)[ \t]+|(?<=[a-zà-ÿ])[ \t]+(?=(?:ARTICLE|Article)\s+\d+\s*[-–—]))('
    # OUTIL-PLU-FIX-14 (LOT 2) — en-tête « ARTICLE <ZONE-à-chiffre> <n°> » (Saint-Joseph « ARTICLE U3 10 -
    # HAUTEUR ») : la zone porte un chiffre (U1…U5), SUIVIE d'un ESPACE puis du n° d'article. La branche
    # générique ci-dessous (zone = lettres seules) avalait le chiffre de la zone comme n° d'article et
    # rabattait U1…U5 sur « U » → toutes les zones numérotées confondues. On capte donc d'abord le code de
    # zone COMPLET (classe + chiffre + secteur) quand un espace le sépare du n° d'article.
    r'(?:ARTICLE|Article)\s+' + _ZCODE + r'[ \t]+\d+[A-Za-z0-9.\-]*'
    # OUTIL-PLU-FIX-5 (Saint-Benoît) — séparateur zone→numéro : espace, point, tiret court/en-dash/em-dash
    # (« Article U – 4. Hauteur » n'était pas détecté → 47 en-têtes perdus, commune entière sans article).
    r'|(?:ARTICLE|Article)\s+[A-Za-z]{0,4}\s*[-–—.]?\s*\d+[A-Za-z0-9.\-]*'
    r'|(?:ZONE|Zone)\s+[0-9A-Za-z]{1,6}\b'
    r'|(?:CHAPITRE|TITRE|SECTION|Chapitre|Titre|Section)\s+[IVXLC0-9]+\b'
    r')')
# OUTIL-PLU-FIX-4 (critère 4) — tolère le POINT entre la classe et le numéro (« Article N.1 », « N.2 »
# à Saint-Denis) : sinon z_ref=None → repli bannière → zone fausse (13 « Article N.x » étiquetés A).
# OUTIL-PLU-FIX-14 (LOT 2) — le chiffre qui suit la classe n'appartient à la ZONE que s'il existe un AUTRE
# numéro ENSUITE (le n° d'article) : « ARTICLE U3 10 - HAUTEUR » → zone « U3 » (deux nombres : U3 puis 10).
# Dans « Article U8 - Hauteur » (PLU modernisé, Sainte-Rose/Saint-Pierre) le chiffre EST le n° d'article :
# zone « U ». On capte donc le code complet UNIQUEMENT quand un espace + un chiffre le suivent (lookahead),
# sinon la classe en lettres seules (forme à un seul nombre, séparée par tiret/point).
_ZONE_FROM_ART = re.compile(
    r'(?i)(?:ARTICLE)\s+(' + _ZCODE + r'(?=[ \t]+\d)|[A-Za-z]{1,4})(?:[ \t]+|\s*[-–—.]?\s*)\d')
_ZONE_FROM_ZONE = re.compile(r'(?i)ZONE\s+([0-9A-Za-z]{1,5})')
# OUTIL-PLU-FIX-8 (LOT 3) — code de zone à CHIFFRE DE TÊTE (zones À URBANISER futures : Le Port
# « Article 2AU 9 », « Article 1AUindicée 5 »). _ZONE_FROM_ART échoue dessus (il attend la classe en
# tête, et le n° d'article se perd dans le mot « indicée » → la référence stockée est « Article 2AU » /
# « Article 1AUindic », sans chiffre d'ancrage). On lit alors la CLASSE+chiffre (2AU, 1AU) — ce motif ne
# vise QUE les codes à chiffre de tête, donc « Article UB » / « Article Ucv » (classe en tête) ne sont
# jamais touchés. Une parcelle 1AUm/2AU retrouve ainsi ses articles (candidats [1AU,1AUM] ⊃ « 1AU »).
_ZONE_FROM_ART_NUM = re.compile(r'(?i)^(?:ARTICLE)\s+([0-9]{1,2}(?:AU|U|A|N))[A-Za-z0-9]*')
# OUTIL-PLU-FIX-10 (LOT 1) — chapitre GÉNÉRIQUE « ZONE AU indicée » (Bras-Panon, Saint-Louis,
# Trois-Bassins, Cilaos) : un seul chapitre « AU indicée » tient les articles de TOUTES les zones AU
# indicées de la commune (AUt, AUec, AUa…), chaque article donnant la règle PROPRE d'une zone (ex.
# AUindicée 10.2 : AUt 8 m/10 m aux Trois-Bassins ; AUec 18 m à Bras-Panon) OU un renvoi EXPRÈS
# (« Pour la zone AUt, se reporter au règlement de la zone Ub »). Sans étiquette ces articles tombaient
# en zone NULL et le filtre AUt servait À TORT la hauteur d'Ub. On les étiquette AUINDICEE (sentinelle,
# jamais une zone de plan) pour les servir comme articles PROPRES sous les filtres AU indicés.
# N'ATTRAPE PAS « Article 1AUindicée » (Le Port, Saint-Joseph : code de zone à chiffre de tête, déjà
# correctement zoné 1AU/AUST) — ancré sur « ARTICLE/ZONE AU indic… » (AU en tête de mot, sans chiffre).
_AUINDICEE_ART = re.compile(r'(?i)^(?:ARTICLE|ZONE)\s+AU\s*indic')
# référence croisée dans la prose juste avant le « titre » : « (voir Article… », « cf. Article… »,
# « au titre… », « à l'article… » → l'en-tête matché n'est pas un vrai début d'article.
_CROSSREF_PRE = re.compile(r"(?i)(?:\(|voir|cf\.?|à l['’]|au|du|de la|sous le|présent|dudit|ledit)\s*$")


def _looks_cross_ref(flat: str, start: int) -> bool:
    pre = _norm(flat[max(0, start - 30):start])
    return bool(_CROSSREF_PRE.search(pre))


# OUTIL-PLU-FIX-10 (LOT 2) — puce de liste : • ▪ ◦ · ‣ ∙, tiret/astérisque, et les puces Wingdings de
# la zone d'usage privé (U+F000–F0FF) que sèment les PDF de règlement.
_BULLET = "•▪◦·‣∙-*"
_PUCE_SEULE = re.compile(r"^[ \t" + _BULLET + r"\-]+$")


def _looks_list_item(flat: str, start: int) -> bool:
    """OUTIL-PLU-FIX-10 (LOT 2) — un « ZONE X » qui est un ÉLÉMENT DE LISTE (valeur énumérée dans un
    article), pas un titre de chapitre. Signature : la LIGNE PRÉCÉDENTE n'est qu'une puce (Sainte-Marie,
    8.2 : « …limitée à : / • / Zone UA : / ▪ / 15,00 mètres… »). Prenait « Zone UA » pour un chapitre et
    coupait l'article U8 juste avant ses hauteurs. Les vrais titres « ZONE UA » sont précédés d'un saut
    de page, d'une fin de phrase ou d'un autre titre — jamais d'une puce nue."""
    ls = flat.rfind("\n", 0, start)                     # début de la ligne de l'en-tête
    if ls < 0:
        return False
    # ligne non vide précédente
    j = ls
    while j > 0:
        pstart = flat.rfind("\n", 0, j)
        line = flat[pstart + 1: j]
        if line.strip():
            return bool(_PUCE_SEULE.match(line)) and line.strip() != ""
        j = pstart
        if pstart < 0:
            break
    return False


# OUTIL-PLU-FIX-6 (point 2, Saint-Denis) — une ligne de SOMMAIRE (« ZONE N …………… 119 ») n'est pas un
# en-tête de chapitre : sinon elle absorbe les dispositions générales qui la suivent et les étiquette
# « N ». On reconnaît les points de suite (table des matières).
_TOC_LEADER = re.compile(r'\.{4,}|…{2,}')
# titre de chapitre SANS zone : réinitialise l'étiquette (dispositions générales/communes, définitions,
# lexique, annexes, titres liminaires) — point 2 : ces pages ne portent pas l'étiquette d'une zone.
_RESET_CHAP_SRC = (
    r"(?:\d+[.)]\s*)?(?:titre\s+[ivx]+\b|annexes?\b|dispositions?\s+(?:g[ée]n[ée]rales?|communes|"
    r"applicables?\s+à\s+(?:toutes|l'ensemble))|d[ée]finitions?\b|lexique\b|glossaire\b|pr[ée]ambule\b)")
_RESET_CHAP = re.compile(r"(?i)^\s*" + _RESET_CHAP_SRC)
# variante MULTILIGNE pour trouver ces titres comme frontières de bloc dans le flux plat.
_RESET_CHAP_M = re.compile(r"(?im)^[ \t]*(" + _RESET_CHAP_SRC + r".*)$")


def _reset_is_title(line: str) -> bool:
    """OUTIL-PLU-FIX-7 (point 4) — « un en-tête est une LIGNE DE TITRE, pas une phrase ». FIX-6 prenait
    toute ligne débutant par annexe/titre/dispositions… pour un titre de chapitre, y compris la PROSE
    (« annexe). Cette disposition ne concerne pas… », « titre V du présent règlement. ») → ~120 réfs
    bidon. Un VRAI titre : le mot-clé est suivi d'une FIN de ligne, d'un séparateur (– - — :), d'un
    NUMÉRO ou d'une CAPITALE — jamais d'un mot MINUSCULE (continuation grammaticale de prose). De plus un
    titre est COURT (≤ 55 car.) ou en CAPITALES."""
    s = line.strip()
    m = _RESET_CHAP.match(s)
    if not m:
        return False
    rest = s[m.end():]
    if re.match(r"\s+[a-zà-ÿ]", rest) and not re.match(r"\s*[:\-–—]", rest):
        return False                              # mot-clé + mot minuscule, sans séparateur → prose
    letters = [c for c in s if c.isalpha()]
    upr = (sum(c.isupper() for c in letters) / len(letters)) if letters else 0.0
    return len(s) <= 55 or upr >= 0.6


def _is_toc_header(flat: str, start: int) -> bool:
    """La ligne de l'en-tête matché porte-t-elle des points de suite (entrée de sommaire) ?"""
    a = flat.rfind("\n", 0, start) + 1
    b = flat.find("\n", start)
    line = flat[a: b if b != -1 else len(flat)]
    return bool(_TOC_LEADER.search(line))


def _valid_header(ref: str) -> bool:
    """OUTIL-PLU-FIX-3 (B3) — un titre « ZONE X » n'est un VRAI en-tête que si X est un code de zone
    (U/AU/A/N…). « Zone de », « Zone du », « Zone qui », « Zone mixte », une référence cadastrale
    « Zone CL0852 » ne sont PAS des zones : ni extrait bidon, ni faux découpage. Les en-têtes
    ARTICLE/CHAPITRE/TITRE/SECTION restent acceptés tels quels."""
    m = _ZONE_FROM_ZONE.match(ref)
    if ref.upper().startswith("ZONE") and m:
        return _valid_zone(m.group(1)) is not None
    return True

# OUTIL-PLU-FIX-1 (LOT 4) — un code de zone réunionnais : préfixe optionnel (chiffre), classe
# U/AU/A/N, puis secteur. Sert à REFUSER les faux libellés (QUI, EST, DE, R, L, SONT, RURAL…) issus
# d'un « ZONE <mot> » attrapé dans la prose : un libellé qui n'a pas cette forme devient « sans
# étiquette » plutôt qu'une carte mensongère.
_ZONE_SHAPE = re.compile(r'(?i)^[0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,5}$')
# bannière de zone RÉPÉTÉE en tête de page (« Zone U2e », « Zones AU2 », « Zones U1a à U1g ») :
# c'est l'indicateur fiable du chapitre régi par la page — mais c'est AUSSI ce qui coupait l'article
# (LOT 3). On la DÉTECTE pour étiqueter, et on la RETIRE du flux avant le découpage.
# préfixe toléré (« Règlement - ZONE UB » à Petite-Île), code entier sur le reste de la ligne.
_BANNER = re.compile(r'(?i)^\s*(?:r[eè]glement\s*[-–—:]\s*)?zones?\s+([0-9A-Za-z][0-9A-Za-z à/,.\-]{0,90}?)\s*$')
_PAGEFOOT = re.compile(r'(?i)^\s*(?:page\s+\d{1,3}(?:\s+sur\s+\d{1,3})?|\d{1,3}\s*/\s*\d{1,3}|-?\s*\d{1,3}\s*-?)\s*$')


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


# OUTIL-PLU-FIX-13 — carte des dossiers de modification concaténés (config/plu_dossiers.yaml), chargée une
# fois. {insee: [{pages:(a,b), etiquette, integre_base, signale_zones:set}]}.
_DOSSIERS_CACHE: dict | None = None


def _dossiers_map() -> dict:
    global _DOSSIERS_CACHE
    if _DOSSIERS_CACHE is not None:
        return _DOSSIERS_CACHE
    import pathlib

    import yaml
    out: dict = {}
    p = pathlib.Path(__file__).resolve().parents[3] / "config" / "plu_dossiers.yaml"
    if p.is_file():
        data = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("communes", {}) or {}
        for insee, c in data.items():
            dos = []
            for d in (c.get("dossiers") or []):
                a, b = d["pages"]
                num = f"n°{d['num']} " if d.get("num") else ""
                etq = f"Dossier de modification {num}— {d['label']} ({d['date']})"
                dos.append({"a": int(a), "b": int(b), "etiquette": etq,
                            "integre_base": bool(d.get("integre_base", True)),
                            "date": d["date"], "label": d["label"],
                            "signale_zones": {z.upper() for z in (d.get("signale_zones") or [])}})
            out[str(insee)] = {"reglement_pages": tuple(c.get("reglement_pages") or (0, 10 ** 9)),
                               "dossiers": dos}
    _DOSSIERS_CACHE = out
    return out


def _applique_dossiers(insee: str, extraits: list[dict]) -> None:
    """OUTIL-PLU-FIX-13 — étiquette chaque extrait selon sa page (dossier de modification ou règlement de
    base) ; pose `modif_note` sur les articles du règlement de base dont une zone est touchée par un dossier
    POSTÉRIEUR non intégré. Modifie `extraits` sur place. No-op si la commune n'a pas de dossiers."""
    cfg = _dossiers_map().get(str(insee))
    if not cfg:
        return
    # zones du règlement de base à signaler (modif postérieure non intégrée) + le libellé de cette modif.
    non_integres = [d for d in cfg["dossiers"] if not d["integre_base"]]
    for e in extraits:
        pg = e.get("page_debut") or e.get("page_pdf")
        dos = next((d for d in cfg["dossiers"] if d["a"] <= pg <= d["b"]), None)
        if dos:
            e["dossier"] = dos["etiquette"]
            e["modif_note"] = None
        else:
            e["dossier"] = None
            zu = (e.get("zone") or "").upper()
            touché = [d for d in non_integres if zu and zu in d["signale_zones"]]
            e["modif_note"] = (
                f"Modification « {touché[0]['label']} » ({touché[0]['date']}) NON intégrée à ce "
                f"règlement de base — voir le dossier de modification." if touché else None)


# OUTIL-PLU-FIX-10 (LOT 3) — livret/bassin de vie dans le fil d'en-tête (Saint-Paul) :
# « …/ Titre 2 – Livret 4 – Bassin de vie La Plaine – Bois de Nèfles ». On garde le libellé parlant
# (« Livret 4 – Bassin de vie … » ou, à défaut, « Livret N »).
_LIVRET = re.compile(r'(?i)(Livret\s+\d+(?:\s*[-–—]\s*Bassin de vie\s+[^/]+?)?|Bassin de vie\s+[^/]+?)\s*$')


def _livret_par_page(pages: list[str]) -> list[str | None]:
    """Livret/bassin de vie de chaque page (lu dans le fil d'en-tête), forward-fill. None si la commune
    n'a pas de livrets (cas général)."""
    out: list[str | None] = []
    last: str | None = None
    for t in pages:
        cur = None
        for l in t.splitlines()[:6]:
            m = _LIVRET.search(_norm(l))
            if m:
                cur = _norm(m.group(1))
                break
        if cur:
            last = cur
        out.append(cur or last)
    return out


def _valid_zone(z: str | None) -> str | None:
    """Renvoie le code zone normalisé (MAJ) s'il a la forme d'un code réunionnais, sinon None.
    OUTIL-PLU-FIX-3 — rejette aussi les RÉFÉRENCES CADASTRALES prises pour des zones (« AK0561 »,
    « CL0852 ») : un vrai code de zone n'a jamais 3 chiffres consécutifs (au plus « AU3 », « 2AU »)."""
    if not z:
        return None
    z = _norm(z).upper().rstrip('.')
    if re.search(r'\d{3,}', z):          # section+parcelle cadastrale, pas une zone
        return None
    return z if _ZONE_SHAPE.match(z) else None


def _banner_zone(expr: str) -> str | None:
    """D'une bannière (« U2e », « U1a à U1g », « AU2 / AU3 ») tire UN code servable : le code unique
    si un seul, sinon le plus long préfixe commun valide des codes listés (famille régie)."""
    toks = [t for t in re.split(r'[\s/,]+|\bà\b|\bet\b|à', expr) if t.strip()]
    codes = [_valid_zone(t) for t in toks]
    codes = [c for c in codes if c]
    if not codes:
        return None
    if len(codes) == 1:
        return codes[0]
    pref = codes[0]
    for c in codes[1:]:
        while not c.startswith(pref):
            pref = pref[:-1]
            if not pref:
                return codes[0]
    return _valid_zone(pref) or codes[0]


def _banner_secteurs(expr: str) -> list[str]:
    """OUTIL-PLU-FIX-11 (LOT 2) — TOUS les secteurs énumérés par une bannière de CHAPITRE MUTUALISÉ
    (« ZONES UA, UB, UC et UD » → [UA,UB,UC,UD]). `_banner_zone` n'en garde que le préfixe commun (« U »),
    perdant quels secteurs le chapitre régit ; `_filtre_scope` ne pouvait donc pas savoir que « Article U 12 »
    ne concerne PAS UE. On renvoie la liste complète (codes valides, MAJ) — vide si moins de 2 secteurs."""
    toks = [t for t in re.split(r'[\s/,]+|\bà\b|\bet\b|à', expr) if t.strip()]
    codes = [c for c in (_valid_zone(t) for t in toks) if c]
    uniq = list(dict.fromkeys(codes))
    return uniq if len(uniq) >= 2 else []


# OUTIL-PLU-FIX-3 (D3) — en-tête/pied COURANT qui VARIE d'une page à l'autre (le « / Titre 2 – Livret 1
# – Bassin de vie X » change de livret en livret → la détection par fréquence le rate). On le reconnaît
# aussi par son DÉBUT DE LIGNE : « Règlement… », « Commune de… », « Ville de… », « Mairie… », « Plan
# Local d'Urbanisme… », « PLU approuvé… », « Edition… », « Modifié par… », une liste de dates, etc.
_CHROME_PAT = re.compile(
    r"(?i)^\s*(?:r[eè]glement\b|commune d|ville d|mairie\b|plan local|p\.?\s?l\.?\s?u\b"
    r"|plu approuv|[eé]dition\b|modifi[eé] par|dossier approuv|d[eé]partement\b"
    r"|\d{1,2}/\d{1,2}/\d{2,4}[\s,]*$)")
# OUTIL-PLU-FIX-8 (LOT 2) — chrome d'en-tête/pied COURANT qui échappait à la détection par fréquence
# (seuil pages/5 non atteint par une partie du document) et polluait l'annexe de Saint-Paul :
#  · le FIL d'en-tête réduit au numéro de partie nu « Titre 4 » / « Livret 2 » (le vrai titre de section
#    « TITRE III - DISPOSITIONS… » a du TEXTE après le numéro, il n'est donc PAS visé) — sinon « Titre 4 »
#    était pris pour un en-tête de section et fragmentait le lexique (p.351-389) en 25 extraits ;
#  · la CONTINUATION de la liste des dates DCM (« 21/10/2015, 05/10/2017, … et du 27/03/2025. »), suite du
#    pied « Modifié par DCM du : … » déjà retiré — une ligne faite UNIQUEMENT de dates/« et du »/ponctuation.
_CHROME_RUNHEAD = re.compile(r"(?i)^\s*(?:titre|livret)\s+\d{1,2}\s*$")
_CHROME_DATELIST = re.compile(r"(?i)^\s*(?:\d{1,2}/\d{1,2}/\d{2,4}|et|du|[,.\s])+$")


def _detect_chrome(pages: list[str]) -> set[str]:
    """Lignes d'en-tête/pied COURANTES CONSTANTES (répétées sur beaucoup de pages). Seuil = max(4,
    pages/5). Complété par `_CHROME_PAT` pour le chrome qui varie (voir `_clean_pages`)."""
    from collections import Counter
    c: Counter = Counter()
    for t in pages:
        ls = [_norm(l) for l in t.splitlines() if _norm(l)]
        for l in ls[:6] + ls[-3:]:
            c[l] += 1
    thr = max(4, len(pages) // 5)
    return {l for l, n in c.items() if n >= thr and len(l) > 3}


_SBANNER_UNSET = object()   # page sans bannière → hérite du chapitre courant (forward-fill)


def _clean_pages(pages: list[str], *, banniere_en_premiere_ligne: bool = False) -> tuple[list[str], list[str | None], list[list[str] | None]]:
    """Retire de chaque page le « chrome » (en-têtes/pieds courants — constants OU variables par page,
    D3 —, bannière de zone, n° de page) et renvoie (pages nettoyées, zone de bannière par page,
    secteurs régis par page). Le texte servi est ainsi celui du règlement, sans en-têtes/pieds répétés.
    OUTIL-PLU-FIX-11 (LOT 2) — `sbanner` = la LISTE des secteurs d'un chapitre mutualisé (« ZONES UA, UB,
    UC et UD » → [UA,UB,UC,UD]), forward-fill comme zbanner : permet de savoir que « Article U 12 » ne
    régit pas UE."""
    chrome = _detect_chrome(pages)
    clean: list[str] = []
    zbanner: list[str | None] = []
    sbanner_raw: list = []
    resets: list[bool] = []
    for t in pages:
        cur: str | None = None
        scur = _SBANNER_UNSET          # secteurs du chapitre vus sur CETTE page (sentinelle = aucun)
        kept: list[str] = []
        lines = t.splitlines()
        nlines = len(lines)
        # OUTIL-PLU-FIX-6 (point 2) — page d'un chapitre SANS zone (dispositions générales/communes,
        # définitions, lexique, annexes, titre liminaire) → réinitialise l'étiquette (stoppe le
        # report de la dernière bannière, qui « fuyait » sur ces pages : Saint-Benoît annexes → UE).
        reset = any(_reset_is_title(_norm(x)) for x in lines[:10] if _norm(x))
        # OUTIL-PLU-FIX-6 (point 2) — SOMMAIRE : une page qui liste PLUSIEURS zones (« ZONE UA … ZONE UB
        # … ZONE UC ») n'est pas une page de zone ; on n'en tire AUCUNE bannière (sinon le sommaire
        # d'Étang-Salé p.3 étiquette UA ses dispositions générales p.6-14). On la traite en reset.
        _bz_page = []
        for x in lines[:12]:
            nx = _norm(x)
            mbx = _BANNER.match(nx)
            if mbx:
                bzx = _banner_zone(mbx.group(1))
                if bzx:
                    _bz_page.append(bzx)
        sommaire = len(set(_bz_page)) >= 2
        if sommaire:
            reset = True
        resets.append(reset)
        for idx, l in enumerate(lines):
            n = _norm(l)
            if not n:
                kept.append(l)
                continue
            top = idx < 12       # le titre de chapitre (« Zone Uavap ») peut suivre un bandeau de 4-5 lignes
            bottom = idx >= nlines - 3
            # BANNIÈRE d'ABORD : « Règlement - ZONE UB » (Petite-Île) commence par « Règlement » comme le
            # chrome ; il faut en extraire la zone AVANT de retirer la ligne comme chrome.
            mb = _BANNER.match(n) if top and (not banniere_en_premiere_ligne or idx == 0) else None
            if mb:
                bz = _banner_zone(mb.group(1))
                if bz:
                    if not sommaire and not _is_toc_header(n, 0):   # pas une ligne de sommaire (points de conduite)
                        cur = cur or bz
                        # secteurs du chapitre : ≥2 → on les mémorise ; sinon chapitre mono-zone → on CLÔT
                        # le contexte multi-secteur (le chapitre UE ne régit plus UA/UB/UC/UD).
                        if scur is _SBANNER_UNSET:
                            secs = _banner_secteurs(mb.group(1))
                            scur = secs if secs else []
                    continue
            if n in chrome:
                continue
            if (top or bottom) and _CHROME_PAT.match(n):   # D3 — chrome qui varie par page
                continue
            # OUTIL-PLU-FIX-8 (LOT 2) — fil d'en-tête « Titre 4 » nu + continuation de liste de dates DCM
            if top and _CHROME_RUNHEAD.match(n):
                continue
            if (top or bottom) and _CHROME_DATELIST.match(n) and re.search(r'\d/\d', n):
                continue
            if _PAGEFOOT.match(n):
                continue
            kept.append(l)
        clean.append("\n".join(kept))
        zbanner.append(cur)
        sbanner_raw.append(scur)
    # OUTIL-PLU-FIX-1 (LOT 4) — forward-fill : certains PLU ne portent le code de zone qu'UNE fois, au
    # titre de chapitre (Saint-Denis « Zone Uavap » p.26), pas en bandeau de chaque page → la zone doit
    # PERSISTER jusqu'au chapitre suivant. Le remplissage ne part JAMAIS vers l'arrière : les pages
    # avant le 1er titre (dispositions générales, sommaire) restent sans étiquette.
    last: str | None = None
    sbanner: list[list[str] | None] = []
    last_s: list[str] | None = None
    for i in range(len(zbanner)):
        if resets[i]:                      # chapitre sans zone → on cesse de reporter la bannière
            last = None
            last_s = None
        if zbanner[i] is not None:
            last = zbanner[i]
        elif last is not None:
            zbanner[i] = last
        # secteurs régis : même forward-fill ; une bannière mono-zone ([]) CLÔT le contexte multi-secteur.
        if sbanner_raw[i] is not _SBANNER_UNSET:
            last_s = sbanner_raw[i] or None
        sbanner.append(last_s)
    return clean, zbanner, sbanner


def zone_candidats(zone: str) -> list[str]:
    """OUTIL-PLU-FIX-1 (LOT 5) — un secteur renvoie au règlement commun de sa famille : UBc → {UB, U},
    AU3c → {AU3, AU}, 2AUd → {2AU}, Ud → {U}. Tous les préfixes qui gardent la CLASSE (U/AU/A/N) :
    jamais « A » tiré de « AU… » (classe atomique). Appariement EXACT sur cette liste (pas de LIKE qui
    confondrait A et AU)."""
    z = _norm(zone).upper()
    m = re.match(r'^(\d*)(AU|U|A|N)(.*)$', z)
    if not m:
        return [z] if z else []
    lead, cls, rest = m.group(1), m.group(2), m.group(3)
    base = lead + cls
    out = [base]
    acc = base
    for ch in rest:
        acc += ch
        out.append(acc)
    # dédoublonne en gardant l'ordre (famille → … → code exact)
    seen: dict[str, None] = {}
    for c in out:
        seen.setdefault(c, None)
    return list(seen)


def _dedup_double_draw(page, sort: bool = False, *, glyphes_imprimes: bool = False) -> str:
    """OUTIL-PLU-FIX-9 (point 3) — certains PDF rendent les TITRES en « fausse graisse » = le texte est
    DESSINÉ DEUX FOIS À LA MÊME POSITION. `get_text()` (texte brut) rend alors la ligne EN DOUBLE
    consécutif (« 10.1 - Définition\\n10.1 - Définition » — Le Tampon : 521 lignes sur 116 pages). On
    retire le doublon consécutif UNIQUEMENT quand ce texte n'occupe qu'UNE ordonnée sur la page (dessin
    EN PLACE) ; une valeur de TABLEAU répétée sur plusieurs lignes (« RECOMMANDÉ », « 100 % ») occupe
    PLUSIEURS ordonnées et reste intacte — aucune règle n'est perdue.

    OUTIL-PLU-FIX-11 (LOT 1) — `sort` (ordre de POSITION haut→bas) rattache les cellules d'un TABLEAU de
    valeurs à leur article : Saint-Denis Up.10 « Hauteur » rend « Upr 16 m / Upi 11 m » APRÈS le titre de
    l'article SUIVANT dans l'ordre brut, collant les valeurs au mauvais article. Le tri est RÉSERVÉ aux
    règlements où ce défaut existe (identifiés par le scan `plu_fix10_scan_tronques.py`, motif
    « valeurs-fuitees ») : appliqué partout il DÉRÈGLE la détection d'en-têtes d'autres communes (Saint-Paul
    livrets, Le Port) dont l'ordre naturel était correct."""
    # Certaines annexes contiennent un ActualText sans rapport avec les glyphes
    # visibles (« ZONE Ur » à la place de « 12.3 »). Lire le dessin pour ces pages.
    flags = fitz.TEXT_IGNORE_ACTUALTEXT if glyphes_imprimes else 0
    plain = page.get_text(sort=sort, flags=fitz.TEXTFLAGS_TEXT | flags)
    ys: dict[str, set] = {}
    for b in page.get_text("dict", flags=fitz.TEXTFLAGS_DICT | flags).get("blocks", []):
        for ln in b.get("lines", []):
            t = _norm("".join(s.get("text", "") for s in ln.get("spans", [])))
            if t:
                ys.setdefault(t, set()).add(round(ln["bbox"][1]))
    out: list[str] = []
    prev: str | None = None
    removed = False
    for l in plain.splitlines():
        nl = _norm(l)
        if nl and nl == prev and len(nl) > 3 and len(ys.get(nl, ())) <= 1:
            removed = True
            continue                               # doublon consécutif dessiné EN PLACE → retiré
        out.append(l)
        if nl:
            prev = nl
    if not removed:
        return plain                               # page intacte → texte RIGOUREUSEMENT inchangé
    res = "\n".join(out)
    return res + "\n" if plain.endswith("\n") else res


# OUTIL-PLU-FIX-11 (LOT 1) — règlements à lire en ORDRE DE POSITION (tableaux de valeurs dont les cellules
# fuient vers l'article suivant dans l'ordre brut). Liste établie par le scan `plu_fix10_scan_tronques.py`
# (motif « valeurs-fuitees ») et VÉRIFIÉE sans régression commune par commune. Les autres sont lus en ordre
# naturel (le tri y déréglerait la détection d'en-têtes — Saint-Paul livrets, Le Port).
_SORT_INSEE = {"97411"}        # Saint-Denis (Up.10 Hauteur : « Upr 16 m / Upi 11 m »)


def _pages(path: str) -> list[str]:
    import os as _os
    insee = _os.path.basename(path)[:5]
    sort = insee in _SORT_INSEE
    with fitz.open(path) as doc:
        plaine = Path(path).name == "97406_reglement_20230527.pdf"
        pages = [_dedup_double_draw(page, sort=sort, glyphes_imprimes=plaine and page.number >= 117)
                 for page in doc]
        if Path(path).name == "97410_reglement_20200206.pdf":
            # Les pp. 29–31 reproduisent l’en-tête de colonnes au-dessus de y=132.
            # La colonne Règles, tableau des usages compris, finit à x=446.
            for n in (29, 30, 31):
                pages[n - 1] = doc[n - 1].get_text(
                    "text", clip=fitz.Rect(65, 132, 446, 550))
        return pages


def _pagination_ambigue(pages: list[str]) -> bool:
    """Double numérotation imprimée (ex. Saint-Benoît : bloc règlement « Page N sur 49 » puis cahier
    d'annexes « Page 1..114 ») → une même « p.N » désigne deux endroits. Heuristique : la suite des
    n° imprimés RÉ-DÉCROÎT franchement en cours de document (repart près de 1 après un maximum élevé)."""
    seq = []
    for t in pages:
        m = re.search(r'(?im)page\s+(\d{1,3})\s+sur\s+\d{1,3}', t) or re.search(r'(?m)^\s*(\d{1,3})\s*$', t)
        seq.append(int(m.group(1)) if m else None)
    nums = [(i, n) for i, n in enumerate(seq) if n is not None]
    peak = 0
    for i, n in nums:
        if n >= peak:
            peak = n
        elif peak >= 8 and n <= 3 and i > len(pages) // 4:
            return True          # ré-décroissance franche après un pic → 2 blocs
    return False


# OUTIL-PLU-FIX-4 (critère 3) — niveaux de structure SOUS l'article, pour re-découper un GROS BLOC
# (règlement scanné / en-tête d'article suivant non détecté) au niveau qui existe dans le document :
# section/chapitre/sous-section, titre numéroté (« 1 - OCCUPATIONS »), sous-article (« 6.3 »), ou
# intertitre tout en capitales. N'est appliqué qu'aux blocs longs (≥ 6 pages) → les articles normaux
# restent entiers (D1 préservé : l'exception reste avec sa règle).
_SUBHEAD = re.compile(
    r'(?m)^[ \t]*('
    r'(?:SECTION|Section|CHAPITRE|Chapitre|SOUS-SECTION|Sous-section)\s+[IVXLC0-9]'
    r'|\d{1,2}\s*[-–.)]?\s*[A-ZÀ-Ÿ]{2,}'       # titre numéroté « 6 IMPLANTATION », « 2. OCCUPATION »
    r'|[IVX]{1,5}\s*[-–.)]\s*[A-ZÀ-Ÿ]{2,}'     # intertitre en chiffres ROMAINS « XXI. AMÉNAGEMENTS EXTÉRIEURS »
    r'|[A-ZÀ-Ÿ][A-ZÀ-Ÿ0-9 \-\'’/]{10,}\s*$'    # intertitre tout en capitales
    r')')
# NB : on NE découpe PAS au sous-article « 6.3 » (séparerait l'exception de sa règle — D1) : l'article
# et ses sous-points 6.1/6.2/6.3 restent ensemble ; on ne redécoupe qu'au niveau article/section/titre.
_BLOC_SEUIL_PAGES = 6                            # au-delà → on tente le sous-découpage


def _subhead_titre(line: str) -> bool:
    """OUTIL-PLU-FIX-7 (point 4) — un sous-titre de re-découpe est une LIGNE DE TITRE : marqueur
    structurel explicite (SECTION/CHAPITRE), capitales dominantes (« II - DISPOSITIONS COMMUNES… »,
    « XXI. AMÉNAGEMENTS EXTÉRIEURS ») même longues, ou ligne courte. On écarte les phrases minuscules
    (« 1) Règles devant être appliquées strictement ») ; les intertitres RÉCURRENTS sont dédoublonnés
    par l'appelant."""
    s = line.strip()
    if not s or len(s) > 90:                       # borne anti-paragraphe
        return False
    if re.match(r'(?i)^(section|chapitre|sous-section)\b', s):
        return True                                # marqueur structurel explicite (même en casse mixte)
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    upr = sum(c.isupper() for c in letters) / len(letters)
    return upr >= 0.5 or len(s) <= 35


# OUTIL-PLU-FIX-7 (point 1) — une FICHE/ANNEXE propre à UNE zone nommée doit PORTER cette zone (sinon,
# mise à `None`, elle est injoignable par le filtre de sa zone : la fiche Beauvallon « ZONE AUp » n'était
# ni dans le filtre AUp ni dans les dispositions communes). On N'attribue QUE pour les fiches/annexes
# (marqueur) nommant EXACTEMENT UNE zone SECTORIELLE (au-delà de la classe nue) : une disposition
# générale qui mentionne une zone en passant reste commune.
_FICHE_MARQUEUR = re.compile(r'(?i)\b(?:fiche\s+annexe|annexe\s+(?:du|de\s+la|relative|des|n°)|stecal)\b')
_ZONE_NOMMEE = re.compile(r'(?i)\b(?:zones?|secteurs?|stecal)\s+([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,5})\b')


def _zone_de_fiche(texte: str) -> str | None:
    """Zone d'une fiche/annexe zonée (point 1), ou None si ce n'est pas une fiche, ou si elle nomme
    zéro / plusieurs zones sectorielles distinctes (section couvrant plusieurs zones = reste commune).
    On ne lit QUE le TITRE (2 premières lignes non vides) : une NOTE citant un secteur historique
    (« secteur Nto créé en 2006 ») ne doit pas faire croire à plusieurs zones (Saint-Benoît NTA)."""
    lignes = [l for l in (texte or "").splitlines() if l.strip()][:2]
    head = " ".join(lignes)
    if not _FICHE_MARQUEUR.search(head):
        return None
    cands = set()
    for m in _ZONE_NOMMEE.finditer(head):
        z = _valid_zone(m.group(1))
        if z and z != zone_candidats(z)[0]:       # sectorielle (≠ classe nue U/AU/A/N)
            cands.add(z)
    return next(iter(cands)) if len(cands) == 1 else None


# OUTIL-PLU-FIX-8 (LOT 3) — PRÉAMBULE / tête de chapitre de zone qui n'est PAS formaté en bannière
# « Zone U2e » et finissait donc SANS zone, injoignable par le filtre de sa zone (Saint-Pierre
# « Préambule · La zone Ucv correspond au centre-ville… », Le Port « La zone 1AU couvre… », Entre-Deux
# « La zone Ua correspond au centre bourg », Petite-Île « DISPOSITIONS APPLICABLES À LA ZONE UB »). On
# n'attribue QUE sur une DÉFINITION de zone (« la zone X est/correspond/couvre… ») ou un « dispositions
# applicables à la zone X » — JAMAIS sur un simple renvoi (« se reporter au règlement de la zone U ») ni
# sur un titre « …AUX ZONES À URBANISER » (pas de « à LA zone X »). On prend la PREMIÈRE zone définie.
_PREAMBULE_DEF = re.compile(
    r"(?i)\b(?:la|les)\s+zones?\s+([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,6})\b[^.\n]{0,40}?"
    r"\b(?:est|sont|correspond|couvre|couvrent|comprend|regroupe|concerne|d[ée]signe|"
    r"a\s+vocation|ont\s+vocation|constitue|est\s+destin[ée]e?)\b")
_PREAMBULE_APPL = re.compile(
    r"(?i)dispositions?\s+(?:r[ée]glementaires\s+)?applicables?\s+à\s+la\s+zone\s+"
    r"([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,6})\b")


def _zone_de_preambule(texte: str) -> str | None:
    """Zone d'un préambule / tête de chapitre de zone (point LOT 3), ou None. Lit les 4 premières lignes
    non vides (le titre + la 1re phrase de définition)."""
    head = " ".join([l for l in (texte or "").splitlines() if l.strip()][:4])
    # un bloc d'ANNEXE qui ÉNUMÈRE des zones (« ANNEXES RELATIVES AUX ZONES NS, NTA ET NTB ») reste COMMUN
    # (plusieurs zones) — ne jamais l'attribuer à la 1re : c'est le travail de `_zone_de_fiche`, qui a déjà
    # renvoyé None faute d'UNE seule zone. Sinon on régresse le cas Saint-Benoît Ns/Nta/Ntb (resté commun).
    if re.search(r'(?i)\bannexes?\b', head):
        return None
    for rx in (_PREAMBULE_APPL, _PREAMBULE_DEF):
        m = rx.search(head)
        if m:
            z = _valid_zone(m.group(1))
            if z:
                return z
    return None


# En-têtes attestés dans les éditions de L’Étang-Salé, Bras-Panon et Saint-Louis.
_ETANG_ART = re.compile(r"(?m)^[ \t]*(" + _ZCODE + r"[ \t]+\d+\.\d+)[ \t]*[-–—][ \t]*(?=[A-ZÀ-Ÿ])")
_INDICE_ART = re.compile(r"(?im)^[ \t]*(ARTICLE[ \t]+AU[ \t]*INDIC[ÉE]E?[ \t]*\d+)\b")
_EXPLICATION_AU12 = "AU 12 · Explication des règles"
_SECTION_SEULE = re.compile(r"(?i)(?:sous-)?section\s+[0-9IVX]+[. \t–—-]+.+")


def _fiches_benoit(clean: list[str], page_off: list[int]) -> dict:
    """Frontières des loupes UE, fiches STECAL Nta/Ntb et immeubles Uap (édition GPU 20200206)."""
    # N° de fiche et secteurs graphiques explicitement visés par son titre.
    fiches = {
        51: ("Loupe L01 · Distillerie Rivière du Mât", ("UE",)),
        52: ("Loupe L02 · Petit Saint-Pierre", ("UE",)),
        82: ("Fiche 47 · Takamaka", ("NTA47",)),
        83: ("Fiche 48 · Piton des Neiges", ("NTA48",)),
        84: ("Fiche 49 à 52 · Grand Étang", tuple(f"NTA{i}" for i in range(49, 53))),
        85: ("Fiche 53 · Grand Étang", ("NTA53",)),
        87: ("Fiche 54 · Cambourg", ("NTA54",)),
        88: ("Fiche 55 · Bras-Madeleine", ("NTB55",)),
        91: ("Fiche 57 · Cambourg", ("NTB57",)),
        95: ("Fiche 59 · Les Orangers", ("NTB59",)),
    }
    limites = {}
    intertitre = re.compile(
        r"(?im)^[ \t]*((?:Hauteur des constructions|Emprise au sol[^:\n]*|"
        r"Implantation des constructions|Stationnement des véhicules automobiles|"
        r"Accès[^:\n]*stationnement|Qualité (?:urbaine|architecturale)[^:\n]*|"
        r"Traitement environnemental[^:\n]*)[ \t]*:|"
        r"[12]\)[ \t]*(?:Règles|Orientations)[^:\n]*:)")
    for n in [51, 52, 53, *range(82, 120)]:
        t = clean[n - 1]
        if n >= 97:
            # Une fiche par immeuble. Le numéro donne accès à la parcelle désignée.
            ref = f"Fiche d’immeuble Uap n°{n - 37}"
            cadastre = re.search(r"(?i)FICHE D[’']IMMEUBLE\s+([A-Z]{2}\s*\d+)", t)
            if cadastre:
                ref += " · " + cadastre.group(1)
            limites[page_off[n - 1]] = (ref, ("UAP",))
            continue
        if n in fiches:
            ref, secteurs = fiches[n]
            contexte = ""
            limites[page_off[n - 1]] = (ref, secteurs)
        for m in intertitre.finditer(t):
            titre = _norm(m.group(1)).rstrip(": ")
            if titre.startswith(("1)", "2)")):
                contexte = " · " + titre
                label = ref + contexte
            else:
                label = ref + contexte + " · " + titre
            limites[page_off[n - 1] + m.start()] = (label, secteurs)
    return limites


# Les deux éditions numérotent quatorze articles par chapitre. Un renvoi dans
# le corps ou l’une des trois rubriques imprimées au Port ne crée pas d’article.
_ARTICLE_CHAPITRE = re.compile(
    r"(?m)^[ \t]*(Article|ARTICLE)[ \t]+(1?AUindicée|AUst|2AU|U[1-6A-Za-z]*|A|N)"
    r"[ \t]*(\d+)[ \t]*[-–—]")
_SECTION_PORT = re.compile(
    r"(?im)^[ \t]*Section\s+[123]\s*:\s*(?:Destination des constructions,\s*usages des\s+"
    r"sols et natures d['’]activité|Caractéristiques urbaine,\s*architecturale,\s*"
    r"environnementale et paysagère|[ÉE]quipement et réseaux)[ \t]*$")


_RUBRIQUE_SUZANNE = re.compile(
    r"(?im)^[ \t]*(?:sous-)?section[ \t]+[0-9.]+[ \t]*:[^\n]*(?:\n[ \t]*constructions?[ \t]*$)?")


def _inventaire_trois_bassins(clean, page_off, head_ref):
    """Une fiche par édifice dans l'inventaire des pp. 96–108 (deux adresses par page)."""
    for i in range(95, 108):
        t, pos = clean[i], page_off[i]
        for m in re.finditer(r"(?im)^[ \t]*(?:MAISON|PATRIMOINE)[ \t]*$", t):
            adresse = re.search(r"ADRESSE POSTALE[ \t]*\n[ \t]*([^\n]+)", t[m.end():])
            if adresse:
                head_ref[pos + m.start()] = "Fiche patrimoniale · " + _norm(adresse[1])


def _split_articles(path: str) -> tuple[list[dict], bool]:
    """OUTIL-PLU-FIX-3/4 — l'extrait est l'ARTICLE ENTIER : d'un en-tête d'article au suivant, QUEL QUE
    SOIT le nombre de pages, avec ses sous-articles, ses « Toutefois… » et ses exceptions. JAMAIS coupé
    par une page ni par une taille. La PAGE est une donnée à part : `page_map` = suite de (offset dans le
    texte → page PDF), d'où `page_debut`/`page_fin` et, à la recherche, la page EXACTE du mot.

    GROS BLOCS (critère 3) : quand l'en-tête d'article suivant n'est pas détecté (scan), un bloc ≥ 6
    pages est re-découpé au NIVEAU QUI EXISTE (section/titre numéroté/sous-article/intertitre) ; la zone
    du bloc est conservée (un bloc ne contient jamais plusieurs zones). Ce qui reste > 10 pages (aucun
    niveau plus fin) est laissé entier et SIGNALÉ.

    Étiquette de zone (point 5) : d'ABORD l'en-tête de l'article (« ARTICLE N 1 » → N), ensuite la
    bannière de page. L'en-tête PRIME sur la bannière (corrige E2)."""
    import bisect
    insee = Path(path).name[:5]
    pages = _pages(path)
    ambigu = _pagination_ambigue(pages)       # détecté sur le texte brut (numéros imprimés)
    etang = Path(path).name == "97404_reglement_20250917.pdf"
    benoit = Path(path).name == "97410_reglement_20200206.pdf"
    petite_ile = Path(path).name == "97405_reglement_20230609.pdf"
    sainte_marie = Path(path).name == "97418_reglement_20251126.pdf"
    joseph = Path(path).name == "97412_Reglement_20251210.pdf"
    port = Path(path).name == "97407_reglement_20241209.pdf"
    edition = Path(path).name
    plaine = edition == "97406_reglement_20230527.pdf"
    denis = edition == "97411_reglement_20260805.pdf"
    suzanne = edition == "97420_reglement_20250929.pdf"
    tampon = edition == "97422_reglement_20230811.pdf"
    bassins = edition == "97423_reglement_20220602.pdf"
    sauts_de_page = etang or benoit or petite_ile or sainte_marie or joseph or port or plaine or denis or suzanne or tampon or bassins
    chapitres = {}
    ouvertures = set()
    if etang:
        # Le titre visuellement en haut est le dernier objet texte de la page.
        # Le replacer avant le préambule évite de couper le premier article en deux.
        for i, page in enumerate(pages):
            lines = page.rstrip().splitlines()
            if i >= 15 and lines and re.fullmatch(r"ZONE (?:AU|U[A-Z]*|A|N)", lines[-1].strip()):
                ouvertures.add(i)
                pages[i] = "\n".join([lines[-1], *lines[:-1]])
    if tampon:
        # La dernière ligne « règlement). » termine Ue3 et ressemble au pied courant.
        pages[72] = re.sub(r"(du présent)[ \t]*\n[ \t]*règlement\)\.", r"\1 règlement).", pages[72])
    clean, zbanner, sbanner = _clean_pages(pages, banniere_en_premiere_ligne=etang)
    if sauts_de_page:
        clean = [t.rstrip() + "\n" for t in clean]
    if suzanne:
        for i in range(9, len(clean)):
            clean[i] = _RUBRIQUE_SUZANNE.sub("", clean[i])
        for i in range(9, 28):
            sbanner[i] = ["UA", "UB", "UC"] if i < 19 else ["UE"]
    if port:
        for i, page in enumerate(clean):
            page = re.sub(r"(?im)^\s*\d+\s+PLU - Pièce écrite n°3[^\n]*", "", page)
            clean[i] = _SECTION_PORT.sub("", page) if 20 <= i < 177 else page
    if insee == "97403":
        # Le sommaire à points de suite reproduit sur plusieurs lignes les titres des articles.
        for i, page in enumerate(pages[:4]):
            if sum(bool(_TOC_LEADER.search(line)) for line in page.splitlines()) >= 3:
                clean[i] = ""
    livrets = _livret_par_page(pages)         # OUTIL-PLU-FIX-10 (LOT 3) — bassin de vie par page (Saint-Paul)
    starts, buf, pos = [], [], 0
    for i, t in enumerate(clean):
        starts.append((pos, i + 1)); buf.append(t); pos += len(t)
    flat = "".join(buf)
    page_off = [o for o, _ in starts]

    def page_of(off: int) -> int:
        j = bisect.bisect_right(page_off, off) - 1
        return starts[j][1] if j >= 0 else 1

    # en-têtes RÉELS (B3) : on écarte les renvois de prose, les faux « ZONE <mot/cadastre> » ET les
    # entrées de SOMMAIRE (points de suite, point 2 — sinon « ZONE N …119 » absorbe les dispositions
    # générales et les étiquette N).
    heads = [m for m in _HEADER.finditer(flat)
             if not _looks_cross_ref(flat, m.start()) and _valid_header(_norm(m.group(1)))
             and not _is_toc_header(flat, m.start())
             # OUTIL-PLU-FIX-10 (LOT 2) — « Zone UA : » énuméré sous une puce (valeur de hauteur) n'est
             # PAS un titre de chapitre : ne pas couper l'article (Sainte-Marie U8).
             and not (_norm(m.group(1)).upper().startswith("ZONE") and _looks_list_item(flat, m.start()))]
    head_ref = {m.start(): _norm(m.group(1)) for m in heads}
    if etang:
        # « Zone AUc » à l’intérieur de AU 2.2 est une ligne du barème.
        head_ref = {pos: ref for pos, ref in head_ref.items() if not ref.upper().startswith("ZONE ")}
    extra_header = {"97404": _ETANG_ART, "97402": _INDICE_ART, "97414": _INDICE_ART}.get(insee)
    if extra_header:
        for match in extra_header.finditer(flat):
            if not _is_toc_header(flat, match.start()):
                head_ref[match.start()] = _norm(match.group(1))
    # Les deux éditions ont des chapitres distincts avec des numéros d’article
    # identiques. La frontière se situe avant la présentation de la zone.
    if petite_ile:
        for n, zone in [(88, "1AU"), (99, "1AUZ"), (109, "AUE")]:
            chapitres[page_off[n - 1]] = zone
        motif = re.compile(r"(?im)^[ \t]*(ARTICLE)[ \t]+1[ \t]*(AUZ?)\.(\d+)\b")
        for m in motif.finditer(flat, page_off[87], page_off[108]):
            head_ref[m.start()] = f"ARTICLE 1{m[2].upper()}.{m[3]}"
    if sainte_marie:
        for n, zone in [(16, "U"), (29, "U"), (41, "AUINDICEE"), (44, "A"), (52, "N")]:
            chapitres[page_off[n - 1]] = zone
        for m in _INDICE_ART.finditer(flat, page_off[40], page_off[43]):
            head_ref[m.start()] = _norm(m[1])
        for i in range(15, 40):
            sbanner[i] = (["UA", "UB", "UC", "UD"] if i < 28 else
                          ["UEA", "UEC", "UEM", "UEP", "UR", "UT"])
    for pos, zone in chapitres.items():
        head_ref[pos] = next(line.strip() for line in flat[pos:].splitlines() if line.strip())
    # OUTIL-PLU-FIX-6 (point 2) — un titre de chapitre SANS zone (ANNEXES, DISPOSITIONS GÉNÉRALES,
    # DÉFINITIONS, LEXIQUE, TITRE liminaire) est une FRONTIÈRE de bloc : l'annexe forme son PROPRE bloc
    # (zone None), au lieu d'être avalée par le bloc de zone précédent (Saint-Benoît annexes AU/N → UE).
    # OUTIL-PLU-FIX-8 (LOT 1) — zone d'un en-tête d'article/zone (pour distinguer un intertitre INTERNE
    # d'un vrai chapitre) : l'en-tête d'abord, sinon la bannière de sa page.
    def _head_zone(pos: int, ref: str) -> str | None:
        zm = _ZONE_FROM_ART.match(ref or "") or _ZONE_FROM_ZONE.match(ref or "")
        return (_valid_zone(zm.group(1)) if zm else None) or zbanner[page_of(pos) - 1]
    _hard = sorted(head_ref.items())                 # en-têtes RÉELS (articles/zones), avant resets
    _hpos = [p for p, _ in _hard]
    reset_at: set[int] = set()
    for m in _RESET_CHAP_M.finditer(flat):
        if _is_toc_header(flat, m.start()) or not _reset_is_title(_norm(m.group(1))):
            continue
        # Un titre de reset n'est une FRONTIÈRE DE CHAPITRE que s'il sépare de VRAIS chapitres. S'il tombe
        # ENTRE DEUX EN-TÊTES D'ARTICLE DE LA MÊME ZONE, c'est un INTERTITRE de l'article (« Définition »,
        # « Perméabilité »… sous l'article 13 de Saint-Paul), pas un nouveau chapitre : le couper détachait
        # l'article 13 (zones U1, U2e, U3e, AU5e) et son seuil de 20 % dans un extrait « Définition » SANS
        # zone (régression introduite dès FIX-6). On ne coupe donc pas dans ce cas.
        i = bisect.bisect_left(_hpos, m.start())
        prev = _hard[i - 1] if i > 0 else None
        nxt = _hard[i] if i < len(_hard) else None
        if (prev and nxt and re.match(r"(?i)^article\b", prev[1]) and re.match(r"(?i)^article\b", nxt[1])):
            zp, zn = _head_zone(*prev), _head_zone(*nxt)
            if zp and zp == zn:
                continue                             # intertitre interne à l'article → pas une frontière
        head_ref[m.start()] = _norm(m.group(1))[:60]
        reset_at.add(m.start())
    if joseph or port:
        debut, annexe = (14, 136) if joseph else (21, 178)
        lo, hi = page_off[debut - 1], page_off[annexe - 1]
        head_ref = {pos: ref for pos, ref in head_ref.items() if not lo <= pos < hi}
        for m in _ARTICLE_CHAPITRE.finditer(flat, lo, hi):
            head_ref[m.start()] = f"{m[1]} {m[2]} {m[3]}"
        # Repartir des pages brutes : _clean_pages retire la bannière ZONE U5
        # au même titre qu’un en-tête courant, mais sa page ouvre le préambule.
        ouverture = re.compile(r"(?im)^[ \t]*(?:La zone|ZONE) (1AU|2AU|AUindicée|AUst|U\w*|A|N)[ \t]*$")
        for i in range(debut - 1, annexe - 1):
            m = ouverture.search(pages[i])
            if m:
                pos = page_off[i]
                zone = m[1].upper().replace("É", "E")
                chapitres[pos] = zone
                head_ref[pos] = ("Caractère de la zone " + m[1] if joseph else "La zone " + m[1])
            elif joseph and i + 1 in (101, 112, 124):
                head_ref[page_off[i]] = "Titre intercalaire"
        head_ref[hi] = "Annexe" if joseph else "Protections patrimoniales"
    if plaine:
        # La p. 169 quitte les citations littérales du règlement pour le rapport
        # de présentation. Les rubriques 4.3.1 à 4.3.4 expliquent les changements.
        for i in range(168, 176):
            pos = page_off[i]
            for m in re.finditer(r"(?m)^[ \t]*((?:[3-5]/|[34]\.\d+(?:\.\d+)?\.)[^\n]+)", clean[i]):
                head_ref[pos + m.start()] = _norm(m[1])
        head_ref[page_off[168]] = "Échéancier fixé par les orientations d’aménagement"
    if denis:
        # P. 124 : les arrêtés sur les captages et forages ont leur propre périmètre.
        head_ref[page_off[123]] = "Annexes relatives aux captages et forages"
        for pos, ref in list(head_ref.items()):
            if ref == "Zone A" and re.match(r"(?i)\s*zone A urbaniser", flat[pos:pos+45]):
                # Le code du chapitre est imprimé dans la bannière (AUa, p. 106).
                zone = zbanner[page_of(pos) - 1]
                if zone and zone.startswith("AU"):
                    chapitres[pos] = zone
                    head_ref[pos] = "Caractère de la zone " + zone
    if suzanne:
        for m in _INDICE_ART.finditer(flat, page_off[28], page_off[31]):
            head_ref[m.start()] = _norm(m[1])
        for n, zone in [(20, "UE"), (29, "AUINDICEE"), (32, "A")]:
            pos = page_off[n - 1]
            # Le titre et le tableau de présentation précèdent le premier article.
            for h in list(head_ref):
                if pos <= h < pos + len(clean[n - 1]) and head_ref[h].lower().startswith("titre "):
                    del head_ref[h]
            chapitres[pos] = zone
            head_ref[pos] = "Présentation du chapitre " + zone
    if bassins:
        # Le long intitulé de l’article 12 se termine à la ligne suivante.
        for m in _INDICE_ART.finditer(flat, page_off[63], page_off[70]):
            head_ref[m.start()] = _norm(m[1])
        lo, hi = page_off[94], page_off[111]
        head_ref = {pos: ref for pos, ref in head_ref.items() if not lo <= pos < hi}
        for m in re.finditer(r"(?m)^(?:SERVITUDE LE LONG DES RIVIERES|AMENAGEMENT DES VOIRIES)[^\n]*", clean[94]):
            head_ref[lo + m.start()] = _norm(m[0])
        for i in (94, 95, 100, 108, 111):
            head_ref[page_off[i]] = next((l.strip() for l in clean[i].splitlines() if l.strip()), "Annexe")
        _inventaire_trois_bassins(clean, page_off, head_ref)
    # frontières = en-têtes d'article/zone + titres de chapitre sans zone (jamais les frontières de page).
    bounds = sorted(set(head_ref) | {len(flat)})
    # OUTIL-PLU-FIX-14 (LOT 5) — frontières DURES entre le règlement de base et les dossiers de modification
    # CONCATÉNÉS dans le même PDF (La Plaine : p.1-117 règlement, p.118 mai 2023, p.150 février 2019, p.177
    # avril 2016). Aucun extrait ne doit enjamber un acte : « ARTICLE UB 14 » (p.149) ouvrait la couverture
    # février 2019 p.150 ; un bloc p.176-199 incorporait le dossier 2016. On coupe au DÉBUT de la 1re page de
    # chaque dossier (et juste après le règlement de base).
    import os as _os
    _dcfg = _dossiers_map().get(_os.path.basename(path)[:5])
    if _dcfg:
        _fronts = {d["a"] for d in _dcfg["dossiers"]} | {int(_dcfg["reglement_pages"][1]) + 1}
        bounds = sorted(set(bounds) | {page_off[p - 1] for p in _fronts if 1 <= p <= len(clean)})
    if etang:
        # Un préambule a son propre extrait, même si sa bannière a été retirée.
        for i in ouvertures:
            head_ref[page_off[i]] = None
        bounds = sorted(set(bounds) | {page_off[i] for i in ouvertures})
    fiches = {}
    if benoit:
        fiches = _fiches_benoit(clean, page_off)
        # Les règles de chaque annexe restent groupées par fiche et par rubrique imprimée.
        for debut, suivant in [(51, 54), (82, 120)]:
            lo, hi = page_off[debut - 1], page_off[suivant - 1]
            head_ref = {p: ref for p, ref in head_ref.items() if not lo <= p < hi}
            bounds = [p for p in bounds if not lo <= p < hi] + [hi]
        head_ref.update({p: ref for p, (ref, _) in fiches.items()})
        bounds = sorted(set(bounds) | set(fiches) | {page_off[31], page_off[148], page_off[151]})
        # Les mentions « Zone AU n°… » sont des lignes de la liste des ER.
        lo, hi = page_off[148], page_off[151]
        for pos in list(head_ref):
            if lo <= pos < hi:
                del head_ref[pos]
        head_ref[lo] = "Liste des emplacements réservés"
        head_ref[hi] = "Schémas relatifs aux voiries"
        bounds = sorted({p for p in bounds if not lo < p < hi} | {lo, hi})
    head_pos = sorted(head_ref)

    _UNSET = object()

    def _emit(a: int, b: int, ref: str | None, zone=_UNSET) -> dict | None:
        if sauts_de_page:
            # Les blancs avant l’en-tête suivant ne font pas partie de l’article.
            b = a + len(flat[a:b].rstrip())
        raw = flat[a:b]
        texte = raw.strip()
        if not texte:
            return None
        if etang and page_of(a) in (14, 73, 87, 97) and page_of(b - 1) == page_of(a):
            return None  # couvertures des titres II à V, sans prescription
        if joseph and (ref == "Titre intercalaire" or page_of(a) == page_of(b - 1) == 13):
            return None
        if petite_ile and page_of(a) == page_of(b - 1) == 87:
            return None  # page intercalaire du titre 3, avant les deux chapitres
        letters = len(re.sub(r'[^0-9A-Za-zÀ-ÿ]', '', texte))
        is_zone_title = bool(ref) and ref.upper().startswith("ZONE")
        # entrée de SOMMAIRE (points de suite « ZONE AU1 …… 3 ») ou titre de zone nu : pas un extrait.
        if (is_zone_title and letters < 40) or (texte.count('.') > letters and letters < 40):
            return None
        if zone is _UNSET:
            if ref and _RESET_CHAP.match(ref):
                zone = None                      # chapitre SANS zone (annexe, dispositions générales…)
            else:
                # PRIORITÉ (points 5 / E2) : l'EN-TÊTE DE L'ARTICLE d'abord (« ARTICLE N 1 » → N), sinon la
                # bannière de la page de début. Pas de « zone de chapitre » héritée du sommaire.
                zm = _ZONE_FROM_ART.match(ref or "") or _ZONE_FROM_ZONE.match(ref or "")
                z_ref = _valid_zone(zm.group(1)) if zm else None
                if z_ref is None:                 # OUTIL-PLU-FIX-8 (LOT 3) — code à chiffre de tête (2AU, 1AU)
                    mnum = _ZONE_FROM_ART_NUM.match(ref or "")
                    z_ref = _valid_zone(mnum.group(1)) if mnum else None
                if insee == "97404" and ref and _ETANG_ART.match(flat, a):
                    z_ref = _valid_zone(ref.split()[0])
                zone = z_ref or zbanner[page_of(a) - 1]
        if zone is None:                          # OUTIL-PLU-FIX-7 (point 1) — fiche/annexe zonée → sa zone
            zone = _zone_de_fiche(texte) or _zone_de_preambule(texte)   # LOT 3 — préambule de zone
        # OUTIL-PLU-FIX-10 (LOT 1) — article du chapitre « ZONE AU indicée » → sentinelle AUINDICEE
        # (prime sur toute bannière, ex. Cilaos dont la bannière AUST fuyait sur ces articles).
        if ref and _AUINDICEE_ART.search(_norm(ref)):
            zone = "AUINDICEE"
        if benoit and page_of(a) in (149, 150, 151, 152):
            zone = None
        pg0 = page_of(a)
        if (port and pg0 < 21) or (joseph and pg0 >= 136):
            zone = None  # inventaire des zones / annexes, hors chapitres réglementaires
        if (plaine and 169 <= pg0 <= 176) or (bassins and pg0 >= 95) or (denis and pg0 >= 124):
            zone = None
        if a in chapitres:
            zone = chapitres[a]
        if petite_ile and 88 <= pg0 <= 108:
            zone = "1AU" if pg0 < 99 else "1AUZ"
        if petite_ile and pg0 == 167:
            zone = "UEA"  # annexe 4, croquis de l’article UEa.6
        lead = len(raw) - len(raw.lstrip())
        pmap = [[0, pg0]]                        # page_map : offset dans `texte` → page PDF
        for o in page_off:
            if a < o < b:
                off = o - a - lead
                p = page_of(o)
                if off >= 0 and p != pmap[-1][1]:
                    pmap.append([off, p])
        net = len(re.sub(r'\s', '', texte))
        _secs = sbanner[pg0 - 1] if 0 < pg0 <= len(sbanner) else None
        return {"article_ref": ref, "zone": zone, "page_pdf": pg0,
                "page_debut": pg0, "page_fin": page_of(b - 1), "page_map": pmap,
                "livret": livrets[pg0 - 1] if 0 < pg0 <= len(livrets) else None,
                # OUTIL-PLU-FIX-11 (LOT 2) — secteurs régis par le chapitre mutualisé (bannière retirée),
                # pour que `_filtre_scope` sache qu'un « Article U 12 » ne concerne pas UE.
                "secteurs": ",".join(_secs) if _secs else None,
                "texte": texte, "doute": net < 25,
                "doute_motif": "extrait quasi vide — page peut-être illisible/scannée, à vérifier au PDF" if net < 25 else None}

    def _emit_block(a: int, b: int, ref: str | None) -> list[dict]:
        """Émet l'article [a,b) ; si c'est un GROS BLOC (≥ seuil pages), le re-découpe au niveau interne
        existant (critère 3), en conservant SA zone (un bloc = une zone)."""
        e = _emit(a, b, ref)
        if not e:
            return []
        if petite_ile and ref and ref.upper().startswith("SECTION") and 88 <= e["page_debut"] <= 108:
            if len(e["texte"].strip().splitlines()) == 1:
                return []
        if insee == "97410" and ref and ref.lower().startswith("section"):
            lines = [line.strip() for line in e["texte"].splitlines() if line.strip()]
            if lines and all(_SECTION_SEULE.fullmatch(line) for line in lines):
                return []
        if (joseph or port) and ref and _ARTICLE_CHAPITRE.match(e["texte"]):
            return [e]
        if e["page_fin"] - e["page_debut"] < _BLOC_SEUIL_PAGES:
            return [e]                           # article normal : entier (D1 préservé)
        # OUTIL-PLU-FIX-7 (point 4) — on ne re-découpe QU'aux vraies LIGNES DE TITRE : capitales dominantes
        # ou ligne courte. Sinon un intertitre RÉCURRENT minuscule (« 1) Règles devant être appliquées
        # strictement », Saint-Benoît) fragmentait le bloc 21×. On dédoublonne aussi les titres identiques
        # (élément de page répété ≠ nouvelle section).
        subs, seen = [], set()
        for m in _SUBHEAD.finditer(flat, a + 1, b):
            hl = _norm(flat[m.start():min(b, m.start() + 90)].splitlines()[0]) if flat[m.start():b].strip() else ""
            if not _subhead_titre(hl) or hl[:60] in seen:
                continue
            seen.add(hl[:60]); subs.append(m.start())
        if not subs:
            return [e]                           # aucun niveau plus fin : laissé entier (signalé)
        cuts = sorted({a} | set(subs) | {b})
        pieces = []
        for x, y in zip(cuts, cuts[1:]):
            if x == a:
                sref = ref
            else:
                head_line = _norm(flat[x:min(y, x + 90)].splitlines()[0]) if flat[x:y].strip() else ""
                sref = head_line[:60] or ref
            pe = _emit(x, y, sref, zone=e["zone"])   # zone du bloc conservée (point 4)
            if pe:
                pieces.append(pe)
        return pieces or [e]

    out: list[dict] = []
    first = head_pos[0] if head_pos else len(flat)
    # préambule avant le 1er en-tête (dispositions générales) : gardé seulement s'il est substantiel.
    out.extend(e for e in _emit_block(0, first, None) if len(re.sub(r'\s', '', e["texte"])) >= 200)
    for a in head_pos:
        j = bisect.bisect_right(bounds, a)
        b = bounds[j] if j < len(bounds) else len(flat)
        if a in fiches:
            ref, secteurs = fiches[a]
            for secteur in secteurs:
                morceau = _emit(a, b, ref, zone=secteur)
                if morceau:
                    morceau["secteurs"] = secteur
                    out.append(morceau)
        else:
            out.extend(_emit_block(a, b, head_ref[a]))
    if benoit:
        # Le commentaire est conservé séparément et ne participe pas à la recherche de règles.
        with fitz.open(path) as doc:
            explication = doc[29].get_text("text", clip=fitz.Rect(447, 132, 810, 550)).strip()
        out.append({"article_ref": _EXPLICATION_AU12, "zone": None, "page_pdf": 30, "page_debut": 30,
                    "page_fin": 30, "page_map": [[0, 30]], "livret": None, "secteurs": None,
                    "texte": explication, "doute": False, "doute_motif": None})
    return _dedup(_fusionne_titres(out)), ambigu


def _dedup(pieces: list[dict]) -> list[dict]:
    """OUTIL-PLU-FIX-8 (LOT 2) — supprime les extraits DOUBLONS octet-pour-octet : le règlement réédite le
    même article générique dans plusieurs livrets/bassins de vie avec la MÊME étiquette de zone (Saint-Paul
    « Article 7- » USDU ×4, etc.) → l'utilisateur voyait N fois la même règle sous le même filtre. On garde
    la 1re occurrence. La clé est (zone, texte) : un texte IDENTIQUE servi sous une AUTRE zone n'est PAS un
    doublon (filtre différent) et est CONSERVÉ — aucune règle n'est perdue. Les résultats restent dans
    l'ordre du document."""
    # La clé NORMALISE les blancs (le même article réédité d'un livret à l'autre diffère parfois d'un
    # espace / saut de page résiduel : « Article 13- USDU » ×3 = 5256/5254/5254 car. → 1 seul une fois les
    # blancs réduits). On compare donc sur le texte à blancs normalisés ; un texte SUBSTANTIELLEMENT
    # différent sous la même (réf,zone) — ex. « Article 7- U1 » 4262 vs 3620 car. — reste DISTINCT, conservé.
    # OUTIL-PLU-FIX-10 (LOT 3) — le LIVRET entre dans la clé : les articles d'une zone RÉÉDITÉS d'un bassin
    # de vie à l'autre (Saint-Paul : Usdu « Article 12- » à La Plaine p.200, La Saline p.246, Guillaume
    # p.306) ne sont PLUS dédoublonnés — chacun reste accessible avec son livret et sa page. Le doublon
    # octet-pour-octet DANS un même livret (vraie redite d'extraction) reste supprimé.
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in pieces:
        k = (e.get("zone"), e.get("livret"), re.sub(r'\s+', ' ', e.get("texte") or "").strip())
        if (e.get("article_ref") or "").startswith("Fiche patrimoniale · "):
            k += (e["page_pdf"],)  # mêmes mots, photographies et pages distinctes
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def _fusionne_titres(pieces: list[dict]) -> list[dict]:
    """OUTIL-PLU-FIX-5 (point 2) — un titre sur PLUSIEURS LIGNES (« TITRE III / DISPOSITIONS /
    APPLICABLES AUX ZONES / À URBANISER ») était éclaté en extraits d'un mot (227 quasi vides). On
    REFOND chaque fragment de titre (quasi vide, majoritairement en CAPITALES) dans l'extrait suivant,
    dont il devient l'en-tête ; un titre sans contenu à la fin est abandonné (non indexé). Cible : 0
    extrait sans contenu."""
    def est_titre(e: dict) -> bool:
        t = e.get("texte") or ""
        net = len(re.sub(r'\s', '', t))
        if net >= 50:
            return False
        ref = (e.get("article_ref") or "")
        if re.match(r'(?i)^article\s', ref):
            return False                          # un VRAI article court (« UB 9 : Sans objet ») n'est
            #                                       PAS un fragment de titre (sinon UB 9 fond dans UB 10).
        if re.match(r'(?i)^(section|chapitre|titre|sous-section)\b', ref):
            return True                           # titre de section nu → refondu dans la suite
        letters = [c for c in t if c.isalpha()]
        return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.6
    res: list[dict] = []
    pending: list[dict] = []
    for e in pieces:
        if est_titre(e):
            pending.append(e)
            continue
        if pending:
            pre = "\n".join(p["texte"] for p in pending)
            shift = len(pre) + 1
            e = dict(e)
            e["texte"] = pre + "\n" + e["texte"]
            e["page_debut"] = pending[0]["page_debut"]
            e["page_pdf"] = pending[0]["page_pdf"]
            e["page_map"] = [[0, pending[0]["page_debut"]]] + [[int(o) + shift, pg] for o, pg in e["page_map"]]
            e["article_ref"] = pending[0]["article_ref"] or e["article_ref"]
            e["doute"] = len(re.sub(r'\s', '', e["texte"])) < 25
            pending = []
        res.append(e)
    # un extrait SANS contenu (net < 40) qui n'est pas un vrai « Article … » (ligne de section nue,
    # ligne de table d'adresses d'annexe…) n'est PAS indexé (cible 0, point 2).
    return [e for e in res
            if len(re.sub(r'\s', '', e.get("texte") or "")) >= 40
            or re.match(r'(?i)^article\s', e.get("article_ref") or "")]


def ensure_fts_config(session: Session) -> None:
    """OUTIL-PLU-FIX-1 (LOT 5) — config FTS `fr_unaccent` = français + unaccent. Corrige DEUX défauts
    mesurés : la base est en locale C → to_tsvector('french','CLÔTURE') rend 'clÔtur' (le Ô accentué
    n'est PAS mis en minuscule) ; et 'clôtur' ≠ 'clotur' (accent). unaccent replie les deux :
    clôture = CLÔTURE = cloture = CLOTURE → 'clotur'. Idempotent (créée si absente)."""
    if session.execute(text("SELECT 1 FROM pg_ts_config WHERE cfgname='fr_unaccent'")).scalar():
        return
    session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    session.execute(text("CREATE TEXT SEARCH CONFIGURATION fr_unaccent ( COPY = french )"))
    session.execute(text(
        "ALTER TEXT SEARCH CONFIGURATION fr_unaccent "
        "ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part, "
        "numword, numhword, hword_numpart WITH unaccent, french_stem"))


def ensure_ddl(session: Session) -> None:
    if session.info.get("plu_data_only"):
        return
    for stmt in _DDL.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))
    ensure_fts_config(session)


def ingest_reglement(session: Session, *, insee: str, commune: str, idurba: str, millesime: str | None,
                     document: str, pdf_path: str, source_url: str, fetched_at: str | None,
                     pdf_url: str | None = None, commit: bool = True, log=lambda *_: None) -> dict:
    """Ré-ingère (idempotent) les extraits article d'un document. Purge (insee, document) puis insère.
    `source_url` = pack intégral (.zip) ; `pdf_url` = règlement écrit direct (.pdf) — LOT 2."""
    ensure_ddl(session)
    extraits, ambigu = _split_articles(pdf_path)
    _applique_dossiers(insee, extraits)          # OUTIL-PLU-FIX-13 — étiquette dossiers + modif non intégrée
    session.execute(text("DELETE FROM plu_reglement_extrait WHERE insee = :i AND document = :d"),
                    {"i": insee, "d": document})
    for e in extraits:
        session.execute(text("""
            INSERT INTO plu_reglement_extrait
              (insee, commune, idurba, millesime, document, zone, article_ref, page_pdf,
               page_debut, page_fin, page_map, livret, secteurs, dossier, modif_note, texte_verbatim, doute,
               doute_motif, pagination_ambigue, source_url, pdf_url, fetched_at, tsv)
            VALUES
              (:insee, :commune, :idurba, :millesime, :document, :zone, :article_ref, :page_pdf,
               :page_debut, :page_fin, CAST(:page_map AS jsonb), :livret, :secteurs, :dossier, :modif_note,
               :texte, :doute, :doute_motif, :ambigu, :url, :pdf_url, :fetched_at,
               to_tsvector('fr_unaccent',
                 coalesce(:article_ref,'') || ' ' || coalesce(:zone,'') || ' ' || :texte))
        """), {"insee": insee, "commune": commune, "idurba": idurba, "millesime": millesime,
               "document": document, "zone": e["zone"], "article_ref": e["article_ref"],
               "page_pdf": e["page_pdf"], "page_debut": e.get("page_debut", e["page_pdf"]),
               "page_fin": e.get("page_fin", e["page_pdf"]),
               "page_map": _json.dumps(e.get("page_map") or [[0, e["page_pdf"]]]),
               "livret": e.get("livret"), "secteurs": e.get("secteurs"),
               "dossier": e.get("dossier"), "modif_note": e.get("modif_note"),
               "texte": e["texte"], "doute": e["doute"],
               "doute_motif": e["doute_motif"], "ambigu": ambigu, "url": source_url,
               "pdf_url": pdf_url, "fetched_at": fetched_at})
    if commit:
        session.commit()
    n_doute = sum(1 for e in extraits if e["doute"])
    log(f"  ✓ {insee} {document} : {len(extraits)} extraits article"
        + (f" · {n_doute} douteux" if n_doute else "")
        + (" · PAGINATION AMBIGUË" if ambigu else ""))
    return {"insee": insee, "document": document, "extraits": len(extraits),
            "doutes": n_doute, "pagination_ambigue": ambigu}


def purge_commune_extraits(session: Session, insee: str, *, commit: bool = False,
                           log=lambda *_: None) -> int:
    """Purge TOUS les extraits d'une commune, par INSEE (quel que soit le nom du document).

    Corrige l'orphelinage au bump de millésime : le nom du document est daté (`..._YYYYMMDD.pdf`),
    donc il CHANGE d'un millésime à l'autre. Purger par (insee, document) — ce que fait
    `ingest_reglement` — laissait alors l'ancien millésime en base (orphelins). On purge ici par le
    seul INSEE, stable. GARDE-FOU 974 : refuse tout INSEE hors Réunion pour qu'une erreur d'appel ne
    puisse jamais déclencher un DELETE de masse. Ne committe pas par défaut (appelé dans une
    transaction unique par `ingest_commune_reglements`)."""
    if not insee or not str(insee).startswith("974"):
        raise ValueError(f"purge_commune_extraits : INSEE hors 974 refusé ({insee!r}) — garde-fou")
    ensure_ddl(session)
    res = session.execute(text("DELETE FROM plu_reglement_extrait WHERE insee = :i"), {"i": insee})
    n = res.rowcount or 0
    if commit:
        session.commit()
    log(f"  ✓ purge {insee} : {n} extrait(s) supprimé(s)")
    return n


def ingest_commune_reglements(session: Session, *, insee: str, commune: str, idurba: str,
                              millesime: str | None, documents: list[dict], source_url: str,
                              fetched_at: str | None, pdf_url: str | None = None, commit: bool = True,
                              log=lambda *_: None) -> dict:
    """Ré-ingère TOUS les documents (multi-volume) d'une commune en UNE transaction.

    Purge par INSEE UNE seule fois (cf. `purge_commune_extraits` : ferme l'orphelinage au bump de
    millésime), PUIS insère chaque volume dans l'ordre fourni. `documents` = liste de
    `{"name": <nom du document>, "path": <chemin PDF>}`. Chaque insertion réutilise `ingest_reglement`
    (parseur unique) avec `commit=False` : sa purge (insee, document) interne devient un no-op (tout a
    déjà été purgé par INSEE) et tout est validé d'un bloc à la fin. Ainsi le bump de millésime ne
    laisse jamais d'ancien document derrière lui, et l'ingestion multi-volume est conservée."""
    ensure_ddl(session)
    purge_commune_extraits(session, insee, commit=False, log=log)
    resultats = []
    for d in documents:
        r = ingest_reglement(
            session, insee=insee, commune=commune, idurba=idurba, millesime=millesime,
            document=d["name"], pdf_path=d["path"], source_url=source_url, pdf_url=pdf_url,
            fetched_at=fetched_at, commit=False, log=log)
        resultats.append(r)
    if commit:
        session.commit()
    total = sum(r["extraits"] for r in resultats)
    log(f"  ✓ {insee} {commune} : {len(documents)} document(s), {total} extrait(s) (1 transaction)")
    return {"insee": insee, "commune": commune, "documents": len(documents),
            "extraits": total, "detail": resultats}


def _classe_token(zone: str) -> str:
    """Préfixe de CLASSE d'un code (chiffres optionnels + U/AU/A/N), ex. AU3ST→'AU', 2AUd→'2AU', Ua→'U'."""
    m = re.match(r'^(\d*)(AU|U|A|N)', _norm(zone).upper())
    return (m.group(1) + m.group(2)) if m else _norm(zone).upper()


def _sans_prefixe_chiffre(zone: str) -> str | None:
    """OUTIL-PLU-FIX-9 (point 1) — libellé de la zone SANS son préfixe de PHASAGE (1AUto→AUto, 2AUa→AUa).
    Le plan de zonage numérote les phases d'ouverture (1AU/2AU/3AU) ; le RÈGLEMENT écrit, lui, ne tient
    souvent qu'UN chapitre pour la famille (« ZONE AUto » servie sous le libellé AUTO à Sainte-Rose).
    None si le retrait ne change rien (pas de préfixe)."""
    s = _norm(zone)
    stripped = re.sub(r'^\d+', '', s)
    return stripped if stripped and stripped.upper() != s.upper() else None


def _renvoi_texte(session: Session, zone: str, insee: str | None) -> str | None:
    """OUTIL-PLU-FIX-9 (point 1) — cible d'un renvoi EXPRIMÉ DANS LE TEXTE du règlement quand la zone
    n'a pas de chapitre propre : « …pour la zone AUt, (il convient de) se reporter au règlement de la
    zone Ua ». On lit le libellé TEL QU'ÉCRIT (phasage retiré : 1AUt→AUt). Vérifié sur pièce :
    Bras-Panon AUt→Ua (p.80), Trois-Bassins AUt→Ub (p.66-70), Le Tampon AUto→Ucto (p.86-89)."""
    if not insee:
        return None
    strip = _sans_prefixe_chiffre(zone) or _norm(zone)
    if not strip:
        return None
    rx = re.compile(r'(?i)zones?\s+' + re.escape(strip) + r'\b[^.]{0,90}?'
                    r'report\w+\s+au\s+r[èe]glement\s+de\s+la\s+zone\s+'
                    r'([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,6})')
    rows = session.execute(text(
        "SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee = :i AND texte_verbatim ILIKE :l"),
        {"i": insee, "l": f"%zone {strip}%"}).scalars().all()
    for t in rows:
        m = rx.search(t or "")
        if m:
            z = _valid_zone(m.group(1))
            if z and z != _valid_zone(strip):      # jamais un renvoi circulaire vers soi-même
                return z
    return None


def _renvoi_cible(zone: str, insee: str | None, session: Session | None = None) -> str | None:
    """OUTIL-PLU-FIX-6/9 (point 1) — cible du RENVOI réglementaire d'un secteur (Saint-Paul AU3c→U3c,
    Le Tampon 2AUd→Ud) via `resolve_zone` : la MÊME résolution que la fiche parcelle (config/
    plu_destinations + patterns AU→U), pas une seconde table ; à DÉFAUT, le renvoi lu DANS le texte du
    règlement (`_renvoi_texte`). None si la zone n'est pas un renvoi."""
    if not insee:
        return None
    try:
        from ..faisabilite.zonage import resolve_zone
        zr = resolve_zone(zone, insee)
        m = re.search(r'règles de (\S+)', getattr(zr, "via_renvoi", None) or "")
        if m:
            return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    if session is not None:
        return _renvoi_texte(session, zone, insee)
    return None


def _zone_u_equivalente(zone: str) -> str | None:
    """OUTIL-PLU-FIX-8 (LOT 3) — zone U « de même indice » d'une zone À URBANISER (clause standard des
    PLU réunionnais : « pour une zone AU, se reporter au règlement de la zone U de même indice »). On
    retire le préfixe à chiffre et on remplace la classe AU par U, en gardant l'indice : AUa→Ua,
    1AUa→Ua, 2AUb→Ub, 1AU3→U3, AUb1→Ub1. None si la zone n'est pas une zone AU."""
    m = re.match(r'(?i)^\d*AU(.*)$', _norm(zone))
    return ("U" + m.group(1)) if m else None


def zone_renvoi_note(zone: str, insee: str | None, session: Session | None = None) -> str | None:
    """Phrase à afficher quand le filtre d'un secteur ouvre les articles de sa zone de renvoi. Le renvoi
    CONFIGURÉ (resolve_zone) prime ; à défaut, le renvoi GÉNÉRIQUE AU→U de même indice est annoncé LORSQU'IL
    sert réellement (la zone AU n'a pas de chapitre propre mais la zone U de même indice est, elle, servie)."""
    # OUTIL-PLU-FIX-10 (LOT 1) — zone AU indicée sectorielle servie par son chapitre générique propre.
    if (insee and _AU_SECTEUR.match(_norm(zone)) and session is not None
            and not _chapitre_propre(session, zone, insee) and _a_chapitre_auindicee(session, insee)):
        indice = _indice_urbain_ecrit(zone, insee)
        if indice:
            return f"{zone} : chapitre AU indicée et articles de la zone {indice} citée par renvoi."
        return (f"{zone} : articles du chapitre « AU indicée » du règlement — chaque article donne la "
                f"règle propre à {zone} ou renvoie expressément à une autre zone (indiqué dans le texte).")
    cible = _renvoi_cible(zone, insee, session)
    if cible:
        return f"{zone} : le règlement renvoie à {cible}"
    if session is not None and not _chapitre_propre(session, zone, insee):
        # phasage : la zone de plan partage le chapitre de la famille écrit sans préfixe (1AUto → AUto)
        strip = _sans_prefixe_chiffre(zone)
        if strip:
            scands = {c.upper() for c in zone_candidats(strip)}
            stored = {z.upper() for z in session.execute(text(
                "SELECT DISTINCT zone FROM plu_reglement_extrait WHERE zone IS NOT NULL AND insee = :i"),
                {"i": insee}).scalars().all() if z}
            if scands & stored:
                return f"{zone} : articles de la zone {strip} (phasage du plan de zonage)"
        ueq = _zone_u_equivalente(zone)
        za = zones_apparentees(session, zone, insee)
        if ueq and za:
            # OUTIL-PLU-FIX-14 (LOT 2, F) — le bandeau doit dire la PROVENANCE RÉELLE des cartes. On
            # n'annonce « renvoie à la zone U de même indice » QUE si les cartes servies sont bien de la
            # famille U. Si elles viennent du chapitre AU propre (Le Port « 1AU » indicée servant 1AUmut/
            # 1AUc ; Saint-Benoît « AU » servant AUb10/AUb15), le bandeau annonçait Umut/Uc/Ub10/Ub15 alors
            # que l'écran sert des articles AU → faux. On décrit alors le chapitre AU réellement servi.
            ueq_fam = {c.upper() for c in zone_candidats(ueq)}
            if set(za) & ueq_fam:
                return (f"{zone} (zone à urbaniser) : le règlement renvoie au règlement de la zone {ueq} "
                        f"de même indice — articles de {ueq} servis ci-dessous.")
            fam = za[0]
            return (f"{zone} : articles du chapitre « {fam} » du règlement — chaque article donne la règle "
                    f"propre à {zone} ou renvoie expressément à une autre zone (indiqué dans le texte).")
    return None


def _chapitre_propre(session: Session, zone: str, insee: str | None) -> bool:
    """Vrai si la zone a un chapitre PROPRE stocké (un code apparenté AU-DELÀ de la classe nue)."""
    cands = {c.upper() for c in zone_candidats(zone)} - {_classe_token(zone).upper()}
    if not cands:
        return False
    sql = "SELECT 1 FROM plu_reglement_extrait WHERE zone IS NOT NULL AND upper(zone) = ANY(:z)"
    params: dict = {"z": sorted(cands)}
    if insee:
        sql += " AND insee = :i"; params["i"] = insee
    return session.execute(text(sql + " LIMIT 1"), params).first() is not None


# OUTIL-PLU-FIX-10 (LOT 1) — zone AU INDICÉE sectorielle : classe AU (préfixe de phase optionnel) SUIVIE
# d'un secteur (AUt, AUec, 1AUa…). Les AU « nus » (AU, 1AU, 2AU — Le Port, Petite-Île) sont exclus : ils
# ont leur propre chapitre, pas le chapitre générique « AU indicée ».
_AU_SECTEUR = re.compile(r'(?i)^\d*AU.+')


def _a_chapitre_auindicee(session: Session, insee: str | None) -> bool:
    """La commune a-t-elle le chapitre générique « ZONE AU indicée » (sentinelle AUINDICEE) ?"""
    sql = "SELECT 1 FROM plu_reglement_extrait WHERE upper(zone) = 'AUINDICEE'"
    params: dict = {}
    if insee:
        sql += " AND insee = :i"; params["i"] = insee
    return session.execute(text(sql + " LIMIT 1"), params).first() is not None


def _indice_urbain_ecrit(zone: str, insee: str | None) -> str | None:
    # Sainte-Marie, chap. V p. 41 et Saint-Joseph, chap. AU indicée p. 106.
    # AUto/AUtok ont leurs propres barèmes, notamment AUindicée 10 p. 110.
    cible = _zone_u_equivalente(zone.strip().upper())
    if cible and insee == "97418" and re.fullmatch(r"U(?:[ABCD]\w*|E[ACMP]|R|TP?)", cible):
        return cible
    if cible and insee == "97420" and re.fullmatch(r"U[ABCE]\w*", cible):
        return cible  # le titre III renvoie expressément au règlement U de même indice
    if cible and insee == "97412" and re.fullmatch(r"U[1-6][A-Z]*", cible):
        return cible
    return None


def zones_apparentees(session: Session, zone: str, insee: str | None) -> list[str]:
    """Zones STOCKÉES à servir pour le filtre `zone` : la zone et ses ANCÊTRES de famille (le règlement
    commun — JAMAIS les secteurs frères : AU3c ne ramène pas AU3st), PLUS la cible du RENVOI réglementaire
    (AU3c→U3c, 2AUd→Ud) et ses ancêtres. Appariement EXACT sur l'ensemble (aucun wildcard de classe)."""
    # OUTIL-PLU-FIX-10 (LOT 1) — une zone AU INDICÉE sectorielle (AUt, AUec, AUa…) SANS chapitre propre,
    # dans une commune dotée du chapitre générique « AU indicée », sert CE chapitre comme articles PROPRES
    # (chaque article y porte la règle de la zone ou son renvoi exprès). On NE rabat PLUS en bloc vers la
    # zone U (c'est l'erreur de la hauteur AUt→Ub des Trois-Bassins) : le renvoi, quand il existe, est
    # DANS le texte de l'article servi, article par article.
    if (insee and _AU_SECTEUR.match(_norm(zone)) and session is not None
            and not _chapitre_propre(session, zone, insee) and _a_chapitre_auindicee(session, insee)):
        indice = _indice_urbain_ecrit(zone, insee)
        if indice:
            famille = zone_candidats(indice)
            stock = session.execute(text(
                "SELECT DISTINCT upper(zone) FROM plu_reglement_extrait WHERE insee=:i "
                "AND upper(zone) = ANY(:zones)"), {"i": insee, "zones": famille}).scalars().all()
            return ["AUINDICEE", *(z for z in famille if z in stock)]
        return ["AUINDICEE"]
    cands = {c.upper() for c in zone_candidats(zone)}
    cible = _renvoi_cible(zone, insee, session)
    if cible:
        cands |= {c.upper() for c in zone_candidats(cible)}
    sql = "SELECT DISTINCT zone FROM plu_reglement_extrait WHERE zone IS NOT NULL"
    params: dict = {}
    if insee:
        sql += " AND insee = :i"; params["i"] = insee
    stored = [z for z in session.execute(text(sql), params).scalars().all() if z]
    match = sorted({z.upper() for z in stored if z.upper() in cands})
    # OUTIL-PLU-FIX-9 (point 1) — PHASAGE : une zone de plan 1AUto/2AUa sans chapitre propre peut partager
    # le chapitre de la famille écrit SANS le préfixe de phase (Sainte-Rose 1AUto → chapitre « AUTO »).
    if not match:
        strip = _sans_prefixe_chiffre(zone)
        if strip:
            scands = {c.upper() for c in zone_candidats(strip)}
            match = sorted({z.upper() for z in stored if z.upper() in scands})
    # OUTIL-PLU-FIX-8 (LOT 3) — renvoi GÉNÉRIQUE AU→U « de même indice » : une zone À URBANISER sans
    # chapitre propre stocké (ni AUa, ni la classe « AU ») ouvre le règlement de la zone U de même indice
    # (AUa→Ua, 1AU3→U3). Purement ADDITIF et DÉCLENCHÉ UNIQUEMENT quand aucune zone propre ne correspond
    # → n'affecte ni « A↛AU » (A n'a pas de forme AU), ni les secteurs AU à chapitre propre (Le Port 1AU/
    # 2AU, Saint-Paul AU3st), ni les renvois configurés (AU3c→U3c, déjà servis ci-dessus).
    if not match:
        ueq = _zone_u_equivalente(zone)
        if ueq:
            ucands = {c.upper() for c in zone_candidats(ueq)}
            match = sorted({z.upper() for z in stored if z.upper() in ucands})
    return match


# OUTIL-PLU-FIX-3 (point 8) — un extrait SANS zone qui NOMME une zone/secteur précis (« en zone UA… »,
# « secteur AU3… ») n'est PAS une disposition commune à toutes les zones : il ne doit pas remonter au
# filtre d'une AUTRE zone. Les vraies dispositions communes (lexique, dispositions générales qui ne
# nomment aucune zone) restent incluses, et sont présentées à part (« Dispositions communes »).
_ZNAME_SQL = r'\y(zones?|secteurs?)\s+[0-9]{0,2}(AU|U|A|N)[0-9A-Za-z]'

# OUTIL-PLU-FIX-10 (LOT 2) — un article MUTUALISÉ (étiquette de famille « U ») qui énumère dans son barème
# un ENSEMBLE PRÉCIS de secteurs (« Zone UA : 15 m · Zone UB : 12 m… ») ne régit QUE ces secteurs. Le
# règlement de Sainte-Marie tient DEUX « Article U8 » : l'un pour UA/UB/UC/UD (p.22), l'autre pour
# UEa/UEm/UEp/UR/UEc/UT (p.35). Sous le filtre UA, seul le premier doit sortir (l'article PROPRE à UA) —
# le second concerne d'autres zones. On lit l'ensemble énuméré et on écarte l'article si la zone filtrée
# n'y figure pas (ni elle, ni un de ses sous-secteurs).
_ENUM_ZONE = re.compile(r'(?i)(?:zones?|secteurs?)\s+([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,5})')
# OUTIL-PLU-FIX-14 (LOT 2) — le n° d'article vient APRÈS le code de zone (« ARTICLE U3 10 » → 10, pas 3) :
# on saute d'abord un code de zone COMPLET séparé par un espace (classe + chiffre + secteur), sinon des
# lettres de classe + séparateur (« Article U – 4 » → 4), sinon rien (« Article 6- » → 6).
_ART_NUM = re.compile(r'(?i)(?:article|art\.?)\s*(?:' + _ZCODE + r'[ \t]+|[A-Za-z]{0,4}\s*[-–—.]?\s*)?(\d{1,2})\b')


def _zones_enumerees(texte: str) -> set[str]:
    """Secteurs explicitement énumérés dans le barème d'un article (codes valides, en MAJ)."""
    out = set()
    for m in _ENUM_ZONE.finditer(texte or ""):
        z = _valid_zone(m.group(1))
        if z:
            out.add(z)
    return out


def _art_num(ref: str | None) -> int | None:
    m = _ART_NUM.search(ref or "")
    return int(m.group(1)) if m else None


def _secteurs_regis(row) -> set[str]:
    """Secteurs qu'un article régit explicitement : ceux énumérés dans son barème (texte) ∪ ceux de la
    BANNIÈRE de son chapitre mutualisé (colonne `secteurs`, OUTIL-PLU-FIX-11 LOT 2 — « ZONES UA, UB,
    UC et UD » retirée du corps à l'ingestion)."""
    out = _zones_enumerees(row["texte_verbatim"] or "")
    sec = row.get("secteurs") if hasattr(row, "get") else None
    if sec:
        out |= {s.strip().upper() for s in str(sec).split(",") if s.strip()}
    return out


# Libellés graphiques dont le chapitre de rattachement reste indéterminé après
# lecture du règlement écrit des Trois-Bassins (2022) et de Cilaos (2024).
_SANS_RATTACHEMENT = {("97423", "NTO1"), ("97424", "UB1"), ("97424", "NTOPOS")}
_DOUTE_RATTACHEMENT = "rattachement non établi dans le règlement écrit, à vérifier"


def mention_rattachement(row: dict, secteur: str, renvoi: str | None = None) -> str | None:
    """Qualifier la provenance de cette carte sous le filtre de secteur."""
    label = _norm(secteur).upper()
    zone = (row["zone"] or "").upper()
    if not zone:
        titre = _norm(row["texte_verbatim"] or "")[:180]
        if re.search(r"(?i)dispositions (?:générales|communes)|applicables à toutes les zones", titre):
            return "disposition commune à toutes les zones"
        return _DOUTE_RATTACHEMENT
    if (row["insee"], label) in _SANS_RATTACHEMENT:
        return _DOUTE_RATTACHEMENT
    if zone == _zone_u_equivalente(label):
        if row.get("document") == "97406_reglement_20230527.pdf" and label in {"AUB", "AUC", "AUE", "AUR"}:
            return f"renvoi à la zone {zone.capitalize()} dans le chapitre AU indicée (p. 75)"
        if row.get("document") == "97422_reglement_20230811.pdf" and re.fullmatch(r"[12]AU[ABCDE]", label):
            return f"renvoi à la zone {zone.capitalize()} dans le chapitre AU indicée (p. 85)"
    if zone == label or label in _secteurs_regis(row) or zone == "AUINDICEE":
        return None
    if zone in zone_candidats(label):
        return "règle de la zone mère"
    phase = _sans_prefixe_chiffre(label)
    if any(target and zone in zone_candidats(target) for target in (renvoi, phase)):
        return None
    return _DOUTE_RATTACHEMENT


def _propre_a(row, zf: str) -> bool:
    """L'article est-il PROPRE à la zone filtrée `zf` (et non un simple ancêtre de famille) ? VRAI s'il est
    étiqueté exactement zf, OU si son barème/bannière nomme zf ou un SOUS-secteur de zf (UAb sous UA).
    N'est PAS « propre » un article d'ANCÊTRE (U pour UE, UE pour UEa) : son code est un préfixe de zf."""
    if (row["zone"] or "").upper() == zf:
        return True
    return any(e == zf or e.startswith(zf) for e in _secteurs_regis(row))


def _filtre_scope(rows: list, zone: str | None, zones_ok: list[str] | None,
                  cible: str | None = None) -> list:
    """OUTIL-PLU-FIX-10/11 (LOT 2) — ARTICLE PROPRE AVANT ARTICLE DE ZONE SŒUR/ANCÊTRE. Quand, pour un même
    NUMÉRO d'article, il existe un extrait PROPRE à la zone filtrée (étiqueté zf, ou dont le barème/bannière
    nomme zf ou un sous-secteur), on ÉCARTE les extraits NON propres du même numéro qui ne sont là que par
    héritage de famille :
      · article d'un ANCÊTRE (code préfixe de zf : « U 12 » sous UE, « UE.10 » sous UEa) — FIX-11 ;
      · article de SECTEURS disjoints (le 2ᵉ « Article U8 » UEa…/UT sous UA à Sainte-Marie) — FIX-10.
    Sinon on garde tout (article unique : exception interne, renvoi AU3c→U3, disposition commune, La
    Possession UBc←UB sans article UBc propre). Ne s'applique pas au chapitre « AU indicée » (LOT 1)."""
    if zone:
        # Ces documents restent consultables dans la recherche communale. Une
        # adresse inventoriée ou un rapport explicatif ne régit pas toute la zone.
        rows = [r for r in rows if not (
            (r.get("document") == "97411_reglement_20260805.pdf" and (r.get("page_debut") or 0) >= 124)
            or (r.get("document") == "97423_reglement_20220602.pdf" and 96 <= (r.get("page_debut") or 0) <= 111)
            or (r.get("document") == "97406_reglement_20230527.pdf" and
                not r["zone"] and (r.get("page_debut") or 0) >= 118))]
    if not zone or zones_ok == ["AUINDICEE"]:
        return rows
    zf = _norm(zone).upper()
    propre_par_num: dict[int, bool] = {}          # un extrait PROPRE à zf existe pour ce n° d'article
    for r in rows:
        n = _art_num(r["article_ref"])
        if n is not None and _propre_a(r, zf):
            propre_par_num[n] = True

    def _ancetre(r) -> bool:
        za = (r["zone"] or "").upper()
        return bool(za) and za != zf and zf.startswith(za)   # code de r = préfixe strict de zf

    def _banner_sec(r) -> set[str]:
        sec = r.get("secteurs") if hasattr(r, "get") else r["secteurs"]
        return {s.strip().upper() for s in str(sec or "").split(",") if s.strip()}

    # Zones CIBLES concrètes (jamais le token de classe nu « U » qui serait couvert par tout secteur) :
    # la zone filtrée ET, en cas de renvoi, la zone de destination (AU3c→U3c sert les articles de U3c).
    cibles = {zf} | ({_norm(cible).upper()} if cible else set())

    def _couvre(secs: set[str]) -> bool:
        # une cible est régie par un secteur énuméré si elle lui est ÉGALE ou en est un SOUS-secteur
        # (U3c ⊂ {U3a,U3c}) ; U2e n'est NI U2a…U2h ni un de leurs sous-secteurs → non couverte.
        return any(t == e or t.startswith(e) for e in secs for t in cibles)

    out = []
    for r in rows:
        # OUTIL-PLU-FIX-14 (LOT 2) — un article MUTUALISÉ (bannière « ZONES U2a, U2b, U2c, U2d et U2h »
        # retirée du corps → colonne `secteurs`) ne régit QUE les secteurs énumérés : s'il n'énumère AUCUNE
        # zone cible (filtre ou renvoi), on l'écarte INCONDITIONNELLEMENT — même si aucun article propre du
        # même numéro n'a matché la requête (Saint-Paul : « espaces » ne matchait pas l'article 6 propre à
        # U2e, donc l'article 6 énumérant U2a…U2h — U2e absente — n'était pas éclipsé et fuyait sous U2e).
        if (zf == "1AUZ" and r.get("document") == "97405_reglement_20230609.pdf"
                and r["zone"] == "1AU"):
            continue  # la ZAC a son propre chapitre, pp. 99–108
        banner = _banner_sec(r)
        if banner and not _couvre(banner):
            continue
        n = _art_num(r["article_ref"])
        if zones_ok and "AUINDICEE" in zones_ok:
            out.append(r)
            continue
        if n is not None and propre_par_num.get(n) and not _propre_a(r, zf) and (
                _ancetre(r) or bool(_secteurs_regis(r))):
            continue                                   # extrait non propre éclipsé par l'article propre
        out.append(r)
    # OUTIL-PLU-FIX-11 (LOT 2) — « l'article propre passe TOUJOURS avant celui d'une zone sœur » : quand la
    # zone a son PROPRE chapitre (≥1 article ÉTIQUETÉ zf), on classe ses articles propres AVANT ceux d'un
    # ancêtre/une sœur, même d'un AUTRE numéro (un « Article Um.2 » d'usage ne doit pas coiffer « Uma.12 »
    # sur « stationnement »). Partition STABLE (le rang FTS est conservé dans chaque groupe). Sans chapitre
    # propre (zone servie par sa famille : Ub1→U), aucun reclassement — l'article de famille est légitime.
    if any((r["zone"] or "").upper() == zf and _art_num(r["article_ref"]) is not None for r in out):
        out = [r for r in out if _propre_a(r, zf)] + [r for r in out if not _propre_a(r, zf)]
    return out

# OUTIL-PLU-FIX-6/7 (point 3) — collisions de STEMMER : le dictionnaire français de Postgres réduit TOUTE
# la famille « stationn… » (stationnement(s), stationner, stationne, stationnent, stationné, stationnant)
# au radical « station », qui matche alors « station d'épuration / de potabilisation / de mesure /
# hydrométrique / service ». FIX-6 ne couvrait QUE 2 formes nominales littérales ; « stationner » rouvrait
# la collision (FIX-7). On traite donc la FAMILLE par PRÉFIXE : tout terme dont la forme désaccentuée
# commence par « stationn » exige le radical littéral « \ystationn » (les collisions « station(s) »
# commencent par « station » sans le 2ᵉ n → écartées). Règle par famille, pas « stem+1 » générique (qui
# exclurait des flexions co-radicalées légitimes, ex. « implantation » et « implantées » divergent dès « implant »).
_FAMILLES_RADICAL = [("stationn", r'\ystationn')]


def _radicaux_requis(terms: list[str] | None) -> list[str]:
    """Radicaux littéraux à exiger dans le verbatim pour neutraliser les collisions de stemmer (par famille)."""
    out, seen = [], set()
    for t in (terms or []):
        u = _ua1(t)
        for pref, rad in _FAMILLES_RADICAL:
            if u.startswith(pref) and rad not in seen:
                seen.add(rad); out.append(rad)
    return out


def _search_where(q: str, insee: str | None, zones_ok: list[str] | None,
                  zone_given: bool, terms: list[str] | None = None) -> tuple[list[str], dict]:
    """Clause WHERE commune à search/count (config `fr_unaccent` : casse + accents).
    Filtre zone (OUTIL-PLU-FIX-2/3) : appariement EXACT sur la liste d'apparentées `zones_ok` (jamais de
    LIKE qui confondait A et AU, B2) ; on inclut les dispositions COMMUNES (`zone IS NULL` qui ne nomment
    PAS une autre zone, point 8)."""
    where = ["tsv @@ websearch_to_tsquery('fr_unaccent', :q)"]
    where.append("article_ref IS DISTINCT FROM :explication")
    params: dict = {"q": q, "explication": _EXPLICATION_AU12}
    if insee:
        where.append("insee = :insee")
        params["insee"] = insee
    if zone_given:
        where.append("(upper(zone) = ANY(:zones) OR (zone IS NULL AND texte_verbatim !~* :znamep))")
        params["zones"] = zones_ok or []
        params["znamep"] = _ZNAME_SQL
    for i, rad in enumerate(_radicaux_requis(terms)):          # OUTIL-PLU-FIX-6 point 3 : anti-collision
        where.append(f"texte_verbatim ~* :rad{i}")
        params[f"rad{i}"] = rad
    return where, params


def _ua1(s: str) -> str:
    """unaccent + minuscule, LONGUEUR PRÉSERVÉE (1 car. → 1 car.) : les offsets restent alignés au texte."""
    out = []
    for ch in s.lower():
        d = _ud.normalize("NFD", ch)
        out.append(d[0] if d else ch)
    return "".join(out)


# mot, césure comprise : « station-\nnement » / soft-hyphen est UN mot.
_WORD_RE = re.compile(r'[0-9A-Za-zÀ-ÿ]+(?:[­\-]\s*\n\s*[0-9A-Za-zÀ-ÿ]+)*')
# césure de fin de ligne à SUPPRIMER (rejoint le mot) : « -\n » / soft-hyphen « ­\n ».
_CESURE = re.compile(r'[­\-]\s*\n\s*')


def _page_slices(texte: str, page_map: list | None) -> list[tuple[int, int | None, str]]:
    """Découpe `texte` en (offset, page, texte_de_la_page) selon page_map (offsets→pages)."""
    pm = page_map or [[0, None]]
    out = []
    for i in range(len(pm)):
        off = int(pm[i][0])
        end = int(pm[i + 1][0]) if i + 1 < len(pm) else len(texte)
        out.append((off, pm[i][1], texte[off:end]))
    return out


def _fenetre(texte: str, start: int, terms: list[str]) -> str:
    """Extrait AUTOUR du mot : fenêtre à la 1re forme d'un terme dans la page (recherche souple pour le
    seul AFFICHAGE — la PAGE, elle, est décidée par le stemmer Postgres), sinon au début de la page."""
    qrads = [_ua1(t) for t in (terms or []) if len(_ua1(t)) >= 4] or [_ua1(t) for t in (terms or [])]
    pos = start
    for m in _WORD_RE.finditer(texte, start, start + 4000):
        tok = _ua1(m.group(0)).replace("­", "").replace("-", "").replace("\n", "").replace(" ", "")
        if any(len(q) >= 4 and (tok.startswith(q) or q.startswith(tok)) for q in qrads):
            pos = m.start(); break
    a, b = max(0, pos - 120), min(len(texte), pos + 220)
    snip = texte[a:b].strip()
    if a > 0:
        snip = "… " + snip
    if b < len(texte):
        snip = snip + " …"
    return snip


def locate_match(session: Session, texte: str, page_map: list | None, q: str,
                 terms: list[str]) -> tuple[int | None, str, list[int]]:
    """OUTIL-PLU-FIX-4 (points 1-3) — situe le mot dans l'article avec EXACTEMENT la même correspondance
    que la recherche : on teste chaque PAGE de l'article avec `to_tsvector('fr_unaccent', …) @@
    websearch_to_tsquery('fr_unaccent', q)` (mêmes radicaux/accents/synonymes que le FTS). Rend
    (1re page où le mot apparaît, extrait autour du mot, TOUTES les pages où il apparaît). Fini le
    `find()` littéral qui ratait les pluriels (« hauteurs » matchait l'article mais pas la page)."""
    slices = _page_slices(texte, page_map)
    # OUTIL-PLU-FIX-5 (césure, point 3) — on REJOINT les mots coupés en fin de ligne (« station-\nnement »)
    # AVANT le stemmer de page, sinon « stationnement » n'y est pas trouvé → page fausse.
    txts = [_CESURE.sub("", s[2]) for s in slices]
    pgs = [int(s[1] or 0) for s in slices]
    rads = _radicaux_requis(terms) or _radicaux_requis([q])   # OUTIL-PLU-FIX-6 point 3 : anti-collision

    def _pages_for(query: str) -> list[int]:
        # Une page ne compte que si elle porte le radical SPÉCIFIQUE (le cas échéant) : on ne cite plus la
        # page d'une « station d'épuration » pour une recherche « stationnement ».
        sql = ("SELECT t.pg FROM unnest(CAST(:txt AS text[]), CAST(:pg AS int[])) AS t(txt, pg) "
               "WHERE to_tsvector('fr_unaccent', t.txt) @@ websearch_to_tsquery('fr_unaccent', :q)")
        p = {"txt": txts, "pg": pgs, "q": query}
        for i, rad in enumerate(rads):
            sql += f" AND t.txt ~* :rad{i}"; p[f"rad{i}"] = rad
        sql += " ORDER BY t.pg"
        rows = session.execute(text(sql), p).scalars().all()
        return [int(p_) for p_ in rows if p_]

    pages = _pages_for(q)
    if pages:
        first = pages[0]
    else:
        # expression répartie sur deux pages : la requête AND ne matche aucune page SEULE. Repli OR
        # SCORÉ (point 3 « localisé correctement ») : la page qui porte le PLUS de termes, pas celle
        # d'un seul mot faible ; pages_match = toutes les pages portant un terme.
        sig = [t for t in (terms or []) if len(t) >= 3] or [q]
        score: dict[int, int] = {}
        order: list[int] = []
        for t in sig:
            for p in _pages_for(t):
                if p not in score:
                    order.append(p)
                score[p] = score.get(p, 0) + 1
        if not score:                             # repli ultime : page de tête
            pg0 = slices[0][1] if slices else None
            return pg0, _fenetre(texte, 0, terms), [pg0] if pg0 else []
        first = sorted(order, key=lambda p: (-score[p], p))[0]
        pages = sorted(score)
    off0 = next((o for o, pg, _ in slices if pg == first), 0)
    return first, _fenetre(texte, off0, terms), sorted(set(pages))


def search_reglement(session: Session, q: str, insee: str | None = None, limit: int = 25,
                     zone: str | None = None, offset: int = 0,
                     terms: list[str] | None = None) -> list[dict]:
    """Recherche full-text (fr_unaccent). L'unité est l'ARTICLE ENTIER (`texte_verbatim`) ; `terms`
    (mots de la requête) sert à CITER la page du mot dans l'article (`page_match`) et à rendre l'extrait
    AUTOUR du mot (`extrait`). `page_debut`/`page_fin` donnent « p. X-Y ». `offset` pagine réellement."""
    zones_ok = zones_apparentees(session, zone, insee) if zone else None
    cible = (_indice_urbain_ecrit(zone, insee) or _renvoi_cible(zone, insee, session)) if zone else None   # zone de destination d'un renvoi
    where, params = _search_where(q, insee, zones_ok, bool(zone), terms)
    base = f"""
        SELECT insee, commune, idurba, to_char(millesime,'YYYY-MM-DD') AS millesime, document,
               zone, article_ref, page_pdf, page_debut, page_fin, page_map, livret, secteurs, dossier, modif_note,
               texte_verbatim, doute, doute_motif, pagination_ambigue, source_url, pdf_url,
               ts_rank(tsv, websearch_to_tsquery('fr_unaccent', :q)) AS rang
        FROM plu_reglement_extrait
        WHERE {' AND '.join(where)}
        ORDER BY (dossier IS NOT NULL), rang DESC, insee, page_pdf, id"""
    if zone:
        # OUTIL-PLU-FIX-10 (LOT 2) — le filtre « articles concurrents » a besoin de TOUS les extraits d'un
        # même numéro ; on récupère donc l'ensemble (borné à la commune+zone, petit), on écarte les articles
        # d'autres secteurs, PUIS on pagine en Python. Requête île/zone-libre : pagination SQL inchangée.
        rows = session.execute(text(base), params).mappings().all()
        rows = _filtre_scope(list(rows), zone, zones_ok, cible)[offset: offset + limit]
    else:
        params["lim"] = limit
        params["off"] = max(0, offset)
        rows = session.execute(text(base + "\n        LIMIT :lim OFFSET :off"), params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        if d["document"] == "97410_reglement_20200206.pdf" and d["article_ref"] == "Article AU – 12.":
            d["explication"] = session.execute(text(
                "SELECT texte_verbatim AS texte, page_pdf FROM plu_reglement_extrait "
                "WHERE insee=:insee AND document=:document AND article_ref=:ref LIMIT 1"),
                {"insee": d["insee"], "document": d["document"], "ref": _EXPLICATION_AU12}).mappings().first()
            if d["explication"]:
                d["explication"] = dict(d["explication"])
        if zone:
            d["mention_rattachement"] = mention_rattachement(d, zone, cible)
        pg, snip, pages = locate_match(session, d.get("texte_verbatim") or "", d.get("page_map"), q, terms or [])
        d["page_match"] = pg or d.get("page_debut") or d.get("page_pdf")
        d["pages_match"] = pages or [d["page_match"]]   # TOUTES les pages où le mot apparaît (point 1)
        d["extrait"] = snip
        out.append(d)
    return out


def count_reglement(session: Session, q: str, insee: str | None = None,
                    zone: str | None = None, terms: list[str] | None = None) -> int:
    """OUT-PLU-008 — nombre TOTAL d'extraits correspondant à la requête (sans le plafond `limit`),
    pour que l'écran dise « N affichés sur M » et non le simple compte de la page servie."""
    zones_ok = zones_apparentees(session, zone, insee) if zone else None
    cible = (_indice_urbain_ecrit(zone, insee) or _renvoi_cible(zone, insee, session)) if zone else None
    where, params = _search_where(q, insee, zones_ok, bool(zone), terms)
    if zone:
        # même filtre « articles concurrents » que search_reglement → compte COHÉRENT avec l'affiché.
        rows = session.execute(text(
            f"SELECT document, page_debut, zone, article_ref, secteurs, texte_verbatim FROM plu_reglement_extrait "
            f"WHERE {' AND '.join(where)}"), params).mappings().all()
        return len(_filtre_scope(list(rows), zone, zones_ok, cible))
    return int(session.execute(text(
        f"SELECT count(*) FROM plu_reglement_extrait WHERE {' AND '.join(where)}"),
        params).scalar() or 0)


def corpus_status(session: Session) -> dict[str, dict]:
    """État INGÉRÉ par INSEE (extraits, doutes, pagination ambiguë). L'API le croise avec
    plu_millesimes pour dire RNU / révision en cours / non ingéré."""
    if session.execute(text("SELECT to_regclass('plu_reglement_extrait')")).scalar() is None:
        return {}
    rows = session.execute(text("""
        SELECT insee, commune, min(idurba) AS idurba, to_char(max(millesime),'YYYY-MM-DD') AS millesime,
               count(*) AS extraits, count(*) FILTER (WHERE doute) AS doutes,
               bool_or(pagination_ambigue) AS pagination_ambigue,
               string_agg(DISTINCT document, ', ') AS documents,
               min(source_url) AS source_url,  -- pack GPU .zip (1 seul par commune) : le « PLU intégral »
               min(pdf_url) AS pdf_url  -- règlement écrit direct (.pdf) : le lien « PDF ↗ » (LOT 2)
        FROM plu_reglement_extrait GROUP BY insee, commune ORDER BY insee
    """)).mappings().all()
    return {r["insee"]: dict(r) for r in rows}
