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
    fetched_at         timestamptz,
    tsv                tsvector
);
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
    Renvoie aussi le drapeau pagination_ambigue (document-level)."""
    pages = _pages(path)
    ambigu = _pagination_ambigue(pages)
    # flux plat + carte offset→page
    starts, buf, pos = [], [], 0
    for i, t in enumerate(pages):
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
    last_zone = None
    for i, m in enumerate(heads):
        ref = re.sub(r'\s+', ' ', m.group(1).strip())
        end = heads[i + 1].start() if i + 1 < len(heads) else len(flat)
        body = flat[m.start():end].strip()
        zm = _ZONE_FROM_ART.match(ref) or _ZONE_FROM_ZONE.match(ref)
        if zm:
            last_zone = zm.group(1).upper()
        zone = last_zone
        if ref.upper().startswith("ZONE"):
            continue   # un titre de zone n'est pas un extrait servable en soi (il précède ses articles)
        doute = len(re.sub(r'\s', '', body)) < 25
        out.append({
            "article_ref": ref, "zone": zone, "page_pdf": page_of(m.start()),
            "texte": body, "doute": doute,
            "doute_motif": "extrait quasi vide — page peut-être illisible/scannée, à vérifier au PDF" if doute else None,
        })
    return out, ambigu


def ensure_ddl(session: Session) -> None:
    for stmt in _DDL.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))


def ingest_reglement(session: Session, *, insee: str, commune: str, idurba: str, millesime: str | None,
                     document: str, pdf_path: str, source_url: str, fetched_at: str | None,
                     commit: bool = True, log=lambda *_: None) -> dict:
    """Ré-ingère (idempotent) les extraits article d'un document. Purge (insee, document) puis insère."""
    ensure_ddl(session)
    extraits, ambigu = _split_articles(pdf_path)
    session.execute(text("DELETE FROM plu_reglement_extrait WHERE insee = :i AND document = :d"),
                    {"i": insee, "d": document})
    for e in extraits:
        session.execute(text("""
            INSERT INTO plu_reglement_extrait
              (insee, commune, idurba, millesime, document, zone, article_ref, page_pdf,
               texte_verbatim, doute, doute_motif, pagination_ambigue, source_url, fetched_at, tsv)
            VALUES
              (:insee, :commune, :idurba, :millesime, :document, :zone, :article_ref, :page_pdf,
               :texte, :doute, :doute_motif, :ambigu, :url, :fetched_at,
               to_tsvector('french', coalesce(:article_ref,'') || ' ' || :texte))
        """), {"insee": insee, "commune": commune, "idurba": idurba, "millesime": millesime,
               "document": document, "zone": e["zone"], "article_ref": e["article_ref"],
               "page_pdf": e["page_pdf"], "texte": e["texte"], "doute": e["doute"],
               "doute_motif": e["doute_motif"], "ambigu": ambigu, "url": source_url,
               "fetched_at": fetched_at})
    if commit:
        session.commit()
    n_doute = sum(1 for e in extraits if e["doute"])
    log(f"  ✓ {insee} {document} : {len(extraits)} extraits article"
        + (f" · {n_doute} douteux" if n_doute else "")
        + (" · PAGINATION AMBIGUË" if ambigu else ""))
    return {"insee": insee, "document": document, "extraits": len(extraits),
            "doutes": n_doute, "pagination_ambigue": ambigu}


def search_reglement(session: Session, q: str, insee: str | None = None, limit: int = 25) -> list[dict]:
    """Recherche full-text (french) qui rend le VERBATIM SOURCÉ complet + la référence + le lien.
    `insee` None = île entière. Aucun résumé : `texte_verbatim` est le texte brut du règlement ;
    `doute` et `pagination_ambigue` sont RENDUS pour affichage."""
    where = ["tsv @@ websearch_to_tsquery('french', :q)"]
    params: dict = {"q": q, "lim": limit}
    if insee:
        where.append("insee = :insee")
        params["insee"] = insee
    rows = session.execute(text(f"""
        SELECT insee, commune, idurba, to_char(millesime,'YYYY-MM-DD') AS millesime, document,
               zone, article_ref, page_pdf, texte_verbatim, doute, doute_motif, pagination_ambigue,
               source_url, ts_rank(tsv, websearch_to_tsquery('french', :q)) AS rang
        FROM plu_reglement_extrait
        WHERE {' AND '.join(where)}
        ORDER BY rang DESC, insee, page_pdf
        LIMIT :lim
    """), params).mappings().all()
    return [dict(r) for r in rows]


def corpus_status(session: Session) -> dict[str, dict]:
    """État INGÉRÉ par INSEE (extraits, doutes, pagination ambiguë). L'API le croise avec
    plu_millesimes pour dire RNU / révision en cours / non ingéré."""
    if session.execute(text("SELECT to_regclass('plu_reglement_extrait')")).scalar() is None:
        return {}
    rows = session.execute(text("""
        SELECT insee, commune, min(idurba) AS idurba, to_char(max(millesime),'YYYY-MM-DD') AS millesime,
               count(*) AS extraits, count(*) FILTER (WHERE doute) AS doutes,
               bool_or(pagination_ambigue) AS pagination_ambigue,
               string_agg(DISTINCT document, ', ') AS documents
        FROM plu_reglement_extrait GROUP BY insee, commune ORDER BY insee
    """)).mappings().all()
    return {r["insee"]: dict(r) for r in rows}
