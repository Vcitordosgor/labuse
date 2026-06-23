# Inventaire stratégique post-16-gold — pourquoi on ne lance pas tout de suite une 17ᵉ commune

> **Décision du 2026-06-23 : 🟡 NO-GO « next commune » + PAUSE STRATÉGIQUE.**
> Le filon « gold facile » est épuisé après Saint-André. La prochaine action à plus forte valeur
> n'est **pas un run** mais un **audit scoring / produit (lecture seule)** du cluster faible-opportunité.
> Inventaire **strictement lecture seule** (aucun run, aucune mutation DB, aucune modif code/config).

## État consolidé

| Élément | Valeur |
|---|---|
| `main` | **`43b791b`** (`docs: merge Saint-Leu PLU freshness watch`) |
| Communes **gold** | **16 / 24** |
| DB | **22 communes / 418 068 parcelles** |
| Dernier gold | **Saint-André** (97409) — **1ᵉʳ gold débloqué par le repli AGORAH** (PLU absent du GPU) |
| Sous veille | **Saint-Leu** (97413) — PLU 2007 en révision (cf. `saint_leu_PLU_AGORAH_FRESHNESS_WATCH.md`) |

**Repère d'opportunité gold** (dernière éval/parcelle) : Saint-André **0,24 %** (54 opp, max_score 79),
Saint-Denis **0,22 %** (84 opp, max 72). C'est le **plancher** des communes gold (les denses/chef-lieu).

## Les 8 communes restantes (non-gold)

| Commune | INSEE | DB | config etat | reliable | parcelles | évaluée | Blocage / raison | Potentiel gold | Recommandation |
|---|---|---|---|---|---|---|---|---|---|
| **Saint-Leu** | 97413 | présente | partiel_non_evalue | False | 22 959 | ❌ (0) | PLU absent GPU ; AGORAH = **PLU 2007 en révision** (projet arrêté 11/12/2025, avis défavorable Région 27/02/2026) | Moyen (différé) | **Veille PLU** (réouverture S2-2026) |
| **Saint-Philippe** | 97417 | présente | partiel_non_evalue | False | 4 162 | ❌ (0) | PLU absent GPU **ET absent AGORAH** (`[]`) ; `is_rnu=false` (un PLU existe mais non numérisé) | Faible court terme | **Sourcing PLU manuel** (commune / CASUD / DEAL) |
| **La Plaine-des-Palmistes** | 97406 | présente | partiel_evalue | False | 6 450 | ✅ 100 % | **0 opp (0,00 %)** ; **max_score 53 < seuil 65** → structurel | **Quasi-nul intrinsèque** | **NO-GO durable** |
| **Les Trois-Bassins** | 97423 | présente | absent → importée | False | 5 314 | ✅ 100 % | importée NO-GO **1 opp (0,02 %)** | Très faible | NO-GO (à confirmer à l'audit) |
| **Sainte-Rose** | 97419 | présente | absent → importée | False | 6 287 | ✅ 100 % | importée NO-GO **8 opp (0,13 %)** | Faible / marginal | Audit scoring |
| **Entre-Deux** | 97403 | présente | partiel_evalue | False | 6 312 | ✅ 100 % | **9 opp (0,14 %)** ; baisserait encore avec bâti R1 | Faible / marginal | Audit scoring |
| **Salazie** | 97421 | **absente** | absent / attendre | False | 0 | — | cirque, relief extrême, urbanisme atypique ; **AGORAH PLU 2022 frais (327 z.)** dispo | Incertain | Attendre / **import risqué** |
| **Cilaos** | 97424 | **absente** | absent / attendre | False | 0 | — | cirque, relief extrême ; AGORAH PLU 2008/2018 (152 z.) dispo | Incertain | Attendre / **import risqué** |

> Toutes les non-gold **évaluées** plafonnent à **≤ 0,14 %** d'opportunité — **sous** le plancher gold (0,22 %).
> Un passage gold sur ces communes (cascade complète avec bâti) ferait plutôt **baisser** encore le taux
> (declassement bâti R1 / pente), sans valeur métier ajoutée.

## Classement par catégorie

1. **Récupérable court terme (cible technique facile)** : **AUCUNE.** Saint-André était la dernière
   (présente + PLU frais immédiatement exploitable via AGORAH).
2. **Récupérable seulement avec source PLU** :
   - **Saint-Leu** — AGORAH 2007 exploitable mais en révision → **veille** (S2-2026).
   - **Saint-Philippe** — ni GPU ni AGORAH → **sourcing PLU manuel** requis.
3. **Scoring / métier à résoudre** (présentes, évaluées, opportunité marginale/nulle) :
   **La Plaine** (0,00 %), **Les Trois-Bassins** (0,02 %), **Sainte-Rose** (0,13 %), **Entre-Deux** (0,14 %).
4. **NO-GO durable** : **La Plaine-des-Palmistes** (max 53 < seuil = structurel) ; **Les Trois-Bassins**
   (quasi-0 confirmé en import complet). (Sainte-Rose / Entre-Deux : à trancher à l'audit.)
5. **Absent / import risqué** : **Salazie** (PLU 2022 frais mais cirque atypique) ; **Cilaos**
   (PLU 2008/2018, cirque). Import possible mais opportunité probablement quasi-nulle (pente → declassement).

## Conclusion

- **Aucune cible technique « facile » ne reste après Saint-André.** Les présentes restantes sont soit
  bloquées source PLU, soit plafonnées par le scoring.
- **Saint-Philippe** nécessite un **sourcing PLU manuel** (pas d'AGORAH, pas de géométrie GPU).
- **Saint-Leu** **attend la révision PLU** (approbation visée S2-2026, non stabilisée — avis Région défavorable).
- **Salazie / Cilaos** = **imports risqués de cirques** (relief extrême, urbanisme atypique) — différés.
- **La Plaine / Les Trois-Bassins / Sainte-Rose / Entre-Deux** = **cluster faible opportunité** (≤ 0,14 %).
  Question ouverte : quasi-0 **intrinsèque** (relief + zonage A/N + bâti R1) **ou** pondérations trop
  sévères en zone rurale/relief ? → à trancher par un audit, pas par un run.

## Verdict

🟡 **NO-GO « next commune ».** Pas de 17ᵉ gold immédiat : ce serait soit impossible (source PLU manquante),
soit sans valeur métier (opportunité quasi-nulle).

**Prochaine vraie action = AUDIT SCORING / PRODUIT (lecture seule)** sur le cluster faible-opportunité
(La Plaine, Entre-Deux, Les Trois-Bassins, Sainte-Rose) : décider **NO-GO durable** (quasi-0 réel) **vs**
**réglage des pondérations** relief/rural (seuils bâti R1 / pente), puis ré-évaluer. En parallèle : **veille PLU**
maintenue (Saint-Leu S2-2026 ; sonde de sourcing Saint-Philippe). Salazie / Cilaos restent en « attendre ».

---

### Provenance (lecture seule)

- Config : `config/communes_gold_standard.yaml` (24 communes) via `labuse.communes`.
- DB (SELECT only) : `parcels` / `parcel_evaluations` — parcelles, évaluées, et **opportunité canonique**
  (dernière éval/parcelle, champ `status`).
- Sondes AGORAH (Open Data Réunion) + GPU `municipality` (apicarto.ign.fr) pour 97413/97417/97421/97424,
  conservées **hors dépôt** dans `/tmp/labuse_plu_probe/`. Aucune mutation DB, aucun run, aucune modif code/config.
