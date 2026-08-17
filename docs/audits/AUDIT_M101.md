# AUDIT M101 — filtre bâti (A) et vérité des prix DVF (B) : mesures, STOP

Mesuré le 2026-08-17, run servi q_v9_m81. **Aucun changement appliqué — deux STOP, Vic
tranche au vu des mesures.**

---

## SECTION A — le filtre bâti

### A1.1 — la condition EXACTE de chaque tier (citée, pas paraphrasée)

**`declasse_bati_revele`** — `faisabilite/bati_revele.py:20-21` (seuils) et `:40-53` (règle SQL) :

> `SEUIL_REGLE_M2 = 40.0` · `SEUIL_COUCHE_VIDE_M2 = 20.0`
> `WHERE COALESCE(bd.emprise, 0) < 20 AND GREATEST(COALESCE(bd.emprise,0), c.emprise_cosia_m2) >= 20`
> `bande = CASE WHEN GREATEST(bd, cosia) >= 40 THEN 'regle' ELSE 'adjudication' END`

En français : la couche vectorielle BD TOPO voit **moins de 20 m²** de bâti sur la parcelle,
mais l'image aérienne (CoSIA 2025) en voit **au moins 40 m²** → le bâti existe, les bases
vectorielles ne l'ont pas encore ; la parcelle est déclassée (bande 20-40 m² : jamais
auto-déclassée, adjudication humaine). Consommé par `scoring/p_v2/pipeline.py:375-383`
(bande `'regle'` seule).

**`declasse_bati_sature`** — `faisabilite/filtre_bati.py:28-29` (seuils) et la décision
`'saturee'` (`:110-120` env., motifs SQL) :

> `RATIO_SATURE_PCT = 40.0` — ratio = `100 × emprise_bati_max / surface_parcelle`
> `sat_sdp = (r.pct_potentiel >= 100 AND r.sdp_residuelle_m2 = 0)`
> saturée si : `ratio > 40 %` **OU** `sat_sdp` **OU** (bâtie 15-40 % à bâti récent/année
> absente ET non divisible) — « le doute ne profite jamais au classement ».

En français : le bâti existant occupe **plus de 40 % de la parcelle**, OU la SDP autorisée
est **déjà consommée** par l'existant, OU la parcelle est moyennement bâtie (15-40 %) d'un
bâti récent (DPE) ou d'année inconnue et n'est pas divisible. Consommé par
`pipeline.py:388-395` (décision `'saturee'` seule).

**La différence de nature** : `revele` = un problème de **connaissance** (l'image contredit
la couche — le bâti vient d'apparaître) ; `sature` = un problème de **capacité** (le bâti
mesuré épuise le potentiel). Deux portes différentes, un même verdict servi (« Potentiel
épuisé »).

### A1.2 — les profils (33 897 parcelles mode B, mesure exacte)

| | n | surface méd. (p90) | SDP résiduelle méd. (p90) | pct_potentiel méd. | q méd. | SDP=0 | assiette ≥1 000 m² |
|---|---|---|---|---|---|---|---|
| `declasse_bati_revele` | 4 014 | 411 m² (1 032) | 58 m² (479) | 67 % | 30,0 | 33 % | 11 % |
| `declasse_bati_sature` | 29 883 | 480 m² (759) | 97 m² (351) | 55 % | 31,0 | 25 % | 3 % |

**Lecture : les deux populations se SUPERPOSENT largement.** Médianes voisines sur toutes
les grandeurs (surface, SDP, potentiel, score). La seule divergence est dans la **queue** :
`revele` compte proportionnellement plus de grandes assiettes (11 % ≥ 1 000 m² contre 3 %)
et plus de SDP nulles (33 % contre 25 %) — cohérent avec sa nature (le bâti « apparu » se
trouve plus souvent sur de grands terrains encore réputés nus). **La mesure ne contredit pas
la fusion au filtre** : les profils ne portent pas deux marchés distincts, ils portent deux
*preuves* distinctes du même état (« le bâti épuise/occupe le terrain »). Le tri utile qui
serait perdu est celui de la *fiabilité de la donnée* (image vs mesure), pas celui du
gisement — il reste dit sur la fiche par le motif.

### A1.3 — où les libellés apparaissent (liste complète)

Les slugs bruts (`declasse_bati_*`) ne sortent **jamais** à l'écran ; les libellés servis
sont « Potentiel épuisé · bâti saturé/révélé » et « Bâti saturé/révélé » :

| surface | libellé | réf |
|---|---|---|
| Filtre > État du sol | « Bâti saturé » / « Bâti révélé » (chips) | FiltreLabuse.tsx:25-26 (clés etatSol, app.py:1029-1042) |
| Liste > groupes/ventilation par tier | « Potentiel épuisé · bâti saturé/révélé » | frontend/src/lib/status.ts:48-50, ResultsSection.tsx:196 |
| Fiche > verdict + motif | idem + motif du filtre bâti (sature seul) | verdict_servi.py:39-41, :142 |
| Fiche > bloc Réhabilitation | porte via motif mode B (« Sans objet » hors population) | blocs_documents.py:81-87 |
| 4 documents | verdict traduit (jamais le slug brut) | flash/data.py:233, briques_pdf/pdf_premium via verdict_servi |
| Copilote > fiche_parcelle | verdict lu (même label) | copilote_v2/outils.py:112-125 |
| Export md/html | verdict.label | export.py |

Le constat du mandat est donc à préciser : ce qui fuit au filtre n'est pas le slug technique
mais le **concept interne** (« saturé »/« révélé » — deux mots que l'utilisateur ne peut pas
deviner), en chips séparées d'un tri « État du sol » qui expose la mécanique des tiers.

### A2 — proposition de formulation fiche (à valider avec l'arbitrage)

À partir des conditions exactes ci-dessus, en français lisible, sans dépasser la règle :

- porte `sature` (ratio) : « Le bâti existant occupe N % du terrain (mesuré sur BD TOPO et
  image aérienne 2025) — il ne reste pas d'assiette pour construire. »
- porte `sature` (SDP) : « La surface constructible autorisée par le PLU est déjà consommée
  par le bâti existant. »
- porte `revele` : « L'image aérienne 2025 montre un bâtiment (~N m²) que les bases
  cartographiques n'ont pas encore enregistré — le terrain n'est pas nu. »

**STOP A.** La mesure ne contredit pas la décision de principe (fusion au filtre en
« Terrain nu » / « Terrain bâti ») ; la divergence de queue (grandes assiettes révélées) est
signalée mais ne porte pas un tri de gisement. Vic confirme ou revoit.

---

## SECTION B — les prix au m²

### B1.1 — les grandeurs existantes (définition, unité, où servi)

| grandeur | définition exacte | unité | où servie |
|---|---|---|---|
| `dvf_secteur_medianes` (dvf_marche.py:59-121) | médiane par SECTEUR (insee+000+section) × `type_bien` (maison / appartement / **terrain** / autre) ; grain MUTATION, `nature='Vente'` seule, valeur >1 000 €, prix_m2 borné 50-20 000 ; **terrain = bati_m2=0 ET terrain>0** ; fenêtre « 2021-2025 (millésimes géo-DVF disponibles) » (:25) | € (médiane valeur) et €/m² (bâti pour maison/appart ; **terrain** pour nu) | fiche > en-tête prix secteur + tiroir Marché (app.py:2424) ; recherche > facette prix (app.py:1136) ; scoreur O2 |
| `sector_price` (faisabilite/bilan.py:163) | prix de SORTIE habitable neuf, rayon adaptatif 500→1000→1500 m puis commune, Q1/méd/Q3 | €/m² HABITABLE | banquier > comparables (profil `banquier_adaptatif`), bilan/calculette |
| `dvf_prix_sortie_neuf` (ingestion/dvf_prix_neuf.py:204-220) | médiane du NEUF par commune/secteur via croisement PC ACHEVÉS × DVF ; préséance override>secteur>commune>île ; communes social-dominantes : NON CALCULABLE dit | €/m² | bilan promoteur, banquier (prix de sortie), Marché MU1 ligne neuf |
| médiane terrain nu M79 (faisabilite/marche_commune.py:115) | €/m² terrain nu du secteur, garde-fous plo/phi 150/325, n≥5 (secteur) / ≥3 | €/m² terrain | outil Marché MU1 (« prix terrain nu par zone U/AU »), argumentaire |
| `voisinage_100m` (profil) | médiane BRUTE de transaction, 100 m / 36 mois, n≥3, « signal, pas référence » | € (transaction) | fiche voisinage, docs |
| `comparables_premium` (profil) | €/m² bâti PAR VENTE (date·distance·surface·prix), 500 m/3 ans, n≥8 | €/m² bâti | premium > comparables |

Les 4 profils sont figés dans `config/dvf_profils.yaml` (+ `reserve_methode` unique +
garde-fou 2×). Point d'appel unique `marche_service` respecté (vérifié M96).

### B1.2 — ce que DVF permet de distinguer

**Terrain nu vs bâti : OUI, déjà porté et déjà servi.** La distinction existe par
construction (`type_bien='terrain'` = 0 m² bâti sur la mutation) dans `dvf_secteur_medianes`
ET dans la médiane M79. **Découverte de la mesure** : `nature_mutation` porte aussi une
catégorie explicite « **Vente terrain à bâtir** » (995 mutations) qui est aujourd'hui
**EXCLUE** des médianes (filtre `nature_mutation = 'Vente'` strict, dvf_marche.py:87) — des
ventes de terrain nu qualifiées par l'acte lui-même n'entrent pas dans la médiane terrain.
À arbitrer : les inclure (elles renforcent l'effectif nu) ou documenter l'exclusion.

**Neuf vs ancien : PARTIELLEMENT, et il faut le dire ainsi.**
- Le NEUF est identifiable de deux façons prouvées : la nature d'acte « Vente en l'état
  futur d'achèvement » (**VEFA, 2 686 mutations** — Sourcé, c'est l'acte qui le dit) et le
  croisement PC-achevés×DVF déjà en production (`dvf_prix_sortie_neuf`). DVF ne porte AUCUNE
  année de construction (colonnes mesurées : id_mutation, date, nature, valeur, commune,
  parcelle, type_local, surfaces, culture, position, millésime).
- L'« ANCIEN » n'est PAS isolable proprement : le complément non-VEFA mélange l'ancien et le
  récent-revendu (une maison de 2023 revendue en 2025 est une « Vente » ordinaire).
  L'inférence par DPE (annee_construction, ~914 points géocodés) est anecdotique en
  couverture. **Étiquette honnête possible : « hors VEFA », jamais « ancien ».**

### B1.3 — les volumes (fenêtre 3 ans, mutations distinctes par commune)

Nu (`bati=0`, terrain>0) et bâti-logement : **servables dans les 24/24 communes** au grain
commune (min nu = 59 à Saint-Philippe, min bâti = 65 ; tout le reste ≥ 66) — le seuil n≥8
se joue donc au grain SECTEUR, comme aujourd'hui (discipline inchangée).

VEFA : **très concentré** — ≥ 8 mutations/3 ans dans **11 communes seulement**
(97411:378, 97415:304, 97422:169, 97413:123, 97416:92, 97408:85, 97404:56, 97418:35,
97423:33, 97405:21, 97414:18) ; 13 communes sous le seuil dont 5 à ZÉRO (97420, 97406,
97403, 97417, 97419…). Une distinction « neuf VEFA » au grain commune n'est servable que
là où l'effectif l'autorise — ailleurs « échantillon insuffisant » avec la grandeur.

### B1.4 — cohérence avec les profils figés

Toute distinction retenue s'inscrit dans `config/dvf_profils.yaml` (nouveau champ de
grandeur d'un profil existant ou nouveau profil AVEC question/rayon/fenêtre/raison/seuil),
lue par `marche_service` — aucun chemin parallèle. Candidats naturels au vu de la mesure :
- étendre `secteur_dossier` (sa grandeur dit déjà « bâti ET terrain nu ») d'une composante
  « neuf VEFA » à seuil n≥8 ;
- ou un profil `neuf_vefa` dédié (question : « à quel prix se vend le neuf en VEFA ici ? »).

**STOP B.** Vic tranche : (1) la distinction servie (nu/bâti déjà là ; neuf = VEFA seul,
« hors VEFA » jamais étiqueté « ancien ») ; (2) le sort des 995 « Vente terrain à bâtir »
exclues des médianes ; (3) le grain (commune vs secteur) et le profil porteur.

---

## Arbitrages rendus (Vic, 17/08/2026) et exécution (A2 · B2 · C)

### A2 — appliqué

- **Filtre** : deux entrées « Terrain nu » / « Terrain bâti » (FiltreLabuse.tsx), partition
  EXACTE sur un critère unique (emprise bâtie, seuil 5 % existant — app.py etat_sol) :
  nu = pas d'emprise ≥ 5 % connue, bâti = emprise ≥ 5 %. Clés legacy
  (bati_marginal/sature/revele) pliées sur « bati » côté front (filters.ts) ET côté API —
  jamais un no-op silencieux. Les tiers internes ont quitté l'interface de filtrage ; la
  fiabilité (désaccord BD TOPO/CoSIA) reste dite en fiche par le motif.
- **Fiche, bloc Réhabilitation** : la PORTE réelle est servie par `compute_mode_b`
  (`_porte_mode_b`, faisabilite/bilan.py — point unique lu par la fiche ET les 4 documents
  via rehab_bloc). Les formulations appliquées, calées mot à mot sur les règles :
  ratio > 40 % → « Le bâti existant occupe N % du terrain… » ; SDP consommée → « La surface
  constructible autorisée par le PLU est déjà consommée… » ; 15-40 % récent/année inconnue
  non divisible → « Le terrain est bâti (N % d'emprise) d'un bâti récent ou d'année
  inconnue, et n'est pas divisible… » ; révélé → « L'image aérienne 2025 montre un bâtiment
  (~N m²) que les bases cartographiques n'ont pas encore enregistré… ». Cache absent = pas
  de phrase inventée. Les caches (preuve brute) ne sont pas réécrits.

### B2 — appliqué

- **« Vente terrain à bâtir » dans la médiane terrain** (dvf_marche.py) : condition 1
  vérifiée AVANT application — écart par commune ≤ **+11 %** (Sainte-Marie ; médiane des
  écarts ~2 %, tableau complet en historique de mesure), aucun > 20 % → pas de signalement
  bloquant. Les 34/995 VTB portant du bâti n'entrent **nulle part**. Condition 2 : le
  filtre `'Vente'` strict excluait aussi VEFA (2 686 — reste exclue du bâti générique, le
  neuf a son profil dédié), Échange (233), Adjudication (190), Expropriation (32) — hors
  marché de gré à gré, exclusion maintenue, rien d'autre intégré. Médianes rejouées :
  2 359 lignes / 850 secteurs / 40 383 ventes.
- **Profil `neuf_vefa` DÉDIÉ** (config/dvf_profils.yaml + marche_service.DVF_NEUF_VEFA +
  ingestion/dvf_marche.neuf_vefa_commune) : grain commune, fenêtre 3 ans, n≥8 (seuil lu de
  la config), grandeur nommée « médiane €/m² bâti des ventes en l'état futur d'achèvement
  (VEFA — le neuf que l'acte déclare) », réserve de méthode jointe. Sous le seuil :
  « Échantillon insuffisant (N ventes VEFA sur 3 ans, seuil 8) » servi À LA PLACE du
  chiffre. Servi : fiche > tiroir Marché (payload dvf_parcelle.neuf_vefa). Le mot
  « ancien » n'apparaît nulle part.

### C — vérification

- Partition : nu **205 814** + bâti **225 849** = **431 663** = parc entier (disjoints par
  construction, somme exacte mesurée) ; legacy `bati_sature` → 225 849 (plié).
- Recette : porte servie sur une saturée 15-40 (« Le terrain est bâti (16 % d'emprise)… »,
  97401000AD0573) et une révélée (« ~89 m²… », 97410000BX0251) ; 3 prix Saint-Denis
  (terrain 350 €/m² n=5 · maison 1 423 n=12 · appart 2 156 n=10 · neuf VEFA 5 850 n=115) ;
  Cilaos rural : VEFA 0 vente → « échantillon insuffisant » avec la grandeur.
- Grep : aucun slug interne rendu (la seule occurrence « saturé/révélé » du panneau est un
  commentaire de code) ; golden 0 FAIL ; tsc 0 ; build OK ; suite complète (résultat au
  commit).
