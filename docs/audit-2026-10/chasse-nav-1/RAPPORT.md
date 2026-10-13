# RAPPORT — CHASSE-NAV-1 (chaque bouton mène au bon endroit)

**VERDICT (5 lignes)**
1. La navigation de l'app est **globalement saine** : les 9 vues du rail s'ouvrent, les raccourcis fiche→outil emportent la parcelle et laissent revenir, l'omnibox ouvre la bonne fiche, Admin↔client fait l'aller-retour, les deep-links `#idu=`/`#radar=1`/`#admin=1` survivent au rechargement, les liens externes (Cadastre/Maps/Errial/KMZ) sont corrects sans `127.0.0.1`, et les PDF ne portent aucun lien douteux.
2. **UN écart bloquant (🔴 N-2)** : ouvrir la fiche d'une parcelle **disparue** du cadastre plante TOUTE l'app (ErrorBoundary) — quel que soit le chemin (projet, veille, recherche, deep-link) — car la fiche calcule `f?.lines.filter(...)` avant son propre garde `cadastre_disparue`.
3. **Deux écarts mineurs (🟡)** : le lien parcelle des digests e-mail (`#parcelle=`) n'ouvre pas la fiche (le front lit `#idu=`) — in-app la cloche reste correcte ; et « Scan patrimoine » depuis Communes n'offre pas le fil de retour que Blocs/Permis/Temps posent.
4. **Deux broutilles (⚪)** : constante morte `etudeZonePdfUrl`→404 (non câblée) et commune dupliquée dans le lien Pages Jaunes.
5. Chasse quasi vide ailleurs : pas de lien vers fonction retirée, pas de bouton vivant vers endpoint absent, pas de doublon ni d'impasse, grisés justifiés ; mobile OK (rien ne déborde, `/flash` utilisable, pages d'entrée app volontairement gatées « ordinateur »). **Banc rejouable** `scripts/coherence/chasse_nav.py` : 5 OK / 5 ECART / exit 1 (vert après FIX-1).

---

## Périmètre & méthode
- Worktree `~/Desktop/labuse-chasse-nav`, branche `audit/chasse-nav-1`, API `:8770` + front vite `:5970`, run servi **q_v18**, **lecture seule** (aucune écriture base/VPS, aucune action irréversible déclenchée).
- Mode **auth-off local** (`auth.enabled()`=False) : écrans admin atteignables, vues scoped en mode pilote/legacy. Limites documentées (ÉTAPE0.md) : `/moi/prefs-carte` 401 (⚪ artefact), liste Projets vide (scoped compte).
- Témoins : bizone `97411000BZ1065`, 2ᵉ parcelle `97415000AB0001`, **disparue** `97411000AE0013` (projets 237/241), communes, run q_v18.
- Inventaire par 6 agents (code) + parcours navigateur piloté (Playwright) + croisement endpoints front↔back + émulation iPhone.

## Les 6 lots
- **A — inventaire** : `NAVIGATION.csv` (~165 passages, 7 colonnes, doublons marqués).
- **B — passages testés** : 9 vues OK ; **N-2 🔴** (disparue), **N-1 🟡** (digest), **N-3 ⚪** (Pages Jaunes). Détails `LOT-B.md`.
- **C — cohérence** : **N-4 🟡** (retour Scan depuis Communes), **C-obs1 🟡** (`select` vs `focusParcelle` recentre la carte ou non) ; familles Courrier/Fiche-commune cohérentes. `LOT-C.md`.
- **D — morts/doublons/impasses** : quasi vide — **N-5 ⚪** (constante morte) ; pas de Street View, pas de bouton→endpoint absent, doublon Densifier non confirmé, pas d'impasse, grisés justifiés. `LOT-D.md`.
- **E — hors de l'app** : **N-1 🟡** (digest) ; domaine protégé (garde `config.py:383`), PDF sans liens, liens expirés → page 404 brandée, `/flash` + `/login` OK. `LOT-E.md`.
- **F — mobile** : **PASS** (rien ne déborde, boutons atteignables) ; **F-obs1 ⚪** (reset/invitation/login gatés « ordinateur » sur mobile, assumé ; `/flash` exempté). `LOT-F.md`.

## Tableau des écarts (détails + causes + fichier:ligne dans ECARTS.md)
| # | Grav. | Écart | Cause (fichier:ligne) |
|---|---|---|---|
| N-2 | 🔴 | Fiche parcelle disparue plante l'app | `Fiche.tsx:561` `f?.lines.filter` avant garde `:688` (payload sans `lines`) |
| N-1 | 🟡 | Lien digest mail n'ouvre pas la fiche | `emails.py:61` `#parcelle=` vs `App.tsx:375` `#idu=` |
| N-4 | 🟡 | « Scan patrimoine » depuis Communes sans retour | `Communes.tsx:56-60` (pas de `pushOutilRetour`) |
| N-3 | ⚪ | Pages Jaunes : commune dupliquée | `liensExternes.ts:32` |
| N-5 | ⚪ | Constante PDF Étude de zone → route 404 (non câblée) | `api.ts:483` |
| C-obs1 | 🟡 | « ouvrir la fiche » recentre la carte selon l'origine (à trancher) | `useApp.ts:764` vs `:772` |
| F-obs1 | ⚪ | reset/invitation/login gatés « ordinateur » sur mobile (assumé) | `onboarding.py:124-143` |

## Priorités pour CHASSE-NAV-FIX-1
1. **N-2 (🔴)** — remonter le retour anticipé `cadastre_disparue` AVANT les dérivés, et/ou `(f?.lines ?? []).filter(...)`. Le back renvoie déjà `cadastre_disparue` (message + `remplacee_par`) : il suffit de l'afficher sans planter.
2. **N-1 (🟡)** — aligner `emails.py:61` sur `#idu={idu}` (et idéalement poser un lien parcelle dans le digest HTML).
3. **N-4 (🟡)** — ajouter `pushOutilRetour({module:'communes'})` au pont Communes→Scan.
4. **N-5/N-3 (⚪)** — supprimer/repointer `etudeZonePdfUrl` ; dédupliquer la commune Pages Jaunes.
5. **C-obs1 / F-obs1** — décisions Vic (unifier `focusParcelle` ? exempter `/reset` du gate mobile ?).

## Banc rejouable (garde automatique)
`PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_nav --api http://127.0.0.1:8770`
→ une ligne `[OK]/[ECART]/[SKIP]` par garde (5 écarts + 5 gardes positives), exit 1 si écart. État au rendu : **5 OK · 5 ECART** (les écarts mordent, attendu avant FIX-1).

## Livrables
`docs/audit-2026-10/chasse-nav-1/` : `MANDAT.md`, `ETAPE0.md`, `NAVIGATION.csv`, `LOT-B.md`, `LOT-C.md`, `LOT-D.md`, `LOT-E.md`, `LOT-F.md`, `ECARTS.md`, `RAPPORT.md`, `captures/` (etape0, N1 ×2, N2, E-flash, F-flash, F-reset-gate) ; banc `scripts/coherence/chasse_nav.py`.
