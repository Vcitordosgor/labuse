# DETTE — Hauteur PLU : zones « non renseignée » et renvois

**M130-12 (rattrapage).** Consigne nommément ce qui, à l'issue du correctif, sort
« hauteur non renseignée au PLU calibré » — jamais un trou silencieux — et les
valeurs réelles connues mais non gravées.

---

## 1. Le mécanisme `zones_au_st` fabriquait une hauteur (corrigé)

**Défaut (corrigé `plu_rules.py:204`)** : les zones portées par `zones_au_st`
(secteurs de transition / gel : `AU*st`, `2AU*`, `Us`, `AU0*`) recevaient
`hf_m = float(st.get("hauteur_max_m", 4))` — soit **4 m codé en dur** quand le
YAML ne définit pas `hauteur_max_m`. **Aucune** commune ne le définit → le 4 m
n'était **jamais** une règle lue au règlement, mais un repli du schéma, que le
YAML Saint-Pierre déclare lui-même **INEXACTE** (« l'étiquette moteur … H max 4 m
est INEXACTE pour ces zones »). C'est la valeur-signature du mécanisme.

**Correctif** : absence de `hauteur_max_m` = absence de règle → `hf_m = None`
(remonté « non renseignée au PLU calibré »). La **capacité** (`constructible_neuf
= False`, zéro construction neuve) reste EXACTE. Une hauteur n'est servie que si
une commune LIT et grave `hauteur_max_m` (avec article/page) au règlement.

### Rayon (mécanisme, toutes communes) — observable sur P1–P4

| Commune | Zone | Millésime | Parcelles servies 4 m (avant) | Après |
|---|---|---|---|---|
| Le Tampon (97422) | `2AUc` | 11/08/2023 | 2 | non renseignée |
| Le Tampon (97422) | `2AUd` | 11/08/2023 | 2 | non renseignée |
| Le Tampon (97422) | `2AUe` | 11/08/2023 | 5 | non renseignée |
| Le Tampon (97422) | `2AUb` | 11/08/2023 | 0 (part non dominante — DH0771 ~ 6 %) | non renseignée |
| Saint-Pierre (97416) | `Us` | 25/06/2024 | 1 | non renseignée |

Le mécanisme couvre aussi `2AUa` (Le Tampon) et `AU01/AU02/AU03/AU0c-1`
(Saint-Pierre), absents des shortlists de QA mais traités identiquement.

### Valeurs RÉELLES connues, non gravées (→ mandat data, rejoint M130-6 F.2)

Ces zones **portent une hauteur** au règlement, à graver dans une entrée propre
`hauteur_max_m: N` (source article/page) séparée du mécanisme de gel :

- **`Us` (Saint-Pierre, 25/06/2024)** : **hé 6 / hf 11**, règlement chapitre 2,
  **p.130** (cf. commentaire YAML : « Le chapitre 2 fixe pourtant hé 6/hf 11 …
  règles gravables le jour où la zone rouvre »). Valeur réelle **connue**.
- **`2AU*` (Le Tampon, 11/08/2023)** : hauteur d'annexes / de gel **à instruire**
  au règlement AUindicée (l'`Art. 2.2.3, p.84` servi jusqu'ici est l'article
  d'**ouverture / phasage**, pas de hauteur). Valeur réelle **à lire**.
- **`AU0*` (Saint-Pierre)** : construction interdite ; hauteur à instruire de
  même si une règle d'annexes existe.

---

## 2. Zones A / N — hauteur non extraite (inchangé)

`config/plu_saint_pierre.yaml` **ne calibre que les zones constructibles U / AU**.
Les zones **A / N** n'y sont pas → `resolve_zone` retombe sur l'estimation
générique (he = hf = None) → « non renseignée au PLU calibré ». Sur P3 :
Saint-Pierre `A` (8 lignes) · `N` (1 ligne).

**On ne sait pas** si le règlement chiffre une hauteur A / N : le règlement a bien
des chapitres A et N (`config/plu_saint_pierre.yaml`, commentaire : « N, Nr, Nc,
Ncu, Nci, Np, Npnr, Nge (chap. p.212-221) » ; A « chap. p.202-211 ») mais leur
hauteur **n'est pas extraite**. Panne ≠ absence : « non renseignée au PLU
calibré » est l'état honnête d'une donnée absente de notre calibrage — pas une
affirmation que le règlement ne porte pas de règle. Pour lever : lire les chap.
A / N et graver (ou marquer « non réglementée au règlement, chap. X p.Y »,
fait sourcé).

---

## 3. Dette COSMÉTIQUE — renvois servis sans mention « via renvoi »

Un motif = un traitement : certains renvois de hauteur affichent leur mécanisme,
d'autres non. Cosmétique d'affichage, **aucune valeur ni source fausse**, hors
périmètre M130-12.

- **`Uazi` (Saint-Pierre)** → sert `Art. Ua3.5, p.177 (règle générale)` — renvoi au
  règlement `Ua` **sans** libellé « via renvoi ».
- **`Ucm` (Le Tampon)** → sert `Art. Uc10.2, p.46 (indice « m »)` — renvoi à `Uc`
  **sans** « via renvoi ».

Alors que `1AUb` affiche « … **via renvoi** (ZONE AUindicée, p.83) » et `Uav` porte
sa **citation de secteur**. Harmoniser l'annotation renvoi/secteur sur `Uazi` /
`Ucm` (affichage seul).
