# COMMUNE-RANGEMENT-1 — Les défauts de l'audit

**Branche** `feat/commune-audit-1`, départ **`7b411d7b`** (fin de COMMUNE-AUDIT-1). Un commit par lot,
branche poussée. Corrige les quatre défauts relevés par l'audit. DA existante.

## Lot 1 — la tendance 12 mois

Le front (`ContextePanel.tsx`) lisait `tend['pct']` ; le moteur Marché commune
(`build_marche_commune` → ligne `tendance_12m`) émet **`delta_pct`** (clé déjà lue par l'outil Marché,
`moteurs.tsx:707`). La tendance ne s'affichait donc **jamais**. Aligné : le front lit `delta_pct`
(via `tendPct`, une seule source de vérité pour le badge de la ligne fermée et la ligne « Tendance 12
mois »).

**Vérifié sur les 24 communes** : `delta_pct` présent (donc tendance affichée) pour **19/24** ;
**5/24** sous le seuil DVF (`SEUIL_TENDANCE_N` par fenêtre) → `delta_pct` absent, rien n'est rendu
(correct — pas de tendance inventée).

Preuve : `captures/commune-rangement1/{saint-denis,cilaos}/marche.png`. Saint-Denis affiche désormais
le badge **« −0,3 % »** + la ligne « Tendance 12 mois −0,3 % » ; Cilaos (sous seuil) reste sans
tendance. Avant : `captures/commune-audit/{saint-denis,cilaos}/06_marche.png` (aucune tendance).

## Lot 2 — les deux lignes mal rangées

**`parc_social_rpls_logements`** (table `rpls_commune`, SDES) — fait 100 % communal, jusqu'ici servi
**uniquement** au contexte marché de la fiche parcelle. **Tranché : servi aussi à la fiche commune**,
à son échelle. Nouveau builder `fiche_commune.parc_social(insee)`, transporté dans le payload et
**re-servi live** (`_rafraichir_partages`, le cache nocturne étant antérieur au lot), rendu dans la
carte **Population & logement** (« Parc social (RPLS) — N logts · constr. médiane AAAA »), source RPLS
créditée. **Déclaré au registre** (`fiche_commune_population`). **Décision : il reste AUSSI sur la
fiche parcelle** — contexte marché autonome, cohérent avec la redondance de contexte assumée entre les
deux fiches (comme `statut_plu`, `tfpb_taux_pct`, `zonage_abc_logement`…).

**`prix_neuf_observe_eur_m2`** — **Tranché : NON déplacé, reste sur la fiche parcelle.** Ce n'est pas un
agrégat communal propre mais le **prix de sortie du bilan résolu par parcelle** (`resolve_prix_neuf_marche`,
cascade bassin sourcé > secteur > commune > repli île) : sa valeur dépend de la localisation du terrain.
La fiche commune sert déjà la **notion neuf** en VEFA à l'acte (`prix_neuf_vefa_acte_eur_m2`, chiffre
en-tête) ; le registre garde les deux **scindés** (« jamais l'un sous le libellé de l'autre »). Ajouter
l'observé à la fiche commune dupliquerait la notion neuf sans grain communal propre. Il reste donc le
prix de sortie de la fiche parcelle.

Preuve : `captures/commune-rangement1/{saint-denis,cilaos}/population.png` (ligne Parc social RPLS +
source SDES).

**Note verrou V5c.** Servir `parc_social_rpls_logements` sur **deux** robinets (commune + parcelle) en
fait un couple multi-robinet : les deux chemins lisent la MÊME table `rpls_commune` par insee (passe-plat,
aucun recalcul) → **comparaison robinet à robinet sans objet**, déclarée dans `sonde_circuit.NON_SONDES`
(même motif que `iris_quartier` / `part_artificialisee_pct`). V5c repasse **ok**.

## Lot 3 — acquisitions_pm

Calculée par `_compute_commune_contexte` (`acquisitions_recentes`, requête coûteuse) et transportée
dans le payload, mais **aucune carte ne la rendait** (déménagée en RETOURS-1 R3 vers l'outil Communes
« Acquisitions récentes »). **Tranché : on cesse de la calculer et de la transporter.** Raison : elle
est déjà servie par l'endpoint dédié **`/communes/{c}/acquisitions-pm`** (intact, 200 vérifié) que lit
l'outil ; la recalculer dans le payload contexte était du travail mort. Retirée du calcul, du payload
caché (`pop`) et du type `ContexteCommune` (front). Le type `AcquisitionsPm` reste (servi par l'endpoint
dédié).

## Lot 4 — la carte ZFANG/FRR

Seule carte rendue **sans robinet** au registre. **Déclarée** comme les autres : deux chiffres commune
`zfang_regime_commune` et `frr_classement_commune` (passe-plats depuis `territoire_fiscal_commune`, la
source unique qui peint aussi la carte et filtre les parcelles) + le robinet
**`fiche_commune_zfang_frr`**. `registre.verifier()` vide, tous les chiffres de robinet existent.

Preuve : `captures/commune-rangement1/{saint-denis,cilaos}/zfang-frr.png` (rendu inchangé — la carte
existait ; c'est sa **déclaration** au registre qui manquait).

## Hors périmètre (respecté)

Les creux de données par commune (Radar sous seuil, QPV absent, ORT hors) = des faits, pas des défauts.
Les 13 données commune absentes = mandat séparé.

## Preuves

- Captures avant : `captures/commune-audit/…` (état `7b411d7b`) · après : `captures/commune-rangement1/…`
  (script `frontend/qa/commune_rangement1_cap.mjs`).
- **`tsc -b` vert** (chaque lot).
- **`circuit verrous -w G8` vert** : 28 joués, **0 cassé** (V5c ok — 8 sondés · 122 raisonnés · 211
  mono-robinet), G8 en avertissement **non bloquant** (environnemental : sources hors sonde, agent à 0 €
  — pré-existant, sans rapport avec ce mandat).

*Note d'historique : le couple V5c (parc_social sur 2 robinets) est ouvert par le lot 2 et refermé par
sa raison `NON_SONDES` regroupée dans le commit du lot 4 (registre) — la branche finale est verte.*
