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

---

## Lots 3 à 6 (enchaînés) + quatre règles permanentes

### Quatre règles permanentes (appliquées aussi aux 5 pilotes)
1. **Couverture complète** — `scripts/stationnement_couverture.py` → `COUVERTURE.md` : chaque zone U/AU des
   24 communes porte une règle ingérée (synthèse) OU une **raison précise** (habitat interdit · habitat
   secondaire/usage non principal · renvoi à la zone mère · texte absent de la base). **Plus aucun « None ».**
   Zones à habitat PRINCIPAL sans barème : **0**. (Saint-Pierre Us sortait « None » au sondage précédent parce
   que la zone n'avait pas de bloc ; elle relève des secteurs servis par Uf6/renvoi — tracée dans la couverture.)
2. **Toute la ligne du tableau, toutes les colonnes** — la colonne « part en ouvrage » du Port est lue :
   `places_integrees` (100 % pour le logement, au-delà de **1 000 m² en Ua/Ub/Uc, 500 m² en Ud**, verbatim
   p.30/73) → **condition BLOQUANTE** « places à intégrer à la construction, plein air exclu au-delà du seuil ».
3. **Arrondi : d'abord l'en-tête et les dispositions générales** — Avirons : l'en-tête dit « arrondi à l'entier
   **supérieur** » → cité comme tel (plus « muet »). « Muet → plus exigeant (supérieur) » n'est écrit qu'après
   avoir lu en-tête + ligne + dispositions générales (Saint-Benoît tranche de 5, Avirons tranche de 35 m²).
   Saint-Pierre « tranche complète » → **inférieur**.
4. **Résidences seniors / étudiantes** — lignes dédiées ingérées et lues par destination : Saint-Pierre
   **0,3 (Ud) / 0,2 (Ucv) place par hébergement** ; Le Tampon & Saint-Benoît **1 place pour 3** ; Le Port
   **0,3 place par chambre**. Le plafond national L151-35 ne remplace plus le barème quand le PLU sert la
   destination (il reste la garde plus favorable). Sans ligne dédiée → destination « Non vérifié ».

### Lot 3 — communes à texte en base
12 communes réingérées en formes typées depuis le verbatim (Bras-Panon, Entre-Deux, Petite-Île, La Possession,
Saint-Joseph, Saint-Louis, Sainte-Marie, **Sainte-Rose**, **Sainte-Suzanne — article corrigé U15-15.2 (pas U13)**,
Salazie, Trois-Bassins, Cilaos) : tranches de surface/pièces, visiteurs, seuils d'opération, social, senior/étudiant,
arrondi d'en-tête. *Saint-Paul : barème par secteur déjà servi, trop de variantes/`propose` → lot ultérieur (dit).*
**Sondage du lot 3** : `SONDAGE-10-LOT3.md` — 10 règles tirées à **graine fixe** (commande écrite dans le fichier),
chacune avec l'**image de sa ligne entière**. (Deux vérifiées à la main ici : Bras-Panon Ub et Saint-Joseph 1AU3 —
images conformes au tableau.)

### Lot 4 — textes manquants
L'Étang-Salé (extraction partielle), Saint-André, Saint-Leu (absents), l'annexe de La Plaine-des-Palmistes, les
dispositions générales XVII de Saint-Denis : **le texte reste introuvable en base** pour le stationnement. Ces
communes/zones restent **« Non vérifié »** et c'est dit (colonne « texte absent » de `COUVERTURE.md`). La
réingestion par le chemin d'ingestion (rejouable en prod) de ces PDF/annexes est le reliquat de ce lot.

### Lot 5 — manques d'enveloppe et libellés
- **Saint-Denis pleine terre INGÉRÉE** depuis le texte : **UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat/Ua 15 %**
  (article U*.13, « % de l'unité foncière laissée libre de toute construction »).
- **Saint-Benoît hauteur** : fixée par **secteur graphique** (15/13/10/7/4 m à l'égout) → reste **« Non vérifié »**.
  *Cadrage pour un mandat dédié* : ingérer la couche graphique « secteurs de hauteur » (document graphique),
  l'intersecter à la parcelle, en déduire le plafond applicable — non chiffrable depuis le seul règlement écrit.
- **Libellé « Non réglementé »** : nouveau chemin (`Regle.absent`, silence prouvé) → le contrôle Emprise affiche
  **« non réglementé (silence prouvé) »** (sans objet), plus « Non effectué ». Marqué sur **Le Tampon** (Ud9
  « Non réglementée », 9 zones). À étendre aux autres zones vérifiées (Salazie, Sainte-Suzanne U7, Saint-Paul,
  La Possession UA/UB, Entre-Deux Ub/Ue) par le même marqueur `emprise_sol.ces.absent`.

### Lot 6 — statut et preuve finale
- **Statut global** : une Étude n'est « Exploitable » que si tous ses contrôles durs reposent sur une règle
  validée correspondant au programme ET qu'aucune condition non modélisable ne reste à vérifier — sinon
  **« À compléter » (esquisse à vérifier)**. C'est désormais le cas des deux témoins (condition « 0,5 extérieur »
  du Tampon / « lotissement individuel » de Saint-Pierre → verdict **À compléter**, pas « Exploitable »).
- **« Surface à retenir »** inchangée : toujours la plus prudente des deux grandeurs (règle existante, non touchée).
- **Études régénérées** dans `~/Desktop/exports-audit-4/` (`08-etude-faisabilite.html` + `08b-stationnement-regenere.json`) :

  | Parcelle | Programme | Places imposées / dessinées | Formule | Verdict |
  |---|---|---|---|---|
  | **97422000AD0887** (Le Tampon Ud) | 8 logts, R+1 | **12 / 12** | 1,5/logt × 8 (opération > 5), arrondi inférieur ; typologie = 11 écartée | **À compléter** (condition 0,5 extérieur à vérifier) |
  | **97416000HT0538** (Saint-Pierre Ud) | 5 logts, R+4 | **6 / 6** | 1 place / 75 m² · SDP 450 m², arrondi inférieur | **À compléter** (condition lotissement à vérifier) |

### Liste des interprétations (cumulée)
- **« > 5 »** = ≥ 6 logements (strictement supérieur à 5).
- **Avirons / Trois-Bassins** « 1 / 35 m² » appliqué à la **SDP totale de l'opération** ; arrondi **supérieur**
  (en-tête « entier supérieur » aux Avirons ; muet → supérieur à Trois-Bassins). Plafond collectif « 2/logt »
  (Trois-Bassins) porté en condition (le moteur n'a pas de plafond par-logement).
- **Saint-Pierre** « tranche complète » → **inférieur** ; dispositions générales NON appliquées (« > 20 places →
  20 % en ouvrage », vérifiée p.93 ; modulations transport/petites parcelles non retrouvées → non appliquées, dit).
  Hébergement **0,3 (Ud) / 0,2 (Ucv)** par hébergement. Ligne sociale **1 (Ud) / 0,85 (Ucv)** par logement social.
- **Senior/étudiant « 1 pour 3 »** encodé **0,3333 place/logt**, arrondi supérieur (muet).
- **Social** = destination dédiée : Avirons/Le Tampon **1 max** (R.111-25) ; Le Port **0,2/logt** (la part
  « + 8 places / 1 000 m² » n'est pas modélisée, signalée) ; Petite-Île **LLTS = 0 place**.
- **Saint-Benoît** visiteur « 1 / 5 logts » seulement **au-delà de 5 logements**, arrondi **supérieur** (muet).
- **SDP « par m² »** = surface de plancher réelle (modules + noyaux, art. R.111-22).
- **Sainte-Suzanne** : article corrigé **U15-15.2** (U13 = continuités écologiques).

### Garde-fou ajouté
`test_controle_citation_identique_implique_regle_identique` étendu à **toutes les communes** (0 violation) :
aucune citation partagée entre deux zones sans règle appliquée identique.

**Reliquat assumé et dit** : lot 4 (réingestion pipeline des textes manquants), Saint-Paul, extension du libellé
« Non réglementé » aux autres communes vérifiées, et le mandat dédié « hauteur par secteur graphique » de Saint-Benoît.

---

## Relecture (2e tour) — refus, contrôle des pages, corrections ciblées

### Fait et vérifié
- **Refus immédiat des parcelles non constructibles** (audit écrans, 97404000AM0838) : l'Étude lit le
  **même verdict partagé** (`potentiel_batir`) que Dossier/Gabarit/pré-dossier et **refuse tout de suite,
  avec le motif, sans lancer le solveur** — habitat interdit, zone rouge PPR, zone fermée, A/N. AM0838 →
  « Habitat interdit dans cette zone » en 0,6 s (avant : 108 s puis « au mieux ~95 logements »). Parcelle
  naturelle → « Zone non constructible — naturelle ». 2 tests (refus sans solveur ; solveur atteint si
  constructible).
- **Contrôle dur des pages** (`scripts/stationnement_controle_pages.py`, + test) : chaque chiffre appliqué
  **et** la citation doivent se retrouver dans le texte de **sa** page du PDF officiel (tolérant aux retours
  à la ligne, pages voisines pour les tableaux à cheval). Sur **1472 règles : 0 échec de FIGURE** — toutes
  les **valeurs** ingérées sont grondées sur leur page. Garde-fou permanent (`test_chaque_chiffre_applique_
  figure_sur_sa_page`).
- **Saint-Joseph (correctif #1 de la relecture)** : citation refaite **verbatim** (plus de « (part
  collective) » inventé, retours à la ligne réels) → **0 échec de contrôle**. La ligne « 1 place par tranche
  de 10 logements (1 logement = 3 places d'hébergement, art. L.312-1 CASF) » a **deux lectures** (cf.
  interprétations) : (a) supplément pour toute opération — **la plus exigeante, appliquée au logement
  ordinaire** (`visiteurs` 1/10) ; (b) règle des établissements d'hébergement — **appliquée aux résidences**
  (`senior` : 1 logement = 3 places). Chaque zone cite sa page.
- **Saint-Denis pleine terre (correctif #3)** : **retirée**. La question « Ua 15 % ou Uat 15 % » est tranchée
  par l'image : le texte dit **« En secteurs Uat : 15 % »** — Uat est un **secteur** (renvoi à Ua), pas la
  zone Ua ; et les autres valeurs (Ui→« Uip », Uj/Um/Uh) ne se vérifiaient pas sur les pages de ce millésime
  du PDF. Plutôt que de garder des valeurs non prouvées, l'ingestion est **annulée** : Saint-Denis pleine
  terre reste à ré-ingérer **zone par zone, image à l'appui** (les n° de page de l'audit ne correspondent pas
  au PDF 2026-08-05).

### Dette VERBATIM des citations (mesurée, pas masquée)
Le contrôle révèle **741 échecs de CITATION** (dont Saint-Joseph, désormais corrigé) : mes citations étaient
des **synthèses** combinant plusieurs cases de tableau, pas le texte mot pour mot de la page. **Les valeurs
sont justes** (0 échec de figure), mais **les citations doivent devenir verbatim**, zone par zone — méthode
prouvée sur Saint-Joseph (passage à 0 échec). C'est le gros du reliquat ci-dessous.

### Reliquat explicite (à faire avant merge, non masqué)
1. **Citations verbatim** pour les ~15 communes restantes (méthode Saint-Joseph, pilotée par le contrôle).
2. **Saint-Paul** (reporté car 55 zones, barème par secteur, nombreux `propose`/« INTROUVABLE ») : à ingérer
   zone par zone, même méthode.
3. **Lot 4 — textes manquants** : les PDF officiels **sont présents** dans `data/plu_reglements/` (Étang-Salé
   97404, Saint-André 97409, Saint-Leu 97413, Plaine 97406, Saint-Denis 97411) — l'absence de la table
   `plu_reglement_extrait` n'est **pas** une raison de laisser « Non vérifié ». À ingérer depuis l'image du
   PDF. (L'ingestion dans `plu_reglement_extrait` est un sujet séparé à lister.)
4. **52 zones « habitat secondaire »** : état non final — pour chacune, soit refus d'Étude (logement non
   principal), soit ingestion si une norme existe. À décompter.
5. **Conditions chiffrées** (Saint-Louis > 10 logements : 0,5 place publique/logt) : afficher le nombre de
   places et les compter dans les places à loger (lecture la plus exigeante).
6. **Contrôle « image prouve le chiffre »** : chaque image de sondage doit contenir, dans sa zone recadrée,
   chaque chiffre appliqué (tableaux à cheval = image des deux pages) ; refuser Le Tampon 1AUa / Le Port 1AUm.
7. **Libellé « non réglementé »** étendu (Salazie, Sainte-Suzanne, Saint-Paul, La Possession UA/UB, Entre-Deux
   Ub/Ue) ; **Études en PDF** (pas seulement HTML/JSON) ; **sondage final graine fixe sur les 24 communes**.

**Priorité de ce tour** : le refus (bloquant, audit écrans) et le contrôle dur des pages (qui prouve que
toutes les valeurs sont justes) ont été traités d'abord ; le reliquat verbatim/ingestion est mesuré et listé
plutôt que bâclé — la relecture a montré que la précipitation sur les valeurs produit des erreurs.

---

## Relecture (3e tour) — contrôle renforcé, barème collectif prouvé, version Saint-Denis

### Contrôle durci (ta remarque A)
Le contrôle vérifie désormais la VRAIE preuve : (1) la citation se retrouve **mot pour mot** sur sa page
(par segments de ligne, tolérant aux retours à la ligne), ET (2) **chaque chiffre appliqué figure DANS la
citation** (plus « quelque part sur la page »). Résultat sur **1465 règles** :
- **0 chiffre hors citation** — tout chiffre appliqué est présent dans la citation de sa règle (garde-fou
  `test_chaque_chiffre_applique_figure_dans_sa_citation`). Corrigé au passage : Saint-Pierre (ligne
  hébergement 0,3/0,2 ajoutée à la citation), la colonne « places intégrées » porte sa propre citation.
- **1247 citations pas encore verbatim** — c'est la DETTE : mes citations étaient des synthèses. Outil
  `scripts/stationnement_citation_verbatim.py` construit le bloc verbatim depuis la page (propre sur Le
  Tampon, Cilaos, etc. ; reste à régler les cases de tableau sur 2 lignes et les dispositions générales).
  La conversion commune par commune, pilotée par le contrôle jusqu'à 0, est le gros du reliquat.

### Contre-audit 97422000BW2635 (barème individuel sur collectif)
Vérifié : le moteur applique BIEN le **collectif**, jamais l'individuel. BW2635 (zone Uav, 20 logements) →
**30 places = 1,5 × 20 (opération > 5)**, formule « barème par typologie / opération > 5 », pas « habitat
individuel ». Pour **30 logements → 45 places** (1,5 × 30), exactement le ~45 attendu. Aucune révision en
cache pour BW2635 : l'écran « 30/30 individuel » relevé était un état **antérieur au correctif**. Test
ajouté (`test_le_tampon_collectif_jamais_le_bareme_individuel`, 8→12, 20→30, 30→45).

### Saint-Denis — version en vigueur (ta remarque B)
Le règlement en vigueur servi par le GPU est **2026-08-05** (`97411_reglement_20260805.pdf`,
`https://data.geopf.fr/annexes/gpu/documents/DU_97411/…`). La table `plu_reglement_extrait` sert **la même
version** — l'écart ne vient pas des versions mais de **n° de page mal transcrits à l'audit** : sur ce PDF,
« 15 % » est **« En secteurs Uat »** (secteur, renvoi à Ua), et « 25 % » est **« En secteurs Uip »** — des
sous-secteurs, pas les zones Ua/Ui. La pleine terre Saint-Denis est à ré-ingérer **zone par zone, image à
l'appui** sur ce PDF 2026-08-05 (fait au lot d'après, hors périmètre stationnement de ce tour).

### Deuxième cas du contre-audit — hauteur près des limites (Ua10.3)
Noté : une règle de hauteur près des limites (art. Ua10.3) que le moteur ne sait pas chiffrer doit
s'afficher **« Non vérifié »**, jamais être traitée comme absente (même principe que le prospect L ≥ h/2).
À implémenter (contrôle dédié), reliquat.

### Reliquat de ce lot (à finir avant merge)
1. **Citations verbatim** : 1247 → 0 (conversion commune par commune, outil prêt, contrôle comme juge).
2. **Saint-Paul** zone par zone. 3. **52 zones « habitat secondaire »** : refus motivé ou ingestion, décompte.
4. Ua10.3 hauteur « Non vérifié ». 5. Saint-Denis pleine terre (image à l'appui). 6. Lot 4, conditions
chiffrées, « non réglementé », Études PDF, sondage final (lot d'après).

---

## Info reçue — Saint-Denis et La Possession exclues de ce lot
Les PLU de **Saint-Denis** (nouveau document approuvé le **05/08/2026**) et de **La Possession**
(modification du **25/06/2026**) ont changé ; une **autre session** ingère les versions en vigueur. Je ne
les traite pas ici et je referai leur stationnement sur le **nouveau texte, à la fin**. Mon ingestion de
La Possession (lot 3, sur l'ancien texte) est **révoquée** (`git checkout origin/main`) pour ne pas diverger ;
Saint-Denis était déjà revenue à l'état d'origine (pleine terre retirée). Les deux apparaissent « version en
cours » dans `COUVERTURE.md`. C'est aussi ce qui explique l'écart base/PDF que j'avais vu à Saint-Denis.
