# MANDAT FABLE — AUDIT & COMPLÉTION DES SOURCES DE DONNÉES LABUSE

## Contexte

LABUSE = plateforme d'intelligence foncière B2B pour La Réunion. 24 communes, ~431 000 parcelles, scoring 3 étages (Stage 0 binaire éliminatoire / Stage 1 Qualité 0–100 / Stage 2 Accessibilité 0–100), matrice Q×A, ~1 083 parcelles "chaudes".

Plusieurs vagues de données sont déjà intégrées. **Objectif de ce mandat : vérifier ce qui existe RÉELLEMENT dans le code et la base, puis intégrer les sources manquantes de la liste cible ci-dessous.** Tu ne dois rien supposer : tu audites d'abord, tu ajoutes ensuite.

## Règles non négociables

1. **Branche dédiée** : `feature/data-gap-2026-07`. **JAMAIS de merge** — Vic valide et merge lui-même en `--no-ff`.
2. **Un commit par lot**, message clair (`data: LOT X — <source> (<statut>)`).
3. **Aucune donnée inventée.** Si une source est introuvable, ne couvre pas le 974, ou l'URL a changé : statut BLOQUÉ dans le rapport avec la raison, et tu passes au lot suivant. Tu ne bloques jamais tout le mandat sur un lot.
4. **Respecter l'architecture existante** : mêmes patterns d'ingestion que les vagues précédentes (BODACC, Géorisques, etc.), mêmes conventions de nommage, mêmes formats de tables/couches.
5. **Fichiers volumineux** (BD TOPO, RGE ALTI) : vérifier l'espace disque disponible AVANT tout téléchargement, ne télécharger que l'emprise 974, nettoyer les fichiers bruts après ingestion.
6. Chaque variable ajoutée doit finir **rattachée à la parcelle** (flag, valeur ou score) — une donnée ingérée mais non exploitable par parcelle ne compte pas comme terminée.
7. **Coexistence Score V (mergé sur main, tag `score-v1.1`)** : la branche part du main à jour. Ne modifie ni `parcel_v_score`, ni le moteur Score V (`scoring/score_v*`), ni la vue `v_parcelles_brulantes`. La dormance/vendabilité est DÉJÀ scorée par le Score V — aucun lot ne doit la re-scorer ailleurs.

---

## PHASE 0 — AUDIT DE L'EXISTANT (obligatoire avant toute ligne de code d'ingestion)

1. Inventorie toutes les sources déjà intégrées : scripts d'ingestion, schémas/tables de la base, couches carto, docs des vagues de données, variables utilisées dans les Stages 0/1/2.
2. Sources **probablement présentes** (à CONFIRMER, pas à supposer) : PLU calibrés (23 communes + Saint-Philippe RNU), cadastre/parcelles, propriétaires personnes morales (DGFiP), BODACC, INPI RNE, Géorisques (PPR), Cartofriches, DPE ADEME, QPV 2024, ABF/Mérimée, ENS.
3. Produis à la racine du repo : **`RAPPORT-DATA-GAP.md`** avec ce tableau :

| Source cible | Statut | Où dans le code / la base | Notes |
|---|---|---|---|
| ... | PRÉSENT / PARTIEL / ABSENT / BLOQUÉ | chemins, tables | ... |

**PARTIEL** = la source existe mais pas la variable visée (ex. : Géorisques ingéré mais sans SIS/CASIAS ; MNT présent mais pente non calculée par parcelle ; DVF présent mais sans flag dormance).

4. Commit du rapport seul (`docs: rapport data gap — phase audit`), PUIS enchaîne directement sur la Phase 1. Pas d'attente de validation entre les deux.

---

## PHASE 1 — INTÉGRATION DES MANQUANTS (ordre de priorité impératif)

Ne traite que les lots ABSENT ou PARTIEL d'après ton audit. Pour chaque lot : ingestion → variables par parcelle → intégration au scoring si indiqué (documente la règle exacte choisie dans le rapport) → mise à jour de la fiche parcelle si elle existe → commit.

### LOT 1 — DVF (demandes de valeurs foncières, Etalab / data.gouv.fr, dép. 974)
- ⚠ La table `dvf_mutations_parcelle` EXISTE (créée par le mandat Score V : géo-DVF 974 niveau parcelle, millésimes **2021-2025 uniquement** — les millésimes 2014-2020 ont été retirés de la distribution officielle, fenêtre glissante 5 ans DGFiP). L'ÉTENDRE, ne pas ré-ingérer. Le flag « mutation > 20 ans » est donc INCALCULABLE — ne pas le tenter.
- Par parcelle : prix et prix/m² de la dernière mutation (les dates y sont déjà).
- Par secteur (section cadastrale ou rayon) : **médiane €/m² par type de bien** → table dédiée (input direct de la future calculette de charge foncière).
- **AUCUN scoring dormance ici** : la détention longue est déjà scorée par le Score V (famille D, signal conditionnel v1.1). Pas de bonus Stage 2.

### LOT 2 — Sols pollués : SIS + CASIAS (Géorisques)
- Flag parcelle intersectant un périmètre SIS ; flag site CASIAS sur la parcelle ou à proximité (< 100 m).
- Scoring : malus Stage 1 + mention explicite en fiche (coût de dépollution potentiel).

### LOT 3 — PEB aérodromes + classement sonore (GPU / DEAL)
- PEB Roland-Garros (Gillot) et Pierrefonds : zone A/B/C/D par parcelle.
- Classement sonore des infrastructures terrestres si disponible au 974.
- Scoring : zones A/B = Stage 0 (logement quasi impossible) ; C = malus fort Stage 1 ; D = info fiche.

### LOT 4 — Servitudes d'utilité publique complètes (GPU, assiettes de SUP)
- Prioritairement : lignes électriques HT/THT (I4), canalisations, servitudes aéronautiques (T4/T5/T7), autres SUP disponibles sur le 974.
- Flag par type de SUP intersectée + liste en fiche. Scoring : malus Stage 1 selon type.

### LOT 5 — SAR / SMVM (Schéma d'Aménagement Régional, Région Réunion / DEAL)
- Coupures d'urbanisation, espaces naturels/agricoles à préserver, zones préférentielles d'urbanisation.
- Scoring : coupure d'urbanisation = Stage 0 ou malus très fort (documente ton choix) ; zone préférentielle = bonus Stage 1.

### LOT 6 — Zone des 50 pas géométriques (DEAL / ONF)
- Flag parcelle dans la bande des 50 pas + statut si disponible.
- Fiche + malus Stage 1 (régime foncier spécifique, cession encadrée).

### LOT 7 — Périmètres irrigués (ILO / PEIGEO)
- Flag parcelle en périmètre irrigué (Irrigation du Littoral Ouest et autres périmètres).
- Scoring : zone agricole irriguée = renforcement du verrou Stage 0 (quasi intouchable).

### LOT 8 — Dynamique constructive (Sitadel)
- ⚠ `sitadel_permits` existe déjà et son refresh (source SDES/Dido, données jusqu'au mois courant) est traité par le **MANDAT SITADEL3, exécuté et mergé AVANT celui-ci**. Ne pas ré-ingérer, ne pas toucher au connecteur.
- Par parcelle : indicateur "dynamique constructive" du secteur (PC dans un rayon de 300–500 m, 5 dernières années) → bonus Stage 1 + matériau de veille concurrence en fiche. Vérifier à l'audit ce que couvre déjà le signal existant `new_permit_nearby` pour ne pas doublonner.

### LOT 9 — Potentiel résiduel (BD TOPO bâti + MNT) — LE PLUS LOURD, EN DERNIER DES LOTS CARTO
- ⚠ AUDIT D'ABORD : `sdp_residuelle_m2` (fiche/API) et un usage du MNT (vue mer) existent déjà partiellement en base — ce lot COMPLÈTE l'existant, il ne repart pas de zéro.
- Bâti existant par parcelle (emprise au sol, hauteur BD TOPO) — seulement ce qui manque.
- Pente par parcelle : écrire dans la table canonique `parcel_terrain(idu PK, pente_moy_deg, pente_max_deg, flag_terrassement_lourd)` — schéma partagé avec le futur mandat ortho, qui la RÉUTILISERA telle quelle. Privilégier **RGE ALTI 5 m** (le mandat ortho a besoin de cette finesse) ; fallback BD ALTI 25 m seulement si le disque l'impose — documente le choix. Conserver le raster de pente dérivé (pas les dalles brutes) pour éviter un re-téléchargement au mandat ortho.
- Calcul : droits PLU (emprise/hauteur de la zone) − existant = **SDP résiduelle estimée** par parcelle. C'est exactement le calcul que KelFoncier rate (emprises à 100 %) : soigne les cas limites et affiche les hypothèses en fiche.
- Scoring : SDP résiduelle intégrée au Stage 1.

### LOT 10 — RNIC (registre national des copropriétés, data.gouv.fr)
- Copropriétés du 974 : localisation, nb de lots, période de construction, éléments de fragilité disponibles.
- Rattachement parcelle si géolocalisable, sinon table communale. Cible marchands de biens — pas de scoring, fiche + filtre.

### LOT 11 — Pack marché (indicateurs communaux / carreaux, pas de scoring parcelle)
- RPLS : parc locatif social par commune.
- Communes carencées SRU (liste DEAL/ministère).
- INSEE Filosofi carreaux 200 m : revenus, ménages.
- Carte des loyers ANIL/ministère : loyers indicatifs communaux.
- Livrable : tables + affichage fiche (contexte marché du secteur). Servira au futur module bailleur et à la calculette de charge foncière.

---

## PHASE 2 — LIVRABLES FINAUX

1. **`RAPPORT-DATA-GAP.md` complété** : pour chaque lot → fait / partiel / bloqué (+ raison), règles de scoring ajoutées (formules exactes), millésimes des données utilisées.
2. **Sanity check chiffré** : pour chaque nouveau flag, nombre de parcelles impactées sur les 431 663 (ex. : "SIS : 412 parcelles ; PEB zone C : 8 940 ; mutation >20 ans : 61 000"). Toute valeur aberrante (0 % ou 90 %+) = à signaler comme suspecte, pas à masquer.
3. **Impact chaudes** : recalcul du nombre de parcelles chaudes avant/après, avec les 10 plus gros mouvements expliqués.
4. **Impact Brûlantes 🔥** : la vue `v_parcelles_brulantes` est dynamique et suit les chaudes — donner la distribution avant/après (nb Brûlantes, garde-fou [30-120] ; si la fenêtre est quittée, PROPOSER un seuil recalculé — top décile V des chaudes — sans jamais l'appliquer).
5. **NE PAS MERGER.** Tu t'arrêtes là. Vic valide et merge.

---

## HORS SCOPE — NE PAS FAIRE

- Veille active (révisions PLU / enquêtes publiques, délibérations communales, EPFR, ventes judiciaires, biens sans maître) → mandat séparé ultérieur.
- MAJIC propriétaires particuliers, LOVAC, Fichiers fonciers CEREMA complets → verrouillés, on n'y touche pas.
- Scraping d'annonces immobilières (LeBonCoin, portails) → interdit.
- Toute refonte UI/UX → hors mandat.

---

## AJOUTS SESSION (10/07/2026)

1. **Phase 0** : vérifier les permis `sitadel_permits` datés dans le futur (max constaté 2026-08-17). Si marginal (< 50) : consigner comme artefact source dans le rapport. Sinon : investiguer le parsing de dates avant de continuer.
2. **LOT 8** : l'indicateur "dynamique constructive" doit être GRADUÉ (densité de PC dans le rayon), pas binaire — `new_permit_nearby` touche déjà 31 499 parcelles sur Saint-Paul seul, un booléen ne discrimine plus rien.
