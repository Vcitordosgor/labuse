# Audit du stationnement dans l'Étude de faisabilité — ETUDE-STATIONNEMENT-AUDIT-1

**Branche** `audit/etude-stationnement-1` · worktree `~/Desktop/labuse-stationnement` · **lecture seule, aucun run, aucune prod.**
Le livrable est ce rapport. Aucun code n'a été modifié.

## Cadre et limites de lecture

Ce que LABUSE **sert hors-ligne** (ce que j'ai pu lire sans lancer l'application) :
- les **barèmes ingérés** par commune/zone dans `config/plu_destinations/<insee>_*.yaml` (feuille `regles.stationnement`), avec leur `article`, `page_pdf`, `citation`, `statut` ;
- le **code** du moteur d'implantation qui lit et applique ces barèmes.

Ce que LABUSE **ne sert pas hors-ligne** : le **texte verbatim intégral** du règlement PLU. Il vit dans une table PostgreSQL (`plu_reglement_extrait`, cf. `src/labuse/ingestion/plu_ingest.py`) peuplée à l'ingestion depuis les PDF — **inaccessible en lecture seule sans base**. Le seul texte réglementaire lisible hors-ligne est le champ `citation` de chaque feuille, qui est un **extrait** (souvent partiel) du règlement.

**Conséquence appliquée dans tout le rapport (consigne du mandat « n'invente rien ») :** quand le barème d'une destination (p. ex. le collectif) **n'est pas ingéré**, je le dis — je ne reconstitue pas le texte réglementaire manquant. Les valeurs attribuées au texte du collectif pour Le Tampon et au texte Ud6 de Saint-Pierre proviennent de la **relecture indépendante citée par le mandat** ; je les signale comme **à valider par un humain sur le PLU**, pas comme un fait vérifié par LABUSE.

---

## 1. Comment le moteur choisit et applique la règle de stationnement

### 1.1 Où la règle est stockée

Un YAML par commune, `config/plu_destinations/<insee>_<slug>.yaml`, zone par zone, feuille `regles.stationnement`. Trois formes sont **déclarées** (`REGLES_RUBRIQUES["stationnement"] = ("par_logement", "par_m2_sdp", "par_typologie")`, `destinations.py:546`) :

| forme | sens |
|---|---|
| `par_logement` | un **scalaire** : N places par logement (plat) |
| `par_typologie` | une **liste de lignes**, chacune bornée par `pieces_min/max` **ou** `sdp_min/max`, avec un champ `destination` (`individuel`/`collectif`) et un `arrondi` |
| `par_m2_sdp` | une place par tranche de m² de surface de plancher |

Chaque feuille porte `statut: propose|valide`. Verrou (`regles.py:3-5`) : **seule une feuille `valide` avec citation est utilisable pour un verdict « Réussi »** ; `propose` ou absente ⇒ non servie.

### 1.2 Comment elle est lue

`regles.charger(insee, zone)` → `_bareme(reg["stationnement"])` (`regles.py:258-283`) construit un `BaremeStationnement`. **Point capital : `_bareme` ne lit que `par_logement` et `par_typologie`.** La forme `par_m2_sdp`, pourtant déclarée, **n'est consommée par aucun code** (`grep par_m2_sdp src/**/*.py` ne trouve que des commentaires et le gabarit de revue). Une règle « 1 place par tranche de 75 m² » **ne peut donc pas être servie** — elle reste `propose/None` et le contrôle tombe en « À confirmer ».

`BaremeStationnement.places_pour(pieces, sdp_m2, destination)` (`regles.py:65-82`) :
- mode `par_logement` → renvoie `flat_places` **sans regarder `destination` ni `pieces` ni `sdp`** (ligne 68-69) ;
- mode `par_typologie` → parcourt les lignes, filtre par `destination`, puis par tranche `pieces` ou `sdp`.

### 1.3 Ce qu'elle distingue — et ce qu'elle ignore

Le modèle de données **peut** distinguer individuel/collectif (champ `destination`), les tranches de pièces ou de surface, et le sens d'arrondi. **Mais le moteur, tel qu'appliqué, perd ces distinctions pour trois raisons structurelles :**

1. **Le moteur ne dessine que du collectif.** `poser_barre` (`geometrie.py:278`) empile des « modules » sur des niveaux ; il n'existe **aucun chemin** qui dessine de l'habitat individuel. Les typologies sont figées dans `config/implantation_conventions.yaml` : `T1 30 m²/1p · T2 56/2 · T3 70/3 · T4 80/4`, toutes collectives. Motif par défaut `repartition_equilibre: [T2,T3,T2,T4,T2,T3]`.
2. **La destination est codée en dur `"collectif"`** à **tous** les points d'appel du barème dans le moteur (`capacite.py:81`, `service.py:336/451/823`). Aucun appel `destination="individuel"` dans le moteur (seul `lotissement.py:274`, module séparé, l'utilise). Donc même quand un barème `par_typologie` contient une ligne individuelle **et** une collective (cas Étang-Salé UA, Saint-André UC), le moteur prend toujours la ligne collective — ce qui est cohérent avec ce qu'il dessine.
3. **Aucune notion de taille d'opération, de visiteurs, de logement social dans le barème.** `grep visiteur|lotissement|seuil` dans `implantation/` : les seuils n'existent que pour la **mixité** (`capacite.py:167-177`), jamais pour le stationnement. Les suppléments « au-delà de 5 logements », « 1 place visiteur / 100 m² » ou « 1 place / 2 logements aidés » présents dans les citations **ne sont jamais appliqués**.

De plus, le mode `par_logement` **force `arrondi="superieur"`** (`regles.py:264`) et ignore tout champ `arrondi` du YAML ; seul `par_typologie` lit l'arrondi (`regles.py:281`). Plusieurs règlements disent « arrondi à l'entier **inférieur** » (Saint-André, Sainte-Rose, Saint-Louis UZ, Trois-Bassins) : le moteur arrondit à l'envers (sans danger ici — il exige *plus* de places — mais non fidèle).

### 1.4 Comment le nombre de places devient une surface

Le comptage et le dimensionnement sont **séparés** :
- **Exigence** : `_places_imposees` (`capacite.py:71-87`) somme, par typologie dessinée, `n × places_pour(...)`, puis arrondit → `cap.places_imposees`.
- **Offre** : les places réellement **dessinées** au sol (objets `place`, 2,5 × 5 m) sont comptées (`cap.places`) ; leur surface = places + allées (5 m) + accès (4 m), mesurée sur la géométrie ; `m²/place = (places+allées+accès)/nb`. En sous-sol : `25 m²/place` (`conventions.yaml`).
- **Contrôle** (`controles.py:415-426`) : si barème `validee` et `places_imposees` non nul → **Réussi** si `cap.places ≥ cap.places_imposees`, sinon **Échoué**, avec la citation du barème. **Si barème non servi → « À confirmer »** (réputé bloquant pour un verdict « Exploitable », `controles.py:550-557`).

**Le stationnement ne rétroagit pas sur l'esquisse** : le moteur dessine d'abord l'enveloppe (logements × niveaux), puis compte les places. Quand le barème est absent, il dessine **0 place** et n'enlève aucune capacité (cas HT0538, §3).

---

## 2. Les 24 communes — barème ingéré vs règlement

**Lecture du tableau.** « Barème servi » = ce que LABUSE applique réellement (feuille `valide`). « Texte (citation servie) » = l'extrait `citation` du YAML. **Écart** :
- **absent** — aucun barème `valide` servi (feuille `propose`/`places:null`) ; le contrôle tombe en « À confirmer ».
- **incomplet** — un taux plat `valide` est servi, mais il **laisse tomber** des distinctions présentes dans le texte cité (tranches de surface/pièces, visiteurs, > 5 logements, logement social).
- **faux** — le taux servi applique la **mauvaise branche** (règle de l'individuel sur du collectif, ou tableau collectif écrasé en un seul nombre erroné).
- **juste** — le taux servi correspond au texte pour un programme collectif (taux uniforme, pas de distinction plus fine dans le texte cité).

> Le moteur ne dessinant que du **collectif**, l'« Écart » est jugé **du point de vue d'un programme collectif** (ce que l'Étude produit). La colonne « individuel » renseigne ce que le texte servi dit de l'individuel quand il le distingue ; « — » = le texte servi ne distingue pas, ou n'est pas ingéré.

| # | Commune (INSEE) | Barème servi (zones U/AU) | Art. · p. | Collectif : texte servi | Individuel : texte servi | **Écart** |
|---|---|---|---|---|---|---|
| 1 | Les Avirons (97401) | `par_logement` **1,5** plat | U 12.2 · p.17 | « 1,5 place/logt » (pas de split indiv/coll) | — | **incomplet** — supplément « +0,5 place sur voie, lotissements > 5 lots » **jamais appliqué** |
| 2 | Bras-Panon (97402) | `par_logement` **1,0** plat | U* 12.2 · p.22-62 | « autres logts : 1 si ≤100 m², 1,5 si ≥100 m² ; aidés 1 max » | — | **incomplet/faux** — tranche de surface **écrasée à 1,0** (logts ≥100 m² sous-comptés) ; plafond aidé ignoré |
| 3 | Entre-Deux (97403) | `par_logement` **2,0** plat | U12 · p.27 | « autres logts — 2 places » (uniforme) | non ingéré | **juste** (collectif) — individuel non servi |
| 4 | L'Étang-Salé (97404) | **UA : `par_typologie` valide** (coll 1-2p=1 / 3-4p=1,5 / 5p+=2 ; **indiv=2**) ; autres zones `propose` | UA 2.7.3 · p.22 | tranches de pièces servies ✔ | indiv 2 ✔ (UA) | **UA : juste** · **AUa/b/c, UB, UBv, UC, UD : absent** |
| 5 | Petite-Île (97405) | `par_logement` **1,0** plat | U*.12 · p.31-106 | « 1 place/logt » (uniforme) | — | **juste** |
| 6 | Plaine-des-Palmistes (97406) | `par_logement` **1,5** plat | U* 12.2 · p.103 | « logt > 30 m² : 1,5 » | — | **juste** (bord <30 m² non traité) |
| 7 | Le Port (97407) | `par_logement` **0,3** plat | U* 12.1 · p.30-73 | « 0,3 place/logt **+ 1 visiteur / 100 m² SDP** » | — | **incomplet** — part **visiteur jamais appliquée** (significative en collectif) |
| 8 | La Possession (97408) | `par_logement` **2,0** plat | U* 12.2 · p.21-78 | « autres logts > 50 m² SDP : 2 min » | — | **incomplet** — tranche ≤50 m² et logt social non servis ; quelques zones (UAv, UEm, AUEm) **absent** |
| 9 | Saint-André (97409) | **UC : `par_typologie` valide** (<50 m²=1 / ≥50 m²=1,5) ; autres zones `propose` | UC 12.2 · p.42 | tranches de surface servies ✔ | — | **UC : incomplet** (réductions prêt-aidé / <500 m gare non servies) · **UA/UB/UD/UE/US/UT : absent** |
| 10 | Saint-Benoît (97410) | `par_logement` **1,0** plat | U 12 · p.17 | « ≤5 logts : 1/logt ; **>5 logts : 1/logt + 1 visiteur/5** ; aidés 1/2 ; résidences 1/3 » | idem (indiv ≤5) | **incomplet** — supplément > 5 logts, aidés, résidences **non appliqués** |
| 11 | Saint-Denis (97411) | `par_logement` **1,0** plat | XVII Stationnement · p.19 | « 1 place/logt **< 100 m² SDP** » | — | **incomplet** — tranche ≥100 m² non servie |
| 12 | Saint-Joseph (97412) | `par_logement` **1,0 / 2,0** (selon zone) | U* 12.2 · p.25-84 | « N place(s) min/logt » (uniforme par zone) | — | **juste** |
| 13 | Saint-Leu (97413) | `par_logement` **2,0** plat (= taux **individuel**) | Art. 11 disp. gén. · p.13 | **Tableau collectif servi dans la citation** : chambre 0,5 / studio-2p 1 / 3-5p 1,5 / 6p+ 2 | indiv 2 | **faux** — le **2 (individuel) est appliqué à tout le collectif** ; le tableau collectif (plus bas) est ignoré (ici sur-compte) |
| 14 | Saint-Louis (97414) | `par_logement` **2,0** (UZ **1,5**) | U* 12.2 · p.23-66 | « autres constructions : 2/logt » ; UZ « 1,5 ; social 1 » | — | **incomplet** — réduction logement social (UZ) non servie |
| 15 | Saint-Paul (97415) | `par_logement` **1,0 / 1,5 / 2,0** (selon secteur) | 12.2 · p.30-288 | « autres logts : N/logt » par secteur | — | **incomplet** (branches social/autres non servies) ; plusieurs zones `propose`/« INTROUVABLE » → **absent** (U1e, U1l, U1pru, U1pso, U2e, U2h, U3e, AU5e) |
| 16 | **Saint-Pierre (97416)** | **Ud/UdBO/Udl/Ucv : `propose`, `places:null`** ; Uf/Ug/AUf/AUg **1,5** ; Up **1,0** | Ud6 · p.93 | **Ud (texte cité) : « 1 place par tranche de 75 m² SDP »** → forme `par_m2_sdp` **non supportée** | — | **Ud (cas signalé) : absent** — la règle existe, LABUSE ne la sert pas (contrôle « À confirmer ») |
| 17 | Sainte-Marie (97418) | `par_logement` **1,5** plat | U13.2 · p.26 | « opération de plusieurs logts : 1,5 min » (= collectif) | non ingéré | **juste** (collectif) |
| 18 | Sainte-Rose (97419) | `par_logement` **1,5** plat | U* 12 · p.17-43 | « 1,5/logt ≥50 m² SDP, **arrondi inférieur** » | — | **incomplet** — tranche <50 m² non servie ; **arrondi forcé supérieur** (texte = inférieur) |
| 19 | Sainte-Suzanne (97420) | `par_logement` **2,0** plat | U13 · p.17 | « logts privés ≥50 m² : 2 min » | — | **incomplet** — tranche <50 m² et logt social non servis |
| 20 | Salazie (97421) | `par_logement` **2,0** plat | U 12.2 · p.18 | « logts privés (PSLA/PTZ/libres) > 50 m² : 2 min » | — | **incomplet** — logt social et tranche ≤50 m² non servis |
| 21 | **Le Tampon (97422)** | `par_logement` **1,0** plat, **citation = « Habitat individuel 1 place/logt »** | **Ud12.2 · p.67** | **Collectif Ud12.2 : NON ingéré** (seule la ligne individuel est servie) | indiv 1 | **faux** — règle **individuelle appliquée au collectif** ; barème collectif absent (cas signalé §3) |
| 22 | Les Trois-Bassins (97423) | `par_logement` **1,5** plat | U* 12.2 · p.22-50 | « habitation : 1,5/logt, **arrondi inférieur** » (uniforme) | — | **juste** (arrondi forcé supérieur — note) |
| 23 | Cilaos (97424) | `par_logement` **1,5** plat | U* 12.2 · p.28-51 | « habitation : 1,5/logt » (uniforme) | — | **juste** |
| 24 | **Saint-Philippe (97417)** | **RNU — aucun PLU, aucun zonage** (`rnu.yaml`) | — | pas de barème quantifié au RNU | — | **absent** (hors périmètre PLU) |

### Synthèse de l'écart

- **« faux » (règle d'une mauvaise destination appliquée) : 2 communes** — **Le Tampon** (individuel → collectif, sous-compte) et **Saint-Leu** (individuel → collectif, sur-compte). Bras-Panon est à la frontière faux/incomplet (tranche de surface écrasée).
- **« absent » (règle existante non servie) : Saint-Pierre Ud** (+ Ucv), **Étang-Salé** (sauf UA), **Saint-André** (sauf UC), zones `propose` de Saint-Paul / La Possession, **Saint-Philippe** (RNU).
- **« incomplet » (taux plat, distinctions perdues) : la majorité** — visiteurs (Le Port, Saint-Benoît), > 5 logements (Avirons, Saint-Benoît), logement social (Saint-Louis, Sainte-Suzanne, Salazie, Bras-Panon), tranches de surface (Saint-Denis, Sainte-Rose).
- **« juste » pour un programme collectif : ≈ 7 communes** à taux réellement uniforme (Petite-Île, Saint-Joseph, Sainte-Marie, Cilaos, Trois-Bassins, Entre-Deux, Plaine-des-Palmistes), **+ 2 zones** correctement typologisées (Étang-Salé UA, partiellement Saint-André UC).

**Le motif dominant : presque toute l'île est ingérée en un seul `par_logement` plat.** Sur 23 PLU, **2 zones seulement** (Étang-Salé UA, Saint-André UC) exploitent le `par_typologie` avec distinction individuel/collectif que le modèle sait pourtant porter. Partout ailleurs, la richesse du règlement (destination, tranches, visiteurs, seuils d'opération, social) est aplatie en une constante — au mieux inoffensive, au pire fausse.

---

## 3. Recalcul à la main — AD0887 et HT0538

### 3.1 AD0887 — Le Tampon, zone Ud (programme : 8 logements collectifs)

L'Étude de ce terrain n'est **pas stockée** dans le dépôt (produite au run) ; je reprends le programme décrit par le mandat : **8 logements collectifs, 8 places dessinées, stationnement « Réussi »**.

**Ce que fait LABUSE :**
- barème servi = `par_logement` plat **1,0**, mode `par_logement` ⇒ `places_pour` renvoie 1,0 **quelle que soit la destination** ;
- `places_imposees = arrondi_sup(8 × 1,0) = 8` ; places dessinées = 8 ⇒ **8 ≥ 8 → Réussi**, citation affichée **« PLU art. Ud12.2 — "Habitat individuel 1 place par logement" »**.
- **Le verdict se contredit lui-même** : il déclare conforme un immeuble **collectif** en citant la règle de l'**habitat individuel**.

**Ce que dit le texte (à valider sur le PLU) :** le barème **collectif** de Ud12.2 **n'est pas ingéré** — LABUSE ne le sert nulle part, je ne le reconstitue pas. La relecture indépendante citée par le mandat lit « **11 places** pour ce programme, plus une disposition au-delà de cinq logements ».
*Corroboration prudente, non substituable à la lecture humaine :* avec le mélange par défaut pour 8 logts (T2×4 à 2p, T3×3 à 3p, T4×1 à 4p) et un barème collectif typé par pièces du type servi ailleurs (1-2p=1 ; 3p+=1,5), on obtient 4×1 + 3×1,5 + 1×1,5 = **10**, +1 au titre du dépassement de 5 logements ⇒ **11** — cohérent avec la relecture. **À confirmer article Ud12.2 p.67 (section collectif) sur le PLU du Tampon.**

**Ce que devient l'esquisse :** les **8 places sont insuffisantes** (manque ≈ **3 places**). Il faut ≈ 3 × 25 m² ≈ **75 m² de stationnement supplémentaire** (aérien ou un niveau de sous-sol). Le verdict « Réussi » n'est pas justifié ; au mieux **« À confirmer »**, voire **« À compléter »** si les places ne tiennent pas au sol sans réduire l'emprise bâtie ou le nombre de logements.

### 3.2 HT0538 — Saint-Pierre, zone Ud (programme : 10 logements collectifs, R+4)

Étude **stockée** dans le dépôt (diagnostic du 14/11/2026, `docs/audit-2026-11/exports-fix-3/COMPTE-RENDU.md:288-313`) : parcelle 510 m², **SDP 887,5 m², 10 logements, R+4**, **barème indisponible → 0 place dessinée, aucune contrainte appliquée**.

**Ce que fait LABUSE :** barème Ud = `propose`, `places:null` (règle « 1 place / 75 m² SDP », forme `par_m2_sdp` **non supportée par `_bareme`**) ⇒ **non validée** ⇒ contrôle **« À confirmer »**, `places_imposees = None`, **0 place dessinée**. **Honnête mais permissif** : l'Étude n'affiche pas « Réussi », mais elle dessine une **enveloppe maximale non bridée par le stationnement** (le garde-fou EXPORTS-FIX-3 l'empêche déjà de se dire « exploitable »).

**Ce que dit le texte servi (citation Ud6, p.93) :** « 1 place de stationnement par tranche de 75 m² de surface de plancher ».
Recalcul à la main sur la SDP dessinée : **887,5 / 75 = 11,8 → 12 places** exigées (une place par tranche de 75 m² entamée). *À valider sur le PLU : le seuil logement social « 1 place/logt locatif social » peut modifier le total ; le texte intégral n'est pas servi hors-ligne.*

**Ce que devient l'esquisse :** 12 places requises, **0 prévue**. Il faut loger ≈ 12 × 25 m² ≈ **300 m² de stationnement** → quasi un niveau de sous-sol complet, ou une amputation sensible de la SDP. **L'enveloppe de 888 m² surévalue** la capacité réelle ; la règle existe, LABUSE devrait la servir et la retrancher (ou au minimum chiffrer l'exigence à côté du 0 dessiné).

**Contraste des deux cas :** Le Tampon = **faux positif** (« Réussi » imprimé à tort). Saint-Pierre = **faux négatif de service** (règle existante jamais servie ⇒ l'Étude ne peut jamais conclure, et son enveloppe n'est pas bridée). Les deux viennent de la même cause : **un seul `par_logement` plat ne capte pas la règle réelle**.

---

## 4. Les autres contrôles durs — une ligne par commune

**Rappel méthodologique.** Emprise (CES), hauteur, reculs et pleine terre sont des règles **d'enveloppe de zone**, en principe **indépendantes de la destination ou du type de logement** — contrairement au stationnement. Pour ces contrôles, « appliquer la valeur de la zone » est méthodologiquement correct *pour le programme dessiné* **dès lors que la valeur ingérée est la bonne** ; le risque n'est pas le mauvais-programme, mais l'**absence** d'ingestion (contrôle « Non effectué », aucune borne) ou une valeur fausse. Le texte verbatim n'étant pas lisible hors-ligne, je rapporte la **couverture** (combien de zones U/AU portent chaque règle `valide`), pas la justesse chiffre par chiffre.

Comptage sur les zones U/AU qui portent leurs propres `regles` (H = hauteur, CES = emprise, RV/RS = reculs voie/séparatives, PT = pleine terre) :

| Commune | zones réglées | H | CES | RV | RS | PT | Lecture (une ligne) |
|---|---|---|---|---|---|---|---|
| Les Avirons | 20 | 19 | 11 | 19 | 19 | 19 | enveloppe bien couverte ; **CES partiel** (9 zones sans emprise → contrôle non effectué) |
| Bras-Panon | 15 | 14 | 14 | 14 | 14 | 14 | couverture quasi complète |
| Entre-Deux | 5 | 5 | 1 | 5 | 5 | 5 | **CES quasi absent** (1/5) |
| L'Étang-Salé | 12 | 12 | 12 | 12 | 12 | 12 | enveloppe complète (le trou est le stationnement, §2) |
| Petite-Île | 15 | 15 | 13 | 15 | 15 | 15 | complète ; CES 13/15 |
| Plaine-des-Palmistes | 10 | 9 | 9 | 9 | 9 | 9 | complète |
| Le Port | 15 | 13 | 13 | 12 | 13 | 12 | bonne couverture, quelques zones partielles |
| La Possession | 23 | 19 | **3** | 22 | 22 | 19 | **CES très lacunaire** (3/23) → emprise non bornée sur l'essentiel |
| Saint-André | 9 | 8 | **0** | 7 | 7 | 7 | **CES absent** (0/9) → aucune limite d'emprise servie |
| Saint-Benoît | 5 | **0** | 5 | **0** | 5 | 5 | **hauteur et recul voie absents** (0/5) → contrôles non effectués |
| Saint-Denis | 21 | 17 | 16 | 20 | 20 | **0** | **pleine terre absente** (0/21) |
| Saint-Joseph | 24 | 24 | 24 | 24 | 24 | 22 | **la mieux couverte** |
| Saint-Leu | 19 | 18 | 17 | 18 | 18 | **5** | **pleine terre lacunaire** (5/19) |
| Saint-Louis | 18 | 18 | 17 | 17 | 18 | 17 | couverture complète |
| Saint-Paul | 32 | 31 | **0** | 30 | 31 | 29 | **CES absent** (0/32) → emprise non bornée |
| Saint-Pierre | 27 | 26 | 25 | 25 | 25 | 21 | enveloppe bien couverte (le trou est le stationnement Ud, §3) |
| Sainte-Marie | 19 | 19 | 16 | 19 | 19 | 17 | complète |
| Sainte-Rose | 9 | 9 | 9 | 9 | 9 | 9 | complète |
| Sainte-Suzanne | 12 | 12 | **2** | 12 | 12 | 12 | **CES quasi absent** (2/12) |
| Salazie | 10 | 10 | **0** | 10 | 10 | 10 | **CES absent** (0/10) |
| Le Tampon | 20 | 20 | **0** | 15 | 15 | 13 | **CES absent** (0/20) → AD0887 n'a aucun contrôle d'emprise ; reculs/PT partiels |
| Les Trois-Bassins | 10 | 9 | 9 | 9 | 9 | 9 | complète |
| Cilaos | 8 | 8 | 7 | 8 | 8 | 7 | complète |
| Saint-Philippe | — | — | — | — | — | — | RNU : pas de règle d'enveloppe zonale |

**Pour le programme dessiné, la règle appliquée est-elle celle du texte ?** Oui *par construction* là où la règle est servie : hauteur/emprise/reculs/PT ne dépendent pas du type de logement, et le moteur mesure le projet contre la borne de la zone (`controles.py:273-413`). Deux réserves :
1. **Lacunes de couverture** (CES absent au Tampon, Saint-Paul, Saint-André, Salazie ; PT absente à Saint-Denis ; H/RV absents à Saint-Benoît) : le contrôle est **« Non effectué »**, aucune borne — l'enveloppe peut être surévaluée sans alerte.
2. **Hauteur sur terrain en pente et distance entre bâtiments** sont déjà traitées finement (gradins « À confirmer », silence prouvé) — pas d'anomalie de type-de-programme repérée ; ce sont des contrôles géométriques, pas destinataires.

Le seul contrôle dur **intrinsèquement lié au type de programme** est donc bien le **stationnement** — et c'est le seul où « la règle appliquée n'est pas celle du texte pour le programme dessiné » (§2, §3).

---

## 5. Proposition de correction, en lots — du plus grave au moins grave

> Chaque lot distingue **ce que LABUSE peut corriger seul** (code / ré-ingestion d'un texte déjà cité) de **ce qu'un humain doit valider sur le PLU** avant ingestion. Rien dans ce rapport ne doit être ingéré sans relecture humaine du texte opposable : le verbatim intégral n'est pas servi hors-ligne.

### LOT 1 — Faux positif « Réussi » sur la mauvaise destination *(le plus grave)*
**Cibles : Le Tampon (toutes zones U/AU), Saint-Leu.** Un barème **individuel** est servi en `par_logement` plat et appliqué au **collectif**, produisant un « Réussi » (Le Tampon : sous-compte **dangereux** ; Saint-Leu : sur-compte, moins risqué mais faux).
- **Code :** quand le programme dessiné est collectif (toujours le cas du moteur) **et** que le barème servi est étiqueté/cité comme « habitat individuel », **refuser le verdict « Réussi »** et retomber en « À confirmer » (ne jamais imprimer la citation individuelle sous un immeuble collectif). Garde-fou symétrique du §5 d'EXPORTS-FIX-3.
- **À valider par un humain sur le PLU :** le **barème collectif réel** — Le Tampon **art. Ud12.2 p.67 (section collectif)** ; Saint-Leu **art. 11 dispositions générales p.13 (tableau HABITAT COLLECTIF)** — puis l'ingérer en `par_typologie` avec `destination: collectif` et les tranches de pièces. **Confirmer le « +1 au-delà de 5 logements » du Tampon** (forme exacte : par opération ? par tranche ?).

### LOT 2 — Règle existante jamais servie, faute de forme supportée
**Cibles : Saint-Pierre (Ud, Ucv : « 1 place / 75 m² SDP ») et toute zone en `par_m2_sdp`.** La forme est **déclarée mais non consommée** par `_bareme` ; la règle reste `propose` et le contrôle ne conclut jamais, tout en laissant l'enveloppe non bridée (HT0538).
- **Code :** **implémenter la branche `par_m2_sdp`** dans `_bareme`/`places_pour` (`places_imposees = arrondi_sup(SDP / m²_par_place)`). C'est du code pur, le texte est déjà cité.
- **À valider par un humain :** le **sens d'arrondi** (« par tranche entamée » ⇒ supérieur ?) et l'articulation avec « 1 place / logement locatif social » (Ud6) avant de passer la feuille en `valide`.

### LOT 3 — Suppléments et réductions jamais appliqués *(incomplet, impact chiffré réel)*
**Cibles : visiteurs (Le Port, Saint-Benoît), > 5 logements/lots (Les Avirons, Saint-Benoît), logement social (Saint-Louis UZ, Sainte-Suzanne, Salazie, Bras-Panon), tranches de surface (Saint-Denis ≥100 m², Sainte-Rose/Sainte-Suzanne/Salazie ≤50 m², Bras-Panon ≥100 m²).** Les citations portent ces clauses ; le `par_logement` plat les ignore.
- **Code :** étendre le modèle de barème pour porter (a) un **supplément visiteur** (places/tranche de SDP), (b) un **seuil d'opération** (places additionnelles au-delà de N logements/lots), (c) une **ligne logement social** (`destination`/produit). Puis les appliquer dans `_places_imposees`.
- **À valider par un humain :** pour chaque commune, **transcrire la clause exacte** (base, seuil, taux) depuis le texte opposable avant ingestion — c'est le gros du travail humain, commune par commune.

### LOT 4 — Tranches de surface/pièces écrasées en un plat *(incomplet, sans danger immédiat mais non fidèle)*
**Cibles : toutes les communes à taux plat dont le texte cité porte des tranches** (Bras-Panon, Saint-Denis, Sainte-Rose, Sainte-Suzanne, Salazie, La Possession…).
- **Code :** aucun nouveau mécanisme — `par_typologie` existe déjà ; il suffit de **ré-ingérer** ces barèmes en lignes typées au lieu d'un scalaire.
- **À valider par un humain :** la lecture des bornes (50 m², 100 m²…) et l'inclusion/exclusion des bornes sur le texte.

### LOT 5 — Arrondi forcé et couverture d'enveloppe *(le moins grave)*
- **Arrondi :** `par_logement` force `superieur` (`regles.py:264`) alors que plusieurs textes disent « inférieur » (Saint-André, Sainte-Rose, Saint-Louis UZ, Trois-Bassins). **Code :** lire un champ `arrondi` en mode `par_logement` comme le fait déjà `par_typologie`. Sans danger (exige plus de places) mais à aligner. **À valider :** le sens d'arrondi par commune.
- **Couverture CES/PT/H (§4) :** combler les **lacunes d'emprise** (Le Tampon, Saint-Paul, Saint-André, Salazie, Sainte-Suzanne, La Possession) et de **pleine terre** (Saint-Denis) qui laissent l'enveloppe non bornée. **À valider par un humain :** le chiffre CES / % pleine terre de chaque zone sur le règlement, avant de passer la feuille `valide`. *(Hors stationnement stricto sensu, mais c'est ce qui permet au faux positif d'enveloppe de HT0538 d'exister.)*

### Garde-fou transversal (applicable immédiatement, sans ingestion)
Tant que les lots ci-dessus ne sont pas validés : **ne jamais afficher « Réussi » sur le stationnement quand la citation servie relève d'une destination différente de celle du programme dessiné** (individuel sous un collectif). C'est la correction minimale qui supprime le faux positif du Tampon sans toucher aux chiffres — à la main de LABUSE seul.

---

## Annexe — fichiers et points de lecture

- Modèle de barème : `src/labuse/implantation/regles.py:42-97` (`BaremeStationnement`, `places_pour`), `:258-283` (`_bareme` — **pas de `par_m2_sdp`, arrondi plat forcé**).
- Application : `src/labuse/implantation/capacite.py:71-87` (`_places_imposees`, `destination="collectif"` codé en dur), contrôle `src/labuse/implantation/controles.py:415-426`.
- Programme dessiné (collectif seul) : `src/labuse/implantation/geometrie.py:278` (`poser_barre`), typologies `config/implantation_conventions.yaml:38-44`.
- Données ingérées : `config/plu_destinations/<insee>_*.yaml`, feuille `regles.stationnement` ; lecture `src/labuse/plu/destinations.py:673` (`regles_zone`).
- Texte verbatim du PLU : table `plu_reglement_extrait` (`src/labuse/ingestion/plu_ingest.py:17-37`) — **non lisible hors-ligne** ; seul le champ `citation` des YAML l'est.
- HT0538 (étude stockée) : `docs/audit-2026-11/exports-fix-3/COMPTE-RENDU.md:288-325`.
