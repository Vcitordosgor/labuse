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
_HEADER = re.compile(
    # OUTIL-PLU-FIX-6 (point 2, La Possession) — un en-tête peut suivre une FIN DE PHRASE sur la même
    # ligne : « …Sans objet. ARTICLE UB 10 - … » (extraction PDF qui colle la suite) → sinon UB 10 est
    # fondu dans UB 9. On ancre en DÉBUT DE LIGNE ou juste après « . ».
    r'(?m)(?:^[ \t]*|(?<=\.)[ \t]+)('
    # OUTIL-PLU-FIX-5 (Saint-Benoît) — séparateur zone→numéro : espace, point, tiret court/en-dash/em-dash
    # (« Article U – 4. Hauteur » n'était pas détecté → 47 en-têtes perdus, commune entière sans article).
    r'(?:ARTICLE|Article)\s+[A-Za-z]{0,4}\s*[-–—.]?\s*\d+[A-Za-z0-9.\-]*'
    r'|(?:ZONE|Zone)\s+[0-9A-Za-z]{1,6}\b'
    r'|(?:CHAPITRE|TITRE|SECTION|Chapitre|Titre|Section)\s+[IVXLC0-9]+\b'
    r')')
# OUTIL-PLU-FIX-4 (critère 4) — tolère le POINT entre la classe et le numéro (« Article N.1 », « N.2 »
# à Saint-Denis) : sinon z_ref=None → repli bannière → zone fausse (13 « Article N.x » étiquetés A).
_ZONE_FROM_ART = re.compile(r'(?i)(?:ARTICLE)\s+([A-Za-z]{1,4})\s*[-–—.]?\s*\d')
_ZONE_FROM_ZONE = re.compile(r'(?i)ZONE\s+([0-9A-Za-z]{1,5})')
# référence croisée dans la prose juste avant le « titre » : « (voir Article… », « cf. Article… »,
# « au titre… », « à l'article… » → l'en-tête matché n'est pas un vrai début d'article.
_CROSSREF_PRE = re.compile(r"(?i)(?:\(|voir|cf\.?|à l['’]|au|du|de la|sous le|présent|dudit|ledit)\s*$")


def _looks_cross_ref(flat: str, start: int) -> bool:
    pre = _norm(flat[max(0, start - 30):start])
    return bool(_CROSSREF_PRE.search(pre))


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


# OUTIL-PLU-FIX-3 (D3) — en-tête/pied COURANT qui VARIE d'une page à l'autre (le « / Titre 2 – Livret 1
# – Bassin de vie X » change de livret en livret → la détection par fréquence le rate). On le reconnaît
# aussi par son DÉBUT DE LIGNE : « Règlement… », « Commune de… », « Ville de… », « Mairie… », « Plan
# Local d'Urbanisme… », « PLU approuvé… », « Edition… », « Modifié par… », une liste de dates, etc.
_CHROME_PAT = re.compile(
    r"(?i)^\s*(?:r[eè]glement\b|commune d|ville d|mairie\b|plan local|p\.?\s?l\.?\s?u\b"
    r"|plu approuv|[eé]dition\b|modifi[eé] par|dossier approuv|d[eé]partement\b"
    r"|\d{1,2}/\d{1,2}/\d{2,4}[\s,]*$)")


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


def _clean_pages(pages: list[str]) -> tuple[list[str], list[str | None]]:
    """Retire de chaque page le « chrome » (en-têtes/pieds courants — constants OU variables par page,
    D3 —, bannière de zone, n° de page) et renvoie (pages nettoyées, zone de bannière par page). Le
    texte servi est ainsi celui du règlement, sans en-têtes/pieds répétés."""
    chrome = _detect_chrome(pages)
    clean: list[str] = []
    zbanner: list[str | None] = []
    resets: list[bool] = []
    for t in pages:
        cur: str | None = None
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
            mb = _BANNER.match(n) if top else None
            if mb:
                bz = _banner_zone(mb.group(1))
                if bz:
                    if not sommaire and not _is_toc_header(n, 0):   # pas une ligne de sommaire (points de conduite)
                        cur = cur or bz
                    continue
            if n in chrome:
                continue
            if (top or bottom) and _CHROME_PAT.match(n):   # D3 — chrome qui varie par page
                continue
            if _PAGEFOOT.match(n):
                continue
            kept.append(l)
        clean.append("\n".join(kept))
        zbanner.append(cur)
    # OUTIL-PLU-FIX-1 (LOT 4) — forward-fill : certains PLU ne portent le code de zone qu'UNE fois, au
    # titre de chapitre (Saint-Denis « Zone Uavap » p.26), pas en bandeau de chaque page → la zone doit
    # PERSISTER jusqu'au chapitre suivant. Le remplissage ne part JAMAIS vers l'arrière : les pages
    # avant le 1er titre (dispositions générales, sommaire) restent sans étiquette.
    last: str | None = None
    for i in range(len(zbanner)):
        if resets[i]:                      # chapitre sans zone → on cesse de reporter la bannière
            last = None
        if zbanner[i] is not None:
            last = zbanner[i]
        elif last is not None:
            zbanner[i] = last
    return clean, zbanner


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


def _pages(path: str) -> list[str]:
    d = fitz.open(path)
    return [d[i].get_text() for i in range(d.page_count)]


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
    pages = _pages(path)
    ambigu = _pagination_ambigue(pages)       # détecté sur le texte brut (numéros imprimés)
    clean, zbanner = _clean_pages(pages)
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
             and not _is_toc_header(flat, m.start())]
    head_ref = {m.start(): _norm(m.group(1)) for m in heads}
    # OUTIL-PLU-FIX-6 (point 2) — un titre de chapitre SANS zone (ANNEXES, DISPOSITIONS GÉNÉRALES,
    # DÉFINITIONS, LEXIQUE, TITRE liminaire) est une FRONTIÈRE de bloc : l'annexe forme son PROPRE bloc
    # (zone None), au lieu d'être avalée par le bloc de zone précédent (Saint-Benoît annexes AU/N → UE).
    reset_at: set[int] = set()
    for m in _RESET_CHAP_M.finditer(flat):
        if not _is_toc_header(flat, m.start()) and _reset_is_title(_norm(m.group(1))):
            head_ref[m.start()] = _norm(m.group(1))[:60]
            reset_at.add(m.start())
    # frontières = en-têtes d'article/zone + titres de chapitre sans zone (jamais les frontières de page).
    bounds = sorted(set(head_ref) | {len(flat)})
    head_pos = sorted(head_ref)

    _UNSET = object()

    def _emit(a: int, b: int, ref: str | None, zone=_UNSET) -> dict | None:
        raw = flat[a:b]
        texte = raw.strip()
        if not texte:
            return None
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
                zone = z_ref or zbanner[page_of(a) - 1]
        if zone is None:                          # OUTIL-PLU-FIX-7 (point 1) — fiche/annexe zonée → sa zone
            zone = _zone_de_fiche(texte)
        pg0 = page_of(a)
        lead = len(raw) - len(raw.lstrip())
        pmap = [[0, pg0]]                        # page_map : offset dans `texte` → page PDF
        for o in page_off:
            if a < o < b:
                off = o - a - lead
                p = page_of(o)
                if off >= 0 and p != pmap[-1][1]:
                    pmap.append([off, p])
        net = len(re.sub(r'\s', '', texte))
        return {"article_ref": ref, "zone": zone, "page_pdf": pg0,
                "page_debut": pg0, "page_fin": page_of(b - 1), "page_map": pmap,
                "texte": texte, "doute": net < 25,
                "doute_motif": "extrait quasi vide — page peut-être illisible/scannée, à vérifier au PDF" if net < 25 else None}

    def _emit_block(a: int, b: int, ref: str | None) -> list[dict]:
        """Émet l'article [a,b) ; si c'est un GROS BLOC (≥ seuil pages), le re-découpe au niveau interne
        existant (critère 3), en conservant SA zone (un bloc = une zone)."""
        e = _emit(a, b, ref)
        if not e:
            return []
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
        out.extend(_emit_block(a, b, head_ref[a]))
    return _fusionne_titres(out), ambigu


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
    session.execute(text("DELETE FROM plu_reglement_extrait WHERE insee = :i AND document = :d"),
                    {"i": insee, "d": document})
    for e in extraits:
        session.execute(text("""
            INSERT INTO plu_reglement_extrait
              (insee, commune, idurba, millesime, document, zone, article_ref, page_pdf,
               page_debut, page_fin, page_map, texte_verbatim, doute, doute_motif, pagination_ambigue,
               source_url, pdf_url, fetched_at, tsv)
            VALUES
              (:insee, :commune, :idurba, :millesime, :document, :zone, :article_ref, :page_pdf,
               :page_debut, :page_fin, CAST(:page_map AS jsonb), :texte, :doute, :doute_motif, :ambigu,
               :url, :pdf_url, :fetched_at,
               to_tsvector('fr_unaccent',
                 coalesce(:article_ref,'') || ' ' || coalesce(:zone,'') || ' ' || :texte))
        """), {"insee": insee, "commune": commune, "idurba": idurba, "millesime": millesime,
               "document": document, "zone": e["zone"], "article_ref": e["article_ref"],
               "page_pdf": e["page_pdf"], "page_debut": e.get("page_debut", e["page_pdf"]),
               "page_fin": e.get("page_fin", e["page_pdf"]),
               "page_map": _json.dumps(e.get("page_map") or [[0, e["page_pdf"]]]),
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


def _renvoi_cible(zone: str, insee: str | None) -> str | None:
    """OUTIL-PLU-FIX-6 (point 1) — cible du RENVOI réglementaire d'un secteur (Saint-Paul AU3c→U3c,
    Le Tampon 2AUd→Ud) via `resolve_zone` : la MÊME résolution que la fiche parcelle (config/
    plu_destinations + patterns AU→U), pas une seconde table. None si la zone n'est pas un renvoi."""
    if not insee:
        return None
    try:
        from ..faisabilite.zonage import resolve_zone
        zr = resolve_zone(zone, insee)
        m = re.search(r'règles de (\S+)', getattr(zr, "via_renvoi", None) or "")
        return m.group(1) if m else None
    except Exception:  # noqa: BLE001
        return None


def zone_renvoi_note(zone: str, insee: str | None) -> str | None:
    """Phrase à afficher quand le filtre d'un secteur ouvre les articles de sa zone de renvoi."""
    cible = _renvoi_cible(zone, insee)
    return f"{zone} : le règlement renvoie à {cible}" if cible else None


def zones_apparentees(session: Session, zone: str, insee: str | None) -> list[str]:
    """Zones STOCKÉES à servir pour le filtre `zone` : la zone et ses ANCÊTRES de famille (le règlement
    commun — JAMAIS les secteurs frères : AU3c ne ramène pas AU3st), PLUS la cible du RENVOI réglementaire
    (AU3c→U3c, 2AUd→Ud) et ses ancêtres. Appariement EXACT sur l'ensemble (aucun wildcard de classe)."""
    cands = {c.upper() for c in zone_candidats(zone)}
    cible = _renvoi_cible(zone, insee)
    if cible:
        cands |= {c.upper() for c in zone_candidats(cible)}
    sql = "SELECT DISTINCT zone FROM plu_reglement_extrait WHERE zone IS NOT NULL"
    params: dict = {}
    if insee:
        sql += " AND insee = :i"; params["i"] = insee
    stored = [z for z in session.execute(text(sql), params).scalars().all() if z]
    return sorted({z.upper() for z in stored if z.upper() in cands})


# OUTIL-PLU-FIX-3 (point 8) — un extrait SANS zone qui NOMME une zone/secteur précis (« en zone UA… »,
# « secteur AU3… ») n'est PAS une disposition commune à toutes les zones : il ne doit pas remonter au
# filtre d'une AUTRE zone. Les vraies dispositions communes (lexique, dispositions générales qui ne
# nomment aucune zone) restent incluses, et sont présentées à part (« Dispositions communes »).
_ZNAME_SQL = r'\y(zones?|secteurs?)\s+[0-9]{0,2}(AU|U|A|N)[0-9A-Za-z]'

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
    params: dict = {"q": q}
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
    where, params = _search_where(q, insee, zones_ok, bool(zone), terms)
    params["lim"] = limit
    params["off"] = max(0, offset)
    rows = session.execute(text(f"""
        SELECT insee, commune, idurba, to_char(millesime,'YYYY-MM-DD') AS millesime, document,
               zone, article_ref, page_pdf, page_debut, page_fin, page_map, texte_verbatim, doute,
               doute_motif, pagination_ambigue, source_url, pdf_url,
               ts_rank(tsv, websearch_to_tsquery('fr_unaccent', :q)) AS rang
        FROM plu_reglement_extrait
        WHERE {' AND '.join(where)}
        ORDER BY rang DESC, insee, page_pdf, id
        LIMIT :lim OFFSET :off
    """), params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
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
    where, params = _search_where(q, insee, zones_ok, bool(zone), terms)
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
