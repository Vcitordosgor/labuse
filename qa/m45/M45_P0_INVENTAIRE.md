# M45 — PHASE 0 · INVENTAIRE de l'existant + MAPPING du cadrage (STOP obligatoire)

**Branche** `m45-filtres-recherche`, base `main` `71b088b9` (post-merge M43). **LECTURE SEULE.**
Tout vérifié **sur pièces** (code + base `labuse`, run servi `q_v8_calibre`). Le cadrage
`docs/mandats/M45_FILTRES_CADRAGE_V1.md` fait foi. **Aucun tier / poids touché.**

> **STOP à la fin** : Vic valide (1) l'architecture proposée et (2) la liste des mensonges à
> corriger avant toute Phase 1.

---

## 1. Inventaire des filtres EXISTANTS (front + API) — claim vs réalité, TESTÉ

Moteur **centralisé** : tous les filtres passent par `_q_v2_where()` (fragment WHERE partagé)
→ `_q_v2_list()` / `_q_v2_stats()`, derrière `/parcels`, `/parcels/export.csv`, `/stats`,
`/parcels/search`, `/map/parcels.geojson`, `/shortlist`. **Bonne nouvelle** : le socle
« critères composables » demandé en P1 existe déjà — l'endpoint unifié l'étend, ne le refait pas.

Chips front actuels (`useApp.ts` `Filters`) : `tiers, scoreMin, surfaceMin/Max, sdpMin,
evenement, veille, horsCopro, flags, flagsExclus, communes, vSignals, personneMorale, zonagePlu`.
Le front envoie **toujours** `source=q_v8_calibre` via le builder `q()` (api.ts) — vérifié.

| Filtre servi | Ce qu'il prétend | Ce qu'il filtre RÉELLEMENT | Verdict (testé) |
|---|---|---|---|
| `tiers` | tier v2 effectif | `s2.tier` + étage 0 servi | ✅ honnête (`tiers=brulante` → 119 exactes) |
| `surface_min/max` | m² parcelle | `p.surface_m2` | ✅ honnête |
| `sdp_min` | SDP résiduelle | `parcel_residuel.sdp_residuelle_m2` | ✅ honnête (max absent) |
| `score_min` | qualité | `d.q_score` (run servi) | ✅ honnête |
| `flags`/`flags_exclus` | contrainte présente/absente | `dryrun_cascade_results` SOFT_FLAG (run servi) | ✅ honnête |
| `personne_morale`, `zonage`, `veille`, `hors_copro`, `evenement`, `communes` | présence/appartenance | tables dédiées (run servi) | ✅ honnête |
| **`v_signal` (Score V)** | signal propriétaire | `parcel_v_score.signals` | ⚠️ **VESTIGE** — Score V retiré (RR 0,51, M35). Cadrage : **ANTI-FILTRE, retirer du front+API**. |
| **`statuts`** | statut | **`d.matrice_statut` = classification v1 MORTE** (désaccord total avec le tier v2) | ❌ **source morte** (M37). Front ne l'envoie plus ; param dormant. |
| **`brulantes`** | brûlantes | alias `tier='brulante'` | ⚠️ alias déprécié dormant. |

## 2. Filtres lisant une SOURCE MORTE (point 2 — vérifié, non présumé)

- **La branche SANS `source` de `/parcels` et `/stats`** (repli legacy) : lit la table **MORTE
  `parcel_evaluations`** (opportunity/completeness) **et n'applique AUCUN filtre** (seul
  `commune`). Testé : `/parcels?tiers=brulante` (sans source) → renvoie des `ecartee` triées par
  idu ; `/stats?tiers=brulante` (sans source) → **total 431 663** (parc entier). ⚠️ **Non
  atteignable depuis le front** (q() injecte toujours `source`) → **piège dormant**, pas mensonge
  live. Cadrage règle 6 : **neutraliser** (exiger `source`, sinon 404).
- `statuts` → `matrice_statut` (cf. §1) : rail matrice **éteint M37**, param encore accepté.
- **`parcel_evaluations`** : 1 001 623 lignes, dernière écriture 2026-07-25 — table legacy encore
  peuplée par des pipelines annexes mais **hors chemin servi** ; ne doit plus alimenter aucun filtre.

**Conclusion point 2** : la promesse « zéro depuis M35/M37 » est tenue **côté front** (les
surfaces vivantes lisent le run v2). Restent **3 pièges dormants** côté API (branche sans-source,
`statuts`, `brulantes`) + le param `v_signal` à retirer — **corriger en P1 avant tout ajout**.

## 3. Mapping cadrage → REQUÊTABLE aujourd'hui vs À EXPOSER (point 3)

Légende : ✅ param existe · 🟡 donnée en base, pas de param (à exposer) · 🔴 donnée à sourcer/vérifier · 🚫 anti-filtre.

### Niveau 1 (barre, 7)
| Filtre cadrage | Backing (sur pièces) | Statut |
|---|---|---|
| Commune / secteur | `commune`/`communes` param ; **dessin polygone** → `parcels.geom_2975` (PostGIS) | ✅ + 🟡 (ST_Intersects à exposer) |
| **Constructibilité calibrée** | `parcel_p_score_v2.tier` (`declasse_non_constructible/zone_fermee/au_fermee/au_statut_inconnu`) + `parcel_constructibilite.label/motif/cause` (11,8k lignes) ; RNU = hors `parcel_zone_plu` | 🟡 **à exposer** comme axe dédié (mapper tiers+constructibilite→classes ; dériver RNU) |
| Surface min/max | `p.surface_m2` | ✅ |
| SDP résiduelle min/max | `parcel_residuel.sdp_residuelle_m2` | ✅ (min) + 🟡 (max) |
| État du sol (nu/marginal/saturé/révélé) | tiers `declasse_bati_sature/revele` + `parcel_bati_revele`/`parcel_filtre_bati` | 🟡 à dériver (« nu »/« marginal divisible » non typés) |
| Capacité logements ≥ N | `parcel_residuel.capacite_estimee` = **BOOLÉEN** (estimabilité, pas un N) ; N à dériver de `sdp_residuelle_m2` | 🟡 à dériver (étiquette **Estimé**) |
| Analyse LABUSE (interrupteur) | `tiers` + périmètre par défaut | ✅ (bascule = front) |

### Niveau 2 — « Puis-je construire ? »
| Zone PLU exacte → `parcel_zone_plu.zone_libelle` 🟡 | U/AU/A/N → `zonage` ✅ | Statut AU détaillé → tiers `declasse_au_*` ✅/🟡 (finesse opération/tiers à dériver) |
| Plancher densité (St-Leu/Trois-Bassins/Étang-Salé) 🔴 à localiser | EBC partiel 🔴 (pas de layer `ebc` vu) | Emplacement réservé 🔴 (à sourcer) |
| 50 pas → cascade `cinquante_pas` ✅(flags) | Parc national → cascade `parc_national` ✅(flags) | Sol naturel/ZAN → `sar`/`potentiel_foncier_region` 🔴 à vérifier |
| Fraîcheur PLU commune → `veille_plu` (M41) 🟡 à exposer | | |

### Niveau 2 — « Combien ça coûte / rapporte ? »
Charge foncière médiane → `dvf_secteur_medianes` 🟡 · Prix marché DVF + fiabilité n≥3 →
`v_parcel_dvf_last`/`dvf_secteur_medianes` 🟡 · Bilan CA → `score_e` 🟡 · Prix achat max ≤ budget →
`score_e.marge` (calculette M22-A) 🟡 · **Mode B rentable au paramètre** → `/parcels/{idu}/mode-b`
+ defisc M44 (curseur session) 🟡 · Sous-densité → `parcel_residuel.sous_densite` (bool) 🟡.

### Niveau 2 — « Ça va muter ? » (cœur)
Tier → `tiers` ✅ · Proba ×N → `parcel_p_score_v2.mult_base` 🟡 · Rang ≤ N → `.rang` 🟡 (têtes) ·
Entrée en tête récente (dette #9) → `.event_date` 🟡 · **Segment Renouvellement** →
`parcel_renouvellement` ⚠️ **vérifier rebuild N°3 train5 AVANT d'exposer** · Division en or O12 →
`division_or_candidates` 🟡 · Activité permis secteur → `sitadel_permits`/`via_permits_geo` (M38/M42) 🟡.

### Niveau 2 — « À qui c'est ? » (propriété)
Type propriétaire → `parcelle_personne_morale` (+`groupe_label` : **Office HLM 7 681 / SEM 4 128 =
bailleur**, Commune, État…) ✅(présence)+🟡(type fin) · **État société (M43)** →
`owner_enrichment`/`bodacc` (`_pm_etat_societe`) 🟡 · Assemblage même proprio ×N → cluster SIREN 🟡 ·
Acquérabilité → dérivé PM/SIREN 🟡 · Copropriété RNIC → `s2.copro` + `rnic_coproprietes` ✅(`hors_copro`)+🟡 ·
Dossier proprio dispo → tables projets 🟡 · **🚫 gérant âgé** = cascade `age_dirigeant` **JAMAIS un param** (RGPD).

### Niveau 2 — « Quels risques ? »
PPR/aléas/`risques` · bruit → `bruit_route` · SIS/pollution → `sol_pollue` · pente → `pente`+`rgealti_pente_5m` ·
accès voirie → `acces` (étiquette limite BD TOPO, dette #12) · **tous en cascade SOFT_FLAG/HARD_EXCLUDE →
✅ via `flags`** ; **niveaux/classes/tranches** 🟡 à exposer. Viabilisation → `parcel_viabilisation.band/c100_acheve`
🟡 · Assainissement/ANC → `.assainissement_zonage` 🟡 · Géométrie exploitable → `osm_faux_positif`/`emprise_lineaire` ✅.
**Vigilances par type** → `flags` ✅ **SAUF piscine (M39 NON basculée : aucun layer/table `piscine` servi)** →
🔴 ne PAS proposer « piscine » tant que M39 n'est pas basculé (sinon filtre qui ment).

### Niveau 2 — « Veille & niches »
**Motif de déclassement (multi)** → `entonnoir_motifs` + `parcel_constructibilite.motif` + cascade
`declassement` (`getEntonnoir` existe déjà) 🟡 · Veille AU → tiers `declasse_au_*` + `veille_plu` 🟡 ·
Potentiel solaire APER ≥1000 m² → `parkings_aper` 🟡 · Proximité NPNRU/QPV → **`anru_quartiers`** 🟡 (spatial) ·
Adresse dispo/absente (BAN) → tables `_ban` 🟡.

### Presets
**`segment_presets`** (slug, nom, `filtres` JSON, `colonnes_export`, `tri_defaut`, actif, ordre) +
`segment_preset_counts` **existent déjà** → les 6 presets s'y sèment (pas de nouvelle infra). Vues
utilisateur sauvegardées (nom+combinaison) → à stocker côté compte (table à ajouter).

## 4. Architecture proposée (point 3 — perf 431 663 parcelles, compteur live)

- **Un endpoint unifié** `/filtre` (critères composables) réutilisant `_q_v2_where` étendu ; le
  compteur = `/stats` (déjà **SQL exact + cache 30 s**). **Aucun filtrage client sur le GeoJSON.**
- Chemin liste déjà optimisé : `_q_v2_list` parcourt l'index `ix_p_v2_run_rang` (top-N ~2 ms, île
  <1 s). Le plafond **GeoJSON 2,2 s n'est PAS sur ce chemin** (compteur/liste = SQL agrégé).
- Nouveaux critères 🟡 : chacun = un `EXISTS`/jointure indexée (modèle M42), **index mesuré avant
  exposition** ; objectif P3 **compteur < 500 ms** sur les combinaisons de la barre niveau 1.
- Renommage « Réserve foncière » → « **Potentiel long terme** » : **libellé seul**, point unique,
  0 calcul touché ; grep verbatim + golden re-vérifié (régén au geste gardé si la référence porte le libellé).

## 5. Règle 5 — plancher « délaissé » : distribution SERVIE (constaté, non présumé)

Sur le run servi : **1 seule** parcelle < 40 m² porte une SDP résiduelle > 0 (**0** en tier actif).
Les bilans sont massivement sur ≥ 100 m² (141 567). **`AI1886` = `97404000AI1886` fait 488 m²**
aujourd'hui (SDP 135), **pas 9 m²** : l'anomalie « R+6 sur 9 m² » **n'est pas reproductible** dans le
run servi (note-vs-source : soit corrigée, soit portait sur l'emprise bâtie). → **Un plancher
d'affichage à 40 m² est sûr et quasi vide** (exclut ~1 parcelle) ; à re-confirmer à l'implémentation.

## 6. LISTE DES MENSONGES/PIÈGES à corriger en P1 (avant tout ajout)

1. **`v_signal` (Score V)** — retirer le param du **front ET de l'API** (`_q_v2_where`, `/parcels`,
   `/stats`, `filterParams`, `Filters.vSignals`). Anti-filtre acté (cadrage).
2. **Branche `/parcels` & `/stats` sans `source`** — neutraliser : exiger `source` (→ 404/400 sinon),
   ne plus jamais lire `parcel_evaluations`.
3. **`statuts`** (matrice morte) — retirer le param (rail M37 éteint).
4. **`brulantes`** (alias déprécié) — retirer, `tiers=brulante` suffit.
5. **Garde `age_dirigeant`** — verrou explicite : jamais exposé en critère de requête (RGPD), test de non-régression.
6. **Piscine (M39)** — ne pas offrir le type de vigilance tant que non basculé (sinon filtre vide qui ment).

## 7. Ce qui est SAIN et réutilisable (ne pas casser)
Moteur `_q_v2_where`/`_q_v2_list`/`_q_v2_stats` (SQL exact, index rang), `getStats`/`getResults`
(source injecté), `segment_presets` (infra presets), `getEntonnoir` (motifs), tables déjà en base
pour ~85 % des filtres cadrage. **La majorité du cadrage est REQUÊTABLE** — l'essentiel de M45 est
d'EXPOSER (params + UI) et de NEUTRALISER les vestiges, pas de sourcer de la donnée neuve.

---

## Annexes
- `qa/m45/filtres_inventaire_p0.csv[.gz]` — inventaire machine (filtre cadrage, backing, statut).
- Aucune écriture servie. Golden / re-mesures / SHA256 M37 intacts (P0 = lecture seule).

**STOP.** Vic valide l'architecture (§4) et la liste des mensonges à corriger (§6) avant la Phase 1.
