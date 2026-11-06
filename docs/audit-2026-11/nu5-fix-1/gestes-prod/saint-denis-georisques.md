# Geste prod E-2 — réparer le trou « mouvement de terrain » à Saint-Denis

**Diagnostic (prouvé sur base locale, identique en prod).** La couche `georisque_alea` servie à la
fiche commune *et* aux fiches parcelles ne portait **0 feature « mouvement de terrain » pour
Saint-Denis** (La Possession : 409 / 62 km², Saint-Paul : 202 / 206 km², Sainte-Marie : 9) — seuls
0,059 km² débordent des communes voisines. La fiche commune affichait donc
`mouvement_terrain_pct ≈ 0,1 %` sur la commune la plus peuplée, et **les fiches de parcelles de
Saint-Denis sont touchées aussi** (vérifié : `97411000CE0218` → aucun aléa mouvement de terrain,
alors que la commune a un PPR multirisques approuvé — chutes de blocs La Montagne / Grande
Chaloupe / route du Littoral, glissements).

**Cause racine.** La complétion DEAL (WFS) de `labuse ingest-georisques --alea` était **sautée dès
qu'une commune portait un aléa quelconque** (`has_alea = count(georisque_alea)`). Saint-Denis
portait déjà l'inondation/submersion (issues du PPR) → le WFS DEAL, qui apporte *aussi* le
mouvement de terrain, n'a **jamais été appelé** pour elle.

**Correctif au code (ce commit).** Le garde ne considère plus une commune « faite » que si elle
porte **déjà du mouvement de terrain** (`… AND lower(coalesce(attrs->>'type',subtype)) LIKE
'%mouvement%'`). Une commune sans mouvement de terrain (toujours présent en 974, relief volcanique)
est donc **re-complétée automatiquement** — sans `--force`.

**Geste prod (chemin sûr, commune-scopé, atomique par commune).**

```bash
# sur labuse-vps, hors 01–05 h, avec le code corrigé déployé :
labuse ingest-georisques --commune 97411            # re-complète Saint-Denis (DELETE+INSERT commune-scopé)
#  (ou, sans attendre le correctif : labuse ingest-georisques --commune 97411 --force)
# puis rafraîchir le cache de la fiche commune (sinon la valeur figée reste servie) :
labuse jobs run fiche-commune-cache
```

**Contrôle après coup** (doit remonter à ~100 %, comme les communes voisines) :

```sql
SELECT round((ST_Area(ST_Union(sl.geom_2975))/1e6)::numeric,2) AS km2
FROM spatial_layers sl
WHERE sl.kind='georisque_alea' AND sl.commune='Saint-Denis'
  AND lower(coalesce(sl.attrs->>'type',sl.subtype)) LIKE '%mouvement%';
-- attendu : couverture significative (≫ 0,06 km²) ; mouvement_terrain_pct de la fiche ≫ 0,1 %
```

> Rappel : la vérification « neighbors ont la couche, Saint-Denis non » prouve que le mouvement de
> terrain EST disponible côté DEAL ; le trou vient bien du garde d'ingestion, pas de l'amont.
