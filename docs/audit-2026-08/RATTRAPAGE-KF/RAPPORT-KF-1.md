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

### Livré (K1)
- Backend : `FiltreCriteres` + `_q_v2_where` étendus (`pm_denom`, `pm_siren`, `pm_forme`, `pm_ape`,
  `pm_dirig_min/max`) ; endpoints `GET /proprietaires/facettes` (formes + APE réels avec comptes,
  couverture, millésime, état du drapeau âge) et `GET /proprietaires/autocomplete` (noms réels).
  Config `filtre_age_dirigeant=false`. Un filtre PM ⊆ PM (jamais un zéro muet).
- Front : section repliable « Propriétaire » dans le panneau de recherche (oui/indifférent — le back
  n'exprime que `personne_morale=true`, « non » non exprimable proprement, noté ; dénomination avec
  autocomplétion, SIREN, forme juridique, code APE, nb dirigeants), listes alimentées par les facettes
  réelles, millésime affiché, « non couvert » si couverture nulle, mauve absent.
- Tests : `tests/test_filtres_proprietaire.py` (facettes réelles, autocomplétion, WHERE, non-couvert, drapeau fermé).

---

## K2 — CONTACTS DES 24 MAIRIES DANS LA FICHE COMMUNE

Source : **Annuaire de l'administration** (service-public.fr, données ouvertes). Les 24 INSEE sont lus
en base (`commune_insee_logement`), jamais devinés. `ingestion/mairies.py` + CLI **`labuse ingest-mairies`**
créent la table `mairies` (INSEE PK) et upsertent adresse, code postal, téléphone, e-mail, site officiel,
lien annuaire, avec la **date de relevé**. Un champ absent reste NULL → affiché « Absent » (jamais inventé).

**Exécuté** : 24/24 communes. Remplissage réel : adresse 24, code postal 24, téléphone 24, site 24,
lien annuaire 24, **e-mail 23/24** (une commune sans e-mail dans l'annuaire → « Absent »).

Affichage : `/communes/{c}/contexte` sert un bloc `mairie` ; `ContextePanel` l'affiche (adresse, tél
cliquable, e-mail, site, fiche annuaire) avec la fraîcheur (« Annuaire de l'administration · relevé le … »).
Rafraîchissement déclaré dans `EXPLOITATION-CRON.md` (à la main, non automatisé — les coordonnées changent
rarement). Tests : `tests/test_mairies.py` (parsing annuaire, `mairie_de`, ABSENT, affichage contexte).

---

## K3 — CALCULETTE DE TAXE D'AMÉNAGEMENT (nouvel outil)

Formule publique (code de l'urbanisme). Valeurs forfaitaires de l'**année en cours (2026)** dans une
config **datée et SOURCÉE** `config/taxe_amenagement.yaml` (source service-public.gouv.fr, relevé le
27/08/2026) : valeur au m² **hors Île-de-France 892 €** (La Réunion), piscine 251 €/m², PV au sol 10 €/m²,
éolienne 3 000 €/mât, stationnement extérieur 2 928 €/place (jusqu'à 5 857 sur délibération) ; abattement
**50 %** sur les 100 premiers m² d'une résidence principale et sur les logements aidés.

**Taux — aucun taux inventé** :
- **Part communale** : issue des délibérations, ni en base ni devinable → **saisie obligatoire**. Sans
  elle, `total_eur=null` et l'outil dit « Taux communal non renseigné pour cette commune » (il ne calcule
  jamais avec un défaut silencieux).
- **Part départementale** : plafond légal **2,5 %** servi par défaut, **étiqueté « à confirmer »**
  (`part_departementale_confirmee_974=false`) — le taux exact 974 n'a pas été trouvé dans une source
  officielle (il vient d'une délibération du conseil départemental) ; on sert le plafond documenté,
  modifiable, jamais présenté comme confirmé.

`src/labuse/taxe_amenagement.py` : calcul pur, **détail LIGNE PAR LIGNE** (surface, forfaits, assiette,
part communale, part départementale, total). Endpoints `GET /outils/taxe-amenagement` (calcul),
`…/config` (valeurs datées) et `…/prefill?idu=` (zone PLU + surface du TERRAIN en référence — la surface
TAXABLE reste saisie, jamais devinée). Outil dans le menu Outils (aplati, DA LABUSE, mauve absent).
Mention à l'écran : estimation indicative, montant officiel notifié après dépôt du permis (clause boussole).
Tests : `tests/test_taxe_amenagement.py` (config sourcée, abattement, détail, forfaits, sans-taux-communal, départemental non confirmé).

---

## FINDINGS
- **KF-001** (K1) — Âge du dirigeant : donnée présente (`age_max_dirigeant`, INPI RNE) mais RGPD sensible
  → drapeau `filtre_age_dirigeant` FERMÉ par défaut, NON activé. Question ouverte avocat (diffusibilité).
- **KF-002** (K1) — Filtre « propriétaire PM » restreint à oui/indifférent : le back n'exprime que la
  présence d'une PM ; « non » (exclusion) non exprimé proprement. À compléter si Vic veut le « non ».
- **KF-003** (K1) — APE (39,7 %) et nb dirigeants (46,8 %) ont une couverture PARTIELLE (jointure SIREN) :
  l'UI le dit ; l'absence n'est jamais présentée comme un « non ».
- **KF-004** (K2) — 1 commune sans e-mail dans l'annuaire (affiché « Absent »).
- **KF-005** (K3) — Taux départemental 974 non confirmé par source officielle : plafond légal 2,5 % servi
  et étiqueté « à confirmer ». Taux communaux non ingérés → saisie utilisateur (jamais de défaut).
