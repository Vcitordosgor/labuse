# ETUDE-STATIONNEMENT-FIX-1 — compte-rendu, lot par lot

Branche `fix/etude-stationnement-1` (depuis `origin/main`, le rapport d'audit y est mergé). Base locale
lue via `.env` copié de `labuse-main`. **LOTS 1 et 2 livrés, puis CORRECTIF de relecture ; ARRÊT de nouveau
avant le LOT 3.**

---

## Correctif de relecture (6 points)

**1. Preuve par la page, pas par l'extrait.** Le `SONDAGE-10.md` est refait : chaque règle est prouvée par
une **image recadrée du tableau de la page officielle** (rendue au PDF opposable servi par le GPU,
`data/plu_reglements/<insee>_…pdf`, via pymupdf), plus la citation propre à la zone. L'extraction de base
perdait des cases de tableau (Saint-Pierre Uf : « place / logement » sans le 1,5 ; Le Tampon tronqué) — on ne
s'en sert plus pour la preuve. Toutes les valeurs appliquées **sont portées par leur image** ; aucune n'a eu
à repasser en « propose ».

**2. Le Port — destination.** L'image de la page 30 montre que le régime « aucune place sous 60 m² / 1 place
par tranche de 60 m² entre 60 et 500 m² / … » appartient aux destinations **commerce et activité de service**,
PAS à l'habitation. La ligne **Habitation / Logement** porte bien « **0,3 place par logement + 1 place visiteur
par tranche de 100 m²** » et la sous-ligne **prêt aidé** « 0,2 place/logement + 8 places / 1 000 m² ». Les
valeurs 0,3 / 0,2 / 8-pour-1000 sont prouvées sur l'image. Rien à réingérer : c'était la bonne lecture.

**3. Saint-Pierre Ucv — citation recopiée.** Corrigé : Ucv cite désormais **son** texte (« 0,85 place de
stationnement par logement social »), distinct de Ud (« 1 place pour les logements locatifs sociaux »).
Vérifié sur l'image de la page 72 : Ucv **ne porte pas** la clause « 0,5 place par parcelle pour les
lotissements » — elle a donc été **retirée** de Ucv. **Contrôle automatique ajouté**
(`test_controle_citation_identique_implique_regle_identique`) : aucune citation identique entre deux zones
sans que la **règle appliquée** soit identique — c'est exactement ce qui aurait attrapé ce bug (même phrase,
mais valeurs 0,85 ≠ 1).

**4. « Tranche complète » = arrondi inférieur.** Corrigé. Le texte Saint-Pierre dit « la place de stationnement
est comptabilisée par **tranche complète** » → seules les tranches entières comptent → **arrondi inférieur**
(888 m² ÷ 75 = **11**, pas 12). Le code `exiger` lit désormais le sens d'arrondi pour `par_m2_sdp` (plus de
`ceil` codé en dur). **Pour chaque règle par tranche, le sens d'arrondi est écrit avec la phrase qui le fonde**
(cf. SONDAGE-10). Texte muet → plus exigeant (**supérieur**), dit (ex. Avirons « 1 place / 35 m² » → supérieur).

**5. Interprétations complétées** — voir la liste ci-dessous (Saint-Pierre dispositions générales non
appliquées ; Avirons ligne sociale ajoutée + arrondi de la tranche de 35 m² ; Saint-Benoît arrondi de la
tranche de 5 logements).

**6. Sondage refait** : dix règles **distinctes** (aucune paire de zones au même texte), chacune avec l'image
qui porte chaque chiffre.

Principe tenu partout : jamais « Réussi » sans règle validée, citée, correspondant au programme dessiné.
Deux lectures possibles → la plus exigeante, écrite. Forme non modélisable → « Non vérifié » / « à vérifier »,
jamais « satisfait ».

---

## LOT 1 — le moteur sait porter les vraies règles

**`regles.py` — modèle de barème enrichi (rétro-compatible, formes facultatives) :**
- **Destination lue dans le type de projet** (`DESTINATION_PAR_PROJET`) : collectif/social/senior/étudiant/
  lotissement. Plus de `destination="collectif"` codé en dur ; threadé `moteur → _rechercher → _evaluer →
  calculer → _places_imposees`.
- **Formes ajoutées** : `par_m2_sdp` (« 1 place par tranche de N m² de SDP », **tranche complète** — enfin
  supportée) ; **sens d'arrondi lu dans la règle** (le plat n'impose plus « supérieur ») ; **places
  visiteurs** (par tranche de logements **ou** de m², avec seuil d'opération `logements_min`) ; **seuil
  d'opération** (ligne `logements_min`) ; **« la plus exigeante de deux formules »** (`retenue=max`) ;
  **ligne du logement social**.
- **Méthode `exiger(modules, destination, sdp_total)`** au niveau du PROGRAMME → `ExigenceStationnement`
  (places résident + visiteur, **formule retenue**, lectures écartées, **conditions non modélisables**,
  drapeau `couvert`). La surface « par m² » prend la **SDP réelle** (modules + noyaux, art. R.111-22), pas la
  somme nominale des logements.

**Application :**
- `capacite.calculer(type_projet)` ; `_places_imposees` passe par `exiger`. **`places_imposees = None` quand
  la règle ne couvre pas le programme** → le contrôle dit « Non vérifié », jamais « Réussi ».
- `Capacite` porte la formule retenue, la part visiteur, les conditions à vérifier.
- `controles.py` : le contrôle « Stationnement » affiche la **formule retenue** et la **lecture écartée** ;
  les **conditions non modélisables** (ex. « 0,5 place à l'extérieur ») sortent en ligne
  « Stationnement — condition à vérifier » (À confirmer), **jamais satisfaites**, et **bloquantes** pour
  « Exploitable ».
- **L'esquisse est contrainte** : `_evaluer` dessine `cible = places_imposees` ; un candidat dont les places
  ne tiennent pas échoue le contrôle → infaisable → le solveur réduit le programme (ou passe en sous-sol).
  Rien n'est compté « après coup ».

**Test** : `tests/test_etude_stationnement_fix_1.py` (9 cas, calculés à la main depuis le texte, dont le
contrôle « citation identique ⇒ règle identique » et l'arrondi des tranches). Suite complète rejouée sans
régression.

---

## LOT 2 — pilote sur cinq communes

Réingestion typée du stationnement de l'habitation, **zone constructible par zone**, depuis le **texte en
base** (verbatim), par un transform qui ne touche QUE le bloc `stationnement` des zones U/AU (le reste du
YAML est préservé). Blocs réécrits : **Le Tampon 9 · Saint-Pierre 11 · Les Avirons 14 · Saint-Benoît 5 ·
Le Port 8**. Chaque feuille garde article + page + citation verbatim.

### Preuve — AD0887 et HT0538 recalculées (moteur réel)

| Parcelle | Avant (audit) | Maintenant | Ce que devient l'esquisse |
|---|---|---|---|
| **97422000AD0887** (Le Tampon Ud) | 8 places, « Réussi » citant l'**habitat individuel** | **8 logts, SDP 795 m² → 12 places imposées** (opération > 5 : 1,5 × 8 ; lecture par typologie = **11** écartée) ; **12 dessinées** ; « Réussi » **+ condition « 0,5 place à l'extérieur » à vérifier** | mêmes 8 logts, mais **12 places** dessinées (au lieu de 8) ; verdict exploitable car la parcelle absorbe le parking |
| **97416000HT0538** (Saint-Pierre Ud) | barème absent → **0 place**, enveloppe 888 m²/10 logts non bridée | barème **servi** (1 place / 75 m², **arrondi inférieur**) → **l'esquisse se réduit à 5 logts, SDP 450 m², 6 places imposées = 6 dessinées** (450 ÷ 75 = 6 exact) ; « Réussi » + condition lotissement individuel à vérifier | **le stationnement contraint l'esquisse** : là où l'enveloppe non bridée montait à 10 logts/888 m², elle redescend à 5 logts/450 m² une fois les places exigées **logées**. *(Si la SDP valait 888 m², la règle exigerait ⌊888/75⌋ = **11** places — arrondi inférieur, correctif #4.)* |

> Lecture du cas Saint-Pierre : l'audit attendait « 12 places » **pour l'enveloppe de 888 m²** — enveloppe qui
> n'était atteignable que parce que le parking était ignoré. Le barème désormais actif **réduit le programme**
> (objet même du LOT 1) : à 450 m² de SDP, 6 places suffisent et sont dessinées. Si l'on force une SDP de
> 888 m², la règle exigerait bien ⌈888/75⌉ = 12 places — mais une telle SDP ne tient plus une fois ces
> 12 places logées sur 510 m². C'est exactement le comportement voulu : l'exigence borne l'esquisse.

**Témoin L'Étang-Salé** (barème non touché, non pilote) : **24 logts / 32 places imposées / 32 dessinées** —
**identique** (le barème UA par typologie n'a pas changé ; `exiger` reproduit la somme par logement des
barèmes sans ligne d'opération).

### Sondage pour Vic
`SONDAGE-10.md` — **dix règles distinctes** (valeur appliquée, citation propre à la zone, article/page,
sens d'arrondi fondé) **accompagnées d'une image recadrée du tableau de la page officielle** (`pages/*.png`)
qui porte chaque chiffre. Contrôle direct image ↔ valeur, sans dépendre d'un extrait de base.

### Interprétations faites (à relire) — on applique la plus exigeante et on l'écrit

1. **Le Tampon — deux lignes concurrentes.** Le tableau Ud12.2 porte à la fois « habitat collectif » (par
   pièces) ET « opération/lotissement > 5 lots ou logements : 1,5/logt ». Je les traite comme **lectures
   concurrentes** et retiens la **plus exigeante** (`retenue=max`). « > 5 » codé `logements_min=6` (strictement
   supérieur à 5). « dont au moins 0,5 place à l'extérieur » → **condition à vérifier** (non comptée).
2. **Le Tampon — social / foyer.** « prêt aidé : 1 place au maximum » → ligne sociale 1/logt (plafond lu comme
   taux social). « foyer/résidence sociale 1 pour 3 » **non modélisé** (relève des types senior/étudiant +
   plafond national L151-35).
3. **Saint-Pierre Ud — par m².** « 1 place / 75 m² de SDP » → `par_m2_sdp`. **Arrondi inférieur** car le texte
   dit « la place est comptabilisée par tranche complète » (correctif #4). « 1 place pour les logements locatifs
   sociaux » → ligne sociale **1/logt**. Ucv : « 0,85 place / logement social » → 0,85 (citation propre).
   « 0,5 place/parcelle pour les lotissements d'habitat individuel » → **condition à vérifier** (présente en Ud,
   **absente en Ucv** → retirée de Ucv).
   **Dispositions générales Saint-Pierre NON appliquées** (à vérifier au cas par cas) : « tout projet > 20 places
   → 20 % intégrées à l'ouvrage » (vérifiée p.93, non modélisée) ; d'éventuelles modulations « à proximité d'un
   transport collectif » ou « dispense des petites parcelles » **n'ont pas été retrouvées sur les pages Ud6
   (p.88-94)** — donc **non appliquées** et à confirmer, non inventées.
4. **Les Avirons — max de deux formules.** Collectif = **max(1,25/logt ; 1 place / 35 m² de SDP)** ; le
   « 1 / 35 m² » est appliqué à la **SDP totale de l'opération** (lecture la plus exigeante). Individuel =
   1,5/logt. **Ligne sociale AJOUTÉE** (correctif #5) : « prêt aidé, R.111-25 : 1 place au maximum par logement »
   → social 1/logt. **Arrondi de la tranche de 35 m² : texte muet → supérieur** (plus exigeant, dit). « + 0,5 sur
   voie par terrain, lotissements > 5 lots » → **condition à vérifier** (forfait par terrain).
5. **Saint-Benoît — visiteur conditionnel.** « 1 visiteur / 5 logts » ne s'applique qu'aux **opérations > 5
   logements** (`logements_min=6`). **Arrondi de la tranche de 5 logements : texte muet → supérieur** (⌈n/5⌉,
   plus exigeant). « aidés : 1 pour 2 » → ligne sociale **0,5/logt**. « résidences univ./âgées 1 pour 3 » **non
   modélisé** (types senior/étudiant + plafond national L151-35).
6. **Le Port — destination Habitation.** « 0,3/logt + 1 visiteur / 100 m² » est bien la ligne **Habitation /
   Logement** (le régime par surface 1/60 m² est celui du commerce/service, cf. correctif #2). Prêt aidé :
   « 0,2/logt **+ 8 places / 1000 m²** » → ligne sociale 0,2/logt ; **la part « +8/1000 m² » n'est pas modélisée**
   (signalée, à compléter si un projet social est étudié au Port). Visiteur muet → supérieur.
7. **SDP « par m² » = surface de plancher réelle** (modules + noyaux, art. R.111-22), pas la somme nominale des
   logements.
8. **Sens d'arrondi écrit pour chaque règle par tranche** (correctif #4) : explicite quand le texte le dit
   (Saint-Pierre « tranche complète » → inférieur), sinon **le plus exigeant (supérieur) et on le dit** (Avirons
   35 m², Saint-Benoît 5 logts, Le Port 100 m²).

### Ce que je NE fais pas (hors pilote, en attente de relecture)
- Les 16 autres communes à texte en base (LOT 3), la référence d'article de Sainte-Suzanne (U15.2), les textes
  manquants (LOT 4), les deux manques d'enveloppe Saint-Denis/Saint-Benoît (LOT 5), le statut global et la
  régénération des PDF dans `~/Desktop/exports-audit-4/` (LOT 6).

**ARRÊT ici** — en attente de relecture avant les autres communes.
