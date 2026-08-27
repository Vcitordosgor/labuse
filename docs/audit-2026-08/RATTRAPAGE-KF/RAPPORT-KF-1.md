# RAPPORT — RATTRAPAGE KELFONCIER 1/2

Branche `feat/rattrapage-kf-1`. Régime autonome, commits par lot K1→K3. Aucune ingestion nouvelle de
donnée foncière — on expose ce qui est déjà en base. Doctrine : Sourcé/Estimé/Absent, zéro faux
positif, fraîcheur = date source amont, aucun chiffre inventé, un chiffre servi = un point de calcul unique.

---

## K1 — INVENTAIRE DES DONNÉES « PERSONNE MORALE » (écrit AVANT tout code)

Mesuré directement en base (`labuse`, 27/08/2026). Table pivot **`parcelle_personne_morale`**
(jointure par `idu`, **82 701 lignes, 1 PM par parcelle**).

### Couverture
- **82 066 parcelles** portent un lien PM sur **431 663** au total → **19,0 %**.
- Toutes les 24 communes ont des liens PM (aucune à zéro) ; la couverture varie fortement :
  Entre-Deux 567/6 312 (9 %), Saint-Philippe 613/4 162 (15 %) … Saint-Paul 12 410/51 129 (24 %),
  Saint-Denis 11 781/38 138 (31 %). Le patron « non couvert » (commune sans donnée) sera implémenté
  par principe mais ne se déclenche pour aucune commune aujourd'hui.

### Fraîcheur
- **millésime = 2025**, `source = "DGFiP — parcelles des personnes morales"` (100 % des lignes).
  Millésimes antérieurs disponibles dans `pm_proprietaires_millesimes` (461 570 lignes) — non exposés.

### Attributs — tableau récap
| Attribut | Colonne | Existe | Remplissage | Filtre | Note |
|---|---|:---:|:---:|:---:|---|
| Dénomination / raison sociale | `parcelle_personne_morale.denomination` | ✅ | 100 % | ✅ autocomplétion | valeurs réelles |
| SIREN | `.siren` | ✅ | 100 % | ✅ (un ou plusieurs) | 9 chiffres |
| Forme juridique | `.forme_juridique` | ✅ | 100 % | ✅ liste réelle | **45 valeurs** distinctes (codes DGFiP : COM, SCI, SEM, SA, SAS, SARL, GFA…) — libellés lisibles ajoutés en affichage, la LISTE vient d'un `DISTINCT` réel |
| Catégorie (groupe) | `.groupe_label` | ✅ | 100 % | ✅ liste réelle | 10 valeurs lisibles (Commune, Office HLM, État, SEM, Département, Copropriétaires…) |
| Nombre de dirigeants | `v_pm_propension_vendre.nb_dirigeants` (par SIREN, INPI RNE) | ✅ | 100 % de la vue ; **46,8 % des parcelles PM** ont des dirigeants connus | ✅ | 9 337 SIREN couverts |
| **Âge du dirigeant** | `v_pm_propension_vendre.age_max_dirigeant` (`pm_dirigeants.date_naissance` 73 %) | ✅ | 89 % de la vue | ⚠️ **derrière un drapeau désactivé** | **RGPD** — question ouverte avocat. Exposé mais **NON activé** (voir ci-dessous) |
| Code APE / activité | `owner_enrichment.payload->>'activite_principale'` (JSONB, jointure SIREN) | ✅ | **39,7 %** des parcelles PM (32 819) | ✅ liste réelle | codes NAF réels (68.20B location logts, 68.20A terrains, 41.10D promotion…) ; libellés d'affichage ajoutés, la LISTE vient d'un DISTINCT réel. Pas une colonne : jointure SIREN sur le cache d'enrichissement. |

Tables annexes : `pm_dirigeants` (27 146 ; siren, nom, prénoms, date_naissance, rôle, `diffusible`),
`pm_dirigeant_gigogne` (2 124), `v_pm_propension_vendre` (9 337 ; agrège nb + âge max par SIREN).

### Ce qui sera construit (K1)
1. **Propriétaire personne morale** : oui / non / indifférent.
2. **Dénomination** : autocomplétion sur les noms réellement en base.
3. **SIREN** : un ou plusieurs.
4. **Forme juridique** : liste alimentée par les valeurs distinctes réelles (libellés d'affichage).
5. **Code APE / activité** : liste des NAF réels (jointure SIREN, 39,7 % des PM couvertes).
6. **Nombre de dirigeants** (min/max) : sur les 46,8 % de PM aux dirigeants connus.

Chaque filtre affiche **le nombre de résultats** et **le millésime (2025)**. Un filtre sans donnée pour
une commune dira « non couvert » (pas un zéro silencieux). Les filtres à couverture partielle (APE 39,7 %,
dirigeants 46,8 %) le disent à l'écran — ils ne présentent pas l'absence comme un « non ».

### Ce qui NE sera PAS construit
- **SIRET** : absent. **Statut « nu »** : pas dans la table PM (croisé ailleurs, hors K1).
- **Âge du dirigeant** : le champ existe (`age_max_dirigeant`, RGPD sensible, date_naissance au mois) →
  exposé **derrière un drapeau de configuration désactivé par défaut** (`filtre_age_dirigeant`, défaut
  `false`) et **NON activé**. Question ouverte pour l'avocat — la donnée INPI porte un indicateur
  `diffusible` (84 % oui, 16 % non) : un filtre par âge devrait au minimum exclure les non-diffusibles.
  Rien n'est servi tant que Vic/l'avocat n'ouvrent pas le drapeau ; l'endpoint refuse la clé `age_*`
  quand le drapeau est fermé.
