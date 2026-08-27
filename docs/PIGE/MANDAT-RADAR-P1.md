# MANDAT — RADAR P1 : VISION IA + INTAKE ADMIN
Régime AUTONOME. Commits par lot (V1→V4). RÈGLES COMMUNES. Findings RD-101→.
Suite du mandat RADAR V0 (docs/PIGE/MANDAT-RADAR-V0.md) dont P0 (socle) et P2 (rattachement) sont livrés et mergés. **Relis les doctrines du §2 de ce mandat avant de commencer : elles gouvernent P1 exactement comme P0.**

## LE VERROU À OUVRIR
Constat du rapport P0/P2 : `ai/core.complete` est TEXTE SEUL. L'extraction d'une capture d'annonce en JSON exige d'étendre le cœur IA à l'image. C'est le préalable de tout le Radar : sans lui, Vic saisit chaque annonce à la main et le rituel de 15 min/jour n'existe pas.

## V1 — LE CŒUR IA APPREND À VOIR
Étends `labuse/ai/core.py` pour accepter des images, sans casser l'existant.
- L'API Messages accepte des blocs image en base64 avec leur media_type. `complete()` doit pouvoir recevoir, en plus de son contexte texte, une ou plusieurs images.
- **Ne casse rien** : la signature actuelle reste valide, tous les appels existants (Copilote, synthèses) continuent de fonctionner à l'identique. Les tests existants du Copilote doivent rester verts sans modification.
- Le modèle utilisé pour la vision est déclaré dans la config, comme les autres (MODEL_FACTUAL / MODEL_REASONING) — pas de nom de modèle en dur.
- Le coût est logué dans le ledger `ia_budget` comme le reste, avec son `kind` propre (« vision_pige » ou équivalent) pour être distinguable au dashboard.
- Gestion des échecs : image illisible, format non supporté, taille excessive, réponse non-JSON. Chaque cas donne un message honnête et une reprise possible — jamais un champ inventé pour combler.
- Tests avec une image réelle (fabrique-en une de test, ne dépends pas d'un fichier externe).

## V2 — L'EXTRACTION D'UNE ANNONCE
Une fonction qui prend une capture + le lien du portail et rend le JSON strict attendu :
`{prix, type, pieces, surface_hab, surface_terrain, dpe_classe, dpe_conso, dpe_ges, commune, particulier_pro, date_publication}`
- **Anti-invention absolue** : tout champ non lisible sur la capture est `null`. Le modèle ne complète pas, ne déduit pas, n'estime pas. Le prompt doit l'exiger explicitement et la sortie être validée contre le schéma.
- Chaque champ porte sa **confiance**. Sous un seuil, il est marqué à vérifier (il sera surligné à l'écran, cf. V3).
- Le portail est déduit du lien via `portails.py` (le seul endroit où vivent les noms de portails) ; un lien d'un portail inconnu est accepté mais signalé.
- **Contrôle commune** : hors des 24 communes → rejet à l'intake avec motif écrit, rien n'entre en base.
- **Dédoublonnage** à l'entrée, selon la règle du mandat V0 §3 : même commune ∧ prix ±2 % ∧ (surface_hab ±5 % ∨ surface_terrain ±5 %) → même `bien_id`, comparaison des prix (baisse éventuelle), fusion proposée à la validation. Une URL déjà connue → proposer la mise à jour du prix, pas une création.
- Après extraction, appelle le rattachement de P2 (`rattachement.rattacher()`) — la cascade existe déjà, ne la réécris pas.

## V3 — LA PAGE RADAR DU DASHBOARD ADMIN
Page entière du dashboard admin (route admin réservée, DA du dashboard v3), **pensée mobile** : Vic saisit depuis son téléphone, upload depuis la galerie. Quatre zones, dans cet ordre :

1. **Saisie du jour** — dropzone multi-captures, un champ lien par capture. Retour immédiat sur les doublons d'URL et les communes hors périmètre.
2. **File d'extraction** — chaque capture donne une fiche pré-remplie ; les champs sous seuil de confiance sont **surlignés en mauve** (couleur réservée à l'IA, conforme DA) ; Vic corrige, complète, puis **Valider** en un clic. Rien n'entre en base validée avant ce clic. La fusion proposée par le dédoublonnage se confirme ou se refuse ici.
3. **File de re-vérification, à DEUX niveaux** (décision Vic — pas de plafond bas) :
   - **(a) LÉGER, en volume** : une ligne par annonce, le lien sortant, un bouton [Toujours en ligne]. L'écran doit permettre d'en enchaîner beaucoup — pense navigation clavier, pas de rechargement complet entre deux.
   - **(b) ATTENTIF** sur celles qui ont bougé : [Prix modifié → champ] [Retirée].
   - **File priorisée** : les plus anciennes non confirmées d'abord, puis celles proches du seuil de vente longue (90 j), puis celles suivies par un client.
4. **Arbre de check quotidien** — la checklist du rituel : captures du jour saisies · file d'extraction vidée · re-vérif du jour traitée · signalements clients en attente · compteurs (nouveautés, en vente longue, baisses du jour). Cible affichée : **≤ 15 min/jour**. L'alerte `pige.intake_vide_48h` se déclenche si aucune saisie depuis 48 h — rappel doux, jamais culpabilisant.

## V4 — RECETTE RÉELLE
Déroule le parcours complet avec de VRAIES captures d'annonces réunionnaises (fabrique-les toi-même en composant des images de test réalistes : tu ne visites AUCUN portail — la doctrine vaut pour toi aussi). Prouve : extraction → confiance → correction → validation → rattachement → statut `active`.
Cas à couvrir : capture nette · capture partielle (champs absents → null, pas d'invention) · doublon d'URL · doublon inter-portails (fusion) · commune hors périmètre (rejet motivé) · baisse de prix détectée à la re-saisie · lien de portail inconnu.

## FIN
Critères : cœur IA étendu au vision sans régression sur les appels texte existants (tests Copilote verts sans modification) · extraction JSON stricte, aucun champ inventé, confiances portées · dédoublonnage et contrôle commune opérationnels · page admin Radar complète et utilisable sur mobile · re-vérification enchaînable en volume · coût vision au ledger ia_budget · **le test anti-requêtes-portails de P0 reste vert** · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [RADAR-TEST] purgés.
Captures de la page admin (390 et 1440) au rapport, avec leur nombre annoncé. Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/radar-p1). Tu ne merges pas.
