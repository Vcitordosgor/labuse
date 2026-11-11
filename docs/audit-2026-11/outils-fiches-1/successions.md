# Successions à venir

Clé interne : `successions` (num M28) · composant : `frontend/src/components/outils/Successions.tsx` · endpoint(s) : `GET /modules/successions`

> Audit en lecture seule. Chemins relatifs à `/Users/openclaw/Desktop/labuse-fiches`, numéros de ligne réellement ouverts. Sorties rejouées sur le backend local `http://127.0.0.1:7300` (06/10/2026 du snapshot) et sur la base Postgres `labuse`.

---

## 1. À quoi il sert, et pour qui

Un **radar patrimonial** : il liste les parcelles dont le propriétaire est une **personne morale** (SCI, société civile ou agricole, SARL familiale…) qui *approche* une transmission — soit son dirigeant le plus âgé a ≥ 70 ans, soit c'est une SCI « dormante » (vieille et sans activité récente au registre). Il s'adresse à un prospecteur foncier qui veut repérer, en amont, du foncier susceptible de bouger dans 3 à 7 ans — **jamais** une succession déjà ouverte (aucun décès ni acte n'est constaté).

## 2. Le parcours

Écran unique, dans le panneau « Outils » :

1. L'utilisateur choisit un **périmètre** : « Toute l'île » par défaut, ou une commune, via le sélecteur `CommuneScope` (`Successions.tsx:58`). C'est la seule saisie.
2. Il obtient un **bandeau** « N parcelles · signal **RNE INPI** — [commune / toute l'île] » (`Successions.tsx:81-85`), puis une **liste de cartes** paginées (200 par page, `SUCCESSIONS_PAGE`, `api.ts:1342`), triées par **SDP résiduelle estimée décroissante**.
3. Chaque carte montre : IDU · surface résiduelle estimée (badge ambre « Estimé », `Successions.tsx:110-111`) · commune · surface · zone PLU · **dénomination + SIREN** de la société · **motif** (« SCI dormante », ou « Nom du dirigeant · N ans », éventuellement « aucun dépôt de comptes depuis N ans »).
4. Un clic sur une carte **zoome et ouvre la fiche de la parcelle** (`focusParcelle`, `Successions.tsx:89`). Si une commune est choisie, un lien vert « Réinitialiser les filtres » revient à toute l'île (`Successions.tsx:61-66`).

Ce que l'outil **ne fait pas** (volontairement, cf. en-tête `Successions.tsx:1-13`) : aucune date de succession par parcelle, aucun badge de score, aucun export, aucune case de sélection, aucun pont « courriers » (tous retirés en OUTILS-S2). Aucun calcul métier au front : `/modules/successions` sert tout.

## 3. Les données lues

Le signal est un **snapshot figé** : il n'est pas recalculé à la volée. La table `parcel_veille_succession` est reconstruite par le batch `score-v-compute` (`score_v.py:595-606`). L'outil ne fait que lire ce snapshot et l'habiller.

| Source (catalogue `data_sources.name`) | Table SQL réellement lue | Rôle dans l'outil | Millésime servi (rejoué) | Cadence |
|---|---|---|---|---|
| INPI RNE (dirigeants) | `pm_dirigeants` (via la vue `v_pm_propension_vendre`) | Âge de l'aîné des dirigeants → signal « dirigeant ≥ 70 ans » ; dates de création / mise à jour RNE → « SCI dormante » | ingéré **05/07/2026** (`max(pm_dirigeants.ingested_at)`, servi au bandeau `rne_sync`) ; catalogue `last_sync_at` = 06/07/2026 | (non renseignée au catalogue) |
| DGFiP — parcelles des personnes morales | `parcelle_personne_morale` (alias `pm`) | Lien parcelle→SIREN, dénomination, **forme juridique** (filtre de forme) | Panel 2019→2025 (situation 1ᵉʳ janvier) ; `last_sync_at` 12/07/2026 | annuelle |
| Recherche d'entreprises (DINUM) | (consommée en amont par le batch Score V, pas relue à l'endpoint) | Fallback âge / nature juridique / date de création lors du build du snapshot | Sirene INSEE / RNE INPI courant | — |
| BODACC (procédures collectives) | `bodacc_depots` | Signal « aucun dépôt de comptes depuis N ans » (renforce « sommeil ») | `last_sync_at` 14/09/2026 | — |
| (moteur de la fiche, pas une source catalogue) | `p_model_ext_dataset` (alias `d`) | **SDP résiduelle estimée** affichée + tri | `max(annee)` du feature store | — |
| (cadastre) | `parcels` (alias `p`) | Commune, surface | — | — |
| (PLU) | `parcel_zone_plu` (alias `z`) | Zone (`zone_lib` sinon `zone_fam`) | — | — |

**Point d'attention — DFI non utilisée.** Le briefing cite « DFI — documents de filiation informatisés (DGFiP) » comme indice d'âge/transmission. Un `grep` sur `src/labuse/scoring/` et `modules.py` ne trouve **aucune** référence à DFI/filiation dans le chemin de cet outil : l'âge vient **exclusivement du RNE INPI** (dates de naissance des dirigeants), pas de la filiation des propriétaires physiques. L'outil ne regarde donc **que** les propriétaires **personnes morales** ; un terrain détenu par un particulier âgé n'y figure jamais.

## 4. Les calculs

Tout le « calcul » métier est **au build du snapshot** (`score_v.py`), pas à l'endpoint. L'endpoint ne fait que filtrer, joindre et habiller.

### 4.1 Éligibilité d'une parcelle au signal (`veille_succession_eligible`, `score_v.py:371-387`)

Une parcelle est taguée si, et seulement si :

```
owner_type == "pm"  ET  confiance == 1.0 (SIREN confirmé en direct, jamais un match par nom)
ET ( SCI dormante  OU  (dirigeant ≥ 70 ans ET forme ∈ formes retenues) )
```

- **Confiance SIREN = 1,0** (`CONF_SIREN_DIRECT = 1.0`, `score_v_constants.py:223`) : le lien parcelle→société doit être **certain** (jamais un rapprochement par dénomination approximative). Origine : codée en dur, doctrine « jamais de faux propriétaire ».
- **Seuil d'âge = 70 ans** (`VEILLE_SUCCESSION_AGE_MIN = 70`, `score_v_constants.py:172`). L'âge retenu est celui de **l'aîné** des dirigeants personnes physiques (`_load_dirigeant_ages`, `score_v.py:104-109`), lu dans la vue `v_pm_propension_vendre.age_max_dirigeant`. Origine : délibération interne (radar 3-7 ans). **Sourcé** (date de naissance RNE) → **estimé** (seuil choisi).
- **Formes retenues** pour le signal « dirigeant âgé » (`VEILLE_SUCCESSION_FORMES`, `score_v_constants.py:183-192`) : `SCI, SC, SCEA, EARL, GFA, SCM, SARL, SNC`. **Exclues** : SA, SAS, SEM, SCA, GIE, association, autre PM — « une société de capitaux ne succède pas quand son président vieillit ». Comparaison **EXACTE** du libellé DGFiP `forme_juridique` (jamais une sous-chaîne). Origine : décision Vic 2026-09-25, codée en dur. Ce filtre est appliqué **au service** (`modules.py:1158`), donc sur le snapshot courant **en plus** du build.
- **SCI dormante** (`score_v.py:326-342`) : la société est une SCI (forme DGFiP contient « SCI » **ou** nature juridique = `6540`) ET créée il y a ≥ **20 ans** (`SCI_DORMANTE_AGE_ANS = 20`, `score_v_constants.py:219`) ET sans mise à jour RNE depuis ≥ **5 ans** (ou date de MAJ inconnue) (`SCI_DORMANTE_INACTIVITE_ANS = 5`, `score_v_constants.py:220`). Une SCI dormante est éligible **quel que soit l'âge du dirigeant**.

### 4.2 Âge du dirigeant servi (vue `v_pm_propension_vendre`, `models.py:1820-1854`)

L'âge = plancher en années depuis `date_naissance` (format `YYYY-MM`, jour inconnu → 1er du mois), **maximum** sur les dirigeants `INDIVIDU` du SIREN (depth-0), avec fallback sur les dirigeants du gérant-société (gigogne, depth-1). Un **garde-fou de bornes [18 ; 110]** (`models.py:1827-1834`) exclut les dates aberrantes (1909/1911 ou futures) qui donnaient des âges 114/117. **Attention : ce garde-fou a été ajouté APRÈS le dernier build du snapshot servi** — voir rubriques 6 et 10.

### 4.3 Dépôt de comptes « muet » (`_depots_par_siren`, `modules.py:254-282`)

Pour chaque SIREN de la page, `bodacc_depots` donne l'année du dernier exercice clôturé et `depuis_ans` = années depuis la dernière **parution**. Le flag `muet = (depuis_ans ≥ 3)` (`SEUIL_DEPOT_MUET_ANS = 3`, `modules.py:251`). Origine : seuil codé en dur (DONNEES-1 lot 2.3). C'est un renfort de motif, **pas** un critère d'éligibilité.

### 4.4 SDP résiduelle et tri

`sdp_residuelle_m2 = round(p_model_ext_dataset.sdp_residuelle_m2)` de l'année courante du feature store (`modules.py:1151`), **Estimé** (enveloppe du moteur de la fiche). Tri `sdp_residuelle_m2 DESC NULLS LAST` (`modules.py:1152`). Sans feature store, SDP servie `NULL` (jamais un 0 fabriqué). Un `sdp_min` optionnel exclut les SDP inconnues (une SDP inconnue « ne peut pas prouver » le seuil, `modules.py:1159-1162`) — mais le front ne l'expose plus (filtre retiré, `Successions.tsx:55-56`).

### 4.5 Mémoïsation

Réponse mise en cache par clé de fraîcheur `empreinte|vs=max(computed_at)|rne=last_sync_at|params` (`modules.py:1115-1122`) : elle ne bouge qu'au recalcul Score V. 8,7 s à froid (coût = jointure île→`parcels`, `modules.py:1107-1111`).

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| « N parcelles » (bandeau) | `total` = `count(*)` du snapshot filtré (`modules.py:1171`) | Sourcé (comptage) |
| « signal RNE INPI » | libellé codé en dur au front (`Successions.tsx:84`) ; la vraie source back est « RNE INPI · Recherche d'entreprises · DGFiP » | — (étiquette) |
| IDU | `v.parcelle_id` → `parcel_veille_succession` | Sourcé (cadastre) |
| surface résiduelle « … m² » + badge **Estimé** | `p_model_ext_dataset.sdp_residuelle_m2` arrondi | **Estimé** (moteur fiche) |
| commune | `parcels.commune` | Sourcé (cadastre) |
| surface « … m² » | `round(parcels.surface_m2)` | Sourcé (cadastre) |
| zone PLU | `parcel_zone_plu.zone_lib`/`zone_fam` | Sourcé (PLU) |
| dénomination · SIREN | `parcelle_personne_morale.denomination` / `.siren` | Sourcé (DGFiP) |
| « Nom · N ans » | `dirigeant_age` (snapshot) + nom de l'aîné (sous-requête `pm_dirigeants`, `modules.py:1180-1184`) | **Sourcé** (date naissance RNE) ; le choix « ≥ 70 » est estimé |
| « SCI dormante » | `v.sci_dormante` (snapshot) | Estimé (règle 20 ans + 5 ans) |
| « aucun dépôt de comptes depuis N ans » | `depot_comptes.depuis_ans` + flag `muet` (≥ 3) | Sourcé (BODACC) ; seuil estimé |

L'horizon « 3-7 ans » n'est **pas** affiché par parcelle : il vit dans l'`avertissement` (`modules.py:1220-1222`) et le « i » de l'en-tête.

## 6. Les limites

- **Personnes morales uniquement.** Un particulier âgé propriétaire d'un terrain n'apparaît **jamais** (pas d'identité SIREN stable). L'outil ne couvre donc **pas** la majeure partie du foncier détenu par des personnes physiques.
- **Snapshot figé.** La liste ne bouge qu'au prochain `score-v-compute`. Toute donnée amont fraîche (nouveau dirigeant, décès déclaré, dépôt de comptes) n'est **pas** reflétée tant que le batch n'a pas tourné (dernier : **06/10/2026**).
- **Centenaires fantômes (false positive réel, voir §10).** Le garde-fou d'âge [18 ; 110] (`models.py:1827-1834`) a été ajouté *après* le snapshot servi : **103 parcelles** portent un `dirigeant_age ≥ 100` (jusqu'à **114 ans**), alors que la vue corrigée en renvoie désormais **0**. Ces âges aberrants (dates INPI 1909/1911) sont de **faux signaux** servis à l'écran aujourd'hui.
- **Filtre de forme au service, pas au build.** Le snapshot peut contenir des SA/SAS taguées (antérieures à la doctrine des formes du 25/09) ; elles sont écartées **à l'affichage** (`modules.py:1158`), donc `total` ≠ nombre de lignes réellement dans la table. Correct à l'écran, mais le compte brut en base surévalue.
- **« SCI dormante » ≠ inactivité réelle.** Une SCI peut gérer un patrimoine actif sans jamais mettre à jour son RNE ni déposer de comptes : « dormante au registre » n'est pas « dormante dans les faits ».
- **Risque éthique.** L'outil désigne nominativement une société et son dirigeant (nom + âge + SIREN) comme cible de prospection sur la base d'une **probabilité** de décès/transmission. Le code multiplie les garde-fous de langage (« probable », « jamais en succession », pas de date), mais la donnée affichée reste un **profilage patrimonial de personnes identifiées** — le faux positif (SCI active, âge erroné) a un coût réputationnel direct.

## 7. Les tests

- `tests/test_outils_muscler1.py:40-95` — endpoint : la liste sert bien des PM nommées, écarte la SA par le filtre de forme (`test_successions_liste`, 3 tags → 2 servis, l'assert vérifie `SUCC0003`/SA absent), sert le millésime même à 0 ligne (`test_successions_commune_vide_honnete`), et le `sdp_min` exclut les SDP inconnues (`test_successions_sdp_min_exclut_les_inconnues`). Vérifie aussi l'absence de tout badge de score (`"tier_v2" not in it`) et le mot « probable » dans l'avertissement.
- `tests/test_score_v13.py:59-93` — règle d'éligibilité pure : SCI dormante éligible quel que soit l'âge ; dirigeant 70 éligible / 69 non ; forme restreinte (SCI/SARL/… oui, SA/SCA non) ; `pp`/`public`/`bailleur` jamais éligibles ; `CONF_DENOMINATION`/`None` jamais éligibles.
- `tests/test_chasse_fix3.py`, `tests/test_fraicheur_fix1_inpi.py` — touchent la version de règle et la date RNE servie.

**Ce qu'aucun test ne vérifie :**
- Qu'aucune valeur d'âge **aberrante** (> 110) ne sorte de l'endpoint sur un snapshot réel — le test construit ses propres âges (82, 88) ; le garde-fou [18;110] n'est **pas** rejoué contre le snapshot servi.
- Le composant front `Successions.tsx` n'a **aucun** test (`*.test.tsx`) : ni le motif, ni le badge Estimé, ni l'état vide ne sont couverts côté UI.
- Aucun test ne prouve que le `total` affiché (après filtre de forme) correspond au contenu réel de la table.

## 8. Les documents liés (PDF, exports)

**Aucun.** L'en-tête du composant le dit explicitement : « aucun export » (`Successions.tsx:7-8`), et le pont « Préparer les courriers » a été **retiré** (OUTILS-S2, `Successions.tsx:9-12`). L'outil ne produit ni PDF ni fichier ; la seule « sortie » est le clic qui ouvre la fiche de la parcelle (dont le dossier PDF est un autre outil, hors périmètre). Il n'y a donc pas d'écart possible écran/PDF à documenter ici.

## 9. Trois cas rejoués

Les 3 parcelles témoins du briefing (`97411000BZ1065`, `97409000AK0804`, `97415000DH0076`) sont **absentes** de cet outil :

```
psql> SELECT parcelle_id … FROM parcel_veille_succession
      WHERE parcelle_id IN ('97411000BZ1065','97409000AK0804','97415000DH0076');
(0 ligne)
```

C'est **attendu et cohérent** : l'outil ne liste que des parcelles détenues par une personne morale à SIREN confirmé ∧ signal succession ; ces trois témoins ne remplissent pas ce critère (propriétaire non-PM ou sans signal). J'ai donc **adapté** les témoins à un cas réel par commune (filtre `commune=`), ci-dessous.

**Cas A — Saint-Denis (`97411000BL0098`).** `curl /modules/successions?commune=Saint-Denis` : total **969**, 1ʳᵉ carte `97411000BL0098`, zone **Ua**, surface 19 588 m², SDP résiduelle estimée 16 579 m². Propriétaire **SCI C H A R** (SIREN 379193493), motif « **ABDOUL HACK CADJEE · 79 ans** », `sci_dormante=false`, `depot_comptes=null` (aucun dépôt BODACC). → signal « dirigeant âgé », forme SCI retenue.

**Cas B — Saint-Louis (`97414000EN1148`, tête de liste île entière).** total île **6 256**. Zone 1AUb2, surface 17 887 m², SDP résiduelle 21 660 m². Propriétaire **LE BOIS DE NEFLES** (SIREN 490146321), motif « **HENRI SERGE LAW-WAI · 72 ans** », dépôt de comptes 2024 (`depuis_ans=0`, `muet=false`). → dirigeant âgé, société à jour de ses dépôts (le radar reste posé sur l'âge seul).

**Cas C — Saint-Joseph (`97412000BW1342`).** total **248**, 1ʳᵉ carte `97412000BW1342`, dirigeant **70 ans**, société **LES JACQUES - SJO**. → cas limite exactement au seuil (70 = éligible, 69 ne le serait pas).

Agrégats base (rejoués) : `count(*)=6256`, `sci_dormante=7` seulement, `dirigeant_age` non nul = 6249, âge min **70**, âge max **114**, `max(computed_at)=2026-10-06`. Le signal est donc écrasé par le motif « dirigeant âgé » (99,9 %) ; « SCI dormante » ne pèse que 7 parcelles.

## 10. Tes doutes (du plus grave au moins grave)

1. **(Grave) Des âges impossibles sont servis comme signal de succession.** 103 parcelles portent `dirigeant_age ≥ 100` (jusqu'à **114 ans**) dans le snapshot servi, parce que le garde-fou [18 ; 110] (`models.py:1827-1834`) est postérieur au dernier build. La vue corrigée renvoie aujourd'hui 0 âge > 110 — mais l'endpoint lit la table figée, pas la vue. Ce sont des **faux positifs nominatifs** affichés en production jusqu'au prochain `score-v-compute`. C'est le défaut le plus préjudiciable (éthique + exactitude).

2. **(Grave) Fraîcheur du radar vs. réalité.** Le signal est un snapshot du **06/10/2026** sur un RNE ingéré le **05/07/2026**. Un dirigeant qui est décédé, a vendu ou a renouvelé sa direction depuis n'est pas reflété. Pour un outil dont toute la promesse est l'anticipation d'un événement de vie, la latence (potentiellement plusieurs mois) n'est **ni affichée par parcelle, ni testée**.

3. **(Moyen) La frontière « sourcé / estimé » est ténue mais réelle.** L'âge et la dénomination sont sourcés (RNE, DGFiP) ; mais le verdict « succession probable » est une **inférence** (seuil 70, formes retenues, 20+5 ans pour la SCI) — tous codés en dur, non calibrés par un backtest visible dans le code lu. Le mot « probable » protège le langage, mais aucune probabilité chiffrée ne justifie le « 3-7 ans ».

4. **(Moyen) `total` affiché ≠ contenu de la table.** Le filtre de forme (SA/SAS exclues) s'applique au service ; le compte brut en base est supérieur. Correct à l'écran, mais aucun test ne garantit la cohérence, et un changement de forme dans `VEILLE_SUCCESSION_FORMES` modifie silencieusement les chiffres sans rebuild.

5. **(Mineur) Zéro couverture UI.** `Successions.tsx` n'a aucun test : le badge « Estimé », le motif multi-lignes et l'état vide honnête reposent uniquement sur la relecture du code. Une régression de rendu passerait inaperçue.

---

## Synthèse INDEX (~12 lignes)

- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/successions.md`.
- Outil `successions` (M28) : radar patrimonial, liste des parcelles de **personnes morales** (SCI/sociétés familiales) à **dirigeant ≥ 70 ans OU SCI dormante (20 ans + 5 ans sans MAJ RNE)**, SIREN confirmé (conf 1,0). Endpoint `GET /modules/successions`, snapshot figé `parcel_veille_succession` (reconstruit par `score-v-compute`).
- Données principales : **RNE INPI (dirigeants)** via `pm_dirigeants`/`v_pm_propension_vendre` (ingéré 05/07/2026) pour l'âge ; **DGFiP personnes morales** (`parcelle_personne_morale`) pour SIREN/dénomination/forme ; **BODACC** (`bodacc_depots`) pour « dépôt muet ≥ 3 ans » ; SDP résiduelle **estimée** via `p_model_ext_dataset`. Snapshot servi daté du **06/10/2026** (total île **6 256**).
- **DFI (documents de filiation) N'EST PAS utilisée** par cet outil (contrairement au briefing) : l'âge vient uniquement du RNE, et seuls les propriétaires PM sont couverts.
- Part sourcé/estimé : identité et âge du dirigeant = **sourcés** (RNE/DGFiP) ; le verdict « succession probable », les seuils (70 ans, 20/5 ans, dépôt ≥ 3 ans) et la SDP = **estimés/barème interne**. ~60 % sourcé / 40 % estimé.
- Témoins du briefing absents (non-PM) → adaptés par commune : Saint-Denis `97411000BL0098` (SCI C H A R, dirigeant 79 ans), Saint-Louis `97414000EN1148` (tête de liste), Saint-Joseph `97412000BW1342` (dirigeant 70 = seuil exact).
- **Doute le plus grave** : le snapshot servi contient **103 parcelles à dirigeant_age ≥ 100 ans (jusqu'à 114)** — faux positifs nominatifs, car le garde-fou d'âge [18;110] est postérieur au dernier build ; la vue corrigée renvoie désormais 0 tel cas, mais l'endpoint lit la table figée. Risque éthique + exactitude, visible en production jusqu'au prochain recalcul Score V.
