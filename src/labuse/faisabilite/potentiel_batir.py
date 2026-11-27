"""CLASSEMENT-USAGE-1 (décision Vic 05/11/2026) — LE « potentiel à bâtir », une SEULE lecture.

LABUSE sert TOUS les professionnels de l'immobilier (agents, marchands de biens,
investisseurs, aménageurs, promoteurs), pas seulement les promoteurs. Le palier reste la
PROBABILITÉ DE VENTE, la même pour tous — il n'est JAMAIS « bonne affaire à construire ».
Le « potentiel à bâtir » devient une information À PART, lue par CETTE fonction et servie
partout de la même façon : fiche, listes, carte, Copilote, PDF.

Quatre faits, une seule règle (jamais une copie de la jointure ni du libellé) :
  · `sdp_restante_m2`  — SDP résiduelle SERVIE, bornée à 0 quand la zone est fermée (gate) ;
  · `zone_ouverte`     — False si la zone est fermée à l'urbanisation (AU non ouverte, A, N,
                         zone fermée au règlement) ou la parcelle non constructible ;
  · `constructible`    — False si un verdict moteur l'interdit (zone fermée / non constructible /
                         cause résiduelle : terrain exigu, PPR, reculs…) ;
  · `rien_a_batir`     — True quand il n'y a rien à bâtir (zone fermée ou SDP restante nulle).

Le GATE (« zone fermée / rien à servir ») est VERDICT-DRIVEN — il lit les caches que le moteur
produit déjà, jamais le préfixe de zone brut (garde-fou 21 077, cf. constructibilite.py) :
  1. `parcel_residuel.cause` présente  → le moteur a dit « pas de potentiel » (zone_non_constructible,
     habitat_interdit, terrain_exigu, redhibitoire…). La SDP stockée vaut alors 0.
  2. `parcel_constructibilite.label` ∈ {zone fermée, non constructible}  → déclassement A/B.
     C'est LE signal qui rattrape le cas 97422000AX1253 (2AUe, declasse_zone_fermee) : le run
     servi lui stocke 25 426 m² sans cause, parce que `parcel_residuel` ignore la fermeture que
     la constructibilité signale. Le gate le borne à 0 (incohérence interne fermée à la LECTURE,
     le run n'est pas recalculé — le chiffre stocké suivra à la prochaine bascule, même doctrine
     que `zone_servie.garde_sdp_residuelle`).
  3. `parcel_au_statut.classe` ∈ classes DIFFÉRÉES (AU fermée / phasage inconnu / générique) → AU
     non ouverte. Les classes SERVIES (`conditionnelle_operation`, `au_sous_plancher`,
     `dimensions_seules`) ne ferment PAS à elles seules — mais la constructibilité (2) prime si
     elle déclasse (le cas AX1253, classé `conditionnelle_operation` ET `declasse_zone_fermee`).

On s'appuie ainsi sur le VERDICT par parcelle (qui respecte l'assiette clippée des parcelles à
cheval, décision FAISABILITE-clip) plutôt que sur la famille de zone dominante nue : une parcelle
dominante A/N mais portant une portion U/AU constructible garde sa SDP clippée (pas de faux 0),
tandis qu'une A/N sans portion constructible porte déjà sa cause résiduelle → fermée.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .au_differe import AU_CLASSES_DIFFEREES
from .zone_servie import _TOK
from .constructibilite import DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE

#: labels de constructibilité qui FERMENT (déclassement A « zone fermée » / B « non constructible »).
_CONSTR_FERME = (DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE)

#: MOTEUR-VERITE-FIX-1 (LOT 3, V4/V9) — seules les causes CERTAINES ferment le gate. Une cause
#: d'IGNORANCE (assiette_a_verifier, hors_plu, zone_non_resolue, indetermine, bati_non_ingere…)
#: donne « Analyse incomplète », JAMAIS « rien à bâtir ». Même partition que
#: `faisabilite.engine.cause_certaine` (source unique, importée pour le jumeau SQL).
from .engine import _CAUSES_CERTAINES, cause_certaine, cause_libelle  # noqa: E402

_SQL_CAUSE_CERTAINE = ("split_part({r}.cause, ':', 1) IN ("
                       + ", ".join(f"'{c}'" for c in sorted(_CAUSES_CERTAINES)) + ")")


def sql_analyse_incomplete(r_alias: str = "r") -> str:
    """Expression SQL : TRUE si la parcelle porte une cause d'IGNORANCE (analyse incomplète) —
    le complément du gate, à servir « ∅ » (jamais un 0 ni un « rien à bâtir »)."""
    return (f"({r_alias}.cause IS NOT NULL AND NOT "
            + _SQL_CAUSE_CERTAINE.format(r=r_alias) + ")")

#: valeur « rien à lire » (parcelle hors run / sans donnée résiduelle) — un dict, jamais None.
POTENTIEL_ABSENT = {
    "sdp_restante_m2": None, "zone_ouverte": None, "zone_fam": None, "zone_lib": None,
    "constructible": None, "rien_a_batir": None, "motif": None,
    "libelle": "Potentiel à bâtir non calculé",
}


def _sql_gate(r_alias: str = "r", pc_alias: str = "pc", au_alias: str = "au") -> str:
    """Fragment SQL booléen « la zone est fermée / rien à servir » — LA définition unique du gate,
    réutilisée par les listes et la carte (mêmes alias de jointure à fournir). NULL-safe.
    LOT 3 (V4/V9) : une cause d'IGNORANCE ne ferme pas (→ « Analyse incomplète »)."""
    return (
        f"(({r_alias}.cause IS NOT NULL AND " + _SQL_CAUSE_CERTAINE.format(r=r_alias) + ")"
        f" OR COALESCE({pc_alias}.label IN ('{DECLASSE_ZONE_FERMEE}', '{DECLASSE_NON_CONSTRUCTIBLE}'), false)"
        f" OR COALESCE({au_alias}.classe IN (" + ", ".join(f"'{c}'" for c in sorted(AU_CLASSES_DIFFEREES))
        + f"), false))")


def sql_gate_ferme(r_alias: str = "r", pc_alias: str = "pc", au_alias: str = "au") -> str:
    """Expression SQL : TRUE si la zone est fermée (rien à bâtir par verdict). Voir `_sql_gate`."""
    return _sql_gate(r_alias, pc_alias, au_alias)


def sql_zone_fermee_verdict(pc_alias: str = "pc", au_alias: str = "au") -> str:
    """Expression SQL booléenne (NULL-safe) : la SDP de TRANSFORMATION ne doit PAS être servie —
    zone fermée au règlement (constructibilité déclassée A/B) SAUF quand la parcelle relève déjà du
    « potentiel différé » AU (`au_differe`, décision CHASSE-FIX-1/C06 : capacité DIFFÉRÉE, pas exclue,
    présentée « ≈ N m² après ouverture »). On ne borne donc QUE la constructibilité ferme ; une AU non
    ouverte garde sa présentation différée (une seule histoire à l'écran). HORS cause résiduelle
    (traitée à part). C'est la part du gate que la tuile (MVT) et le jumeau SQL du banc reproduisent
    pour que la SDP de transfo soit la MÊME partout : écran, carte, exports."""
    au_in = ", ".join(f"'{c}'" for c in sorted(AU_CLASSES_DIFFEREES))
    return (f"(COALESCE({pc_alias}.label IN ('{DECLASSE_ZONE_FERMEE}', '{DECLASSE_NON_CONSTRUCTIBLE}'), false)"
            f" AND NOT COALESCE({au_alias}.classe IN ({au_in}), false))")


def sql_sdp_restante(r_alias: str = "r", pc_alias: str = "pc", au_alias: str = "au") -> str:
    """Expression SQL : SDP restante SERVIE (0 si zone fermée), même règle que la lecture Python.
    LOT 3 (V4/V9) : une cause d'IGNORANCE sert NULL (SDP ∅ « à vérifier »), jamais le 0 stocké
    pollué ni un faux chiffre."""
    return (f"CASE WHEN {_sql_gate(r_alias, pc_alias, au_alias)} THEN 0 "
            f"WHEN {sql_analyse_incomplete(r_alias)} THEN NULL "
            f"ELSE COALESCE({r_alias}.sdp_residuelle_m2, 0) END")


def sql_a_construire(r_alias: str = "r", pc_alias: str = "pc", au_alias: str = "au") -> str:
    """Expression SQL : TRUE si la parcelle a RÉELLEMENT quelque chose à bâtir (zone ouverte ET
    SDP restante > 0) — le prédicat du tri « À construire ». Même règle que `rien_a_batir`.
    LOT 3 : une analyse incomplète n'est JAMAIS « à construire » (on ne sait pas)."""
    return (f"(NOT {_sql_gate(r_alias, pc_alias, au_alias)} "
            f"AND NOT {sql_analyse_incomplete(r_alias)} "
            f"AND COALESCE({r_alias}.sdp_residuelle_m2, 0) > 0)")


def where_a_construire(p_alias: str = "p") -> str:
    """Fragment WHERE (EXISTS/NOT EXISTS corrélés sur `<p_alias>.id`) — « il reste RÉELLEMENT
    quelque chose à bâtir » : zone OUVERTE (gate négatif) ET SDP restante > 0. AUTONOME (aucune
    jointure à ajouter par l'appelant) → la MÊME règle coule dans le compteur, la page ET la liste
    d'IDU de la carte. C'est LE prédicat du tri « À construire » (CLASSEMENT-USAGE-1).

    Miroir exact de `_sql_gate` / `sql_a_construire`, exprimé en sous-requêtes pour les lecteurs
    qui ne joignent pas résiduel/constructibilité/AU (compteur, IDU carte)."""
    au_in = ", ".join(f"'{c}'" for c in sorted(AU_CLASSES_DIFFEREES))
    return (
        f" AND EXISTS (SELECT 1 FROM parcel_residuel r_ac WHERE r_ac.parcel_id = {p_alias}.id"
        f"             AND r_ac.cause IS NULL AND COALESCE(r_ac.sdp_residuelle_m2, 0) > 0)"
        f" AND NOT EXISTS (SELECT 1 FROM parcel_constructibilite pc_ac WHERE pc_ac.parcel_id = {p_alias}.id"
        f"                 AND pc_ac.label IN ('{DECLASSE_ZONE_FERMEE}', '{DECLASSE_NON_CONSTRUCTIBLE}'))"
        f" AND NOT EXISTS (SELECT 1 FROM parcel_au_statut au_ac WHERE au_ac.parcel_id = {p_alias}.id"
        f"                 AND au_ac.classe IN ({au_in}))")


def _fmt_m2(v: float) -> str:
    return f"{round(v):,}".replace(",", " ")


def _assemble(sdp_raw, cause, constr_label, au_classe, zone_fam, zone_lib) -> dict:
    """Les cinq signaux bruts → les quatre faits + le libellé. Pur (testable sans DB)."""
    # Rien de connu (ni SDP, ni zone, ni verdict) → POTENTIEL ABSENT, jamais un faux « non calculé
    # constructible » : une parcelle sans aucune donnée (base de test nue, couche manquante) ne doit
    # pas faire apparaître une section « potentiel à bâtir » vide (régression test_flash_report).
    if (sdp_raw is None and cause is None and constr_label is None and au_classe is None
            and zone_fam is None and zone_lib is None):
        return dict(POTENTIEL_ABSENT)
    constr_ferme = constr_label in _CONSTR_FERME
    au_differe = au_classe in AU_CLASSES_DIFFEREES
    # MOTEUR-VERITE-FIX-1 (LOT 3, V4/V9) — seule une cause CERTAINE ferme ; une IGNORANCE donne
    # « Analyse incomplète » avec sa cause (SDP ∅, jamais le 0 stocké), jamais « rien à bâtir ».
    cause_ferme = cause is not None and cause_certaine(cause)
    ignorance = cause is not None and not cause_certaine(cause) and not constr_ferme and not au_differe
    gate_ferme = cause_ferme or constr_ferme or au_differe

    if ignorance:
        lib_cause = cause_libelle(cause) or str(cause)
        lib = lib_cause if lib_cause.startswith("Analyse incomplète") else f"Analyse incomplète — {lib_cause}"
        return {
            "sdp_restante_m2": None,
            "zone_ouverte": None, "zone_fam": zone_fam, "zone_lib": zone_lib,
            "constructible": None, "rien_a_batir": None,
            "motif": lib,
            "libelle": lib,
        }

    sdp_restante = 0 if gate_ferme else (int(round(sdp_raw)) if sdp_raw is not None else None)
    # MOTEUR-VERITE-FIX-1 (LOT 3, V10) — AU DIFFÉRÉE : un seul verdict, cohérent avec la surface
    # servie. La capacité stockée est PRÉSENTÉE « après ouverture » (doctrine CHASSE-FIX-1/C06 :
    # différée, pas exclue) — fini l'écran qui montre 168 m² quand le gate dit « rien à bâtir ».
    if au_differe and not constr_ferme and not cause_ferme and sdp_raw is not None and sdp_raw > 0:
        sdp_restante = int(round(sdp_raw))
    zone_ouverte = not gate_ferme
    constructible = not (constr_ferme or cause_ferme or au_differe)
    rien_a_batir = gate_ferme or (sdp_restante is not None and sdp_restante <= 0)

    # motif : POURQUOI il n'y a rien, None si constructible.
    # EXPORTS-FIX-3 LOT 2 — ORDRE DES MOTIFS imposé par le mandat (« un seul verdict, partout ») :
    #   1. zone non constructible (famille A/N)  2. zone rouge du PPR  3. le reste.
    # « Terrain trop étroit » ne passe JAMAIS devant une raison de zone — c'était la faute A2/B2 de
    # l'audit (97408000BI0351, 2,8 ha de zone N, affichée « terrain trop exigu »). La famille de zone
    # (A/N) est lue par `zone_fam` (source unique du run servi, `parcel_zone_plu.zone_fam`, dérivée du
    # subtype par `labuse_zone_famille`), jamais du préfixe du libellé. La cause résiduelle (exigu,
    # reculs…) ne sert QUE lorsqu'aucune raison de zone ne s'applique.
    motif = None
    _zfam = str(zone_fam or "").upper()
    _ppr_rouge = cause is not None and str(cause).partition(":")[0] in ("redhibitoire", "ppr_rouge")
    if gate_ferme and _zfam in ("A", "N"):
        _nat = {"A": "agricole", "N": "naturelle"}[_zfam]
        _suf = f" ({zone_lib})" if zone_lib and str(zone_lib).upper() != _zfam else ""
        motif = f"Zone non constructible — {_nat}{_suf}"
    elif str(cause or "").startswith("zone_non_constructible"):
        motif = f"Zone non constructible{(' (' + zone_lib + ')') if zone_lib else ''}"
    elif _ppr_rouge:
        motif = "Zone rouge du PPR — inconstructible (L562-1)"
    elif constr_label == DECLASSE_ZONE_FERMEE:
        motif = f"Zone fermée à l'urbanisation{(' (' + zone_lib + ')') if zone_lib else ''}"
    elif au_differe:
        motif = f"Zone AU non ouverte à l'urbanisation{(' (' + zone_lib + ')') if zone_lib else ''}"
    elif constr_label == DECLASSE_NON_CONSTRUCTIBLE:
        motif = "Parcelle non constructible (surface ou reculs insuffisants)"
    elif cause is not None:
        # cause résiduelle brute → formulation client (jamais le slug nu).
        if str(cause).startswith("terrain_exigu"):
            motif = "Terrain trop exigu pour un projet"
        elif str(cause).startswith("habitat_interdit"):
            motif = "Habitat interdit dans cette zone"
        elif str(cause).startswith("assiette_a_verifier"):
            motif = "Assiette constructible à vérifier (géométrie)"   # EXIGU-FIX-1 — ignorance, pas « pas de potentiel »
        else:
            motif = "Pas de potentiel constructible résiduel"

    # libellé de synthèse (une ligne, servi tel quel partout).
    if au_differe and not constr_ferme and not cause_ferme and (sdp_restante or 0) > 0:
        # LOT 3 (V10) — différé AVEC sa surface : le même chiffre que l'écran, une seule histoire.
        from .au_differe import libelle_differe
        libelle = libelle_differe(sdp_restante)
    elif gate_ferme:
        libelle = f"Rien à bâtir — {motif}" if motif else "Rien à bâtir"
    elif sdp_restante is None:
        libelle = "Potentiel à bâtir non calculé"
    elif sdp_restante <= 0:
        libelle = "Rien à bâtir — parcelle déjà construite au maximum"
    else:
        libelle = f"≈ {_fmt_m2(sdp_restante)} m² encore constructibles"

    return {
        "sdp_restante_m2": sdp_restante,
        "zone_ouverte": zone_ouverte,
        "zone_fam": zone_fam,
        "zone_lib": zone_lib,
        "fermeture_au": _zfam == "AU" and not cause_ferme and (au_differe or constr_label == DECLASSE_ZONE_FERMEE),
        "constructible": constructible,
        "rien_a_batir": rien_a_batir,
        "motif": motif,
        "libelle": libelle,
    }


_SELECT = text(f"""
    SELECT p.idu AS idu, p.id AS pid, p.commune AS commune,
           r.sdp_residuelle_m2 AS sdp_raw, r.cause AS resid_cause,
           pc.label AS constr_label, au.classe AS au_classe, au.motif AS au_motif,
           zp.zone_fam AS zone_fam, zp.zone_lib AS zone_lib,
           ARRAY(SELECT DISTINCT {_TOK} FROM spatial_layers z
                 WHERE z.kind='plu_gpu_zone' AND z.commune=p.commune
                   AND labuse_zone_famille(z.subtype)='AU'
                   AND ST_Intersects(z.geom_2975,p.geom_2975)) AS codes_au
    FROM parcels p
    LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
    LEFT JOIN parcel_constructibilite pc ON pc.parcel_id = p.id
    LEFT JOIN parcel_au_statut au ON au.parcel_id = p.id
    LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
    WHERE p.idu = ANY(:idus)
""")

#: familles de zone CONSTRUCTIBLES : seules elles sont éligibles à la correction PPR-PARTIEL (une A/N
#: reste fermée même hors rouge). AU n'est éligible que si elle n'est pas différée (gate `au_classe`).
_ZONES_CONSTRUCTIBLES = ("U", "AU")


def _override_ppr_partiel(info: dict, zone_fam, zone_lib) -> dict:
    """Le verdict de potentiel d'une parcelle PARTIELLEMENT rouge, servi IDENTIQUE partout (DOCS-1).
    On n'invente PAS de SDP (la capacité chiffrée est à l'Étude, qui découpe le rouge) ; on dit la
    vérité doctrinale : la part rouge est retirée, le reste garde son potentiel."""
    return {
        "sdp_restante_m2": None,
        "zone_ouverte": True,
        "zone_fam": zone_fam, "zone_lib": zone_lib,
        "constructible": True,
        "rien_a_batir": False,
        "motif": None,
        "ppr_partiel": info,
        "libelle": (f"Constructible sur la partie hors zone rouge du PPR "
                    f"({info['pct_hors_rouge']} %) — zone rouge ({info['pct_rouge']} %) retirée ; "
                    f"capacité à l'Étude de faisabilité"),
    }


def potentiel_batir_batch(db: Session, idus: list[str]) -> dict[str, dict]:
    """{idu → potentiel à bâtir} en UNE requête. IDU sans donnée → POTENTIEL_ABSENT (présent).

    Lecture seule, tolérante : `parcel_residuel` (vue du run servi) / `parcel_constructibilite` /
    `parcel_au_statut` absentes (base de test nue) → la jointure rend NULL, le gate reste NULL-safe
    (aucune de ces absences ne ferme une zone), jamais une 500.

    DOCS-1 (décision Vic) — PPR-PARTIEL : quand le run ferme une parcelle en zone CONSTRUCTIBLE par sa
    SEULE cause résiduelle (ni déclassement, ni AU différée) ET que cette parcelle n'est que
    PARTIELLEMENT rouge avec un reste hors rouge exploitable, on remplace le verdict « rien à bâtir —
    rédhibitoire » par « constructible sur la partie hors rouge » — la MÊME lecture que l'Étude de
    faisabilité (qui découpe le rouge). SOURCE UNIQUE `faisabilite.db.verdict_ppr_partiel`."""
    out: dict[str, dict] = {i: dict(POTENTIEL_ABSENT) for i in idus}
    if not idus:
        return out
    rows = {row["idu"]: row for row in db.execute(_SELECT, {"idus": list(idus)}).mappings().all()}
    for idu, row in rows.items():
        out[idu] = _assemble(row["sdp_raw"], row["resid_cause"], row["constr_label"],
                             row["au_classe"], row["zone_fam"], row["zone_lib"])
    # MOTEUR-VERITE-FIX-3 — commune au RNU : « hors du PLU outillé » n'est PAS une ignorance,
    # c'est un RÉGIME NATIONAL connu (rnu.py, doctrine : on n'affirme JAMAIS une constructibilité
    # au RNU). L'ignorance « Analyse incomplète » laissait Estimer servir un prix de terrain À
    # BÂTIR sur Saint-Philippe (E105). On ne remplace qu'un verdict d'ignorance/absence — jamais
    # un verdict ferme venu d'une autre couche.
    for idu in idus:
        if out[idu].get("constructible") is None:
            try:
                from ..rnu import LIBELLE_RNU, is_rnu_idu
            except Exception:  # noqa: BLE001 — module indisponible : on garde l'assemblage
                break
            if is_rnu_idu(idu):
                lib = (f"{LIBELLE_RNU} — constructibilité limitée aux parties actuellement "
                       "urbanisées, analyse au cas par cas.")
                out[idu] = {"sdp_restante_m2": None,
                            "zone_ouverte": None, "zone_fam": None, "zone_lib": None,
                            "constructible": False, "rien_a_batir": None,
                            "motif": lib, "libelle": lib}
    # PPR-PARTIEL — correction à la lecture, UNIQUEMENT pour les parcelles fermées par leur seule cause
    # résiduelle en zone constructible (candidat rare : ~cause présente, pas de déclassement/AU différée).
    from .au_differe import AU_CLASSES_DIFFEREES
    for idu, row in rows.items():
        res = out[idu]
        if not res.get("rien_a_batir"):
            continue
        if (row["resid_cause"] is None or row["constr_label"] in _CONSTR_FERME
                or row["au_classe"] in AU_CLASSES_DIFFEREES
                or row["zone_fam"] not in _ZONES_CONSTRUCTIBLES):
            continue
        try:
            from .db import verdict_ppr_partiel
            info = verdict_ppr_partiel(db, row["pid"])
        except Exception:  # noqa: BLE001 — correction best-effort ; jamais une 500 sur la lecture
            info = None
        if info:
            out[idu] = _override_ppr_partiel(info, row["zone_fam"], row["zone_lib"])
    # OUTIL-ASSEMBLAGE-FIX-8 (LOT 5) — une cause 'redhibitoire' est GÉNÉRIQUE : elle ne prouve PAS une
    # zone rouge du PPR. En base, ~219 des 448 parcelles 'redhibitoire' n'intersectent AUCUN PPR rouge
    # (ex. DH0119, en PPR BLEU B2) — le motif « Zone rouge du PPR » y était FAUX (audit bloquant 5). On
    # ne garde ce motif que si la parcelle intersecte RÉELLEMENT un PPR rouge (labuse_ppr_couleur) ;
    # sinon on dit la vérité : contrainte rédhibitoire du run de capacité, hors zone rouge, à vérifier.
    for idu, row in rows.items():
        res = out[idu]
        if not str(res.get("motif") or "").startswith("Zone rouge du PPR"):
            continue
        try:
            with db.begin_nested():
                rouge_m2 = db.execute(_PPR_ROUGE_M2, {"pid": row["pid"]}).scalar()
        except Exception:  # noqa: BLE001 — géométrie pathologique : on ne corrige pas, jamais une 500
            rouge_m2 = None
        if rouge_m2 is not None and float(rouge_m2 or 0.0) <= 0.0:
            m = ("Parcelle inconstructible selon le run de capacité (contrainte rédhibitoire hors zone "
                 "rouge du PPR — à vérifier)")
            res["motif"] = m
            res["libelle"] = f"Rien à bâtir — {m}"
    # OUTIL-ASSEMBLAGE-FIX-9 (LOT 3) — ZONE À URBANISER FERMÉE : le run servi (parcel_residuel, figé) a pu
    # chiffrer une capacité pour une zone AU fermée (`constructible_neuf=False`) alors que le moteur LIVE la
    # zéro (CP1639 : AU3st + éclat U3c → 11 294 m² fantômes). On lit le verdict LIVE (`parcel_faisabilite`,
    # même règle que le chemin union) pour les parcelles dominées par une zone AU fermée : si le live confirme
    # « zone à urbaniser fermée » (cause zone_transition), le potentiel dit « capacité non calculée — zone à
    # urbaniser fermée », au lieu d'un chiffre que le Bilan reprendrait. Le run servi / le classement q_v20 ne
    # sont PAS touchés (lecture seule à l'affichage).
    from .zonage import resolve_zone
    for idu, row in rows.items():
        codes = set(row["codes_au"] or [])
        if row["zone_fam"] == "AU":
            codes.add(row["zone_lib"])
        if not any((rz := resolve_zone(code, row["commune"])) and not rz.constructible_neuf for code in codes):
            continue
        try:
            from .db import parcel_faisabilite
            with db.begin_nested():
                pf = parcel_faisabilite(db, row["pid"])
        except Exception:  # noqa: BLE001 — verdict live best-effort ; jamais une 500 sur la lecture
            pf = None
        regle_dom = resolve_zone(row["zone_lib"], row["commune"]) if row["zone_fam"] == "AU" else None
        ferme = (regle_dom is not None and not regle_dom.constructible_neuf and pf is not None
                 and not pf[1].constructible and pf[1].cause == "zone_transition")
        if ferme:
            _motif = (row["au_motif"] or "").strip()
            base = f"Zone à urbaniser fermée ({row['zone_lib']})"
            m = f"Capacité non calculée — {base}" + (f" : {_motif}" if _motif else
                " : ouverture conditionnée à une modification du PLU.")
            out[idu] = {"sdp_restante_m2": None,
                        "zone_ouverte": False, "zone_fam": row["zone_fam"], "zone_lib": row["zone_lib"],
                        "constructible": False, "rien_a_batir": True, "fermeture_au": True,
                        "motif": m, "libelle": m}
        elif (pf and pf[0].zone_fam in ("A", "N") and not pf[1].constructible and pf[0].uau_reelle):
            from .db import _contient_au_fermee, _uau_portion_reelle
            portion = pf[0].uau_reelle
            if _contient_au_fermee(pf[0]) and not _uau_portion_reelle(portion["m2"], portion["erode_m2"]):
                aire = "moins de 1 m²" if portion["m2"] < 1 else f"{_fmt_m2(portion['m2'])} m²"
                m = (f"Capacité non calculée — zone dominante {pf[0].zone}. "
                     "Après retrait de la zone à urbaniser fermée, la portion ouverte "
                     f"({aire} sur le plan) est trop petite ou trop étroite pour un projet.")
                out[idu].update(constructible=False, rien_a_batir=True, zone_ouverte=False,
                                motif=m, libelle=m, sdp_restante_m2=None)
        elif (pf and pf[1].constructible and pf[0].portion_servie_m2 and pf[0].uau_reelle
              and (pf[1].fourchette or {}).get("surface_plancher_m2")
              and row["constr_label"] != DECLASSE_NON_CONSTRUCTIBLE
              and row["resid_cause"] in (None, "zone_transition")):
            ctx = pf[0]
            ouvertes = []
            fermees = []
            for part in ctx.zone_parts:
                if part["fam"] not in _ZONES_CONSTRUCTIBLES:
                    continue
                regle = resolve_zone(part["zone"], ctx.commune)
                if regle and regle.constructible_neuf and regle.habitat != "interdit":
                    ouvertes.append(part["zone"])
                elif regle and not regle.constructible_neuf and part["fam"] == "AU":
                    fermees.append(part)
            if not ouvertes or not fermees:
                continue
            plan = round(ctx.uau_reelle["m2"])
            terrain = ctx.portion_servie_m2
            aire = f"{_fmt_m2(terrain)} m²"
            if plan != terrain:
                aire += f" à l’échelle de la contenance cadastrale, {_fmt_m2(plan)} m² sur le plan"
            zones = " et ".join(ouvertes)
            secteur = f"la seule portion {zones}" if len(ouvertes) == 1 else f"les seules portions {zones}"
            pct = sum(part["pct"] for part in fermees)
            pct_txt = f"{pct:.1f}".rstrip("0").rstrip(".").replace(".", ",")
            lib = (f"Capacité calculée sur {secteur} ({aire}). "
                   f"{pct_txt} % du terrain est en zone à urbaniser fermée "
                   f"({' et '.join(part['zone'] for part in fermees)}).")
            # Le résiduel du classement peut encore porter l'assiette entière.
            # Seul le calcul sur la portion ouverte peut alimenter la lecture individuelle.
            from .residuel import compute_residuel
            try:
                with db.begin_nested():
                    residuel = compute_residuel(db, row["pid"], faisa=pf)
            except Exception:  # Lecture du bâti facultative pour qualifier la portion de terrain.
                residuel = {}
            sdp = residuel.get("sdp_residuelle_m2") if residuel.get("disponible") else None
            out[idu].update(constructible=True, rien_a_batir=sdp == 0, zone_ouverte=True,
                            motif=None, libelle=lib, sdp_restante_m2=sdp,
                            portion_ouverte={"m2": terrain, "pct": ctx.uau_reelle["pct"], "mention": lib})
    return out


#: OUTIL-ASSEMBLAGE-FIX-8 (LOT 5) — surface de PPR ROUGE (interdiction) réellement intersectée par la
#: parcelle, via la classification UNIQUE `labuse_ppr_couleur`. 0 → aucune zone rouge (le motif « zone
#: rouge du PPR » serait alors faux).
_PPR_ROUGE_M2 = text(
    "SELECT COALESCE(sum(ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975))), 0) "
    "FROM spatial_layers sl JOIN parcels p ON p.id = :pid "
    "WHERE sl.kind = 'ppr' AND labuse_ppr_couleur(sl.subtype, sl.attrs) = 'rouge' "
    "AND ST_Intersects(sl.geom_2975, p.geom_2975)")


def potentiel_batir(db: Session, idu: str) -> dict:
    """Potentiel à bâtir d'UNE parcelle (fiche / Copilote / PDF). Toujours un dict — jamais None."""
    return potentiel_batir_batch(db, [idu])[idu]


def est_ferme_parcel(db: Session, parcel_id: int) -> bool:
    """TRUE si la zone est fermée / rien à servir pour un `parcel_id` (clé interne) — MÊME gate
    verdict-driven, pour les lecteurs qui tiennent le parcel_id (PDF `bloc_potentiel`). Tolérant."""
    try:
        row = db.execute(text(
            "SELECT r.cause AS resid_cause, pc.label AS constr_label, au.classe AS au_classe, "
            "       zp.zone_fam AS zone_fam "
            "FROM parcels p "
            "LEFT JOIN parcel_residuel r ON r.parcel_id = p.id "
            "LEFT JOIN parcel_constructibilite pc ON pc.parcel_id = p.id "
            "LEFT JOIN parcel_au_statut au ON au.parcel_id = p.id "
            "LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu "
            "WHERE p.id = :pid"), {"pid": parcel_id}).mappings().first()
    except Exception:  # noqa: BLE001 — caches absents → pas de fermeture (jamais une 500)
        return False
    if not row:
        return False
    # LOT 3 (V4/V9) — même partition que le gate : une cause d'IGNORANCE ne ferme pas.
    ferme = (cause_certaine(row["resid_cause"])
             or row["constr_label"] in _CONSTR_FERME
             or row["au_classe"] in AU_CLASSES_DIFFEREES)
    # PPR-PARTIEL (DOCS-1) — une parcelle fermée par sa SEULE cause résiduelle en zone constructible,
    # mais seulement PARTIELLEMENT rouge avec un reste exploitable, n'est PAS fermée (même lecture que
    # `potentiel_batir` et l'Étude — le `bloc_potentiel` du Flash ne doit pas dire « rien à construire »).
    if (ferme and row["resid_cause"] is not None and row["constr_label"] not in _CONSTR_FERME
            and row["au_classe"] not in AU_CLASSES_DIFFEREES
            and row["zone_fam"] in _ZONES_CONSTRUCTIBLES):
        try:
            from .db import verdict_ppr_partiel
            if verdict_ppr_partiel(db, parcel_id):
                return False
        except Exception:  # noqa: BLE001 — correction best-effort, jamais une 500
            pass
    return ferme
