# LOT C — la même action, le même comportement

Comparaison des familles d'actions répétées (destination · contexte · libellé · icône · retour).

## Famille « Scan patrimoine » (→ `setM02Prefill(siren)` + `setModule('patrimoine')`)

| Origine | Retour (`pushOutilRetour`) | fichier:ligne |
|---|---|---|
| Blocs fonciers | **OUI** `{module:'blocs-fonciers'}` | outils/Blocs.tsx:118 |
| Permis (ModulePanel) | **OUI** `{module:'permis', restore}` | outils/ModulePanel.tsx:433 |
| Remonter le temps (HistoireFrise) | **OUI** `RETOUR` | outils/HistoireFrise.tsx:129 |
| **Communes** | **NON** | outils/Communes.tsx:56-60 |
| Fiche §Identité | n/a (la fiche reste via `selectedIdu`) | fiche/Fiche.tsx:1497 |
| Omnibox / fiche commune / popup carte | n/a (pas d'outil d'origine) | Header.tsx:87 · ContextePanel.tsx:167 · MapView.tsx:853 |

→ **ÉCART N-4 🟡** : destination/contexte/libellé identiques, mais le **comportement de retour diverge** — depuis **Communes**, « Scan patrimoine » ne pose PAS le fil de retour que Blocs/Permis/Temps posent (le commentaire `Communes.tsx:55` dit pourtant « même idiome »). L'utilisateur arrive dans Scan sans « ← Communes ».

## Famille « ouvrir la fiche » — deux mécaniques

- `focusParcelle(idu,{fiche:true})` (store:772) = **vue cartes + zoom/contour + fiche** — utilisé par les outils-listes à carte visible : Communes:54, Successions:113, Prospection:215, Veille foncier:145, Pièges, Calculette, Taxe.
- `select(idu)` (store:764) = **fiche seule**, sans changer de vue ni recentrer la carte — utilisé par CRM Kanban:121/251, Projets kanban:455, Copilote (App IaRestitution), listing panneau, Tinder:113. (CRM/Projets ajoutent `setView('cartes')` à part.)

→ **Observation C-obs1 (🟡, peut-être intentionnel)** : la MÊME action « ouvrir la fiche d'une parcelle » **recentre la carte** depuis un outil-liste mais **pas** depuis CRM/Projets/Copilote (le contour reste surligné via `selectedIdu`, mais la carte ne vole pas vers la parcelle → parcelle potentiellement hors écran). À trancher par Vic (unifier sur `focusParcelle` ou assumer la différence). Non classé en écart dur : les deux ouvrent la BONNE fiche (destination correcte).

## Famille « Courrier » (→ `setModule('courriers')`)

- « Courrier SPF » (Fiche §Identité, `setCourrierPrefill`), « Courrier » (Fiche pied), « Nouveau courrier → » (Projets:238, ProjetKanban:480 `setCourrierPrefillIdus`).
- **Destination unique cohérente** (`module:'courriers'`). Libellés distincts **par intention** (SPF = lettre au SPF pour identifier le propriétaire ; « Courrier » / « Nouveau courrier » = courrier propriétaire). ⇒ **cohérent**, pas d'écart (nuance de libellé justifiée).

## Famille « Fiche commune » (→ `setContexteCommune(commune)`)

- Header « voir la fiche → » (:306), Header « Fiche commune » (:327, via `focusCommune` = zoom + contexte), Fiche §Autour (autour.tsx:87 `setCommune`+`setContexteCommune`). **Même destination** (volet contexte commune). Cohérent (le `focusCommune` ajoute le zoom, superset acceptable).

## Verdict Lot C
1 écart dur (**N-4 🟡** retour incohérent depuis Communes → Scan) + 1 observation à trancher (**C-obs1** recentrage carte `select` vs `focusParcelle`). Les familles Courrier et Fiche commune sont cohérentes en destination.
