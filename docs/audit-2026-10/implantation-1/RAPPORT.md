# IMPLANTATION-1 — Rapport

Premier moteur d'implantation collectif. **Un terrain, une zone réglementaire, un scénario.**
Terrain : **L'Étang-Salé, AW 99 + 451 + 624 + 625**, assiette fusionnée, zone **UA**, collectif
**logements seuls** (aucun commerce), **stationnement aérien**, terrain libéré.

Livrables de ce dossier : `plan.png` (rendu depuis la géométrie), `scenario.json` (archive
rejouable), `A0-EXISTANT.md` (inventaire), ce rapport. Référence de forme :
`maquette-etude-faisabilite-v3.html` (forme cible, pas des chiffres à reproduire).

> Nature du document : pré-faisabilité automatisée. Ni étude d'architecte, ni preuve de
> conformité, ni dossier de permis. Le mot « conforme » n'apparaît pas.

---

## 1. Verdict

| | |
|---|---|
| **Scénario retenu** | deux barres end-to-end, **R+3** |
| **Capacité** | **16 logements** (T2 ×12 · T3 ×4) |
| **Stationnement** | **18 places aériennes** dessinées = 18 imposées |
| **Statut de l'étude** | **exploitable en pré-faisabilité** |
| **Contrôles automatisés** | 5 Réussi · 0 Échoué · 4 Non effectué · 1 Non applicable |

Le moteur a cherché parmi 135 candidats (3 formes × 3 hauteurs × 15 longueurs de barre) et gardé
le **meilleur candidat qui passe tous les contrôles durs** (objectif « équilibre » = max logements
puis max SHAB, départage stable). **24 à 34 candidats** sont faisables selon la forme ; le retenu
maximise les logements. La contrainte qui plafonne la capacité n'est ni l'emprise ni la hauteur ni
la perméabilité : c'est **le stationnement aérien** (voir §5).

Déterministe : deux exécutions produisent une géométrie au hash identique.

## 2. Terrain et règles (détail dans `A0-EXISTANT.md`)

- Assiette = `ST_Union(geom_2975)` des 4 parcelles → **un seul polygone**. Contenance cadastrale
  **1 746 m²** (501 + 586 + 274 + 385 ; fait foi), aire du dessin 1 744,2 m².
- Zone d'implantation (après reculs) = **1 155,3 m²**. Façade sur voie : 27,7 m sur l'Avenue
  Raymond Barre (BD TOPO). Aucune contrainte PPR / ER / EBC / SUP sur le terrain.
- Règles UA **validée avec citation** (7/8) : hauteur 12 m égout / 15 m faîtage, CES 70 %,
  recul voie 4 m, recul séparatives 3 m, perméabilité (pleine terre) 30 %, mixité (seuil 1 000 m²
  SDP / quota 20 %). Le **barème stationnement** a été validé au LOT A (UA 2.7.3, p. 22).

**Zone d'implantation — robustesse.** La zone est construite en appliquant le recul voie (4 m) aux
arêtes « voie » et le recul séparatif (3 m) à **toutes** les autres arêtes (side / rear / nonclass).
Comme toute arête non-voie reçoit le même recul 3 m, la zone est **insensible** à la façon dont le
classifieur (conçu pour la parcelle unique) répartit les arêtes internes de l'union entre « rear » et
« nonclass » — la réserve signalée en A0 n'a aucun effet sur l'enveloppe constructible.

## 3. D'où vient chaque m² et chaque logement

Tout est **tiré de la géométrie dessinée** (jamais l'inverse). Conventions « Estimé » :
profondeur 13 m, coursive 1,4 m, noyau 3,5 m, étage 3 m, plancher→habitable 0,80, place 2,5 × 5 m,
allée 5 m (cf. `config/implantation_conventions.yaml`).

### Bâtiment
- Deux barres de **13 m** de profondeur, le long de la grande limite opposée à la voie :
  **B1 = 7,8 × 13 = 101,5 m²**, **B2 = 17,7 × 13 = 230,4 m²**. Emprise au sol = union = **331,9 m²**.
- Chaque barre : une coursive extérieure (1,4 m) côté voie, un noyau (3,5 m), le reste en modules.
- **Module = largeur × (13 − 1,4) = largeur × 11,6 m.** La largeur se déduit de la surface moyenne :
  - **T2** : 50 / 11,6 = **4,31 m** → 50,0 m² plancher → SHAB 0,80 × 50 = **40,0 m²**
  - **T3** : 65 / 11,6 = **5,60 m** → 65,0 m² plancher → SHAB **52,0 m²**
- **Répartition par niveau : T2 ×3 · T3 ×1 = 4 logements** (motif « équilibre »), identique sur
  **4 niveaux (R+3)** → **16 logements** = **16 modules dessinés** (verrou : nb = nb dessiné).

### Surfaces (mesurées sur la géométrie)
| Grandeur | Valeur | Origine géométrique |
|---|---|---|
| SDP (surface de plancher) | **1 327,8 m²** | aire (modules + noyaux + coursives) × 4 niveaux = emprise 331,9 × 4 |
| SHAB estimée | **688,0 m²** | 0,80 × aire des modules (T2 12×50 + T3 4×65 = 860 m²) → T2 480 · T3 208 |
| Emprise au sol | **331,9 m²** | union des 2 emprises (≤ plafond 1 222 m²) |
| Pleine terre (perméabilité) | **590,2 m²** | assiette − bâti − places − allées − accès (≥ 524 m² requis) |

### Stationnement (barème validé, par typologie)
- Barème UA 2.7.3 : collectif 1-2 pièces = 1 place, 3-4 pièces = 1,5. Donc **T2 → 1**, **T3 → 1,5**.
- Imposées = 12×1 + 4×1,5 = **18 places**. Dessinées = **18** (place 2,5 × 5 m, desservies par des
  allées de 5 m, chaque place touche une allée ; accès de 4 m sur la limite voie au sud).

### Mixité sociale (règle sourcée, UA 1.3)
- SDP d'habitation 1 327,8 m² **> seuil 1 000 m²** → mixité **applicable**. Quota 20 % →
  **265,6 m² de SDP aidée imposée**, soit **≈ 4 logements aidés** sur 16.

### Distribution par niveau
RDC / R+1 / R+2 / R+3 : **T2 ×3 · T3 ×1** chacun (SDP 331,9 m² par niveau). Pas de commerce
(logements seuls). Modules et noyaux placés par le moteur : 4 modules dessinés = 4 logements comptés.

## 4. Contrôles (quatre résultats, jamais « conforme »)

| Contrôle | Règle | Scénario | Résultat |
|---|---|---|---|
| Emprise au sol | ≤ 1 222 m² (70 %) | 332 m² | **Réussi** |
| Hauteur | ≤ 12 m à l'égout | R+3 ≈ 12 m | **Réussi** |
| Reculs | voie 4 m · séparatives 3 m | bâti dans la zone | **Réussi** |
| Perméabilité (pleine terre) | ≥ 524 m² (30 %) | 590 m² | **Réussi** |
| Stationnement | ≥ 18 places (barème typologie) | 18 dessinées | **Réussi** |
| Espaces verts | règle non validée distincte | — | Non effectué |
| Destination | non modélisée par ce moteur | logements seuls | Non effectué |
| Distance entre constructions | non modélisée | — | Non effectué |
| Locaux vélos · déchets | non modélisés | — | Non effectué |
| PPR / ER / EBC / SUP | aucune contrainte sur le terrain | — | **Non applicable** |

Règle d'or : **un « Réussi » n'existe que si la règle est validée avec citation ET que la mesure la
respecte** (vérifié par test). Une règle non validée ou non modélisée est « Non effectué », jamais
« Réussi ». Une contrainte absente du terrain est « Non applicable ».

## 5. Comparaison avec le projet de l'architecte

Projet archi (référence) : **29 logements, SP 2 368 m², emprise 710 m², 31 places dont 30 en
sous-sol, perméabilité 710 m²**.

| | Archi | LABUSE (ce moteur) | Écart | Explication |
|---|---:|---:|---:|---|
| Logements | 29 | **16** | −13 | voir ci-dessous (sous-sol d'abord) |
| Surface de plancher | 2 368 m² | **1 328 m²** | −1 040 | emprise plus petite × ~4 niveaux |
| Emprise au sol | 710 m² | **332 m²** | −378 | le sol libéré par le sous-sol archi devient du bâti |
| Places | 31 (30 ss-sol) | **18 (aérien)** | — | contrainte de mandat : aérien seul |
| Perméabilité | 710 m² | **590 m²** | −120 | les deux ≥ 524 m² requis ; archi en garde plus |

**Le sous-sol explique l'essentiel de l'écart.** L'archi met **30 de ses 31 places en sous-sol**,
ce qui libère le rez pour un bâtiment presque deux fois plus étendu (emprise 710 vs 332 m²). Notre
mandat impose le **stationnement aérien** : les 18 places + allées + accès occupent au sol
**≈ 822 m²** (= assiette 1 744 − emprise 332 − pleine terre 590). C'est précisément cette surface
que l'archi s'épargne au sol en l'enterrant. Si ce parking passait en sous-sol, ces ~822 m² de
terrain redeviendraient constructibles — l'emprise se rapprocherait des 710 m² de l'archi et la
capacité des ~29 logements. **L'option « en ouvrage / sous-sol » est hors périmètre d'IMPLANTATION-1**
(elle viendra plus tard) ; l'écart était attendu et il est entièrement imputable à ce choix.

**Écarts secondaires**, honnêtement :
- **Forme.** Le moteur n'essaie que des rectangles simples (barre, deux barres, L) plaqués sur le
  grand axe ; l'architecte épouse le contour irrégulier du terrain et optimise mieux l'emprise.
- **Rendement de plancher.** La convention plancher→habitable 0,80 et des modules rectangulaires
  bornent la SHAB ; un plan réel d'architecte fait mieux.
- Le moteur **ne cherche pas à égaler l'archi** : il publie la meilleure implantation *qui passe
  tous les contrôles*, avec le stationnement entièrement dessiné au sol.

## 6. Limites et ce qui reste à confirmer

- Terrain traité **à plat** (le relief n'entre pas dans le volume ; cf. gabarit E-C1). Pente /
  dénivelé LiDAR non mobilisés ici (non requis pour l'implantation).
- Non modélisés → **à faire confirmer par un architecte** : distance entre constructions, locaux
  vélos/déchets, plans de logements. Accès véhicule : limite classée voie, mais visibilité et
  autorisation non vérifiées.
- Répartition T2/T3 et toutes les « conventions » sont **Estimé**, modifiables.

## 7. Reproduire le scénario à l'identique

```
# base réelle (lecture seule), repère /src du worktree
PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
<python> -c "from labuse.implantation import moteur, rendu; s=moteur.etudier(); \
rendu.rendre_plan_png(s,'plan.png'); rendu.ecrire_scenario_json(s,'scenario.json')"
```

`scenario.json` archive entrées, version des règles (avec citations), conventions, géométrie
(EPSG:2975), tableau de capacité et contrôles : le scénario se rejoue tel quel.

Tests du LOT C : `pytest tests/test_implantation1.py` (marqués `reel` ; 20 tests, re-mesurent chaque
invariant depuis la géométrie). Nécessite `LABUSE_APP_DATABASE_URL` sur la base applicative.
