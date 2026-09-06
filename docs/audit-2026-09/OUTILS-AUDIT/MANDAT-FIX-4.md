# MANDAT OUTILS-FIX-4 — Scan patrimoine · Étudier un bien · Risques · Courrier

**Rédigé par :** Fable, 06/09/2026. Dernier mandat de correctifs de l'audit OUTILS-AUDIT-1. Suite de FIX-1, FIX-2, FIX-3 (tous mergés dans `main`).
**Branche :** `fix/outils-4`, créée depuis `main` à jour.
**Périmètre :** exactement les points listés. Pas d'audit collatéral, pas de refonte, pas d'extraction de composants au-delà de ce qui est écrit.

## Étape 0

`pwd`, `git branch --show-current`, `git status -sb`. Conditions : branche `fix/outils-4`, arbre propre, `main` contient le merge de `fix/outils-3`. Sinon : s'arrêter.

## Garde-fous

- DA existante, composants existants, aucun style nouveau. Rappel FIX-3/A : tout composant portant la grammaire `.fiche-v6` doit être rendu dans un conteneur `.fiche-v6`, sinon la typographie retombe au défaut navigateur.
- Aucun calcul métier au front. Aucune donnée servie sans son statut Sourcé / Estimé / Absent.
- Aucun bouton d'export (décision Vic du 06/09). Aucune surface IA hors fiche parcelle et Copilote.
- Capture avant / après par écran touché dans `docs/audit-2026-09/OUTILS-FIX-4/`.
- `pytest tests/` (avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`), vitest, tsc — verts.
- Un commit par lot. Push, **pas de merge**.

---

## Lot A — Scan patrimoine

**A1. Millésime MAJIC affiché.** L'outil sert des parcelles détenues d'après les fichiers fonciers DGFiP sans jamais dire de quelle année ils datent. Afficher le millésime servi par la base, en tête de l'onglet Possession, au même endroit et dans la même forme que les autres mentions de fraîcheur de l'app.

**A2. Valorisation affichée.** `valorisation_nu_eur` est calculée par le moteur puis jetée avant l'écran. La servir dans le bloc de synthèse, à côté de « m² SDP résiduelle », avec son statut (Estimé) et la même convention de format que le reste de l'app.

**A3. Dates d'opération, onglet Construction.** Les opérations à un seul permis s'affichent « 01/01/2024 », « 01/01/2023 » — une année seule rendue comme une date complète. Quand seule l'année est connue, afficher l'année (« 2024 »). Quand la date réelle est connue, la date.

**A4. Nombre sans libellé.** Chaque ligne d'opération se termine par un nombre nu (« · 5 », « · 2 ») dont rien ne dit ce qu'il compte. Lui donner son libellé (« 5 logements », « 5 permis », selon ce que c'est réellement — CC le vérifie dans la source avant d'écrire le mot).

## Lot B — Étudier un bien

**B1. Une seule médiane appartement.** L'écran sert aujourd'hui deux médianes contradictoires en apparence : le bloc secteur (2 365 €/m², 34 ventes, fenêtre longue) et le détail par type (2 403 €/m², 43 ventes, fenêtre courte). CC établit d'abord ce que chacune calcule (fenêtre, périmètre, filtre) et le consigne. Puis : soit une seule médiane est servie, soit les deux restent mais chacune dit sa fenêtre et son périmètre à l'écran. Jamais deux chiffres pour le même fait sans que l'écart soit lisible.

**B2. Badges Sourcé / Estimé** sur les champs servis hors bloc secteur, comme dans la fiche parcelle dont l'outil reprend le moteur.

**B3. Dernières ventes de la parcelle.** L'historique DVF de la parcelle consultée existe en base et n'est jamais montré ; seules les médianes de secteur le sont. Ajouter une ligne « Dernières ventes de cette parcelle » (date, prix, surface) quand il y en a, et l'état vide honnête quand il n'y en a pas.

## Lot C — Pièges & risques

**C1. Tiroir « Comment ce score est calculé ».** Les seuils qui font le résultat (emprise PPR 2 % / 50 %, distances 50 m, barème 70/50/30) sont invisibles. Les exposer dans un tiroir replié, valeurs lues de la config, jamais réécrites en dur au front. Même composant de tiroir que « Le calcul, étape par étape » de Faisabilité.

**C2. CATNAT dans le crible de lot.** Les 426 arrêtés de catastrophe naturelle sont lus par la fiche parcelle mais pas par le crible de lot — or c'est exactement ce qu'on veut cribler sur un lot. Ajouter la colonne (nombre d'arrêtés, dernier arrêté) au crible, avec son statut.

**C3. Doublon d'aléa à vérifier.** Sur `97415000AC0024`, l'audit soupçonne « mouvement de terrain moyen » affiché deux fois. CC vérifie sur cette parcelle : s'il y a doublon, il l'explique (deux sources ? deux zonages ?) et le corrige ; sinon il le dit et ne touche à rien.

## Lot D — Courrier propriétaire

**D1. État du service avant le geste.** Aujourd'hui le client découvre que l'envoi est indisponible seulement au moment d'envoyer. Afficher l'état du service (disponible / indisponible) à l'ouverture de l'outil, avant toute saisie.

**D2. Plafond du jour visible.** Le quota quotidien n'est connu qu'à travers l'erreur 422. L'afficher à l'ouverture, avec ce qu'il reste.

---

## Compte-rendu

≤ 20 lignes : les commits, les captures, ce que B1 et C3 ont établi, ce qui a résisté avec `fichier:ligne`, le résultat des tests. Toute décision prise faute d'instruction est signalée explicitement.
