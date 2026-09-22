# LA BUSE — Propriétaires « Niveau 2 » (design only)

> **Statut : NON IMPLÉMENTÉ — document de conception.**
> Rien de ce qui suit n'est branché. LA BUSE reste aujourd'hui en **Niveau 1** :
> prospection **100 % manuelle**, **aucune** donnée propriétaire nominative récupérée
> automatiquement, **aucun** scraping. Ce document prépare un éventuel Niveau 2 **si, et
> seulement si, un accès légal est obtenu et validé par un juriste**.

---

## 1. Rappel : où on en est (Niveau 1)

- `src/labuse/prospection.py` — saisie **manuelle** du statut propriétaire et du contact ;
  jamais de nom pré-rempli ; stocké dans `pipeline_entries.prospection` (jsonb), **effaçable**
  d'un bloc (droit à l'effacement).
- `src/labuse/api/enrichment.py::owner()` — lit les **Fichiers fonciers** *uniquement s'ils
  ont déjà été ingérés pour la parcelle* (cas rare) et n'affiche qu'une **catégorie** :
  `publique` / `morale_privee` / `personne_physique` — **jamais** un nom de personne physique
  (« Personne physique (non nominatif) »).
- En démo : **aucun** nom réel n'apparaît (garde-fou testé).

Le Niveau 2 = **enrichir** ce statut avec une source propriétaire autorisée (Fichiers Fonciers /
MAJIC / Datafoncier / DV3F), **sans jamais** transformer LA BUSE en fichier de personnes.

---

## 2. Conditions LÉGALES préalables (bloquantes)

Aucune ligne de code Niveau 2 ne doit être écrite avant que **tous** ces points soient validés
par un juriste / le DPO :

| Condition | Détail |
|---|---|
| **Accès autorisé** | Convention d'accès signée (Cerema pour les Fichiers Fonciers ; ou fournisseur Datafoncier). Les Fichiers Fonciers (MAJIC dérivé) **ne sont pas librement rediffusables**. |
| **Finalité déclarée** | Prospection foncière B2B pour un promoteur identifié — finalité **déterminée, explicite, légitime** (RGPD art. 5). Pas de réutilisation hors finalité. |
| **Base légale** | À qualifier : **intérêt légitime** (art. 6.1.f) avec balance des intérêts documentée, OU exécution contractuelle. À trancher avec le juriste. |
| **Minimisation** | Ne récupérer que ce qui est nécessaire : **catégorie** + **coordonnées strictement utiles**, pas l'historique patrimonial complet d'une personne. |
| **Information des personnes** | Obligation d'information (art. 14) quand on traite des données obtenues indirectement — modalités à définir (mentions, registre). |
| **Conservation limitée** | Durée de conservation bornée (ex. durée de la prospection active + purge), pas de stockage indéfini. |
| **Droits des personnes** | Accès, rectification, **effacement**, opposition — mécanisme opérationnel obligatoire (cf. §3). |
| **Registre des traitements** | Inscription au registre RGPD ; **AIPD/DPIA** probablement requise (traitement de données à grande échelle pouvant présenter un risque). |
| **Personnes physiques** | Traitement le plus sensible. Par défaut **masquées** ; dé-masquage seulement si la base légale et la finalité le permettent explicitement, et **jamais en démo**. |

> **Règle d'or produit** : LA BUSE *vérifie, priorise, explique et organise* la prospection.
> Elle n'est **pas** un annuaire de propriétaires. Le Niveau 2 enrichit un **statut**, il ne
> publie pas un fichier de personnes.

---

## 3. Architecture RECOMMANDÉE (à coder plus tard, derrière garde-fous)

### 3.1 Feature flag — OFF par défaut
- `LABUSE_OWNER_LEVEL2=0` par défaut (comme `LABUSE_ENRICH_LIVE`). Aucun chemin Niveau 2 actif
  sans activation explicite + présence d'une source autorisée configurée.
- Le flag conditionne : l'import, l'affichage dé-masqué, l'export des coordonnées.

### 3.2 Import SÉPARÉ et tracé
- Pipeline d'ingestion **distinct** (`ingestion/owners_level2.py`, non appelé par `run_all` /
  `rebuild-demo`), alimenté par un fichier sous convention — **jamais** par une API publique
  ni par scraping.
- Stockage dans une table dédiée (ex. `parcel_owner_secure`) **séparée** des couches publiques,
  avec `commune`, `parcel_id`, `categorie`, et les champs nominatifs **chiffrés au repos**.

### 3.3 Masquage par DÉFAUT
- Par défaut, l'API n'expose que la **catégorie** (`publique` / `morale` / `personne_physique`)
  et, pour les personnes **morales/publiques**, la raison sociale (donnée moins sensible).
- Les **personnes physiques** : nom **masqué** (`J. D***`) ou remplacé par « Personne physique
  (à contacter via voie légale) » tant que le dé-masquage n'est pas autorisé.
- Réutilise et étend la catégorisation existante de `enrichment.owner()` (publique/morale/PP).

### 3.4 Différenciation PP / morale / publique
- **Publique** (commune, État, EPF, EPCI, conservatoire…) : affichage de la collectivité OK
  (donnée publique de fait) — déjà détecté par heuristique dans `owner()`.
- **Morale privée** (SCI, société…) : raison sociale affichable, prudence sur les dirigeants.
- **Personne physique** : régime le plus strict → masquage par défaut.

### 3.5 Journal d'AUDIT (obligatoire)
- Table `owner_access_log` : qui (user), quoi (parcel_id), quand, finalité, dé-masquage oui/non.
- Toute lecture de donnée nominative dé-masquée est journalisée — traçabilité RGPD.

### 3.6 Suppression / rectification
- Endpoint/commande d'**effacement** par personne et par parcelle (droit à l'effacement),
  et de **rectification**. La donnée Niveau 2 doit être supprimable **sans** casser la
  prospection Niveau 1 (qui reste manuelle et autonome).
- Purge automatique à l'échéance de conservation.

### 3.7 Démo : barrière dure
- Le mode démo, `warm-demo`, `rebuild-demo` et le seed pipeline **n'activent jamais** le
  Niveau 2 et **n'affichent aucun nom de personne physique** (garde-fou déjà testé en Niveau 1,
  à reconduire par un test explicite « aucun nom PP en démo » au Niveau 2).

---

## 4. Ce qui NE doit PAS être fait

- ❌ Scraper des annuaires, réseaux sociaux, ou sites publics pour retrouver un propriétaire.
- ❌ Brancher Fichiers Fonciers / MAJIC / Datafoncier **sans** convention signée.
- ❌ Afficher un nom de personne physique en démo ou dans un export commercial.
- ❌ Présenter une donnée propriétaire comme « officielle » ou « vérifiée » : elle reste
  **à confirmer** (SPF / cadastre / mairie).
- ❌ Conserver les données au-delà de la finalité.

---

## 5. Risques à valider avec un juriste (checklist)

- [ ] Base légale retenue (intérêt légitime vs contrat) et **balance des intérêts** documentée.
- [ ] **AIPD/DPIA** nécessaire ? (probable) — la mener avant tout traitement.
- [ ] Modalités d'**information des personnes** (art. 14) réalistes et conformes.
- [ ] Durée de **conservation** et procédure de **purge**.
- [ ] Procédure d'exercice des **droits** (accès / rectification / effacement / opposition).
- [ ] Conditions de la **convention** Cerema/fournisseur (rediffusion, périmètre, finalité).
- [ ] **Sous-traitance** / hébergement : où sont stockées les données, chiffrement, accès.
- [ ] Mentions contractuelles côté **client promoteur** (responsabilité partagée).

---

## 6. Étapes d'implémentation suggérées (le jour venu)

1. Validation juridique complète (§2 + §5) — **bloquant**.
2. Table sécurisée + chiffrement au repos + feature flag OFF.
3. Import séparé sous convention (manuel, tracé).
4. Affichage **masqué par défaut** (catégorie seule) + journal d'audit.
5. Endpoints d'effacement / rectification + purge automatique.
6. Tests : « aucun nom PP en démo », masquage par défaut, audit log écrit, effacement effectif.
7. Revue DPO finale avant activation.

---

*LA BUSE — pré-analyse foncière sur données publiques. La propriété n'est jamais garantie ;
le Niveau 2, s'il voit le jour, enrichira un statut sous cadre légal strict, sans jamais
faire de LA BUSE un fichier de personnes.*
