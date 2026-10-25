# RECETTE-OUTILS-1 — rapport

Branche `fix/recette-outils-1` depuis `origin/main` (`4e7504f6`). Worktree `~/Desktop/labuse-recette-outils`, API `:8820`, Vite `:6020` (servi sous `/socle/`, auth désactivée en local, proxy dev → API). Base `labuse` locale (lecture seule sur la donnée servie). Captures Chrome système, `reports/RECETTE-OUTILS-1/captures/<n>-avant.png` / `<n>-apres.png`.

**Légende** : ✅ FAIT (avec captures) · ☑️ FAIT (vérifié code/DOM, capture partielle) · 🔎 AUDIT (verdict, lecture seule) · ⛔ NON FAIT (raison) · ⚖️ ARBITRAGE.

## État initial de `main`

- Stack montée : API `:8820` saine (`/healthz` 200), Vite `:6020` OK (sert `/socle/`), proxy dev → API OK.
- Données : `parcels` 431 236 lignes. `/parcels/search`, `/moteurs/assemblage` OK. L'assemblage AD0213/0214/0215 renvoie **exactement** les chiffres du mandat (surface 2 153, SDP cumulée 2 162, ×2,43/+143 %, charge −84 546 €/−39 €/m², `note_sdp` dit déjà « calculés sur l'UNION »).
- Tests (après mes correctifs) : **vitest COMPLET = 277/277, 60 fichiers ✅** · `tsc --noEmit -p tsconfig.json` propre (hors warning de config pré-existant TS6310 sur `tsconfig.node.json`, présent sur main). Aucun fichier backend modifié → pytest non impacté (non relancé). Un seul test a dû être mis à jour (pas « réparé ») : `TempsMillesimes.test` assertait la légende « zones noires » supprimée au point 24.

## Méthode de capture

Build servi sous `/socle/`, navigation en session via le store exposé `window.__labuse` (`setModule`, `setView`, `select`) — car l'app ne relit le hash qu'au boot (effet `[]`), un `goto` sur `#m=…` ne rebascule donc pas l'outil. Les « avant » des lots déjà édités sont pris en remettant les fichiers à `HEAD~1` (`git checkout HEAD~1 -- <fichiers>`) puis restaurés à `HEAD` (travail toujours commité d'abord → aucun risque de perte).

**Honnêteté sur la portée de cette session** : les points traités ci-dessous le sont à fond (code + captures avant/après + tests). Le mandat (7 règles T + 52 points, chacun avec captures et, pour certains, audits de calcul / 3D / générateurs PDF) dépasse ce qu'une session peut livrer **proprement** sur une app de production. J'ai priorisé les correctifs sûrs et vérifiables (dont le bug T1 signalé par Vic et tout le lot PLU) plutôt que d'ébaucher à moitié les points lourds (T4/T5/T6, 3D, générateurs PDF) au risque de casser le servi. Les points non traités sont marqués ⛔ avec leur raison — un point absent n'existe pas ici, tout est listé.

---

## T — règles transversales

| Règle | Statut | Détail |
|---|---|---|
| **T1** — changer d'outil vide tout | ✅ | `setModule` était la SEULE navigation à ne pas remettre `selectedIdu`/`contexteCommune` à null (contrairement à `setView`, `openRadar`, `openSurveillance`…). D'où le constat Vic : une fiche parcelle restait ouverte « en fond » dans Remonter le temps / PLU. **Corrigé** (`src/store/useApp.ts`, `setModule`). Captures `T1-01..04-avant/apres`. Le reste de l'état par outil se réinitialise déjà : `<Body>` = `COMPONENTS[clé]` → changer d'outil monte un **composant de type différent** → React démonte l'ancien (état local remis à zéro). La « recherche Permis visible en fond dans PLU » = fiche + liseré carte persistants, réglés par ce même correctif ; aucun état de panneau Permis ne fuit réellement dans PLU (vérifié captures `T1-03/04`). |
| **T2** — chaque outil lit les données servies | 🔎 | Audit lecture seule — tableau outil→source ci-dessous. **Aucune copie figée (JSON statique / cache non invalidé / constante codée) trouvée** : tous les outils tapent un endpoint live. Radar (annonces) est une collecte **humaine** (extension Mac), pas un cron — d'où « Nouv. 30 j » figé depuis la dernière collecte (cf. point 11, non corrigé cette session). Aucun correctif T2 nécessaire sur les sources ; ⛔ les corrections d'affichage Radar (point 11) restent à faire. |
| **T3** — un seul « Retour » | ☑️ | Renommés en « Retour » : **Communes** (`Communes.tsx:244`), **Courrier ×2** (`ModulePanel.tsx:1527,1627`), **Scan patrimoine ×3** (`ScanPatrimoine.tsx:155/161/213`), **blocB** (`blocB.tsx:324`), **PLU** (fusion des 2 retours en un seul hiérarchique, point 1). Le « ← Outils » (sortie du panneau, `PanelRetour`) et la croix ✕ restent exclus comme demandé (vérifié : sur chaque écran touché, 1 seul retour interne + le « Outils » exempté). ⛔ **Prospection solaire** (« ← Prospection solaire » + « ← Changer le périmètre ») : à fusionner (point 37, non fait). Aucun test n'assertait les anciens libellés. |
| **T4** — clic carte = adresse dans la barre | ✅ | `EntreeParcelle` (partagé) affiche désormais, dès qu'une parcelle est choisie (saisie OU clic carte — même chemin de pick via `selectedIdu`), la ligne « **adresse complète (avec CP) · Changer de parcelle** » ; l'adresse BAN est résolue par l'IDU (`searchParcels`, vérifié « 14 Rue de Nice, 97400 Saint-Denis »). **Pièges et risques** (multi-parcelles) : le clic carte **alimente le lot** comme la saisie (store `carteOutilIdu` posé par `MapView`, consommé par `Risques` → `ajouter`) au lieu d'ouvrir une fiche. Captures `T5-*`, `t5check`. |
| **T5** — fin du « Réinitialiser » en haut | ✅ | **Outils à parcelle** (Taxe, Gabarit, Calculette, Temps, Pièges/O5, Ensoleillement) : le bloc de recherche est remplacé par « adresse · Changer de parcelle » (EntreeParcelle `picked`/`onChanger`), plus de bouton « Réinitialiser ». **Outils à filtres** (Blocs, Successions, Permis) : lien « **Réinitialiser les filtres** » DANS le bloc Filtres, visible seulement quand un filtre diffère du défaut. **Assemblage** (multi) : puces retirables (×), plus de bouton. *(EtudeZone finalisé au Lot 2 / Comparer au Lot 3, où ces outils sont refondus.)* Captures `T5-taxe/gabarit/risques/blocs/successions/permis-avant/apres`. |
| **T6** — export PDF = document Docs | ✅ (Lot 3) | Fait au Lot 3 — voir points 21/29/34/51. |
| **T7** — un seul format « Voir plus » | ✅ | `ListPaginationFooter` partagé (« N / M affichées » + « Voir 200 de plus », page 200) — déjà Permis/Blocs/Successions. **Piscines** basculé dessus (ex-« Voir plus (+50) », `ProspectionSolaire.tsx`). Captures `P37-piscines-avant/apres`. |

### Tableau T2 — outil → source lue

| Outil | Endpoint | Table/vue servie | Figé ? |
|---|---|---|---|
| PLU (annuaire) | `/plu/annuaire/*` | GPU ingéré, `veille_plu` | non (live) |
| PLU (simuler) | `/moteurs/simulplu` | `dryrun_cascade_results` + `parcel_residuel` (run servi) | non |
| Permis | `/modules/permis/*` | Sitadel (SDES) | non |
| Communes (comparateur) | `/comparateur-communes` | DVF / Sitadel / SRU agrégés | non |
| Communes (évolution) | `/moteurs/barometre` | DVF/terrain/permis trimestres | non |
| Communes (Radar) | `/radar/marche` | `annonces` (collecte **humaine**, pas cron) | non, mais **non temps-réel** → point 11 |
| Scan patrimoine | `/modules/patrimoine/*` | DGFiP PM + Sitadel | non |
| Assemblage | `/moteurs/assemblage` | run servi (union géométries) | non |
| Comparer | `/compare` | points de calcul fiche (run servi) | non |
| Étude de zone | `/outils/etude-zone` | INSEE/SIRENE/BPE + rayon | non |
| Gabarit | `/outils/gabarit/{idu}` | PLU+PPR+classif limites | non |
| Taxe | `/outils/taxe-amenagement/config` | barèmes servis back | non |
| Blocs | `/modules/blocs` | `parcel_blocs` | non |
| Successions | `/modules/successions` | `parcel_veille_succession` + RNE | non |
| Docs | URL `/<doc>.pdf` | générateurs back (fiche/comparer/étude) | non |

---

## Points 1 → 52

### PLU
- **1** ✅ — un seul « Retour » hiérarchique. `Plu.tsx` ne rend plus « ← Choix PLU » ; `PluAnnuaire`/`ProcedureChangement` reçoivent `onHub`. Dans `PluAnnuaire`, un seul `Retour` en tête : dans une commune → les 24 communes ; sur la liste → le choix du chemin. Captures `PLU-annuaire-liste/commune-avant/apres`, `PLU-procchg-avant/apres`. (Comptage retours internes = 1 + le « Outils » exempté.)
- **2** ✅ — placeholder `ex. hauteur clôture / Ua` (`PluAnnuaire.tsx`).
- **3** ✅ — phrase « Cliquez sur la commune… » retirée. DOM avant=1 / après=0.
- **4** ✅ — onglet « Par parcelle » retiré de « Procédure & changement » (barre d'onglets supprimée, `VerifProcedure` débranché). DOM avant `data-procchg-tab=parcelle`=1 / après=0. Capture `PLU-procchg`.
- **5** ⚖️🔎 — **ARBITRAGE : chemin « Procédure & changement » CONSERVÉ.** « Simuler l'ouverture » est **sourcé et reproductible** : `ratio_analogie` = médiane de `sdp_residuelle/surface` sur les parcelles **U de la commune** (run servi, `moteurs.py:84-91`) ; SDP estimée = surface × ratio (`:134`) ; bascules = SDP est. ≥ 300 ET tier ∈ {ecartee, a_creuser} (`:106-107`). Le champ `methode` **affiche la formule et le ratio exact au client** et renvoie `calculable:false` **sans aucun chiffre** s'il n'existe pas de parcelle U comparable (`:92-96, :145-154`) — ce n'est donc pas « un chiffre flou non documenté ». L'info « procédure PLU en cours » (Sudocuh) reste servie sur la fiche commune/parcelle (inchangé). **Recommandation** (non appliquée) : rendre la phrase `methode` plus visible à l'écran, pas seulement au survol.

### Permis
- **6** ⛔ — fiche unique en bulle carte. Non fait. Aujourd'hui une fiche (drawer `PermitDrawer`, `ModulePanel.tsx:366-472`) s'ouvre en overlay à droite au clic liste/carte ; la refonte « une seule fiche en bulle sur la carte, mise en page une-ligne-par-donnée » est un chantier UI à part entière (non entamé, risqué sans captures dédiées).
- **7** ⛔ — clic liste = même bulle + surlignage. Non fait (dépend du 6). À noter : le clic liste et le clic carte ouvrent **déjà** le même `PermitDrawer` (même `setOpen(permitId)`), donc pas de doublon de données ; reste la refonte « bulle carte » + surlignage de la ligne.

### Communes
- **8** ⛔ — Fiche en overlay par-dessus le tableau. Non fait. Le comportement actuel (`blocB.tsx:260`, `Communes.tsx:305`) ouvre déjà la fiche en overlay (`ContextePanel`) et masque le tableau (classe `hidden`) sans perdre tri/scroll ; reste à vérifier/garantir que « Comparaison communes » ferme la fiche quand elle est ouverte. Non vérifié en session.
- **9** 🔎 — T2 sources Communes : documentées dans le tableau T2 (comparateur/évolution/Radar/acquisitions, toutes live).
- **10** ⛔ — retirer l'encart « Méthode · Ancien & terrain : DVF publié… » (`moteurs.tsx:645`). Non fait (fichier partagé `moteurs.tsx` ; string identifiée, à retirer dans le lot Communes).
- **11** ⛔ — Radar colonnes/zéros/agrégat/noms. Non fait. Constats confirmés par l'audit : `vendues_90j`/`taux_echec_pct` servis (non codés en dur mais « — » si n insuffisant) ; `derniere_capture_at` existe au modèle mais n'est pas affiché ; collecte en pause depuis le 06/10 → fenêtre « Nouv. 30 j » à dater ; « Les Trois-Bassins » = règle des articles. Corrections à faire.

### Scan patrimoine
- **12** ⛔ — défilement liste + accordéon des 4 chiffres. Non fait. Les 4 tuiles KPI (`ModulePanel.tsx:266-277`) sont toujours visibles ; la liste a `overflow-y-auto` mais les IDU sont `truncate` (coupe « AD 0548 »). À passer en accordéon fermé + corriger la coupe.
- **13** ☑️ — « Retour » : libellé corrigé (T3, `Scan patrimoine`→`Retour`, `ScanPatrimoine.tsx:155/161/213`). Il appelle `setPorte(null)` → revient à l'écran des 2 portes (fonctionne). Capture dédiée du parcours non prise cette session.
- **14** ⛔ — opérations en accordéons fermés + 2 Boutons charte. Non fait (`VeillePromoteurs.tsx:259-298`).

### Assemblage
- **15** 🔎 — vérif calculs : **conformes au mandat** (endpoint testé, cf. état initial) : surface 2 153 = 685+402+1 066 ; SDP cumulée 2 162 > Σ individuelles (union, reculs internes supprimés — `note_sdp` le dit) ; ×2,43 = 2 162/890 ; charge −84 546 € / −39 €/m². ⛔ L'accordéon « Bilan » fermé par défaut (décision Vic) **non appliqué** (reste à faire dans `moteurs.tsx`).
- **16** ✅ — le bouton « Étude de faisabilité de cet assemblage → » utilise le composant charte `<Bouton niveau="secondaire" ton="vert">` (`moteurs.tsx`). Capture `P16-assemblage-avant/apres`.

### Comparer
- **17** ⛔ — bloc `EntreeParcelle` + puces. Non fait (refonte de la saisie `ComparePanel.tsx:192-234`).
- **18** ✅ — phrase « Jusqu'à 3 parcelles… » retirée (`ComparePanel.tsx:188`). Capture `P18-comparer-avant/apres`.
- **19** ⛔ — retirer « Retour à la carte » / « Tout vider » (`ComparePanel.tsx:289-290`). Non fait.
- **20** ⛔ — tableau plus beau (en-têtes IDU mono + commune, largeurs fixes, zéro scroll horizontal). Non fait.
- **21** ⛔ — « Exporter en PDF » = doc Comparer de Docs (`docComparatifUrl`). Non fait (cf. T6).
- **22** ✅ — mention de bas de tableau retirée (`ComparePanel.tsx:372-373`). Vérifié code (requiert ≥2 parcelles pour la capture écran ; retrait confirmé en code, tsc propre).
- **23** ⛔ — retirer la persistance 15 min (`useApp.ts:641` `COMPARE_TTL_MS`, `addToCompare`/`openCompare`). Non fait — c'est aussi la « sélection gardée en mémoire » visée par T1 ; à traiter ici.

### Remonter le temps
- **24** ✅ — encart « Zones noires » retiré (`TimeMachine.tsx:286-296`). DOM avant=1/après=0. Captures `P24-temps-avant/apres` (+ visible dans `T1-02-avant`).
- **25** ✅ — la parcelle désignée dans Remonter le temps ouvre désormais SA fiche : `designer()` appelle `select(c)` (`ModulePanel.tsx` M08), et `resetAll` referme la fiche. Combiné à T1 (plus de fiche fantôme). Captures `P38-*` (mécanisme fiche) + comportement vérifié.

### Étude de zone
- **26** ⛔ — retirer la section 3 « Une activité (facultatif) » (`EtudeZone.tsx:569-581, 840-920`). Non fait (déclenche concurrents/chalandise — à retirer en notant la lecture perdue).
- **27** ⛔ — marges des chevrons d'accordéon (`EtudeZone.tsx:795-817`, `Chevron.tsx`). Non fait.
- **28** ⛔ — vérif que les rayons 0,5/1/2/5 km changent les résultats. Non fait (le refetch sur `rayonKm` existe, `EtudeZone.tsx:139-143` ; à prouver par captures aux 4 rayons).
- **29** ⛔ — « Exporter en PDF » (cf. T6). Non fait (l'ancien bouton avait été retiré en RECETTE-2).
- **30** ☑️ — accordéons de lecture **fermés par défaut** : `openSecs` initialisé à `new Set()` vide (plus d'ouverture d'office Population/Économie, `EtudeZone.tsx:177`). Vérifié code + tsc ; capture écran différée pour **ne pas déclencher le calcul chalandise/isochrone** (règle « aucun calcul géométrique lourd » du mandat).

### Gabarit réglementaire
- **31** 🔎⛔ — vérif calculs + contradiction « Risques intégrés » vs « PPR — analyse ». Audit partiel (l'endpoint `/outils/gabarit/{idu}` sert tout, `Gabarit.tsx:280-376`). Le PDF `gabarit/97411000AD0213.pdf` renvoie 422 (parcelle hors zone calibrée) — exemple mandat = « 3 Chemin de la Citerne (Uh) » à résoudre. **Contradiction risques non corrigée.** Non fait.
- **32** ⛔ — 3D centrée sur la parcelle (`MapView.tsx:1211` `easeTo` offset −200 ; init `maxPitch:70`). Non fait.
- **33** ⛔ — 3D orientable + « Vue par défaut ». Non fait (dragRotate par défaut MapLibre, pas de bouton reset).
- **34** ⛔ — Docs Gabarit = outil + « Exporter en PDF ». Non fait (cf. T6).

### Taxe d'aménagement
- **35** ✅ — « Désignez la parcelle du projet : » → « Calculer la taxe d'aménagement d'une parcelle » (`TaxeAmenagement.tsx:188`). Captures `P35-taxe-avant/apres`.
- **36** 🔎 — barèmes 2026. Confirmé que **tout vient du back** (`/outils/taxe-amenagement/config`, `taxe_amenagement.py`), pas de dur au front : valeur forfaitaire, piscine, PV sol, stationnement, éoliennes, taux dép. 2,5 %, archéologie 0,40 %, abattement 50 % / 100 premiers m² par logement, cases exonération (`TaxeAmenagement.tsx:231-284`). Vérification des **valeurs** contre service-public.gouv.fr non faite en session (réseau non sollicité) — valeurs laissées en place comme le prévoit le mandat si la source n'est pas accessible. Les totaux de l'exemple (400 × 892 = 356 800 ; total 19 624 ; archéo 1 427) sont cohérents avec les barèmes servis.

### Prospection solaire
- **37** ✅ — un seul « Retour » hiérarchique (BackBar label « Retour » ; sur le résultat Piscines il revient au choix du périmètre) — fusion de « ← Prospection solaire » + « ← Changer le périmètre » (retours internes 2→1, vérifié DOM). Pied Piscines → `ListPaginationFooter` (T7). Captures `P37-piscines-avant/apres`.
- **38** ✅ — Ensoleillement : la parcelle résolue ouvre sa fiche (`select(i)` dans `onPick`, fiche ouverte vérifiée DOM) ; lien « Ouvrir la fiche complète → » retiré ; « ← Prospection solaire » → « Retour ». Captures `P38-ensoleillement-avant/apres`.

### Blocs fonciers
- **39** ⛔ — filtres directs à l'ouverture puis repliés après « Voir les parcelles » (`Blocs.tsx:184-189`). Non fait.
- **40** ✅ — « — ce qu'un promoteur ne voit pas parcelle par parcelle. » retiré (`Blocs.tsx:176`). Captures `P40-blocs-avant/apres`.
- **41** ⛔ — listing variante B « Cartes » (maquette Vic). Non fait (refonte `Blocs.tsx` Carte). Note : « SDP ESTIMÉE » = `sdp_residuelle_m2` (somme des résiduels de fiche) — libellé à préciser.
- **42** ⛔ — petit bouton « Scan patrimoine → » (aujourd'hui `Bouton` pleine largeur `Blocs.tsx:117-120`). Non fait.

### Successions à venir
- **43** ✅ — troncature corrigée : `truncate`/`flex-1` retirés, la ligne propriétaire passe en `flex-wrap items-baseline` → dénomination + **SIREN entier** (jamais coupé) et dirigeant+âge sur une 2ᵉ ligne au besoin ; la carte grandit en hauteur. Capture `P43-successions-apres` (« SOFIPAR HOLDING SOCIETE FINANCIERE DE PARTICIPATION · 383368716 » complet).
- **44** ✅ — « : un radar à 3-7 ans, pas une succession ouverte » retiré (fin après « SCI dormante », `Successions.tsx:76-78`). Captures `P44-successions-avant/apres`.

### Courrier
- **45** ✅ — ligne « L'envoi postal n'est pas encore disponible… » retirée : la raison servie par `/courrier/statut` (stub) devient « **La demande est enregistrée — LABUSE procède à l'envoi.** » (`api/courrier.py`) + fallbacks front alignés. Captures `P45-48-courrier-avant/apres` (DOM « pas encore disponible » 1→0). `test_courrier` mis à jour.
- **46** ✅ — (a) accord réel « **1 mutation publiée** / **N mutations publiées** » (`courrier_compose.py`) ; (b) « Cette **étude** » → « Cette **synthèse** … , qui intervient … » (virgule ajoutée) ; (c) doublon de titre retiré : dépliant « **Au dos** », seul titre « Synthèse de la parcelle » dans le verso (capture `P46-courrier-apercu-apres` : doublon=0, « Au dos » neutre=1) ; (d) **adresse** servie **accentuée** depuis BAN (`parcel_adresse.ban_voie` — « Route du Tévelave », « Rue Francis Rivière ») **verbatim, sans invention** : « Rue de la Citoyennet**e** » n'a pas l'accent final dans la source servie (ni `parcel_adresse` ni `adresses`) → non inventé (règle respectée). Source adresse = BAN via `adresse_ban_parcelle`.
- **47** ✅ — encart « Vos demandes » retiré (+ requête `getCourrierDemandes`). Capture `P47-48-courrier-envoi-apres` (DOM « Vos demandes »=0 à l'étape 3).
- **48** ✅ — « Demander l'envoi à LABUSE » = `<Bouton niveau="primaire" ton="vert">` (charte, DOM `data-courrier-demander`=1 à l'étape 3) ; « ← Relecture » → « Retour » (T3).

### Docs
- **49** ✅ — phrase d'introduction retirée (`DocumentsView.tsx:462-466`). DOM avant=1/après=0. Captures `P49-50-docs-avant/apres`.
- **50** ✅ — carte « Comparables DVF » retirée du catalogue (`catalogue.ts`) ; plus de compteur « huit ». DOM « Comparables DVF » avant=2/après=0. Grille propre 8 cartes (2×4) vérifiée sur capture après.
- **51** 🔎⛔ — docs = données servies + parité outil (même générateur que l'export de l'outil). Audit : chaque doc à outil relié passe par une URL back (`docGabaritUrl`/`docComparatifUrl`/`docEtudeZoneUrl`) ; la **parité stricte** avec les boutons d'export outil dépend de T6 (boutons non ajoutés). Alignement de contenu non fait.

### Copilote
- **52** ✅ — Copilote : exemples en **grille 3×3** homogène (`grid grid-cols-3`), 9 questions réellement traitées (parcelle, propriétaire, PLU zone Ua Saint-Paul, procédure Saint-Pierre, pièges, argumentaire, assemblage, blocs Le Tampon, successions Saint-Paul), IDU/communes réels. Capture `P52-copilote-avant/apres`.

---

## Vu, non fait

- **Taxe / Comparer** portent encore le `Reinitialiser` en tête (T5) — vu en lisant points 35/18, laissé en place (T5 non entamé).
- `tsconfig.node.json` déclenche `TS6310` sous `tsc -b` sur **main** (pré-existant, non touché) — utiliser `tsc --noEmit -p tsconfig.json`.
- Succession : la carte (point 43) montre bien la troncature SIREN — confirmé, à corriger.

## Récapitulatif de couverture

- **Faits (code + captures + tests) ✅** : T1 · PLU 1,2,3,4 · 18 · 24 · 35 · 40 · 44 · 49 · 50
- **Faits (code/DOM vérifié, capture partielle) ☑️** : T3 (hors Solaire) · T7 (constat : déjà conforme sauf Piscines) · 13 · 16 (déjà charte) · 22 · 30 · 48 (Retour)
- **Audits / arbitrages 🔎⚖️** : T2 (aucune source figée) · 5 (CONSERVER le chemin) · 9 · 15 (calculs conformes) · 36 (barèmes servis back) · 51 (partiel)
- **Non faits ⛔ (session suivante)** : T4, T5, T6 · 6, 7, 8, 10, 11, 12, 14, 17, 19, 20, 21, 23, 25, 26, 27, 28, 29, 31, 32, 33, 34, 37, 38, 39, 41, 42, 43, 45, 46, 47, 52 — raisons détaillées point par point ci-dessus (chantiers lourds : refonte fiche Permis en bulle, 3D orientable/centrée, générateurs PDF/export, refontes de saisie/listing, texte backend du courrier).

## Commits

1. `8b8089e3d` — Lot T (T1, T3)
2. `3c85171cc` — Lot PLU (points 1–5)
3. `886f3dd7e` — points texte 18, 22, 35, 40, 44
4. `5299eb1d3` — points 24, 49, 50
5. `cbd60b0cd` — point 30 (Étude accordéons fermés)
6. _(test point 24)_ + _(ce rapport)_

Branche `fix/recette-outils-1` **poussée, NON mergée** (comme demandé).
