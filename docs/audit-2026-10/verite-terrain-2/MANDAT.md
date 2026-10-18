# MANDAT-VERITE-TERRAIN-2 — tout ce que LABUSE affirme, face à la réalité

Rédigé le 15/10/2026. Modèle : Opus en chef d'orchestre, un sous-agent par volet, **un seul à la fois** (Mac 8 Go, une autre session tourne). Branche `audit/verite-terrain-2` depuis main, worktree `~/Desktop/labuse-verite2`, ports 8795/5995. **Lecture seule : aucune correction, aucune écriture en base, rien sur le VPS.**

Repartir du comparateur de VERITE-TERRAIN-1 (`src/labuse/verite_terrain*.py`) : l'étendre, ne pas le réécrire. Verdicts : **CONFORME · LABUSE FAUX · SOURCE PLUS RÉCENTE · NON COMPARABLE** (avec la raison). Chaque « LABUSE FAUX » est revérifié à la main. Appels aux API publiques séquentiels, espacés, mis en cache dans le dossier de la chasse. Aucune métrique arrangée : un mauvais résultat est écrit tel quel, avec ses limites.

## Deux temps

**Temps 1 — maintenant, avant le run final** (volets A, B, C : ils ne dépendent pas du calcul ; ce qu'ils trouvent partira dans le run final). À la fin du temps 1 : rapport intermédiaire, commit, **STOP**, et attendre que Vic écrive « run final fait ».

**Temps 2 — après le run final q_v19** (volets D, E : ils mesurent le calcul lui-même, donc sur ses nouveaux chiffres). Reprendre dans la même branche, rebasée sur main.

## Temps 1

**A — Toutes les règles PLU, pas un échantillon.** Chaque règle chiffrée validée de `config/plu_destinations/` (hauteur, emprise, reculs, pleine terre, niveaux, stationnement, mixité si mergée) relue dans le règlement officiel en vigueur, à la page citée ; la citation correspond au texte. Exhaustif. Taux de conformité par commune et par type de règle.

**B — Temps de trajet et distances.** Sur 300 parcelles stratifiées (littoral, mi-pentes, Hauts, cirques) : chaque temps ou distance servi (isochrones, « à X minutes de », distances aux équipements, arrêts de transport) comparé à un calculateur d'itinéraire de référence pour le même mode. Tolérance justifiée (par ex. ±20 %).

**C — Les trous de la première vérité terrain.** DPE par adresse BAN (API ADEME) et permis (Sitadel) sur les 500 parcelles de VERITE-TERRAIN-1 ; et tout ce qui y était NON COMPARABLE et peut l'être autrement.

## Temps 2

**D — La capacité face aux vrais permis.** Parcelles ayant obtenu un permis (Sitadel : surface créée, logements, date) depuis l'entrée en vigueur du PLU actuel de leur commune : capacité LABUSE contre autorisé. Écart médian, dispersion, par commune et type de zone. Chaque permis **au-dessus** de la capacité LABUSE est expliqué un par un (dérogation, règle mal calibrée, réunion de parcelles, permis antérieur au PLU…).

**E — Les prédictions face à ce qui s'est passé ensuite.**
- Signal de mutation : à partir de l'état des données à une date passée, les parcelles « probables » se sont-elles vendues plus souvent ensuite que les autres ? Taux de vente par bande, lift, intervalle de confiance. Si un rejeu propre n'est pas possible, le dire et proposer le protocole (instantané daté) qui le rendra possible.
- Prix : pour les ventes réelles postérieures au calcul, prix estimé contre prix réel : écart médian, part à ±10 % et ±20 %, par commune et type de bien.

## Livrables

`docs/audit-2026-10/verite-terrain-2/` : `PLU-TOUTES-REGLES.md`, `TRAJETS.csv`, `DPE-PERMIS.csv`, `PERMIS-VS-CAPACITE.csv`, `SIGNAL-BACKTEST.md`, `PRIX-BACKTEST.csv`, `ECARTS.md`, `RAPPORT.md` (verdict en 5 lignes, un tableau par volet, limites honnêtes, et ce qui peut servir d'argument commercial **seulement si** les chiffres le justifient). Comparateurs et protocoles rejouables. Un commit par volet. Ne merge pas.
