"""M51-P1b — Ingestion du règlement écrit en extraits ARTICLE, indexés full-text (Postgres FTS
french). Sert du VERBATIM SOURCÉ : chaque extrait porte commune, document, article, PAGE PDF,
millésime, lien. Le doute (page quasi vide → scan/illisible possible) est un CHAMP SERVI, pas
interne. La pagination ambiguë (double numérotation, ex. Saint-Benoît) est détectée et DITE.

Granularité = article (unité naturelle, regex-détectable). On cite la PAGE PDF (fiable) — jamais la
page imprimée seule (noyée dans les en-têtes, ambiguë en double numérotation)."""
from __future__ import annotations

import re

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
    r'(?m)^[ \t]*('
    r'(?:ARTICLE|Article)\s+[A-Za-z]{0,4}\s*\.?\s*\d+[A-Za-z0-9.\-]*'
    r'|(?:ZONE|Zone)\s+[0-9A-Za-z]{1,6}\b'
    r'|(?:CHAPITRE|TITRE|SECTION|Chapitre|Titre|Section)\s+[IVXLC0-9]+\b'
    r')')
_ZONE_FROM_ART = re.compile(r'(?i)(?:ARTICLE)\s+([A-Za-z]{1,4})\s*[-–]?\s*\d')
_ZONE_FROM_ZONE = re.compile(r'(?i)ZONE\s+([0-9A-Za-z]{1,5})')
# référence croisée dans la prose juste avant le « titre » : « (voir Article… », « cf. Article… »,
# « au titre… », « à l'article… » → l'en-tête matché n'est pas un vrai début d'article.
_CROSSREF_PRE = re.compile(r"(?i)(?:\(|voir|cf\.?|à l['’]|au|du|de la|sous le|présent|dudit|ledit)\s*$")


def _looks_cross_ref(flat: str, start: int) -> bool:
    pre = _norm(flat[max(0, start - 30):start])
    return bool(_CROSSREF_PRE.search(pre))

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
    """Renvoie le code zone normalisé (MAJ) s'il a la forme d'un code réunionnais, sinon None."""
    if not z:
        return None
    z = _norm(z).upper().rstrip('.')
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


def _detect_chrome(pages: list[str]) -> set[str]:
    """Lignes d'en-tête/pied COURANTES (répétées sur beaucoup de pages) : bandeau « Règlement –
    Commune de … », ligne « PLU approuvé le … / Edition … / Modifié par DCM du : … », numéros de
    page. Seuil = max(4, pages/5)."""
    from collections import Counter
    c: Counter = Counter()
    for t in pages:
        ls = [_norm(l) for l in t.splitlines() if _norm(l)]
        for l in ls[:6] + ls[-3:]:
            c[l] += 1
    thr = max(4, len(pages) // 5)
    return {l for l, n in c.items() if n >= thr and len(l) > 3}


def _clean_pages(pages: list[str]) -> tuple[list[str], list[str | None]]:
    """Retire de chaque page le « chrome » (en-têtes/pieds courants, bannière de zone, n° de page) et
    renvoie (pages nettoyées, zone de bannière par page). La bannière n'est PLUS dans le flux — elle
    ne coupe donc plus l'article (LOT 3) — mais sa zone est conservée pour l'étiquette (LOT 4)."""
    chrome = _detect_chrome(pages)
    clean: list[str] = []
    zbanner: list[str | None] = []
    for t in pages:
        cur: str | None = None
        kept: list[str] = []
        for idx, l in enumerate(t.splitlines()):
            n = _norm(l)
            if not n:
                kept.append(l)
                continue
            top = idx < 12       # le titre de chapitre (« Zone Uavap ») peut suivre un bandeau de 4-5 lignes
            if n in chrome:
                continue
            mb = _BANNER.match(n) if top else None
            if mb:
                bz = _banner_zone(mb.group(1))
                if bz:
                    cur = cur or bz
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


_MAX_CHARS = 2800                               # taille max d'un extrait (B1 : « avec une taille maximale »)
_SUBART = re.compile(r'(?m)(?=^\s*(?:\d{1,2}\.\d{1,2}\b|[-–•]\s))')   # frontière de sous-article/alinéa


def _chunk(body: str, maxlen: int = _MAX_CHARS) -> list[str]:
    """Découpe un corps trop long au sous-article / paragraphe, en morceaux ≤ maxlen (B1)."""
    body = body.strip()
    if len(body) <= maxlen:
        return [body] if body else []
    parts = [p for p in _SUBART.split(body) if p.strip()] or [body]
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) > maxlen:
            out.append(cur.strip()); cur = ""
        while len(p) > maxlen:                  # paragraphe isolé plus long que maxlen → coupe dure
            out.append(p[:maxlen].strip()); p = p[maxlen:]
        cur += p
    if cur.strip():
        out.append(cur.strip())
    return out


def _split_articles(path: str) -> tuple[list[dict], bool]:
    """Découpe le PDF en extraits (article → sous-article/paragraphe), BORNÉS À LA PAGE.
    Chaque extrait porte page_debut == page_fin == page_pdf : la page citée est EXACTEMENT celle où se
    trouve le texte (OUTIL-PLU-FIX-2 B1 — fini les blocs fusionnés cités à leur page de tête).

    Méthode : on coupe le flux nettoyé à l'UNION des frontières d'EN-TÊTE (article/zone, filtrées des
    renvois de prose, B3) ET des frontières de PAGE. Un article qui court sur plusieurs pages devient
    donc une suite d'extraits, un par page, portant tous sa référence. Un corps de page trop dense est
    re-scindé au sous-article (`_chunk`). La zone vient de la BANNIÈRE de la page (fiable) ou, à défaut,
    de l'en-tête d'article (C3 — plus de « Article N 14 » qui étiquette 50 pages en N)."""
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

    # en-têtes RÉELS (B3) : on écarte les références croisées lues en pleine phrase.
    heads = [m for m in _HEADER.finditer(flat) if not _looks_cross_ref(flat, m.start())]
    head_pos = [m.start() for m in heads]
    head_ref = {m.start(): _norm(m.group(1)) for m in heads}
    cuts = sorted(set(head_pos) | set(page_off) | {len(flat)})
    out: list[dict] = []
    for a, b in zip(cuts, cuts[1:]):
        body = flat[a:b].strip()
        if not body:
            continue
        j = bisect.bisect_right(head_pos, a) - 1
        ref = head_ref[head_pos[j]] if j >= 0 else None
        pg = page_of(a)
        is_zone_title = bool(ref) and ref.upper().startswith("ZONE")
        if is_zone_title and len(re.sub(r'\s', '', body)) < 60:
            continue                           # titre de zone nu (sommaire/intitulé) : pas un extrait
        zm = _ZONE_FROM_ART.match(ref or "") or _ZONE_FROM_ZONE.match(ref or "")
        z_ref = _valid_zone(zm.group(1)) if zm else None
        zone = zbanner[pg - 1] or z_ref        # bannière de PAGE d'abord (per-page, fiable) ; sinon l'en-tête
        for piece in _chunk(body):
            pn = len(re.sub(r'\s', '', piece))
            out.append({
                "article_ref": ref, "zone": zone, "page_pdf": pg,
                "page_debut": pg, "page_fin": pg, "texte": piece, "doute": pn < 25,
                "doute_motif": "extrait quasi vide — page peut-être illisible/scannée, à vérifier au PDF" if pn < 25 else None,
            })
    return out, ambigu


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
               page_debut, page_fin, texte_verbatim, doute, doute_motif, pagination_ambigue,
               source_url, pdf_url, fetched_at, tsv)
            VALUES
              (:insee, :commune, :idurba, :millesime, :document, :zone, :article_ref, :page_pdf,
               :page_debut, :page_fin, :texte, :doute, :doute_motif, :ambigu, :url, :pdf_url, :fetched_at,
               to_tsvector('fr_unaccent',
                 coalesce(:article_ref,'') || ' ' || coalesce(:zone,'') || ' ' || :texte))
        """), {"insee": insee, "commune": commune, "idurba": idurba, "millesime": millesime,
               "document": document, "zone": e["zone"], "article_ref": e["article_ref"],
               "page_pdf": e["page_pdf"], "page_debut": e.get("page_debut", e["page_pdf"]),
               "page_fin": e.get("page_fin", e["page_pdf"]), "texte": e["texte"], "doute": e["doute"],
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


def _zone_match(a: str, b: str) -> bool:
    """Deux codes de zone s'apparentent (OUTIL-PLU-FIX-2 B2+C1) si :
      (a) l'un est ANCÊTRE de l'autre dans la chaîne de candidats (ex. A→Ah, U→Ua), OU
      (b) ils partagent un ancêtre commun PLUS PROFOND que la seule classe (ex. AU3c↔AU3ST : famille
          AU3 ; UBc↔UBa : famille UB).
    Un simple partage de classe NE SUFFIT PAS : AU3c n'attrape pas AU1 (commun = « AU » = classe), et
    A n'attrape jamais AU (classes disjointes, commun = ∅)."""
    au, bu = _norm(a).upper(), _norm(b).upper()
    sa, sb = set(zone_candidats(au)), set(zone_candidats(bu))
    if au in sb or bu in sa:                      # (a) ancêtre / descendant
        return True
    common = sa & sb                              # (b) ancêtre commun plus profond que la classe
    if not common:
        return False
    return len(max(common, key=len)) > len(_classe_token(au))


def zones_apparentees(session: Session, zone: str, insee: str | None) -> list[str]:
    """Liste des codes de zone STOCKÉS apparentés à `zone` (cf. `_zone_match`). On interroge les zones
    réellement présentes (indexé, bon marché) et on filtre en Python — appariement EXACT ensuite."""
    sql = "SELECT DISTINCT zone FROM plu_reglement_extrait WHERE zone IS NOT NULL"
    params: dict = {}
    if insee:
        sql += " AND insee = :i"; params["i"] = insee
    stored = [z for z in session.execute(text(sql), params).scalars().all() if z]
    return sorted({z.upper() for z in stored if _zone_match(zone, z)})


def _search_where(q: str, insee: str | None, zones_ok: list[str] | None,
                  zone_given: bool) -> tuple[list[str], dict]:
    """Clause WHERE commune à search/count (config `fr_unaccent` : casse + accents).
    Filtre zone (OUTIL-PLU-FIX-2) : appariement EXACT sur la liste d'apparentées `zones_ok` (jamais de
    LIKE qui confondait A et AU, B2) ; on INCLUT aussi les extraits SANS étiquette (`zone IS NULL`) car
    ils portent les dispositions GÉNÉRALES, applicables à toute zone — sinon 31–41 % du règlement
    (Le Port, Saint-Pierre, Cilaos) devenaient inatteignables dès qu'on filtrait (C2)."""
    where = ["tsv @@ websearch_to_tsquery('fr_unaccent', :q)"]
    params: dict = {"q": q}
    if insee:
        where.append("insee = :insee")
        params["insee"] = insee
    if zone_given:
        where.append("(upper(zone) = ANY(:zones) OR zone IS NULL)")
        params["zones"] = zones_ok or []
    return where, params


def search_reglement(session: Session, q: str, insee: str | None = None, limit: int = 25,
                     zone: str | None = None, offset: int = 0) -> list[dict]:
    """Recherche full-text (fr_unaccent) qui rend le VERBATIM SOURCÉ complet + la référence + le lien.
    `insee` None = île entière. `zone` filtre la famille de zone et ses secteurs (classe-conscient) +
    les dispositions générales. `offset` pagine RÉELLEMENT. Aucun résumé : `texte_verbatim` est le texte
    brut ; `doute`/`pagination_ambigue` sont RENDUS ; `page_debut`/`page_fin` bornent la page citée."""
    zones_ok = zones_apparentees(session, zone, insee) if zone else None
    where, params = _search_where(q, insee, zones_ok, bool(zone))
    params["lim"] = limit
    params["off"] = max(0, offset)
    rows = session.execute(text(f"""
        SELECT insee, commune, idurba, to_char(millesime,'YYYY-MM-DD') AS millesime, document,
               zone, article_ref, page_pdf, page_debut, page_fin, texte_verbatim, doute, doute_motif,
               pagination_ambigue, source_url, pdf_url,
               ts_rank(tsv, websearch_to_tsquery('fr_unaccent', :q)) AS rang
        FROM plu_reglement_extrait
        WHERE {' AND '.join(where)}
        ORDER BY rang DESC, insee, page_pdf, id
        LIMIT :lim OFFSET :off
    """), params).mappings().all()
    return [dict(r) for r in rows]


def count_reglement(session: Session, q: str, insee: str | None = None,
                    zone: str | None = None) -> int:
    """OUT-PLU-008 — nombre TOTAL d'extraits correspondant à la requête (sans le plafond `limit`),
    pour que l'écran dise « N affichés sur M » et non le simple compte de la page servie."""
    zones_ok = zones_apparentees(session, zone, insee) if zone else None
    where, params = _search_where(q, insee, zones_ok, bool(zone))
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
