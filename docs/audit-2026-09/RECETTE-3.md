# RECETTE-3 — rapport

**Branche** : `feat/recette-3` (depuis `feat/recette-2`). **Worktree** : `~/Desktop/labuse-recette3`.
**Run servi** : `q_v11_m137` (inchangé — aucun rescoring, aucune bascule). **Aucun merge.**
**Règle de preuve** : chaque « corrigé » a été constaté dans un vrai navigateur (Playwright) contre le
backend réel (uvicorn :8021 + front vite :5176). Preuves visuelles : `RECETTE-3-preuves/`.

## Étape 0
`pwd` = worktree · branche `feat/recette-3` · arbre propre · `.env` présent (DB `labuse` locale).
Mandat + maquette validée archivés dans le dépôt : `MANDAT-RECETTE-3.md`, `maquette-apporteur-v3.html`.

---

## Tableau des 14 points

| # | Point | État | Constaté au navigateur | Preuve |
|---|-------|------|------------------------|--------|
| **T1** | Brief apporteur — version validée (maquette v3) | ✅ Fait | Page 1 : **un seul bandeau** (confidentiel + non-mandat fusionnés) ; **plan de situation** ortho réel (contour parcelle mint + voisines) ; ligne **« À côté »** (voisines même propriétaire, Blocs fonciers, réf. CW 1036/0662/…) ; **« Dernière vente »** datée+chiffrée (février 2021 …), omise si inconnue (S8) ; « à jour du GPU »/« plomberie » **absents du brief** (vérifiés inexistants). Pages 2-4 : **contact en 1re question** (L'ESSENTIEL), **3 questions « l'essentiel »** (contact + prix + bail/voisines), photos **par message en citant la référence** (« n'imprimez rien »), une phrase sous chaque section. | `apporteur_p1.png`, `apporteur_q.png`, `apporteur_photos.png` · `tests/test_exports2_lot6.py` (13) |
| **T2** | Supprimer le document Résumé | ✅ Fait | `/resume/{idu}.pdf` → **404** ; dossier/financier/apporteur → 200 ; `/parcels/{idu}/export.pdf` → **308 → /dossier** (repointé, ex-cible /resume). Bloc, route, bouton front, proxy, préfixe numéro, tests : retirés. Aucun autre document ne dépendait du bloc (`api/resume.py` métier conservé, distinct). | curl routes (404/200/308) · `test_exports2_lot1`, `test_non_contradiction` MAJ |
| **T3** | Tri par défaut du listing factuel | ✅ Fait | Défaut factuel = **« Potentiel »** (adressées d'abord → SDP résiduelle → surface), pill Surface conservée. Top des lignes **toutes adressées**, réparties (Saint-Paul, Sainte-Marie, Le Tampon, Saint-Pierre…) — fini les emprises géantes sans adresse. Justification mesurée ci-dessous. | `T3_factuel_potentiel.png` · perf 0,87 s |
| **T4** | Segmentation du listing d'analyse | ✅ Fait | 4 segments **repliables**, ordre fixe, **compteurs exacts** servis par `/filtre` : **Un professionnel a déposé un permis 518** · Terrain nu constructible 67 016 · Bâti à densifier 109 855 · Le reste 108 392. Chaque carte garde son palier (chips Priorité/…). Chevrons togglent (repli vérifié). | `T4_segments.png` |
| **T5** | Servitudes de Pièges et risques (kinds manquants) | ✅ Fait | 6 couches remontées et décodées sur parcelles témoins : **DPU** (« la commune peut se substituer à l'acquéreur »), **DPF** ravines/reculs (« Bras des Chevrettes — marge de recul »), **Zone humide**, **Espace naturel protégé** (« Etang de Saint-Paul »), **PEB remis** (aérodrome Roland Garros), **EBC** (« inconstructible ») + **ER** (« terrain grevé — préemption/expropriation ») via `plu_gpu_prescription` (filtré aux typepsc 01/05). PEB retiré du « non couvert ». | fetch `/servitudes-invisibles/{idu}` sur 7 parcelles · `test_servitudes.py` (14) |
| **T6** | Message IA — crédits Anthropic épuisés | ✅ Fait (déjà conforme) | Texte servi au client (copilote) : « … solde de crédits Anthropic épuisé … (recharger le compte / facturation). Ce n'est pas passager … Inutile de réessayer dans l'immédiat … ». **Ne dit plus « réessayez dans un instant »** et **dit quoi faire**. Cas « plus de crédits » = structurel (core.py:86 → answering.py). | preuve déterministe (simulation BadRequestError 400 « credit balance ») |
| T7 | Tableau des 22 sources | ✅ Fait (lecture seule) | Tableau ci-dessous : chaque source · où elle sert (surface · `fichier:ligne`) · où elle devrait · apport · coût. Vérifié en base réelle (`layer_name` du run servi). | § Lot 2 |
| T8 | Les orphelines | ✅ Fait | Oublis : **TFPB** (ingérée, jamais servie), Zonage A/B/C (commune seule), DPU/PEB/DPF/zones humides (verdict cascade hors run servi). Choix assumés : AZI/TRI, SAR, DVF Région, potentiel foncier, DFI. Absente : ZPPA. | § Lot 2 |
| T9 | Les trois surfaces à couvrir | ✅ Fait | Fiche parcelle > outils > exports — propositions classées. | § Lot 2 |
| T10 | Rendre compte et s'arrêter | ✅ Fait | Rapport livré, branchements classés par valeur, **rien appliqué hors T5**. | § Lot 2 |
| T11 | Financier de bout en bout (S2/S3) | ⛔ Lot 3 — hors périmètre de cette session | — | — |
| T12 | Courrier propriétaire sans champ vide | ⛔ Lot 3 | — | — |
| T13 | Points RECETTE-2 « à recetter à l'œil » | ⛔ Lot 3 | — | — |
| T14 | Maquette apporteur archivée | ✅ Fait (anticipé) | `maquette-apporteur-v3.html` archivée à côté de ce rapport (référence T1). | dépôt |

> La session livre **Lot 1 (T1-T6)** puis **Lot 2 (T7-T10, lecture seule)** et **s'arrête**. Lot 3 (T11-T14) n'est pas traité.

---

## T3 — justification du tri (mesure sur les 30 premières lignes)

Périmètre : univers d'analyse servi `q_v11_m137`, hors étage 0, surface ≥ 2 m² (le listing factuel).

| Tri candidat | avec adresse /30 | avec potentiel (SDP>0) /30 | communes | surface moyenne |
|---|---|---|---|---|
| **A. Surface ↓ (ancien défaut)** | 16 | 4 | 8 | **253 568 m²** (≈ 25 ha, max 96 ha) |
| B. Commune (alphabétique) | 20 | 5 | **1** (une seule commune) | 25 780 m² |
| C. Potentiel seul (SDP ↓) | 24 | 30 | 9 | 90 187 m² |
| **D. Retenu — adresse puis SDP puis surface** | **30** | **30** | **10** | 75 149 m² |

Le tri **A** remonte des emprises géantes **sans adresse et à SDP nulle** (ex. `97416000CR1231`, 96 ha,
0 plancher restant) — inutiles pour un promoteur ou un agent. **B** entasse tout dans une commune
arbitraire. **D** (« Potentiel ») met **toutes les lignes adressées d'abord**, puis celles où il **reste
le plus de plancher à bâtir** : 30/30 adressées, 30/30 avec potentiel réel, sur 10 communes. C'est
celui qui sert le mieux. Coût mesuré : **0,87 s** sur l'île (< budget 1,5 s). Clé serveur `potentiel`
(`_Q_V2_ORDERS`), défaut du mode factuel côté front (`ResultsSection`), tri client identique en mode commune.

## T4 — le signal « un professionnel a déposé un permis »

C'est **exactement** le feature q_v14 `pc_pm_sur_parcelle_pp_36m` : un permis de construire à
pétitionnaire **SIREN** (professionnel) autorisé dans les **36 mois**, **sur une parcelle de personne
physique** (`owner_type = pp`). Live dans l'univers servi : **518** parcelles (le « ~88 » du mandat était
le sous-ensemble monté en *Priorité* par q_v14, pas la taille du segment). Le signal est calculé au vol
(Sitadel), exposé au listing île (`_q_v2_list`) et à la carte commune (geojson), gardé si les tables
Sitadel existent (sinon `permis_pro=False`, jamais une 500). Les compteurs des 4 segments sont servis
exacts par `/filtre` (`_q_v2_stats.segments`, hors étage 0) — leur somme = 285 781 = l'univers retenu.

## T5 — couches ajoutées à `_KINDS` (toutes peuplées en base, vérifié)

`dpu` (202) · `dpf` (281) · `zone_humide` (3 122) · `ens` (84) · `plu_gpu_prescription` (10 490, filtré
EBC/ER = typepsc 01/05) · `peb` (4, aérodrome Roland Garros). Le PEB avait été retiré à M137-T quand la
couche était **vide** ; elle est **peuplée depuis** → remis dans `_KINDS` et sorti du « non couvert »
(règle anti-« couvert-vide » respectée : on ne déclare que des couches réellement peuplées).

## Tests
- Backend (zones touchées) : `test_servitudes` 14, `test_exports2_lot6` 13, `test_exports2_lot1`,
  `test_exports2_lot4`, `test_api`, `test_p_v2_api`, `test_m45_filtres`, `test_filtres_cumul`,
  `test_etage0_filtre_dur`, `test_signaux_vie`, `test_retours14/16_carte` — **verts** (≈ 125 tests).
- Front : `tsc -b` propre · `vitest run` **198/198**.
- Routes documents contre backend réel : /resume 404 · dossier/financier/apporteur 200 · export.pdf 308→/dossier.

# LOT 2 — Les 22 sources : où elles servent, où elles devraient (lecture seule)

**Ce lot n'applique rien** au-delà de T5 (déjà décidé, fait au Lot 1). Il rend compte pour que Vic
tranche source par source. Sources = celles ingérées par **SOURCES-1** (`docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md`,
run candidat `q_v13_sources1` **jamais basculé**).

### Point de fond mesuré (change la lecture de la colonne « cascade »)

Le run **servi** est `q_v11_m137`. J'ai lu ses verdicts stockés (`dryrun_cascade_results`). Les couches
SOURCES-1 se répartissent en deux groupes pour le **scoring servi** :

- **Déjà dans le scoring servi** (verdict présent dans q_v11_m137) : ER/EBC (`prescription_plu`),
  ENS (`ens`), RPG (`safer`), SIS+CASIAS (`sol_pollue`), classement sonore (`bruit_route`), SUP (`sup`),
  SAR (`sar`), potentiel foncier Région (`potentiel_foncier_region`), ravines (`ravine`).
- **PAS dans le scoring servi** — leur **donnée** est en base et **servie live** (fiche, Pièges et
  risques via T5), mais leur **verdict cascade** n'est pas encore dans le run servi : **DPU, PEB, DPF,
  zones humides**. Ils entreront au **prochain rebuild** (ou à la bascule de `q_v13_sources1`). C'est un
  geste de run (Vic), pas un correctif de code.

## T7 — Le tableau des sources

Légende surfaces : **F** fiche parcelle · **O** outils (P&R = Pièges et risques, EZ = Étude de zone,
FA = Faisabilité, CO = fiche Commune, MA = Marché) · **X** exports · **C** cascade/scoring (servi q_v11_m137) · **K** carte.

| # | Source | Où elle sert AUJOURD'HUI (surface · `fichier:ligne`) | Où elle DEVRAIT servir en plus | Apport client (une phrase) | Coût |
|---|--------|------------------------------------------------------|-------------------------------|----------------------------|------|
| 1 | Emplacements réservés (ER) | F+O+X+**C**+K — fiche `app.py` bloc dispositifs ; cascade `cascade/layers/phase1.py` (ER≥50 % rédhibitoire) ; exports `exports/blocs/zonage.py`+`apporteur.py` ; P&R `servitudes.py` (T5) | — (complète) | Un terrain grevé/exproprié se voit avant l'offre. | — |
| 2 | Espaces boisés classés (EBC) | F+O+X+**C**+K — idem ER (`prescription_plu` typepsc 01, ≥80 % rédhibitoire, assiette soustraite) | — (complète) | La part inconstructible est retirée du potentiel. | — |
| 3 | Droit de préemption urbain (DPU) | F+O(P&R T5)+X+K — fiche dispositifs ; P&R `servitudes.py`(T5) ; **cascade PAS dans le run servi** | **C** : au prochain rebuild (vigilance transaction) | La mairie peut se substituer à l'acheteur. | moyen (rebuild) |
| 4 | PEB (Roland-Garros) | F+O(P&R T5)+X+K — fiche dispositifs ; P&R (T5, remis) ; **cascade PAS dans le run servi** | **C** : au prochain rebuild (A/B rédhibitoire) | Bruit aérien = constructibilité restreinte, isolation. | moyen (rebuild) |
| 5 | Zonage A/B/C logement (DHUP) | O(CO) seul — `fiche_commune.py` `zonage_abc()` | **F** (zone de la commune sur la fiche parcelle) + **X** Financier (éligibilité PLS/Pinel/Denormandie) | Détermine les dispositifs d'aide et le prix bailleur. | petit |
| 6 | SUP du GPU | F+**C**+K — fiche dispositifs ; cascade `sup` (servi) ; carte `_MAP_LAYER_KINDS` | **X** exports (bloc dispositifs) ; **O** P&R (déjà via `_KINDS` `sup`) | Servitudes lourdes (ABF, canalisations…) dans le dossier. | petit |
| 7 | ZPPA (Atlas patrimoines) | nulle part — **absente** (Atlas injoignable, `a_faire`, sentinelle 180 j) | — (source hors de portée) | (patrimoine — quand la source ré-ouvre) | gros (source) |
| 8 | Espaces naturels protégés (ENS/INPN) | O(P&R T5)+**C**+K — P&R (T5) ; cascade `ens` (servi, réserves/APB rédhibitoires) ; carte `enp` | **F** bloc dispositifs + **X** exports | Réserve/APB = terrain inconstructible, à dire tôt. | petit |
| 9 | Ravines / reculs (DPF) | O(P&R T5)+X(aléas)+K — P&R (T5) ; carte `dpf` ; **cascade PAS dans le run servi** | **C** : rebuild (marchepied 3,25 m rédhibitoire, L2131-2) | La bande de recul le long des ravines grève l'assiette. | moyen (rebuild) |
| 10 | Zones humides (DEAL) | O(P&R T5)+K — P&R (T5) ; carte `zone_humide` ; **cascade PAS dans le run servi** | **C** : rebuild (vigilance forte) + **X** exports | Remblai/drainage encadrés (loi sur l'eau). | moyen (rebuild) |
| 11 | AZI / TRI (Géorisques) | O(CO) seul — `fiche_commune.py` bloc `azi_tri` | — (**choix** : la géométrie est un doublon de l'aléa `georisque_alea` déjà servi en fiche parcelle) | Atlas inondation, au niveau commune. | — |
| 12 | RPG (cultures) | F+O+X+**C**+K — cascade `safer` (servi, zone A×canne CSA≥50 % rédhibitoire) ; carte `rpg`→`safer` ; `code_cultu` servi | — (complète) | Usage agricole déclaré = friche possible / contrainte. | — |
| 13 | SIS (secteurs d'info sols) | F+O+X+**C**+K — fiche `_sols_block` ; cascade `sol_pollue` (servi, L556-2) ; carte `sis` | — (complète) | Étude de sols obligatoire à l'achat. | — |
| 14 | CASIAS (anciens sites industriels) | F+O+X+**C**+K — fiche `_sols_block` ; cascade `sol_pollue` ; carte `casias` | — (complète) | Historique industriel = risque de dépollution. | — |
| 15 | Classement sonore (Cerema) | F+O(P&R)+X+**C**+K — P&R `servitudes.py` `bruit_route` ; cascade (servi) ; carte | — (complète) | Isolation acoustique imposée le long des axes. | — |
| 16 | SAR (Région/DEAL) | F(texte)+**C**(PASS/indication) — proxy, `a_faire` (couche officielle non diffusée) | — (**choix** : proxy non opposable, en attente Région ; sentinelle) | Vocation régionale (indicatif). | gros (source) |
| 17 | DVF Région | contrôle interne seul — échantillon de validation du filtre DVF (`ingestion/seed_sources.py`) | — (**choix** : jeu figé mi-2021, sert à valider les comptes, pas à servir) | (contrôle qualité, invisible client) | — |
| 18 | Potentiel foncier Région | **C**(`potentiel_foncier_region`, servi)+K — proxy comparé en permanence au filtre | — (**choix** : proxy indicatif d'îlot, jamais un zonage réglementaire) | Repère de densification par îlot. | — |
| 19 | Fibre (Arcep) | F+X — fiche bloc Réseaux (`app.py` `_fibre_block`) ; export `exports/blocs/reseaux.py` | — (complète) | Desserte FttH du bien (330 k immeubles, 97,5 %). | — |
| 20 | **Taux TFPB (REI DGFiP)** | **nulle part** — ingérée 24/24 (taux 29,55→68,40 %), aucun consommateur | **O(CO)** fiche commune (bloc coûts) + **X** Financier (charge annuelle) | La taxe foncière pèse sur le rendement — 24 communes prêtes. | **petit** |
| 21 | ACV/PVD/ORT (ANCT) | O(CO) — `fiche_commune.py` (condition Denormandie) | **X** Financier (éligibilité Denormandie chiffrée) | Dispositif d'aide fiscale selon la commune. | petit |
| 22 | Loyers (DHUP + OLL) | O(MA,CO)+X — `faisabilite/marche_commune.py` `ligne9_loyer` (OLL canonique) ; fiche commune ; export Marché | — (complète) | Loyer médian observé = sortie locative du bilan. | — |
| +a | Coût de construction (EPTB SDES) | O(FA)+X — calculette `faisabilite/bilan.py` ; export Financier | — (complète) | Coût/m² sourcé (remplace la constante). | — |
| +b | Recensement IRIS (INSEE RP2022) | F+O(CO)+X — fiche bloc Autour (`_iris_quartier_block`) ; fiche commune ; export `exports/blocs/autour.py` | — (complète) | Vacance, âge du bâti, ménages du quartier. | — |
| +c | DFI (filiation, DGFiP) | contrôle interne — rattachement des permis orphelins (moteur permis) | — (**choix** : source de plomberie, pas une surface client) | (985 permis rattachés — invisible client) | — |

## T8 — Les orphelines : oubli ou choix ?

- **Taux TFPB (REI DGFiP)** — 🔴 **OUBLI**. Ingérée proprement (24/24, colonnes tracées) mais **consommée
  nulle part**. C'est la seule source « servie » de SOURCES-1 qui n'atteint aucune surface client. La
  taxe foncière est un chiffre que tout investisseur/promoteur regarde. **Branchement le plus rentable.**
- **Zonage A/B/C (DHUP)** — 🟠 **oubli partiel**. Vit en fiche commune seule ; il commande pourtant les
  dispositifs (PLS/PLAI/Pinel/Denormandie) et le prix bailleur — utile en fiche parcelle et au Financier.
- **DPU / PEB / DPF / zones humides** — 🟠 **oubli de run**, pas de code : la donnée est servie live
  (fiche, Pièges et risques T5) mais le **verdict cascade** manque au run servi. Un rebuild (ou la bascule
  de `q_v13_sources1`) les fait entrer dans le scoring.
- **ENS / SUP** — 🟡 servies (P&R/cascade/carte) mais absentes des **exports** (et ENS du bloc dispositifs
  de la fiche) — petit reliquat d'affichage.
- **AZI/TRI, SAR, DVF Région, potentiel foncier Région, DFI** — ✅ **choix assumés** : doublon d'aléa déjà
  servi (AZI/TRI), proxy non opposable en attente Région (SAR, potentiel foncier), échantillon de contrôle
  (DVF Région), plomberie de rattachement (DFI). À laisser tels quels.
- **ZPPA** — ⛔ **absente** : source injoignable (Atlas), sentinelle posée. Rien à brancher tant qu'elle ne ré-ouvre pas.

## T9 — Les trois surfaces à couvrir, par valeur

1. **Fiche parcelle** (la plus regardée) : y faire descendre le **zonage A/B/C** de la commune ; y
   afficher **ENS** dans le bloc dispositifs (aujourd'hui seulement en Pièges et risques).
2. **Outils** : la **taxe foncière (TFPB)** en fiche commune (bloc coûts) ; DPU/PEB/DPF/zones humides
   basculent en verdict Faisabilité/Pièges dès que le run est rebâti.
3. **Exports** : **TFPB** et **Zonage A/B/C** au Financier (charge + éligibilité) ; **SUP/ENS** au bloc
   dispositifs du Dossier/Apporteur.

## T10 — Branchements proposés, classés par valeur (RIEN appliqué hors T5)

| Rang | Branchement proposé | Surfaces | Coût | Pourquoi en premier |
|------|---------------------|----------|------|---------------------|
| 1 | **Taxe foncière TFPB** → fiche commune + Financier | O(CO)+X | petit | Seule source ingérée jamais servie ; chiffre attendu de tout investisseur ; 24/24 prêtes. |
| 2 | **Rebuild / bascule** pour faire entrer DPU+PEB+DPF+zones humides dans le **scoring servi** | C | moyen (geste de run) | La donnée est déjà servie live (T5) ; seul le verdict cascade manque. |
| 3 | **Zonage A/B/C** → fiche parcelle + Financier (éligibilité dispositifs) | F+X | petit | Commande les aides fiscales et le prix bailleur. |
| 4 | **ENS + SUP** → bloc dispositifs des exports (et ENS en fiche) | F+X | petit | Reliquat d'affichage, complète des couches déjà servies ailleurs. |
| 5 | **ORT/Denormandie** chiffré au Financier | X | petit | Rend l'aide fiscale opérationnelle, pas seulement signalée. |

**Aucun de ces branchements n'est appliqué** (décision Vic, source par source). **Seul T5** (les kinds de
Pièges et risques) a été appliqué, car décidé au Lot 1.

## Tests / posture du Lot 2
Lecture seule : aucune modification de code dans ce lot (au-delà de T5, déjà committé au Lot 1). Le
mapping fichier:ligne a été établi par exploration du code + vérification en base réelle (liste des
`layer_name` du run servi). **Rien n'est mergé.**

