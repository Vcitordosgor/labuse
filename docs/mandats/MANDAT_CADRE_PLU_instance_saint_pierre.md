# MANDAT-CADRE PLU-{COMMUNE} — RE-GRAVURE DES RÈGLES CHIFFRÉES DE FAISABILITÉ

> **Mandat réutilisable.** Pour chaque nouvelle commune : remplir le bloc §0, tout le reste s'applique tel quel.
> Les leçons des communes précédentes s'accumulent en §9 — **les lire AVANT de commencer.**
>
> *Restauré le 28/07/2026 : §§0-8 depuis la copie de Vic (`MANDAT_CADRE_PLU.md`), §9 = copie vivante du dépôt, conservée intégralement (session B).*

---

## 0 · PARAMÈTRES DE L'INSTANCE

| Paramètre | Valeur |
|---|---|
| **Commune** | *(à remplir)* |
| **Fichier cible** | `config/plu_<commune>.yaml` |
| **Branche** | `feat/plu-<commune>` |
| **Clone** | *(dédié)* |
| **Pool servi** | *(nombre de parcelles, contexte)* |
| **Statut** | PILOTE (rapport d'industrialisation §7 complet) / SÉRIE (rapport allégé) |

**Exécuteur** : Claude Code, modèle **Fable** — l'extraction demande une lecture juridique, pas de l'exécution mécanique.
**Fable ne merge JAMAIS** — Vic merge en `--no-ff`. Une commune = un mandat = une branche.

---

## 1 · POURQUOI CE MANDAT

LABUSE calibre le **zonage opposable** sur 24 communes (6 306 zones, round-trip DB↔YAML zéro écart), mais les **règles chiffrées de faisabilité** (hauteurs, emprises, reculs, sourcées par article) doivent être gravées commune par commune depuis les règlements. Sans elles, le moteur applique un repli générique (9 m → 3 niveaux, `calibree=False`, étiquette Estimé).

**Fait produit établi sur trois communes indépendantes** : le repli générique n'est pas neutre, il est **optimiste** — SDP médiane −33 % / −33 % / −53 % après calibrage, 0 gain de constructibilité sur 1 200 parcelles testées. C'est l'argument chiffré qui justifie le calibrage complet de l'île.

Ce calibrage est le travail non-scalable qui constitue la barrière concurrentielle de LABUSE. Il est aussi ce qui permet de passer de « SDP estimée — règle générique » à « SDP tracée par article » dans tout le produit.

**La boussole prime sur la couverture.** Un chiffre faux étiqueté « Sourcé » est le pire faux positif possible : il porte la mention de fiabilité maximale. Mieux vaut 12 zones gravées juste et 23 en repli honnête que 35 zones à moitié devinées. **Aucun quota de zones à atteindre** — la seule métrique qui compte est : zéro valeur non sourcée.

---

## 2 · POINT D'ARRÊT A — LE RÈGLEMENT SOURCE (avant tout travail)

Identifier la source officielle du règlement en vigueur : Géoportail de l'urbanisme (GPU), site de la commune / intercommunalité, ou document déjà présent dans les données ingérées.

Rendre à Vic, puis **attendre son GO** (en variante SÉRIE NUIT : embranchement automatique, voir le mandat de nuit) :

1. URL ou chemin · millésime · date d'approbation · statut (en vigueur / en révision / modification en cours) · **md5**.
2. **Concordance de millésime** : le règlement trouvé correspond-il au millésime du zonage calibré en base (`plu_gpu_zone`, `config/calibrage/zonage_<commune>.yaml`) ? Divergence → STOP : graver des règles plus récentes que le zonage servi produirait des incohérences invisibles.
3. **Offset de pagination** PDF ↔ pagination imprimée. *(Leçon Tampon : l'écart des deux paginations a produit 3 citations de page fausses.)* Si l'offset est indéterminable, graver en pagination PDF explicite avec un champ qui le dit.
4. **Inventaire des zones** : libellés du manifeste, pool servi par zone, croisement avec `o12_zones_activite.yaml` (pré-identification des zones habitat-interdit — **indice seulement, jamais une preuve**).
5. Si le document n'est pas téléchargeable automatiquement, le dire avec le lien exact.

---

## 3 · SCHÉMA — CONFORMITÉ PAR DÉFAUT, FRICTION CONSIGNÉE

Étudier `config/plu_saint_paul.yaml` et `config/plu_saint_denis.yaml` (calibrages de référence) et en extraire le schéma exact : champs, types, conventions de nommage, portage de la source (article + page), représentation de l'absence de règle.

**Point critique** : documenter la distinction entre « non réglementé » (lu dans le texte), « absent du document » et « valeur nulle ». Un `null` doit toujours être une lecture, jamais un oubli.

Le fichier cible est **conforme par défaut** au schéma. Aucun champ nouveau, aucune convention nouvelle, sans arbitrage de Vic. **Mais chaque friction est consignée** dans une section dédiée du rapport (`§ Frictions de schéma`) avec la citation du règlement et ce qu'un schéma idéal aurait porté — on ne tord jamais le schéma en douce, on documente.

Au rapport final : **verdict de schéma** — le schéma actuel est-il apte pour les communes restantes, ou faut-il un v2 ? Si v2 : spécification et coût de migration des fichiers existants.

---

## 4 · EXTRACTION — PAR LOTS, JAMAIS D'UN TRAIT

Un lot par famille de zones (U d'abord, en commençant par le plus gros pool ; puis AU ; puis A/N si pertinent), un commit par lot, porte de sortie passée à chaque commit.

**Règles d'extraction — non négociables :**

1. **Chaque valeur porte sa source** : article + page. Une valeur sans source ne rentre pas dans le fichier.
2. **Ne jamais deviner.** Ambiguïté, renvoi non résolu, contradiction entre articles, graphie non tranchée → zone **non calibrée**, passage cité verbatim au rapport.
3. **Destinations d'abord** : lire les articles 1/2 (interdictions) avant les chiffres. `habitat: interdit` prime sur tout calibrage de hauteur. **Balayer tous les alinéas pour chaque secteur** dans les chapitres mutualisés.
4. **Tiroirs** : tiroir d'**affectation** (le moteur ne peut pas départager) → tranche la plus conservatrice. Tiroir **géographique** (la tranche dure ne vise qu'une minorité identifiable) → tranche majoritaire, tranches dures citées en note, croisement spatial en v2.
5. **Rattachement d'un libellé** : fondé sur une **clause écrite** du règlement (« la règle générale de la zone s'applique à chacun de ses secteurs ») pour un **secteur déclaré**. Un **saut d'indice non écrit**, fondé sur l'absence d'alternative, n'est pas un rattachement → zone non calibrée.
6. **COS** : aboli par la loi ALUR (2014). Vérifier la date d'approbation ; s'il figure dans un document postérieur, le consigner **sans l'appliquer**.
7. **Sous-secteurs** : une entrée distincte chacun, jamais d'héritage implicite.
8. **Hauteur absolue** : `he = hf = valeur`. Un champ laissé `null` ne signifie pas « pas de contrainte » — il déclenche le repli générique, qui peut être plus permissif que le plafond réel.
9. **Aucune rétro-ingénierie depuis la base.** Les règles se lisent dans le règlement, uniquement.
10. **Gel vs habitat-interdit** : gel (`zones_au_st`) = ouverture juridiquement conditionnée. Interdiction d'habitat dans une zone constructible = zone **calibrée** avec `habitat: interdit`. **EXCEPTION (vérifiée sur pièces le 28/07/2026)** : tant que le schéma v1 n'a pas de type « gel » distinct, une zone habitat-interdit **sans hauteur chiffrée** va en `zones_au_st` — test empirique : `resolve_zone` en mode progressif substitue l'estimation générique (9 m, habitat non contraint, `calibree=False`) à toute entrée sans hauteur exploitable AVANT que `engine.py:157` ne force la capacité zéro ; l'interdiction serait perdue. **Exigence v2 de premier rang.**
11. **`source.reglement_grave`** : fichier, md5, millésime, document GPU au calibrage, date de vérification.

**Porte de sortie de lot (obligatoire)** : tous les libellés résolus ou explicitement non calibrés avec motif · **script de re-vérification des citations** (chaque couple article/page re-résolu contre le PDF, zéro FAIL) · le YAML se charge sans erreur.

---

## 5 · POINT D'ARRÊT B — VALIDATION SUR PIÈCES

Rendre à Vic :
1. **Échantillon de 10 parcelles** couvrant plusieurs zones, résultat du moteur **avant** (repli) et **après** (calibré) — SDP résiduelle, hauteur, emprise, article invoqué. Vérifiable à la main.
2. **Liste zones calibrées / non calibrées**, motif cité pour chaque non-calibrée.
3. Les mesures d'impact du §6.

---

## 6 · IMPACT SUR LES CHIFFRES SERVIS — MESURER, NE PAS APPLIQUER

La chaîne du résiduel irrigue `residuel_socle`, donc le scoring servi, la shortlist, le renouvellement et `score_e`. Calibrer une commune touche potentiellement des chiffres servis.

À mesurer et rapporter, **sans rien appliquer** :
- Golden 116/116 avec le fichier en place — si un test tombe, lequel et pourquoi.
- **Tiers servis (120 / 1031 / 3587 / 72980 / 353945) inchangés au bit près** — le confirmer explicitement.
- Si un re-run était lancé : combien de parcelles changeraient de résiduel, dans quel sens, quels consommateurs seraient affectés.
- **Écart repli vs calibré** : distribution, médiane, quartiles, nombre de parcelles perdant toute constructibilité, nombre en gagnant.

**Interdits absolus : aucun re-run de scoring, aucun contact avec le champion P.**

---

## 7 · RAPPORT

`docs/mandats/PLU_<COMMUNE>_RAPPORT.md`.

**En PILOTE** : temps réel décomposé · manuel vs automatisable · verdict d'industrialisation (extraction assistée viable ? architecture, validation, taux d'erreur) · estimation pour les communes restantes · hétérogénéité des formats · ordre de priorité recommandé.

**En SÉRIE** : temps passé · écarts par rapport aux leçons du §9 · nouveaux pièges rencontrés (à reverser au §9).

---

## 8 · LIVRABLES ET INTERDITS

**Livrables** : `config/plu_<commune>.yaml` conforme, chaque valeur sourcée · tests de non-régression (chargement, `calibree=True` sur les zones gravées, repli propre sur les autres) · **golden 116/116 PASS** (`LABUSE_DEV_MODE=1`, `PYTHONPATH=src`) · tiers au bit près · rapport §7 · **mise à jour du §9 de ce fichier**.

**Interdits** : merger · deviner une valeur · valeur sans article + page vérifiés par script · re-run de scoring · toucher au champion P · étendre le schéma sans arbitrage · traiter une autre commune que celle du §0.

---

## §9 — LEÇONS ACCUMULÉES (reconstitution sourcée, puis ajouts de la série de nuit)

### Acquis pilote Saint-Pierre + éclaireur Le Tampon (sources : PLU_SAINT_PIERRE_RAPPORT.md, PLU_LE_TAMPON_RAPPORT.md)

1. **Destinations d'abord** : lire l'Art. 1/2 (ou le tableau des destinations) de toutes
   les zones AVANT les chiffres — `habitat: interdit` prime sur tout calibrage de hauteur ;
   un pattern-match (« gardiennage ») peut conclure l'inverse du texte.
2. **Préambules porteurs de droit** : les caractères de zone se lisent systématiquement
   (secteurs, indices, renvois s'y cachent).
3. **Renvois explicites pour les codes à préfixe chiffré** (1AUx/2AUx) : le renvoi
   mécanique du moteur ne les couvre pas → entrées explicites.
4. **Offset de pagination PDF ↔ imprimée** : à établir et documenter AVANT de citer
   (3 pages fausses au Tampon avant le script de re-vérification) ; re-vérification
   par script de CHAQUE (article, page) avant commit.
5. **`null` sourcé** ≠ valeur manquante : « Non réglementé » se grave null AVEC citation.
6. **Gels conditionnels via `zones_au_st`** (friction F2) : capacité zéro exacte,
   étiquette « secteur de transition » inexacte — assumée, documentée.
7. **Base partagée** : aucun moyen sans modification de code de booter l'API sans risque
   de convoi de verrous pendant une ingestion (PGOPTIONS écrasé par db.py) ; golden et
   mesures en fenêtre calme uniquement.
8. **COS post-ALUR** : vérifier la date d'approbation ; citer avec la date, ne JAMAIS
   appliquer.

### Ajouts série de nuit — session B, 9 communes, 27-28/07/2026 (source : PLU_NUIT_RAPPORT_B.md)

9. **PDF composite à double pagination imprimée** (Saint-Benoît) : le vote d'offset
   majoritaire peut désigner le mauvais bloc (cahier d'annexes auto-paginé). Identifier CE
   QUE numérote le bloc gagnant ; en double référentiel → `pagination_citee: "pdf"`,
   jamais de mélange.
10. **Numéros de page imprimés en EN-TÊTE** (Les Avirons, Cilaos, Bras-Panon,
    Trois-Bassins) : un vote de pied de page rend 0 sur un document proprement paginé.
11. **Couches texte fantômes** dans les notices de modification concaténées
    (Plaine-des-Palmistes) : contenu normatif lisible uniquement en rendu IMAGE.
12. **Le pré-vol pypdf peut mentir dans les deux sens** : lettres doublées fantômes
    (Cilaos, PyMuPDF propre) ET COS invisible à la regex naïve (les textes écrivent
    « coefficient d'occupation DU SOL », apostrophe typographique).
13. **Chapitre AU à destinations propres + renvoi d'indice** (Trois-Bassins 1AUe) : les
    Art. 1/2 du chapitre peuvent CONTREDIRE la zone U d'indice → vérifier renvoi vs
    contenu autonome avant de propager un habitat-interdit ; en contradiction :
    non-calibrage, arbitrage sur pièces.
14. **Renvois de modification asymétriques** (Trois-Bassins AUa→Uaa) : chercher les
    renvois article par article, pas seulement en tête de chapitre.
15. **Article hauteur qui ne fixe que le secteur** (Le Port Ue 8 → Uem seul) : vérifier le
    PDF brut avant de conclure à une perte d'extraction ; zone support sans hauteur →
    capacité zéro exacte via st-liste, jamais d'entrée sans hauteur (retombée générique
    9 m avec habitat non contraint).
16. **STECAL à caducité légale datée** (Saint-Benoît, ELAN 31/12/2021 + condition
    préfet/SCOT invérifiable) : seul le non-calibrage motivé est honnête.
17. **Sommaire périmé** après modifications successives (Petite-Île) : citer le corps
    vérifié, jamais le sommaire.
18. **Convention de citation des sous-alinéas** : « Art. X 2.2 (al. 7) » (le vérificateur
    ne résout pas les jetons à 3 niveaux) ; articles à cheval sur 2 pages → citer la plage.
19. **Hauteurs par SECTEURS GRAPHIQUES transverses aux zones** (Saint-Benoît, 4-15 m) :
    règle NON PORTABLE par le schéma v1 — arbitrage Vic 28/07/2026 : ne pas graver une
    tranche (facteur 4 de sous-estimation = faux négatifs en série), zones non calibrées
    motif « hauteur définie par secteur graphique, non portable par le schéma v1 ».
    **Friction de schéma majeure — candidat v2 : hauteur par calque graphique.**
20. **Doctrines harmonisées A/B/C (arbitrage Vic, 28/07/2026)** :
    - la doctrine s'applique à TOUTE règle qui soustrait une part de la parcelle à la
      construction, quel que soit le vocabulaire employé (pleine terre, espace vert,
      perméable, paysager, éco-aménageable) → VALEUR GRAVÉE dans `pleine_terre_pct`,
      libellé exact en source verbatim : **c'est la fonction qui décide, pas le mot**
      (arbitrage final Vic 28/07/2026 — si 40 % de la parcelle sont en « espace vert
      paysager », stationnements compris, ces 40 % ne portent pas de bâtiment :
      l'emprise bâtie est bornée à 60 %). Seul cas d'exclusion : une règle qui
      n'empêche PAS de bâtir sur la surface visée — ex. ratio de plantation sur dalle
      ou en toiture.
    - Retraits en H/2 → valeur gravée = **max(H/2 à la hauteur maximale gravée, plancher
      du texte)**, fond du calcul en note.
21. **Signal de pré-vol ≠ preuve** (Cilaos NtoPOS→Nto) : un rattachement de famille
    proposé par le pré-vol reste une hypothèse — le corps du texte prime, sinon non
    calibrée.
22. **Rattachement d'un secteur muet à sa zone support** : uniquement si la règle
    générale « la règle de la zone s'applique aux secteurs sauf disposition particulière »
    est ÉCRITE dans le règlement (citée dans l'entrée) — sinon non calibrée.
    **Ligne de partage adoptée (Vic, 28/07/2026)** : elle n'est PAS « clause
    présente/absente » — les deux communes du cas d'école possèdent la clause — mais
    « **secteur déclaré couvert par la clause** vs **saut d'indice non écrit** ».
    Cilaos Ub1 : secteur cartographique d'une zone Ub, couvert par la clause générale
    des secteurs → rattachement VALIDÉ. Saint-Louis 1AUb1/1AUb2/2AUb1/2AUb2 : zones AU
    dont l'indice « b1 »/« b2 » ne correspond à aucune zone urbaine — le passage b1→b
    est une élimination non écrite que la clause (pourtant présente, p.4) ne couvre
    pas → rattachement REFUSÉ, zones non calibrées, motif « rattachement non fondé sur
    une clause du règlement, indice cartographique sans disposition écrite ». Repris
    en règle d'extraction au §4 (règle 5) du présent mandat-cadre.
23. **Schéma v1, manques récurrents constatés en série** (2e signalement après le
    Tampon) : `habitat: interdit` devrait primer sur le gate hauteur dans `resolve_zone`,
    et un vrai type « gel » devrait remplacer l'étiquette « secteur de transition »
    (utilisée pour capacité zéro exacte dans 6 communes sur 9 du lot B).
24. **Le repli générique n'est pas systématiquement optimiste : il est ARBITRAIRE**
    (doctrine reformulée par Vic, 28/07/2026, sur la mesure phase 4 — 18 communes).
    Il se trouve optimiste dans 17 cas sur 18 parce que 9 m est en dessous de la
    plupart des plafonds réunionnais, mais rien ne le garantit : Salazie est calibrée
    hé = 12 m (Art. U 10.2, p.13) → le repli y SOUS-estimait de 33 %, et les queues
    positives (+2 355 % Le Port Ud R+6, Art. Ud 8 p.68) montrent l'erreur dans les
    deux sens sur les petites parcelles denses. **L'argument du calibrage est
    l'EXACTITUDE, pas la correction d'un biais unidirectionnel** — on ne vend pas
    « on corrige une surestimation », on vend « on lit le règlement ». Tout
    durcissement uniforme du repli (mandat « Repli non optimiste » compris) doit être
    pensé avec ce contre-exemple en tête.

### À fusionner (sessions A et C)

Les leçons propres au lot A (PLU_NUIT_RAPPORT_A.md) et au verdict de contre-preuve
(PLU_NUIT_CONTREPREUVE.md) sont à verser ici par leurs sessions ou par Vic au moment
de la mise à jour post-nuit du §9 prévue par MANDAT_PLU_SERIE_NUIT.md §6.
