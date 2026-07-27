# PLU-SÉRIE-NUIT — CONTRE-PREUVE (session C)

> Contre-extraction à l'aveugle de 3 communes du lot B, depuis le clone de la session A.
> Branche `feat/plu-nuit-verif`, fichiers `config/verif/plu_<slug>_contre.yaml`.
> **RIEN N'A ÉTÉ CORRIGÉ** — chaque divergence est documentée avec les deux lectures et le
> passage verbatim du règlement ; Vic arbitre au matin.

## 1. Protocole (aveuglement)

- **Tirage documenté (00:06)** : parmi les 5 communes commitées du lot B à cet instant
  (sujets de commits tronqués au libellé de commune, détails jamais lus), classement par
  nombre de parcelles cadastre → max / médiane / min = **Saint-Louis (29 241) /
  Petite-Île (13 137) / Les Avirons (8 611)**. Une grosse, une moyenne, une petite.
- **Sources** : UNIQUEMENT les PDF de `/tmp/plu_nuit/reglements/`, md5 re-vérifiés au tirage
  contre la table du pré-vol (bae5ab70…45 / 19407563…f4 / 73a0f8f6…db). Les YAML et le
  rapport du lot B n'ont pas été ouverts avant la fin des 3 contre-extractions.
- **Contre-extractions** : 00:06 → 00:22 (Saint-Louis 00:12, Petite-Île 00:17, Les Avirons
  00:22). Mêmes invariants et même schéma v1 que la série. Couverture 100 % des libellés des
  manifestes (52 + 34 + 27), **387 citations re-résolues par script, 0 FAIL**.
- **Ouverture des YAML B : 00:25**, après la fin des 3 contre-extractions
  (`git show origin/feat/plu-nuit-b:…`). Diff structuré valeur par valeur sur 8 champs ×
  zones communes + blocs source/gels/renvois.

## 2. Résultat global

| Commune | Zones communes | Champs comparés | Identiques | Divergences |
|---|---|---|---|---|
| Saint-Louis | 25/25 (+ gels 10/10 identiques) | ~173 | 134 | 39 |
| Petite-Île | 15 communes (+3 structurelles UF/UFcim/AUF) | ~99 | 88 | 11 |
| Les Avirons | 19/19 (+ gels 2/2 identiques) | ~116 | 100 | 16 |
| **Total** | **59 zones + 12 gels** | **~388** | **322 (83 %)** | **66** |

**Sur les champs à plus fort impact moteur — hauteurs et emprises — la concordance est
quasi totale** : aucune divergence numérique sur he/hf/emprise sur les 59 zones, hors
3 cas d'interprétation (UZ Saint-Louis, Ub4 Les Avirons « hauteur absolue », et les
`a_verifier` de C). Les gels (zones_au_st) et les périmètres A/N sont identiques partout.
Les md5 et offsets de pagination concordent sur les 3 communes.

Les 66 divergences se répartissent en **2 motifs doctrinaux systématiques** (42 cas, 64 %),
**4 divergences d'interprétation** ponctuelles, et **17 défauts de la contre-extraction C
elle-même** (consignés honnêtement au §6 : la contre-preuve coupe dans les deux sens).

## 3. MOTIF SYSTÉMATIQUE n°1 — « perméable » gravé ou non en pleine_terre_pct (32 cas)

**Le plus gros écart de la nuit, et il sépare les SESSIONS, pas les communes.**

- **Lecture B** : `pleine_terre_pct: null` quand l'article 13 impose un % d'« espace vert
  et perméable » SANS sous-minimum explicite de « pleine terre » (src B, Saint-Louis UA :
  « 15 % … en espace vert et perméable, SANS sous-minimum de pleine terre »).
- **Lecture C — et lecture du LOT A ENTIER** : ce % est gravé dans `pleine_terre_pct`
  (convention posée dès Sainte-Rose lot A : « PLEINE TERRE = “% espace perméable”
  (Art. 13) »).

Verbatim Saint-Louis, Art. UA 13.1, p.22 : « *Au minimum 15 % de la superficie totale de
l'unité foncière doit être traité en espace vert et perméable comprenant des plantations* ».
Verbatim Les Avirons, Art. U 13.1, p.18 : « *Le terrain doit être traité en espace libre et
perméable … sur au moins : En zone Uc : 30 % de l'unité foncière …* ».
Contre-exemple Petite-Île, Art. UB.13, p.32 : « *doivent être conservées en espaces de
**pleine terre** à hauteur de 25 % de l'unité foncière* » — là le mot y est, et **les deux
sessions ont gravé la même valeur** (zéro divergence pleine-terre sur Petite-Île).

Cas concernés : Saint-Louis 24 champs (UA, UB, UC, UC1, UC2, UD, UD1, UE, US, UZ et toute
la famille 1AU) ; Les Avirons 8 champs (Ub, Ub1, Ub2, Ub3, Ub4, Ue, AUec, AUt).

**Enjeu d'arbitrage (île entière, pas seulement lot B)** : B applique une sémantique
stricte du champ (fidèle au nom `pleine_terre_pct`) mais **perd une contrainte de surface
réelle et opposable** — le % perméable mord sur l'emprise exactement comme une pleine
terre. La convention A/C conserve la contrainte (prudente pour le moteur) mais étire la
sémantique du champ. Trancher : soit graver le % perméable dans le champ actuel avec note
(convention A/C, 12+ communes déjà gravées ainsi), soit ajouter un champ
`permeable_pct` au schéma v2 et re-passer les YAML B. **En l'état, les YAML B sont plus
OPTIMISTES que les YAML A sur ce point** — incohérence inter-lots à résoudre avant mesures.

## 4. MOTIF SYSTÉMATIQUE n°2 — retraits « H/2 avec minimum » (10 cas, Saint-Louis)

- **Lecture C — et convention du LOT A** (rapport A, friction n°5) : graver le **minimum
  plancher** (règle relative en note). Ex. UE : rv 5, rl 4.
- **Lecture B** : graver **H/2 calculé à la hauteur max gravée de la zone**. Ex. UE
  (12 m égout) : rv 6, rl 6 ; UC1/1AUc1 (9 m) : rl 4,5 (src B : « Valeur gravée = H/2 à la
  hauteur max du secteur … plancher du texte : 3 m »).

Verbatim Saint-Louis, Art. UE 6.2, p.71 : « *… au moins égale à la moitié de la hauteur (H)
de la façade concernée, avec un minimum de 5 mètres* » ; Art. UE 7.2, p.72 : « *… au moins
égale à la moitié de la hauteur (H) …, avec un minimum de 4 mètres* » ; Art. UC 7.2, p.44 :
« *en secteur UC1, le retrait (L) est obligatoire et doit correspondre au minimum à la
moitié de la hauteur à l'égout … sans être inférieur à 3,00 mètres* ».

Cas : UE (rv, rl), US (rv, rl), 1AUe (rv, rl), 1AUe oap1 (rv, rl), UC1 (rl), 1AUc1 (rl).

**Les deux lectures sont fidèles au texte ; c'est un choix de convention.** À noter
franchement : **la convention B est la plus conservatrice** (un projet à la hauteur max
subit bien H/2, pas le plancher) — le plancher gravé par A/C est exact pour un projet bas
mais optimiste pour un projet haut. La friction n°5 du rapport A qualifiait le plancher de
« prudent » : **c'est contestable, et la session B l'a implicitement contesté.** Arbitrage
île entière nécessaire (Saint-Joseph, Sainte-Marie, La Possession, Étang-Salé du lot A sont
gravés au plancher).

## 5. Divergences d'interprétation ponctuelles (les deux lectures se défendent)

### 5.1 Saint-Louis UZ (ZAC de l'Avenir) — 5 champs
- **C** : contradiction consignée entre Art. UZ 1/2 (lu « gardiennage ») et 10.2 → hauteurs,
  reculs, stationnement en `a_verifier` ; seule la cote NGR 42 m notée.
- **B** : résolution complète — habitat admis, tranche la plus conservatrice gravée
  (hf 9 m), rl 3 m, 1,5 pl/logt, emprise 60 %.
- **Verbatim (donne largement raison à B)** : Art. UZ 1.2, p.92 n'interdit que
  industrie/entrepôt/agricole. Art. UZ 2.2, p.92 : « *Sont admises … 1. Les constructions à
  destination de logements … dans le respect des affectations et implantations indiquées au
  schéma joint en annexe. 2. Les espaces … “affectation en activités tertiaires” sont
  seulement destinés à ce type d'occupation. Toutefois les logements … à la condition d'être
  nécessaires à la surveillance et au gardiennage* » — la clause gardiennage ne vaut QUE
  pour les espaces tertiaires ; la « contradiction » vue par C n'existe pas. Art. UZ 10.2,
  p.96-97 : 17 m (collectifs) / 9 m (individuels) / 12 m (tertiaires), plafond NGR 42 m —
  B a gravé la tranche la plus conservatrice (9), conforme à l'invariant tiroirs.

### 5.2 Petite-Île AUs, recul voirie — tranche gravée (C=10, B=4)
Verbatim Art. AUS.6, p.126 : « *recul minimal de : 10 mètres par rapport aux routes
départementales - 30 mètres par rapport aux routes nationales - 4 mètres par rapport aux
autres voies* ». C a gravé la tranche RD (invariant « tranche la plus conservatrice ») ;
B la tranche générale « autres voies » (note B : « 4 m des autres voies »). Un tiroir
GÉOGRAPHIQUE (dépend de la voie riveraine) n'est pas un tiroir d'AFFECTATION — l'invariant
ne dit rien de ce cas. À trancher (le moteur ne connaît pas le type de voie riveraine).

### 5.3 Petite-Île UF / UFcim / AUF — zone calibrée ou gel ?
- **C** : zones à part entière, hauteur « par schéma » → `a_verifier`, habitat interdit.
- **B** : versées dans `zones_au_st` (motif : équipements publics, habitat interdit hors
  logements de fonction, « aucun plafond de hauteur chiffré au règlement », UF.10 p.70).
- **Effet moteur identique (0 logement)** dans les deux cas. Sémantiquement, le gel B
  surdéclare (« construction neuve non autorisée » — faux pour un équipement public),
  mais aucun impact sur la capacité logement. Question de forme pour le schéma v2.

### 5.4 Les Avirons Ub4 — « 8 mètres en hauteur absolue »
Verbatim Art. U 10.2, p.13 : « *Ub4 : 8 mètres en hauteur absolue* ». C : he null / hf 8
(prudent). B : he 8 / hf 8 (note : « Plafond absolu unique => he = hf = 8 »). Équivalent
pour le plafond ; la forme B est plus informative. Micro-convention à fixer.

## 6. Défauts de la contre-extraction C (17 cas) — consignés contre moi-même

La contre-extraction a été menée en ~16 min pour 3 communes ; le texte tranche CONTRE C sur
tous les cas suivants. **Sur cet échantillon, l'extraction B est plus profonde et plus
exacte que la contre-extraction C.**

**Valeurs fausses de C (4)** :
- Petite-Île 1AU/1AUa/1AUz, rl : C=4 (« retrait minimal 4 m » — citation INEXACTE), B=3.
  Verbatim Art. 1 AU.7, p.92 : « *la marge de recul minimale doit être égale à 3 mètres.
  Cette marge peut être ramenée à 2 mètres dans le cas d'un mur plein* » (fond : 3 m aussi).
- Petite-Île UZ, rv : C=4 (sans citation), B=0. Verbatim Art. UZ.6, p.83 : « *implantées
  soit à l'alignement soit en retrait des voies publiques* » — aucun minimum chiffré (RD :
  annexe 5, noté par B).

**`a_verifier` de C là où le texte est limpide (11)** :
- Petite-Île UZ rl (Art. UZ.7, p.83 : « *soit en limite séparative soit en retrait* » → 0,
  lecture B) ; UZ stat (Art. UZ.12, p.85 : « *1 place de stationnement par logement* ») ;
  UEa rv (Art. UEa.6, p.61 : « *Pour toutes les autres voies … recul minimum de 5 mètres* » ;
  20 m d'axe RN2) ; UEa rl et AUE rl (Art. UEa.7, p.62 / AUE.7, p.112 : « *recul de
  4 mètres* ») ; AUs rl (Art. AUS.7, p.127 : « *recul minimum de 3 mètres* »).
- Les Avirons Ue rl et AUec rl (Art. UE/AUec 7.2, p.21/31 : « *au moins être égale à
  5 mètres* ») ; AUt rl (Art. AUt 7.2, p.37 : « *au minimum de 3 mètres* »). Les fins de
  page avaient été tronquées par mes requêtes d'extraction, pas par le PDF.

**Alinéas de destinations MANQUÉS par C (2 zones, 4 champs — les plus graves)** :
- Les Avirons **Ub4** : C l'a traité en zone d'habitat ordinaire (stat 1,5 pl/logt).
  Verbatim Art. U 1.2 al.7, p.7 : « *En secteur Ub4, les constructions, ouvrages et travaux
  non liés à la réalisation d'équipements collectifs d'intérêt général* » [sont interdits]
  → **habitat interdit, B a raison**. (Ironie : C avait bien lu l'alinéa 8 voisin, Ub5.)
- Les Avirons **Ud2** : idem. Verbatim Art. U 2.2, p.8 : « *En secteur Ud2, seules les
  constructions destinées à la pratique du tourisme … ainsi que l'extension limitée des
  constructions existantes sont autorisées* » (60 m²/bât., 120 m²/UF) → **aucun logement
  neuf, B a raison**.

Leçon pour le §9 du mandat-cadre : dans les chapitres MUTUALISÉS, les interdictions par
secteur sont des ALINÉAS NUMÉROTÉS au fil des articles 1/2 communs — il faut balayer TOUS
les alinéas pour CHAQUE secteur, pas s'arrêter au premier trouvé. C est tombé exactement
dans le piège que le motif « le préfixe ne prouve rien » annonçait.

## 7. Verdict d'ensemble proposé à l'arbitrage

1. **Aucun signe de négligence dans le lot B** — au contraire : sur l'échantillon tiré,
   B est exact sur toutes les valeurs à texte limpide, a résolu UZ Saint-Louis plus
   finement que C, et a attrapé 2 statuts habitat que C a manqués. **Les 3 YAML B
   sortent RENFORCÉS de la contre-preuve.**
2. **Les 2 vrais chantiers sont doctrinaux et INTER-LOTS** (§3 perméable/pleine-terre,
   §4 plancher/H-2) : ils opposent les conventions du lot A (et de C, qui les a suivies)
   à celles du lot B. Tant qu'ils ne sont pas tranchés, les mesures comparatives
   inter-communes (phase 4) mélangeront deux doctrines — à arbitrer AVANT la phase 4.
3. Micro-arbitrages de forme : tiroir géographique voirie (§5.2), UF-en-gel (§5.3),
   hauteur absolue (§5.4).
4. Les 3 fichiers `config/verif/*_contre.yaml` sont des artefacts de preuve — pas des
   candidats au merge. **Aucune correction appliquée nulle part**, conformément au mandat.

— Session C, 00:06 → 00:5x. Base applicative jamais touchée. Phase 4 et micro-arbitrages
du matin non lancés, conformément au mandat.
