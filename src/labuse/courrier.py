"""Envoi de courrier postal par API (mandat wave-adresses, Lot 2B).

Étude DOM (10/07/2026, sourcée dans NOTES_WAVE_ACI.md) : La Réunion est du courrier
INTÉRIEUR France (≤ 100 g égrené — le vrai différenciateur est l'API, pas le DOM).
Prestataire RETENU : **Merci Facteur PRO** — doc API publique v1.2, sandbox, webhooks
(preuve de dépôt, AR), LRAR incluse, self-service (~2,69 € la lettre verte 3 pages +
19,95 €/mois pour l'API de production). Alternatives documentées : MySendingBox (sans
abonnement), Maileva (garantie OM1 écrite, volume).

Sans compte prestataire (action Vic) : provider « stub » — la mécanique (plafonds,
responsabilité du contenu, tarification coût × marge, suivi) est en place et testée,
AUCUN envoi réel ne part, et le front N'AFFICHE PAS le bouton (jamais de bouton mort).

Facturation à l'usage : FACTURE SÉPARÉE mensuelle (le plus simple — la table
courrier_envois porte coût et prix par envoi ; le metered billing Stripe pourra s'y
brancher quand Stripe sera en production côté Flash).
"""
from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy import text

from .config import get_settings

log = logging.getLogger("labuse.courrier")

# COURRIER-SERVICE (refonte 13 outils) — la table des DEMANDES d'envoi REVIENT À LA VIE : le client
# prépare, LABUSE envoie. M82 l'avait déclarée morte (aucun consommateur) ; elle a désormais cloche +
# Brevo + vue admin. CREATE + ALTER idempotents pour réconcilier une éventuelle table héritée d'un
# ancien schéma (colonnes ajoutées sans casser ; anciennes lignes = corps NULL, filtrées à la lecture).
#
# FIX-GB-011 — les statements sont une LISTE EXPLICITE, plus jamais `DDL.split(";")`. L'ancien découpage
# naïf coupait le DDL sur le `;` PRÉSENT DANS UN COMMENTAIRE SQL ci-dessus (« aucun consommateur ; elle
# a désormais… ; anciennes lignes… ») → produisait des morceaux de SQL invalides → toute la migration
# courrier avortait à CHAQUE boot (le CREATE/ALTER courrier_demandes ne s'appliquait jamais). Ici, aucun
# statement ne contient de `;` interne et rien n'est splitté : chaque élément est exécuté tel quel.
DDL_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS courrier_envois (
        id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
        sujet varchar(24) NOT NULL,
        idu varchar(14), adresse text NOT NULL,
        statut varchar(16) NOT NULL,
        provider varchar(16) NOT NULL, provider_ref varchar(64),
        cout_eur numeric(6,2), prix_eur numeric(6,2),
        assume_contenu boolean NOT NULL,
        modele varchar(40)
    )""",
    "CREATE INDEX IF NOT EXISTS courrier_envois_sujet_idx ON courrier_envois (sujet, ts)",
    """CREATE TABLE IF NOT EXISTS courrier_demandes (
        id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now()
    )""",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS compte_id integer",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS parcelles jsonb",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS n integer",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS communes text",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS modele varchar(40)",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS corps text",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS statut varchar(24) DEFAULT 'demande'",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now()",
    # CONNEXIONS-2 Lot 4 (KO-6) — RATTACHEMENT à la boucle commerciale : la demande de courrier porte
    # la piste CRM (pipeline_entry_id) et le projet (projet_id) d'où elle est née. Nullable : un courrier
    # peut naître hors piste (fiche/Assemblage). Backfill par IDU+compte quand univoque (ensure_tables).
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS pipeline_entry_id integer",
    "ALTER TABLE courrier_demandes ADD COLUMN IF NOT EXISTS projet_id integer",
    "CREATE INDEX IF NOT EXISTS courrier_demandes_compte_idx ON courrier_demandes (compte_id, ts)",
    "CREATE INDEX IF NOT EXISTS courrier_demandes_pe_idx ON courrier_demandes (pipeline_entry_id)",
    # RÉCONCILIATION du schéma LEGACY (FIX-GB-011, 2ᵉ volet) : une `courrier_demandes` héritée porte des
    # colonnes `sujet`/`texte` en NOT NULL SANS défaut. Le nouvel INSERT (creer_demande) ne les fournit
    # pas → sinon violation not-null (le POST /courrier/demande tombait en 500 même schéma « réparé »).
    # On relâche la contrainte SI la colonne existe (no-op sur une table neuve qui ne les a pas). Le bloc
    # DO contient des `;` INTERNES : sans danger car ce runner exécute chaque statement TEL QUEL (aucun
    # split — c'est précisément le sens du fix).
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'courrier_demandes' AND column_name = 'sujet') THEN
            ALTER TABLE courrier_demandes ALTER COLUMN sujet DROP NOT NULL;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'courrier_demandes' AND column_name = 'texte') THEN
            ALTER TABLE courrier_demandes ALTER COLUMN texte DROP NOT NULL;
        END IF;
    END $$""",
)

# CONNEXIONS-2 Lot 4 (KO-6) — VOCABULAIRE DE STATUT UNIQUE de la boucle commerciale :
#   demande (le client a demandé, à déposer par LABUSE) → depose → envoye → repondu / sans_reponse.
# Une seule source pour les trois écrans (outil Courrier, « Mes courriers », Kanban, dashboard).
STATUTS_DEMANDE = ("demande", "depose", "envoye", "repondu", "sans_reponse")
#: alias LEGACY → canonique (anciennes lignes, anciens clics de la Tour de contrôle). On NE casse rien :
#: `tarif_confirme`/`imprime` sont assimilés à « en préparation », `poste` à « envoyé ».
STATUT_ALIAS = {"tarif_confirme": "demande", "imprime": "depose", "poste": "envoye"}
#: libellés client uniques (servis partout).
STATUT_LIBELLES = {"demande": "Demandé", "depose": "Déposé", "envoye": "Envoyé",
                   "repondu": "Répondu", "sans_reponse": "Sans réponse"}
#: correspondance statut → BUCKET dashboard (Courrier.tsx) — table unique, plus de sets disjoints.
STATUT_BUCKET = {"demande": "a_deposer", "depose": "en_cours", "envoye": "en_cours",
                 "repondu": "clos", "sans_reponse": "clos"}
#: statuts de RETOUR, saisissables par la CLIENTE (dans le CRM) comme par l'admin (dashboard).
STATUTS_RETOUR = ("repondu", "sans_reponse")


def normaliser_statut(s: str | None) -> str | None:
    """Ramène un statut (éventuellement legacy) à sa forme canonique unique."""
    return STATUT_ALIAS.get(s, s) if s is not None else None


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL_STATEMENTS:
            c.execute(text(stmt))
    _backfill_rattachement(engine)


_BACKFILL_SQL = """
    UPDATE courrier_demandes d
       SET pipeline_entry_id = m.pe_id
      FROM (
        SELECT did, min(pe_id) AS pe_id
          FROM (
            SELECT d2.id AS did, pe.id AS pe_id
              FROM courrier_demandes d2
              JOIN parcels par ON par.idu = (d2.parcelles->>0)
              JOIN pipeline_entries pe ON pe.parcel_id = par.id
                   AND pe.compte_id IS NOT DISTINCT FROM d2.compte_id
             WHERE d2.pipeline_entry_id IS NULL
               AND d2.parcelles IS NOT NULL
               AND jsonb_array_length(d2.parcelles) = 1
          ) x
         GROUP BY did
        HAVING count(*) = 1
      ) m
     WHERE d.id = m.did"""


def backfill_rattachement_exec(conn) -> int:
    """CONNEXIONS-2 Lot 4 (KO-6) — backfill de `pipeline_entry_id` sur les demandes héritées : quand une
    demande porte EXACTEMENT UN IDU et qu'il existe EXACTEMENT UNE piste (pipeline_entries) de ce même
    compte sur cette parcelle, on rattache. Ambigu (0 ou ≥2 candidats) → laissé NULL (jamais un faux lien).
    Idempotent (ne touche que les lignes encore NULL). S'exécute sur un connexion/session fournie."""
    if conn.execute(text("SELECT to_regclass('pipeline_entries')")).scalar() is None:
        return 0  # table pipeline_entries absente (schéma partiel) → rien à faire
    return conn.execute(text(_BACKFILL_SQL)).rowcount


def _backfill_rattachement(engine) -> int:
    """Wrapper boot : ouvre sa propre transaction. Retourne le nombre rattaché."""
    with engine.begin() as c:
        n = backfill_rattachement_exec(c)
    if n:
        log.info("courrier backfill rattachement : %d demande(s) rattachée(s) à une piste", n)
    return n


# FIX-GB-013 — fenêtre d'idempotence (secondes) : deux demandes IDENTIQUES rapprochées ne créent qu'UNE
# ligne. Court exprès (un double-submit / retry part en quelques ms ; au-delà, une re-demande légitime
# du MÊME courrier doit rester possible).
IDEMPOTENCE_FENETRE_S = 120


def creer_demande(db, *, compte_id: int | None, parcelles: list[str],
                  communes: str | None, modele: str | None, corps: str,
                  pipeline_entry_id: int | None = None, projet_id: int | None = None) -> dict:
    """Enregistre une demande d'envoi (le client prépare, LABUSE envoie). Une ligne = une demande de N
    courriers. `parcelles` = liste d'IDU (jsonb) ; `communes` = récap lisible fourni par le front.

    FIX-GB-013 — DÉDUP DOUCE + CEINTURE CONCURRENCE : une demande identique (même compte, mêmes parcelles,
    même corps) datant de moins de `IDEMPOTENCE_FENETRE_S` est RENVOYÉE (`existing:true`) au lieu d'en
    créer une seconde. Robuste au double-POST CONCURRENT via un verrou consultatif TRANSACTIONNEL
    (`pg_advisory_xact_lock`, libéré au commit) qui sérialise les requêtes de même clé : la 2ᵉ attend que
    la 1ʳᵉ soit committée, la voit (READ COMMITTED) et la renvoie — jamais deux INSERT. L'UI garde son
    bouton `disabled` ; ceci est la ceinture serveur."""
    p_json = json.dumps(parcelles)
    # clé d'idempotence = md5(compte|parcelles|corps) → 60 bits pour le verrou (⊂ bigint signé)
    cle = hashlib.md5(f"{compte_id}|{p_json}|{corps or ''}".encode()).hexdigest()
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": int(cle[:15], 16)})
    dup = db.execute(text("""
        SELECT id, ts, n, communes, statut FROM courrier_demandes
        WHERE compte_id IS NOT DISTINCT FROM :c
          AND corps IS NOT DISTINCT FROM :corps
          AND parcelles = cast(:p AS jsonb)
          AND ts > now() - make_interval(secs => :w)
        ORDER BY ts DESC LIMIT 1"""),
        {"c": compte_id, "corps": corps, "p": p_json, "w": IDEMPOTENCE_FENETRE_S}).mappings().first()
    if dup is not None:
        return {**dict(dup), "existing": True}
    r = db.execute(text("""
        INSERT INTO courrier_demandes (compte_id, parcelles, n, communes, modele, corps, statut,
                                       pipeline_entry_id, projet_id)
        VALUES (:c, cast(:p AS jsonb), :n, :com, :m, :corps, 'demande', :pe, :pj)
        RETURNING id, ts, n, communes, statut"""),
        {"c": compte_id, "p": p_json, "n": len(parcelles),
         "com": communes, "m": modele, "corps": corps,
         "pe": pipeline_entry_id, "pj": projet_id}).mappings().one()
    return {**dict(r), "existing": False}


def demandes_de(db, compte_id: int | None) -> list[dict]:
    """Les demandes DU client (cloison), pour la timeline de statut. `corps IS NOT NULL` écarte les
    lignes héritées de l'ancien schéma M82."""
    return [{**dict(r), "statut": normaliser_statut(r["statut"])}
            for r in db.execute(text("""
        SELECT id, ts, n, communes, modele, statut, updated_at, pipeline_entry_id, projet_id
        FROM courrier_demandes
        WHERE corps IS NOT NULL AND compte_id IS NOT DISTINCT FROM :c
        ORDER BY ts DESC LIMIT 100"""), {"c": compte_id}).mappings()]


def demandes_admin(db, statut: str | None = None) -> list[dict]:
    """Vue admin (Vic) : toutes les demandes, filtrable par statut. D8 (Tour de contrôle) :
    + nom du client (jointure comptes, LEFT — compte NULL = pilote) et parcelles (pour le PDF)."""
    where = "WHERE d.corps IS NOT NULL" + (" AND d.statut = :s" if statut else "")
    return [{**dict(r), "statut": normaliser_statut(r["statut"])}
            for r in db.execute(text(
        f"SELECT d.id, d.ts, d.compte_id, d.n, d.communes, d.modele, d.corps, d.statut,"
        f"       d.updated_at, d.parcelles, d.pipeline_entry_id, d.projet_id, k.nom AS client"
        f" FROM courrier_demandes d LEFT JOIN comptes k ON k.id = d.compte_id"
        f" {where} ORDER BY d.ts DESC LIMIT 300"),
        ({"s": normaliser_statut(statut)} if statut else {})).mappings()]


def set_statut_demande(db, demande_id: int, statut: str, *, compte_id: int | None = None,
                       reserve_retour: bool = False) -> dict:
    """Fait avancer le statut d'une demande (vocabulaire canonique unique ; legacy normalisé).

    CONNEXIONS-2 Lot 4 : `compte_id` fourni ⇒ écriture SCOPÉE (la cliente ne touche QUE ses demandes) ;
    `reserve_retour` ⇒ seuls les statuts de RETOUR (repondu/sans_reponse) sont permis (garde CRM cliente).
    Sans ces deux, comportement admin (tout le cycle)."""
    statut = normaliser_statut(statut)
    permis = STATUTS_RETOUR if reserve_retour else STATUTS_DEMANDE
    if statut not in permis:
        raise ValueError(f"statut invalide : {statut} (attendu {', '.join(permis)})")
    scope = " AND compte_id IS NOT DISTINCT FROM :cid" if compte_id is not None else ""
    params = {"s": statut, "id": demande_id}
    if compte_id is not None:
        params["cid"] = compte_id
    r = db.execute(text(
        "UPDATE courrier_demandes SET statut = :s, updated_at = now() "
        f"WHERE id = :id{scope} "
        "RETURNING id, compte_id, n, communes, statut, pipeline_entry_id, projet_id"),
        params).mappings().first()
    if not r:
        raise ValueError("demande introuvable")
    return dict(r)


def kpi_dashboard(db) -> dict:
    """CONNEXIONS-2 Lot 4 (KPI dashboard) — agrégat des demandes par BUCKET (à déposer / en cours / clos),
    à partir du vocabulaire unique. « à déposer » = ce que LABUSE doit encore déposer (statut 'demande')."""
    rows = db.execute(text(
        "SELECT statut, count(*) AS n FROM courrier_demandes WHERE corps IS NOT NULL GROUP BY statut"
    )).mappings().all()
    buckets = {"a_deposer": 0, "en_cours": 0, "clos": 0}
    for r in rows:
        buckets[STATUT_BUCKET.get(normaliser_statut(r["statut"]), "en_cours")] += int(r["n"])
    return {"a_deposer": buckets["a_deposer"], "en_cours": buckets["en_cours"], "clos": buckets["clos"]}


def statut_par_pipeline_entry(db, compte_id: int | None, entry_ids: list[int]) -> dict[int, dict]:
    """Statut du DERNIER courrier rattaché à chaque piste (pour la carte Kanban + « Mes courriers »).
    Scopé compte. Retour : {pipeline_entry_id: {statut, libelle, demande_id, ts}}."""
    if not entry_ids:
        return {}
    rows = db.execute(text("""
        SELECT DISTINCT ON (pipeline_entry_id) pipeline_entry_id, id, statut, ts
          FROM courrier_demandes
         WHERE corps IS NOT NULL AND pipeline_entry_id = ANY(:ids)
           AND compte_id IS NOT DISTINCT FROM :c
         ORDER BY pipeline_entry_id, ts DESC"""),
        {"ids": entry_ids, "c": compte_id}).mappings().all()
    out: dict[int, dict] = {}
    for r in rows:
        st = normaliser_statut(r["statut"])
        out[r["pipeline_entry_id"]] = {"statut": st, "libelle": STATUT_LIBELLES.get(st, st),
                                       "demande_id": r["id"],
                                       "ts": r["ts"].isoformat() if r["ts"] else None}
    return out


def provider_actif() -> str:
    """'mercifacteur' si configuré, sinon 'stub' (aucun envoi réel, pas de bouton front)."""
    s = get_settings()
    if s.courrier_provider == "mercifacteur" and s.mercifacteur_api_key:
        return "mercifacteur"
    return "stub"


def tarif() -> dict:
    """Prix affiché au client = coût prestataire × marge (config, défaut × 1,5)."""
    s = get_settings()
    cout = float(s.courrier_cout_lettre_eur)
    return {"cout_prestataire_eur": round(cout, 2),
            "marge": float(s.courrier_marge),
            "prix_client_eur": round(cout * float(s.courrier_marge), 2),
            "provider": provider_actif(),
            "note": "lettre verte 1-3 pages, tarif intérieur France (DOM inclus ≤ 100 g)"}


def envois_du_jour(db, sujet: str) -> int:
    # « Le jour » est ancré sur l'HORLOGE DB (current_date), cohérent avec `ts DEFAULT now()`.
    # NE PAS comparer à un date.today() Python : quand la tz machine ≠ tz DB (ici Réunion +04),
    # ts::date (DB) et date.today() (local) divergent après minuit → le plafond ne compte plus rien.
    return int(db.execute(text(
        "SELECT count(*) FROM courrier_envois WHERE sujet = :s AND ts::date = current_date"),
        {"s": sujet}).scalar() or 0)


def _envoyer_mercifacteur(adresse: str, pdf_contenu: bytes | None) -> tuple[str, str]:
    """Envoi réel via l'API Merci Facteur v1.2 (sendCourrier, mode 'normal').

    Nécessite le compte PRO (LABUSE_MERCIFACTEUR_API_KEY/SECRET) — doc :
    https://www.merci-facteur.com/api/1.2/doc.php. Retourne (statut, référence)."""
    import httpx
    s = get_settings()
    # authentification + création du courrier — squelette conforme à la doc publique ;
    # à valider en SANDBOX à l'ouverture du compte (action Vic) avant toute production.
    resp = httpx.post(
        "https://www.merci-facteur.com/api/1.2/sendCourrier",
        data={"apiKey": s.mercifacteur_api_key, "apiSecret": s.mercifacteur_api_secret,
              "mode": "normal", "adresseDestinataire": adresse},
        files={"document": ("courrier.pdf", pdf_contenu or b"", "application/pdf")},
        timeout=s.http_timeout_s)
    resp.raise_for_status()
    ref = str(resp.json().get("courrierId", ""))
    return "envoye", ref


def envoyer(db, sujet: str, destinataires: list[dict], *, modele: str | None,
            assume_contenu: bool, pdf_contenu: bytes | None = None) -> dict:
    """Crée les envois (plafond/jour, responsabilité du contenu OBLIGATOIRE).

    destinataires : [{idu, adresse}] — adresses BAN normalisées (jamais de nom de
    personne physique : « À l'occupant »). Aucun envoi sans assume_contenu=True.
    """
    s = get_settings()
    if not assume_contenu:
        raise ValueError("Le contenu du courrier est de la responsabilité de l'émetteur — "
                         "case « j'assume le contenu de ce courrier » obligatoire.")
    deja = envois_du_jour(db, sujet)
    if deja + len(destinataires) > max(1, s.courrier_max_jour):
        raise ValueError(f"Plafond d'envois atteint ({s.courrier_max_jour}/jour) : "
                         f"{deja} déjà envoyés aujourd'hui.")
    prov = provider_actif()
    t = tarif()
    crees = []
    for d in destinataires:
        if prov == "mercifacteur":
            try:
                statut, ref = _envoyer_mercifacteur(d["adresse"], pdf_contenu)
            except Exception as exc:  # noqa: BLE001 — un échec d'envoi est un statut, pas un 500
                statut, ref = "erreur", type(exc).__name__
        else:
            statut, ref = "simule", None      # stub : mécanique testable, rien ne part
        row = db.execute(text(
            "INSERT INTO courrier_envois (sujet, idu, adresse, statut, provider, "
            " provider_ref, cout_eur, prix_eur, assume_contenu, modele) "
            "VALUES (:s, :i, :a, :st, :p, :r, :c, :px, true, :m) RETURNING id"),
            {"s": sujet, "i": d.get("idu"), "a": d["adresse"], "st": statut, "p": prov,
             "r": ref, "c": t["cout_prestataire_eur"], "px": t["prix_client_eur"],
             "m": modele}).scalar()
        crees.append({"id": row, "idu": d.get("idu"), "statut": statut})
    log.info("courrier : %d envoi(s) créés (provider=%s, sujet=%s)", len(crees), prov, sujet)
    return {"envois": crees, "provider": prov, "prix_unitaire_eur": t["prix_client_eur"],
            "total_eur": round(t["prix_client_eur"] * len(crees), 2),
            "facturation": "facture séparée mensuelle (voir NOTES_WAVE_ACI.md)"}
