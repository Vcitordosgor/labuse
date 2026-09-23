# GABARIT-6 — correctif de prémisse : 97417 est un CODE POSTAL, pas l'INSEE

Date : 23/09/2026 · Enquête (lecture seule, **aucun code corrigé**).

## Ce qui était faux dans GABARIT-6

Le rapport GABARIT-6 affirmait « 97417 = Saint-Philippe, RNU → 3 Chemin de la Citerne non servable,
hors mandat ». **Faux.** `97417` est le **code postal de La Montagne** (quartier de **Saint-Denis**,
INSEE **97411**), qui a un **PLU calibré**.

## La collision de codes (réelle, dans les données)

`97417` existe **deux fois** :

| `97417` interprété comme… | Résout vers | Preuve |
|---|---|---|
| **code postal** | INSEE **97411 — Saint-Denis** (La Montagne) | `adresses.code_postal='97417'` → `insee='97411'` (seul) |
| **code INSEE** | **97417 — Saint-Philippe** (4 162 parcelles) | `parcels substr(idu,1,5)='97417'` = Saint-Philippe |

## Où la chaîne a confondu — et où elle NE confond PAS

**L'application ne confond pas.** Le chemin réel résout correctement :

- `/adresses/autocomplete?q=3 chemin de la citerne` (`app.py:2309`) matche le **texte « numéro voie »**
  (pas de filtre insee/postal) et renvoie **en tête** :
  `3 Chemin de la Citerne | Saint-Denis | 97417 | 97411000BZ1065`.
- La suggestion porte déjà l'**IDU** `97411000BZ1065` → la fiche/le builder travaillent sur
  l'**INSEE 97411** (l'IDU contient l'INSEE, jamais le code postal). `parcels.commune` = « Saint-Denis ».
- `build_gabarit_input('97411000BZ1065')` résout la zone via la commune « Saint-Denis » → **PLU calibré**
  (pas de « zone PLU indéterminée »). La référence courte du placeholder ParcelInput est d'ailleurs
  « ex. BZ1065 » — la parcelle même.

**La confusion était dans l'enquête GABARIT-6 (agent), pas dans le code.** Pour trouver « 3 Chemin de
la Citerne », j'avais requêté `SELECT … FROM adresses WHERE insee='97417'` — en traitant le code postal
du mandat comme un INSEE. Comme `97417` est *aussi* l'INSEE de Saint-Philippe, la requête a renvoyé les
adresses « Chemin de la 2e Citerne » de Saint-Philippe, d'où la fausse conclusion « RNU / hors mandat ».
La recette GABARIT-6 a donc capturé la **mauvaise parcelle** (`97417000BH0267`, Saint-Philippe) sous le
label « 3 Chemin de la Citerne ».

## La vraie parcelle et son vrai blocage

**`97411000BZ1065`** — 3 Chemin de la Citerne, Saint-Denis, 1 625 m².

`build_gabarit_input` la **bloque** (`status=incomplete`) sur :

> Limites de la parcelle non qualifiées (voie / limite séparative) — **arête résiduelle < 1 m, non classable**

Arêtes classées : `rear 10.27 · side 2.57 · voie 7.72 · **nonclass 2.26** · voie 93.02 · side 2.85 ·
rear 92.62`. L'arête bloquante est **entre deux arêtes voie**.

### Pourquoi Lot A ne la débloque pas (et pourquoi le motif ment)

L'arête « nonclass » de **2,26 m** est un **run de quatre micro-chunks consécutifs** issus de la
densification `_chunks` (contour cadastral dense à cet endroit) :

```
NONCLASS chunk L=0.33  -> COURTE(<1m)
NONCLASS chunk L=0.64  -> COURTE(<1m)
NONCLASS chunk L=0.63  -> COURTE(<1m)
NONCLASS chunk L=0.66  -> COURTE(<1m)      total = 2.26 m   (périmètre 211,3 m ; 2 % = 4,23 m)
```

Deux effets se combinent :

1. **Motif trompeur.** À la fusion, `run_motif = run_motif or m` hérite du motif du **premier** chunk
   (0,33 m → `MOTIF_ARETE_COURTE` « arête résiduelle < 1 m »). L'arête fusionnée fait pourtant **2,26 m**.
   C'est ce libellé « < 1 m » que le mandat a repris (« une arête < 1 m bloque »), alors que l'arête
   réelle mesure 2,26 m.
2. **Garde Lot A inopérante.** `_attach_residual_microedges` teste la **longueur fusionnée** :
   `2.26 ≥ MIN_EDGE_M (1.0)` → **non rattachée** (`residual_attached = 0`). La condition « < 2 % » est
   pourtant remplie (2,26 < 4,23), mais pas la condition « < 1 m ».

Autrement dit : c'est bien un artefact de numérisation (4 sommets serrés dans une ré-entrance de la
façade sur voie, entre deux tronçons voie), mais Lot A — écrit sur la **longueur fusionnée < 1 m** — ne
le capte pas. La prémisse « < 1 m » venait du motif erroné, pas de la géométrie.

## Conséquences (à trancher — rien corrigé)

- Le rapport GABARIT-6 et sa recette sont à amender (mauvaise commune / mauvaise parcelle).
- Le vrai correctif du cas « 3 Chemin de la Citerne » n'est PAS le Lot A tel qu'écrit. Pistes (non
  implémentées) : (a) corriger le motif hérité à la fusion pour qu'un run porte sa **vraie** longueur et
  le bon motif (`NON_QUALIFIEE` dès que le run ≥ 1 m) ; (b) appliquer le test d'artefact au **run**
  (tous les chunks < 1 m ET run < 2 % du périmètre → rattachement), ce qui débloquerait BZ1065
  (2,26 m < 4,23 m, chunks tous < 1 m) — à valider par une remesure des 170 + audit 0 faux.
- Aucun garde-fou applicatif « code postal ≠ INSEE » n'est en cause ; la collision 97417 est une
  particularité des données (un code postal égal à un INSEE d'une autre commune).
