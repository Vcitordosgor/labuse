# MANDAT SCORING-3 — le run candidat « gains sûrs », et le potentiel

**Branche : `feat/scoring-3`** (depuis `main` après merge de `feat/scoring-2`). Aucun sous-agent ne touche à git. Claude Code en Fable.
**Références** : `docs/audit-2026-09/COMPTE-RENDU-SCORING-2.md` (tableau K0, verdicts), `LABUSE-SCORE-V2-PLAN.md`.
**Doctrine** : le run candidat est **calculé, pas basculé**. `q_v11_m137` reste servi. Vic bascule depuis Données › Circuit après lecture de la note de version et de l'écart.
**Clôture** : tsc, build, tests 100 % verts, commit à la fin de chaque lot.

Contexte : pas de convention fichiers fonciers — le bloc propriétaire n'existe pas. Le plafond mesuré de la probabilité de vente est le plafond réel. La valeur se déplace vers **ce qu'on fait des dixièmes gagnés, le potentiel, et les données propres à LABUSE**.

**Étape 0** : pwd, branche, arbre propre.

---

## L1 — Le run candidat q_v12 : gains sûrs de SCORING-2, rien d'autre

1. Recette du candidat, **exactement** ce que l'arène a validé : variables mortes retirées (K2) · résiduel lu correctement (K3, la correction du feature store) · voisinage global (K4 bis, variante globale, la meilleure tête) · calibration isotonique **par segment** (le seul apport de K4 retenu) · modèle global, pas segmenté · horizon 12 mois servi, 24 mois calculé et stocké.
2. Produit par le pipeline **réel** (celui du bouton « Calculer »), pas par le harnais d'arène — c'est la seule façon d'être sûr que ce qui a été mesuré est ce qui sera servi. Vérification : les scores du run réel et ceux de l'arène doivent coïncider sur 1 000 parcelles tirées au hasard (écart médian < 10⁻⁶) ; sinon, la différence est expliquée avant d'aller plus loin.
3. Le run enregistre ses millésimes (FLUX-1 F2.2), son protocole, ses métriques K0 sur 2025 et **sa note de version** en français, lisible depuis Données › Circuit › Basculer.
4. **Garde de churn** : le compte-rendu donne le churn du top-1158 vs q_v11_m137 et la liste des 50 parcelles qui sortent de Priorité avec la raison (variable retirée ? résiduel corrigé ? voisinage ?). Vic ne bascule pas à l'aveugle.
5. Rien n'est basculé. Le bouton Basculer de Données › Circuit doit montrer q_v12 comme candidat prêt, avec l'écart avant/après.

## L2 — Le bug du feature store, corrigé à la source

K3 a montré que le feature store perdait les zéros de `parcel_residuel`. La lecture a été corrigée en arène ; ici on corrige **la source** : le job qui alimente le feature store, un test qui échoue si une parcelle avec résiduel = 0 ressort « inconnue », et une vérification que les autres colonnes numériques n'ont pas le même défaut (un zéro n'est jamais un NULL). Liste des colonnes vérifiées au compte-rendu.

## L3 — BDNB au catalogue et au CRON

La Base nationale des bâtiments (open data) donne, par bâtiment : année de construction, classe DPE, surface, usage. C'est le dernier proxy accessible de l'âge du propriétaire et de l'état du bien.

1. **Ingestion** : source ajoutée au catalogue (Données), avec sa méthode de veille (data.gouv, `api`), cadence trimestrielle au CRON, jamais auto-injectée (doctrine). Jointure bâtiment → parcelle par l'emprise (BD TOPO / cadastre), couverture mesurée.
2. **Variables candidates**, testées au banc K0 avant toute inscription au modèle : année de construction (et « avant 1975 »), classe DPE (et « F ou G »), écart entre surface bâtie BDNB et BD TOPO (extension non déclarée ?). Tableau K0 avec/sans. Elles n'entrent dans le candidat q_v12 **que si** elles gagnent sur la précision en haut de liste sans dégrader l'ECE — sinon elles attendent.

## L4 — Le potentiel, prêt pour la Priorité v2

Le résiduel couvre 99 % du parc. Préparer la seconde moitié de « Priorité = mutation × potentiel » — calculée et stockée, **pas encore affichée** (c'est PALIERS-1) :

1. **Par parcelle** : SDP résiduelle (m²), et **valeur créée estimée** (€) = SDP résiduelle × prix de secteur au m² bâti (sector_price), avec un intervalle honnête, et la source de chaque terme.
2. **Un indice d'opportunité** = probabilité 12 mois × valeur créée, normalisé par commune, stocké dans le run candidat. Pas un nouveau modèle : un produit de deux colonnes existantes, expliqué.
3. **Mesure** : sur 2025, les parcelles qui se sont vendues **et** avaient un fort potentiel — c'est la cible réelle du promoteur. Précision@100 par commune de l'indice d'opportunité vs celle de la probabilité seule. Tableau au compte-rendu.
4. **Accès** : trois indicateurs par parcelle, stockés : propriétaire identifiable (PM via SIREN / PP inconnu) · courrier possible (adresse connue) · déjà contacté par un compte (piste CRM, courrier) — ce dernier **jamais partagé entre comptes**.

## L5 — Le retour terrain : commencer à capter

Sans propriétaire, c'est la donnée qui fera la différence dans six mois. Le strict minimum, sans alourdir :

1. Sur la carte Kanban CRM et la fiche parcelle, un **sélecteur d'un clic** après contact : contacté · pas de réponse · refus ferme · pas maintenant · ouvert à discuter · en négociation · vendu à nous · vendu à un autre. Stocké par compte, horodaté, réversible.
2. **Cloisonnement écrit et testé** : une étiquette d'un compte n'apparaît jamais chez un autre. Un agrégat anonyme (« 3 refus fermes sur cette parcelle, tous comptes ») n'est pas produit dans ce mandat.
3. Un compteur admin (Pilotage) : étiquettes posées / semaine. Quand il dépassera 200, TERRAIN-1 aura de la matière.

---

## Compte-rendu attendu

Par lot : fait / mesuré / reste. Attendus nommés : **L1.2 l'écart run réel vs arène** · L1.4 le churn et les 50 sorties de Priorité expliquées · L1.3 la note de version de q_v12 telle que Vic la lira · L2 les colonnes vérifiées · L3.2 le tableau K0 avec/sans BDNB · **L4.3 précision@100 de l'indice d'opportunité vs probabilité seule** · L5.2 le test de cloisonnement.

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/scoring-3
```
