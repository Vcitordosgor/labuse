# PHASE 1.B — Prescriptions GPU (Q3) + zones A/N exclues (Q2) — livré · SAR (Q4) bloqué

> Suite des décisions de Vic sur le RAPPORT_PHASE1A_GPU.md (Compléter l'existant · A/N →
> HARD_EXCLUDE · prescriptions GPU en priorité · vrai SAR). Ce document rend compte de ce qui
> est **livré et mesuré**, et pose le **STOP & VALIDATE** sur le seul point bloqué : le vrai SAR.
>
> Commit code : `eda29dd`. Tests : **204 verts**, ruff clean, **démo 8/8 conforme**. Date : 2026-06-12.

---

## 1. Q3 — Prescriptions PLU/GPU intégrées à la cascade ✅

Jusqu'ici la cascade ne lisait que le **zonage** ; les **prescriptions** opposables du PLU étaient
ignorées. Elles sont désormais ingérées (live, API Carto GPU) et évaluées.

### Ingestion (`ingest_gpu_prescriptions`, `kind='plu_gpu_prescription'`)
`prescription-surf` + `-lin` + `-pct` → **117 prescriptions** sur Saint-Paul. Libellé GPU stocké
tel quel (jamais inventé) ; `source`, `url_source`, `millesime` (idurba) tracés ; loader
idempotent et isolé (savepoint). Distribution **réelle** des `typepsc` (a servi à calibrer, pas
d'invention) :

| typepsc | nature | n | parcelles touchées | traitement cascade |
|---|---|---|---|---|
| 48 | zonage eaux pluviales | 5 | **96 %** | PASS informatif |
| 17 | secteur de mixité sociale (« Clause logements aidés ») | 50 | **92 %** | PASS informatif |
| 18 | OAP (orientation d'aménagement) | 5 | 9 % | PASS informatif |
| 05 | emplacement réservé (ER) | 20 | 3 % | **SOFT_FLAG moyen/fort** (selon couverture) |
| 07 | élément bâti protégé (L151-19) | 36 | 2 % | **SOFT_FLAG moyen** |
| 01 | espace boisé classé (EBC) | 1 | <1 % | **SOFT_FLAG fort** |

### Décision de conception : discriminant vs blanket
Mesure clé : **eaux pluviales (96 %) et mixité sociale (92 %) couvrent quasi toute la commune**.
Les pénaliser reviendrait à décaler uniformément 92-96 % des parcelles et à encombrer chaque
fiche — du bruit, pas du signal. Donc :
- **Contraintes discriminantes** (spécifiques à la parcelle) → **SOFT_FLAG pénalisant** : ER
  (moyen ; **fort si ≥ 50 %** de la parcelle), EBC (fort), élément bâti protégé (moyen). Les
  fortes (ER majoritaire, EBC) **remontent en vigilance** dans le résumé, avec leur libellé exact.
- **Contraintes quasi-communales / de programme** → **PASS informatif** : mixité sociale, eaux
  pluviales, OAP. **Recensées et tracées** (visibles dans la fiche et les exports), **sans
  pénaliser le score ni polluer la vigilance**. L'impact économique de la mixité est porté par
  le **bilan**, pas par une pénalité de cascade.

Garde-fou hérité : un SOFT_FLAG **fort** plafonne le statut à « à creuser » (une parcelle avec
un ER majoritaire ou un EBC ne peut pas être « opportunité chaude »).

---

## 2. Q2 — Zones A (agricole) / N (naturelle) → HARD_EXCLUDE ✅

Aligné sur le brief 1.B **et** sur le règlement (`plu_saint_paul.yaml` : « zones non
constructibles : A, N »). U/AU testés **avant** A/N (car « AU » commence par « A »). Préfixes de
repli conservés (config) pour d'éventuelles sous-zones à carve-out (ex. un futur Nh constructible).
Verdict + motif lisible écrits dans `cascade_results` (« Exclue : zone PLU "A" (agricole — non
constructible au règlement) »).

---

## 3. Impact mesuré (ré-évaluation des 3 000 parcelles de Saint-Paul)

| Statut | Avant | Après | Δ |
|---|---:|---:|---:|
| opportunité | 108 | **88** | −20 |
| à creuser | 956 | **768** | −188 |
| faux positif probable | 1 770 | **1 978** | +208 |
| exclue | 166 | 166 | 0 |

**Mouvements :**
- **208** `à creuser → faux positif` : l'exclusion A/N (parcelles agricoles/naturelles non
  constructibles). Modéré et attendu (la plupart des A/N étaient déjà écartées par d'autres
  signaux ; 208 basculent nettement).
- **20** `opportunité → à creuser` : prescriptions discriminantes (ER/EBC/patrimoine) sur des
  parcelles jusque-là « opportunités » — désormais signalées avec le motif précis. Honnête : ce
  sont de vraies servitudes (ex. un emplacement réservé public sur la parcelle).

**Démo préservée — 8/8 conforme**, vitrine **BK0023 toujours « opportunité » (74)** (seulement
mixité/eaux en PASS informatif). BV0912 reste « opportunité » (67) avec son ER 81 honnêtement
signalé. Aucune parcelle de démo cassée.

---

## 4. Q4 — Vrai SAR (PEIGEO) : ⛔ bloqué par la DONNÉE, pas par le code — STOP & VALIDATE

Tu as choisi « ingérer le vrai SAR ». Or **le SAR réglementaire (Destination Générale des Sols)
n'est récupérable d'aucune source atteignable depuis cet environnement**. Sources sondées
(avec retries) :

| Source | Résultat |
|---|---|
| **PEIGEO** `geoserver/ows` (WFS) | **HTTP 503** sur 3 essais ; portail en timeout |
| **data.gouv.fr** API | **connection refused** (policy réseau de l'environnement) |
| **Region Réunion** ODS (catalogue complet) | **aucun dataset SAR** (seulement `potentiel-foncier` = le proxy déjà utilisé) |
| **Géoplateforme** WFS (GetCapabilities) | **aucune couche SAR** (seulement « ramsar », sans rapport) |

Le code actuel le documente déjà : `ingest_sar` note « DEAL/PEIGEO injoignables, rien sur la
Géoplateforme pour 974 » → d'où le **proxy de démo** (`espacesar` du potentiel foncier, sous-types
`vocation_*`). Le brief interdit explicitement de **bricoler une donnée de zonage** : je ne
fabrique donc pas un faux SAR.

### Ce qu'il te faut trancher (je ne fais rien sur le SAR avant ta réponse)

- **(a) Tu me fournis la donnée** — export du SAR (SHP / GeoJSON / GML depuis PEIGEO, AGORAH ou
  la DEAL) déposé dans le dépôt. **Le loader est prêt** (même schéma que les autres couches
  vecteur, ex. le trait de côte SHP→4326). C'est la voie qui satisfait vraiment « le vrai SAR ».
- **(b) Tu whitelistes PEIGEO** dans la policy réseau de l'environnement (peigeo.re répond 503
  ici — à confirmer s'il est joignable hors sandbox) → j'ingère via WFS automatiquement.
- **(c) Repli sûr en attendant** — rétrograder le **proxy actuel en informatif** (le SAR ne
  HARD_EXCLUDE plus jamais seul, uniquement un flag « à vérifier »). C'était l'option « Informatif
  seul » du choix Q4 ; c'est conforme à l'esprit du brief et **ne bricole rien**. Réversible dès
  que le vrai SAR arrive.

**Recommandation** : (c) **maintenant** comme filet (1 ligne de config, sans inventer de donnée),
puis (a) ou (b) pour le vrai SAR dès que la source est disponible. Si tu préfères, je laisse le
SAR strictement en l'état jusqu'à la donnée — **dis-moi.**

---

## 5. Reste (non commencé, gaté par ta validation)
- Q4 SAR selon ton choix ci-dessus.
- Libelle fin de zone (U6c vs U) dans la cascade — petit, optionnel (la faisabilité l'exploite déjà).
- Ingestion par mailles (vs bbox unique) — seulement si on craint une troncature API (non constatée).

**Je m'arrête sur le SAR. Q2 + Q3 sont livrés, testés, mesurés, démo intacte.**
