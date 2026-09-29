/**
 * fiche/constructibilite.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F5).
 * La section « Constructibilité » + toute sa machinerie (capacité, calcul tracé, bilan, Mode B,
 * RTAA, calculette de charge foncière, potentiel de transformation). Extrait de Fiche.tsx.
 * Cycle-free : n'importe QUE des primitives + blocs feuilles, jamais Fiche.tsx.
 * Fiche.tsx ré-exporte Calculette + FaisabiliteTab (consommés par CalculetteFonciere / M22Programme).
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { getCalculetteDefaults, getFaisabilite, getModeB, getPipelineForParcel, patchPipeline, postChargeFonciere, postFaisabiliteScenario, type CalculetteDefaults } from '../../lib/api'
import { fmtEurCompact, fmtInt, fmtM2, fmtPctConsomme } from '../../lib/format'
import { PERIM_POTENTIEL_COURT } from '../../lib/perimetres'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { BlocIndisponible } from './BlocIndisponible'
import type { Fiche, PotentielTransformation } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { IC, RefDrawer, MicroTriple, PorteOutil, StepProv, HypInput, GroupLabel, FactRow, FactNote, RefLink, Vigilance } from './primitives'
import { Badge } from '../ui/Badge'
import { GrilleOutils, OutilCase } from '../shared/GrilleOutils'   // FAISABILITE-POLISH-1 — tuiles « Étudier ce bien »
import { Tip } from '../Tip'
// FICHE-FIX-5 (reste 2) — « Ce que le PLU permet » en Repli, Transformation/bilan en Lignes.
import { Repli, Lignes, Ligne, InfoI } from './formes'

// RETOURS-15 (retouche Vic) — la surface de PLANCHER s'écrit TOUJOURS en m², jamais en hectares
// (« ~14 200 m² de plancher », pas « ~1,42 ha ») : fmtM2 bascule en ha ≥ 10 000 m². Le verdict serveur
// (scenarios._fmt_m2) le fait déjà ; ici on couvre les surfaces de plancher rendues côté front (Tester).
const fmtPlancherM2 = (v: number | null | undefined): string => v == null ? '—' : `${fmtInt(v)} m²`
const PT_COLORS: Record<string, string> = { fort: '#4ADE96', modere: '#F5C244', faible: '#9AA6A0', nul: '#6B7280', indetermine: '#6B7280' }
export function TransformationBlock({ pt }: { pt: PotentielTransformation }) {
  if (pt.indisponible) return <BlocIndisponible titre="Potentiel de transformation" />   // M125 — panne ≠ absence
  const color = PT_COLORS[pt.niveau] ?? '#9AA6A0'
  // RETOURS-20 Z3 — plus de card-elev : kicker (titre + badge d'état à droite), les lignes
  // chiffrées deviennent des FactRow (valeur mono à droite), la source passe en FactNote.
  return (
    <div data-transformation>
      {/* FICHE-FIX-5 (reste 2) — Potentiel de transformation en Lignes : SDP consommée % et marge en
          hauteur ; la phrase (libellé) et le détail de contrainte passent derrière le « i ». */}
      <GroupLabel right={
        <span className="rounded-full px-2 py-0.5 text-[10.5px] font-medium capitalize" style={{ background: `${color}22`, color }}>{pt.niveau}</span>
      }>Potentiel de transformation</GroupLabel>
      <Lignes>
        {/* COHERENCE-FIX-1 (lot B) — plus jamais « 999 % » : au-delà de 300, « > 300 % » (l'« i »
            porte le libellé moteur qui explique) ; une valeur absente est « — », jamais 0. */}
        {pt.pct_consomme != null && (
          <Ligne label={<>SDP consommée / autorisée{pt.libelle ? <InfoI aria="Sur le potentiel de transformation" tip={pt.libelle} /> : null}</>}
            valeur={<>{fmtPctConsomme(pt.pct_consomme)} <small>%</small></>} />
        )}
        {pt.hauteur_marge_m != null && (
          <Ligne ton={pt.hauteur_discordante ? 'ambre' : undefined}
            label={<>Marge en hauteur<InfoI aria="Sur la marge en hauteur" tip={`${pt.hauteur_contrainte ? `Contrainte : ${pt.hauteur_contrainte === 'faîtage' ? 'le faîtage' : "l'égout"}. ` : ''}${pt.hauteur_survol ? `Mesuré au LiDAR HD, survol de ${pt.hauteur_survol}. ` : ''}${pt.hauteur_permis_posterieur ? `Antérieur au permis du ${pt.hauteur_permis_posterieur}, possiblement dépassé.` : ''}` || 'Marge mesurée sous la règle de hauteur.'} /></>}
            valeur={<>~{pt.hauteur_marge_m} <small>m sous la règle</small></>} />
        )}
      </Lignes>
      {/* PLU-EXCEPTIONS-1 Lot B — une exception du règlement peut changer l'enveloppe (bande depuis
          une limite, sous-secteur, majoration de hauteur…). On la SIGNALE ici « à vérifier » (jamais
          appliquée au calcul), avec renvoi vers le règlement de la zone (§Urbanisme). */}
      {pt.exceptions_calcul && pt.exceptions_calcul.length > 0 && (
        <div data-exception-calcul className="mt-0.5">
          <Badge ton="ambre">Exception au règlement — à vérifier</Badge>
          <p className="mt-0.5 text-[11px] leading-snug text-amber">
            {pt.exceptions_calcul.length === 1 ? 'Une règle de cette zone comporte' : `${pt.exceptions_calcul.length} règles de cette zone comportent`} une exception
            qui pourrait modifier la capacité (non appliquée au calcul) — voir le détail sous « Règlement » (§Urbanisme)
            {pt.exceptions_calcul.some((e) => e.page_pdf != null) ? `, art. ${pt.exceptions_calcul.map((e) => e.article).filter(Boolean).join(', ')}.` : '.'}
          </p>
        </div>
      )}
      {/* PLU-CALIBRAGE-5 Lot C — une exception du règlement N'EST PAS modélisée (bande depuis une
          limite, sous-secteur non calibré, condition non mesurable par parcelle…). On ne l'approxime
          jamais : la capacité porte le badge « Estimé » et on l'affiche ici sous la capacité, AVEC le
          texte verbatim de l'exception (article/page en source). Le Dossier et le Copilote suivent par
          le registre (capacite_estimee). */}
      {pt.regles_non_modelisees && pt.regles_non_modelisees.length > 0 && (
        <div data-regle-non-modelisee className="mt-0.5">
          <Badge ton="ambre">Estimé — exception non modélisée</Badge>
          <p className="mt-0.5 text-[11px] leading-snug text-amber">
            {pt.regles_non_modelisees.length === 1 ? 'Une exception du règlement n’est pas modélisée' : `${pt.regles_non_modelisees.length} exceptions du règlement ne sont pas modélisées`} — à vérifier. La capacité affichée est estimée (jamais sourcée) sur cette parcelle.
          </p>
          <ul className="mt-0.5 space-y-0.5">
            {pt.regles_non_modelisees.map((e, i) => (
              <li key={i} className="text-[10.5px] leading-snug text-txt-dim">
                {e.texte ? <span className="italic">« {e.texte} »</span> : <span>Règle {e.regle}</span>}
                {e.article ? <span className="not-italic"> — art. {e.article}{e.page_pdf != null ? ` · p. ${e.page_pdf}` : ''}.</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {/* DONNEES-FIX-1 lot A — même règle que le §3 Bâti (`discordance_hauteur`) : le badge compare
          l'ÉGOUT LiDAR à BD TOPO (même grandeur) ou signale un faîtage aberrant, jamais le faîtage↔BD
          TOPO. Sans choix automatique. */}
      {pt.hauteur_discordante && (
        <div data-marge-discordante className="mt-0.5">
          <Badge ton="ambre">Sources discordantes</Badge>
          <p className="mt-0.5 text-[11px] leading-snug text-amber">
            {pt.hauteur_discordance_motif === 'faîtage aberrant'
              ? <>Faîtage LiDAR {pt.hauteur_faitage_lidar_m} m — valeur physiquement impossible, mesure à écarter.</>
              : <>Égout LiDAR {pt.hauteur_egout_lidar_m} m · BD TOPO {pt.hauteur_bdtopo_m} m — écart{pt.ecart_egout_bdtopo_m != null ? ` de ${Math.abs(pt.ecart_egout_bdtopo_m)} m` : ''} sur la même grandeur, à vérifier sur photo aérienne.</>}
          </p>
        </div>
      )}
      <FactNote>{pt.source}</FactNote>
    </div>
  )
}

// ── RECETTE-8 W2 — Taxe d'aménagement : le TAUX communal, jamais un montant sans projet ─────────
// La taxe se paie sur la surface de plancher CRÉÉE par un projet (art. L331 c. urb.). Sur la fiche,
// aucun projet n'est saisi : LABUSE ne l'invente pas (avant, elle affichait « 22 469 € » sur une
// table rase que personne n'avait choisie). On sert le taux communal (public, daté) + départemental
// et la phrase disant sur quoi elle se calculera ; le montant est chiffré au Dossier financier, sur
// la SDP du projet. Taux communal inconnu → « non renseigné », jamais inventé (CIRCUIT-3 lot 6.2).
export function TaxeAmenagementBlock({ t }: { t: NonNullable<Fiche['taxe_amenagement']> }) {
  return (
    <div data-taxe-amenagement>
      <GroupLabel>Taxe d'aménagement</GroupLabel>
      {t.taux_communal_manquant ? (
        <FactRow label="Taux communal" tone="mute" value="non renseigné — à saisir" />
      ) : (
        // TAXE-FIX-1 point 3 — dire quand le taux vient d'un SECTEUR à taux majoré (≠ taux général).
        <FactRow label={t.taux_communal_secteur_majore ? 'Taux communal (secteur majoré)' : 'Taux communal'}
          value={<>{t.taux_communal_pct} <small>%</small></>}
          src={t.taux_communal_source === 'public'
            ? (t.taux_communal_secteur_majore ? 'secteur à taux majoré (délibération)' : 'délibération communale (public)')
            : undefined} />
      )}
      {/* TAXE-AMÉNAGEMENT-1 lot C — millésime du taux public + alerte fraîcheur (> 1 an). */}
      {t.taux_communal_source === 'public' && t.taux_communal_millesime && (
        <FactNote>
          {t.taux_communal_millesime}
          {t.taux_communal_perime && ' — ⚠ non rafraîchi depuis plus d’un an, à réingérer'}
        </FactNote>
      )}
      <FactRow label="Taux départemental"
        value={t.taux_departemental_pct != null ? <>{t.taux_departemental_pct} <small>%</small></> : '—'}
        src={t.taux_departemental_confirme ? 'confirmé' : 'plafond légal 2,5 % — à confirmer'} />
      {/* TAXE-FIX-1 point 4 — la taxe porte sur la SURFACE TAXABLE (garages/annexes inclus), pas la SDP. */}
      <FactNote>Se calcule sur la surface taxable de votre projet (close et couverte &gt; 1,80 m, garages et annexes inclus — ≠ SDP) — chiffrée dans le Dossier financier une fois le projet saisi. Barème {t.annee} — {t.source}.</FactNote>
    </div>
  )
}

// ── DESTINATIONS-1 (X4.2) — ligne « Destinations » d'une zone du règlement PLU ──────────────────
// Résumé (principales autorisées / interdites / seuil commerce) + dépliable (chevron) : les 23
// sous-destinations R151-28 avec leur PHRASE SOURCÉE (servie telle quelle — jamais reformulée).
// Commune non calibrée / zone non lue → la phrase du backend, JAMAIS un vide.

/** Champ éditable d'hypothèse promoteur — valeur SAISIE (jamais estimée par LABUSE). */

/** LA CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette). LABUSE affiche le SOURCÉ (SDP,
 *  prix DVF) ; le promoteur saisit SES hypothèses (coût, marge) ; le résultat « selon vos
 *  hypothèses » se recalcule côté moteur (endpoint déterministe, aucune arithmétique dupliquée
 *  en JS). Cas limites honnêtes : capacité non résolue / prix insuffisant → pas de faux chiffre.
 *
 *  M-Q P1-16 — les défauts (coût, marge) viennent du SERVEUR (getCalculetteDefaults, dérivé du
 *  YAML), plus d'une constante 2500 gravée ici qui divergeait du 2550 serveur (donc du PDF « Note
 *  de financement »). On seed les champs une fois les défauts connus : calculette et PDF portent le
 *  même coût par défaut sur la même parcelle. */
// onResult / hideResult (mandat ETUDIER) : « Étudier un bien » hisse la charge « vos hypothèses » dans
// SON verdict unique (bascule calibré/hypothèses). Il passe `hideResult` (la calculette ne rend alors
// que ses RÉGLAGES — coût/marge/VRD — pas son propre bloc-verdict, fini les deux bandeaux) et `onResult`
// (elle remonte la charge calculée). Défaut = props absentes → usage fiche INCHANGÉ.
export interface CalcResult { central: number; par_m2_terrain: number; ca_central: number | null; negatif: boolean }
export function Calculette({ idu, hideSource, prixDemandeExterne, onResult, hideResult }:
  { idu: string; hideSource?: boolean; prixDemandeExterne?: number | null
    onResult?: (r: CalcResult | null) => void; hideResult?: boolean }) {
  // M58-P1 (Q5) : `staleTime:Infinity` SANS retry laissait la calculette en « Chargement »
  // DÉFINITIF si /bilan/calculette-defaults échouait une fois. On ajoute un retry et surtout un
  // ÉTAT D'ERREUR explicite avec « Réessayer » (règle DA « les états parlent » — jamais de zone muette).
  const defs = useQuery({ queryKey: ['calculette-defaults'], queryFn: getCalculetteDefaults, staleTime: Infinity, retry: 2 })
  if (defs.isError) {
    return (
      <div data-calculette>
        <p className="label-caps mb-1">Calculette de charge foncière</p>
        <div data-calc-erreur className="card-elev px-3 py-2.5">
          <ErrorState message="Chargement de la calculette impossible." retry={() => defs.refetch()} />
        </div>
      </div>
    )
  }
  if (!defs.data) {
    return (
      <div data-calculette>
        <p className="label-caps mb-1">Calculette de charge foncière</p>
        <div className="card-elev px-3 py-2.5"><Squelette lignes={3} /></div>
      </div>
    )
  }
  return <CalculetteBody idu={idu} defauts={defs.data} hideSource={hideSource} prixDemandeExterne={prixDemandeExterne} onResult={onResult} hideResult={hideResult} />
}

function CalculetteBody({ idu, defauts, hideSource = false, prixDemandeExterne, onResult, hideResult = false }:
  { idu: string; defauts: CalculetteDefaults; hideSource?: boolean; prixDemandeExterne?: number | null
    onResult?: (r: CalcResult | null) => void; hideResult?: boolean }) {
  const [cout, setCout] = useState<number | null>(defauts.cout_construction_m2)
  const [marge, setMarge] = useState<number | null>(defauts.marge_frais_pct)
  // VRD/aménagements : hypothèse SAISIE, seed du défaut DIT servi (jamais un 0 silencieux).
  const [vrd, setVrd] = useState<number | null>(defauts.vrd_m2)
  const [prixDemande, setPrixDemande] = useState<number | null>(null)
  // FUSION « Étudier un bien » : quand le prix demandé est piloté par le parent (constat), on le
  // reçoit ici — UN seul champ de saisie, pas deux. `undefined` = mode autonome (fiche/outil hérité).
  const prixPilote = prixDemandeExterne !== undefined
  useEffect(() => { if (prixPilote) setPrixDemande(prixDemandeExterne ?? null) }, [prixPilote, prixDemandeExterne])
  // M22-A : la même équation, deux lectures — charge supportable (historique) ou prix d'achat
  // max admissible (inverse). Le moteur garantit l'identité des totaux (aucun calcul en JS).
  const [mode, setMode] = useState<'charge' | 'achat_max'>('charge')
  const [deb, setDeb] = useState({ cout: defauts.cout_construction_m2, marge: defauts.marge_frais_pct, vrd: defauts.vrd_m2, prix: null as number | null })
  useEffect(() => {
    const t = setTimeout(() => setDeb({ cout: cout ?? defauts.cout_construction_m2, marge: marge ?? defauts.marge_frais_pct, vrd: vrd ?? defauts.vrd_m2, prix: prixDemande }), 350)
    return () => clearTimeout(t)
  }, [cout, marge, vrd, prixDemande, defauts])
  const q = useQuery({
    queryKey: ['charge', idu, deb.cout, deb.marge, deb.vrd, deb.prix, mode],
    queryFn: () => postChargeFonciere(idu, { cout_construction_m2: deb.cout, marge_frais_pct: deb.marge, vrd_m2: deb.vrd, prix_demande_eur: deb.prix, mode }),
    placeholderData: (prev) => prev,   // garde l'ancien résultat pendant le recalcul (pas de flash)
  })
  const d = q.data
  // A6 : partager les hypothèses courantes avec le bouton PDF (l'export les reflète)
  const setCalculette = useApp((s) => s.setCalculette)
  useEffect(() => {
    setCalculette(d?.calculable ? { cout_construction_m2: deb.cout, marge_frais_pct: deb.marge, vrd_m2: deb.vrd, prix_demande_eur: deb.prix } : null)
    return () => setCalculette(null)
  }, [d?.calculable, deb.cout, deb.marge, deb.vrd, deb.prix, setCalculette])
  const cf = d?.charge_fonciere
  const achat = d?.achat
  // M60 P1b — présentation : (1) résultat NÉGATIF → verdict en clair, le détail chiffré ne mène plus ;
  // (2) fourchette ORDONNÉE bas→haut, principal BORNÉ à 0 ; (3) garde-fou coût > prix de sortie DVF.
  const sortie = d?.prix_sortie_median != null ? Number(d.prix_sortie_median) : null
  const coutSaisi = cout ?? defauts.cout_construction_m2
  const coutDepasse = sortie != null && coutSaisi > sortie          // garde-fou immédiat
  const central = cf != null ? Number(cf.central) : 0
  const negatif = cf != null && central <= 0                        // l'opération ne dégage aucune valeur
  const principal = Math.max(0, central)                           // borné à 0 en principal
  const [bornBas, bornHaut] = cf != null ? [Number(cf.bas), Number(cf.haut)].sort((a, b) => a - b) : [0, 0]
  // Mandat ETUDIER : remonter la charge « vos hypothèses » au parent (verdict unique). On rapporte la
  // CHARGE (mode 'charge') ; en mode embarqué (hideResult) la bascule de mode reste sur 'charge'.
  useEffect(() => {
    onResult?.(d?.calculable && cf
      ? { central, par_m2_terrain: Number(cf.par_m2_terrain), ca_central: d.ca?.central != null ? Number(d.ca.central) : null, negatif }
      : null)
  }, [onResult, d, cf, central, negatif])
  return (
    <div data-calculette>
      <p className="label-caps mb-1 flex items-center gap-2">
        Calculette de charge foncière
        {q.isFetching && <span data-calc-recalc className="animate-pulse text-[9px] normal-case tracking-normal text-mint">recalcul…</span>}
      </p>
      <div className="card-elev px-3 py-2.5 text-[11px] leading-relaxed text-txt">
        {q.isLoading && <Squelette lignes={3} />}
        {d && d.calculable === false && (
          <div data-calc-indispo>
            <p className="text-st-creuser">{d.message ?? 'Charge foncière non calculable.'}</p>
            {d.marche?.median != null && (
              <p className="mt-1 text-txt-mut">Au mieux — prix de sortie bâti secteur : <b className="tnum text-mint">{fmtInt(Number(d.marche.median))} €/m²</b> ({d.marche.fiabilite}).</p>
            )}
          </div>
        )}
        {d && d.calculable && cf && (
          <>
            {/* le SOURCÉ (lecture seule) — ce que LABUSE sait. Masqué quand le CONSTAT l'a déjà dit
                (fusion « Étudier un bien ») : pas deux fois les mêmes faits. */}
            {/* FIX-INTEGRATION I2 — « prix de sortie NEUF » (commercialisation d'une opération, échelle
                secteur avec repli) : à distinguer du « marché ancien commune » affiché sur le Kanban. */}
            {!hideSource && (
              <p className="text-[11px] text-txt-dim">
                LABUSE : SHAB vendable <b className="tnum text-txt">{fmtInt(Number(d.shab_vendable_m2))} m²</b> <span className="text-txt-dim">({PERIM_POTENTIEL_COURT})</span> ·
                <span> prix de sortie</span> <b className="tnum text-txt">{fmtInt(Number(d.prix_sortie_median))} €/m²</b>
                {/* RETOUCHES-1 (lot B.8) — le prix DVF est une MÉDIANE (estimé), pas une valeur sourcée
                    par bien : badge « Estimé » (comme Comparer) + source/fenêtre en sous-ligne. */}
                <span className="ml-1 rounded bg-st-creuser/10 px-1 py-0.5 align-middle text-[8.5px] font-medium text-st-creuser">Estimé</span> ·
                terrain <b className="tnum text-txt">{fmtInt(Number(d.terrain_m2))} m²</b>
              </p>
            )}
            {/* RETOUCHES-1 (lot B.8) — la SOURCE et la FENÊTRE du prix de sortie DVF, sous la ligne. */}
            {!hideSource && d.marche?.median != null && (
              <p data-prix-sortie-source className="text-[10px] text-txt-dim">
                Prix de sortie <span className="text-st-creuser">Estimé</span> — DVF (ventes actées{d.marche.type_prix ? `, ${d.marche.type_prix}` : ''})
                {d.marche.n != null ? ` · ${fmtInt(Number(d.marche.n))} vente${Number(d.marche.n) > 1 ? 's' : ''}` : ''}
                {d.marche.rayon_m ? ` · rayon ${fmtInt(Number(d.marche.rayon_m))} m` : ''}
                {Array.isArray(d.marche.periode) && d.marche.periode.length === 2
                  ? ` · ${d.marche.periode[0]}–${d.marche.periode[1]}`
                  : (d.marche.periode ? ` · ${String(d.marche.periode)}` : '')}.
              </p>
            )}
            {/* DIRE LE COÛT-PLANCHER : le coût de construction porte sur la SDP de PLANCHER (vendable
                ÷ rendement), pas sur la surface vendable affichée — sinon l'écart au calcul de tête
                (coût × surface vendable) fait douter. On l'explicite noir sur blanc. */}
            {d.sdp_plancher_m2 != null && (
              <p data-calc-plancher className="mt-1 text-[10px] leading-snug text-txt-dim">
                Le coût s'applique à <b className="tnum text-txt-mut">{fmtInt(Number(d.sdp_plancher_m2))} m² de surface plancher</b>
                {' '}({fmtInt(Number(d.shab_vendable_m2))} m² vendables ÷ {d.coef_rendement != null ? Number(d.coef_rendement).toLocaleString('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 2 }) : '0,8'}), pas sur la surface vendable.
              </p>
            )}
            {/* les HYPOTHÈSES — saisies par le promoteur (coût, marge & frais, VRD/aménagements).
                LOT1 — empilées (un champ par ligne, pleine largeur) : les libellés longs et leur chip
                « hyp. » ne se chevauchent plus. Placeholder = la valeur PAR DÉFAUT réelle (celle qui
                s'applique si le champ est vidé — deb retombe sur defauts.*), jamais un nombre en dur. */}
            <div className="mt-2 flex flex-col gap-2">
              <HypInput label="Coût construction" value={cout} onChange={setCout} suffix="€/m²" hint
                placeholder={defauts.cout_construction_m2 != null ? String(defauts.cout_construction_m2) : undefined} />
              <HypInput label="Marge & frais" value={marge} onChange={setMarge} suffix="%" hint
                placeholder={defauts.marge_frais_pct != null ? String(defauts.marge_frais_pct) : undefined} />
              <HypInput label="VRD & aménagements" value={vrd} onChange={setVrd} suffix="€/m²" hint
                placeholder={defauts.vrd_m2 != null ? String(defauts.vrd_m2) : undefined} />
            </div>
            {d.vrd_total_eur != null && (
              <p data-calc-vrd className="mt-1 text-[9.5px] leading-snug text-txt-dim">
                VRD/aménagements : hypothèse par défaut {fmtInt(Number(d.vrd_m2))} €/m² de terrain (soit {fmtEurCompact(Number(d.vrd_total_eur))} sur {fmtInt(Number(d.terrain_m2))} m²) — à ajuster par devis local, jamais un coût à zéro masqué.
              </p>
            )}
            {/* M60 P1b — garde-fou IMMÉDIAT : coût de construction > prix de sortie DVF du secteur. */}
            {coutDepasse && (
              <p data-calc-gardefou className="mt-2 rounded-lg bg-st-ecartee/10 px-3 py-2 text-[11px] font-medium leading-snug text-st-ecartee">
                ⚠ Coût de construction ({fmtInt(coutSaisi)} €/m²) au-dessus du prix de sortie du secteur ({sortie != null ? fmtInt(sortie) : '—'} €/m²) — à ces hypothèses, l'opération ne peut pas dégager de valeur pour le terrain.
              </p>
            )}
            {/* M22-A · BASCULE DE LECTURE — même équation, deux sens (discret, pas de refonte).
                Masquée en mode embarqué (hideResult) : le verdict unique du parent porte la charge. */}
            {!hideResult && (
              <div className="mt-2 flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
                {([['charge', 'Charge supportable'], ['achat_max', "Prix d'achat max"]] as const).map(([m, l]) => (
                  <button key={m} data-calc-mode={m} onClick={() => setMode(m)}
                    className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${mode === m ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>
                    {l}
                  </button>
                ))}
              </div>
            )}
            {/* le RÉSULTAT — M60 P1b : NÉGATIF → verdict en clair (le détail chiffré reste accessible,
                il ne mène plus) ; sinon principal BORNÉ à 0, fourchette ORDONNÉE bas→haut.
                Masqué en mode embarqué (hideResult) : le parent (« Étudier un bien ») rend LE verdict. */}
            {!hideResult && (
            <div data-calc-resultat className={`mt-2.5 rounded-lg border px-3 py-2 ${negatif ? 'border-st-ecartee/40 bg-st-ecartee/[0.07]' : 'border-mint/40 bg-mint/[0.06]'}`}>
              {negatif ? (
                <>
                  <p data-calc-verdict-neg className="text-[11.5px] font-medium leading-snug text-st-ecartee">
                    À ces hypothèses, l'opération ne dégage aucune valeur pour le terrain. Le coût de construction
                    ({fmtInt(coutSaisi)} €/m²) dépasse le prix de sortie du secteur ({sortie != null ? fmtInt(sortie) : '—'} €/m²).
                  </p>
                  <p className="mt-1 text-[10px] text-txt-dim">Détail — {mode === 'achat_max' ? "prix d'achat max" : 'charge foncière'} calculé : <b data-calc-cf className="tnum text-txt-mut">{fmtEurCompact(central)}</b> · fourchette {fmtEurCompact(bornBas)} – {fmtEurCompact(bornHaut)}.</p>
                </>
              ) : (
                <>
                  <p className="text-[11px] text-txt-dim">{mode === 'achat_max' ? "Prix d'achat maximal admissible" : 'Charge foncière supportable'} <span className="text-txt-mut">— selon vos hypothèses</span></p>
                  <p className="mt-0.5">
                    <b data-calc-cf className="num-key text-lg text-mint">{fmtEurCompact(principal)}</b>
                    <span className="ml-1.5 text-[11px] text-txt-mut">≈ {fmtInt(Number(cf.par_m2_terrain))} €/m² de terrain</span>
                  </p>
                  {/* fourchette ORDONNÉE bas→haut — n'est DITE que si c'est un vrai intervalle : quand le
                      prix de sortie est un point unique (cas servi q1=median=q3), bornBas===bornHaut===central
                      et répéter « ~119 k€ » sous le grand chiffre était LE DOUBLON (le central en double). */}
                  {fmtEurCompact(bornBas) !== fmtEurCompact(bornHaut) && (
                    <p data-calc-fourchette className="text-[11px] text-txt-dim">fourchette {fmtEurCompact(bornBas)} – {fmtEurCompact(bornHaut)}{d.fiabilite === 'fragile' ? ' · prix de sortie fragile (ordre de grandeur)' : ''}</p>
                  )}
                  {fmtEurCompact(bornBas) === fmtEurCompact(bornHaut) && d.fiabilite === 'fragile' && (
                    <p className="text-[11px] text-txt-dim">prix de sortie fragile (ordre de grandeur)</p>
                  )}
                  {/* SURFACER ce qui est déjà calculé (le geste du scoreur) : le CA visé et surtout LA
                      CONFRONTATION — ce que le marché de la zone paie le terrain nu, à côté de la charge
                      supportable en €/m². C'est ce qui rend l'outil utile (achat au prix du marché ou pas). */}
                  {d.ca?.central != null && (
                    <p data-calc-ca className="mt-1 text-[11px] text-txt-dim">CA visé <b className="tnum text-txt-mut">{fmtEurCompact(Number(d.ca.central))}</b> sur {fmtInt(Number(d.shab_vendable_m2))} m² vendables.</p>
                  )}
                  {mode === 'charge' && d.terrain_zone_eur_m2 != null && (
                    <p data-calc-terrain-zone className="mt-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 text-[11px] leading-snug text-txt-dim">
                      Confrontation — vous pouvez payer <b className="tnum text-mint">{fmtInt(Number(cf.par_m2_terrain))} €/m²</b> de terrain ;
                      le marché de la zone vend le terrain nu à <b className="tnum text-txt">{fmtInt(Number(d.terrain_zone_eur_m2))} €/m²</b>
                      {' '}<span className="text-txt-dim">(DVF terrains, fiabilité {String(d.terrain_zone_fiabilite ?? 'moyenne')})</span>.
                      {/* FRONT-CHIFFRES-2 (F02) — verdict charge vs marché SERVI (charge_couvre_marche) ;
                          le front ne compare plus les deux €/m². */}
                      {d.charge_couvre_marche
                        ? ' Votre charge couvre le prix du marché.'
                        : ' Votre charge est sous le prix du marché — négociation ou densité à retrouver.'}
                    </p>
                  )}
                  {mode === 'achat_max' && (
                    <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">
                      = ce que l'opération peut payer le terrain (CA × (1 − marge & frais) − construction − VRD le cas
                      échéant) — les trois scénarios suivent la fourchette de prix de sortie DVF (même équation que la
                      charge supportable, lue à l'envers).
                    </p>
                  )}
                </>
              )}
            </div>
            )}
            {/* aide à la DÉCISION D'ACHAT — prix demandé optionnel. Masqué quand le parent (constat)
                pilote le prix : UN seul champ dans le parcours fusionné, jamais deux. */}
            {!prixPilote && (
              <div className="mt-2 flex items-end gap-2">
                <HypInput label="Prix demandé du terrain" value={prixDemande} onChange={setPrixDemande} suffix="€" placeholder="si connu" />
              </div>
            )}
            {mode === 'achat_max' && d.ecart_negociation && (
              <div data-calc-ecart className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${d.ecart_negociation.sens === 'marge' ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                {d.ecart_negociation.sens === 'surcout'
                  ? <>Écart : prix demandé {fmtEurCompact(d.ecart_negociation.prix_demande_eur)} − prix d'achat max {fmtEurCompact(d.ecart_negociation.prix_achat_max_eur)} = <b>surcoût de {fmtEurCompact(d.ecart_negociation.demande_moins_max_eur)}</b> (+{Math.round(d.ecart_negociation.demande_moins_max_pct)} % au-dessus du max admissible).</>
                  : <>Écart : prix demandé {fmtEurCompact(d.ecart_negociation.prix_demande_eur)} est <b>sous votre prix d'achat max</b> ({fmtEurCompact(d.ecart_negociation.prix_achat_max_eur)}) — marge de {fmtEurCompact(Math.abs(d.ecart_negociation.demande_moins_max_eur))}.</>}
              </div>
            )}
            {/* M143 Lot 2 — bouton « Éditer l'argumentaire de négociation (PDF) » RETIRÉ (décision Vic,
                affichage seul). La route et le Copilote NE bougent pas dans ce mandat :
                l'argumentaire reste servi sur demande explicite (ReponseInline.tsx). Fermer la route
                est une décision séparée, liée à l'arbitrage de posture d'exposition (dette F4). */}
            {!hideResult && mode === 'charge' && achat && (
              <div data-calc-verdict className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${achat.supportable ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                {achat.supportable
                  ? <>✓ Supportable — le terrain peut valoir {fmtEurCompact(achat.prix_demande_eur)} ; marge de {fmtEurCompact(achat.ecart_eur)} ({achat.ecart_pct > 0 ? '+' : ''}{Math.round(achat.ecart_pct)} %) sous votre charge foncière.</>
                  : <>✗ Trop cher — à {fmtEurCompact(achat.prix_demande_eur)}, l'opération dépasse de {fmtEurCompact(Math.abs(achat.ecart_eur))} ({Math.round(achat.ecart_pct)} %) ce que vos hypothèses supportent.</>}
              </div>
            )}
            {(d.avertissements ?? []).length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-[11px] text-st-creuser">
                {d.avertissements.map((a: string, i: number) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">
              Le coût de construction et la marge sont VOS hypothèses (LABUSE ne les estime pas). Le
              résultat empile 4 hypothèses (coût, marge, prix de sortie DVF, prix demandé) — les écarts
              sont arrondis au point de % (pas de fausse précision décimale). Estimation indicative, ne
              vaut pas conseil.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

// Badges ÉQUIPEMENTS (mandat wave-ortho Lot 6) : piscine / PV / CES / pente — dans la
// synthèse, sourcés « ortho IGN 2025, fiabilité statistique, non contractuelle ».

// FAISABILITE-3 (Vic 27/09/2026) — LE panneau de la maquette validée, une seule implémentation
// partagée par l'outil Faisabilité (M22) et l'onglet Faisabilité de la fiche parcelle. RÈGLE
// ABSOLUE : aucun calcul dans le front. Chaque chiffre (verdict, « ce qui limite », les 8 étapes,
// la section PLU, le test d'un projet) vient d'UN SEUL appel au moteur (postFaisabiliteScenario →
// faisabilite_scenario) ; le front ne fait que rendre et renvoyer le scénario + les hypothèses.
// Le scénario est mémorisé dans la SESSION (Map ci-dessous) et, en projet, dans l'entrée pipeline
// (prospection.faisa_scenario/faisa_overrides — doctrine 09/09), jamais en base hors projet.
const _sessionScenario = new Map<string, 'terrain_libere' | 'bati_garde'>()
type Sc = 'terrain_libere' | 'bati_garde'

// FAISABILITE-POLISH-1 — les 4 suites deviennent des TUILES « Étudier ce bien » (icône + titre,
// GrilleOutils/OutilCase partagé de la fiche parcelle), 2 × 2, sans « → ». Tracés SVG 15 px « line »,
// même idiome que les tuiles d'export de la fiche.
const svg15 = (path: ReactNode) =>
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{path}</svg>
const SUITE_ICO = {
  gabarit: svg15(<><path d="M21 7.5 12 3 3 7.5v9L12 21l9-4.5z" /><path d="m3 7.5 9 4.5 9-4.5" /><path d="M12 12v9" /></>),
  taxe: svg15(<><line x1="19" y1="5" x2="5" y2="19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></>),
  comparer: svg15(<><path d="M3 17h6" /><path d="m6 14 3 3-3 3" /><path d="M21 7h-6" /><path d="m18 10-3-3 3-3" /></>),
  courrier: svg15(<><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>),
} as const

export function FaisabiliteTab({ idu }: { idu: string; embedded?: boolean }) {
  const { setModule, setParcelPrefill, chercherParCapacite } = useApp()
  // ALGO-FIX-1 (point 3, suite autorisée) — l'onglet s'ouvre par DÉFAUT sur « bâti gardé » : pour une
  // parcelle BÂTIE, la première capacité montrée est le RÉSIDUEL SERVI (parcel_residuel, ex. EO0796
  // 179 m²), la MÊME que la fiche §Potentiel et le Dossier — plus l'enveloppe démolition (338, une
  // grandeur distincte) en tête. Pour une parcelle NUE, le backend rétrograde bati_garde→terrain_libere
  // (scenarios.py) et l'UI suit `pan.scenario` : rien à masquer. Un choix explicite (session/projet)
  // reste prioritaire (le `??` ne s'applique qu'à l'ouverture initiale).
  const [scenario, setScenario] = useState<Sc>(_sessionScenario.get(idu) ?? 'bati_garde')
  const [overrides, setOverrides] = useState<Record<string, number>>({})
  const [nLog, setNLog] = useState<number | null>(null)
  const [surfLog, setSurfLog] = useState<number | null>(null)
  const [showSteps, setShowSteps] = useState(false)   // « replié par défaut dans l'app » (maquette)
  const [loaded, setLoaded] = useState(false)

  // Projet : charge scénario + hypothèses gardés (une fois), persiste au fil des changements.
  const pipeQ = useQuery({ queryKey: ['pipe-faisa', idu], queryFn: () => getPipelineForParcel(idu) })
  const entryId = pipeQ.data?.entry?.id ?? null
  useEffect(() => {
    if (!pipeQ.data || loaded) return
    const pros = (pipeQ.data.entry?.prospection as Record<string, unknown> | undefined) ?? {}
    const ov = pros.faisa_overrides
    if (ov && typeof ov === 'object') setOverrides(ov as Record<string, number>)
    const sc = pros.faisa_scenario
    if (sc === 'terrain_libere' || sc === 'bati_garde') setScenario(sc)
    setLoaded(true)
  }, [pipeQ.data, loaded])

  // Débounce des hypothèses + du test (le scénario, lui, bascule tout de suite).
  const [deb, setDeb] = useState<{ ov: Record<string, number>; test: { n_logements: number | null; surface_par_logement: number | null } | null }>({ ov: {}, test: null })
  useEffect(() => {
    const t = window.setTimeout(() => setDeb({
      ov: overrides,
      test: nLog != null || surfLog != null ? { n_logements: nLog, surface_par_logement: surfLog } : null,
    }), 350)
    return () => window.clearTimeout(t)
  }, [overrides, nLog, surfLog])

  const q = useQuery({
    queryKey: ['faisa-scenario', idu, scenario, JSON.stringify(deb.ov), JSON.stringify(deb.test)],
    queryFn: () => postFaisabiliteScenario(idu, { scenario, overrides: deb.ov, test: deb.test }),
    placeholderData: (prev) => prev,   // pas de flash au recalcul
  })
  const pan = q.data?.scenario ?? null

  // Persiste scénario + hypothèses dans le projet (jamais bloquant).
  useEffect(() => {
    _sessionScenario.set(idu, scenario)
    if (!loaded || entryId == null) return
    const t = window.setTimeout(() => {
      patchPipeline(entryId, { prospection: { faisa_overrides: overrides, faisa_scenario: scenario } })
        .catch(() => { /* projet non bloquant */ })
    }, 350)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idu, scenario, overrides, loaded, entryId])

  const chooseSc = (s: Sc) => { setScenario(s); _sessionScenario.set(idu, s) }
  const setOv = (key: string, v: number | null) => setOverrides((o) => {
    const n = { ...o }; if (v == null) delete n[key]; else n[key] = v; return n
  })
  const goOutil = (key: string) => { setParcelPrefill(idu); setModule(key) }

  if (q.isLoading && !pan) return <Squelette lignes={5} />
  if (q.isError) return <ErrorState message="Faisabilité indisponible." retry={() => q.refetch()} />
  if (!pan) return <p className="text-[11px] text-txt-mut">Zone PLU non résolue pour cette parcelle — capacité non calculable (honnête).</p>

  const badges = pan.badges ?? {}
  const test = pan.test as Record<string, any> | null
  const rv: Record<string, any>[] = pan.plu?.regles_valeurs ?? []
  const nOv = Object.keys(overrides).length
  const hypModif: { key: string; label: string; valeur: number; unite: string; min: number; max: number }[] = pan.hypotheses_modifiables ?? []
  const etapes: { n: number; label: string; valeur: string; source: string; prov: string }[] = pan.etapes ?? []

  // FAISABILITE-POLISH-1 — chip d'état pour une règle PLU (source line) : Sourcé (vert) quand la
  // règle est chiffrée avec un article ; sinon on reflète l'état SANS l'inventer (jamais « Sourcé »
  // sur une règle non modélisée). Le texte de fond (valeur) n'est pas touché.
  const regleBadge = (r: Record<string, any>) => {
    if (r.etat === 'non_modelisee') return <Badge ton="neutre">Non modélisée</Badge>
    if (r.etat === 'absent') return <Badge ton="neutre">Pas de règle PLU</Badge>
    if (r.etat === 'prospect') return <Badge ton="neutre">Selon la voie</Badge>
    if (r.etat === 'a_verifier') return <Badge ton="ambre">À vérifier</Badge>
    return <Badge ton="vert">Sourcé</Badge>
  }
  const pluDoc = pan.plu?.document as string | undefined

  return (
    // Grille du panneau : UN seul rythme — 24 px entre sections (gap-6), aucune section ne rajoute
    // de padding horizontal (le gutter de 16 px vient du conteneur), les titres passent tous par
    // GroupLabel (capitales espacées, comme la fiche parcelle).
    <div data-faisa-panneau className="flex flex-col gap-6">
      {/* 1 · SCÉNARIO — deux cartes (« En gardant le bâti » visible seulement si bati_present) */}
      <div data-faisa-scenarios className="flex gap-2">
        <button data-sc="terrain_libere" onClick={() => chooseSc('terrain_libere')}
          className={`min-w-0 flex-1 rounded-md border px-3 py-2 text-left transition-colors duration-quick ${pan.scenario === 'terrain_libere' ? 'border-2 border-mint bg-mint/[0.08]' : 'border-line-2 hover:border-mint/50'}`}>
          <div className={`text-[12.5px] font-medium ${pan.scenario === 'terrain_libere' ? 'text-mint' : 'text-txt'}`}>Terrain libéré</div>
          <div className="text-[10.5px] leading-snug text-txt-dim">l'enveloppe du terrain, bâti rasé</div>
        </button>
        {pan.bati_present && (
          <button data-sc="bati_garde" onClick={() => chooseSc('bati_garde')}
            className={`min-w-0 flex-1 rounded-md border px-3 py-2 text-left transition-colors duration-quick ${pan.scenario === 'bati_garde' ? 'border-2 border-mint bg-mint/[0.08]' : 'border-line-2 hover:border-mint/50'}`}>
            <div className={`text-[12.5px] font-medium ${pan.scenario === 'bati_garde' ? 'text-mint' : 'text-txt'}`}>En gardant le bâti</div>
            <div className="text-[10.5px] leading-snug text-txt-dim">{pan.bati_libelle ?? 'bâti existant conservé'}</div>
          </button>
        )}
      </div>

      {/* 2 · VERDICT (bloc surligné) — QUATRE lignes empilées, jamais mêlées :
          (a) la phrase seule, taille titre ; (b) une rangée de chips ; (c) une ligne de texte gris
          (ce qui limite) ; (d) la source PLU en petit. L'en-tête « zone · surface » reste le titre. */}
      <div data-faisa-verdict className="rounded-md border-2 border-mint/70 bg-mint/[0.05] px-4 py-3">
        <div className="text-[10.5px] uppercase tracking-[0.12em] text-txt-dim">
          Verdict · zone {pan.zone}{pan.a_cheval && pan.portion_zone ? ` (à cheval)` : ''} · <span className="whitespace-nowrap">{fmtM2(pan.surface_m2)}</span>
          {q.isFetching && <span className="ml-2 animate-pulse normal-case tracking-normal text-mint">recalcul…</span>}
        </div>
        <div data-faisa-verdict-phrase className="mt-2 text-[15px] font-medium leading-snug text-txt-hi">{pan.verdict}</div>
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          {pan.ce_qui_limite && <Badge ton="ambre">Ce qui limite</Badge>}
          {badges.regles_sourcees && <Badge ton="vert">Règles sourcées</Badge>}
          {badges.plancher_estime && <Badge ton="ambre">Plancher estimé</Badge>}
        </div>
        {pan.ce_qui_limite && <p className="mt-2 text-[12px] leading-snug text-txt-mut">{pan.ce_qui_limite}</p>}
        {badges.plu_approuve_le && <p className="mt-2 text-[10.5px] text-txt-dim">PLU — {String(badges.plu_approuve_le)}</p>}
      </div>

      {/* 3 · TESTER UN PROJET — deux champs EMPILÉS pleine largeur, unité dans le champ, libellé dessus */}
      <div data-faisa-test>
        <GroupLabel>Tester un projet · vos chiffres</GroupLabel>
        <div className="flex flex-col gap-3">
          <HypInput label="Nombre de logements" suffix="logements" value={nLog} placeholder="—" onChange={setNLog} />
          <HypInput label="Surface de plancher par logement" suffix="m²" value={surfLog} placeholder="—" onChange={setSurfLog} />
        </div>
        {test && (
          <div data-faisa-test-result className="mt-3 text-[12px] leading-snug">
            {test.statut === 'a_completer' && (<><Badge ton="neutre">À compléter</Badge> <span className="text-txt-dim">{test.message}</span></>)}
            {test.statut === 'non_autorise' && (<><Badge ton="ambre">Logement non autorisé</Badge> <span className="text-txt-mut">{test.message}</span></>)}
            {test.statut === 'tient' && (
              <><Badge ton="vert">Tient</Badge> <span className="text-txt-mut">{fmtPlancherM2(test.besoin_m2)} sur {fmtPlancherM2(test.possible_m2)} possibles{test.places != null ? ` · ${test.places} place(s)` : ''}{test.demolition_m2 ? ` · démolition de ${fmtPlancherM2(test.demolition_m2)} à chiffrer` : ''}</span></>
            )}
            {test.statut === 'ne_tient_pas' && (
              <><Badge ton="ambre">Ne tient pas</Badge> <span className="text-txt-mut">il manque {fmtPlancherM2(test.manque_m2)} de plancher ({fmtPlancherM2(test.besoin_m2)} demandés pour {fmtPlancherM2(test.possible_m2)} possibles)</span></>
            )}
          </div>
        )}
      </div>

      {/* 4 · CE QUE LE PLU PERMET — chaque règle = TROIS lignes empilées : libellé en petites
          capitales grises · valeur en clair pleine largeur · ligne source (chip + article/page).
          Le nom du PLU vit dans l'info « i » du titre, pas dans la ligne. Un filet fin entre règles. */}
      {/* FICHE-FIX-5 (reste 2) — « Ce que le PLU permet » = doublon des tuiles §Urbanisme → REPLI
          « Règles du PLU » (fermé par défaut ; le nom du règlement reste dans le « i »). */}
      {rv.length > 0 && (
        <Repli compteur={rv.length} label={<>Règles du PLU · zone {pan.zone}{pluDoc ? (
          <Tip garder tip={<>Règlement : {pluDoc}{badges.plu_approuve_le ? ` · approuvé le ${String(badges.plu_approuve_le)}` : ''}</>}>
            <span data-faisa-plu-info tabIndex={0} className="ml-1 inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-line-2 text-[9px] text-txt-dim">i</span>
          </Tip>) : null}</>}>
        <div data-faisa-plu>
          <div>
            {rv.map((r) => (
              <div key={r.cle} className="flex flex-col gap-1 border-b border-line/60 py-2.5 last:border-0">
                <span className="text-[10px] font-medium uppercase tracking-[0.11em] text-txt-dim">{r.libelle}</span>
                <span className={`text-[12.5px] leading-snug ${r.etat === 'non_modelisee' || r.etat === 'absent' ? 'text-txt-dim' : 'text-txt'}`}>{r.valeur}</span>
                <span className="flex items-center gap-2 text-[11px]">
                  {regleBadge(r)}
                  {r.reference && <RefLink href={r.url}>{r.reference}</RefLink>}
                </span>
              </div>
            ))}
          </div>
        </div>
        </Repli>
      )}

      {/* 5 · NOS HYPOTHÈSES (3 seulement) — champs EMPILÉS pleine largeur ; « Revenir aux valeurs
          LABUSE » en Bouton lien SOUS les champs (jamais dans le titre). Tout se recalcule au moteur. */}
      {hypModif.length > 0 && (
        <div data-faisa-hypotheses>
          <GroupLabel>Nos hypothèses · modifiables</GroupLabel>
          <div className="flex flex-col gap-3">
            {hypModif.map((h) => (
              <HypInput key={h.key} label={h.label} suffix={h.unite} hint={overrides[h.key] != null}
                value={overrides[h.key] ?? null} placeholder={String(h.valeur)}
                onChange={(v) => setOv(h.key, v)} />
            ))}
          </div>
          {nOv > 0 && (
            <button data-faisa-hyp-reset onClick={() => setOverrides({})}
              className="mt-2.5 text-[11px] text-mint underline decoration-mint/40 underline-offset-2 transition-colors duration-quick hover:decoration-mint">
              ↻ Revenir aux valeurs LABUSE
            </button>
          )}
        </div>
      )}

      {/* 6 · LE CALCUL, ÉTAPE PAR ÉTAPE — accordéon (chevron de la charte : ◀ fermé / ▼ ouvert,
          chevron vert), replié par défaut. */}
      {etapes.length > 0 && (
        <div data-faisa-steps-wrap>
          <button onClick={() => setShowSteps((s) => !s)} aria-expanded={showSteps}
            className="flex w-full items-center justify-between gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-lab transition-colors duration-quick hover:text-txt-hi">
            <span>Le calcul, étape par étape ({etapes.length})</span>
            <span className="text-mint">{showSteps ? '▼' : '◀'}</span>
          </button>
          {showSteps && (
            <ol data-faisa-steps className="mt-1.5">
              {etapes.map((s) => (
                <li key={s.n} className="flex items-start gap-2 border-b border-line/60 py-2 text-[11px] last:border-0">
                  <span className="shrink-0 font-mono text-[9px] text-txt-dim">{s.n}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="min-w-0 text-txt">{s.label}</span>
                      <b className="shrink-0 whitespace-nowrap font-mono font-medium tnum text-txt-hi">{s.valeur}</b>
                    </div>
                    <div className="mt-1 flex items-center gap-1.5">
                      <StepProv prov={s.prov} />
                      <span className="truncate text-[9.5px] text-txt-dim">{s.source}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* 7 · ACTIONS DU BAS — 4 tuiles « Étudier ce bien » (icône + titre), 2 × 2 à largeurs
          égales, sans « → ». Le texte « Pré-faisabilité indicative… » reste en dernier, en petit. */}
      <div data-faisa-suites className="flex flex-col gap-2.5">
        {/* FICHE-FIX-5 (reste 2) — « Comparer » et « Écrire au propriétaire » RETIRÉS du panneau
            (même décision que Scan). Restent : Voir en 3D · Taxe d'aménagement · Chercher par capacité. */}
        <GrilleOutils cols={2}>
          <OutilCase data-suite="gabarit" nom="Voir en 3D" ic={SUITE_ICO.gabarit} onClick={() => goOutil('gabarit')} />
          <OutilCase data-suite="taxe" nom="Taxe d'aménagement" ic={SUITE_ICO.taxe} onClick={() => goOutil('taxe-amenagement')} />
        </GrilleOutils>
        <div className="text-[10.5px] leading-snug text-txt-dim">
          <button onClick={() => chercherParCapacite()} className="underline decoration-txt-dim/40 underline-offset-2 transition-colors duration-quick hover:text-mint">Chercher des parcelles par capacité →</button>
          {' · '}{pan.bandeau ?? 'Pré-faisabilité sur règlement public, pas un certificat d’urbanisme.'}
        </div>
      </div>
    </div>
  )
}

export function BilanTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (isLoading) return <Squelette lignes={4} />
  if (isError || !b) return <ErrorState message="Bilan indisponible." retry={() => refetch()} />
  return (
    <div className="flex flex-col gap-3">
      {/* M58-P1 (b) : le bloc « Capacité » vivait ICI ET dans FaisabiliteTab (même b.capacite) —
          DOUBLON supprimé. La capacité est rendue UNE seule fois, en tête de FaisabiliteTab.
          BilanTab ne porte plus que Marché → Fiscal → RTAA (ordre M58-P1 h). */}
      {/* RETOURS-11F4 F5/F0 — le PRIX DE SORTIE bâti vit désormais dans « Marché et secteur » (fait
          unique). La Constructibilité ne montre QUE le prix RETENU pour le bilan + un renvoi ; plus de
          fiche de marché rivale ici (le détail — n ventes, rayon, tendance, fraîcheur — est dans Marché). */}
      {/* RETOURS-20 Z3 — les Sec (card-elev) deviennent kicker + FactRow/FactNote (plus de boîte). */}
      {/* FICHE-RANGEMENT-1 Lot 1 (doublon #3) — le PRIX DE SORTIE bâti secteur est un FAIT de marché :
          il vit UNE fois, dans « Marché et secteur » (échantillon, rayon, tendance, fraîcheur). Le
          bilan ne répète plus le chiffre — il renvoie au fait unique (la charge foncière ci-dessous
          s'appuie dessus). */}
      {b.marche?.median != null && (
        <div>
          <GroupLabel>Prix de sortie retenu (bilan)</GroupLabel>
          <FactNote>Le prix de sortie bâti retenu pour la charge foncière est le prix du secteur affiché dans « Marché » (échantillon, rayon, tendance, fraîcheur y sont détaillés).</FactNote>
        </div>
      )}
      {/* FICHE-RANGEMENT-3 Lot 1 — « Fiscal & leviers » (QPV/TVA/taxe) et « RTAA DOM » RETIRÉS de la
          Simulation : ils vivent déjà en §7 Fiscalité (FiscalLeviersBlock) et §4 Urbanisme
          (RtaaFromBilan). §11 ne garde que le prix de sortie retenu (+ les 3 portes, côté Fiche). */}
    </div>
  )
}

/** §7 Fiscalité — QPV / TVA / note taxe d'aménagement (levier fiscal du bilan). */
export function FiscalLeviersBlock({ idu }: { idu: string }) {
  const { data: b } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (!b) return null
  return (
    <div>
      <GroupLabel>Fiscal &amp; leviers</GroupLabel>
      <FactRow label="QPV" value={<span className={b.fiscal.qpv ? 'text-mint' : 'text-txt-mut'}>{b.fiscal.qpv ? 'OUI' : 'non'}</span>} tone={b.fiscal.qpv ? undefined : 'mute'} />
      {/* FICHE-RANGEMENT-2 Lot 4 — la TVA outre-mer (8,5 % / 2,1 % LLS) n'est plus RÉPÉTÉE ici :
          elle est expliquée UNE fois, en « Dispositifs territoriaux » (dispositifs_dom).
          OUTILS-FIX-5 L4 — la note de taxe d'aménagement « taux non ingéré » est RETIRÉE (fausse
          depuis TAXE-AMENAGEMENT-1) : le taux communal public daté est servi par le bloc taxe de la
          fiche (§7) et l'outil Taxe. « Fiscal & leviers » ne garde donc que QPV. */}
    </div>
  )
}

/** §4 Urbanisme — rappel RTAA DOM (conception), servi par le bilan (b.rtaa). */
export function RtaaFromBilan({ idu }: { idu: string }) {
  const { data: b } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (!b?.rtaa) return null
  return <RtaaBlock rtaa={b.rtaa} />
}

/** RTAA DOM (mandat 5bis) — rappel réglementaire de CONCEPTION, vérifié Légifrance
 *  (config/rtaa_dom.yaml). Les seuils d'altitude (400/600 m) sont énoncés dans chaque
 *  exigence — l'altitude de la parcelle n'est pas calculée ici (consigné). */
/** M33 — MODE B (réhabilitation) : lecture COMPLÉMENTAIRE, visuellement subordonnée au tier
 *  (M34 intact). TOUJOURS Estimé (le paramètre travaux l'est) — assumé au libellé. Le
 *  paramètre est un état d'UI : rien n'est persisté (recalcul via /parcels/{idu}/mode-b). */
// FICHE-RANGEMENT-3 Lot 3 — Mode B (Réhabilitation) rendu DANS §11 Simulation (plus un 12e tiroir) :
// mêmes calculs, wrapper RefDrawer remplacé par un GroupLabel (bloc inline sous la Simulation).
export function ModeBBody({ idu, initial }: { idu: string; initial: import('../../lib/types').ModeB }) {
  // M45-B (L2) : le coût travaux est une VALEUR DE SESSION PARTAGÉE (fiche ↔ filtre) — le curseur
  // du tiroir Économie et cette fiche lisent/écrivent le même `modeB.travauxM2` (rien persisté).
  const travaux = useApp((s) => s.modeB.travauxM2)
  const setModeB = useApp((s) => s.setModeB)
  const q = useQuery({
    queryKey: ['mode-b', idu, travaux],
    queryFn: () => getModeB(idu, travaux),
    placeholderData: (prev) => prev,
  })
  const mb = q.data ?? initial
  if (!mb.disponible) return null
  // M59-P1 (Q4) — sous le seuil de SHAB : la section ne montre PAS le calcul, elle DIT pourquoi.
  if (mb.trop_petit) return (
    <div data-mode-b-section>
      <GroupLabel right={<Badge ton="ambre">non pertinent</Badge>}>Réhabilitation (Mode B)</GroupLabel>
      <p data-mode-b-trop-petit style={{ margin: '4px 0 0', fontSize: 11.5, lineHeight: 1.5, color: '#8FA69A' }}>
        {mb.motif ?? `Bâti trop petit (SHAB ~${mb.shab_rehabilitable_m2 ?? '—'} m²) pour une thèse de réhabilitation.`}
      </p>
    </div>
  )
  if (!mb.composantes) return null
  const c = mb.composantes
  const [bMin, bMax] = c.travaux.bornes
  const foncierM2 = mb.surface_parcelle_m2 ?? mb.terrain_nu?.surface_m2 ?? null
  return (
    <div data-mode-b-section>
      <GroupLabel right={mb.negatif
        ? <Badge ton="ambre">bilan négatif</Badge>
        : <span className="text-[10.5px] text-txt-dim">Estimé · ~{mb.achat_max_libelle ?? ''}</span>}>Réhabilitation (Mode B)</GroupLabel>
      <div data-mode-b style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 6 }}>
        {/* M101 A2 — la PORTE du mode B en tête : pourquoi cette parcelle est « bâtie »,
            en français lisible (servie par compute_mode_b, jamais un libellé interne). */}
        {mb.porte && (
          <p data-mode-b-porte style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: 'var(--txt-hi)' }}>
            {mb.porte}
          </p>
        )}
        {/* M59-P1 (Q1) — tête + comparaison terrain. La comparaison terrain nu ET la phrase
            « portée par le terrain » s'affichent dans LES DEUX cas (positif ou négatif) : c'est la
            vraie information sur ~50-64 % du stock, souvent des bilans bâti négatifs. */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {mb.negatif ? (
            /* résultat négatif : verdict en clair, JAMAIS un nombre négatif en tête. */
            <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#E8B44C' }}>{mb.message_negatif}</p>
          ) : (
            <>
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--txt-hi)' }}>
                Ce que la réhabilitation du bâti justifie : <b data-mode-b-achat>~{mb.achat_max_libelle ?? '—'}</b>
                <span style={{ marginLeft: 6, fontSize: 10.5, color: '#8FA69A' }}>(Estimé — l'hypothèse travaux l'est toujours)</span>
              </p>
              <p data-mode-b-hors-terrain style={{ margin: 0, fontSize: 10.5, color: '#8FA69A' }}>
                hors valeur du terrain — le foncier{foncierM2 != null ? ` (${fmtInt(foncierM2)} m²)` : ''} s'ajoute à ce montant
              </p>
            </>
          )}
          {mb.terrain_nu && (
            <p data-mode-b-terrain-nu style={{ margin: 0, fontSize: 10.5, color: '#8FA69A' }}>
              terrain nu au prix du secteur : <b style={{ color: 'var(--txt-hi)' }}>~{mb.terrain_nu.valeur_libelle}</b>{' '}
              <span style={{ fontSize: 10 }}>({fmtInt(mb.terrain_nu.prix_m2)} €/m² × {fmtInt(mb.terrain_nu.surface_m2)} m² · Estimé)</span>
            </p>
          )}
          {mb.porte_par_terrain && (
            <p data-mode-b-porte-terrain style={{ margin: '2px 0 0', fontSize: 11, lineHeight: 1.45, color: '#E8B44C' }}>
              À ces hypothèses, la valeur de cette parcelle est portée par le terrain, pas par le bâti.
            </p>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {/* FICHE-FIX-5 (reste 2) — le DÉTAIL (surface réhabilitable, emprise, niveaux) passe dans un
              Repli ; restent visibles la réhabilitation (en tête), le prix de sortie, le coût travaux. */}
          <Repli label="Détail du bilan">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--txt-dim)' }}>Surface réhabilitable</span>
              <span style={{ color: 'var(--txt-hi)' }}>~{fmtInt(c.surface.shab_rehabilitable_m2)} m² hab.</span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 10, color: '#8FA69A' }}>
              emprise {fmtInt(c.surface.emprise_bati_m2)} m² <b style={{ color: '#5CE6A1' }}>Sourcé</b> ({c.surface.source_emprise}) × {c.surface.niveaux} niveau(x){' '}
              <b style={{ color: c.surface.niveaux_reels ? '#5CE6A1' : '#E8B44C' }}>{c.surface.niveaux_reels ? 'Sourcé' : 'Estimé'}</b>
              {' '}— {c.surface.niveaux_etiquette}
            </p>
          </Repli>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)' }}>Prix de sortie (revente)</span>
            <span style={{ color: 'var(--txt-hi)' }}>{fmtInt(c.prix_sortie.prix_m2)} €/m² <b style={{ color: '#5CE6A1', fontSize: 10 }}>Sourcé DVF</b></span>
          </div>
          <p data-mode-b-perimetre style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
            {c.prix_sortie.libelle}{c.prix_sortie.perimetre ? ` · ${c.prix_sortie.perimetre}` : ''}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)', flex: 1 }}>Coût travaux <b style={{ color: '#E8B44C', fontSize: 10 }}>ESTIMÉ</b></span>
            <input data-mode-b-travaux type="number" min={bMin} max={bMax} step={50} value={travaux}
              onChange={(e) => setModeB({ travauxM2: Number(e.target.value) })}
              style={{ width: 80, background: '#0d1512', border: '1px solid #26302B', borderRadius: 6, color: 'var(--txt-hi)', padding: '3px 6px', fontSize: 11 }} />
            <span style={{ color: 'var(--txt-dim)' }}>€/m²</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.travaux.libelle}</p>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.frais_marge.libelle}</p>
        </div>
        {/* M44 — SORTIE LOCATIVE : côte à côte avec la revente, jamais fusionnée. Loyer au plafond
            réglementaire Sourcé (ou marché Estimé) ; prix d'achat max à rendement cible. Mention fiscale. */}
        {/* FICHE-FIX-5 (reste 2) — la SORTIE LOCATIVE passe dans un Repli. */}
        {mb.sortie_locative && (
          <Repli label="Sortie locative">
          <div data-mode-b-locatif style={{ paddingTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {/* M59-P1 (Q2) — l'avertissement sur le loyer retenu passe AVANT le chiffre du prix
                d'achat locatif : le plafond réglementaire n'est pas un loyer de marché observé. */}
            <p data-mode-b-loyer-avert style={{ margin: 0, fontSize: 10, lineHeight: 1.4, color: '#E8B44C' }}>
              Loyer retenu : {mb.sortie_locative.loyer.etiquette}
              {mb.sortie_locative.loyer.source ? ` (réf. plafond ${mb.sortie_locative.loyer.source})` : ''}.
            </p>
            {mb.sortie_locative.negatif ? (
              <p style={{ margin: 0, fontSize: 11.5, color: '#E8B44C' }}>{mb.sortie_locative.message_negatif}</p>
            ) : (
              <p style={{ margin: 0, fontSize: 11.5, color: 'var(--txt-hi)' }}>
                Prix d'achat max : <b>~{mb.sortie_locative.achat_max_libelle}</b>
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(Estimé)</span> à rendement cible {mb.sortie_locative.rendement_cible_pct} %
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(paramètre client)</span>
              </p>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--txt-dim)' }}>Loyer</span>
              <span style={{ color: 'var(--txt-hi)' }}>~{fmtInt(mb.sortie_locative.loyer.annuel_eur)} €/an · {mb.sortie_locative.loyer.m2_mois_effectif} €/m²/mois</span>
            </div>
            {mb.sortie_locative.loyer.coef_surface != null && (
              <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>coefficient de surface {mb.sortie_locative.loyer.coef_surface}</p>
            )}
            <p style={{ margin: 0, fontSize: 9.5, lineHeight: 1.45, color: '#E8B44C' }}>{mb.sortie_locative.mention_fiscale}</p>
          </div>
          </Repli>
        )}
        <p style={{ margin: 0, fontSize: 9.5, lineHeight: 1.45, color: '#6b7a72' }}>{mb.avertissement}</p>
      </div>
    </div>
  )
}

function RtaaBlock({ rtaa }: { rtaa: { meta: Record<string, string>; exigences: { volet: string; exigence: string; reference: string; url: string; condition_altitude?: string }[] } }) {
  const [open, setOpen] = useState(false)
  const VOLET_COLOR: Record<string, string> = { cadre: '#8FA69A', thermique: '#E8B44C', acoustique: '#B497F0', aeration: '#7DE8E0', ecs: '#5CE6A1' }
  return (
    // RETOURS-20 Z3 — plus de card-elev ni de tuiles bg-surface-3 : kicker + note, chaque exigence
    // à plat (badge volet + phrase + renvoi d'article RefLink), séparée par le filet des lignes.
    <div data-rtaa-block>
      {/* FICHE-FIX-5 (reste 3) — RTAA DOM en une Ligne « N exigences → » ; le rappel de conception
          passe derrière le « i ». Le dépliage garde la liste détaillée. */}
      <Lignes>
        <Ligne label={<>RTAA DOM<InfoI aria="Sur le RTAA DOM" tip="Construction neuve de logements : protection solaire, ventilation traversante, acoustique, aération et ECS renouvelable s'appliquent (seuils d'altitude 400/600 m). Rappel de conception, ne remplace pas l'étude du maître d'œuvre." /></>}
          valeur={<button data-rtaa-toggle onClick={() => setOpen((o) => !o)} className="text-mint hover:underline">{open ? 'replier' : `${rtaa.exigences.length} exigences →`}</button>} />
      </Lignes>
      {open && (
        <div className="mt-1.5 flex flex-col">
          {rtaa.exigences.map((e, i) => (
            <div key={i} className="border-b border-line/60 py-2 last:border-0">
              <span className="rounded-full px-1.5 py-0.5 font-mono text-[8.5px] font-semibold uppercase"
                style={{ color: VOLET_COLOR[e.volet] ?? '#8FA69A', background: `${VOLET_COLOR[e.volet] ?? '#8FA69A'}18` }}>
                {e.volet}
              </span>
              <p className="mt-1 text-[10.5px] leading-snug text-txt">{e.exigence}</p>
              {e.condition_altitude && <p className="mt-0.5 text-[11px] text-st-creuser">altitude : {e.condition_altitude}</p>}
              <div className="mt-0.5"><RefLink href={e.url}>{e.reference}</RefLink></div>
            </div>
          ))}
          <FactNote>
            {rtaa.meta.champ} — rappel de conception, ne
            remplace pas l'étude réglementaire du maître d'œuvre.
          </FactNote>
        </div>
      )}
    </div>
  )
}

// M-B (passe directeur) : « qu'a-t-il d'autre ? » → scan patrimoine en un clic depuis la fiche.
// M60 P1c — PatrimoineLink (lien inline « tout son patrimoine ») RETIRÉ : remplacé par la PORTE
// Scan patrimoine en pied du tiroir Propriétaire (une seule entrée par outil).

// M19 : la barre d'onglets a été retirée (fiche = pile de tiroirs) ; `tab` subsiste comme
// état interne toujours à 'synthese' (le contenu unique), gardé pour un diff minimal.

// ── SOURCES-1 lot 1 — « Dispositifs et périmètres » du droit des sols (ER, EBC, DPU, PEB, SUP).
// Tiroir DISTINCT sous Constructibilité : ces servitudes commandent l'emprise (ER déduite, EBC
// soustraite de l'assiette) et la transaction (DPU). N'affiche QUE ce que le payload donne ;
// chaque absence est TYPÉE (« non déterminée — non publié par la commune »), jamais un zéro.
const PEB_PHRASES: Record<string, string> = {
  A: 'constructions d’habitation interdites (art. L112-10 CU)',
  B: 'constructions d’habitation interdites (art. L112-10 CU)',
  C: 'constructions d’habitation limitées, sans accroissement sensible de la population exposée (art. L112-10 CU)',
  D: 'constructions autorisées sous réserve d’isolation acoustique (art. L112-10 et L112-12 CU)',
}

// FICHE-RANGEMENT-2 Lot 1 — nombre de périmètres du droit des sols (pour le résumé de §4/tiroir).
export function dispositifsCount(d: NonNullable<Fiche['dispositifs']>): number {
  return (d.er?.length ?? 0) + (d.ebc?.length ?? 0) + (d.sup?.length ?? 0)
    + (d.dpu.etat === 'servi' ? 1 : 0) + (['A', 'B', 'C', 'D'].includes(d.peb.zone) ? 1 : 0)
}

/** §4 Urbanisme — corps « droit des sols » (ER / EBC / doc urba / DPU / PEB / SUP), sans son RefDrawer. */
export function DispositifsBody({ d }: { d: NonNullable<Fiche['dispositifs']> }) {
  // FICHE-FIX-5 (reste 3) — ER / EBC / DPU / PEB / SUP en Lignes COURTES ; les paragraphes (source,
  // article, détail) passent derrière le « i ». Code court en valeur (« PM1 · PPR … » via title).
  return (
      <div className="flex flex-col gap-3" data-dispositifs>
        <Lignes>
          {(d.er ?? []).map((e, i) => (
            <Ligne key={`er${i}`} ton={e.part_pct >= 50 ? 'ambre' : undefined}
              label={<>Emplacement réservé<InfoI aria="Sur l'emplacement réservé" tip={`${e.libelle ? `${e.libelle}. ` : ''}Surface réservée déduite de l'emprise constructible (pré-faisabilité). Source : prescriptions PLU (GPU).`} /></>}
              valeur={<>{e.part_pct} <small>% de la parcelle</small></>} />
          ))}
          {(d.ebc ?? []).map((e, i) => (
            <Ligne key={`ebc${i}`}
              label={<>Espace boisé classé<InfoI aria="Sur l'EBC" tip={`${e.libelle ? `${e.libelle}. ` : ''}Construction interdite sur l'emprise boisée classée (art. L113-1 et L113-2 CU) — part soustraite de l'assiette. Source : GPU.`} /></>}
              valeur={<>{e.part_pct} <small>%</small></>} />
          ))}
          {d.plu_procedure && (
            <Ligne label={<>Document d'urbanisme<InfoI aria="Sur la procédure PLU" tip={d.plu_procedure.detail} /></>}
              valeur={<a href={d.plu_procedure.lien} target="_blank" rel="noreferrer" className="text-mint hover:underline">enquête publique ↗</a>} />
          )}
          <Ligne data-dispositifs-dpu ton={d.dpu.etat === 'servi' ? undefined : 'gris'}
            label={<>Préemption (DPU)<InfoI aria="Sur la préemption" tip={d.dpu.etat === 'servi'
              ? `${d.dpu.statut === 'renforce' ? 'DPU renforcé' : 'DPU simple'} — la commune peut préempter à la vente (DIA, ~2 mois).`
              : d.dpu.etat === 'hors' ? 'Hors périmètre de préemption publié.' : `Non déterminée — ${d.dpu.detail}.`} /></>}
            valeur={d.dpu.etat === 'servi' ? (d.dpu.statut === 'renforce' ? 'DPU renforcé' : 'DPU simple') : d.dpu.etat === 'hors' ? 'hors périmètre' : 'non déterminée'} />
          <Ligne data-dispositifs-peb ton={['A', 'B'].includes(d.peb.zone) ? 'ambre' : (['C', 'D'].includes(d.peb.zone) ? undefined : 'gris')}
            label={<>Bruit aérien (PEB)<InfoI aria="Sur le PEB" tip={['A', 'B', 'C', 'D'].includes(d.peb.zone)
              ? `${d.peb.libelle ? `${d.peb.libelle}. ` : ''}${PEB_PHRASES[d.peb.zone]}`
              : d.peb.zone === 'hors' ? `Hors zones PEB${d.peb.detail ? ` — ${d.peb.detail}` : ''}.` : `Non déterminée${d.peb.detail ? ` — ${d.peb.detail}` : ''}.`} /></>}
            valeur={['A', 'B', 'C', 'D'].includes(d.peb.zone) ? `Zone ${d.peb.zone}` : d.peb.zone === 'hors' ? 'hors zone' : 'non déterminée'} />
          {(d.sup ?? []).map((sv, i) => (
            <Ligne key={`sup${i}`} data-dispositifs-sup title={sv.libelle || sv.categorie}
              label={<>Servitude (SUP)<InfoI aria="Sur la servitude" tip={`${sv.categorie} · ${sv.libelle || 'servitude'}. Assiettes publiées au GPU (T5/PT1/PT2 restreintes ; AS1 captages non publiée pour le 974).`} /></>}
              valeur={<>{sv.categorie}{sv.libelle ? <small> · {sv.libelle}</small> : null}</>} />
          ))}
        </Lignes>
      </div>
  )
}

// tiroir « Dispositifs et périmètres » actuel = corps + son RefDrawer (conservé jusqu'au basculement).
function DispositifsDrawer({ d }: { d: NonNullable<Fiche['dispositifs']> }) {
  const nEls = dispositifsCount(d)
  return (
    <RefDrawer id="dispositifs" icon={IC.faisa} name="Dispositifs et périmètres"
      context="ER · EBC · DPU · PEB · SUP"
      value={nEls > 0
        ? <Badge ton="ambre">{nEls} périmètre{nEls > 1 ? 's' : ''}</Badge>
        : <Badge ton="vert">rien à signaler</Badge>}>
      <DispositifsBody d={d} />
    </RefDrawer>
  )
}

// ── RETOURS-11F4 (F5) — la SECTION « Constructibilité » (RefDrawer + Mode B), auto-suffisante :
// re-dérive ses locaux depuis `f` + le bilan (queryKey ['bilan', idu] partagée, 0 requête en plus).
export function ConstructibiliteSection({ f, idu }: { f: Fiche; idu: string }) {
  const setModule = useApp((s) => s.setModule)
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const faisa = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu), enabled: !!f })
  const cap = faisa.data?.capacite
  const fo = cap?.fourchette
  const delaisse = faisa.data?.delaisse
  const reglesZone = f.reglement_plu?.zones?.[0]?.zone
  const reglesSdp = f.potentiel_transformation?.sdp_residuelle_m2
  // FRONT-CHIFFRES-2 (F01a) — verdict de constructibilité NEUVE servi par la cascade (même valeur
  // que la fiche et la garde SDP résiduelle) ; plus de regex front sur le libellé de zone.
  const nonConstructible = f.reglement_plu?.constructible_neuf === false
  const logMax = Array.isArray(fo?.logements_au_sol)
    ? Math.max(fo.logements_au_sol[0] ?? 0, fo.logements_au_sol[1] ?? 0)
    : (typeof fo?.logements_au_sol === 'number' ? fo.logements_au_sol : null)
  const capaciteNulle = logMax != null && logMax <= 0
  const logementsNonCalculable = nonConstructible || capaciteNulle
  // RETOURS-11F4 F5 — fourchette bornes égales → un seul nombre (« 2 », jamais « 2–2 »), comme la grille capacité.
  const logtsInterval = Array.isArray(fo?.logements_au_sol)
    ? (fo.logements_au_sol[0] === fo.logements_au_sol[1] ? `${fo.logements_au_sol[0]}` : `${fo.logements_au_sol[0]}–${fo.logements_au_sol[1]}`)
    : null
  const logementsTxt = delaisse ? `délaissé (${delaisse.surface_m2} m²)`
    : nonConstructible ? 'non calculable'
      : capaciteNulle ? undefined
        : (logMax != null && logMax > 0)
          ? (logtsInterval ? `${logtsInterval} logts` : `${fo!.logements_au_sol} logts`)
          : (reglesSdp != null && reglesSdp > 0 ? `~${fmtInt(reglesSdp)} m² SDP` : 'à estimer')
  return (
    <>
      <RefDrawer id="faisabilite" icon={IC.faisa} name="Constructibilité" value={logementsTxt}
        valueColor={logementsNonCalculable ? 'var(--txt-faint)' : undefined}
        context={delaisse
          ? `surface ${delaisse.surface_m2} m² · seuil ${delaisse.seuil_m2} m²`
          : logementsNonCalculable ? (reglesZone ? `zone ${reglesZone} · sans objet` : 'sans objet')
            : [fo?.niveaux ?? null, 'calcul tracé'].filter(Boolean).join(' · ') || 'calcul tracé'}
        micro={<MicroTriple items={delaisse
          ? [`surface ${delaisse.surface_m2} m²`, `seuil délaissé ${delaisse.seuil_m2} m²`, 'bilan non servi']
          : [fo?.niveaux ?? 'gabarit', <>SDP <span style={{ color: 'var(--txt-dim)' }}>{fo?.surface_plancher_m2 ?? reglesSdp ?? '—'} m²</span></>, 'calcul tracé']} />}>
        <div className="flex flex-col gap-3">
          {/* KELFONCIER-FIX-1 (Lot A) — CAUSE §10 : une zone AU FERMÉE (ou au statut non déterminé)
              explique un potentiel nul — la parcelle n'est pas constructible tant que le PLU n'a pas
              ouvert la zone. Le motif cité vient du règlement (moteur d'ouverture AU). */}
          {f.au_ouverture?.bloquant && (
            <div data-au-ouverture-cause>
              <Vigilance title={`Zone AU${f.au_ouverture.zone_lib ? ` (${f.au_ouverture.zone_lib})` : ''} — ${f.au_ouverture.statut}.`} />
              {f.au_ouverture.motif && <FactNote>{f.au_ouverture.motif}</FactNote>}
            </div>
          )}
          {/* RETOURS-20 Z5 — l'alerte « délaissé » (boîte bordée creuser) devient une Vigilance
              (filet ambre à gauche, sans boîte). Libellé inchangé. */}
          {delaisse && (
            <div data-delaisse><Vigilance title={delaisse.libelle} /></div>
          )}
          {/* capacité + SDP + potentiel de transformation (SDP consommée/résiduelle/surélévation) reçu d'Urbanisme */}
          {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
          <FaisabiliteTab idu={idu} />
          {!delaisse && <BilanTab idu={idu} />}
          {/* FICHE-1 lot 5 — taxe d'aménagement estimée (table rase) + lien vers l'outil pour
              changer les hypothèses. Omise si pas de scénario constructible (f.taxe_amenagement null). */}
          {f.taxe_amenagement && <TaxeAmenagementBlock t={f.taxe_amenagement} />}
          {f.taxe_amenagement && (
            <PorteOutil ico="€" data="taxe-amenagement-outil" titre="Taxe d'aménagement"
              sous="Changer les hypothèses (résidence principale, logement aidé, piscine, taux communal)"
              onClick={() => { setParcelPrefill(idu); setModule('taxe-amenagement') }} />
          )}
          <PorteOutil ico="◱" data="faisabilite-outil" titre="Faisabilité"
            sous={`La capacité constructible de ces ${fmtM2(f.surface_m2)} : SDP, hauteur PLU, calcul tracé`}
            onClick={() => { setParcelPrefill(idu); setModule('programme') }} />
          <PorteOutil ico="▦" data="calculette" titre="Calculette foncière"
            sous={`Ce terrain de ${fmtM2(f.surface_m2)} : SDP, prix de sortie, votre coût et marge`}
            onClick={() => { setCalcPrefill(idu); setModule('calculette-fonciere') }} />
          <PorteOutil ico="⧉" data="assemblage-outil" titre="Assemblage"
            sous={`Partir de ces ${fmtM2(f.surface_m2)} et agréger les parcelles contiguës`}
            onClick={() => { setParcelPrefill(idu); setModule('assemblage') }} />
        </div>
      </RefDrawer>
      {/* SOURCES-1 lot 1 — Dispositifs et périmètres (ER/EBC/DPU/PEB/SUP), tiroir distinct. */}
      {f.dispositifs && <DispositifsDrawer d={f.dispositifs} />}
      {/* FICHE-RANGEMENT-3 Lot 3 — ModeBDrawer devenu ModeBBody (bloc inline §11). Ce composant
          ConstructibiliteSection est mort (dissous au basculement rangement-2) — conservé compilable. */}
      {f.mode_b?.indisponible
        ? <BlocIndisponible titre="Réhabilitation (Mode B)" />
        : f.mode_b?.disponible && <ModeBBody idu={idu} initial={f.mode_b} />}
    </>
  )
}
