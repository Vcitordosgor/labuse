# MANDAT — HYGIÈNE TECHNIQUE : FIABILISER LE DÉPLOIEMENT
Régime AUTONOME. Commits par lot (H1→H2). RÈGLES COMMUNES. Findings HY-001→.
Mandat court et ciblé. Deux dettes constatées le 27/08 sur le VPS, qui menacent le déploiement lui-même. Tu ne touches à RIEN d'autre : pas de refactor, pas d'amélioration opportuniste. Ce mandat doit être petit, lisible et sûr.
Les deux autres dettes connues (golden à régénérer sur q_v11_m137, ON-002 script inline CSP au login) sont HORS PÉRIMÈTRE — ne les traite pas, elles ont leur mandat plus tard.

## H1 — FIGER LA VERSION DU CLIENT ANTHROPIC
Constat du 27/08 : le venv du VPS portait `anthropic==1.1.0`, incompatible (refuse le paramètre `temperature`) alors que le code exige la lignée 0.116.0. Résultat : le Copilote tombait en mode dégradé (« service d'analyse indisponible ») SANS erreur visible. Corrigé à la main sur le serveur — mais rien n'empêche le prochain deploy de réinstaller une version au hasard.
- Fige `anthropic==0.116.0` là où les dépendances sont déclarées (requirements et tout fichier de dépendances effectivement utilisé par deploy.sh — vérifie lequel est réellement lu, ne suppose pas).
- Vérifie qu'aucun autre fichier de dépendances ne contredit ce pin.
- **Garde-fou** : un test (ou une vérification au démarrage) qui échoue BRUYAMMENT si la version installée n'est pas celle attendue. Le mode dégradé silencieux est précisément ce qui a coûté une heure de debug — il ne doit plus jamais être silencieux.
- Dis au rapport quels autres paquets critiques ne sont PAS figés et pourraient poser le même problème. Ne les fige pas de ta propre initiative : liste-les, Vic tranchera.

## H2 — DEPLOY.SH DOIT DÉPLOYER MAIN
Constat du 27/08 : deploy.sh déploie la branche courante du dépôt VPS, resté sur `feat/vps-golive`. Un déploiement peut donc ne RIEN déployer (commit avant = commit après) en affichant un succès. Échec silencieux — le pire des deux.
- deploy.sh se place explicitement sur `main` à jour avant de déployer (fetch + checkout main + pull, ou l'équivalent robuste de ce script).
- Il **affiche en clair, avant et après, la branche et le commit déployés**. Vic doit lire dans la sortie ce qui est parti en ligne.
- S'il ne peut pas se mettre sur main (modifications locales sur le VPS, conflit, dépôt sale), il **s'arrête avec un message explicite** — il ne déploie jamais « au mieux » en silence.
- Le script reste idempotent et rejouable. Teste ce que tu peux localement (dry-run, shellcheck, simulation) et dis honnêtement ce qui n'est vérifiable que sur le VPS : Vic exécutera, la sortie fera preuve.

## FIN
Périmètre strictement tenu : aucun fichier hors dépendances et deploy.sh (+ le test de garde de H1). Si tu découvres autre chose, c'est un finding, pas une correction.
Critères : version figée dans le bon fichier · garde-fou bruyant en place et prouvé · deploy.sh se met sur main, annonce branche et commit, s'arrête proprement en cas d'obstacle · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree).
Compte-rendu « Demandé → traité » par lot + la sortie attendue du deploy pour que Vic sache quoi vérifier + commande de merge en dernier élément isolé (git merge --no-ff fix/hygiene-deploiement). Tu ne merges pas.
