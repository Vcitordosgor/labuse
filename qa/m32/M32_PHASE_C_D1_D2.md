# M32 — Phase C : D1 composition du deck + D2 vérification des 5 cartes

## D1 — Composition du deck (écart expliqué + mini-deck livré)

**L'écart.** Le rapport estimait « ~16 dé-déclassées ». En réalité il y a **20** dé-déclassées AU → tête
(`declasse_au_statut_inconnu → chaude`). Le deck des 20 est ordonné dé-déclassées d'abord, `LIMIT 20`
→ les 20 dé-déclassées ont **rempli le quota**, coupant les mouvements brûlante + la sortie. Le deck
livré est donc juste (les 20 plus « prioritaires ») mais il a mangé la vitrine.

**Mini-deck complémentaire (5 cartes) — `~/Desktop/deck_mini_brulante_m32.pdf`** (format identique) :
| # | idu | commune | avant → après | cause |
|---|---|---|---|---|
| 1 | 97418000AT2542 | Sainte-Marie | chaude → **brûlante** | recalibration/départage (zone UB, hors AU) |
| 2 | 97422000CY0197 | Le Tampon | chaude → **brûlante** | recalibration/départage (zone Uc, hors AU) |
| 3 | 97422000AK1442 | Le Tampon | a_creuser → **brûlante** | ⚠ override registre M28 (piscine) → a_creuser ré-appliqué à la bascule |
| 4 | 97416000ET2162 | Saint-Pierre | **brûlante** → chaude | recalibration/départage (sortie douce, reste en tête) |
| 5 | 97404000AL1773 | L'Étang-Salé | **brûlante** → a_creuser | **plancher L'Étang-Salé** : AUb 470 m² < 3333 m² min = au_sous_plancher pénalisé |

**Correction du rapport** : la carte #5 (AL1773) et les **10 « chaude → a_creuser »** attribués à tort
à « recalibration » sont en réalité le **plancher L'Étang-Salé** (nouveau min 10 log × 30-50 log/ha) :
11 parcelles AUb trop petites (< 3333 m²) deviennent au_sous_plancher **pénalisées** → sortent de tête.
C'est le plancher qui fait son travail (parcelles non constructibles seules), pas du bruit.

## D2 — Vérification des 5 cartes (requêtes + résultats)

### D2a — Emprise bâti max(BD TOPO, CoSIA) + piscine (AS1400, AL1154)

| idu | commune / zone | surface | bâti BD TOPO | bâti CoSIA | ratio bâti | piscine |
|---|---|---|---|---|---|---|
| 97418000AS1400 | Sainte-Marie 1AUb | 322 m² | **0** | **0** | **0 %** | non |
| 97419000AL1154 | Sainte-Rose 1AUa | 1 702 m² | **0** | **0** | **0 %** | **OUI (conf. 0,888)** |

- **AS1400** : les DEUX couches la voient vide, aucune piscine → **vraiment nue** → chaude **correct**
  (dé-déclassement AU légitime, la parcelle est bien constructible).
- **AL1154** : **0 bâti** (BD TOPO ET CoSIA) mais **piscine détectée** (0,888). Le filtre bâti
  s'appuie sur l'EMPRISE BÂTIE (0 % ici, une piscine n'est pas du bâti) → **aucun seuil dépassé** →
  la parcelle **suit LA RÈGLE** (servie chaude), pas une exception. ⚠ MAIS c'est un cas piscine comme
  **AK1442** : si tu veux que la piscine déclasse (a_creuser), c'est une **entrée de REGISTRE** à
  décider (elle n'y est PAS aujourd'hui) — pas un déclenchement du filtre bâti. **On statue.**

### D2b — Largeur inscriptible + Polsby-Popper → badge « géométrie contrainte » (AL1523, AI1136, AM0768)

Seuils badge (M28) : largeur inscriptible < 8 m **OU** Polsby-Popper < 0,1.

| idu | commune | surface | largeur inscriptible | Polsby-Popper | badge attrape ? |
|---|---|---|---|---|---|
| 97403000AM0768 | Entre-Deux | 316 m² | **6,7 m** (< 8) | 0,322 | **OUI** (largeur) |
| 97405000AL1523 | Petite-Île | 1 295 m² | 9,6 m | **0,074** (< 0,1) | **OUI** (Polsby-Popper) |
| 97402000AI1136 | Bras-Panon | 1 025 m² | 25,1 m | **0,063** (< 0,1) | **OUI** (Polsby-Popper) |

**Les 3 sont attrapées par le badge.** Le cas que tu craignais — **AL1523 filiforme** (largeur 9,6 m
> 8, donc PAS attrapée par la largeur) — **est bien attrapée par Polsby-Popper (0,074 < 0,1)**. AI1136
est large (25 m) mais très allongée (PP 0,063) → attrapée aussi. Aucune filiforme n'échappe.

## Verdict D2

- **Aucun ratio bâti ne dépasse les seuils du filtre** sur les 5 (AS1400/AL1154 = 0 % bâti ;
  AM0768/AL1523/AI1136 = contraintes géométriques attrapées par le badge). Elles **suivent la règle**.
- **Un seul point à statuer** : AL1154 porte une piscine (0,888) sans bâti — cas type AK1442. Le
  filtre bâti ne la déclasse pas (0 % bâti) ; à toi de dire si elle rejoint le registre (a_creuser
  piscine) comme AK1442, ou reste servie (chaude) telle quelle.

Rien n'a changé dans la mesure (`q_v13_m32_mesure` inchangée, servi gelé, golden 117/117). Pas de
bascule avant ta revue de D1 + D2.
