# MANDAT RETOURS-11F — le reste de RETOURS-11 (backend + refontes de fiche) + recette du 04/09

**Origine** : (1) tout ce que les sessions A/B/C/D ont porté NON FAIT parce qu'il fallait la base réelle ; (2) huit retours de Vic après recette visuelle du 04/09 (R1 → R8).
**Ce mandat travaille SUR LA BASE RÉELLE de Vic** (le `DATABASE_URL` du `.env`), pas sur `labuse_test` : c'est la raison même de son existence. Chaque chiffre affirmé au compte-rendu vient d'une requête, jamais d'une lecture de code.

**Deux sessions, deux branches, dans l'ordre :**

| Session | Branche | Contenu |
|---|---|---|
| F1 | `fix/retours-11f1` | lot M (moteurs uniques, mesurés) + lot R (les 8 retours du 04/09) |
| F2 | `fix/retours-11f2` | lot S (refonte des 9 sections de la fiche, qui s'appuie sur les moteurs de F1) |

**Étape 0** : `pwd`, branche de la session, arbre propre, **et** `cat config/served_run.txt` → noter le run servi au compte-rendu (il doit rester inchangé à la fin ; ce mandat ne bascule rien).
**Clôture** : tsc 0 · build · vitest · pytest 100 % verts (Pango est installé, plus d'excuse sur les tests PDF) · golden 119/119 · commit sur la branche AVANT le compte-rendu · merge = Vic.
**Autonomie complète** : aucune question, on tranche et on note.

**Règles héritées de RETOURS-11** (elles s'appliquent toujours) : survol vert partout · un fait vit dans UNE section · Sourcé / Estimé / Dérivé · jamais de zéro inventé (« — ») · jamais de valeur interne à l'écran client · pagination « Voir plus — N / M » par 200 · DA v3.

---

# LOT M — Les moteurs uniques (le cœur du mandat)

La fiche se contredit aujourd'hui parce que plusieurs moteurs répondent à la même question. Chaque ID ci-dessous : mesurer, unifier, poser le test qui empêche la divergence de revenir.

**M1 — Moteur VEFA unique (ex-C3).** Le chemin est tracé par la session A : `comparateur.py` (table Communes) et `carnet.py` (Évolution du marché) lisent le précalculé `dvf_prix_sortie_neuf` (4 730 à Saint-Paul) là où la fiche lit le live `neuf_vefa_commune` (5 003). Router les deux vers le moteur live, mesurer la convergence commune par commune, et évaluer la performance (24 appels live pour la table — si c'est trop lent, matérialiser le moteur unique dans une vue rafraîchie, pas refaire un second calcul). Test : pour 5 communes, fiche = table = carte, à l'euro près. Au compte-rendu : le tableau des 24 communes avant/après.

**M2 — Couverture VEFA (la question de fond de Vic).** La session A a mesuré 988 ventes VEFA et un filtre surface qui en tue 68 %, faute de surface Carrez au 974. Aller au bout : compter en **mutations** (`id_mutation` distinct), pas en lignes ; par commune, sur 36 mois ; dire combien de mutations ont une surface exploitable et combien n'en ont aucune. Puis trancher, en le documentant : soit un prix **au logement** (€/logement) quand la surface manque, soit une fenêtre élargie à 60 mois, soit la hachure maintenue. L'objectif de Vic est d'avoir la couche sur toute l'île ; s'il faut la refuser, le compte-rendu doit dire précisément pourquoi, chiffres à l'appui.

**M3 — Moteur prix de secteur unique.** Constat O1 : `sector_price` et `_ref_local` répondent tous deux « prix bâti du secteur » avec des valeurs et des fenêtres différentes (2 365 vs 2 403 sur le même écran), et « terrain nu : échantillon < 5 » cohabite avec « terrain nu dans la zone : 485 €/m² ». Un seul moteur, une seule fenêtre, un seul n affiché ; servi par Étudier un bien, la fiche (Marché), Comparer, la table Communes. Test de non-contradiction sur un même écran.

**M4 — Moteur équipements et permis à proximité.** Constat F0 : BPE et OSM donnent deux jeux de distances (école 87 m vs 95 m, commerces 0 m — un zéro inventé) et les permis à proximité sont comptés dans trois sections avec trois nombres. Un moteur `autour_parcelle` (équipements dédoublonnés BPE+OSM, distance à pied, seuil par famille) et un moteur `permis_proximite` (rayon, fenêtre, un seul tableau). Aucun « 0 m » : absent = « — ».

**M5 — Bilan et charge foncière (le point le plus important).** La charge foncière est négative partout : −219 123 € dans Étudier un bien, −37 €/m² dans Comparer, −194 058 € dans Assemblage — alors que le marché achète ce foncier ~479 €/m². Mesurer : distribuer la charge foncière calibrée sur toutes les parcelles U de l'île, comparer à la médiane DVF terrain nu par zone. Si la médiane des charges est négative ou très éloignée du marché, les hypothèses (coût de construction €/m² SHAB, frais, marge, TVA, stationnement, démolition, coûts fixes) sont fausses → les corriger et surtout **les afficher** : aujourd'hui « Hypothèses calibrées LABUSE » ne montre que le résultat. Graver le test de cohérence. Un seul moteur pour la fiche (Constructibilité), Étudier un bien, Comparer, Assemblage.

**M6 — Réconciliations de compteurs.** Chaque paire ci-dessous doit être expliquée puis unifiée : PLU annuaire « 2 en révision » vs Procédures « 3 communes en procédure » (O7/O8) · Scan patrimoine 1 833 vs 1 871 parcelles, onglet (29) vs 20 opérations, 31 permis/113 logements vs 20 opérations/226 logements (O11) · compteurs Radar entre l'écran Radar, la table Communes et Évolution (O20) · Risques « 9 couches évaluées » pour 15 lignes (F6). Au compte-rendu : ce que chaque nombre comptait vraiment.

**M7 — Étapes de calcul de capacité : une seule liste.** 13 étapes dans la fiche, 12 dans Faisabilité par parcelle, pour le même calcul (F5/O3). Un seul moteur, une seule liste, servie aux deux écrans.

**M8 — Taxe d'aménagement : config 2026 datée.** Constat O4 : la valeur forfaitaire affichée (892 €/m²) est inférieure à celle de 2024 alors que le forfait stationnement (2 928 €) suppose +17 % — les deux ne peuvent pas être vrais. Recharger toutes les valeurs 2026 depuis l'arrêté officiel dans une config unique datée avec sa source (valeur forfaitaire, piscine, PV au sol, stationnement, éoliennes), ajouter la redevance d'archéologie préventive si elle s'applique, et créer la table admin « taux communal par commune » (24 lignes, saisies par Vic depuis les délibérations) — tant qu'un taux n'est pas saisi, champ vide obligatoire, jamais une valeur par défaut.

**M9 — Densifier l'existant : capacité nette (ex-O18).** Le score est saturé (toutes les têtes de liste à 100) et la capacité ne déduit pas les contraintes. Calculer une capacité résiduelle **nette** : pente > 30 %, PPR rouge, reculs, emprise non constructible (ravine, falaise) ; ajouter la surélévation possible (hauteur max PLU − hauteur du bâti, BD TOPO) ; rendre le score discriminant. Vic l'a dit : une maison de 100 m² sur 1 000 m² dont 900 sont en falaise ne densifie rien.

**M10 — Cloche → Veille (ex-F3).** Créer une veille parcelle depuis la cloche de la fiche, dans les deux sens (retirer depuis Veille éteint la cloche), avec le toast. C'est du backend, d'où le report.

**M11 — Signalements typés de bout en bout (ex-A4/F2).** Le type (Bug / Idée / Question / Donnée) écrit en base, affiché et filtrable dans Produit, compté dans Pilotage ; un signalement venu de la fiche porte l'IDU, la section et un lien cliquable vers la fiche. **Vérification explicite demandée par Vic (R-verif)** : le bouton « Signaler » du bandeau et le « Signaler une erreur » du bas de fiche arrivent bien dans le dashboard, au bon endroit, avec le bon type. Test à deux comptes : A signale, Produit l'affiche avec le bon compte, B ne le voit pas.

**M12 — Piscines : confiance et corrections (ex-O12).** Vic a vu ~1 faux sur 4 et des manqués. Sans re-détection : afficher la confiance par piscine (haute / moyenne), relever le seuil par défaut avec une bascule « inclure les incertaines », et un bouton « pas une piscine » par ligne qui alimente une table de corrections servie au prochain calcul.

**M13 — Colonnes manquantes.** Comparer des parcelles (O9) : probabilité de vente, propriétaire moral/particulier, bâti existant %, hauteur max, logements possibles, accès, réseaux, prix secteur bâti, nombre de risques. Table Communes (O14) : **€/m² terrain nu DVF** (le chiffre du promoteur, absent aujourd'hui) et population. Évolution du marché (O15) : sélecteur de commune.

---

# LOT R — Recette visuelle du 04/09 (retours de Vic)

**R1 — Lettres de zonage PLU visibles plus tôt.** Aujourd'hui il faut trop zoomer. Abaisser le zoom d'apparition des étiquettes, et à zoom moyen n'afficher qu'une étiquette par îlot de même zone (au lieu d'une par parcelle) pour ne pas saturer. Capture avant/après à trois niveaux de zoom.

**R2 — La couche « Parcelles » sert-elle à quelque chose ?** Question de Vic. Répondre par une mesure : ce que dessine `parcels-fill` par rapport à `parcels-line` (« Limites parcelles »), sur les trois fonds. Verdict au compte-rendu : soit elle apporte quelque chose (dire quoi, et l'écrire dans son info-bulle), soit elle fait doublon → la fusionner avec « Limites parcelles » et retirer la case. Trancher, ne pas rendre la question à Vic.

**R3 — Adresse de la fiche sur une seule ligne.** « 13 Rue Pierre Lemazurier, 97460 Saint-Paul » passe sur deux lignes alors qu'il reste de la place : marge interne à droite trop grande, le bloc texte ne s'étire pas. Corriger, tester avec une adresse longue (« Chemin de la Rivière des Galets, 97419 La Possession ») ; si ça déborde vraiment, tronquer la ville, jamais couper au milieu.

**R4 — Mon compte : « Signaler / nous écrire » devient « Contact ».** Un seul intitulé, « Contact », relié par défaut à **contact@labuse.immo** (mailto, objet pré-rempli avec le compte). Retirer la mention « Signaler » de ce menu — le bouton Signaler du bandeau reste, lui.

**R5 — Ortho : la densité des parcelles doit suivre le zoom.** Sur toute l'île, l'ortho avec toutes les limites est illisible (capture). Cible : à faible zoom, seules les limites de communes ; à mesure qu'on zoome, les limites de parcelles apparaissent progressivement (opacité et épaisseur qui montent avec le zoom, apparition à partir d'un seuil). Même principe pour les aplats de zonage. Sombre reste inchangé — capture témoin.

**R6 — Puces de permis : hauteur réduite.** Le badge « Autorisé » est collé en bas et occupe une ligne pour lui seul ; le remonter sur la ligne du texte. Gain attendu : presque moitié moins haut par puce. Vérifier avec les puces qui portent une adresse longue.

**R7 — Faisabilité par critères : le cadre vert et la barre.** Retirer le liseré vert autour du bloc de résultat, retirer la barre horizontale, et **figer la hauteur du bloc** : il ne doit plus bouger quand le résultat change.

**R8 — Piscines : gouttes d'eau et bouton qui disparaît.** (a) Les points verts deviennent des symboles goutte d'eau (demandé au lot 3, non fait). (b) Une fois « Voir sur la carte » cliqué, le bouton disparaît (ou devient « Masquer sur la carte ») — sinon rien ne dit que l'action a eu lieu. (c) Au passage : le compteur dit « 200 / 500 affichées » alors que l'outil annonce 8 299 piscines — vérifier ce que compte réellement le total servi et corriger.

---

# LOT S — Les neuf sections de la fiche (session F2)

Reprendre **F0 et F4 à F12 du mandat RETOURS-11** (docs/audit-2026-09/MANDAT-RETOURS-11.md), qui restent intégralement à faire. Les moteurs du lot M étant posés, la restructuration devient possible.

Rappel du travail attendu, pour chaque section : vérifier chaque ligne sur la base réelle (source, millésime, valeur recalculée sur la parcelle de la capture), appliquer la table des doublons de F0, restructurer, et rendre compte de ce qui était faux / retiré / ajouté / fusionné.

- **S0 (= F0)** — la table « un fait, une section » : SDP consommée, SDP résiduelle, accès voirie, équipements, permis, prix de sortie, socio-économique, transport, ensoleillement, zone PLU, friche, fiscal, SUP. Plus les seuils de pertinence par famille (une ligne HT à 3 887 m ou un téléphérique à 24 km ne sont pas des informations).
- **S1 (= F4)** — Urbanisme : le tableau des règles de la zone AVEC les valeurs (hauteur, emprise, reculs, pleine terre, stationnement), pas seulement des références d'articles ; retirer la clé brute `declassement` et le jargon « 0 pt anti-double-compte » ; résoudre la contradiction « rien à construire » vs 80 m² de SDP dispo.
- **S2 (= F6)** — Risques : compteur vrai, vigilances d'abord, « rien à signaler » repliés, SUP rapatriées par famille, monument ABF nommé.
- **S3 (= F7)** — Marché : prix seulement ; VEFA du moteur unique (M1) ; recalculer « parc social 100,0 % en QPV », qui est douteux.
- **S4 (= F8)** — Réseaux et accès : UN verdict d'accès (trois formulations contradictoires aujourd'hui), quatre blocs, l'ensoleillement sort de là.
- **S5 (= F9)** — Autour : moteur M4, plus de zéros inventés, Filosofi en Sourcé et non Estimé.
- **S6 (= F10)** — Dispositifs : vérifier dans le CGI la largeur de la bande TVA réduite et le taux applicable aux DOM ; ajouter zonage B1 et TVA 8,5 / 2,1 LLS.
- **S7 (= F11)** — Propriétaire : le double en-tête « PACIFIC » + « propriétaire inconnu » ; « Personnes morales non remarquables » → formulation client ; forme juridique, APE, siège, date d'immatriculation.
- **S8 (= F12)** — Données et méthode : replié, groupé par thème, chips « à confirmer » retirées de la vue client (doctrine du 02/09), « ce que LABUSE ne sait pas » visible.

---

## Livrables

1. `docs/audit-2026-09/RETOURS-11F-RAPPORT.md` — une ligne par ID (M, R, S), et pour chaque mesure le chiffre trouvé avec la requête qui l'a produit.
2. Les tableaux de mesure : VEFA par commune avant/après (M1-M2), distribution de la charge foncière vs DVF (M5), réconciliation des compteurs (M6).
3. Captures avant/après pour tout le lot R, nommées par ID.
4. La liste des tests ajoutés (un par divergence corrigée — c'est ce qui empêche la fiche de se remettre à se contredire).
