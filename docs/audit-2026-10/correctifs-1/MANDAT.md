# MANDAT-CORRECTIFS-1 — Flash, dashboard admin, compte, données personnelles

Rédigé le 09/10/2026. Modèle : Opus. Branche `fix/correctifs-1` depuis `origin/main`, worktree `~/Desktop/labuse-correctifs`, ports 8720/5920.

## Règles

- **Étape 0** : `pwd`, branche, arbre propre. Sinon STOP, rien n'est écrit.
- **Jamais de merge.** Un commit par lot, jamais avant la recette du lot. Vic merge.
- **DA existante**, aucun nouveau composant, aucun redesign. Pas d'audit collatéral, pas d'extraction de composants partagés, pas de « liste des autres endroits au même problème » : on corrige ce qui est listé ici.
- **Captures avant/après** pour chaque point visuel, dans `docs/audit-2026-10/correctifs-1/captures/`.
- **Ne rien lancer en prod.** Aucun `deploy.sh` (il écraserait le crontab posé le 07/10). Rien n'est réingéré. Stéphanie teste en ce moment.
- Un point impossible ou douteux → STOP sur ce point, note dans le rapport, on continue le lot suivant.

Rapport final : `docs/audit-2026-10/correctifs-1/RAPPORT.md` — une ligne par point : fait / STOP + motif.

---

## Lot A — page /flash (le site doit pouvoir y brancher son bouton)

A1. **Mobile** : `/flash`, `/flash/retour` et « Lien expiré » ne doivent plus charger `/ordinateur.js` (paramètre sur `coffre_ui.page`). Le blocage « disponible sur ordinateur » ne concerne que l'app. Vérifier qu'aucune autre page publique ne le porte. Recette en émulation iPhone : formulaire visible, rien ne déborde, on atteint « Payer ».
A2. **`/flash/`** (barre finale) → redirection 301/308 vers `/flash`.
A3. **CGV avant paiement** : case obligatoire au-dessus de « Payer 79 € » : « J'agis pour les besoins de mon activité professionnelle et j'accepte les conditions générales de vente ». Version des CGV + heure d'acceptation enregistrées dans `flash_commandes`. Retirer la renonciation de l'art. 4 bis ; dire dans les CGV que pour le Flash l'acceptation se fait avant le paiement. Impossible de payer sans cocher.
A4. **E-mail « Flash prêt »** : envoyé à la fin de `_flash_fulfill` (modèle Brevo `flash_pret`, lien de téléchargement). Recette : achat test, mail reçu, lien fonctionnel.
A5. **Textes** : appliquer le texte proposé (joint à ce mandat par Vic), avec ces corrections : **« 79 € » partout, jamais « HT », jamais de mention de TVA à ajouter** (franchise en base, art. 293 B : écrire « TVA non applicable, art. 293 B du CGI » une seule fois en pied). « Vendu par LABUSE (CLOSING CREST) » reste tel quel. Remplacer « Radar foncier » → LABUSE, « votre contact LABUSE » → contact@labuse.immo.
A6. **Saisie** : on garde les deux champs (adresse / référence cadastrale) tels qu'ils sont. Corriger seulement la recherche par adresse : complétion BAN pendant la frappe (même appel que l'omnibox de la carte, `api-adresse.data.gouv.fr`) ; si le point BAN tombe hors parcelle, prendre la parcelle la plus proche dans un rayon court et la faire valider ; si rien, le dire et proposer la référence cadastrale. Le champ référence accepte l'IDU 14 caractères et « Saint-Paul CW 658 ». Changer l'exemple affiché (l'actuel échoue). Recette : les 7 adresses du test de Vic aboutissent.
A7. **Écran de validation** : vue aérienne IGN (couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, déjà utilisée par la carte) avec le contour cadastral de la parcelle, assombrissement autour, trait vert. Ligne « CW 0658 — Saint-Paul · surface · Vue aérienne IGN ».
A8. **Surface** : l'app affiche 27 156 m² pour 97415000CW0658, le cadastre dit 25 633 m². Dire d'où vient la surface affichée (géométrie ? contenance DGFiP ?) sur la fiche, le Dossier et /flash. Si c'est la géométrie : servir la contenance cadastrale partout où elle existe, géométrie en repli étiquetée. STOP et rapport si ça touche un moteur partagé — Vic tranche.
A9. **Stripe live** : ne rien basculer. Lister dans le rapport ce qui manque pour `docs/BASCULE_LIVE_CHECKLIST.md` (clé `sk_live`, Price Flash 79 €, webhook live) et comment vérifier (`cs_live_` dans l'URL). Vic fait la bascule et l'achat test remboursé lui-même.

## Lot B — dashboard admin

B1. **Comptes** : onglet « À toucher » = texte blanc sur vert, illisible → contenu inversé en sombre (règle DA). Premier onglet affiché = **Actifs**, et il doit contenir Stéphanie (son essai 7 jours est un compte actif, pas seulement un « essai »). Supprimer la répétition « Comptes — que dois-je faire… » / « Comptes 1 licence active » : un seul titre.
B2. **IA — séparation** : deux blocs distincts, jamais un total mélangé : (a) **interne** = agents de vérification des sources + tout ce que lance le dashboard ; (b) **clients** = Recherche NL + Copilote /ask + missions. Coût du mois, projection et coût moyen calculés **par bloc**. Retirer la ligne « SURFACE IA — le mauve est réservé à cette section… ».
B3. **IA — crédit Anthropic restant** : CC vérifie si l'Admin API Anthropic (`/v1/organizations/cost_report`, clé admin) expose le solde ou seulement la dépense. Si le solde n'est pas exposé : champ admin « crédit acheté le JJ/MM » et affichage « reste ≈ crédit saisi − conso tracée depuis cette date », clairement étiqueté estimation. Plus de tiret « non exposé par l'API » sans alternative.
B4. **Données — coût des agents** : 39 agents = 4,86 €, soit ~0,12 €/agent pour vérifier une version de source. CC répond dans le rapport : quel modèle, combien de tokens par agent, que fait-il exactement (lit-il des pages entières ?). Puis refaire l'agent de vérification au moins cher : modèle le plus petit du registre `ai_models.py`, lecture ciblée (en-têtes HTTP / page de version seulement), plafond de tokens par agent. Mesure avant/après sur 10 sources.
B5. **Données — plafond 5 €** : retirer la limite.
B6. **Données — « Injecter » ne fait rien** : reproduire, corriger, et afficher un retour visible (en cours / fait / échec) après le clic.
B7. **Données — envoi d'agent** : après « Envoyer un agent », le bouton de cette source passe grisé « Agent envoyé » jusqu'au retour au journal (plus de double clic possible). Le bouton doit exister sur **toutes** les sources, dans le même état et au même endroit ; si une source ne peut pas être vérifiée par agent, le bouton est grisé avec le motif, jamais absent.
B8. **Produit** : messages longs qui débordent sur la colonne Statut → tronquer avec « … » et texte complet au survol. Retirer : « UNE file : signalements fiche + annonce… », « RETOURS — FICHE + ANNONCE + « SIGNALER » GLOBAL · 3 » (doublon des filtres), « Ouvertures d'outil (événement léger, par licence)… ».
B9. **Sources (côté client)** : vérifier si la sonde quotidienne tourne depuis le crontab du 07/10 (`sonde-sources` dans `/etc/cron.d/labuse`, trace dans `ingestion_runs`). Si oui, rien à changer. Si non, adoucir la phrase « vérifiées automatiquement chaque jour » de `SourcesPage.tsx` et le dire dans le rapport.

## Lot C — app

C1. **3D** : la vue 3D ne se charge parfois pas. CC instrumente : erreur console/réseau loggée côté front quand la 3D échoue (WebGL, tuile terrain, ortho IGN, timeout), message visible « 3D indisponible : motif » à la place d'un écran vide. Rapport : causes observées sur 10 ouvertures.
C2. **Barres de recherche** : le placeholder de la barre des permis est coupé (« …n° de permis ou parce »). Raccourcir le placeholder de **chaque** barre de recherche de l'app pour qu'il tienne en entier à la largeur actuelle (capture de chacune).
C3. **Mon compte** : retirer « ton-email@test.com » et « Intégral depuis le 24 juillet 2026 ». Vérifier que « Changer mon mot de passe » envoie bien le mail de réinitialisation (recette réelle sur un compte de test, mail reçu, lien qui marche).
C4. **Textes** : Veille « ou un retour » → « ou un retrait » (le serveur produit : nouvelle annonce, baisse, retrait, mise en vente d'une parcelle suivie) · catalogue Docs « 17 lignes » → « 19 lignes » · CRM « (+ Pipeline) » → « (+ CRM) ».
C5. **Successions** : si l'âge exact des dirigeants est affiché (outil + API `getSuccessions`), le remplacer par une tranche (« plus de 70 ans »). Partout, écran et PDF.
C6. **Street View** : petite fenêtre « Afficher la vue Google ? » avant de créer l'iframe ; `referrerPolicy="no-referrer"`.
C7. **Polices** : héberger les polices sur le serveur (`@fontsource`), plus aucun appel à Google Fonts (front + pages serveur `coffre_ui.py`).

## Lot D — pages légales et données personnelles

D1. `/mentions-legales` et `/confidentialite` de l'app → 301 vers `https://labuse.immo/mentions-legales/` et `https://labuse.immo/confidentialite/`. CGV : éditeur « Victor Lagane, entrepreneur individuel », 3 chemin de la Citerne, La Montagne, 97417 Saint-Denis, SIRET 987 641 917 00016, contact@labuse.immo (art. 5 et 8) ; art. 8 renvoie vers labuse.immo/confidentialite/.
D2. Courriers propriétaires : ajouter en pied, après `_PIED_STOP` : « D'où viennent ces informations et quels sont vos droits : labuse.immo/confidentialite/#courriers ».
D3. Dirigeants : retirer la nationalité de `owner_enrichment.payload` ; vider `pm_dirigeants.raw` quand l'entreprise n'est pas diffusible. Migration avec backfill + test.
D4. Sauvegardes : la doc annonce 7 quotidiennes et 4 hebdo, la prod tourne avec `BACKUP_ROTATION_N=4`. Aligner la doc sur le code, pas l'inverse.

## Lot E — fraîcheur (à CODER maintenant, à JOUER après le test de Stéphanie)

Rien de ce lot ne s'exécute en prod dans ce mandat. Code + tests seulement, recette en local.

E1. **DVF** : `refresh_dvf` écrit des colonnes inexistantes et ne cible pas `dvf_mutations`. Corriger table et colonnes, recharger aussi `dvf_mutations`, années calculées (2026 incluse), date de livraison enregistrée seulement après succès, test du rechargement (pas seulement de la détection).
E2. **BAN** : lire `/var/log/labuse/ban_refresh.log` (lecture seule sur le VPS), trouver pourquoi le 05/10 a échoué (téléchargement ou garde-fou 80 %), corriger le code. Relance par Vic plus tard.
E3. **Millésimes** : SOURCES-FIX-2 a créé un magasin unique `data_sources.source_millesime` via le composer. Dire si `persist_millesime()` est l'ancien chemin ou le vivant, et brancher le vivant à la fin de chaque ingestion (DVF, DPE, BAN, BODACC, Sitadel). Pas deux magasins.
E4. **PLU / Géorisques** : **aucune ingestion automatique** (doctrine : la sentinelle détecte, Vic clique). Vérifier que gpu_plu et georisques sont bien sous veille hebdo de la sentinelle avec le bouton « Envoyer un agent » / injection (B7). La date d'approbation du PLU se lit de la base (Sudocuh) et non de `config/plu_millesimes.yaml`, si la base la porte.
E5. **Registre des jobs** : ajouter `ban`, `dvf`, `abuse`, `sessions` au registre `jobs.py` avec les rythmes voulus (permis et BODACC chaque jour, DPE/DVF/PLU/Géorisques chaque semaine, adresses chaque mois, sonde chaque jour), pour qu'un futur `labuse jobs crontab --tz reunion` les porte. Ne pas poser le crontab.

---

## Hors mandat (noté, plus tard)

Purges par table + copilote-purge + rotation journald/Caddy · registre d'exclusion (opposition → indicateurs, Successions, filtres d'âge) · bascule Stripe live (geste de Vic).
