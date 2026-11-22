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
CREATE INDEX IF NOT EXISTS ix_plu_extrait_tsv    ON plu_reglement_extrait USING gin(tsv);
CREATE INDEX IF NOT EXISTS ix_plu_extrait_insee  ON plu_reglement_extrait(insee);
CREATE INDEX IF NOT EXISTS ix_plu_extrait_doc    ON plu_reglement_extrait(insee, document);
"""

# En-tête d'article ou de zone. Formats rencontrés sur l'île : mutualisé « Article U 4 »,
# classique « Article Ua 1 », NUMÉROTÉ « Article 1- » / « ARTICLE 1 - » (dispositions générales),
# code « Article R111-2 », titres « ZONE UE » / « CHAPITRE|TITRE|SECTION … ».
_HEADER = re.compile(
    r'(?im)^[ \t]*('
    r'(?:ARTICLE|Article)\s+[A-Za-z]{0,4}\s*\.?\s*\d+[A-Za-z0-9.\-]*'
    r'|ZONE\s+[0-9A-Za-z]{1,6}\b'
    r'|(?:CHAPITRE|TITRE|SECTION)\s+[IVXLC0-9]+\b'
    r')')
_ZONE_FROM_ART = re.compile(r'(?i)(?:ARTICLE)\s+([A-Za-z]{1,4})\s*[-–]?\s*\d')
_ZONE_FROM_ZONE = re.compile(r'(?i)ZONE\s+([0-9A-Za-z]{1,5})')

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


def _split_articles(path: str) -> tuple[list[dict], bool]:
    """Découpe le PDF en extraits ARTICLE ({article_ref, zone, page_pdf, texte, doute, doute_motif}).
    Renvoie aussi le drapeau pagination_ambigue (document-level).

    OUTIL-PLU-FIX-1 (LOT 3) — on découpe sur le flux NETTOYÉ de ses en-têtes/pieds courants : une
    bannière « Zone U2e » répétée en haut de chaque page ne crée plus de frontière d'article (elle
    coupait l'article U2e au milieu du §6.3, cf. Saint-Paul p.92). La zone de page (bannière) est
    conservée à part et sert d'étiquette fiable (LOT 4)."""
    pages = _pages(path)
    ambigu = _pagination_ambigue(pages)       # détecté sur le texte brut (numéros imprimés)
    clean, zbanner = _clean_pages(pages)
    # flux plat NETTOYÉ + carte offset→page_pdf (le n° de page reste celui du PDF d'origine)
    starts, buf, pos = [], [], 0
    for i, t in enumerate(clean):
        starts.append((pos, i + 1)); buf.append(t); pos += len(t)
    flat = "".join(buf)

    def page_of(off: int) -> int:
        pg = 1
        for o, p in starts:
            if o <= off:
                pg = p
            else:
                break
        return pg

    heads = list(_HEADER.finditer(flat))
    out: list[dict] = []
    for i, m in enumerate(heads):
        ref = _norm(m.group(1))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(flat)
        body = flat[m.start():end].strip()
        pg = page_of(m.start())
        # zone éventuellement portée par l'en-tête lui-même (« Article Ua 1 », « ZONE UE »)
        zm = _ZONE_FROM_ART.match(ref) or _ZONE_FROM_ZONE.match(ref)
        z_ref = _valid_zone(zm.group(1)) if zm else None
        body_net = len(re.sub(r'\s', '', body))
        is_zone_title = ref.upper().startswith("ZONE")
        # OUTIL-PLU-FIX-1 (LOT 3) — un titre de zone n'est PLUS jeté AVEC son corps : le préambule de
        # chapitre (« caractère de la zone »…) et surtout les dispositions générales qui suivent le
        # sommaire (ex. Saint-Denis : « piscine » dans l'emprise au sol, p.5/p.22) restaient hors
        # recherche (« piscine » rendait zéro). On ne saute QUE les titres NUS (entrée de sommaire,
        # corps trivial < 60 c.) ; on émet les autres pour que leur texte soit indexé.
        if is_zone_title and body_net < 60:
            continue                   # titre nu (sommaire/intitulé) : pas un extrait servable
        # OUTIL-PLU-FIX-1 (LOT 4) — l'étiquette vient du chapitre RÉELLEMENT régi : l'en-tête d'article
        # (« Article Ua 10 ») sinon la bannière de page (« Zones U1a…U1pso » → famille U1). Aucun
        # héritage « glissant » : une page sans bannière (dispositions générales, lexique, annexes)
        # reste SANS étiquette plutôt que de recopier la zone du chapitre précédent (faux « N »).
        zone = z_ref or zbanner[pg - 1]
        # un bloc LONG rattaché à un titre de zone de sommaire = dispositions générales mêlées :
        # on ne lui invente pas une zone unique (mieux sans étiquette que fausse).
        if is_zone_title and body_net > 1500:
            zone = None
        doute = body_net < 25
        out.append({
            "article_ref": ref, "zone": zone, "page_pdf": pg,
            "texte": body, "doute": doute,
            "doute_motif": "extrait quasi vide — page peut-être illisible/scannée, à vérifier au PDF" if doute else None,
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
               texte_verbatim, doute, doute_motif, pagination_ambigue, source_url, pdf_url, fetched_at, tsv)
            VALUES
              (:insee, :commune, :idurba, :millesime, :document, :zone, :article_ref, :page_pdf,
               :texte, :doute, :doute_motif, :ambigu, :url, :pdf_url, :fetched_at,
               to_tsvector('fr_unaccent',
                 coalesce(:article_ref,'') || ' ' || coalesce(:zone,'') || ' ' || :texte))
        """), {"insee": insee, "commune": commune, "idurba": idurba, "millesime": millesime,
               "document": document, "zone": e["zone"], "article_ref": e["article_ref"],
               "page_pdf": e["page_pdf"], "texte": e["texte"], "doute": e["doute"],
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


def _search_where(q: str, insee: str | None, zone: str | None) -> tuple[list[str], dict]:
    """Clause WHERE commune à search/count. OUTIL-PLU-FIX-1 (LOT 5) : config `fr_unaccent` (casse +
    accents), et filtre zone qui SUIT LES SECTEURS ET LES RENVOIS au règlement commun — un secteur
    UBc remonte à {UB, U} (appariement EXACT, jamais A pris pour AU), et une famille UB rattrape ses
    secteurs (UB → UBa, UBc…) par préfixe."""
    where = ["tsv @@ websearch_to_tsquery('fr_unaccent', :q)"]
    params: dict = {"q": q}
    if insee:
        where.append("insee = :insee")
        params["insee"] = insee
    if zone:
        cands = zone_candidats(zone)
        where.append("(upper(zone) = ANY(:zones) OR upper(zone) LIKE :zpref)")
        params["zones"] = cands
        params["zpref"] = _norm(zone).upper() + "%"
    return where, params


def search_reglement(session: Session, q: str, insee: str | None = None, limit: int = 25,
                     zone: str | None = None, offset: int = 0) -> list[dict]:
    """Recherche full-text (fr_unaccent) qui rend le VERBATIM SOURCÉ complet + la référence + le lien.
    `insee` None = île entière. `zone` filtre la famille de zone et ses secteurs (lien contextuel
    fiche → règlement). `offset` pagine RÉELLEMENT (OUTIL-PLU-FIX-1 LOT 5 : offset=25 ne renvoyait plus
    les 25 premiers). Aucun résumé : `texte_verbatim` est le texte brut ; `doute` et
    `pagination_ambigue` sont RENDUS pour affichage."""
    where, params = _search_where(q, insee, zone)
    params["lim"] = limit
    params["off"] = max(0, offset)
    rows = session.execute(text(f"""
        SELECT insee, commune, idurba, to_char(millesime,'YYYY-MM-DD') AS millesime, document,
               zone, article_ref, page_pdf, texte_verbatim, doute, doute_motif, pagination_ambigue,
               source_url, pdf_url, ts_rank(tsv, websearch_to_tsquery('fr_unaccent', :q)) AS rang
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
    where, params = _search_where(q, insee, zone)
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
