# M12 — LOT F « Projet »

Branche `feat/m12-f-projet` (worktree isolé). Base : `main` (5e50113). Pas de merge.
Zéro touche au scoring. Backend : un seul ajout (endpoint lecture F7).

## Statut par point

| # | Point | Statut |
|---|-------|--------|
| F1 | Jauge « Votre projet » = 5 segments (Programme/Ampleur/Où/Contraintes/Budget) + progression left→right | ✅ FAIT |
| F2 | « + Décrire un projet » ouvre « Votre projet » DIRECTEMENT | ✅ FAIT |
| F3 | « Le copilote réfléchit » → « LABUSE réfléchit » | ✅ FAIT |
| F4 | Réduire le délai entre étapes (setTimeout artificiel) | ⚠️ CONSIGNÉ — aucun délai artificiel n'existe |
| F5 | Après « Lancer la recherche » → vue 3 colonnes directe (pas la carte globale) | ✅ FAIT |
| F6 | « + Chercher plus » : rien ne se passe | ✅ FAIT (cause + robustesse) |
| F7 | Bouton « Projet » sur la fiche (→ « À trier »), voisin de « + Pipeline » | ✅ FAIT |
| F8 | État vide « Aucun projet encore » : pictogramme gris → menthe | ✅ FAIT |

## Détail

### F1 — jauge 5 segments + progression left→right
`frontend/src/components/projets/ProjetEntretien.tsx`.
- **Budget** devient un 5e `SLOT` à part entière (avant : 4 SLOTS + rendu Budget bricolé à part sous la
  fiche). Il apparaît maintenant dans la fiche projet comme les 4 autres (dt/dd, `tnum`).
- **Bug du segment vert en position 3** : chaque segment s'allumait indépendamment selon *son* champ
  (`s.rempli(fiche)`). Comme l'IA remplit les champs dans un ordre arbitraire (elle peut saisir « Où »
  avant « Programme »), un segment vert isolé apparaissait au milieu. Corrigé en **sémantique de
  progression** : les `remplis` PREMIERS segments s'allument, dans l'ordre (`i < remplis`). La barre
  avance de gauche à droite, sans trou.

### F2 — ouverture directe de « Votre projet »
Avant : « + Décrire un projet » (`ProjetsPanel`) faisait `setView('ia')` → écran copilote à deux portes
(IAStub) ; il fallait cliquer « Démarrer le montage » pour atteindre le formulaire. Maintenant :
- Store `useApp` : nouveau champ `entretienDirect` + actions `ouvrirEntretien(amorce?)` / `clearEntretienDirect()`
  (même nettoyage de nav exclusive que `setView`).
- `ProjetsPanel` (bouton + action de l'état vide) appelle `ouvrirEntretien()`.
- `IAStub` : `useEffect` consomme `entretienDirect` → ouvre l'entretien `ProjetEntretien` immédiatement,
  sans afficher l'écran à deux portes. Le chemin normal (clic Rail → copilote) reste inchangé.

### F3 — libellé
`ProjetEntretien.tsx` : `Loading label="Le copilote réfléchit"` → `"LABUSE réfléchit"`. Occurrence unique
(grep vérifié).

### F4 — délai entre étapes — CONSIGNÉ (pas de bug à corriger)
Recherche exhaustive : **aucun `setTimeout`/`sleep`/`asyncio.sleep` artificiel** dans le flux de
l'entretien (front `ProjetEntretien`/`Loading`, back `ia.py:ia_entretien`, `core.complete`, couche IA).
Le « délai entre étapes » perçu est le **round-trip réel vers le LLM** (`core.complete`, `MODEL_NL`) —
il n'y a pas de temporisation factice à raccourcir. **Avant/après = inchangé (aucune valeur artificielle
trouvée).** Fabriquer un raccourci reviendrait soit à trafiquer l'appel IA réel, soit à inventer un délai
inexistant : les deux sont écartés (règle « never ship broken »). Si Vic constate une lenteur, le levier
est le modèle/tokens de `core.complete`, hors périmètre LOT F (touche scoring/IA).

### F5 — redirection vers la vue 3 colonnes
`ProjetEntretien.tsx`, mutation `lancer`. Avant : `deriveProjet` + `getApercu` → `apply(filtres)` +
`setView('cartes')` + restitution flottante + brouillon non persisté (la carte globale, pas le projet).
Maintenant : `lancer` **persiste le projet** (`createProjet`, dédup douce serveur) puis
`setOpenProjet({id, nom})` → **vue kanban 3 colonnes** (À trier / Retenues / Écartées). Le kanban
(re)propose les parcelles du jour à l'ouverture (`proposerProjet`, idempotent) → elles atterrissent
dans « À trier ». Imports morts retirés (`deriveProjet`, `getApercu`, `useApplySearch`).

### F6 — « + Chercher plus » : rien ne se passe
Diagnostic : l'endpoint `/projets/{id}/chercher-plus` **fonctionne** (testé : `n_added:24`) et le
handler Kanban est correct. La cause de « rien ne se passe » en **dev** : le **proxy Vite ne
proxifiait PAS `/projets`** (ni `/ia`, `/crm`, `/pipeline`, `/modules`…) → tous les appels métier
tombaient en 404 silencieux sous `npm run dev`. En prod FastAPI sert `dist/` à la même origine (aucun
proxy), donc invisible tant qu'on ne teste pas en dev.
- Fix : `frontend/vite.config.ts` + `.js` — liste `apiPaths` complétée avec les préfixes métier.
- Robustesse : `ProjetKanban` + `ParcoursTinder` — la mutation `elargir` a désormais un `onError`
  (« recherche indisponible — réessayez ») : un échec n'est **jamais** silencieux.

### F7 — bouton « Projet » sur la fiche
`frontend/src/components/fiche/Fiche.tsx` — nouveau `ProjetButton`, placé **juste après `+ Pipeline`**.
- **Distinction visuelle à l'œil** : Pipeline = **menthe** (CRM prospection), Projet = **violet** (la
  couleur du copilote/projet dans toute l'app — porte « Montage de projet », badges kanban). Bouton
  bordé violet quand non rattaché, violet plein quand rattaché.
- Non rattachée → menu déroulant des projets ACTIFS ; clic sur un projet = `ajouterParcelle` →
  la parcelle arrive dans **« À trier »** (`proposee`). Projets déjà contenant la parcelle = grisés
  (« ✓ dedans »).
- Déjà rattachée → bouton **actif** (violet plein) affichant le nom du projet (ou « ✓ N projets ») ;
  clic = ouvre le projet (si un seul) ou le menu (si plusieurs).
- **Multi-projet : AUTORISÉ** (décision). Une parcelle peut nourrir plusieurs opérations ; le serveur
  dédoublonne par projet (`ON CONFLICT DO NOTHING`). Le bouton reflète le nombre (« ✓ 2 projets »).
- Backend : réutilise `/projets/{id}/ajouter` (existant). **Ajout minimal** d'un endpoint LECTURE
  `GET /projets/pour-parcelle/{idu}` (projets actifs du compte contenant la parcelle + statut) —
  nécessaire pour l'état « déjà rattachée ». SEC-IDOR : borné au compte (cloison en Python, pas de
  bind NULL non typé). Déclaré avant `/{pid}` (lève l'ambiguïté de route). Testé : attaché (2 projets),
  non attaché (`[]`), dédup (`already:true`).

### F8 — état vide en menthe
`frontend/src/components/States.tsx` : `EmptyState` prend une prop `mint` → `Oiseau dim={!mint}` (menthe
`#2FE0A0` au lieu du gris de repos `#1E2A23`). `ProjetsPanel` : `mint={!showArchived}` sur « Aucun
projet encore » (l'état « Aucun projet archivé » reste au gris de repos, cohérent). Les 2 autres usages
d'`EmptyState` (ResultsSection) sont intacts (prop optionnelle, défaut = gris).

## Vérifications

- **Build front** : `npm run build` → **0 erreur TS** ✅
- **Tests backend** (F7) : `pytest -k projet` → 8 passed (`.venv`) ; `test_projet_m2.py` → 4 passed
  (conda worktree). Endpoint F7 prouvé en direct (attaché/non/dédup/multi-projet).
- **Golden** : `qa/golden_check.py` sur port 8023 → **116/116 PASS**, 0 FAIL ✅

## Laissé / non fait

- **F4** : aucun délai artificiel n'existe → rien à corriger (consigné ci-dessus).
- Rien d'autre en suspens. Pas de merge (mandat).
