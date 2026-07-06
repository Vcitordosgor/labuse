# SCHÉMA DU SCORING PREMIUM — LABUSE (v2)

> **Source de vérité = le code.** Ce document décrit le scoring **tel qu'implémenté** (couches
> `src/labuse/cascade/`, barèmes `config/*.yaml`, matrice `src/labuse/scoring/dryrun.py`). La spec
> suit le code, jamais l'inverse. Valeurs datées du run de calibrage `q_v2` (Saint-Paul, dry-run).

## 1. Principe — l'économie d'abord

Le scoring répond à trois questions, dans cet ordre :

1. **Combien de m² constructibles ?** → SDP résiduelle (socle L1, facteur Q dominant).
2. **À qui, acquérable ?** → axe A « pur vendeur » + garde foncier public.
3. **Est-ce du terrain ou un équipement en usage ?** → gardes étage 0.

**Trois lois :**
- **L1** — la constructibilité résiduelle est LE socle de Q (−25 à +30), pas un bonus parmi d'autres.
- **L2** — le zonage et la surface ne donnent **plus** de points (déjà encodés dans la SDP → anti double-compte).
- **L3** — un coût **inconnu** est un flag ; un coût **estimable** est un malus (pente = malus, pollution/écoulement = flag).

Score = **Q** (qualité/constructibilité) × **A** (accessibilité vendeur), chacun `base 50 + Σ(poids), borné [1,100]`.

---

## 2. Étage 0 — filtre dur (`HARD_EXCLUDE` → `écartée`, score 0)

Une seule couche en `HARD_EXCLUDE` suffit à écarter la parcelle. Couches historiques conservées :
eau (majorité/centroïde), cœur Parc National, forêt domaniale, PPR zone rouge, ER ≥ 50 %,
zonage PLU A/N ≥ 90 %, **pente > 60 %**, micro-parcelle, occupation bâtie franche, faux-positif OSM.

**Gardes v2 ajoutées** (`config/cascade_rules.yaml`) :

| Garde | Couche | Règle | Motif |
|---|---|---|---|
| **G1** | `foncier_public` | propriétaire PM de droit public non marchand — DGFiP groupes **{1 État, 2 Région, 3 Département, 4 Commune, 9 Éts publics}** | « Propriété publique (X) — non acquérable » |
| **G2** | `emprise_lineaire` | enveloppe orientée **largeur < 8 m ET ratio L/l > 8** (cumulés) | « Emprise linéaire — voirie/délaissé probable » |

> **HLM (groupe 5) et SEM (groupe 6) sont MARCHANDS → jamais exclus** (contreparties acquérables,
> futur segment bailleur). Le « non-marchand » du barème est porteur.
>
> **G2 — la jambe `largeur < 8` protège les drapeaux** (corps large + lanière d'accès) : 0/3831
> drapeaux flaggés à tort sur l'échantillon Saint-Paul.
>
> **G3 (équipement en usage) et G4 (emprise routière) : NON câblés** — inmesurables sans ingestion
> OSM loisirs/parkings (G3) et surfaces routières BD TOPO (G4). Dette Phase 1bis (cf. NOTES).

---

## 3. Q — Qualité économique (`base 50`)

### 3.1 Socle L1 — SDP résiduelle (`residuel_socle`, poids signé direct)

Facteur **dominant**, lu dans `parcel_residuel.sdp_residuelle_m2` (calibrée règlement PLU réel) :

| SDP résiduelle | points | lecture |
|---|---:|---|
| < 100 m² | **−25** | rien à construire |
| 100–300 | −10 | une maison — hors cible collectif |
| 300–800 | +5 | petit collectif / 2–4 lots |
| 800–2 000 | +15 | opération viable |
| 2 000–5 000 | +25 | belle opération |
| > 5 000 | +30 | opération majeure |
| **non calculé** | **UNKNOWN** | absence de donnée ≠ absence de droits → complétude, **jamais −25** (règle absolue) |

### 3.2 Marché → Q (spec §4.2/4.3 ; le marché SORT de A)

| Signal | Couche | Barème |
|---|---|---|
| **Prix de sortie** | `dvf` | quintile **île** du €/m² **bâti** (méthode secteur-médian) → **0/+2/+4/+7/+10**. Bornes figées `[1719, 2307, 2917, 3968]` (retunables `config`). Base bâti = ce qu'un promoteur vend (SDP × prix de sortie). |
| **Liquidité** | `dvf` | mutations récentes secteur → **0..+6** (courbe / `liquidity_ref`). |
| **Permis récents** | `sitadel` | le marché construit ici → **0..+4**. |
| **Écoulement (L3)** | `dvf` | SDP > 2 000 m² ET liquidité faible (< 4 mut.) → **flag** « profondeur de marché à vérifier » (0 pt). |

### 3.3 Autres signaux Q

| Signal | Couche | Barème |
|---|---|---|
| **Vue mer** (974) | `vue_mer` | oui **+8** / partielle **+4** — prime de prix de sortie. |
| **Assemblage** | `assemblage` | voisin contigu (`ST_DWithin 1 m`) même SIREN, **garde-fou détention ≤ 10** (anti-lotissement) → **+6** + flag « assiette élargissable ». |
| **OCS artificialisé** | `ocs_ge` | sol artificialisé non bâti (ZAN-compatible) → **+4**, **cumul plafonné à +10 avec la vue mer**. |
| **Pente graduée (L3)** | `pente` | 0–10 % → 0 · 10–25 % → **−4** · 25–40 % → **−10** · 40–60 % → **−16** (> 60 % : exclu étage 0). |
| **Friche** | `friche` | avec projet +8 / sans projet +5. |
| **Aménités** | `amenites` | plafond **+5** (confort de revente, départage). |
| **Potentiel foncier Région** | `potentiel_foncier_region` | **+5** (corroborant). |
| **Accès voirie** | `acces` | +3. |

### 3.4 L2 — SUPPRIMÉ

`zonage_u_au = 0` et `surface_utile = 0` (`config/opportunity_weights.yaml`) : subsumés par le socle SDP.
Les hard-excludes zonage A/N et micro-parcelle (étage 0) restent — seuls les **bonus** sont retirés.

---

## 4. A — Accessibilité = PUR VENDEUR (`base 50`)

`config/scoring_matrice.yaml → a_layers` = **`[proprietaire, age_dirigeant, bodacc, dpe_passoire]`**.
Le marché (dvf, sitadel) a **quitté A** pour Q (v2) : A ne mesure plus que « qui vend ».

| Couche | Signal | Barème |
|---|---|---|
| `proprietaire` | PM acquérable / indivision | +12 / flag indivision (fort). Fichiers fonciers sous convention → souvent UNKNOWN. |
| `age_dirigeant` | INPI, gérant âgé = horizon transmission | courbe 55/65/75/85 → **4/8/12/14**. Âge **absent = UNKNOWN** (complétude), jamais malus. |
| `bodacc` | procédure collective | **flag 0 pt** ; état **ROUGE** (procédure ouverte) → `evenement='rouge'` (override, §6). |
| `dpe_passoire` | maison F/G | flag 0 pt « pression réglementaire datée ». |

---

## 5. Matrice Q × A → statut

`compute_matrice` (`src/labuse/scoring/dryrun.py`), seuils `config/scoring_matrice.yaml` :

```
exclue étage 0                                             → écartée
evenement='rouge' (survivante)                             → chaude       (override, §6)
Q ≥ 65  ET  A ≥ 60  ET  A-complétude ≥ 50                  → chaude
Q ≥ 65                                                     → à surveiller
Q ≥ 50                                                     → à creuser
Q < 50                                                     → écartée
```

**Double verrou (règle d'or)** : jamais « chaude » sur une accessibilité connue à moins de 50 %
(`a_completude` = part des signaux A ≠ UNKNOWN). Une A « creuse » (que des UNKNOWN) ne promeut pas.

---

## 6. UNKNOWN & overrides

- **UNKNOWN** = donnée absente/non instruite → impacte la **complétude**, **jamais un malus** ni un
  défaut silencieux. Cas : socle SDP non calculé, âge dirigeant absent, ABF (covisibilité 500 m non
  instruite), couche non ingérée pour la commune.
- **Override rouge** : une procédure collective BODACC **ouverte** (`evenement='rouge'`) force
  « chaude » sur une survivante, quel que soit Q/A (l'exclusion étage 0 n'est jamais surchargée).
- **`weight_override`** (`base.py::scored`) : contribution **signée directe** au score, court-circuite
  sévérité/bonus, pour les barèmes à bandes hors du multiplicateur de sévérité (socle SDP −25..+30,
  pente −16..0, prix quintile). Rétro-compatible (défaut `None`).

---

## 7. Traçabilité

Chaque verdict porte `source_table` + `source_id` (cliquable jusqu'à l'enregistrement) et son
`weight_applied` signé. Contrôle : `base + Σ(weight_applied) = score` (hors clamp/hard-exclude).

---

## 8. Invariants observés — run `q_v2` (Saint-Paul, dry-run)

- **Répartition** : chaude **83** (1,6 ‰ = funnel premium) · à surveiller 1 720 · à creuser 3 353 · écartée 45 973.
- **Override rouge** : `97415000AC0253` chaude via BODACC procédure ouverte (au mérite ET override).
- **UNKNOWN socle** : 14 % des chaudes, **37 % de la population évaluée** (= couverture `parcel_residuel` ~63 %).
- **Signaux Q neufs actifs** : 31 entrantes (28 prix Q4/Q5, 22 vue mer, 7 assemblage).
- **Rééquilibrage** : le très-haut Q (90+) se dégonfle (retrait L2), la bande premium 70–89 se concentre.

Le seuil A ≥ 60 et le calibrage fin seront rejugés **en usage**, sur les vraies parcelles (Phase 3+).
