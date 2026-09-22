# LA BUSE — Rapport d'audit QA fonctionnel

> Audit mené **en pilotant l'app dans un vrai navigateur** (Playwright headless, Chromium),
> pas par simple lecture de code. Backend `labuse api` sur `:8000`, données pilote Saint-Paul
> (97415, 2 995 parcelles évaluées). Suite reproductible : `node qa/e2e.mjs` (14 scénarios, verts).

## Méthode

- Collecteurs globaux : erreurs JS non rattrapées (`pageerror`), `console.error`, requêtes
  4xx/5xx/échec — **le bruit des tuiles externes (réseau bloqué) est exclu**.
- ~45 interactions automatisées : chargement, refresh, 5 filtres rapides, panneau filtres
  (statuts, 3 curseurs, sous-densité, propriétaire), reset, audit à la demande (vide / valide /
  invalide), carte (zoom, légende, contrôles), fiche (ouverture, accordéons, actions, exports,
  Escape), pipeline (8 colonnes, tris, « à rappeler », retour radar), veille (+Zone, ↻), démo
  (ouverture / Escape), 4 points de rupture responsive, a11y (focus, ✕ cachés).
- Vérifications ciblées sur les zones sensibles (cohérence des compteurs, focus des modales,
  repli des KPIs).

## Verdict global

**App solide et crédible en démo.** Aucun bug **P0**. **Zéro** erreur JS, **zéro** requête en
échec, **zéro** débordement horizontal (1440 → 390 px). KPIs remplis, filtres cohérents
(83 + 782 + 1 965 + 165 = 2 995 = « Tout »), exports 200, audit valide ouvre la fiche, pipeline
8 colonnes, démo sans commande technique au premier niveau. **2 défauts réels** trouvés et
**corrigés** (1 a11y, 1 résilience).

---

## Registre des bugs

### BUG-A11Y-01 — La fiche fermée capte encore le focus clavier · **P1** · CORRIGÉ
- **Écran** : fiche parcelle (`#sheet`).
- **Repro** : ouvrir une fiche, la fermer (✕ / Escape / scrim), puis tabuler dans la page.
- **Attendu** : une fiche fermée sort de l'ordre de tabulation et de l'arbre d'accessibilité.
- **Observé** : fermée, `#sheet` reste `display:block` (poussée hors écran via `translateX(102%)`
  pour conserver la transition de glissement) → **36 éléments focusables** restaient atteignables
  au clavier, et `aria-hidden="true"` posé sur un conteneur à descendants focusables = **violation
  ARIA** (le focus « disparaissait » hors écran).
- **Cause** : choix de transition `display:block` + translation, sans neutralisation du focus.
- **Correction** : attribut **`inert`** sur `#sheet` au repos (retiré à l'ouverture, reposé à la
  fermeture) → retire la fiche fermée du tab order, de l'arbre a11y et des événements pointeur,
  **sans casser** l'animation. `inert` présent dès le HTML initial.
- **Fichiers** : `src/labuse/api/web/index.html` (attribut initial), `src/labuse/api/web/app.js`
  (`openSheet` / `closeSheet`).
- **Garde-fou** : E2E `7b.fiche-escape-inert` (`hidden=true, inert=true, focusLeak=false`).

### BUG-RESIL-01 — KPIs bloqués sur « — » si `/stats` échoue · **P2** · CORRIGÉ
- **Écran** : sidebar, blocs KPI (parcelles / opportunités / à creuser / exclues).
- **Repro** : `/stats` indisponible (panne backend) pendant que la carte charge.
- **Attendu** : les KPIs ne restent jamais à « — » tant que des parcelles s'affichent.
- **Observé** : `loadStats()` (en parallèle du geojson) tombait sur `{}` → `fmt(undefined)` = « — »
  **persistant**, alors que la carte montrait des parcelles → impression de produit « cassé/vide ».
- **Cause** : KPIs (source `/stats`) et carte (source `/map/parcels.geojson`) découplés, sans repli.
- **Correction** : `reconcileKpisFromFeatures()` — après chargement des parcelles, si un KPI est
  encore « — », on **reconstruit les compteurs depuis les parcelles déjà chargées** (même périmètre
  commune → cohérent avec la carte). `/stats` reste autoritatif : on n'écrase que ce qui est vide.
- **Fichiers** : `src/labuse/api/web/app.js` (`reconcileKpisFromFeatures`, appel dans `main`).
- **Garde-fou** : E2E `11.kpi-fallback-stats-down` (`/stats` aborté → KPIs = 2 995 / 83 / 782 / 165).

---

## Vérifié — comportements corrects (suspects levés)

| Zone | Résultat |
|---|---|
| **Loader + état vide simultanés** | Jamais. Loader couvre au boot, état vide seulement `DATA_READY` + 0 résultat. |
| **« Aucune parcelle » à tort** | Non. Caché par défaut (filtre opp + à creuser → 865 affichées). |
| **Reset filtres** | Récupère bien (exclue 165 → reset 865 ; surface max → vide → reset 865). |
| **Refresh / persistance** | **Aucun `localStorage`** : refresh repart sur le filtre par défaut, jamais d'« état fantôme ». Filtres sauvegardés = **serveur** (`/filters`), non auto-appliqués. L'hypothèse « filtres sauvés masquant tout au refresh » **ne peut pas se produire**. |
| **Filtre « Écartée » = 1 965** | Correct : Saint-Paul compte 1 965 `faux_positif_probable`. (La « zéro faux positif » venait d'un dump multi-communes non scopé.) |
| **Audit champ vide** | N'ouvre pas de fiche ; message « Saisissez une adresse ou une référence… ». |
| **Audit valide (« BP 571 »)** | `POST /audit/reference` 200 → « Déjà au référentiel — fiche ouverte ». |
| **Escape / ✕ / scrim** | Ferment la fiche (la détection initiale `isVisible` était faussée par `display:block`). |
| **Exports** | `format=md/html/onepager` → 200. PDF 1-page (onepager) ouvert en nouvel onglet. |
| **Actions fiche** | + Pipeline (`POST /pipeline` 200), ⊕ Comparer (tray), bon lead / écartée (`POST /feedback` 200). |
| **Owner / sous-densité** | Filtrent (public 161, privé 129, sous-densité 482). |
| **Démo guidée** | Ouvre/ferme, « Démo prête », **0 commande terminal** au 1er niveau (repliées en `<details>`). |
| **✕ multiples dans le DOM** | `demo-close` / `cmp-close` en `display:none` (OK) ; seul `#sheet` fuyait → corrigé. |
| **Responsive** | 0 débordement horizontal à 1440 / 1024 / 768 / 390 px. |

## Endpoints exercés (tous 200)

`/app/*`, `/stats`, `/coverage`, `/filters`, `/map/parcels.geojson`, `/map/permits.geojson`,
`/parcels/{idu}`, `/parcels/{idu}/enrichment`, `/parcels/{idu}/export`, `/pipeline`,
`/pipeline/meta`, `/pipeline/parcel/{idu}`, `/watch-zones`, `/alertes`, `POST /alertes/refresh`,
`/assistant/status`, `/demo`, `/demo-status`, `POST /audit/reference`, `POST /audit/adresse`,
`POST /pipeline`, `POST /feedback`.

## Résultats

- **E2E `qa/e2e.mjs`** : 14/14 verts (exit 0).
- **pytest** : 293 verts. **ruff** : clean. **`node --check`** : OK.

## À tester manuellement ensuite (hors portée headless)

1. **Lecteur d'écran réel** (NVDA/VO) sur la fiche ouverte/fermée (l'`inert` est posé, à confirmer en conditions réelles).
2. **Dessin de polygone** au pointeur (création zone de veille / audit zone) — le mode s'arme/désarme bien, mais le tracé multi-clics se valide mieux à la main.
3. **Carte en ligne** (tuiles) sur un poste à réseau ouvert : ici les tuiles externes sont bloquées (normal en CI).
4. **IA « Expliquer cette parcelle »** : nécessite `ANTHROPIC_API_KEY` (statut « non configurée » géré proprement).
5. **Démo « non prête »** : état dégradé non déclenchable sans casser la base de démo.
