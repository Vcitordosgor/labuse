# LA BUSE — Barème : score, complétude, verdict & mutabilité

> **But du document.** Rendre la notation **défendable** face à un promoteur. Toute parcelle
> peut être expliquée : « pourquoi ce verdict, pourquoi cette note ». Aucun chiffre n'est inventé —
> chaque seuil ci-dessous est **tiré du code** (fichier + valeur exacte). Les seuils marqués
> **PLACEHOLDER** sont des valeurs par défaut **à calibrer** (jamais présentées comme sourcées).

LA BUSE affiche **quatre notions distinctes** qu'il ne faut pas confondre :

| Notion | Question à laquelle elle répond | Échelle | Source |
|---|---|---|---|
| **Score d'opportunité** | « À quel point le signal est-il fort ? » | 0–100 | `config/opportunity_weights.yaml` |
| **Score de complétude** | « Combien sait-on sur cette parcelle ? » | 0–100 | `config/completeness_weights.yaml` |
| **Verdict** | « Qu'en conclut LA BUSE ? » | 4 statuts | `scoring/status.py` + `scoring/declassement.py` |
| **Mutabilité** | « Le terrain est-il libre ou déjà bâti ? » | bâti % | `bati.py` (BD TOPO IGN) |

Le **score** mesure une intensité, le **verdict** est une décision prudente, la **mutabilité** est une
observation du sol. Un score élevé ne vaut pas « opportunité » (voir §5).

---

## 1. Score d'opportunité (0–100)

Calculé à partir de la cascade. **Source : `config/opportunity_weights.yaml`.**

```
si une couche = HARD_EXCLUDE        → score = 0  (verdict « exclue » ou « faux positif »)
sinon :
  base      = 50
  pénalités = Σ ( 5 × multiplicateur_sévérité )     # un terme par SOFT_FLAG
  bonus     = Σ ( plafond_bonus × magnitude )       # un terme par signal positif
  score = clamp(50 − pénalités + bonus, 1, 100)
  score = clamp(score + ajustement_terrain, 1, 100) # feedback ∈ [−20, +20]
```

**Pénalités (SOFT_FLAG)** — base **5 points**, multipliée par la sévérité :

| Sévérité | Multiplicateur | Pénalité |
|---|:--:|:--:|
| faible | ×1 | −5 |
| moyen | ×2 | −10 |
| fort | ×3 | −15 |

**Bonus (signaux positifs)** — le poids est un **plafond** ; la couche renvoie une `magnitude` ∈ [0,1]
(intensité réelle), et le bonus appliqué = `round(plafond × magnitude)`. Tout est borné et tracé.

| Bonus | Plafond | Déclencheur |
|---|:--:|---|
| `potentiel_foncier_region` | 12 | recouvrement d'un îlot de potentiel foncier régional |
| `proprietaire_morale_acquerable` | 12 | propriétaire personne morale (acquisition facilitée) |
| `permis_sitadel_recent_proximite` | 8 | permis SITADEL récents à proximité (marché actif) |
| `surface_utile` | 8 | courbe **saturante** sur la surface (une parcelle géante ne gagne pas mécaniquement) |
| `zonage_u_au` | 8 | zone U ou AU (binaire) |
| `contexte_dvf_favorable` | 8 | marché DVF réel : médiane €/m² + liquidité |
| `acces_direct_voirie` | 3 | accès direct à la voirie (binaire) |

**Ajustement par retour terrain** (feedback agrégé par zone de 300 m, borné à ±20) : une zone qui
accumule des faux positifs décote les voisines (−8/faux positif), un bon lead remonte (+6). Tracé
dans la fiche ; **ne court-circuite jamais** la règle d'or (§5).

---

## 2. Score de complétude (0–100)

Mesure **combien on sait**, pas si c'est bon. Une famille de données qui répond ajoute son poids ;
un échec/UNKNOWN ajoute 0. **Somme des poids = 100. Source : `config/completeness_weights.yaml`.**

| Famille | Poids | | Famille | Poids |
|---|:--:|---|---|:--:|
| zonage PLU/GPU | 12 | | cadastre | 8 |
| risques (Géorisques/PPR) | 12 | | agricole (SAFER) | 8 |
| SAR | 10 | | SITADEL (permis) | 8 |
| DVF (marché) | 10 | | propriétaire | 8 |
| pente | 8 | | parc national | 6 |
| OCS GE (occupation sol) | 5 | | accès (BD TOPO/BAN) | 5 |

**Bandes :** forte 80–100 · moyenne 50–79 · **faible 0–49** (la bande « faible » plafonne le verdict, §5).

---

## 3. Verdict — l'arbre de décision

**Source : `scoring/status.py`**, puis correction métier `scoring/declassement.py` (§7).
Les seuils viennent de `opportunity_weights.yaml › status_rules`.

```
1.  HARD_EXCLUDE présent ?            → « exclue »  ou  « faux positif probable »
2.  complétude < 50 ?                 → « à creuser »   (RÈGLE D'OR — voir §5)
3.  opportunité ≥ 65  ET  complétude ≥ 50  ET  aucun SOFT_FLAG « fort » ?
                                      → « opportunité »
4.  sinon                            → « à creuser »
5.  (post) déclassement métier       → peut RÉTROGRADER vers à creuser / faux positif / exclue
```

- **opportunity_threshold = 65** — au-dessus, le signal est jugé suffisamment fort.
- **completeness_floor = 50** — en dessous, on ne déclare **jamais** une opportunité chaude.
- Un **SOFT_FLAG « fort »** présent empêche aussi le statut « opportunité ».

---

## 4. Les 4 verdicts, en langage promoteur

| Verdict | Ce que ça veut dire | Action conseillée |
|---|---|---|
| **Opportunité** | Signal fort **et** données suffisantes, aucun bloqueur. | À démarcher / shortlister. |
| **À creuser** | Soit le signal est moyen, soit **on ne sait pas encore assez** (complétude < 50), soit un bloqueur « fort ». | Vérifier le point manquant avant d'investir du temps. |
| **Écartée** | Contrainte **bloquante** réglementaire/physique (ex. PPR rouge, cœur de Parc, plan d'eau). | Ne pas prospecter (sauf changement réglementaire). |
| **Faux positif probable** | La parcelle **est** en réalité autre chose (micro-parcelle, équipement, déjà bâtie, pente non aménageable). | Ignorer — c'est un artefact de détection. |

---

## 5. Pourquoi un score élevé peut rester « à creuser »

C'est **volontaire** et c'est la **règle d'or** du produit. Extrait exact de `scoring/status.py` :

```python
# Complétude trop mince : on ne déclare jamais une opportunité chaude.
if completeness_score < floor:        # floor = 50
    return EvaluationStatus.A_CREUSER
```

**Exemple.** Une parcelle peut afficher **score 72** (zone U, propriétaire moral, marché actif) mais
n'avoir que **complétude 35** (risques PPR non disponibles, pente inconnue, propriétaire non résolu).
LA BUSE refuse de la marquer « opportunité » : **le signal est bon, mais on ne sait pas encore assez**
pour l'affirmer. Le verdict honnête est « à creuser » — *« vérifiez les risques et la pente, puis
revenez »*. Afficher « opportunité » sur une donnée trop mince serait une promesse non tenue.

> **Le score est une intensité, pas une promesse.** Le verdict tient compte de la **confiance**
> (complétude) en plus de l'intensité (score).

---

## 6. Contraintes BLOQUANTES (HARD) vs VIGILANCE (SOFT)

**Source : `config/cascade_rules.yaml`.**

**BLOQUANTES (HARD_EXCLUDE → score 0, verdict « écartée » ou « faux positif ») :**

- Plan d'eau (centroïde ou ≥ 50 % de la parcelle sur l'eau).
- Cœur de Parc national.
- Forêt publique **domaniale**.
- Zonage **A/N** ≥ **90 %** de la parcelle *(seuil **PLACEHOLDER**, défaut directive)*.
- Emplacement réservé (**ER**) ≥ **50 %** *(seuil **PLACEHOLDER**)*.
- PPR **zone rouge**.
- Équipement OSM franc (cimetière, école sur la parcelle).

**VIGILANCE (SOFT_FLAG → pénalité, pondérée par la sévérité) :**

- Eau en débord (< 50 %) → moyen ; adhésion Parc → moyen ; forêt publique non domaniale → fort.
- Zonage **mixte** (A/N < 90 % avec U/AU) → liséré toléré dès **5 %** *(PLACEHOLDER)*.
- SAFER (agricole) → moyen ; aléas non rouges (fort/moyen/faible) → flag de même sévérité.
- Proximité **ravine** (buffer **10 m**, *PLACEHOLDER*) → moyen ; trait de côte → moyen.
- **Pente > 30 %** *(seuil flag **PLACEHOLDER**)* → moyen ; ABF → faible ; ENS → moyen ;
  occupation naturelle/agricole (OCS GE) → faible ; indivision ≥ 2 droits → fort.

La **SAR** est **informative** (ne pénalise pas le score, Décision 2) — toute divergence est signalée
en vigilance, jamais en exclusion.

---

## 7. Déclassement métier — le garde-fou « faux positifs »

**Source : `scoring/declassement.py`.** Un score brut élevé ne suffit pas : si la parcelle porte un
signal bloquant **franc**, on la **rétrograde avec un motif visible**. Le score brut est **conservé**
(transparence) ; seul le **statut** est corrigé. On ne **remonte jamais** un statut.

| Critère | Seuil | Conséquence |
|---|---|---|
| **Surface** | < 100 m² | faux positif probable (« aucun programme possible ») |
| | < 250 m² | à creuser (« sous le seuil d'un programme ») |
| **Pente** | > 60 % | faux positif probable (« non aménageable ») |
| | > 40 % | à creuser (« aménagement difficile ») |
| **Équipement OSM** | ≥ 50 % | faux positif probable (« la parcelle EST l'équipement ») |
| | ≥ 30 % | à creuser |
| **Accès (voirie BD TOPO)** | aucune voirie à ≤ 6 m | à creuser (« accès non identifié — servitude à vérifier ») |
| **Bâti (R1)** | voir §8 | à creuser / faux positif selon la couverture |

**Cumul :** ≥ 2 signaux « faux positif » → **écartée**. Calibré sur Saint-Paul pour **ne pas**
déclasser à tort une grande parcelle qui ne fait qu'**effleurer** un équipement (chevauchement de
bord) : seuls les recouvrements **francs** comptent.

> Le seuil **250 m²** explique pourquoi la plus petite « opportunité » de Saint-Paul fait 251 m² :
> en dessous, le déclassement la passe automatiquement en « à creuser ».

---

## 8. Mutabilité (bâti) — terrain libre ou déjà construit

**Source : `bati.py`** (couche **BD TOPO IGN**, confiance haute). Ratio = surface bâtie ∩ parcelle ÷
surface parcelle. C'est une **observation du sol**, distincte du verdict.

| Classe | Ratio bâti | Libellé | Déclassement |
|---|---|---|---|
| vacant | < 5 % | aucun bâti significatif | — |
| peu bâti | 5–15 % | présence à vérifier | — (sauf grande parcelle > 5 000 m² → « restructuration potentielle ») |
| partiellement bâti | 15–30 % | partiellement bâtie | à creuser |
| déjà bâti probable | 30–50 % | déjà bâtie probable | faux positif |
| déjà bâti | ≥ 50 % | déjà bâtie | faux positif |
| **ensemble bâti** | ≥ 3 bâtiments **ou** 1 bâtiment ≥ 400 m², dès **15 %** de couverture | résidence/équipement | faux positif |

Sur la **carte**, le mode **« Mutabilité »** colore en **vert** le foncier mutable (< 15 % bâti) et en
**gris** le bâti (≥ 15 %). Si la couche bâtiments n'est pas ingérée, LA BUSE affiche « occupation non
vérifiée » — **jamais** un faux « vacant ».

---

## 9. Récapitulatif des seuils & des PLACEHOLDER à calibrer

**Seuils structurants (assumés, calibrés sur Saint-Paul) :**

| Seuil | Valeur | Fichier |
|---|---|---|
| base du score | 50 | `opportunity_weights.yaml` |
| pénalité / SOFT_FLAG | 5 (×1/2/3) | `opportunity_weights.yaml` |
| seuil opportunité | 65 | `opportunity_weights.yaml` |
| plancher complétude | 50 | `opportunity_weights.yaml` |
| micro-parcelle / seuil programme | 100 / 250 m² | `declassement.py` |
| pente difficile / non aménageable | 40 % / 60 % | `declassement.py` |
| accès enclavé | 6 m | `declassement.py` |
| mutabilité (info/léger/signif./bâti) | 5 / 15 / 30 / 50 % | `bati.py` |

**PLACEHOLDER — valeurs par défaut à calibrer avec Vic (jamais présentées comme sourcées) :**

| PLACEHOLDER | Défaut | Fichier:ligne |
|---|---|---|
| zonage A/N hard-exclude | 90 % | `cascade_rules.yaml:79` |
| zonage A/N liséré min | 5 % | `cascade_rules.yaml:81` |
| ER hard-exclude | 50 % | `cascade_rules.yaml:105` |
| buffer ravine | 10 m | `cascade_rules.yaml:134` |
| seuil flag pente | 30 % | `cascade_rules.yaml:159` |

---

## 10. Traçabilité

Chaque note est **traçable** : la cascade enregistre, couche par couche, le verdict, la pénalité/bonus
appliqué (`weight_applied`) et la source. Chaque déclassement porte un **motif en clair** (ex.
« micro-parcelle 85 m² — aucun programme possible »). La fiche affiche un **badge de provenance**
(sourcé / estimé) sur chaque valeur. La réponse à « pourquoi cette note ? » est toujours dans la fiche.

---

*Document de référence du barème. Les seuils sont **tunables** (YAML + déclassement) et destinés à
être affinés par le feedback terrain et la calibration Vic. Aucun seuil n'est modifié par ce document.*
