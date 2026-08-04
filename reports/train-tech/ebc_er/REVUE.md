# Dette #10 — drapeaux EBC / ER sur la fiche (revue visuelle)

Drapeaux d'INFORMATION, jamais une exclusion. Dérivés côté frontend des prescriptions PLU
DÉJÀ servies par la cascade (`layer='prescription_plu'`, run servi q_v8_calibre). Aucune
modification backend, aucun poids de score, aucun verdict touché.

## Captures (parcelles réelles, run servi)

| Fichier | Parcelle | Contenu |
|---|---|---|
| `apres_ebc_er_97418000AT1740.png` | 97418000AT1740 (Sainte-Marie) | badges « partiellement en EBC (~26 %) » + « emplacement réservé » |
| `avant_ebc_er_97418000AT1740.png` | même parcelle | AVANT : aucun badge (info seulement dans le tiroir « Confiance ») |
| `apres_er_numero_97407000AI1886.png` | 97407000AI1886 (Le Port) | badges « emplacement réservé n°26 » + « n°18 » |
| `avant_er_numero_97407000AI1886.png` | même parcelle | AVANT : aucun badge |

## Ce que prouvent les captures
- Le verdict d'en-tête (« Écartée ×0,9 » / « ×1,2 ») et tous les scores sont **identiques**
  avant/après — les badges n'ajoutent que de l'information.
- Le n° d'ER est affiché quand le libellé GPU le porte (« n°26 »), sinon « emplacement
  réservé » sans n° (honnête : la donnée servie ne l'a pas toujours).
- Couleurs distinctes : EBC vert-menthe, ER ambre (mêmes tokens que les badges existants).

## Reproduire
```
# API : LABUSE_DEV_MODE=1 LABUSE_SERVED_RUN=q_v8_calibre PYTHONPATH=src \
#   ~/miniforge3/envs/labusedb/bin/python -m uvicorn labuse.api.app:app --lifespan off --port 8000
# Front : cd frontend && VITE_RUN_LABEL=q_v8_calibre npm run dev
cd frontend && PHASE=apres node scripts/ebc_er_captures.mjs
```

## Portée / limite honnête
- ER ≥ seuil (~50 %) reste `HARD_EXCLUDE` dans le scoring servi : NON touché (chiffre servi).
  Le badge est purement additif ; il n'a pas modifié cette règle.
- Comptage île (run servi) : 36 205 parcelles avec EBC, 37 088 avec ER.
