# CIRCUIT-P6 tâche 1 — relance des 4 « sortie non-JSON », et tâche 2 « sans millésime »

Base réelle `labuse`. Suite de CIRCUIT-P5 (`docs/CIRCUIT/captures/p5/etats-agents-avant-apres.md`).
Un calcul résiduel tournait sur la base pendant l'opération (aucune bascule/injection lancée).

## Tâche 1 — `labuse agent source --ids 148,25,40,73`

Les quatre sources restées « jamais vérifiée » après P5 sur une **sortie du modèle non-JSON**
(aucun objet exploitable). Contrôle daté du **2026-09-24**.

**Coût jetons : 0,6617 € pour 4 appels** (web_search facturé à part par Anthropic, hors ledger
`ia_log`). Détail par appel : 0,1414 / 0,1838 / 0,1581 / 0,1786 €.

| id | source | verdict | ce que l'agent a trouvé | état après |
|---|---|---|---|---|
| 73 | FRR ex-ZRR (Légifrance) | **nouvelle** | Arrêté du 14 avril 2025 (NOR ATDB2508688A) modifiant l'arrêté du 19 juin 2024 — en vigueur depuis le 17/04/2025 · preuve Légifrance JORFTEXT000051469445 | **nouvelle version** (vanne) |
| 148 | Communes La Réunion — contours (IGN) | introuvable | sortie du modèle non-JSON (aucun objet exploitable) | jamais vérifiée |
| 25 | INPN / patrinat — espaces protégés | introuvable | sortie du modèle non-JSON | jamais vérifiée |
| 40 | NPNRU (DEAL Réunion / ANCT) | introuvable | sortie du modèle non-JSON | jamais vérifiée |

**Bilan : 1 résolue sur 4.** FRR ex-ZRR passe « nouvelle version » (sa vanne d'injection
apparaît, veille `methode='agent'` / `dernier_statut='nouvelle_version'` / passage 24/09). Les
trois autres retombent sur une sortie non exploitable — un nouveau passage pourra les résoudre
(le parseur robuste de P5 avait déjà récupéré INPI/PVGIS/CBS d'un run où ils tombaient « JSON
invalide » ; ici FRR a basculé grâce au même mécanisme).

## Tâche 2 — le mode « sans millésime » (à jour par construction)

Trois réservoirs n'ont **aucun millésime amont** à comparer : les laisser en « jamais vérifiée »
(gris) était un contresens — il n'y a rien à vérifier. Nouveau mode `sans_millesime` (posé sur
`data_sources.mode_remplissage`, seed `MODE_ET_CADENCE`) : `etat_reservoir` les rend
**« à jour » (mint)**, hors « jamais vérifiée », et la **raison écrite** est portée par le
réservoir (`sans_millesime`, affichée dans la fiche : « sans millésime — … » + « dernier contrôle :
sans objet — à jour par construction »).

| id | source | raison écrite |
|---|---|---|
| 19 | OpenStreetMap / Overpass | flux continu (planet hebdomadaire + diffs) : aucune version datée à comparer |
| 31 | INPI RNE (dirigeants) | API RNE v3.0 sans extrait daté chez le producteur : pas de millésime publié (règle anti-invention 6.2) |
| 131 | Coût de construction (EPTB SDES + choix LABUSE) | donnée interne (choix LABUSE) : pas de producteur amont ni de millésime |

Les trois sont exclues des agents `--tous` (rien à trouver) et de la garantie G5 (leur absence de
date de contrôle est légitime). Vérifié via `_assembler_reservoirs` : les 3 sortent `('mint',
'à jour')`.
