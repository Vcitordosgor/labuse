# PLU-SÉRIE-NUIT — RAPPORT SESSION B

> Session B, nuit du 27 au 28/07/2026. Clone `labuse-plu-b`, branche `feat/plu-nuit-b`
> (basée sur le commit de pré-vol `738b1b6`). AUCUN accès base applicative, AUCUNE API,
> AUCUN réseau : règlements lus depuis le cache local `/tmp/plu_nuit/reglements/`
> (9/9 md5 re-vérifiés conformes au tableau de pré-vol avant toute gravure).
> Outillage session : `/tmp/plu_nuit_b/` (extraction paginée PyMuPDF, script de
> re-vérification des citations — porte 4.b, smoke `resolve_zone` — portes 4.a/4.c).
> Push autorisé par Vic en cours de nuit (23 h 20 env.) pour alimenter la
> contre-extraction de la session C : branche poussée après chaque porte de sortie.

## SYNTHÈSE

**9 communes traitées / 9 — AUCUNE SAUTÉE.** 176 zones gravées (dont 40 en gel
capacité-zéro) / 130 libellés en non-calibrage motivé un par un. **872 citations
(article, page) re-résolues par script contre les PDF : 0 FAIL** (21 corrections de
citations avant PASS, toutes par relecture du PDF). 100 % de la surface U/AU des
9 manifestes est couverte par du calibré, à deux exceptions près documentées
(Uoap Le Port 7,2 ha — règles dans l'OAP hors règlement ; 1AUe Trois-Bassins 1,9 ha —
contradiction textuelle, arbitrage Vic). Les 3 COS post-ALUR du lot sont consignés
avec la date d'approbation du document, JAMAIS appliqués (+ 1 découvert à Saint-Louis,
doc modifié 09/07/2025). Premier commit 23:02, dernier 00:55 — **9 communes en 2 h 10**
(≈ 13-16 min/commune, porte de sortie et contre-vérification de session comprises).

| # | Commune | Statut | Commit (heure) | Zones cal. / non cal. | Habitat interdit | Gels (st) | % surface manifeste calibrée* | Citations (corr.) | md5 gravé | Alertes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Saint-Louis | GRAVÉE | `6c4cdec` (23:02) | 35 / 17 | UE, US, 1AUe, «1AUe oap1» | 10 (AUst = gel à modif. PLU, PAS transition) | 15,4 % (100 % du U/AU) | 155 (3) | `bae5ab70e6a8dc7697b2414fddf62145` | COS Art. AUst 14 « nul sauf 20 m² » — doc modifié 09/07/2025, consigné NON appliqué |
| 2 | Saint-Benoît | GRAVÉE | `cf1f2ea` (23:16) | 24 / 47 | Ue, Up, Ut, AUe3, AUp1 | 0 | 5,1 % (12,4 % hors Npnr ; 100 % du U/AU) | 161 (0) | `900a6c13641a4fd39b5bb65b71914f70` | **`pagination_citee: "pdf"`** (PDF composite à double numérotation) ; hauteurs par secteurs graphiques → tranche 4 m TRÈS conservatrice ; 53 STECAL caducs ELAN non calibrés |
| 3 | Petite-Île | GRAVÉE | `1fc6ba1` (23:30) | 20 / 14 | UE, UEa, UT, AUE, AUs, AUT | 5 (dont UF/UFcim/AUF sans hauteur → capacité zéro) | 13,4 % (100 % du U/AU) | 97 (4) | `19407563d46266104df408b837d67fc4` | O12 INFIRMÉES sur texte : UZ et 1AUz admettent l'habitat (ZAC) ; sommaire périmé |
| 4 | Le Port | GRAVÉE | `2a80525` (23:46) | 23 / 4 | Uem, Umi, Us, 1AUem, 1AUs (+ Ue/Up/Uppp/Uv en gel) | 10 | **81,9 %** (99,6 % du U/AU — Uoap 0,42 % exclue) | 85 (1) | `5df6eb00bd505c3f29154ce7f1d72cd5` | Uem = seul porteur de hauteur du chapitre Ue (≠ servitude type Tampon) ; 1AUm recul voirie `a_verifier` (lacune du règlement) |
| 5 | Les Avirons | GRAVÉE | `e456140` (23:58) | 21 / 6 | Ue, AUec, AUt, Ub4, Ud2 | 2 (AUes, Ub5) | 15,8 % (100 % du U/AU) | 120 (8) | `73a0f8f65869a65da5c666bf27ed91db` | O12 3/3 confirmées ; numéros de page en EN-TÊTE (vote pied-de-page aveugle) |
| 6 | Cilaos | GRAVÉE | `d224e73` (00:12) | 9 / 6 | aucune (pas de zone d'activité) | 1 (AUst) | 4,1 % (100 % du U/AU) | 49 (0) | `124d7e80e9c14db4194eedc021666062` | **Lettres doublées = artefact pypdf du pré-vol** : extraction PyMuPDF propre, 33 pages VÉRIFIÉES VISUELLEMENT au rendu image, zéro divergence ; COS doc 13/02/2024 consigné NON appliqué ; NtoPOS : graphie jamais écrite → non rattachée (signal pré-vol écarté) |
| 7 | La Plaine-des-Palmistes | GRAVÉE | `6ffcf78` (00:27) | 11 / 10 | Ue, AUe | 2 (AUs1, AUs2) | 6,9 % (100 % du U/AU) | 57 (0) | `533ce4c9aa4ba3acdcb3ee78a9317929` | PDF = 4 blocs concaténés, **couches texte fantômes** dans les notices (rezonage 2023 lisible en rendu image seulement) ; COS doc 27/05/2023 consigné NON appliqué |
| 8 | Bras-Panon | GRAVÉE | `5fd22b6` (00:41) | 19 / 10 | Ue, Udu, 1AUe, 1AUec+2AUec, 1AUt | 5 | 4,9 % (100 % du U/AU) | 90 (5) | `7032a0cc8d10ebf6d51ac167edd9e1ef` | Doc le plus récent de l'île (28/04/2026) ; 25-27 renvois TOUS résolus ; AUst (O12) requalifiée : gel total, PAS zone d'activité |
| 9 | Les Trois-Bassins | GRAVÉE | `359bb2c` (00:55) | 14 / 16 | Ue, 1AUt | 5 (2AUa/b/c, AUs, AUse) | 7,4 % (U/AU sauf 1AUe 1,9 ha) | 58 (0) | `c3d7e7fd26ba985cf7bb8e5a14bb4534` | COS doc 2017 modifié 02/06/2022 consigné NON appliqué ; **1AUe non calibrée : contradiction destinations** (arbitrage Vic) |

\* % de la SURFACE du manifeste (proxy sans base — le pool servi en parcelles sera mesuré
en phase 4) ; numérateur = zones calibrées + habitat-interdit calibré + gels capacité-zéro.
Les faibles % s'expliquent par le poids A/N (Npnr Saint-Benoît : 13 489 ha à lui seul) ;
la ligne de partage produit est : TOUT le U/AU est calibré ou gelé-exact, le A/N est en
repli générique non constructible sur décision motivée (modèle Tampon), verdict correct.

Détail des motifs de non-calibrage : chaque YAML porte ses motifs zone par zone
(bloc `zones_non_constructibles` / `zones_non_calibrees`), plafonds STECAL cités
(SDP/emprise par fiche ou article). Aucun libellé orphelin silencieux : smoke
`resolve_zone` passé sur les 305 libellés cumulés des 9 manifestes.

## LES 4 POINTS DE VIGILANCE DU MANDAT — TOUS TRAITÉS

1. **Offset Saint-Benoît (ND au pré-vol)** : résolu AVANT gravure — mais l'hypothèse
   s'est inversée en cours d'analyse : le vote massif (+48, 130 voix) désignait le cahier
   d'ANNEXES « Page N sur 114 » (PDF 49-162) ; le règlement écrit est le bloc PDF 1-48,
   auto-paginé « Page N sur 49 ». Double numérotation imprimée ⇒ branche prévue par le
   mandat : **gravure en pagination PDF explicite**, champ `pagination_citee: "pdf"` posé
   + en-tête explicatif. Aucun mélange de référentiels.
2. **Cilaos lettres doublées** : artefact de l'extracteur pypdf du pré-vol. L'extraction
   PyMuPDF de la session est propre ; par précaution mandat, TOUTES les valeurs chiffrées
   gravées ont été confirmées visuellement (rendu PNG de 33 pages, liste page → valeur au
   rapport d'extraction). Zéro divergence texte/visuel. Commune NON sautée, qualité pleine.
3. **Graphies pattern pré-vol jamais inférées** : appliqué 9 fois. Cas d'école :
   Bras-Panon (« 1AUec » rattaché car « zones 1AUec » et la typologie 1AU/2AU sont
   ÉCRITES p.75/p.6) ; contre-exemples honorés : NtoPOS (Cilaos) jamais écrite → non
   rattachée malgré le signal pré-vol « NtoPOS→Nto » ; 1AUe (Trois-Bassins) non calibrée
   sur contradiction ; 1AUb1/1AUb2 (Saint-Louis) et Ub1 (Cilaos) rattachés UNIQUEMENT
   parce que la règle générale « la règle de la zone s'applique aux secteurs sauf
   disposition particulière » est écrite dans le texte (citée dans chaque entrée).
4. **Les 3 COS post-ALUR du lot** (Cilaos 13/02/2024, Plaine-des-Palmistes 27/05/2023,
   Trois-Bassins 02/06/2022) : consignés en tête de YAML avec la date d'approbation du
   document, valeurs citées verbatim (Art. AUst/AUs 14 « nul sauf 20 m² » à Cilaos et
   PdP ; « il n'est pas fixé »/« sans objet » partout ailleurs), JAMAIS appliqués — les
   gels gravés reposent sur les Art. 1.2/2.2, indépendants du COS. **+ 1 hors liste** :
   Saint-Louis (doc modifié 09/07/2025), même traitement. Saint-Benoît/Petite-Île/
   Le Port/Les Avirons/Bras-Panon : 0 occurrence, re-vérifié et consigné.

## FRICTIONS SCHÉMA V1

- **F2 en série (6 communes sur 9)** : le seul véhicule de « capacité zéro exacte » reste
  `zones_au_st`, dont l'étiquette moteur « secteur de transition » est inexacte pour des
  gels 2AU/AUst à modification de PLU et, pire, pour des zones U pleines à habitat
  interdit SANS hauteur chiffrée (UF/UFcim/AUF Petite-Île ; Ue/Up/Uppp/Uv + renvois
  Le Port). Sans cela, une zone calibrée sans hauteur retombe en générique 9 m avec
  habitat non contraint (capacité fictive dans un cimetière ou un port). **Le schéma v1
  mériterait : `habitat: interdit` prioritaire sur le gate hauteur dans `resolve_zone`,
  et un vrai type « gel »** (2e signalement après le Tampon).
- **Hauteur par calque graphique hors manifeste** (Saint-Benoît : 15/13/10/7/4 m selon
  secteurs repérés au document graphique) : aucun véhicule — tranche la plus conservatrice
  gravée (4 m) avec sous-estimation forte assumée en centre-ville. Le manifeste ne porte
  pas les secteurs graphiques ; croiser le règlement graphique serait un mandat à part.
- **Pleine terre** : 8 règlements sur 9 ne connaissent que le « % espace vert et
  perméable » (stationnements parfois comptabilisables) sans sous-minimum de pleine
  terre → `pleine_terre_pct: null` + note partout, sauf dérivation arithmétique écrite
  (Le Port « 30 % dont au moins 50 % de pleine terre » → 15 % gravé, calcul documenté).
- **Hors schéma, porté en notes/`regles_transverses`** : densités MINIMALES AU (Saint-Louis,
  Les Avirons 30/20 logts/ha), mixité sociale à seuils (Saint-Louis 30 %/20 % à
  2 000/1 500/1 000 m²), stationnement à tranches par SDP du logement (Bras-Panon),
  hauteur « absolue » sans couple égout/faîtage (AUec 18 m → `hf_m` + note).
- `a_verifier` utilisé UNE fois sur tout le lot (recul voirie 1AUm Le Port — le renvoi
  d'indice pointe une zone « Um » qui n'existe pas : lacune du règlement, pas d'analogie).

## NOUVEAUX PIÈGES → à verser au §9 du mandat-cadre

1. **PDF composite à double pagination imprimée** (Saint-Benoît) : le vote d'offset
   majoritaire peut désigner le mauvais bloc (annexes auto-paginées). Toujours identifier
   CE QUE numérote le bloc gagnant avant de trancher ; en double référentiel → pagination
   PDF explicite, jamais de mélange.
2. **Numéros de page imprimés en EN-TÊTE** (Les Avirons, Cilaos, Bras-Panon,
   Trois-Bassins) : un vote de pied de page rend 0 sur des documents proprement paginés.
3. **Couches texte fantômes** dans les notices de modification concaténées
   (Plaine-des-Palmistes) : le texte extrait superpose deux documents ; le contenu
   normatif (rezonage AV 613) n'était lisible qu'en rendu IMAGE des pages.
4. **Le pré-vol pypdf peut mentir dans les deux sens** : lettres doublées fantômes
   (Cilaos — PyMuPDF propre) ET alerte COS d'abord invisible pour la session (regex
   trop stricte : les règlements écrivent « coefficient d'occupation DU SOL », pas
   « des sols », avec apostrophe typographique). Le compteur COS de l'outillage a été
   corrigé en cours de nuit ; re-grep manuel systématique par commune ensuite.
5. **Chapitre AU à destinations PROPRES + renvoi d'indice général** (Trois-Bassins) :
   les Art. 1/2 du chapitre peuvent CONTREDIRE la zone U d'indice (1AUe : le chapitre
   admet l'habitat, Ue l'interdit). Vérifier si les Art. 1/2 du chapitre AU sont un
   renvoi ou un contenu autonome AVANT de propager un habitat-interdit. En contradiction :
   non-calibrage, arbitrage sur pièces.
6. **Renvois de hauteur asymétriques introduits par modification** (Trois-Bassins :
   AUa→Uaa, le secteur et non la zone support) : chercher les renvois article par
   article, pas seulement le renvoi de tête de chapitre.
7. **Dans un chapitre à secteurs, l'article hauteur peut ne fixer QUE le secteur**
   (Le Port : Ue 8 ne fixe que Uem) — vérifier le PDF brut avant de conclure à une perte
   d'extraction ; la zone support reste alors sans hauteur (→ gel exact, cf. F2).
8. **STECAL à caducité légale datée** (Saint-Benoît : ELAN 31/12/2021 + condition
   « prise en compte Préfet/SCOT » invérifiable sans source externe) : seul le
   non-calibrage motivé est honnête.
9. **Sommaire périmé après modifications successives** (Petite-Île : queue de sommaire
   décalée de 10-23 pages) : ne jamais citer une page depuis le sommaire, toujours le corps.
10. **Convention de citation des sous-alinéas** : le vérificateur ne résout pas les
    jetons à 3 niveaux (« 2.2.7 ») → citer « Art. X 2.2 (al. 7) » d'emblée (21 corrections
    de citations sur le lot, dont la moitié sur ce motif ou sur des articles à cheval sur
    2 pages → citer la plage « p.12-13 »).

## RESTE À FAIRE AU MATIN (commune par commune)

- **Toutes** : mesures phase 4 en fenêtre groupée (golden 116/116, tiers, échantillons
  10 parcelles, écart repli/calibré 400 parcelles/commune — RIEN lancé cette nuit) ;
  merges `--no-ff` par Vic ; verdict de la contre-extraction session C.
- **Saint-Louis** : valider la décision 1AUb1/1AUb2/2AUb1/2AUb2 → règles UB (secteurs
  jamais écrits, règle générale citée) ; hauteur OAP2 (17/20 m) volontairement non gravée
  (pas de suffixe oap2 au manifeste) ; bonus « 40 % des constructions à +2 m ≥ 4 000 m² »
  non gravé (conservateur).
- **Saint-Benoît** : ARBITRAGE le plus lourd du lot — hauteurs gravées à la tranche 4 m
  (égout) alors que les secteurs graphiques montent à 15 m : sous-estimation assumée,
  piste = mandat « règlement graphique » ; STECAL Ns/Nta/Ntb : statut préfet/SCOT à
  vérifier si Vic veut les ouvrir.
- **Petite-Île** : valider UZ/1AUz habitat admis (2 candidates O12 infirmées sur texte) ;
  UF/UFcim/AUF en st-liste (capacité zéro exacte, étiquette inexacte).
- **Le Port** : Uoap (0,42 % de surface) calibrable en lisant l'OAP « Portes de l'océan »
  (pièce n°4, hors règlement) si souhaité ; 1AUm recul voirie `a_verifier`.
- **Les Avirons** : rien de bloquant (Ud1 régime ELAN/CDNPS en note).
- **Cilaos** : valider Ub1 → règles Ub (libellé jamais écrit, règle générale des secteurs
  citée p.5) ; NtoPOS non rattachée (sans enjeu de capacité, famille N).
- **La Plaine-des-Palmistes** : rien de bloquant (structure 4 blocs documentée en YAML).
- **Bras-Panon** : valider la convention hauteur absolue → `hf_m` (AUec 18 m) ;
  stationnement gravé 1 pl/logt (tranche 1,5 ≥ 100 m² en note).
- **Les Trois-Bassins** : TRANCHER 1AUe (1,9 ha) — les deux lectures et les passages
  verbatim sont dans `zones_non_calibrees` du YAML.

## NOTES DE SESSION

- Le mandat-cadre `MANDAT_CADRE_PLU_instance_saint_pierre.md` est INTROUVABLE dans ce
  clone, dans l'historique git et sur le disque : le §9 a été reconstitué via les
  invariants du mandat de nuit + les rapports Saint-Pierre/Tampon (leçons appliquées :
  destinations d'abord, préambules porteurs de droit, renvois explicites pour préfixes
  chiffrés, null sourcé, F2). À rebrancher au dépôt.
- Méthode d'exécution : un agent d'extraction par commune (contexte vierge, brief
  commun `/tmp/plu_nuit_b/BRIEF_AGENT.md` portant invariants + leçons accumulées,
  enrichi commune après commune), porte de sortie re-jouée par la session elle-même
  (verify_citations + smoke) AVANT chaque push — double contrôle systématique.
- Horodatage : session démarrée ~22 h 40, premier commit 23:02:09, dernier commit
  commune 00:55:05 ; heure de fin (rapport compris) : voir commit du présent fichier.

---

## ANNEXE — ARBITRAGES DU MATIN (28/07/2026, appliqués sur instruction de Vic)

1. **Saint-Benoît, hauteurs par secteurs graphiques** (`f55416a`) : la tranche 4 m est
   retirée. 19 zones habitat-admis passées NON CALIBRÉES (motif : « hauteur définie par
   secteur graphique, non portable par le schéma v1 ») : Ua, Uap, Ub + AUa5/8/9/18 +
   AUb2/6/7/10-17/19 — 67 polygones, 1 064,9 ha (Ua 230,8 · Uap 21,4 · Ub 773,3 ·
   AU 39,4). 5 zones habitat-interdit (interdiction TEXTUELLE) en capacité zéro exacte
   via st-liste : Ue, Up, Ut, AUe3, AUp1 — 9 polygones, 107,0 ha. Le nombre de PARCELLES
   concernées exige la base (interdite) : mesure en phase 4. Friction de schéma majeure
   consignée au §9 (candidat v2 : hauteur par calque graphique).
2. **Harmonisation doctrines A/B/C** (`7fd6244`) : % perméable gravé avec libellé
   verbatim sur **79 zones** (Saint-Louis 23, Le Port 5, Les Avirons 19, PdP 9,
   Bras-Panon 14, Trois-Bassins 9 ; Cilaos 0 — « espace vert paysager », pas une règle
   perméable, note posée ; Petite-Île 0 — valeurs déjà en vraie pleine terre) ;
   retraits H/2 réalignés sur max(H/2 à hauteur max, plancher) sur **13 zones**
   (Bras-Panon : Ua 5 m, Ub/Uba/Uc 4 m, Ud/Udu 3,5 m, 1AUa 5, 1AUb/1AUc 4, 1AUd 3,5,
   1AUec 9 — hauteur absolue 18 m, habitat interdit —, 1AUt 5 ; Trois-Bassins : Ue 5 m).
   Portes re-jouées : 614 citations 0 FAIL, 8 YAML rechargés, smoke conforme.
3. **Mandat-cadre** : original INTROUVABLE partout — déposé en RECONSTRUCTION explicite
   (`docs/mandats/MANDAT_CADRE_PLU_instance_saint_pierre.md`) : §§1-8 en squelette à
   restaurer par Vic, §9 peuplé (8 leçons pilote/Tampon sourcées + 15 ajouts nuit B).
4. **En attente d'arbitrage Vic (inchangés, consignés au YAML)** : 1AUe Trois-Bassins
   (contradiction de destinations, deux lectures verbatim dans `zones_non_calibrees`) ;
   rattachements par règle générale — Cilaos Ub1 (Titre I, p.5 : « la règle générale de
   la zone s'applique à chacun [des secteurs] sauf lorsqu'une disposition particulière
   est prévue ») et Saint-Louis 1AUb1/1AUb2/2AUb1/2AUb2 (aucun secteur UB1/UB2 au
   règlement, liste des zones p.5-6, caractère UB p.24 : indice « b » → règlement UB,
   sous-numérotation cartographique).

5. **Arbitrages finaux de Vic (28/07/2026, seconde passe)** : Saint-Benoît VALIDÉ tel
   quel · 1AUe Trois-Bassins RESTE non calibrée (« je ne tranche pas, et c'est la
   réponse » — à poser à la commune, consigné au YAML) · rattachements : Cilaos Ub1 GO,
   Saint-Louis 1AUb1/1AUb2/2AUb1/2AUb2 REFUSÉS — passées non calibrées, motif
   « rattachement non fondé sur une clause du règlement, indice cartographique sans
   disposition écrite » ; pool concerné : 28 polygones, 37,5 ha (1AUb1 7/7,1 ·
   1AUb2 12/20,8 · 2AUb1 1/2,0 · 2AUb2 8/7,6 ; parcelles en phase 4) ; 2AUb1/2AUb2
   sortent aussi du gel 2AUindicée (même rattachement d'indice non écrit) ·
   harmonisation VALIDÉE, y compris le non-gravage Cilaos (la doctrine perméable ne
   s'applique qu'aux règles qui bornent réellement l'emprise constructible — un
   stationnement comptable n'est pas du bâti). DÉCOUVERTE en appliquant le refus
   Saint-Louis : la clause générale des secteurs y EXISTE aussi (p.4 imprimée) — elle
   ne sauve pas le rattachement (elle vise les secteurs déclarés d'une zone, pas le
   saut d'indice b1→b d'une zone AU), mais la distinction Cilaos/Saint-Louis est plus
   fine que « clause présente/absente » : signalé à Vic, précision versée au §9.
6. **⚠ CONTRADICTION OUVERTE — classe « paysager » (à trancher par Vic)** : deux
   décisions opposées coexistent, toutes deux de Vic, le 28/07 au matin. (a) Message à
   la session B : « un stationnement n'est pas du bâti (…) je me range à ta lecture,
   ne grave pas » — la doctrine perméable ne s'applique qu'aux règles qui bornent
   réellement l'emprise constructible. (b) Commit `4890058` (Vic, 08:14:39, poussé sur
   la branche B) : GRAVE la classe paysager (Cilaos Ua/Uah 10, Ub/Ub1/AUb/AUb1 40,
   AUb2 30 ; Saint-Louis UZ 25) au motif « un % de parcelle sans bâti est une
   contrainte d'emprise réelle, quel que soit le traitement de surface ». La session B
   n'a PAS annulé le commit (jamais écraser un arbitrage poussé) : l'état de branche
   applique (b), le §9 (leçon 20) et l'annexe 5 documentent (a). Les deux lectures
   sont défendables — dernier mot à Vic ; portes re-vérifiées sur (b) : 0 FAIL.

7. **Contradiction « paysager » RÉSOLUE (Vic, 28/07/2026)** : le commit `4890058`
   TIENT — la classe paysager reste gravée (Cilaos Ua/Uah 10, Ub/Ub1/AUb/AUb1 40,
   AUb2 30 ; Saint-Louis UZ 25), rien n'est reverté. La seconde position (« ne grave
   pas ») était fausse : si 40 % de la parcelle sont soustraits à la construction,
   l'emprise bâtie est bornée à 60 % quel que soit l'usage de ces 40 %. Doctrine
   finale au §9 (leçon 20) : c'est la FONCTION qui décide, pas le mot — seule
   exclusion, une règle qui n'empêche pas de bâtir sur la surface visée (plantation
   sur dalle/toiture). Leçon 22 reformulée dans les termes adoptés (« secteur déclaré
   couvert par la clause » vs « saut d'indice non écrit »). Mandat-cadre : §§0-8
   restaurés depuis la copie de Vic, §9 vivant conservé intégralement.

8. **Suites d'arbitrage (28/07, seconde vague)** : (a) Bras-Panon AUec — règle 8
   appliquée, he = hf = 18 (90 citations 0 FAIL re-vérifiées). (b) Gel vs
   habitat-interdit TRANCHÉ SUR MESURE : test local pur Python (YAML jetable, zéro
   accès base) — une zone calibrée habitat-interdit SANS hauteur chiffrée rend
   `calibree=False, habitat=None, he=9.0, constructible_neuf=True` : `resolve_zone`
   (plu_rules.py, gate `_has_usable_height` en mode progressif) substitue le
   générique AVANT `engine.py:157`. Leçon 15 confirmée, pratique de la nuit
   maintenue, exception explicite ajoutée à la règle 10 du §4 du mandat-cadre,
   exigence v2 de premier rang. (c) Bras-Panon Ub, tiroir 8/11 vs 10/13 : verbatim
   remis à Vic — le critère de partage est un seuil d'assiette de PROJET (≥ 2 000 m²,
   hors secteur Uba), pas un secteur géographique ; la branche gravée 8/11 est la
   règle générale (majoritaire ET conservatrice coïncident) — arbitrage Vic sur
   pièces en attente.
9. **Analyses du matin (28/07, demande Vic)** → `PLU_NUIT_ANALYSES_MATIN_B.md` :
   les 18 zones « plafond unique » avec verbatims classés en 2 catégories (dont une
   double clause concurrente découverte à La Possession UApsfr2, p.16) · les 15 zones
   `a_verifier` he+hf (pool = phase 4, proxy surface fourni) · les 14 zones
   habitat-interdit logées en st pour la raison mesurée (Le Port 6, Saint-Benoît 5,
   Petite-Île 3 — périmètre de migration v2) · la table des 89 emprises implicites
   (100 − % soustrait), documentée SANS application. Rien appliqué aux YAML.

10. **Clôture des arbitrages (28/07)** : CAT 2 Saint-Denis — he reste null (décompte
    corrigé 18) · La Possession UApsfr2 → a_verifier (deux clauses concurrentes p.16-17,
    verbatims consignés au YAML — leçon §9-24) · les 89 emprises implicites VERSÉES au
    MANDAT_REPLI_NON_OPTIMISTE §5.c (3e population, mesure d'impact + tiers servis avant
    toute implémentation) · réconciliation strict/progressif gravée en leçon de méthode
    (§9-25) · reclassement Petite-Île : solution « entrées C en clé documentaire inerte »
    validée par Vic. Rien d'autre avant la phase 4.
