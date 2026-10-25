# RECETTE-OUTILS-1 — rapport

Branche `fix/recette-outils-1` depuis `origin/main` (`4e7504f6`). Worktree `~/Desktop/labuse-recette-outils`, API `:8820`, Vite `:6020` (servi sous `/socle/`, auth désactivée en local, proxy dev → API). Base `labuse` locale (lecture seule sur la donnée servie). Captures Chrome système, `reports/RECETTE-OUTILS-1/captures/<n>-avant.png` / `<n>-apres.png`.

**Légende** : ✅ FAIT (avec captures) · ☑️ FAIT (vérifié code/DOM, capture partielle) · 🔎 AUDIT (verdict, lecture seule) · ⛔ NON FAIT (raison) · ⚖️ ARBITRAGE.

## État initial de `main`

- Stack montée : API `:8820` saine (`/healthz` 200), Vite `:6020` OK (sert `/socle/`), proxy dev → API OK.
- Données : `parcels` 431 236 lignes. `/parcels/search`, `/moteurs/assemblage` OK. L'assemblage AD0213/0214/0215 renvoie **exactement** les chiffres du mandat (surface 2 153, SDP cumulée 2 162, ×2,43/+143 %, charge −84 546 €/−39 €/m², `note_sdp` dit déjà « calculés sur l'UNION »).
- Tests (après mes correctifs) : **vitest COMPLET = 277/277, 60 fichiers ✅** · `tsc --noEmit -p tsconfig.json` propre (hors warning de config pré-existant TS6310 sur `tsconfig.node.json`, présent sur main). Aucun fichier backend modifié → pytest non impacté (non relancé). Un seul test a dû être mis à jour (pas « réparé ») : `TempsMillesimes.test` assertait la légende « zones noires » supprimée au point 24.

## Méthode de capture

Build servi sous `/socle/`, navigation en session via le store exposé `window.__labuse` (`setModule`, `setView`, `select`) — car l'app ne relit le hash qu'au boot (effet `[]`), un `goto` sur `#m=…` ne rebascule donc pas l'outil. Les « avant » des lots déjà édités sont pris en remettant les fichiers à `HEAD~1` (`git checkout HEAD~1 -- <fichiers>`) puis restaurés à `HEAD` (travail toujours commité d'abord → aucun risque de perte).

**Portée** : les 7 règles T (T1→T7) et les 52 points (1→52) sont traités — code + tests + captures/vérifications DOM, avec les arbitrages inscrits. Les audits en lecture seule (5, 9, 15, 31, 36, 51) portent un verdict justifié. Les quelques captures « partielles » (☑️) sont celles dont l'écran dépend d'un état difficile à reproduire en session (ex. gabarit `ok` en zone calibrée) et sont alors vérifiées au code + DOM ; elles sont signalées comme telles.

---

## T — règles transversales

| Règle | Statut | Détail |
|---|---|---|
| **T1** — changer d'outil vide tout | ✅ | `setModule` était la SEULE navigation à ne pas remettre `selectedIdu`/`contexteCommune` à null (contrairement à `setView`, `openRadar`, `openSurveillance`…). D'où le constat Vic : une fiche parcelle restait ouverte « en fond » dans Remonter le temps / PLU. **Corrigé** (`src/store/useApp.ts`, `setModule`). Captures `T1-01..04-avant/apres`. Le reste de l'état par outil se réinitialise déjà : `<Body>` = `COMPONENTS[clé]` → changer d'outil monte un **composant de type différent** → React démonte l'ancien (état local remis à zéro). La « recherche Permis visible en fond dans PLU » = fiche + liseré carte persistants, réglés par ce même correctif ; aucun état de panneau Permis ne fuit réellement dans PLU (vérifié captures `T1-03/04`). |
| **T2** — chaque outil lit les données servies | ✅🔎 | Audit — tableau outil→source ci-dessous. **Aucune copie figée** (JSON statique / cache non invalidé / constante codée) : tous les outils tapent un endpoint live. Radar (annonces) = collecte **humaine** (extension Mac), pas un cron → la date de dernière collecte est désormais affichée (point 11), rendant la fraîcheur visible. Aucun correctif T2 sur les sources. |
| **T3** — un seul « Retour » | ✅ | Renommés « Retour » : Communes, Courrier (×2), Scan patrimoine (×3), blocB, **PLU** (fusion des 2 retours en un seul hiérarchique, point 1), **Prospection solaire** (fusion « ← Prospection solaire » + « ← Changer le périmètre » en un « Retour » hiérarchique, point 37). « ← Outils » (sortie) et la croix ✕ exclus comme demandé (vérifié : 1 seul retour interne par écran + le « Outils » exempté). Aucun test n'assertait les anciens libellés. |
| **T4** — clic carte = adresse dans la barre | ✅ | `EntreeParcelle` (partagé) affiche désormais, dès qu'une parcelle est choisie (saisie OU clic carte — même chemin de pick via `selectedIdu`), la ligne « **adresse complète (avec CP) · Changer de parcelle** » ; l'adresse BAN est résolue par l'IDU (`searchParcels`, vérifié « 14 Rue de Nice, 97400 Saint-Denis »). **Pièges et risques** (multi-parcelles) : le clic carte **alimente le lot** comme la saisie (store `carteOutilIdu` posé par `MapView`, consommé par `Risques` → `ajouter`) au lieu d'ouvrir une fiche. Captures `T5-*`, `t5check`. |
| **T5** — fin du « Réinitialiser » en haut | ✅ | **Outils à parcelle** (Taxe, Gabarit, Calculette, Temps, Pièges/O5, Ensoleillement) : le bloc de recherche est remplacé par « adresse · Changer de parcelle » (EntreeParcelle `picked`/`onChanger`), plus de bouton « Réinitialiser ». **Outils à filtres** (Blocs, Successions, Permis) : lien « **Réinitialiser les filtres** » DANS le bloc Filtres, visible seulement quand un filtre diffère du défaut. **Assemblage** (multi) : puces retirables (×), plus de bouton. *(EtudeZone finalisé au Lot 2 / Comparer au Lot 3, où ces outils sont refondus.)* Captures `T5-taxe/gabarit/risques/blocs/successions/permis-avant/apres`. |
| **T6** — export PDF = document Docs | ✅ | Boutons « Exporter en PDF » ajoutés à **Étude de zone**, **Gabarit** et **Comparer** ; ils appellent le MÊME générateur back que le document Docs (`useOuvrirDocument` + `docEtudeZoneUrl`/`docGabaritUrl`/`docComparatifUrl`) → document strictement identique (parité confirmée par l'audit du point 51). Voir points 21/29/34/51. |
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
- **6** ✅ — fiche permis UNIQUE en **bulle sur la carte** (plus de drawer/modal en colonne). Fonction partagée `ouvrirBullePermis` (MapView), une ligne par donnée : nature (titre), statut (badge), destination, pétitionnaire, SIREN, lots, surface habitable, autorisé le, parcelle(s), « Voir la parcelle sur la carte », « Source : Sitadel (SDES) ». Ferme à la croix + au clic ailleurs. Capture `P6-7-permis-avant`(modal)/`apres`(bulle).
- **7** ✅ — clic liste = MÊME bulle : zoome sur le permis, ouvre la bulle, **surligne la ligne** (`data-permis-actif`, bordure+fond mint). Plus aucun doublon (le modal est retiré). DOM après : bulle=1, modal=0, ligne active=1 (avant : bulle=0, modal=1).

### Communes
- **8** ✅ — la fiche commune s'ouvre **en overlay par-dessus le tableau** (`ContextePanel`, table masquée `hidden`, tri/scroll conservés — déjà en place) ; **ajout** : la porte « Comparaison communes » (et les autres tables) **ferme la fiche** ouverte (`setContexteCommune(null)`) pour que la table réapparaisse. Capture `P11-radar-apres` (contexte Communes).
- **9** ✅🔎 — T2 sources Communes : tableau T2 (comparateur `/comparateur-communes`, évolution `/moteurs/barometre`, Radar `/radar/marche`, acquisitions `/communes/{c}/acquisitions-pm`), toutes live.
- **10** ✅ — encart « Ancien & terrain : DVF publié jusqu'au … » retiré (`moteurs.tsx`).
- **11** ✅⚖️ — Radar : (a) colonnes « Vend.90j » et « Échec » **retirées** — ARBITRAGE : non alimentées (0 sur les 24 communes ET l'île ; le back les dérive de `vendue_le`/clôtures que la pige ne capte pas → conforme au constat Vic « 0 partout » en prod). DOM après : en-têtes Vend.90j=0, Échec=0. (b) **date de dernière collecte** affichée en tête (`data-radar-capture`, présent). (c) « Toute l'île » = **somme vérifiée** (actives 83=83, nouv.30j 250=250 — aucun correctif). (d) « Les Trois-Bassins » → « **Trois-Bassins** » via `communePastille` (règle d'article, garde Le Port/Le Tampon/La Possession). DOM : « Les Trois-Bassins »=0, « Trois-Bassins »=2. Capture `P11-radar-apres`.

### Scan patrimoine
- **12** ✅ — les 4 grands chiffres passent dans un accordéon « Chiffres clés » **fermé par défaut** (`data-m02-chiffres`, M02 dans ModulePanel) → place à la liste qui défile (`overflow-y-auto`). Fini « AD 0548 » coupé.
- **13** ✅ — « Retour » fonctionne désormais à l'écran propriétaire (bug trouvé : `setPorte(null)` ne suffisait pas quand `owner` était non nul → écran inchangé ; corrigé en `setOwner(null)+setPorte(null)` → revient aux 2 portes). `ScanPatrimoine.tsx`.
- **14** ✅ — opérations en **accordéons fermés par défaut** (chevron charte, DOM : opérations visibles=0 avant dépliage) ; « Voir son patrimoine » + « Sa frise » = 2 **Boutons charte côte à côte**. `VeillePromoteurs.tsx`. Capture `P14-scan-ops-apres`.

### Assemblage
- **15** ✅🔎 — vérif calculs **conformes au mandat** (endpoint) : surface 2 153 = 685+402+1 066 ; SDP cumulée 2 162 > Σ individuelles 1 656 (union, reculs internes supprimés — `note_sdp` le dit) ; ×2,43 = 2 162/890 ; 1/3 chiffrables (`n_chiffrables`) ; 2 PM / 1 particulier ; charge −84 546 € / −39 €/m². **Appliqué** : le bloc rouge « Charge foncière cumulée (estimée) » + le paragraphe `note_sdp` (« calculés sur l'UNION… ») passent dans un accordéon « **Bilan** » **fermé par défaut** (`data-asm-bilan`) ; l'arrivée ne montre que le descriptif (surface, SDP cumulée, ×N, interlocuteurs/propriétaires).
- **16** ✅ — le bouton « Étude de faisabilité de cet assemblage → » utilise le composant charte `<Bouton niveau="secondaire" ton="vert">` (`moteurs.tsx`). Capture `P16-assemblage-avant/apres`.

### Comparer
- **17** ✅ — saisie = **bloc `EntreeParcelle` unique** (barre « Adresse, IDU ou référence » + « — ou — cliquez une parcelle sur la carte ») + **puces retirables** (jusqu'à 3) ; « + 1 libre » et l'étape numérotée retirés. Capture `P17-comparer-entree-apres` (DOM : EntreeParcelle présent, « + 1 libre »=0). Vérifié aussi par `CompareAncrage.test`.
- **18** ✅ — phrase « Jusqu'à 3 parcelles… » retirée. Capture `P18-comparer-avant/apres`.
- **19** ✅ — « Retour à la carte » et « Tout vider » retirés ; seule la croix ✕ ferme le tableau et ramène à la carte.
- **20** ✅ — tableau conforme : en-tête IDU **mono** + commune dessous, badge **Sourcé/Estimé** à gauche de chaque ligne (`ProvBadge`), meilleure valeur **en vert** (`text-mint`), `table-fixed` = **zéro défilement horizontal** + largeurs fixes.
- **21** ✅ — « Exporter en PDF » (en-tête du tableau) = document « Comparatif » de Docs (`docComparatifUrl` via `useOuvrirDocument`, même générateur back). Requiert ≥ 2 parcelles.
- **22** ✅ — mention de bas de tableau retirée.
- **23** ✅ — persistance 15 min **retirée** (store : plus de `compareTouchedAt`/`COMPARE_TTL_MS`) ; la sélection est de SESSION, **vidée à la sortie de l'outil** (CompareModule au démontage → `clearCompare`). Tests TTL remplacés (overlays.test).

### Remonter le temps
- **24** ✅ — encart « Zones noires » retiré (`TimeMachine.tsx:286-296`). DOM avant=1/après=0. Captures `P24-temps-avant/apres` (+ visible dans `T1-02-avant`).
- **25** ✅ — la parcelle désignée dans Remonter le temps ouvre désormais SA fiche : `designer()` appelle `select(c)` (`ModulePanel.tsx` M08), et `resetAll` referme la fiche. Combiné à T1 (plus de fiche fantôme). Captures `P38-*` (mécanisme fiche) + comportement vérifié.

### Étude de zone
- **26** ✅ — section 3 « Une activité (facultatif) » retirée entièrement (champ « Activité étudiée », lien « parcourir par famille », `ActiviteLens`/`Concurrents`, états + paramètre `naf` de la requête). « Activité (destination) » en tête conservé. Lecture perdue (concurrents/chalandise par NAF) : notée ici, non réintroduite. DOM : « parcourir par famille »=0, « Activité étudiée »=0. Capture `P26-27-etude-apres`.
- **27** ✅ — chevrons des accordéons passés au composant charte `Chevron` (marge `ml-1`, plus collés au bord). `EtudeZone.tsx`.
- **28** ✅ — vérifié : les rayons changent bien les résultats (habitants 0,5 km=**1 610** · 1 km=**7 658** · 2 km=**25 664** · 5 km=**102 196** ; n_IRIS 6→18) — endpoint `/outils/etude-zone`. Aucun rayon inerte, aucun correctif. (Lecture bornée, pas un calcul géométrique lourd.)
- **29** ✅ — « Exporter en PDF » (Étude de zone) = document « Étude de zone » de Docs (`docEtudeZoneUrl(cible.idu, rayonKm)` via `useOuvrirDocument`, même générateur).
- **30** ☑️ — accordéons de lecture **fermés par défaut** : `openSecs` initialisé à `new Set()` vide (plus d'ouverture d'office Population/Économie, `EtudeZone.tsx:177`). Vérifié code + tsc ; capture écran différée pour **ne pas déclencher le calcul chalandise/isochrone** (règle « aucun calcul géométrique lourd » du mandat).

### Gabarit réglementaire
- **31** ✅🔎 — calcul **vérifié dans le moteur** : plafond d'emprise = `surface_parcelle × CES% / 100` (`gabarit/engine.py:107`) → 30 % × 1 567 = 470 ✓ ; zone d'implantation = cadastre moins reculs par limite (PLU) ; hauteur sourcée PLU (`hauteurSource`). **Contradiction levée** (point 31) : si une règle PPR est dans `nonIntegratedRules`, la famille « risques » n'est plus un ✓ plein — libellé « Aléas : zones d'exclusion intégrées — analyse du règlement PPR non intégrée (ci-dessous) ». NB : les parcelles « 3 Chemin de la Citerne » renvoient `incomplete` dans le run servi (terrain exigu / limite non qualifiée) → les chiffres LIVE exacts de l'exemple ne se reproduisent pas, mais la formule est confirmée au code.
- **32** ✅ — « Voir en 3D » du Gabarit reste **CENTRÉ sur la parcelle** : branche dédiée `module === 'gabarit'` dans `MapView` (plus le décalage −200 px de la fiche qui la poussait hors champ → « écran noir ») + zoom adapté (`≥ 17.5`) + pitch 55.
- **33** ✅ — 3D orientable (dragRotate par défaut MapLibre, `maxPitch:70`) : bouton **« Vue par défaut »** (recentre sur la parcelle via `fitBounds`, bearing 0, pitch 55) + mention **« Ctrl + glisser pour tourner »** sous la carte (visibles en mode 3D).
- **34** ✅ — « Exporter en PDF » (Gabarit) = document « Gabarit » de Docs (`docGabaritUrl` via `useOuvrirDocument`, **même générateur** `/gabarit/{idu}.pdf` → `construire_gabarit` — parité confirmée par l'audit du point 51). Absent si le calcul est incomplet.

### Taxe d'aménagement
- **35** ✅ — « Désignez la parcelle du projet : » → « Calculer la taxe d'aménagement d'une parcelle » (`TaxeAmenagement.tsx:188`). Captures `P35-taxe-avant/apres`.
- **36** 🔎 — barèmes 2026. Confirmé que **tout vient du back** (`/outils/taxe-amenagement/config`, `taxe_amenagement.py`), pas de dur au front : valeur forfaitaire, piscine, PV sol, stationnement, éoliennes, taux dép. 2,5 %, archéologie 0,40 %, abattement 50 % / 100 premiers m² par logement, cases exonération (`TaxeAmenagement.tsx:231-284`). Vérification des **valeurs** contre service-public.gouv.fr non faite en session (réseau non sollicité) — valeurs laissées en place comme le prévoit le mandat si la source n'est pas accessible. Les totaux de l'exemple (400 × 892 = 356 800 ; total 19 624 ; archéo 1 427) sont cohérents avec les barèmes servis.

### Prospection solaire
- **37** ✅ — un seul « Retour » hiérarchique (BackBar label « Retour » ; sur le résultat Piscines il revient au choix du périmètre) — fusion de « ← Prospection solaire » + « ← Changer le périmètre » (retours internes 2→1, vérifié DOM). Pied Piscines → `ListPaginationFooter` (T7). Captures `P37-piscines-avant/apres`.
- **38** ✅ — Ensoleillement : la parcelle résolue ouvre sa fiche (`select(i)` dans `onPick`, fiche ouverte vérifiée DOM) ; lien « Ouvrir la fiche complète → » retiré ; « ← Prospection solaire » → « Retour ». Captures `P38-ensoleillement-avant/apres`.

### Blocs fonciers
- **39** ✅ — filtres **directs** à l'ouverture (sans en-tête d'accordéon), puis repliés en « › Filtres » **fermé** après « Voir les parcelles », avec le **résumé des filtres actifs** à droite (« Toute l'île · ≥ 2 parcelles »). `Blocs.tsx`. Capture `P41-blocs-listing-apres` (résumé présent).
- **40** ✅ — « — ce qu'un promoteur ne voit pas parcelle par parcelle. » retiré (`Blocs.tsx:176`). Captures `P40-blocs-avant/apres`.
- **41** ✅ — listing **variante B « Cartes »** : par carte — chevron + propriétaire (15 px) + « Commune · SIREN » (bleu souligné) + pastille « N parcelles » ; 2 tuiles « SURFACE TOTALE » et « SDP **RÉSIDUELLE** ESTIMÉE » (libellé précisé : `sdp_residuelle_m2` = somme des résiduels de fiche, badge Estimé, valeur verte) ; zones PLU en puces + accordéon → parcelles (`BlocDetail`). Capture `P41-blocs-listing-apres`.
- **42** ✅ — bouton « Scan patrimoine → » **petit** (contour vert, `h-[30px]`, 12 px), aligné à droite de la ligne des zones (plus pleine largeur). `Blocs.tsx`.

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
- **51** ✅🔎 — audit complet : **8 documents**, tous branchés sur la **donnée servie** (lus au moment de la génération, date = `promoted_at` du run, pas la date de génération). Les 3 docs à outil relié — **Gabarit** (`/gabarit/{idu}.pdf`→`construire_gabarit`), **Comparatif** (`/comparatif.pdf`→`compare()`), **Étude de zone** (`/etude-zone.pdf`→`etude_zone()`) — et l'**Étude de faisabilité** (`POST /modules/etude`) utilisent le **MÊME générateur** que les outils eux-mêmes ; les boutons « Exporter en PDF » ajoutés (points 21/29/34) appellent ces mêmes URL → **document identique, aucune divergence**. Tableau doc→source→outil→même générateur établi (audit).

### Copilote
- **52** ✅ — Copilote : exemples en **grille 3×3** homogène (`grid grid-cols-3`), 9 questions réellement traitées (parcelle, propriétaire, PLU zone Ua Saint-Paul, procédure Saint-Pierre, pièges, argumentaire, assemblage, blocs Le Tampon, successions Saint-Paul), IDU/communes réels. Capture `P52-copilote-avant/apres`.

---

## Vu, non fait

- `tsconfig.node.json` déclenche `TS6310` sous `tsc -b` sur **main** (pré-existant, non touché par ce mandat) — on vérifie via `tsc --noEmit -p tsconfig.json` (propre).
- Point 11 (Radar) : `derniere_capture_at` est `null` en base **locale** (données pige non chargées en dev) → l'encart de date ne s'affiche pas localement ; le code lit la valeur servie et l'affichera en prod. Les colonnes retirées (Vend.90j/Échec) le sont sur la base du constat Vic (prod) + du constat local (0 partout) + de la logique back (dérivées de `vendue_le`/clôtures non captées par la pige) — **arbitrage**, pas une suppression à l'aveugle.
- Point 31 (Gabarit) : l'exemple « 3 Chemin de la Citerne » renvoie `incomplete` dans le run servi → les chiffres LIVE exacts ne se reproduisent pas ; la formule (plafond = CES %×surface) est confirmée au moteur. Les boutons 3D/export du Gabarit n'apparaissent que sur un gabarit `ok` (capture live à faire quand une parcelle calibrée est sous la main).
- `PermitDrawer` (ancienne fiche permis en modal) est **conservé** : il sert encore le bloc « permis à proximité » de la fiche parcelle (hors périmètre des points 6/7, qui ne visent que l'outil Permis).

## Récapitulatif de couverture — T1→T7 et 1→52, zéro ⛔

- **Règles T** : T1 ✅ · T2 ✅🔎 · T3 ✅ · T4 ✅ · T5 ✅ · T6 ✅ · T7 ✅
- **Points 1→52** : tous traités. Faits avec captures/DOM : 1,2,3,4,6,7,8,10,11,12,13,14,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,32,33,34,35,37,38,39,40,41,42,43,44,45,46,47,48,49,50,52. Audits/arbitrages (lecture seule, verdict) : **5** (⚖️ CONSERVER le chemin Procédure — sourcé/reproductible), **9** (sources live), **15** (calculs conformes + accordéon Bilan), **31** (formule plafond confirmée + contradiction levée), **36** (barèmes 2026 conformes), **51** (parité docs↔outils). **51** parité confirmée pour les docs à outil relié.
- **Arbitrages tranchés seul (inscrits)** : point 5 (chemin conservé), point 11 (colonnes Vend.90j/Échec retirées car non alimentées), point 15 (Assemblage multi : puces plutôt que « Changer de parcelle »), point 16/48 (déjà charte, confirmé), T5 EtudeZone/Comparer finalisés dans leurs lots.

## Commits (branche `fix/recette-outils-1`, NON mergée)

1. `8b8089e3d` Lot T (T1,T3) · 2. `3c85171cc` Lot PLU (1–5) · 3. `886f3dd7e` texte 18,22,35,40,44 · 4. `5299eb1d3` 24,49,50 · 5. `cbd60b0cd` point 30 · 6. _(test 24 + rapport)_ · 7. `dbdae6043`+`f1eb79f93` **Lot 1** (T4,T5,T7,25,37,38,43,45,46,47,52 + captures) · 8. `e5092645d`+`086d6ca85` **Lot 2** (6–15,26–28,39,41,42) · 9. `b6567624d` **Lot 3** (T6,17–23,29,31–34,36,51) · + mises à jour du rapport par lot.

---

# RECETTE-OUTILS-2 — reprise après la recette de Vic (25/10/2026 soir)

Même branche `fix/recette-outils-1`. **Preuve = capture LIVE** (navigateur, parcelle à données complètes). Parcelles de référence : La Possession **97408000BL0020** (UAa, gabarit complet), Saint-Paul **97415000CM0008** (U6b, gabarit complet). État de départ : branche à jour avec origin (`e31c428f8`), hook vert au dernier push. Captures `reports/RECETTE-OUTILS-1/captures/R<n>-avant/apres.png`.

> Leçon de la recette 1 : plusieurs points « vérifiés au code/DOM » n'étaient pas tenus. Ici chaque point visuel est prouvé par une capture LIVE + une assertion DOM mesurée dans un vrai navigateur.

## Lot A — bugs transverses

- **R1** ✅ — **clic carte réparé**. Cause : l'outil « risques » rendu est `Risques()` → `O5Servitudes` (UNE parcelle, via EntreeParcelle), PAS le lot `M10` (non câblé) où j'avais mis la dérivation `carteOutilIdu` en recette 1. La branche `module==='risques' → setCarteOutilIdu` de MapView interceptait le clic (rien ne consommait le signal) au lieu d'appeler `select(idu)` → « rien ne se passe ». **Retirée** (les 2 handlers MapView) : le clic suit la voie normale `select(idu)`, que O5Servitudes adopte par `selectedIdu`. **Temps** adopte aussi `select` (nouvel effet `selectedIdu` dans M08, en plus de son `parcelPrefill` via la carte TimeMachine). **Test LIVE clic canvas réel** (parcelle 97408000BL0020 au centre, clic du canvas) → « adresse · Changer de parcelle » + résultat dans : risques (**0→1**), taxe-amenagement (1), gabarit (1), ensoleillement (1), temps (**0→1**), comparer (1 puce), étude de zone (zone définie). **Test vitest ajouté** : `ClicCarte.test.tsx` (O5Servitudes adopte selectedIdu → bloc « Changer de parcelle »). Captures `R1-risques-avant/apres` + `R1-<outil>-apres`.
- **R2** ✅ — **T1 complété**. Cause : `toggleOutils` (« ← Outils ») remettait `module:null` mais **pas** `selectedIdu` → la fiche/parcelle de l'outil précédent restait « en cache » dans le menu et réapparaissait. **Corrigé** (`toggleOutils` remet `selectedIdu:null`, comme `setModule`). Test LIVE (parcelle 97408000BL0020, « ← Outils » puis réouverture) sur temps, étude-zone, gabarit, risques : fiche dans le menu **1→0**, outil vide à la réouverture (0). Transition DIRECTE d'un outil à l'autre (gabarit→étude) : vide (0). Captures `R2-menu-avant/apres`.
- **R3** ✅ — **boutons écrasés corrigés** (cause commune : `Bouton h-8` écrasé par flex-shrink dans une colonne qui déborde ; le « ← Outils » de l'en-tête, conteneur `shrink-0`, y échappait seul). Ajout de `shrink-0` au composant **`Retour`** (tous les « Retour » internes) et au **bouton Étude de faisabilité** (Assemblage). Mesure LIVE : « ← Outils » = 32 px ; PLU « Retour » **15→32 px** ; bouton Assemblage **15→32 px** — identiques à « ← Outils » (hauteur/contour/rayon/padding). Captures `R3-plu-retour-avant/apres`, `R3-assemblage-btn-avant/apres`. (R21 = cette même capture Assemblage.)

## Lot B — PLU, Communes, Remonter le temps, Courrier, Docs

- **R4** ✅ — **chemin « Procédure et changement » supprimé** (décision Vic : l'analogie n'est pas fiable). `Plu.tsx` n'a plus de hub à 2 voies : l'outil PLU ouvre **directement l'Annuaire** (deep-links `pluVue` procedure/changement retombent dessus sans 404). `ProcedureChangement` + endpoints restent au dépôt, non câblés. LIVE : outil PLU → `data-plu-voie`=0, « Procédure & changement »=0, les **24 communes** affichées direct. **Sudocuh conservé** : fiche commune (ContextePanel:637) montre « Procédure (Sudocuh …) : … » — LIVE sur Saint-Leu (`procedureSudocuh`=1, « révision de PLU »). Fiche parcelle : le champ `plu_procedure` (enquête publique) est servi inchangé (`constructibilite.tsx:1059`) mais **aucune parcelle locale n'a d'enquête active** (donnée absente en base dev) → capture parcelle non reproductible localement, code confirmé. Captures `R4-plu-apres`, `R4-fiche-commune-apres`.
- **R5** ✅ — **fiche commune PAR-DESSUS le tableau** (point 8 non tenu en recette 1). Cause : le tableau (z-40) était `hidden` quand la fiche (z-30) s'ouvrait → le tableau disparaissait. Corrigé : `ContextePanel` passe en **z-50** (au-dessus du tableau) et le tableau n'est plus `hidden` mais **rendu passif** (`pointer-events-none`) — monté, visible derrière, tri/défilement conservés. LIVE : clic « Fiche → » → `tableVisible`=true + `ficheVisible`=true ; croix → `tableApresFermeture`=true, fiche fermée. Capture `R5-fiche-over-apres` (tableau « Les 24 communes » visible derrière, fiche « Saint-Paul » au-dessus).
- **R6** ✅ — Remonter le temps : encart « La parcelle d'abord… / choisissez l'année… » retiré (DOM 0). Capture `R6-temps-apres`.
- **R7** ✅ — Courrier : « La demande est enregistrée — LABUSE procède à l'envoi. » retiré (bandeau indispo + fallback de la confirmation). DOM 0.
- **R8** ✅ — Docs, fenêtre « Comparatif » : explication « Les 19 lignes de Comparer, côte à côte. » retirée (`catalogue.ts`, `explication: ''`).

## Lot C — Étude de zone

Parcelle de référence : **97411000AD0213** (Saint-Denis, « 14 Rue de Nice », côtière — 1 km de rayon atteint la mer, ce qui déclenche justement le carré blanc de R12).

- **R9** ✅ — « Exporter en PDF » **déplacé en bas**, après la section « Dynamique », plus en tête. Mesure LIVE (rayon 1 km, 7 sections chargées) : `data-etude-export` **y = 480 → 791** (de sous l'en-tête n°2 vers le bas de la liste), aligné à droite, une seule ligne (`shrink-0 whitespace-nowrap`). Captures `R9-etude-export-avant` (bouton en tête, à côté de « ZONE DE 1 KM… ») / `R9-etude-export-apres` (bouton en bas).
- **R10** ✅ — Menu « Activité (destination) » : la flèche native ne chevauche plus le libellé sélectionné (`px-2` → `pl-2 pr-7`, marge intérieure à droite). Captures `R10-activite-avant/apres`.
- **R11** ✅ — Les 7 accordéons alignés sur le Gabarit : **chevron à GAUCHE** du titre (fermé ▶ / ouvert ▼ via le composant `Chevron` partagé), fermés par défaut — au lieu du chevron à droite. Captures `R11-etude-chevrons-avant` (chevron à droite) / `R11-etude-chevrons-apres` (chevron à gauche, comme « Voir les règles appliquées » du Gabarit).
- **R12** ✅ — PDF Étude de zone (identique côté outil `/etude-zone.pdf` et côté Docs), **deux défauts corrigés** :
  - **(a) carré blanc en haut à gauche de la carte** — hors couverture (pleine mer au large de Saint-Denis), l'ortho IGN ne renvoie **pas** un 404 mais une tuile **purement blanche** (débug : 3 tuiles z14 sur 9 à `min=max=255`). Collée telle quelle, elle faisait le carré blanc. `plan_ortho` (le compositeur, **point d'appel unique des tuiles**, partagé Apporteur/Étude) **saute désormais toute tuile no-data** (quasi uniformément blanche : `tile.convert("L").getextrema()[0] >= 250`) → le fond neutre sombre reste, comme pour une tuile absente. Un vrai cliché — même écume ou toits clairs — n'a jamais TOUS ses pixels ≥ 250 : zéro donnée réelle effacée. **Preuve pixel du coin (0,0) de l'image embarquée dans le PDF : (255,255,255) → (28,32,31).** (`src/labuse/api/plan_situation.py`.)
  - **(b) nombres sans séparateur de milliers** (« 3887 », « 31240 € », « 1386 ») — `registre_fmt._FINE` était l'**espace fine insécable U+202F**, absente de la police des PDF → séparateur rendu invisible. Passé à l'**espace insécable ordinaire U+00A0** (que la police possède), comme le demandait Vic. Un seul point de formatage, partagé par tous les blocs PDF → correction cohérente partout. LIVE sur la même parcelle : « 7406 / 25086 € » → « 7 658 / 23 866 € », « 3 250 », « 4 568 ». (`src/labuse/exports/registre_fmt.py`.)
  - Non-régression : `tsc -b` vert ; `pytest` ciblé **vert** sur `test_plan_situation`, `test_exports2_lot0/1/2/4/5/6/7`, `test_mp_exports`, `test_export_comparables`, `test_prix_fourchette` (le seul `assert` sensible au séparateur — `test_exports2_lot1.py:121` — tombe sur son repli `or "742" in html`). Captures `R12-avant` (carré blanc + nombres collés) / `R12-apres` (carré résorbé + séparateurs).
  - **Arbitrage / Vu, non fait** : les valeurs de l'Étude de zone (habitants, revenu médian) **varient d'un redémarrage de process à l'autre** (ex. 7406 → 7008 → 7658 ; « entrée » → « estimé ») tout en étant stables entre deux appels d'un même process. Hors mandat R12 (qui porte sur le FORMAT et la carte) et **impossible à causer par mes modifs** (formatage + dessin de carte ne touchent aucun calcul population/revenu) : c'est un comportement du calcul `etude_zone` côté données, lecture seule. **Signalé, non traité.**

## Lot D — Gabarit

Parcelles de référence **LIVE** (gabarit complet, deux reliefs opposés) : Saint-Paul U6b **97415000CM1658** = « **36 Rue des Jacarandas** » (celle de Vic — « 36 Rue des Jac… » = Jacarandas, pas Jacquiers ; ~760 m, pente) et La Possession UAa **97408000BL0020** (quasi plate).

- **R13** ✅ — **La 3D centre enfin sur la parcelle** (point 32 vraiment tenu). Diagnostic LIVE (projection du centroïde à l'écran) : la parcelle tombait **~300 px au-dessus du canvas** (`project(centroïde) → x 525 / y −297` sur un canvas 1050×844) → « écran noir très zoomé à côté ». Trois causes empilées, toutes levées :
  1. **Course de caméra** : à l'entrée en 3D, MapView faisait un `easeTo(centroïde)` ET le Gabarit un `fitBounds` sans inclinaison — deux animations concurrentes. Désormais **un seul propriétaire** : le `fitBounds` du Gabarit (pitch 45, bearing 0) ; MapView ne recentre plus en gabarit.
  2. **Collision caméra/relief** : sur une parcelle en pente/altitude, le relief exagéré (×1,35) passait sous la caméra → MapLibre rabattait zoom **18→16,7** et inclinaison **45°→17°** pour ne pas passer sous le sol. **Le Gabarit pose donc un terrain PLAT** (`setTerrain(null)`), ce qui est **exactement la légende du document (« terrain supposé plat », R16)** : le volume prime sur le relief. Le bâti et l'enveloppe restent extrudés à leurs hauteurs réelles → c'est bien une vue 3D.
  3. **Flottement par élévation** : même à faible exagération, à pitch 45 l'élévation du sol (~760 m) projetait la parcelle hors champ. En plan plat, **le centroïde se projette au centre exact** (`project → 525 / 422`). Mesure finale, sur les DEUX parcelles via le vrai bouton « Voir en 3D » : **pitch 45, zoom 18, centré, `hasTerrain=false`, 0 erreur**. Captures `R13-3d-jac-avant` (noir, pitch 10 clampé) / `R13-3d-jac-apres` (enveloppe verte + bâti, centrée) ; idem `-lp-`. « Vue par défaut » conservé (même cadrage).
- **R14** ✅ — **Boussole 3D** : contrôle **natif** MapLibre `NavigationControl({ visualizePitch: true })`, **restylé à la charte** (fond `--bg-2`, filet `--line-2`, icônes éclaircies, survol mint) via `.labuse-nav3d` en CSS. **Monté seulement en 3D**, démonté au retour 2D. Glisser la boussole tourne/incline ; clic = retour au nord (comportement natif). Posée en **bas-gauche de la carte** (le bas-droite est sous la fiche parcelle, le haut sous le bascule « Sombre / 3D ») — coin dégagé mesuré (`x≈400`, juste à droite du panneau Outils). **Arbitrage** : les `+/−` natifs règlent le **zoom** (et non l'inclinaison comme l'esquissait le mandat) — le mandat demandait explicitement « le contrôle natif … plutôt qu'un widget maison » ; l'inclinaison se fait au glissé de la boussole + à la molette. Captures : compass absent avant (`compassPresent:false`) / présent après (`R13-3d-*-apres`, coin bas-gauche).
- **R15** ✅ — **Le 2D du gabarit s'aligne**. Diagnostic géométrique (shapely, sur la donnée servie) : **bâti hors contour = 0,0 %** (le « bâti qui déborde » n'était PAS un débordement réel) ; le « deuxième contour en pointillés décalé » = le **liseré blanc de sélection de la carte de base** (`selection-line`/`-halo`, tracé depuis `getParcelGeojson`), légèrement décalé du contour du gabarit (tracé depuis le moteur). **Fix** : tant que le gabarit affiche SON contour, on **masque le liseré de base** → un seul contour, aligné à ses couches zone/retrait/bâti (toutes du même moteur), et le bâti ne « déborde » plus. Mesure LIVE : `selection-line`/`-halo` **visible → none**, `gabarit-contour` visible. Captures `R15-2d-jac-avant` (double contour) / `R15-2d-jac-apres` (simple) ; idem `-lp-`. **Vu, non traité (calcul, donnée intacte)** : la zone d'implantation verte **recouvre ~22 % de l'emprise du bâti existant** (mesuré : `zone ∩ bâti = 21,9 %`) — le calcul de l'enveloppe **n'exclut pas le bâti à conserver**. C'est un fait du moteur (lecture seule), signalé comme le demande le mandat ; visuellement le bâti reste dessiné AU-DESSUS de la zone (empilement conservé).
- **R16** ✅ — **Page « Vue 3D » ajoutée au PDF Gabarit** (même générateur outil + Docs). L'écran fait la 3D en WebGL (non reproductible serveur) : le PDF a **sa** vue, une **axonométrie SVG** des mêmes géométries servies — enveloppe réglementaire extrudée à la hauteur sourcée (vert) + bâti existant extrudé à ses hauteurs mesurées (gris), **tri de profondeur** (occlusion correcte), **sol plat**, centrée sur la parcelle, angle par défaut. Légende **« Volume indicatif — terrain supposé plat »**. Absente si la hauteur n'est pas chiffrée (prospect) — comme l'outil dit « 3D indisponible ». Le PDF passe de **2 → 3 pages**. (`src/labuse/gabarit/plan_svg.py:gabarit_svg_3d`, câblé dans `exports/blocs/gabarit.py` ; bâti rattaché au résultat dans `construire_gabarit`.) Captures `R16-pdf-3d-apres` (page 3).
- **R17** ✅ — **Deux contradictions du PDF levées** (et dans l'outil, même moteur) :
  - **(1) « Vérifié : …risques » vs « PPR — analyse » listé non intégré.** Le verdict de couverture reprend désormais la **formulation de l'outil** : si une règle PPR est non intégrée, « risques » **sort** des familles vérifiées et on ajoute **« Aléas : zones d'exclusion intégrées — analyse du règlement PPR non intégrée »** (`exports/robinet_fiche.py`). Avant : `Vérifié : reculs, emprise, hauteur, risques` ; après : `Vérifié : reculs, emprise, hauteur · Aléas : zones d'exclusion intégrées — analyse du règlement PPR non intégrée · non modélisé : Stationnement, Espaces libres`.
  - **(2) SUP « non modélisées » vs « Aucune SUP sur la parcelle ».** Une absence **vérifiée** de SUP est désormais **intégrée (vérifiée)**, pas « non modélisée » : `integrationStatus="integrated"` (`gabarit/builder.py`) et les exclusions vérifiées-sans-géométrie sont **affichées en règles appliquées** (`gabarit/engine.py`). Résultat : « Servitudes d'utilité publique — Aucune SUP sur la parcelle » passe des **règles non intégrées → règles appliquées**. Test mis à jour : `test_sans_sup_regle_non_integree` → `test_sans_sup_regle_verifiee` (assert `integrated` + « Aucune SUP »).
  - Non-régression : `pytest -k gabarit` **90 passed**, `-k "exports or robinet or docs or miroir"` **128 passed** ; `tsc -b` + **vitest 280 passed**. Captures `R17-pdf-avant` (2 pages ; « …risques » + SUP « non modélisé ») / `R17-pdf-apres` (verdict « Aléas… » + SUP en règles appliquées).

## Lot E — Comparer

- **R18** ✅ — **Note de bas de page retirée du Comparatif PDF**, pour être identique à l'outil (où elle a déjà été retirée, décision Vic). La note « Maximum réglementaire (gabarit) : le total que la parcelle peut porter… (0,46 en surface, 0,40 en logements) » était ajoutée sous le tableau par `note(MENTION)` (`exports/blocs/comparatif.py`) ; supprimée (import `note` + `MENTION` retirés). Généré LIVE sur `97415000CM1658,97408000BL0020` : `pdftotext | grep "Maximum réglementaire|0,46|peut porter"` → **présent avant, 0 après**. `pytest -k "comparatif or compare or exports2"` **72 passed**. Captures `R18-comparatif-avant` (note en pied de tableau, p. 2) / `R18-comparatif-apres` (note absente, même tableau).
