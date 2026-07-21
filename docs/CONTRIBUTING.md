# Contribution — politique binaires (léger en git, lourd hors git)

Trois règles pour garder l'historique git sain :

1. **Doc légère EN git** : Markdown, petits schémas SVG, petites captures nécessaires à la
   compréhension. Le texte et les sources versionnables restent dans le dépôt.
2. **Artefacts lourds HORS git** : dossiers de revue générés (PDF), tuiles/ortho, captures
   d'audit volumineuses, modèles binaires. Ils sont **régénérables** (scripts) ou stockés
   ailleurs — jamais dans l'historique. Conventions ignorées : `reports/revues/`,
   `reports/**/DOSSIER-*.pdf`, `reports/*/captures*/`, `reports/*/_tiles/`, `data/*` (hors
   whitelist JSON/CSV), `audit_shots/`, `outputs/`.
3. **Un doute = léger** : dans le doute sur le poids ou la nécessité, mettre le contenu hors
   git et laisser un pointeur (chemin de régénération) dans la doc. Le nettoyage d'un binaire
   DÉJÀ tracké (réécriture d'historique) est une décision explicite du mainteneur, jamais
   automatique.

*(État au 2026-07-21 : ~318 Mo de binaires historiquement trackés — surtout
`reports/j3-revue/DOSSIER-REVUE-J3.pdf` (13,8 Mo, généré par `scripts/j3_revue_dossier.py`) et
les captures `docs/design/captures/**`. Leur retrait éventuel de l'historique = décision Vic.)*
