"""RADAR (pige d'annonces) — domaine transactionnel ISOLÉ.

Doctrines gravées (mandat RADAR V0 §2, NON négociables) :
  · Collecte 100 % HUMAINE — aucun code de ce paquet (ni d'ailleurs) ne requête, fetch, parse ou
    capture un portail d'annonces. Tout entre par la saisie admin. Recette : `tests/test_pige_socle.py`.
  · JAMAIS de republication — ni photo, ni titre, ni texte d'annonce, ni coordonnées vendeur, nulle
    part (app, mails, exports). Les captures sont des documents de TRAVAIL internes, répertoire privé
    jamais servi par le web.
  · Sourcé / Estimé / Absent sur le RATTACHEMENT parcelle ; anti-invention sur l'EXTRACTION (champ
    illisible = null, jamais deviné).
  · Le Radar n'entre PAS dans le scoring. Il s'affiche, il ne pondère rien.
  · Tables `pige_*` isolées — en V0, rien n'arrose le reste de l'app.
"""
