# OUTILS-P1-1 — Retouches lot 3 (Permis, Successions, Scan patrimoine, Courrier)

Branche `fix/outils-p1-1` (suite). Étape 0 OK : `pwd`=labuse-outils, branche `fix/outils-p1-1`, arbre
propre. Pas de merge, DA existante, une capture avant/après par point. Ports 10010 / 7210.

Captures : `lot3-<outil>-avant.png` / `lot3-<outil>-apres.png`.

## Liste des 13 points — fait / non fait

### PERMIS (`ModulePanel.tsx` M03)
| # | Point | État |
|---|-------|------|
| 1 | Aucun libellé d'état coupé par « … » (2 lignes autorisées) | **Fait** — `truncate` retiré de la définition, bouton `items-start` : « Permis dormants · sans achèvement déclaré (DAACT) » passe sur 3 lignes, aucune ellipse. |
| 2 | « Autorisés · depuis 90 jours » → « Récents · autorisés depuis 90 jours » | **Fait** — label `Récents`, définition `autorisés depuis 90 jours`. |
| 3 | « Ancien permis » → « Permis dormants » (mot du sous-titre) | **Fait** — label `Permis dormants` (le sous-titre dit « permis dormants ») ; infobulle + « permis dormants sur la carte » alignés. |
| 4 | Date de la donnée Sitadel sous « 50 808 permis autorisés en base » | **Fait** — « Donnée Sitadel au 2026-08-31 » (`donnees_jusqu_au` = `max(date)` de `sitadel_permits`, lue en base). |

### SUCCESSIONS (`Successions.tsx`)
| # | Point | État |
|---|-------|------|
| 5 | Libellé du grand chiffre (Estimé) + tri de la liste | **Fait** — le chiffre à droite est libellé « plancher restant » ; bandeau « Triées par plancher restant estimé, du plus grand au plus petit. » |
| 6 | 97409000AY1281 (zone A) 12 031 m² : que mesure-t-il ? | **Investigation, AUCUNE correction (comme demandé).** C'est `sdp_residuelle_m2` = **plancher restant estimé = potentiel à bâtir** (même grandeur « Estimé » que la fiche). Comptage sur la liste servie (île, 6 151) : **1 292 parcelles en zone A ou N** (924 en A, 368 en N), dont **59** affichent un potentiel à bâtir strictement positif (AY1281 en fait partie). **Arrêt sur ce point.** |
| 7 | « 74 ans » insécable | **Fait** — espace insécable (U+00A0) entre le nombre et « ans » (vérifié DOM : charCode 160). |

### SCAN PATRIMOINE (`ModulePanel.tsx` M02 + `modules.py patrimoine`)
| # | Point | État |
|---|-------|------|
| 8 | « 1 871 recensées » → « 1 871 parcelles » | **Fait** — résumé replié « N parcelles · surface » (le détail Recensées/Rattachées/Visibles reste dans le tableau dessous). |
| 9 | Surfaces des blocs en ha dès 1 ha (comme le total) | **Fait** — `fmtM2` (bascule ha à 10 000 m²) : « 30 694 m² » → « 3,07 ha ». |
| 10 | « 12 affichés » sur 460 : « voir plus » sous la liste | **Fait** — backend param `blocs_limit` (défaut 12, cap 500) + bouton « Voir plus (448 de plus) », fetch lazy : 12 → 460 blocs. |

### COURRIER (`ModulePanel.tsx` M09)
| # | Point | État |
|---|-------|------|
| 11 | Étape « ③ 3 · Envoi » : un seul chiffre | **Fait** — la pastille porte le numéro (ou ✓), le texte ne le répète plus : « ③ 3 · Envoi » → « ③ Envoi ». |
| 12 | Ligne « Total » (N × prix) au-dessus de « Déposer une demande d'envoi » | **Fait** — « Total · 1 × 2,50 € = 2,50 € » juste au-dessus du bouton (montant estimé, prix lu de `/courrier/statut`). |
| 13 | Retirer « (SPF/CERFA) » du texte d'introduction | **Fait** — « Adressage générique — aucune identité de propriétaire particulier. » |

## Vérification
- tsc 0 · vitest **326** (dont PermisDouble/Courrier/Assemblage mis à jour) · secrets · pytest unitaires
  (relancé) · DB `test_retours16/17_permis` + `test_patrimoine` **16 passed** · cohérence 12 témoins.
- Fix robustesse : `patrimoine()` appelée en direct (copilote/tests) → `blocs_limit` ramené à 12 si non résolu
  (même garde que `limit`/`offset`).
- Captures « avant » des outils partageant `ModulePanel.tsx` (Scan, Courrier) prises via `git stash` du
  lot 3 (état committé lot 1), puis `stash pop` — l'« avant » est donc bien l'état d'avant ce lot.
