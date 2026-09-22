# M-W — Montée vite 5 → 8 (purge esbuild GHSA-67mh-4wv8-2f99)

**Préconditions vérifiées** : `git log` montre `Merge branch 'feat/m-u-agent-prix'` (3f947472) **et**
`Merge branch 'feat/m-v-purge-dette'` (a4d18226). Base = main a4d18226. Branche `feat/m-w-vite8`,
**1 commit**, STOP review Vic.

## Ce qui a été monté (lockstep, rien de plus)

| paquet | avant | après | raison |
|---|---|---|---|
| `vite` | ^5.4.9 | **^8.2.1** | correctif esbuild (3 majeures) |
| `@vitejs/plugin-react` | ^4.3.2 | **^6.0.5** | plugin-react v6 exige vite 8 (peer `^8.0.0`) |
| `vitest` | ^4.1.10 | **inchangé** | 4.1.10 supporte déjà vite `^6 \|\| ^7 \|\| ^8` |

Autres devDeps : aucune montée (peers déjà satisfaits). Les peers babel de plugin-react v6
(`@rolldown/plugin-babel`, `babel-plugin-react-compiler`) sont **optionnels** → non ajoutés.

## Breaking changes RÉELS traités (guides 5→6→7→8 lus, pas à l'aveugle)

**Vite 8 = Rolldown + Oxc remplacent Rollup + esbuild.** Sur notre config, trois seuls impacts :

1. **`build.rollupOptions` → `build.rolldownOptions`** (renommé sous Rolldown). Fait.
2. **`output.manualChunks` forme OBJET RETIRÉE** sous Rolldown (`{maplibre:[...], vendor:[...]}` ne
   compile plus : `tsc` erreur TS2769). Migré vers **`output.codeSplitting.groups`** (test par
   chemin). ⚠ J'ai d'abord essayé `advancedChunks` (cité par le guide) mais Rolldown 1.2.3 le
   déprécie lui-même (« advancedChunks is deprecated, please use codeSplitting instead ») → j'ai
   pris le nom courant **`codeSplitting`** pour ne pas laisser un avertissement à redécouvrir.
   Découpage **identique** : maplibre-gl isolé, react/react-dom/scheduler/react-query/zustand → `vendor`.
3. **plugin-react v6** : Babel retiré, React Refresh via Oxc natif. `react()` sans option → OK,
   React 18.3.1 build + HMR vérifiés.

**Non affectés** (vérifiés) : `base:'/socle/'`, `define` injectant `VITE_RUN_LABEL` (chaîne via
`JSON.stringify`, pas un objet → change de « copie d'objet » v8 sans effet), `readFileSync(new URL
(...served_run.txt))` à l'éval, `server.proxy`/`port`, `outDir`/`emptyOutDir`. Les deux mécanismes
sensibles (garde M-Q run servi + code-splitting maplibre M-V) **survivent à l'identique**.

## Validation — complète

1. **`npm run build` passe.** Tailles chunks avant (vite 5) / après (vite 8), même base a4d18226 :

   | chunk | avant brut | après brut | avant gzip | après gzip |
   |---|---|---|---|---|
   | index (eager) | 479,4 kB | 494,1 kB | 129,4 | 129,3 |
   | vendor (eager) | 185,3 kB | 170,6 kB | 58,6 | 54,5 |
   | rolldown-runtime (eager) | — | 0,58 kB | — | 0,36 |
   | maplibre (**différé**) | 801,9 kB | 786,6 kB | 216,7 | 210,0 |
   | MapView (différé) | 33,6 kB | 33,1 kB | 10,5 | 10,2 |
   | TimeMachine (différé) | 3,6 kB | 3,6 kB | — | 1,7 |

   **JS initial (eager) gzip : 188,0 → 184,2 kB** — quasi identique, légèrement plus petit.
   **Pas d'explosion de bundle.** maplibre reste HORS du graphe initial (`grep -c maplibre
   dist/index.html` = 0) → le lazy-load M-V est intact.

2. **`test_run_serving_coherence.py`** : `test_served_run_...`, `test_front_source_...`,
   **`test_bundle_front_construit_sur_le_run_servi`** verts (3 passed ; 2 skips légitimes =
   tuiles/cible distante absentes de cette machine). Le bundle dist contient bien `q_v8_calibre`.

3. **`npm run dev`** : démarre en 108 ms sur vite 8.2.1, sert l'app sous `/socle/`, `VITE_RUN_LABEL`
   transformé en dev (`q_v8_calibre` présent dans `/src/lib/api.ts` servi). Proxy câblé : `/moteurs`
   (outil Marché M-U) → 502 (tentative d'atteindre le backend :8000 éteint), donc la route proxy est
   bien enregistrée. *Rendu carte + interaction Marché = validation écran de Vic (backend requis).*

4. **`VITE_RUN_LABEL`** : injecté au build ET en dev ; le repli vide + la garde `RunNonConfigure`
   (main.tsx) sont du code non touché → env absente ⇒ écran « run non configuré », jamais un run en dur.

5. **`npm audit` : 0 vulnérabilité.** `npm ls esbuild` → **esbuild hors de l'arbre** (Rolldown/Oxc
   l'ont remplacé) → GHSA-67mh-4wv8-2f99 ne s'applique plus. `rolldown@1.2.3` présent.

6. **`vitest run` : 26/26 verts** (et les anciens avertissements esbuild/oxc de vitest ont disparu,
   plugin-react v6 étant oxc-natif).

## À signaler à Vic (hors périmètre code)

- **Node ≥ 20.19 / 22.12 requis par vite 8** (engine). Local = 22.22 ✓. **Vérifier le Node du VPS/CI
  qui exécute `npm run build`** — un Node plus vieux casserait le build en prod.
- **Cible de build par défaut relevée** (baseline 2026 : Chrome/Edge 111, Firefox 114, Safari 16.4).
  Non épinglée (périmètre minimal). Si un navigateur pré-2023 doit être supporté, épingler
  `build.target` explicitement — sinon rien à faire.
- Nouveau petit chunk `rolldown-runtime` (0,58 kB) au graphe initial : normal sous Rolldown.

Aucun autre changement front (pas de refacto, pas de montée de lib non exigée par vite 8).
