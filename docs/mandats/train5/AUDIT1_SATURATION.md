# AUDIT 1 — SATURATION & EX AEQUO (lecture seule, 04/08/2026)

## p_raw ≥ 0,99 : il n'en reste que 3 — mais le vrai problème est ailleurs
- **3 parcelles à p_raw = 1,0 exact** : rangs 1-2-3, toutes brûlantes, toutes AP La Possession
  (lotissement récent). Les 2 autres saturées historiques (AB1908/AB1910, Trois-Bassins) ont
  été cassées par la **pondération au_sous_plancher** (×0,19 → p ~0,19/0,15) puis retirées
  par la règle bâtie-révélée : la saturation en tête s'est auto-réduite de 5 → 3.
- « permis < 2 ans » (+1,30) est LA cause dominante (top-1 des 3, comme des 5 d'origine),
  cumulée avec zone AU (+0,39), rotation nu (+0,31), canopée (+0,24), croisement
  tenure×permis (+0,22) — le sigmoïde sature.

## LA TROUVAILLE (remontée en cours d'audit) : le classement de tête est un TRI DE PALIERS
Le modèle est entièrement binné (features discrétisées) → p ne prend que des valeurs
discrètes. **Top 1000 servi : 19 valeurs de p distinctes, 988/1000 parcelles en ex aequo,
plus gros palier = 514.** Top 100 : 1,0×3, 0,3438×13, puis 4 singletons, puis 0,2044×81.
- L'ordre INTRA-palier est le tirage seedé 974 (`pipeline.py:256-266`) — reproductible
  mais ARBITRAIRE.
- Pire : la coupure chaude (n_entrée ~1150) et la coupure brûlante tombent AU MILIEU de
  paliers → l'appartenance à la tête parmi des centaines d'égales est décidée par la graine.
- Plafonner permis_bin ne crée pas d'ordre : il déplace les paliers (le top 20 changerait
  d'ordre, mais vers un autre arbitraire).

## Départage explicite proposé (arbitrage Vic)
À p égal (même palier), ordonner par critères PRODUIT, dans cet ordre :
1. **SDP résiduelle décroissante** (la capacité est le cœur de l'offre) ;
2. **surface décroissante** ;
3. contribution D décroissante (dynamique) ;
4. IDU croissant (stabilité totale, plus de graine).
Implémentation : remplacer le tie aléatoire du lexsort par ces clés — mesure à blanc
(mouvements du top 100) avant toute bascule. Phase 3, sur arbitrage.
