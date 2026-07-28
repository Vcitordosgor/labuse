# PLU-SÉRIE-NUIT — RAPPORT SESSION A

> Lot A : consolidation Saint-Paul + 8 communes. Branche `feat/plu-nuit-a`.
> AUCUN accès base applicative de toute la session (mandat §4) — porte de sortie par
> commune : couverture 100 % des libellés du manifeste + script de re-vérification des
> citations (0 FAIL exigé) + chargement YAML sans erreur.

## Synthèse

| | |
|---|---|
| Phase 0 (pré-vol 17 communes) | 22:12 → 22:32 (commit `738b1b6`) |
| GO Vic + tâche 0 (conso Saint-Paul) | 22:36 → 22:47 (`be70749`) |
| 8 communes du lot | 22:48 → 23:29 |
| **Total exécution lot A** | **53 min (conso incluse), 8/8 communes traitées, 0 sautée** |
| Zones calibrées (8 communes) | **70 entrées** (dont 26 habitat-interdit sourcés) |
| Gels (2AU/3AU/AUst/AU0-like) | **32 libellés** via zones_au_st |
| Non calibrées motivées | A/N : 72 libellés · non-calibrables cités : UAv, AUAv, AUBm (La Possession), AUe (Entre-Deux) |
| Citations vérifiées script | **667 OK cumulées, 0 FAIL** (Saint-Paul 194, Saint-Joseph 147, Sainte-Marie 122, La Possession 137, Sainte-Suzanne 76, Étang-Salé 75, Salazie 63, Entre-Deux 30, Sainte-Rose 57 — moins recouvrements) |
| COS post-ALUR | AUCUN dans le lot A (les 4 détectés au pré-vol sont dans le lot B) |

## Détail par commune (horodatages = commits)

| Commune | Commit | Heure | Calibrées / interdites / gels / A-N | Points saillants |
|---|---|---|---|---|
| Saint-Paul (conso) | `be70749` | 22:47 | consolidation | **2 corrections de fond** : retrait zones éco 3→5 m (les « 3 valeurs sans source » de l'audit étaient FAUSSES) ; pleine terre 20→30/40 % sur U3b/c, U4b/c, U5b/c, U6b/c (l'ancien 20 % uniforme était OPTIMISTE sur les plus gros pools : U3c 2 730, U6c 2 642 parcelles servies). Usdu résolu (4 m/4 m, 2 pl./logt, perméable 50 %) ; emprise Usdu = plafonds ABSOLUS m² (friction v1, non portable) ; 5 citations habitat converties PDF→imprimée ; 48 pages ajoutées. |
| Saint-Joseph | `1b61e46` | 22:56 | 18 / 6 / 21 / 13 | Bassins U1-U6 à hauteurs PAR BANDES (précédent Saint-Paul U1a appliqué) ; U6 habitat interdit Y COMPRIS gardiennage ; 1/2/3AU (3 degrés d'ouverture) ; AUto/AUtok règles propres ; retraits H/2 → minimum gravé. |
| Sainte-Marie | `5cd538d` | 23:02 | 11 / 8 / 3 / 10 | Offset « ND » TRANCHÉ via table des matières (vigilance n°1). 3e style de format (moderne MUTUALISÉ par groupes). UAz 27/30 m (record île). Groupe activités : faîtage seul, % perméable non isolé → a_verifier motivé. 2AU « à partir de 2031 ». |
| La Possession | `a520369` | 23:08 | 14 / 5 / 1 / 10 | **UAa : secteur résidentiel à HABITAT INTERDIT** (Art. UA 1.2). **UEm : habitat ADMIS — divergence avec O12 « inféré », le règlement prime** (consigné). AUBm hauteur « R+3 » (niveaux) → friction v1, a_verifier (repli R+2 < R+3 réel : prudent). UAv hauteur PAR ÎLOT → a_verifier. |
| Sainte-Suzanne | `619661a` | 23:12 | 8 / 4 / 2 / 10 | UE habitat interdit SANS exception (pas même gardiennage — vérifié in extenso). UC1 = SDU loi ELAN (L.121-8, densification contrainte, notée). UAc commerce/services uniquement. |
| L'Étang-Salé | `af5f747` | 23:19 | 8 / 4 / 1 / 11 | Offset -1 TRANCHÉ via en-têtes (vigilance n°1). 4e style de format (« UA 2.4 »). Zone AU à règles PROPRES par secteur. Stationnement logements : tableau NON extractible → a_verifier motivé partout. AUs = réserve long terme gelée. |
| Salazie | `874f915` | 23:22 | 7 / 3 / 0 / 5 | Hauteurs à L'ÉGOUT SEUL (hf null). UA1 Hell-Bourg patrimonial 7 m/R+1. Aucune 2AU. |
| Entre-Deux | `78504e2` | 23:26 | 5 / 0 / 1 / 8+1 | **AUe SAUTÉE proprement** : matrice des destinations V/X illisible à l'extraction → statut habitat de Ue INDÉTERMINABLE sur pièces (invariant « jamais deviner ») ; lecture visuelle à faire au matin. |
| Sainte-Rose | `109f3c3` | 23:29 | 6 / 3 / 4 / 9 | Signal pré-vol « indices AU absents » LEVÉ par le renvoi d'indice (vigilance n°3 : rattachement lu dans le texte). 1AUto chapitre propre, tourisme interdit. |

## Frictions de schéma v1 rencontrées (aucune contorsion appliquée)

1. **Hauteur en NIVEAUX** (« R+3 », AUBm La Possession ; « sans dépasser R+1 » Salazie UA1 —
   ici doublé d'une valeur métrique, donc gravable) : le schéma ne porte que des mètres.
   a_verifier motivé quand la valeur métrique manque ; le repli générique (~R+2) sous-estime
   R+3 : sens prudent.
2. **Hauteur PAR ÎLOT opérationnel** (UAv/AUAv La Possession : tableau par îlot) → a_verifier.
3. **Emprise en PLAFONDS ABSOLUS m²** (Usdu Saint-Paul : 150/25/200/300 m² par destination) —
   déjà consignée au pilote (F1-bis), confirmée.
4. **Hauteurs par BANDES de profondeur** (Saint-Joseph U1/U2/U3/U5cvd) : précédent Saint-Paul
   U1a appliqué (bande profonde gravée, front en note) — convention à contre-vérifier par la
   session C.
5. **Retraits « H/2 avec minimum »** (Saint-Joseph, Sainte-Marie, La Possession…) :
   minimum plancher gravé, règle relative en note — **DÉSAVOUÉE par la contre-preuve puis
   par l'arbitrage Vic (28/07, doctrine b)** : le plancher seul sous-estime le retrait à
   hauteur max, donc SURESTIME la constructibilité. Convention corrigée partout :
   gravé = max(H/2 à la hauteur max de la zone, plancher) — cf. PLU_NUIT_HARMONISATION.md
   (49 valeurs lot A re-gravées).
6. **Tableaux perdus à l'extraction texte** : stationnement (Étang-Salé, La Possession UEm),
   matrice destinations V/X (Entre-Deux) → a_verifier/non-calibrage motivés, JAMAIS devinés.

## Nouveaux pièges pour le §9 du mandat-cadre

- **EN TÊTE DE §9 (décision Vic, 28/07/2026) — LE PRÉFIXE D'UN LIBELLÉ NE PROUVE RIEN.**
  UAa (La Possession) est un secteur *résidentiel* à habitat INTERDIT ; UEm (La Possession)
  est une zone *économique* à habitat ADMIS. Seule la lecture des articles 1/2 (destinations)
  tranche. **Conséquence structurante : l'usage naïf de la liste O12 PAR CODE est INVALIDÉ
  comme fondement du mandat « Repli non optimiste »** — la liste reste un indice de
  pré-identification, jamais une source ; le mandat devra s'appuyer sur les statuts habitat
  SOURCES des YAML calibrés (désormais disponibles pour 12+ communes) et non sur les codes.
- **L'île compte AU MOINS 4 styles de règlement** (ancien préfixé, moderne par chapitre,
  moderne mutualisé par groupe, sections « UA 2.4 ») — la détection du style est la première
  minute de chaque commune ; les 6 requêtes-clés (voies/limites/emprise/hauteur/perméable/
  stationnement) se transposent partout.
- **Les matrices de destinations V/X peuvent perdre leurs symboles** à l'extraction texte
  (Entre-Deux) : un chapitre « propre » peut cacher un statut habitat indéterminable — motif
  de non-calibrage, PAS de déduction.
- **Un secteur résidentiel peut interdire l'habitat** (UAa La Possession) et **une zone
  économique peut l'admettre** (UEm La Possession) : le préfixe du libellé ne prouve RIEN,
  seule la lecture d'Art. 1/2 tranche — la liste O12 « inféré » est un indice, jamais une
  source (1 divergence trouvée, consignée).
- **Degrés d'ouverture AU multiples** : 1/2/3AU (Saint-Joseph), 2AU-2031 (Sainte-Marie,
  Sainte-Suzanne), AUst-modification (partout), AUs-réserve (Étang-Salé) — tous portés par
  zones_au_st avec la condition citée.
- **Hauteur « fixée à N mètres » sans précision égout/faîtage** (Ud Sainte-Rose, UT/UAa
  La Possession…) : gravée en hf_m (prudent), notée.
- **offset de pagination : 4 méthodes** — vote de pieds de page, table des matières,
  en-têtes, en-têtes d'articles. Toujours résoluble ; 2 offsets « ND » du pré-vol tranchés.

## Reste à faire au matin (arbitrages / mesures)

1. **Entre-Deux AUe** : lire visuellement la matrice p.16-18 → statut habitat de Ue, puis
   calibrer AUe (5 min).
2. **Étang-Salé + La Possession (UEm)** : normes de stationnement en tableaux — lecture
   visuelle si on veut les résoudre (non bloquant, a_verifier honnêtes).
3. **La Possession UAv/AUAv** : plan des îlots opérationnels si disponible → hauteurs.
4. **Phase 4 groupée** (base) : golden 116 par branche, tiers au bit près, échantillons
   avant/après, écart repli/calibré par commune, pools servis par zone.
5. Divergence O12/règlement (UEm La Possession) → répercuter si besoin sur la liste O12
   (décision Vic).

Session A disponible pour renfort du lot B ou pour la phase C si Vic la réaffecte — sinon
travail terminé à 23:29, aucune commune sautée (1 zone sautée motivée sur ~150 traitées).
