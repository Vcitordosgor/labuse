# MANDAT FABLE — Wave Copro, Tertiaire & Flux : clôture de la carte data

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/wave-copro-tertiaire-flux` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot.

**Dépendance souple** : les presets de ce mandat s'implémentent dans le moteur de segments (`feat/moteur-segments-habitat`) s'il est mergé ; sinon, les données s'ingèrent quand même et les presets sont livrés en seed prêt à activer. Aucun lot n'est bloqué.

---

## 1. Contexte

Dernière vague d'ingestion : après elle, la carte de l'open data exploitable du 974 est close. Elle ouvre deux univers nouveaux où le décideur est un **professionnel récurrent** (syndics de copropriété, exploitants de locaux pro) plutôt qu'un particulier — cycles de vente différents, paniers plus gros, récurrence naturelle.

## 2. Schéma cible

```sql
coproprietes(id PK, immatriculation unique, adresse text, insee, commune,
             geom point, idu text,                    -- rattachement parcelle
             nb_lots_total int, nb_lots_habitation int,
             periode_construction text,
             syndic_type text,                        -- 'professionnel'|'benevole'|'cooperatif'
             syndic_nom text,                         -- NULL si bénévole (RGPD, voir contraintes)
             raw jsonb, updated_at)
dpe_tertiaire(id PK, adresse, insee, geom, idu, classe_energie, classe_ges,
              surface_m2, usage text, date_dpe, raw jsonb)
etablissements_flux(siret PK, denomination, naf, insee, commune, geom, idu,
                    date_creation, caractere_employeur bool, statut_diffusion text, raw jsonb)
peb_zones(id PK, aeroport text, zone text, geom polygon, source, raw jsonb)
-- ICPE : intégrer au pattern spatial_layers existant
```

---

## Lot 1 — RNIC : les copropriétés 🔥 le plus gros ajout

**Source** : Registre National d'Immatriculation des Copropriétés (ANAH) — open data sur data.gouv.fr, filtrage département 974.

1. Ingestion → `coproprietes`. Géolocalisation : si références cadastrales présentes dans le RNIC, matcher par IDU (réutiliser `_idu()`) ; sinon géocodage **BAN** (api-adresse.data.gouv.fr, batch CSV) → parcelle contenante. Taux de rattachement au rapport.
2. **Règle RGPD stricte** : `syndic_nom` renseigné UNIQUEMENT si `syndic_type='professionnel'` (personne morale). Un syndic bénévole est une personne physique → stocker le type, jamais le nom, même si le RNIC le fournit.
3. Presets copro (catégorie "Copropriété" du moteur) :
   - `copro-ravalement-ite` : construction < 1990, ≥ 10 lots — tri âge desc
   - `copro-bornes-ve` : ≥ 15 lots — argumentaire : droit à la prise + électrification du parc, le syndic qui reçoit une offre clé en main la met à l'ordre du jour de l'AG
   - `copro-controle-acces` : ≥ 10 lots, construction < 2000
   - `copro-ascenseurs` : ≥ 20 lots, construction < 2000 — **proxy assumé** (le RNIC ne garantit pas l'info ascenseur ; l'argumentaire du preset le dit : "copropriétés de taille et d'âge où un ascenseur vieillissant est probable")
4. Colonnes d'export copro : adresse, commune, nb lots, période, type de syndic, nom du syndic (si pro). C'est un export B2B, pas "à l'occupant".

## Lot 2 — DPE tertiaire + décret tertiaire

**Source** : open data ADEME, dataset DPE tertiaire — même pipeline que le DPE résidentiel déjà en base (réutiliser le connecteur, adapter le dataset).

1. Ingestion → `dpe_tertiaire`, géocodage/rattachement idem Lot 1.
2. **Assujettis probables décret tertiaire** (obligation de réduction de consommation, plateforme OPERAT — la liste officielle des assujettis n'est pas publique, on identifie les *probables*) : emprises bâties > 1 000 m² × usage tertiaire (DPE tertiaire OU établissement SIRENE/Places rattaché) → flag `decret_tertiaire_probable`.
3. Preset `decret-tertiaire` : assujettis probables, tri par classe énergie desc (D-E-F-G d'abord) — cible : BE énergie, CVC, GTB, installateurs LED. Enrichit aussi la vue tertiaire du mandat Solaire (classe énergie en colonne).
4. Vérifier par une recherche courte les seuils/jalons exacts du dispositif Éco Énergie Tertiaire avant d'écrire l'argumentaire (jalons -40/-50/-60% — dates à confirmer) ; seuils en config.

## Lot 3 — SIRENE flux : le signal "nouveau local pro"

**Source** : fichiers SIRENE établissements géolocalisés (INSEE, open data) — stock initial 974 + flux mensuel des créations.

1. Ingestion → `etablissements_flux` : créations < 24 mois glissants, filtre NAF sur les secteurs à local physique probable (commerce de détail, CHR, industrie légère, santé, services avec accueil — liste NAF en config). **Respecter le statut de diffusion INSEE** : les établissements en diffusion partielle ne sont ni stockés ni exportés au-delà de ce que l'INSEE diffuse.
2. Signal `nouveau_commerce` : création < 3 mois — le local est en cours d'aménagement, c'est LA fenêtre.
3. Presets (catégorie "Local pro") : `agenceurs-nouveaux-locaux` (créations < 3 mois, NAF commerce/CHR), `enseignistes` (idem), `frigoristes-chr` (NAF restauration/alimentaire), `electriciens-securite-pro` (créations < 6 mois, tous NAF retenus). Export B2B : dénomination, NAF, adresse, date de création.
4. Refresh : intégré au job mensuel.

## Lot 4 — PEB aéroports : menuiseries acoustiques

1. **Source** : Plans d'Exposition au Bruit de Roland-Garros et Pierrefonds — chercher sur le GPU (servitudes/annexes) puis portails DGAC/préfecture. Ingestion des zones A/B/C(/D) → `peb_zones`.
2. **Point de rigueur** : les aides à l'insonorisation des riverains relèvent du **PGS** (Plan de Gêne Sonore, dispositif TNSA), pas du PEB. Fable vérifie si Roland-Garros dispose d'un PGS/dispositif d'aide actif : si OUI → l'argumentaire du preset mentionne "travaux potentiellement aidés" (avec la source) ; si NON → l'argumentaire reste "zone d'exposition au bruit = besoin réel d'isolation acoustique", sans promesse d'aide. Ne jamais afficher une aide non vérifiée.
3. Preset `menuiseries-acoustiques` : parcelles bâties résidentielles × zones PEB (B/C prioritaires), croisé bâti ancien.
4. Bonus Foncier : zone PEB = information/malus sur la fiche parcelle (constructibilité contrainte en zones A/B) — brancher au scoring existant en simple flag informatif, pas de refonte.

## Lot 5 — ICPE (micro-lot)

Installations classées géolocalisées (Géorisques, même famille que la wave existante) → couche `spatial_layers`. Deux effets : info fiche parcelle Foncier (proximité ICPE, régime) + malus léger optionnel au scoring (config, désactivé par défaut — Vic décidera). Une heure max.

## Lot 6 — Mesure de couverture DPE (le chiffre décisionnel Cerema)

Pas d'ingestion — une mesure pour trancher une décision d'achat :

```sql
SELECT commune,
       count(*) FILTER (WHERE dpe_present)::float / count(*) AS taux_couverture_dpe
FROM parcels p ... WHERE p.a_bati_residentiel GROUP BY 1;
```

Le rapport livre le taux global + par commune. **Règle de décision (pour Vic, pas pour Fable)** : si < 40% du bâti résidentiel a un DPE, les presets "bâti ancien" ratent la majorité du parc → la licence Fichiers Fonciers Cerema (seule source exhaustive d'année de construction) devient justifiable. Sinon, on vit très bien sans le seul dataset payant de la carte.

---

## Critères d'acceptation

```sql
-- Copros : volumétrie et rattachement
SELECT count(*), count(idu)::float/count(*), count(*) FILTER (WHERE syndic_type='benevole' AND syndic_nom IS NOT NULL)
FROM coproprietes;   -- rattachement ≥ 85% ; le 3e chiffre DOIT être 0 (RGPD)

-- Tertiaire
SELECT count(*) FROM dpe_tertiaire;  -- non trivial
SELECT count(*) FROM parcels WHERE decret_tertiaire_probable;  -- dizaines à centaines

-- Flux
SELECT date_trunc('month', date_creation), count(*) FROM etablissements_flux GROUP BY 1 ORDER BY 1;
-- flux mensuel régulier, pas de mois vide récent

-- PEB
SELECT aeroport, zone, count(*) FROM peb_zones GROUP BY 1,2;  -- les 2 aéroports présents

-- Statuts de diffusion respectés
SELECT count(*) FROM etablissements_flux WHERE statut_diffusion NOT IN ('diffusible','O','P');  -- règle documentée
```

+ Playwright : 3 presets de ce mandat (1 copro, 1 local pro, 1 PEB) chargent, filtrent, exportent non-vide.

## Contraintes

- **RGPD renforcé** : syndics bénévoles jamais nominatifs ; statuts de diffusion SIRENE respectés à l'ingestion ET à l'export ; exports copro/pro = données de personnes morales uniquement.
- Argumentaires de presets : factuels, sourcés, aucune promesse d'aide ou d'obligation non vérifiée dans les textes (PGS, décret tertiaire).
- Paramètres (seuils lots, NAF, fenêtres temporelles) en config/seed.
- Réseau : data.gouv (RNIC, SIRENE), ADEME, BAN, GPU/DGAC, Géorisques. Rien d'autre.
- Ordre conseillé : 1 → 3 → 2 → 4 → 5 → 6 (valeur décroissante, le 6 est une requête).

## Rapport de fin attendu

Volumétries par lot avec taux de rattachement, nb de copros par tranche de lots et par type de syndic, flux mensuel SIRENE moyen, statut PGS Roland-Garros (trouvé/pas trouvé, source), taux de couverture DPE global et par commune avec la recommandation Cerema chiffrée, et compteurs des nouveaux presets.
