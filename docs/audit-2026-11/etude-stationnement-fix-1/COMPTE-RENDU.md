# ETUDE-STATIONNEMENT-FIX-1 — compte-rendu, lot par lot

Branche `fix/etude-stationnement-1` (depuis `origin/main`, le rapport d'audit y est mergé). Base locale
lue via `.env` copié de `labuse-main`. **LOTS 1 et 2 livrés ; ARRÊT demandé après le LOT 2.**

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

**Test** : `tests/test_etude_stationnement_fix_1.py` (8 cas, calculés à la main depuis le texte).
Suite implantation/étude rejouée : **135 passed**, aucune régression.

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
| **97416000HT0538** (Saint-Pierre Ud) | barème absent → **0 place**, enveloppe 888 m²/10 logts non bridée | barème **servi** (1 place / 75 m², tranche complète) → **l'esquisse se réduit à 5 logts, SDP 450 m², 6 places imposées = 6 dessinées** ; « Réussi » + condition lotissement individuel à vérifier | **le stationnement contraint l'esquisse** : là où l'enveloppe non bridée montait à 10 logts/888 m², elle redescend à 5 logts/450 m² une fois les places exigées **logées** |

> Lecture du cas Saint-Pierre : l'audit attendait « 12 places » **pour l'enveloppe de 888 m²** — enveloppe qui
> n'était atteignable que parce que le parking était ignoré. Le barème désormais actif **réduit le programme**
> (objet même du LOT 1) : à 450 m² de SDP, 6 places suffisent et sont dessinées. Si l'on force une SDP de
> 888 m², la règle exigerait bien ⌈888/75⌉ = 12 places — mais une telle SDP ne tient plus une fois ces
> 12 places logées sur 510 m². C'est exactement le comportement voulu : l'exigence borne l'esquisse.

**Témoin L'Étang-Salé** (barème non touché, non pilote) : **24 logts / 32 places imposées / 32 dessinées** —
**identique** (le barème UA par typologie n'a pas changé ; `exiger` reproduit la somme par logement des
barèmes sans ligne d'opération).

### Sondage pour Vic
`SONDAGE-10.md` — dix règles réingérées (valeur appliquée, citation, article/page) **accompagnées de
l'extrait verbatim de la page** lu en base, pour contrôle direct texte ↔ valeur.

### Interprétations faites (à relire) — on applique la plus exigeante et on l'écrit

1. **Le Tampon — deux lignes concurrentes.** Le tableau Ud12.2 porte à la fois « habitat collectif » (par
   pièces) ET « opération/lotissement > 5 lots ou logements : 1,5/logt ». Je les traite comme **lectures
   concurrentes** et retiens la **plus exigeante** (`retenue=max`). « > 5 » codé `logements_min=6` (strictement
   supérieur à 5). « dont au moins 0,5 place à l'extérieur » → **condition à vérifier** (non comptée).
2. **Le Tampon — social / foyer.** « prêt aidé : 1 place au maximum » → ligne sociale 1/logt (plafond lu comme
   taux social). « foyer/résidence sociale 1 pour 3 » **non modélisé** (relève des types senior/étudiant +
   plafond national L151-35).
3. **Saint-Pierre Ud — par m².** « 1 place / 75 m² de SDP » → `par_m2_sdp`, **tranche complète** (arrondi
   supérieur, car « comptabilisée par tranche complète »). « 1 place pour les logements locatifs sociaux » →
   ligne sociale **1/logt** (forfait lu comme taux). Ucv : « 0,85 place / logement social » → 0,85.
   « 0,5 place/parcelle pour les lotissements d'habitat individuel » → **condition à vérifier**.
4. **Les Avirons — max de deux formules.** Collectif = **max(1,25/logt ; 1 place / 35 m² de SDP)** ; le
   « 1 / 35 m² » est appliqué à la **SDP totale de l'opération** (lecture la plus exigeante du texte « par
   tranche de 35 m² de surface de plancher »). Individuel = 1,5/logt. « + 0,5 sur voie par terrain,
   lotissements > 5 lots » → **condition à vérifier** (forfait par terrain, non par logement).
5. **Saint-Benoît — visiteur conditionnel.** « 1 visiteur / 5 logts » ne s'applique qu'aux **opérations > 5
   logements** (`logements_min=6`). « aidés : 1 pour 2 » → ligne sociale **0,5/logt**. « résidences univ./âgées
   1 pour 3 » **non modélisé** (types senior/étudiant).
6. **Le Port — visiteur + aidé partiel.** « 1 visiteur / 100 m² de SDP » modélisé. « prêt aidé : 0,2/logt
   **+ 8 places / 1000 m²** » → ligne sociale 0,2/logt ; **la part « +8/1000 m² » n'est pas modélisée** (signalée,
   à compléter si un projet social est étudié au Port).
7. **SDP « par m² » = surface de plancher réelle** (modules + noyaux), pas la somme nominale des logements.

### Ce que je NE fais pas (hors pilote, en attente de relecture)
- Les 16 autres communes à texte en base (LOT 3), la référence d'article de Sainte-Suzanne (U15.2), les textes
  manquants (LOT 4), les deux manques d'enveloppe Saint-Denis/Saint-Benoît (LOT 5), le statut global et la
  régénération des PDF dans `~/Desktop/exports-audit-4/` (LOT 6).

**ARRÊT ici** — en attente de relecture avant les autres communes.
