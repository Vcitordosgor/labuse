# RAPPORT — Wave copro-data (mandat Copro/Tertiaire/Flux re-scopé 11/07/2026)

**Branche** : `feat/wave-copro-data` (depuis main 8f2e1b5) · **Merge : Vic uniquement.**
**Périmètre re-scopé (décision produit 11/07)** : catalogue réduit à 5 segments grand public →
toutes les vues copro/tertiaire/veille du mandat d'origine sont **PARKÉES** (aucun preset créé).
Exécuté : ① DPE ADEME complet + recalcul Score V, ② mesure de couverture DPE (décision Cerema),
③ compléments RNIC data socle.

---

## 1. DPE ADEME — le « gisement complet » fait 914 lignes (constat majeur)

Le jeu ADEME `dpe03existant` (= « DPE Logements existants depuis juillet 2021 », 15,2 M
national) ne contient que **912 DPE pour tout le 974** — vérifié par trois filtres concordants
(`code_insee_ban:974*`, `code_departement_ban:974`, `code_region_ban:04`) + 2 enregistrements
hors filtre BAN (CP brut 974xx). **La « vague pilote » de 910 lignes était donc déjà une
ingestion quasi complète** : le manque n'était pas dans notre connecteur mais dans la réalité
du DPE réglementaire à La Réunion (~10 DPE/mois depuis 07/2021, flux vérifié par histogramme).

Fait quand même :
- **914 DPE ingérés** (912 + 2 orphelins), 24/24 communes balayées.
- **Rattachement parcelle re-fait 100 % local** (mandat : « géocodage = table adresses locale ») :
  `identifiant_ban` → `adresses.id_ban` (574), point BAN natif EPSG:2975 → ST_Contains (328),
  adresse brute normalisée (1), aucun (11). **903/914 = 98,8 %** (avant : 866/910 = 95,2 % via
  api-adresse — le local fait mieux, sans réseau).
- 277 parcelles distinctes (les appartements partagent les parcelles d'immeubles),
  étiquettes : A 15 · B 22 · C 483 · D 215 · E 136 · **F 25 · G 18** ; passoires (vue) : 17.

## 2. Impact Score V (famille E) et Brûlantes

| Indicateur | Avant | Après | Δ |
|---|---|---|---|
| Parcelles signal E retenu | 23 | **27** | +4 (13 F, 13 G, 1 G_MULTI ; +3 sur parcelles `na`) |
| Bande `faible` | 10 958 | 10 962 | +4 (sorties de `aucun`) |
| Bandes `fort`/`present` | 169 / 8 880 | 169 / 8 880 | 0 |
| **Brûlantes** | **79** | **79** | **0** (garde-fou [30-120] respecté) |

**Lecture honnête : l'impact est marginal et ne peut pas être autre chose** — la famille E est
plafonnée à 15 pts et il n'existe que 42 DPE F/G rattachés sur toute l'île. Le Score V est
recalculé, propre, et suivra automatiquement le flux ADEME (croissant si l'obligation DPE DROM
monte en charge). Le rapport Flash lit la même table.

## 3. Couverture DPE — le chiffre décisionnel Cerema (Lot 6)

Dénominateur : parcelles bâties (`parcel_residuel_bati.emprise_batie_m2 > 0`, 24/24 communes).

- **Global : 255 / 292 056 parcelles bâties = 0,09 %.**
- Coupe « résidentiel probable » (propriétaire personne physique) : 196 / 252 223 = 0,08 %.
- Meilleure commune : Les Trois-Bassins 0,23 % ; 4 communes à 0 (Salazie, Cilaos, Entre-Deux,
  Bras-Panon). Détail 24 communes : `outputs/dpe/couverture_dpe_par_commune_20260711.csv`.

**Recommandation chiffrée (règle du mandat : seuil 40 %)** : la couverture est ~440× sous le
seuil. Les presets « âge du bâti » assis sur le DPE ratent >99,9 % du parc réunionnais, et le
flux ADEME actuel (~10/mois) ne comblera jamais l'écart à horizon utile. **La licence Fichiers
Fonciers Cerema (seule source exhaustive d'année de construction) est justifiée** si un preset
« bâti ancien » doit exister dans l'offre. Décision : Vic.

## 4. Compléments RNIC (data socle uniquement, aucun preset)

Table `rnic_coproprietes` : 2 220 copros (T3 2025 = dernière édition publiée, vérifié
data.gouv 11/07 ; pas de re-téléchargement utile).

- **Purge RGPD : 984 lignes** (86 syndics bénévoles + 898 « non connu ») — `syndic_nom`/
  `syndic_siret` effacés ET clés du représentant retirées de `raw`. Règle verrouillée à
  l'ingestion pour les rafraîchissements futurs. **Critère d'acceptation : 0 syndic non
  professionnel nominatif ✓** (les 1 236 professionnels restent nominatifs — personnes morales).
- **Rattachement : 2 220/2 220 = 100 %** — les 71 copros restantes récupérées par la passe
  `proche_20m` (point RNIC sur voirie, même idiome que l'ingestion BAN).
  Répartition : cadastre 1 083 · geocode 850 · adresse 216 · proche_20m 71.
- Tranches (lots habitation) : <10 : 806 · 10-19 : 459 · 20-49 : 653 · 50+ : 302.
- CLI : `labuse rnic-complements` (idempotent, sans CSV).

## 5. Non fait (parké par le re-scoping — ne pas relancer sans décision)

Presets copro (ravalement/bornes/accès/ascenseurs), DPE tertiaire + décret tertiaire,
SIRENE flux, PEB aéroports, ICPE : **rien construit**, conformément à la décision du 11/07.

## Tests & commits

- `tests/test_dpe.py` (10) + `tests/test_rnic.py` (3) : 13/13 verts. Échecs restants de la
  suite globale = dette préexistante (pyproj/état base de test), vérifié identique sans ces
  changements.
- Commits : `feat(dpe)` 37ac357 · `feat(rnic)` bb0aa26 · docs (celui-ci).
