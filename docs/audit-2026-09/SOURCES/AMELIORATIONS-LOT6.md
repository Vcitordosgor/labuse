# SOURCES-3b lot 6 — les cinq améliorations, dans l'ordre

## 1. Consommation NAF → trajectoire ZAN (fiche commune, à côté d'OCS GE) — **FAIT**
`_zan_indicateur` (api/moteurs.py) servait déjà le budget ZAN −50 % (consommé 2011-2021 / 2021-2024,
budget 2021-2031, reste, % consommé, dépassé) + le bloc OCS GE à côté. **Ajouté : la TRAJECTOIRE
annualisée** — `rythme_2011_2021_ha_an` (référence, 10 ans), `rythme_2021_2024_ha_an` (récent, 3 ans),
`rythme_cible_ha_an` (budget −50 % lissé sur 2021-2031), et le verdict `trajectoire` (« sous la
cible » / « au-dessus de la cible » : le rythme récent tient-il l'enveloppe 2031 ?). Estimé (même
caveat −50 %). Vérifié : Saint-Denis 22,6 → 27,5 ha/an (au-dessus de 11,3) ; Cilaos 3,3 → 7,6 (au-dessus,
budget dépassé). Rendu front = geste de Vic (COUCHES-1).

## 2. Personnes morales DGFiP → vue « mouvements » — **DÉJÀ LIVRÉ (CIRCUIT-4), vérifié**
`proprietaire_historique.acquisitions_recentes` (commune) et `.historique` (parcelle) exploitent DÉJÀ
les millésimes empilés `pm_proprietaires_millesimes` (2019→2024) ∪ `parcelle_personne_morale` (2025) :
chaque changement porte le **cédant** (siren_avant/dénomination_avant) ET l'**acquéreur**
(siren_après/dénomination_après) entre `de_millesime → a_millesime`. Vérifié : 676 mouvements à
Saint-Denis depuis 2022. C'est la « vue mouvements » demandée — rien à ajouter.

## 3. SUP AS1 (périmètres de captage) hors GPU — **INSTRUIT : source ARS trouvée mais accès restreint**
Recherche producteur (2026-09-14) : les périmètres de protection de captage (SUP AS1) de La Réunion
EXISTENT, produits par l'**ARS Océan Indien** et catalogués sur **SIGENA** (catalogue.sigena.fr — ex.
« ARS Réunion – Périmètres de Protection Éloignée », record b9c9394b). MAIS l'accès est **RESTREINT
aux membres PRODIGE pour raison de sûreté** (localisation des captages sensible) — **pas d'open data**.
Ils devraient figurer au GPU après traitement ARS, mais sont **absents du GPU 974** (vérifié SOURCES-1,
06/09/2026). Les jeux data.gouv « SUP AS1 » trouvés sont métropolitains (dépt 60, Oise). **Phrase
honnête** (à servir en fiche là où l'AS1 est attendu) : « Périmètres de protection de captage (SUP
AS1) non publiés en open data pour La Réunion — données ARS OI à accès restreint (PRODIGE) ; à
demander à l'ARS Océan Indien. » → **courrier ARS OI** (à joindre au dossier licences/demandes).

## 4. RPG → brancher le DAAF ou pinner l'année du proxy IGN — **FAIT (pin)**
Le zonage SAFER/DAAF officiel reste INTROUVABLE en open data (proxy assumé). **Année PINNÉE** :
`source_millesime` = « proxy RPG.LATEST (IGN) — campagne 2024 (data.gouv RPG-R) » (n'était plus « année
non pinnée »). RPG.LATEST est un pointeur vers la campagne la plus récente ; la sentinelle data.gouv
(RPG-R, sondée) suit les republications.

## 5. PLU — règlement écrit complet — **INSTRUIT (coût), non fait (conforme au mandat)**
Le GPU sert le règlement d'urbanisme surtout en **PDF non structurés par document** (un fichier par
PLU/commune), et non en pièce structurée exploitable champ à champ. Une ingestion du **texte intégral**
supposerait un pipeline d'extraction/segmentation par document : téléchargement des N règlements PDF du
974, OCR/parse par article (zonage, hauteurs, emprise, stationnement, mixité…), rattachement zone↔article,
et une garde de fraîcheur (le règlement change à chaque révision PLU). **Coût : élevé** (parseur PDF
robuste par gabarit de règlement + validation manuelle par commune + maintenance à chaque révision) pour
un gain incrémental sur ce que la fiche sert déjà (zone, hauteurs, destinations via l'API Carto GPU
structurée + `plu_reglement_extrait`). **Décision Vic** : à arbitrer — instruit ici, non fait.

---
**Bonus lot 2** : le slug data.gouv du CONSOENAF (Cerema) retrouvé via la table ingérée (source_url) →
sentinelle posée (last_update 2025-05-12), Conso NAF sort des « jamais vérifié » (**8** au total).
