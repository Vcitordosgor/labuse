# MANDAT RETOURS-8 — recette du 02/09 (soir)

**Branche : `fix/retours-8`**. Aucun sous-agent ne touche à git.
**Maquette** : `docs/audit-2026-09/maquette-retours-8.html` (Radar en onglets · Contacts liste + panneau · fiche parcelle en onglets).

**Clôture** : tsc, build, tests backend et front 100 % verts, puis commit sur la branche. Merge = Vic.

---

## R1 — Un seul vocabulaire pour l'état d'une source

Constat : quatre chiffres se contredisent — bandeau « rien à injecter », chip « 1 à rafraîchir », Pilotage « 0 nouvelle version / 3 manuelles en retard », page Sources client « 2 en retard » (DPE, DVF). Trois mécanismes distincts : l'agent (version amont constatée), la fraîcheur (heuristique « dernière publication + cadence habituelle du producteur »), les rappels manuels. Illisible.

1. **Une fonction unique** `etat_source(source)` rendant UN état parmi quatre, utilisée par le Catalogue, le bandeau, Pilotage, la page Sources client et la notification :
   - **À jour** — l'agent a vérifié, l'amont est identique ; ou source manuelle dans sa cadence.
   - **Nouvelle version disponible** — l'agent a vu plus récent → action Injecter.
   - **À rafraîchir** — source manuelle dont la cadence attendue est dépassée → action : Vic.
   - **Non surveillée** — pas d'agent ; l'heuristique de cadence devient une mention « le producteur publie habituellement tous les N jours ; dernière publication le … », **jamais un état rouge**.
2. **Règle de priorité** : quand l'agent surveille une source, **son constat gagne**. L'heuristique « publication ancienne » ne peut plus contredire un « amont identique » — DPE et DVF sont ce cas : le producteur est en retard sur sa cadence, LABUSE ne l'est pas. La ligne dit « à jour — le producteur n'a rien publié depuis le JJ/MM ».
3. Les compteurs (bandeau, chips, Pilotage, Sources client) sont **dérivés de la même liste** ; un test vérifie leur égalité.
4. Compte-rendu : pour DPE et DVF, l'état final et la phrase affichée.

## R2 — Page Sources client : deux mots, pas plus

Le client ne doit jamais croire que LABUSE est en retard. Sur sa page Sources, une source n'a que **deux états** :

- **À jour** — la dernière version publiée par le producteur est dans l'app. C'est le cas de DPE et DVF aujourd'hui. Le mot « retard » n'apparaît pas.
- **Pas à jour** — une version plus récente existe chez le producteur et n'est pas encore dans l'app. Rare et court grâce à l'agent : jamais rouge, dit seulement « mise à jour en cours ».

Chaque ligne affiche **la date de publication par le producteur** (« publié le 31/12/2025 ») et la cadence habituelle à titre d'information — jamais comme un jugement.

Le bloc accueil « 2 sources en retard — voir les données » disparaît. À la place : **« 65 sources · 436 3xx parcelles → voir les données »** (chiffres réels, lus).

Tout ce qui est « à rafraîchir », « nouvelle version disponible », rappel manuel reste **dans le dashboard admin** — jamais côté client. R1 fournit les quatre états admin ; R2 les projette en deux états client : « nouvelle version disponible » → pas à jour ; tout le reste → à jour.

## R3 — IA : plafond en euros, pas en appels

Vic a lu « 80 » comme 80 € par jour. C'était 80 questions (≈ 0,64 €).

1. Carte coût unitaire : **« 0,008 € / question »** seulement (retirer « pour 1 000 questions »).
2. **Plafond quotidien par compte exprimé en €**, défaut **2,00 € / jour**, éditable (0,50 · 1 · 2 · 5 ou libre). L'app convertit en appels avec le coût moyen réel des 30 derniers jours du compte (repli : coût moyen global) et affiche « ≈ 250 questions ». Le compteur du jour affiche « 0,12 € / 2,00 € » et, en petit, le nombre d'appels.
3. Les missions lourdes (Sonnet) comptent au **coût réel**, pas à l'appel — c'est l'intérêt du plafond en €.
4. `quota_du_compte` reste la fonction unique ; elle rend un budget € et un équivalent appels. Test : éditer 2 € → 5 € → la question suivante lit 5 €.
5. Le champ d'édition affiche l'unité (« 2,00 € ») avec un bouton Enregistrer.

## R4 — Données : Circuit ne charge pas, Horloge plante, bouton en double

1. **Horloge** : `jobs.py:181` `_champ_match` fait `int('7,37')` — le parseur cron ne comprend pas les listes. Supporter `,` (liste), `-` (plage), `/` (pas) et `*`. Tests sur `7,37`, `*/15`, `1-5`.
2. **Circuit** reste sur « Chargement… » : trouver la cause (endpoint `/admin/flux` en erreur ? prop manquante ?) et corriger. Test qui rend la page avec un flux réel.
3. Retirer le bouton « Ouvrir le Circuit → » en haut à droite — l'onglet suffit.

## R5 — Radar : la pige en onglets

Maquette section 1.

1. **Quatre chiffres en tête** : annonces en vie · à rattacher · à valider · re-vérifiées aujourd'hui / dues.
2. **Onglets** : Déposer · À valider (N) · À rattacher (N) · Re-vérifier (N dues) · Check du jour. L'onglet ouvert par défaut est le premier qui a du travail. Plus de blocs empilés, plus de descente.
3. **À rattacher** : chaque proposition porte une **confiance** et son **pourquoi** — « forte » (adresse BAN exacte ou position) → bouton **Rattacher** en un clic (humain, toujours) ; « faible » (surface seule ±10 %) → Instruire avec l'ortho. Aujourd'hui « 1 candidate » ne dit pas pourquoi ; quand la candidate vient d'une adresse exacte, le rattachement doit être à un clic.
4. Re-vérifier garde le regroupement par commune, dues d'abord.

## R6 — Contacts : liste + panneau, ajout en ligne

Maquette section 2. Retirer la barre de recherche et le bouton global en tête. Colonne gauche : les 24 communes, badge = nombre de contacts nommés. Panneau droit : la commune choisie — standard officiel, contacts nommés, et « + Ajouter » qui ouvre **une ligne vide dans cette commune** (nom · rôle · tél · email · note · Enregistrer). Après enregistrement la ligne reste à sa place dans la commune — plus de bloc séparé. Même composant réutilisé dans la fiche commune (carte Mairie).

## R7 — Fiche parcelle : onglets, trois boutons en tête, états cliqués

Maquette section 3.

1. **Maps · Cadastre · Pages jaunes** remontent en tête de fiche, à côté de l'IDU — trois petits boutons. Ils quittent la section Exports.
2. **Onglets** : Analyse · Autour · Actions. « Actions » = + CRM, + Projet, Courrier propriétaire, exports experts. Accessible sans défiler.
3. **État cliqué** : « + CRM » cliqué reste **plein vert** (encre sombre) et affiche la colonne choisie ; « + Projet » cliqué reste **plein ambre**. Un second clic rouvre le menu.

## R8 — Carte : retirer la légende « Bien rattaché / non localisé »

Retirer la pastille-légende « Bien rattaché : la carte vole à sa parcelle · bien non localisé : l'annonce s'ouvre sur le portail ». Le comportement reste, sans texte.

## R9 — Fiche commune : le bouton reparaît avec la commune

Quand une commune est sélectionnée, un bouton **« Fiche commune »** apparaît immédiatement à côté du sélecteur (là où était « Contexte ») et reste cliquable tant que la commune l'est. Vérifier que l'ouverture depuis ce bouton et depuis l'omnibox donne le même écran.

## R10 — Pilotage : « Backup : aucun »

Le job `backup-postgres` existe et Vic a un backup. Trouver pourquoi la tuile dit « aucun » — probablement `LABUSE_BACKUP_DIR` non renseigné en local, ou la tuile lit un chemin différent du job. Corriger pour que la tuile lise **le même endroit que le job**, affiche la date du dernier fichier et sa taille, et dise « répertoire non configuré » quand c'est le cas plutôt qu'« aucun ». Compte-rendu : la cause exacte.

## R11 — Copilote : fils de conversation et rétention

1. Comportement voulu, à vérifier : « Répondre » continue le fil ; la zone principale en haut ouvre un nouveau fil. Le dire en une ligne sous la zone principale.
2. **Mesurer** ce que pèsent les conversations stockées (nombre, taille en base, croissance par jour) — chiffre au compte-rendu.
3. **Rétention 7 jours** par défaut (réglage admin), purge par le job quotidien, et un bandeau discret sous les fils passés : « Vos conversations sont conservées 7 jours. »

## R12 — Copilote : sur une parcelle, répondre comme la fiche

Constat : « résume-moi cette parcelle » rend quatre lignes ; « quels sont les pièges » répond « pas de mesure dédiée » alors que l'outil Pièges existe. La fiche, elle, produit une synthèse IA riche.

Décision : **les deux voies ensemble** — répondre avec la vraie donnée, et tendre l'outil prérempli.

1. **Même matière que la fiche** : quand une question porte sur une parcelle (IDU résolu), le Copilote charge le **même payload que la synthèse IA de la fiche** (`collect_report_data`, run courant) et répond dessus. Pas un second chemin : la fonction de la fiche est réutilisée. Coût : un appel Sonnet avec le payload, dans le plafond €.
2. **Raccourcis vers les outils** : table intention → outil prérempli — pièges/risques → Pièges avec l'IDU ; faisabilité → Faisabilité ; taxe → Taxe d'aménagement ; « combien de parcelles possède X » → Scan patrimoine avec le nom ; prix du secteur → Étudier un bien avec l'adresse. La réponse se termine par le bouton « Ouvrir Pièges et risques → » prérempli. Dix intentions couvertes, listées au compte-rendu.
3. Le message « Je n'ai pas de mesure LABUSE dédiée » ne peut plus apparaître pour une intention couverte par un outil : soit on répond, soit on ouvre l'outil.
4. Recette : les deux questions de Vic (résumé de 97409000AB0570, pièges) — textes avant/après au compte-rendu.

## R13 — Signalements de test

La file contient des signalements de test (« E2E M9 — signalement via UI », « AAAA… », comptes « interne ») qui gonflent le compteur Pilotage à 19. Ajouter une action admin « Traiter tout ce qui vient d'un compte interne/test » et l'appliquer une fois ; le compteur doit retomber au nombre réel de signalements clients. Rien n'est supprimé, tout est marqué traité.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : R1.4 l'état final de DPE et DVF, côté admin ET client, avec la phrase affichée · R3 le test 2 € → 5 € · R4.2 la cause du Circuit vide · R10 la cause du « Backup : aucun » · R11.2 le poids réel des conversations · R12.4 les réponses avant/après.
