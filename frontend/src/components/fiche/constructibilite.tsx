/**
 * fiche/constructibilite.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F5).
 * La section « Constructibilité » + toute sa machinerie (capacité, calcul tracé, bilan, Mode B,
 * RTAA, calculette de charge foncière, potentiel de transformation). Extrait de Fiche.tsx.
 * Cycle-free : n'importe QUE des primitives + blocs feuilles, jamais Fiche.tsx.
 * Fiche.tsx ré-exporte Calculette + FaisabiliteTab (consommés par EtudierBien / M22Programme / test).
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { faisabiliteExplain, getCalculetteDefaults, getFaisabilite, getModeB, postChargeFonciere, type CalculetteDefaults } from '../../lib/api'
import { fmtEurCompact, fmtInt, fmtM2 } from '../../lib/format'
import { PERIM_POTENTIEL_COURT, PERIM_RESIDUEL_COURT } from '../../lib/perimetres'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { AvisIA } from '../AvisIA'
import { renderRich } from './AskBar'
import { BlocIndisponible } from './BlocIndisponible'
import type { Fiche, PotentielTransformation } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { IC, RefDrawer, MicroTriple, PorteOutil, StepProv, HypInput, GroupLabel, FactRow, FactNote, RefLink, Vigilance } from './primitives'

const PT_COLORS: Record<string, string> = { fort: '#4ADE96', modere: '#F5C244', faible: '#9AA6A0', nul: '#6B7280', indetermine: '#6B7280' }
function TransformationBlock({ pt }: { pt: PotentielTransformation }) {
  if (pt.indisponible) return <BlocIndisponible titre="Potentiel de transformation" />   // M125 — panne ≠ absence
  const color = PT_COLORS[pt.niveau] ?? '#9AA6A0'
  // RETOURS-20 Z3 — plus de card-elev : kicker (titre + badge d'état à droite), les lignes
  // chiffrées deviennent des FactRow (valeur mono à droite), la source passe en FactNote.
  return (
    <div data-transformation>
      <GroupLabel right={
        <span className="rounded-full px-2 py-0.5 text-[10.5px] font-medium capitalize" style={{ background: `${color}22`, color }}>{pt.niveau}</span>
      }>Potentiel de transformation</GroupLabel>
      <p className="mt-1 text-[11px] leading-snug text-txt-mut">{pt.libelle}</p>
      {pt.pct_consomme != null && <FactRow label="SDP consommée / autorisée" value={<>{pt.pct_consomme} <small>%</small></>} />}
      {pt.sdp_residuelle_m2 != null && pt.sdp_residuelle_m2 > 0 && <FactRow label={`SDP résiduelle estimée · ${PERIM_RESIDUEL_COURT}`} value={<>~{fmtInt(pt.sdp_residuelle_m2)} <small>m²</small></>} />}
      {pt.surelevation_possible != null && <FactRow label="Surélévation" value={pt.surelevation_possible ? <>possible{pt.hauteur_marge_m != null ? <> <small>(marge ~{pt.hauteur_marge_m} m)</small></> : ''}</> : 'non'} tone={pt.surelevation_possible ? undefined : 'mute'} />}
      <FactNote>{pt.source}</FactNote>
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
        <div data-calc-erreur className="card-elev px-3 py-2.5 text-[11px] text-txt">
          <p className="text-st-creuser">Chargement de la calculette impossible.</p>
          <button onClick={() => defs.refetch()} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Réessayer</button>
        </div>
      </div>
    )
  }
  if (!defs.data) {
    return (
      <div data-calculette>
        <p className="label-caps mb-1">Calculette de charge foncière</p>
        <div className="card-elev px-3 py-2.5 text-[11px] text-txt"><Loading label="Chargement" /></div>
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
        {q.isLoading && <Loading label="Calcul en cours" />}
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
                LABUSE (sourcé) : SHAB vendable <b className="tnum text-txt">{fmtInt(Number(d.shab_vendable_m2))} m²</b> <span className="text-txt-dim">({PERIM_POTENTIEL_COURT})</span> ·
                <span title="Prix de commercialisation du NEUF, à l'échelle du secteur (avec repli commune/île) — pas le prix du bâti ancien de la commune"> prix de sortie neuf</span> <b className="tnum text-txt">{fmtInt(Number(d.prix_sortie_median))} €/m²</b> ·
                terrain <b className="tnum text-txt">{fmtInt(Number(d.terrain_m2))} m²</b>
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
                      {Number(cf.par_m2_terrain) >= Number(d.terrain_zone_eur_m2)
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

// OUTILS-FIX-3 Lot F — `embedded` : FaisabiliteTab est partagé entre la FICHE (garde l'IA) et l'OUTIL
// Faisabilité (M22, mode « par parcelle »). Hors fiche, on cantonne l'IA : le bouton « Expliquer ce
// calcul en clair » (faisabiliteExplain) et l'encart AvisIA ne s'affichent QUE dans la fiche. Le calcul
// tracé, la capacité et la charge foncière restent — l'outil ne perd pas son contenu utile (F3).
export function FaisabiliteTab({ idu, embedded }: { idu: string; embedded?: boolean }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  // §1e — le calcul étape par étape est OUVERT par défaut (on passait à côté quand il était replié) ;
  // mis en valeur dans un encadré dédié « Le calcul, étape par étape » plutôt qu'un accordéon discret.
  const [showSteps, setShowSteps] = useState(true)
  const explain = useMutation({ mutationFn: () => faisabiliteExplain(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
  if (isError || !b) return <ErrorState message="Faisabilité indisponible." retry={() => refetch()} />

  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const steps: { label: string; valeur: string; source: string; prov: string }[] = cap?.steps ?? []
  // FAISABILITE (mandat) — ÉTAPE MANQUANTE tracée : le saut « SHAB brute ~175 m² » (une étape) →
  // « SHAB vendable ~123 m² » (en-tête) n'était pas dans la trace. Le vendable est calculé par le
  // moteur (engine.py: shab_vendable_m2 = sol_central × logt_moyen) : c'est le nombre de logements
  // RETENUS au sol (après plafond de densité ∩ stationnement ∩ modulation réunionnaise) reconverti en
  // surface habitable (~72,5 m²/logt) — PAS un simple plafond appliqué à la SHAB brute. On expose la
  // valeur SERVIE (fo.shab_vendable_m2), avec la vraie raison. Provenance « Dérivé » (cohérente moteur).
  const stepsAff = steps.length > 0 && fo.shab_vendable_m2 != null
    ? [...steps, {
        label: 'SHAB vendable retenue',
        valeur: `~${fmtM2(fo.shab_vendable_m2)}`,
        source: 'logements retenus au sol × surface moyenne/logement — base du CA (la SHAB brute est théorique)',
        prov: 'derive',   // LOT2 — la clé StepProv est 'derive' (sans accent) ; 'dérivé' retombait sur « — »
      }]
    : steps
  const ex = explain.data
  // M58-P1 (c) : « un zéro n'est pas une absence ». Capacité réelle = fourchette logements > 0.
  const logAuSol = Array.isArray(fo.logements_au_sol) ? fo.logements_au_sol : null
  const logMax = logAuSol ? Math.max(logAuSol[0] ?? 0, logAuSol[1] ?? 0) : null
  const capaciteReelle = logMax != null && logMax > 0
  return (
    <div className="flex flex-col gap-3">
      {/* ── LE RÉSULTAT (bloc capacité UNIQUE — M58-P1 b) ── */}
      {/* RETOURS-20 Z3 — plus de boîte bordée mint : kicker « Capacité constructible » (verdict à
          droite) + les 4 tuiles de stat (autorisées par la maquette). La phrase de méthode passe en
          FactNote ; la zone non calibrée en Vigilance. */}
      {cap ? (
        <div>
          <GroupLabel right={<span className="text-[13px] font-medium text-txt-hi normal-case">{cap.verdict}</span>}>Capacité constructible</GroupLabel>
          {/* M58-P1 (c) : jamais « 0–0 » / « ( m) » / « ~— » — on n'affiche la grille que si la
              capacité est réelle ; chaque champ retombe sur « — » plutôt qu'un zéro/vide trompeur. */}
          {capaciteReelle ? (
            <>
              <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-txt-mut">
                <div>Gabarit : <b className="text-txt">{fo.niveaux && fo.hauteur_m != null ? `${fo.niveaux} (${fo.hauteur_m} m)` : '—'}</b></div>
                <div>SDP : <b className="text-txt">{fo.surface_plancher_m2 ? fmtM2(fo.surface_plancher_m2) : '—'}</b></div>
                {/* RETOURS-11 F5 — fourchette bornes égales → un seul nombre (« 2 », plus jamais « 2–2 »). */}
                <div>Logements : <b className="text-txt">{logAuSol![0] === logAuSol![1] ? `${logAuSol![0]}` : `${logAuSol![0]}–${logAuSol![1]}`}</b></div>
                <div>SHAB vendable <span className="text-txt-dim">({PERIM_POTENTIEL_COURT})</span> : <b className="text-txt">{fo.shab_vendable_m2 ? `~${fmtM2(fo.shab_vendable_m2)}` : '—'}</b></div>
              </div>
              {/* FAISABILITE (mandat) : dire pourquoi la SHAB vendable (~123) < SHAB brute — c'est le
                  nombre de logements RETENUS reconverti en surface, pas un plafond sur la brute (théorique). */}
              <FactNote>SHAB vendable = logements retenus au sol × surface moyenne/logement (fourchette après plafond de densité). La SHAB brute est théorique, hors bâti existant.</FactNote>
            </>
          ) : (
            <div className="mt-1.5 text-[11px] text-txt-faint">Capacité logements non calculable pour cette parcelle.</div>
          )}
          {!cap.calibree && <div className="mt-1 text-[11px] text-st-creuser">▲ estimation générique (zone non calibrée)</div>}
          <FactNote>{cap.bandeau}</FactNote>
        </div>
      ) : (
        <p className="text-[11px] text-txt-mut">
          Zone PLU non résolue pour cette parcelle — capacité non calculable (honnête).
        </p>
      )}

      {/* ── LE CALCUL, ÉTAPE PAR ÉTAPE (déterministe) — §1e : ouvert par défaut ── */}
      {/* RETOURS-20 Z3 — plus de boîte bordée mint autour : le bouton de repli sert d'en-tête, la
          liste d'étapes (ol.steps + StepProv) garde sa structure (rule 7, conforme maquette). */}
      {stepsAff.length > 0 && (
        <div>
          <button onClick={() => setShowSteps((s) => !s)} className="mb-1 flex w-full items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-mint transition-colors duration-quick hover:text-txt-hi">
            <span>▾ Le calcul, étape par étape ({stepsAff.length})</span>
            <span>{showSteps ? '−' : '+'}</span>
          </button>
          {showSteps && (
            // RETOURS-23 Z3 — plus de boîte striée (card-elev + bg alternés) : filets entre étapes,
            // valeur mono alignée à droite, badge de provenance sous la ligne (grammaire de la maquette).
            <ol data-faisa-steps>
              {stepsAff.map((s, i) => (
                <li key={i} className="flex items-start gap-2 border-b border-line/60 py-1.5 text-[11px] last:border-0">
                  <span className="shrink-0 font-mono text-[9px] text-txt-dim">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-txt">{s.label}</span>
                      <b className="shrink-0 font-mono font-medium tnum text-txt-hi">{s.valeur}</b>
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5">
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

      {/* ── EXPLIQUER CE CALCUL EN CLAIR (IA, sur clic) — M58-P1 (e) : SEULEMENT s'il y a un
          calcul à expliquer (steps > 0). Sur une parcelle non calculable (0 step), pas de bouton.
          OUTILS-FIX-3 Lot F — l'IA est cantonnée à la fiche parcelle et au Copilote : `!embedded`
          (l'outil Faisabilité, qui embarque ce composant, n'affiche donc pas ce point d'entrée IA). ── */}
      {!embedded && cap && steps.length > 0 && (
        <div data-faisa-explain>
          {!ex && !explain.isPending && (
            <button onClick={() => explain.mutate()} data-faisa-explain-btn
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-violet/50 bg-violet/[0.07] py-2 text-[12px] font-medium text-violet hover:bg-violet/10">
              <svg viewBox="0 0 20 20" className="h-3.5 w-3.5"><path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" fill="currentColor" /></svg>
              Expliquer ce calcul en clair
            </button>
          )}
          {explain.isPending && <p className="flex items-center gap-2 py-2 text-[11px] text-violet"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet" /> L'IA lit les étapes du calcul…</p>}
          {explain.isError && <p className="py-1 text-[11px] text-st-ecartee">Explication indisponible — réessayez.</p>}
          {ex && ex.disponible === false && <p className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">{ex.message}</p>}
          {ex && ex.disponible && ex.rejected && <p className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] text-st-creuser">{ex.texte}</p>}
          {ex && ex.disponible && !ex.rejected && (
            <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2.5">
              <AvisIA className="mb-2 border-violet/25 bg-violet/[0.05] text-txt-mut" />
              <p className="mb-1 font-mono text-[10px] tracking-widest text-violet">✦ EXPLICATION IA — À PARTIR DES ÉTAPES</p>
              <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-txt">{renderRich(ex.texte ?? '')}</p>
              <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">L'IA narre les étapes ci-dessus (elle ne recalcule rien) ; chaque chiffre est ancré sur une étape. Estimation indicative, ne vaut pas conseil.</p>
            </div>
          )}
        </div>
      )}

      {/* M60 P1a — la CALCULETTE interactive a quitté la fiche : elle vit dans l'outil « Calculette
          foncière » (moteur unique). La fiche garde le bilan en LECTURE (capacité/gabarit/SDP ci-dessus)
          + une PORTE pré-remplie posée au pied du tiroir Constructibilité (voir Fiche, RefDrawer faisabilite). */}
    </div>
  )
}

function BilanTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
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
      {b.marche?.median != null && (
        <div>
          <GroupLabel>Prix de sortie retenu (bilan)</GroupLabel>
          <FactRow label="Prix de sortie retenu" value={<>{fmtInt(Number(b.marche.median))} <small>€/m² bâti</small></>} />
          <FactNote>Valeur retenue pour le calcul de charge foncière. Détail du marché (échantillon, rayon, tendance, fraîcheur) → section « Marché et secteur ».</FactNote>
        </div>
      )}
      {/* M58-P1 : note « la charge foncière est dans Faisabilité » RETIRÉE — elle pointait vers la
          calculette rendue juste au-dessus (FaisabiliteTab), dans le MÊME tiroir : redondante. */}
      <div>
        <GroupLabel>Fiscal &amp; leviers</GroupLabel>
        <FactRow label="QPV" value={<span className={b.fiscal.qpv ? 'text-mint' : 'text-txt-mut'}>{b.fiscal.qpv ? 'OUI' : 'non'}</span>} tone={b.fiscal.qpv ? undefined : 'mute'} />
        <FactRow label="TVA" value={b.fiscal.tva} />
        <FactNote>{b.fiscal.ta_note}</FactNote>
      </div>
      {b.rtaa && <RtaaBlock rtaa={b.rtaa} />}
    </div>
  )
}

/** RTAA DOM (mandat 5bis) — rappel réglementaire de CONCEPTION, vérifié Légifrance
 *  (config/rtaa_dom.yaml). Les seuils d'altitude (400/600 m) sont énoncés dans chaque
 *  exigence — l'altitude de la parcelle n'est pas calculée ici (consigné). */
/** M33 — MODE B (réhabilitation) : lecture COMPLÉMENTAIRE, visuellement subordonnée au tier
 *  (M34 intact). TOUJOURS Estimé (le paramètre travaux l'est) — assumé au libellé. Le
 *  paramètre est un état d'UI : rien n'est persisté (recalcul via /parcels/{idu}/mode-b). */
function ModeBDrawer({ idu, initial }: { idu: string; initial: import('../../lib/types').ModeB }) {   // M55-L point 10 : defaultOpen retiré (accordéon contrôlé, initial fermé)
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
    <RefDrawer id="mode-b" icon={IC.faisa} name="Réhabilitation" context="bâti trop petit"
      value={<span className="pill-amber">non pertinent</span>}>
      <p data-mode-b-trop-petit style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#8FA69A' }}>
        {mb.motif ?? `Bâti trop petit (SHAB ~${mb.shab_rehabilitable_m2 ?? '—'} m²) pour une thèse de réhabilitation.`}
      </p>
    </RefDrawer>
  )
  if (!mb.composantes) return null
  const c = mb.composantes
  const [bMin, bMax] = c.travaux.bornes
  const foncierM2 = mb.surface_parcelle_m2 ?? mb.terrain_nu?.surface_m2 ?? null
  return (
    <RefDrawer id="mode-b" icon={IC.faisa} name="Réhabilitation"
      context="Estimé — hypothèse travaux à ajuster"
      value={mb.negatif ? <span className="pill-amber">bilan négatif</span> : `~${mb.achat_max_libelle ?? ''}`}>
      <div data-mode-b style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)' }}>Surface réhabilitable</span>
            <span style={{ color: 'var(--txt-hi)' }}>~{fmtInt(c.surface.shab_rehabilitable_m2)} m² hab.</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
            emprise {fmtInt(c.surface.emprise_bati_m2)} m² <b style={{ color: '#5CE6A1' }}>Sourcé</b> ({c.surface.source_emprise}) × {c.surface.niveaux} niveau(x){' '}
            <b style={{ color: c.surface.niveaux_reels ? '#5CE6A1' : '#E8B44C' }}>{c.surface.niveaux_reels ? 'Sourcé' : 'Estimé'}</b>
            {' '}— {c.surface.niveaux_etiquette}
          </p>
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
        {mb.sortie_locative && (
          <div data-mode-b-locatif style={{ borderTop: '1px solid #24312b', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--txt-hi)', fontWeight: 600 }}>Sortie locative</p>
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
        )}
        <p style={{ margin: 0, fontSize: 9.5, lineHeight: 1.45, color: '#6b7a72' }}>{mb.avertissement}</p>
      </div>
    </RefDrawer>
  )
}

function RtaaBlock({ rtaa }: { rtaa: { meta: Record<string, string>; exigences: { volet: string; exigence: string; reference: string; url: string; condition_altitude?: string }[] } }) {
  const [open, setOpen] = useState(false)
  const VOLET_COLOR: Record<string, string> = { cadre: '#8FA69A', thermique: '#E8B44C', acoustique: '#B497F0', aeration: '#7DE8E0', ecs: '#5CE6A1' }
  return (
    // RETOURS-20 Z3 — plus de card-elev ni de tuiles bg-surface-3 : kicker + note, chaque exigence
    // à plat (badge volet + phrase + renvoi d'article RefLink), séparée par le filet des lignes.
    <div data-rtaa-block>
      <GroupLabel>RTAA DOM — rappel réglementaire</GroupLabel>
      <p className="mt-1 text-[10.5px] leading-snug text-txt-mut">
        Construction neuve de logements : protection solaire, ventilation traversante,
        acoustique, aération et ECS renouvelable s'appliquent (seuils d'altitude 400/600 m).
        <button onClick={() => setOpen((o) => !o)} className="ml-1.5 text-mint hover:underline">
          {open ? 'replier' : `${rtaa.exigences.length} exigences →`}
        </button>
      </p>
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
  const nonConstructible = !!(reglesZone && /^(A(?!U)|N)/i.test(reglesZone))
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
          {/* RETOURS-20 Z5 — l'alerte « délaissé » (boîte bordée creuser) devient une Vigilance
              (filet ambre à gauche, sans boîte). Libellé inchangé. */}
          {delaisse && (
            <div data-delaisse><Vigilance title={delaisse.libelle} /></div>
          )}
          {/* capacité + SDP + potentiel de transformation (SDP consommée/résiduelle/surélévation) reçu d'Urbanisme */}
          {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
          <FaisabiliteTab idu={idu} />
          {!delaisse && <BilanTab idu={idu} />}
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
      {/* Mode B — Réhabilitation, rattaché à la Constructibilité (tiroir distinct, accordéon exclusif). */}
      {f.mode_b?.indisponible
        ? <BlocIndisponible titre="Réhabilitation (Mode B)" />
        : f.mode_b?.disponible && <ModeBDrawer idu={idu} initial={f.mode_b} />}
    </>
  )
}
