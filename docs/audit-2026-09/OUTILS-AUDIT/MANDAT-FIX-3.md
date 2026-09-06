# MANDAT OUTILS-FIX-3 — Retours de recette · fil de retour · exports · IA

**Rédigé par :** Fable, 06/09/2026. Suite de OUTILS-FIX-2 (à merger dans `main` avant).
**Branche :** `fix/outils-3`, créée depuis `main` à jour.
**Périmètre :** exactement les points listés. Pas d'audit collatéral au-delà des inventaires demandés en E et F, pas de refonte, pas d'extraction de composants au-delà de ce qui est écrit.

## Étape 0

`pwd`, `git branch --show-current`, `git status -sb`. Conditions : branche `fix/outils-3`, arbre propre, `main` contient le merge de `fix/outils-2`. Sinon : s'arrêter.

## Garde-fous

- DA existante, composants existants, aucun style nouveau.
- Capture avant / après par écran touché dans `docs/audit-2026-09/OUTILS-FIX-3/`.
- `pytest tests/` (avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`), vitest, tsc — verts.
- Un commit par lot. Push, **pas de merge**.

---

## Lot A — Faisabilité ouverte depuis Densifier (P1)

**A1.** Arrivé sur Faisabilité par le pont depuis Densifier, le bloc « Capacité constructible » sort de la DA : titre et corps de texte nettement plus gros que partout ailleurs (voir capture Vic `Capture 18:31:16`). Réaligner sur les tailles de la DA de l'app — mêmes classes que le même bloc affiché depuis la fiche parcelle ou depuis Faisabilité ouverte directement. Le contenu ne change pas ; seule la typographie revient à la norme.

**A2.** CC dit en une ligne pourquoi la taille différait selon le chemin d'ouverture (classe conditionnelle ? conteneur différent ?), pour que le cas ne revienne pas.

## Lot B — Les deux ponts vers Scan patrimoine (P2, P3)

Constat Vic : depuis Permis, le pont ouvre Scan sur le SIREN 392801130 et l'écran rend « 0 parcelle · 0 actionnable · 0 m² SDP » plus l'encart « Aucun dirigeant au registre INPI — succession ou société en sommeil probable », alors que le permis porte bien un SIRET.

**B1. Établir la cause, avant de corriger.** Pour ce SIREN précis : le pont transmet-il la bonne valeur (SIREN à 9 chiffres, pas le SIRET à 14) ? La résolution propriétaire trouve-t-elle l'entreprise ? Le zéro vient-il d'une absence réelle en base (l'entreprise ne possède rien à La Réunion) ou d'une requête qui échoue silencieusement ? Réponses avec `fichier:ligne` et requête SQL rejouable, déposées dans `docs/audit-2026-09/OUTILS-FIX-3/B-scan-ponts.md`.

**B2. Corriger selon la cause.** Si le pont passe un SIRET là où Scan attend un SIREN : tronquer à la source. Si la donnée est réellement vide : l'écran doit le dire ainsi (« Cette entreprise ne détient aucune parcelle à La Réunion ») au lieu d'afficher trois zéros et un encart d'interprétation.

**B3. L'encart « Aucun dirigeant au registre INPI ».** Il tire une conclusion (« succession ou société en sommeil probable ») d'une absence. Tant que B1 n'a pas prouvé que l'absence est réelle et non un échec de requête, cet encart ne s'affiche pas. Après B1 : il ne s'affiche que si la résolution INPI a effectivement abouti et rendu zéro dirigeant — jamais sur une requête en erreur ou une entreprise non résolue.

## Lot C — Comparer : retirer le badge de scoring (P4)

**C1.** Retirer le badge « Faible » de chaque carte de Comparer. L'analyse LABUSE n'a pas été demandée sur cet écran ; on ne l'impose pas. Le badge « secteur qui bouge » reste (c'est un fait de marché, pas un score).

## Lot D — Fil de retour entre outils

**D1.** Tout pont ouvert par les gestes de FIX-2 (Scan→Courrier, Densifier→Faisabilité, Étudier→Faisabilité/Assemblage, Permis→Scan, listes→Comparer, Solaire→Courrier) pose un retour visible en tête de l'outil cible : « ← Densifier », « ← Permis », « ← Scan patrimoine »… Le retour ramène à l'outil de départ **dans l'état où il était** (même sélection, même filtres, même liste), pas à son état vide.

**D2.** Un seul composant de retour, un seul mécanisme (pile de navigation entre outils), pas une implémentation par pont. Le retour n'apparaît que si l'outil a été ouvert par un pont ; ouvert depuis le menu, rien ne s'affiche.

## Lot E — Retirer tous les exports CSV

**E1. Inventaire d'abord.** CC liste tous les points d'export de l'app (bouton, lien, endpoint `fmt=csv` ou équivalent) : `fichier:ligne` + écran concerné. Liste déposée dans `docs/audit-2026-09/OUTILS-FIX-3/E-exports.md`.

**E2. Retirer les boutons et liens d'export côté écran**, partout — connus à ce jour : Comparer (posé en FIX-2), Solaire piscines (posé en FIX-1), Scan patrimoine, plus ce que l'inventaire révèle. Décision Vic du 06/09 : aucun export CSV dans l'app pour l'instant ; on décidera plus tard où en remettre.

**E3.** Les endpoints et helpers back **restent en place** et testés — c'est le geste utilisateur qui disparaît, pas la capacité. CC ne supprime aucun endpoint, aucune fonction, aucun test back.

## Lot F — Cantonner l'IA

**F1. Inventaire d'abord.** CC liste tous les points d'entrée IA de l'app côté client (bouton, encart, surface mauve, appel à un endpoint IA) : `fichier:ligne` + écran. Liste déposée dans `docs/audit-2026-09/OUTILS-FIX-3/F-ia.md`. Le dashboard admin est hors périmètre.

**F2. Retirer les points d'entrée IA partout sauf deux** : la fiche parcelle et le Copilote. Comme en E, les endpoints back restent.

**F3.** Si un écran perd son seul contenu utile en perdant l'IA, CC ne le supprime pas : il le signale au compte-rendu et laisse l'écran en l'état, pour arbitrage.

---

## Compte-rendu

≤ 20 lignes : les commits, les captures, les trois inventaires (B, E, F) avec leurs comptes, ce qui a résisté avec `fichier:ligne`, le résultat des tests. Toute décision prise faute d'instruction est signalée explicitement.
