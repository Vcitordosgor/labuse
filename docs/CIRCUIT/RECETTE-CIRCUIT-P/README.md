# Recette CIRCUIT-P — captures

Deux harnais Playwright (Chrome local `chromium_headless_shell-1217`, 1440×900).

## 1. Recette visuelle (jouée) — `qa/circuit_p_captures.mjs`

Rend la VRAIE page (`frontend/circuit-harness.html`) avec l'API **interceptée** par des fixtures
RÉELLES capturées de la base (`qa/fixtures/circuit_p/*.json`, run servi `q_v11_m137`, 68 réservoirs,
130 robinets, résumé = 9 lignes, 87 entrées de journal). **Aucune base touchée.**

Rejeu :
```
cd frontend && npm run dev            # vite sur [::1]:5175 (localhost)
BASE=http://localhost:5175 node qa/circuit_p_captures.mjs
```

Captures (`01`→`11`) :

| # | vue |
|---|-----|
| 01 | Résumé — « 9 choses à regarder », 4 repères, 3 groupes, verbes |
| 02 | clic « Décider » (quarantaine, 1 cible) → page de détail réservoir |
| 03 | clic « hors moteur » (cibles multiples) → circuit déplié sur le groupe |
| 04 | onglet Circuit — un bloc déplié, deux lignes par élément (jamais tronqué) |
| 05 | survol d'une ligne → famille → pompe → catégories **allumées** (vert) |
| 06 | page de détail de la pompe (ce qui attend, moteurs, horloges) |
| 07 | gestes de la pompe (Faire tourner inactif : rien en attente) |
| 08 | page de détail d'un élément (retour par bouton ou Échap) |
| 09 | Journal — tableau, « aujourd'hui · 77 » |
| 10 | Journal filtré par type de geste |
| 11 | bouton « Vérifier que tout coule » → bascule sur l'onglet Circuit |

Le parcours couvre exactement le lot 6.1 : Résumé → clic de chaque type de ligne → détail → retour →
circuit déplié → survol → journal filtré.

## 2. Recette des gestes RÉELS (rejouable) — `qa/circuit_p_recette.mjs`

Rejoue vanne → calcul → note → bascule → vérifier → **revenir** sur la NOUVELLE page, contre une app
**bootée** (API + frontend servi sous `/socle/`, base réelle), et vérifie que la base retrouve son
run de départ — comme la recette du lot 5 de CIRCUIT-1. Les gestes appellent les **mêmes endpoints**
déjà éprouvés par CIRCUIT-1 et couverts par les tests backend ; seule la coquille d'UI a changé
(les gestes vivent désormais dans les pages de détail). Non joué ici (nécessite une app bootée avec
`PYTHONPATH=src` — l'env conda importe un `labuse` installé sans les endpoints CIRCUIT-P) ; captures
`gestes-00`→`gestes-06` produites au rejeu :
```
PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uvicorn labuse.api.app:app --port 8010
BASE=http://127.0.0.1:8010 node qa/circuit_p_recette.mjs
```

---

## 3. Recette CIRCUIT-P2 (retours de recette du 06/09) — `qa/circuit_p2_captures.mjs`

Même harnais (`frontend/circuit-harness.html`, Chrome `chromium_headless_shell-1217`, 1440×900),
fixtures RÉELLES capturées de la base dans `qa/fixtures/circuit_p2/*.json` (run servi `q_v11_m137`,
82 réservoirs, 130 robinets, journal avec un passage groupé de filtres). **Aucune base touchée.**
Les tâches longues (contrôle, agents) sont simulées par une petite machine à états dans le stub
(progression → message ; agents **sans crédit** → message clair).

Rejeu :
```
cd frontend && npm run dev            # vite (base /socle/) — écoute sur localhost:5173
BASE=http://localhost:5173 node qa/circuit_p2_captures.mjs
```

Captures (`P2-01`→`P2-13`) :

| # | vue |
|---|-----|
| P2-01 | Résumé **sans enrobage** (3 onglets, 2 boutons, aucun bandeau « à jour ? ») |
| P2-02 | repère « N / 68 » → **page du compteur** (réservoirs par état + lignes non servies) |
| P2-03 | Circuit — interrupteur **ALLUMÉ** (seulement ce qui cloche) |
| P2-04 | Circuit — interrupteur **ÉTEINT** (tout ; même titre de colonne) |
| P2-05 | « Vérifier que tout coule » → **ligne de progression** sous les onglets |
| P2-06 | contrôle terminé → **message** + Résumé rafraîchi |
| P2-07 | « Envoyer les agents » **sans crédit** → message clair, rien lancé (jamais grisé) |
| P2-08 | page de détail d'un **réservoir** (« Envoyer un agent » actif) |
| P2-09 | page de détail d'un **robinet** (passe-plat neutre, hors moteur ambre) |
| P2-10 | page de détail de la **pompe** |
| P2-11 | **journal** — un passage groupé sur une ligne |
| P2-12 | journal — passage groupé **déplié** source par source (noms affichés, cliquables) |
| P2-13 | filtre de catégorie **« sonde » présent même vide** |

Le parcours couvre le lot 5.1 du mandat CIRCUIT-P2.
