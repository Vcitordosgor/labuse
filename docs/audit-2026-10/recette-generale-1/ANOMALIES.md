# ANOMALIES — Recette générale 1 (16/10/2026)

Format par anomalie : **[GRAVITÉ]** titre — Où / Reproduire / Capture / Cause probable (fichier:ligne).
Gravité : **bloquant** (empêche usage/plante) · **gênant** (dégrade sans bloquer) · **cosmétique** (visuel mineur).


---

## Famille 1 — Carte

Bilan : **aucune anomalie bloquante ni gênante.** 3 points cosmétiques/informatifs ci-dessous.
0 erreur console JS, 0 réponse HTTP 4xx/5xx sur l'ensemble de la famille.

### A-01-1 — Recherche : pas de message « aucun résultat » dans le dropdown live
- **Gravité** : cosmétique
- **Où** : barre de recherche globale (header) · `http://localhost:5998/socle/`
- **Reproduire** :
  1. Charger la carte.
  2. Taper « zzzqwerty » dans la barre « Rechercher : IDU, SIREN, propriétaire, adresse… » SANS
     presser Entrée.
- **Observé** : le dropdown n'affiche que les communes-raccourcis fixes (Saint-Denis, Saint-Paul,
  La Possession, Sainte-Marie, Trois-Bassins) et aucun message « aucun résultat ». Le message
  honnête « Aucun résultat (IDU, SIREN, propriétaire ou adresse) pour « zzzqwerty » » n'apparaît
  qu'à la **validation (Entrée)**, sous forme de toast. Un utilisateur qui ne presse pas Entrée
  peut croire que la recherche est muette, ou confondre les communes-raccourcis avec des résultats.
- **Capture** : captures/01-carte/003_search-absurde.png · 004_search-absurde-enter.png
- **Cause probable** : `frontend/src/components/header/Header.tsx:185` — le `setToast('Aucun
  résultat …')` est déclenché au submit (ligne ~156/185), pas sur le dropdown d'autocomplétion
  live, qui n'a pas d'état vide explicite.

### A-01-2 — Compteur « total foncier » : 433 229 vs 432 350 (écart 879)
- **Gravité** : cosmétique
- **Où** : panneau FILTRES, bouton « Voir les N parcelles » · carte
- **Reproduire** :
  1. Charger la carte, ouvrir FILTRES (aucun filtre).
  2. Observer le nombre dans « Voir les N parcelles » au chargement puis après stabilisation.
- **Observé** : la valeur affichée oscille entre **433 229** (cible d'animation / fallback, issue de
  `/accueil/chiffres`.parcelles = parc vivant) et **432 350** (compte SQL live `/filtre?limit=0` =
  base scorée du run q_v18). Écart de 879 parcelles. Les deux chiffres sont légitimes (parc total
  vs périmètre du run servi), mais le chiffre « d'accroche » vu en premier est ~879 plus haut que
  le nombre réellement filtrable. Aucun chiffre faux n'est servi.
- **Capture** : captures/01-carte/001_filtres-panneau-ouvert.png
- **Cause probable** : `frontend/src/components/panel/FiltreLabuse.tsx:632-645` — `totalIle`
  (getAccueilChiffres = 433 229) sert de cible/fallback tandis que `getFiltreCount` (432 350) est
  le live ; vérifié côté API (`/accueil/chiffres`=433229, `/filtre?limit=0`=432350, tous deux
  déterministes).

### A-01-3 — Mobile : app entièrement bloquée (écran-barrage « disponible sur ordinateur »)
- **Gravité** : cosmétique (comportement VOLONTAIRE, pas un défaut — consigné pour traçabilité)
- **Où** : tout viewport mobile (390px) · `http://localhost:5998/socle/`
- **Reproduire** :
  1. Ouvrir en mobile (`ouvrir({mobile:true})`) ou réduire la fenêtre sous le seuil mobile.
  2. Naviguer vers `` ou même un deep-link `#idu=97401000AC0428`.
- **Observé** : un écran unique « LABUSE est disponible sur ordinateur. Ouvrez app.labuse.immo
  depuis votre ordinateur. [Contact] » s'affiche à la place de la carte ; AUCUN panneau
  (COUCHES/FILTRES), recherche, zoom ou bouton n'est monté, même via deep-link. L'écran est
  propre : 0 débordement horizontal (`debordements` = 0), 0 erreur, centré correctement.
- **Capture** : captures/01-carte/001_mobile-chargement-initial.png · 002_mobile-deeplink-idu.png
- **Cause probable** : décision produit assumée — `frontend/src/main.tsx:75-79` : si
  `estAppareilMobile()` alors seul `EcranOrdinateur` (`components/EcranOrdinateur.tsx`) est monté
  (« CHARGEMENT-1 point 6 : téléphone/tablette, l'app NE s'ouvre PAS »). → Les contrôles mobiles
  demandés (panneaux utilisables, texte coupé) sont donc sans objet sur cette famille.

### A-02-1 — Fiche : la valeur de zone « Non publié au GPU » (RNU) est tronquée par ellipsis
- **Gravité** : cosmétique
- **Où** : fiche parcelle, tiroir « Urbanisme », tuile « Zone » · `#idu=97417000BD0967`
  (Saint-Philippe, commune en RNU) ; concerne toute parcelle RNU/sans zone publiée.
- **Reproduire** :
  1. Ouvrir `http://localhost:5998/socle/#idu=97417000BD0967` (recharger pour monter la fiche).
  2. Déplier le tiroir « Urbanisme ».
  3. Regarder la tuile « Zone » : la valeur « Non publié au GPU » ne tient pas dans la case.
- **Observé** : la case `.stat-v` fait 102 px de large pour un contenu de 116 px ;
  `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` → le texte s'affiche tronqué
  « Non publié au GP… ». Le libellé complet reste accessible via l'infobulle (ⓘ). Aucun impact
  fonctionnel, aucun chiffre faux. `debordements()` le remonte (1 seul élément). Même mécanique
  d'ellipsis sur les noms de société longs en valeur d'en-tête repliée (ex. 97407000AS0421
  « SOCIETE ANONYME D'… ») — là c'est acceptable car le nom complet est dans le corps du tiroir.
- **Capture** : captures/02-fiche/001_97417000BD0967-deb-gpu.png · 001_97417000BD0967-rnu-banner.png
- **Cause probable** : `frontend/src/styles/index.css:503` — `.fiche-v6 .stat-v { white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis }` ; valeur posée en `frontend/src/components/fiche/
    Fiche.tsx:957` (`reglesZone ?? 'Non publié au GPU'`). La chaîne RNU « Non publié au GPU » est
    plus longue que la largeur de la tuile de zone. Correctif possible : autoriser le retour à la
    ligne (ou réduire la police) pour cette tuile RNU, ou raccourcir le libellé.

### A-03-1 — Fiche commune : warning React « clés dupliquées » à chaque ouverture
- **Gravité** : gênant
- **Où** : ContextePanel (fiche commune), toutes les communes. Geste : sélecteur commune → « voir la fiche → ».
- **Reproduire** :
  1. Ouvrir la fiche d'une commune (ex. Bras-Panon, Le Port, Entre-Deux…).
  2. Regarder la console : 1–2 warnings `Warning: Encountered two children with the same key, %s`
     avec des valeurs comme `IOME2401804A`, `INTE0600904A`, `INTE1802929A`, `IOME2407754A`.
- **Observé** : warning React de clé non unique émis à chaque rendu de la fiche. La pile pointe
  `LigneCarte (ContextePanel.tsx:570)` sous `CommuneAccProvider`. Les valeurs ressemblent à des
  identifiants SITADEL/permis. Non bloquant : les 10 cartes s'affichent, mais React prévient qu'il
  peut dédupliquer/omettre des enfants (risque de ligne manquante silencieuse). 0 HTTP en erreur.
- **Capture** : captures/03-commune/001_Bras_Panon.png (contenu OK ; le warning est en console, voir
  logs du sweep — reproductible sur ~17/24 communes).
- **Cause probable** : un `.map()` quelque part dans l'arbre de la fiche commune (le plus proche
  `LigneCarte` est la carte « Permis et rythme », `ContextePanel.tsx:565-591`) utilise une clé non
  unique construite sur un identifiant qui se répète (deux permis/établissements au même numéro).
  Les `.map()` du fichier (`ContextePanel.tsx:342,368,505,744,760` + acquéreurs `:172`) sont a priori
  sûrs (clés dédupliquées) ; la source exacte est probablement un sous-composant alimenté par
  `permis_bloc`/données SITADEL. À confirmer : ajouter un index à la clé du map concerné.

### A-03-2 — Fiche commune LENTE sur les grandes communes (cache `commune_contexte_cache` vide)
- **Gravité** : gênant (perçu comme bloquant sur les plus grandes : ~45 s d'attente)
- **Où** : endpoint `GET /communes/<nom>/contexte` ; fiche des communes volumineuses
  (Le Tampon ~46 s, Saint-Benoît ~45 s, Saint-Leu ~33 s, Saint-Paul ~24 s, Saint-Denis ~13–20 s).
- **Reproduire** :
  1. Ouvrir la fiche de Le Tampon (ou Saint-Benoît / Saint-Leu / Saint-Paul).
  2. Le panneau affiche « FICHE COMMUNE / <nom> » + un spinner (points animés `labuse-dot`) ;
     le bandeau et les cartes n'apparaissent qu'après 24–46 s.
  3. Mesure API directe (à chaud, requête répétée) : `/contexte` répond en 17–35 s pour ces communes
     (Le Tampon 31 s, Saint-Benoît 35 s, Saint-Leu 26 s, Saint-Paul 18 s, Saint-Denis 13 s).
- **Observé** : table de cache `commune_contexte_cache` **VIDE** en recette (`SELECT count(*) = 0`).
  Le job nocturne `fiche-commune-cache` (qui doit remplir ce cache, ~20 s/commune, pour une ouverture
  < 500 ms) n'a jamais tourné sur cette base. Du coup l'endpoint tombe dans la branche `else` →
  `_compute_commune_contexte` en DIRECT à CHAQUE appel → 20–45 s. Les données finissent par
  s'afficher correctement (10 cartes, bandeau plausible, aucun faux zéro), mais l'attente est très
  longue. Un spinner est présent (retour honnête), ce qui évite le classement « bloquant ».
- **Capture** : captures/03-commune/001_Saint-Paul_midload_etat.png (panneau pendant l'attente :
  nom + spinner, pas encore de contenu) · 001_Le_Tampon_slow.png · 002_Saint_Beno_t_slow.png ·
  003_Saint_Leu_slow.png · 004_Saint_Paul_slow.png (contenu complet après chargement).
- **Cause probable** : `src/labuse/api/app.py:2296-2328` (`commune_contexte`) — sans entrée de cache,
  fallback `_compute_commune_contexte` (`app.py:2460`) lent ; cache alimenté par le job
  `fiche-commune-cache` (`src/labuse/jobs_impl.py:145`, « ~20 s/commune … ouverture < 500 ms »).
  En environnement servi/prod le cache doit être pré-amorcé (lancer le job une fois) ; en recette il
  ne l'est pas. Côté produit : envisager aussi une génération à la demande en arrière-plan +
  squelette de contenu plutôt qu'un simple spinner sur 45 s.

### A-03-3 — Fiche commune : texte PPR tronqué dans la carte Risques
- **Gravité** : cosmétique
- **Où** : carte « Risques et contraintes » de la fiche commune, sous-titre PPR. ~17/24 communes.
- **Reproduire** :
  1. Ouvrir une fiche commune (ex. Bras-Panon, Saint-Denis, Petite-Île…).
  2. Repérer le span « PPR · mouvement de terrain · CatNat » (classe `truncate`).
- **Observé** : le span a `scrollWidth > clientWidth` (débordement détecté par `debordements()`).
  Classe `block truncate text-[11px] text-txt-mut` → ellipsis volontaire. La liste des aléas est
  coupée à la largeur de la colonne (420 px). Cosmétique : l'info détaillée est dans le corps de la
  carte dépliée ; le sous-titre n'est qu'un résumé. Aucune valeur chiffrée n'est perdue.
- **Capture** : captures/03-commune/001_Bras_Panon.png (sous-titre PPR tronqué visible).
- **Cause probable** : classe `truncate` (Tailwind `overflow:hidden; text-overflow:ellipsis`) sur le
  sous-titre d'aléas de la carte Risques dans `ContextePanel.tsx` (bloc `risques`, ~l.731+).
  Comportement voulu (résumé repliable) — à laisser tel quel ou autoriser le retour à la ligne.

### A-04-1 — Blocs fonciers : table `parcel_blocs` vide → l'outil ne montre jamais rien
- **Gravité** : gênant
- **Où** : outil « Blocs fonciers » (`#m=blocs-fonciers`), bouton « Voir les parcelles ».
- **Reproduire** :
  1. Ouvrir l'outil Blocs fonciers (rail Outils → « Blocs fonciers », ou `#m=blocs-fonciers`).
  2. Cliquer « Voir les parcelles » (filtres par défaut, n_min=2).
- **Observé** : la requête `GET /modules/blocs?limit=200&n_min=2` répond **200** mais
  `{"total":0,"n":0,"items":[]}`. L'UI affiche correctement l'état vide (data-blocs-vide :
  « Aucun bloc de deux parcelles ou plus sur l’île. ») — pas de plantage, pas de NaN. Mais QUELLE
  QUE SOIT la recherche, l'outil renvoie 0 : il ne peut jamais démontrer sa valeur dans cet
  environnement. Vérifié en base : `SELECT count(*) FROM parcel_blocs;` = **0** (la table existe
  mais n'a pas été alimentée).
- **Capture** : captures/04-outils/ (blocs-vide).
- **Cause probable** : la table `parcel_blocs` est bâtie par le batch `labuse blocs-build`
  (cf. `src/labuse/api/modules.py:1169-1211`, « table parcel_blocs (bâtie par le batch … ») — ce
  batch n'a pas été exécuté dans l'environnement de recette. Donc **défaut d'ENVIRONNEMENT (donnée
  non ingérée), pas un bug de code applicatif.** Le code front/back se comporte correctement
  (empty-state honnête). À corriger côté données : lancer `labuse blocs-build` avant la démo/prod,
  sinon l'outil reste muet. Les 23 autres outils ne dépendent pas de cette table.

### A-05-1 — Dossier expert : « Capacité (logements) = 1 » affiche un booléen, pas un nombre de logements
- **Gravité** : gênant
- **Où** : Dossier expert PDF, §10 « Potentiel » (table « Ce qui est constructible ») — `GET /dossier/{idu}.pdf`. Reproduit sur `97422000BX1106` (R+6) et `97411000AT0427` (R+3).
- **Reproduire** :
  1. Rail « Docs » → carte « Dossier » → parcelle `97422000BX1106` → « Générer le dossier ».
  2. Ouvrir le PDF, aller à la section 10 « Potentiel » (ligne « Capacité (logements) »).
  3. `curl -L -o /tmp/d.pdf "http://127.0.0.1:8798/dossier/97422000BX1106.pdf" && pdftotext -layout /tmp/d.pdf - | grep "Capacité (logements)"`.
- **Observé** : la ligne affiche « Capacité (logements) : **1** · estimé ». La valeur « 1 » n'est pas un vrai décompte de logements : c'est le drapeau booléen `potentiel_transformation.capacite_estimee = true` rendu en « 1 ». La vraie capacité de cette parcelle R+6 (module faisabilité) est ~8 à 10 logements au sol. Un promoteur lit « 1 logement » → sous-estimation grossière dans un document client. L'écran (fiche React §Potentiel) ne rend PAS ce chiffre : il traite `capacite_estimee` comme un simple badge « Estimé » → le PDF DIVERGE de la fiche sur ce point.
- **Capture** : captures/05-exports/003_apres_Dossier.png (+ extrait texte ci-dessus).
- **Cause probable** : `src/labuse/exports/robinet_fiche.py:454-457` — l'extracteur `_c_capacite` retourne `p.get("capacite_estimee")` (un `bool`) au lieu d'un nombre de logements ; le rendu `src/labuse/exports/blocs/potentiel.py:115-118` imprime `str(cap)` dans une ligne libellée « Capacité (logements) », ce qui transforme `True` en « 1 ». Il faudrait soit retirer la ligne, soit servir un vrai décompte (ex. fourchette logements de la faisabilité), soit la renommer en drapeau oui/non.

### A-05-2 — Bilan / Étude de faisabilité : non générable en visiteur anonyme (401) et message d'erreur imprécis
- **Gravité** : gênant
- **Où** : carte « Bilan » → écran d'hypothèses → bouton « Générer le bilan ». Endpoint `POST /bilan/{idu}/generer`. (`components/fiche/BilanEcran.tsx:164-174`)
- **Reproduire** :
  1. Rail « Docs » → carte « Bilan » → parcelle `97422000BX1106` → « Générer le bilan » (ouvre l'écran d'hypothèses).
  2. Dans l'écran d'hypothèses, cliquer « Générer le bilan ».
  3. Observer la requête réseau et le message affiché.
- **Observé** : `POST /bilan/97422000BX1106/generer` → **HTTP 401** `{"detail":"Session requise — connectez-vous à votre compte."}`. Le bouton est présent et activable pour un visiteur anonyme, mais la génération échoue. Côté UI, l'erreur est bien catchée et affichée, MAIS avec le texte générique « **Génération impossible.** » au lieu de la raison réelle (« Session requise — connectez-vous à votre compte »). Le `detail` du 401 est une chaîne, pas un objet `{message}`, donc `d?.message` est `undefined` et le fallback générique s'affiche → l'utilisateur ne sait pas qu'il doit se connecter. (Le calcul du bilan À L'ÉCRAN fonctionne ; seule la génération PDF persistée est gated.) Les 6 autres documents se génèrent sans compte ; seul le Bilan l'exige.
- **Capture** : captures/05-exports/001_bilan_erreur_session.png · 001_bilan_hypotheses_ouvert.png
- **Cause probable** : gate serveur `POST /bilan/{idu}/generer` qui exige une session (le PDF persiste un `doc_id` en base → besoin d'un compte). Message imprécis dû à `components/fiche/BilanEcran.tsx:170-173` : `const d = (e as {detail?:{message?:string}})?.detail; setErreurGen(d?.message ?? 'Génération impossible.')` — ne gère pas le cas où `detail` est une `string`. Deux pistes : (a) faire remonter le message serveur quand `detail` est une chaîne ; (b) décider si le Bilan doit être accessible anonyme (comme les 6 autres docs) ou afficher d'emblée « réservé aux comptes ».

### A-06-1 — Copilote : IDU inexistant (bien formé) → message « incident serveur » au lieu de « parcelle introuvable »
- **Gravité** : gênant
- **Où** : Copilote (rail « Copilote ») → `POST /api/copilote-v2/ask`. Reproduit aussi en curl.
- **Reproduire** :
  1. Rail « Copilote ».
  2. Taper « Quelle est la surface de la parcelle 00000000ZZ9999 ? » (ou « Que puis-je construire sur la parcelle 97411000ZZ9999 ? ») et Envoyer.
  3. Observer la réponse.
- **Observé** : réponse `{"erreur":true}` (variant `err`) : « **Je n'ai pas su traiter cette demande — l'incident est enregistré côté serveur. Reformulez-la autrement, ou réessayez dans un instant.** » (HTTP 200). Le message suggère un incident transitoire et invite à « réessayer », alors que la cause est simplement un IDU qui n'existe pas (réessayer ne changera rien). Avec un IDU VALIDE (`97422000BX1106`) la même question répond proprement « Surface : 629 m² ». Pas d'hallucination (c'est le point positif), mais le message induit l'utilisateur en erreur et masque la vraie raison.
- **Capture** : captures/06-copilote/011_10_ambigu.png
- **Cause probable** : l'exception remonte jusqu'à la **garde générale** `src/labuse/api/copilote_v2.py:128-133` (`except Exception: … "erreur": True`). Or les outils ont pourtant un refus PROPRE pour ce cas : `copilote_v2/outils.py:344` (`fiche_parcelle` → `refus=f"parcelle {idu} introuvable"`) et `:629` (`destination_zone` → `refus="parcelle introuvable"`). Une étape AMONT (routeur/résolution d'IDU, probablement `_q_v2_fiche` ou la résolution de parcelle dans le router pour les intents « construire/surface ») lève une exception pour un IDU absent au lieu de retourner falsy → le refus propre n'est jamais atteint. Piste : garantir que la résolution d'IDU renvoie « introuvable » (refus `neutral`, sans « réessayez ») plutôt que de laisser remonter l'exception.

### A-06-2 — Copilote : décline les règles PLU / calcul de capacité que LABUSE détient (routage vers « web » au lieu des données)
- **Gravité** : gênant
- **Où** : Copilote → `POST /api/copilote-v2/ask`, intents EXPLIQUER/général.
- **Reproduire** :
  1. Rail « Copilote ».
  2. Taper « Quelle hauteur maximale en zone Ua à Saint-Denis ? » puis Envoyer.
  3. (Variante) « Combien de logements sur un terrain de 2000 m² en zone U2 ? ».
- **Observé** : les deux renvoient un badge « **RÉPONSE GÉNÉRALE — HORS DONNÉES LABUSE** » puis « Je n'ai pas trouvé de source fiable sur le web pour cette question — je ne réponds pas de mémoire. Reformulez-la, ou posez-la sur les données LABUSE. » (`refus:"web_rien_trouve"`, `general:true`). Or Saint-Denis est une commune CALIBRÉE (règles de hauteur par zone U présentes dans les données PLU LABUSE) ; la question est posée et routée comme une « notion » web, pas vers les données LABUSE. Même reformulée sur une parcelle (`…hauteur maximale autorisée sur la parcelle 97411000AT0427 ?`), l'outil `fiche_parcelle` répond « la hauteur maximale autorisée n'est pas disponible dans les données cadastrales … consultez le PLU » — le tool n'expose pas la règle de hauteur calibrée. Comportement **honnête** (aucune invention) mais couverture faible sur une question foncière cœur : un utilisateur attend que le copilote foncier sache répondre.
- **Capture** : captures/06-copilote/004_03_plu.png · 007_06_calcul.png
- **Cause probable** : routage (router EXPLIQUER → recherche web) + l'outil `fiche_parcelle` (`copilote_v2/outils.py:339-352`) ne remonte que `surface/zone/verdict` et non le bloc `reglement_plu.zones[].regles` (hauteur/emprise calibrées, pourtant présent dans `_q_v2_fiche`). Deux pistes : (a) un intent/outil « règle PLU par zone » qui lit les règles calibrées ; (b) enrichir `fiche_parcelle` pour exposer la hauteur quand `reglement_plu` la porte. Non bloquant (pas de faux chiffre servi).

### A-06-3 — Copilote : question PPR directe répondue par le zonage PLU (esquive, sans oui/non PPR)
- **Gravité** : cosmétique
- **Où** : Copilote → `POST /api/copilote-v2/ask`.
- **Reproduire** :
  1. Rail « Copilote ».
  2. Taper « La parcelle 97422000BX1106 est-elle en zone rouge PPR ? » et Envoyer.
- **Observé** : réponse « **Zone PLU : Zone Ua (famille U)** » (`tool:fiche_parcelle`, `champ_id:zone_plu_famille`). La parcelle n'est effectivement PAS en zone rouge PPR, donc **aucune affirmation fausse** (pas d'hallucination), mais le copilote ne répond pas à la question posée (PPR) — il bascule sur le zonage PLU. L'utilisateur n'obtient pas le « non » attendu ni l'état PPR.
- **Capture** : (cas sondé en API ; comportement identique à la ligne 10 du parcours) captures/06-copilote/011_10_ambigu.png
- **Cause probable** : mapping d'intent/champ : la question « zone rouge PPR » matche le champ zonage (`zone_plu_famille`) plutôt qu'un champ risque/PPR. Piste : router les questions « PPR / zone rouge / aléa » vers le champ risques de la fiche (qui existe) et formuler un oui/non explicite.

### A-07-1 — `/login` (auth désactivée) atterrit sur la doc Swagger sur l'origine API
- **Gravité** : cosmétique (artefact dev — non reproductible en prod)
- **Où** : `/login` sur l'origine API `http://127.0.0.1:8798/login` ; cible finale `http://127.0.0.1:8798/docs`.
- **Reproduire** :
  1. Ouvrir `http://127.0.0.1:8798/login`.
  2. Observer : 302 → `/` → la page servie est **« LABUSE — radar foncier - Swagger UI »**.
- **Observé** : `login_page()` (app.py:580) fait `RedirectResponse("/")` quand l'auth est désactivée ; sur l'origine API, `/` sert la doc OpenAPI/Swagger (le front vit sur le dev-server Vite `/socle/`, pas à `/` de l'API). Un client qui tape `/login` tombe donc sur la doc technique, pas sur l'app. **En prod (Caddy sert le front à `/`) le comportement est correct** → artefact d'environnement dev. S'ajoute le fait que `/login`, `/reset`, `/invitation`, `/onboarding`, `/logout`, `/cgv`, `/flash` ne sont **pas dans le proxy Vite** (`vite.config`) → 404 sur `:5998`.
- **Capture** : captures/07-compte/003_login_api.png
- **Cause probable** : `src/labuse/api/app.py:580` `RedirectResponse("/")` + `/` monté sur Swagger côté API en dev ; `frontend/vite.config.ts` `apiPaths` n'inclut pas les routes du parcours compte. Non bloquant : purement dev (prod même-origine).

### A-07-2 — Mot de passe oublié : message « un lien vient d'être envoyé » alors que le mail est en dry-run
- **Gravité** : gênant (message trompeur dans cet environnement)
- **Où** : `/reset` → POST `/reset-demande` (page de confirmation). `src/labuse/api/onboarding.py:571-607`.
- **Reproduire** :
  1. Ouvrir `http://127.0.0.1:8798/reset`.
  2. Saisir `integral-7@labuse.test` → « Recevoir le lien ».
  3. Lire la confirmation.
- **Observé** : la page affiche **« Vérifiez votre boîte mail — un lien valable 1 heure vient d'être envoyé »** et « un e-mail de réinitialisation vient de lui être envoyé ». Or l'envoi est en **dry-run** (`.eml` écrit, 0 réseau — ligne mail_queue 48 : `etat=a_rejouer`, erreur « dry-run (local, LABUSE_MAIL_REEL absent) — aucun appel Brevo »). Le message affirme un envoi qui n'a pas eu lieu. **Cause racine** : le choix du message dépend de `brevo.etat_configuration().api` (présence de `BREVO_API_KEY`), **pas** de l'autorisation d'envoi réel (`envoi_reel_autorise` = `mail_reel`). Comme `.env` **contient** `BREVO_API_KEY` mais **pas** `LABUSE_MAIL_REEL`, la branche « Brevo configuré → on annonce l'envoi » est prise alors que rien ne part. Il existe bien une branche honnête « L'envoi automatique par e-mail n'est pas actif sur cet environnement », mais elle n'est atteinte que si `BREVO_API_KEY` est absente. En prod (Brevo + mail_reel) le message serait exact ; mais dès que la clé Brevo est présente sans envoi réel (dev/staging), le message ment.
- **Capture** : captures/07-compte/005_reset_demande_confirmee.png (+ 006 e-mail inconnu : message identique = anti-énumération OK)
- **Cause probable** : `src/labuse/api/onboarding.py:593-606` — condition `if etat_configuration().get("api")` devrait aussi tester l'autorisation d'envoi réel (ex. `mail.envoi_reel_autorise(settings)`), pas seulement la présence de la clé API.

### A-07-3 — Stripe Checkout : saisie carte non automatisable (accordéon/iframe) + nom marchand « LASTONE »
- **Gravité** : cosmétique
- **Où** : `checkout.stripe.com` (mode test) après « Payer 349 € ».
- **Reproduire** :
  1. Parcours invitation payante → MDP + CGV → bascule → « Payer 349 € ».
  2. Observer le checkout.
- **Observé** : (1) **Fonctionnel confirmé** — `cs_test_…`, bandeau **« Environnement de test »**, produit « S'abonner à LABUSE Intégral · 349,00 €/mois », e-mail pré-rempli. (2) Le bloc carte est un **accordéon** (radio « Carte » replié) et les champs numéro/exp/CVC vivent dans des iframes Stripe cross-origin montées seulement après sélection du radio → **la saisie de la carte test 4242 n'a pas pu être pilotée par Playwright** (limitation Stripe hosted checkout, pas un bug LABUSE). La complétion du paiement test et l'activation seraient à vérifier manuellement ou par simulation de webhook. (3) **Détail cosmétique** : le nom marchand affiché est **« LASTONE »** (nom du compte Stripe de test) au lieu de « LABUSE » — en-tête + « Payez en toute sécurité sur LASTONE ». À corriger côté réglages du compte Stripe prod avant lancement.
- **Capture** : captures/07-compte/024_paiement_4_checkout.png (bandeau TEST + 349€), 071_paiement_carte_accordeon_ouvert.png (accordéon carte replié, nom « LASTONE »)
- **Cause probable** : nom marchand = réglage du compte Stripe (Settings → Public business name), pas le code. Saisie carte = sandbox iframe Stripe (hors périmètre LABUSE).

### A-07-4 — Pas d'inscription self-service ; accès client aux pages compte impossible sur le front dev
- **Gravité** : gênant (dev) / informatif
- **Où** : parcours d'entrée client (invitation) vs front `:5998`.
- **Reproduire** :
  1. Depuis l'app `http://localhost:5998/socle/`, chercher un lien « S'inscrire / Créer un compte ».
  2. Tenter `http://localhost:5998/socle/../reset` ou `/login`.
- **Observé** : il n'existe **aucune porte d'inscription libre** dans l'app (par conception : entrée sur invitation signée émise par l'admin — modèle B2B assumé). De plus, sur le front dev `:5998`, les pages du parcours (`/login`, `/reset`, `/invitation`, `/cgv`, `/flash`, `/logout`) renvoient **404** (non proxiées). Le menu compte lie bien `/logout` et `/reset` (`Header.tsx:709,724`) mais ces hrefs, cliqués depuis `:5998`, tombent sur 404 en dev (ils marchent en prod même-origine). En local l'auth est désactivée (`/moi` → `mode:"local"`), donc l'action « Changer mon mot de passe » est masquée (`Header.tsx:706` `mode==='compte'`) — attendu.
- **Capture** : captures/07-compte/001_app_menu_compte.png (menu « Session locale (dev) », pas d'action MDP)
- **Cause probable** : `frontend/vite.config.ts` `apiPaths` n'inclut pas les routes serveur du parcours compte → elles ne sont pas proxiées vers `:8798` en dev. Décision produit (invitation-only) = non-anomalie ; le trou de proxy dev = à documenter (sinon un testeur croit les pages cassées).

### A-07-5 — Résiliation : aucun mail de résiliation émis automatiquement sur la transition d'état
- **Gravité** : gênant
- **Où** : `suspendre_compte` (`src/labuse/comptes.py:712`) appelé par webhook `customer.subscription.deleted` (`src/labuse/facturation.py:493`) ou endpoint admin `/suspendre`.
- **Reproduire** :
  1. Lire `suspendre_compte` : UPDATE statut='suspendu' + DELETE sessions + audit. **Aucun `envoyer_mail`.**
  2. Lire le webhook `customer.subscription.deleted` → appelle `suspendre_compte` sans mail.
  3. Comparer avec `invoice.payment_failed` qui, lui, enfile `relance_carte` (template 9).
- **Observé** : à la résiliation (abonnement Stripe supprimé) **aucun e-mail `resiliation` (template 16) n'est envoyé au client** ; le compte passe silencieusement `suspendu`. Le template `resiliation` existe mais n'est enfilé **nulle part en code** (grep `key="resiliation"` = 0 ; seul `flash_pret` est auto-enfilé) — il n'est envoyable qu'à la main via l'admin (`POST /admin/licences/{id}/mail key=resiliation`, vérifié : produit un `.eml` « Votre abonnement LABUSE prend fin le … »). Même constat pour `suspension`/`retablissement`/`onboarding1`/`essai` : tous **manuels**, aucun déclenché par la transition. Le client peut donc être résilié/suspendu sans confirmation écrite automatique.
- **Capture** : captures/07-compte/ (mails `resiliation`/`suspension` produits manuellement : fichiers `.eml` 20261016-150657-404412 / -419195, lisibles)
- **Cause probable** : `src/labuse/comptes.py:712-717` `suspendre_compte` et `facturation.py:493-495` (`customer.subscription.deleted`) n'enfilent pas le mail du cycle de vie. À câbler (best-effort, comme `relance_carte`) si une confirmation automatique est attendue — ou assumé « envoi manuel admin » et documenté.

---

## Famille 8 — Courrier / Veille / CRM

### A-08-1 — Le deep-link `#idu=…&m=courriers` n'injecte pas la parcelle comme destinataire
- **Gravité** : gênant
- **Où** : outil Courriers, hash `#idu=97416000EW0446&m=courriers` (et AT0427, BD0967)
- **Reproduire** :
  1. Ouvrir `http://localhost:5998/socle/#idu=97416000EW0446&m=courriers`.
  2. La fiche EW0446 s'ouvre à droite ET l'outil Courriers s'ouvre à gauche.
  3. Regarder l'étape 1 « Destinataires ».
- **Observé** : l'outil affiche « 0 destinataire — un courrier par parcelle » ; la parcelle de la fiche active n'est PAS pré-remplie. Il faut re-saisir l'IDU dans la barre. Le pré-remplissage n'existe QUE via la tuile fiche « Préparer les courriers » (one-shot `courrierPrefill`), pas via le deep-link combiné. Le brief attendait un destinataire « pré-rempli depuis les données parcelle ».
- **Capture** : captures/08-courrier-veille-crm/001_A_courriers_societe_EW0446.png
- **Cause probable** : `frontend/src/components/outils/ModulePanel.tsx:1372-1382` — le seed des destinataires lit `courrierPrefillPiste` / `courrierPrefillIdus` / `courrierPrefill`, jamais `selectedIdu` (la parcelle du hash). Le deep-link `m=courriers` ouvre l'outil mais ne pose aucun prefill. Comportement possiblement voulu (l'outil est multi-parcelles), mais l'URL combinée laisse croire au pré-remplissage.

### A-08-2 — `.eml` interne de demande : « ×1 » cassé dans l'en-tête Subject
- **Gravité** : cosmétique
- **Où** : `outputs/mails_dryrun/…__LABUSE<contact_at_labuse.immo>.eml` (notification interne de demande de courrier)
- **Reproduire** :
  1. Composer un courrier (parcelle EW0446), aller à l'étape Envoi.
  2. Cliquer « Demander l'envoi à LABUSE ».
  3. Ouvrir le `.eml` le plus récent dans `outputs/mails_dryrun/`.
- **Observé** : la ligne `Subject:` contient `Saint-Pierre =?utf-8?q?=C3=971=29?=` — le « ×1 » (× + chiffre) s'encode mal (« =C3=971 » → « ×1 » devient illisible). N'affecte QUE l'en-tête du mail interne LABUSE→LABUSE (le corps est correct) ; aucun impact client, aucun mail réel.
- **Capture** : (fichier `.eml` lisible, cf. `outputs/mails_dryrun/20261016-151903-404495__LABUSE<contact_at_labuse.immo>.eml`)
- **Cause probable** : composition du sujet de la notification interne (src/labuse/courrier.py, construction du Subject avec « ×N ») — le « × » (U+00D7) passé dans un en-tête encodé casse le groupage. Purement cosmétique/interne.

### A-08-3 — `#surveillance=secteurs` retombe silencieusement sur « parcelles »
- **Gravité** : gênant
- **Où** : deep-link `#surveillance=secteurs`
- **Reproduire** :
  1. Ouvrir `http://localhost:5998/socle/#surveillance=secteurs` (chargement frais).
  2. Observer l'écran.
- **Observé** : affiche « VEILLE · LE FONCIER / Vos parcelles suivies » — exactement le même écran que `#surveillance=parcelles`. Aucun volet « secteurs » distinct, aucun message expliquant la redirection. Le brief cite 3 volets (parcelles/secteurs/criteres) ; seuls 2 écrans réels existent (LE FONCIER, LES ANNONCES). `criteres` ouvre bien « LES ANNONCES ».
- **Capture** : captures/08-courrier-veille-crm/002_B_fresh_surveillance_secteurs.png
- **Cause probable** : `frontend/src/store/useApp.ts:866-867` — « 'secteurs' a été RETIRÉ (l'outil secteur n'existe plus) : toute demande 'secteurs' retombe sur 'parcelles' » ; `App.tsx:379` mappe tout ≠ parcelles/criteres → 'secteurs' → retombe parcelles. Décision produit assumée, mais le deep-link reste exposé et trompeur (pas de 404/message). Retirer le deep-link `secteurs` ou le rediriger explicitement vers « criteres ».

### A-08-4 — Donnée de stress-test `[GB-TEST] AAAA…` (5000 car.) visible dans le CRM client
- **Gravité** : cosmétique
- **Où** : CRM, colonne « Repérée », carte parcelle 97404000BA0005 (`pipeline_entries` id 93)
- **Reproduire** :
  1. Ouvrir le CRM (rail de gauche).
  2. Première carte de la colonne « Repérée » (BA0005).
- **Observé** : la note de la carte contient `[GB-TEST] AAAAA…` (5000 caractères de « A ») — reliquat de test. Le layout n'est PAS cassé : la note est confinée (max-h ~4,5 rem + overflow-y-auto + overflow-wrap:anywhere), aucun débordement horizontal de page (docScrollW = viewport). Reste une donnée polluante affichée côté client. (Une 2ᵉ note test existe : id 91 « [GB-TEST] prospect audit — a supprimer ».)
- **Capture** : captures/08-courrier-veille-crm/001_C_crm_note_overflow.png, 001_C_crm_pipeline.png
- **Cause probable** : données de test laissées en base (`pipeline_entries.notes` sur id 91/93), pas un bug code. À purger avant mise en prod (nettoyage de jeu de données), ou borner la longueur de note à la saisie.

### A-09-1 — Circuit : `verrous.phrases` vide dans le résumé (donnée morte, non affichée)
- **Gravité** : cosmétique
- **Où** : Admin → Données (Circuit) ; payload `GET /admin/circuit` champ `verrous.phrases`
- **Reproduire** :
  1. `curl -s http://127.0.0.1:8798/admin/circuit | python3 -c "import sys,json;print(json.load(sys.stdin)['verrous'])"`
  2. Observer `phrases: {'G5': '', 'G8': ''}` alors que `casses: ['G5','G8']`.
- **Observé** : le dict `verrous.phrases` renvoie des chaînes vides pour G5 et G8. L'UI n'en
  souffre PAS : la ligne « À faire » lit `a_faire.lignes[].phrase` qui, elle, contient le texte
  complet et correct (« Le dernier passage de "labuse circuit verrous" a cassé sur G5… » /
  « G8 est un avertissement de fraîcheur de veille… »). C'est donc un champ de résumé non
  renseigné et non surfacé — pas un écran vide muet côté client.
- **Capture** : captures/09-admin/003_section_donnees.png
- **Cause probable** : dans `src/labuse/api/dashboard.py` (constructeur du bloc `verrous` de
  `/admin/circuit`, autour de L2585+), `phrases` n'est pas rempli depuis VERROUS.md / la sortie
  de `labuse circuit verrous` ; la phrase utile est recalculée à part pour `a_faire`. À nettoyer
  (remplir ou retirer le champ mort) — sans impact fonctionnel.

### A-09-2 — Produit : note de test `[GB-TEST] AAAA…` (5000 « A ») — donnée polluante
- **Gravité** : cosmétique
- **Où** : Admin → Produit (et déjà présent via le CRM, cf. A-08 de la Famille 8)
- **Reproduire** :
  1. Ouvrir l'admin, section « Produit ».
  2. `debordements()` remonte 1 élément : `div.max-w-[360px] truncate` = « « AAAAA… ».
- **Observé** : un reliquat de test (`[GB-TEST]` + 5000 caractères « A ») s'affiche. Le layout
  n'est PAS cassé : le conteneur est `max-w-[360px] truncate` → texte tronqué, aucun débordement
  horizontal de page. C'est de la **donnée de test laissée en base**, pas un bug code admin.
  Même origine que l'anomalie Famille 8 (notes `pipeline_entries`/retours de test).
- **Capture** : captures/09-admin/004_produit_detail.png, 006_section_produit.png
- **Cause probable** : jeu de données de recette pollué (`[GB-TEST]`). À purger avant la mise en
  prod (nettoyage des données de test), ou borner la longueur à la saisie. Aucune correction de
  code applicatif requise.
