"""Export PDF d'un PROJET (copilote-projet, V3) — DOCUMENT DE PRÉSENTATION : la fiche de cadrage +
la SHORTLIST FIGÉE du projet (datée), chaque parcelle portant de la DONNÉE pure (SDP résiduelle
estimée, hauteurs du PLU calibré, zone). Même identité d'impression que la fiche parcelle (fond
blanc, menthe en accents, fontes du design system). Réutilise la palette/fontes de pdf_premium.

M130-2 : aucun verdict, rang, score, probabilité ni indice de complétude (doctrine exportables).
Les chiffres viennent du MOTEUR (shortlist figée + moteur déterministe), jamais de l'IA.
"""
from __future__ import annotations

from datetime import date

from fpdf import FPDF

from .export_commun import pied_de_page_pdf
from .pdf_premium import FONTS, LINE, MINT, MINT_SOFT, TXT, TXT_DIM, TXT_HI, TXT_MUT, _logo

TYPE_LABEL = {"logements": "Logements", "etudiant": "Logement étudiant",
              "bureaux": "Bureaux", "autre": "Projet"}
# M130-4 §E.2 — vocabulaire FERMÉ des causes d'absence de SDP (« résiduel nul » seul, ambigu, retiré).
# Quatre familles de contrainte + les états de donnée indisponible (distincts, honnêtes).
_CAUSE_LABEL = {
    "zone_non_constructible": "zone fermée à l'urbanisation",
    "zone_non_constructible_neuf": "zone fermée à l'urbanisation",
    "habitat_interdit": "logement non admis au règlement de la zone",
    "terrain_exigu": "résiduel nul après reculs et emprises",
    "capacite_nulle": "résiduel nul après reculs et emprises",
    "redhibitoire": "capacité annulée par les modulations : risque / pente / servitude",
    # états de donnée indisponible (pas une contrainte de zone) — dits, jamais confondus avec un « 0 »
    "hauteur_indispo": "hauteur PLU non renseignée au règlement",
    "hors_plu": "parcelle hors PLU (donnée indisponible)",
    "zone_non_resolue": "zone non outillée au règlement (donnée indisponible)",
    "bati_non_ingere": "bâti non mesurable (donnée manquante)",
    "indetermine": "indéterminée",
}


def _cause_txt(cause: str | None) -> str:
    """« zone_non_constructible:2AUe » → « zone fermée à l'urbanisation » (vocabulaire fermé §E.2)."""
    if not cause:
        return "non calculable"
    return _CAUSE_LABEL.get(str(cause).split(":", 1)[0], "non calculable")


def _fr(x: float) -> str:
    """M130-3 §F.2 — nombre en français : séparateur décimal VIRGULE, sans zéro parasite (3.5 → 3,5)."""
    s = f"{x:g}"
    return s.replace(".", ",")


def _num(v: int) -> str:
    """Entier à MILLIERS espacés (« 10 725 ») — sans manger les virgules LITTÉRALES d'une phrase
    (M130-8 §B.1/§B.2 : un `.replace(',', ' ')` global effaçait « , toutes » / « , soit »)."""
    return f"{v:,}".replace(",", " ")


def _src_propre(src: str | None) -> str | None:
    """M130-4/6 §E.3 — retire le point final parasite d'une citation (« p.84. » → « p.84 ») ET le point
    avant une parenthèse fermante des libellés « via renvoi » (« Source: p.154.) » → « … p.154) »)."""
    if not src:
        return src
    return src.rstrip().replace(".)", ")").rstrip(".")


# M130-6 §A — le CAS 3 (« résiduel calculé et NUL ») se reconnaît à la CAUSE, jamais à l'absence de
# nombre : reculs / emprises / modulations / logement non admis. (Le zonage fermé = cas 2, la famille.)
_CASE3_CAUSES = {"terrain_exigu", "capacite_nulle", "redhibitoire", "habitat_interdit"}


def _sdp_calcul_nul(it: dict) -> bool:
    """M130-7 §D — la SDP a été CALCULÉE et vaut zéro (≠ supprimée par la famille de zone, ≠ donnée
    indisponible). Testé sur l'ÉTAT du résiduel, jamais sur la famille de la zone dominante :
      · famille A/N → supprimée (pas calculée) → False ;
      · cause ∈ {reculs, emprises, modulations, logement non admis} → True ;
      · aucune cause, non chiffrée, pas A/N → résiduel nul calculé (cas de HY0897 : Ug, sdp 0) → True.
    Aligne la variante multi-zones sur la ligne SDP, qui affiche déjà « résiduel nul » dans ces cas."""
    if it.get("non_constructible"):
        return False
    cause0 = (it.get("sdp_indispo") or "").split(":", 1)[0]
    if cause0:
        return cause0 in _CASE3_CAUSES
    return not it.get("sdp_chiffree")


class _Pdf(FPDF):
    def header(self):
        self.set_draw_color(*MINT)
        self.set_line_width(0.6)
        self.line(14, 8, self.w - 14, 8)
        self.set_line_width(0.2)
        self.set_y(12)

    def footer(self):
        # M6 2a : pied de page commun (non-garantie + disclaimer CU au mot près +
        # attributions sources + date de génération) — une seule vérité, export_commun.
        pied_de_page_pdf(self, "dossier projet")


def _perimetre_label(cadrage: dict) -> str:
    # M120 — le périmètre vit dans le cadrage (facette `communes`).
    cs = (cadrage or {}).get("communes") or []
    if not cs:
        return "Toute l'île"
    return cs[0] if len(cs) == 1 else f"{len(cs)} communes"


def render_projet_pdf(projet: dict, shortlist: dict) -> bytes:
    cadrage = projet.get("cadrage") or {}
    identite = projet.get("identite") or {}
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=26)   # pied de page commun (4 lignes)
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    # ── En-tête produit
    _logo(pdf, 14, pdf.get_y() + 1, 13)
    pdf.set_x(30)
    pdf.set_font("grotesk", size=13)
    pdf.set_text_color(*MINT)
    pdf.cell(0, 6, "LABUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    # M130-2 §5.1 — dire ce qu'est le document : une PRÉSENTATION.
    pdf.cell(0, 4, "Radar foncier premium — La Réunion · dossier PROJET · document de présentation",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Titre du projet
    pdf.set_font("grotesk", size=16)
    pdf.set_text_color(*TXT_HI)
    pdf.multi_cell(0, 7, projet.get("nom") or "Projet", new_x="LMARGIN", new_y="NEXT")
    # M130-2 §1.2 — DEUX dates distinctes, nommées : figeage du cadrage ET génération du document.
    # M130-4 §D : jamais « figé le — » quand la date est absente → « Cadrage non figé ».
    figee_le = shortlist.get("figee_le")
    cadrage_txt = f"Cadrage figé le {figee_le}" if figee_le else "Cadrage non figé"
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_MUT)
    pdf.cell(0, 4.6, f"{cadrage_txt}   ·   Document généré le {date.today().isoformat()}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Fiche de cadrage
    def ligne(label: str, valeur: str) -> None:
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(34, 5, label)
        pdf.set_text_color(*TXT_HI)
        pdf.multi_cell(0, 5, valeur, new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(*LINE)
    y0 = pdf.get_y()
    pdf.rect(14, y0, pdf.w - 28, 1, style="F")  # filet fin
    pdf.ln(2)
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_MUT)
    pdf.cell(0, 5, "FICHE DE CADRAGE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    # M120 — un champ VIDE ne s'imprime pas (jamais de « — »). Programme/budget sont INFORMATIFS.
    remplies: list[tuple[str, str]] = []
    t = identite.get("type_logement")
    if t and TYPE_LABEL.get(t):
        remplies.append(("Programme", f"{TYPE_LABEL[t]} (indicatif)"))
    remplies.append(("Périmètre", _perimetre_label(cadrage)))
    if cadrage.get("sdpMin"):
        remplies.append(("SDP min.", f"{int(cadrage['sdpMin']):,} m² (facette du cadrage)".replace(",", " ")))
    if cadrage.get("surfaceMin") or cadrage.get("surfaceMax"):
        # M130-4 §E.1 — pas d'« ∞ » : « X m² et plus » / « jusqu'à Y m² » / « X – Y m² », milliers espacés.
        lo, hi = cadrage.get("surfaceMin"), cadrage.get("surfaceMax")
        _sm = lambda v: f"{int(v):,}".replace(",", " ")   # noqa: E731 — milliers espacés
        if lo and hi:
            surf = f"{_sm(lo)} – {_sm(hi)} m²"
        elif lo:
            surf = f"{_sm(lo)} m² et plus"
        else:
            surf = f"jusqu'à {_sm(hi)} m²"
        remplies.append(("Surface", surf))
    if identite.get("budget_eur"):
        remplies.append(("Budget foncier", f"{identite['budget_eur'] / 1000:,.0f} k€ (indicatif)".replace(",", " ")))
    for k, v in remplies:
        ligne(k, v)
    pdf.ln(3)

    # ── Les parcelles de la shortlist figée (§2.2 titre neutre, §2.3 ordre neutre, §2.1 aucun verdict)
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_MUT)
    if not shortlist.get("figee"):
        # M130-2 §1.3 / §4.3 — pas de shortlist figée exploitable : le DIRE, ne rien fabriquer.
        pdf.cell(0, 5, "SHORTLIST DU CADRAGE", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("inter", size=8)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(0, 4.6, "Ce projet n'a pas de shortlist figée exploitable. Lancez (ou "
                       "relancez) le cadrage dans l'application pour figer et dater la sélection — "
                       "aucune liste n'est fabriquée à l'export.", new_x="LMARGIN", new_y="NEXT")
    else:
        n = shortlist.get("n", 0)
        pdf.cell(0, 5, f"PARCELLES DE LA SHORTLIST  ·  {n:,} parcelle(s), cadrage figé le {figee_le}"
                 .replace(",", " "), new_x="LMARGIN", new_y="NEXT")
        # M130-4/5 §A — ligne d'état de la liste INCONDITIONNELLE (jamais d'omission) : 3 états sur le
        # TOTAL de la population dont la shortlist est extraite (`total`, = `_run_cadrage`). None → État 3
        # (échec RÉEL de requête) ; un 0 légitime n'est pas un échec. Rang de sélection jamais muet.
        total = shortlist.get("total")
        neutre = ("Élargir la shortlist ne supprime pas ce rang : seule une liste complète ou un tri "
                  "explicite (surface) est neutre.")   # §B — plus de fausse issue « chercher plus »
        # M130-6/8 §C/§B.1 — « dont ~ {t0} classées à l'étage 0 » ; quand t0 vaut EXACTEMENT le total,
        # « toutes classées à l'étage 0 » (pas de tilde+valeur redondants).
        t0 = shortlist.get("total_etage0")
        if t0 is not None and total is not None and t0 == total:
            dont0 = ", toutes classées à l'étage 0"
        elif t0:
            dont0 = f", dont ~ {_num(t0)} classées à l'étage 0"
        else:
            dont0 = ""
        if total is None:
            etat = ("Nombre total de parcelles retenues par le cadrage : INDISPONIBLE (requête en "
                    "échec). Cette liste peut être tronquée ; si elle l'est, les parcelles ont été "
                    "sélectionnées par probabilité de mutation — un rang non visible. " + neutre)
        elif total > n:
            etat = (f"Liste plafonnée : {n} parcelles figées sur ~ {_num(total)} retenues par le "
                    f"cadrage{dont0} (à ce jour). Les figées ont été SÉLECTIONNÉES par probabilité de "
                    "mutation (critère interne du moteur) — un rang non visible ; elles sont présentées "
                    "ici par ordre géographique. " + neutre)
        else:
            etat = (f"Liste complète : les {n} parcelles retenues par le cadrage sont toutes "
                    "présentées. Aucune sélection, aucun rang.")
        # M130-7 §A/§B — l'ÉTAGE 0 servi est dit par son EFFET SUR LA DONNÉE, sans nommer statut, run
        # ni scoring (pas de verdict/probabilité dans un exportable). §C : incise vers l'exception
        # multi-zones quand des parcelles écartées gardent une part constructible.
        k0 = shortlist.get("etage0_count", 0)
        exc = " — voir toutefois les parcelles multi-zones ci-dessous" if \
            shortlist.get("etage0_constructible") else ""
        if k0 and k0 >= n:
            etat += (" Cette sélection est intégralement composée de parcelles que le moteur a écartées "
                     f"de son vivier exploitable. Elles n'ont pas vocation à être instruites en l'état{exc}.")
        elif k0:
            etat += (f" {k0} des {n} parcelles figées ont été écartées du vivier exploitable par le "
                     f"moteur ; elles n'ont pas vocation à être instruites en l'état{exc}.")
        pdf.ln(0.5)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.6, etat, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        for it in shortlist.get("parcelles", []):
            lignes = _lignes_donnees(it)
            # M130-7 §B — keep-together sur le bloc ENTIER (IDU + adresse + toutes les lignes, y compris
            # la ligne multi-zones qui peut faire 2-3 lignes). On mesure la hauteur RÉELLE de chaque
            # ligne (retours à la ligne compris, dry_run) — plus aucune veuve d'un mot en tête de page.
            adr = it.get("adresse_ban") or "Adresse non disponible"
            pdf.set_font("inter", size=7.5)
            _bloc_h = 5.0 + 1.5
            _bloc_h += pdf.multi_cell(pdf.epw - 4, 4.4, adr, dry_run=True, output="HEIGHT",
                                      new_x="RIGHT", new_y="TOP")
            for dl in lignes:
                _bloc_h += pdf.multi_cell(pdf.epw - 4, 4.4, dl, dry_run=True, output="HEIGHT",
                                          new_x="RIGHT", new_y="TOP")
            if pdf.get_y() + _bloc_h > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.set_font("mono", size=8.5)
            pdf.set_text_color(*TXT_HI)
            pdf.cell(0, 5, f"{it['idu']}  ({it.get('section', '')} {it.get('numero', '')})"
                           f"  ·  {it.get('commune', '')}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("inter", size=7.5)
            pdf.set_text_color(*(TXT_MUT if it.get("adresse_ban") else TXT_DIM))
            pdf.cell(4, 4.4, "")
            pdf.cell(0, 4.4, adr, new_x="LMARGIN", new_y="NEXT")
            # ── données par parcelle (chacune Sourcé ou Estimé — §3.5)
            for dl in lignes:
                pdf.set_text_color(*MINT)
                pdf.cell(4, 4.4, "·")
                pdf.set_text_color(*TXT)
                pdf.multi_cell(0, 4.4, dl, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)

    # ── mention (§4.1 — décrit EXACTEMENT ce qui est rendu ; aucune promesse de score)
    pdf.ln(1)
    pdf.set_fill_color(*MINT_SOFT)
    pdf.set_font("inter", size=7)
    pdf.set_text_color(*TXT_MUT)
    pdf.multi_cell(0, 4.4, "Les données par parcelle viennent du moteur déterministe : SDP résiduelle "
                   "(estimée), hauteurs du PLU calibré (égout et faîtage) et zone PLU. Aucun verdict, "
                   "score ni classement ; l'ordre est géographique (commune, section, numéro). L'IA ne "
                   "produit aucun chiffre. La SDP résiduelle est une surface de plancher cumulée sur "
                   "plusieurs niveaux : elle peut dépasser la surface de la parcelle.",
                   border=0, fill=True, new_x="LMARGIN", new_y="NEXT")

    # ── §5.2 — CE QUE CE DOCUMENT NE PEUT PAS DIRE (limites propres au projet)
    pdf.ln(2)
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_MUT)
    pdf.cell(0, 5, "CE QUE CE DOCUMENT NE PEUT PAS DIRE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)
    pdf.set_font("inter", size=7)
    pdf.set_text_color(*TXT_DIM)
    # M130-3 §C — la ligne « shortlist datée » s'ADAPTE : si pas de shortlist figée, ne pas affirmer un
    # figeage inexistant ni afficher une date à trou.
    ligne_shortlist = (
        f"La shortlist est datée (figée le {figee_le}) : elle peut différer de l'état actuel du "
        "cadrage si les critères ou les données ont changé depuis."
        if shortlist.get("figee") else
        "Ce projet n'a pas encore de shortlist figée : aucune parcelle n'est présentée tant que le "
        "cadrage n'a pas été lancé et daté dans l'application."
    )
    for lim in (
        "Le cadrage est un jeu de filtres géographiques et réglementaires, pas un avis d'opportunité.",
        ligne_shortlist,
        "Aucune parcelle n'est validée : la constructibilité et la faisabilité restent à instruire "
        "(fiche parcelle, règlement de zone, certificat d'urbanisme).",
    ):
        pdf.set_text_color(*TXT_MUT)
        pdf.cell(4, 4, "·")
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(0, 4, lim, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def _lignes_donnees(it: dict) -> list[str]:
    """Les lignes de DONNÉE d'une parcelle — chacune porte Sourcé ou Estimé (§3.5). Jamais un verdict.
    M130-3 : famille A/N → aucune SDP chiffrée (§A) ; ligne Hauteur TOUJOURS présente avec état (§B) ;
    surface parcelle (§F.1) ; virgule décimale (§F.2) ; « aucune » ≠ « ~ 0 » (§F.3) ; renvoi (§F.4)."""
    out: list[str] = []
    # §F.1 surface de la parcelle (Sourcé — cadastre) : permet de vérifier un filtre de surface.
    if it.get("surface_m2") is not None:
        out.append(f"Surface parcelle : {int(it['surface_m2']):,} m² (Sourcé — cadastre)".replace(",", " "))
    # §A / §3.1 SDP résiduelle. La FAMILLE décide : A/N = fermée à l'urbanisation → jamais de chiffre
    # (§E.2 vocabulaire fermé). §F.3 : 0/None → « aucune », pas « ~ 0 ».
    if it.get("non_constructible"):
        out.append("SDP résiduelle : aucune (zone fermée à l'urbanisation)")
    elif it.get("sdp_indispo"):
        out.append(f"SDP résiduelle : aucune ({_cause_txt(it['sdp_indispo'])})")
    elif it.get("sdp_m2"):
        out.append(f"SDP résiduelle ~ {it['sdp_m2']:,} m² (Estimé)".replace(",", " "))
    else:
        out.append("SDP résiduelle : aucune (résiduel nul après reculs et emprises)")
    # §B / §3.2 Hauteur PLU : ligne TOUJOURS présente, avec état explicite (panne ≠ absence).
    he, hf = it.get("he_m"), it.get("hf_m")
    renvoi = f" · via renvoi : {_src_propre(it['hauteur_renvoi'])}" if it.get("hauteur_renvoi") else ""  # §F.4/E.3
    if he is not None or hf is not None:
        tag = "Sourcé — PLU calibré" if it.get("hauteur_calibree") else "Estimé — générique"
        eg = f"égout {_fr(he)} m" if he is not None else "égout non réglementé"
        fa = f"faîtage {_fr(hf)} m" if hf is not None else "faîtage non réglementé"
        src = _src_propre(it.get("hauteur_source"))                        # §E.3 : point final retiré
        out.append(f"Hauteur PLU : {eg} · {fa} ({tag}{(' · ' + src) if src else ''}{renvoi})")
    elif it.get("non_constructible"):
        out.append("Hauteur PLU : non applicable (zone fermée à l'urbanisation)")
    elif it.get("zone_resolue"):
        out.append("Hauteur PLU : non réglementée pour cette zone")
    else:
        out.append("Hauteur PLU : règlement non outillé pour cette zone (donnée indisponible)")
    # §3.3 zone PLU + famille correcte (U = urbaine, AU = à urbaniser) — Sourcé + millésime amont (§6).
    if it.get("zone_code"):
        fam = it.get("zone_famille")
        mil = it.get("zone_millesime")
        out.append(f"Zone PLU {it['zone_code']}{(' — ' + fam) if fam else ''} "
                   f"(Sourcé — GPU/PLU, {('millésime ' + mil) if mil else 'millésime non renseigné'})")
    # §C — MULTI-ZONE dite (réserve M130-3) : une partie constructible ne se tait pas. Aucune SDP
    # partielle chiffrée — on dit l'existence, pas la quantité. Vaut dans les DEUX sens (dominante
    # constructible avec SDP chiffrée = SDP calculée sur une sous-zone → à signaler aussi).
    if it.get("multi_zone"):
        parts = it.get("zones_parts") or []
        if parts and all(p[2] is not None for p in parts):
            liste = " · ".join(f"{lib} ({fam or '—'}) ~ {pct} %" for lib, fam, pct in parts)
            # §C : reliquat non muet — zones sous le seuil d'affichage / trou de géométrie (≥ 2 %).
            reste = it.get("zones_reste") or 0
            if reste >= 2:
                liste += f" · autres zones ~ {reste} %"
        else:
            liste = "zones " + ", ".join(p[0] for p in parts) + " — parts non disponibles"
        # M130-8 §A — on ne PROMET JAMAIS une part constructible sans l'avoir vérifiée. `pc` = la plus
        # grande part réellement OUVERTE (U / 1AU ; exclut A, N, 2AU) — calculée en amont par
        # `_part_ouverte`. Quatre cas, choisis sur l'état du résiduel PUIS l'existence d'une part ouverte.
        pc = it.get("part_constructible")   # (libellé, pct) ou None
        if it.get("sdp_chiffree"):                                        # cas 3 (SDP > 0) — inchangé
            from .projets import _part_ouverte
            tout_ouvert = bool(parts) and all(_part_ouverte(lib) for lib, _f, _p in parts)
            tail = ("SDP calculée sur la partie constructible ; les autres parts relèvent d'un autre "
                    "règlement de zone, à instruire." if tout_ouvert else   # §E.1
                    "SDP calculée sur la partie constructible ; les autres parts restent à instruire.")
            out.append(f"Parcelle multi-zones : {liste} — {tail}")
        elif _sdp_calcul_nul(it):                                         # cas 4 (calculé et NUL) — inchangé
            out.append(f"Parcelle multi-zones : {liste} — le résiduel calculé est nul sur la part "
                       f"{it.get('zone_code')} ; les autres parts restent à instruire.")
        elif pc:                                                          # cas 1 : SDP supprimée + part OUVERTE
            surf = round(pc[1] / 100 * (it.get("surface_m2") or 0))   # §B.2 surface de la part (Estimé)
            surf_txt = f", soit ~ {_num(surf)} m² — Estimé" if surf else ""
            if it.get("etage0"):     # sous-cas étage 0 (M130-7 §C), désormais gardé par pc non vide
                out.append(f"Parcelle multi-zones : {liste} — écartée du vivier, mais une part {pc[0]} "
                           f"(~ {pc[1]} %{surf_txt}) est constructible : à instruire séparément.")
            else:
                out.append(f"Parcelle multi-zones : {liste} — la SDP n'est pas chiffrée ; une part "
                           f"{pc[0]} (~ {pc[1]} %{surf_txt}) est constructible et reste à instruire.")
        else:                                                             # cas 2 : AUCUNE part ouverte
            out.append(f"Parcelle multi-zones : {liste} — aucune des parts n'est ouverte à l'urbanisation.")
    return out
