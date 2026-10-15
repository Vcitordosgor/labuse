# Domaine 11 — API et robustesse (routes servies, 8790)

## Verdict (3 lignes)
59 requêtes limites tirées sur les vraies routes servies (q_v18/run 15) · 7 invariants de robustesse vérifiés · **2 violations ROBUSTESSE** (toutes deux : tuile MVT avec x/y hors plage → HTTP 500, sur les DEUX routes de tuiles) · aucun affichage sale (« NaN »/« None »/« undefined »/« null »-texte) ni chiffre négatif impossible trouvé dans aucune réponse 2xx.
Resté muet : POST authentifiés (évaluate, projets, scoreur) non sondés en profondeur (demandent une session/tenant) ; la validation x/y a été prouvée côté SQL (ST_TileEnvelope) mais la reproduction en concurrence (pool) n'a pas été rejouée.

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles/requêtes passées | violations |
|---|---|---|---|---|
| I1 | Un idu invalide / malformé / inexistant ne rend JAMAIS 500 : 404 propre (ou 200 vide). | `for p in "" ABCDEF 1 97499000ZZ9999 "97413000%20DD1480" "97413日本語"(url-enc) "' OR 1=1--"(enc) 999…×500 "a%2Fb%2Fc" "97413%00DD"; do curl -so/dev/null -w"%{http_code}\n" "http://127.0.0.1:8790/parcels/$p"; done` + variantes `/geojson /.kmz /zone /explain /exposition /hauteur-lidar /mode-b` | 17 variantes idu | **0** (tous 404, idu valide 200) |
| I2 | Une commune inconnue / vide / unicode / injection ne rend JAMAIS 500. | `curl -s "http://127.0.0.1:8790/communes/ZZZINCONNUE/contexte?source=q_v18"` ; variantes `日本`(enc), `'; DROP TABLE parcels;--`(enc), `/acquisitions-pm` | 5 variantes | **0** (200 structure vide `insee:null, foncier.n_parcelles:0` ; vide/`//`→404) |
| I3 | Paramètres de liste extrêmes (limit énorme/négatif/0/non-num, offset/page négatif, bbox absurde/malformée, source bidon, source-sqli) ne rendent JAMAIS 500 ni donnée fausse. | `curl -s "…/parcels?source=q_v18&limit=99999999"` ; `&limit=-5` ; `&limit=0` ; `&limit=abc` ; `&offset=-10` ; `&page=-1` ; `source=q_v9999` ; `source=q_v18'--`(enc) ; `&bbox=9999,9999,-9999,-9999` ; `&bbox=a,b,c` | 11 variantes | **0** (limit hors-borne/non-num → 422 ; `source=q_v9999` → `[]` vide, pas de fausse donnée ; bbox absurde → 200 liste cohérente) |
| I4 | `/filtre` et `/stats` avec valeurs hors-sens (sdp_min négatif, surface géante, zone bidon, tri injecté, source bidon) ne rendent JAMAIS 500. | `curl -s "…/filtre?source=q_v18&sdp_min=-100"` ; `&surface_min=999999999` ; `&zone=XXXXX` ; `&tri=%3B%20DROP`(enc) ; `/stats?source=q_vZZ` ; `/stats/entonnoir?source=q_vZZ` | 6 variantes | **0** (tous 200, agrégats cohérents ; tri injecté ignoré) |
| I5 | Recherche / suggest (vide, SQLi, unicode, 2000 car.) ne rendent JAMAIS 500 ni fuite SQL. | `curl -s "…/parcels/search?source=q_v18&q="` + `' OR '1'='1`(enc), `日本語🏠`(enc), `x`×2000 ; `/api/recherche/suggest?q=` + `'--`(enc), `À la Réü`(enc) | 7 variantes | **0** (q vide → 422 ; SQLi/unicode → 200 résultat vide ou filtré) |
| I6 | Une tuile MVT hors plage de zoom ou hors emprise répond proprement (204/vide ou 200), JAMAIS 500. | `curl -so/dev/null -w"%{http_code}\n" "…/map/tiles/{z}/{x}/{y}.pbf"` pour z=-1,99,0 ; x/y hors ; hors-Réunion ; valide | 8 variantes `/map/tiles/{z}/{x}/{y}.pbf` | **2 VIOLATIONS** (x ou y hors `[0,2^z)` → **500**) |
| I7 | Aucune réponse 2xx ne contient « NaN »/« None »/« undefined »/« null »-affiché-texte ni chiffre négatif sur surface/prix/SDP/compte. | scan regex `(:\s*NaN\|"NaN"\|"None"\|"undefined"\|:\s*Infinity\|>None<)` + `"(surface…\|prix…\|sdp…\|parcelles\|total\|n…)"\s*:\s*-\d` sur fiche (69 ko), /explain, /stats, /entonnoir, /communes, /filtre | 6 payloads riches | **0** |

## Violations

### V1 — ROBUSTESSE : tuile parcelles `x`/`y` hors plage → HTTP 500
- **gravité** : ROBUSTESSE (plantage serveur, erreur 500 brute).
- **route / cas** : `GET /map/tiles/{z}/{x}/{y}.pbf` avec x ou y hors de l'intervalle valide `[0, 2^z)` **ou négatif**, pour un z accepté (8–15).
- **requêtes** : `GET /map/tiles/12/999999/999999.pbf` → **500** ; `GET /map/tiles/12/-5/-5.pbf` → **500** ; `GET /map/tiles/12/999999/2110.pbf` → **500** (x seul suffit).
- **attendu** : 204 (ou 200 tuile vide), comme pour z hors plage (z=-1/99/0 rendent bien 204).
- **obtenu** : `HTTP 500 Internal Server Error` (corps « Internal Server Error », nu).
- **cause probable** : la route valide `z` (`if z < 8 or z > 15: return 204`) mais **ne valide jamais `x` ni `y`**. À la génération (`_parcel_tile_bytes`) l'appel `ST_TileEnvelope(:z, :x, :y)` lève `ERROR: ST_TileEnvelope: Invalid tile x value, 999999` (reproduit en psql), exception non interceptée → 500.
- **fichier:ligne** : `src/labuse/api/tiles.py:820-840` (garde `z` seule, aucune garde x/y) → `src/labuse/api/tiles.py:625` (`ST_TileEnvelope(:z, :x, :y)` dans `_parcel_tile_bytes`, `tiles.py:546`).

### V2 — ROBUSTESSE : tuile couche (tuyau) `x`/`y` hors plage → HTTP 500
- **gravité** : ROBUSTESSE (même plantage 500, route sœur).
- **route / cas** : `GET /map/tiles/{kind}/{z}/{x}/{y}.pbf` avec un `kind` déclaré valide et x/y hors plage / négatifs.
- **requêtes** : `GET /map/tiles/zfang/12/999999/999999.pbf` → **500** ; `GET /map/tiles/zfang/12/-5/-5.pbf` → **500** ; idem z=14 ; tuile valide `…/zfang/12/2345/2110.pbf` → 200.
- **attendu** : 204/200 vide (un `kind` inconnu rend déjà 404 proprement ; un z hors `[0,22]` rend 404).
- **obtenu** : `HTTP 500 Internal Server Error`.
- **cause probable** : identique à V1 — la route garde `kind` (404 si absent) et `z` (`if z < 0 or z > 22`) mais **jamais `x`/`y`** ; `_construire_tuile` appelle `ST_TileEnvelope(:z, :x, :y)` → même exception non interceptée.
- **fichier:ligne** : `src/labuse/api/couches_tuyau.py:731-754` (gardes kind+z, pas x/y) → `src/labuse/api/couches_tuyau.py:646-647` (`ST_TileEnvelope(:z, :x, :y)` dans `_construire_tuile`, `couches_tuyau.py:606`).

> Note : les deux routes partagent la MÊME cause (bornage x/y absent avant `ST_TileEnvelope`). Un seul correctif conceptuel (valider `0 ≤ x,y < 2^z`, sinon 204) couvre les deux. Impact réel en prod faible (un client carto bien élevé ne demande jamais une tuile hors grille), mais un scanner / lien forgé / cache CDN mal configuré déclenche des 500 en série.

## Non vérifié
- **POST authentifiés** : `/parcels/{idu}/evaluate`, `/projets/*` (POST), `/scoreur-adresse`, `/ia/*`, `/partners/*`, `/moteurs/assemblage` — exigent une session/tenant et/ou des corps JSON structurés ; non sondés en fuzzing pour rester en lecture seule et ne pas muter d'état (évaluate relance une cascade). Risque de robustesse sur corps JSON malformés non couvert.
- **Concurrence / pool** : le 500 tuile a été prouvé en requête isolée + reproduction SQL de `ST_TileEnvelope`, mais l'effet sous charge (fuite de session / « idle in transaction », cf. TUILES-TX-1) n'a PAS été rejoué — `api_session()` est ouvert en `with`, donc le `finally` devrait fermer même sur exception ; à confirmer si besoin.
- **Rate-limiter** : le défi anti-abus (`/protection/defi`, 60 req/min) s'est déclenché pendant la batterie ; quelques variantes « source bidon » ont d'abord renvoyé le challenge (200 avec `detail`), re-tirées après pause → `[]` vide confirmé. Les séries longues d'un même chemin peuvent donc être tronquées par le limiteur, ce qui est un comportement voulu, pas un écart.
- **PDF / exports binaires** (`/parcels/{idu}/export.pdf`, `/dossier-banquier/{idu}.pdf`, `.kmz`) : seul l'idu malformé a été testé (404) ; la génération sur idu valide + options extrêmes n'a pas été fuzzée.

## Gardes proposées
Deux gardes pour `scripts/coherence/chasse_invariants.py` — l'une par requêtes HTTP (robustesse vive), l'autre indépendante de l'API (SQL pur, rejouable sans serveur).

```python
import urllib.request

BASE = "http://127.0.0.1:8790"

def _code(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return "ERR"

def garde_tuiles_jamais_500():
    """INVARIANT I6 : une tuile MVT hors grille (x/y hors [0,2^z) ou négatif), sur les deux routes
    de tuiles, répond proprement (204/200/404) et JAMAIS 500. Un z hors plage rend déjà 204/404 ;
    x/y doivent suivre la même règle."""
    cas = [
        "/map/tiles/12/999999/999999.pbf",   # x+y hors
        "/map/tiles/12/999999/2110.pbf",     # x seul hors
        "/map/tiles/12/-5/-5.pbf",           # x/y négatifs
        "/map/tiles/14/999999/999999.pbf",
        "/map/tiles/zfang/12/999999/999999.pbf",  # route couche (kind déclaré)
        "/map/tiles/zfang/12/-5/-5.pbf",
    ]
    mauvais = [(p, _code(p)) for p in cas if _code(p) == 500 or _code(p) == "ERR"]
    if mauvais:
        print(f"[ECART] tuile MVT hors grille → 500 : {mauvais}")
        return False
    print(f"[OK] {len(cas)} tuiles hors grille servies proprement (jamais 500)")
    return True

def garde_tileenvelope_bornes(db):
    """Second calcul indépendant de l'API : prouve que ST_TileEnvelope lève dès que x|y sort de
    [0,2^z). La route DOIT donc border x/y en amont (sinon 500). Ici on vérifie que la borne
    théorique vaut bien 2^z et on documente la plage servie z8-15 / z0-22 (couches)."""
    import psycopg
    for z, x, y, doit_lever in [(12, 0, 0, False), (12, 4095, 4095, False),
                                (12, 4096, 0, True), (12, -1, 0, True)]:
        leve = False
        try:
            db.execute("SELECT ST_TileEnvelope(%s,%s,%s)", (z, x, y))
            db.fetchone()
        except psycopg.Error:
            leve = True
            db.connection.rollback()
        if leve != doit_lever:
            print(f"[ECART] ST_TileEnvelope({z},{x},{y}) lève={leve}, attendu {doit_lever}")
            return False
    print("[OK] ST_TileEnvelope borne x/y à [0,2^z) — la route doit border en amont")
    return True
```

```sql
-- INVARIANT I3/I7 (SQL pur, sans API) : la table servie ne porte aucun chiffre impossible —
-- surfaces, SDP et comptes jamais négatifs. (0 attendu ; une ligne = ECART FAUX-CLIENT.)
SET statement_timeout='120s';
SELECT count(*) AS violations
FROM parcels p
LEFT JOIN parcel_residuel r ON r.idu = p.idu
WHERE COALESCE(p.contenance_m2, 0) < 0
   OR COALESCE(r.sdp_residuelle, 0) < 0
   OR COALESCE(r.sdp_max, 0) < 0;
-- Résultat observé pendant l'audit : 0 (via les réponses /parcels, /filtre, /stats — aucun négatif).
```

### Bilan chiffré de la batterie (rejouable : `/tmp/battery.py`)
`requêtes=59 · http500=2 · affichages_sales=0 · négatifs_impossibles=0`
(2 « ERR » supplémentaires dans la sortie brute = erreurs **client urllib** sur espaces non-encodés dans l'URL, PAS des réponses serveur ; re-testés URL-encodés → 404/200 propres.)
