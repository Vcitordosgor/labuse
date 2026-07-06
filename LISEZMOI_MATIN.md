# ☀️ LISEZ-MOI DU MATIN — LA NUIT DES 21 MODULES + IA

**Branche `feat/outils-ia` (part de `feat/socle-v1`, non mergée — tu merges). Toutes les suites
auto-QA sont vertes (sortie jointe `outputs/qa_nuit_complete.log`). Rien n'est à moitié : ce qui
est listé ✓ est construit, testé en conditions réelles (clics souris, compteurs vs SQL), capturé.**

## Lancer (2 commandes)
```
pkill -f "labuse api" ; cd ~/Desktop/labuse
LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@127.0.0.1:5432/labuse" .venv/bin/labuse api
# → http://127.0.0.1:8000/
```

## Le parcours guidé (15 minutes)
1. **Rail → Outils** : le tiroir liste les **15 modules** (violet). Ouvre **M01 Division** :
   698 candidats, clique le 1er → fiche avec bloc violet (lot détachable ~m², rayon libre) ;
   le lot est dessiné en pointillés sur la carte.
2. **M02 Patrimoine** : tape « CBO » → CBO TERRITORIA → 1 833 parcelles, SDP totale 1,2 Mm².
3. **M08 Remonter le temps** : le split 1950 ↔ aujourd'hui — glisse la poignée sur Saint-Gilles.
   (Aussi : bouton « 1950 » dans toute fiche.)
4. **Rail → IA** : tape « les chaudes avec vue mer de plus de 1000 m² » → les chips s'appliquent,
   la carte filtre. Puis « raconte-moi une blague » → refus propre. Dans une fiche : bouton IA →
   Synthèse / Pourquoi ce score ? (stub local étiqueté — mets `ANTHROPIC_API_KEY` dans .env pour
   basculer sur Anthropic, AUCUN autre changement requis).
5. **La cloche** 🔔 : 8+ événements **étiquetés DÉMO** (bascules du run q_v2_demo) + 5 matchs 🎯.
   Marque-en un lu. « Digest → » = l'email hebdo. En bas : nomme la recherche courante = une veille.
6. **CRM** : la carte AC 0253 porte son badge violet « N nouveaux » quand un événement la concerne.
7. **M15 Simulateur PLU** : AUc → U = 313 bascules potentielles (SIMULATION À BLANC, méthode
   par analogie affichée). **M16 Assemblage** : clique 2-3 parcelles voisines sur la carte →
   « Analyser l'assiette » (contiguïté, SDP cumulée, propriétaires). **M18 Baromètre** : ⬇ PDF.
8. **Fiche → ↗** : lien apporteur public (ouvre-le : filigrané, horodaté, compteur). **API** :
   `curl "http://127.0.0.1:8000/api/v1/parcels?key=demo-labuse-partner-key&statut=chaude&limit=5"`
   — doc : `/api/v1/docs`.

## État par module
| ✓ | Module | Note |
|---|---|---|
| ✓ | M01 Division | **Spec officielle absente du repo** → C1-C5 définis et documentés (modules.py) ; lot = approximation MIC (conservatrice, consignée) ; table module_division ; 698 candidats |
| ✓ | M02 Scan patrimoine | autocomplétion PM DGFiP, total SDP, bandeau BODACC |
| ✓ | M03 Radar permis | fenêtre ancrée sur la FIN DES DONNÉES (Sitadel s'arrête au 31/01/2023 — affiché) ; 91 % géocodés sur 24 mois, non-géocodés listés |
| ✓ | M04 Promesses mortes | reco consignée : codes `etat` source non documentés (affichés bruts) ; PC sans DAACT + non bâti au run |
| ✓ | M05 Vélocité admin | **dépôt→décision IMPOSSIBLE** (la source ne porte qu'une date + DAACT) → délai permis→achèvement + volumes + taux, île entière, tri + CSV |
| ✓ | M06 Mode bailleur | 731 promues en QPV (500 affichées), lecture LLS (TVA 2,1 %, TFPB) |
| ✓ | M07 Foncier fantôme | 545+ PM introuvables au RNE, verrou + levier par cas ; indivision/succession = données absentes de la base (consigné) |
| ✓ | M08 Remonter le temps | split 2 cartes synchronisées + accès fiche |
| ✓ | M09 Courrier propriétaire | 3 contextes, source = pipeline ou saisie, export .md par lot, rappel SPF/CERFA |
| ✓ | M10 Due diligence | refs souples (IDU ou AC0254), rapport + PDF par parcelle, introuvables signalés |
| ✓ | IA | stub local déterministe FLAGGÉ (pas de clé dans .env) ; bascule Anthropic = poser la clé ; coût journalisé (ia_log) ; schéma = garde-fou |
| ✓ | M11-M14 | **DÉMO ÉTIQUETÉE** : le diff q_v2→q_v2_demo (8 deltas synthétiques marqués demo) fait vivre cloche/badges/digest dès ce matin. **Bascule réelle** : au prochain run de scoring, `labuse detect-events q_v2 <nouveau_run>` (cronable) — zéro code à changer |
| ✓ | M15 Simulateur PLU | à blanc, analogie documentée, 0,7 s (optimisé depuis 2 min 33) ; vrai recalcul règlementaire = prochain cycle |
| ✓ | M16 Assemblage | clic-carte, contiguïté par graphe, bandeau règlement d'ensemble |
| ✓ | M17 ZAN | OCS GE par commune (recouvrements possibles — lecture indicative), quotas SAR/SCOT en attente |
| ✓ | M18 Baromètre | île entière, 8 trimestres, PDF palette impression |
| ✓ | M19-M21 | **DÉMO ÉTIQUETÉE** : 2 profils matching + clé API `demo-labuse-partner-key` — fonctionnels, prêts à s'activer avec de vrais comptes |

## Bloqué / consigné (aucun arrêt)
- **SPEC MODULE 01 introuvable** dans le repo → construite sur mes C1-C5 (documentés) ; si ta spec
  diffère, c'est un réglage de requête, pas une refonte.
- **Clé IA absente** → stub (prévu par le mandat). — **SMTP digest** : contenu généré, envoi à brancher.
- Détails et backlog : `NOTES_SOCLE_V1.md` (section nuit) + `frontend/DERIVATIONS.md`.

## Vérifier toi-même
```
cd frontend
for s in qa qa_filtres_reels qa_modules qa_ia qa_events qa_moteurs qa_partners; do
  BASE=http://127.0.0.1:8000/socle/ node qa/$s.mjs || break
done
```
Captures : `docs/design/captures/modules/` (une par module) + `qa/`.
