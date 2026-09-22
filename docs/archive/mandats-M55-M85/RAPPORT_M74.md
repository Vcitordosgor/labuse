# RAPPORT M74 — Fermeture du dossier sources

Branche `feat/m74-catalogue` depuis `main` (`0bbc75a0`, M71 mergé — précondition « M60 mergé » lue
« M71 mergé », OK). **Un commit par bloc, A → E. NON MERGÉ.**

| Bloc | Commit | Contenu |
|------|--------|---------|
| A | `37931946` | requalifier les sources réellement branchées → bandeau 49 |
| B | `53aadbcf` | refresh des 3 écarts résiduels + périmètre sols pollués tranché |
| C | `784afd4e` | lever les 4 NON MESURÉ → tous MAXIMUM |
| C bis | `77a54cdc` | page Sources : audit + corrections |
| E | (BACKLOG) | registre à jour |
| F (accueil) | `8884a864` (M71) | déjà à 42 → recalculé 49 en A |

---

## BLOC A — Requalifier les 7 sources utilisées hors bandeau

Les 7 sources ont été mesurées (peuplées + lues) avant toute requalification. **6 sont
réellement branchées et passent connecte ; la 7e ne peut pas honnêtement le devenir — sa mesure
contredit la prémisse du mandat.**

| id | Source | Avant | Après | Mesure à l'appui | Nature |
|----|--------|-------|-------|------------------|--------|
| 9 | SAR Réunion (PEIGEO) | a_faire | **connecte** | couche cascade `sar` = 431 663 verdicts réels ; 2 453 emprises (spatial `sar`) | proxy (jeu Potentiel foncier) |
| 10 | Zonage SAFER (DAAF) | partiel | **connecte** | spatial `safer` 38 460 + scoring | proxy RPG |
| 13 | DEAL Réunion (WMS/WFS) | a_faire | **connecte** | spatial `anru` 8 + fiche ; catégorie hub→urbanisme | servi par proxys |
| 22 | OCS GE (IGN) | partiel | **connecte** | spatial `ocs_ge` + scoring ; couverture mesurée en C | proxy BDCARTO |
| 25 | ENS (Département) | partiel | **connecte** | spatial `ens` 73 + scoring | proxy INPN |
| 52 | Filosofi INSEE | partiel | **connecte** | 14 773 carreaux = amont exact + 3 features Z | — (direct) |

**Déviation mesurée (interdit « aucune requalification sans mesure ») — id 27 :**
- « Fichiers fonciers (Cerema) » **reste manuel**. Mesure : la couche cascade `proprietaire` qui la
  cite renvoie **100 % UNKNOWN** (`parcel_source_results` VIDE, convention non branchée), et sa note
  légale interdit le démarchage commercial. La requalifier en connecte serait un **faux positif**.
- La VRAIE source du propriétaire moral — **« DGFiP — parcelles des personnes morales »** (open data
  Licence Ouverte v2, 82 701 liens `parcelle_personne_morale`, lue par la fiche) — n'avait **aucune
  ligne au catalogue**. Elle est **AJOUTÉE** (connecte). C'est une source manquante surfacée par l'audit
  (cf. C bis), pas une requalification aveugle.

**Bandeau mesuré = 49** (42 + 6 requalifiées + DGFiP ajoutée ; Fichiers fonciers non compté).
Accueil = 49 (aligné, dynamique). Catalogue : 52 connecte (dont 3 doublons) + 5 a_faire + 2 partiel
+ 2 manuel + 2 hub = 63 lignes.

**Condition ferme respectée** : chaque source proxy porte sa note de nature (rendue visible en C bis).

---

## BLOC B — Refresh des trois écarts résiduels

| Source | Avant | Après | Cible | Résultat |
|--------|-------|-------|-------|----------|
| Géorisques — ICPE | 1 252 | **1 261** | 1 261 | ✅ atteint |
| Cartofriches | 372 | **372** | 373 | 1 friche non rattachée à une commune dans l'amont (l'ingestion par commune ne peut la placer) — documenté, pas forcé |
| Géorisques — sols pollués | 486 | **513** | ~548 | périmètre tranché (ci-dessous) |

**Périmètre sols pollués TRANCHÉ (code + note source)** : /ssp expose 4 sous-collections. LABUSE
ingère les **3 site-centrées** — `casias` (ex-BASIAS, inventaire) + `instructions` (ex-BASOL, gestion)
+ `conclusions_sis` (SIS, périmètres réglementaires L.125-6 CE) — et **EXCLUT `conclusions_sup`** :
une SUP n'est pas un descripteur de site mais une servitude, **déjà portée par la couche SUP (id 44)**
— l'ingérer ici serait un doublon de portée SUP. Répartition mesurée : casias 453 + instruction 56 +
sis 4 = 513. Le reliquat vs le comptage département (~543) = objets CASIAS **sans géométrie**,
non cartographiables, écartés à raison.

---

## BLOC C — Lever les NON MESURÉ mesurables : les 4 sont MAXIMUM

Requêtes comptables légères uniquement (WFS `resultType=hits`, ODS `total_count`, dump data.gouv).

| Source | base | amont mesuré | verdict |
|--------|------|--------------|---------|
| Potentiel foncier (Région) | 2 453 | 2 458 (ODS total_count) | **MAXIMUM** (99,8 %) |
| ABF / Monuments historiques | 200 tampons | 200 immeubles MH 974 (dump data.gouv) | **MAXIMUM** sur les MH |
| Forêts publiques (ONF) | 65 distinctes | 65 (WFS BDTOPO) | **MAXIMUM** |
| OCS GE (IGN) | 1 643 distinctes | 1 643 (WFS BDCARTO) | **MAXIMUM** vs proxy |

**Findings :**
- **« base > amont » était un DOUBLE-COMPTAGE par bbox commune** : foret_publique 227 lignes = **65
  géométries distinctes** (= amont WFS exactement) ; ocs_ge 3 250 lignes = **1 643 distinctes** (= amont
  exactement). Features à cheval sur 2 communes comptées 2×. → dette dedup au BACKLOG (touche le
  scoring, hors périmètre « mesure »).
- **ABF** : la couche compte des **tampons ~500 m** autour de ~200 MH, **pas** les périmètres ABF/SPR
  réglementaires (objet distinct non mesuré). Et **l'endpoint ODS data.culture.gouv.fr est
  décommissionné** (301, plus d'API) → re-sourcer via dump data.gouv avant toute ré-ingestion.
- **OCS GE** : le proxy BDCARTO n'est pas le plafond de l'OCS GE natif (non exposé en WFS) — MAXIMUM
  se lit « vs le proxy servi », la couverture OCS GE réelle reste non mesurable.
- Piège WFS Géoplateforme documenté : seul `SRSNAME=urn:ogc:def:crs:EPSG::4326` (ordre lat,lon)
  compte ; la forme courte `EPSG:4326` renvoie `numberMatched=0` (faux « 0/NON MESURÉ »).

DVF et Recherche d'entreprises restent NON MESURÉ à raison (téléchargement lourd / service unitaire).

---

## BLOC C bis — La page Sources confrontée à la mesure

### Anomalies trouvées (audit ligne à ligne)
1. **3 doublons encore listés** (Cadastre Etalab, RGE ALTI 5m, GPU typeinf) — badgés en M71 mais
   toujours affichés.
2. **Notes de nature INVISIBLES** : SAR/SAFER/OCS GE/ENS (proxy) et DEAL (servi par proxys) étaient
   présentés à l'écran comme des sources directes — exactement le risque « proxy présenté comme
   source officielle » que la doctrine interdit.
3. **Référence fantôme** : `LICENCE_PAR_SOURCE` gardait une entrée « Fichiers fonciers (Cerema) »,
   source qui n'est plus servie.
4. **Pastille « vérifiée auto »** : établie — elle vient de `source_radar` (table peuplée, 52 lignes,
   9 a_jour), **PAS** de `source_checks` (vide). Ce n'est donc **pas** un faux positif à l'écran. Le
   champ `verified_at` (issu de `source_checks`) est renvoyé par l'API mais **jamais affiché**.
5. Aucun libellé technique brut à l'écran (les typenames WFS restent dans les notes) ; aucune ligne
   fantôme parmi les 49 (toutes servent scoring/fiche/outil, vérifié en A).

### Corrections
- `/sources` ne sert plus les doublons (`served = connecte ET NOT « DOUBLON de »`) → 49 lignes.
- Champ `nature` (proxy / servi par proxys) extrait des notes → **chip ambre visible + ligne de détail
  NON REPLIÉE** sous chaque source proxy.
- Entrée fantôme Fichiers fonciers retirée de `LICENCE_PAR_SOURCE`.
- **Les 3 nombres du bandeau, recalculés et documentés** (infobulle sur chacun) :
  - **SOURCES BRANCHÉES = 49** — connecte hors doublons, mesuré.
  - **VÉRIFIÉES AUTO = 8** — radar (`source_radar`) confirme la dernière version amont ; faible car
    peu de producteurs (et aucun proxy/import) n'exposent une date interrogeable. Honnête, non
    adossé à `source_checks` vide.
  - **MILLÉSIME NON TRACÉ = 20** — sources sans date de version ; inhérent aux proxys sans amont daté,
    une limite dite, pas un défaut caché.

Vérifié Playwright (viewport 900×1100) : 49 lignes, 0 doublon, 5 chips nature, 5 détails proxy
visibles, 0 erreur console. Capture `/tmp/m74_sources_after.png`.

---

## BLOC D — Les deux gisements dormants (proposition, arbitrage Vic)

Rien branché. Statut `partiel — ingéré, non exploité` maintenu.

**PVGIS — `parcel_solar` (431 663 lignes, 100 % du parc).** Table riche : `score_solaire` (0-100),
`prod_spec_kwh_kwc`, `azimut_bati_deg`, flags (ABF/amiante/ombrage/ombrage_vegetal), `conso_est_kwh_an`,
`facture_est_eur_mois`, `proba_proprio_occupant`, `pv_existant`, `repowering`.
- **Usage naturel** : un bloc « Potentiel solaire » sur la fiche (comme le bloc piscine) — score +
  production estimée + facture mensuelle estimée, avec les flags de vigilance. Signal d'opportunité
  foncière (toiture exploitable) et argument commercial.
- **Coût estimé** : ~1 bloc backend (`app.py`, lecture `parcel_solar` par idu, motif SAVEPOINT comme
  piscine) + 1 carte front (`Fiche.tsx`) + type. ≈ une demi-journée. **Caveat** : ce jeu a été bâti
  pour le spin-off « Vues/Plein Sud » — vérifier avec Vic que le solaire est dans le périmètre du
  produit foncier avant de l'afficher.

**Parkings APER — `parkings_aper` (901 parkings ≥ 500 m²).** Colonnes : `surface_m2`, `proprio_pm`,
`proprio_siren`, `tranche`, `echeance`, `equipe` (déjà équipé ?), `exempt_probable`, `idus`.
- **Usage naturel** : un signal fiche « Parking soumis à l'obligation APER (ombrières PV) — échéance
  {echeance} » quand la parcelle porte/est un grand parking non encore équipé. Double lecture :
  contrainte pour le propriétaire, **opportunité** pour un développeur solaire.
- **Coût estimé** : ~1 signal fiche (jointure `parkings_aper` par idu) + 1 chip. ≈ 2-3 h. Plus
  clairement dans le périmètre foncier que PVGIS (c'est une contrainte réglementaire sur la parcelle).

---

## BLOC E — Le registre reflète le produit

`docs/BACKLOG.md` : section « M66→M74 » ajoutée — dettes CLOSES (bandeau 49, DPE hors scoring,
BODACC 12 605/12 605, terrain 100 %, 7 sources + DGFiP, refresh, 4 NON MESURÉ, page Sources), dettes
OUVERTES (tuilage Sainte-Rose, PVGIS/Parkings dormants, session PV en pause, doublons bbox
foret/ocs, ABF endpoint mort, **golden 33 FAIL à rebaser avant Train 8**), et la **règle acquise :
tout signal du scoring porte un test de non-constance** (garde M71-B3).

---

## Garde-fous (état final)

| Garde | Résultat |
|-------|----------|
| tsc --noEmit | **0 erreur** |
| vitest | **37/37** |
| npm run build | **vert** (743 ms) |
| pytest | sans régression nouvelle vs baseline M71 (mêmes échecs préexistants) |
| golden 118 | **33 FAIL = baseline M71, 0 régression** (refresh spatial_layers n'affecte que les futurs runs) |
| bandeau = accueil | **49 = 49**, dynamique, aucun chiffre en dur |
| page Sources | notes proxy visibles, 0 doublon, 0 ligne fantôme, 0 libellé technique brut |
| exports PDF | Saint-Philippe (proxy-heavy) **200**, Saint-Paul **200** |
| console navigateur | **0 erreur** |

## Interdits respectés
Aucune requalification sans mesure (id 27 laissé manuel pour cette raison même). Aucun chiffre en
dur. Aucune source proxy présentée comme officielle (notes de nature visibles).

## Pièges notés
- WFS Géoplateforme : `SRSNAME=urn:ogc:def:crs:EPSG::4326` obligatoire (forme courte → 0).
- `_source_nature` détecte la nature par préfixe de note (`PROXY` / `SERVI PAR PROXYS`) — les notes
  DB doivent commencer par ce marqueur (OCS GE réaligné : le prepend « MESURÉ MAXIMUM » l'avait masqué).
- CASIAS/friches : le comptage département inclut des objets sans géométrie que l'ingestion par
  commune écarte → « base < comptage département » est normal.

**NE PAS MERGER.**
