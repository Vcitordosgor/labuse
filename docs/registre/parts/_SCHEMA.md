# Schéma FAITS.csv — 13 colonnes, RFC-4180

Ordre des colonnes (identique pour tous les fragments) :

1. `id` — identifiant stable (ex. FP-012, FC-003, OUT-PLU-004)
2. `libelle` — libellé EXACT affiché à l'écran (copié du code/JSX)
3. `ecran_section` — écran + section précise
4. `autres_surfaces` — toutes les autres surfaces où le même fait apparaît (`;`-séparé) ou « — »
5. `type` — donnée brute | dérivée | calcul | verdict | estimation
6. `source` — table.colonne OU fonction fichier:ligne
7. `formule` — formule en clair + réf réglementaire (R.111-22, L.562-1, loi 2025-1129, barème 2026…)
8. `unite_format` — unité, arrondi, format
9. `millesime` — millésime de la donnée + comment il est affiché
10. `si_manque` — ce qui est montré quand la donnée manque
11. `test` — test automatisé fichier::nom, ou « aucun »
12. `verif_independante` — audit (nu-1 lot X / nu-2 / J) + nb parcelles, ou « jamais vérifié »
13. `doute` — tout ce qui semble faux/ambigu/sur-promis, ou « — »

Règles CSV : chaque champ entre guillemets doubles `"`, guillemets internes doublés `""`,
pas de saut de ligne dans un champ (remplacer par ` / `). UNE ligne = UN fait. Pas de ligne d'en-tête
dans les fragments (elle est ajoutée à la concaténation).
