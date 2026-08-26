# GRAND BALAYAGE — CYCLE 6 : LES ~1450 (certification finale — porte le total campagne à ~2250)
Protocole inchangé (MANDAT.md) : audit seul, aucun fix ; findings GB-041→ ; [GB-TEST] + inventaire de purge ; vérification jusqu'à la cause ; append + commit PAR LOT ; sous-agents parallèles + seeds notés (patron cycles 4-5). Rapport : RAPPORT-CYCLE-6.md + annexes CSV par lot. Front :5174, back :8000. AUCUNE mission ne rejoue les cycles 1-5 : tout est neuf.
DÉROGATIONS EXPLICITES à « lecture stricte », pour les LOTS AJ/AK uniquement : création/suppression d'une base TEMPORAIRE labuse_c6_test et d'un second serveur éphémère sur :8001 — jamais la base réelle, jamais le :8000. Budget LLM ≤ 200 appels (AL ≤ 160, AP ≤ 40).

## LOT AA — VÉRITÉ DES TUILES : 150 passes
150 tuiles MVT tirées au sort (seedées : mix z12-z16, 24 communes couvertes). Pour chacune : décoder la tuile → les parcelles présentes == requête SQL sur la même emprise (même filtre slivers) ; tier encodé == run servi ; aucune parcelle fantôme ni manquante. Annexe lot-aa.csv (z/x/y, n_tuile, n_sql, verdict).

## LOT AB — LES 240 BLOCS COMMUNES : 240 passes
24 communes × 10 blocs de la fiche Communes (prix ancien, terrain U/AU, sortie neuf, tendance, liquidité, offre engagée, offre potentielle, DPE, loyer, ZAN, délai — prends les 10 servis). Chaque valeur affichée == recalcul SQL indépendant, chaque mention (fragile/non calculable/médiane) justifiée. C'est l'outil vitrine : zéro tolérance. Annexe lot-ab.csv (commune, bloc, servi, recalculé, verdict).

## LOT AC — RECHERCHE DE MASSE : 200 passes
200 recherches omnibox seedées : 80 adresses réelles tirées de la BAN locale, 60 IDU (formats courts/longs/bizarres), 30 lieux-dits, 30 hostiles (quasi-adresses, fautes, mélanges). Invariants : une adresse réelle trouve sa parcelle ou dit honnêtement pourquoi ; jamais de mauvais résultat silencieux (le pire : la MAUVAISE parcelle servie avec assurance — vérifie la géométrie sur 20 échantillons) ; hostiles → messages propres. Annexe lot-ac.csv.

## LOT AD — 100 PDF OUVERTS : 100 passes
100 fiches parcelles PDF générées (parcelles stratifiées, retirage seedé) : chaque PDF PARSÉ (pdftotext) → les 6 grandeurs == API == base ; date du run imprimée ; aucune section vide non expliquée ; accents/œ selon la règle documentée. Annexe lot-ad.csv.

## LOT AE — FUZZING DES ÉCRITURES : 100 passes (jamais fait — on n'avait fuzzé que les GET)
Avec session, sur les POST/PATCH/DELETE ([GB-TEST] obligatoire, inventaire tenu) : payloads hostiles (champs manquants, types faux, JSON malformé, champs inconnus, tailles énormes, unicode, doubles requêtes) sur projets, CRM, courrier, veilles/surveillance, décisions kanban. Invariants : jamais un 500 ; jamais une écriture PARTIELLE (l'objet est créé entier ou pas du tout — vérifie en base après chaque refus) ; jamais un objet corrompu affichable. Annexe lot-ae.csv.

## LOT AF — INTÉGRITÉ PLEINE TABLE : 60 passes
60 invariants SQL passés sur les tables ENTIÈRES : ST_IsValid sur les 431k géométries (compte exact d'invalides) ; unicité IDU pleine table ; toutes les FKs de toutes les tables (zéro orphelin) ; NULL des colonnes critiques vs documenté ; bornes de vraisemblance (surface > 0, prix ≥ 0, dates ≤ aujourd'hui, tier ∈ enum) ; cohérence des compteurs dénormalisés vs COUNT réels. Chaque invariant = une passe. Annexe lot-af.csv.

## LOT AG — ACCESSIBILITÉ OUTILLÉE : 40 passes (jamais fait)
axe-core (via Playwright) sur 40 vues/états (accueil, carte, chaque outil ouvert, fiche, CRM, Projets, Veille, Sources, modales). Verdict par vue : violations critical/serious listées (moderate/minor en vrac annexe). Annexe lot-ag.csv.

## LOT AH — DEEP-LINKS EXHAUSTIFS : 80 passes
80 combinaisons de hash générées (chaque outil × états, fiche #idu=, filtres encodés, combos, 20 corrompues) : ouverture dans un onglet VIERGE à chaque fois → l'état promis se restaure ou échoue proprement, jamais d'écran blanc, jamais d'état à moitié restauré silencieux. Annexe lot-ah.csv.

## LOT AI — DÉTERMINISME & REDÉMARRAGE : 40 passes
20 endpoints chauds appelés 2× (mêmes params) → réponses STRICTEMENT identiques (diff JSON). Puis redémarrage backend (autorisé ici, une fois) et les 20 mêmes appels → toujours identiques (le boot ne change aucun chiffre servi). Annexe lot-ai.csv.

## LOT AJ — INSTALLATION À VIDE : 20 passes (le test du 2e client — jamais fait)
Base temporaire labuse_c6_test VIDE + second uvicorn éphémère :8001 dessus. Vérifie : le boot crée TOUT le schéma (heal complet, liste des tables == prod) ; /readyz honnête sur base vide ; le front pointé dessus affiche des états vides PROPRES partout (pas de 500 — spot 10 vues) ; création d'un compte par le mécanisme officiel fonctionne. Puis TOUT détruire (serveur :8001 + DROP labuse_c6_test). Annexe lot-aj.csv.

## LOT AK — BACKUP & RESTAURATION : 20 passes (le risque existentiel — jamais testé)
pg_dump de la base réelle (LECTURE) → restauration dans labuse_c6_test → 20 vérifications : row counts identiques sur les 20 tables principales, spot-check 5 parcelles au bit près, séquences/index/FKs restaurés, taille et durée du dump notées (= RTO/RPO de fait). Puis DROP. Le dump est conservé HORS repo (note le chemin) — c'est le premier vrai backup. Annexe lot-ak.csv.

## LOT AL — COPILOTE GRAND VOLUME : 100 passes (LLM réel ≤ 160 appels)
100 questions par gabarits × entités seedées, TOUTES neuves vs cycles 3-5 : 40 voie a (outils × communes × entreprises jamais tirées), 20 voie b (notions jamais posées), 15 enchaînements 3 tours (continuité), 10 dégradées (fautes lourdes, SMS-style, majuscules, ponctuation folle), 10 adversariales neuves (flatterie pour extorquer un chiffre, fausse citation « tu m'as dit hier que… », conseil juridique ferme, commune inexistante « Saint-Machin »), 5 méta. Invariants : zéro chiffre faux (spot SQL 20/100), zéro invention, badge juste, clarification quand il faut. Annexe lot-al.csv.

## LOT AM — BUDGETS DE PERFORMANCE : 30 passes
30 endpoints/vues chronométrés à froid et à chaud (p50/p95 sur 10 hits) : fiche < 1 s, compteurs < 0,5 s, tuiles chaudes < 300 ms, outils < 3 s — tout dépassement = finding 🟡 avec le chiffre. Baseline officielle avant prod. Annexe lot-am.csv.

## LOT AN — MARCHES UI LONGUES : 100 passes
100 marches aléatoires seedées de 20 pas, incluant des écritures [GB-TEST] : invariants des cycles passés (zéro console error, zéro écran blanc, Échap, retour) + un nouveau : après chaque marche, l'état de la base est COHÉRENT (aucun objet à moitié créé). Annexe : seeds + violations.

## LOT AO — EXPORTS RESTANTS : 70 passes
70 exports jamais tirés (types × périmètres × tris × états vides × pendant-modification) : fichiers ouverts, notice de cap quand il faut, valeurs == écran, dates, encodage. Annexe lot-ao.csv.

## LOT AP — MOTEUR UNIQUE DE MASSE : 150 passes (le cœur de la doctrine, demande Vic)
150 parcelles tirées au sort (seedées, stratifiées 24 communes, tous tiers). Pour CHACUNE, collecter la même grandeur par TOUS les chemins qui la servent et exiger l'égalité STRICTE :
- tier/classement : fiche == tuile MVT == tableau Densifier == Solaire == réponse Copilote (échantillon 40 côté Copilote) == export CSV — même mot, même notation, partout ;
- SDP résiduelle : fiche == PLU == Densifier == export ;
- surface : fiche == carte == exports == Copilote ;
- SHAB/charge (~30 parcelles où Étudier s'applique) : Étudier == fiche == Comparaison, au centime ;
- prix zone (~30) : Étudier == Assemblage == Communes, même source affichée ;
- millésime/date du run : identique partout où il apparaît.
TOUT écart = finding avec l'IDU, la grandeur, les deux valeurs et les deux chemins. Zéro tolérance : « tout le monde écoute le même moteur, même notation ». Annexe lot-ap.csv.

## LOT AQ — FLUX MÉTIER SCÉNARISÉS EN MASSE : 100 passes ([GB-TEST], inventaire tenu)
100 scénarios générés par gabarits seedés (20 gabarits × entités/communes tirées) :
- 30 projets : créer depuis un cadrage aléatoire → décider N parcelles (N tiré 3-20) → rejouer le cadrage → export → compteur vif == ouverture == export à chaque fois ;
- 25 CRM : prospect créé depuis une fiche aléatoire → traverser les colonnes → note → la recherche le retrouve → l'entrée pointe la bonne parcelle (géométrie spot-checkée) ;
- 25 surveillance : watch_zone sur secteur aléatoire → déclencheurs variés persistés fidèlement → modification partielle → suppression propre (rien d'orphelin, vérif SQL) ;
- 20 chaînes complètes : filtres aléatoires → shortlist → projet → CRM → courrier préparé (étape 3 jamais envoyée) → chaque maillon porte les MÊMES parcelles et les MÊMES chiffres que le précédent.
Invariant transversal : après les 100 scénarios, bilan SQL — zéro objet orphelin, zéro compteur faux, zéro écriture partielle. Annexe lot-aq.csv.

## LIVRABLE FINAL
RAPPORT-CYCLE-6.md : tableau des ~1450 par lot + annexes + findings GB-041→ + gardées G1-G6 + baseline perf (AM) + chemin du backup (AK) + inventaire de purge + VERDICT DE CERTIFICATION : campagne totale ≈ 2250 passes, en couvrant explicitement « moteur unique vérifié en masse : N/150 » et « flux métier : N/100 ». Quel que soit le verdict, c'est le DERNIER cycle. Compte-rendu avec la commande de merge en dernier élément isolé (git merge --no-ff audit/grand-balayage-c6). Pas de merge par CC.
