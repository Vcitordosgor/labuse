# M26-A-bis — Spec : enrichir le payload `restituees` (mandat back court)

**Origine** : GO M26-B, arbitrage n°2. La carte lead de la maquette B4 montre l'article
PLU invoqué, la façade, les comparables DVF et les checks risques — la substance de la
preuve. Ces données existent déjà en amont des moteurs M26-A ; il s'agit de les PORTER
dans le payload de l'assemblage, rien de plus. Spec seulement — aucune implémentation
au M26-B (front seul).

## Périmètre

Un seul point de sortie : `_recap()` dans `src/labuse/copilote/moteurs.py` (clé
`restituees`, mission `instruire`). Aucun nouveau moteur, aucun nouvel appel réseau,
aucun recalcul — chaque champ est déjà calculé par une étape existante et doit être
recopié depuis le dossier du run.

## Champs à ajouter à chaque élément de `restituees`

| Champ | Source amont (déjà calculée) | Étiquette portée |
|---|---|---|
| `article_faisabilite` | moteur faisabilité — l'article PLU invoqué pour la SDP résiduelle (ex. « UB10 · R+2 ») ; `null` en règle générique (jamais un libellé d'article inventé) | celle de l'étape faisabilité |
| `facade_voirie_m` | géométrie parcelle (filtre géométrique) | sourcé |
| `n_comparables_dvf` | moteur marche_dvf — nombre de comparables retenus pour le prix probable | estimé |
| `checks_risques` | moteur risques — liste `{couche, statut}` par couche examinée : `hors` / `dans` / `non_verifie` (donnée absente ≠ vérifié — distinction imposée par la boussole) | sourcé, `absent` par couche manquante |

## Règles

1. **Aucun recalcul à l'assemblage** : si une valeur n'est pas dans le dossier au moment
   de l'assemblage, elle sort `null` + étiquette `absent` — jamais recalculée, jamais
   devinée.
2. **Boussole** : `filtrer_payload` s'applique tel quel (aucune identité de personne
   physique ne transite par ces champs — vérifier `checks_risques`).
3. **Rétro-compatibilité** : champs ADDITIFS uniquement. Le front M26-B affiche déjà le
   payload actuel ; il affichera ces champs quand ils existeront, sans breaking change.
4. **Taille d'événement** : + ~200 octets × 20 restituées — négligeable, à confirmer au
   mandat (l'event log est append-only, la ligne assemblage grossit).

## Tests attendus (au mandat, pas ici)

- `article_faisabilite` null sur commune non calibrée (verrou : jamais un article en
  règle générique).
- `checks_risques` distingue `hors` de `non_verifie` (une couche absente n'est pas un
  feu vert).
- Golden 116/116 inchangé (le recap s'enrichit, aucun chiffre existant ne bouge).
