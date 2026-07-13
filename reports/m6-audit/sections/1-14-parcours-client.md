# M6 §1.14 — Parcours premier client (audit lecture seule, 13/07/2026)

**Protocole.** Simulation Playwright desktop 1440×900, cache froid, app en dev mode sur
`http://127.0.0.1:8010/socle/`. Script rejouable : `frontend/qa/m6_parcours_client.mjs`
(`cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/m6_parcours_client.mjs`).
Captures : `reports/m6-audit/sections/captures-1-14/`.
Persona : un client qui n'a jamais vu l'app, objectif « trouver une première opportunité
foncière crédible ».

## 1. Chronologie chiffrée

Les temps « machine » sont mesurés par le script (constants à ±0,5 s sur 3 exécutions).
Le « temps client estimé » ajoute la lecture/compréhension humaine (estimation, consignée
comme telle).

| # | Étape | Machine (cumul) | Client estimé |
|---|-------|----------------:|--------------:|
| 1 | Arrivée : structure de page | 0,3 s | — |
| 2 | Carte de l'île affichée (MapLibre) | 0,6 s | ~5 s |
| 3 | Tuiles + couches au repos | 3,3 s | ~15 s (il regarde la carte) |
| 4 | Clic sur l'unique CTA « Afficher l'analyse LABUSE » → chips de verdict (Brûlantes v2 117 · Chaudes 960 · …) + liste triée par rang | +2,8 s après le clic (8,5 s) | ~45 s (trouver le CTA, lire les 5 chips) |
| 5 | Ouverture du « pourquoi ? ▾ » (lexique des verdicts) | 9,0 s | ~1 min 30 (lecture) |
| 6 | Premier filtre : chip « Brûlantes v2 » | +2,5 s (12,1 s) | ~2 min |
| 7 | Première fiche ouverte (1re carte de liste = rang 1) : verdict, zone PLU, surface, marché, propriétaire | +3,0 s (15,6 s) | ~2 min 30 |
| 8 | **Première opportunité PERTINENTE** : AB 1908, Brûlante v2 · rang 1 · ×64,0, 313 m², Les Trois-Bassins, non écartée, signaux sourcés | **16,1 s machine** | **~3 min réels** |
| 9 | (Détour classique) recherche omnibox « AS 1425 » | +2,7 s | — |

**Verdict global : le chemin nominal est COURT et honnête.** Un seul CTA à l'arrivée, le
tri par rang met une vraie brûlante en tête, la fiche confirme le verdict sans
contradiction, et le « pourquoi ? » existe. Aucune erreur console, aucun clic mort sur le
chemin nominal. Le client atteint une opportunité défendable en ~3 minutes.

## 2. Frictions, priorisées

### P1 — bloquant pour un client payant

1. **Aucune adresse sur la fiche parcelle.** La fiche (`GET /parcels/{idu}`) ne sert
   ni numéro, ni voie, ni lieu-dit — seulement IDU + commune. Le client qui veut aller
   voir le terrain ou en parler à un notaire n'a que la carte. Or les adresses BAN sont
   en base (rapprochement à 99,99 %, wave adresses) et les vues métier les exportent
   déjà (`adresse_numero`, `adresse_voie`…). Vérifié : la réponse API de la fiche
   AB 1908 ne contient aucun champ adresse. → Servir l'adresse BAN sur la fiche.

### P2 — ralentit ou trouble la découverte

2. **Jargon interne non expliqué à l'écran de première lecture** : « Brûlantes **v2** »
   (numéro de version interne exposé au client), « rang P », « ×N », toggle
   « Verdict / Mutabilité », badge « VL ». Le « pourquoi ? ▾ » explique les tiers, mais
   ni le « v2 », ni le ×N, ni « Mutabilité ».
3. **Lecture des cartes de résultat** : la ligne se termine par « ×64.092 » — c'est en
   réalité « ×64.0 » (multiplicateur vs moyenne du parc) collé au « 92 » (score
   qualité). Sans séparateur ni libellé, le premier regard lit un nombre absurde. Les
   explications n'existent qu'en tooltip au survol.
4. **Latences perceptibles aux moments décisifs** : 2,8 s entre le clic CTA et les
   chips ; 3,0 s à l'ouverture de fiche ; 2,5 s par filtre. Des indicateurs de
   chargement existent (toast « Chargement de la carte », squelettes) mais la fenêtre
   « j'ai cliqué, rien ne bouge » reste sensible sur le CTA d'entrée.
5. **Popover « pourquoi ? »** : il se ferme en cliquant n'importe où SAUF sur le bouton
   « pourquoi ? » lui-même (le fond plein écran intercepte le clic). Re-cliquer le
   bouton = clic sans effet perçu. (Découvert par le script : le clic est intercepté
   par `div.fixed.inset-0`.)

### P3 — cosmétique / à savoir

6. **Prix** : la fiche donne une médiane DVF de secteur (ex. 381 €/m²) et la calculette
   de charge foncière — c'est honnête (pas de prix par parcelle en base, doctrine
   consignée) mais le client cherchera « le prix de CETTE parcelle » ; le libellé
   « médiane bâti secteur » mérite d'être dit dès la synthèse.
7. **Contact propriétaire** : personnes physiques non identifiables (RGPD) — la fiche
   l'assume (« non couvertes par l'open data ») et le canal « Courrier propriétaire »
   existe. Correct, mais le client doit comprendre que « contact » = courrier posté,
   jamais un téléphone.
8. **Réseau** : ~30-50 requêtes de tuiles `.pbf` avortées (ERR_ABORTED) pendant les
   zooms — invisible pour le client, mais du bruit dans les logs.

## 3. Ce qui marche bien (à préserver)

- Un seul CTA à l'arrivée, pas de tunnel de configuration.
- Tri par rang P : la première carte est la meilleure opportunité de l'île — le
  « wahou » arrive à la première fiche.
- Cohérence liste ↔ fiche (même verdict, même rang) — vérifiée aussi par la suite §1.15
  (scénario S8 : chips SQL-exactes, fiche d'une écartée porte bandeau + badge).
- La recherche omnibox répond en <3 s sur une référence cadastrale partielle.
