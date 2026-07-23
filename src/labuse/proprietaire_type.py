"""Type de propriétaire (Lot C3) — classification + courrier SPF, cœur PUR (sans DB).

Aucune donnée personnelle n'est scrapée ni fabriquée : on CLASSE ce qui est déjà présent dans
les Fichiers fonciers (Cerema, sous convention) quand ils ont été importés ; pour tout le reste
(le cas dominant : propriétaire inconnu), on PRODUIT un courrier de demande au Service de la
Publicité Foncière (SPF) — la voie LÉGALE d'obtention, pré-remplie avec la seule référence
cadastrale (donnée publique). Jamais de nom de personne physique.
"""
from __future__ import annotations

from datetime import date

# type -> (libellé, public ?, acquérabilité / interlocuteur). `public=None` = indéterminé.
OWNER_TYPES: dict[str, tuple[str, bool | None, str]] = {
    "commune": ("Commune", True, "cession/préemption — interlocuteur public"),
    "etat": ("État / domaine public", True, "domaine — cession soumise à procédure"),
    "collectivite": ("Collectivité (Région / Département / EPCI)", True, "interlocuteur public"),
    "epf": ("EPF — établissement public foncier", True, "portage foncier possible"),
    "etablissement_public": ("Établissement public / organisme associé", True, "interlocuteur public/parapublic"),
    "sem": ("SEM — société d'économie mixte", True, "parapublic — un interlocuteur"),
    "bailleur_social": ("Bailleur social", False, "négociation directe — un interlocuteur"),
    "sci": ("SCI", False, "acquérable — interlocuteur unique"),
    "societe": ("Société (SA / SARL / SAS)", False, "acquérable — personne morale"),
    "copropriete": ("Copropriété", False, "multi-décideurs (syndic / AG)"),
    "indivision": ("Indivision", False, "bloqueur fréquent — accord de tous les indivisaires"),
    "personne_physique": ("Personne physique", False, "identité à obtenir via le SPF"),
    "inconnu": ("Propriétaire à identifier", None, "demande au SPF (voie légale)"),
}

# Groupe de personne morale DGFiP (champ « Groupe personne », 0-9) → owner_type (1.A).
_DGFIP_GROUPE: dict[int, str] = {
    1: "etat", 2: "collectivite", 3: "collectivite", 4: "commune",
    5: "bailleur_social", 6: "sem", 7: "copropriete", 8: "indivision",
    9: "etablissement_public",
    # 0 = « personnes morales non remarquables » → raffiné par la forme juridique (SCI vs société).
}

# Heuristiques sur le libellé `categorie` des Fichiers fonciers (mots-clés → type).
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("epf", "etablissement public foncier", "établissement public foncier"), "epf"),
    (("commune", "mairie", "ville de", "ccas"), "commune"),
    (("état", "etat", "domaine", "drfip", "dgfip", "ministère", "ministere"), "etat"),
    (("région", "region", "départe", "departe", "epci", "cinor", "tco", "civis", "casud", "cirest",
      "collectiv", "syndicat mixte", "conservatoire", "cdl"), "collectivite"),
    (("hlm", "shlmr", "sidr", "semader", "sodiac", "sodegis", "bailleur", "office public", "opac",
      "logement social"), "bailleur_social"),
    (("sci", "société civile immobilière", "societe civile immobiliere"), "sci"),
    (("copropri", " asl", "syndic", "aful"), "copropriete"),
    (("sa ", "s.a.", "sarl", "s.a.r.l", "sas", "s.a.s", "société", "societe", "snc", "eurl"), "societe"),
]


def classify_owner_type(payload: dict | None) -> dict:
    """Classe le type de propriétaire à partir d'un payload Fichiers fonciers (ou None).

    Renvoie {owner_type, label, public, acquerabilite, indivision, identifiable}. `identifiable`
    = on connaît un interlocuteur (morale/public) ; sinon il faut passer par le SPF."""
    if not payload:
        return _pack("inconnu", indivision=False, identifiable=False)

    cat = (payload.get("categorie") or "").lower()
    morale = bool(payload.get("personne_morale"))
    nb = payload.get("nb_droits_propriete")
    indivision = bool(payload.get("indivision") or (nb is not None and nb >= 2))

    otype = None
    for keys, t in _RULES:
        if any(k in cat for k in keys):
            otype = t
            break
    if otype is None:
        otype = "societe" if morale else ("personne_physique" if (cat or payload.get("personne_physique")) else "inconnu")

    # Indivision : signalée à part ; prime sur « personne physique » pour le libellé d'action.
    if indivision and otype in ("personne_physique", "inconnu"):
        otype = "indivision"
    identifiable = otype not in ("inconnu", "personne_physique", "indivision")
    return _pack(otype, indivision=indivision, identifiable=identifiable, categorie=payload.get("categorie"))


def _pack(otype: str, *, indivision: bool, identifiable: bool, categorie: str | None = None) -> dict:
    label, public, acq = OWNER_TYPES[otype]
    return {
        "owner_type": otype, "label": label, "public": public,
        "acquerabilite": acq, "indivision": indivision, "identifiable": identifiable,
        "categorie_source": categorie,
        # Pour les filtres : famille agrégée.
        "famille": ("public" if public else "prive" if public is False else "inconnu"),
    }


def classify_dgfip(groupe: int | None, forme_abregee: str | None, denomination: str | None) -> dict:
    """Classe un propriétaire à partir du fichier DGFiP des personnes morales (1.A) : groupe
    (0-9) + forme juridique abrégée + dénomination → owner_type + owner_name (donnée publique)."""
    forme = (forme_abregee or "").strip().upper()
    nom = (denomination or "").strip()
    nom_l = nom.lower()
    otype = _DGFIP_GROUPE.get(int(groupe)) if groupe is not None else None
    # Affinages dénomination (avant le repli groupe 0).
    if otype == "etablissement_public" and any(k in nom_l for k in ("epf", "foncier")):
        otype = "epf"
    if otype is None:  # groupe 0 — personnes morales « non remarquables »
        if "SCI" in forme or "civile immobili" in nom_l:
            otype = "sci"
        elif any(k in forme for k in ("ASL", "AFUL", "SYND")) or "copropri" in nom_l:
            otype = "copropriete"
        else:
            otype = "societe"
    ot = _pack(otype, indivision=(otype == "indivision"),
               identifiable=(otype not in ("inconnu", "personne_physique")), categorie=nom or forme)
    ot["owner_name"] = nom or None
    ot["forme_juridique"] = forme or None
    return ot


def needs_spf(owner: dict) -> bool:
    """Faut-il une demande SPF ? Oui si le propriétaire n'est pas un interlocuteur identifié."""
    return not owner.get("identifiable", False)


def spf_letter(parcel: dict, *, demandeur: str | None = None, today: date | None = None) -> str:
    """Courrier de demande de renseignement au Service de la Publicité Foncière (SPF), pré-rempli
    avec la seule référence cadastrale (donnée publique). Aucune donnée personnelle. Texte brut."""
    d = (today or date.today()).strftime("%d/%m/%Y")
    idu = parcel.get("idu", "—")
    commune = parcel.get("commune", "—")
    section = parcel.get("section") or "—"
    numero = parcel.get("numero") or "—"
    surface = parcel.get("surface_m2")
    surf = f"{round(surface)} m²" if surface else "—"
    dem = demandeur or "[Votre nom / société]\n[Adresse]\n[Téléphone / courriel]"
    return f"""{dem}

Service de la Publicité Foncière (SPF) territorialement compétent
[Adresse du SPF de La Réunion]

À {commune}, le {d}

Objet : demande de renseignement hypothécaire / d'identification du propriétaire
Référence cadastrale : {idu} (commune de {commune}, section {section}, parcelle n° {numero}, ~{surf})

Madame, Monsieur,

Dans le cadre d'un projet d'acquisition foncière, je sollicite la communication des
renseignements relatifs à la situation juridique de la parcelle cadastrée ci-dessus
(identité du ou des propriétaires, servitudes et inscriptions publiées la concernant).

Je vous remercie de m'indiquer les pièces et le montant éventuel à joindre pour le
traitement de cette demande.

Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

[Signature]

—
Pré-rempli par LABUSE à partir de la référence cadastrale publique. Le SPF est la voie
légale d'identification d'un propriétaire ; LABUSE ne collecte aucune donnée nominative.
"""
