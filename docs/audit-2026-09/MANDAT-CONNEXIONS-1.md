# MANDAT CONNEXIONS-1 — audit exhaustif des connexions et interconnexions

**Nature : AUDIT EN LECTURE SEULE.** Aucune modification de code. Le seul fichier écrit est le rapport.
**Branche : `audit/connexions-1`** (depuis `main`). Bloc commun habituel.
**Livrable : `docs/audit-2026-09/CONNEXIONS-RAPPORT.md`** — commité par CC avant le compte-rendu.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.

## Méthode

Pour **chaque ligne** ci-dessous, CC établit l'état réel en lisant le code (front → api.ts → endpoint → module → table), pas en supposant. Chaque ligne du rapport porte :

| connexion | état | preuve | impact |
|---|---|---|---|
| ce qui doit être relié à quoi | **OK** · **KO** (branché mais faux/cassé) · **ABSENT** (rien n'existe) · **DOUTE** (indéterminable sans exécution) | `fichier:ligne` ou test | ce que voit l'utilisateur si c'est KO |

Règles :
- **« Branché » veut dire bout en bout** : un bouton qui appelle un endpoint qui écrit en base qui est relue par l'écran cible. Un bouton qui appelle un endpoint qui ne fait rien = KO.
- **Une seule source de vérité par donnée** : si deux écrans lisent la même chose par deux chemins, le signaler même si les deux marchent aujourd'hui.
- **Le front ne calcule pas** : tout calcul métier trouvé côté front (scoring, prix, surfaces, valorisation) est un KO, même juste.
- Le rapport se termine par **les KO classés par impact**, du plus grave au plus bénin, et une **liste des connexions que ce mandat n'avait pas prévues** et que CC a trouvées en chemin.

---

## A — Un seul moteur, une seule vérité

A1. Inventaire des moteurs : `sector_price` · scoring et tiers (Priorité / À suivre) · capacité résiduelle et SDP · rattachement parcelle (adresse → IDU) · valorisation du foncier nu · détection des signaux (permis récent, succession, permis abandonné). Pour chacun : **une seule implémentation**, chemin d'import, et liste de tous ses appelants.
A2. Aucune réimplémentation partielle : chercher tout code front ou backend qui recalcule l'un de ces moteurs (même une formule simplifiée pour un affichage).
A3. **Tiers identiques partout** : une parcelle « Priorité » l'est dans Projets, Radar, Scan patrimoine, Densifier, fiche parcelle, exports. Vérifier que tous lisent le même champ, du même run.
A4. **Dates de valeur** : d'où vient chaque « valeurs au JJ/MM » affiché (accueil, projets, fiche, exports, Copilote) ? Une table de millésimes unique, ou des dates codées çà et là ?
A5. **Run courant** : quel run de scoring est « le bon » (ex. `m135-run2-ile`), qui le décide, et tous les écrans lisent-ils celui-là ?
A6. **Caches** : lister chaque cache (front, backend, matérialisations). Pour chacun : qu'est-ce qui l'invalide quand une source est rafraîchie ? Un cache sans invalidation = KO.
A7. **Couches, filtres, outils** : chacun écoute-t-il la version courante des données, ou une table/vue figée d'une version antérieure ? Lister toute table « _old », « _v1 », « _backup », « _tmp » encore lue par quelque chose.

## B — Accueil et rail

B1. Les 4 cartes d'entrée ouvrent le bon écran (Carte, Radar, Copilote, tiroir Outils).
B2. Compteur d'outils : lu depuis le registre, égal au nombre d'outils visibles (15).
B3. « Toutes les données sont à jour » : sur quoi repose cette phrase ? Si c'est un texte fixe, c'est KO — elle doit refléter l'état réel des sources.
B4. « voir les données → » ouvre Sources.
B5. Rail : chaque entrée mène à sa surface ; Admin n'est rendu que pour le rôle admin ; l'état actif suit la route.

## C — Recherche globale (barre du bandeau)

C1. Ce qu'elle accepte réellement : IDU · adresse · commune · nom de propriétaire · SIREN · annonce Radar · projet. Pour chaque type : atteint-il la bonne cible ?
C2. Le rattachement adresse → IDU utilise le moteur A1 (pas un géocodage parallèle).
C3. Une adresse ambiguë propose des choix, ne prend pas le premier en silence.

## D — Carte

D1. Couches : chaque couche lit une source identifiée, avec sa date de valeur ; lister couche → source → millésime.
D2. Filtres : chaque filtre agit sur les mêmes données que les couches (pas un jeu à part).
D3. **« Créer une veille sur cette recherche »** : crée réellement une veille, visible dans Veille, avec les critères exacts du filtre courant ; la veille se déclenche ensuite (voir G).
D4. Clic parcelle → fiche parcelle avec le bon IDU ; fiche commune → chip « Fiche commune » et sélecteur de commune donnent la même fiche.
D5. Fond de carte, cadastre, zoom : pas de source de tuiles différente entre écrans.

## E — Fiche parcelle

E1. Chaque section (Urbanisme, Constructibilité, Risques et protections, propriétaire, DVF, permis, annonces Radar, secteur…) : source, moteur A1 utilisé, date de valeur.
E2. **Boutons d'action** : « ajouter à un projet » → le projet choisi (pas le dernier ouvert) ; « CRM » → la piste choisie ; **cloche** → une veille parcelle dans Veille ; « signaler » → arrive au dashboard admin avec l'IDU, l'auteur et le motif.
E3. **Adresse exacte** : réservée aux abonnés, y compris dans les exports et les mails.
E4. Tuiles d'export (PDF, Dossier, Finance, Cadastre, Argumentaire, Maps, Courrier, Pré-dossier PC) : chacune lit **la même fiche que l'écran**, mêmes chiffres, même date de valeur — pas une seconde requête ni un cache différent. « Courrier » ouvre l'outil Courrier propriétaire pré-rempli. « Maps » ouvre au bon point.
E5. Passerelles vers les outils (« Étudier ce bien », etc.) : pré-remplies avec l'IDU courant.
E6. Bloc « Autour de cette parcelle » : même moteur que l'outil Étude de zone.

## F — Fiche commune

F1. Chaque carte (Terrain nu, Annonces — Radar, Loyers, Foncier repéré, Zonage, Risques, Population & logement, Quartiers prioritaires, marché, rareté ZAN, rythme d'instruction…) : source, millésime, moteur.
F2. Chaque carte cliquable ouvre le détail correspondant (Radar filtré sur la commune, PLU de la commune, permis de la commune…).
F3. Les mêmes chiffres apparaissent à l'identique dans l'outil Communes.

## G — Veille (surface) et déclenchement

G1. **Les trois types de veille** — annonces (Radar), filtre (recherche carte), parcelle (cloche) — existent-ils tous trois, et sont-ils créés par les bons boutons (D3, E2, Radar) ?
G2. Ce qui les évalue : le cron (CRON-1/2) ou autre ; à quelle fréquence ; sur le run courant A5.
G3. Un déclenchement produit **une entrée unique** relayée à : cloche · mail · historique de la veille · dashboard (compteur). Lister les quatre chemins et vérifier qu'ils partent du même événement.
G4. Le mail part réellement (transport configuré, expéditeur, gabarit, désabonnement) ; il ne contient jamais l'adresse exacte pour un non-abonné ni le contenu d'une annonce.
G5. Une veille se désactive, se supprime, et son propriétaire est le seul à la voir.

## H — Radar

H1. Annonces → parcelle : rattachement par le moteur A1 ; degré de certitude affiché.
H2. Filtres Radar (commune, type, prix, surface, rattachement, vendeur, prix face au marché) : agissent sur les mêmes annonces que la carte et que la fiche commune (« 5 biens en vente »).
H3. « Sous le marché » : référence = `sector_price`, pas un calcul local.
H4. **Notifications Radar** : nouvelle annonce dans une veille annonces → G3 (cloche + mail + dashboard).
H5. Dépôt agence : écrit dans la même table que la collecte, avec le flag admin ; invisible des clients tant que le flag est fermé, dans **tous** les écrans (Radar, fiche parcelle, fiche commune, Mon secteur, exports).
H6. Doctrine : aucun stockage du contenu d'annonce, nulle part (colonnes, logs, caches).

## I — Projets

I1. Cadrage → parcelles : le même run A5 ; compteurs (retenues / écartées / à trier / tiers) lus du backend.
I2. Bandeau d'analyse : chiffres = ceux de la liste dessous.
I3. Retenir / écarter → écrit, relu partout (Scan patrimoine « actionnables hors écartées », Kanban CRM).
I4. **« Mes courriers »** → l'outil Courrier propriétaire (mêmes courriers, mêmes statuts) → dashboard admin (Vic voit qu'une cliente veut qu'il dépose un courrier) → statut retour (déposé / envoyé / répondu) relu dans Projets et CRM.
I5. Un projet appartient à un compte ; jamais visible d'un autre.

## J — CRM

J1. Parcelle retenue → piste CRM (création automatique ou manuelle ? cohérente ?).
J2. Piste → contact propriétaire (source du nom et de l'adresse postale), courrier (I4), relances, statut.
J3. Kanban : colonnes et statuts identiques à ceux du Courrier propriétaire et du dashboard.
J4. La **boucle se ferme** : retenue → piste → courrier → réponse → statut, sans ressaisie. Pointer chaque rupture.
J5. Données CRM strictement par compte.

## K — Copilote

K1. Connexion API : modèle utilisé, clé, gestion d'erreur, timeout, repli.
K2. **Il lit les moteurs A1** (ne recalcule rien) ; ses chiffres sont ceux des fiches, à la même date de valeur.
K3. Ses 4 missions (donnée, web, notion, script) : chacune branchée sur sa source.
K4. **Crédits** : consommation comptée **par compte**, remontée au dashboard (Stéphanie a dépensé N ; total N ; possibilité d'ajouter des crédits à un compte depuis le dashboard). Quota (80/jour) appliqué par compte.
K5. **Mémoire des recherches : par compte, jamais globale.** Un utilisateur ne voit que ses propres conversations — vérifier la requête de la liste « Reprendre » et l'endpoint de lecture d'une conversation (contrôle d'appartenance).
K6. Ses réponses proposent d'ouvrir l'outil ou la parcelle citée (pas un cul-de-sac).

## L — Les 15 outils, un par un

Pour chacun : entrée (IDU/adresse via C2) · moteur A1 · source et millésime · passerelles sortantes (vers fiche, projet, CRM, courrier) · ce qu'il écrit, et où c'est relu.

L1 Étudier un bien (bloc secteur = `sector_price`) · L2 Faisabilité · L3 Taxe d'aménagement · L4 Pièges et risques · L5 PLU · L6 Comparer des parcelles · L7 Assemblage · L8 Scan patrimoine (onglet possèdent + onglet construisent ; recherche par nom réellement branchée ; ponts vers Permis et fiche) · L9 Courrier propriétaire (voir I4/J2 ; transport d'envoi ; statut) · L10 Remonter le temps · L11 Permis (Sitadel, millésime, lien vers opérations de L8) · L12 Densifier l'existant (même capacité résiduelle que la fiche) · L13 Prospection solaire (piscines + ensoleillement ; sources) · L14 Communes (mêmes chiffres que F) · L15 Étude de zone (même moteur que E6).

## M — Sources

M1. Chaque source : nom · fournisseur · millésime chargé · date de dernier rafraîchissement · **qui la consomme** (couches, outils, moteurs). Produire la matrice source → consommateurs.
M2. **Dashboard** : chaque source y remonte son état (à jour / en retard / en erreur) ; un agent vérifie l'existence d'une nouvelle version ; l'admin peut désactiver une source depuis le dashboard, et la désactivation se propage aux consommateurs (l'écran dit « source désactivée », pas un chiffre faux).
M3. La page Sources affiche les mêmes millésimes que ceux réellement lus (A4).

## N — Dashboard admin

N1. Chaque tuile/section : quelle source elle écoute (comptes, crédits IA, veilles, signalements, courriers à déposer, dépôts agence, sources, sessions, santé). Pour chacune : même donnée que la surface d'origine, pas une copie qui diverge.
N2. Actions admin (ajouter des crédits, ouvrir/fermer le flag dépôt, désactiver une source, gérer une invitation, révoquer une session) : effectives et relues immédiatement par les écrans clients.
N3. **Santé technique** : les endpoints lus par les écrans sont-ils surveillés ? Un endpoint mort doit se voir ici (cas vécu : `/accueil/chiffres` vivant, écran vide, rien ne l'a signalé).

## O — Comptes, licences, sessions, mails

O1. Invitation → essai 48 h → conversion → licence : chaque étape écrite et visible au dashboard ; expiration de l'essai : que deviennent l'accès et les données ?
O2. Multi-licences : sièges comptés, rattachés à la structure.
O3. SESSION-1 (si livré) : éviction visible au dashboard comme signal commercial, jamais comme blocage.
O4. Tous les mails sortants (invitation, veille, courrier, Radar) : un seul transport, un seul expéditeur, gabarits DA, respect d'E3/H6.
O5. Cloisonnement : projets, CRM, veilles, conversations Copilote, courriers, crédits — **strictement par compte**. Chercher tout endpoint qui liste sans filtrer par propriétaire.

## P — Doctrine, vérifiée comme des connexions

P1. Aucun écran, export, mail, log ou cache ne contient le contenu d'une annonce.
P2. Adresse exacte : abonnés seulement, partout.
P3. Aucun robot sur les portails : aucun fetch planifié vers un portail (le one-shot du dépôt est le seul appel sortant, à la demande).
P4. « Rien n'entre sans validation humaine » : la collecte assistée n'écrit rien en base sans passage par l'admin.

---

## Compte-rendu attendu

Le rapport `CONNEXIONS-RAPPORT.md`, complet, une ligne par connexion, avec en tête : nombre de lignes par état, **les KO classés par impact**, et les connexions non prévues trouvées en chemin. Aucun correctif dans ce mandat — les corrections feront l'objet du mandat CONNEXIONS-2, écrit à partir du rapport. Commit du rapport par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff audit/connexions-1
```
