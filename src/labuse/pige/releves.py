"""FLUX-1 (F3) — « voir la donnée s'accumuler » : les compteurs Radar et la mesure de finesse.

Ce ne sont pas les annonces qui affinent l'estimateur, ce sont les RAPPROCHEMENTS : une annonce
(prix demandé) reliée plus tard à une vente DVF (prix acté) sur la même parcelle. Le rapprochement
existe déjà (`pige.cycle.matcher_dvf` : rattachement Sourcé + vente DVF dans [3;18] mois → `vendue`
+ `vendue_ecart_prix`). Ce module ne fait que LIRE : compteurs cumulés, courbe (depuis les relevés
quotidiens `radar_releves`), et l'écart demandé/acté médian par type — honnête sur le nombre de
paires derrière chaque chiffre.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

#: en-dessous de ce nombre de paires, l'écart médian est affiché « encore fragile » (jamais caché,
#: jamais présenté comme sûr) — la mesure de finesse doit dire sa propre solidité (F3.3).
SEUIL_PAIRES_FIABLE = 30


def _scalar(db: Session, sql: str, **kw) -> int:
    return int(db.execute(text(sql), kw).scalar() or 0)


def compteurs(db: Session) -> dict:
    """Les 5 compteurs cumulés + « +N cette semaine » (F3.1). Lecture seule."""
    depuis = date.today() - timedelta(days=7)
    annonces = _scalar(db, "SELECT count(*) FROM pige_annonces")
    annonces_sem = _scalar(db, "SELECT count(*) FROM pige_annonces WHERE date_saisie >= :d", d=depuis)
    biens = _scalar(db, "SELECT count(*) FROM pige_biens")
    rattachees = _scalar(db, "SELECT count(*) FROM pige_biens WHERE idu IS NOT NULL")
    paires = _scalar(db, "SELECT count(*) FROM pige_biens WHERE statut = 'vendue'")
    paires_sem = _scalar(db, "SELECT count(*) FROM pige_biens WHERE statut = 'vendue' AND vendue_le >= :d", d=depuis)
    communes = _scalar(db, "SELECT count(DISTINCT commune) FROM pige_biens")
    types = _scalar(db, "SELECT count(DISTINCT type_bien) FROM pige_biens WHERE type_bien IS NOT NULL")
    return {
        "annonces": annonces, "annonces_semaine": annonces_sem,
        "biens": biens,   # S5 — dénominateur M du compteur « rattachées N / M »
        "rattachees": rattachees, "rattachees_pct": round(100.0 * rattachees / biens, 1) if biens else None,
        "paires": paires, "paires_semaine": paires_sem,
        "communes": communes, "communes_total": 24,
        "types": types,
    }


def ecart_par_type(db: Session) -> list[dict]:
    """F3.3 — écart demandé/acté MÉDIAN par type (maison / appartement / terrain), calculé sur les
    paires, avec le nombre de paires derrière chaque chiffre. `ecart_pct` = médiane de
    (prix_acté − prix_demandé) / prix_demandé (négatif = vendu sous le prix affiché). L'écart n'est
    servi QUE sur un rattachement Sourcé (déjà garanti par `matcher_dvf`). `fragile` si n < seuil."""
    rows = db.execute(text(
        "SELECT b.type_bien AS type, count(*) AS n, "
        "  percentile_cont(0.5) WITHIN GROUP ("
        "    ORDER BY (b.vendue_valeur - f.prix)::float / NULLIF(f.prix, 0)) AS ecart "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE b.statut = 'vendue' AND b.vendue_valeur IS NOT NULL AND f.prix IS NOT NULL "
        "  AND f.prix > 0 AND b.type_bien IS NOT NULL "
        "GROUP BY b.type_bien ORDER BY count(*) DESC")).mappings().all()
    return [{"type": r["type"], "n": int(r["n"]),
             "ecart_pct": round(float(r["ecart"]) * 100, 1) if r["ecart"] is not None else None,
             "fragile": int(r["n"]) < SEUIL_PAIRES_FIABLE}
            for r in rows]


def courbe(db: Session, jours: int = 120) -> dict:
    """F3.2 — la courbe cumulée des paires depuis le déploiement (relevés quotidiens). `depuis_le` =
    premier relevé (la courbe DIT quand elle commence, pas de reconstruction inventée)."""
    depuis = date.today() - timedelta(days=jours)
    rows = db.execute(text(
        "SELECT jour, paires, annonces, rattachees FROM radar_releves "
        "WHERE jour >= :d ORDER BY jour"), {"d": depuis}).mappings().all()
    premier = db.execute(text("SELECT min(jour) FROM radar_releves")).scalar()
    return {
        "points": [{"jour": r["jour"].isoformat(), "paires": r["paires"],
                    "annonces": r["annonces"], "rattachees": r["rattachees"]} for r in rows],
        "depuis_le": premier.isoformat() if premier else None,
    }


def bloc_radar(db: Session) -> dict:
    """Le bloc Radar complet de la page Flux + la tuile Pilotage (F3.5) : compteurs + courbe + écart."""
    return {"compteurs": compteurs(db), "ecart": ecart_par_type(db), "courbe": courbe(db)}


def ecrire_releve(db: Session, jour: date | None = None) -> dict:
    """F3.2 — le JOB de fin de journée : écrit (upsert) la photo cumulée du jour dans `radar_releves`.
    Idempotent (ON CONFLICT jour) : rejouer le même jour rafraîchit la ligne, ne la duplique pas."""
    j = jour or date.today()
    c = compteurs(db)
    db.execute(text(
        "INSERT INTO radar_releves (jour, annonces, rattachees, paires, communes, types) "
        "VALUES (:j, :a, :r, :p, :co, :ty) "
        "ON CONFLICT (jour) DO UPDATE SET annonces = EXCLUDED.annonces, rattachees = EXCLUDED.rattachees, "
        "  paires = EXCLUDED.paires, communes = EXCLUDED.communes, types = EXCLUDED.types"),
        {"j": j, "a": c["annonces"], "r": c["rattachees"], "p": c["paires"],
         "co": c["communes"], "ty": c["types"]})
    return {"jour": j.isoformat(), "annonces": c["annonces"], "rattachees": c["rattachees"],
            "paires": c["paires"], "communes": c["communes"], "types": c["types"]}
