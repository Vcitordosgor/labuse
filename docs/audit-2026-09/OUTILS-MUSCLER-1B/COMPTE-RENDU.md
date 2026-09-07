# OUTILS-MUSCLER-1B — compte-rendu (07/09/2026)

**Périmètre.** Outil « Successions à venir » seul, six points. Diff front-only, 4 fichiers.

1. **Renommé** partout via `registry.ts:107` (`label`) — sert menu, titre panneau, fil d'Ariane —
   et le fil de retour `Successions.tsx:51`. Endpoint/clé `successions` inchangés.
2. **« Assembler → » retiré** des cartes (`Successions.tsx`, ancien bloc `data-successions-assembler`) ;
   Assemblage et `/moteurs/assemblage/voisines` intacts (commentaire `moteurs.tsx:148` corrigé).
3. **« Comparer (N) » retiré** ; la sélection reste (elle sert le point 6).
4. **Étiquette de tri retirée** — le tri serveur (résiduel SDP décroissant) ne change pas ;
   la case « tout sélectionner » garde son rôle (libellé honnête « Tout sélectionner »).
5. **Mention du filtre retirée** via prop `noteFiltre={false}` sur `CommuneScope` (partagé par 5 outils
   → masquage local, comportement du filtre inchangé).
6. **« Préparer les courriers » déplacé** en pied, à droite, même ligne que « Détail et méthode »
   (`items-start` maintient l'alignement quand le tiroir s'ouvre) ; compteur, pont et fil conservés.

**Preuve écran.** PNG impossibles (capture Playwright expire à 5 s sur cet écran, avant écriture) —
six points prouvés par mesure DOM + test fonctionnel du pont Courrier, `captures/PREUVE-DOM.md`.

**Tests.** tsc 0 · vitest 187/187 · pytest ciblé 6/6. Suite back 2701 passed / **9 failed
PRÉ-EXISTANTS** (diff front-only, back non touché ; verrous ×3 exigent la base réelle, +courrier_boucle
×2/dashboard/front_reliquats/run_serving/sentinelle — env `labuse_test`).

**Commit.** Un seul, poussé, **pas de merge**.
