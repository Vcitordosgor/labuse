# Domaine 7 — Permis (Sitadel / pc_caducs), DPE, BODACC servis

## Verdict (3 lignes)
50 809 permis + 4 822 PC caducs + 1 123 DPE + 674 procédures / 14 078 dépôts / 1 418 annonces BODACC passés au crible, rattachés au stock de 434 582 parcelles.
13 invariants vérifiés sur TOUT le stock : **0 violation FAUX-CLIENT**, **0 INCOHERENT non géré**, **0 ROBUSTESSE active**. Les 3 anomalies de source (dates inversées, clôture 2117, SIREN hors SIRENE) sont déjà neutralisées au niveau LECTEUR (note transparente, filtre `<= now()`, dénomination résolue par `parcelle_personne_morale`).
Resté muet : les lecteurs géométriques (`permits.geojson`, `nearby_permits` rayon 300 m) non rejoués côté rendu ; la véracité externe des idu_codes / numéros DPE non confrontée à la source SDES/ADEME.

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles/lignes passées | violations |
|---|---|---|---|---|
| I1 | Tout PC caduc servi est rattaché à une parcelle EXISTANTE (idu ∈ parcels). | `SELECT count(*) FROM pc_caducs pc LEFT JOIN parcels p ON p.idu=pc.idu WHERE p.idu IS NULL;` | 4 822 | 0 |
| I2 | Tout permis SITADEL rattaché par idu à une fiche référence au moins une parcelle existante (sinon jamais servi par idu). | `SELECT count(*) FROM sitadel_permits s WHERE jsonb_typeof(idu_codes)='array' AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(s.idu_codes) e(idu) JOIN parcels p ON p.idu=e.idu);` | 50 809 | 0 servi par idu* |
| I3 | Aucune date de permis (autorisation/dépôt) dans le futur (> 2026-10-14). | `SELECT count(*) FROM sitadel_permits WHERE date::date > DATE '2026-10-14' OR date_depot > DATE '2026-10-14';` | 50 809 | 0 |
| I4 | Aucune date BODACC (parution/annonce) dans le futur. | `SELECT count(*) FROM bodacc_procedures WHERE date_annonce>DATE '2026-10-14';` + depots.date_parution + owner.date_annonce | 16 170 | 0 |
| I5 | Aucune date de clôture d'exercice BODACC servie dans le futur. | `SELECT count(*) FROM bodacc_depots WHERE date_cloture > DATE '2026-10-14';` | 14 078 | 1 (non servi, filtré) |
| I6 | Aucune date de DPE (établissement) ni année de construction dans le futur. | `SELECT count(*) FROM dpe_records WHERE date_etablissement>DATE '2026-10-14' OR annee_construction>2026;` | 1 123 | 0 |
| I7 | Tout DPE servi (etiquette non nulle + parcelle_idu) est rattaché à une parcelle EXISTANTE. | `SELECT count(*) FROM dpe_records d LEFT JOIN parcels p ON p.idu=d.parcelle_idu WHERE d.etiquette_dpe IS NOT NULL AND d.parcelle_idu IS NOT NULL AND p.idu IS NULL;` | 1 100 servables | 0 |
| I8 | Tout DPE servi est rattaché par une adresse valide (rattachement BAN/adresse, INSEE connu, jamais « aucun »). | `SELECT rattachement,count(*) FROM dpe_records WHERE etiquette_dpe IS NOT NULL AND parcelle_idu IS NOT NULL GROUP BY 1;` + jointure `communes_referentiel` | 1 100 | 0 |
| I9 | Toute étiquette DPE servie est une valeur légale A–G. | `SELECT count(*) FROM dpe_records WHERE etiquette_dpe IS NOT NULL AND etiquette_dpe !~ '^[A-G]$';` | 1 123 | 0 |
| I10 | Toute entrée BODACC servie (proc/owner/dépôt attachée à un owner de parcelle) résout vers une société CONNUE (dénomination). | `… JOIN parcelle_personne_morale ppm … LEFT JOIN sirene_etablissements se … WHERE (ppm.denomination IS NULL OR '') AND se.siren IS NULL;` | 177 SIREN servis (proc) | 0 |
| I11 | La caducité d'un PC dormant est datée de façon cohérente (pc_annee ≤ caduc_depuis ≤ 2026, n_pc_octroyes>0). | `SELECT count(*) FROM pc_caducs WHERE caduc_depuis<pc_annee OR caduc_depuis>2026 OR pc_annee>2026 OR n_pc_octroyes<=0;` | 4 822 | 0 |
| I12 | Pas de doublon d'identifiant servi (permit_id, numero_dpe uniques). | `SELECT count(*) FROM (SELECT permit_id FROM sitadel_permits GROUP BY 1 HAVING count(*)>1) x;` idem numero_dpe | 50 809 + 1 123 | 0 |
| I13 | Si le dépôt est postérieur à l'autorisation (impossible), l'incohérence est QUALIFIÉE à l'écran (jamais servie muette). | `SELECT count(*) FROM sitadel_permits WHERE date_depot>date::date;` confronté à `exports/miroir.permis_incoherence_note` | 50 809 | 0 muet (7 754 notés) |

\* I2 : 10 800 permis ne référencent AUCUNE parcelle existante par idu_codes, mais ils ne sont **jamais** servis par les lecteurs idu (`historique_permis` `idu_codes ? :idu`, `depots_recents`, `nearby_permits` par idu). Ils ne subsistent qu'en couche carte / voisinage géométrique (voir Violations V3).

## Violations

Aucune violation FAUX-CLIENT ni INCOHERENT active. Trois anomalies de **source** repérées, toutes déjà neutralisées par le code lecteur — listées pour traçabilité.

### V1 — ROBUSTESSE (NEUTRALISÉE) · clôture d'exercice BODACC en l'an 2117
- idu/clé : `bodacc_depots.annonce_id = C201900709638`, SIREN `443565023` (AUSTRAL PROMOTION), `date_cloture = 2117-11-03`.
- attendu : date de clôture ≤ aujourd'hui ; obtenu : 2117 (coquille producteur BODACC, parution réelle 2019-04-09).
- impact servi : **nul**. Le lecteur filtre `max(date_cloture) FILTER (WHERE date_cloture <= now()::date)` et retombe sur `date_parution.year`.
- cause : garbage à l'ingestion (pas de borne haute sur `date_cloture`). `src/labuse/api/modules.py:262-266` (garde présente) ; l'ingestion n'assainit pas l'entrée amont.

### V2 — ROBUSTESSE (NEUTRALISÉE) · 7 754 permis avec dépôt postérieur à l'autorisation
- idu/clé : 7 754 lignes `sitadel_permits` (5 848 rattachées à une parcelle réelle ; 7 412 avec écart > 31 j, 342 ≤ 31 j).
- attendu : `date_depot ≤ date_autorisation` ; obtenu : inversion (producteur SDES/Dido — modificatifs/transferts sans n° de modificatif dans l'open data).
- impact servi : **nul/transparent**. Chaque ligne porte `note_incoherence` à l'écran et au PDF : « Dépôt enregistré après l'autorisation — souvent un permis modificatif ou transféré » (> 31 j) ou « dates incohérentes chez le producteur » (≤ 31 j). Jamais réordonné.
- cause : qualité source ; géré par `src/labuse/exports/miroir.py:303` (`permis_incoherence_note`), appelé `src/labuse/api/site_voisinage.py:59`.

### V3 — ROBUSTESSE (bornée) · 10 800 permis sans aucune parcelle existante, visibles en couche carte / voisinage
- idu/clé : 10 800 `sitadel_permits` dont tous les `idu_codes` sont absents de `parcels` (sur 50 809) ; 12 253 permis ont ≥ 1 code mort.
- attendu : un permis servi devrait pointer une parcelle du stock servi ; obtenu : ces 10 800 ne sont rattachables à aucune fiche par idu, mais `GET /map/permits.geojson` (`app.py:7517`) et `nearby_permits` (rayon 300 m géom, `ingestion/permits.py:265`) les affichent par géométrie.
- impact servi : marqueur carte / « permis à proximité » sans fiche parcellaire cible. Ni FAUX chiffre ni incohérence de fiche — le point reste factuel (date + type). Gravité ROBUSTESSE basse : décalage référentiel parcellaire (idu_codes SDES antérieurs au millésime cadastral servi, ou hors périmètre ingéré).
- cause : les idu_codes SITADEL ne sont pas re-vérifiés contre `parcels` à l'ingestion ; `src/labuse/ingestion/permits.py:68` insère les codes bruts.

### Note V4 — 35 SIREN BODACC servis absents de `sirene_etablissements` (NON une violation)
177 SIREN sont servis via `bodacc_procedures` attachés à un owner de parcelle ; 35 n'ont pas d'établissement dans `sirene_etablissements` (table de référence incomplète), MAIS **tous** résolvent une dénomination via `parcelle_personne_morale`. L'invariant « société connue » tient donc au niveau serving (0 société anonyme servie). `sirene_etablissements` n'est pas la source d'identité du serving.

## Non vérifié
- **Lecteurs géométriques** : `permits.geojson` et `nearby_permits` (buffer 300 m) non exécutés via l'API — vérifiés seulement par leurs requêtes SQL. Le rendu carte des 10 800 permits orphelins (V3) n'a pas été observé à l'écran.
- **Véracité externe** : les idu_codes, numéros DPE et SIREN n'ont pas été confrontés aux sources amont (SDES, ADEME, INSEE) — seule la cohérence INTERNE (présence en base, dates, format) est prouvée.
- **BODACC `date_jugement_txt`** : champ texte libre servi tel quel ; 0 année future 2027+ détectée par regex, mais les formats non datés (« voir annonce ») ne sont pas validés sémantiquement.
- **DPE geocode_score < 0,5** (396 servables) : qualité du géocodage non contrôlée au-delà du fait que le rattachement est BAN/adresse (jamais « aucun ») — risque résiduel d'adresse approximative, pas fantôme.

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (chacune rend `("OK"|"ECART", msg)` ; exit 1 si un ECART). N'empiètent pas sur `g10_sirene_etat`/`g11_bodacc_fraicheur` déjà dans `chasse_donnees.py`.

```python
TODAY = "2026-10-14"  # ou db.execute("SELECT now()::date")

def g7_01_pc_caduc_idu_present(db):
    """Tout PC caduc est rattaché à une parcelle existante."""
    n = db.execute("SELECT count(*) FROM pc_caducs pc LEFT JOIN parcels p ON p.idu=pc.idu WHERE p.idu IS NULL").scalar()
    return ("ECART", f"{n} PC caducs orphelins") if n else ("OK", "pc_caducs ⊆ parcels")

def g7_02_dpe_servi_rattache(db):
    """DPE servi (etiquette + parcelle_idu) → parcelle existante, INSEE connu, rattachement != 'aucun'."""
    n = db.execute("""SELECT count(*) FROM dpe_records d LEFT JOIN parcels p ON p.idu=d.parcelle_idu
      LEFT JOIN communes_referentiel c ON c.insee=d.code_insee
      WHERE d.etiquette_dpe IS NOT NULL AND d.parcelle_idu IS NOT NULL
        AND (p.idu IS NULL OR c.insee IS NULL OR d.rattachement='aucun')""").scalar()
    return ("ECART", f"{n} DPE servis mal rattachés") if n else ("OK", "DPE servis rattachés")

def g7_03_aucune_date_future(db):
    """Aucune date servie dans le futur (permis, DPE, BODACC annonce/parution).
    date_cloture BODACC EXCLUE : coquilles amont déjà filtrées par le lecteur (modules.py)."""
    q = f"""SELECT
      (SELECT count(*) FROM sitadel_permits WHERE date::date>DATE '{TODAY}' OR date_depot>DATE '{TODAY}')
     +(SELECT count(*) FROM dpe_records WHERE date_etablissement>DATE '{TODAY}' OR annee_construction>2026)
     +(SELECT count(*) FROM bodacc_procedures WHERE date_annonce>DATE '{TODAY}')
     +(SELECT count(*) FROM bodacc_depots WHERE date_parution>DATE '{TODAY}')
     +(SELECT count(*) FROM bodacc_annonces_owner WHERE date_annonce>DATE '{TODAY}')"""
    n = db.execute(q).scalar()
    return ("ECART", f"{n} dates futures servies") if n else ("OK", "0 date future servie")

def g7_04_etiquette_dpe_legale(db):
    n = db.execute("SELECT count(*) FROM dpe_records WHERE etiquette_dpe IS NOT NULL AND etiquette_dpe !~ '^[A-G]$'").scalar()
    return ("ECART", f"{n} étiquettes DPE hors A-G") if n else ("OK", "étiquettes DPE A-G")

def g7_05_pc_caduc_dates_coherentes(db):
    n = db.execute("SELECT count(*) FROM pc_caducs WHERE caduc_depuis<pc_annee OR caduc_depuis>2026 OR pc_annee>2026 OR n_pc_octroyes<=0").scalar()
    return ("ECART", f"{n} PC caducs mal datés") if n else ("OK", "caducité datée cohérente")

def g7_06_bodacc_servi_societe_connue(db):
    """Toute procédure BODACC servie (attachée à un owner de parcelle) résout une dénomination."""
    n = db.execute("""SELECT count(DISTINCT bp.siren) FROM bodacc_procedures bp
      JOIN parcelle_personne_morale ppm ON ppm.siren=bp.siren
      LEFT JOIN sirene_etablissements se ON se.siren=bp.siren
      WHERE (ppm.denomination IS NULL OR ppm.denomination='') AND se.siren IS NULL""").scalar()
    return ("ECART", f"{n} SIREN BODACC servis sans dénomination") if n else ("OK", "BODACC servi → société connue")

def g7_07_identifiants_uniques(db):
    """permit_id et numero_dpe uniques (pas de doublon servi)."""
    n = db.execute("""SELECT (SELECT count(*) FROM (SELECT 1 FROM sitadel_permits GROUP BY permit_id HAVING count(*)>1) a)
                           +(SELECT count(*) FROM (SELECT 1 FROM dpe_records GROUP BY numero_dpe HAVING count(*)>1) b)""").scalar()
    return ("ECART", f"{n} identifiants dupliqués") if n else ("OK", "permit_id/numero_dpe uniques")

def g7_08_depot_inverse_toujours_note(db):
    """Un permis au dépôt postérieur à l'autorisation ne doit JAMAIS être servi muet :
    la note d'incohérence (exports.miroir.permis_incoherence_note) doit être non vide.
    Garde de non-régression du lecteur, pas de la donnée source."""
    from labuse.exports.miroir import permis_incoherence_note
    muet = db.execute("""SELECT date_depot::text, date::date::text FROM sitadel_permits
      WHERE date_depot IS NOT NULL AND date IS NOT NULL AND date_depot>date::date LIMIT 2000""").fetchall()
    rates = [1 for dep, aut in muet if not permis_incoherence_note(dep, aut)]
    return ("ECART", f"{len(rates)} inversions servies sans note") if rates else ("OK", f"{len(muet)} inversions, toutes notées")
```

Garde de SURVEILLANCE (facultative, non bloquante — V3 est un décalage référentiel assumé) :
```python
def g7_09_permits_orphelins_carte(db):
    """Signale (sans bloquer) les permis dont AUCUN idu_codes n'existe en parcels : visibles
    en couche carte/voisinage géom mais rattachables à aucune fiche. Seuil d'alerte informatif."""
    n = db.execute("""SELECT count(*) FROM sitadel_permits s WHERE jsonb_typeof(idu_codes)='array'
      AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(s.idu_codes) e(idu) JOIN parcels p ON p.idu=e.idu)""").scalar()
    return ("OK", f"{n} permits sans parcelle (carte/voisinage géom seulement — décalage référentiel SDES, non servi par idu)")
```
