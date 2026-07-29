# REPLI NON OPTIMISTE — PHASE A, MESURE (lecture seule)

> **Statut : MESURE TERMINÉE — RIEN IMPLÉMENTÉ. POINT D'ARRÊT.**
> Mesuré le 29/07/2026 sur la base courante (run servi `q_v7_defisc`, 21 YAML calibrés,
> golden 116). Aucun re-run de scoring, aucune écriture de production. Tout est vérifié
> PAR LE CODE (resolve_zone, cascade classe(), M6 2b), jamais par le préfixe d'un libellé.

---

## Résumé exécutif — trois retournements et une condition d'arrêt

1. **Le correctif du gate (§2 du mandat) est un NO-OP dans l'état courant.** Recensement
   direct des 21 YAML : **82 zones `habitat: interdit`, TOUTES avec hauteur exploitable →
   0 zone interdit-sans-hauteur.** La série PLU phase 4 a calibré les hauteurs et colmaté
   la fuite du gate. La ligne `if strict or r.habitat=="interdit" or _has_usable_height(r)`
   ne changerait aucun verdict aujourd'hui. C'est le principe #3 de Vic en acte : le chiffre
   fondateur du mandat (interdit-sans-hauteur servi optimiste) est un **vestige** d'avant la
   phase 4. Les 104 zones interdit calibrées portent une hauteur → M6 2b les gère déjà.

2. **Le seul enjeu vivant, ce sont les GELS — et le correctif esquissé pour eux (§2bis,
   « honorer constructible_neuf dans la cascade ») est DANGEREUX tel quel.** `resolve_zone`
   rend `constructible_neuf=False` dès que le `name` GPU ne se parse pas en préfixe U/AU.
   Or plusieurs communes stockent une **description** dans `name` (« Zone essentiellement
   les écarts des hauts de Sainte-Marie », subtype U). Un correctif qui lirait
   `constructible_neuf(name)` exclurait à tort ces zones U réellement constructibles.
   Chiffré : **21 077 parcelles servies (dont 28 brûlantes, 211 chaudes) seraient
   faussement exclues** ; **13 parcelles GOLDEN (dont 4 brûlantes) casseraient.** La cascade
   classe aujourd'hui sur le SUBTYPE (robuste) précisément pour éviter cette fragilité de
   parsing — un correctif naïf la réintroduirait.

3. **Le run servi `q_v7_defisc` (15/07/2026) PRÉCÈDE l'état YAML courant.** 412 parcelles
   sont servies à ≥90 % de recouvrement dans des zones interdit-AVEC-hauteur que M6 2b
   (code déjà en production) devrait exclure. Elles ne le sont pas → le run a été calculé
   avant le calibrage phase 4. **Conséquence de méthode : re-passer la cascade sur les YAML
   courants déplacerait déjà des parcelles, avant tout correctif.** On ne peut pas mesurer
   proprement le delta d'un correctif sur une base déjà décalée de son propre code.

4. **CONDITION D'ARRÊT DÉCLENCHÉE — 3 golden bougent, pas 2.** La discipline nommait deux
   parcelles de référence (97422000AD1237, 97422000AX1253). La mesure en trouve une
   **TROISIÈME** dans la population des vrais gelés : **97407000AV0096 (Le Port,
   réserve_foncière, 100 % en zone gel calibrée).** Règle de Vic : « une 3e parcelle qui
   bouge = arrêt ». → **Arrêt, arbitrage requis avant toute suite.**

---

## §1 — Population qui basculerait « positive → non positive » (Vic #1)

### Méthode (par les maillons)
La bascule vers `ecartee` passe par **M6 2b hard_exclude** (`phase1.py:277-294`), qui exige
`resolve_zone(name).calibree AND habitat=="interdit"` ET un recouvrement ≥ seuil (90 %).
La classification positive de préfixe se lit sur le **subtype** (`phase1.py:251`, pos_p=[U,AU]),
l'interdit sur le **name**. J'ai classé les 5 848 polygones `plu_gpu_zone` par catégorie via
`resolve_zone`, puis calculé pour chaque parcelle servie le recouvrement EXACT par catégorie
(même formule que la cascade : `Σ aire(∩)/aire(parcelle)` en geom_2975).

### Catégories de zones (5 848 polygones)
| Catégorie | Polygones | Sens |
|---|---:|---|
| `an_ou_autre_negatif` (A/N, déjà exclues par préfixe) | 3 153 | hors sujet |
| `constructible` (U/AU sains) | 1 669 | inchangé |
| `gel_faux_parse` (subtype U/AU, `name`=description → False de parsing) | 757 | **piège du correctif naïf** |
| `gel_calibree` (2AU/3AU/AUst + gels éco calibrés Ue/Up/Uv/Uppp) | 165 | **vrais gelés** |
| `interdit_avec_hauteur` (M6 2b déjà actif) | 104 | déjà géré |

### La population réelle : GELS CALIBRÉS servis positifs, recouvrement ≥ 90 %
**738 parcelles** — direction unique **positive → non positive** garantie par construction
(le correctif ne fait que RETIRER des positives ; aucun mécanisme n'en ajoute — vérifié :
le gate ne peut que durcir, la cascade-gel ne peut qu'exclure). Aucun changement d'un autre
sens n'est possible → l'invariant « tout autre sens = bug » est satisfait structurellement.

| Tier | Parcelles |
|---|---:|
| brûlante | **1** (97422000AD1237) |
| chaude | 19 |
| réserve_foncière | 61 |
| à creuser | 657 |
| **total** | **738** |

Bande soft-flag (recouvrement 5–90 %, pénalité de score et non exclusion) : 163 de plus
(144 à creuser, 19 réserve).

**Par commune × tier (gel calibré ≥ 90 %)** — communes concernées : Saint-Paul (183 : 177
à creuser + 6 chaudes), Le Port (134), Le Tampon (113 dont la brûlante), Saint-Joseph (105),
Saint-Louis (52), La Possession (59), Les Trois-Bassins (45), La Plaine-des-Palmistes (28),
Sainte-Suzanne (13), Les Avirons (6). Détail complet en base (`repli_pcov`).

> **Écart avec le recensement du mandat (2 234 fusionné d+e).** Le 738 est plus BAS et plus
> juste : (a) seuil de recouvrement ≥ 90 % appliqué (le 2 234 comptait tout chevauchement) ;
> (b) exclusion des `gel_faux_parse` (artefacts de parsing, pas des gels) et des interdits
> déjà gérés ; (c) mesuré sur l'état post-phase-4. Le 2 234 était une borne haute d'avant la
> série PLU.

---

## §2 — Question bloquante : les TIERS (Vic #2)

**Prouvé par les maillons, puis mesuré.**
- **Maillon 1 (P direct)** : `parcel_residuel` alimente le modèle P comme features —
  `sdp_residuelle_m2`, `pct_potentiel`, `sous_densite` (`p_model/features.py:102-108`) +
  `zone_plu` (l.86). Une SDP résiduelle qui tombe à 0 fait chuter le score P → le rang → le tier.
- **Maillon 2 (cascade)** : `residuel_socle` (`etage0_ext.py:153`, barème −25…+30) lit la
  TABLE précalculée `parcel_residuel`, pas `resolve_zone` en direct.

**Mesure.** Sur les 738 gelés servis, **370 portent une `sdp_residuelle_m2` optimiste > 0**
(moyenne 2 009 m², **743 352 m² de SDP fictive au total** sur du foncier juridiquement fermé).
Un recalcul les ramène à 0 → les 370 scores P baissent → **les tiers bougent**. Exposition de
tête directe : **1 brûlante + 19 chaudes + 61 réserve**. Les tiers servis actuels
(120 / 1 031 / 3 587 / 72 980 / 353 945) NE sont donc PAS invariants sous le correctif.

→ **Statut d'arrêt confirmé** : un correctif gel touche les tiers commercialement servis.
Pas de merge sans re-run du champion, arène, arbitrage Vic.

---

## §3 — `parcel_residuel` : coût de la migration (Vic #3)

Ce n'est pas un correctif de code, c'est un correctif + une **migration de données**.
- **Recalcul scopé = 738 parcelles** (les gelés ≥ 90 %) ; **372 ont une ligne
  `parcel_residuel`, dont 370 avec SDP optimiste > 0** à remettre à 0. Les 366 restantes
  n'ont pas de ligne (rien à migrer).
- **Effet sur l'étalonnage Saint-Paul (32 448 verdicts).** **183 des 738 sont à Saint-Paul.**
  Saint-Paul est la commune de référence du golden ET la source du barème `residuel_socle`
  (−25…+30 extrait des 32 448 verdicts). Recalculer ses gelés change leur contribution socle →
  risque direct sur le golden 116 et sur le barème lui-même si l'un des 183 sert d'ancre
  d'étalonnage. **À isoler avant tout recalcul** (mesure de recalibrage du barème à prévoir).

---

## §4 — Discipline golden (Vic #4) — ARRÊT

Golden 116 · 51 servies non-écartées.

**Doivent bouger (gel calibré ≥ 90 %) : 3 — une de trop.**
| IDU | Commune | Tier run | Recouvrement | SDP résiduelle |
|---|---|---|---:|---:|
| 97422000AD1237 | Le Tampon | brûlante | 1,000 | 453 |
| 97422000AX1253 | Le Tampon | chaude | 0,997 | (aucune ligne) |
| **97407000AV0096** | **Le Port** | **réserve_foncière** | **1,000** | **5 401** |

Les deux premières sont les nommées. **La troisième (Le Port AV0096) n'était pas au mandat**
→ mouvement au-delà de l'attendu → **ARRÊT** conformément à la règle. À trancher : est-ce
un gel légitime (le golden la sur-classe aujourd'hui, bug de référence latent) ou le
correctif la sur-exclut ? La réponse conditionne la mise à jour de la référence.

**Ne doivent PAS bouger, mais casseraient sous un correctif naïf (gel_faux_parse ≥ 90 %) :
13 golden, dont 4 brûlantes** — 97403000AR1423, 97409000AR1260 (Saint-André),
97416000EY1406 (Saint-Pierre), 97418000AT2379. Preuve concrète que la version esquissée
du §2bis (« honorer constructible_neuf ») blesserait le golden 116. Le correctif doit
détecter le gel par le CALIBRAGE (`calibree=True`), jamais par `constructible_neuf` seul.

**interdit_avec_hauteur ≥ 90 % ∩ golden : 0** (M6 2b ne touche pas le golden).

---

## §5 — Populations b (553) et a (238), note c (Vic #5)

Dans l'état post-phase-4, ces populations sont largement absorbées :
- **a (interdiction perdue si calibrée, gelée à raison)** : couverte par `gel_calibree` /
  `interdit_avec_hauteur` — plus de trou de gate (§1 point 1).
- **b (servies au générique 9 m optimiste, habitat admis)** : le correctif ne les change
  pas (restent au repli générique assumé `calibree=False`) ; leur sortie = calibrage des
  hauteurs (phase 4), pas ce mandat.
- **c (emprise implicite, 237)** : reste une note, hors périmètre.
Relevé complet à re-chiffrer seulement si Vic ré-ouvre après arbitrage.

---

## Note — Saint-André (vérification n°1, tranchée par Vic 29/07)

Saint-André est l'une des 3 communes « générique pur » (population d, GPU dépubliée).
**Statut PLU tranché : le PLU de 2019 est EN VIGUEUR et c'est lui qu'il faut graver.**
La révision générale est au stade du **dossier d'ARRÊT** (délibération 02/07/2025, bilan de
concertation 18/12/2024) — projet arrêté, **non approuvé**.

**Garde-fou de fraîcheur** : révision arrêtée le 02/07/2025 ; enquête publique et
approbation à venir. **Le calibrage 2019 devra être repris à l'approbation** de la révision.

Ressource (mandat dossier communal, à SIGNALER, ne pas exploiter maintenant) : dossier
complet de la révision en un ZIP unique — https://www.saint-andre.re/plu/mstandre_plu.zip
(rapport de présentation, PADD, règlement écrit et graphique, OAP, annexes).

---

## Ce que je recommande de trancher (Vic)

1. **Le gate (§2) est mort-né dans l'état courant** — le fermer comme le « coût par taille » :
   correction déjà réalisée par la phase 4. À confirmer.
2. **Le correctif gel (§2bis) doit être redessiné** : détection par `calibree=True`
   (jamais `constructible_neuf` de parsing), sinon 21 077 faux positifs / 13 golden cassés.
3. **La base est périmée** : re-passer la cascade sur YAML courants (412 interdits encore
   servis) AVANT de mesurer un delta de correctif — sinon les deltas se mélangent.
4. **3 golden bougent** → arrêt, arbitrage sur AV0096, puis re-run champion + arène si suite.

*Artefacts de mesure : table `repli_pcov` (recouvrement par catégorie × parcelle servie),
`zone_cat_p` (catégorie des 5 848 polygones), scripts `/tmp/repli_cat.py`,
`/tmp/repli_mesure.py`.*
