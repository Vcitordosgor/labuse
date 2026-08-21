# Audit — Promesses mortes (M04) + correction (21/08/2026)

Branche `audit/promesses-mortes`. Audit d'abord, puis correction. Ne merge pas.

## 1. Audit (mesuré)

### a. Branché de bout en bout ? Sert-il quelque chose ?
- Tables : **`sitadel_permits`** (`modules.py:416`), **`parcels`** (`:418`), **`dryrun_parcel_evaluations`**
  (`:419`, run-scopé `q_v10_m129`), **`dryrun_cascade_results`** (`:424`, garde « bâti HARD_EXCLUDE »),
  **`parcel_p_score_v2`** (`:431`, tier v2). Le COUNT est DÉCOUPLÉ (`count_only`, ~4 s) du chemin des lignes.
- **Sert bien** (pas vide) : **17 123** promesses à 24 mois (défaut), 15 415 à 36 m, 13 758 à 48 m, 11 895 à 60 m.

### b. Que fait-il exactement ? (définition d'un permis « mort »)
Un « mort » selon le code (`modules.py:420-426`) = **PC** (`type='PC'`) dont **`date < now() − months`**
(seuil temporel, défaut **24 mois**, sélecteur 24/36/48/60) **ET** sans DAACT (`raw->>'daact' IS NULL` =
aucune déclaration d'achèvement) **ET** parcelle **toujours non bâtie** au run (pas de couche `bati` en
HARD_EXCLUDE). L'écran DIT exactement cela (« PC accordé, aucune déclaration d'achèvement, parcelle
toujours non bâtie… réalisation à vérifier »). **Écran ≡ calcul.**

⚠️ **Nuance nom vs calcul** : un PC est **caduc légalement à 3 ans (36 mois)**. Le **défaut de l'outil est
24 mois** → il liste des permis pas encore caducs. « Mort » est plus fort que le calcul (= **au point mort**,
pas juridiquement caduc). Le bandeau se rattrape honnêtement (« réalisation à vérifier sur place », codes
d'état bruts non documentés). **→ FAIT (ajout avant merge)** : défaut passé à **36 mois** (caducité PC ;
sélecteur inchangé 24/36/48/60). Compte : **17 123 à 24 m → 15 415 à 36 m**.

### c. Un LIMIT caché ? → NON (le seul des 5 outils SANS plafond muet)
La liste pagine (`limit` défaut 1000, plafond 2000/page, « voir plus » par offset) ; le **total est SERVI**
(appel `count_only`) et **affiché** (« N promesses · M affichées »). La carte suit les IDU chargés. Aucun
plafond silencieux — le seul des cinq outils audités cette semaine à être honnête ici.

### d. Vestiges de matrice → OUI, `q_score` (CORRIGÉ)
`d.q_score` (matrice MORTE depuis M129-B) était **sélectionné** (`modules.py:414`), **re-sélectionné**
(`:429`) et **renvoyé** dans les items (`:439`) — mais **aucun consommateur ne le lit** (grep front = 0,
aucun test). Vestige pur. **RETIRÉ** des trois emplacements (`d` reste utilisé pour `status`).

### e. Lien vers la parcelle et vers le radar permis
- **Vers la parcelle : OUI.** Un clic sur une ligne (`Row`) fait `select(idu)` → ouvre la fiche parcelle,
  + attache une mini-fiche permis (3 lignes : Permis / État source / Lecture) via `setModuleFiche`.
- **Vers le drawer permis : NON** (avant cette correction). M04 montrait sa PROPRE mini-fiche (3 lignes),
  pas le `PermitDrawer` riche du radar permis. Le même permis n'était donc PAS présentable via le drawer.
  → La correction apporte le drawer (chemin unique) pour la recherche par numéro ; les lignes gardent leur
  lien vers la PARCELLE (comportement utile conservé).

## 2. La correction — recherche directe par numéro de permis
Champ de saisie d'un numéro de permis en tête de l'outil → **son état dans le `PermitDrawer`** — le MÊME
drawer que le radar permis (chemin unique, aucune 2ᵉ fiche permis). Trouvé (`/modules/permis/{id}` = 200) →
drawer détaillé (nature, statut, porteur, lots, surface, dates, délai, parcelle, « Voir la parcelle »).
**Introuvable (404)** → le drawer gagne une **branche d'erreur claire** (« Permis introuvable — aucun permis
X dans SITADEL… ») au lieu d'un tiroir vide.

## Ajouts avant merge
1. **Défaut 36 mois** (caducité légale du PC) : l'écran ouvre sur ce que la loi dit. Sélecteur inchangé.
2. **Renommage** « Promesses mortes » → **« Permis au point mort »** — le nom promettait la caducité, le
   calcul dit « au point mort » (accordé, sans achèvement, parcelle non bâtie ; « à vérifier »). La CLÉ reste
   `promesses` (URL/QA/concept-route inchangés) ; les anciens mots-clés Copilote sont conservés + le nouveau
   nom ajouté. Renommé partout : menu (registry), en-tête, compteur, concept-route.

## Vérif
Captures (`qa/audit-promesses/`) : recherche numéro → permis TROUVÉ (drawer détaillé) ; numéro bidon →
INTROUVABLE (message clair) ; **renommage + défaut 36 mois (compte 15 415)**. q_score retiré de
`/modules/promesses` · Copilote guidage 26/26 · golden 119/119 · garde-run 431 663=431 663 · tsc 0 · build.
