# Import du CSV de prospection dans Notion

Ce guide décrit comment importer **`exports/prospection_notion.csv`** dans la base Notion
**« Prospection LABUSE »** (data source `e17db1a3-96db-485f-a648-750d38a323c4`) **sans aucune retouche**.

Le fichier est produit par :

```bash
labuse prospection-notion            # 24 mois, enrichissement adresse activé
# ou : labuse prospection-notion --mois 36 --no-enrich   (options)
```

> Le CSV vit dans `exports/` (gitignoré) : les données nominatives (dirigeants) ne vont **jamais** en git.

---

## 0. Avant tout : supprimer l'ancien import désaligné

Le **premier import a désaligné les colonnes** (les noms du CSV ne correspondaient pas à ceux de la base).
Il faut donc **d'abord supprimer les lignes de cet ancien import** :

1. Ouvrir la base « Prospection LABUSE ».
2. Repérer les lignes de l'ancien import (colonnes brutes remplies : `n_pc`, `n_permis`, `dernier_depot`,
   `source`… au lieu des jolies colonnes). Les sélectionner toutes (Ctrl/Cmd-A dans une vue table).
3. **Supprimer** ces lignes. La structure (les propriétés/colonnes) reste, on ne supprime que les données.

> Les colonnes brutes désalignées (`n_pc`, `n_pa`, `n_permis`, `nb_logements`, `n_parcelles_detenues`,
> `dernier_depot`, `source`) peuvent être laissées dans la base ou masquées : le nouveau CSV ne les
> alimente plus (il écrit dans `Nb PC`, `Nb PA`, `Logements autorisés`, etc.).

---

## 1. Importer le nouveau CSV (Fusionner avec CSV)

1. En haut à droite de la base → menu `•••` → **Merge with CSV** (« Fusionner avec CSV »).
2. Choisir `exports/prospection_notion.csv`.
3. Notion associe automatiquement les colonnes **par nom** : comme les en-têtes du CSV sont **exactement**
   ceux de la base (casse + accents), la correspondance est **1-pour-1, sans intervention**.

### Correspondance colonne par colonne (déjà alignée)

| Colonne CSV            | Propriété Notion       | Type Notion | Remarque |
|------------------------|------------------------|-------------|----------|
| `Dénomination`         | Dénomination           | Titre       | Nom normalisé INSEE/INPI si trouvé, sinon nom SITADEL |
| `SIREN`                | SIREN                  | Texte       | 9 chiffres — sert de clé de dédup (1 SIREN = 1 ligne) |
| `Segment`              | Segment                | Select      | **Suggestion heuristique** (promoteur/lotisseur/cmi/bailleur/autre_pro) — à corriger à la main |
| `Nb PC`                | Nb PC                  | Nombre      | Permis de construire déposés (fenêtre) |
| `Nb PA`                | Nb PA                  | Nombre      | Permis d'aménager déposés (fenêtre) |
| `Logements autorisés`  | Logements autorisés    | Nombre      | Somme `nb_lgt` SITADEL (quand renseigné) |
| `Parcelles détenues`   | Parcelles détenues     | Nombre      | Foncier DGFiP |
| `Communes`             | Communes               | Texte       | Liste séparée par ` ; ` |
| `Dirigeants`           | Dirigeants             | Texte       | RNE **actifs + diffusibles uniquement** (non-diffusion respectée) |
| `Dernière autorisation`| Dernière autorisation  | Date        | ISO `YYYY-MM-DD` |
| `Entité publique`      | Entité publique        | Case à cocher | `true`/`false` — mairie/SEM/EPIC/collectivité |
| `Adresse siège`        | Adresse siège          | Texte       | Open data INSEE/INPI |
| `Ville siège`          | Ville siège            | Texte       | `CP + commune` du siège |
| `Site web`             | Site web               | URL         | **Vide** (voir § limites) |

4. Valider. Comme la fusion se fait sur des lignes neuves (l'ancien import a été supprimé à l'étape 0),
   il n'y a pas de doublon à craindre.

> **Astuce clé de fusion :** si Notion propose de fusionner sur une propriété unique, choisir **SIREN**.
> Ainsi, un ré-import ultérieur mettra à jour les lignes existantes au lieu d'en créer de nouvelles.

---

## 2. Après import : filtrer les vrais prospects

- Créer/utiliser une vue filtrée **`Entité publique` = décoché** → ne restent que les prospects commerciaux.
- Les entités publiques (mairies, SEM, SIDR, département, région, EPCI…) restent dans la base
  (on **marque, on n'exclut pas**) mais sortent de la vue de prospection d'un clic.
- La colonne **Segment** est une suggestion automatique : la corriger à la main au fil de la qualification.

---

## 3. Ce qui est enrichi — et ce qui ne l'est pas (assumé)

L'enrichissement passe par l'**API publique** `recherche-entreprises.api.gouv.fr` (données INSEE/INPI,
gratuite, sans clé). Elle fournit **honnêtement** :

- ✅ **Adresse du siège** et **ville (CP + commune)**
- ✅ Nom normalisé, nature juridique, flags officiels de service public (utilisés pour le tag « Entité publique »)

Elle **ne fournit pas** :

- ❌ **Téléphone** / ❌ **Email** : l'open data ne les expose quasiment jamais pour une personne morale.
  Les colonnes `Contact tél` / `Contact email` de la base **restent donc vides** — à compléter à la main
  (site web de la société, LinkedIn du dirigeant, annuaire pro).
- ❌ **Site web** : non exposé par cette API → colonne `Site web` vide.

**Pistes payantes (non utilisées ici, documentées pour information) :**

- **Pappers API** (`api.pappers.fr`) : coordonnées enrichies, dirigeants, comptes — payant à la requête.
- **Societeinfo** : enrichissement B2B (téléphone, email, site) — payant, sur abonnement.

Ces sources n'ont **pas** été appelées : ce mandat s'en tient à l'open data public et n'invente aucune
coordonnée. Un champ vide est un champ honnêtement vide.

---

## 4. Régénérer / mettre à jour le fichier

- La commande est **read-only** sur la base LABUSE et **idempotente** : l'enrichissement API est mis en
  cache (`exports/.prospection_enrichment_cache.json`) et **reprend là où il s'est arrêté** en cas de coupure.
- Pour forcer un ré-enrichissement complet : supprimer le fichier de cache puis relancer.
- Rythme d'appel throttlé (~6,5 req/s) pour respecter la limite de l'API publique.
