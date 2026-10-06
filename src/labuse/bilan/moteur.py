"""BILAN-1 Lot 2 — moteur du bilan promoteur.

Tout le calcul du bilan vit ICI (doctrine 5 : aucun calcul dans le front). Le
front envoie les saisies, le moteur rend HT / TVA / TTC par poste, les totaux par
bloc, le CA par produit, la marge (€ et % du CA HT), et — au choix — la marge au
prix d'achat saisi OU le prix maximal du terrain pour une marge cible.

Doctrine : rien n'entre dans le calcul que le client n'a pas posé. Un poste sans
valeur et non « Sans objet » laisse le bilan incomplet → ni marge ni export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalogue import Catalogue, Poste, charger_catalogue

# États d'un poste (doctrine 4).
SOURCE = "source"
SAISI = "saisi"
REPERE = "repere"
RATIOS = "ratios"
SANS_OBJET = "sans_objet"
A_RENSEIGNER = "a_renseigner"

_RENSEIGNES = {SOURCE, SAISI, REPERE, RATIOS}


@dataclass
class Produit:
    """Une ligne du programme : un produit (libre · PLS · LLI)."""

    libelle: str
    lots: float | None = None
    suv: float | None = None
    prix_ttc_m2_suv: float | None = None
    tva: float | None = None  # taux de TVA de vente (0.021 social, 0.085 libre)

    @property
    def complet(self) -> bool:
        return None not in (self.lots, self.suv, self.prix_ttc_m2_suv, self.tva)

    @property
    def ca_ttc(self) -> float | None:
        if self.suv is None or self.prix_ttc_m2_suv is None:
            return None
        return self.suv * self.prix_ttc_m2_suv

    @property
    def ca_ht(self) -> float | None:
        ttc = self.ca_ttc
        if ttc is None or self.tva is None:
            return None
        return ttc / (1.0 + self.tva)


@dataclass
class SaisiePoste:
    """Ce que le client a posé sur un poste. Rien d'autre n'entre dans le calcul."""

    valeur: float | None = None  # taux (%) · €/unité · forfait selon le mode
    etat: str = A_RENSEIGNER
    tva: float | None = None  # pour les lignes « TVA à saisir »
    assiette_valeur: float | None = None  # pour notP (prêt) / cvae (valeur ajoutée)


@dataclass
class Programme:
    terrain: float | None = None  # m² (cadastre / union d'un assemblage) — Sourcé
    surface_taxable: float | None = None  # m²
    loyer: float | None = None  # €/m² de SUV (assiette de la garantie locataire)


@dataclass
class EntreesBilan:
    programme: Programme = field(default_factory=Programme)
    produits: list[Produit] = field(default_factory=list)
    postes: dict[str, SaisiePoste] = field(default_factory=dict)
    mode: str = "marge"  # "marge" | "prix"
    marge_cible: float | None = None  # % du CA HT (saisie, sans défaut)

    def saisie(self, pid: str) -> SaisiePoste:
        return self.postes.get(pid, SaisiePoste())


@dataclass
class LigneBilan:
    id: str
    libelle: str
    bloc: str
    assiette: str | None
    assiette_valeur: float | None
    taux_ou_montant: float | None
    etat: str
    ht: float | None
    tva: float | None
    ttc: float | None
    manquant: bool


@dataclass
class TotalBloc:
    id: str
    titre: str
    ht: float
    tva: float
    ttc: float
    complet: bool
    manquants: int


@dataclass
class ResultatBilan:
    lignes: list[LigneBilan]
    blocs: list[TotalBloc]
    produits: list[dict[str, Any]]
    produits_totaux: dict[str, float | None]
    depenses_ht: float | None
    depenses_tva: float | None
    depenses_ttc: float | None
    ca_ht: float | None
    ca_tva: float | None
    ca_ttc: float | None
    tva_residuelle: float | None
    resultat_net: float | None
    marge_pct: float | None
    cash_flow: float | None
    aleas: float | None
    resultat_sans_aleas: float | None
    marge_sans_aleas_pct: float | None
    ratios: list[tuple[str, str]]
    prix_max_terrain: float | None
    prix_max_terrain_m2: float | None
    prix_achat_dvf: float | None
    total_postes: int
    postes_renseignes: int
    manquants: list[str]
    vraisemblance: list[dict[str, str]]  # alertes non bloquantes [{cible, message}]

    @property
    def complet(self) -> bool:
        return not self.manquants


class Moteur:
    def __init__(self, catalogue: Catalogue | None = None) -> None:
        self.cat = catalogue or charger_catalogue()
        self._postes = self.cat.postes()

    # -- résolution des assiettes ------------------------------------------
    def _assiette(self, poste: Poste, saisie: SaisiePoste, ctx: dict) -> float | None:
        a = poste.assiette
        prog: Programme = ctx["programme"]
        pt = ctx["produits"]
        if a == "forfait" or a is None:
            return None
        if a == "terrain":
            return prog.terrain
        if a == "surface_taxable":
            return prog.surface_taxable
        if a == "suv":
            return pt["suv"]
        if a == "lots":
            return pt["lots"]
        if a == "prix_terrain":
            return ctx.get("prix_terrain")
        if a in ("pret", "valeur_ajoutee"):
            return saisie.assiette_valeur
        if a == "ca_ttc":
            return pt["ca_ttc"]
        if a == "ca_produit_1":
            return pt["ca"][0] if len(pt["ca"]) > 0 else None
        if a == "ca_produit_2":
            return pt["ca"][1] if len(pt["ca"]) > 1 else None
        if a == "construction":
            return ctx.get("construction")
        if a == "demi_construction_ttc":
            c = ctx.get("construction")
            return None if c is None else c * (1.0 + self._tva_dom()) / 2.0
        if a == "total2_ttc":
            return ctx.get("total2_ttc")
        if a == "total2_ht":
            return ctx.get("total2_ht")
        # Assiettes composées à la main dans le modèle de la promotrice (assurances) :
        # base = total (2) + étude de sol − imprévus (techniques). Reproduites à l'identique.
        if a == "total2_ttc_sol_imprevus":
            t2, sol, imp = ctx.get("total2_ttc"), ctx.get("sol_ttc"), ctx.get("aleaC_ttc")
            return None if None in (t2, sol, imp) else t2 - imp + sol
        if a == "total2_ht_sol_imprevus":
            t2, sol, imp = ctx.get("total2_ht"), ctx.get("sol_ht"), ctx.get("aleaC_ht")
            return None if None in (t2, sol, imp) else t2 - imp + sol
        if a == "loyers_annuels":
            if prog.loyer is None or pt["suv"] is None:
                return None
            return prog.loyer * pt["suv"]
        return None

    def _tva_dom(self) -> float:
        return float(self.cat.tva_legales["dom_standard"])

    def _taux_tva(self, poste: Poste, saisie: SaisiePoste) -> float | None:
        if saisie.etat == SANS_OBJET:
            return 0.0
        if isinstance(poste.tva, (int, float)):
            return float(poste.tva)
        if poste.tva == "a_saisir":
            return saisie.tva  # None si non posé → poste incomplet
        return None

    def _ligne_ht(
        self, poste: Poste, saisie: SaisiePoste, assiette: float | None, taux_tva: float | None
    ) -> tuple[float | None, float | None, float | None]:
        """Retourne (ht, tva, ttc) ; None si indéterminable (→ poste à renseigner)."""
        if saisie.etat == SANS_OBJET:
            return 0.0, 0.0, 0.0
        if saisie.valeur is None:
            return None, None, None
        # montant brut selon le mode (en HT ou en TTC selon poste.base)
        if poste.mode == "forfait":
            brut = saisie.valeur
        elif poste.mode == "pct":
            if assiette is None:
                return None, None, None
            brut = assiette * saisie.valeur / 100.0
        elif poste.mode == "unit":
            if assiette is None:
                return None, None, None
            brut = assiette * saisie.valeur
        else:  # pragma: no cover - mode inconnu
            return None, None, None
        if taux_tva is None:
            return None, None, None
        if poste.base == "ttc":
            ttc = brut
            ht = ttc / (1.0 + taux_tva)
            tva = ttc - ht
        else:
            ht = brut
            tva = ht * taux_tva
            ttc = ht + tva
        return ht, tva, ttc

    # -- calcul principal ---------------------------------------------------
    def calculer(self, e: EntreesBilan, _achat_ht_force: float | None = None) -> ResultatBilan:
        # Totaux produits
        produits_vue = []
        lots = suv = ca_ttc = ca_ht = 0.0
        ca = []
        prod_ok = bool(e.produits)
        for p in e.produits:
            if not p.complet:
                prod_ok = False
                ca.append(None)
            else:
                lots += p.lots  # type: ignore[arg-type]
                suv += p.suv  # type: ignore[arg-type]
                ca_ttc += p.ca_ttc  # type: ignore[operator]
                ca_ht += p.ca_ht  # type: ignore[operator]
                ca.append(p.ca_ttc)
            produits_vue.append(
                {
                    "libelle": p.libelle,
                    "lots": p.lots,
                    "suv": p.suv,
                    "prix_ttc_m2_suv": p.prix_ttc_m2_suv,
                    "tva": p.tva,
                    "ca_ttc": p.ca_ttc,
                    "ca_ht": p.ca_ht,
                    "complet": p.complet,
                }
            )
        pt = {
            "ok": prod_ok,
            "lots": lots if prod_ok else None,
            "suv": suv if prod_ok else None,
            "ca_ttc": ca_ttc if prod_ok else None,
            "ca_ht": ca_ht if prod_ok else None,
            "ca": ca,
        }

        ctx: dict[str, Any] = {"programme": e.programme, "produits": pt}

        def ht_de(pid: str) -> float | None:
            poste = self.cat.poste(pid)
            s = e.saisie(pid)
            if pid == "achat" and _achat_ht_force is not None:
                return _achat_ht_force
            a = self._assiette(poste, s, ctx)
            taux = self._taux_tva(poste, s)
            return self._ligne_ht(poste, s, a, taux)[0]

        # Étapes de dépendance : achat (prix terrain) -> construction -> bloc C
        ctx["prix_terrain"] = ht_de("achat")
        ctx["construction"] = ht_de("constr")
        # total du bloc Construction & honoraires (pour DO/TRC)
        c_ht = 0.0
        c_tva = 0.0
        c_ok = True
        for poste in self.cat.blocs[1].postes:  # bloc C
            s = e.saisie(poste.id)
            a = self._assiette(poste, s, ctx)
            taux = self._taux_tva(poste, s)
            h, t, _ = self._ligne_ht(poste, s, a, taux)
            if h is None or t is None:
                c_ok = False
            else:
                c_ht += h
                c_tva += t
        ctx["total2_ht"] = (c_ht) if c_ok else None
        ctx["total2_ttc"] = (c_ht + c_tva) if c_ok else None

        # Étude de sol & imprévus techniques : composent les assiettes d'assurances
        # (D.O / C.N.R, TRC) comme dans le tableur de la promotrice (0 € d'écart).
        def ligne_complete(pid: str) -> tuple[float | None, float | None]:
            poste = self.cat.poste(pid)
            s = e.saisie(pid)
            a = self._assiette(poste, s, ctx)
            taux = self._taux_tva(poste, s)
            h, _, c = self._ligne_ht(poste, s, a, taux)
            return h, c

        ctx["sol_ht"], ctx["sol_ttc"] = ligne_complete("sol")
        ctx["aleaC_ht"], ctx["aleaC_ttc"] = ligne_complete("aleaC")

        # Toutes les lignes
        lignes: list[LigneBilan] = []
        blocs_tot: list[TotalBloc] = []
        manquants: list[str] = []
        renseignes = 0
        for bloc in self.cat.blocs:
            b_ht = b_tva = 0.0
            b_manq = 0
            for poste in bloc.postes:
                s = e.saisie(poste.id)
                if poste.id == "achat" and _achat_ht_force is not None:
                    a = None
                    h, t, c = _achat_ht_force, 0.0, _achat_ht_force
                else:
                    a = self._assiette(poste, s, ctx)
                    taux = self._taux_tva(poste, s)
                    h, t, c = self._ligne_ht(poste, s, a, taux)
                manquant = h is None or t is None
                lignes.append(
                    LigneBilan(
                        id=poste.id,
                        libelle=poste.libelle,
                        bloc=bloc.id,
                        assiette=poste.assiette,
                        assiette_valeur=a,
                        taux_ou_montant=s.valeur,
                        etat=s.etat,
                        ht=h,
                        tva=t,
                        ttc=c,
                        manquant=manquant,
                    )
                )
                if manquant:
                    manquants.append(poste.id)
                    b_manq += 1
                else:
                    b_ht += h  # type: ignore[arg-type]
                    b_tva += t  # type: ignore[arg-type]
                    if s.etat in _RENSEIGNES or s.etat == SANS_OBJET:
                        renseignes += 1
            blocs_tot.append(
                TotalBloc(
                    id=bloc.id,
                    titre=bloc.titre,
                    ht=b_ht,
                    tva=b_tva,
                    ttc=b_ht + b_tva,
                    complet=b_manq == 0,
                    manquants=b_manq,
                )
            )

        if not pt["ok"]:
            manquants.append("produits")

        total_postes = len(self._postes)
        complet = not manquants

        dep_ht = sum(b.ht for b in blocs_tot) if complet else None
        dep_tva = sum(b.tva for b in blocs_tot) if complet else None
        dep_ttc = (dep_ht + dep_tva) if complet else None

        res_net = tva_res = marge = cash = aleas_tot = res_sa = marge_sa = None
        if complet:
            tva_res = (pt["ca_ttc"] - pt["ca_ht"]) - dep_tva  # type: ignore[operator]
            res_net = pt["ca_ht"] - dep_ht  # type: ignore[operator]
            marge = res_net / pt["ca_ht"] if pt["ca_ht"] else None
            mod = next((ln.ht for ln in lignes if ln.id == "mod"), 0.0) or 0.0
            cash = res_net + mod
            aleas_tot = sum(
                (ln.ht or 0.0) for ln in lignes if self.cat.poste(ln.id).alea
            )
            res_sa = res_net + aleas_tot
            marge_sa = res_sa / pt["ca_ht"] if pt["ca_ht"] else None

        # Prix max du terrain (sens « prix ») — modèle linéaire exact
        prix_max = prix_max_m2 = None
        if _achat_ht_force is None and e.mode == "prix" and e.marge_cible is not None and pt["ok"]:
            prix_max = self._prix_max_terrain(e, pt["ca_ht"])
            if prix_max is not None and e.programme.terrain:
                prix_max_m2 = prix_max / e.programme.terrain

        ratios = self._ratios(lignes, blocs_tot, pt, ctx, complet, res_net)
        vrais = self._vraisemblance(lignes, pt, e.programme, marge, complet)

        return ResultatBilan(
            lignes=lignes,
            blocs=blocs_tot,
            produits=produits_vue,
            produits_totaux=pt,  # type: ignore[arg-type]
            depenses_ht=dep_ht,
            depenses_tva=dep_tva,
            depenses_ttc=dep_ttc,
            ca_ht=pt["ca_ht"],
            ca_tva=(pt["ca_ttc"] - pt["ca_ht"]) if pt["ok"] else None,
            ca_ttc=pt["ca_ttc"],
            tva_residuelle=tva_res,
            resultat_net=res_net,
            marge_pct=marge,
            cash_flow=cash,
            aleas=aleas_tot,
            resultat_sans_aleas=res_sa,
            marge_sans_aleas_pct=marge_sa,
            ratios=ratios,
            prix_max_terrain=prix_max,
            prix_max_terrain_m2=prix_max_m2,
            prix_achat_dvf=None,  # info DVF attachée par la route, hors calcul
            total_postes=total_postes,
            postes_renseignes=renseignes,
            manquants=manquants,
            vraisemblance=vrais,
        )

    def _vraisemblance(self, lignes, pt, programme, marge, complet) -> list[dict[str, str]]:
        """Alertes de vraisemblance NON bloquantes (le bilan se calcule quand même) :
        une valeur hors des bornes usuelles est signalée « à vérifier », jamais corrigée."""
        out: list[dict[str, str]] = []
        suv = pt["suv"]
        # Coût de construction au m² SUV (= le RATIO servi : construction + imprévus ÷ SUV)
        constr = next((ln for ln in lignes if ln.id == "constr"), None)
        aleaC = next((ln for ln in lignes if ln.id == "aleaC"), None)
        if constr and constr.ht is not None and suv:
            cout = (constr.ht + (aleaC.ht or 0.0 if aleaC else 0.0)) / suv
            if cout < 1000 or cout > 5000:
                out.append({
                    "cible": "cout_const",
                    "message": "Coût de construction inhabituel (hors 1 000–5 000 €/m² SUV), à vérifier.",
                })
        # Surface taxable très basse par rapport à la SUV totale
        stax = programme.surface_taxable
        if stax is not None and suv and stax < 0.5 * suv:
            out.append({
                "cible": "stax",
                "message": "Surface taxable inhabituellement basse (< 50 % de la SUV totale), à vérifier.",
            })
        if complet and marge is not None and marge > 0.25:
            out.append({
                "cible": "marge",
                "message": "Marge inhabituellement élevée (> 25 % du CA HT), à vérifier.",
            })
        return out

    def _prix_max_terrain(self, e: EntreesBilan, ca_ht: float | None) -> float | None:
        """Prix d'achat du terrain maximal pour atteindre la marge cible.

        dep_ht(achat) = other + achat·(1+K) avec K la somme des coefficients des
        postes assis sur le prix du terrain. On mesure `other` et `(1+K)` par deux
        évaluations (achat = 0 et achat = 1) ; exige que tout le reste soit posé.
        """
        if ca_ht is None:
            return None
        # tout sauf « achat » doit être résolu
        test = self.calculer(e, _achat_ht_force=0.0)
        reste = [m for m in test.manquants if m != "achat"]
        if reste:
            return None
        dep0 = test.depenses_ht
        dep1 = self.calculer(e, _achat_ht_force=1.0).depenses_ht
        if dep0 is None or dep1 is None:
            return None
        un_plus_k = dep1 - dep0  # = 1 + K
        if un_plus_k <= 0:
            return None
        cible = e.marge_cible / 100.0  # type: ignore[operator]
        achat = (ca_ht * (1.0 - cible) - dep0) / un_plus_k
        return achat

    def _ratios(self, lignes, blocs, pt, ctx, complet, res_net):
        def ht(pid):
            return next((ln.ht for ln in lignes if ln.id == pid), None)

        def euro(x):
            return f"{round(x):,} €".replace(",", " ") if x is not None else "—"

        suv = pt["suv"]
        rows: list[tuple[str, str]] = []
        constr = ht("constr")
        aleaC = ht("aleaC") or 0.0
        rows.append(
            (
                "Coût const. m² SUV HT",
                euro((constr + aleaC) / suv) if complet and constr is not None and suv else "—",
            )
        )
        rows.append(
            ("Prix moyen au m² SUV HT", euro(pt["ca_ht"] / suv) if pt["ok"] and suv else "—")
        )
        if complet and suv:
            net = (pt["ca_ht"] - (ht("acte") or 0) - (ht("pack") or 0) - (ht("proc") or 0))
            rows.append(("Net promoteur m² SUV TTC", euro(net / suv * (1 + self._tva_dom()))))
        else:
            rows.append(("Net promoteur m² SUV TTC", "—"))
        rows.append(("CA TTC programme", euro(pt["ca_ttc"]) if pt["ok"] else "—"))
        rows.append(
            (
                "Renta nette / CA HT",
                f"{res_net / pt['ca_ht'] * 100:.1f} %".replace(".", ",")
                if complet and pt["ca_ht"]
                else "—",
            )
        )
        rows.append(("Nombre de lots", str(round(pt["lots"])) if pt["ok"] else "—"))
        rows.append(
            ("Prix terrain y compris dation", euro(ctx.get("prix_terrain")))
        )
        rows.append(
            (
                "Charge foncière / m² SUV",
                euro(blocs[0].ht / suv) if complet and suv else "—",
            )
        )
        return rows


def calculer(e: EntreesBilan, catalogue: Catalogue | None = None) -> ResultatBilan:
    """Raccourci : calcule un bilan avec le catalogue par défaut."""
    return Moteur(catalogue).calculer(e)
