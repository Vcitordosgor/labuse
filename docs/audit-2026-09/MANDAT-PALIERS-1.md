# MANDAT PALIERS-1 — trois paliers vrais, un seul vocabulaire, sur q_v14

**Nature** : refonte de la politique de paliers (étape 4) et de leur présentation (étape 5). Le modèle ne change pas : `p_raw` de q_v14 est conservé tel quel.
**Modèle CC** : Fable (touche tous les écrans qui classent).
**Branche** : `feat/paliers-1` **depuis `feat/scoring-4`** (elle porte q_v14 et ses libellés). **Worktree** : `~/Desktop/labuse-paliers1`.
**Pourquoi sur scoring-4** : les clients ne doivent subir qu'UNE seule bascule — nouveau modèle et nouveaux paliers ensemble, jamais deux changements à une semaine d'écart.
**Interdits** : aucun `promote`, aucune écriture sur `config/served_run.txt`, aucun merge, aucun rescoring, aucun composant neuf (DA existante), aucun audit collatéral. Ce qui n'est pas dans ce mandat n'est pas fait.

## Étape 0
`pwd` = `~/Desktop/labuse-paliers1`, branche = `feat/paliers-1`, arbre propre, `git log` montre les commits de scoring-4. Sinon : s'arrêter et signaler.

## Lot A0 — corriger les quatre restes du rapport SCORING-4 (avant tout)
1. Note de version : « 608 sorties de Priorité » est faux (Priorité en a 111) — c'est 608 sorties du top-1158. Corriger le générateur, pas le texte.
2. Réconcilier la matrice de migration (61 + 27 = 88, zéro depuis Faible) avec le top-50 (n° 3 vient de Faible). Dire lequel a raison.
3. Expliquer réserve foncière 8 789 → 5 997 en une phrase de cause.
4. Libellés : « état bâti/nu reconstruit à la date » → « terrain nu constructible » ; « part de parcelles bâties du secteur (à la date) » → « secteur peu bâti ».

## La nouvelle règle (décision Vic, 08/09/2026)
Le palier dit les **chances de vente sous 12 mois**, en probabilité absolue, hors copropriété :
- **Priorité** : p ≥ 0,20 (une chance sur cinq)
- **À suivre** : 0,10 ≤ p < 0,20 (une chance sur dix)
- **Sans signal** : p < 0,10
- **Écartée** : cascade (étage 0), inchangée
Copropriété : hors palier, comme aujourd'hui, avec le motif « copropriété ».
Anti-churn simple : au re-score mensuel, une parcelle ne descend que si p passe sous 0,18 (Priorité) ou 0,09 (À suivre). Pas d'autre hystérésis, pas de calibrage par rang, pas de plancher de capacité dans le palier.

**Ce qui sort de l'échelle et devient un motif** (affiché sur la fiche, filtrable) : bâti saturé, zone fermée, AU fermée, non constructible. Ces parcelles gardent leur palier de probabilité — une maison saturée avec une chance sur cinq de se vendre est « Priorité » pour un agent, et le motif dit au promoteur qu'il n'y a pas de projet.
**Ce qui devient un filtre** : réserve foncière (SDP résiduelle dans le décile supérieur), proposé là où le listing « Long terme » existait, indépendant du palier.
**Ce qui disparaît du vocabulaire client** : Long terme, Neutre, Faible, Score V. Le Score V reste calculable en base, il n'est plus affiché nulle part.

## Lot A — mesurer avant d'implémenter
Au banc K0 (test 2025), sur q_v14 : effectif et précision réelle de Priorité et À suivre selon la nouvelle règle, île et Saint-Paul, avec et sans les anciens déclassements. Churn mensuel simulé sur les seuils de sortie.
**Garde-fou chiffré** : si la précision de Priorité sans déclassements tombe sous 20 % au K0, s'arrêter et rendre compte avant d'implémenter.

## Lot B — la politique
`statuts.assign_tiers` v2 : seuils en config (pas en dur), déclassements → motifs, réserve → drapeau. Recalcul des paliers de **q_v14 seulement**, p_raw intact. Registre CIRCUIT mis à jour (règle derrière le calcul), sonde nocturne étendue aux quatre valeurs.

## Lot C — un seul vocabulaire, partout
Le domaine de `tier_opportunite` devient **Priorité / À suivre / Sans signal / Écartée**. Plus de brûlante / chaude / réserve / à creuser / déclassé, ni de table de traduction : la fiche, la carte, Étudier un bien, Projets, Radar, Veille, Communes, Densifier, Prospection solaire, les PDF et le Copilote lisent la valeur, aucun n'a son propre libellé. Le ×N (rapport à la moyenne de la commune) s'affiche à côté de Priorité et À suivre seulement. Les anciens runs gardent leurs valeurs via une correspondance en lecture, jamais réécrits.

## Recette
Une capture **avant / après** par écran qui classe, **sur la même parcelle**, jointe au rapport. Rien d'autre.

## Rapport
`docs/audit-2026-09/PALIERS-1.md` : le tableau du lot A, les effectifs finaux par palier (île, Saint-Paul), la liste des écrans touchés avec captures, la note de version mise à jour. Aucune promotion : Vic bascule lui-même, une fois, avec `golden promote q_v14`.
