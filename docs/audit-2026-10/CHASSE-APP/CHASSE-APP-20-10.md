# App LABUSE — campagne profonde du 19-20/10/2026

Troisième passe, avec autorisation de **créer des données**. J'ai joué ce que je
n'avais pas pu jouer : créer deux projets, ajouter puis retirer une parcelle du
CRM, écrire une note, préparer un courrier jusqu'à l'écran d'envoi, aller
jusqu'à la page de paiement Stripe, et interroger le Copilote.

**Tout ce que j'ai créé a été supprimé** : les deux projets sont archivés, le
CRM est revenu à zéro parcelle. Je n'ai **pas** envoyé de courrier à un
propriétaire et je n'ai **pas** payé.

Cette passe a surtout servi à **vérifier mes propres rapports**. Elle en annule
quatre points. Commençons par là, parce que tu as déjà envoyé les mandats.

---

# PARTIE 1 — Ce que je retire de mes rapports des 19/10

## 1. Les ventes DVF ne sont pas en panne. Je me suis trompé.

Je t'avais écrit que c'était « le défaut le plus coûteux commercialement » et
j'avais demandé à Claude Code de commencer par là. C'est faux.

Ce que dit l'app sur elle-même, relevé aujourd'hui sur `/healthz/crons` :

| | |
|---|---|
| tâche `ingest-dvf` | statut **ok**, dernier succès 19/10 à 21 h 16, âge **0 jour** |
| source `dvf` | dernière donnée **31/12/2025**, dernière ingestion **20/10/2026** |
| | écart 293 jours, seuil toléré 364 jours, statut **à jour** |

Et ce que publie la source, vérifié directement chez Etalab
(`files.data.gouv.fr/geo-dvf/latest/csv/`) : les millésimes disponibles sont
**2021, 2022, 2023, 2024, 2025**. Le répertoire `2026/` est vide.

**Il n'existe pas de DVF 2026.** La ligne « DVF — jusqu'à déc. 2025 » affichée
sur la fiche n'est pas un retard : c'est la donnée la plus fraîche qui existe,
et l'app le dit honnêtement. Le rechargement fonctionne.

Deux lectures possibles : soit Claude Code l'a réparé aujourd'hui même, soit il
n'a jamais été cassé et mon relevé du 19 était mauvais. Dans les deux cas,
**il n'y a plus rien à faire ici** — et si Claude Code n'y a pas encore touché,
dis-lui d'arrêter.

## 2. L'app n'est pas lente. Ma mesure l'était.

J'avais annoncé « 8 à 10 secondes par outil », « PLU 37 secondes »,
« `/usage/event` 4,8 secondes ». Je mesurais mal : j'attendais un nombre de
secondes fixe, puis je notais ce que j'avais attendu. Je lisais mes propres
pauses.

Mesuré proprement aujourd'hui, en attendant le silence réseau et en lisant la
durée réelle de chaque requête :

| Outil ouvert | Jusqu'au silence réseau | Requête la plus lente |
|---|---|---|
| PLU | 4,6 s | `/usage/event` 143 ms |
| Permis | 4,3 s | `/modules/permis` **942 ms** |
| Communes | 3,9 s | `/usage/event` 182 ms |
| Faisabilité | 3,9 s | `/usage/event` 346 ms |
| Successions à venir | 5,3 s | `/modules/successions` 716 ms |

**Aucune requête de l'app ne dépasse une seconde.** `/usage/event` répond entre
143 et 365 ms : il n'est pas un problème. Les 37 secondes du PLU ne se
reproduisent pas.

Reste **une** lenteur réelle, mesurée deux fois contre un repère propre (le
nom du secteur, qui n'apparaît qu'une fois les données arrivées) :
**ouvrir une fiche parcelle prend 9,1 s**. Et le Dossier PDF se fabrique en
8,2 s côté serveur (mesuré en direct).

→ **Le point 4 du mandat tombe**, sauf la fiche parcelle.

## 3. Le Copilote répond en 4 secondes, pas en 126.

Même erreur de ma part. Les durées réelles de `/api/copilote-v2/ask`, sur
quatre questions : **1 691, 2 941, 3 955 et 4 078 ms**.

## 4. Sur /flash, la liste de suggestions s'affiche.

Le point C de mon complément est faux. Elle s'affiche très bien — j'avais
rempli le champ par programme au lieu de **taper**, donc aucune frappe n'était
émise. En tapant « 5 rue des Béliers » :

> 5 Rue des Beliers, Saint-Leu (97424) · **5 Rue des Béliers, Saint-Paul
> (97460)** · 15 Rue des Beliers, Saint-Leu (97424) · …

Mieux : **le bon numéro arrive en tête** et la commune est affichée. La seule
scorie est un doublon (« 15 Rue des Beliers, Saint-Leu » apparaît deux fois).

## 5. La commune tapée n'est plus ignorée.

Le point B tombe aussi. « 5 rue des Béliers Saint-Paul » ne renvoie que des
adresses de 97460 Saint-Paul.

## 6. Et je m'étais trompé d'endroit sur le point A.

J'avais écrit « la cause se lit sur `/adresses/autocomplete` » en pointant
`app.py:2598`. Non. Voir ci-dessous.

---

# PARTIE 2 — Ce qui est grave, et nouveau

## A. La base de données n'a pas été sauvegardée depuis 50 jours

C'est le point le plus grave de toute la campagne, et il est écrit en clair sur
la page de santé de l'app, `/healthz/crons` :

> `backup-postgres` — statut **en_retard** — dernier succès **30/08/2026** —
> âge **50 jours** — attendu tous les **2 jours**

Dans cette base il y a les projets, les parcelles retenues, le CRM, les notes,
les courriers préparés, les comptes. Cinquante jours sans filet. Si la base est
perdue cette nuit, tout est perdu, et il n'y a rien pour revenir en arrière.

`/healthz/crons` renvoie d'ailleurs `"ok": false` globalement.

**À faire avant tout le reste.** Avant Stripe, avant les adresses, avant tout.

**Vérifier :** `backup-postgres` doit afficher un succès daté du jour, et il
faut avoir **restauré une sauvegarde pour de vrai** au moins une fois — une
sauvegarde jamais restaurée n'est pas une sauvegarde.

## B. Quatre tâches planifiées sont mortes

Toujours `/healthz/crons`, même page :

| Tâche | État | Ce qu'elle fait |
|---|---|---|
| `filtres-sources` | **jamais lancée** | rejoue les contrôles qualité sur les versions servies |
| `sync-gpu` | **jamais lancée** | diff PLU des 24 communes → veille foncière + bandeau PLU |
| `sonde-sources` | en retard de **27 jours** (attendu : 2) | détecte une nouvelle version chez les fournisseurs |
| `coherence-robinets` | en retard de **27 jours** (attendu : 2) | détecte les fuites entre robinets et l'eau ancienne |

Les deux premières n'ont **jamais** tourné. Conséquence directe et visible :
la source `gpu_plu` a une donnée du 14/09/2026 et une ingestion **vide** — les
changements de PLU ne sont jamais détectés, alors que c'est le cœur du métier.

Et les deux sondes qui devaient prévenir quand une donnée vieillit sont
elles-mêmes à l'arrêt depuis le 22 septembre. Les gardiens dorment.

L'app signale aussi elle-même deux retards : `dpe` (donnée du 23/09, 27 jours
pour un seuil de 14) et `ban` (donnée **du 19/08**, 62 jours pour un seuil de
60 — et ingestion du 19/08 également, donc la base adresses n'a pas été
rechargée depuis deux mois). Trois autres sources n'ont jamais été ingérées :
`sudocuh` (donnée de fin 2024), `ortho_piscine` et `cosia` (début 2025).

## C. L'envoi postal n'est pas branché, et l'écran ne le dit pas

J'ai préparé un courrier jusqu'au dernier écran. Il affiche :

> **1 courrier × 4,04 € = 4,04 € TTC** — impression, mise sous pli,
> affranchissement, suivi.
> [ Demander l'envoi à LABUSE ]

Pendant ce temps, le serveur répond ceci sur `/courrier/statut` :

```json
{"disponible": false, "provider": "stub",
 "raison": "L'envoi postal n'est pas encore disponible — la demande est enregistrée.",
 "tarif_unitaire_eur": 4.04}
```

Le fournisseur est un **bouchon**. L'app le sait, écrit la phrase qu'il
faudrait montrer, et ne la montre pas. Un client à 349 €/mois prépare son
courrier, lit un prix et une liste de prestations, clique, et croit que sa
lettre partira.

**C'est la deuxième chose en mode test en production, après Stripe.**

**Vérifier :** tant que `disponible` est `false`, l'écran d'envoi doit afficher
la phrase du serveur, et le prix ne doit pas être présenté comme une
prestation en cours.

## D. Le courrier part au nom de LABUSE, pas au nom du client

J'ai téléchargé l'aperçu PDF (le bouton de relecture, qui est une excellente
idée). Voici ce qui est écrit, mot pour mot, en pied des deux pages :

> « Analyse réalisée avec LABUSE, plateforme d'intelligence foncière
> spécialisée sur La Réunion, **pour le compte de LABUSE**. »

Et dans le corps :

> « Si vous souhaitez aller plus loin, nous pouvons vous adresser gratuitement
> une analyse plus complète de votre terrain […] Il suffit de la demander à
> **contact@labuse.immo**. »
> « Cette étude vous est offerte par **LABUSE** qui intervient à Saint-Paul. »

Le professionnel paie 4,04 € par pli pour envoyer une lettre signée LABUSE,
qui renvoie le propriétaire vers LABUSE. Son nom n'apparaît nulle part.

Et ce n'est pas un réglage oublié : j'ai cherché. **« Mon compte » ne contient
que** l'adresse e-mail, le plan, la date de fin d'essai, un changement de mot
de passe, un lien contact et la déconnexion. Aucun champ raison sociale,
adresse, signature. Il n'y a nulle part où mettre le nom du client.

C'est peut-être voulu — LABUSE qualifie, puis transmet. Mais alors il faut
l'écrire sur l'écran d'envoi, parce que personne ne s'attend à payer pour
prospecter au nom de son fournisseur. **C'est une décision pour toi, pas un
bug à corriger à l'aveugle.**

## E. Stripe est toujours en test — confirmé par le bout

J'ai cliqué « Payer 79 € ». La session ouverte est `cs_test_a1s7A130ecY4RI…`,
et la page affiche le bandeau **« Environnement de test »**. Le dernier
événement Stripe reçu par l'app date toujours du **24 juillet**.

Personne ne peut acheter de Flash aujourd'hui. Inchangé depuis mon premier
rapport.

## F. Au moment de payer, le vendeur s'appelle « LASTONE »

Sur la page de vérification, LABUSE écrit — très bien — « Vendu par LABUSE
(CLOSING CREST) · contact@labuse.immo ».

Puis la page de paiement affiche, en haut et sur le bouton :

> **LASTONE** · Environnement de test · **Payer LASTONE**

Trois noms pour un paiement de 79 € : LABUSE, CLOSING CREST, LASTONE. C'est le
moment précis où l'acheteur sort sa carte. Le nom affiché vient du compte
Stripe (« nom public » / nom de l'entreprise) et se règle dans Stripe, pas dans
le code.

**À régler en même temps que la bascule en réel**, c'est la même visite.

## G. La page de paiement met 92 $US en avant, pas 79 €

Toujours sur l'écran Stripe :

> Choisir la devise — **92,13 $US** / 79,00 €
> 1 EUR = 1,1662 USD (**frais de conversion de 4 % inclus**)
> LABUSE Flash … **92,13 $US**

Le prix mis en avant est en dollars, majoré de 4 %, alors que la page
précédente promet « Paiement unique de 79 € » et « Prix total, sans TVA à
ajouter ».

J'ai refait l'essai avec un navigateur réglé en français, fuseau de La Réunion,
position à Saint-Denis : **même résultat**, 92,14 $US en tête. Je ne peux pas
exclure que Stripe se fie à l'adresse IP de ma machine, qui n'est pas à La
Réunion — c'est le réglage **Adaptive Pricing** de Stripe. À vérifier depuis
une vraie connexion réunionnaise, et à désactiver s'il est actif.

---

# PARTIE 3 — Confirmé, toujours ouvert

## H. Le classement des adresses dans la barre de recherche

**C'est le point A de mon complément, et il est toujours là.** En tapant
vraiment, dans la barre de l'app, avec la commune :

| Demandé | Ce qui arrive en tête |
|---|---|
| 5 rue des Béliers Saint-Paul | **15** Rue des Béliers, puis 5 |
| 2 rue de Paris Saint-Denis | **12** Rue de Paris, puis 2, 2 bis, 22 |
| 1 chemin Summer Saint-Paul | **10, 100, 101, 102** — le n° 1 est absent |

C'est un tri de texte : 1, 10, 100, 101 / 12, 2, 22.

**L'endroit exact, cette fois.** Ce n'est pas `/adresses/autocomplete`. La barre
de recherche appelle :

```
GET /api/recherche/suggest?q=5 rue des Béliers Saint-Paul
    &types=adresse,cadastre,proprietaire,siren,lieu_dit
```

et le serveur renvoie lui-même le mauvais ordre :

```json
{"groupes":[{"type":"adresse","items":[
  {"label":"15 Rue des Béliers","sub":"97460 Saint-Paul","idu":"97415000EY1268"},
  {"label":"5 Rue des Béliers", "sub":"97460 Saint-Paul","idu":"97415000EY0109"}
]}],"total":2,"ms":156.8}
```

**Et la bonne nouvelle : le correctif existe déjà dans la maison.** La liste de
`/flash`, elle, met le bon numéro en premier. Il suffit de reprendre son
classement dans `/api/recherche/suggest`.

**Vérifier :** les trois lignes du tableau ci-dessus doivent donner le bon
numéro en première position.

## I. La surface du dessin au lieu du cadastre — sur /flash *et* sur le CRM

Sur `/flash?idu=97415000EY0109`, l'écran de vérification affiche toujours :

> EY 0109 — Saint-Paul · **1150 m²**

alors que la contenance cadastrale est de **1 111 m²**. Et c'est aussi le cas
sur **la carte du CRM** : « 97415000EY0109 — **1 150 m²** · Saint-Paul ».

Font bien les choses, en revanche : la fiche (« 1 111 m² » puis « Dessin du
plan : 1 150 m² »), le Dossier PDF (« Surface cadastrale : 1 111 m² ») et
l'aperçu du courrier (« 1 111 m² »). Il n'y a que ces deux écrans à aligner.

Au passage, `1150 m²` sur /flash est écrit sans espace de milliers, contre
« 1 111 m² » partout ailleurs.

## J. Les trois retouches de texte de /flash

Pas appliquées. Le pied de page dit toujours « Document d'aide à la décision
établi à partir des données publiques. Il ne remplace ni le certificat
d'urbanisme… » au lieu de « **LABUSE ne remplace** ni… ».

Et la description du produit **dans Stripe** dit encore : « Rapport Flash — UNE
parcelle, un PDF sourcé, paiement unique. **Pré-analyse** sur données
publiques ». C'est le dernier endroit où « pré-analyse » survit, et il est
visible par l'acheteur. Il se change dans le catalogue Stripe.

## K. Le halo de focus, toujours absent

Vérifié au clavier sur les huit entrées du rail : `outline: none, 0px` et
aucune ombre portée sur les huit. Rien ne se voit.

## L. « Aucune correspondance » toujours annoncé comme un résultat

```
UL role="listbox"
  LI role="option"  « Aucune correspondance pour « zzzzqqqq9999 » — formats acceptés… »
```

Pas d'`aria-live`. Un lecteur d'écran l'annonce comme un choix sélectionnable.

---

# PARTIE 4 — Nouveau, de gravité moyenne

## M. Radar : aucune annonce n'est rattachée à une parcelle

Le Radar sert 110 biens. Dans sa propre réponse :

> `n_total: 110` · `n_servi: 110` · **`n_rattaches: 0`** · `n_carte: 80`

**Zéro annonce sur 110 n'est reliée à une parcelle cadastrale.** Dans un outil
d'intelligence foncière, faire le lien entre « cette maison est en vente » et
« voici sa parcelle, son zonage, son potentiel » est précisément la valeur
ajoutée. Les 110 fiches restent des annonces nues, avec un lien sortant.

Trois autres choses sur cet écran :

- **Un seul portail.** Les 110 annonces viennent de `leboncoin`. L'écran
  annonce « les biens en vente **sur les portails** », au pluriel, et le site
  parle du marché.
- **La capture date du 6 octobre** (`derniere_capture_at`), soit 13 jours, et
  **cette date n'est affichée nulle part** sur l'écran. Pour une veille de
  marché, la date de relevé est l'information la plus importante après le prix.
- **Deux totaux qui se contredisent** dans la même réponse : `biens_en_vente:
  110`, mais la somme par type donne **149** (terrain 8 + maison 98 +
  appartement **43**) — alors que la liste ne contient aucun appartement.

Enfin, sur 110 biens, **8 sont des terrains**. Pour des chasseurs de foncier,
c'est maigre, et ça mérite d'être dit à l'écran plutôt que découvert.

## N. Projets : « 0 ressortent », quoi qu'on fasse

J'ai créé deux projets. Le second ciblait Saint-Paul avec le signal
**Succession** : 495 parcelles, toutes porteuses d'un signal. Le panneau
d'explication affiche :

> « LABUSE a analysé les 495 parcelles de votre cadrage : **0 ont plus de
> chances que les autres d'être vendues** — 0 À suivre. Elles arrivent en tête
> de votre tri ; **les 495 autres** suivent, sans jugement. »
>
> « Signaux détectés : succession, société en procédure, permis récent, permis
> abandonné »

La phrase se contredit en trois lignes : zéro parcelle ne ressort, « elles »
arrivent en tête, et la ligne suivante énumère les signaux détectés. La charge
serveur confirme que le compteur n'est jamais calculé :
`analyse: {total: 495, priorite: 0, a_suivre: 0, signalees: 0}`. Même chose sur
le projet « toute l'île » : 282 287 analysées, 0 ressortent.

Et l'arithmétique ne tient pas : 0 + « les 495 autres » = 495 analysées.

## O. Projets : deux dates différentes pour la même chose

Sur la carte du projet, dans la liste :

> 282 287 parcelles · **valeurs au 19/10**

Dans le projet ouvert, et dans la charge serveur :

> Signaux détectés : … · **valeurs au 11 oct. 2026** — `valeurs_run: {"label":"q_v18","date":"2026-10-11"}`

Même étiquette, huit jours d'écart. La carte semble afficher la date du jour.
Sur un produit qui vend la fraîcheur, c'est l'étiquette qu'il faut avoir juste.

## P. Projets : « rien n'est retiré » — alors que si

Le récapitulatif annonce :

> « Le vivier entier entre dans le projet, classé — **rien n'est retiré**, tout
> est ordonné. »
> « Vivier : **282 287** parcelles classées par probabilité de mutation »

Or le site annonce 434 582 parcelles à La Réunion. 152 295 n'entrent pas. Et
l'étape précédente l'explique très bien, elle :

> « **Figeable = hors terrains non constructibles et faux positifs**
> (exclusions automatiques du moteur). »

L'exclusion est juste et bien expliquée à l'étape 4 ; c'est le récapitulatif
qui la nie à l'étape 5. Il suffit d'y reprendre la phrase de l'étape 4.

## Q. CRM : la carte déplacée disparaît

Le tableau montre **5 colonnes sur 8** (« 1–5 / 8 »). J'ai déplacé ma parcelle
vers « Opportunité chaude », qui est la 7ᵉ. La carte a disparu de l'écran, les
cinq compteurs visibles sont restés à 0, et il m'a fallu **deux clics sur ›**
pour la retrouver. Seul indice : le bandeau « 1 parcelle suivie ».

Et une fois la parcelle au CRM, le bouton de la fiche devient
`<button disabled>✓ Dans le CRM</button>` : il n'indique pas l'étape où elle se
trouve et n'offre aucun chemin de retour. Pour la sortir ou la déplacer, il
faut aller au CRM et paginer.

## R. Courrier : « EY 109 » au lieu de EY 0109

La référence cadastrale est écrite **« EY 109 »** dans l'objet, dans le corps,
dans la synthèse au dos, et — le plus gênant — dans la consigne d'opposition :

> « Vous ne souhaitez plus recevoir de courrier de notre part : écrivez à
> stop@labuse.immo **en indiquant la référence cadastrale EY 109**. »

La parcelle est la **EY 0109** (IDU 97415000EY0109), et c'est bien ainsi que
l'app l'écrit partout ailleurs. Un propriétaire qui veut exercer son droit
d'opposition citerait une référence qui n'est pas la sienne.

## S. Courrier : l'étape « Rédaction » n'a rien à rédiger

Le bandeau promet « **Écrivez** au propriétaire, LABUSE envoie » et « vous
préparez vos courriers (destinataires + **rédaction**) ». L'étape 2 s'appelle
« Rédaction ». Elle ne contient **aucun champ de saisie** — ni zone de texte,
ni zone éditable : seulement la lettre déjà écrite, en lecture, avec la mention
« Lettre générée automatiquement ».

Soit on renomme l'étape (« Relecture » conviendrait), soit on laisse ajouter
une phrase. En l'état, un professionnel ne peut pas glisser son numéro de
téléphone dans un courrier qu'il paie.

Détail : à l'étape 3, le bouton de retour renvoie à « ← Destinataires », pas à
la rédaction. On ne peut pas reculer d'un pas.

## T. Courrier : « les 3 dernières années » sur des ventes arrêtées à fin 2025

La synthèse au dos affirme :

> « Environnement immobilier : **72 mutation(s) publiée(s)** dans le périmètre
> analysé **sur les 3 dernières années**. »

Les ventes s'arrêtent au 31/12/2025 (c'est la donnée disponible, cf. partie 1).
« Les 3 dernières années » désigne donc 2023-2025, pas octobre 2023 à octobre
2026. Dans une lettre envoyée à un tiers, mieux vaut écrire la période :
« sur 2023-2025 ».

Et ces 72 mutations ne se raccordent pas aux « 26 ventes · section cadastrale »
de la fiche, pour la même parcelle le même jour. Les deux périmètres sont
différents, mais le courrier ne dit pas lequel.

## U. Copilote : des noms de colonnes dans les réponses

Les réponses sont rapides, prudentes et sourcées — mais elles laissent passer
les noms techniques des champs :

> « Surface : 1 111 m² **(surface_parcelle_m2)**. »
> « Zone PLU : Zone U3c (famille U) **(zone_plu_famille)**. »

Deux autres observations :

- **Une question sur deux peut être perdue.** À « Quelle est la surface
  cadastrale de la parcelle 97415000EY0109 **et sa zone PLU** ? », il a répondu
  la zone seulement, sans signaler qu'il laissait la moitié de côté.
- **La surface varie selon la formulation.** Posée seule, la question donne la
  bonne valeur, 1 111 m². Dans ma session du 19 au soir, une question plus
  large avait donné « une surface de **1 150 m²** » — celle du dessin — et la
  phrase « Elle ne dispose pas de rez-de-chaussée. »
- Une question de constructibilité (« puis-je y construire 3 logements ? ») est
  routée vers « la Calculette foncière pour la comparer au prix ».

---

# Ce qui est très bien fait, et que cette passe a confirmé

- **Le Dossier PDF est excellent.** 10 pages, 12 sections, chaque chiffre
  étiqueté « sourcé / ƒ dérivé / estimé / projet », des blocs « VÉRIFIÉ : RIEN »
  et « NON DISPONIBLE ICI », un tableau de sources en clôture, la bonne
  contenance cadastrale, et la bonne mise en garde. C'est le meilleur livrable
  de la maison. Il s'ouvre dans un onglet `blob:` — à surveiller, les
  bloqueurs de fenêtres peuvent l'arrêter, et rien n'indique les 8 secondes de
  fabrication.
- **Le courrier est pensé RGPD.** Adressage non nominatif (« À l'occupant »),
  « aucune identité de propriétaire particulier », une adresse d'opposition
  (`stop@labuse.immo`), un lien vers la page de confidentialité (`#courriers`),
  et un avertissement « ni une autorisation d'urbanisme, ni une offre d'achat,
  ni un mandat, ni un conseil juridique ». L'aperçu PDF avant envoi est la
  bonne idée.
- **Le cadrage des projets est honnête à l'étape 4** : « 495 parcelles
  figeables · la shortlist figera les 200 meilleures », et la définition de
  « figeable » donnée sur place. Les compteurs par zonage sont affichés en
  direct (U : 306 630 parcelles · 131 zones…).
- **Le CRM fonctionne bien** : ajout depuis la fiche avec un menu « AJOUTER
  DANS… » et les 8 étapes, retour immédiat « ✓ Dans le CRM », carte avec
  « Déplacer vers… », « + Note » et « Retirer du CRM », note enregistrée du
  premier coup.
- **Le Copilote ne brode pas.** « Propriétaire : non renseigné pour la parcelle
  97415000EY0109 (donnée absente au run servi) ». Et il demande une précision
  quand il en manque une (« rayon de recherche autour de la parcelle ? »).
- **Aucune erreur JavaScript, aucun appel en échec** sur l'ensemble de cette
  campagne — création de projets, CRM, courrier, Radar, Copilote, Flash.

---

# Fausses pistes de cette passe, à ne pas poursuivre

Je les note parce que je les ai crues un moment :

- **« Le bouton + CRM de la fiche ne fait rien »** : faux. Il ouvre un menu
  « AJOUTER DANS… » avec les 8 étapes. Mon sélecteur attrapait l'entrée du rail
  nommée « CRM », pas le bouton de la fiche.
- **« On ne peut pas retirer une parcelle du CRM »** : faux. « Retirer du CRM »
  est la dernière **option du menu déroulant** « Déplacer vers… », pas un
  bouton. Placement un peu curieux, mais ça marche.
- **« Le Dossier PDF ne se télécharge pas »** : faux, déjà corrigé le 19 — il
  s'ouvre dans un onglet `blob:`.
- **Les quatre points de la partie 1** (DVF, lenteurs, `/usage/event`,
  Copilote à 126 s) : mes erreurs de mesure, pas des défauts.

---

# Ce que je n'ai pas fait, et pourquoi

- **Je n'ai pas envoyé de courrier.** Je me l'étais interdit : il part chez un
  vrai propriétaire d'une vraie parcelle. Je suis allé jusqu'au bouton et je me
  suis arrêté. Le statut du serveur m'a d'ailleurs donné la réponse que l'envoi
  ne m'aurait pas donnée.
- **Je n'ai pas payé.** Je me suis arrêté sur le formulaire de carte Stripe.
- **Le glisser-déposer du CRM**, je ne peux pas le reproduire fidèlement : j'ai
  utilisé le menu déroulant, qui fait la même opération côté serveur.
- **Un vrai test d'utilisation.** Toujours valable : il faut de vrais
  professionnels. Le protocole est prêt dans `TEST-UTILISATION.md`, et le point
  qui le bloquait vraiment — le classement des adresses — est le point H.

---

# Dans quel ordre, maintenant

1. **La sauvegarde de la base** (A). Cinquante jours. Rien d'autre ne compte
   avant.
2. **Les quatre tâches mortes** (B), en particulier `sync-gpu` : les PLU ne
   sont jamais rafraîchis.
3. **L'envoi postal** (C) : afficher la phrase du serveur tant que c'est un
   bouchon. Une heure de travail, un mensonge en moins.
4. **Le nom au nom de qui part le courrier** (D) : ta décision, puis la mettre
   à l'écran.
5. **Stripe en réel, le nom « LASTONE » et la devise** (E, F, G) : une seule
   visite dans Stripe.
6. **Le classement des adresses** (H) : recopier dans `/api/recherche/suggest`
   ce que fait déjà `/flash`.
7. **La surface du dessin** (I) sur `/flash` et sur la carte du CRM.
8. **Les textes et étiquettes** : J, N, O, P, R, S, T, U.
9. **Le halo de focus** (K) et le `role="option"` (L).
10. **La fiche parcelle à 9,1 s** — la seule lenteur réelle.

---

*Relevé le 19 et 20 octobre 2026 depuis un navigateur piloté, connecté au
compte d'essai (essai jusqu'au 21 octobre 2026). Chaque chiffre de ce rapport
vient soit d'un écran, soit d'une réponse serveur citée. Les données créées
pendant la campagne ont été supprimées.*
