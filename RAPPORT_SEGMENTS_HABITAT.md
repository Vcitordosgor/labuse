# RAPPORT DE FIN — Moteur de Segments Habitat (11 métiers, 1 architecture)

**Branche** : `feat/moteur-segments-habitat` (5 commits atomiques, merge réservé à Vic).
**Livré** : UN moteur de segments (registry de filtres + évaluateur SQL paramétré) + une
bibliothèque de 18 presets métiers **en données** (`segment_presets`, seed versionné
`config/segment_presets.yaml`). Ajouter le 31e métier = une ligne de preset (admin ou YAML),
zéro dev. Page « Segments » au rail, exports CSV « à l'occupant », signal CATNAT, droits
résiduels sur bâti calculés pour les 24 communes.

---

## 1. Filtres câblés et disponibilité constatée (18 / 25 disponibles)

| Filtre | Source | Dispo | Note |
|---|---|---|---|
| anciennete_mutation_mois | v_parcel_dvf_last | ✓ | ancrée sur le dernier millésime DVF (31/12/2025) — DVF publie avec ~6 mois de retard, sinon « < 6 mois » serait structurellement vide |
| prix_mutation_eur | v_parcel_dvf_last | ✓ | |
| type_bien | dvf_mutations_parcelle | ✓ | Maison / Appartement / Dépendance / Local |
| periode_construction | dpe_records | ✓ | **couverture mince : 910 DPE en base (vague pilote)** — les presets « âge du bâti » sont étroits mais corrects ; s'élargiront avec l'ingestion DPE île entière |
| flag_amiante | dpe_records | ✓ | proxy < 1997 (interdiction amiante) |
| emprise_batie_m2 · jardin_m2 · ces_probable_pct | parcel_residuel_bati (Lot 2) | ✓ | calculés ce jour, 24 communes |
| pente_moy_deg · pente_max_deg | parcel_terrain | ✓ | RGE ALTI 5 m (data-gap) |
| flag_abf | dryrun_cascade_results (run q_v3_datagap) | ✓ | abords MH ~500 m |
| zonage_plu | dryrun_cascade_results | ✓ | classes U / AU / A / N / hors |
| qpv | spatial_layers kind='qpv' | ✓ | |
| communes | parcels | ✓ | |
| proprio_occupant_pct | filosofi_carreaux_200m | ✓ | part de ménages propriétaires du carreau 200 m (proxy) |
| emprise_residuelle_m2 · surelevation_possible | parcel_residuel_bati (Lot 2) | ✓ | |
| catnat_recent | catnat_arretes (Lot 3) | ✓ | fenêtre 6 mois + périls en config |
| piscine · pv_detecte | parcel_equipements | ✗ grisé | **mandat Détection Ortho** |
| score_solaire · facture_elec_estimee_eur | parcel_solar | ✗ grisé | **mandat Habitat Solaire** |
| ombrage_vegetal · canopee_limite · zone_anc | parcel_vegetation / parcel_anc | ✗ grisé | **mandat ANC & Végétation** |

La disponibilité est détectée **à l'exécution** (tables/colonnes + non-vide) : quand un
mandat livrera sa table, ses filtres s'allumeront et les presets « partiels » se
complèteront sans un seul déploiement. Vérifié en sens inverse par test de résilience
(base sans parcel_solar/parcel_equipements → aucun crash, presets badgés partiels).

## 2. Compteurs par preset — le « combien de leads par métier »

Parc bâti de référence : **292 056 parcelles bâties** (emprise BD TOPO ≥ 5 m², 24 communes).

| Preset | Leads | État |
|---|---:|---|
| extensions-surelevations | 92 589 | complet |
| elagage | 90 469 | partiel (ombrage/canopée → ANC & Végétation) |
| pv-residentiel | 13 090 | partiel (score solaire, PV détecté) |
| parc-piscines-entretien | 10 164 | partiel (piscine détectée) |
| cuisinistes | 7 660 | complet |
| clotures-portails | 5 879 | complet |
| piscinistes-construction | 5 742 | partiel (piscine détectée) |
| pergolas-terrasses | 5 315 | complet |
| alarmes-telesurveillance | 4 327 | complet |
| paysagistes | 3 992 | complet |
| clim-pac | 154 | partiel (facture élec) |
| menuiseries-cyclonique | 125 | complet (boost CATNAT) |
| couvreurs-etancheite | 111 | complet (boost CATNAT) |
| termites-charpente | 103 | complet |
| chauffe-eau-solaire | 13 | partiel (score solaire) |
| salles-de-bain | 13 | complet |
| artisans-renovation | 12 | complet |
| anc-travaux | 11 | partiel (zonage ANC) |

**Critères d'acceptation** : 18 presets actifs (≥ 11 ✓) ; chaque preset > 0 ✓ ; les deux
plus gros = 32 % et 31 % du parc bâti (< 50 % ✓). Les presets « âge du bâti »
(couvreurs, termites, artisans, salles-de-bain…) sont bornés par la couverture DPE
actuelle (910 DPE) : les chiffres sont petits parce que la donnée l'est — ils grimperont
mécaniquement avec l'ingestion DPE complète, sans toucher au moteur.

## 3. Droits résiduels sur bâti (Lot 2) — volumétrie

Table dédiée `parcel_residuel_bati` (clé idu) — la `parcel_residuel` historique (SDP
promoteur, clé parcel_id, recalculée par les runs) n'est PAS touchée : sémantiques
différentes, aucun système parallèle côté vues (les filtres du moteur consomment la
nouvelle table).

| confiance | surélévation possible | résiduel ≥ 30 m² | total parcelles |
|---|---:|---:|---:|
| haute (YAML PLU calibré : Saint-Denis emprise chiffrée, Saint-Paul hauteurs strictes) | 20 147 | 8 894 | 30 480 |
| moyenne (pleine terre en borne, plancher prospect 10 m, estimation générique) | 140 903 | 19 820 | 206 611 |
| NULL (aucune règle exploitable : zones A/N, RNU Saint-Philippe, hors zonage) | 0 | 0 | 54 965 |

Détails de méthode :
- `emprise_max = surface × emprise_sol_pct` du zonage (règle directe → **haute**) ;
  quand l'Art. 9 « ne fixe pas de règle » (Saint-Paul) mais que la pleine terre (Art. 13)
  est chiffrée, borne = 100 − pleine_terre (→ **moyenne**) ; sinon NULL, jamais inventé.
- `surelevation_possible` = hauteur max zonage − hauteur bâtiment BD TOPO ≥ 2,8 m
  (hauteur BD TOPO présente sur 100 % des 817 506 bâtiments). Zones « prospect » (L≥H) :
  plancher règlement 10 m (→ moyenne).
- **Libellé impératif affiché partout** (builder + exports) : « potentiel indicatif
  estimé — les règles complètes du PLU (retraits, prospects, servitudes) peuvent le
  réduire ».
- Refresh : `labuse segments-residuel` (14 s à 5 min/commune, ~35 min l'île).

## 4. Confirmation termites (une phrase, sourcée)

L'île de La Réunion est **intégralement** classée zone d'infestation termites par
l'arrêté préfectoral du **11 avril 2001** (art. L.133-5 CCH — toutes les communes) :
le zonage n'est pas un filtre, le preset repose sur l'âge du bâti et son argumentaire
le dit. Sources : [DEAL Réunion](https://www.reunion.developpement-durable.gouv.fr/termites-et-autres-insectes-xylophages-a216.html),
[liste nationale des arrêtés](https://www.ecologie.gouv.fr/sites/default/files/documents/dgaln_dpts_termites_2016_0.pdf).

## 5. Statut CATNAT (Lot 3)

- **Constat d'inventaire** : la wave Géorisques existante ingère les zonages (PPR,
  aléas → spatial_layers) mais PAS les arrêtés CATNAT → ingestion dédiée via
  l'endpoint `/gaspar/catnat` du connecteur existant.
- **239 arrêtés** ingérés (24/24 communes) → `catnat_arretes`. Dates GASPAR en
  JJ/MM/AAAA (vérifié live, parseur adapté). `max(date_arrete) = 2025-07-08`, cohérent
  avec les derniers événements 974 (Garance : arrêtés « Vents Cycloniques » du
  20/03/2025 sur Saint-Denis, Bras-Panon, Saint-André, Saint-Benoît…).
- Signal `catnat_recent` : fenêtre 6 mois + périls (vent/cyclone/inondation) dans
  `config/segments.yaml`. **Aucune commune dans la fenêtre au 10/07/2026** (dernier
  arrêté : 08/07/2025) → bandeau éteint, comportement attendu. Le boost est du
  DONNÉES-DRIVEN : au prochain arrêté, bandeau + filtre pré-coché (décochable)
  apparaissent seuls sur couvreurs/menuiseries — il n'est PAS seedé en dur (le segment
  tomberait à zéro entre deux événements).
- Refresh mensuel : `deploy/cron.d/catnat` (le 5 à 05h00, + recalcul des compteurs).

## 6. Presets « partiels » et le mandat qui les complétera

| Preset | Filtres en attente | Mandat |
|---|---|---|
| pv-residentiel | score_solaire, pv_detecte | Habitat Solaire + Détection Ortho |
| chauffe-eau-solaire | score_solaire | Habitat Solaire |
| clim-pac | facture_elec_estimee_eur | Habitat Solaire |
| piscinistes-construction · parc-piscines-entretien | piscine | Détection Ortho |
| elagage | ombrage_vegetal, canopee_limite | ANC & Végétation |
| anc-travaux | zone_anc | ANC & Végétation |

**Règle de convergence tenue** : ces mandats implémenteront leurs vues comme presets de
ce moteur (leurs filtres sont déjà déclarés dans le registry, grisés) — un seul système
de vues quel que soit l'ordre d'exécution.

## 7. Tests & QA

- **pytest** : 9/9 verts (`tests/test_segments.py`) — intégrité du registry, contrat du
  seed, injection impossible (clé inconnue/valeur hors énum/tri libre → 422, valeurs
  toujours bindées), groupes OU, seed idempotent qui n'écrase jamais une édition admin,
  export RGPD sans colonne nominative, **résilience sur base sans
  parcel_solar/parcel_equipements** (critère du mandat).
- **Playwright** (`frontend/qa/qa_segments.mjs`) : 26 checks verts — page charge,
  3 presets testés dont un « partiel » filtrent et exportent non-vide (en-têtes
  français, zéro nominatif), filtres grisés « disponible prochainement », admin
  duplique un preset et le retrouve en galerie. Captures :
  `docs/design/captures/segments/`.
- Les 2 échecs de `tests/test_api_q_v2.py` préexistent sur main (TypeError de fixtures,
  sans rapport).

## 8. Notes d'exploitation

- RGPD : exports « à l'occupant » — adresse (source DPE quand connue), commune,
  caractéristiques du preset ; aucune donnée nominative, aucun filtre nominatif.
- Un preset modifié à la volée ne s'enregistre jamais ; « Enregistrer… » crée un
  NOUVEAU preset (admin Vic). CRUD complet sur la galerie (dupliquer / argumentaire /
  activer / supprimer — la suppression est réservée aux presets non-seed).
- Compteurs : cache 24 h (`segment_preset_counts`), bouton « Recalculer », CLI
  `labuse segments-counts`, et recalcul mensuel accroché au cron CATNAT.
- ⚠ Un serveur API antérieur à ce mandat tourne encore sur le port 8010 : il ne
  connaît pas /segments — le redémarrer pour voir la page (la validation a tourné sur
  :8011).
