# EXPORTS-AUDIT — annexe de reproductibilité

Chaque valeur citée dans `DONNEES-RAPPORT.md` a ici sa commande ou sa requête. Environnement d'exécution :

```sh
# Toute commande python de cette annexe se lance ainsi (voir préalable du rapport) :
alias pyaudit='DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  PYTHONPATH=/Users/openclaw/Desktop/labuse-merge/src \
  /Users/openclaw/miniforge3/envs/labusedb/bin/python'
# Base : psql -U openclaw -d labuse   (lecture seule)
```

## Préalable — génération des 28 artefacts

```sh
~/Desktop/exports/generer.sh 97415000BO0852
~/Desktop/exports/generer.sh 97401000AD0554
~/Desktop/exports/generer.sh 97416000DY0106
~/Desktop/exports/generer.sh 97411000AV0110
# Extraction texte des PDF (base des citations « le PDF imprime … ») :
for d in 97415000BO0852 97401000AD0554 97416000DY0106 97411000AV0110; do
  for f in ~/Desktop/exports/$d/*.pdf; do pdftotext -layout "$f" "${f%.pdf}.txt"; done
done
```

Scripts : `~/Desktop/exports/generer.sh`, `~/Desktop/exports/generer.py` (hors dépôt, reproduits en fin d'annexe).

## Choix des témoins

```sql
-- T2 (nue en U, hors Saint-Paul, adressée)
SELECT p.idu, p.commune, round(p.surface_m2) surf, z.zone_lib, r.taux_emprise_pct
FROM parcels p
JOIN parcel_zone_plu z ON z.idu = p.idu AND z.zone_fam='U'
JOIN parcel_residuel r ON r.parcel_id = p.id AND r.taux_emprise_pct = 0
WHERE p.commune <> 'Saint-Paul' AND p.surface_m2 BETWEEN 400 AND 1500
  AND EXISTS (SELECT 1 FROM adresse_parcelles ap WHERE ap.idu = p.idu)
ORDER BY p.idu LIMIT 5;   -- retenu : 97401000AD0554

-- T3 (zone A/N bâtie) — a aussi révélé taux_emprise_pct=198 et SDP>0 en N
SELECT p.idu, p.commune, round(p.surface_m2) surf, z.zone_lib, r.taux_emprise_pct, r.sdp_residuelle_m2
FROM parcels p
JOIN parcel_zone_plu z ON z.idu = p.idu AND z.zone_fam IN ('A','N')
JOIN parcel_residuel r ON r.parcel_id = p.id
WHERE p.commune IN ('Le Tampon','Saint-Pierre') AND p.surface_m2 BETWEEN 1000 AND 10000
  AND r.taux_emprise_pct > 0
  AND EXISTS (SELECT 1 FROM adresse_parcelles ap WHERE ap.idu = p.idu)
ORDER BY p.idu LIMIT 6;   -- retenu : 97416000DY0106

-- T4 (à cheval sur deux zones, Saint-Denis)
SET statement_timeout='120s';
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.surface_m2, p.geom_2975
  FROM parcels p WHERE p.commune='Saint-Denis' AND p.surface_m2 BETWEEN 500 AND 5000
), inter AS (
  SELECT c.idu, c.commune, round(c.surface_m2) surf,
         rtrim(split_part(btrim(z.attrs->>'libelle'),' ',1),':') AS zone,
         round((ST_Area(ST_Intersection(ST_MakeValid(z.geom_2975), c.geom_2975))
                / c.surface_m2 * 100)::numeric,1) AS pct
  FROM cand c JOIN spatial_layers z
    ON z.kind='plu_gpu_zone' AND ST_Intersects(z.geom_2975, c.geom_2975)
)
SELECT idu, commune, surf, string_agg(zone||' '||pct||'%', ' + ' ORDER BY pct DESC) AS zones
FROM inter GROUP BY idu, commune, surf
HAVING count(DISTINCT zone) >= 2 AND min(pct) >= 25
ORDER BY idu LIMIT 8;   -- retenu : 97411000AV0110 (Uh 57.4% + N 42.6%)
```

## §A1/A2/A3/A4 — mesure des moteurs sur les 4 témoins

Le script `~/Desktop/exports/audit_valeurs.py` (reproduit en fin d'annexe) appelle chaque moteur
concurrent en direct et écrit `~/Desktop/exports/audit_valeurs.json` :

```sh
pyaudit ~/Desktop/exports/audit_valeurs.py > ~/Desktop/exports/audit_valeurs.json
```

Moteurs appelés (mêmes imports que les exports) : `faisabilite.bilan.sector_price`,
`faisabilite.bilan.resolve_prix_sortie_servi`, `faisabilite.marche_commune.ligne1_prix_ancien` /
`ligne4_tendance`, `ingestion.dvf_marche.neuf_vefa_commune`, `marche_service.comparables`,
`flash.data._marche` / `_dynamique`, `faisabilite.db.parcel_faisabilite`,
`ingestion.permits.nearby_permits` (défauts), `api.site_voisinage.voisinage_proche`,
`faisabilite.bilan.compute_bilan_servi`, tables `parcel_residuel_bati`, `parcel_residuel`, `rpls_commune`.

### A1.q1 — parcelle « représentative » du centroïde (n 11)

```sh
pyaudit -c "
from labuse.db import session_scope
from sqlalchemy import text
from labuse.faisabilite import marche_commune as mc
with session_scope() as s:
    print(s.execute(text(\"\"\"SELECT idu FROM parcels WHERE commune='Saint-Paul' AND geom_2975 IS NOT NULL
      ORDER BY centroid <-> (SELECT ST_Centroid(ST_Collect(centroid)) FROM parcels WHERE commune='Saint-Paul')
      LIMIT 1\"\"\")).scalar())          # → 97415000CO0049
    print(mc.ligne1_prix_ancien(s, 'Saint-Paul'))   # → median 3766, n 11, type appartement, fiabilite fiable
"
```

### A1.q3 — réfutation du coefficient 1,24

```sh
grep -rn "1\.24\|1,24\|uplift\|UPLIFT\|coef.*neuf\|neuf.*coef" src/labuse --include="*.py" | grep -vi test
# → seul hit : partners.py:313 (couleur SVG rgba). Aucun coefficient prix.
pyaudit -c "
from labuse.db import session_scope
from sqlalchemy import text
with session_scope() as s:
    pid = s.execute(text(\"SELECT id FROM parcels WHERE idu='97415000BO0852'\")).scalar()
    from labuse.faisabilite.bilan import resolve_prix_sortie_servi
    print(resolve_prix_sortie_servi(s, pid))
"   # → {'prix': 4730.0, 'niveau': 'commune', 'n': 54, …}
```

### A1.q6 — borne réelle DVF

```sql
SELECT max(date_mutation)::date, max(extract(year FROM date_mutation))::int FROM dvf_mutations;
-- → 2026-08-10 | 2026
SELECT name, source_millesime FROM data_sources WHERE name ILIKE '%DVF%';
-- → « géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 »
```

### A1.q5 — médiane des « 22 ventes » calculée mais non imprimée

```sh
# la mesure : flash._marche → med_m2_bati = 4207 (audit_valeurs.json, T1)
grep -n "4 207\|4207" ~/Desktop/exports/97415000BO0852/dossier.txt   # → aucun hit
sed -n '184,190p' ~/Desktop/exports/97415000BO0852/dossier.txt        # légende sans le chiffre
```

### A2 — la vente d'immeuble « appartement 750 m² »

```sql
SELECT date_mutation, type_local, surface_reelle_bati, valeur_fonciere
FROM dvf_mutations WHERE valeur_fonciere=4500000 AND date_mutation='2025-06-17';
-- → UNE ligne : Appartement | 750 | 4500000
SELECT mutation_id, nature_mutation, surface_terrain, left(raw::text, 600)
FROM dvf_mutations WHERE valeur_fonciere=4500000 AND date_mutation='2025-06-17';
-- → 2025-1268771 | Vente | 170 | {"vefa": false, "source": "geo-dvf Etalab (data.gouv)", …}
```

Présence dans les documents : `sed -n '213,228p' ~/Desktop/exports/97415000BO0852/fiche.txt`
(table 12 ventes avec 750 m²/6 000, 10 135, 814) ; `sed -n '198,213p' …/dossier.txt` (table 5 ventes avec 750 m²).

### A3 — la table orpheline `parcel_residuel_bati`

```sql
SELECT emprise_batie_m2, emprise_max_m2, emprise_residuelle_m2, hauteur_bati_m,
       hauteur_max_m, surelevation_possible, confiance
FROM parcel_residuel_bati WHERE idu='97415000BO0852';
-- → 540.4 | 667.8 | 127.4 | 9.4 | 16 | t | moyenne     (127 = 667.8 − 540.4 ; 667.8 = 742×0.9 ; 6.6 = 16 − 9.4)
SELECT min(updated_at)::date, max(updated_at)::date FROM parcel_residuel_bati;   -- 2026-07-10 | 2026-07-11
SELECT count(*), count(emprise_max_m2) FROM parcel_residuel_bati;                 -- 292056 | 43420
```

```sh
# Le bâtisseur retiré du code actif (spin-off « Vues », 24/07/2026) :
git log --all --oneline -S "parcel_residuel_bati" | head    # → 7fd96725 [M12-C-bis] Spin-off « Vues »
git show 7fd96725^:src/labuse/segments/residuel_bati.py | head -60
#   « emprise_max_m2 = surface parcelle × coefficient d'emprise du zonage (emprise_sol_pct) ;
#     emprise_residuelle_m2 = max(0, emprise_max_m2 − emprise bâtie BD TOPO) ;
#     surelevation_possible = hauteur max du zonage − hauteur bâtiment BD TOPO ≥ 2,8 m »
# Lecteurs encore vivants :
grep -rn "parcel_residuel_bati" src/labuse --include="*.py" -l
# → flash/data.py (238-250), renouvellement.py (214-227), api/app.py, api/briques_pdf.py, scoring/…
```

### A3 / zone — les deux résolutions de zone qui divergent (T3/T4)

```sql
SELECT idu, zone_lib, zone_fam FROM parcel_zone_plu
WHERE idu IN ('97416000DY0106','97411000AV0110');
-- → DY0106 = N ; AV0110 = Uh (dominante par surface, api/tiles.py:35-80)
```

```sh
# faisabilité (zone du centroïde, faisabilite/db.py:29-36) — via audit_valeurs.json :
#   DY0106 → zone "Ud", constructible=true, logements (27,31), SDP 6837
#   AV0110 → zone "N", constructible=false, cause=zone_non_constructible:N
```

### A4 — les cinq définitions de permis (T1, 05/09)

```
flash._dynamique (500 m·24 mois)        → 18   (audit_valeurs.json ; dossier.txt:219-227 « AUTORISATIONS (500 M · 24 MOIS) : 18 »)
cascade phase2 (≤400 m·5 ans)          → 17   (fiche.txt:106 « Dynamique constructive : 17 PC à ≤ 400 m sur 5 ans »)
voisinage (<100 m·36 mois)             → 0    (fiche.txt:179)
nearby_permits défauts (300 m·5 ans)   → 6 lignes ≤168 m (banquier.txt:256-270)
viabilisation (<100 m)                 → 6 autorisés, 2 depuis 2022 (fiche.txt:149, dossier.txt:319)
```

Preuve du profil menteur : `sed -n '181,195p' src/labuse/marche_service.py` (appel `nearby_permits(db, pid)`
sans rayon) + `sed -n '234,235p' src/labuse/ingestion/permits.py` (défauts `radius_m=300.0, dynamique_years=5`).

### A6 — les deux verdicts accès dans le même JSON servi

```sh
python3 - <<'EOF'
import json
f = json.load(open('/Users/openclaw/Desktop/exports/97415000BO0852/fiche.json'))
print([l for l in f['lines'] if l.get('layer')=='acces'][0]['detail'])
# → « Pas d'accès direct évident à la voirie. »
print(f['viabilisation']['contributions'][1]['detail'])
# → « voie au contact + bâti riverain → réseaux enterrés sous voirie »
EOF
```

### A7 — ICPE « Non ICPE » : donnée amont brute

```sql
SELECT name, subtype, attrs->>'regime' FROM spatial_layers
WHERE kind='icpe' AND name ILIKE '%ENGEN%';
-- → 7 lignes ; « ENGEN (ex CALTEX) - St Paul » : subtype = regime = 'Non ICPE'
```

### A10 — pct_qpv et parc social

```sql
SELECT insee, nb_logements, pct_qpv FROM rpls_commune
WHERE insee IN ('97415','97401','97416','97411');
-- → pct_qpv = 100.0 pour les 4 (7265 / 649 / 7572 / 25185 logements)
```

Masquage servi : `sed -n '3482,3490p' src/labuse/api/app.py` (le dict fiche retire `pct_qpv`).
Vérif PDF 05/09 : `grep "QPV" ~/Desktop/exports/97415000BO0852/fiche.txt` → la ligne « Parc social »
n'imprime plus de %.

## §B — LOT B (requêtes exécutées le 05/09)

```sql
-- B1 DPE
SELECT count(*), count(parcelle_idu), count(DISTINCT parcelle_idu),
       max(date_etablissement), min(date_etablissement) FROM dpe_records;      -- 17 | … | 14 | 2026-07-21
SELECT rattachement, count(*) FROM dpe_records GROUP BY 1;                     -- ban_locale 13 / point_ban 2 / aucun 2
SELECT code_insee, count(*) FROM dpe_records GROUP BY 1 ORDER BY 2 DESC;

-- B2 BDNB
SELECT table_name FROM information_schema.tables WHERE table_name ILIKE '%bdnb%';  -- 0 ligne
SELECT name, source_millesime, status FROM data_sources WHERE name ILIKE '%bdnb%';
-- → BDNB | 2026-02-a (métropole seule — 974 absent) | a_faire

-- B3 CoSIA / végétation
SELECT count(*), round(100.0*count(*)/431663,2) FROM p_model_bati_cosia;       -- 321314 | 74.44
SELECT count(*) FROM qa_cosia_bati;                                            -- 445190
SELECT count(*), count(canopee_pct), round(100.0*count(canopee_pct)/count(*),1),
       max(updated_at)::date FROM parcel_vegetation;                           -- 431663 | … | 98.7 | 2026-08-13
SELECT idu, emprise_cosia_m2, source_millesime FROM p_model_bati_cosia
WHERE idu IN ('97415000BO0852','97401000AD0554','97416000DY0106','97411000AV0110');
SELECT idu, ndvi_moyen, canopee_pct, confiance FROM parcel_vegetation
WHERE idu IN ('97415000BO0852','97401000AD0554','97416000DY0106','97411000AV0110');

-- B4 historique propriété
SELECT millesime, count(*) FROM pm_proprietaires_millesimes GROUP BY 1 ORDER BY 1;  -- 2019→2024
SELECT count(DISTINCT idu) FROM pm_proprietaires_millesimes;                        -- 91397
SELECT max(date_import)::date FROM pm_proprietaires_millesimes;                     -- 2026-07-12

-- B7 contacts
SELECT count(*), count(DISTINCT insee) FROM commune_contacts;                  -- 0 | 0

-- B8 programmes
SELECT count(*), count(op_siren), count(DISTINCT commune), max(date_releve) FROM programmes;
-- → 9 | 5 | 4 | 2026-08-31

-- B11 pige/Radar
SELECT statut, count(*) FROM pige_biens GROUP BY 1;
SELECT count(*), count(idu), count(DISTINCT commune) FROM pige_biens WHERE statut='active';  -- 104 | 7 | 12
SELECT rattachement_niveau, count(*) FROM pige_biens WHERE statut='active' GROUP BY 1;       -- absent 85 / estime 12 / source 7
SELECT max(date_derniere_confirmation)::date, min(date_premiere_saisie)::date
FROM pige_biens WHERE statut='active';                                                        -- 2026-08-31 | 2026-08-29

-- B13 millésimes
SELECT name, source_millesime FROM data_sources
WHERE source_millesime IS NULL OR source_millesime='' ORDER BY name;           -- 31 lignes
SELECT ds.name, sv.methode, sv.dernier_vu, sv.dernier_passage_at::date, sv.dernier_statut
FROM data_sources ds JOIN source_veille sv ON sv.source_id=ds.id
WHERE ds.source_millesime IS NULL OR ds.source_millesime='';                   -- 17 lignes
SELECT ds.name, ds.last_sync_at::date, (sv.id IS NOT NULL) AS veille
FROM data_sources ds LEFT JOIN source_veille sv ON sv.source_id=ds.id
WHERE ds.source_millesime IS NULL OR ds.source_millesime='' ORDER BY veille DESC, ds.name;
```

B10 (destinations, exécution réelle) :

```sh
pyaudit -c "
from labuse.plu.destinations import verdict
for c, z in [('Saint-Paul','U1a'), ('Les Avirons','Ud3'), ('Saint-Pierre','N'), ('Saint-Denis','Uh')]:
    v = verdict(c, z, 'logement')
    print(c, z, v.get('etat'), '|', (v.get('phrase') or '')[:80])
print(verdict('Saint-Paul','U1a','artisanat_commerce_detail').get('cdac'))
"
```

## §C — LOT C (sondes exécutées le 05/09)

```bash
# --- Base (lecture seule)
psql -U openclaw -d labuse -c "SELECT ds.name, sv.methode, sv.dernier_statut FROM source_veille sv JOIN data_sources ds ON ds.id=sv.source_id"   # 49 sources actives
psql -U openclaw -d labuse -c "SELECT subtype, count(*) FROM spatial_layers WHERE kind='plu_gpu_prescription' GROUP BY 1"   # typepsc 05 (ER)=2250, 01 (EBC)=1782…
psql -U openclaw -d labuse -c "SELECT subtype, count(*) FROM spatial_layers WHERE kind='sup' GROUP BY 1"                    # pm1/pm2/pm3/el10/ac1-4 — pas d'AS1/T5
psql -U openclaw -d labuse -c "SELECT insee, count(*) FROM catnat_arretes GROUP BY 1"                                       # 10 partout = troncature

# --- GPU / API Carto
curl "https://apicarto.ign.fr/api/gpu/municipality?insee=97409"                          # is_rnu=false (idem 97413/97417/97405)
curl "https://apicarto.ign.fr/api/gpu/document?geom={Point 55.646,-20.9605}"             # [] Saint-André — aucun DU
curl "https://apicarto.ign.fr/api/gpu/zone-urba?partition=DU_97409&_limit=1"             # 0 (97413, 97417 idem ; 97405=335 zones)
curl "https://apicarto.ign.fr/api/gpu/prescription-surf?geom={Point 55.4674,-20.8860}"   # ER typepsc 05 Saint-Denis (live)
curl "https://apicarto.ign.fr/api/gpu/prescription-surf?partition=DU_97405&_limit=5"     # 0 — Petite-Île sans prescriptions téléversées
curl "https://apicarto.ign.fr/api/gpu/info-surf?partition=DU_97411&_limit=3000"          # typeinf 04 DPU=41 ; ⚠ ?typeinf=04 NE filtre PAS (compter côté client)
curl "https://apicarto.ign.fr/api/gpu/assiette-sup-s?partition=130014368_SUP_974_AS1"    # 0 (A5/I4/EL9/T7 idem ; PM1=76)
curl "https://apicarto.ign.fr/api/gpu/assiette-sup-s?geom={Point 55.5169,-20.8871}"      # piste Roland-Garros : PM1 oui, T5 NON servi
curl "https://www.geoportail-urbanisme.gouv.fr/api/document?documentType%5B%5D=SUP&grid=974&page=N"  # 24 doc SUP 974 ; T5 production 09/07/2026 ; pas d'AS1

# --- Géorisques
curl "https://georisques.gouv.fr/api/v1/gaspar/catnat?code_insee=97411&page_size=100"    # 21 arrêtés (base=10) ; 97415→24 ; 97410→17
curl "https://georisques.gouv.fr/api/v1/zonage_sismique?code_insee=97411"                # « 2 - FAIBLE » (14 communes sondées)
curl "https://georisques.gouv.fr/api/v1/rga?latlon=55.45,-20.93"                         # corps vide au 974 ; témoin 1.44,43.60 → « Exposition moyenne »
grep -rn "catnat" src/labuse/cli.py src/labuse/api/ops.py                                # cli.py:2630 (commande retirée), ops.py:28-29 (cron retiré)
ls /etc/cron.d/ 2>/dev/null                                                              # inexistant sur cette machine

# --- PEB
curl "https://data.geopf.fr/wms-v/ows?...GetFeatureInfo&LAYERS=dgac_peb_plan_wmsv&BBOX=-20.91,55.49,-20.85,55.54"   # zone D Lden 50 Roland-Garros
curl "...&BBOX=-21.3229,55.4197,-21.3149,55.4277"                                                                    # zone C Lden 52 Pierrefonds

# --- DEAL Lizmap (recherche captages AS1)
curl "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&REQUEST=GetCapabilities"  # ~95 couches, pas de captage
curl "...repository=02sprinr&project=01risque&..."                                        # PPR_APPROUVE, aléas, TRI — pas de captage

# --- Économique
curl ".../liste-ensemble-des-communes-zonage-abc-en-vigueur-26-juin-2026.csv" | grep 974  # 4 communes zone A + 20 en B1
curl ".../pred-app-mef-dhup.csv" | grep '"974'                                            # carte des loyers DHUP 2025 : 24/24 communes
curl "https://lareunion.opendatasoft.com/api/explore/v2.1/.../financement-et-cout-des-logements-sociaux-construits-a-la-reunion/records"  # 2 842 €/m² SU (2025)
```

## Scripts (copie de référence)

### `~/Desktop/exports/generer.sh`

```sh
#!/bin/zsh
set -e
[ -n "$1" ] || { echo "usage: generer.sh <IDU>"; exit 1; }
cd /Users/openclaw/Desktop/labuse-merge
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
PYTHONPATH=/Users/openclaw/Desktop/labuse-merge/src \
/Users/openclaw/miniforge3/envs/labusedb/bin/python \
  /Users/openclaw/Desktop/exports/generer.py "$1"
```

### `~/Desktop/exports/generer.py` — cœur

```python
from fastapi.testclient import TestClient
from labuse.api.app import app
c = TestClient(app)
c.get(f"/parcels/{IDU}")                 # → fiche.json (référence écran)
c.get(f"/parcels/{IDU}/export.pdf")      # → fiche.pdf
c.get(f"/dossier/{IDU}.pdf")             # → dossier.pdf
c.get(f"/dossier-banquier/{IDU}.pdf")    # → banquier.pdf
c.get(f"/argumentaire/{IDU}.pdf")        # → argumentaire.pdf (2500 €/m² · 21 % · VRD 90)
c.get(f"/pre-dossier/{IDU}.zip")         # → predossier-pc.zip
from labuse.flash.report import generate_flash_report
generate_flash_report(IDU, order_ref=f"AUDIT-{IDU[-6:]}", force=True)   # → flash.pdf
```

### `~/Desktop/exports/audit_valeurs.py`

Script complet conservé hors dépôt ; il appelle, pour chaque témoin, les moteurs listés au §A1/A2/A3/A4
ci-dessus avec les mêmes imports que les exports, et écrit `audit_valeurs.json`. Toute valeur de la
colonne « Valeurs » du LOT A en provient ou provient d'un `<doc>.txt` extrait par `pdftotext`.

## §catalogue — vérification de SOURCES-CATALOGUE.md (05/09)

```sql
SELECT count(*) FROM data_sources;                                   -- 77
SELECT count(*) FROM source_veille;                                  -- 49
SELECT fraicheur_statut, count(*) FROM data_sources GROUP BY 1;      -- sans_echeance 62 · NULL 10 · a_jour 3 · en_retard 2
SELECT status, count(*) FROM data_sources GROUP BY 1;                -- connecte 65 · a_faire 6 · manuel 4 · hub 2
SELECT id, name FROM data_sources
WHERE id IN (1,5,16,18,37,61,70,71,83,84,87,88,89,93,94,95);         -- 16/16 conformes au catalogue
SELECT ds.id, ds.name, sv.dernier_statut, ds.fraicheur_statut
FROM data_sources ds LEFT JOIN source_veille sv ON sv.source_id=ds.id
WHERE ds.id IN (5,13,16) OR sv.dernier_statut <> 'ok';
-- → 5 DVF en_retard · 13 DEAL injoignable · 16 SITADEL nouvelle_version
-- sous-ensembles testés pour le « 44 » : sous veille+sans_echeance = 40 ; connectées+sans_echeance = 58 → aucun ne donne 44
```

```sh
for kw in sudocuh egoul "plh" lidar mnh "réunion express" tcsp; do
  grep -rniE "$kw" src/labuse/flash/ src/labuse/api/briques_pdf.py src/labuse/api/pdf_premium.py \
    src/labuse/api/argumentaire.py src/labuse/api/banquier.py src/labuse/api/pre_dossier.py
done
# → 0 occurrence partout SAUF egoul : api/pre_dossier.py:563 (notice PCMI4, source ANC)
```
