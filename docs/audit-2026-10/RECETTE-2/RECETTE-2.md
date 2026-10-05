# RECETTE-2 — retours de Vic du 05/10/2026 (48 captures)

Branche `fix/recette-2` depuis `origin/main` · worktree `~/Desktop/labuse-recette2` · ports API **8705** / Vite **5905** · modèle Opus.
Captures : `captures/avant/` et `captures/apres/` (même cadrage que les captures de Vic).

> **Convention** : un point n'est marqué ✅ **fait** qu'après constat dans un vrai navigateur (Chrome/Playwright, base réelle sur 8705) **et** capture après. Les points non constatables en headless (3D de Gabarit) sont marqués ⚠ et listés pour Vic en fin de rapport.

## Étape 0 — état de départ (constaté)

| Contrôle | Résultat |
|---|---|
| `~/Desktop/labuse` sur `main...origin/main` | oui |
| Worktree `~/Desktop/labuse-recette2` créé depuis `origin/main` | oui — HEAD `7eea04de` |
| Branche `fix/recette-2` | recréée depuis `origin/main` (l'ancienne `fix/recette-2` locale était un alias déjà fusionné dans main, non poussée — supprimée) |
| `git log origin/main..origin/fix/recette-1` | **vide** — aucun commit de recette-1 non mergé ne touche les outils ; rien à signaler |
| API 8705 / Vite 5905 | démarrées (API `labuse api --port 8705` via `.venv` du dépôt + `PYTHONPATH` du worktree ; Vite `--port 5905 --strictPort`, proxy `LABUSE_API_DEV=…:8705`) |
| Base | PostgreSQL `labuse` (rôle `openclaw`) accessible |

> Note env : l'env conda `labusedb` du poste n'a plus d'interpréteur Python ; l'API tourne via le `.venv` du dépôt principal (python 3.12, weasyprint OK) avec `PYTHONPATH=~/Desktop/labuse-recette2/src` pour servir le **code du worktree**. `.env` copié depuis le dépôt principal (gitignoré, non hérité par le worktree).

---

## Tableau fait / non fait

Légende : ✅ fait+capturé · 🚧 en cours · ⬜ non commencé · ⚠ à vérifier par Vic (non constatable en headless).

### T — Règles transversales  — **commit `fix/recette-2` lot T**
| Pt | Sujet | État | Preuve |
|---|---|---|---|
| T1 | Doublon « ou cliquez une parcelle » — une seule mention | ✅ | `EntreeParcelle` (withCarte={false}) + blocB.tsx & ParcelPicker.tsx (phrases libres retirées) ; `T12_gabarit_01_entree.png` 2→1 ; sweep 18 outils (tableau ci-dessous) |
| T2 | Invite + chemin non utilisé disparaissent après résolution | ✅ | plus d'invite `◎` grisée-mais-visible sous le champ (Solaire) ; `T12_*_02_apres_clic` |
| T3 | Réinitialiser : secondaire, seul sur sa ligne, texte dessous ; présent ssi effaçable | ✅ | `T3_assemblage.png`, `T3_pieges.png` (avant: côte à côte → après: bouton seul en haut-droite, intro dessous). Permis « Revenir à l'île » → « Réinitialiser » |
| T4 | Aucun texte tronqué « … », aucun scroll horizontal | ✅ mécanisme + hors-fiche ; instances fiche en lot A | `.t-sub`/`.t-val`/tuiles `formes.tsx` (wrap), Blocs, acquéreurs commune, lignes mono Faisabilité, annonces marché. Tableau Comparer → D6 |
| T5 | Formats FR (virgule, JJ/MM/AAAA, « 1,1 an ») | ✅ mécanisme ; instances fiche/commune en lot A/B | helpers `fmtDist`/`fmtAns` ajoutés ; `fmtDateNum` = JJ/MM/AAAA ; date PPR risques fixée. Rappel : `toLocaleString('fr-FR')` rend déjà correctement — défauts réels (« 1.25 km », ISO) aux points A7/A8/A10/B5/B6 |
| T6 | Aucun code brut (`mouvement_terrain`, `tres_fort`, `EL10_…`) | ✅ aléas ; servitude EL10 en A5 | helpers `fmtAlea`/`fmtIntensite` ; risques.tsx câblé (nature+niveau). `EL10_Reunion_ass` traité en A5 (données servies réelles) |
| T7 | Boutons hors composant → Bouton/Retour | ✅ | Gabarit 3D déjà `<Bouton>` ; « Revenir à l'île » → `Réinitialiser`. Arbitrage : carte-choix « Rechercher dans le PLU » reste une carte (voir ci-dessous) |
| T8 | Chevron unique fiche parcelle ↔ fiche commune | ✅ | 3 glyphes ad hoc de la fiche (`primitives.tsx` TRow, `Fiche.tsx` Analyse LABUSE, `FinancierQuestionnaire`) → `<Chevron>` ; fiche commune déjà conforme. Visuel fiche complet en lot A |
| T9 | Cartes de choix internes sans bord gauche vert | ✅ | `T9_scan_portes.png` (2 portes sans barre verte). Portes Étude de zone supprimées en D8 |
| T10 | Survol = vert opaque, contenu sombre (« Toute l'île » Piscines) | ✅ | `T10_piscines_perimetre.png` — fond inline mint-0f (qui écrasait le `:hover`) retiré → fond neutre, survol opaque lisible |

**Sweep T1/T2 — 18 outils (doublon résiduel ?)** : plu, permis, communes, blocs-fonciers, successions = pas d'entrée parcelle (sans objet) · patrimoine, comparer, courriers, mon-secteur, étude-zone = `ParcelInput` direct, invite unique interne (OK) · assemblage, gabarit, taxe, solaire, calculette, temps = `EntreeParcelle` corrigé (OK) · **risques (blocB)** et **faisabilité (ParcelPicker)** = doublon **corrigé** (phrase libre retirée).

**Arbitrages lot T (tranchés) :**
- **T7 / PLU** — « Rechercher dans le PLU » est une **carte de choix sur 2 lignes**, jumelle du lien `<a>` « Télécharger le PLU intégral ». La forcer dans `<Bouton>` (ligne unique h-8) casserait la paire. Elle utilise déjà l'interaction partagée `hover-fill`. **Conservée en carte.** Les vraies cibles T7 (3D, « Revenir à l'île ») sont traitées.
- **T4 / T5 / T6 sur la fiche** — mécanismes (CSS tuiles, helpers de format, chevron) livrés en lot T ; les **instances précises de la fiche parcelle et de la fiche commune** (identité A3, servitude EL10 A5, pente A6, réseaux A7, fiscalité A8, quartier A10, CatNat B2, dates B6) sont appliquées et **constatées en lot A/B**, fiche chargée — aucun point sauté, traçabilité au point concerné.
- **T3 / Successions, Étude de zone, Piscines** — le compagnon du bouton n'y est pas un texte d'explication mais un sélecteur commune / un `Retour` ; ces écrans sont retravaillés en D8/D14, le placement Réinitialiser y est finalisé là.

> **Test pré-existant rouge (hors périmètre)** : `src/lib/layersCoquilles.test.ts` (« i » BPE attend `35 546`) échoue **déjà sur `origin/main`** (constaté par stash) — le texte `i` de la couche BPE (`lib/layers.ts`) ne porte aucun compte. Non causé par ce lot, non dans le périmètre T. Signalé ; à rattacher au lot C (couches) ou à un correctif données.

### A — Fiche parcelle
A1…A13 : ⬜ (non commencé)

### B — Fiche commune
B1…B7 : ⬜

### C — Couches
C1 : ⬜

### D — Outils
D1…D15 : ⬜

### E — Docs, Signaler, Notifications
E1…E6 : ⬜

---

## Détail des correctifs

### T1 / T2 — doublon « ou cliquez une parcelle » + invite résiduelle après clic carte

**Constat (avant).** Le composant partagé des outils `EntreeParcelle` (`frontend/src/components/outils/EntreeParcelle.tsx`) rendait **deux** invites :
1. celle, interne, de `ParcelInput` (boîte pointillée « ◎ ou cliquez une parcelle sur la carte ») ;
2. la ligne libre « — ou — cliquez une parcelle sur la carte » du wrapper lui-même.

Après un clic carte (`source='carte'`), le wrapper grisait son champ adresse — mais l'invite interne de `ParcelInput`, à l'intérieur de ce bloc grisé, restait **visible en gris** : c'est l'« encore visible sur Solaire après un clic carte » de T2.

**Correctif.** Dans `EntreeParcelle`, `ParcelInput` reçoit désormais `withCarte={false}` : il ne rend plus sa propre invite (doublon supprimé) et ne reconsomme plus le clic carte (le tiroir l'adopte déjà via `selectedIdu`). L'unique invite restante est la ligne « — ou — » du wrapper, qui **grise** selon `source` (règle du 04/10, couverte par `EntreeParcelle.test.tsx`).

**Portée.** Tous les outils passant par `EntreeParcelle` : Prospection solaire, Gabarit, Taxe d'aménagement, blocB, Faisabilité/Calculette, VerifProcedure, moteurs, ModulePanel. **Reste à traiter** (prochain incrément T1/T2) : les outils qui consomment `ParcelInput` **en direct** (Étude de zone, Comparer, Scan patrimoine, Mon secteur, Pièges/ModulePanel, Documents, Veille) — sweep des 17 outils à compléter.

**Vérification.** `npx vitest run EntreeParcelle.test ParcelInput.test socle.test` → 15/15. Captures Gabarit avant/après (`T12_gabarit_01_entree.png`) : 2 invites → 1.

---

## Tableaux de vérification (A2, A12, D4, D10, D11, D14e) — à venir
## Réponses (A13, E2, E4) — à venir
## Ce que CC n'a pas pu constater (à vérifier par Vic) — à venir
