# RAPPORT — Lots A + B livrés · ⛔ STOP & VALIDATE (avant Lot C)

> Réponse à la DIRECTIVE de re-priorisation. Étape DONE §7 désormais **testable de bout en
> bout**. Commits : `c3e2885` (§1-§2), `aaf08df` (Lot A), `a1d300e` (Lot B).
> **231 tests verts** (+12), ruff clean, **démo 8/8**, baseline 3 000 parcelles intacte. 2026-06-12.

---

## §1 — `pct_lls` : valeur sourcée proposée (⛔ à valider avant activation)

**Proposition : `pct_lls = 30 %`.** Source : **Règlement PLU Saint-Paul, Article 2
« Occupations et utilisations du sol soumises à des conditions particulières », clause de
logement aidé** (Titre 2 Livret 1, p. imprimée 11 — zones U1a/U1b/U1c/U1d/U1f/U1g/U1pru/U1pso ;
valeur **identique 30 % dans tous les bassins**, vérifié sur les 6 livrets).

Déclencheurs (le quota s'applique au-dessus de seuils) : programme SDP ≥ 1 800 m² → 30 % de la
programmation logement en LLTS/LLS/PLS ; OU ≥ 20 logements (SDP < 1 800) ; OU SDP ∈ [1 500 ;
1 800[ ; OU terrain d'habitation > 6 000 m² → 30 % en logements aidés ou accession sociale.
La plupart des programmes collectifs estimés franchissent ce seuil. **Reste PLACEHOLDER (0)
dans le YAML** — `pct_lls: 30` à poser après ton feu vert. `prix_m2_lls` et
`majoration_vrd_pluvial` restent PLACEHOLDER (calibrage bailleurs/promoteurs).

## §2 — Revue carte → `ANNEXE_REVUE_AN_ER.md`

Livrée : 10 réadmises (leads), 17 mixtes, 10 ER-HARD, avec idu/section/zones+%/opportunité/lien
carte. Cas limite signalé : **BV1521 à 90 % pile** (au seuil `an_hard_exclude_pct`).

## §3 — SAR : clôturé

Repli informatif = **état final** (livré en D2, plus aucun pouvoir d'exclusion). **PEIGEO reste
injoignable depuis cet environnement** (timeout sur `peigeo.re/geoserver`, re-testé aujourd'hui) :
le whitelisting que tu as acté n'est pas encore effectif ici. Aucun chantier « vrai SAR » ; le
remplacement opportuniste de la donnée proxy attendra que PEIGEO réponde (effort plafonné).

---

## LOT A — Audit pull ✅ (priorité absolue, première ligne du DONE §7)

Le connecteur cadastre API Carto IGN (live, **HTTP 200 vérifié**) est câblé sur **LE pipeline
existant** : une parcelle auditée entre au référentiel avec `origine='audit'` et est évaluée
par la **même** cascade que la découverte (aucune logique dupliquée).

| Chemin | Mécanique | Perf mesurée |
|---|---|---|
| **Référence cadastrale** | cache section+numéro (sans réseau) sinon fetch API Carto → ingest → cascade | **COLD 3,1 s · WARM 0,0 s** |
| **Adresse** | géocodage **BAN** (HTTP 200, 2 tentatives) → point → parcelle | **1,4 s** |
| **Polygone dessiné** | Leaflet natif (clic/double-clic) → `fetch_by_geom` → parcelles (≤ 25) | **3,6 s** (20 parcelles) |

- **Garde-fou commune** AVANT tout réseau quand l'INSEE est connu → hors Saint-Paul : message
  propre (« non couverte — phase pilote sur Saint-Paul »), **jamais de crash ni d'évaluation
  trompeuse**. Testé par référence (97411) et par adresse (Saint-Denis).
- **UI** : champ « 🔎 Auditer un terrain » dans l'en-tête (auto-détecte réf vs adresse) +
  bouton « ✏ Dessiner sur la carte » + **bandeau « audit à la demande »** sur la fiche.
- **Recette (3 chemins, 3 cas)** : BV0122 **hors référentiel** (cold 3,1 s → ingérée
  `origine='audit'`, cascade complète) ; BV0912 **déjà au référentiel** (warm 0,0 s, cache) ;
  Saint-Denis **hors commune** (message propre). ✅
- **Bug attrapé en cours** : l'upsert marquait à tort le référentiel `'audit'` quand un polygone
  le recoupait (`COALESCE` sur un NULL) → corrigé (l'upsert ne touche plus `origine`), référentiel
  restauré à 3 000.

## LOT B — Potentiel résiduel ✅

Croise le **bâti existant** (BD TOPO) et la **capacité max** (faisabilité), qui existaient
séparément :
- **`taux_emprise` = emprise bâtie / emprise constructible max — RÉEL** (aucune hypothèse de
  hauteur) → base du filtre « sous-densité ».
- **`SDP résiduelle` = SDP max − SDP existante**. SDP existante = emprise bâtie × niveaux ;
  niveaux = `nombre_d_etages`/`hauteur` BD TOPO **quand ingérés**, sinon PLACEHOLDER
  `niveaux_bati_existant_defaut` (prudent) → SDP **estimée, signalée comme telle**. La capture
  de la hauteur est ajoutée à l'ingestion (la SDP devient réelle à la prochaine ré-ingestion).
- **Fiche** : bloc « Potentiel résiduel » (taux d'emprise, % bâti du potentiel, SDP résiduelle).
- **Filtre liste « sous-densité < X % »** (slider, défaut 40 % PLACEHOLDER), alimenté par le
  cache `parcel_residuel` (CLI `compute-residuel` : **2 342 parcelles constructibles, 601 en
  sous-densité**, taux médian 70 %).
- **Recette (nue / dense / mid)** : BN0266 nue (taux 2 %, résiduel ~997 m² ≈ SDP max, sous-densité) ;
  BI0056 dense (taux 80 %, pas sous-densité) ; BI0055 mid (taux 40 %). ✅

---

## ⛔ Démonstration de bout en bout — parcelle **jamais vue** (DONE §7 testable intégralement)

**BV1232**, absente du référentiel, auditée **par référence cadastrale** :

1. **Audit pull** : absente → fetch live + ingestion `origine='audit'` + cascade en **0,41 s**.
2. **Verdicts** : zone U (POSITIVE), accès voirie, surface 1 385 m², marché DVF 548 €/m² ; mais
   garde-fou **« ensemble bâti : 4 bâtiments, 25 % » → HARD_EXCLUDE**.
3. **Capacité** : zone U1f, **R+2, ~12-13 logts**, SDP max 1 252 m², emprise constructible 928 m².
4. **Résiduel** : **bâtie à ~37 % de l'emprise · SDP résiduelle ~905 m² · sous-densité=True**.
5. **Bilan** : CA ~2,2–3,4 M€, charge foncière médiane affichée.
6. **Complétude** : **84/100**, statut final **FAUX POSITIF PROBABLE**.

L'histoire que ça raconte : une parcelle « déjà bâtie » (donc écartée d'un jeu greenfield) que
le **potentiel résiduel révèle comme lead de densification** (905 m² de SDP mobilisables) — Lot A
+ Lot B + le garde-fou faux positifs, sur une parcelle hors référentiel, en moins d'une seconde.

---

## État DONE §7 après A + B

| Item | Avant | Après A+B |
|---|---|---|
| **Audit pull** (réf / adresse / polygone, hors référentiel) | ❌ connecteur non câblé | ✅ **3 chemins live, < 30 s froid / < 5 s cache** |
| **Potentiel résiduel** (taux d'utilisation, SDP résiduelle) | ❌ croisement absent | ✅ **fiche + filtre sous-densité** |
| Export / comparateur / filtres sauvegardés (Lot D) | partiel | inchangé (après Lot C) |
| Couches Phase 3 (Lot C) | partiel | inchangé — **STOP** |

## Disponibilité réseau pour le Lot C (constat, sans engager de loader)

| Source | État aujourd'hui | Lot |
|---|---|---|
| Géoplateforme WFS (`data.geopf.fr`) | ✅ HTTP 200 | C1 ravines (BD TOPO hydro), C4 SITADEL à vérifier |
| API Carto IGN (`apicarto.ign.fr`) | ✅ HTTP 200 | (déjà utilisé — audit pull) |
| BAN (`api-adresse`) | ✅ HTTP 200 | (déjà utilisé — audit pull) |
| **PEIGEO** (`peigeo.re`) | ❌ timeout | **C2 50 pas — bloqué** tant que non whitelisté |

---

## ⛔ STOP & VALIDATE

Lots A + B livrés, testés, recettés ; démo bout-en-bout OK ; DONE §7 testable intégralement.
**Je n'entame pas le Lot C.** En attente de :
1. ton **feu vert sur `pct_lls = 30 %`** (sourcé ci-dessus) pour activation ;
2. ta **revue de l'annexe carte** (seuils A/N + ER) ;
3. la **confirmation Lot C** (ordre C1→C5) — je produirai le **rapport de disponibilité par
   couche AVANT tout loader**, en commençant par celles dont la source répond (C1 ravines).
