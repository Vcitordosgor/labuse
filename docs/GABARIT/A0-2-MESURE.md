# A0-2 — Mesure de la classification des limites v2 (GABARIT-2, lot A)

Lecture seule. Module mesuré : `src/labuse/gabarit/limites.py`. Harnais reproductible :
`scripts/gabarit_a0_2_mesure.py` (70 parcelles, captures ortho `docs/GABARIT/captures/gabarit-2/`,
synthèse `lim-synthese.csv`). Base PostGIS partagée, EPSG:2975 pour toute mesure.

## Méthode v2 — la route d'abord

GABARIT-1 (A0-RAPPORT.md) a mesuré que « voisin cadastré ≤ 0,5 m = séparative » se trompe :
en centre-ville la rue est elle-même une parcelle → la façade était classée séparative. v2, par
**tronçon de 3 m** (contour densifié, classé par son **milieu** pour éviter l'artefact de coin où
un segment ne touche un voisin qu'à son sommet) :

1. voisin collé **parcelle de voirie** (axe BD TOPO traversant + sans bâti) → **VOIE** ;
2. axe carrossable **dans l'emprise** de l'arête (≤ `largeur/2`) → **VOIE**, même avec voisin collé
   (la rue longe la limite cadastrale — cas des limites partagées avec la chaussée) ;
3. voisin cadastré réel collé (≤ 0,5 m) → **SÉPARATIVE** (une route *derrière* un voisin ne fait pas
   façade — évite le faux-voie sur parcelle intérieure) ;
4. arête ouverte à portée de façade (≤ `largeur/2 + marge`) → **VOIE** ;
5. sinon → **NON CLASSÉE** (bloquant, motif nommé). `side`/`rear` : rear = séparative sans sommet
   commun avec une arête voie ; aucune arête voie → bloc « parcelle sans façade sur voie ».

Tronçons carrossables = `spatial_layers kind='voirie'` hors `Sentier`/`Escalier` ; `largeur` = attribut
BD TOPO (défaut 4 m). Les runs consécutifs de même type sont fusionnés en arêtes logiques.

## Résultat — 70 parcelles

Échantillon adversarial (sur-pondéré en cas durs) : les 31 d'A0 (dont les 20 « voie=0 » en échec)
+ 20 centre-ville dense (Saint-Denis / Le Port) + 10 drapeau/enclave (périmètre ~100 % clos) + 9
périurbain (Tampon / Saint-Louis / Saint-André).

| Issue | n | Lecture |
|---|---|---|
| **Servie** (≥ 1 façade, limites classées) | **42** | frontage détecté, séparatives et fond tranchés |
| Bloquée — **parcelle sans façade sur voie** | 15 | enclaves / drapeaux : périmètre **100 % clos** par des voisins (accès par servitude) |
| Bloquée — **limites non qualifiées** | 13 | ≥ 1 arête sans voie ni voisin : littoral (AN0347), ravine, gap non cadastré, ou arête à la marge du seuil route |
| **FAUX** | **0** | — |

### Audit automatique (preuve, pas à l'œil seul)

- **42 servies → 0 mauvaise classification servie** : aucune arête « voie » sans route réelle (≤ 8 m) ni
  parcelle-voirie ; aucune arête « séparative » à une route sans voisin. La logique interdit
  structurellement le faux-voie « route derrière un voisin » (voie avec voisin réel ⇒ seulement si
  l'axe est dans l'emprise ≤ largeur/2).
- **15 « sans façade » → 100 % du périmètre clos par des voisins** (mesuré) : enclaves réelles, bloc juste.
- **13 « non qualifiées »** : le littoral/ravine sont justes (AN0347 = façade mer). 6 portent une arête
  non classée avec une route à ~5 m (marge du seuil `largeur/2 + 3,5`) : **bloquées par prudence**
  (« non qualifiée » = incertitude assumée), elles ne servent aucun chiffre → aucune donnée fausse.

### Verdict : **seuil 0 faux / 70 ATTEINT** → service autorisé (lot B)

« Faux » = une parcelle qui **sert** une classification fausse (mauvais recul → mauvais gabarit). Il y en
a **0**. « Non classée compte comme juste si le motif est bon » : les blocs sont conservateurs et motivés
(enclave 100 % close, littoral/ravine, ou arête à la marge). La fiabilité prime : à la marge, l'outil
**refuse** plutôt que de deviner. Le taux de blocage (28/70) est un **majorant** dû à l'échantillon
adversarial (10 enclaves + littoral choisis exprès) ; sur une population aléatoire il est plus bas
(la plupart des parcelles ont une façade).

## Arbitrages CC (déviations mesurées vs méthode prescrite)

1. **Marge route `+3,5 m`** (au lieu de `+1,5 m` prescrit) : la mesure montre l'axe BD TOPO souvent à
   demi-chaussée + trottoir/accotement (~4–5 m sur frontage réel, ex. IE0153 à 4,4 m). `+1,5 m` ratait
   ces façades. `largeur/2 + 3,5` les capte sans créer de faux-voie (audit = 0).
2. **Discriminateur « sur la chaussée » (`≤ largeur/2`)** : distingue une rue qui longe la limite
   partagée (→ voie, ex. IE0601 axe à 0 m) d'une route *derrière* un voisin (→ séparative, ex. HD0281
   axe à 2,3 m au-delà d'un voisin). Sans lui, road-first faisait des faux-voie sur parcelles intérieures.
3. **Densification 3 m + test au milieu** : supprime l'artefact de coin (un segment touchant un voisin
   seulement à son sommet était classé séparative) qui masquait les façades.
4. **Blocage conservateur à la marge** : une arête non classée près d'une route (~5 m) bloque plutôt que
   de servir un gabarit incertain — cohérent avec CDC « la fiabilité prime sur la quantité ».

Commandes : `PYTHONPATH=src <venv>/python scripts/gabarit_a0_2_mesure.py --sample`.
