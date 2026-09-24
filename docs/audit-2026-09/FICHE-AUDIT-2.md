# FICHE-AUDIT-2 — La fiche parcelle : chaque ligne branchée, juste, rangée une seule fois

*Audit lecture seule — branche `audit/fiche-audit-2`, base main `2d3b7213` (main a avancé en cours d'audit : merge de `feat/faisabilite-clip` — la branche d'audit a été réalignée avant tout constat servi), 2026-09-24.*
*Témoins : BZ1065 `97411000BZ1065` (Saint-Denis Uh, bâti, PPR bleue) · nue en U `97411000AC0215` (Uvl 1 454 m²) · à cheval A/N `97402000AB1117` (Bras-Panon) · PM `97415000BI0007` (CBO Territoria, Saint-Paul) · copropriété `97411000BH0670` (Les Jacquiers, Saint-Denis, 120 lots).*
*Livrable jumeau : `reports/fiche-audit-2/LIGNES.csv` (une ligne par information affichée).*

---

## 🔴 §0 — Constat bloquant découvert en cours d'audit : la fiche renvoie 500 sur le main courant

Le commit `1a39a90b` (FAISABILITE-clip, 24/09 15:26, mergé dans main via `2d3b7213`) retire dans `_potentiel_transformation_block` l'appel `sdp_servie, _cause_zone = garde_sdp_residuelle(...)` **mais laisse la clé `"cause": _cause_zone`** à `app.py:5324`. Résultat : `NameError: name '_cause_zone' is not defined` pour **toute parcelle ayant une ligne `parcel_residuel`** → `GET /parcels/{idu}` = **500** (reproduit sur l'API 8385 de l'audit, les 5 témoins). Les tests listés au commit passent car aucun ne construit le bloc `potentiel_transformation` de bout en bout.

**Fix d'une ligne** (pour FICHE-FIX ou hotfix immédiat) : servir `"cause": None` (la garde est retirée, la cause-garde n'existe plus) ou retirer la clé et adapter le front (`TransformationBlock` lit `cause`).

*Pour poursuivre l'audit sans modifier le code, les payloads ont été générés avec une injection mémoire (`labuse.api.app._cause_zone = None`) dans le script d'extraction — aucun fichier du dépôt touché.*

## §1 — Les contradictions constatées par Vic sur BZ1065

### 1.1 Hauteur : « 3 m max » vs « 7 m faîtage · 4,5 m égout »

| Affichage | Valeur | Source réelle |
|---|---|---|
| En-tête Urbanisme | « 3 m max » | `Fiche.tsx:630-631` lit `fo.hauteur_m`, où `fo = cap?.fourchette` (`Fiche.tsx:609`) = la **fourchette du moteur de capacité** (`/parcels/{idu}/bilan`) |
| Potentiel « Gabarit R+0 (3 m) » | R+0 · 3 m | même fourchette (`niveaux`, `hauteur_m`) |
| Règlement Art. Uh.10 | 7 m faîtage · 4,5 m égout | feuilles **validées** du calibrage `config/plu_destinations/97411_saint_denis.yaml` (zones.Uh.regles.hauteur, p.73) |
| Gabarit réglementaire | 7 m | `resolve_zone` → hf_m = 7 (même calibrage) |

**D'où sort « 3 m » :** `engine.py:472-473` calcule `niveaux = int(he_m // etage_m)` = int(4,5 ÷ 3,0) = **1 niveau** (hypothèse île `etage_m: 3.0`, `config/hypotheses_ile.yaml:13`), puis `engine.py:649` : `hauteur_m = niveaux × etage_m = 3,0` — le commentaire du code dit lui-même « hauteur du gabarit (niveaux × hauteur d'étage), **pour l'extrusion 3D** ». C'est donc une **hypothèse de modélisation** (le gabarit que le moteur retient pour compter la SDP), pas une règle. Le calibrage Uh est **juste** (7 / 4,5 validés) ; seul l'étiquetage ment.

**Qui est juste :** le règlement (7 m faîtage · 4,5 m égout). **Quel écran corriger :** l'en-tête Urbanisme — afficher la règle (« 7 m faîtage » ou « 7 m / 4,5 m ») au lieu du gabarit modélisé, et dans Potentiel renommer « R+0 (3 m) » en « gabarit modélisé (hypothèse 3 m/niveau) ». Aucun changement moteur nécessaire.

### 1.2 Pente : 13,8° (en-tête) vs 17,4° (Exposition)

Deux calculs, deux périmètres :
- **13,8°** = `parcel_terrain.pente_moy_deg` (batch RGE ALTI 5 m, moyenne **sur l'emprise de la parcelle**) — recompte SQL : 13,8 ✓ (pente_max 31,1).
- **17,4°** = endpoint lazy `/parcels/{idu}/exposition` (`faisabilite/exposition.py`, `FENETRE_M = 200.0`) : fenêtre MNT de **200 m autour du centroïde**, moyenne vectorielle pondérée (gdaldem slope/aspect) — c'est la pente du **versant**, pas celle de la parcelle.

Les deux sont « RGE ALTI » d'où la confusion. **Corriger l'affichage** : dans le bloc Exposition, libeller « pente du versant (fenêtre 200 m) » — ou faire lire à l'Exposition la même `pente_moy_deg` et ne garder la fenêtre 200 m que pour l'orientation (l'azimut d'un versant a besoin du contexte, la pente affichée non).

### 1.3 Assainissement : badge « confirmée » vs « zonage NON COLLECTIF »

- Le badge en-tête Réseaux = **bande d'un score de probabilité 0-100** (`faisabilite/viabilisation.py` `compute_score`/`band`) : permis < 100 m + façade sur voie + bâti adjacent + pondération de zone PLU. **L'assainissement n'entre pas dans le score** — le zonage (`parcel_viabilisation.assainissement_zonage`) n'alimente que le texte qualitatif `cout_raccordement` (viabilisation.py:196-205).
- Le contexte de l'en-tête affiche pourtant « eau · assainissement · élec » (`reseaux.tsx:53`) sous un badge « confirmée » (`reseaux.tsx:48-49`).
- BZ1065 : zonage = **anc** (« Zone d'assainissement - moyen terme », recompte `spatial_layers kind='zonage_assainissement'` ✓) → le tiroir dit vrai.

**Le badge ment par étiquetage, pas par calcul.** Corriger l'en-tête : soit retirer « assainissement » du contexte (« desserte eau/élec présumée »), soit dégrader le badge quand `assainissement_zonage='anc'` (« confirmée · ANC »). Le score lui-même est honnête (disclaimer « PROBABILITÉ de viabilisation »), mais l'en-tête le résume au-delà de ce qu'il teste.

### 1.4 Appartement : 2 365 €/m² (34 ventes) vs 2 403 €/m² (43 ventes)

Deux moteurs **dans le même module** `faisabilite/bilan.py`, qui répondent à deux questions :

| | « Prix de sortie bâti secteur » | « Médiane par type · Appartement » |
|---|---|---|
| Fonction | `sector_price` (bilan.py:207) | `reference_locale` (bilan.py:295) via `/outils/mon-secteur` → `_ref_local` |
| Types | appartement + maison, **type prioritaire retenu** — pour BZ1065 le payload sert `type_prix: "appartement"` : même type que la ligne d'en face | Appartement **seul** |
| Filtres | surf ≥ 20 m², valeur > 20 000 €, nature vente, **dédoublonnage par mutation_id**, aberrants exclus, récence pondérée | `_BAROMETRE_RETENUE`, **trim 5 % des extrêmes**, PAS de dédoublonnage par mutation |
| Fenêtre | récence pondérée — fenêtre effective servie « ventes **2022–2025** » (payload BZ1065) | non bornée (2021→2025) ; « millésime » = année de la vente la plus récente (« 2025 ») |
| Rayon | adaptatif 500 → 1000 → 1500 m | même échelle de rayons (constantes partagées) |

Et il existe un **troisième** chiffre appartement dans la fiche : `dvf_secteur_medianes` (secteur cadastral `97411000BZ`, servi dans `dvf_parcelle.secteur` « médianes du secteur cadastral — indicateur secondaire ») = **2 381 €/m² · 54 ventes · 2021-2025** (recompte SQL ✓). Trois médianes appartement, trois échantillons.

ETUDIER-BIEN-2 n'a unifié **que le terrain nu** (commentaire `mon_secteur.py:24-33` : « UNE seule méthode terrain nu partout ») — le bâti garde deux chemins. 2 365 ≠ 2 403 est donc structurel : mêmes ventes, deux filtres. **Corriger** : partager `filtre_ventes` + le dédoublonnage mutation_id entre les deux, ou étiqueter les deux lignes par leur question (« prix de sortie (appart+maison, pondéré récence) » vs « médiane brute appartements »). Un lecteur ne peut pas deviner que « 1 000 m · 2025 » et « ≤ 1 000 m » ne sont pas le même échantillon.

### 1.5 Parc social 25 185 logements sous « (secteur) »

`rpls_commune` est à maille **commune** (`insee = left(idu,5)`, app.py:3958-3978) — recompte SQL : Saint-Denis, millésime RPLS 01/2025, 25 185 ✓. La donnée est juste ; c'est le **titre du bloc** (« Contexte socio-économique (secteur) », `MarcheSecteurBlock`) qui étend « secteur » à une ligne communale. À corriger côté front : sous-titre de maille par ligne (« carreau 200 m » pour Filosofi, « commune » pour RPLS), pas de déplacement nécessaire.

### 1.6 Bâti : « 10,3 m faîtage · 3,6 m égout · monopente 22° » — plausible ?

Base (`batiment_hauteur_lidar` BZ1065) : faîtage 10,3 · égout 3,6 · **hauteur BD TOPO 4,2 m** · **écart faîtage/BD TOPO 6,1 m** (colonne `ecart_faitage_bdtopo_m` déjà en base) · 648 cellules · méthode `dalle` · survol 14/09/2023. `toiture_lidar` : monopente 22,2°, part pentue 0,82, confiance 0,757.

Géométrie : Δh faîtage−égout = 6,7 m à 22,2° ⇒ portée horizontale ≈ 6,7 ÷ tan(22,2°) ≈ **16,6 m**. Une emprise de 193 m² (≈ 14 × 14 m) ne porte pas 16,6 m de rampant dans l'axe — c'est tout juste possible en diagonale, et surtout **BD TOPO donne 4,2 m de hauteur totale**. Un vrai faîtage à 10,3 m sur une maison BD TOPO 4,2 m est très improbable : la valeur p99 du MNS a vraisemblablement capté **de la végétation ou une structure voisine** dans la dalle. La base le sait (écart 6,1 m flaggé) mais la fiche affiche « 10,3 m au faîtage » en Sourcé sans avertissement.

**Corriger** : afficher le drapeau quand `ecart_faitage_bdtopo_m` dépasse un seuil (« mesure LiDAR incohérente avec BD TOPO (+6,1 m) — à vérifier ») et faire porter ce doute à la marge de surélévation (1.7).

### 1.7 Marge en hauteur −3,3 m

`surelevation_mesuree` teste les deux contraintes et retient la plus serrée : égout 4,5 − 3,6 = **+0,9 m** ; faîtage 7 − 10,3 = **−3,3 m** → −3,3. La formule est cohérente **avec la règle 7 m** — ce qui prouve une seconde fois que le « 3 m max » de l'en-tête n'est pas la règle utilisée par le même écran (sinon la marge serait −7,3 m). Mais si le faîtage 10,3 est une mesure polluée (1.6), la marge −3,3 est fausse avec lui : un bâti réel à ~4,2 m aurait +2,8 m de marge au faîtage. Les deux corrections (étiquette en-tête, drapeau LiDAR) se rejoignent ici.

### 1.8 « Ensoleillement très favorable… » dans le bloc Assainissement

La ligne appartient au bloc **Viabilisation** (back : `solaire_note`, `faisabilite/viabilisation_build.py:130-149`, volet PV du S3REnR — M75). Le front (`ViabilisationBlock.tsx`) rend dans l'ordre : faisceau de preuves → sous-bloc « Assainissement (zonage) » (l.72-79) → note S3REnR + **note solaire (l.97-101)**, sans titre de groupe entre les deux → la ligne solaire se lit comme la suite de l'assainissement. **Corriger le front** : remonter S3REnR + solaire AVANT le sous-bloc ANC, ou leur donner un `GroupLabel` « Électricité — réseau et solaire ». (La déplacer en §2 Terrain serait défendable, mais sa raison d'être est le couple « le réseau accepte-t-il l'injection × le soleil est-il bon » → elle reste en Réseaux, correctement titrée.)

### 1.9 « 7 parcelles À suivre dans cette section »

`_secteur_opportunites` (app.py:3705-3721) compte `tier IN ('brulante','chaude','priorite','a_suivre')` sur `parcel_p_score_v2` (section cadastrale) ; le front (`marche.tsx:257-258`) titre tout « **À suivre** ». Le libellé sous-évalue donc (il mélange les deux vocabulaires PALIERS-1 : legacy brûlante/chaude + v15 priorité/à suivre). À la bascule q_v15 (bande + Signal) : le compte devrait lire les seuls tiers servis (ou la bande `score_labuse`) et le libellé devenir « N parcelles Priorité ou À suivre ». Le clic, lui, est déjà cohérent (il pose le filtre sur les 4 tiers, marche.tsx:248).

## §2 — Ligne par ligne (voir LIGNES.csv)

Le détail vit dans `reports/fiche-audit-2/LIGNES.csv` (une ligne par information affichée : champ lu, table, badge, recompte BZ1065, verdict, doublons). Réponses aux points de vigilance du mandat :

- **L'en-tête lit-il les mêmes fonctions que les tiroirs ?** Surface, Zone, Pente, SDP : oui (mêmes champs, motif ChiffreDissous). **Deux exceptions** : la tuile Exposition porte en sous-titre une pente d'une autre fenêtre que la tuile Pente (§1.2) ; la tuile Risques compte les **lignes cascade du run servi** (`f.lines`, onglet risques, SOFT_FLAG/HARD_EXCLUDE) alors que le tiroir Risques affiche les **aléas live** (`servitudes.aleas_parcelle`) + ces mêmes lignes — deux sources pour un même compteur (cf. ci-dessous).
- **Le tiroir Risques lit-il `aleas_parcelle`/`contraintes_parcelle` (PR-2 lot C) ?** Oui — `_aleas_block` = `servitudes.aleas_parcelle(db, idu)` en direct `spatial_layers` (app.py:4510), même source que l'outil Pièges & risques.
- **La SDP restante 26 m² = `parcel_residuel` run 8 ?** Oui — recompte SQL : 26 m², vue `parcel_residuel` sur `residuel_runs.run_seq=8` (`post-plu8-clip-2shard`, is_served ✓), `served_manifest.json` aligné (residuel_run_seq 8 sur cette base).
- **Le tiroir Faisabilité (11 étapes) = moteur clippé ?** Oui sur cette base : `parcel_faisabilite(assiette_clippee=True)` par défaut (`faisabilite/db.py:296`), garde de lecture « dominante A/N → 0 » retirée des 3 lecteurs (`1a39a90b`) — AB1117 sert 81 m² clippés (vérifié par le commit, à confirmer au payload).
- **Les 2 vigilances de l'en-tête = tiroir Risques = Pièges & risques (4 pour BZ1065) ?** Payload vérifié : en-tête = **2** (lignes cascade `risques` + `sup`, SOFT_FLAG) ; tiroir = **1 aléa live** (PPR zone bleue, 100 % de la parcelle) + **1 vigilance hors aléas** (SUP) = 2, cohérent avec l'en-tête ; outil Pièges & risques = **4** (ANC + DPU + PPR + SUP, `/servitudes-invisibles` live ✓). L'écart 2 vs 4 n'est pas une contradiction de valeur mais de **périmètre** : l'outil compte les « contraintes dormantes », dont l'ANC (qui vit en §6 Réseaux) et le DPU (qui vit en §4 Dispositifs). À dire quelque part (le libellé de la porte pourrait annoncer « 4 contraintes »).
- **« X couches sans objet » : compte juste ?** Oui — BZ1065 : 12 lignes PASS repliées, compteur « 14 couches évaluées » = 2 vigilances + 12 sans objet + 0 inconnue (`risques.tsx:20-25`), exact par construction.
- **Mixité sociale (LLS)** : la fiche affiche « non renseigné » alors que la feuille YAML Uh `mixite` est **validée** (30 logements / 15 %, Art. Uh.2 p.71) — la donnée calibrée n'est pas branchée jusqu'à la ligne fiche (le moteur, lui, la détecte : étape « clause détectée — part non calibrée »). Écart à corriger côté branchement.

## §2bis — Témoins

| Témoin | idu | Rôle |
|---|---|---|
| BZ1065 | 97411000BZ1065 | Saint-Denis Uh, bâti, PPR bleue — les 16 captures de Vic |
| Nue en U | 97411000AC0215 | Saint-Denis Uvl, 1 454 m², taux d'emprise 0 |
| À cheval A/N | 97402000AB1117 | Bras-Panon, portion U — témoin de la divergence clip |
| Personne morale | 97415000BI0007 | CBO Territoria, Saint-Paul |
| Copropriété | 97411000BH0670 | Les Jacquiers, Saint-Denis, 120 lots |

## §3 — Ce qui manque (en base, absent de la fiche)

Base : `data_sources` = **116 sources actives** (121 avec retirées ; le « 92 » du mandat date d'avant les ajouts de l'été) · `spatial_layers` = **65 kinds**. Revue des attendus du mandat puis des manques trouvés en balayant les tables.

### Les attendus du mandat, vérifiés

| Donnée | En base | Dans la fiche | Verdict |
|---|---|---|---|
| Hauteur LiDAR **dans le calcul** de capacité | `batiment_hauteur_lidar` ✓ | Affichée (Bâti) et utilisée pour la **surélévation** (`surelevation_mesuree`) ; le **gabarit de capacité** (niveaux/SDP) vient de la seule règle PLU (`engine.py:456-482`), le LiDAR n'y entre pas | Partiel — choix défendable (la règle borne le droit, pas le bâti) ; à documenter, pas à corriger |
| ER / EBC / SUP déduits de l'assiette | couches ✓ | **Oui** : EBC soustraite de l'assiette (`faisabilite/db.py:87`), grèves certaines unionnées et clippées (db.py:205-250) ; lignes « EBC N m² » dans les étapes (`engine.py:385`) | Présent |
| Zonage d'assainissement SIG | `parcel_anc` + couche ✓ | **Oui** — bloc ANC 3 états (M88) | Présent |
| ZAE / ZAC | kind `zone_activite` (9 020 obj.) ; source 135 « Inventaires ZAE » **partenariat_requis** | **Absente** | Manque — à dire « statut partenariat » ; où : Urbanisme (dispositifs) ; utilité moyenne ; coût faible (intersection simple) |
| DPE du bâtiment (1 123 lignes) | `dpe_records` ✓ (recompte : 1 123) | **Oui** (`dpe_connu`, app.py:4535) — BZ1065 : 0 DPE rattaché (normal) | Présent |
| Consommation NAF | `commune_conso_enaf` ✓ | **Non** (servie à la fiche commune seulement) | Manque léger — maille commune : un **renvoi** vers la fiche commune suffit (règle du fait unique) |
| Loyers OLL | `oll_loyers` ✓ (133 lignes) | **Non** (Étude de zone l'a) | Manque — où : §8 Marché (« loyer médian commune, OLL ») ; utilité forte (rendement locatif) ; coût faible |
| Trafic RN | `trafic_rn` ✓ (692) | **Non** | Manque — où : §6 « Axes et nuisances » (trafic de l'axe le plus proche) ; utilité moyenne ; coût faible |
| Bruit (classement sonore, PEB) | `bruit_route` (1 004), `peb` (8) ✓ | **Oui** : PEB au tiroir Dispositifs ; classement sonore évalué au tiroir Risques (pointé depuis « Axes », app.py:4761) | Présent |
| Cartofriches | kind `friche` (372) ✓ | **Non** en fiche (sert le filtre `parcel_signaux_vie.signal='friche'` seulement, app.py:1484) | Manque — où : §2 Terrain (« parcelle à l'inventaire Cartofriches ») ; utilité forte (signal d'opportunité) ; coût faible |
| Dernière vente de LA parcelle | `v_parcel_dvf_last` ✓ | **Oui** (§1 Identité, DerniereVenteBlock) | Présent |
| Bande LABUSE + Signal | `score_labuse` ✓ | **Oui** (`analyse_labuse`, bande + contributions, Fiche.tsx:847-903) — l'ancien moteur (carte verdict ×N) coexiste encore (Fiche.tsx:909-1052) | Présent — mais **deux moteurs affichés** (cf. §4) |
| Les 3 éléments d'Étudier un bien | — | Écart secteur/commune (`ecart_commune`) ✓ · médiane par type ✓ · annonces Radar autour (1,5 km) ✓ | Présents |
| Acquisitions récentes PM voisines | `pm_proprietaires_millesimes` ✓ | **Non** — la fiche ne sert que l'historique PM de LA parcelle (`proprietaire_historique`) | Manque — où : §9 Quartier (« N parcelles acquises par des PM < 500 m depuis 2023 ») ; utilité forte (pression foncière) ; coût moyen (agrégat spatial) |

### Autres manques trouvés en balayant les tables

| Donnée | Table | Où la mettre | Utilité · coût |
|---|---|---|---|
| Arrêtés CatNat de la commune | `catnat_arretes` | §5 Risques (« N arrêtés CatNat inondation depuis 2000 ») | forte (assurabilité, mémoire du risque) · faible |
| Établissements SIRENE sur la parcelle | `sirene_etablissements` (géolocalisés) | §3 Bâti (« 2 établissements actifs domiciliés ici ») | moyenne (occupation réelle, bail commercial) · faible |
| OCS GE évolution (artificialisation dans le temps) | `ocsge_evolution` | §2 Terrain, sous la ligne OCS GE | faible · faible |
| Zonage ABC / PTZ de la commune | `commune_zonage_abc` | §7 Fiscalité (dispositifs) | moyenne (financement acquéreur) · faible |
| SRU — état commune (carence) | `commune_contexte_sru` | §7 Fiscalité ou renvoi fiche commune | moyenne (obligation LLS pression) · faible |
| PAU / permis dormants de la parcelle | `parcel_pau`, `pc_caducs` | §1 Identité — l'« Historique permis » de la parcelle existe mais la caducité PAU n'est pas mise en avant | déjà partiellement servi (historique_site) |

**Non-manques assumés** (données à maille outil, pas fiche) : `cadastre_historique` (outil Remonter le temps), radars/pige agrégés commune (fiche commune), BPE complet (Étude de zone ; la fiche sert le « au plus proche » dédoublonné).

## §4 — Rangement

### Ce qui est au bon endroit (vérifié dans le code, pas seulement déclaré)

- **Historique permis de LA parcelle** : bien relocalisé en §1 Identité (FICHE-RANGEMENT-2 Lot 1, `Fiche.tsx:1371`) ; §9 Quartier ne garde que le voisinage (`autour.tsx:123-124`). Le double signalé par l'inventaire automatique n'existe plus.
- **Dépôts Sitadel** : rapatriés en §9 Quartier (`autour.tsx:126`), plus dans Réseaux.
- **Taxe d'aménagement** : une seule porte, en §7 Fiscalité (FICHE-PORTES-1 : retirée de §8 Marché, `marche.tsx:240-242`).
- **Bruit** : bon exemple de la règle « un fait, une section » — le bloc Axes (§6) **pointe** vers le tiroir Risques pour le classement sonore au lieu de le dupliquer (app.py:4761, libellé « Le classement sonore, lui, est évalué au tiroir Risques »).
- **Tuiles d'en-tête** : le motif `ChiffreDissous` (la tuile se dissout dans sa section) fait des tuiles des résumés, pas des doublons — conforme à la règle du 03/09.

### Mal placé

1. **« Ensoleillement… » rendu sous l'assainissement** (§1.8) — remonter S3REnR+solaire avant le sous-bloc ANC ou les titrer.
2. **RPLS sous un titre « (secteur) »** (§1.5) — étiquette de maille par ligne.
3. **Deux moteurs d'analyse affichés** : la bande `analyse_labuse` (ANALYSE-1, `Fiche.tsx:847-903`) coexiste avec l'ancienne carte verdict + réglette ×N (`Fiche.tsx:909-1052`). Deux « verdicts » pour une parcelle, deux vocabulaires — à trancher à la bascule q_v15 (garder la bande, retirer ou replier l'ancienne carte).

### En double (fait présent deux fois, hors motif tuile/section)

1. **La pente dans l'en-tête lui-même** : tuile 3 « Pente » (13,8° — `parcel_terrain`) et tuile 4 « Exposition » en sous-titre (17,4° — fenêtre 200 m). Deux chiffres de pente côte à côte dans le même en-tête (§1.2) — c'est le vrai lieu de la contradiction.
2. **La hauteur** : quatre affichages (en-tête « 3 m max », §3 Bâti mesuré, §4 règlement 7/4,5, §10 gabarit réglementaire 7 m + marge) pour trois concepts (règle, mesure, gabarit modélisé). Chaque écran est individuellement défendable, mais rien ne dit au lecteur lequel est la règle (§1.1) — étiqueter les trois concepts.
3. **SDP restante** : tuile 6, §10a `ChiffreDissous`, jauge « % SDP consommée » (§4 micro), et re-servie dans le tableau FaisabiliteTab (11 étapes). Tuile+§10 = motif assumé ; la ligne de FaisabiliteTab devrait *renvoyer* (« = SDP restante, §Potentiel ») plutôt que réafficher un nombre qui pourrait dériver (deux lectures : `parcel_residuel` vs moteur au vol — cf. §2, divergence à cheval connue).

### Renvois manquants

- Conso ENAF / SRU / contexte commune : aucune ligne fiche ne renvoie à la **fiche commune** qui les porte (§3).
- La carte verdict ancienne ne renvoie pas à la bande Analyse (et réciproquement).

### Les portes de sortie — chacune ouvre-t-elle l'outil sur CETTE parcelle, avec fil de retour ?

Le fil de retour est inhérent au mécanisme : `setModule` préserve `selectedIdu`, fermer l'outil ramène la fiche (commentaire `Fiche.tsx:1739-1740`).

| Porte | Pré-remplissage | Verdict |
|---|---|---|
| Courrier SPF (§1 + barre) | `setCourrierPrefill(idu)` (Fiche.tsx:1363, 1736) | ✓ |
| Scan patrimoine (§1, PM) | `setM02Prefill(siren)` (1357) | ✓ |
| Annuaire PLU (§4) | `setPluPrefillF({insee, zone})` (1528) | ✓ (grain commune+zone, adapté) |
| Vérif procédure PLU (§4) | lit `selectedIdu` préservé (1532-1535) | ✓ implicite |
| Pièges et risques (§5) | `setModule('risques')` seul (`risques.tsx:167`) — mais l'outil lit `selectedIdu` (`blocB.tsx:36-38`) | ✓ implicite |
| Permis de la commune (§9) | `setCommune`+filtre commune (autour.tsx:120) | ✓ (outil communal par nature) |
| Marché commune (§8) · Comparer (`addToCompare(idu)`, marche.tsx:266) · Remonter le temps (prefill + flyTo, Fiche.tsx:1743) | | ✓ |
| Taxe d'aménagement (§7) · Faisabilité · Calculette · Assemblage · Gabarit (§10) | `setParcelPrefill(idu)` / `setCalcPrefill(idu)` (1593, 1686, 1689, 1692, GabaritLine.tsx:71) | ✓ |
| Densifier l'existant (§10) | `setCommune` + filtre (1663) | ✓ (outil communal par nature) |

**Aucune porte cassée.** Seule remarque : Pièges et risques et Vérif procédure reposent sur le pré-remplissage *implicite* (`selectedIdu`) là où les autres passent un prefill explicite — fragile si un jour l'outil s'ouvre hors fiche, mais correct aujourd'hui.

## §5 — Verdict

### Les contradictions du §1, tranchées

| # | Contradiction | Qui a raison | Écran à corriger |
|---|---|---|---|
| 1 | Hauteur 3 m vs 7/4,5 | Le règlement (7 m faîtage · 4,5 m égout) | **En-tête Urbanisme** (afficher la règle) + libellé « R+0 (3 m) » du Potentiel (« gabarit modélisé ») — convergent avec GABARIT-AUDIT-1 (« point n°1 ») |
| 2 | Pente 13,8° vs 17,4° | Les deux (emprise vs versant 200 m) | Bloc Exposition : libeller « pente du versant (200 m) » — ou servir la pente d'emprise partout |
| 3 | Réseaux « confirmée » vs ANC | Le tiroir (zonage ANC) | En-tête Réseaux : contexte/badge (le score ne teste pas l'assainissement) |
| 4 | Appartement 2 365 vs 2 403 (et 2 381) | Aucun n'est faux — trois filtres | §8 Marché : filtre bâti partagé ou étiquettes de question |
| 5 | Parc social 25 185 « (secteur) » | La donnée (commune) | Titre/maille du bloc MarcheSecteurBlock |
| 6 | Faîtage 10,3 m plausible ? | Douteux (BD TOPO 4,2, écart 6,1 flaggé en base) | §3 Bâti : drapeau d'écart LiDAR/BD TOPO |
| 7 | Marge −3,3 m | Cohérente avec la règle 7 m — donc l'en-tête « 3 m » est bien faux ; fausse si le faîtage 10,3 l'est | Suit #1 et #6 |
| 8 | Ensoleillement dans Assainissement | Ligne de Viabilisation (volet PV/S3REnR) | `ViabilisationBlock` : ordre/titre de groupe |
| 9 | « 7 parcelles À suivre » | Compte juste, libellé sous-évalué (4 tiers) | `marche.tsx` : « Priorité ou À suivre » ; à revoir à la bascule bande+Signal |

### Le compte des écarts du §2 (LIGNES.csv, 119 lignes)

**104 OK · 9 ECART · 5 ETIQUETTE · 1 A_VERIFIER.** Les 9 écarts : les deux pentes de l'en-tête (tuile Exposition ≠ tuile Pente) et son double en §2 Terrain ; « 3 m max » vs règle 7/4,5 (§1.1) ; hauteur LiDAR 10,3 affichée sans le drapeau d'écart BD TOPO 6,1 (§1.6) et la marge −3,3 qui en hérite (§1.7) ; mixité LLS « non renseigné » alors que la feuille Uh est validée — et la capacité sert **10 étapes au lieu de 11** sur BZ1065, la ligne mixité manquant faute de branchement ; les 3 médianes bâti non réconciliées (2 365/2 381/2 403 appartement, 3 747/3 494 maison — §1.4). Les 5 étiquettes : badge Réseaux « confirmée » (contexte + valeur), ensoleillement sous l'ANC, RPLS « (secteur) », « 7 À suivre ». L'A_VERIFIER : le repli « N sans objet » du tiroir Urbanisme (11 lignes PASS avant filtre front — l'écran n'a pas pu être rendu, fiche 500, cf. §0).

Vérifications positives à souligner : le **bilan** de la fiche lit le **même** `prix_dvf` (2 365 · 34) que le §8 Marché (une source ✓) ; l'écart secteur/commune (−7 %) et l'exposition (NO 301,3° · 17,4°) servent exactement ce que leurs moteurs calculent ; AB1117 à cheval sert 81 m² clippés = run servi = outil (divergence FAISABILITE-1 éteinte sur cette base).

### 5 recommandations pour un mandat FICHE-FIX (max)

0. **AVANT TOUT — hotfix du 500** (§0) : `"cause": None` à `app.py:5324` (une ligne). La fiche est morte sur main tant que ce n'est pas fait. (Hors décompte : c'est une réparation, pas un rangement.)
1. **Hauteur** — l'en-tête Urbanisme affiche la règle (`hf_m`/`he_m` de `resolve_zone`) au lieu de `fourchette.hauteur_m` ; « R+0 (3 m) » renommé « gabarit modélisé (3 m/niveau) ». Un concept par étiquette : règle / mesure / modèle. (Convergent GABARIT-AUDIT-1 n°1.)
2. **Réseaux honnête** — badge d'en-tête dégradé ou contextualisé quand `assainissement_zonage='anc'` ; note solaire et S3REnR sous leur propre titre, hors du sous-bloc ANC.
3. **Un seul filtre DVF bâti** — `sector_price` et `reference_locale` partagent dédoublonnage par mutation_id + fenêtre + trim (comme ETUDIER-BIEN-2 l'a fait pour le terrain nu) ; sous-titres portant la question (« prix de sortie » vs « médiane par type ») ; maille « commune » dite sur la ligne RPLS.
4. **Drapeau LiDAR** — quand `ecart_faitage_bdtopo_m` > seuil (ex. 3 m), la fiche l'affiche (« mesure incohérente avec BD TOPO — à vérifier ») et la marge de surélévation porte le doute ; brancher au passage la ligne **mixité LLS** sur la feuille validée du calibrage (30 log/15 %, affichée « non renseigné » à tort).
5. **Un seul verdict affiché** — à la bascule q_v15 : retirer/replier l'ancienne carte verdict au profit de la bande Analyse ; compteur de section « Priorité ou À suivre » ; la porte Pièges & risques annonce son compte (« 4 contraintes »).

---

## Note d'environnement (reproductibilité)

- Base occupée pendant l'audit par une requête psql tierce (pid 5903, scan PPR non clippé Saint-Denis+Saint-Paul, 17:12→17:56, ~44 min) : le DDL `ensure_schema` de tout démarrage d'app se met en file derrière elle et **gèle toutes les nouvelles lectures de `parcels`** (file AccessExclusive). Symptôme identique aux galères PIEGES-1/ETUDE-ZONE-1. Aucune session tierce tuée ; seules mes propres requêtes orphelines ont été annulées (`pg_cancel_backend`).
- main a avancé pendant l'audit (`7ed3211e` → `2d3b7213`, merge faisabilite-clip + GABARIT-AUDIT-1) : la branche d'audit a été réalignée sur `2d3b7213` avant tout constat servi ; tous les recomptes/payloads datent d'après le réalignement.
- Payloads des 5 témoins : appel direct `_q_v2_fiche` (session SQLAlchemy), **avec l'injection mémoire décrite en §0** (la fiche HTTP renvoie 500 sur cette base). Captures d'écran non réalisées pour la même raison : l'écran fiche est une page d'erreur sur ce main.
