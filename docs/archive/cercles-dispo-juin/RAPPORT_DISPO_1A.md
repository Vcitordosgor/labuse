# RAPPORT DE DISPONIBILITÉ — 1.A Propriétaire / personnes morales (DGFiP)

> Règle §7 : rapport AVANT le loader. Sondé le 2026-06-14 depuis le conteneur (la policy réseau
> autorise désormais data.gouv.fr / data.economie.gouv.fr — bloqués lors des sondes du Lot C2).

## Source retenue

| | |
|---|---|
| **Jeu de données** | « Fichiers des locaux et des **parcelles** des personnes morales » |
| **Producteur** | DGFiP (Ministères économiques et financiers) — application MAJIC |
| **Portail** | data.gouv.fr / data.economie.gouv.fr (ODS) |
| **Licence** | **Licence Ouverte v2 (lov2)** — réutilisation libre, y compris commerciale |
| **Millésime** | situation au 1er janvier ; dernier publié = **2025** (historique 2019→2025) |
| **Couverture 974** | ✅ ressource « fichier des parcelles (situation 2025) — dpts 57 à 976.zip » (le 976 borne haute inclut **974 Réunion**) |
| **Format / poids** | ZIP (171 Mo, dpts 57-976) → fichier texte délimité ; descriptif PDF/ODT fourni |
| **Fraîcheur** | annuelle |

## Schéma utile (descriptif DGFiP 2024/2025)

Champs restitués (par parcelle) : code département, **code INSEE commune**, **préfixe section**,
**code section**, **numéro de plan** (→ IDU 14), contenance, code droit réel, **n° SIREN**,
**GROUPE PERSONNE (0-9)**, **FORME JURIDIQUE** + **abrégée** (SCI, SARL, SA…), **DÉNOMINATION**
(nom du propriétaire morale).

**Groupe de personne morale (catégorie)** :
`0` = personnes morales non remarquables (SCI, sociétés…) · `1` = État · `2` = région ·
`3` = département · `4` = commune · `5` = office HLM (bailleur social) · `6` = SEM ·
`7` = copropriétaires · `8` = associés · `9` = établissements publics / organismes associés.

→ mappe directement sur la taxonomie `owner_type` de C3 (commune, État, collectivité, EPF/EP,
bailleur social, SEM, SCI, société, copropriété, indivision).

## Conséquences de conception

- Une parcelle **présente** dans le fichier → propriétaire **personne morale** : `owner_type`
  (depuis le groupe + forme juridique) + **`owner_name`** (dénomination). Donnée **publique**,
  pas de convention.
- Une parcelle **absente** → propriétaire **personne physique** (particulier) : aucune donnée
  perso (légal) → **bouton « demande SPF »** (déjà livré en C3). C'est le comportement voulu.
- On **fusionne** avec C3 : le classifieur `owner_type`, le badge fiche, le filtre carte et le
  bouton SPF existent ; 1.A leur fournit la **vraie donnée** (remplace le proxy convention absent).

## Verdict : **GO** — loader construit dans la foulée (filtré INSEE 97415, idempotent, source/millésime tracés).
