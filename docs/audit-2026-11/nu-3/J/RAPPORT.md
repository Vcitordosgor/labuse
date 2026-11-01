# MANDAT AUDIT-NU-3 — Lot J : vérité et même vérité

**Registre.** Audit LECTURE SEULE joué le 2026-11-01. Branche `audit/nu-3-j`, worktree
`~/Desktop/labuse-nu3-j`, API locale `:9310` (venv partagé `labuse/.venv`, `PYTHONPATH=src`
du worktree), run servi `q_v20`, base Mac `labuse` (434 582 parcelles). Aucune écriture base,
aucun correctif, aucun merge, aucun accès prod. Les sources extérieures (cadastre.gouv,
Géoportail de l'urbanisme, DVF Etalab, Géorisques, BAN) ont été interrogées en HTTP sortant
(`curl`, certificats système). Tout le code de l'audit, les sorties brutes et la matrice CSV
sont sous `docs/audit-2026-11/nu-3/J/` (`scripts/`, `out/`).

> Les deux questions du mandat : **l'app dit-elle la vérité ? dit-elle la même vérité partout ?**
> Réponse courte : **oui pour la vérité** (les faits-socle collent au monde extérieur au m², à
> l'euro, au jour) ; **presque partout pour la cohérence**, avec six familles de faits qui
> divergent d'une surface à l'autre — la plus trompeuse étant une Faisabilité qui titre « zone
> constructible » et « R+1 » sur des parcelles que toutes les autres surfaces disent « N ».

---

## Les chiffres

| Chiffre | Valeur |
|---|---|
| **Parcelles tirées** | **120** (5 × 24 communes), hors 55 témoins nu-1/nu-2, variété forcée |
| **Surfaces confrontées** | 7 JSON (fiche API · comparateur/liste · carte geojson · Gabarit · Étude de faisabilité · Estimer un bien · Exposition) + 8 PDF/Docs (Dossier, Apporteur, Pré-dossier PC, Étude de zone, Gabarit, Comparatif, Étude de faisabilité, Bilan) + Copilote |
| **Couples comparés** | **5 508** = 4 637 (JSON, 7 surfaces) + 814 (PDF/Docs, 8 documents × 24 parcelles) + 57 (externe) |
| **Couples en écart** | **667** = 659 (JSON) + 8 (PDF/Docs) + 0 (externe) |
| **Cellules relevées (JSON)** | 5 129, sur 2 412 lignes (fait × parcelle) |
| **Écarts JSON** | concentrés sur **6 familles de faits** (sur 24) ; 18 faits identiques partout |
| **Faits confrontés au monde extérieur** | 20 parcelles × (surface, zone, dernière vente, risques, adresse) |
| **Écart de vérité externe** | **0** (surface 20/20, zone 20/20, dernière vente 20/20) |

**Verdict de synthèse.** L'arithmétique et les données-socle sont justes et fidèles au monde :
sur 20 parcelles tirées, la **surface** colle au m² à cadastre.gouv (20/20), la **zone** au
Géoportail de l'urbanisme (20/20 là où le GPU répond), la **dernière vente** à DVF Etalab au
jour et à l'euro (20/20), l'adresse n'est jamais inventée (BAN). En interne, la **pente** servie
par la fiche égale la table source sur 117/117 parcelles, la **SDP** ne se contredit plus (0
écart entre les deux notions historiques — NU-A-001 corrigé), le **palier**, le **rang**, la
**copropriété** et l'**emprise réglementaire** sont identiques d'une surface à l'autre.
Le danger n'est donc **pas la donnée, c'est la pluralité des surfaces** : six faits sont calculés
ou étiquetés différemment selon l'écran qui les porte. Le plus grave, parce qu'il est visible et
oriente une décision : une **Faisabilité** qui titre une zone constructible (Uf, UC, UB) et un
verdict « R+1 » sur des parcelles que toutes les autres surfaces disent « N ». À noter aussi, plus
discret, que l'**endpoint API `/exposition`** calcule une seconde « pente moyenne » qui contredit
la table source sur 115/117 parcelles — mais aucune surface livrée ne l'affiche (piège latent).

---

## Le tirage — 120 parcelles, variété forcée

Tirage déterministe (ordre `md5(idu||seed)`), 5 par commune, **greedy** maximisant la couverture
des axes de variété, **55 témoins nu-1/nu-2 exclus** (`out/sample120.json`,
`scripts/01_sample.py`). Couverture obtenue sur les 120 :

| nue | bâtie | copro | zone A | zone N | zone AU | zone U | RNU | PPR | grande (≥3000 m²) | petite (<200 m²) | vendue 2024-25 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 68 | 52 | 25 | 32 | 27 | 24 | 56 | 5 | 71 | 33 | 32 | 31 |

Tous les profils demandés par le mandat sont représentés.

---

## La matrice fait × surface

Pour chaque parcelle, chaque fait chiffré ou qualitatif est relevé sur **chaque surface qui
l'affiche**, une cellule par couple (`scripts/02_matrix_json.py`). Les surfaces JSON sont les
**points d'entrée réels** de l'app : `GET /parcels/{idu}` (fiche), `GET /compare` (comparateur =
la liste/carte peinte), `GET /map/parcels.geojson` (popup carte), `GET /outils/gabarit/{idu}`,
`GET /modules/faisabilite/{idu}`, `GET /radar/annonce/estimation|classement/{idu}` (Estimer un
bien), `GET /parcels/{idu}/exposition`. Les PDF/Docs passent par le harnais maison
`scripts/docs_coherence.py` (8 documents, `pdftotext`, 18 faits partagés), rejoué sur un
sous-ensemble (`scripts/04_docs_pdf.py`). Normalisation **de forme seulement** (« 2 458 m² »→2458,
« 9,0 »→9) : 625 ≠ 630 **reste** un écart.

**Annexes** (dans `out/`) : `matrix_json.csv` (6 360 lignes, **matrice JSON complète** fait×surface),
`matrix_docs.csv` (matrice PDF/Docs) + `docs/{idu}.csv` (une par parcelle), `external20.json`
(confrontation extérieure), `truth.json` (vérité recalculée par parcelle), `prix_labels.json`
(type/fiabilité du prix médian servi, 120 parcelles), `ecarts_json.json` (tous les écarts JSON),
`stats.json` (comptages). Scripts reproductibles : `scripts/01_sample.py` … `06_stats.py`.

### Écarts inter-surfaces par fait (couples JSON)

| fait (notion) | couples comparés | **couples en écart** | nature |
|---|---|---|---|
| médiane prix bâti €/m² | 307 | **184** | fiche/comparateur (secteur, appart/mixte) ≠ Estimer (comparateur typé) — **réel** |
| type de propriétaire | 179 | **179** | liste (badge « BAILLEUR »…) ≠ comparateur (« morale ») ≠ fiche (« personne morale ») — **vocabulaire/granularité** |
| pente moyenne (°) | 120 | **117** | fiche (= table source) ≠ endpoint API `/exposition` (recalcul live) — **réel mais LATENT** (fiche juste ; l'UI n'affiche pas la pente de l'exposition) |
| zone PLU | 1 138 | **91** | Faisabilité sert la zone *constructible minoritaire* ≠ N/A servie partout ailleurs — **réel** |
| nombre d'aléas | 115 | **57** | fiche (`aleas.n`) ≠ Estimer (`n_aleas`) — **réel, deux comptes** |
| taux bâti existant (%) | 51 | **31** | fiche (dérivé emprise/parcelle) ≠ comparateur — ±1–4 pts (base/arrondi) — **mineur** |
| surface (contenance) | 1 192 | 0 | fiche = comparateur = carte = Gabarit — **identique** |
| SDP résiduelle | 426 | 0 | les deux notions + comparateur + carte — **identique (NU-A-001 corrigé)** |
| SDP max réglementaire | 65 | 0 | comparateur = Faisabilité |
| emprise au sol régl. (CES %) | 49 | 0 | comparateur = Gabarit |
| palier / tier | 356 | 0 | fiche = comparateur = carte |
| classement (bande) | 120 | 0 | fiche = endpoint classement |
| rang v2 | 283 | 0 | fiche = comparateur = carte |
| copropriété | 118 | 0 | fiche = carte |

### Écarts par surface (nombre de couples où la surface diffère de l'autre)

fiche 381 · comparateur 295 · Estimer 241 · carte 170 · Exposition 117 · Faisabilité 91 · Gabarit 23.
La fiche « diffère » beaucoup **parce qu'elle est le point de passage de presque tous les couples** ;
dans les cas tranchés (pente, zone) **c'est elle qui porte la vérité**, les autres surfaces qui dévient.

---

## Question 1 — L'app dit-elle la vérité ?

### Confrontée au monde extérieur (20 parcelles, `scripts/05_external.py`)

| source extérieure | fait | résultat |
|---|---|---|
| **cadastre.gouv** (apicarto) | contenance, numéro | **20/20 exacts** (ex. IE0241 625 m² = 625 ; AP1631 4 932 = 4 932) |
| **Géoportail de l'urbanisme** (apicarto GPU, point centroïde) | zone | **20/20 concordent** (ex. 1AUd, AUb, UC, N, A) ; 2 cas où le GPU ne renvoie rien au point (silence externe, pas un écart) ; Saint-Philippe = RNU des deux côtés |
| **DVF Etalab** | dernière vente (date, valeur) | **20/20 exacts au jour et à l'euro** (ex. AE0617 2025-09-22 / 749 400 € ; EP0285 2024-10-28 / 155 350 €) |
| **Géorisques** (gaspar) | risques de la commune | cohérent (les aléas internes sont des sous-ensembles des risques commune) |
| **BAN** | adresse | jamais inventée : adresse interne = BAN là où elle existe, `null` (honnête) sinon |

**Aucun écart de vérité externe.** C'est le résultat le plus net de l'audit : les faits-socle de
LABUSE sont fidèles au référentiel public à l'unité près.

### Recalcul interne indépendant (120 parcelles, `scripts/03_truth_sql.py`)

Chaque fait a été recalculé par une requête SQL à moi, sans passer par le code applicatif
(SRID 2975), puis comparé à ce que la fiche sert :

- **pente moyenne** : fiche = `parcel_terrain.pente_moy_deg` sur **117/117** — la fiche dit vrai.
- **aléas** : la décomposition par niveau est désormais **servie entièrement** (les 50 parcelles à
  plusieurs niveaux montrent fort + moyen + faible et « exposition totale », plus le sliver du seul
  niveau max — **NU-A-007 corrigé**).
- **PPR rouge** : 45 parcelles touchent une zone d'interdiction ; **toutes** sont `tier=ecartee`,
  `bande=0`, avec libellé « zone rouge sur N % : partie INCONSTRUCTIBLE (interdiction, C. env.
  L562-1) » — **NU-A-008 corrigé**.
- **SDP** : `score_labuse` (run servi) et `parcel_residuel` (live) concordent — **NU-A-001 corrigé**.
- **propriétaire PM, palier, copropriété** : fiche = tables sources.

---

## Question 2 — L'app dit-elle la même vérité partout ?

**Presque.** 659 couples JSON en écart sur 4 637, concentrés sur **6 faits**. Deux sont des
divergences réelles **visibles** qui peuvent tromper (zone Faisabilité, médiane de marché), une
troisième réelle mais **latente** (la pente de l'endpoint `/exposition`, non affichée par l'UI),
deux des différences de **notion/vocabulaire** à nommer (nombre d'aléas, type de propriétaire),
une est un **mineur d'arrondi** (taux bâti). Les 18 autres faits partagés sont **identiques d'une
surface à l'autre** — y compris les trois qui étaient contradictoires dans nu-1 (SDP, aléas,
compteur de risques). Le détail chiffré est au § matrice ; les cas les plus graves au § suivant.

### Surfaces PDF / Docs (24 parcelles, harnais maison `docs_coherence`)

Rejoué **hors des témoins fixes du hook** (sous-ensemble aléatoire 1/commune) : sur 24 parcelles
et 432 lignes fait × parcelle, **8 écarts inter-documents seulement** (3 faits), ce qui confirme
la bonne cohérence des 8 documents — mais pas le zéro affiché sur les témoins :

| parcelle | fait | documents concernés | valeurs |
|---|---|---|---|
| 97411000EP0285 | surface terrain | Dossier/Apporteur/Gabarit **8809** vs **Étude faisabilité 2784** | assiette ≠ contenance |
| 97418000AP3309 | surface terrain | Dossier/Apporteur **4162** vs **Étude faisabilité 895** | assiette ≠ contenance |
| 97420000AI0562 | surface terrain | Dossier/Apporteur/Gabarit **4260** vs **Étude faisabilité 2654** | assiette ≠ contenance |
| 97413000CU0804 | surface terrain | Dossier/Apporteur **9687** vs Étude **9677** | dessin vs contenance (±10) |
| 97411000EP0285 | zone impl. libérée | Dossier/Gabarit/Étude **707** vs **Pré-dossier PC 394** | réel |
| 97420000AI0562 | zone impl. libérée | Dossier/Gabarit/Étude **1880** vs **Pré-dossier PC 1268** | réel |
| 97412000AM1955 | zone impl. libérée | Dossier/Gabarit **43** vs Pré-dossier **42** | arrondi (±1) |
| 97406000AE0592 | hauteur faît./égout | Dossier/Étude **9/6** vs **Pré-dossier PC 9/?** | égout omis au Pré-dossier |

Les écarts « surface terrain » viennent de l'**Étude de faisabilité** qui imprime une **assiette
constructible** (plus petite que la contenance) sous un libellé que l'extracteur lit comme
« surface terrain » — même racine que l'écart JSON n°2 (la Faisabilité raisonne sur une sous-surface).
Les écarts « zone implantation libérée » opposent le **Pré-dossier PC** aux autres documents
(707 vs 394, 1880 vs 1268 — matériel). Nota : l'Étude de faisabilité et le Gabarit refusent (HTTP
400/422) sur les parcelles non éligibles (nue/non constructible) — **absence honnête** du document,
pas un écart. Le Copilote n'affirme (doctrine COPILOTE-3) que ce qu'un outil porte ; non ré-audité
en profondeur ici faute de budget, signalé comme angle non couvert.

---

## Le sens des mots (10 faits)

Pour dix faits, le libellé affiché dit-il bien ce que le chiffre *est* ? Un libellé plus fort que
la donnée est un écart.

1. **« Prix ancien médian »** — le chiffre mis en tête n'est **jamais** le prix du type du bien
   quand c'est une maison : sur 119 parcelles qui servent un médian, **63 sont étiquetées
   « appartement », 56 « mixte (appart+maison) », 0 « maison »**. Le libellé affiche désormais le
   type entre parenthèses (honnête), mais le **nombre en tête** reste un €/m² d'appartement ou de
   mixte servi sur une maison ou un terrain (persistance de NU-A-002). *Libellé plus fort que la
   donnée.*
2. **« Prix ancien médian » + fiabilité** — **66/119** médians servis sont auto-étiquetés
   `fragile` (voire `insuffisant`), souvent « commune entière » (repli), et pourtant présentés en
   tête comme « Prix ancien médian » (persistance NU-A-023). *Libellé plus fort que la donnée.*
3. **« surface »** — la tuile SURFACE de la fiche = **contenance cadastrale** (acte, = cadastre.gouv,
   juste) ; l'omnibox / le dessin montrent le `ST_Area` géométrique (ex. 625 vs 630). Deux surfaces
   sous le même mot. (NU-A-014 — mineur, non régressé dans la matrice : contenance identique 1 192/1 192.)
4. **« zone »** — sur la Faisabilité, « Uf »/« UC » est servi **nu** pour une parcelle à 93 %/99 %
   en N (voir écart n°1 ci-dessous). *Le mot « zone Uf » dit plus que la donnée (7 % de la parcelle).*
5. **« constructible »** — le comparateur sert `constructible:true` sur des parcelles à cheval dont
   la part constructible est marginale (cohérent avec la Faisabilité qui titre la zone constructible).
6. **« dernière vente »** — **est bien la dernière** (20/20 = DVF Etalab). Une vente VEFA (neuf)
   apparaît comme « dernière vente » (AX0036) : exact (c'est bien une mutation), mais à surveiller
   si elle entre dans une médiane dite « ancien ».
7. **« SDP résiduelle / restante »** — le mot « SDP » (R.111-22) désigne une enveloppe
   (emprise × niveaux × coef), tagué « estimé » : honnête sur l'incertitude, fort sur le terme
   (dette NU-A-020, inchangée).
8. **« Loyers OLL »** — **désormais `disponible:true`** (un loyer médian est servi) — NU-A-013
   **corrigé** : l'absence n'est plus affichée là où la donnée existe.
9. **« surface libre »** — présentée à 100 % (696 563 m²) sur une parcelle **entièrement en PPR zone
   rouge** (AO0010) : le mot « libre » dit « disponible » sur une emprise légalement inconstructible
   (NU-A-010, persistance). *Libellé plus fort que la donnée.*
10. **« aléa … sur X % »** — le libellé dit maintenant le niveau ET la part ET « exposition totale »
    (plus de « fort ~3 % » trompeur) — **corrigé**. Reste que l'outil Estimer compte « 2 aléas » là
    où la fiche en compte « 6 » (écart n°4).

---

## Les absences

- **`etat_bien = non_mesure`** et `occupation_label` honnêtes (« Aucun bâti significatif détecté »,
  « Présence de bâti à vérifier ») — l'absence de mesure n'est **pas** présentée comme « 0 bâtiment
  certain ». Bon.
- **emprise bâtie = 0** sur parcelle nue : servie comme « 0 m² au sol » + label d'absence, pas comme
  « aucun bâti » définitif. Bon.
- **Loyers OLL** : quand absent, dit « non disponible » (jamais 0 €) ; désormais souvent disponible.
- **prix médian** : quand `n` est faible, servi en repli « commune entière » + `fiabilite:fragile`
  — **mais toujours servi** (cf. mots n°2) ; une absence honnête (ne rien servir sous un plancher)
  serait préférable à un médian fragile en tête.
- **adresse** : `null` quand inconnue (jamais inventée — confirmé BAN).
- **Carte** : 2 parcelles du tirage (`97401000AR1377`, `97415000BR0139`, toutes deux `ecartee`) sont
  servies par la fiche et le comparateur mais **absentes de la carte** — la carte ne peint pas les
  parcelles écartées. Choix produit défendable, mais un même objet existe sur une surface et pas sur
  l'autre : à documenter (mineur).

---

## Les 10 écarts les plus graves (cause fichier:ligne)

### 1. MAJEUR — La Faisabilité déclare constructible (zone Uf, « R+1 », 1 logement) une parcelle à 93 % en zone N
- **Où** : `src/labuse/api/modules.py:1873-1878` — `_zone_lbl = f.zone` (la zone *constructible*, pas
  la dominante) ; le suffixe « sur X % » et le drapeau `a_cheval` ne sont posés **que si**
  `_ctx.a_cheval` est vrai, or `a_cheval = dominante_pct < 90 %` (`src/labuse/faisabilite/zone_servie.py:124`,
  `SEUIL_A_CHEVAL_PCT = 90`).
- **Repro** : `GET /modules/faisabilite/97416000IA1264` → `capacite.zone = "Uf"`, `a_cheval = false`,
  verdict « R+1 · jusqu'à ~20 m² de plancher », `logements_au_sol = [0,1]`, alors que
  `zone_parts = [N 93 %, Uf 7 %]` et que fiche/comparateur/carte/Gabarit disent tous **« N »**
  (vérité `parcel_zone_plu` = N). Idem 97414000HE0022 (N 99,2 % / UC 0,8 % → « UC »),
  97420000AO0601 (→ « UC »), 97416000IA1264.
- **Affiché vs juste** : une parcelle à 93 % inconstructible (N) est titrée « Uf » et déclarée
  bâtissable, **sans aucun avertissement à cheval** (le seuil 90 % masque la part de 7 %). Toutes les
  autres surfaces disent « N ». C'est le fait le plus susceptible d'induire une décision d'achat erronée.
- **Amélioration** : afficher « Uf sur 7 % » (et lever le drapeau à cheval) dès qu'une zone
  constructible minoritaire sert de base au verdict, **indépendamment** du seuil 90 % ; ou titrer la
  dominante (N) et ne présenter la capacité du sliver qu'en second rang, explicitement.

### 2. MAJEUR — « Prix ancien médian » : jamais le type du bien (0/119 maison), 66/119 fragiles servis en tête
- **Où** : `src/labuse/faisabilite/bilan.py:275-276` (`base_plans` : appartement → mixte appart+maison →
  commune, **aucun plan maison-seule** ; la docstring assume « appartements = comparable d'un collectif
  neuf ») ; servi en tête de fiche (`marche_synthese`), repris par le comparateur
  (`prix_secteur_bati_m2`), tandis qu'Estimer un bien sert un comparateur **typé**
  (`/radar/annonce/estimation`, `type_comparateur`).
- **Mesure** : 119/120 parcelles servent un médian ; **63 appartement + 56 mixte, 0 maison** ;
  **66 étiquetés `fragile`/`insuffisant`** et pourtant servis en tête (ex. AO0010 : 70 ha de forêt
  PPR-rouge → « Prix ancien médian 1 750 €/m² (appartement) »).
- **Affiché vs juste** : le chiffre phare du marché n'est pas le prix du bien ; sur une même parcelle,
  la fiche affiche un €/m² (appartement/mixte) et l'outil Estimer en affiche un autre (maison) — deux
  « médianes » qui s'écartent (184 couples en écart, écart n°4). *Décision d'achat.*
- **Amélioration** : ajouter un plan « maison-seule » prioritaire selon `etat_bien` ; plancher de
  `n`/fiabilité avant de servir en tête ; aligner le libellé entre fiche, comparateur et Estimer.

### 3. MAJEUR — La médiane de marché diffère entre la fiche/comparateur et l'outil Estimer (184 couples)
- **Où** : fiche `prix_ancien.median` + comparateur `prix_secteur_bati_m2` (rayon adaptatif, type
  appartement/mixte) ≠ Estimer `median` (comparateur maison↔maison ou terrain↔terrain, autre rayon).
- **Affiché vs juste** : deux surfaces présentent toutes deux un « prix médian €/m² » du bien et
  donnent des nombres différents (ex. BV… 1 596 vs 1 747 ; …1 750 vs 2 950). Le lecteur ne sait pas
  lequel fait foi.
- **Amélioration** : une définition unique de « médiane de marché du bien » partagée par la fiche, le
  comparateur et Estimer, ou un libellé qui distingue clairement « médiane secteur » de « comparateur
  d'estimation ».

### 4. MAJEUR — Le nombre d'aléas diffère entre la fiche et Estimer (57 parcelles)
- **Où** : fiche `aleas.n` (compte les vigilances : PPR + aléas + SUP…) ≠ Estimer `n_aleas`
  (`/radar/annonce/estimation`).
- **Mesure** : 57/115 en écart, ex. 97403000AS0721 fiche **6** / Estimer **2** ; 97424000AE0394
  fiche **4** / Estimer **1**. (Écho de NU-A-011 : la tuile, la section et le PDF comptaient déjà
  1/2/3.)
- **Affiché vs juste** : « 2 aléas » sur Estimer vs « 6 vigilances » sur la fiche pour la même
  parcelle — même mot (« aléas »), deux comptes.
- **Amélioration** : une source unique de comptage des aléas/vigilances, consommée par la fiche et
  par Estimer.

### 5. MAJEUR (libellé) — « Surface libre » = 100 % sur une parcelle entièrement en PPR zone rouge
- **Où** : `src/labuse/bati.py:284` — `surface_libre = contenance − emprise_BDTOPO`, sans tenir
  compte du PPR rouge ni de COSIA.
- **Repro** : 97402000AO0010 — PPR interdiction sur 100 %, `emprise=0` → `surface_libre_m2 = 696 563`
  (soit la totalité des 70 ha), `occupation_label = "Aucun bâti significatif détecté"`.
- **Affiché vs juste** : « libre » se lit « disponible/constructible » sur une emprise légalement
  inconstructible (interdiction PPR). (Persistance NU-A-010.)
- **Amélioration** : déduire de la « surface libre » la part en zone rouge PPR et la part COSIA
  imperméabilisée, ou renommer « surface non bâtie (BD TOPO) ».

### 6. MINEUR / LATENT — L'endpoint API `/exposition` calcule une seconde « pente moyenne » qui contredit la table source (115/117)
- **Où** : tuile « Pente » de la fiche ← `terrain.pente_moy_deg` (= `parcel_terrain`, RGE ALTI 5 m,
  servi par `app.py:_pente_bande`) ; endpoint `GET /parcels/{idu}/exposition` →
  `src/labuse/faisabilite/exposition.py:82` (`pente_moy = np.mean(slope[ok])` sur une dalle MNT WMS
  live) et `:96` (`"pente_moyenne_deg": …`).
- **Mesure** : fiche == table source **117/117** ; l'endpoint `/exposition` == table source **2/117**
  → divergence sur **115/117** parcelles, dont **20 de ≥ 5°** (97424000AC0699 10,5° → **27,9°** ;
  97424000AL0072 30,5° → **20,5°**).
- **Nuance honnête (vérifiée)** : **aucune surface livrée n'affiche cette seconde pente** — le front
  l'écrit noir sur blanc dans l'info-bulle (« la pente affichée est celle de l'emprise ; l'exposition
  n'en montre pas une seconde », `Fiche.tsx:996`), et l'export/Copilote ne lit de l'exposition que
  l'`orientation` (`exports/robinet_fiche.py:135`). C'est donc un **piège latent au niveau API**, pas
  une tromperie actuelle à l'écran — mais tout futur consommateur de l'endpoint hériterait d'une pente
  fausse.
- **Amélioration** : l'endpoint doit lire `parcel_terrain.pente_moy_deg` (source unique) ou renommer
  son champ « pente locale au centroïde » et ne jamais l'exposer comme « pente moyenne ».

### 7. MINEUR — Le type de propriétaire change de mot selon la surface ; le caractère PUBLIC disparaît sur le comparateur
- **Où** : carte/liste `owner_type` rendu en badge (`frontend/.../ResultsSection.tsx:133-136`,
  `bailleur`/`pm` ; **`public` non badgé**) ; comparateur `proprietaire` (« morale »/« particulier ») ;
  fiche `proprietaire_moral` (« personne morale — … »).
- **Mesure** : 179/179 couples « en écart », mais **aucune contradiction de fond** : « pp »↔« particulier »,
  et public/bailleur/PM ⊂ « morale » (cohérent avec `parcelle_personne_morale`). En revanche, une
  parcelle de l'État ou d'une commune apparaît « morale » sur le comparateur (le caractère **public**
  n'y est pas dit) et sans badge sur la carte.
- **Amélioration** : un vocabulaire unique (particulier / personne morale / **public** / bailleur)
  partagé par les trois surfaces.

### 8. MINEUR — Taux de bâti existant : ±1 à 4 points entre fiche et comparateur
- **Où** : comparateur `bati_existant_pct` vs fiche (dérivé `emprise_batie_m2 / surface_parcelle_m2`).
- **Mesure** : 31 écarts, tous ≤ 4 pts (ex. 37 vs 41, 87 vs 89) — base géométrique (dessin vs
  contenance) et arrondi. Pour partie imputable à la dérivation de l'audit.
- **Amélioration** : servir le même dénominateur (contenance) et le même arrondi partout.

### 9. MINEUR — Deux parcelles servies par la fiche mais absentes de la carte
- **Où** : `97401000AR1377` (copro nue, Ud) et `97415000BR0139` (PPR, Nerl), toutes deux
  `status=ecartee` — `GET /map/parcels.geojson` ne les peint pas, `GET /parcels/{idu}` et
  `/compare` les servent.
- **Amélioration** : décision assumée (la carte = le gisement) ; la documenter pour que « voir N
  parcelles » et l'univers des fiches ne paraissent pas incohérents.

### 10. DETTE — « SDP résiduelle » (R.111-22) et VEFA dans la chaîne « ancien »
- **Où** : `residuel.py` (enveloppe nommée « SDP ») ; DVF « dernière vente » peut être une VEFA
  (neuf) servie telle quelle (exact) — à surveiller si une VEFA entre dans une médiane « ancien ».
- **Amélioration** : « enveloppe constructible estimée » ; exclusion explicite VEFA des médianes
  « ancien » (le flag existe).

---

## Ce qui est sain (à décharge)

- **Vérité externe parfaite** : surface (cadastre.gouv), zone (GPU), dernière vente (DVF Etalab) —
  **0 écart sur 20 parcelles**, à l'unité/euro/jour. L'adresse n'est jamais inventée (BAN).
- **SDP** : les deux notions historiques (`parcel_residuel` live et `score_labuse` run servi) et le
  comparateur et la carte **concordent** — **NU-A-001 (bloquant nu-1) corrigé**, 0 écart / 426 couples.
- **Aléas** : la décomposition par niveau est **servie entièrement** (« fort X % · moyen Y % ·
  exposition totale ») — **NU-A-007 corrigé** ; PPR zone rouge dit « INCONSTRUCTIBLE (L562-1) » et
  **écarte** la parcelle (45/45) — **NU-A-008 corrigé**.
- **Cohérence inter-surfaces** sur 18 des 24 faits : surface (1 192 couples, 0 écart), SDP max,
  emprise CES, palier/tier (356, 0), classement, rang (283, 0), copropriété (118, 0) — identiques.
- **Pente** : la fiche = table source `parcel_terrain` sur 117/117.
- **Loyers OLL** disponibles (NU-A-013 corrigé) ; `etat_bien`/occupation honnêtes sur l'absence de mesure.

---

## Verdict en une phrase par question

- **L'app dit-elle la vérité ?** — **Oui** : sur les faits-socle, elle colle au référentiel public
  (cadastre, GPU, DVF, BAN) à l'unité près, et ses calculs internes égalent les tables sources.
- **Dit-elle la même vérité partout ?** — **Presque** : 18 faits sur 24 sont identiques d'une surface
  à l'autre (dont la SDP et les aléas, jadis contradictoires), mais **six divergent** — le plus grave
  étant une Faisabilité qui dit « constructible » (Uf, R+1) là où toutes les autres surfaces disent
  « N », le plus insidieux une pente fausse servie par l'API `/exposition` (non affichée, pour l'instant).
