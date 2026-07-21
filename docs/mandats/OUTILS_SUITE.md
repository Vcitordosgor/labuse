# FENÊTRE PRÉ-M7 · LA SUITE DES 12 OUTILS (+ lot 0 Score É V2)

Branche `fenetre/outils-suite`. **Un outil = un lot = un commit `[O0]`…`[O12]`.** Rapport incrémenté à chaque lot.
Rythme : O0→O5 puis STOP review (mi-course) ; O6→O12 autonome ; STOP final. Vic merge (`--no-ff`) ; je ne merge jamais.

Règles communes (priment sur la vitesse) : réutiliser l'existant, zéro ingestion risquée, zéro scraping ;
**Sourcé/Estimé sur chaque chiffre** ; non calculable = « non estimable », jamais inventé ; indice non calibrable =
livré MASQUÉ (flag) + finding ; personne morale (SIREN public) OK, particulier JAMAIS nommé ; lot cassé non réparable
en ~15 min → revert + finding + lot suivant ; l'arbre ne finit jamais rouge. Chaque lot note sa **reco d'exposition**.

---

## O0 · Score É V2 — le déblocage ✅

**Problème (note de sensibilité, clôture cycle 2).** Le Score É v1 prenait le prix de sortie sur la **médiane DVF de
l'EXISTANT** (~2 265 €/m², ancien + maisons diluées). Or un promoteur ne revend pas de l'ancien : il vend du **NEUF**.
Ce prix trop bas écrasait ~99 % des marges — **697 parcelles positives sur 58 282 estimables**, médiane −334 k€. Le
Score É était juste dans sa mécanique mais faux dans son entrée prix → livré **MASQUÉ**.

**Correctif.** Nouveau prix de sortie NEUF reconstruit par secteur.

### Table `dvf_prix_sortie_neuf` (additive, `src/labuse/ingestion/dvf_prix_neuf.py`)
- **Source (Sourcé DVF).** Ventes (`nature_mutation='Vente'`, histo + parcelle) d'un logement `Maison`/`Appartement`
  avec surface bâtie, réalisées **≤ 3 ans après l'achèvement d'un PC** sur la parcelle (`m10_permit_delais.date_achevement`).
  Proxy VEFA/livraison : les VEFA pures sont sans surface au 974, d'où le proxy achèvement. €/m² borné **[1 000 ; 12 000]**
  (anti-artefact, mêmes bornes que `bilan.py`).
- **Repli documenté (seuils).** Médiane €/m² au **niveau secteur** (préfixe IDU 10) si **n ≥ 5**, sinon **niveau commune**
  (INSEE 5) si **n ≥ 5**, sinon **absent → « non estimable »** côté score_e. Le niveau retenu est tracé (`niveau_prix`).
- **Couverture.** **45 secteurs + 17 communes** (n ≥ 5). Médiane du prix neuf reconstruit ≈ **3 688 €/m²** (vs 2 265 existant, **+63 %**).

### Score É recalculé (`score_e`, `HYP_VERSION = "bilan-neuf-v2"`)
Charge foncière supportable = bilan à rebours batch inchangé (`surf_habitable = SDP_rés / 1,15` ; `charge = surf_habitable
× prix_sortie_NEUF × 0,79 − SDP_rés × 2 550 €/m²` ; VRD = 0 prudent) — **seule l'entrée prix change** : prix de sortie neuf
(secteur → commune). Nouvelle colonne `niveau_prix` (secteur / commune) exposée en fiche pour la transparence du repli.

**Distribution avant / après** (77 718 parcelles non-écartées de `q_v7_defisc`, Estimé partout) :

| | estimables | **marges positives** | médiane marge | p90 marge |
|---|---|---|---|---|
| **v1 (existant)** | 58 282 | **697** | −334 k€ | — |
| **V2 (neuf)** | 51 926 | **3 788 (×5,4)** | −159 k€ | −18 k€ |

- Les positives passent de **697 → 3 788** ; la médiane des marges se relève de −334 k€ à −159 k€. La marge reste
  négative pour la majorité : c'est **honnête** — la plupart des parcelles ne sont pas des cibles de promotion aux
  hypothèses génériques ; le Score É trie celles qui le sont.
- **3 681 / 3 788 positives font ≤ 5 000 m²** (2 seulement > 5 ha). Le max (33,7 M€) est une vraie parcelle de 4,6 ha
  (SDP résiduelle 57 546 m²) : math cohérente (marge = montant absolu → grand foncier = grand nombre), **pas un artefact**.
- Estimables en baisse (58 282 → 51 926) : le neuf a une couverture plus stricte que l'existant ; **25 792 non estimables**
  (pas de prix neuf secteur ni commune). C'est le prix de l'honnêteté — pas de chiffre inventé.
- **Répartition du niveau prix** (estimables) : **secteur 7 208 · commune (repli) 44 718**. Le repli commune domine (86 %) :
  couverture secteur encore fine, à densifier quand la fenêtre des ventes neuves s'élargira.

### Reco d'exposition (décision Vic au STOP) — **LEVER le flag, avec garde-fous**
Le Score É V2 est **économiquement juste** : bilan à rebours d'un promoteur sur le prix de sortie neuf, qui est
exactement le raisonnement métier. Le blocage v1 (prix existant) est corrigé. Je recommande de **lever le flag de masquage**
sous trois conditions déjà tenues dans le livrable :
1. **Badge `Estimé` systématique** (jamais un prix ni une promesse) — présent (`libelle_court` + `detail`).
2. **Niveau du prix affiché** (`secteur` / `commune (repli)`) — l'utilisateur voit la granularité. Le repli commune
   (86 %) est plus grossier : c'est dit, pas caché.
3. **« non estimable » explicite** là où le prix neuf manque (25 792 parcelles) — pas de zéro trompeur.

Le Score É reste **un signal parmi d'autres**, cloisonné du score P servi (colonnes annexes `score_e.*`, zéro touche au
scoring / runs servis / golden). **Décision finale à Vic.**

### Livrable technique
- `src/labuse/ingestion/dvf_prix_neuf.py` — builder + table `dvf_prix_sortie_neuf`.
- `src/labuse/ingestion/score_e.py` — prix de sortie neuf (secteur→commune), `niveau_prix`, `HYP_VERSION` v2.
- `src/labuse/api/app.py` — `niveau_prix` exposé en fiche.
- `src/labuse/cli.py` — commandes `prix-neuf` et `score-e` (chaîne le prix neuf par défaut).
- `tests/test_score_e.py` — mis à V2 : **5/5 verts**.

**Findings O0.** (1) Couverture secteur du prix neuf encore fine (86 % de repli commune) → se densifiera avec le flux DVF ;
à re-builder périodiquement. (2) VEFA sans surface au 974 → proxy achèvement PC, borné, documenté ; **ne pas sur-vendre**
comme « prix VEFA réel ». (3) `q_v7_defisc` = run servi ; le Score É suit ce run, à re-builder après toute bascule de run.

---

## O1 · Dossier banquier ✅ (candidat démo)

**Le PDF qu'un porteur pose sur le bureau de son financeur.** 6-8 pages print sobres, **tout sourcé**, zéro donnée
nouvelle — assemble l'existant. Endpoint `GET /dossier-banquier/{idu}.pdf` (`src/labuse/api/banquier.py`), bouton
« Banquier » ajouté à la fiche (à côté de PDF / Dossier).

### Structure (7 pages sur la parcelle de test)
1. **Couverture** — identité + **photo aérienne IGN (BD ORTHO, Géoplateforme)** avec contour parcelle + **synthèse
   exécutive** + bandeau de KPI (terrain, surface vendable, charge foncière, marge Score É).
2. **Identité** — références cadastrales, adresse BAN, surface, **zonage** + règles calibrées (Estimé).
3. **Faisabilité** — les **11 steps déterministes** (`parcel_faisabilite`), chaque ligne Sourcé/Estimé + potentiel indicatif.
4. **Bilan promoteur & charge foncière** — postes du `compute_bilan`, fourchette de charge foncière, + **Score É V2**
   (marge = charge supportable − prix probable, prix de sortie neuf O0).
5. **Marché de comparaison** — comparables DVF (Q1/médiane/Q3, ancien vs neuf/VEFA) + **permis SITADEL voisins**.
6. **Risques, servitudes & ZAN** — couches dormantes + consommation ENAF de la commune (Cerema, Sourcé).

### Synthèse exécutive — narrée par le socle IA, **strict_numbers**
`core.complete(model=sonnet, validate=True, strict_numbers=True)` sur un contexte de **faits sourcés uniquement**
(parcelle, capacité, charge foncière, marché, marge, permis, vigilance). L'IA **narre les étapes, n'invente aucun
chiffre** ; la couche de validation rejette tout nombre absent des faits. **Repli déterministe honnête** si pas de clé
(crédits épuisés) : concaténation des faits, aucune invention. **Jamais de RR ni de score interne en vitrine.**

### Robustesse
- Chaque section est guardée (`to_regclass`, try/except) : une donnée absente devient « non estimable », jamais un
  chiffre fabriqué. Testé sur parcelle **sans** faisabilité/marge → PDF produit proprement.
- **Bug corrigé en cours de route** : la requête ZAN utilisait `code_insee` (colonne réelle = `insee`) → elle abortait
  la transaction Postgres et faisait échouer la synthèse IA en aval. Colonne corrigée ; TX propre vérifiée.

### Livrable technique
- `src/labuse/api/banquier.py` — module + endpoint.
- `src/labuse/api/app.py` — routeur branché.
- `frontend/src/components/fiche/Fiche.tsx` — bouton « Banquier ».
- `tests/test_banquier.py` — **7/7 verts** (puces Sourcé/Estimé, Score É rendu, non estimable sans chiffre, comparables
  ancien/VEFA, synthèse de repli sans invention, absence de RR/percentile en vitrine).

**Reco d'exposition.** **Visible** (candidat démo). C'est une vitrine, pas un indicateur calibré : aucun risque de
faux signal, tout est sourcé et labellisé. **Findings O1** : (1) synthèse IA en repli déterministe tant que les crédits
Anthropic sont épuisés — fonctionnel mais moins fluide ; (2) gating `dossier_parcelle` (Essentiel) — à confirmer si le
dossier banquier doit être un cran au-dessus (Intégral).

---

## O2 · Scoreur d'adresse inversé ✅

**« Je visite ce terrain, qu'en dit LA BUSE ? »** Entrée : une adresse (+ prix DEMANDÉ **saisi à la main**, jamais
scrapé). `POST /scoreur-adresse` (`src/labuse/api/scoreur.py`).

### Chemin
adresse → **BAN** (géocodage, même client que `audit.audit_by_address`) → point → **parcelle contenant le point**
(`ST_Contains`, déjà en base et déjà scorée) → **verdict compact** : tier du run servi (`q_v7_defisc`) + rang/percentile,
Score É (marge €). **Île entière** — pas de restriction commune-pilote : on lit une parcelle déjà scorée, **aucune
ingestion live**, zéro scraping.

### Confrontation du prix demandé (si fourni)
Le prix saisi (Estimé du marché) est confronté à la **charge foncière supportable** et au **prix probable du foncier**
(Score É V2, O0) : `opportunite` (≤ charge supportable, marge résiduelle affichée), `dans_le_marche` (≤ prix probable
+10 %), `cher` (au-dessus des deux), ou `non_estimable` si la charge manque. Toujours labellisé « Estimé — ni un prix ni
une promesse ». **Adresse hors base → réponse honnête** (`ok:false`, renvoi vers l'audit cadastral), jamais un verdict inventé.

### Livrable technique
- `src/labuse/api/scoreur.py` — endpoint + logique prix.
- `src/labuse/api/app.py` — routeur branché.
- `tests/test_scoreur.py` — **6/6 verts** (opportunité/marché/cher/non estimable ; flux adresse→verdict ; hors base honnête).

**Reco d'exposition.** **Visible** côté API ; **UI à ajouter** (barre « scorer une adresse » — aucune UI d'audit
n'existe encore côté front). Aucun risque de faux signal (verdict = tier déjà servi + Score É labellisé). **Finding O2** :
brancher un champ de saisie sur la fiche/carte pour l'usage terrain (visite, panneau « à vendre »).

---

## O3 · Anti-fiche (« pourquoi PAS ») ✅

**La fiche dit pourquoi c'est intéressant ; l'anti-fiche dit pourquoi ça ne l'est pas.** `GET /anti-fiche/{idu}`
(`src/labuse/api/anti_fiche.py`). Lit la **cascade déjà calculée** (`cascade_results`) — aucune donnée nouvelle,
aucun recalcul.

### Deux niveaux hiérarchisés, chacun sourcé
- **RÉDHIBITOIRE** (`HARD_EXCLUDE`) : motifs bloquants (ex. « Exclue : PPR zone rouge », « pente 74 % — non
  aménageable », « forêt domaniale — inacquérable »). La parcelle est écartée (étage 0).
- **VIGILANCE** (`SOFT_FLAG`) : contraintes non bloquantes qui pèsent (ex. avis ABF probable).
Chaque motif = libellé déjà rédigé + couche + source (réelle, sinon « cascade (dérivé) » pour un motif
géométrique/règle). **Dédup par couche** (le motif le plus fort gagne, HARD trié en premier).

### Honnêteté
- Cadre selon le tier servi (écartée / réserves / bien classée). Une parcelle **sans motif** le dit
  (« Aucun motif d'écartement ni point de vigilance »). Une parcelle **bien classée** liste ses rares points de
  vigilance plutôt que d'inventer des défauts. Les lignes `PASS`/`POSITIVE` sont exclues.

### Livrable technique
- `src/labuse/api/anti_fiche.py` — endpoint. `src/labuse/api/app.py` — routeur branché.
- `tests/test_anti_fiche.py` — **3/3 verts** (écartée : HARD puis SOFT, PASS exclu ; bien classée : aucune invention ;
  dédup par couche).

**Reco d'exposition.** **Visible** (transparence pure, tout sourcé/dérivé de la cascade servie). **Finding O3** : brancher
un panneau « pourquoi pas » sur la fiche (miroir du bloc verdict) et l'utiliser dans le wording des parcelles écartées.

---

## O4 · Traducteur de règlement PLU ✅

**« Cet article, ça donne quoi sur MA parcelle ? »** `POST /traducteur-plu/{idu}` (`src/labuse/api/traducteur.py`).
Deux couches, du plus sûr au plus souple :

1. **Application déterministe** (toujours dispo) — les règles **chiffrées** de la zone (`resolve_zone`, déjà calibrées
   + sourcées par champ) appliquées à la surface de CETTE parcelle : emprise au sol max **en m²** (`% × surface`, calcul
   affiché), hauteurs égout/faîtage, reculs voirie/limites, stationnement, pleine terre en m². Chaque ligne porte sa
   **source** (« Art. 10.2, p.41 »…). **`A_VERIFIER` signalé** (« à vérifier — règlement ambigu »), jamais comblé ;
   règle absente (None) **omise**, jamais inventée. Zone non calibrée → avertissement « estimation générique ».
2. **Traduction IA d'un article collé** (optionnelle) — si l'utilisateur colle un texte d'article, le socle (sonnet,
   **`strict_numbers`**) l'explique en clair, **ancré sur les faits chiffrés** ci-dessus ; il n'invente aucun nombre ;
   **refus propre** si l'article ne se rattache à aucun fait connu.

Le texte intégral du règlement **n'est pas ingéré** — on ne prétend pas le lire : on fournit le **lien profond** vers la
page/article (`resolve_reglement`, ex. `…REGLT_PLU_st_paul…pdf#page=45`) pour vérification. **Jamais un conseil juridique**
(disclaimer : seul le règlement opposable fait foi).

### Validation
Testé sur parcelle Saint-Paul zone **U1l** (calibrée) : hauteur faîtage 14 m (Art. 10.2 p.41), recul limites 3 m
(Art. 7), reculs/stationnement/pleine terre = « à vérifier » honnêtes, deep-link PDF p.45. Zone **N** → refus honnête
(« aucune règle calibrée »).

### Livrable technique
- `src/labuse/api/traducteur.py` — endpoint + application déterministe + traduction IA. `app.py` — routeur branché.
- `tests/test_traducteur.py` — **7/7 verts** (emprise/pleine terre en m² sourcées ; A_VERIFIER signalé ; règle absente
  omise ; hauteurs/reculs avec unité ; prospect ; disclaimer sans conseil juridique).

**Reco d'exposition.** **Visible** (règles déterministes sourcées + lien opposable ; l'IA n'ajoute que de la prose
groundée). **Finding O4** : la traduction IA est en repli tant que les crédits Anthropic sont épuisés ; la couche 1
(règles chiffrées appliquées) fonctionne sans IA et suffit déjà à l'usage.

---

## O5 · Servitudes invisibles ✅

**Ce qui ne « crie » pas sur la fiche mais peut tout bloquer.** `GET /servitudes-invisibles/{idu}`
(`src/labuse/api/servitudes.py`). 100 % lecture de `spatial_layers` (déjà ingérée) — **zéro donnée nouvelle**.

### Couches dormantes lues, chacune sourcée + datée
**SUP** (servitudes d'utilité publique, 417 en base) décodées en effet concret (PM1 → « Risques naturels (PPR) —
prescriptions constructives », AC1 → « Abords MH — avis ABF », I3 → « Canalisation de gaz — bande de servitude »,
AS1 → « Captage d'eau potable »…), **50 pas géométriques**, **classement sonore routier** (catégorie d'isolement),
**SIS/CASIAS** (sols pollués), **recul du trait de côte**, **PEB**, **zonage d'assainissement**. Chaque ligne porte sa
**source** (`data_sources.name`) et sa **date** (dernier sync). **Dédup** (une SUP répétée en enveloppes gen1/gen2 = une
ligne).

### Honnêteté
- Couches attendues mais **non ingérées** (canalisations de transport, RNIC copro) listées comme **non couvertes** —
  jamais un faux « RAS ». Parcelle sans servitude → dit clairement, avec l'avertissement que « l'absence ici ne vaut pas
  absence réelle ; vérifiez le certificat d'urbanisme ». Un code SUP inconnu est affiché tel quel, jamais inventé.

### Validation
Parcelle Saint-Louis intersectant une SUP PM1 → « Risques naturels (PPR) — prescriptions constructives », source
« SUP — assiettes GPU (API Carto) », datée 2026-07-10. Parcelle sans servitude → n=0, RAS honnête.

### Livrable technique
- `src/labuse/api/servitudes.py` — endpoint + décodage SUP. `app.py` — routeur branché.
- `tests/test_servitudes.py` — **8/8 verts** (décodage SUP/SIS/bruit ; code inconnu non menti ; dédup ; source+date ;
  RAS honnête ; non-couvert listé).

**Reco d'exposition.** **Visible** (lecture sourcée + datée, avec caveat de non-exhaustivité explicite). **Finding O5** :
ingérer les canalisations de transport (BNPT/PGT) compléterait le tableau ; le lien SUP `urlreg` est souvent vide dans
`attrs` (Géoportail) — à enrichir si une URL réglementaire par SUP devient disponible.

---

## O0b · Suite review Vic — niveau_prix visible client (flag Score É levé) ✅

Décision Vic : **flag Score É levé**, exigence **niveau_prix visible côté client** (« estimation niveau secteur/commune »),
idem dossier banquier. Constat : `score_e` n'était **jamais rendu** côté front — c'était ça, le masquage. Le rendu fiche
lui-même revient au **mandat front** (réorg fiche en un passage — cf. décision 3) ; je garantis ici le **contrat de données**.
- `src/labuse/ingestion/score_e.py` : helper `niveau_label()` (« estimation niveau secteur » / « … commune (repli) ») ;
  wording embarqué dans le `detail` stocké (rebuild effectué).
- `src/labuse/api/app.py` : bloc fiche `score_e` expose `niveau_label` (tooltip/détail prêt pour le front).
- `src/labuse/api/banquier.py` : Score É du dossier affiche « prix de sortie neuf — estimation niveau secteur/commune (repli) ».
- Tests : +2 (score_e `niveau_label`, banquier wording) → **14/14** sur ces deux fichiers.

Décisions Vic actées : (2) dossier banquier reste **Essentiel** (Intégral + gating = post-M7 sur feedback) ; (3) **UI O2/O3
NON faites en partie 2** — affectées au mandat front (fiche réorganisée en un passage).

---

## STOP MI-COURSE (après O0→O5)

**6 lots livrés, 6 commits, arbre vert.** Score É débloqué (×5,4 marges positives) ; dossier banquier démo ; scoreur
d'adresse ; anti-fiche ; traducteur PLU ; servitudes invisibles. **36 tests verts** (score_e V2 5 + 31 neufs : banquier 7,
scoreur 6, anti-fiche 3, traducteur 7, servitudes 8). Zéro touche scoring / runs servis / golden.

### Table des recommandations d'exposition (à trancher par Vic)
| Lot | Reco | Motif |
|---|---|---|
| **O0 Score É V2** | **Lever le flag de masquage** (garde-fous) | Économiquement juste (prix de sortie neuf) ; badge Estimé + niveau prix + non estimable explicite |
| **O1 Dossier banquier** | **Visible** (candidat démo) | Vitrine sourcée, aucun risque de faux signal |
| **O2 Scoreur d'adresse** | **Visible** (API) + **UI à ajouter** | Verdict = tier servi + Score É labellisé |
| **O3 Anti-fiche** | **Visible** | Transparence pure, dérivé de la cascade servie |
| **O4 Traducteur PLU** | **Visible** | Règles déterministes sourcées + lien opposable |
| **O5 Servitudes invisibles** | **Visible** | Lecture sourcée + datée, caveat de non-exhaustivité |

### Décisions attendues au STOP
1. **Score É** : lever le flag de masquage ? (reco : oui, avec garde-fous).
2. **Gating** dossier banquier : Essentiel (actuel) ou Intégral ?
3. **UI** : brancher O2/O3 sur la fiche/carte (findings ouverts).

Reste : **O6→O12** en mode autonome (règles du batch de nuit), puis STOP final (dont dossier de revue 20 cartes O12).

---

# PARTIE 2 — O6→O12 (autonome)

## O6 · Comparateur de communes ✅

**« Où investir ? » un tableau, une ligne par commune.** `GET /comparateur-communes` (`src/labuse/api/comparateur.py`).
Agrège 6 indicateurs **déjà en base** (zéro donnée nouvelle), un par colonne, chacun Sourcé/Estimé, sur les **24 communes** :

| Indicateur | Direction | Source | Nature |
|---|---|---|---|
| Stock d'opportunités (brûlantes + chaudes) | haut = mieux | run servi | Sourcé |
| Vélocité admin (délai médian dépôt→autorisation, mois) | bas = mieux | m10 / SITADEL | Sourcé |
| Dynamisme permis (SITADEL, 24 mois) | haut = mieux | SITADEL | Sourcé |
| Déficit SRU (objectif − taux LLS, points) | haut = mieux | DHUP | Sourcé |
| Pression ZAN (ENAF consommé 2021-2024, ha) | bas = mieux | Cerema | Sourcé |
| Prix de sortie neuf (DVF, €/m²) | haut = mieux | DVF | Estimé |

### Composite = commodité, PAS un score calibré
Chaque indicateur **normalisé min-max [0-100]** selon sa direction ; composite = **moyenne pondérée des axes présents**.
**Pondération réglable** (query params `w_*`, défauts documentés : stock 0,30 · vélocité/permis/SRU/prix 0,15 · ZAN 0,10)
et **présentée** dans la réponse (`indicateurs`, `methode`, `poids_total`). Un **axe manquant reste `null`** (jamais 0
trompeur) et son poids est **retiré du composite de cette commune** (renormalisation), pour ne pas la pénaliser.

### Validation
24 communes classées ; Saint-Paul en tête (stock 259, 580 permis/24 mois). 7 communes ont un axe manquant → renormalisé.
`src/labuse/api/comparateur.py` (helper testable `_compute`), routeur branché.
`tests/test_comparateur.py` — **5/5 verts** (+1 skip DB propre) : direction stock/vélocité, axe manquant null +
renormalisation, classement/rang, borne dégénérée neutre.

**Reco d'exposition.** **Visible** avec la mention « aide à la comparaison, pas un score de rendement » (déjà dans la
réponse) et la pondération affichée réglable. **Finding O6** : brancher un tableau triable + curseurs de poids côté front
(mandat front) ; le PLH par EPCI (`plh_epci`) pourrait devenir un 7ᵉ axe (objectifs de production) si utile.

---

## O7 · Carnet de secteur consultable ✅

**Une page de suivi par micro-secteur** (`left(idu,10)` = INSEE + « 000 » + section). `GET /carnet-secteur/{secteur}`
+ `GET /carnet-secteur` (liste des secteurs à suivre, triés par stock d'opportunités). `src/labuse/api/carnet.py`.
100 % lecture (zéro donnée nouvelle).

### Contenu de la page (chaque bloc sourcé, requêtes optionnelles guardées `to_regclass`)
- **Stock** par tier (brûlantes / chaudes / à creuser / écartées) + opportunités.
- **Prix** : médianes DVF sectorielles (terrain / maison / appart) + prix de sortie neuf (si le secteur atteint n ≥ 5).
- **Signaux de veille** agrégés (végétation haute en limite, piscine sans PC, ANC mutation, APER échéance PV).
- **Permis SITADEL** rattachés au secteur (via `idu_codes`) sur 24 mois.
- **Contexte ZAN** de la commune (ENAF consommé, Cerema).

### Décision par défaut documentée (mail hebdo / comptes = POST-M7)
L'**abonnement** à un secteur (digest hebdomadaire, compte utilisateur) relève du **mandat Auth & Plans** — **pas livré
ici** ; le carnet est **consultable à la demande**. Les tables `watch_zones` / `watched_parcels` existent déjà et seront
l'ancrage de l'abonnement le moment venu. Décision inscrite dans la réponse (`note`) et ici.

### Livrable technique
- `src/labuse/api/carnet.py` — liste + page, requêtes optionnelles guardées. `app.py` — routeur branché.
- `tests/test_carnet.py` — **5/5 verts** (422 mauvaise longueur ; POST-M7 documenté ; libellés signaux ; stock par tier ;
  liste triée brûlantes/chaudes).

**Reco d'exposition.** **Visible** (lecture sourcée). **Finding O7** : brancher la page carnet + la liste côté front
(mandat front) ; l'abonnement hebdo attend le mandat Auth & Plans (ancrage `watch_zones` prêt).

---

## O8 · Indice de tension foncière — **LIVRÉ MASQUÉ (flag) + finding** ✅ (point dur respecté)

**Indice 0-100 demande vs offre par micro-secteur** (`GET /tension-fonciere`, `src/labuse/api/tension.py`). Formule
documentée, bornée, distribution renvoyée — **mais non exposé** (`expose = false`, `masque = true`).

### Sonde de calibrabilité (le point dur du mandat)
Conformément à « si non calibrable défendablement → livré MASQUÉ + finding », l'indice est confronté à un **exutoire
INDÉPENDANT** : le **prix relatif du secteur vs sa commune** (désirabilité révélée par le marché — non utilisé comme
entrée). Résultat mesuré, **recalculé à la volée** (reproductible) :

> **Spearman(tension, prix relatif) = −0,042 (n = 616)** — corrélation nulle, sous le seuil ±0,20. **NON défendable.**

Signes concordants : la distribution **sature** (médiane = 100) car l'offre `part d'opportunités` vaut 0 sur beaucoup de
secteurs ; deux entrées sur trois sont **clairsemées** (permis 24 mois, 5 % de secteurs sans permis) ou **constantes à
l'échelle communale** (déficit SRU) — la granularité « micro-secteur » est en partie **factice**.

### Décision
**Indice MASQUÉ.** Le moteur est **livré** (formule `demande = moyenne(norm[densité permis/parcelle], norm[déficit SRU]) ;
offre = norm[part d'opportunités] ; tension = 100 × demande/(demande+offre)`, bornes [0-100], sonde intégrée) pour être
**prêt** le jour où une source de calibration existera (série de prix datée, taux d'absorption permis/stock daté) —
**jamais affiché en l'état, pas de faux signal « pour faire joli »**. Zéro exposition en fiche.

### Livrable technique
- `src/labuse/api/tension.py` — moteur + sonde Spearman + endpoint masqué (tables requises guardées `to_regclass`).
- `tests/test_tension.py` — **6/6 verts** (EXPOSE False ; Spearman monotone ±1 ; n<3 → 0 ; masqué + finding ; vide reste masqué).

**Reco d'exposition.** **MASQUÉ** — finding ci-dessus. À ré-évaluer uniquement si un exutoire calibrant apparaît et fait
passer |Spearman| au-dessus de 0,20.

---

## O9 · Pipeline de rareté ✅

**Combien d'années avant que le foncier constructible d'une commune soit épuisé ?** `GET /pipeline-rarete`
(`src/labuse/api/rarete.py`). Projection arithmétique **Estimé, caveat large**, sur les **24 communes**.

### Formule (documentée, sourcée)
```
rythme  = conso ENAF 2021-2024 / 3 ans          (ha/an, Sourcé Cerema)
budget  = 50 % de la conso 2011-2021            (enveloppe loi Climat/TRACE, Estimé doctrine)
reste   = budget − conso déjà réalisée 2021-2024
horizon = reste / rythme                         (années avant plafond ZAN, rythme constant)
```
Stock d'opportunités **détecté** (ha de brûlantes + chaudes) fourni en **contexte** (ne se substitue pas à
l'enveloppe ZAN). Statut dérivé : budget dépassé / tension forte (≤ 5 ans) / modérée (≤ 15) / détendu.

### Robustesse & honnêteté
- Rythme nul → **non projetable** (`null`, jamais un horizon inventé) ; reste ≤ 0 → **budget dépassé** (0). Table ZAN
  absente → liste vide guardée.
- **Caveat assumé** dans la réponse : rythme supposé constant ; budget = interprétation −50 % (loi TRACE assouplie) ;
  épuisement de l'enveloppe ENAF ≠ interdiction de bâtir (densification hors ENAF possible). **Outil de hiérarchisation,
  pas une date couperet.**

### Validation
24 communes triées par pression : Cilaos « budget dépassé », petites communes (Trois-Bassins, Petite-Île) en tension
forte (< 1 an), grandes communes plus détendues. Cohérent.

### Livrable technique
- `src/labuse/api/rarete.py` — `compute_rarete` + endpoint (table ZAN guardée). `app.py` — routeur branché.
- `tests/test_rarete.py` — **6/6 verts** (horizon normal ; rythme nul → non projetable ; budget dépassé ; reste absent ;
  caveat large ; table absente → vide).

**Reco d'exposition.** **Visible** avec le caveat large affiché (projection Estimé, hiérarchisation). **Finding O9** :
mettre à jour le millésime ENAF quand Cerema publie 2025 ; la trajectoire loi TRACE (assouplie) pourra affiner le budget.

---

## O10 · Surface D — LE MOTEUR seulement ✅

**Détection de BASCULES par parcelle** (changements d'état datés qui rendent une parcelle intéressante MAINTENANT).
Livré : **le moteur** (table + builder + CLI de test). `src/labuse/ingestion/surface_d.py`, table additive
`surface_d_events(idu, type, date_evenement, detail, source)`. **Zéro donnée nouvelle.**

### Sources BRANCHÉES (datées, par parcelle) — dont les 2 badges Phase A demandés
| Type d'événement | Source | Volume |
|---|---|---|
| `entree_fenetre_defisc` | `defisc_fenetres` (badge Phase A-1) | 797 |
| `pc_caduc` | `pc_caducs` (badge Phase A cycle 2) | 2 164 |
| `dpe_passoire` | `dpe_records` F/G (réserve M4.0, sourcé) | 30 |
| `permis_octroye` | `sitadel_permits` rattachés (idu_codes), 36 mois | 8 793 |
| **Total** | | **11 784 événements datés** |

Types **déclarés mais sans source datée par parcelle** à ce jour (extensibles, **non fabriqués**) : `plu_revise`,
`bodacc_pm`, `permis_voisin` (à proximité, ≠ sur la parcelle). Le moteur les accepte ; on ne les invente pas.

### Moteur seulement — notification POST-M7
Dédup `UNIQUE (idu, type, date_evenement)` ; rebuild idempotent ; sources absentes guardées `to_regclass` (→ 0, jamais un
crash). CLI : `labuse surface-d` (build) + `labuse surface-d-events --type … --limit …` (diagnostic). **La notification
(alerte / digest) est POST-M7** (mandat Auth & Plans) — non livrée ici, conformément à « LE MOTEUR seulement ».

### Livrable technique
- `src/labuse/ingestion/surface_d.py` — table + builder + `recent_events`. `src/labuse/cli.py` — `surface-d` + `surface-d-events`.
- `tests/test_surface_d.py` — **3/3 verts** (types déclarés ; défisc+caducs branchés + sources absentes → 0 ; dédup).

**Reco d'exposition.** **Moteur interne** (pas d'exposition client en partie 2 ; la notification et l'affichage
viennent post-M7 / mandat front). **Finding O10** : brancher `plu_revise` dès qu'une révision de zonage datée est
ingérée, et `bodacc_pm` via le flux BODACC personne morale ; câbler la notification sur `watch_zones` au mandat Auth.

---

## O11 · Opérations & lots — **LOT 0 PROUVÉ**, puis outil ✅ (point dur respecté)

### LOT 0 (obligatoire) — le rattachement PA/PC groupés ↔ rafales DVF **tient**
Problème : **DVF n'a AUCUNE identité vendeur** (que parcelle/valeur/date). Le rattachement est donc **multi-signal** :
(a) **déclin de propriété** du porteur PERSONNE MORALE entre millésimes fonciers (`pm_proprietaires_millesimes`,
2019-2024) = lots cédés ; (b) **permis PA/PC** sur le secteur (SITADEL) ; (c) **rafale de ventes DVF** sur le
secteur/période. **Vérifié sur des opérations réelles nommées** (PM = SIREN public) :

| Porteur (SIREN) | Secteur | Propriété | Permis | Ventes DVF |
|---|---|---|---|---|
| **CBO TERRITORIA** (452038805) | 97415000DK | 387 → 229 (−158) | PA×8, PC×200 (2013-…) | 73 (2021-25) |
| **CONCORDE** (830360418) | 97418000AW | 85 → 12 (−73) | PA×3, PC×152 | 114 (2021-25) |
| **OPHELIA** | 97420000BD | 74 → 12 (−62) | PA×1, PC×141 | 107 |
| **GRAND NATTE / ALLIANCE** | 97408/97410 | −50 / −46 | PA + PC | 40 / 98 |

Les trois signaux **s'alignent** → rattachement **circonstanciel mais convergent**. **LOT 0 = GO.** (Caveat assumé :
l'attribution d'UNE vente précise au porteur n'est pas garantie — DVF sans identité vendeur.)

### Outil livré (Lot 0 tenu)
`GET /operations` (liste) + `GET /operations/{siren}/{secteur}` (fiche). `src/labuse/api/operations.py`.
**763 opérations détectées** (283 confiance élevée, 328 moyenne, 152 faible), triées par confiance (alignement des 3
signaux). Fiche : **porteur (SIREN public, jamais un particulier)**, secteur, permis (PA/PC + années), lots au pic,
**vendus (Sourcé** = déclin de propriété), **restant (Estimé** + **caveat DVF ~6 mois** : ventes récentes non encore
publiées). Détection : PM détenant un pic ≥ 5 parcelles, PA ≥ 1 (ou PC ≥ 5), et déclin de propriété.

### Livrable technique
- `src/labuse/api/operations.py` — `detect_operations` + liste + fiche. `app.py` — routeur branché.
- `tests/test_operations.py` — **6/6 verts** (confiance 3/2/1 signaux ; vendus Sourcé / restant Estimé ; porteur PM ;
  caveat DVF ; table absente → vide).

**Reco d'exposition.** **Visible** avec confiance affichée + caveat DVF, **filtré sur la confiance « élevée/moyenne »**.
**Finding O11** : certains « porteurs » sont des entités publiques (Conservatoire du Littoral, SEM, Aéroport) qui cèdent
du foncier sans être des promoteurs privés — transparent via le SIREN ; un filtre par forme juridique / NAF affinerait.

---

## O12 · Division en or — détecteur MASQUÉ + **dossier de revue 20 cartes** ✅ (point dur respecté)

**Parcelles où le bâti occupe un coin et laisse un résiduel DÉTACHABLE constructible.** **Faux positif = péché
mortel** → l'outil est **MASQUÉ** (`EXPOSE = False`, aucune exposition client) ; le livrable qui conditionne
l'exposition est le **dossier de revue 20 cartes** : **`docs/mandats/O12_DIVISION_OR_REVUE.pdf`** (20 pages,
fond IGN BD ORTHO + tracés parcelle/bâti/lot proposé + métriques + cases ☐ vrai positif / ☐ faux positif / ☐ douteux),
**à valider visuellement par Vic**.

### Détecteur (géométrie EPSG:2975, seuils CONSERVATEURS, zéro donnée nouvelle)
`src/labuse/ingestion/division_or.py`, table masquée `division_or_candidates` :
- parcelle **1 000–6 000 m²** (place pour DEUX lots viables) ; bâti **8–45 %** de l'emprise ;
- résiduel = plus grand polygone de (parcelle − bâti bufferisé 3 m), **500 m² ≤ résiduel ≤ surface − 400 m²**
  (le lot bâti garde ≥ 400 m²) ;
- **cercle inscrit ≥ 9 m de rayon** (largeur ~18 m constructible — pas une lanière) ;
- **façade voirie du lot ≥ 12 m** (accès indépendant — le discriminant-clé).
Gain via **Score É V2** joint en SQL (Estimé, NULL si non estimable) ; `clarte` (rayon + façade) trie le dossier de
revue. Aucune affirmation de constructibilité réglementaire (reculs, prospect, servitudes) — la revue tranche.

### Résultat (2 communes pilotes)
**123 candidats** (Bras-Panon 51, Entre-Deux 72) en 130 s. Top : parcelles 3 000-6 000 m², bâti 8-18 %, résiduels
2 500-5 400 m², rayons 15-29 m. CLI : `labuse division-or --communes …` + `labuse division-or-review` (régénère le PDF).

### Deux findings d'ingénierie (honnêteté)
1. **Métrique « façade restante du lot bâti » INVALIDÉE** : `façade_parcelle − façade_lot` sort des valeurs négatives
   (médiane −56 m — artefact de la frontière du lot découpé qui suit la voirie). **Retirée du filtre, champ NULL** —
   on ne filtre pas sur un chiffre faux ; l'accès restant du lot bâti est jugé **visuellement** carte par carte.
2. **Verrous Postgres zombies** : des runs interrompus (client tué) laissaient leurs transactions serveur ouvertes
   (jusqu'à 2h47), bloquant tout `CREATE TABLE` suivant — diagnostiqué via `pg_stat_activity`, purgé
   (`pg_terminate_backend`). À savoir pour les batchs géométriques longs.

### Livrable technique
- `src/labuse/ingestion/division_or.py` — détecteur single-pass SQL (masqué). `src/labuse/api/division_review.py` —
  générateur du dossier (IGN + tracés SVG). `cli.py` — `division-or`, `division-or-review`.
- `docs/mandats/O12_DIVISION_OR_REVUE.pdf` — **le dossier de revue 20 cartes** (3,9 Mo).
- `tests/test_division_or.py` — **4/4 verts** (EXPOSE False ; seuils conservateurs présents ; métrique invalidée non
  filtrante ; commune vide → 0).

**Reco d'exposition.** **MASQUÉ jusqu'à validation visuelle du dossier par Vic.** Si la revue est bonne : étendre aux
24 communes (batch ~130 s / 2 petites communes — prévoir quelques heures île entière, ou pré-agrégation voirie),
puis exposer avec le wording conservateur. **Finding O12 (suite)** : remplacer la façade voirie sommée par une façade
« plus long segment continu » éviterait de sur-compter les parcelles d'angle (465 m sur un candidat).

---

# STOP FINAL

## Bilan de la fenêtre (13 lots + O0b)

**14 commits, arbre vert, zéro touche scoring / runs servis / golden 116.** Partie 1 (O0→O5 + STOP mi-course) mergée
par Vic ; partie 2 (O0b, O6→O12) sur `fenetre/outils-suite`, prête pour merge `--no-ff` (je ne merge jamais).

### Table des recommandations d'exposition M7 (récapitulatif final)
| Lot | Outil | Reco | Condition |
|---|---|---|---|
| O0 | Score É V2 | **Exposé** (flag levé par Vic) | `niveau_label` visible (fait, O0b) |
| O1 | Dossier banquier | **Visible** (démo) | gating Essentiel (décision Vic) |
| O2 | Scoreur d'adresse | Visible (API) | UI au mandat front |
| O3 | Anti-fiche | **Visible** | panneau fiche au mandat front |
| O4 | Traducteur PLU | **Visible** | — |
| O5 | Servitudes invisibles | **Visible** | — |
| O6 | Comparateur communes | **Visible** | tableau front au mandat front |
| O7 | Carnet de secteur | **Visible** | abonnement = post-M7 (Auth & Plans) |
| O8 | Tension foncière | **MASQUÉ** | Spearman −0,04 → attendre un exutoire calibrant (seuil ±0,20) |
| O9 | Pipeline de rareté | **Visible** | caveat large affiché |
| O10 | Surface D (moteur) | Interne | notification post-M7 |
| O11 | Opérations & lots | **Visible** | filtré confiance élevée/moyenne + caveat DVF |
| O12 | Division en or | **MASQUÉ** | validation visuelle du dossier 20 cartes par Vic |

### Tests de la fenêtre
score_e 6 · banquier 8 · scoreur 6 · anti-fiche 3 · traducteur 7 · servitudes 8 · comparateur 5(+1 skip) ·
carnet 5 · tension 6 · rareté 6 · surface_d 3 · division_or 4 = **67 verts** (0 rouge).

### Findings transverses (pour M7 et les mandats suivants)
1. **IA en repli** : crédits Anthropic épuisés → synthèse banquier (O1) et traduction PLU (O4) en repli déterministe
   honnête. Fonctionnel ; re-tester au retour des crédits.
2. **UI** : O2/O3 (et l'affichage O6/O7) affectés au mandat front (fiche réorganisée en un seul passage — décision Vic).
3. **Batchs à re-lancer après bascule de run servi** : `prix-neuf` + `score-e`, `surface-d`, `division-or`.
4. **O8** ré-évaluable uniquement si un exutoire calibrant apparaît ; **O12** attend la revue visuelle.

### Décisions attendues de Vic à ce STOP
1. **O12** : valider (ou non) le dossier `O12_DIVISION_OR_REVUE.pdf` — 20 cartes, cases à cocher.
2. **O11** : confirmer l'exposition (confiance élevée/moyenne) et l'éventuel filtre forme juridique.
3. Merge `--no-ff` de `fenetre/outils-suite`.
