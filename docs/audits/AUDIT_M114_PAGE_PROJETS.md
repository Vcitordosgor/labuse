# M114 — la page Projets : refonte visuelle

Livré le 18/08/2026, d'après `DA-PROJETS-v1.html` (font foi). Corrige trois problèmes mesurés :
(1) le parcours de création s'empilait au-dessus de la liste ; (2) les cartes étaient
indistinguables ; (3) les chips répétaient le titre et la date occupait la place de l'info utile.
DA : fond noir, mint `#4ADE80` en accent rare (le mint SIGNALE, il ne décore pas), mono pour le
statutaire. Aucun chiffre en dur — tout dérive de `projet_parcelles`.

## Phase 0 — la vignette (arbitrée : RÉELLE) — voir `AUDIT_M114_VIGNETTE.md`

Mesuré : la vignette réelle (schéma SVG des centroïdes, normalisés par le serveur, contour pour
proposée/écartée + aplat mint pour retenue) coûte **~27 ms pour toute la liste**, zéro stockage,
zéro cache (lecture live). Vic a tranché : vignette réelle. Projet sans emprise → **initiale de la
commune** (état vide distinct d'un chargement). Backend : `_vignettes_by_projet` (une requête
batchée) + champ `vignette {commune, points}` sur la fiche de liste. Front : `Vignette.tsx`.

## Phase 1 — le parcours de création (`ParcoursProjet.tsx` refondu)

Occupe l'**écran seul** (la liste ne s'affiche pas dessous ; Échap/× ramènent). **Une question à la
fois** en 24 px + aide. **Barre de progression 5 segments** (mint = faits) + compteur mono
`3 / 5 · PROGRAMME`. **Clavier** : Entrée valide et avance, Échap ferme, Retour revient
(`↵ POUR CONTINUER` en mono). Le **fil des réponses** (coche mint) reste en bas. **Cadre mint** —
seul bloc encadré. Commune du **référentiel** (jamais texte libre). Le préremplissage Copilote
(M113) est conservé (le composant est partagé).

## Phase 2 — la liste (`ProjetsPanel.tsx` refondu)

Deux onglets `Actifs N` / `Archivés N`. Ordre : **travail restant d'abord** (proposée > 0 en tête,
du plus gros reste au plus petit ; les autres par activité) — aucun intertitre. **Une famille de
lignes, deux intensités** : *à trier* (bande mint, vignette 64, barre, compteur mint `N À TRIER`)
vs *à jour* (bande grise, vignette 52, `RIEN À TRIER` en mono discret). Commune en **mono** à côté
du titre. Les **chips disparaissent** → une ligne de contexte (« 20 logements · budget 600 k€ »,
« Cadrage à compléter »). Barre : `13 / 49 RETENUES` ou `AUCUNE RETENUE`. **Toute la ligne
cliquable** ; le menu `⋯` (Renommer/Archiver) reste, en survol. `VOIR LES N AUTRES` au-delà de 4.

## Phase 3 — en-tête + état vide

En-tête `Vos projets` (pas « Mes projets ») + sous-titre. **Un seul bouton plein** mint
(`Nouveau projet`) ; « Décrire au copilote » devient un lien discret. État vide : cadre pointillé,
« Aucun projet pour l'instant », une phrase qui dit à quoi sert un projet, bouton de création.

## Phase 4 — vérification

| Contrôle | Résultat |
|---|---|
| Captures (liste 2 intensités, parcours, archivés, VOIR LES N AUTRES, état vide) | **7 captures** — conformes maquette (`qa/m114/captures/`) |
| Navigation clavier complète du parcours, sans souris | **OK** — atteint `5 / 5 · RÉCAPITULATIF` et crée par Entrée |
| Projet créé → « Voir le projet → » ouvre le kanban | **OK** |
| Préremplissage depuis le Copilote (M113) | **OK** — « 25 logements à Saint-Leu » → commune Saint-Leu |
| Vignette réelle + état vide (initiale commune) | **OK** — à-jour « Logements ×15/×12 » rendent l'initiale S/B |
| Golden | **115/119 PASS, 0 FAIL** (4 INDÉTERMINÉ env) |
| Suite | **1594 passed, 0 failed** (43 env-skips) |
| tsc · build | **0 · OK** |

## Interdits respectés

Liste jamais affichée sous le parcours ouvert · aucun chip qui répète le titre · un seul bouton
plein mint par écran · aucun compteur/seuil en dur (tout dérive de `projet_parcelles`) · non mergé.
