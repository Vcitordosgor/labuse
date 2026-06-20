# SAINT-PAUL — LOT 2 : Résultats de l'import complet (GOLD STANDARD)

> Exécution réelle du LOT 2 le **2026-06-20**. Saint-Paul est passé de **3 000 → 51 129 parcelles**
> (cadastre complet Etalab), 100 % évalué, en préservant toutes les données existantes et sans
> toucher aux autres communes. **Conclusion : SUCCÈS** — Saint-Paul est désormais la commune
> **gold standard** de LA BUSE.

## 1. Résultat final de l'import

| # | Contrôle | Résultat | Statut |
|---|---|---|:---:|
| 1 | **Parcelles Saint-Paul** | **51 129** (cadastre complet, source cadastre.data.gouv.fr Etalab) | ✅ |
| 2 | **Sections** | **98 / 98** | ✅ |
| 3 | Doublons IDU | **0** | ✅ |
| 4 | Géométries invalides | **0** (geom + geom_2975) | ✅ |
| 5 | **Parcelles évaluées** | **51 129 / 51 129** (100 %) | ✅ |
| 6 | Conservation pipeline / feedback / alertes | **4 / 1 / 12 — inchangés** (avant = après) | ✅ |

## 2. Verdicts après recalcul cascade

| Verdict | Nombre | Part |
|---|---:|---:|
| Faux positif probable | 29 943 | 58,6 % |
| À creuser | 19 172 | 37,5 % |
| Écartée | 1 490 | 2,9 % |
| **Opportunité** | **524** | **1,0 %** |

> Taux d'opportunités **1,0 %** (vs 2,8 % sur le pilote urbain de 3 000) → **pas d'explosion
> d'opportunités**, au contraire plus conservateur : les Hauts ajoutent surtout des « à creuser »
> et « écartées » (zones A/N), comme attendu. **Anti-fausse-opportunité R1 maintenu** : aucune
> opportunité n'est bâtie à > 50 % (vérifié sur les 524).

## 3. Couches critiques (emprise commune COMPLÈTE)

| Couche | Avant (pilote urbain) | Après (commune complète) |
|---|---:|---:|
| **Bâti** (BD TOPO) | 11 285 | **83 981** (×7,4 — Hauts couverts) |
| **Zonage PLU** | — | **1 097** · couverture parcelles **100 %** |
| **Pente** (RGE ALTI) | — | **13 062** |
| **Voirie** (BD TOPO) | — | **5 000** |
| Ravines | 98 | **1 244** |
| Prescriptions PLU (ER…) | 117 | **710** |
| PPR | 4 | 4 (partiel — détail PEIGEO-bloqué) |
| SAR | 303 | 303 |
| DVF (mutations) | 3 651 | 3 651 |

## 4. Santé après import

| Endpoint | Statut |
|---|---|
| `/healthz` | **200** |
| `/readyz` | **200** |
| `/demo-status` | **200 · `ready_for_demo=True` · all_conform=True · 14/14 checks** |

> La parcelle de démo **BV0912** est passée `opportunité` → **`à creuser`** : la donnée commune
> complète a révélé un **emplacement réservé (ER 81 - chemin de la Cigale)** + un **accès non
> identifié** (voirie la plus proche à ~93 m). Verdict plus conservateur et **correct** ; l'attente
> de fixture a été mise à jour en conséquence (sans toucher au verdict métier).

## 5. Temps total

**≈ 2 h 50** (10:58:59Z → ~13:49Z), décomposé :
- import parcelles : **76 s** ;
- ré-ingestion des couches (emprise complète, 19 couches, 0 erreur) : **371 s** ;
- 1ʳᵉ cascade interrompue (goulot voirie identifié) + diagnostic + création d'index ;
- **recalcul cascade complet : 7 020 s (~117 min)** — long pole, coût `ST_Intersection`/couverture
  sur zones urbaines denses (84 k bâtiments).

## 6. Index ajouté (persisté)

Pendant l'exécution, le recalcul cascade s'est révélé très lent : le calcul de **distance à la
voirie la plus proche** (proxy d'accès) faisait un KNN qui **parcourait l'index spatial complet**
(dont les 83 981 bâtiments) en rejetant les non-voirie.

**Correctif (persisté dans `models.ensure_geom_2975`) :**
```sql
CREATE INDEX IF NOT EXISTS idx_spatial_layers_voirie_geom2975
ON spatial_layers USING gist (geom_2975) WHERE kind = 'voirie';
```
> Prédicat **`kind='voirie'` SEUL** (pas de `AND geom_2975 IS NOT NULL`) : la requête cascade ne
> garantissant pas `IS NOT NULL`, le planner ne pourrait pas matcher un index partiel plus
> restrictif et retomberait sur l'index complet (lent). Mesure : voirie ~0,95 ms/parcelle après
> index (vs des heures sans). Cet index est désormais **créé automatiquement** sur toute base
> (VPS, restauration, déploiement neuf, future généralisation) et **vérifié par
> `tests/test_saint_paul_quality.py`**.

## 7. Sécurité (backups)

| Backup | Chemin | Taille | SHA-256 (début) | Restaurabilité |
|---|---|---:|---|---|
| Pré-LOT 2 (LOT 1) | `/var/backups/labuse/labuse-labuse-20260620-101644.dump` | 235 Mo | `5de67e10…` | testée (LOT 1) |
| **Post-LOT 2** | `/var/backups/labuse/labuse-post-lot2-saint-paul-complet-20260620-140347.dump` | **477 Mo** | `9c6d26af…` | **testée** (base temporaire, RC=0, 51 129 SP) |

## 8. QA verrouillée

`tests/test_saint_paul_quality.py` (gold standard, contre la base applicative) :
- nombre minimal **51 129** parcelles · **98 sections** ;
- 0 doublon IDU · 0 géométrie invalide · IDU propres ;
- index GIST présents (dont **`idx_spatial_layers_voirie_geom2975`**) ;
- **100 % évaluées** · couverture zonage ≥ 95 % ;
- **couches critiques complètes** (bâti > état pilote, zonage/pente/voirie présents) ;
- échantillon des verdicts · **anti-fausse-opportunité R1** sur toutes les opportunités ;
- requête fiche < 1 s.
→ **12/12 verts.**

## 9. Conclusion

✅ **Saint-Paul est COMPLET (51 129 parcelles), auditable, fiable, explicable et 100 % évalué.**
Tous les contrôles critiques sont verts ; aucune corruption ; données métier préservées ; backup
post-LOT 2 vérifié et restaurable. **Saint-Paul est verrouillé comme commune GOLD STANDARD de
LA BUSE.**

La méthode est désormais reproductible : pour une autre commune, on rejoue
`scripts/lot2_import_saint_paul.py` (paramétré par INSEE) avec l'index voirie déjà en place →
la généralisation aux 23 autres communes devient une **duplication maîtrisée** (cf. LOT 6 à venir).
