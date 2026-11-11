# Taxe d'aménagement

Clé interne : `taxe-amenagement` (num K3) · composant : `frontend/src/components/outils/TaxeAmenagement.tsx` · endpoint(s) : `GET /outils/taxe-amenagement` (calcul), `GET /outils/taxe-amenagement/config` (barème), `GET /outils/taxe-amenagement/prefill?idu=…` (contexte parcelle).

---

## 1. À quoi il sert, et pour qui
Une calculette qui estime la taxe d'aménagement (et la redevance d'archéologie préventive) qu'un porteur de projet paiera au dépôt d'un permis, à partir d'une surface taxable qu'il saisit. Pour un promoteur / propriétaire qui veut chiffrer ce coût AVANT le permis, sur une parcelle donnée — l'outil lit le taux communal officiel de la parcelle et n'invente aucun chiffre.

## 2. Le parcours
Un seul chemin (pas d'onglets). Écran par écran :
1. **Choix de la parcelle** — `EntreeParcelle` : l'utilisateur saisit une adresse/IDU ou clique une parcelle sur la carte. Tant qu'aucune parcelle n'est désignée, le reste de l'outil est masqué (`TaxeAmenagement.tsx:173`, `223`, `270` : tout est gardé par `prefillIdu`).
2. **« Votre projet »** (`TaxeAmenagement.tsx:172-218`) — champ **surface taxable** (m², clavier numérique), bascule **Logement / Autre**, et si « Logement » deux cases : **Résidence principale** (abattement 50 % sur 100 m²) et **Logement social aidé**.
3. **« Options »** repliable (`:223-267`) — aménagements au forfait (stationnement ext., piscine, panneaux PV au sol, éoliennes) et **exonérations de plein droit** mutuellement exclusives (locaux agricoles, PLAI, reconstruction à l'identique).
4. **Résultat** (`:276-364`) — « Total à prévoir » en gros, puis l'assiette détaillée ligne par ligne, la part communale, la part départementale, la redevance d'archéologie (0,40 %), et une note (valeur forfaitaire + taux + lien source). Si le taux communal manque, aucun total n'est affiché : un message honnête le dit.

Le barème (valeurs forfaitaires, abattement, forfaits) vient de `/config` ; le taux communal vient du `/prefill` de la parcelle ; **aucun montant ni taux n'est écrit en dur dans le front** (commentaire `:16-19`).

## 3. Les données lues

| Donnée | Nom au catalogue | Table SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Taux communal (part communale %) + secteur à taux majoré | `Taxe d'aménagement — taux communaux (délibérations)` | `taxe_amenagement_taux` (par INSEE) et `taxe_amenagement_secteur` (par IDU) | `DGFiP DELTA — 24/24 communes en vigueur (08/09/2026)` ; en base : `delib_date=2022-01-01`, `maj_at=2026-09-25` | 2×/an (fin janvier + 2ᵉ quinzaine d'octobre), jeu DELTA `delta_deliberation_tam_17_01_23` |
| Contexte parcelle (commune, surface terrain, zone PLU, famille de zone, SDP résiduelle, déjà bâtie) | — (données internes) | `parcels`, `parcel_zone_plu`, vue `parcel_residuel` | run servi (M135) | — |
| Barème (valeur forfaitaire, abattement, forfaits, part départementale) | — (config datée, pas de table) | `config/taxe_amenagement.yaml` | `annee: 2026`, relevé `2026-08-28` (source service-public A15416) | mise à jour manuelle annuelle (indexation ICC INSEE) |

`data_sources` : la ligne `Taxe d'aménagement — taux communaux (délibérations)` est au statut `connecte` (colonne `source_cadence` vide en base).
Le code lit `taxe_amenagement_taux`/`taxe_amenagement_secteur` directement (SQL dans `taxe_amenagement.py:88-161`), **pas** `data_sources`.

## 4. Les calculs
Tout le calcul est dans `src/labuse/taxe_amenagement.py::calculer` (`:203-391`). Formules :

1. **Assiette surface** (`:254-285`)
   - petites surfaces : si `0 < surface ≤ 5 m²` → **0 €** (exonération plein droit CGI 1635 quater D-10°, borne inclusive ; `:256-263`, seuil `exoneration_surface_min_m2: 5` dans le YAML).
   - sinon `assiette = pleine × VF + abattue × VF × (1 − 50 %)` où `VF = 892 €/m²` (`:275`).
     - **Logement aidé** : toute la surface abattue à −50 % (`:267-269`).
     - **Résidence principale** : les 100 premiers m² **par logement** abattus à −50 %, soit `abattue = min(surface, 100 × nb_logements)` (`:272`). `nb_logements` non saisi → 1 logement appliqué + message d'invite (`:243-252`).
2. **Surface exonérée** (`:290-295`) : si un motif (agricole / plai / reconstruction) est posé, cette surface fait une ligne à **0 €** (distincte de l'abattement).
3. **Forfaits** (`:298-310`) : `qté × tarif` pour piscine, PV sol, stationnement ext., éoliennes.
4. **Parts** (`:314-330`) : `part_communale = assiette × taux_communal / 100` ; `part_departementale = assiette × taux_departemental / 100` ; `total = part_com + part_dep`. **Si le taux communal est inconnu, `part_communale=None` et `total=None`** (`:327-330`) — pas de total inventé.
5. **Redevance d'archéologie préventive** (`:334`) : `rap = assiette × 0,40 % / 100`, sur la MÊME assiette. Le front l'ajoute au « Total à prévoir » (`TaxeAmenagement.tsx:277-279`).

Arrondis : chaque euro arrondi à 2 décimales (`_eur`, `:169-170`).
Résolution du taux par parcelle : `taux_parcelle` (`:151-161`) prend le **secteur à taux majoré** s'il existe pour l'IDU, sinon le taux communal général.

**Constantes (toutes sourcées de la config YAML, pas en dur dans le code de calcul) :**

| Constante | Valeur | fichier:ligne | Origine |
|---|---|---|---|
| Valeur forfaitaire hors-IdF (974) | **892 €/m²** | `config/taxe_amenagement.yaml:21` | service-public A15416, millésime 2026 (CGI 1635 quater H) — barème légal daté |
| Abattement | **50 % sur 100 m²** | `taxe_amenagement.yaml:32-33` | CGI 1635 quater I — barème légal |
| Exonération petites surfaces | **≤ 5 m²** | `taxe_amenagement.yaml:26` | CGI 1635 quater D-10° |
| Piscine | **251 €/m²** | `taxe_amenagement.yaml:38` | CGI 1635 quater J, 2026 |
| PV au sol | **10 €/m²** | `taxe_amenagement.yaml:39` | idem |
| Éolienne (mât > 12 m) | **3 000 €/mât** | `taxe_amenagement.yaml:40` | idem |
| Stationnement ext. | **2 928 €/place** (jusqu'à 5 857 sur délibération) | `taxe_amenagement.yaml:41-42` | idem |
| Part départementale 974 | **2,5 %** (défaut servi, confirmé DELTA) | `taxe_amenagement.yaml:52-53` | confirmé par DGFiP/DELTA |
| Part communale défaut | **null** (aucun défaut) | `taxe_amenagement.yaml:50` | doctrine « aucun taux inventé » |
| Redevance archéologie | **0,40 %** | `taxe_amenagement.py:198` | **codée en dur** (CGI, gestion DGFiP ord. 2022-883) |
| Péremption du taux | **365 jours** | `taxe_amenagement.py:29` | codée en dur |

L'endpoint borne les saisies (422 hors bornes) : surface 0–1 000 000 m², taux communal 0–20 %, part départementale 0–2,5 % (`app.py:3693-3703`).

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| Surface taxable | saisie utilisateur | saisi |
| Valeur forfaitaire 892 €/m² | `config.yaml` (barème daté 2026) | sourcé (barème légal) |
| « dont N m² à −50 % » | calcul abattement RP/aidé | estimé (calculé) |
| Assiette imposable | `assiette_surf + forfaits` | estimé (calculé) |
| Part communale · taux % | `assiette × taux_communal` ; taux = `taxe_amenagement_taux`/`_secteur` (DELTA) | montant **estimé** / taux **sourcé** |
| Part départementale · 2,5 % | `assiette × 2,5 %` | montant estimé / taux sourcé (confirmé DELTA) |
| Taxe d'aménagement | `part_com + part_dep` | estimé |
| Redevance d'archéologie · 0,40 % | `assiette × 0,40 %` | estimé (taux en dur) |
| Total à prévoir | `total_eur + rap_eur` | estimé |
| Millésime du taux (« en vigueur depuis le 01/01/2022 ») | `delib_date` de la table | sourcé |
| « ⚠ taux non rafraîchi depuis plus d'un an » | `maj_at` vs 365 j | sourcé (dérivé) |

## 6. Les limites
- **La surface taxable n'est jamais déduite automatiquement du projet** : l'utilisateur doit la saisir. Le prefill propose la SDP résiduelle du gabarit comme repère (`app.py:3671-3676`), mais le front ne pré-remplit pas le champ surface avec (il remet `surface=null` à chaque changement de parcelle, `TaxeAmenagement.tsx:98`).
- **Exonérations facultatives** votées par la commune (abris ≤ 20 m², commerces < 400 m²… CGI 1635 quater E) : **jamais appliquées** (listées dans `non_couvert`, `taxe_amenagement.py:337-346`).
- **Non modélisés** : versement pour sous-densité (VSD), participations PVR/PFAC, secteurs majorés au-delà de ceux ingérés (`:344-345`).
- **Taux figés au 01/01/2022** : les délibérations en base datent toutes de 2022 ; une commune ayant revoté depuis ne serait reflétée qu'après réingestion DELTA. Le drapeau `perime` compare `maj_at` (relevé du 25/09/2026), pas `delib_date`.
- **Collectif** : sans `nb_logements` saisi, l'abattement RP est appliqué pour 1 seul logement — sous-estime la minoration d'un collectif (message d'invite affiché).
- **Part départementale servie par défaut même sans la saisir**, étiquetée « confirmée DELTA » mais la valeur vient du YAML, pas d'une table.

## 7. Les tests
- `tests/test_taxe_amenagement.py` : config datée/sourcée, **valeurs 2026 conformes** (892, 1011, 251, 10, 2928, 3000, abattement 50/100, seuil 5), abattement par logement collectif, pas de total sans taux communal, départemental confirmé.
- `tests/test_taxe_cas_reels.py` : 5 cas (maison simple, maison+piscine+stationnement, logement aidé, projet < 5 m², taux manquant).
- `tests/test_recette4_taxe.py` : 10 combinaisons (surface non-RP, RP 1/3 logements, aidé, piscine, stationnement, < 5 m², mixte, sans taux).
- `tests/regles/test_taxe_amenagement.py` : exonérations plein droit (agricole zone A, PLAI, reconstruction), programme mixte 3 PLAI/10, RAP 0,40 %, RAP suit l'exonération.
- `tests/test_taxe_amenagement_delta.py` : ingestion DELTA (remplit la table par INSEE, garde la délibération la plus récente, bornes, communes absentes signalées, millésime/fraîcheur, secteur majoré résolu par parcelle, export sans pagination).

**Ce qu'aucun test ne vérifie :** le composant front `TaxeAmenagement.tsx` — **aucun `*.test.tsx`** ne mentionne la taxe (grep vide). Rien ne teste le câblage prefill → affichage, ni le calcul du « Total à prévoir » (TA + RAP) côté front, ni le fait que le champ surface ne se pré-remplit pas.

## 8. Les documents liés (PDF, exports)
Le bloc fiche §7 et le Dossier PDF appellent le **MÊME** `calculer()` mais avec `surface_taxable_m2=0` (`app.py:5766-5774`). Conséquence : sur la fiche/le Dossier, **aucun montant en euros n'est imprimé** — seulement le taux communal, sa fraîcheur, et la part départementale (`:5775-5791`, `projet_saisi=False`, `total_eur=None`). Le PDF dit « sur quoi la taxe se calculera », l'outil chiffre un montant sur une surface saisie. Le montant chiffré sur une SDP de projet n'apparaît qu'au Financier (`exports.builder._financier_contexte`, cité en commentaire). Donc : **mêmes taux et même barème que l'écran, mais le PDF ne reprend pas le total de l'outil** (il n'en calcule aucun).

## 9. Trois cas rejoués (curl réels sur :7300)

**Témoin 1 — `97411000BZ1065` (Saint-Denis).** Prefill : `insee=97411, commune=Saint-Denis, surface_terrain=1567 m², zone Uh (famille U), sdp_gabarit=35 m², taux_communal=3,0 % (public, vigueur 01/01/2022, non périmé), secteur_majore=false`.
Calcul (`surface=35, residence_principale=true, idu=…`) → assiette `35 × 892 €/m²` dont 35 m² à −50 % (1 logement) = **15 610 €** ; part communale 3,0 % = **468,30 €** ; part départementale 2,5 % = **390,25 €** ; **total TA = 858,55 €** ; RAP 0,40 % = **62,44 €** → total à prévoir ≈ **920,99 €**. Message d'invite collectif présent.

**Témoin 2 — `97409000AK0804` (Saint-André).** Prefill : `insee=97409, surface_terrain=27862 m², zone UB, sdp_gabarit=35086 m², taux_communal=5,0 %`.
Calcul (`surface=120, residence_principale=true, piscine_m2=30, idu=…`) → surface `120 × 892` dont 100 m² à −50 % = **62 440 €** + piscine `30 × 251` = **7 530 €** → assiette **69 970 €** ; part communale 5,0 % = **3 498,50 €** ; part départementale = **1 749,25 €** ; **total TA = 5 247,75 €** ; RAP = **279,88 €**.

**Témoin 3 — `97415000DH0076` (Saint-Paul, PAS Saint-Pierre — témoin adapté : l'IDU du brief résout en réalité à Saint-Paul, zone U2b).** Prefill : `insee=97415, surface_terrain=19513 m², sdp_gabarit=null, taux_communal=5,0 %`.
Calcul (`surface=200`, non résidentiel, `idu=…`) → assiette `200 × 892` = **178 400 €** ; part communale 5,0 % = **8 920 €** ; part départementale = **4 460 €** ; **total TA = 13 380 €** ; RAP = **713,60 €**. Aucun abattement (non-RP).

Aucun des 3 IDU n'est dans un secteur à taux majoré (table `taxe_amenagement_secteur` = 10 465 lignes, 0 pour ces IDU).

## 10. Tes doutes (gravité décroissante)
1. **Taux figés 2022, péremption aveugle à la délibération.** Tous les taux en base ont `delib_date=2022-01-01` et `maj_at=2026-09-25`. Le drapeau `perime` ne regarde que `maj_at` (notre relevé) : un taux réellement revoté en 2024 mais non réingéré ne serait jamais signalé. Risque de servir un taux périmé en le présentant comme « en vigueur ».
2. **Le témoin du brief est faux.** `97415000DH0076` résout en Saint-Paul (zone U2b), pas Saint-Pierre/Joseph ; son taux communal est 5,0 %, pas celui attendu. À vérifier côté données cadastrales si c'est l'IDU ou le brief qui se trompe.
3. **Zéro test front.** Le câblage prefill→écran et le calcul du « Total à prévoir » (TA + RAP) côté React ne sont couverts par aucun test ; une régression d'affichage passerait inaperçue.
4. **Part départementale servie par défaut sans saisie.** Elle est toujours ajoutée (2,5 %) et étiquetée « confirmée DELTA », mais la valeur vient du YAML en dur, pas d'une table ; si le département la modifiait, rien ne le détecterait automatiquement.
5. **Le prefill propose une SDP résiduelle que le front n'utilise pas** pour pré-remplir la surface : travail de saisie manuel redondant, et risque que l'utilisateur confonde SDP résiduelle et surface taxable (qui inclut garages/annexes, ≠ SDP, dit le tooltip).
