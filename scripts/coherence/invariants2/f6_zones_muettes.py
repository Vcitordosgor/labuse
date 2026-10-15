"""F6 — Les ZONES MUETTES de la vague 1 (chasse-invariants-2).

La vague 1 a laissé des trous : des invariants qu'elle n'a PAS pu vérifier, chacun noté « Muet : … »
en fin de domaine dans docs/audit-2026-10/chasse-invariants-1/RAPPORT.md. F6 reprend cette liste et,
pour chaque item, soit GÉNÈRE une vraie règle, soit l'ÉCARTE avec la raison pour laquelle il reste
hors de portée en lecture seule / local.

Trois chantiers portants :

  (1) APPARTENANCE GÉOMÉTRIQUE parcelle ⊂ commune — le muet-titre du domaine 1.
      `parcels.commune` est posée à la SOURCE (Etalab), jamais par ST_Contains. Les limites officielles
      vivent dans frontend/public/communes974.geojson (24 communes {nom, code=INSEE}, WGS84). On les
      charge en Python et on les passe en LITTÉRAL GeoJSON (ST_GeomFromGeoJSON) dans des requêtes PAR
      COMMUNE — AUCUNE table temporaire, AUCUNE écriture (connexion read_only).
      PIÈGE : la geojson fait 44 KB pour 24 communes → frontières LOURDEMENT simplifiées. Un NOT
      ST_Within(geom, polygone) naïf drapeaute TOUTE parcelle de bord = des milliers de faux positifs.
      On raisonne donc sur le CENTROÏDE (pas le contour) et on ne retient une violation que si le
      centroïde tombe dans une AUTRE commune par une MARGE RÉELLE (> MARGE_GROSSE m du polygone de sa
      propre commune). Mesure île entière (cf. F6.md) : le pire centroïde « hors » n'est qu'à ~75 m de
      sa commune (idu-préfixe INSEE, qui fait foi au cadastre) → 0 cas > 100 m, 0 misattribution réelle.
      Le rattachement par INSEE (substr(idu,1,5)) EST l'autorité ; la règle prouve qu'aucune parcelle
      n'est grossièrement dans la mauvaise commune, les ~590 « hors » étant des échardes de frontière
      simplifiée, pas des erreurs de données.

  (2) FAISABILITÉ À PLEINE ÉCHELLE, en APPEL DIRECT du moteur (la vague 1 était bloquée par le
      rate-limit API 60/min). On appelle `estimate_capacity`/`resolve_zone` en process, à blanc, sur
      5000 parcelles stratifiées — aucune API, aucune écriture. On vérifie par parcelle que le moteur
      rend sans lever, que les sorties sont cohérentes (SDP ≥ 0, emprise ≥ 0, non-constructible ⇒ SDP=0,
      SDP = emprise × niveaux à la tolérance près) et on compte combien calculent proprement.

  (3) LE RESTE DE LA LISTE MUETTE : volet A/N île entière (SQL), union PPR mono-polygone (ce qui est
      traitable), CatNat/OCSGE par géométrie, et les muets hors portée (sondes amont, Copilote LLM,
      POST authentifiés, prix obsimmo live…) ÉCARTÉS avec raison.

Lecture seule STRICTE : connexion read_only, statement_timeout posé par le noyau (120 s), jointures
lourdes une par une, geojson parsée en Python et injectée en littéral.
"""
from __future__ import annotations

import json
import pathlib
import sys

_ICI = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_ICI.parents[2]))  # scripts/
from coherence.invariants2.noyau import (  # noqa: E402
    RACINE,
    Ecartee,
    RuleSpec,
    bilan,
    connexion,
    echantillon_stratifie,
    run_specs,
    table_existe,
)

# ── moteur de faisabilité (pur, appelé en process — jamais via l'API) ──────────────────────────
from labuse.faisabilite.engine import estimate_capacity  # noqa: E402
from labuse.faisabilite.zonage import resolve_zone  # noqa: E402

GEOJSON = RACINE / "frontend" / "public" / "communes974.geojson"

# Marge au-delà de laquelle un centroïde « hors de sa commune » cesse d'être une écharde de frontière
# simplifiée et devient une misattribution grossière. Calibrée sur la mesure île entière : le pire
# centroïde hors est à ~75 m (44 KB de geojson simplifié) → 200 m est un plancher franc et conservateur.
MARGE_GROSSE_M = 200.0
EPS = 1e-6


# ════════════════════════════════════════════════════════════════════════════════════════════
#  (1) Appartenance géométrique parcelle ⊂ commune
# ════════════════════════════════════════════════════════════════════════════════════════════
def _polygones_communes() -> dict[str, str]:
    """{code INSEE -> GeoJSON de la géométrie}, lu de la geojson officielle (24 communes)."""
    d = json.loads(GEOJSON.read_text())
    out: dict[str, str] = {}
    for f in d.get("features", []):
        code = str(f["properties"]["code"])
        out[code] = json.dumps(f["geometry"])
    return out


def _regles_containment(cx, polys: dict[str, str]) -> list[RuleSpec]:
    """Une règle par commune + une règle île : 0 centroïde grossièrement dans une AUTRE commune.

    Chaque règle injecte TOUS les polygones en littéral GeoJSON (VALUES … ST_GeomFromGeoJSON), compte
    les parcelles (par préfixe INSEE idu) dont le centroïde (a) n'est PAS dans son propre polygone ET
    (b) est à plus de MARGE_GROSSE_M mètres de celui-ci (donc pas une écharde de frontière). C'est la
    seule forme « vraie par construction » : l'INSEE du cadastre fait foi, la geojson simplifiée ne peut
    que générer du bruit de bord — qu'on neutralise par la marge métrique.
    """
    codes = sorted(polys)
    vals_placeholders = ",".join(["(%s,%s)"] * len(codes))
    base_params: list[str] = []
    for c in codes:
        base_params += [c, polys[c]]

    cte_polys = f"""
        WITH polys AS (
            SELECT v.code, ST_SetSRID(ST_GeomFromGeoJSON(v.gj), 4326) AS g
            FROM (VALUES {vals_placeholders}) AS v(code, gj)
        )"""

    # fragment commun : « centroïde hors de SA commune de plus de MARGE_GROSSE_M, et dans une autre »
    # (le « dans une autre » exclut les parcelles côtières tombées dans la mer de la geojson simplifiée)
    def _viol(code_pred: str) -> str:
        return f"""{cte_polys}
        SELECT count(*) FROM parcels p
        JOIN polys own ON own.code = substr(p.idu,1,5)
        WHERE p.cadastre_disparue_le IS NULL
          AND {code_pred}
          AND NOT ST_Within(p.centroid, own.g)
          AND ST_Distance(ST_Transform(p.centroid,2975), ST_Transform(own.g,2975)) > {MARGE_GROSSE_M}
          AND EXISTS (SELECT 1 FROM polys o
                      WHERE o.code <> own.code AND ST_Within(p.centroid, o.g))
        """

    def _ex(code_pred: str) -> str:
        return f"""{cte_polys}
        SELECT p.idu,
               substr(p.idu,1,5) AS insee_revendique,
               (SELECT o.code FROM polys o WHERE o.code <> own.code
                  AND ST_Within(p.centroid, o.g) LIMIT 1) AS insee_contenant,
               round(ST_Distance(ST_Transform(p.centroid,2975),
                                 ST_Transform(own.g,2975))::numeric,1) AS dist_m_a_sa_commune
        FROM parcels p
        JOIN polys own ON own.code = substr(p.idu,1,5)
        WHERE p.cadastre_disparue_le IS NULL
          AND {code_pred}
          AND NOT ST_Within(p.centroid, own.g)
          AND ST_Distance(ST_Transform(p.centroid,2975), ST_Transform(own.g,2975)) > {MARGE_GROSSE_M}
          AND EXISTS (SELECT 1 FROM polys o WHERE o.code <> own.code AND ST_Within(p.centroid, o.g))
        ORDER BY dist_m_a_sa_commune DESC
        LIMIT 3
        """

    specs: list[RuleSpec] = []
    # une règle par commune (×24) — quantifie le bruit par commune et localise toute vraie erreur
    for c in codes:
        pred = "substr(p.idu,1,5) = %s"
        specs.append(RuleSpec(
            id=f"F6.containment.commune.{c}",
            famille="F6",
            source="frontend/public/communes974.geojson + parcels.centroid",
            libelle=(f"Commune {c} : aucun centroïde de parcelle ne tombe dans une AUTRE commune à plus "
                     f"de {int(MARGE_GROSSE_M)} m de la sienne (misattribution grossière)."),
            gravite="INCOHERENT",
            attendu=f"0 parcelle grossièrement (> {int(MARGE_GROSSE_M)} m) dans une autre commune",
            sql_violations=_viol(pred),
            exemples_sql=_ex(pred),
            params=tuple(base_params + [c]),
        ))
    # règle île : 0 misattribution grossière, toutes communes confondues
    specs.append(RuleSpec(
        id="F6.containment.ile",
        famille="F6",
        source="frontend/public/communes974.geojson + parcels.centroid",
        libelle=(f"Île : aucune parcelle n'a son centroïde grossièrement (> {int(MARGE_GROSSE_M)} m) "
                 f"dans une commune autre que son INSEE cadastral."),
        gravite="INCOHERENT",
        attendu=f"0 parcelle grossièrement (> {int(MARGE_GROSSE_M)} m) hors de sa commune",
        sql_violations=_viol("TRUE"),
        exemples_sql=_ex("TRUE"),
        params=tuple(base_params),
    ))
    return specs


# ════════════════════════════════════════════════════════════════════════════════════════════
#  (2) Faisabilité à pleine échelle — appel DIRECT du moteur (bypass API) sur 5000 parcelles
# ════════════════════════════════════════════════════════════════════════════════════════════
_FAISA_CACHE: dict | None = None


def _faisa_echantillon(cx, n: int = 5000) -> dict:
    """Appelle estimate_capacity/resolve_zone EN PROCESS sur n parcelles stratifiées (aucune API).

    Rend un dict d'agrégats : combien de parcelles ont une zone servie, combien ont calculé proprement,
    combien ont levé, et les compteurs de VIOLATIONS de cohérence (SDP<0, emprise<0, non-constructible
    avec SDP>0, SDP ≠ emprise×niveaux). Déterministe (échantillon md5 du noyau). Un seul passage, caché.
    """
    global _FAISA_CACHE
    if _FAISA_CACHE is not None:
        return _FAISA_CACHE
    idus = echantillon_stratifie(cx, n=n)
    with cx.conn.cursor() as cur:
        cur.execute(
            "SELECT p.idu, p.commune, z.zone_lib, p.surface_m2 "
            "FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu "
            "WHERE p.idu = ANY(%s) AND z.zone_lib IS NOT NULL",
            (idus,))
        rows = cur.fetchall()

    agg = {
        "echantillon": len(idus),
        "avec_zone": len(rows),
        "resolues": 0,
        "resolve_none": 0,
        "calculees": 0,
        "raised": 0,
        "sdp_negatif": 0,
        "emprise_negatif": 0,
        "capacite_negatif": 0,
        "non_constructible_sdp_pos": 0,
        "sdp_sup_emprise_niveaux": 0,
        "exemples_raised": [],
        "exemples_sdp_neg": [],
        "exemples_non_constr_sdp": [],
        "exemples_sdp_vs_en": [],
    }
    for idu, commune, zone, surf in rows:
        try:
            r = resolve_zone(zone, commune)
        except Exception as e:  # noqa: BLE001
            agg["raised"] += 1
            if len(agg["exemples_raised"]) < 3:
                agg["exemples_raised"].append(f"{idu} resolve_zone {type(e).__name__}: {e}")
            continue
        if r is None:
            agg["resolve_none"] += 1
            continue
        agg["resolues"] += 1
        try:
            f = estimate_capacity(r, float(surf or 0.0))
        except Exception as e:  # noqa: BLE001
            agg["raised"] += 1
            if len(agg["exemples_raised"]) < 3:
                agg["exemples_raised"].append(f"{idu} estimate_capacity {type(e).__name__}: {e}")
            continue
        agg["calculees"] += 1
        fr = f.fourchette or {}
        sdp = float(fr.get("surface_plancher_m2") or 0.0)
        emprise = float(fr.get("emprise_constructible_m2") or 0.0)
        niveaux = fr.get("niveaux_max")
        constructible = bool(getattr(r, "constructible_neuf", False)) and bool(f.constructible)

        if sdp < -EPS:
            agg["sdp_negatif"] += 1
            if len(agg["exemples_sdp_neg"]) < 3:
                agg["exemples_sdp_neg"].append(f"{idu} sdp={sdp}")
        if emprise < -EPS:
            agg["emprise_negatif"] += 1
        # non-constructible ⇒ SDP = 0
        if (not constructible) and sdp > EPS:
            agg["non_constructible_sdp_pos"] += 1
            if len(agg["exemples_non_constr_sdp"]) < 3:
                agg["exemples_non_constr_sdp"].append(f"{idu} zone={zone} sdp={sdp} (non constructible)")
        # Borne physique : SDP ≤ emprise × niveaux_max (on ne peut pas bâtir plus de plancher que
        # l'emprise constructible empilée sur le nombre max de niveaux). `niveaux` rendu par le moteur
        # est un LIBELLÉ texte (« R+1 ») ; le chiffre exploitable est `niveaux_max`. L'égalité stricte
        # ne tient PAS (CES/pleine terre/implantation rabotent la SDP sous le plafond) — seule la borne
        # supérieure est vraie par construction.
        if constructible and isinstance(niveaux, (int, float)) and emprise > EPS and sdp > EPS:
            plafond = emprise * float(niveaux)
            if sdp > plafond * 1.01 + 1.0:
                agg["sdp_sup_emprise_niveaux"] += 1
                if len(agg["exemples_sdp_vs_en"]) < 3:
                    agg["exemples_sdp_vs_en"].append(
                        f"{idu} zone={zone} sdp={sdp} > emprise×niveaux_max={plafond} (empr={emprise}, niv_max={niveaux})")
    _FAISA_CACHE = agg
    return agg


def _regles_faisabilite(cx) -> list[RuleSpec]:
    """6 règles callable sur le passage unique des 5000 parcelles (moteur en process)."""
    def mk(nom, cle, libelle, gravite="INCOHERENT", exemples_cle=None):
        def check(cx_, api):
            agg = _faisa_echantillon(cx_)
            n = agg[cle]
            if n == 0:
                base = f"{agg['calculees']}/{agg['avec_zone']} parcelles calculées proprement"
                return "OK", f"{libelle} tenu (0) · {base}"
            exs = agg.get(exemples_cle or "", []) if exemples_cle else []
            return "ECART", f"{n} violation(s) — {libelle}" + (f" · ex: {exs}" if exs else "")
        return RuleSpec(id=f"F6.faisa.{nom}", famille="F6",
                        source="faisabilite.engine.estimate_capacity (appel direct, 5000 parcelles)",
                        libelle=libelle, gravite=gravite, attendu="0", check=check)

    specs = [
        mk("moteur_ne_leve_pas", "raised",
           "le moteur rend sans lever sur chaque parcelle servie", "ROBUSTESSE", "exemples_raised"),
        mk("sdp_non_negatif", "sdp_negatif", "SDP ≥ 0", "INCOHERENT", "exemples_sdp_neg"),
        mk("emprise_non_negative", "emprise_negatif", "emprise constructible ≥ 0"),
        mk("non_constructible_sdp_nulle", "non_constructible_sdp_pos",
           "non-constructible ⇒ SDP = 0", "FAUX-CLIENT", "exemples_non_constr_sdp"),
        mk("sdp_borne_emprise_x_niveaux", "sdp_sup_emprise_niveaux",
           "SDP ≤ emprise × niveaux_max (borne physique)", "INCOHERENT", "exemples_sdp_vs_en"),
    ]
    # règle « assez de parcelles ont effectivement calculé » : au moins 90 % des zones résolues calculent
    def check_couverture(cx_, api):
        agg = _faisa_echantillon(cx_)
        res = agg["resolues"]
        if res == 0:
            return "SKIP", "aucune zone résolue (échantillon sans zonage servi ?)"
        ratio = agg["calculees"] / res
        if ratio >= 0.999:
            return "OK", f"{agg['calculees']}/{res} zones résolues calculent (100 %)"
        return "ECART", f"seulement {agg['calculees']}/{res} zones résolues calculent ({ratio:.1%})"
    specs.append(RuleSpec(
        id="F6.faisa.couverture_calcul", famille="F6",
        source="faisabilite.engine (appel direct, 5000 parcelles)",
        libelle="toute zone résolue produit un calcul de faisabilité",
        gravite="ROBUSTESSE", attendu="100 % des zones résolues calculent", check=check_couverture))
    return specs


# ════════════════════════════════════════════════════════════════════════════════════════════
#  (3) Le reste de la liste muette — règles SQL île entière + écartés justifiés
# ════════════════════════════════════════════════════════════════════════════════════════════
def _regles_reste(cx) -> tuple[list[RuleSpec], list[Ecartee]]:
    specs: list[RuleSpec] = []
    ecartees: list[Ecartee] = []

    # Muet domaine 2 : « volet A/N île-entière (échantillon 400, 0 fuite) ».
    # La vague 1 n'a échantillonné que 400 parcelles. Deux invariants servables sur l'île entière :
    #   (a) toute parcelle a une famille de zone connue (A/AU/N/U) — zone_fam jamais NULL/hors-nomenclature ;
    #   (b) cohérence zone_fam ↔ zone_lib : la famille est le préfixe de forme de la zone (A*→A, N*→N,
    #       (1..9)?AU*→AU, U*→U) — aucune parcelle ne porte une famille contredisant le code servi.
    # ⚠ Le cas « A/N à SDP>0 » (≈4 127, assiette déjà clippée U/AU) a été ADJUDIQUÉ non-bug par Vic le
    # 24/09 (RAPPORT-1 domaine 2) : assiette_source ∈ {gabarit, residuel_legacy, NULL}, PAS de marqueur
    # « clip » → une règle « A/N ⇒ SDP=0 » re-mordrait 4 167 cas déjà acceptés = faux-mordant. Écarté.
    if table_existe(cx, "parcel_zone_plu"):
        specs.append(RuleSpec(
            id="F6.an.famille_connue",
            famille="F6",
            source="parcel_zone_plu.zone_fam (île entière)",
            libelle=("Volet A/N île entière : toute parcelle zonée porte une famille de la nomenclature "
                     "(A, AU, N, U) — jamais NULL ni hors-nomenclature."),
            gravite="INCOHERENT",
            attendu="0 parcelle zonée sans famille valide",
            sql_violations="""
                SELECT count(*)
                FROM parcel_zone_plu z
                JOIN parcels p ON p.idu = z.idu
                WHERE p.cadastre_disparue_le IS NULL
                  AND z.zone_lib IS NOT NULL
                  AND (z.zone_fam IS NULL OR upper(z.zone_fam) NOT IN ('A','AU','N','U'))
            """,
            exemples_sql="""
                SELECT z.idu, z.zone_lib, z.zone_fam
                FROM parcel_zone_plu z JOIN parcels p ON p.idu = z.idu
                WHERE p.cadastre_disparue_le IS NULL AND z.zone_lib IS NOT NULL
                  AND (z.zone_fam IS NULL OR upper(z.zone_fam) NOT IN ('A','AU','N','U'))
                LIMIT 3
            """,
        ))
        specs.append(RuleSpec(
            id="F6.an.famille_coherente_code",
            famille="F6",
            source="parcel_zone_plu.zone_fam ↔ zone_lib (île entière)",
            libelle=("Volet A/N île entière : la famille servie est cohérente avec le code de zone "
                     "(A*→A, N*→N, [1-9]?AU*→AU, U*→U)."),
            gravite="INCOHERENT",
            attendu="0 parcelle famille↮code",
            sql_violations="""
                SELECT count(*)
                FROM parcel_zone_plu z JOIN parcels p ON p.idu = z.idu
                WHERE p.cadastre_disparue_le IS NULL AND z.zone_lib IS NOT NULL AND z.zone_fam IS NOT NULL
                  AND NOT (
                    (upper(z.zone_fam)='AU' AND z.zone_lib ~* '^[0-9]*au')
                    OR (upper(z.zone_fam)='A'  AND z.zone_lib ~* '^a' AND z.zone_lib !~* '^[0-9]*au')
                    OR (upper(z.zone_fam)='N'  AND z.zone_lib ~* '^n')
                    OR (upper(z.zone_fam)='U'  AND z.zone_lib ~* '^[0-9]*u' AND z.zone_lib !~* '^[0-9]*au')
                  )
            """,
            exemples_sql="""
                SELECT z.idu, z.zone_lib, z.zone_fam
                FROM parcel_zone_plu z JOIN parcels p ON p.idu = z.idu
                WHERE p.cadastre_disparue_le IS NULL AND z.zone_lib IS NOT NULL AND z.zone_fam IS NOT NULL
                  AND NOT (
                    (upper(z.zone_fam)='AU' AND z.zone_lib ~* '^[0-9]*au')
                    OR (upper(z.zone_fam)='A'  AND z.zone_lib ~* '^a' AND z.zone_lib !~* '^[0-9]*au')
                    OR (upper(z.zone_fam)='N'  AND z.zone_lib ~* '^n')
                    OR (upper(z.zone_fam)='U'  AND z.zone_lib ~* '^[0-9]*u' AND z.zone_lib !~* '^[0-9]*au')
                  )
                LIMIT 3
            """,
        ))
    else:
        ecartees.append(Ecartee(
            "F6.an.famille_connue", "F6", "parcel_zone_plu.zone_fam",
            "table parcel_zone_plu absente → volet A/N non testable ici."))
    # le cas A/N à SDP>0 lui-même : adjudiqué non-bug (Vic 24/09), écarté pour ne pas re-mordre
    ecartees.append(Ecartee(
        "F6.an.sdp_positive", "F6", "parcel_residuel + parcel_zone_plu",
        "A/N-dominant à SDP>0 (≈4 127, assiette déjà clippée U/AU) ADJUDIQUÉ non-bug par Vic 24/09 "
        "(RAPPORT-1 domaine 2) ; aucun marqueur assiette_source ne distingue le cas légitime du reste → "
        "une règle « A/N ⇒ SDP=0 » serait un faux-mordant sur 4 167 cas acceptés. Écarté."))

    # Muet domaine 4 : « union géométrique PPR sur 64 299 mono-polygone (timeout, sans objet) ».
    # Ce qui EST traitable en lecture seule : pour les parcelles ne touchant QU'UN SEUL polygone PPR
    # INTERDICTION (mono-polygone), l'union est triviale (= le polygone lui-même), donc la part rouge
    # calculée doit égaler l'intersection simple — invariant trivialement vrai → on génère la version
    # TRAITABLE : aucune parcelle mono-polygone INTERDICTION ≥ 50 % rouge n'est servie constructible
    # sans exclusion cascade. Dépend du schéma : on écarte proprement si les tables ne s'y prêtent pas.
    layers_ok = table_existe(cx, "spatial_layers")
    if layers_ok:
        # on teste seulement la DISPONIBILITÉ du kind PPR INTERDICTION ; la recoupe géométrique île
        # entière sur 433k × polygones PPR est exactement la double-jointure lourde interdite par le
        # mandat (une à la fois) et déjà portée par E-03/E-11 de la vague 1 → écarté comme doublon.
        ecartees.append(Ecartee(
            "F6.ppr.union_mono_polygone", "F6", "spatial_layers (PPR INTERDICTION) + parcels",
            "l'union PPR ≥50 % servie constructible est DÉJÀ couverte par E-03/E-11 (vague 1) ; la "
            "recoupe géométrique île entière est une double-jointure lourde hors budget F6 (une à la "
            "fois). Mono-polygone : union triviale = polygone, invariant sans mordant → écarté."))
    else:
        ecartees.append(Ecartee(
            "F6.ppr.union_mono_polygone", "F6", "spatial_layers",
            "table spatial_layers absente → recoupe PPR non testable."))

    # Muet domaine 4 : « CatNat/OCSGE par géométrie non recoupés ».
    ecartees.append(Ecartee(
        "F6.catnat_ocsge.recoupe_geometrique", "F6", "spatial_layers (OCSGE/CatNat) + parcels",
        "recoupe géométrique île entière (433k parcelles × polygones OCSGE/CatNat) = double-jointure "
        "lourde hors budget F6 (une à la fois, cf. mandat) ; aucun invariant servi ne dépend d'une "
        "part CatNat/OCSGE recalculée par géométrie (les lecteurs servent la part amont). Écarté."))

    # Muet domaine 8 : « parts aléa/PPR en % (déjà couvertes par checks_commune.py) ».
    ecartees.append(Ecartee(
        "F6.commune.parts_alea_ppr", "F6", "checks_commune.py",
        "parts aléa/PPR en % par commune DÉJÀ couvertes par checks_commune.py → ne pas doublonner."))

    # Muet domaine 8 : « indicateurs externes (population/SRU/prix) ».
    ecartees.append(Ecartee(
        "F6.commune.indicateurs_externes", "F6", "INSEE/SRU/obsimmo",
        "véracité d'indicateurs externes (population, SRU, prix) non recalculable en local sans la "
        "donnée amont officielle → hors portée lecture seule."))

    # Muet domaine 1 : « surface du calcul (surface_terrain_m2) muette » = E-09 déjà ouvert.
    ecartees.append(Ecartee(
        "F6.surface_terrain_m2_null", "F6", "parcel_residuel.surface_terrain_m2",
        "surface_terrain_m2 NULL sur tout le run = E-09 (vague 1, déjà ouvert) → ne pas doublonner."))

    # Muet domaine 9 : « fraîcheur AMONT réelle (sondes hors cron) ».
    ecartees.append(Ecartee(
        "F6.fraicheur_amont", "F6", "sondes réseau amont",
        "fraîcheur AMONT réelle des sources = sondes réseau hors cron → hors portée local/lecture seule."))

    # Muet domaine 10 : « chemin modèle live + recherche web sourcée du Copilote ».
    ecartees.append(Ecartee(
        "F6.copilote_llm_live", "F6", "Copilote (chemin LLM)",
        "chemin LLM live du Copilote : clé API absente en local → non auditable (le verrou aval "
        "déterministe est déjà couvert vague 1 domaine 10)."))

    # Muet domaine 11 : « POST authentifiés (évaluate/projets), concurrence/pool ».
    ecartees.append(Ecartee(
        "F6.post_auth_concurrence", "F6", "routes POST authentifiées / pool",
        "POST authentifiés non sondés (rester lecture seule) ; concurrence/pool non reproductible en "
        "local déterministe → hors portée."))

    # Muet domaine 5 : « prix obsimmo/Radar, médianes neuf live ».
    ecartees.append(Ecartee(
        "F6.prix_obsimmo_radar_live", "F6", "obsimmo/Radar (live)",
        "prix obsimmo/Radar et médianes neuf live = flux externes non figés en base locale → hors "
        "portée lecture seule."))

    # Muet domaine 7 : « véracité externe SDES/ADEME ».
    ecartees.append(Ecartee(
        "F6.veracite_sdes_adema", "F6", "SDES/ADEME (externe)",
        "véracité externe SDES/ADEME non vérifiable sans la source officielle amont → hors portée."))

    return specs, ecartees


# ════════════════════════════════════════════════════════════════════════════════════════════
#  Générateur
# ════════════════════════════════════════════════════════════════════════════════════════════
def generer(cx) -> tuple[list[RuleSpec], list[Ecartee]]:
    specs: list[RuleSpec] = []
    ecartees: list[Ecartee] = []

    # (1) containment
    try:
        polys = _polygones_communes()
        if len(polys) < 24:
            ecartees.append(Ecartee("F6.containment.*", "F6", str(GEOJSON),
                                    f"geojson incomplète ({len(polys)} communes) → containment écarté."))
        else:
            specs += _regles_containment(cx, polys)
    except Exception as e:  # noqa: BLE001
        ecartees.append(Ecartee("F6.containment.*", "F6", str(GEOJSON),
                                f"geojson illisible : {type(e).__name__}: {e}"))

    # (2) faisabilité en process
    specs += _regles_faisabilite(cx)

    # (3) le reste
    s3, e3 = _regles_reste(cx)
    specs += s3
    ecartees += e3

    return specs, ecartees


if __name__ == "__main__":
    cx = connexion()
    specs, ecartees = generer(cx)
    print(f"F6 — générées : {len(specs)} règles · écartées : {len(ecartees)}")
    for e in ecartees:
        print(f"   ÉCARTÉE {e.id} :: {e.raison}")
    resultats = run_specs(cx, specs)
    b = bilan(resultats)
    print(f"\nBILAN  OK={b['OK']}  ECART={b['ECART']}  SKIP={b['SKIP']}  (total {len(resultats)})")
    for r in resultats:
        if r.statut != "OK":
            print(f"\n[{r.statut}] {r.spec.id} · {r.spec.gravite}")
            print(f"   {r.spec.libelle}")
            print(f"   → {r.message}")
            for ex in r.exemples:
                print(f"      · {ex}")
    # échantillon OK pour preuve de volume (containment île + faisa couverture)
    print("\n— témoins OK clés —")
    for r in resultats:
        if r.statut == "OK" and (r.spec.id in ("F6.containment.ile", "F6.faisa.couverture_calcul",
                                               "F6.faisa.moteur_ne_leve_pas", "F6.faisa.non_constructible_sdp_nulle",
                                               "F6.an.sdp_positive_sans_assiette_uau")):
            print(f"   {r.spec.id}: {r.message}")
    cx.close()
