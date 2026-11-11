# ESTIMER-4 — comparables sans terrain renseigné (maison à terrain connu)

**Branche** `fix/estimer-4` (depuis `origin/main` à jour, `cc25a62fc`) · worktree `~/Desktop/labuse-estimer3`
· base locale `labuse` (DVF au 31/12/2025). Date 11/11/2026. Fait suite à ESTIMER-ECRAN-1 (recette 2 :
« terrain non renseigné », 9,1 % des ventes de maisons de l'île).

## Question

Pour estimer une **maison dont le terrain est connu**, comment traiter les **comparables sans terrain
renseigné** (`surface_terrain = 0` dans DVF) ? Trois variantes, mesurées **no-leak** (comparables
strictement antérieurs, mutation jugée exclue), sur les **ventes 2025 de maisons à terrain connu et
surface connue** (niveau « surface » du servi), via la chaîne SERVIE (`estimer3._selection_rayon` +
pondération de `estimer3.eur_m2_semblable`) — seul le traitement du terrain manquant change :

- **A. Plein poids (actuel)** — la pondération saute le facteur « écart de terrain » pour un comparable
  sans terrain → il garde tout son poids (distance / surface / ancienneté).
- **B. Pénalisé** — on applique le facteur terrain en traitant le comparable comme `terrain = 0` (écart =
  terrain du sujet) : d'autant plus pénalisé que le sujet a du terrain.
- **C. Écarté si ≥ 8 restent** — on retire les comparables sans terrain quand il reste **≥ 8** comparables
  AVEC terrain dans la sélection ; sinon on les garde (repli).

Mesure : `docs/audit-2026-11/estimer-4/mesure_terrain.py`. **2 123** maisons évaluées ; **1 146 (54 %)
concernées** (leur sélection contient au moins un comparable sans terrain — les seules où la variante
change l'estimation). Mesure **déterministe** sur toute la cohorte (aucun sous-échantillonnage).

## Résultat global (sujets concernés) — écart médian | biais signé

Biais signé = médiane de (estimé / réel − 1). **Négatif = sous-estimation, positif = surestimation.**

| Variante | écart médian | biais médian | biais **moyen** |
|---|---|---|---|
| **A. plein poids (actuel)** | **24,65 %** | −2,05 % | **+7,63 %** |
| B. pénalisé | 24,67 % (**+0,02**) | −1,66 % | +9,10 % (**+1,47**) |
| C. écarté si ≥ 8 | 24,98 % (**+0,33**) | +0,00 % | +10,64 % (**+3,01**) |

Lecture : les comparables sans terrain sont un peu **moins chers au m²** (−7 %, mesuré en recette 2), donc
les garder à plein poids tire l'estimation vers le bas → **sous-estimation médiane de 2 %**. Les
pénaliser / les écarter **corrige cette sous-estimation médiane** (biais médian → −1,7 % / 0,0 %) **MAIS** :
- l'**écart médian se dégrade** (24,65 → 24,67 / 24,98 %), et
- le **biais moyen empire** (+7,63 → +9,10 / +10,64 %) : retirer les comparables bas accentue la
  **sur-estimation dans la queue** (quelques biens poussés trop haut).

## Par commune (sujets concernés, communes ≥ 20) — écart médian / biais signé médian

```
  insee      n     A. plein poids       B. pénalisé          C. écarté si ≥8
                   écart   biais        écart   biais        écart   biais
  97422    169      25.2   -0.8          25.9   -0.8          25.9   +0.0    
  97415    151      19.1   +0.7          20.1   +1.6          23.4   +4.5    
  97411    137      29.4   +2.3          29.1   +2.3          29.9   +9.3    
  97416    121      20.4   -6.2          19.9   -6.7          19.5   -2.9    
  97414     87      20.6   -5.3          19.0   -5.3          18.5   -4.6    
  97408     54      22.1   -3.7          22.5   -2.3          23.9   -0.2    
  97409     54      26.3  -12.5          26.7  -13.6          26.5  -12.1    
  97412     47      31.1  -12.2          33.1  -10.2          34.1  -10.2    
  97418     44      27.6   +6.2          26.3   +6.2          25.8  +11.4    
  97405     44      21.9  +10.0          21.9  +10.7          21.9  +10.7    
  97413     39      27.1   +1.5          27.8   +0.6          27.8   -1.8    
  97404     28      27.3  -18.2          29.3  -20.4          36.0  -27.6    
  97407     28      26.5  -15.0          24.7  -15.1          23.5  -11.2    
  97403     26      47.7  +14.2          46.7  +14.2          38.8  +14.2    
  97401     25      28.8   +5.7          28.3   +5.7          28.8   +5.7    
  97420     24      29.1   -4.4          31.9   -4.4          32.6   +3.9    
  97410     22      21.0   -4.5          21.0   -0.1          18.2   +3.2    

```

Par commune, l'effet sur l'écart est **mitigé** : pénaliser/écarter aide quelques communes (97416, 97414,
97407…) mais **dégrade plusieurs des plus grosses** (97422, 97415, 97412, 97404, 97420) — d'où un écart
global qui ne baisse pas.

## Décision — ON NE CHANGE RIEN

La règle : appliquer la meilleure variante **seulement si elle réduit l'écart OU le biais sans dégrader
l'autre**. Or :

- **B (pénalisé)** réduit le biais médian (−0,39 pt en valeur absolue) **mais dégrade l'écart médian
  (+0,02)** *et* le biais moyen (+1,47) → **ne qualifie pas**.
- **C (écarté)** annule le biais médian (−2,05) **mais dégrade l'écart médian (+0,33)** *et* le biais
  moyen (+3,01) → **ne qualifie pas**.

Aucune variante ne réduit une métrique sans en dégrader une autre. Le **plein poids (actuel)** a déjà
l'**écart médian le plus bas** et le **biais MOYEN le plus faible** ; les alternatives n'achètent une
moindre sous-estimation médiane qu'au prix d'un écart plus large et d'une sur-estimation moyenne accrue.

→ **Le traitement actuel est conservé, inchangé.** Aucune modification du moteur (`estimer3.py`). Seuls la
mesure et ce compte-rendu sont ajoutés.

## Fichiers

| Fichier | Rôle |
|---|---|
| `docs/audit-2026-11/estimer-4/mesure_terrain.py` | mesure no-leak des 3 variantes (écart médian + biais signé, global + par commune) |
| `docs/audit-2026-11/estimer-4/COMPTE-RENDU.md` | ce rapport |

**Rejouer** : `PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg:///labuse ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/estimer-4/mesure_terrain.py`
