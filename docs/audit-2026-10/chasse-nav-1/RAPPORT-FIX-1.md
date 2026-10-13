# RAPPORT — CHASSE-NAV-FIX-1 (corrections de navigation)

Branche `fix/chasse-nav-1` (depuis `main` `5c4b156c`), worktree `~/Desktop/labuse-chasse-nav`, ports 8770/5970. **Ne pas merger.**
Un commit par point, captures avant/après dans `captures/fix/`.

## Verdict (3 gates demandés)
- **banc `chasse_nav` : 10 OK · 0 ÉCART** (les 5 gardes d'écart basculent au vert + 5 gardes positives tenues).
- **banc `chasse_donnees` : 25 OK · 0 ÉCART** (aucune régression de cohérence des données servies).
- **tsc : 0 erreur.**
- vitest : 255 passés · **1 échec PRÉ-EXISTANT** (`ProspectionSolaire.test.tsx` — libellé de source « …, 2025 » obsolète, fichier NON touché par ce fix ; introduit par `c13471c3`).

## Les 6 points

| # | Écart | Correctif | Commit |
|---|---|---|---|
| 1 | **N-2 🔴** fiche disparue plante l'app | Garde `cadastre_disparue` remonté AVANT tout dérivé (+ `faisa`/`gab` montés avec lui pour respecter les règles des hooks) ; bandeau « Parcelle disparue » avec remplaçantes cliquables via `focusParcelle` | `3306d53e` |
| 2 | **N-1 🟡** lien digest `#parcelle=` mort | `emails.py` digest TEXTE `#parcelle=`→`#idu=` + digest HTML : lien « voir la parcelle » (`#idu=`) par parcelle et par priorité ; `events.py` lien stocké aligné (5 sites) | `c789af10` |
| 3 | **N-4 🟡** pas de retour Communes→Scan | `Communes.ouvrirScanPatrimoine` pose `pushOutilRetour({module:'communes'})` après `setModule` (parité Blocs/Permis/Temps) | `57d6c67c` |
| 4 | **N-5 ⚪** constante morte / **N-3 ⚪** Pages Jaunes | Suppression de `etudeZonePdfUrl` ; `pagesJaunes` n'ajoute la commune que si l'adresse ne la contient pas déjà | `e5bcafa1` |
| 5 | **C-obs1 🟡** ouverture de fiche incohérente | CRM, Projets (Kanban+Tinder), Copilote (ReponseInline+App), listing : `select(idu)`→`focusParcelle(idu,{fiche:true})` (vue cartes + recentrage + fiche en un geste) | `6b77bca6` |
| 6 | **F-obs1 ⚪** reset/invitation gatés mobile | `onboarding.py` : `gate=False` sur /invitation (+ admin interne, lien invalide, succès) et /reset (+ pages POST) ; responsive (même builder que /flash). **L'app React reste gatée sur mobile.** Paiement bascule laissé gaté (hors périmètre « mot de passe ») | `69febce2` |

## Preuves live (captures `captures/fix/`)
- **P1** : `P1-N2-avant-crash.png` (ErrorBoundary) → `P1-N2-apres-bandeau.png` (bandeau + remplaçantes AE0919 56 % / AE0920 44 % ; clic → fiche AE0919 ouverte).
- **P2** : `P2-N1-digest-html.html` (digest rendu avec liens `#idu=` « voir la parcelle »).
- **P5** : `P5-Cobs1-crm-fiche-carte-recentree.png` (clic CRM → bascule carte + fiche).
- **P6** : `P6-Fobs1-reset-mobile-apres.png`, `P6-Fobs1-invitation-mobile-apres.png` (formulaire mobile sans gate ni débordement ; `/socle/` mobile reste « disponible sur ordinateur »).

## Notes
- `main` a avancé (`5c4b156c`→`87fa4211`) pendant le travail (autre session) ; la branche reste basée sur `main` au moment du branchement. Mes changements réels (depuis le merge-base) = uniquement les fichiers de ce fix. Pas de rebase (non demandé, « ne pas merger »).
- Rejouer le banc : `PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_nav --api http://127.0.0.1:8770`.
