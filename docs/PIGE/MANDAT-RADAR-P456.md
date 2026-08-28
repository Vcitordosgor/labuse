# MANDAT — RADAR P4/P5/P6 : VEILLE, CYCLE DE VIE, MARCHÉ
Régime AUTONOME. Commits par lot (D1→D4). RÈGLES COMMUNES. Findings RD-401→.
Dernier mandat du Radar. P0 (socle), P2 (rattachement), P1 (vision + intake admin) et P3 (écran client) sont livrés et mergés. **Relis les doctrines du §2 de docs/PIGE/MANDAT-RADAR-V0.md avant de commencer.** Réutilise l'existant (pige/*, client.py, api.py, event_log, envoyer_mail, veille existante), ne le réécris pas.

## D1 — VEILLE RADAR ET LES DEUX DIGESTS (P4)
**Branche-toi sur le mécanisme de veille existant** — nouveau type « Radar », pas un second système parallèle.
Le client crée ses critères (ex. terrain > 2 000 m² à Saint-Benoît, particuliers uniquement) et coche les événements qui l'intéressent : nouvelle annonce · baisse de prix · retour sur le marché.

**DEUX envois distincts, en fin de journée heure Réunion** (décision Vic) :
- **(a) digest quotidien** — à tous les clients actifs : les nouveautés du jour.
- **(b) alerte veille** — à ceux dont les critères correspondent.
Un client concerné reçoit **les deux** : ils ne se remplacent pas. **Un mail ne part jamais vide** — s'il n'y a rien, il n'y a pas d'envoi.

Transport : la fonction unique `envoyer_mail`, **template Brevo ID 12**. Ses variables ont été listées au rapport P1 : `prenom`, `type_envoi` (digest|alerte), `date_jour`, `n_items`, `intro`, `items[]{type, commune, prix, surface, rattachement, url_fiche}`, `lien_preferences`. Si le template n'est pas encore monté côté Brevo au moment où tu testes, l'envoi doit échouer **proprement et bruyamment** (erreur visible au dashboard), jamais en silence — souviens-toi de RV-013, où des clés mal nommées auraient fait taire tous les mails sans que personne ne le voie.

Contenu : **faits + lien vers la fiche LABUSE**. Jamais de lien portail direct dans le mail (le clic passe par la fiche, c'est ce qui le rend mesurable), jamais de contenu d'annonce.
Cloche in-app (event_log) en miroir de chaque envoi. Événement `pige.digest_envoye`.

## D2 — CYCLE DE VIE AUTOMATISÉ (P5)
Jobs quotidiens, au fuseau Indian/Reunion :
- `en_vente_longue` : plus de 90 jours depuis la date de publication.
- `a_reverifier` : plus de 60 jours depuis la dernière confirmation.
Job à chaque ingestion DVF :
- `vendue` : même parcelle (**rattachement Sourcé uniquement** — un Estimé ne suffit pas) + mutation dans une fenêtre de 3 à 18 mois après la publication. Enregistre le délai et **l'écart entre prix affiché et prix acté** — c'est une donnée de marché précieuse, et elle n'est affichée que sur un rattachement Sourcé.
Job mensuel :
- `retiree_sans_vente` : retirée + aucune mutation DVF sous 12 mois.

**GARDE CRITIQUE** : `retiree_sans_vente` ne se déduit JAMAIS d'un lien mort. Un lien mort donne `retiree`, rien de plus. Seule l'absence de mutation DVF après 12 mois qualifie `retiree_sans_vente`. C'est la cible du service Courrier : une erreur ici enverrait une sollicitation à quelqu'un qui vient de vendre — exactement le faux positif que la doctrine interdit.

Rien ne se supprime, jamais. Chaque changement de statut émet `pige.statut_change` (et `pige.vendue_dvf` le cas échéant).
Historique de prix visible sur la fiche (mini-sparkline si le volume s'y prête).
Tous les jobs sont déclarés dans EXPLOITATION-CRON.md avec leur horaire, testés manuellement avant d'être posés au crontab.

## D3 — ONGLET « MARCHÉ » (P6)
Dans l'outil Radar, un onglet agrégé par commune (24 lignes + total île) :
annonces actives · nouvelles sur 30 j · retirées sur 30 j · vendues (DVF) sur 90 j · prix médian €/m² terrain et €/m² bâti · délai médian avant retrait ou vente · taux d'échec (retirées_sans_vente / clôturées) · part de particuliers.
Mini-heatmap de l'île.

**Honnêteté statistique gravée** : chaque chiffre affiche son **n**. Toute cellule dont n < 5 affiche « — (échantillon insuffisant) » et ne montre AUCUN chiffre. Pas de fausse précision, pas de médiane sur trois valeurs. C'est la clause boussole appliquée aux statistiques.
Au démarrage, la plupart des cellules seront vides : c'est normal et c'est honnête. L'écran doit être digne dans cet état — pas un tableau de tirets qui fait peur, mais une explication claire que le corpus se constitue.

## D4 — EXPLOITATION ET RECETTE
- Le Radar rejoint le **registre des sources** du dashboard admin, avec sa fraîcheur réelle = date de dernière collecte (jamais une date de run).
- Note d'exploitation pour Vic : le geste quotidien en dix lignes, dans docs/EXPLOITATION.md.
- Recette avec un jeu représentatif [RADAR-TEST] : biens de tous statuts, avec et sans baisse, rattachés Sourcé / Estimé / non rattachés, sur plusieurs communes et plusieurs dates — de quoi faire tourner les jobs et remplir quelques cellules du Marché. Purge vérifiée SQL en fin.
- Cas à prouver : bascule en vente longue · bascule à re-vérifier · rapprochement DVF avec écart de prix (Sourcé) · absence de rapprochement sur un Estimé · qualification mensuelle retiree_sans_vente · digest quotidien envoyé · alerte veille envoyée séparément · aucun mail quand il n'y a rien · cellule Marché avec n < 5 · onglet Marché quasi vide (état de démarrage).

## FIN
Critères : veille branchée sur le mécanisme existant · deux envois distincts, jamais de mail vide, échec d'envoi bruyant · aucun lien portail dans les mails · retiree_sans_vente jamais déduit d'un lien mort · écart de prix affiché seulement sur Sourcé · n affiché partout, « échantillon insuffisant » sous 5 · jobs déclarés et testés · Radar au registre des sources · Radar toujours hors scoring · le test anti-requêtes-portails de P0 reste vert · couleurs depuis la source unique · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [RADAR-TEST] purgés (vérifié SQL).
Captures 390 et 1440 de l'onglet Marché (état rempli ET état de démarrage) et du mail rendu, au rapport, avec leur nombre annoncé. Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/radar-p456). Tu ne merges pas.
