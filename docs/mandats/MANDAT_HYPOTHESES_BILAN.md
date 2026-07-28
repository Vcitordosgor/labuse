# MANDAT HYPOTHÈSES BILAN — une seule vérité pour `compute_bilan`

**Priorité n°1 du back** (décision Vic, 28/07/2026, revue M26-B). **Non exécuté** — ce
document est le mandat à tirer, pas un rapport.

**Exécuteur** : Claude Code (back, du jugement requis — mesures d'impact avant tout code).
**Clone dédié** : depuis `origin/main` post-merge M26-B. **Branche** : `fix/hypotheses-bilan`.
**Fable ne merge JAMAIS** — Vic merge en `--no-ff`.

**Pièces d'instruction** : `docs/mandats/M26B_CONSTAT_CHARGES.md` (constat intégral :
divergence prouvée à l'euro, chronologie, inventaire, estimation).

## 0 · Le problème, en une phrase

Une seule méthode (`compute_bilan`) mais deux jeux d'hypothèses : les défauts du code
portent l'audit O2 du 12/06 (`2c25746` — coûts 2300–2800 €/m² **de plancher**,
`coef_plancher_habitable` 1.15), le YAML versionné (`hypotheses_faisabilite` des 3 PLU)
porte encore les valeurs d'avant-audit (1800–2200, commentées « au m² habitable »).
Conséquence mesurée : charge supportable ×2,37 (médiane) selon le chemin, **11/20
verdicts de viabilité inversés** sur l'échantillon du run M26-B. Un même utilisateur
lit 216 k€ sur la fiche et 449 k€ dans la note Copilote pour la même parcelle.

## 1 · Réalignement du YAML versionné (traçabilité obligatoire)

- Porter `hypotheses_faisabilite` des **3 YAML** (`plu_saint_paul/denis/pierre.yaml`)
  aux valeurs auditées du 12/06 : `cout_construction_m2_bas: 2300`,
  `cout_construction_m2_haut: 2800`, et corriger les COMMENTAIRES d'unité (€/m² de
  **plancher**, pas « habitable » — le contresens d'unité fait partie du bug).
- Ajouter `coef_plancher_habitable: 1.15` explicitement au YAML (aujourd'hui implicite
  via le défaut du code — la config doit être complète pour être la source unique).
- **Traçabilité gravée dans le YAML** (commentaire) : décision Vic 28/07/2026 (revue
  M26-B), audit d'origine `2c25746` (12/06/2026), valeurs périmées introduites par
  `e3191f2` (10/06/2026), renvoi au constat M26-B.

## 2 · Source unique — plus jamais deux chemins

Basculer les 4 surfaces à défauts codés sur `Hypotheses.charger()` :

| Consommateur | Aujourd'hui | Cible |
|---|---|---|
| Fiche GET `/faisabilite/{idu}` (`api/modules.py:810`) | `Hypotheses()` | `charger()` |
| Calculette POST `/charge` (`api/modules.py:937`) | `Hypotheses()` + `bilan_params` | `charger()` + `bilan_params` |
| Explication `/explain` (même chemin) | `Hypotheses()` | `charger()` |
| Dossier banquier (`api/briques_pdf.py:243`) | `Hypotheses()` + `bilan_params_defaut()` | `charger()` + idem |
| Copilote `marche_dvf` (`copilote/moteurs.py:385`) | `charger()` | inchangé |
| Cœur `parcel_faisabilite` (`faisabilite/db.py:368`) | `charger()` + `bilan_params` secteur | inchangé |
| Tests | `Hypotheses()` fixtures | fixtures explicites autorisées |

- **Test-verrou** : aucun appel ne construit `Hypotheses()` en direct hors
  `engine.py` (le `charger()` lui-même) et fixtures de test — un test balaie `src/` et
  échoue bruyamment sur toute occurrence nouvelle (même mécanique que les verrous de
  wording du mandat dette-tests).
- Trancher et DOCUMENTER la préséance `charger()` × `bilan_params` (secteur/table) —
  aujourd'hui les deux coexistent sans règle écrite ; l'invariant
  calculette = dossier banquier (test `test_bilan_calculette_vs_dossier`) doit tenir.

## 3 · Mesure d'impact AVANT toute application — point d'arrêt

À produire et soumettre à Vic **avant** de basculer quoi que ce soit :

1. **score_e** (77 718 lignes, snapshot du 21/07) : consommateur ? Le pipeline batch
   « bilan-neuf-v2 » n'appelle pas `compute_bilan` (cf. constat §3) — vérifier sur
   pièces si ses propres hypothèses portent les mêmes valeurs périmées ; si oui,
   chiffrer le recalcul (durée, delta).
2. **`residuel_socle` et la chaîne du résiduel** : affectés ? (inventaire à étendre à
   la chaîne complète, pas seulement aux appels directs de `compute_bilan`).
3. **Les tiers servis bougent-ils ?** — **QUESTION BLOQUANTE.** Rejouer le scoring
   concerné avant/après sur le run servi : si un seul tier change, STOP et arbitrage
   Vic avant application. (Attendu : la fiche et le banquier étant DÉJÀ sur les valeurs
   auditées, le réalignement ne devrait bouger que les chemins `charger()` — copilote
   et cœur faisabilité — donc pas le run servi. À PROUVER, pas à supposer.)
4. Golden 116 + tiers 120/1031/3587/72980/353945 au bit près sur tout ce qui ne doit
   pas bouger.

## 4 · Le chiffre commercial — verdicts de viabilité

Après réalignement, sur un **échantillon représentatif** (a minima : les retenues d'un
run `instruire` par commune calibrée + tirage aléatoire stratifié par tier sur le parc) :
**combien de parcelles passent de « viable » (charge > 0) à « non viable » (charge ≤ 0) ?**
C'est ce que verra un client — le rapport du mandat livre ce nombre, sa méthode, et sa
répartition par commune/tier. Référence : 11/20 sur l'échantillon M26-B (constat §4).

## 5 · Questions jointes (à trancher au mandat, pas bloquantes)

- Porter la sémantique « opération non viable » (charge ≤ 0) dans le payload copilote
  (champ dédié) — le front M26-B l'affiche déjà par convention (constat §5.3).
- Le YAML par commune permet des hypothèses différentes par commune : dire si c'est
  voulu (et alors l'afficher) ou si `hypotheses_faisabilite` doit être unique et sorti
  des YAML PLU communaux.

## 6 · Interdits

Appliquer sans la mesure d'impact validée · faire bouger un tier servi sans GO ·
réaligner sans traçabilité datée dans le YAML · laisser subsister UN appel
`Hypotheses()` direct hors engine/tests · corriger « en douce » d'autres hypothèses au
passage (tout écart = décision listée au rapport).

## 7 · Points d'arrêt

- **A** — Plan + résultat de l'inventaire étendu (chaîne résiduel, score_e sur pièces).
- **B** — Mesure d'impact complète (§3-§4) AVANT tout code de bascule. GO/arbitrage Vic.
- **C** — Application + preuves (tests, golden, verrou), revue finale.
