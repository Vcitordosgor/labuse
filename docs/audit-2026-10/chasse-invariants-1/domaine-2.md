# Domaine 2 — Zonage et règles PLU

## Verdict (3 lignes)
434 582 parcelles au crible (427 419 zonées dans `parcel_zone_plu`, 1 ligne/idu, 0 NULL) ; 7 invariants vérifiés. **2 violations** : (A) **2 901 parcelles intersectent une zone PLU GPU mais n'ont AUCUNE ligne dans `parcel_zone_plu`** → la fiche sert la zone + la capacité (lecture live `spatial_layers`), la carte/filtres/liste/garde la voient sans zone (table dérivée PÉRIMÉE) ; dont **1 380 servent une SDP positive sans zone à la carte**. (B) rien d'autre : non-validées, bornes de gabarit, bizone, RNU Saint-Philippe — tout tient.
Resté muet : l'invariant « A/N dominant + SDP positive » vérifié sur **échantillon 400/4 127** (0 fuite) et non île-entière (coût spatial).

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| I1 | `parcel_zone_plu` porte exactement UNE zone par idu, sans champ NULL (pas de double-comptage, pas de zone vide servie). | SQL ci-dessous (coverage) | 434 582 (427 419 zonées) | 0 (PK idu, 0 NULL sur zone_lib/fam/filtre) |
| I2 | La zone servie à la fiche = la zone de la carte (les deux lisent `parcel_zone_plu`, dominante par surface ; ni l'une ni l'autre n'est « la zone au centroïde »). | lecture code `tiles.build_parcel_zone_plu` + `faisabilite/zone_servie.py` + `api/app.py:3356/3649` | source unique confirmée | 0 (invariant tenu par construction — voir §Non vérifié pour la nuance centroïde) |
| I3 | Saint-Philippe (commune au RNU) : aucune règle PLU de zone U/AU servie. | SQL ci-dessous (RNU) | 4 180 (commune) | 0 (9 parcelles zonées, toutes N par débord d'un GPU voisin ; 0 U/AU) |
| I4 | Les parts de zone d'une parcelle bizone ne somment JAMAIS > 100 % (pas de double-comptage) ; `pct_constructible` = somme bornée des parts U/AU. | SQL ci-dessous (parts) sur échantillon 0,3 % (coût spatial) | 1 404 échantillonnées | 0 (max couverture = 100,00 % ; sous-100 % = débord hors zonage, attendu) |
| I5 | Aucune règle PLU non validée (`statut != 'valide'`) n'alimente un chiffre SDP servi ; une feuille `propose` chiffrée rend la zone « non calculable », jamais une valeur par défaut. | script Python ci-dessous (scan 2 071 zones calibrées + `resolve_zone`) | 2 071 zones · 9 communes à feuilles `propose` | 0 (0 feuille `propose` porte une valeur SDP numérique dans q_v18 ; code double-garde) |
| I6 | Hauteur/niveaux/emprise d'une zone restent DANS le gabarit : emprise ∈ [0;100] %, `niveaux_max` loge sous le faîtage, aucune valeur servie négative ; `zone_fam` colle au préfixe de `zone_lib`. | script Python (bornes) + SQL (fam↔lib) | 2 071 zones + 427 419 parcelles | 0 (0 emprise HS, 0 niveaux>faîtage, 0 négatif, 0 fam/lib désaccord) |
| I7 | Toute parcelle servie avec une SDP résiduelle positive a une zone PLU reconnue (pas de zone vide alimentant un calcul) ; une SDP sur zone dominante A/N n'existe que si une portion U/AU réelle la justifie. | SQL ci-dessous (SDP>0 ⋈ zone) + échantillon 400 | 193 394 (SDP>0) | **1 380** sans aucune zone à la carte · 4 127 A/N-dominant (échantillon 400 : 0 fuite) |

### Requêtes rejouables

```sql
SET statement_timeout='120s';
-- I1
SELECT (SELECT count(*) FROM parcels) parcels,
 (SELECT count(DISTINCT idu) FROM parcel_zone_plu) pzp_idu,
 (SELECT count(*) FROM parcel_zone_plu WHERE zone_lib IS NULL) lib_null,
 (SELECT count(*) FROM parcel_zone_plu WHERE zone_fam IS NULL) fam_null;

-- I3 (RNU Saint-Philippe)
SELECT p.commune, count(*) n, count(zp.idu) zoned,
  count(*) FILTER (WHERE zp.zone_fam IN ('U','AU')) uau
FROM parcels p LEFT JOIN parcel_zone_plu zp ON zp.idu=p.idu
WHERE p.commune='Saint-Philippe' GROUP BY 1;

-- I4 (parts jamais > 100 %, échantillon)
WITH z0 AS (SELECT ST_MakeValid(geom_2975) g FROM spatial_layers WHERE kind='plu_gpu_zone'),
samp AS (SELECT p.geom_2975 g, ST_Area(p.geom_2975) a FROM parcels p TABLESAMPLE SYSTEM (0.3)
         JOIN parcel_zone_plu zp ON zp.idu=p.idu),
parts AS (SELECT s.a, sum(ST_Area(ST_Intersection(z0.g,s.g))) covered
          FROM samp s JOIN z0 ON s.g && z0.g AND ST_Intersects(z0.g,s.g) GROUP BY s.a)
SELECT count(*) sampled, count(*) FILTER (WHERE covered > a*1.005) over_100 FROM parts;

-- I6 (fam ↔ lib)
SELECT count(*) FILTER (WHERE
  (zone_fam='U'  AND zone_lib !~* '^[0-9]*U') OR (zone_fam='AU' AND zone_lib !~* '^[0-9]*AU') OR
  (zone_fam='A'  AND zone_lib !~* '^A')        OR (zone_fam='N'  AND zone_lib !~* '^N')) fam_lib_mismatch
FROM parcel_zone_plu;

-- I7a (SDP>0 sans aucune zone à la carte)
SELECT count(*) served_sdp, count(*) FILTER (WHERE zp.idu IS NULL) no_zone_row
FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
LEFT JOIN parcel_zone_plu zp ON zp.idu=p.idu WHERE r.sdp_residuelle_m2>0;

-- VIOLATION A (périmètre) : parcelles sans ligne pzp mais intersectant une zone GPU
WITH missing AS (SELECT p.id, p.idu, p.geom_2975 g FROM parcels p
  WHERE NOT EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu=p.idu))
SELECT count(*) missing_total,
  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_zone'
    AND z.geom_2975 && m.g AND ST_Intersects(ST_MakeValid(z.geom_2975), m.g))) missing_but_intersects_gpu
FROM missing m;   -- → 7163 total ; 2901 intersectent pourtant une zone
```

```python
# I5 + I6 (script) — PYTHONPATH=src, .venv labuse
from labuse.plu import destinations as D
from labuse.faisabilite.zonage import resolve_zone
import glob, os, re
SDP=[("hauteur","faitage","m","hf_m"),("hauteur","egout","m","he_m"),
     ("emprise_sol","ces","pct","emprise_sol_pct"),("retraits","voie","min_m","recul_voirie_m"),
     ("retraits","limites_separatives","min_m","recul_limites_sep_m"),("pleine_terre","pct","pct","pleine_terre_pct")]
leaks=[]
for f in glob.glob("config/plu_destinations/*.yaml"):
    ins=os.path.basename(f)[:5]
    if not re.fullmatch(r"974\d\d",ins): continue
    for r in D.regles_commune(ins):
        zone=r["zone"]; reg=D.regles_zone(ins,zone); zr=resolve_zone(zone,ins)
        for rub,feu,cle,champ in SDP:
            leaf=(reg.get(rub) or {}).get(feu) if isinstance(reg.get(rub),dict) else None
            if (isinstance(leaf,dict) and leaf.get("statut")=="propose"
                and isinstance(leaf.get(cle),(int,float)) and not leaf.get("absent") and not leaf.get("plage")):
                served=getattr(zr,champ,None) if zr else None
                if isinstance(served,(int,float)) and abs(float(served)-float(leaf[cle]))<1e-6:
                    leaks.append((ins,zone,champ))
print("leaks (propose numeric == served):", len(leaks))   # → 0
```

## Violations

### A — `parcel_zone_plu` PÉRIMÉE : 2 901 parcelles zonables sans zone à la carte (dont 1 380 à SDP positive)
- **Gravité : INCOHERENT (→ FAUX-CLIENT sur 1 380)**. Deux lecteurs se contredisent sur la MÊME parcelle : la fiche (live) sert une zone U/AU + une capacité ; la carte/filtres/liste/`zone_dominante` (table dérivée) la voient zone-less.
- **idu témoin** : `97401000AH0371` (Les Avirons) — la fiche sert `reglement_plu.zones[0].zone = "Ud1"` + `sdp_residuelle_m2 = 1907` ; `SELECT * FROM parcel_zone_plu WHERE idu='97401000AH0371'` → **0 ligne**, alors que la parcelle intersecte la zone Ud1 sur **4 447 m²** (`ST_Intersects = true`, `bbox && = true`). Idem sur toute l'île : 468 à Saint-Paul, 419 à Saint-Benoît, 229 à Saint-Pierre, etc. (réparties partout).
- **Attendu** : toute parcelle intersectant une zone `plu_gpu_zone` a une ligne `parcel_zone_plu` (zone dominante) — la carte la colore, les filtres la captent, la fiche et la carte s'accordent.
- **Obtenu** : 7 163 parcelles sans ligne `parcel_zone_plu`, dont **2 901 intersectent pourtant une zone GPU** (devraient en avoir une) ; 1 380 d'entre elles servent une SDP positive (jusqu'à 1 907 m²).
- **Cause probable** : `parcel_zone_plu` est une table dérivée STATIQUE, bâtie une fois (`build_parcel_zone_plu`, commentaire tiles.py:148-149 « construit une seule fois (long) puis réutilisé tel quel à chaque rebuild — le zonage ne bouge pas avec les runs ») et jamais reconstruite par `build_mvt_table` tant qu'elle existe et n'est pas vide (`tiles.py:153-155` ne relance le build que si la table est ABSENTE ou VIDE). Les parcelles nées/re-géométrisées depuis le dernier build, et l'extension de couverture `spatial_layers` depuis, ne sont jamais rattrapées → dérive silencieuse `parcels`/`spatial_layers` ↔ `parcel_zone_plu`.
- **fichier:ligne** : `src/labuse/api/tiles.py:40-107` (`build_parcel_zone_plu`, SQL de construction) ; `src/labuse/api/tiles.py:148-155` (condition de reconstruction trop faible : « absente OU vide », jamais « périmée »).

### (classé, NON-violation) A/N dominant + SDP positive — 4 127 parcelles
- Observé : 4 127 parcelles de zone dominante A/N stockent une SDP positive dans `parcel_residuel` (ex. `97411000EH0044`, dominant N, fiche `sdp_residuelle_m2 = 152 518`, `cause = None`).
- Ce N'EST PAS une fuite : décision Vic 24/09/2026 (`api/app.py:6192-6194`, garde « dominante A/N → 0 » RETIRÉE) — l'assiette du run est déjà CLIPPÉE à la portion U/AU des parcelles à cheval. Témoin : `97411000EH0044` est 64 % N (dominant) mais 35 % AU (AUh 17,7 % + AUm 17,4 %) → la SDP porte sur les ~169 000 m² réellement AU. Échantillon aléatoire 400/4 127 : **0 parcelle A/N-dominant à SDP positive SANS portion U/AU**. Invariant I7 (volet A/N) tenu sur l'échantillon.

## Non vérifié
- **I7, volet A/N sur l'île entière** : « SDP positive sur zone A/N ⇒ portion U/AU réelle » testé sur un échantillon ALÉATOIRE de 400/4 127 (0 fuite) — le join spatial île-entière dépasse `statement_timeout=120s`. À dérouler par commune pour une preuve exhaustive.
- **I2, nuance « au centroïde »** : la carte NE colore PAS par point-au-centroïde mais par la même dominante-surface que la fiche (source unique `parcel_zone_plu` / build dominant par `ST_Area(ST_Intersection) DESC`) — donc fiche = carte par construction. Mesuré à part : sur 8 896 parcelles échantillonnées, **127 (1,4 %) ont une dominante-surface dont le point-sur-surface tombe dans une AUTRE zone**, et ~2 400 île-entière (extrapolé 8 % : 97 U/AU→point A/N, 100 A/N→point U/AU). Ce n'est pas une violation de l'invariant servi (choix DOCUMENTÉ `zone_servie.py:1-15` : dominante-surface, pas centroïde), mais un angle mort réglementaire possible si l'utilisateur « clique sur le point ». Signalé, non compté en violation.
- **I4 parts** sur 0,3 % (coût spatial) ; max couverture 100,00 % sur l'échantillon → extrapolable, mais non prouvé île-entière.

## Gardes proposées

```python
# scripts/coherence/chasse_invariants.py — domaine 2 (zonage PLU). Lecture seule.
from sqlalchemy import text

def inv_pzp_non_perimee(db):
    """[A] Toute parcelle intersectant une zone GPU a une ligne parcel_zone_plu
    (carte/filtres = fiche). ECART = parcelle zonable sans ligne dérivée."""
    n = db.execute(text("""
        WITH missing AS (SELECT p.geom_2975 g FROM parcels p
          WHERE NOT EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu=p.idu))
        SELECT count(*) FROM missing m WHERE EXISTS (
          SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_zone'
            AND z.geom_2975 && m.g AND ST_Intersects(ST_MakeValid(z.geom_2975), m.g))
    """)).scalar() or 0
    return ("OK", "0 parcelle zonable orpheline de parcel_zone_plu") if n == 0 \
        else ("ECART", f"{n} parcelles intersectent une zone GPU sans ligne parcel_zone_plu "
                       "(table dérivée périmée — carte/filtres contredisent la fiche)")

def inv_sdp_sans_zone(db):
    """[A, volet client] Aucune SDP résiduelle positive servie sur une parcelle sans
    zone reconnue à la carte."""
    n = db.execute(text("""
        SELECT count(*) FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
        LEFT JOIN parcel_zone_plu zp ON zp.idu=p.idu
        WHERE r.sdp_residuelle_m2>0 AND zp.idu IS NULL
          AND EXISTS (SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_zone'
            AND z.geom_2975 && p.geom_2975 AND ST_Intersects(ST_MakeValid(z.geom_2975), p.geom_2975))
    """)).scalar() or 0
    return ("OK", "0 SDP positive sans zone à la carte") if n == 0 \
        else ("ECART", f"{n} parcelles servent une SDP positive alors que la carte les voit sans zone PLU")

def inv_rnu_saint_philippe(db):
    """[I3] Saint-Philippe (RNU) : aucune zone U/AU PLU servie."""
    n = db.execute(text("""
        SELECT count(*) FROM parcels p JOIN parcel_zone_plu zp ON zp.idu=p.idu
        WHERE p.commune='Saint-Philippe' AND zp.zone_fam IN ('U','AU')""")).scalar() or 0
    return ("OK", "Saint-Philippe : 0 zone U/AU PLU servie (RNU)") if n == 0 \
        else ("ECART", f"Saint-Philippe (RNU) sert {n} parcelles en zone U/AU PLU")

def inv_fam_colle_lib(db):
    """[I6] zone_fam cohérent avec le préfixe de zone_lib (pas de famille inventée)."""
    n = db.execute(text("""
        SELECT count(*) FROM parcel_zone_plu WHERE
          (zone_fam='U'  AND zone_lib !~* '^[0-9]*U') OR (zone_fam='AU' AND zone_lib !~* '^[0-9]*AU') OR
          (zone_fam='A'  AND zone_lib !~* '^A')        OR (zone_fam='N'  AND zone_lib !~* '^N')
    """)).scalar() or 0
    return ("OK", "zone_fam colle à zone_lib partout") if n == 0 \
        else ("ECART", f"{n} parcelles ont zone_fam en désaccord avec le préfixe de zone_lib")

def inv_parts_jamais_sur_100(db):
    """[I4] Les parts de zone d'une parcelle ne somment jamais > 100 % (échantillon spatial)."""
    n = db.execute(text("""
        WITH z0 AS (SELECT ST_MakeValid(geom_2975) g FROM spatial_layers WHERE kind='plu_gpu_zone'),
        samp AS (SELECT p.geom_2975 g, ST_Area(p.geom_2975) a FROM parcels p TABLESAMPLE SYSTEM (0.3)
                 JOIN parcel_zone_plu zp ON zp.idu=p.idu),
        parts AS (SELECT s.a, sum(ST_Area(ST_Intersection(z0.g,s.g))) covered
                  FROM samp s JOIN z0 ON s.g && z0.g AND ST_Intersects(z0.g,s.g) GROUP BY s.a)
        SELECT count(*) FROM parts WHERE covered > a*1.005
    """)).scalar() or 0
    return ("OK", "aucune parcelle ne somme >100 % (échantillon 0,3 %)") if n == 0 \
        else ("ECART", f"{n} parcelles (échantillon) somment >100 % — double comptage de zone")

def inv_non_validee_ne_sert_pas(_db=None):
    """[I5] Aucune feuille PLU `propose` chiffrée n'alimente une valeur SDP servie
    (vérifié par resolve_zone sur toutes les zones calibrées — indépendant de la base runtime)."""
    from labuse.plu import destinations as D
    from labuse.faisabilite.zonage import resolve_zone
    import glob, os, re
    SDP=[("hauteur","faitage","m","hf_m"),("hauteur","egout","m","he_m"),
         ("emprise_sol","ces","pct","emprise_sol_pct"),("retraits","voie","min_m","recul_voirie_m"),
         ("retraits","limites_separatives","min_m","recul_limites_sep_m"),("pleine_terre","pct","pct","pleine_terre_pct")]
    leaks=0
    for f in glob.glob("config/plu_destinations/*.yaml"):
        ins=os.path.basename(f)[:5]
        if not re.fullmatch(r"974\d\d",ins): continue
        for r in D.regles_commune(ins):
            reg=D.regles_zone(ins,r["zone"]); zr=resolve_zone(r["zone"],ins)
            for rub,feu,cle,champ in SDP:
                leaf=(reg.get(rub) or {}).get(feu) if isinstance(reg.get(rub),dict) else None
                if (isinstance(leaf,dict) and leaf.get("statut")=="propose"
                    and isinstance(leaf.get(cle),(int,float)) and not leaf.get("absent") and not leaf.get("plage")):
                    s=getattr(zr,champ,None) if zr else None
                    if isinstance(s,(int,float)) and abs(float(s)-float(leaf[cle]))<1e-6: leaks+=1
    return ("OK", "aucune règle PLU non validée ne sert de valeur SDP") if leaks==0 \
        else ("ECART", f"{leaks} valeurs SDP servies proviennent d'une feuille `propose` non validée")

# exit 1 si une garde rend ECART.
```
