# M6 §1.15 — Scénarios anti-incohérences & suite permanente (13/07/2026)

**Suite rejouable :** `frontend/qa/m6_scenarios.mjs`
(`cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/m6_scenarios.mjs` ;
`M6_STRICT=1` fait échouer la suite sur les tickets ouverts). Aucun IDU codé en dur :
les parcelles de test sont retrouvées par SQL à chaque exécution. Lecture seule
(les POST utilisés sont des calculs sans persistance).

**État au 13/07/2026 : 10 scénarios — 4 PASS · 6 XFAIL (tickets M6-INC-01 à 06) ·
0 FAIL · exit 0.** Captures : `reports/m6-audit/sections/captures-1-15/`.

| Scénario | Verdict | Ticket |
|---|---|---|
| S1 Logement étudiant → zones économiques/industrielles | **XFAIL** | M6-INC-01 |
| S2 Division / faisabilité sur parcelle zone A/N → réponses honnêtes | PASS | — |
| S3 Collectif R+4 → aucune hauteur PLU vérifiée insuffisante | PASS | — |
| S4 Vue Piscinistes → zone A/N, cœur de Parc, sans bâti | **XFAIL** | M6-INC-02 |
| S5 Outil Division → parcelles étage 0 (PPR rouge) sans avertissement | **XFAIL** | M6-INC-03 |
| S6 Vue Pergolas → parcelles sans bâti / zone A-N | **XFAIL** | M6-INC-04 |
| S7 Vue PV résidentiel → aucune parcelle boisée dense (canopée ≥ 60 %) | PASS | — |
| S8 Écartées hors liste par défaut + fiche d'une exclue honnête | PASS | — |
| S9 M22 → « hauteur vérifiée » sur commune non calibrée | **XFAIL** | M6-INC-05 |
| S10 Faisabilité zone A → motif de verdict erroné (texte AU*st) | **XFAIL** | M6-INC-06 |

---

## TICKETS

### M6-INC-01 — Un programme HABITAT propose des parcelles en zone économique, industrielle… et sur l'aéroport — **gravité : MAJEURE**

C'est l'alerte client connue (« logement étudiant en zone industrielle »), reproduite et
mesurée : **31 des 200 candidats** servis pour une résidence étudiante (île entière) ont
une zone PLU **dominante** à vocation économique.

**Repro.**
1. Outils → « Faisabilité programme » (M22) → type « rés. étudiante », 40 unités → « Trouver les parcelles » (capture `s1-m22-etudiant.png`) ; ou `POST /modules/programme {"type":"etudiant","logements_par_batiment":40,"niveaux":2,...}`.
2. Exemples servis (zone dominante vérifiée en SQL, libellés du PLU) :
   - `97407000AT0073`, `AV0253`, `AZ0170`… (Le Port, **Ue/Uem** — 8 des 15 premiers candidats du Port) ;
   - `97410000AR1547` (Saint-Benoît, **Ue15 « zones affectées aux activités économiques et industrielles »**) ;
   - `97409000AR1232` (Saint-André, **US « espaces destinés à accueillir des activités économiques et commerciales »**) ;
   - `97416000CR0884` (Saint-Pierre, **Uazi « activités industrielles et artisanales »**) ; `97416000CR0190` (ZAC Roland Hoareau, secteur d'activités) ;
   - `97411000BL0007/0008/0111` (Saint-Denis, **Ua « zone d'activités du Chaudron »**) ;
   - `97418000BC0368` (Sainte-Marie, **UR « aéroport Roland Garros »**).
3. Même moteur exposé côté « Projets » : `POST /projets/apercu` (projet « LES LILAS »,
   secteur Ouest) sert le top M22 — Le Port y figure avec « Hauteur PLU 9 m (vérifiée), zone U ».

**Cause racine.** `src/labuse/api/modules.py` › `faisabilite_sens2()` (l. 602-660) :
la sélection = `parcel_residuel.sdp_residuelle_m2 ≥ besoin` × `matrice_statut IN
(chaude, a_surveiller, a_creuser)`. La zone PLU n'est lue (détail cascade
`zonage_plu_gpu`) **que pour la hauteur** (`resolve_zone` → hauteur max) — **la
vocation de la zone (habitat interdit en Ue/Ui/US/UR…) n'est jamais vérifiée**, ni par
la cascade (qui classe constructible tout préfixe U/AU, `positive_prefixes`), ni par le
moteur. Aggravant : la sous-zone GPU est normalisée en `subtype='U'` — l'UI affiche
« zone U (h 9 m ✓) » pour une parcelle Ue.

**Piste.** Filtrer/étiqueter par vocation (libellé long GPU + calibrage
`stat_logement` des YAML PLU) pour les types de programme habitat ; a minima bandeau
« vocation de zone à vérifier » quand le libellé matche activités/industriel/aéroport.

---

### M6-INC-02 — La vue « Piscinistes — construction » vend des terrains agricoles, naturels, sans maison… jusqu'au cœur du Parc national — **gravité : MAJEURE**

**Repro.** Vues → « Piscinistes — construction » (5 541 parcelles), tri par défaut
« jardin décroissant » ; ou `POST /segments/query {"slug":"piscinistes-construction","limit":200}`.
Sur le top 200 servi : **117 en zone dominante A ou N**, **100 sans aucun bâti**
(jardin = surface totale), **1 dans le cœur du Parc national**
(`97412000AN0019`, Saint-Joseph, 10 587 m²) et 97 intersectent une zone PPR
INTERDICTION (mesure SQL du 13/07). Les premières lignes sont des parcelles de
**15 hectares** (ex. `97422000BS0413`, Le Tampon, 159 543 m² de « jardin »).

**Cause racine.** Moteur segments : `src/labuse/segments/engine.py` l. 32 —
`_BASE_WHERE = "p.surface_m2 >= 2"` : **aucun** filtre de zonage, de bâti ni d'étage 0
dans le socle du moteur. Le preset (`config/segment_presets.yaml`,
`piscinistes-construction`) = jardin ≥ 200 + mutation < 24 mois + pente ≤ 10° +
piscine=false — `jardin_m2 = surface − emprise bâtie` (registry l. 66) fait d'un champ
agricole nu un « grand jardin », et le tri `jardin_desc` met les pires en tête.

**Piste.** Le fix du 12/07 sur `parc-piscines-entretien` (proxy bâti
`emprise_batie_m2` 40-400 m²) est exactement le garde-fou manquant : l'appliquer aux
presets construction/extérieur + exclure zones A/N/cœur de Parc.

---

### M6-INC-03 — L'outil « Division parcellaire » sert des parcelles EXCLUES à l'étage 0 (PPR rouge, foncier public) à score 99, sans le moindre avertissement — **gravité : MAJEURE**

**Repro.** Outils → « Division parcellaire » (capture `s5-division-etage0.png`) ; ou
`GET /modules/division?limit=300`. **161 des 300 items servis** (et 2 148 des 4 433
candidats précalculés, 48 %) sont exclus à l'étage 0 :
- `97415000EW0374` (score 99) : « **PPR zone rouge (inconstructible)** » ×4 + « Propriété
  publique (COMMUNE DE SAINT PAUL) — non acquérable » ;
- `97419000AL0269`, `97412000BS0436`, `97413000CH0515`… (score 99, PPR rouge) ;
- `97414000CI0998` (faux_positif_probable, pente).

La ligne du panneau n'affiche AUCUN badge — impossible pour le client de savoir.

**Cause racine.** `src/labuse/api/modules.py` :
- `division_compute()` (l. 71-135) : les critères C1-C5 (surface, bâti, zone U, lot,
  voirie) ne joignent jamais `dryrun_parcel_evaluations` ;
- `division_list()` (l. 139-151) ne renvoie ni `etage0` ni `tier_v2` — l'UI
  (`ModulePanel.tsx` › M01) ne PEUT donc pas afficher le `TierBadge`, contrairement à
  M22, Assemblage, SimulPLU et ZAN qui le font tous.

**Piste.** Ajouter le join étage 0 dans `division_list` (comme duediligence l. 440+)
+ `TierBadge` dans la Row M01 ; décider si l'étage 0 exclut du précalcul ou n'est
qu'affiché.

---

### M6-INC-04 — La vue « Pergolas & terrasses » (« les maisons avec du jardin ») liste 40 % de parcelles SANS maison — **gravité : MOYENNE**

**Repro.** Vues → « Pergolas & terrasses » (5 315 parcelles) ; ou
`POST /segments/query {"slug":"pergolas-terrasses","limit":200}` : **81/200 sans aucun
bâti** (ex. `97407000AH1363`), **24/200 en zone dominante A/N** (ex. `97412000AN0429`).
L'argumentaire promet « les maisons avec du jardin nu à équiper » — une pergola sans
maison n'existe pas.

**Cause racine.** Identique à M6-INC-02 : preset sans exigence de bâti
(`emprise_batie_m2` min absent de `pergolas-terrasses` et `paysagistes`), socle moteur
sans zonage. Gravité moindre (le tri par défaut « mutation récente » ne concentre pas
les cas absurdes en tête comme le tri jardin des piscinistes).

---

### M6-INC-05 — « Hauteur PLU 9 m (vérifiée) » affichée pour des communes dont le PLU n'est PAS calibré — **gravité : MOYENNE**

**Repro.** `POST /modules/programme {..., "commune":"Le Port"}` → **64/64 candidats**
étiquetés `hauteur_verifiee: true` (« h 9 m ✓ » dans l'UI M22, « Hauteur PLU 9 m
(vérifiée) » dans le « pourquoi » des projets) alors qu'il n'existe AUCUN
`config/plu_le_port.yaml` : la hauteur vient de l'**estimation générique**.

**Cause racine.** `src/labuse/api/modules.py` › `faisabilite_sens2()` l. 636 :
`hauteur_verifiee = h is not None`. Or `resolve_zone()`
(`src/labuse/faisabilite/plu_rules.py` l. 175) renvoie `_zone_generique()` (marquée
`calibree=False`) pour toute commune sans YAML — le flag `calibree` est ignoré.
Fausse assurance réglementaire vendue au client.

**Piste.** `hauteur_verifiee = h is not None AND rules.calibree`.

---

### M6-INC-06 — En zone AGRICOLE, le verdict de faisabilité invoque un motif « secteur de transition (AU*st) » — **gravité : MINEURE (libellé)**

**Repro.** `GET /modules/faisabilite/{idu}` sur une parcelle 100 % zone A (ex.
`97401000AN0654`, Les Avirons) → verdict : « Construction neuve non autorisée —
secteur de transition (AU*st) : travaux mineurs de mise aux normes, H max 4 m. »
La conclusion (non constructible) est juste ; le motif est faux (c'est une zone
agricole, pas un secteur AU*st) et laisse croire que des « travaux mineurs H 4 m »
seraient permis au même titre.

**Cause racine.** `src/labuse/faisabilite/engine.py` l. 150-153 : la branche
`not rules.constructible_neuf` a un message unique codé en dur pour AU*st, servi à
toutes les zones non constructibles (A, N, générique).

---

## Scénarios qui PASSENT (garde-fous confirmés)

- **S2** : le module Division ne liste aucune parcelle à dominante A/N (critère C3
  zone U dominante effectif) ; la calculette de charge foncière sur une parcelle 100 %
  zone A répond `calculable:false, capacite_non_resolue` — jamais un faux chiffre.
- **S3** : collectif R+4 (h min 15 m) — aucune parcelle à hauteur PLU **vérifiée**
  insuffisante n'est servie. Vigilance (pas un ticket) : 58/58 candidats sont
  « hauteur à instruire », le filtre hauteur ne mord donc presque jamais — à recouper
  avec M6-INC-05.
- **S7** : la vue PV résidentiel n'a servi aucune parcelle à canopée ≥ 60 % (le filtre
  optionnel `flag_ombrage_vegetal=false` est bien pré-appliqué). Noter qu'il est
  décochable par l'utilisateur dans le builder.
- **S8** : la liste par défaut du parcours principal exclut les 352 620 écartées (chip
  « Tout » = 79 043, SQL-exact) ; la fiche d'une parcelle exclue porte bandeau
  « écartée » + badge « Écartée » (capture `s8-fiche-ecartee.png`).

## Synthèse des causes racines (pour M6 phase correctifs)

1. **L'étage 0 et le zonage ne sont garantis QUE sur le chemin `/parcels`** (liste,
   recherche, carte, fiche). Les surfaces « latérales » — modules (`/modules/division`),
   moteur de segments (`_BASE_WHERE = surface ≥ 2`) — re-requêtent `parcels` sans ces
   garde-fous : chaque nouvelle surface reproduit le trou.
2. **La vocation des zones PLU n'existe nulle part comme donnée de décision** : la
   cascade ne connaît que constructible (U/AU) vs non (A/N) ; les sous-zones
   économiques/aéroportuaires passent pour de l'habitat possible.
3. **Le mot « vérifié » est sur-employé** : il couvre aujourd'hui des estimations
   génériques non calibrées (M6-INC-05) et des motifs recyclés (M6-INC-06).
