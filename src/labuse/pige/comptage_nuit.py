"""OPS-NUIT-2 — LE compteur Radar de la nuit : UN SEUL chiffre par notion, PAR PORTAIL.

Le 02/11 disait TROIS choses différentes pour la même nuit :
  · « dernière capture » = 152 — SOMME de `pige_passes.n_nouvelles` sur toutes les passes auto du soir
    (la passe « nouvelles » ET la passe « relecture » comptent chacune des nouvelles → 33 + 119) ;
  · le résumé du matin = 119 — la DERNIÈRE ligne `pige_passes` (ORDER BY id) seule (ici la relecture) ;
  · le compte-rendu de l'extension = « Leboncoin 2, Bien'ici 3 » — des PAGES lues, pas des annonces.

Trois lectures, trois nombres, aucune par portail (``pige_passes`` ne porte pas le portail). Ces chiffres
``n_nouvelles`` sont l'AUTO-DÉCLARATION de l'extension (comptée page par page, sommée entre passes).

La SOURCE DE VÉRITÉ par portail, c'est ``pige_annonces`` : une ligne par annonce (``url_sortante`` /
``list_id`` UNIQUES), avec son ``portail`` et son ``created_at`` = première fois vue. « Annonces nouvelles
de la nuit », par portail = les lignes ``pige_annonces`` créées ce jour-là (heure Réunion). C'est ce
compteur-ci, et LUI SEUL, qu'affichent le Tableau de bord, le résumé du matin et l'admin Radar.

La notion « pages lues » (compte-rendu de l'extension) reste distincte et nommée comme telle — jamais
confondue avec « annonces nouvelles ».
"""
from __future__ import annotations

from sqlalchemy import text

#: fuseau de référence du « jour » Radar (une nuit = un jour calendaire Réunion).
_TZ = "Indian/Reunion"


def comptage_nuit(ex, jour: str | None = None) -> dict:
    """Le comptage canonique de la nuit, par portail, lu de ``pige_annonces`` (vérité par portail).

    `ex` = une Connection (``engine().begin()``) ou une Session (``session_scope``) — les deux savent
    ``execute(text(...))``. `jour` = date ISO « AAAA-MM-JJ » en heure Réunion ; None → la nuit de la
    DERNIÈRE capture automatique (date Réunion du dernier ``pige_passes.captured_at`` source='auto').

    Retour : ``{jour, par_portail:[{portail, nouvelles}], nouvelles, pages, captured_at}`` où
    ``nouvelles`` = total (somme des portails) et ``pages``/``captured_at`` = l'activité de capture
    (``pige_passes`` auto) du même soir, exposée À PART (diagnostic), jamais mélangée au total d'annonces.
    """
    # 1) jour de référence = celui passé, sinon la date Réunion de la dernière capture AUTO.
    cap = ex.execute(text(
        "SELECT max(captured_at) FROM pige_passes WHERE source = 'auto'")).scalar()
    jour_sql = ex.execute(text(
        "SELECT COALESCE(CAST(:j AS date), (CAST(:c AS timestamptz) AT TIME ZONE :tz)::date)"),
        {"j": jour, "c": cap, "tz": _TZ}).scalar()
    out: dict = {"jour": jour_sql.isoformat() if jour_sql else None,
                 "par_portail": [], "nouvelles": 0,
                 "captured_at": cap.isoformat() if cap else None, "pages": 0}
    if jour_sql is None:
        return out                                   # aucune capture auto encore : rien à compter

    # 2) annonces NOUVELLES de la nuit, par portail (created_at tombe ce jour Réunion).
    rows = ex.execute(text(
        "SELECT COALESCE(portail, '?') AS portail, count(*) AS n FROM pige_annonces "
        "WHERE (created_at AT TIME ZONE :tz)::date = CAST(:j AS date) "
        "GROUP BY COALESCE(portail, '?') ORDER BY n DESC, portail"),
        {"tz": _TZ, "j": jour_sql.isoformat()}).all()
    out["par_portail"] = [{"portail": r[0], "nouvelles": int(r[1])} for r in rows]
    out["nouvelles"] = sum(int(r[1]) for r in rows)

    # 3) activité de capture du soir (pages lues par l'extension) — notion DISTINCTE, pour diagnostic.
    if cap is not None:
        pages = ex.execute(text(
            "SELECT COALESCE(sum(n_pages), 0) FROM pige_passes "
            "WHERE source = 'auto' AND captured_at = :c"), {"c": cap}).scalar()
        out["pages"] = int(pages or 0)
    return out


def ligne_resume(comptage: dict) -> str:
    """Une ligne lisible identique partout : « N annonce(s) nouvelle(s) (Portail a · Portail b) ».
    Les NOMS d'affichage des portails viennent du SEUL endroit autorisé (pige/portails.py)."""
    from . import portails
    total = int(comptage.get("nouvelles") or 0)
    pp = comptage.get("par_portail") or []
    detail = " · ".join(f"{portails.nom(p['portail'])} {p['nouvelles']}" for p in pp)
    base = f"{total} annonce(s) nouvelle(s)"
    return f"{base} ({detail})" if detail else base
