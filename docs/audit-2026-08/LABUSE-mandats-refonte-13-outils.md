# LABUSE — Mandats Claude Code · refonte des 13 outils
23/08/2026 · issus de l'audit validé (`LABUSE-audit-maquettes-13-outils.html`) · à numéroter dans ta séquence Mxxx en cours

## Ordre d'exécution conseillé

| # | Mandat | Outil(s) | Priorité | Dépend de |
|---|--------|----------|----------|-----------|
| 1 | SOCLE | transversal | P1 | — |
| 2 | COMMUNES | 10 | P1 | — |
| 3 | ETUDIER | 01 | P1 | — |
| 4 | DENSIFIER | 12 | P1 | SOCLE |
| 5 | SOLAIRE | 09 | P1 | SOCLE (barre unique) |
| 6 | COURRIER | 08 | P1 | SOCLE (barre unique) |
| 7 | COMPARAISON | 05 | P2 | SOCLE |
| 8 | PLU | 04 | P2 | SOCLE (pagination) |
| 9 | PIEGES | 03 | P2 | SOCLE (barre unique) |
| 10 | PERMIS | 11 | P2 | — |
| 11 | ASSEMBLAGE | 06 | P3 | ETUDIER (bloc charge), COURRIER (pont) |
| 12 | FAISABILITE | 02 | P3 | SOCLE (pagination) |
| 13 | SCAN | 07 | P3 | — |
| 14 | TEMPS | 13 | P3 | — |

Seules 4 dépendances sont dures : SOCLE avant DENSIFIER / SOLAIRE / COURRIER / COMPARAISON / PLU / PIEGES / FAISABILITE (composants partagés), ETUDIER et COURRIER avant ASSEMBLAGE. Le reste se réordonne librement.

---

## Bloc commun — à coller en tête de chaque session CC, avec le mandat

```
RÈGLES COMMUNES (refonte 13 outils)
- Branche dédiée indiquée dans le mandat. Jamais main. Tu ne merges jamais :
  le merge --no-ff est un geste de Vic ; la commande de merge est le dernier
  élément isolé de ton compte-rendu.
- DA v3 conservée : tokens existants (vert canonique #4ADE80 / --mint, fond
  sombre), mauve réservé aux surfaces IA. Aucune nouvelle lib/framework sans accord.
- Doctrine données : chaque valeur affichée porte son statut Sourcé/Estimé/Dérivé ;
  fraîcheur = date de la source amont ; jamais inventer un chiffre ; le faux
  positif est le péché cardinal.
- Les maquettes de référence sont dans
  docs/audit-2026-08/LABUSE-audit-maquettes-13-outils.html (section indiquée) ;
  leurs valeurs sont illustratives — les vraies valeurs viennent des mêmes points
  de calcul que les fiches (run servi).
- Si un état existant contredit le mandat, tu t'arrêtes et tu le signales, tu
  n'improvises pas.
```

---

## Mandat SOCLE — composants partagés + cycle de vie des overlays
**Priorité P1 · branche `outil/socle-refonte` · réf. maquettes : sections 03, 05, 12**

Contexte. Trois besoins reviennent dans 7 outils ; on les fabrique une fois.

Changements.
1. **Cycle de vie des overlays plein écran** (tableau Comparaison, table des 24 communes, futur tableau Densifier) : à la sortie de l'outil courant (changement d'outil ou de route), tout overlay ouvert se ferme/démonte proprement. Bug repro actuel : ouvrir le tableau Comparaison → cliquer un autre outil sans ✕ → le tableau persiste par-dessus. Hypothèse : le composant overlay n'est pas démonté à la sortie de la route — ajouter un cleanup on-leave centralisé. L'état de sélection associé (parcelles comparées) est conservé 15 min (TTL) pour retour sans perte.
2. **Composant « barre unique parcelle »** : un seul champ « Adresse ou IDU… », qui détecte le format saisi (IDU cadastral vs adresse), propose l'autocomplete existant et renvoie l'IDU résolu. Destiné à remplacer tous les doubles champs (Pièges) et à s'insérer en tête d'outils (Densifier, Solaire, Courrier).
3. **Composant pagination de liste** : pied de liste « **n / total** affichées · [Voir 400 de plus] · [Tout charger (total)] », compteur toujours visible, jamais tronqué. Consommé par PLU, Densifier, Faisabilité.

Critères d'acceptation.
- Changer d'outil avec un overlay ouvert ne laisse jamais rien à l'écran ; revenir dans Comparaison sous 15 min retrouve la sélection.
- La barre unique résout aussi bien `97415000CW0658` qu'une adresse, et expose l'IDU au parent.
- La pagination charge par paquets de 400 jusqu'à épuisement, « tout charger » fonctionne, le compteur est exact.

Garde-fous. Pas de refonte visuelle des outils ici — uniquement les composants et le fix de cycle de vie. Ne pas toucher au contenu du tableau Comparaison.

---

## Mandat COMMUNES — tableau mis en valeur + fiche scrollable
**Priorité P1 · outil 10 · branche `outil/communes-lisibilite` · réf. maquette : section 10**

Contexte. Le fond est bon (chaque bloc sourcé + fraîcheur + fiabilité ; ZAN vérifié : 145,5 ha × 58 % = 84,4 ≈ 85 ha, 85 ÷ 20,2 = 4,2 ans ✓) mais l'info est enterrée : en-têtes cryptiques, clic invisible, et le contenu de la fiche sous la ligne de flottaison est inaccessible (il faut dézoomer le navigateur).

Changements.
1. **Tableau des 24 communes** (overlay plein écran existant) :
   - Renommer la colonne **VÉLO → « Instruction (mois) »** (c'est la vélocité administrative : délai médian dépôt→autorisation ; Saint-Pierre 8 cohérent avec les « 5 à 11 mois » de sa fiche).
   - Tooltip (i) sur chaque en-tête + **légende permanente en pied de tableau** : Stock = parcelles promues LABUSE · Instruction = délai médian dépôt→autorisation · Permis 12 m = autorisations glissantes (Sitadel) · SRU = % obligation loi SRU · €/m² = DVF millésime.
   - **Affordance de clic** : consigne dans l'en-tête (« cliquez une ligne pour ouvrir sa fiche »), chevron › en bout de ligne, survol qui révèle « Ouvrir la fiche → ».
   - Indicateur de tri visible sur la colonne active ; meilleures valeurs en vert pour guider l'œil.
2. **Fiche commune** :
   - **Fix du scroll** : tout le contenu doit être atteignable à zoom 100 %. Hypothèse : conteneur en hauteur fixe sans `overflow-y:auto` (ou 100vh avec header qui déborde) — le scroll interne ne s'active jamais.
   - **Header sticky** (nom + signal) avec ancres Marché · Prix · Dynamique · Offre · ZAN · Loyer qui sautent aux sections.
3. **Donnée à réconcilier** : € ANC. du tableau (Saint-Pierre 3 015) ≠ prix ancien de la fiche (2 634 €/m², DVF 2025). Identifier les deux séries (segment ? millésime ?) ; soit unifier sur une seule, soit libeller distinctement les deux colonnes/valeurs. Documenter le choix dans le compte-rendu.

Critères d'acceptation. Fiche Saint-Pierre lisible jusqu'à la dernière section à zoom 100 % ; « VÉLO » n'existe plus ; un utilisateur qui n'a jamais vu l'outil comprend en 5 s que les lignes s'ouvrent ; l'écart € ANC est expliqué ou résorbé.

---

## Mandat ETUDIER — charge négative lisible + verdict unique + cohérences
**Priorité P1 · outil 01 · branche `outil/etudier-verdict` · réf. maquette : section 01**

Contexte. Les calculs sont justes, l'affichage ment. Sur BZ 1065 : charge foncière calibrée = −135 €/m² × 1 625 m² = **−219 375 €** (négative) ; écart affiché « dépasse de 719 k€ » = 500 000 − (−219 375) ✓. L'écran affiche pourtant « 0 € » (négatif écrêté à l'affichage mais utilisé au calcul) et empile deux bandeaux de verdict (calibré −219 k€ → 719 k€ ; hypothèses utilisateur −122 911 € → 623 k€) sans hiérarchie.

Changements.
1. **Ne jamais écrêter la charge foncière à 0** : afficher la valeur négative telle quelle (−219 375 €), en rouge, avec la phrase d'explication « l'opération ne finance pas ce foncier à ces hypothèses » + **jauge** avec le zéro marqué (cf. maquette).
2. **Verdict unique** : un seul bloc, avec bascule segmentée **[Calibrées LABUSE | Vos hypothèses]** qui commute les chiffres (charge, écart au prix). Plus jamais deux bandeaux empilés.
3. **Libellé** : « SDP vendable 123 m² » est faux — 123 m² est une **SHAB** (SDP = 219 m² dans la trace Faisabilité). Renommer partout dans la fiche (« SHAB vendable »), en gardant SDP là où c'est vraiment de la SDP.
4. **Alerte de cohérence résiduel** : quand la SDP résiduelle nette du bâti existant (calcul « Un lot » de Pièges : 26 m² sur BZ 1065) est inférieure à la surface théorique vendue par la fiche, remonter une alerte visible dans Étudier un bien (« Résiduel net du bâti : 26 m² — voir Pièges & risques ») au lieu de laisser les deux outils se contredire en silence.
5. Reçus conservés : CA 4 275 €/m² × 123 = 525 825 ≈ 526 k€ ✓ ; 123 ÷ 0,8 = 154 m² plancher ✓ — ces chaînes de calcul ne bougent pas, seul l'affichage change.

Critères d'acceptation. Sur BZ 1065 : une seule zone de verdict, charge −219 375 € visible et expliquée, bascule calibré/hypothèses qui recalcule l'écart (719 k€ ↔ 623 k€), mention SHAB, alerte résiduel présente avec lien.

Garde-fous. Aucun changement aux moteurs de calcul ni aux points de calcul (run servi) — mandat 100 % présentation + une alerte croisée.

---

## Mandat DENSIFIER — grand tableau plein écran + recherche directe
**Priorité P1 · outil 12 · branche `outil/densifier-tableau` · dépend de SOCLE · réf. maquette : section 12**

Contexte. 67 214 parcelles vivent dans un panneau de ~320 px : colonnes coupées, chips de tri tronquées, compteur illisible, scroll horizontal obligatoire. Et aucune entrée directe « ma parcelle densifie-t-elle ? ».

Changements.
1. **Barre unique parcelle (SOCLE) en tête de panneau** : IDU ou adresse → ligne de résultat directe (score, classement, SDP résiduelle) sans passer par la liste.
2. Panneau latéral réduit à : barre de recherche, note d'analyse datée (« maj 2026-08-20 · 67 214 parcelles… »), top 3-5 lignes, bouton **« ⛶ Ouvrir le tableau complet »**.
3. **Grand tableau plein écran** (même mécanique d'overlay que Comparaison/Communes, cycle de vie SOCLE) : colonnes Parcelle · Classement · Score · SDP résiduelle · Surface · Bâti existant · Zone · Rang commune — **toutes visibles sans scroll horizontal**, chips de tri entières dans l'en-tête, tri par Score / SDP résiduelle / Surface / Rang commune.
4. **Pagination SOCLE** (400 par 400 + tout charger) + **export CSV** en pied.

Critères d'acceptation. Zéro scroll horizontal au format desktop courant ; compteur « 400 / 67 214 » net ; recherche `97404000AZ0004` → réponse immédiate ; fermeture de l'overlay au changement d'outil.

---

## Mandat SOLAIRE — refonte en deux modes
**Priorité P1 · outil 09 · branche `outil/solaire-deux-modes` · dépend de SOCLE (barre unique) · réf. maquette : section 09 (3 écrans)**

Contexte. Le fond est bien branché (PVGIS v5.3 SARAH3, RGE ALTI, BD ORTHO 20 cm 2025, données V1 gelées au 11/07/2026, disclaimers panneaux/ombrage présents) mais l'info est invisible : colonnes coupées, potentiel sans unité, tri noyé d'« Écartée », aucune entrée directe. Et les deux cibles métier (pisciniste / installateur PV) sont mélangées.

Changements.
1. **Écran d'entrée à deux cartes** : 💧 **Piscines** (pisciniste — rénovation, couverture, entretien) / ☀️ **Ensoleillement** (installateur PV). Mentions sources conservées en pied (détection FLAIR sur ortho · PVGIS v5.3 SARAH3 · RGE ALTI · données gelées 11/07/2026).
2. **Mode Piscines** : sélecteur Toute l'île / commune + filtres (surface piscine ≥, bâti) → **la stat d'abord** (compteur piscines détectées île + par commune, mention « détection ortho/IA · à confirmer sur site ») → bouton « 💧 Voir sur la carte » (marqueurs) → listing parcelles synchronisé. Les décomptes = agrégats de la détection piscines existante, rien de recalculé.
3. **Mode Ensoleillement** : critères (potentiel ≥, pente, orientation) **puis barre unique adresse/IDU (SOCLE)** → **fiche soleil de la parcelle** : potentiel **avec unité (kWh/m²/an)**, toiture exploitable, orientation et inclinaison optimales, **profil mensuel** (12 barres), limites affichées (ombrage de proximité non modélisé · panneaux existants non détectés — vérif photo aérienne avant démarchage).
4. **Écartées masquées par défaut** dans toutes les listes, avec option « les inclure ».

Critères d'acceptation. Un pisciniste obtient « combien de piscines à Saint-Paul » en 2 clics ; un installateur obtient la fiche soleil d'une adresse en 1 saisie ; plus aucune colonne coupée ; « Écartée » n'apparaît plus en tête de tri par défaut.

Garde-fous. Aucun recalcul de données solaires (V1 gelée) — refonte de présentation + requêtes d'agrégats uniquement.

---

## Mandat COURRIER — refonte en service d'envoi
**Priorité P1 · outil 08 · branche `outil/courrier-service` · dépend de SOCLE (barre unique) · réf. maquette : section 08 (2 écrans)**

Contexte. Le PDF exporté est vide (PJ de Vic : seulement « LABUSE » + la ligne Objet — le corps rédigé manque) et la proposition de valeur self-serve est faible. L'outil devient un **service** : le client prépare, LABUSE envoie.

Changements.
1. **Flow en 3 étapes** :
   - **① Destinataires** : barre unique IDU/adresse (SOCLE) + « + Ajouter » → chips retirables ; **import en un geste** depuis Assemblage (« les 3 parcelles ») ou depuis un lot Pièges.
   - **② Rédaction** : chips de modèles **[Approche standard] [Dormance / succession] [Voisin direct] [Libre]** + zone d'édition ; variables `{parcelle} {commune} {surface}` remplacées par courrier (un courrier généré par destinataire). Adressage générique conservé (workflow SPF/CERFA côté LABUSE, mention existante gardée).
   - **③ Envoi** : récap (nb courriers, communes, adressage) + CTA **« Demander l'envoi à LABUSE »** → confirmation « LABUSE vous rappelle sous 24 h ouvrées avec le tarif — impression, mise sous pli, affranchissement et suivi compris ».
2. **Statuts visibles côté client** : Demandé → Tarif confirmé → Envoyé (timeline sur la demande).
3. **Côté LABUSE** : à chaque demande, événement dans **event_log** (cloche header) + **email Brevo** à Vic (« {client} demande l'envoi de {n} courriers ({communes}) ») — se brancher sur les canaux existants, pas de canal parallèle. Vue admin minimale : liste des demandes (client, n, communes, corps, date) + changement de statut manuel.
4. **Persistance** : table des demandes (client, parcelles, modèle, corps, statuts + horodatages). Respect du pattern existant pour toute table nouvelle (elle entre en bascule ou elle est déclarée morte).
5. **Fix PDF** (aperçu de relecture, action secondaire) : le corps multi-paragraphes doit apparaître dans le PDF. Hypothèse : le gabarit n'injecte que les champs d'en-tête — la variable du corps n'est pas passée au générateur ou le rendu multi-paragraphes échoue silencieusement. Corriger, puis réactiver « Télécharger l'aperçu PDF (relecture) ».

Critères d'acceptation. Une demande de 3 courriers déclenche cloche + email chez Vic avec client/n/communes ; le client voit « Demandé » puis les statuts suivants quand Vic les passe ; le PDF de relecture contient l'intégralité du corps ; l'import depuis Assemblage pré-remplit les 3 parcelles.

Garde-fous. Aucun envoi automatique, aucun prix affiché côté client — le tarif est donné par Vic au téléphone.

---

## Mandat COMPARAISON — ancré dans Outils
**Priorité P2 · outil 05 · branche `outil/comparaison-ancrage` · dépend de SOCLE · réf. maquette : section 05**

Contexte. Le tableau plein écran est bon (mêmes points de calcul que la fiche, charge négative affichée en négatif) et le clic-carte plaît — mais ouvrir l'outil bascule l'app sur « Cartes » et lâche l'utilisateur. Le panneau fantôme est réglé par SOCLE.

Changements.
1. **Rester dans l'onglet Outils** : le panneau gauche reste affiché et guide — stepper **① Cliquez les parcelles sur la carte** (la carte reste active à droite ; entrée aussi possible depuis une fiche → « Comparer ») **② Ouvrez le tableau** (bouton « Comparer (n/3) ») **③ Revenez à la carte** (✕ ou Échap, sélection conservée).
2. Chips de sélection dans le panneau (IDU + ✕ de retrait, slot « + n libre »), compteur n/3.
3. Note dans le panneau : « en quittant l'outil, le tableau se ferme ; votre sélection est gardée 15 min » (comportement SOCLE).
4. **Le tableau overlay ne change pas** (contenu, colonnes, plein écran conservés tels quels).

Critères d'acceptation. Ouvrir Comparaison ne quitte plus Outils ; on peut cliquer 3 parcelles sur la carte avec le panneau visible ; retirer une parcelle depuis une chip ; le tableau s'ouvre/ferme sans résidu.

---

## Mandat PLU — pagination + précalcul nocturne
**Priorité P2 · outil 04 · branche `outil/plu-perf` · dépend de SOCLE (pagination) · réf. maquette : section 04 (2 écrans)**

Contexte. Le recalcul à blanc AUc/AUs/AU → U est très long avec un spinner muet, et la liste est bloquée à « les 400 premières sur 1 451 ». Le fond est sain (méthode transparente, ratio d'analogie affiché, vérif Sudocuh datée ; AB0790 : 743 402 × 0,318 ≈ 236 275 ✓).

Changements — deux lots, livrables séparément.
1. **Lot A (rapide) — pagination** : remplacer la coupe à 400 par le composant SOCLE (« Voir 400 de plus » jusqu'à épuisement + « Tout charger (1 451) »), compteur toujours visible.
2. **Lot B — précalcul nocturne** : cron qui précalcule chaque nuit les **72 combinaisons (24 communes × 3 scénarios)** et les sert en cache → l'écran devient instantané, avec mention de fraîcheur (« servi depuis le précalcul de la nuit (date · heure) ») ; recalcul live **uniquement** si l'utilisateur change les paramètres. Le tri « toute l'île » = fusion des caches communaux, pas un recalcul. Versionner le cache façon run + pointeur (pattern parcel_residuel) : le recalcul écrit un run parallèle, la mise en service est un geste explicite/atomique.
3. **UI de chargement honnête** pour le cas live : barre de progression réelle (n / total parcelles), squelettes de lignes, bouton **Annuler**. Si le calcul live reste nécessaire, streamer les résultats par paquets de 100 pour que les premiers apparaissent tout de suite.

Critères d'acceptation. Bascule AUs → U sur une commune précalculée : affichage < 1 s avec mention de fraîcheur ; liste navigable jusqu'à 1 451/1 451 ; en mode live : progression réelle + annulation effective.

---

## Mandat PIEGES — barre unique, « + ajouter » réparé, retraits
**Priorité P2 · outil 03 · branche `outil/pieges-un-lot` · dépend de SOCLE (barre unique) · réf. maquette : section 03**

Changements.
1. **Mode « Un lot »** : remplacer les deux champs (IDU / adresse) par la **barre unique SOCLE**.
2. **Fix « + ajouter »** : le clic doit ajouter la parcelle saisie à la **liste du bas** (le lot en cours). Aujourd'hui il n'alimente rien. Hypothèse : handler branché sur le mauvais état/liste — vérifier où atterrit l'ajout.
3. **Retirer l'export PDF** de l'outil (bouton et code mort associé).
4. **Conditionner le critère `age_dirigeant`** : la règle « PM sans dirigeant physique daté » ne doit s'évaluer/s'afficher que si le propriétaire est une **personne morale** — elle apparaît aujourd'hui sur un propriétaire particulier.

Critères d'acceptation. Saisir 3 IDU successifs construit un lot de 3 visibles en bas ; plus aucun bouton PDF ; sur une parcelle à propriétaire particulier, aucune ligne age_dirigeant n'apparaît.

---

## Mandat PERMIS — double entrée + densité d'affichage
**Priorité P2 · outil 11 · branche `outil/permis-double-entree` · réf. maquette : section 11**

Contexte. Bien branché (Sitadel au 2026-06-30 — retard ~2 mois normal ; géocodage 90 % annoncé, 576 non géocodés listés) mais : énorme espace noir entre l'en-tête et les premiers permis, « au point mort » réduit à une case à cocher noyée, lignes trop pauvres pour scanner.

Changements.
1. **Deux entrées franches à l'arrivée**, avec compteurs : **« En cours & récents »** (chantiers, DP, PC — veille concurrentielle) / **« Accordés, jamais réalisés »** (sous-titre « au point mort » — PC purgés non commencés : du gisement). Le point mort reste techniquement un filtre (fusion actée), mais il devient un choix d'entrée visible.
2. **Supprimer le vide** : entrées → filtres compacts (période 12/24/48/72/tout + types PC/DP/PA/PD) → ligne de stats (« 5 613 permis · 5 037 sur la carte · 576 sans localisation → liste ») → la liste commence immédiatement.
3. **Lignes enrichies** : type (badge) + date + logements + commune + statut/badges (« non géocodé », « point mort — jamais commencé »).
4. **Synchro carte** : survol d'une ligne = le point s'allume sur la carte ; clic = fiche permis (porteur, lots, surfaces, délai).

Critères d'acceptation. Plus aucun bloc vide entre l'en-tête et la liste ; les deux entrées affichent leurs compteurs réels ; le survol allume le bon point.

---

## Mandat ASSEMBLAGE — libellés + charge négative + pont Courrier
**Priorité P3 · outil 06 · branche `outil/assemblage-libelles` · dépend de ETUDIER (bloc charge) et COURRIER (pont) · réf. maquette : section 06**

Contexte. Garde-fous exemplaires (NON contigu, 3 interlocuteurs, reculs internes, indivision « non affichée plutôt qu'inventée ») ; deux ambiguïtés d'affichage. Reçus : SDP cumulée 217+122+10 726 = 11 065 ✓ ; surface d'assiette 619+250+13 242 = 14 111 ; −1 879 117 ÷ 14 111 = −133 €/m² ✓.

Changements.
1. Remplacer « Assiette 11 065 m² SDP » par **deux KPI distincts** : « Surface d'assiette 14 111 m² » et « SDP cumulée 11 065 m² ».
2. « ×1 vs la meilleure seule » → **×1,03 (+3 %)** (11 065 ÷ 10 726).
3. **Charge cumulée négative** (−1,88 M€ · −133 €/m²) : réutiliser le bloc rouge + phrase du mandat ETUDIER, avec la référence marché à côté (479 €/m² DVF · fiab. moyenne).
4. **Pont Courrier** : remplacer les boutons courrier par parcelle par un seul **« Préparer les courriers (n) »** qui ouvre l'outil Courrier pré-rempli avec les parcelles de l'assemblage.

Critères d'acceptation. Les deux grandeurs s'affichent séparément ; la charge négative a le même traitement que dans Étudier un bien ; le bouton pré-remplit bien Courrier étape ①.

---

## Mandat FAISABILITE — étape 12 + confort de liste
**Priorité P3 · outil 02 · branche `outil/faisabilite-etape12` · dépend de SOCLE (pagination) · réf. maquette : section 02**

Contexte. Le meilleur pattern de l'app (trace en étapes sourcées ; 24×60×1,2 = 1 728 ✓ ; DK1169 281 159 ÷ 1 728 = ×162,7 ✓). Un trou : la trace « par parcelle » passe de SHAB ~175 m² (étape 6) à ~123 m² en tête de fiche sans l'expliquer.

Changements.
1. **Ajouter l'étape manquante** (plafond de densité) dans la trace par parcelle, pour que le passage 175 → 123 m² soit sourcé comme les autres étapes.
2. **Programme épinglé** : en mode « par critères », le récap du programme reste sticky pendant le scroll des résultats.
3. **Pagination SOCLE** sur les listes de résultats.

Critères d'acceptation. La trace se lit de bout en bout sans saut inexpliqué ; le programme reste visible en scrollant ; « voir 400 de plus » fonctionne.

---

## Mandat SCAN — deux retraits
**Priorité P3 · outil 07 · branche `outil/scan-retraits` · réf. maquette : section 07 (maquette de principe — l'écran de réf. manque, travailler sur le code existant)**

Changements.
1. **Retirer les badges « priorité »** des lignes — ne restent que les classements canoniques (Écartée / Neutre / Faible / Long terme), identiques au reste de l'app.
2. **Retirer toute action d'envoi de courrier** (boutons par ligne et en pied) — l'outil observe, il ne démarche pas ; le courrier est désormais une démarche volontaire depuis l'outil Courrier.
3. Conserver l'export CSV.

Rappel périmètre. Les données patrimoine restent côté personnes morales / open data DGFiP tant que l'avis avocat (RGPD âge dirigeant, CGU/CGV) n'est pas rendu — ne rien étendre ici.

Critères d'acceptation. Plus aucun badge priorité ni bouton courrier dans l'outil ; CSV inchangé.

---

## Mandat TEMPS — légende, contour, frise (conditionnelle)
**Priorité P3 · outil 13 · branche `outil/temps-millesimes` · réf. maquette : section 13**

Changements.
1. **Légende in-UI** : « Zones noires : secteurs non couverts par l'ortho ancienne (mer, limites de mission IGN) — ce n'est pas un défaut de chargement. »
2. **Contour de la parcelle épinglé** (vert --mint) sur **les deux couches** du comparateur, pour ne jamais la perdre en glissant le curseur.
3. **Frise des millésimes — lot conditionnel** : d'abord **inventorier les millésimes d'ortho historiques IGN réellement disponibles pour La Réunion** ; si ≥ 2 en plus de 1950-65, câbler une frise (l'« après » reste aujourd'hui, l'« avant » se choisit). Sinon, ne rien câbler et le documenter.
4. Conserver l'accès direct depuis toute fiche (bouton « 1950 »).

Critères d'acceptation. La légende apparaît dès qu'une zone non couverte est visible ; le contour reste visible des deux côtés du curseur ; la frise n'expose que des millésimes qui servent réellement des dalles.

---

## Addendum post-SOCLE (23/08/2026) — où sont les composants
- « Barre unique parcelle (SOCLE) » = `ParcelInput` (composant existant, omnibox M137) : détection IDU/adresse, autocomplete BAN, IDU résolu via onPick. Ne pas créer de doublon — PIEGES / DENSIFIER / SOLAIRE / COURRIER branchent celui-là.
- « Pagination (SOCLE) » = `frontend/src/components/ListPagination.tsx` : usePagination(total) + ListPaginationFooter (slot children pour l'export CSV).
- Cycle de vie overlays = constante `CLOSE_OVERLAYS` dans `store/useApp.ts` : tout nouvel overlay plein écran (ex. tableau Densifier) s'ajoute à cette constante et s'ouvre via une action dédiée façon openCompare().
