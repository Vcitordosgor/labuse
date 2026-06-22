# La Plaine-des-Palmistes (97406) — DÉCISION : NO-GO gold « 0 opportunité »

> **Statut : NON-GOLD (différée).** Run technique réussi, mais résultat métier `0 opportunité`
> non promu sans décision produit explicite. Décision du 2026-06-22.

Référence run : `docs/communes/la_plaine_des_palmistes_RESULTS.md`
(commit `33696ca` — `LOT6: La Plaine-des-Palmistes re_couches_re_cascade`).

---

## 1. Le run est techniquement propre

- **Exit 0 / SUCCÈS**, 22/22 post-checks verts, aucun rollback, aucun doublon.
- Cadastre 6 450 conservé · 0 doublon IDU · 0 géométrie invalide · 100 % geom_2975 · **100 % évaluées (6 450/6 450)**.
- Couches re-fetchées : bâti 0→7 618, PPR/SAR/ravines/OSM/prescriptions ajoutés (2/133/504/103/986),
  voirie 3 178 (**garde adaptée validée** : >0, ≠5000, non tronquée, page unique), DVF 736→271 (geo-dvf).
- Zonage **100 % total ET 100 % propre `DU_97406`** (`97406_PLU_20230527`).

**→ Aucune objection technique.** Le blocage est métier/scoring, pas data.

## 2. Le résultat métier `0 opportunité` n'est pas promouvable en l'état

Verdicts *latest* (dernière éval/parcelle) après run :

| Verdict | n |
|---|---:|
| opportunité | **0** |
| à creuser | 2 013 |
| écartée | 415 |
| faux positif probable | 4 022 |
| **Σ** | 6 450 |

- **Score d'opportunité max de la commune = 53** ; **0 parcelle ≥ 55** sur 6 450 (seuil opportunité = **65**).
- Complétude haute (moy. 79–84, **0 parcelle < 50**) → ce n'est **pas** un blocage de complétude ni de flag :
  **aucune parcelle n'atteint le score requis.**
- Comparé aux pairs gold (mêmes règles `2b45db74`) : Bras-Panon max 81 / Petite-Île 82 / Les Avirons 79 /
  Le Port 78 — **tous 78–82 avec des centaines/milliers de parcelles ≥ 65**. La Plaine **plafonne à 53**.
- `faux positif probable` (62,4 %, le plus bas des pairs) et `écartée` (6,4 %, milieu de gamme) sont **cohérents**
  (bâti déjà construit ; grandes parcelles naturelles ~15 ha). L'anomalie est concentrée sur l'absence totale
  d'opportunité.

**Promouvoir « gold » une commune à 0 opportunité exige une décision produit explicite** (une commune gold
sert de référence de fiabilité ; 0 opportunité doit être un choix assumé, pas un défaut subi).

## 3. Simulation : neutraliser `02 + 15 + 24` ne crée AUCUNE opportunité

Le `0 opportunité` est partiellement amplifié par une lacune de mapping des prescriptions GPU
(les typepsc `02`, `15`, `24` ne sont pas mappés dans `config/cascade_rules.yaml` → pénalité `FAIBLE −5`
par défaut ; `02` « PPRN » couvre **100 %** des parcelles de La Plaine).

Simulation **lecture seule** (retrait des −5, sans mutation) :

| Verdict | n | score max **théorique** | → ≥ 65 |
|---|---:|---:|---:|
| à creuser | 2 013 | **58** | **0** |
| faux positif probable | 4 022 | 54 | 0 |
| écartée | 415 | 48 | 0 |

➡️ **Toujours 0 opportunité.** Le score max passe de **53 à 58**, toujours **< 65**. Les parcelles plafonnent
à ~58 (base 50 + zonage U/AU 8) car **les gros bonus ne se déclenchent pas** (marché DVF mince 271,
potentiel_foncier/propriétaire morale/permis récents absents). **Le 0-opportunité est un profil d'opportunité
intrinsèquement faible (montagne, marché mince, contraintes réelles), PAS un simple artefact corrigeable.**

## 4. NO-GO sur le mapping global `02 → PASS`

Le typepsc `02` est **hétérogène** (1 378 polygones, 10 communes, 20 libellés) et **porte de vrais risques
bloquants** :
- périmètre/informational : « PPRN <date> » (946), « conditions spéciales » (180) ;
- **🔴 risque bloquant** : « **interdiction de constructibilité** » (77, 7 communes ; La Plaine = 2 201 ha),
  « PPR - principe d'interdiction », « **Aléa fort R1** », « **submersion R** » (rouge), « aléa inondation STPC » ;
- mal classé : « Emplacement réservé » (devrait être `05`), « biotope ».

La couche risque dédiée `ppr` est **séparée et éparse** (La Plaine `ppr` = 2) — le `02` n'est **pas redondant**
avec `ppr`. **Un `02 → PASS` en bloc masquerait de vrais risques** → **NO-GO**. De plus, **8+ communes gold**
portent `02/15/24` (Le Tampon 389, Bras-Panon 205, Saint-Denis 90, Saint-Pierre 40, Saint-Joseph t15=121…) :
tout changement de mapping **doit être re-validé contre les golds** (risque de régression).

## 5. Décision et suites possibles

- **La Plaine-des-Palmistes reste NON-GOLD** (`etat: partiel_evalue`, `reliable=False`). Config **inchangée**.
- **Aucune correction `cascade_rules.yaml` maintenant**, aucune re-cascade, aucun rollback, aucun nettoyage,
  aucun merge.
- **Deux chantiers DÉCOUPLÉS**, à traiter séparément sur décision explicite :
  1. **Décision produit** : une commune à **0 opportunité réelle** peut-elle être « gold » ?
     (si oui → ATTENTION + note métier ; si non → laisser non-gold, état actuel).
  2. **Chantier mapping prescriptions** (global, indépendant de La Plaine) : remap **content-aware** par
     libellé/nature (périmètre PPRN → PASS ; aléa rouge/interdiction → pénalité/exclusion ; ER mal classé → `05`),
     **avec re-validation de toutes les golds impactées**. Ce chantier **ne rendra pas** La Plaine gold-éligible
     (cf. §3).

---

*Document de décision — lecture seule, aucune mutation DB, aucun changement de scoring/config.*
