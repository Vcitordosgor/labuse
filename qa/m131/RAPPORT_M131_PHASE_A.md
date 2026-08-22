# M131 — Phase A : lecture des règlements (lecture seule, aucune gravure)

Branche `feat/m131-dette-hauteur` @ `70937818` (garde-fou OK). **Aucun YAML écrit,
aucun commit de données.** Livrable = extraits sourcés, pour arbitrage de Vic.

Source lue : `97416_reglement_20240625.pdf` (règlement Saint-Pierre, millésime
25/06/2024), présent dans le checkout d'intégration (`~/Desktop/labuse/reports/
m6-audit/reglements/`), lu en **lecture seule**.

---

## A.1 — Us (Saint-Pierre, 25/06/2024) → CANDIDAT GRAVURE

**Extrait verbatim** (`ARTICLE Us3 : VOLUMÉTRIE ET IMPLANTATION DES
CONSTRUCTIONS`, en-tête **p.133** ; CHAPITRE 2) :

> **5/ Hauteur**
> **Règle générale**
> La hauteur maximale des constructions nouvelles est fixée à **6 m à l'égout du
> toit ou au sommet de l'acrotère et à 11 m au faîtage.**  *(p.134)*

**Contrôles :**

| Contrôle | Résultat |
|---|---|
| Les **deux** valeurs (égout ET faîtage) ? | **Oui** — égout 6 m · faîtage 11 m. |
| Valeur **générale** ou conditionnée (sous-secteur / occupation) ? | **Générale** — le texte porte l'intitulé « **Règle générale** » ; s'applique aux « constructions nouvelles » (donc au logement, à la réouverture). Aucun sous-secteur. |
| Article de **hauteur** ou piège ouverture/phasage/capacité ? | Article de **hauteur** — `ARTICLE Us3 … 5/ Hauteur`, CHAPITRE 2 (VOLUMÉTRIE). **Pas** le piège `Art. 2.2.3`. |

**Proposition de gravure (Phase B, sur go de Vic)** :
- `he_m: 6`, `hf_m: 11`
- source : **`Art. Us3, § 5 (« 5/ Hauteur — Règle générale »), p.134`** (règlement
  Saint-Pierre 25/06/2024).

**Correction de citation** : le commentaire M130-12 annonçait « chapitre 2,
**p.130** ». La p.130 est la table des destinations (`ARTICLE Us1`, CHAPITRE 1) ;
la hauteur est **`Art. Us3, p.134`** (CHAPITRE 2). Valeurs 6/11 confirmées, page
corrigée.

**Doctrine acquise rappelée** : cette gravure ne change PAS la capacité — Us reste
gelée (`constructible_neuf=False`), la ligne SDP continuera d'afficher « aucune ».
Hauteur autorisée ≠ constructibilité. Les deux coexisteront (résultat attendu).

---

## A.2 — 2AU du Tampon (11/08/2023) → LECTURE IMPOSSIBLE (document absent)

**Le document règlement du Tampon `97422_reglement_20230811.pdf` n'est présent
NULLE PART** dans les checkouts accessibles (`~/Desktop/labuse-pdf` : pas de
`data/reglements/` ; `~/Desktop/labuse` : aucun fichier `97422*reglement*`). Seul
le règlement Saint-Pierre (97416) est disponible.

Conséquence, dans le respect strict de la doctrine (« un constat d'absence doit
être aussi sourcé qu'une présence — panne ≠ absence ») :

- **Je ne peux ni graver une hauteur, ni établir un constat d'absence sourcé**
  pour `2AUa`–`2AUe`. Les deux exigent le texte, que je n'ai pas lu.
- **`2AU*` reste `non renseignée au PLU calibré`** (état honnête M130-12), et la
  **lecture A.2 attend le document** `97422_reglement_20230811.pdf`.

Ce qui reste établi et ne compte PAS comme réponse : `Art. 2.2.3, p.84` est
l'article d'**ouverture/phasage** (établi M130-12) ; le `4 m` était le repli
`zones_au_st`, supprimé.

**Demande** : déposer `97422_reglement_20230811.pdf` (ou son extrait texte) dans
le checkout, ou m'indiquer où le lire — alors A.2 sera traité de la même façon
qu'A.1 (extrait verbatim, ou constat d'absence sourcé : chapitre + plage de pages
parcourues).

---

## STOP — arbitrage de Vic

Fin de Phase A. **Je n'enchaîne pas sur la gravure (B).** À trancher, zone par
zone :
- **Us** : graver `he 6 / hf 11` sur `Art. Us3 §5, p.134` ? (candidat validé, 3
  contrôles passés).
- **2AU** : en attente du document du Tampon.

La Phase C (renvois Uazi/Ucm — affichage seul) et la vérification au rendu seront
faites **avec** la Phase B (leur contrôle est couplé : « après B et C »).
