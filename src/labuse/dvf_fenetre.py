"""CHASSE-INVARIANTS-FIX-1 Lot 5 (E-04) — la fenêtre des ventes DVF, ancrée une fois pour toutes.

Une fenêtre « N ans / N mois » de ventes DVF doit être ancrée sur la DERNIÈRE vente du jeu servi
(`max(date_mutation)`), JAMAIS sur `CURRENT_DATE` : DVF s'arrête ~9 mois avant aujourd'hui, donc
l'horloge qui avance jette silencieusement les ventes du vieux bord de la fenêtre (île : −1 068
ventes, −8,9 % ; témoin 97411000AK0182 : 129 réelles vs 121 servies). Un SEUL helper, lu par la
fiche « Mon secteur », le Flash, le Dossier, les PDF et les comparables — fin des chemins parallèles.

L'ancre exclut la ligne parasite (1 enregistrement 2026-08-10 à heure ≠ minuit, hors du flux
mensuel) via `date_trunc('day', …)` : même convention que `zone.py`/`commune.py`/`anc.py`.
"""
from __future__ import annotations

#: dernière date de mutation RÉELLE du jeu DVF servi (ligne « minuit », hors parasite).
ANCRE_DVF_SQL = ("(SELECT max(date_mutation) FROM dvf_mutations "
                 "WHERE date_mutation = date_trunc('day', date_mutation))")


def fenetre_dvf_sql(col: str = "dm.date_mutation", *,
                    annees_param: str | None = None, mois_param: str | None = None) -> str:
    """Fragment SQL : `col` dans la fenêtre ancrée sur la dernière vente DVF (jamais CURRENT_DATE).
    La taille de la fenêtre reste un bind-param (`:<annees_param>` ou `:<mois_param>`). Exclut aussi
    la ligne parasite non-minuit. À insérer dans un `WHERE` (f-string de la requête)."""
    if annees_param:
        delta = f"make_interval(years => :{annees_param})"
    elif mois_param:
        delta = f"make_interval(months => :{mois_param})"
    else:
        raise ValueError("fenetre_dvf_sql : préciser annees_param ou mois_param")
    return (f"{col} >= ({ANCRE_DVF_SQL} - {delta}) "
            f"AND {col} = date_trunc('day', {col})")
