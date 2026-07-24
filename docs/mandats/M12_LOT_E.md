# M12 — LOT E : Filtres & résultats

**Branche** : `feat/m12-e-filtres` · **Base** : `main` · **Dépend de** : LOT A (A2, A4, A5).
**Build** : `tsc -b && vite build` 0 erreur. **Golden** : voir bas de page.

## Fait

### E1 — Refonte du panneau Filtres (`header/Header.tsx`, `lib/filters.ts`)
- **« Dirigeant 65+ » MASQUÉ** : audit A5 → les codes `RNE_DIRIGEANT_75/70/65` sont absents des données (0 résultat sur le run servi). Filtré à l'affichage (`V_SIGNAL_DEFS.filter(d => d.key !== 'dirigeant')`). **Le code reste** dans `filters.ts` (R1 : masquer ≠ supprimer) — réapparaîtra dès le backfill du signal.
- **Renommage client** (cohérent B1) : `SCORE Q ≥` → **« POTENTIEL ≥ /100 »** ; `SDP ≥ m²` → **« SURF. CONSTR. ≥ m² »**. Commentaire A5 sur l'exclusion silencieuse du SDP (les parcelles sans surface résiduelle mesurée — 39 % — ne sont pas retournées).
- **Marginaux conservés** (renvoient des résultats) : « Avec événement (BODACC) » (40), « DPE F-G » (27). Non masqués (ils fonctionnent), mais candidats à relégation si Vic le souhaite.

### E2 — Retrait des chips de verdict du bandeau (`panel/ResultsSection.tsx`)
- Composant `TierChips` (Tout / Brûlantes / Chaudes / Réserve / À creuser / Écartées) **retiré** — doublon avec le bloc « Verdict · Scoring v2 (multi) » du panneau « + Filtre » (**point d'entrée unique**).
- Toggle **« masquer les copropriétés » retiré du bandeau** (présent dans « + Filtre »).
- **Les chiffres restent** : la ligne `120 brûlantes · 1 031 chaudes · 3 587 réserve` + la barre proportionnelle, en **info non cliquable**. A4 : ces compteurs sont cohérents (opportunité = brûlante + chaude).

### E3 — Lever la limite de 500 (`panel/ResultsSection.tsx`, `lib/api.ts`)
- `getResults` gagne un paramètre **`offset`** (le back le supporte déjà nativement — A2 : `LIMIT/OFFSET` en SQL, top-N sur index `ix_p_v2_run_rang`).
- La liste île passe de `useQuery` (fetch unique 500) à **`useInfiniteQuery`** : pages de 200, bouton **« Charger plus »** qui accumule via offset. Le plafond dur de 500 disparaît ; les deux libellés (« 500 premiers » / « 200 visibles / 500 ») sont supprimés au profit de « N affichées / total ».
- **Les deux plafonds constatés en A2 traités** : le slice client 200 ne s'applique plus qu'au **mode commune** (GeoJSON déjà complet) ; le mode île pagine côté serveur.
- Choix **pagination** (pas scroll infini) — conforme à l'arbitrage : A2 a montré que le tri `rang` est quasi-gratuit (index top-N) mais que `mult/surface/commune` paginés en profondeur coûtent (VPS CPU-bound). « Charger plus » borne la charge à l'action explicite de l'utilisateur.

### E4 — Export CSV : **INCHANGÉ** (décision Vic). Aucune touche au CSV.

## Décisions CC (défaut réversible)

| Point | Choix | Alternative écartée | Revenir en arrière |
|---|---|---|---|
| E1 Dirigeant 65+ | **Masqué** (filter à l'affichage) | Supprimer du code | Retirer le `.filter(d => d.key !== 'dirigeant')` |
| E1 architecture IA | **Proposé, non implémenté** (voir ci-dessous) | Implémenter sans validation | — |
| E3 | **Pagination « Charger plus »** (page 200) | Scroll infini | Remettre `useQuery` limit 500 |

## E1 — Piste architecture « filtres spéciaux via saisie IA » (proposé, NON implémenté — Vic arbitre)

Le panneau « + Filtre » reste **fixe** pour les filtres à fort impact (verdict, potentiel, surface, SDP, événement, veille, copro, flags, signaux). Pour les **filtres rares/spéciaux**, piste : une **saisie IA en langage naturel** (exemples pré-remplis), sur le modèle de la partie « IA » de la recherche simple.
**Attention (croise A8)** : la cible réutilisable est **`useApplySearch` + `/ia/search`** (brique NL **partagée**, reste dans l'app), **PAS** le `Builder`/`nlSegmentsSearch` de Vues (qui part au spin-off C-bis). À trancher par Vic avant implémentation.

## Note de merge

E et B éditent tous deux `panel/ResultsSection.tsx` (B retire le « 92 » + libellés de tri ; E retire les chips + pagine). **Conflit de merge attendu** entre `feat/m12-b-preuve` et `feat/m12-e-filtres` sur ce fichier — les deux changements sont compatibles (zones différentes : B = ResultCard + SORTS ; E = list/chips/footer). Résolution simple à la main.
