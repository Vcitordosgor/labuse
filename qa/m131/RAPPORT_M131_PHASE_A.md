# M131 — Phase A : lecture des règlements (lecture seule, aucune gravure)

Branche `feat/m131-dette-hauteur`. **Aucun YAML écrit, aucun code touché**
(`git diff` sur `src/` et `config/` = vide). Livrable = extraits sourcés, pour
arbitrage de Vic avant toute gravure.

Sources lues en place (lecture seule, non copiées dans le repo) :
- Saint-Pierre : `~/Desktop/labuse/reports/m6-audit/reglements/97416_reglement_20240625.pdf`
- Le Tampon : `~/Downloads/97422_PLU_20230811/Pieces_ecrites/3_Reglement/97422_reglement_20230811.pdf`

---

## A.1 — Us (Saint-Pierre, 25/06/2024) — contrôle des dérogations

`ARTICLE Us3 : VOLUMÉTRIE…` (en-tête p.133), CHAPITRE 2, **§ 5/ Hauteur** (p.134-135).

**Règle générale (p.134), verbatim :**
> **Règle générale** — « La hauteur maximale des constructions nouvelles est fixée
> à **6 m à l'égout du toit ou au sommet de l'acrotère et à 11 m au faîtage.** »

**Dispositions particulières (p.135), verbatim — ce que « règle générale » supposait :**
> - *Limites séparatives* : « … la hauteur des constructions nouvelles n'excède
>   pas **4 m** … gabarit angle 100 % sur 3 m … Au-delà de cette bande de 3 m …
>   **la règle générale s'applique**. » → prospect (taper de bord), universel ;
>   au-delà de 3 m, on revient à 6/11.
> - *Équipements publics ou d'intérêt collectif* : « … limitée à **8 m à l'égout
>   … et à 13 m au faîtage.** » → **type d'occupation ≠ logement** (valeur plus
>   haute, autre destination).
> - *PPRN* : hauteurs **augmentées** de la surélévation exigée (bonus risque).
> - *Surtoiture / toiture végétalisée* : **+50 cm** (bonus).
> - *Terrains en pente* : **+1,5 m** en partie aval (bonus).

**Verdict du contrôle :**

| Question du mandat | Réponse sourcée |
|---|---|
| Clause de **secteur / sous-zone** qui déroge au 6/11 (le piège UfCa) ? | **NON.** Aucun « Dans le secteur Us-… limiter à … ». Contraste : `Uf3.5` (p.119) porte, lui, `Dans le secteur UfCa … 6 m égout / 7,5 m faîtage`. Us n'a **pas** d'équivalent. |
| Clause de **type d'occupation** qui déroge ? | **OUI, une seule** : équipements publics = 8/13. C'est une **autre destination**, pas le logement. |

**Précédent qui tranche la question** : `Uf3.5` a **exactement** la même structure
que `Us3 §5` — règle générale 6/11, un secteur (UfCa) 6/7,5, équipements publics
8/13, limites séparatives 4 m, bonus pente. Le YAML a gravé **`Uf = 6/11`
(logement)**, en notant le secteur UfCa, et en **ignorant** l'équipements-publics
8/13. Convention établie : **on grave la règle générale du logement.**

**Recommandation** : `Us` est un cas **plus simple** qu'Uf (aucun sous-secteur) →
graver `he_m: 6, hf_m: 11`, source `Art. Us3 §5 « Hauteur — Règle générale »,
p.134`. La seule « dérogation » (équipements publics 8/13) est une autre
destination, non gravée pour le logement — comme partout ailleurs.

**Je m'arrête néanmoins avant d'écrire** (le mandat : « dérogation trouvée →
stop, remonte-la »). J'ai trouvé des dispositions particulières : je les remonte,
tu tranches. Mon avis : gravure `6/11` conforme à la convention Uf.

---

## A.2 — 2AU du Tampon (11/08/2023) — le règlement EXISTE et porte une hauteur (par renvoi)

Document lu en place (`~/Downloads/97422_PLU_…`). La `ZONE AUindicée` (chap. unique,
p.83-87) porte l'article de hauteur :

**`ARTICLE AUindicée 10 - HAUTEUR MAXIMALE DES CONSTRUCTIONS` (p.86), verbatim :**
> « **Se reporter au règlement de la zone U indiquée en indice** ainsi qu'aux
> orientations d'aménagement et de programmation lorsqu'elles existent. Pour la
> zone AUto, il convient de se reporter au règlement de la zone Ucto. »

Donc **les 2AU ont une règle de hauteur — PAR RENVOI**, exactement comme les 1AU.
Ce n'est **pas** « non renseignée » : le `4 m` supprimé en M130-12 était le repli
`zones_au_st` ; la **vraie** règle est ce renvoi. Le piège `Art. 2.2.3` (=
`ARTICLE AUindicée 2` / phasage : « ouverture … dès lors que l'aménagement de
l'ensemble des 1AUindicée … », p.84) est bien distinct — c'est de l'ouverture, pas
de la hauteur.

**Hauteur par renvoi, pour chaque 2AU (source : `Art. AUindicée 10, p.86` →
article U-indice) :**

| Zone | Indice U | égout / faîtage | Article renvoyé |
|---|---|---|---|
| `2AUa` | Ua | 21 / 25 | Art. Ua10.2, p.16 |
| `2AUb` | Ub | 13 / 17 | Art. Ub10.2, p.31 |
| `2AUc` | Uc | 9 / 13 | Art. Uc10.2, p.46 |
| `2AUd` | Ud | 7 / 11 | Art. Ud10.2, p.61 |
| `2AUe` | Ue | 12 / — (« limitée à 12 m à l'égout » ; faîtage non précisé) | Art. Ue10.2, p.75-76 |

Aucune dérogation de secteur ne s'applique aux indices de base (a/b/c/d/e ; le
renvoi vise `Ua`/`Ub`/… de base, pas les secteurs type `Uav`).

**Subtilité de gravure (Phase B, à trancher)** : les 2AU sont AUSSI dans
`zones_au_st` (capacité = construction neuve non autorisée, `constructible_neuf
=False`). Graver leur hauteur par renvoi doit **conserver le gel** (ne pas
réactiver le repli 4 m, ne pas rendre la zone constructible). Cela suppose une
entrée `2AU*` propre portant `he_m/hf_m` **et** `constructible_neuf=False`,
distincte du bloc `zones_au_st` — sans réintroduire de défaut dans `plu_rules.py`.

---

## STOP — remontée, arbitrage avant gravure

**Rien n'est gravé.** À trancher :
1. **Us** : graver `6/11` (`Art. Us3 §5, p.134`) — recommandé, convention Uf. La
   dérogation équipements-publics 8/13 est une autre destination (non gravée).
2. **2AU** (a→e) : graver la hauteur **par renvoi** (`AUindicée 10, p.86` →
   U-indice, valeurs ci-dessus), en conservant le gel — ou laisser « non
   renseignée » ? Le règlement, lui, **porte** la règle.

Phase C (renvois Uazi/Ucm) et la vérification au rendu se feront **avec** la
gravure (Phase B), sur ton go. `git diff plu_rules.py` restera vide.
