# RAPPORT CIRCUIT-P7 — la page Données selon la maquette v10

Date : 24/09/2026 · Modèle : Opus · Branche `feat/circuit-p7` (depuis `main` `245db078`) ·
Worktree `~/Desktop/labuse-p7` · Ports recette : API **8345** · Vite **5545** · **PAS mergée**.
Un commit par lot : `82f6a428` (1) · `3bd16419` (2) · `b5b853cb` (3) · `ee984cb9` (4) ·
`14bde204` (5) · ce rapport + captures (6).

Recette faite sur la **vraie base** (`labuse`, env=local, auth désactivée) : un seul démarrage
d'API, un seul envoi d'agent réel (une source), aucune injection ni bascule.

---

## Ce que chaque lot a changé (résumé)

| Lot | Quoi |
|---|---|
| **1 — une action, un endroit** | En-tête = titre « Données » + 4 onglets, plus aucun bouton ni bandeau. Deux cartes en tête de Sources : « Sonde de nuit » (+ *Sonder maintenant* → `POST /admin/circuit/sonder`) et « Agents » (coût du ledger, plafond, prochain dimanche, menu de portée jamais / G8 / vitrine / une source). « Vérifier que tout coule » vit dans Circuit, résultat sous le bouton. |
| **2 — Sources lisible** | Tableau à colonnes fixes (nom jamais tronqué, sous-ligne producteur·famille·mode·⟳cadence). Tri problèmes d'abord, filtres à sélection unique qui FILTRENT, « Toutes » en dernier. Clic = fiche source (vraie page, ← Sources, Échap) : trois faits, « si cette version entre » (registre), « ce qu'elle alimente », « comment elle entre », historique, *Injecter / Envoyer un agent / Suspendre la veille*. |
| **3 — Circuit rangé** | Une seule recherche (réservoir/robinet/chiffre **ou** élément de l'app → ses sources) ; le bloc « Sens inverse » disparaît. Légende sur une ligne + interrupteur « ne montrer que ce qui cloche ». Le dessin ne change pas. |
| **4 — À faire = l'invariant** | La FUITE (robinet hors moteur) et l'ÉCART (circuit_ecarts) ont enfin leur ligne « Décider » (le bug). « jamais vérifiée » n'en fait pas (→ agents depuis Sources). Ordre rouge → ambre. Trois dates sous le titre. `total_a_faire()` = pastilles non vertes + actions = tuile Pilotage (`taches_a_effectuer`). |
| **5 — Journal** | « tous » en dernier à droite ; chevron ‹ / ▼ ; coût du ledger sur chaque passage d'agents ; cibles cliquables. |

---

## Trois preuves par geste (base réelle, 24/09)

| Geste | Endpoint | Ligne de journal (avec « qui ») | Écran |
|---|---|---|---|
| **Sonder maintenant** | `POST /admin/circuit/sonder?source_id=99` → `{lance:true}` ; tâche `sonde` terminée « 1 interrogée, 0 en panne, 1 nouvelle version vue » | `sonde · Annuaire de l'administration · par Vic · ok` | `07-filtre-sources.png` (carte Sonde « dernier passage 16:33 »), `05-fiche-source.png` (historique) |
| **Envoyer les agents (une source)** | dashboard `POST /admin/circuit/agents?source_id=148` → `{lance:true}` ; **agent LLM réel** `labuse agent source --ids 148` | `agent · Communes La Réunion · introuvable · 0,14 €` | `04-journal.png` |
| **Vérifier que tout coule** | `POST /admin/circuit/verifier` → `{lance:true}` ; tâche terminée « 1 fuite, 0 eau ancienne, 1 écart » | `controle · Vérifier que tout coule · par Vic · ok` | `03-circuit.png` (résultat sous le bouton) |
| **Filtre de Sources** | (front) | — | `07-filtre-sources.png` (chip « Nouvelle version » → 4 lignes exactes) |
| **Ouverture d'une fiche source** | `GET /admin/circuit/reservoir/99` | — | `05-fiche-source.png` |
| **Clic « Décider »** | (front → cible Circuit) | — | `06-clic-decider.png` |

**Coût de l'agent de recette : 0,1424 €** (`ia_log`, claude-sonnet-4-6, 41 373 in / 1 218 out ;
le web_search natif est facturé à part par Anthropic, hors ledger).

---

## Le test d'invariant (sur la vraie base)

`À faire` = **9** = tuile Pilotage `taches_a_effectuer` = **9** (à la capture ; 8 au premier
relevé, avant que la sonde de recette ne fasse passer « Annuaire » en nouvelle version — le compteur
suit l'état, l'égalité tient à chaque instant). L'**écart `exports_recette`**, qui n'avait AUCUNE
ligne avant P7, a désormais sa ligne « Décider » : le bug est fermé, prouvé sur la base réelle.

Test unitaire construit (`tests/test_circuit_p7_lot4.py`) : le cas qui casserait sans les lignes
fuite/écart, puis `compteur = nombre de lignes = pastilles non vertes + actions = total_a_faire`.

---

## Portes (toutes vertes)

| Porte | Résultat |
|---|---|
| `tsc -b` · `vite build` | verts |
| `vitest run` | **184 passed** (dont Sources tri+filtre, invariant, Journal « tous » à droite) |
| `pytest --co` (tout le dépôt) | **3384 collectés, 0 erreur d'import** |
| `pytest` circuit p7 (lot 1+4) · p4 (etats/afaire/dependance) | 41 passed |
| `pytest` endpoints circuit (tour complet, journal, agents) | 13 passed |
| `pytest` dashboard/pilotage · circuit1 lot5 · circuit1 lot6 | 30 + … passed |
| **22 verrous inchangés** | `circuit_verrous.py` NON touché. La vraie base porte **23** verrous (pré-existant P6), dont 1 cassé (V1c/G8 selon le dernier passage journalisé) — inchangé par P7. |

---

## Captures (`docs/CIRCUIT/captures/p7/`, deviceScaleFactor 2)

`01-a-faire.png` · `02-sources.png` · `03-circuit.png` · `04-journal.png` (les quatre onglets) ·
`05-fiche-source.png` · `06-clic-decider.png` · `07-filtre-sources.png`.

L'« avant » est la maquette v10 de Vic (`docs/CIRCUIT/maquette-donnees-v10.html`) et l'état P6 ; l'« après » est ci-dessus, cadré à 1280 px.

---

## Arbitrages (décisions prises en autonomie)

- **A.** « fuite » = robinet qui lit hors moteur (`hors_moteur > 0`) ; « écart » = `circuit_ecarts`
  ouvert. Deux sources de données distinctes → pas de double compte. Sur la base réelle, la seule
  fuite/écart vivante est `exports_recette` (un écart).
- **B.** Le dashboard « Envoyer les agents » reste la mécanique existante (sentinelle amont, hors
  périmètre « prompt des agents ») ; l'agent LLM réel (coût) est `labuse agent source`, joué une
  fois sur une source pour la recette.
- **C.** La tuile Pilotage `taches_a_effectuer` LIT le circuit (mêmes fonctions), jamais un recompte
  propre — l'invariant tient par construction. Le reste du Pilotage n'est pas touché.
- **D.** La tâche `verrous` (déclenchée depuis le détail de la pompe) garde sa ligne de progression
  sous les onglets ; c'est la seule qui y reste (sonde/agents/contrôle ont leur place).

**Reste à Vic** : merge ; injecter les nouvelles versions quand il veut (INSEE RP, DEAL CBS, FRR,
Annuaire) ; la carte Agents affiche un coût estimé de la vitrine (12,88 €) fondé sur le coût moyen
du dernier passage — à recalibrer si le passage du dimanche donne une autre moyenne.

---

## Suite (24/09, à la demande) — l'agent LLM sur le bouton « Envoyer les agents »

Le bouton « Envoyer les agents » lance désormais l'**agent LLM réel** (comme `labuse agent source
--tous`) : un appel Claude par réservoir (`agent_source.lancer_agent`), coût au ledger `ia_log`,
rapport + veille + journal. Portée par défaut = `--tous` (réservoirs affichés, hors flux en direct /
sans millésime / absents). La **sentinelle sans coût reste sur « Sonder maintenant »** (la sonde de
nuit), inchangée.

- **Plafond PAR PASSAGE** respecté : l'envoi est séquentiel, lit le coût cumulé du ledger après
  chaque agent, et s'**arrête** dès que le plafond `LABUSE_AGENT_PLAFOND_EUR` est atteint (message
  « plafond X € atteint, arrêt »). Plafond à 0 € → rien de lancé, message clair.
- **Confirmation avant l'envoi** (carte Agents) : coût **estimé** + **plafond** affichés, boutons
  *Annuler* / *Envoyer les agents* — capture `08-agents-confirmation.png` (« Agent LLM sur 92
  sources — coût estimé ≈ 15,64 € · Plafond 5,00 € par passage : l'envoi s'arrête dès qu'il est
  atteint »).
- **Preuve live** : `POST /admin/circuit/agents?portee=jamais` → tâche « 2 / 3 agents · 0,23 € » (le
  coût monte), terminée **« 3 agent(s) · 0,40 € — écrit au journal »** ; journal 3 lignes agent
  « par Vic » avec coût par source (0,15 / 0,09 / 0,16 €) ; un verdict « nouvelle ».

Portes : `tsc` + `vite build` verts · vitest **184** · pytest p7 (portée + plafond) + endpoints
agents (`test_circuit_p2_lot3`) verts. Commit dédié, **pas de merge**.

---

## Suite 2 (24/09) — portée des agents : sonde vs agents, cadence 15 jours

Partage clair du travail entre la sonde (gratuite) et les agents (LLM, coût) :

- **Sonde de nuit** : inchangée, sur les sources à **amont lisible** (api/page/entête/témoin) —
  77 aujourd'hui (89 dans la maquette). Chaque nuit, sans coût.
- **Agents — portée par défaut = « sans amont lisible »** (`circuit_garanties.sources_sans_amont` :
  ni sonde, ni rappel manuel, ni dépôt/flux/sans-millésime — les pages rendues en JS qu'un LLM doit
  lire). **5 aujourd'hui** (Communes IGN, DEAL CBS, FRR, INPN, ZFANG). *(La maquette disait « 3 » — les
  3 jamais-vérifiées ; l'ensemble structurel stable, rechecké chaque quinzaine, en compte 5.)*
- **Cron du dimanche : une semaine sur deux** (`jobs.semaine_agents` = semaines ISO paires ;
  `jobs_impl.agents_sources` saute les semaines impaires et ne vise plus QUE la portée sans-amont).
  Registre `agents-sources` → cadence « tous les 15 j (dim) ».
- **Bouton « Envoyer les agents »** garde ses portées manuelles avec confirmation + plafond : **sans
  amont** (défaut) · **verrou G8** · **les 92**, chacune avec son coût estimé.
- **Carte Agents** : « **tous les 15 jours (dimanche)**, lisent les **N** sources sans amont lisible
  — coût estimé ≈ X € … prochain passage dimanche JJ/MM » (capture `09-agents-portee-defaut.png`).

**Test sur la portée par défaut (base réelle)** : `POST /admin/circuit/agents` (sans paramètre) →
`n=5`, agent LLM sur les 5 sans-amont, terminé **« 5 agent(s) · 0,72 € — écrit au journal »**
(sous le plafond 5 €, `plafond_atteint=False`), 5 lignes journal « par Vic ». `semaine_agents` testé
(1 sur 2). tsc + vite build verts, vitest 184, pytest p7 (portée + quinzaine) verts. API + navigateur
arrêtés. Commit dédié **poussé**, pas de merge.
