# RAPPORT M55-N — Fiche : diagnostics et finitions (9 points)

Branche `feat/m55-n` (base = main après merge de `feat/m55-m` `4cb964c7` ET `feat/m55-l`
`739a0786`). **NON mergée** — Vic valide et merge. Points 1, 2, 6 = diagnostics
(cause avant correctif). Commits atomiques.

- Précondition vérifiée : `feat/m55-m` ET `feat/m55-l` mergés sur main.
- `tsc -b` 0 · `vitest` 32/32 · `npm run build` vert · console : **0 erreur nouvelle**
  (testé sur 3 familles : brûlante, `declasse_*`, `ecartee`).
- Captures : `reports/m55-n/captures/`. Parcelles de test : `97408000AP1647` (brûlante),
  `97409000AR1260` (declasse_bati_sature), `97411000HM0273` (ecartee), `97415000CT1389`
  (fiche riche, Saint-Paul).

---

## Point 1 — DIAGNOSTIC « Motifs momentanément indisponibles » — `a254a88d`

**Constat.** Tiroir « Pourquoi pas ? » d'une écartée → « Motifs momentanément
indisponibles » + Réessayer.

**Diagnostic.** Le tiroir appelle `GET /anti-fiche/{idu}` (getAntiFiche). **CAUSE =
`/anti-fiche` absent de `vite apiPaths`** → 404 en DEV → `q.isError` → le message. Ce
n'est **PAS une donnée absente** : l'endpoint répond **200** à :8000 avec des motifs
RÉELS, vérifié sur les deux familles demandées + un témoin :

| Parcelle | Famille | Réponse /anti-fiche |
|---|---|---|
| 97409000AR1260 | declasse_bati_sature | 200 · 0 rédhibitoire, 2 vigilance |
| 97411000HM0273 | ecartee | 200 · 1 rédhibitoire, 4 vigilance |
| 97408000AP1647 | brûlante (témoin) | 200 · 0 motif → état vide honnête « Aucun motif… » déjà géré |

Donc **panne technique (proxy)**, pas absence. Le cas donnée-absente est DÉJÀ traité
honnêtement par le composant (« Aucun motif d'écartement… », pas « indisponible »).

**Correctif** (dev-only, prod inchangée) : ajout `/anti-fiche` à `vite apiPaths`. Vérifié
E2E : motifs affichés sur les 3 familles, **0 erreur 404**.

**Conséquence TRAIN 8 (prod) — RASSURANTE.** Le `deploy/Caddyfile.prod` utilise un
**catch-all** `reverse_proxy 127.0.0.1:8000` pour tout sauf le statique (`/`, `/assets/*`,
`index.html`). Donc `/anti-fiche`, `/traducteur-plu`, `/courrier`, `/dossier-banquier` et
tous les autres préfixes API sont **DÉJÀ routés vers FastAPI en prod**. Le gap 404 est
**strictement dev** (la liste explicite `apiPaths` de vite). **Aucune action prod requise.**
Liste des routes en fetch relatif hors `/parcels` (toutes couvertes par le catch-all prod,
toutes désormais dans le proxy dev) : `/anti-fiche`, `/traducteur-plu`, `/courrier`,
`/dossier-banquier`, plus les préfixes historiques (`/moi`, `/events`, `/adresses`, …).

---

## Point 2 — DIAGNOSTIC indicateur « Qualité » figé à 50 — *constat seul, pas de commit*

**Constat.** « Qualité » (ScoreBar `f.q_score`) affiche 50 (mi-barre) sur les parcelles
observées.

**Mesure (run servi `q_v8_calibre`, 431 663 parcelles).**

| Métrique | Valeur |
|---|---|
| min / max | 1 / 100 |
| moyenne | 47,6 |
| valeurs distinctes | 100 |
| **% à exactement 50** | **82,5 %** (355 936 parcelles) |

**Diagnostic — « variable et juste ».** `q_score` n'est PAS constant ni figé : c'est un
calcul réel (`scoring/dryrun.py`) `q = clamp(1..100, base(50) + Σ poids cascade non-A)`.
**50 = la BASE NEUTRE** (aucun poids Q : PLU/risques/terrain neutres) — 82,5 % des parcelles
sont neutres, ce qui est plausible. L'affichage est **fidèle** (vérifié : la parcelle
97410000AV0703 à q=100 affiche bien **100**, pas 50 figé). Le libellé/tip DIT vrai :
`SCORE_TIP.q` = « Q — Qualité intrinsèque (règles PLU, risques, terrain) » — cohérent avec
le calcul.

**Doublon ?** NON. « Qualité » (q_score, base±poids) ≠ « Confiance données » (ICD, complétude
des couches, tiroir « Les données ») — deux indicateurs distincts, deux libellés distincts.

**Conclusion (Vic décide).** Selon l'arbre du mandat : variable et juste → **ne rien
retirer, rapporter**. Nuance signalée : `q_score`/`a_score` sont des dimensions de la
**matrice LEGACY** (M37, morte per M53) — elles n'entrent PAS dans le verdict/tier/×N servi
(modèle P, score_v2). 82,5 % à la base neutre 50 = peu discriminant. Vic peut vouloir retirer
ces ScoreBars Q/A comme legacy — non fait ici (l'indicateur n'est ni cassé ni figé).

---

## Point 3 — Retirer le logo de l'accueil — `8ac3f2f3`
Logo (l'oiseau, SVG) retiré de l'accueil (AccueilPreuves) ; le `mt-7` du bouton
« Commencer » (qui l'espaçait) retiré avec. `my-auto` **conservé** (il centre le contenu,
ne compense plus le logo coupé de M55-I) — jamais de `justify-center`. **Autres emplacements
du logo NON touchés, signalés** (grep) : `Header.tsx`, `States.tsx` (états de chargement),
`deploy/Caddyfile.prod` (page maintenance). **Fichier** : `panel/LeftPanel.tsx`.

## Point 4 — Bouton « Demander l'analyse » affiné — `e9326d0d`
Étoile retirée. Largeur ajustée au contenu (`alignSelf:flex-start` + `maxWidth:100%`, plus
de `width:100%`) → le bouton n'occupe plus toute la largeur (marge à droite). Libellé
« Demander à LABUSE d'analyser la parcelle » (source unique `CLIENT.fiche.demanderAnalyse`) ;
sous-titre conservé. Comportement (M55-L P5) inchangé. **Fichiers** : `fiche/Fiche.tsx`,
`lib/strings.ts`. Capture `p4_bouton_verdict_affine`.

## Point 5 — Tiroir « Les données » : libellé honnête — `fb2a1a7b`
En-tête « N sources » → « N sources utilisées sur cette fiche » (dit ce qu'il compte, cf.
audit M55-L P13). Source unique `CLIENT.fiche.sourcesUtilisees(n)`, chiffre servi
(`f.data_sources.length`). Vérifié : « 28 sources utilisées sur cette fiche ». Dette « 52
vs 62 » accueil + dette millésime (54/62) **non traitées** (registre, signalées). **Fichiers** :
`fiche/Fiche.tsx`, `lib/strings.ts`.

## Point 6 — DIAGNOSTIC barre grise du tiroir « Règles » — `2d4368cf`
**Diagnostic.** La barre = `MicroJauge` ; son remplissage = `potentiel_transformation.
pct_consomme` (part de SDP max déjà bâtie — donnée RÉELLE, 49 % sur la parcelle de réf), mais
le label n'affichait que « zone Ub » → rien ne disait la mesure ni l'échelle. **Information
réelle, mal libellée** (pas décorative). **Correctif** : label → « 49 % SDP consommée »
(mesure + échelle 0-100 %) + **infobulle** (sens : reste = potentiel résiduel ~N m² ; source :
potentiel de transformation ; étiquette Estimé). `MicroJauge` gagne un prop `tip`. Libellés
depuis strings. Repli inchangé (zone/article) si pct absent. **Note (hors périmètre)** : la
même MicroJauge sert le tiroir Renouvellement (fill = renouv_score, label = rang) — ambiguïté
voisine, non touchée. **Fichiers** : `fiche/Fiche.tsx`, `lib/strings.ts`. Capture
`p6_p8_regles_jauge_hauteur`.

## Point 7 — Accueil : pleine hauteur, sections rétractées — `25c385a9`
Corrige le clip mesuré M55-L P1. À l'état ACCUEIL (`!accueilVu && !verdict`), les DEUX
sections (Couches ET Filtres) sont rétractées → l'accueil prend la pleine hauteur. Même
esprit que le `listing` de M55-M. `panneauSection` (champ unique) reste 'couches' par défaut
en coulisse ; l'accueil est un CONTEXTE d'entrée `enAccueil` (dérivé de `accueilVu`) qui
prime : `couchesOpen/filtresOpen = !enAccueil && …`. Le quitter (Commencer / rouvrir une
section) lève l'override. Jamais de `justify-center`.

**RE-MESURE aux 5 tailles du rapport M55-L — ZÉRO CLIP :**

| Taille | dispo | contenu | clip |
|---|---|---|---|
| 1440×900 | 687 | 234 | 0 |
| 1200×800 | 587 | 234 | 0 |
| 1024×700 | 487 | 291 | 0 |
| 900×700 | 487 | 291 | 0 |
| 768×800 | 587 | 291 | 0 |

Transitions vérifiées E2E : accueil (2 fermées) → clic Couches (ouvre, exclusivité, accueil
quitté) ; Commencer → Filtres ; verdict → listing (M55-M) intact. **Fichier** :
`panel/LeftPanel.tsx`. Capture `accueil_pleine_hauteur_1024x700`.

## Point 8 — SDP résiduelle : retirer le doublon d'en-tête — `41ff01ac`
Constat M55-L P14 : SDP (~101 m²) dans DEUX en-têtes voisins (Règles ET Faisabilité).
Décision Vic : la SDP reste en **Faisabilité** (le bilan) ; l'en-tête **Règles** affiche une
CONTRAINTE de gabarit (`fo.hauteur_m`), ou rien si non calculée (le micro-jauge porte déjà
zone + article — jamais la SDP ni un doublon de zonage). SDP retirée reste accessible (corps
du tiroir + en-tête Faisabilité). Vérifié : **Règles « 9 m max », Faisabilité « 1–3 logts »**
— deux valeurs distinctes, doublon résolu. **Fichier** : `fiche/Fiche.tsx`.

## Point 9 — Retirer l'AvisIA du traducteur de zone — `6dcbcfff`
Constat M55-L P13.d : `<AvisIA/>` (« L'IA ne juge pas le sentiment d'une communauté… »)
posé sur le traducteur, HORS SUJET (traduire des règles PLU = lecture factuelle). Décision
Vic : retiré du traducteur UNIQUEMENT. **Grep après retrait** — AvisIA CONSERVÉ sur les
surfaces IA génératives : Synthèse/explication IA fiche (`Fiche.tsx:878`), « Une question ? »
(`AskBar.tsx`), recherche IA (`IAStub.tsx`), entretien projet (`ProjetEntretien.tsx`),
Copilote (`CopiloteView.tsx`), restitution IA (`App.tsx`). Vérifié E2E : traducteur sans
AvisIA. **Fichier** : `fiche/Fiche.tsx`. Capture `p9_traducteur_sans_avisia`.

---

## Validation

| Contrôle | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest run` | 32/32 |
| `npm run build` | vert |
| Console (3 familles brûlante/declasse/ecartee) | 0 erreur nouvelle |
| Point 1 : Pourquoi pas ? sur 3 familles | motifs OK, 0 « indisponible », 0 404 |
| Point 7 : re-mesure 5 tailles | zéro clip |
| Non-régression : accordéon exclusif (M55-L P10), verdict à la demande (P5), listing (M55-M P1), transitions accueil | OK |

**Ne pas merger.** Décisions en attente de Vic : point 2 (utilité des ScoreBars Q/A legacy),
point 6 (jauge Renouvellement, ambiguïté voisine), dettes registre (52 vs 62, millésime 54/62).
