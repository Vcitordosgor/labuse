# AUDIT M108 — la cartographie des capacités du Copilote

Audit pur (aucune correction). Mesuré le 17/08/2026 sur la base réelle et l'API live
(chaque demande rejouée, réponse exacte citée). Ce document est la **carte de référence**
pour tous les mandats Copilote à venir.

Le constat déclencheur : « Combien de parcelles en procédure judiciaire à Saint-Denis »
→ « Je n'ai pas d'outil dédié pour cette demande. » La donnée existe (facette servie),
le refus est un défaut de câblage du routeur. Cet audit mesure l'étendue exacte du défaut.

---

## PHASE 1 — ce que le Copilote SAIT faire (inventaire fichier:ligne)

### 1.1 Le routeur d'intention — `copilote_v2/router.py`

- **7 intentions** (`INTENTS`, ligne 24) : QUESTION, OUTIL, RECHERCHE, VERIFICATION,
  VEILLE, PROJET, HORS_SUJET.
- **12 paramètres extractibles** (`PARAM_KEYS`, ligne 27) — LA liste blanche, une clé
  hors liste est élaguée (ligne 164) : `commune, idu, zone, surface_min, surface_max,
  budget_eur, prix_eur, entreprise, programme_logements, perimetre, veille_type, sujet`.
- Déclencheurs (prompt `ROUTER_SYSTEM`, ligne 63) : « Combien » → QUESTION (règle dure,
  ligne 106) ; « trouve/liste/des parcelles » → RECHERCHE ; IDU + prix → VERIFICATION ;
  « préviens-moi/surveille » → VEILLE ; « nouveau projet » → PROJET ; maire/élu/notaire/
  fiscalité → QUESTION (ligne 98-102, l'aval décide web/refus).
- **Le routeur n'a AUCUN paramètre pour un critère d'événement** (BODACC, procédure,
  friche, défisc, copro…). `veille_type ∈ permis|ventes|procedure_plu|bodacc` (ligne 124)
  n'existe que pour l'**alerte** (VEILLE), jamais pour un comptage QUESTION.

### 1.2 Les outils SQL (QUESTION) — `copilote_v2/outils.py` + `answering.py`

Huit fonctions dans `OUTILS` (outils.py:323). Mais le sélecteur QUESTION ne voit que le
**CATALOGUE** de `answering.py:37` — **7 outils** (`divisibilite` est dans `OUTILS` mais
**absent du CATALOGUE** : injoignable en QUESTION, réservé à l'enrichissement `_division`).

| outil | fichier:ligne | paramètres acceptés | point de calcul |
|---|---|---|---|
| `compter_parcelles` | outils.py:96 | **commune, surface_min, surface_max, tier, personne_morale** | facette `filtre()`/`FiltreCriteres` |
| `parcelles_par_entreprise` | outils.py:131 | q (nom ou SIREN) | `patrimoine` (DGFiP) |
| `fiche_parcelle` | outils.py:165 | idu | `_q_v2_fiche` |
| `stats_commune` | outils.py:182 | commune | `commune_contexte` (SRU/INSEE) |
| `delais_instruction` | outils.py:202 | commune | `velocite` (Sitadel) |
| `marche` | outils.py:227 | commune | `build_marche_commune` (DVF/Sitadel/DHUP) |
| `recherche_web` | outils.py:251 | question (verbatim) | web natif Anthropic |
| `divisibilite` | outils.py:293 | idu | `module_division` — **hors CATALOGUE** |

**Le point critique** : `compter_parcelles` appelle la facette complète `FiltreCriteres`
(outils.py:107) mais n'expose que **5 critères** sur les ~37 qu'elle porte (cf. Phase 2).

### 1.3 L'aiguillage OUTIL — `answering.py:382` (`_OUTIL_MAP`)

Onze familles d'outils atteignables par mots-clés (fold accent) :

| mots-clés | outil ouvert | prefill |
|---|---|---|
| assembl | assemblage | parcelPrefill |
| faisabil / constructib / capacit | programme (Faisabilité) | parcelPrefill |
| charge fonci / combien payer / marge | calculette-fonciere | calcPrefill |
| courrier / ecrire au proprio | courriers | idu |
| comparer / cote a cote | comparer | selection |
| reglement / annuaire plu | plu-annuaire | pluPrefill |
| lettre de zonage / verification de zonage | lettre-zonage | idu |
| procedure plu / revision plu / sursis / nouveau plu | verif-procedure | idu |
| due diligence / controle avant achat | duediligence | idu |
| servitude | o5-servitudes | idu |
| remonter le temps / en 1950 / historique du site | temps | idu |

`division/decoup/lotir` → `_sans_outil` → `_division` (answering.py:445) : ne tranche pas,
dit le règlement + enrichit du score géométrique. Toute autre action → `_sans_outil`
(answering.py:430) : « Je n'ai pas d'outil dédié… » — **la phrase exacte du constat**.

### 1.4 La mission RECHERCHE — `copilote/interpreteur.py` + `prompts.py:16`

Le brief `SORTIE_SCHEMA` (prompts.py:16) n'accepte que **7 critères** :
`communes, programme{logements|sdp}, budget_max_eur, contraintes{exclure_ppr_rouge,
exclure_abf, zones[U|AU|A|N]}, surface_min_m2`, plus `criteres_non_appliques` (liste dite
au client). Le prompt (prompts.py:97) dit de ne flaguer que la **proximité spatiale** et
« déjà en vente » — il **ne mentionne aucune des autres facettes servables** (friche,
procédure, défisc…), qui sont donc **silencieusement abandonnées** (preuve Phase 3).

### 1.5 Les actions — `answering.py` + `api/copilote_v2.py`

- PROJET → crée un projet réel (missions_lourdes.preparer_projet + endpoint).
- VEILLE → pose une veille (event_log, M104).
- OUTIL → ouvre l'outil pré-rempli (porte + prefill → `setModule`).
- RECHERCHE → lance le run de scoring (mission M26-A).
- Guidage fiche : `ouvrirFiche(idu)`. **Pas de guidage** vers les documents (PDF/export)
  ni vers la section **Surveillance** (M104) — aucune porte.

### 1.6 La recherche web — `outils.py:251`, hiérarchie `answering.py:78`

Dernier recours : un fait PUBLIC hors base (élu, organigramme, actualité réglementaire)
de La Réunion, marqué `web` (jamais Sourcé/Estimé). La base prime toujours (règle M78-ter).
**Mais l'aiguillage échoue à la respecter quand le critère de comptage manque** (Phase 3,
cas « friches »).

---

## PHASE 2 — ce que le PRODUIT sait faire que le Copilote ignore

### 2.1 La matrice CRITÈRES DE COMPTAGE (le cœur de l'écart)

La facette `FiltreCriteres` (api/app.py:1170) porte **~37 critères filtrables + 8 signaux
de vie** (`signaux`, app.py:1223 : procedure, permis_actif, permis_caduc, defisc, nu_pm,
friche, cession, assemblage). Le Copilote (`compter_parcelles`) en expose **5**.

| critère servi (facette / Filters) | comptable au Copilote ? | preuve live |
|---|---|---|
| commune | ✅ | « Combien de parcelles à Saint-Paul ? » → **51 129** |
| surface_min/max | ✅ | (via compter_parcelles) |
| tier brûlante/chaude/opportunités | ✅ | « brûlantes à Saint-Paul » → **25** |
| personne_morale | ✅ | « personnes morales à Saint-Pierre » → **7 868** |
| **evenement (BODACC rouge) / procédure** | ❌ REFUS | « procédure judiciaire à Saint-Denis » → *« Je n'ai pas d'outil dédié »* |
| **signaux=friche** | ❌ WEB (pire) | « friches à Saint-Paul » → **recherche web**, « pas de chiffre précis » |
| **adresse_absente** | ❌ REFUS | « sans adresse à Saint-Pierre » → *« Je n'ai pas d'outil dédié »* |
| **defisc_active** | ❌ REFUS | « en défiscalisation à Saint-Leu » → *« Je n'ai pas d'outil dédié »* |
| **copro / hors_copro** | ❌ REFUS | « copropriétés à Saint-Denis » → *« Je n'ai pas d'outil dédié »* |
| **constructibilite** | ⚠️ MISCOMPTE | « constructibles à Saint-André » → **22 600** (= TOTAL commune, critère lâché) |
| **zone_plu / zonage** | ⚠️ MISCOMPTE (honnête) | « en zone U à Saint-Benoît » → **21 671** (TOTAL) + « le filtre zone U n'a pas pu être appliqué » |
| **renouvellement** | ❌❌ MISCOMPTE MUET | « renouvellement urbain à Saint-Denis » → **1 970** servi comme tel ; le VRAI compte = **213** (§3.2) |
| etat_societe (cessée/radiée/procédure) | ❌ REFUS (inféré, même famille) | — |
| proprietaire_type (bailleur, pp) | ⚠️ partiel (pm seul via personne_morale) | — |
| score_min, sdp_min/max, capacite_min, mult_min, rang_max | ❌ (aucun param) | — |
| sous_densite, division_or, npnru, pc_caduc | ❌ (aucun param) | — |
| budget_max, charge_min/max, prix_marche_min/max, marche_fiable, ca_min, mode_b_rentable, marge_min | ❌ (facettes économiques, aucun param) | — |
| veille (succession) | ❌ (aucun param) | — |

**Écart chiffré : sur ~37 critères de comptage servis à l'écran, 5 sont interrogeables
via le Copilote (≈ 14 %).** Les 3 comportements d'échec, du moins au plus grave :
refus honnête → miscompte flagué → **miscompte muet (chiffre faux servi comme vrai)**.

### 2.2 Les 28 outils du registre — `frontend/.../outils/registry.ts`

| outil (num) | atteignable par le Copilote ? | voie |
|---|---|---|
| scoring-v2 (M25) | ✅ | RECHERCHE (la mission) |
| programme (M22) | ✅ | OUTIL « faisabilité/constructibilité » |
| calculette-fonciere (M23) | ✅ | OUTIL « charge foncière/marge » |
| duediligence (M10) | ✅ | OUTIL « contrôle avant achat » |
| verif-procedure (O11) | ✅ | OUTIL « procédure/révision PLU » |
| plu-annuaire (O13) | ✅ | OUTIL « règlement/annuaire PLU » |
| o5-servitudes (O5) | ✅ | OUTIL « servitude » |
| comparer (A8) | ✅ | OUTIL « comparer » |
| assemblage (M16) | ✅ | OUTIL « assembler » |
| courriers (M09) | ✅ | OUTIL « courrier » + refus proprietaire_pp (porte) |
| temps (M08) | ✅ | OUTIL « remonter le temps » |
| patrimoine (M02) | ✅ (donnée) | QUESTION parcelles_par_entreprise |
| marche (MU1) | ✅ (donnée) | QUESTION marche |
| velocite (M05) | ✅ (donnée) | QUESTION delais_instruction |
| division (M01) | ~ (répond, n'ouvre pas) | `_division` |
| **fantome (M07)** | ❌ | *« parcelles fantômes » → carte PRÉCISION « je ne suis pas sûr de comprendre »* |
| **bailleur (M06)** | ❌ | *« bailleurs sociaux » → carte PRÉCISION « je ne comprends pas votre besoin »* |
| **scoreur-adresse (O2)** | ❌ | aucun mot-clé |
| **o6-comparateur (O6)** | ❌ | aucun mot-clé |
| **barometre (M18)** | ❌ | aucun mot-clé |
| **permis (M03)** | ❌ | (VEILLE alerte, l'outil ne s'ouvre pas) |
| **promesses (M04)** | ❌ | aucun mot-clé |
| **zan (M17)** | ❌ | aucun mot-clé |
| **renouvellement (MR1)** | ❌ | aucun mot-clé (+ miscompte §3.2) |
| **o9-rarete (O9)** | ❌ | aucun mot-clé |
| **simulplu (M15)** | ❌ | aucun mot-clé |
| **o10-bascules (O10)** | ❌ | *« qui a basculé en brûlante ce mois-ci » → « Je n'ai pas d'outil dédié »* |
| **o7-carnet (O7)** | ❌ | aucun mot-clé |

**≈ 15 des 28 outils atteignables ; 13 invisibles au Copilote.**

### 2.3 Les surfaces

- **Carte** : le Copilote n'ouvre PAS la carte filtrée (les critères de comptage ne
  produisent pas de vue carte ; un « montre sur la carte les X » n'existe pas).
- **Fiche** : ✅ `ouvrirFiche(idu)`.
- **Documents / exports** : ❌ aucune porte (sauf lettre-zonage via mot-clé, PDF direct).
- **Surveillance (M104)** : ❌ aucune porte (VEILLE pose une veille mais n'ouvre pas la
  section ni ne crée un secteur dessiné).

---

## PHASE 3 — les défauts de conversation (preuves)

### 3.1 Contamination de contexte (brief_effectif, M107)

Mécanisme : `answering.py:370-372` — le brief effectif RECHERCHE = les 4 derniers tours
CLIENT du fil **concaténés** au message courant. **Aucune détection de rupture de sujet.**

Preuve (même conversation, 2 RECHERCHE de sujets différents) :

```
T1 : « trouve des terrains de plus de 20000 m² à Saint-Paul pour 30 logements »
     → recap : « Saint-Paul, 30 logements, ≥ 20000 m², hors PPR rouge »
T2 : « montre-moi des friches en zone U à Cilaos pour 8 logements »
     → recap : « Saint-Paul, Cilaos, 38 logements, ≥ 20000 m², zones U, hors PPR rouge »
     → brief_effectif : « trouve des terrains de plus de 20000 m² à Saint-Paul pour 30
        logements, montre-moi des friches en zone U à Cilaos pour 8 logements »
```

Trois contaminations dans un seul tour : **Saint-Paul reste** (devrait être Cilaos seul) ·
**38 logements = 30+8 SOMMÉS** · **≥ 20000 m² hérité** (T2 ne parle pas de surface) · et
**« friches » abandonné** (ni appliqué, ni flagué). C'est le 2ᵉ défaut du constat, reproduit.

**Critère de rupture proposé (NON implémenté)** : le brief effectif ne doit hériter d'un
tour antérieur QUE si le tour courant est une *continuation* (réponse à une clarification,
correction « et à X ? », ajout de critère). Signaux de rupture : nouvelle commune explicite
+ nouveau verbe de recherche (« montre/trouve »), ou nouveau programme chiffré. Un tour qui
porte sa propre commune ET son propre programme est un sujet neuf → ne rien hériter. Le
routeur sait déjà distinguer héritage vs correction (gate 45) — le brief effectif, lui,
concatène en aveugle. La rupture devrait se décider au même endroit que l'héritage.

### 3.2 Le miscompte muet — le défaut le plus grave

Quand `_select_tool` choisit `compter_parcelles` pour une demande dont le critère n'est
pas un paramètre, le critère est **lâché en silence** et le TOTAL (ou un sous-total) est
servi comme s'il répondait. L'anti-invention ne l'attrape pas : le nombre EXISTE bien dans
le résultat d'outil — il répond juste à une autre question.

Preuve mesurée (facette live vs réponse Copilote) :

```
« Combien de grandes parcelles en renouvellement urbain à Saint-Denis »
  → Copilote : « 1 970 parcelles d'au moins 5 000 m² identifiées comme relevant du
                 renouvellement urbain »
  → facette surface_min=5000 (SANS renouvellement)          = 1970   ← ce qui a été compté
  → facette surface_min=5000 + renouvellement=true          = 213    ← la VRAIE réponse
```

**Chiffre servi 9,2× trop haut, présenté comme si le critère était appliqué.** Le cas
« zone U » (§2.1) est le même mécanisme mais HONNÊTE (le formuler a dit « n'a pas pu être
appliqué ») ; « renouvellement » et « constructibles » ne l'ont pas dit. La différence
tient au hasard de formulation du modèle, pas à une garantie code.

### 3.3 Classement d'un échantillon de refus

| demande | classe | preuve |
|---|---|---|
| « procédure judiciaire à Saint-Denis » | **refusée à tort** (facette servie) | aucun_outil |
| « sans adresse », « défiscalisation », « copropriétés » | **refusées à tort** | aucun_outil ×3 |
| « friches à Saint-Paul » | **refusée à tort + détournée au web** | recherche_web, rien trouvé |
| « constructibles », « zone U », « renouvellement » | **exécutées FAUX** (§3.2) | chiffre erroné servi |
| « combien de parcelles à Saint-Paul » | exécutée juste | 51 129 |
| « brûlantes », « personnes morales » | exécutées justes | 25 · 7 868 |
| « vaudra dans 10 ans » | refusée à raison **avec voie** | projection → marché constaté |
| « propriétaire de la parcelle » | refusée à raison **avec voie** | proprietaire_pp → courrier |
| « qui a basculé en brûlante ce mois-ci » | refusée à tort (o10-bascules existe) | aucun_outil |

Télémétrie agrégée (`copilote_telemetrie`, session d'audit incluse) : `aucun_outil` = **31**,
`projection` = 17, `proprietaire_pp` = 17, `web_servi` = 12, `critere_non_traduisible` = 2.
Le refus dominant est `aucun_outil` — cohérent avec l'écart de la Phase 2.

---

## PHASE 3-ter — refus mal gabarités, exemples d'accueil

### 3ter.1 « Qui est le maire de X » — la prémisse est renversée

Le maire **fonctionne** aujourd'hui : QUESTION → recherche_web.
- « Qui est le maire de Saint-Denis ? » → *« Ericka Bareigts, mandat 2020-2026… »* (web).
- « Qui est le maire de Saint-Benoît ? » → *« ⚠️ Les sources divergent… 22 mars 2026… »* (web).

La prémisse « le routeur n'atteint pas l'intention VÉRIFICATION qui existe pour ça » est
**fausse** : dans ce moteur, **VERIFICATION = évaluer une parcelle face à un prix**
(router.py:78, `recap_verification`), pas un fact-check. Le maire route correctement
QUESTION → web (router.py:98-102 le prévoit explicitement). La gate routeur 45 msgs couvre
la famille « élu/collectivité » (classée QUESTION). **Rien de cassé côté routeur.**

Le vrai artefact est à l'**accueil** : l'exemple #4 est ÉTIQUETÉ « Vérifier »
(AccueilCopilote.tsx:31) alors qu'il route QUESTION→web. L'étiquette induit en erreur (elle
a produit la prémisse du mandat), mais la réponse est juste. Défaut de libellé, pas d'intention.

### 3ter.2 Refus qui empruntent le gabarit PRÉCISION (carte + champ de réponse)

`recap_recherche` (recap.py:61-70) enveloppe **toute** clarification de l'interpréteur —
y compris un hors-sujet (`champ_manquant="besoin"`) — dans une `clarification_recap` =
carte PRÉCISION AVEC un champ de réponse. Un concept que le PRODUIT possède mais que le
Copilote ne connaît pas devient un « je ne comprends pas, donnez-moi un besoin foncier »
qui **offre un champ alors qu'il ne sait pas quoi en faire** :

```
« Montre-moi les parcelles fantômes à Saint-Paul »  (l'outil fantôme M07 existe)
  → carte PRÉCISION + champ : « Je ne suis pas sûr de comprendre "parcelles fantômes" … »
« Quelles parcelles de bailleurs sociaux à Saint-Denis »  (l'outil bailleur M06 existe)
  → carte PRÉCISION + champ : « je ne comprends pas encore votre besoin foncier … »
```

Le routeur HORS_SUJET pré-filtre le vrai hors-sujet (« recettes de cari » → refus sobre,
sans champ), donc la carte-précision-refus se déclenche surtout sur les **concepts
produit non reconnus** (fantôme, bailleur) — exactement les outils invisibles de la Phase 2.
Les refus QUESTION (proprietaire_pp, projection, aucun_outil, hors_sujet) rendent, eux,
une réponse plate SANS champ (answering.py:299-311) — corrects.

### 3ter.3 Les six exemples de l'accueil rejoués

| # | exemple (étiquette) | résultat | verdict |
|---|---|---|---|
| 1 | « Quelles parcelles appartiennent à la SIDR ? » (Chercher) | 16 parcelles, 904 m² | ⚠️ exécuté mais **entité douteuse** : le seul « SIDR » de l'index personnes morales est « COPROPRIETAIRES DU LOT SIDR DE TERRE SAINTE » (16) — le bailleur SIDR lui-même est **absent de l'index sous ce nom** (vérifié : 2 lots copro « SIDR » seulement). L'exemple sert une entité qui n'est pas celle attendue, sans le dire |
| 2 | « Combien de parcelles à Saint-Paul ? » (Chercher) | 51 129 | ✅ juste |
| 3 | « Préviens-moi de tout nouveau permis à Saint-Paul » (Veiller) | veille posée | ✅ juste |
| 4 | « Qui est le maire de Saint-Denis ? » (Vérifier) | Ericka Bareigts (web) | ✅ juste — mais étiquette « Vérifier » trompeuse (§3ter.1) |
| 5 | « Qui gère les dossiers de financement des bailleurs sociaux à la Région ? » (Vérifier) | réponse web structurée | ✅ juste (web) |
| 6 | « Je veux écrire au propriétaire de cette parcelle » (Agir) | clarification « quelle référence ? » | ⚠️ sur l'accueil « cette parcelle » n'a pas de référent → demande l'IDU (l'exemple suppose un contexte fiche absent de l'accueil) |

Aucun exemple ne se solde par un refus dur — mais #1 sert la mauvaise entité et #6 tourne
à la clarification. Un exemple servi qui déçoit reste une contradiction douce du produit.

---

## PHASE 4 — écarts triés par valeur (pour l'arbitrage Vic)

Aucune correction faite. Priorisation proposée, du plus dommageable au moins :

1. **Le miscompte muet (§3.2)** — GRAVITÉ MAXIMALE : un chiffre FAUX servi comme vrai
   (1 970 pour 213). Ce n'est pas un refus, c'est une désinformation. Tant que
   `compter_parcelles` accepte un critère qu'il ne peut appliquer, il faut soit l'exposer,
   soit refuser explicitement — jamais servir le total en silence.
2. **Les critères d'événement au comptage (procédure/BODACC, friche, défisc, sans adresse,
   copro)** — le cas du constat : facettes servies à l'écran, refusées au Copilote, et pour
   « friche » détournées au web. Ce sont les critères d'un prospecteur (signaux de vie).
   Fort volume de demandes légitimes (`aucun_outil` = refus n°1).
3. **La contamination de sujet (§3.1)** — sommes de logements, communes et surfaces
   fantômes ; mine la confiance dans le récap. Critère de rupture proposé §3.1.
4. **Les 13 outils invisibles (§2.2)** — dont fantôme et bailleur (concepts produit forts),
   o10-bascules, barometre, zan. Priorité aux 2-3 les plus demandés.
5. **La carte-précision-refus (§3ter.2)** — un refus ne devrait pas offrir un champ ;
   un concept produit non reconnu devrait dire « voici l'outil X » plutôt que « je ne
   comprends pas ».
6. **Défauts doux** : étiquette « Vérifier » du maire (§3ter.1), entité SIDR (§3ter.3),
   `divisibilite` hors CATALOGUE (§1.2), guidage absent vers carte/documents/Surveillance
   (§2.3), rendu JSON brut du marché sans données (§2.2, « tendance 5 ans »).

**Aucune correction dans ce mandat — Vic arbitre ce qu'on branche et dans quel ordre.**
