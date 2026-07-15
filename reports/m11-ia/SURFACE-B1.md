# M11 · SURFACE B1 — Réparation de crédibilité de la recherche IA (`/ia/search`)

**Branche** : `feat/m11-surface-b1` (NON mergée — Vic merge). **Date** : 2026-07-15.
**Périmètre** : crédibilité de la **recherche simple** de la page IA (les 14 champs de `FILTER_SCHEMA`).
**Hors périmètre** (= B2) : aucune agrégation, aucun nouveau filtre de donnée (zonage, PM, DPE…), aucune
touche au scoring / cascade / étage 0 / run servi `q_v6_m8`. Le socle IA (`core.py`) n'est pas modifié.

**Boussole (Vic)** : `signaler > refuser > appliquer un filtre douteux`. Un faux résultat servi
(mistraduction) est pire qu'un critère signalé manquant, lui-même pire qu'un refus.

---

## Le problème (constaté à l'audit AUDIT-SURFACE-B)

Le schéma `FILTER_SCHEMA` garantit qu'un filtre a une **clé/valeur valide**, PAS qu'il correspond au
**SENS** de la requête. Deux trous de crédibilité en découlaient :

1. **MISTRADUCTION** — « les passoires thermiques classées G à Saint-Denis » → `flags:["risques"]`.
   Le DPE (énergie) n'a aucun rapport avec un risque naturel. Le schéma valide l'enum → **un filtre faux
   mais « validé par schéma »** servi comme vrai. *Le pire cas : le client obtient des parcelles à risque,
   croit avoir ses passoires.*
2. **DROP SILENCIEUX** — « brûlantes de Saint-Pierre, propriétaire personne morale » →
   `{commune, tiers}`, le critère PM **avalé sans un mot**. Le client lit « Filtres proposés » et **croit
   sa demande honorée**. Faux positif de confiance.

---

## La réparation

### Lot 1 + 2 — garde-fou SÉMANTIQUE (`src/labuse/api/nl_semantics.py`)

Fonction **pure et déterministe** `check_semantics(query, filters) -> (filtres_nettoyés, criteres_non_appliques)`,
appliquée **après** la validation de schéma, sur les 3 chemins de retour de `ia_search` (réel, repli stub
sur API dégradée, stub local sans clé). Aucun appel IA, aucune DB — testable en isolation.

Deux mécanismes orthogonaux :

- **A. Filtres catégoriels gatés par mot-clé** (anti-mistraduction) — chaque `flags`/`flagsExclus`
  (risques, sol_pollue, abf, icpe, prescription_plu) et chaque booléen catégoriel (`vueMer`, `evenement`,
  `veille`, `horsCopro`) n'est **gardé que si un mot de la requête le justifie**. `flags:[risques]` sur
  « passoire thermique » n'a aucun mot de risque → **retiré, jamais appliqué**. Un `vueMer:true` inventé
  par le modèle sur une requête sans « mer » → retiré. *Un filtre non demandé ou mistraduit ne s'applique
  jamais.*
- **B. Familles non supportées signalées** (anti-drop-silencieux) — les critères présents dans la requête
  que les 14 champs ne savent pas traiter (DPE, propriétaire personne morale/SCI, zonage, viabilisation,
  BODACC, âge/succession, piscine, jardin, pente, amiante, végétation, solaire) sont **listés** dans le
  nouveau champ de réponse `criteres_non_appliques: [...]`. *Jamais avalés.*

Ces deux mécanismes se combinent sur le cas dur : « passoire G » → le flag risques est **retiré** (A) ET
la famille « DPE / classe énergétique » est **signalée** (B). Le critère chiffré/nommé pur (`surfaceMin`,
`scoreMin`, `commune`, `tiers`) n'est jamais touché (aucun risque de contresens).

Ce n'est **pas** le tout-ou-rien de `/ia/segments-search` (qui refuse la requête entière) : on **applique
le supporté** ET **signale le reste**.

### Contrat de sortie — nouveau champ

`/ia/search` renvoie désormais `criteres_non_appliques: string[]` (liste vide si tout est supporté),
sur les réponses portant des `filters`. Le front (`iaSearch` dans `api.ts`) type ce champ.

### Lot 3 — bannière front

**Placement corrigé** : `apply()` (`useApplySearch`) fait `setView('cartes')` dès qu'un filtre s'applique
→ la vue IA (`IAStub`) se **démonte**. Une bannière dans `IAStub` ne s'afficherait donc jamais. Elle est
posée **là où l'utilisateur atterrit** : la **restitution** (carte flottante, `App.tsx`), à côté du
résultat servi — exactement comme le fait déjà le badge « mode mots-clés ». Le champ voyage :
`ia_search` → `apply(meta.criteres_non_appliques)` → `IaRestitution.criteres_non_appliques` → bannière
`data-ia-non-appliques` : *« ⚠ Certains critères n'ont pas pu être appliqués : X, Y. »*.
La bannière **coexiste avec les résultats valides** (ne les cache pas) ; absente si la liste est vide.

### Lot 4 — tests (`tests/test_nl_semantics.py`, 12/12 verts)

- **Mistraduction** : « passoire thermique G à Saint-Denis » → `flags` **absent** ; `{commune:Saint-Denis}` ;
  signale « DPE ». (+ variantes : flag risques *conservé* si vrai risque demandé ; flag partiel abf gardé /
  risques retiré.)
- **Drop silencieux** : PM signalée, `{commune, tiers}` appliqués ; SCI reconnue PM ; multi-critères tous listés, dédupliqués.
- **Non-régression / pas de faux positif** : requête 100 % supportée → filtres **inchangés**,
  `criteres_non_appliques == []` (pas de loup crié) ; vueMer justifié conservé / inventé retiré ; chiffrés intacts ;
  entrées vides/None sans plantage ; le dict entrant n'est jamais muté.

---

## Preuves en réel (instance dev, backend servant `dist/`)

Endpoint `/ia/search` (`curl` live) :

| Requête | `filters` servis | `criteres_non_appliques` |
|---|---|---|
| passoires thermiques G à Saint-Denis | `{commune: Saint-Denis}` — **pas de flags:[risques]** | `["DPE / classe énergétique"]` |
| brûlantes Saint-Pierre + propriétaire personne morale | `{commune: Saint-Pierre, tiers:[brulante]}` | `["propriétaire (personne morale)"]` |
| chaudes de Saint-Paul de plus de 800 m² | `{commune: Saint-Paul, tiers:[chaude], surfaceMin:800}` | `[]` (rien signalé) |

Captures front (`reports/m11-ia/captures/`, script `frontend/qa/m11_b1_captures.mjs`) :
- `b1-1-mistraduction-passoire.png` — bannière ⚠ « DPE / classe énergétique », résultats servis à côté.
- `b1-2-drop-personne-morale.png` — bannière ⚠ « propriétaire (personne morale) », tier+commune appliqués.
- `b1-3-non-regression.png` — **aucune** bannière, seulement le ✓ d'application.

---

## Garanties & limites

- **Zéro touche** scoring / cascade / étage 0 / run servi ; socle `core.py` inchangé (les appels modèle
  passent toujours par `core.complete`).
- **Aucun nouveau filtre de donnée** : B1 refuse proprement ce que B2 implémentera (zonage, PM…).
- **Détection par motifs** (regex sur la requête) : volontairement conservatrice — elle signale les
  familles connues non supportées et retire les flags non justifiés. Elle ne prétend pas couvrir toute
  formulation ; un critère non supporté inédit non capté retombe sur le comportement antérieur (drop),
  jamais sur une mistraduction (les flags restent gatés). Enrichir les motifs est un ajout localisé.
- Tests : `test_nl_semantics.py` 12/12. Suite IA : pas de régression introduite ; l'unique échec
  `test_ai_core::test_cache_roundtrip` est une indisponibilité DB `labuse_test` (rôle `labuse` absent),
  pré-existante et environnementale.
