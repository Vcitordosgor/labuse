# RECETTE-4 — reprise de la recette Vic des 29 et 30/10

Branche `fix/recette-4` · worktree `~/Desktop/labuse-recette4` · API 9030 / front 6230 ·
base locale `labuse` (run servi `q_v20`). Pas de merge, aucun accès prod. Preuve = constat
navigateur (Playwright) ; captures sous `docs/audit-2026-10/recette-4/captures/` (hors git
par doctrine MENAGE-1 — livrées via l'app). Un commit par lot.

Légende : **AVANT** = constat Vic reproduit ici · **APRÈS** = après correctif, re-constaté.

---

## Lot 1 — T1 (état d'outil vidé au changement d'outil) + nettoyages Solaire / Assemblage

### T1 — « Changer d'outil vide tout l'état de l'outil quitté »

**Racine.** Le store vide bien l'état partagé (`setModule` remet `selectedIdu`,
`contexteCommune`, `moduleMap`… à null). Mais l'**état local React** des composants-outils
(sous-vue, commune choisie, onglet, champ saisi) ne tombe que si React **remonte** le
composant. Or `<Body />` dans `ModulePanel` n'était **pas keyé**. Quand deux clés d'outil
résolvent la **même fonction composant** — `communes`↔`barometre` → `Communes`,
`permis`↔`promesses` → `M03` — React **réutilise l'instance** à travers le changement
d'outil : la sous-vue (« Acquisitions récentes ») et sa commune survivaient.

**AVANT (reproduit).** Outil Communes → porte « Acquisitions récentes » → commune
Saint-Denis → bascule vers un autre outil → retour sur Communes : la sous-vue
« Acquisitions récentes » et « Saint-Denis » étaient **toujours là** (`select` encore monté).
→ `captures/t1-communes-AVANT.png`.

**Correctif (racine, mécanisme commun).** `frontend/src/components/outils/ModulePanel.tsx` :
`<Body key={def.key} />` aux deux points de rendu (branche normale + branche
`analyser-annonce`). React remonte **à neuf à chaque changement de clé d'outil** — garantie
uniforme pour TOUS les outils, pas seulement les paires aliasées.

**APRÈS (re-constaté).**
- Communes : `barometre` (acquisitions, Saint-Denis) → `communes` ⇒ retour à l'accueil
  (4 portes), plus de `select`. → `captures/t1-communes-APRES.png`.
- Scan patrimoine : porte « Un propriétaire » + saisie `TESTSTATE123` → PLU → retour
  `patrimoine` ⇒ accueil (2 portes), champ vidé.
- Les 5 outils cités (Communes, Scan patrimoine, Analyser une annonce, Prospection solaire,
  Successions) remontent désormais à neuf à tout changement d'outil.

### Prospection solaire — deux paragraphes retirés

**Mandat.** Supprimer les deux paragraphes sous le graphe mensuel (« Productible estimé… » et
« En clair… »).

**Correctif.** `ProspectionSolaire.tsx` — les deux `<p>` retirés ; le graphe mensuel et le
bloc annuel (qui porte déjà la maille) restent.

**APRÈS.** Parcelle `97410000AS1425` : graphe « Profil mensuel » présent, aucun des deux
paragraphes (`Productible estimé à la…` / `En clair : le potentiel…`). →
`captures/solaire-APRES.png`.

### Assemblage — encart d'en-tête retiré, noms de PM en entier

**Mandat.** Retirer l'encart d'explication en tête ; afficher les noms des personnes morales
en entier, sur plusieurs lignes si besoin.

**Correctif.** `moteurs.tsx` (M16) — `<Banner>` d'intro retiré ; `truncate` → `break-words`
sur la liste « PM : … » et sur la dénomination par parcelle.

**APRÈS.** Assiette contiguë `97422000BW1992 + BW2857 + BW2858` (bloc SA HLM) : en-tête =
directement « Étape 1 » (plus d'encart) ; « PM : SOCIETE ANONYME D'HABITATIONS A LOYER
MODERE DE LA REUNION » affiché **en entier sur 2 lignes**, non tronqué. →
`captures/assemblage-APRES.png`, `captures/assemblage-pm-nom-APRES.png`.

_tsc -b : 0 erreur._
