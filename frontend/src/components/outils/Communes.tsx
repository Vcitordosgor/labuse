import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { modVelocite, motMarcheCommune, motRarete } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { TOKENS } from '../../lib/tokens'
import { O6Comparateur } from './blocB'
import { M18, MarcheCommune } from './moteurs'

// M137-Z — OUTIL « COMMUNES » : fusion des 4 outils échelle-commune (Rareté · Vélocité · Marché ·
// Comparateur). Entrée = la table des 24 communes (le Comparateur). Clic → fiche commune (tous ses
// indicateurs) + « Voir ses parcelles → » (carte filtrée). Baromètre (île) et Suivi de secteur
// (secteur) restent séparés — autre échelle. Chaque indicateur vient d'UN endroit (voir en-tête doc).
const fmt = (v: unknown, s = '') => (v == null ? '—' : `${Number(v).toLocaleString('fr-FR')}${s}`)

function Row({ lbl, val, strong }: { lbl: string; val: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="min-w-0 text-txt-mut">{lbl}</span>
      <span className={`tnum shrink-0 ${strong ? 'font-semibold text-mint' : 'text-txt'}`}>{val}</span>
    </div>
  )
}

// Ancres du header sticky (mandat COMMUNES) : sautent aux sections/sous-groupes du corps défilant.
// prix/dynamique/offre/loyer = sous-groupes de MarcheCommune (data-anchor posé là) ; zan = section ZAN.
const FICHE_ANCRES: [string, string][] = [
  ['marche', 'Marché'], ['prix', 'Prix'], ['dynamique', 'Dynamique'],
  ['offre', 'Offre'], ['zan', 'ZAN'], ['loyer', 'Loyer'],
]

function CommuneFiche({ commune, onBack }: { commune: string; onBack: () => void }) {
  const setCommune = useApp((s) => s.setCommune)
  const setModule = useApp((s) => s.setModule)
  const rar = useQuery({ queryKey: ['communes-rarete'], queryFn: motRarete })
  const vel = useQuery({ queryKey: ['communes-velocite'], queryFn: () => modVelocite() })
  // Signal marché pour l'en-tête sticky — MÊME clé que MarcheCommune (React Query dédoublonne, 0 fetch en plus).
  const mar = useQuery({ queryKey: ['mu-marche', commune], queryFn: () => motMarcheCommune(commune) })
  const r = (rar.data?.communes ?? []).find((c) => c['commune'] === commune) as Record<string, any> | undefined
  const v = (vel.data?.communes ?? []).find((c) => c['commune'] === commune) as Record<string, any> | undefined
  const homogene = vel.data?.['communes_homogenes'] as boolean | undefined
  const sig = mar.data?.['market_signal'] as Record<string, any> | undefined
  const sigLabel = sig?.['disponible'] ? String(sig['label']) : null
  const sigCol = sigLabel === 'favorable' ? TOKENS.mint : sigLabel === 'prudence' ? TOKENS.stEcartee : TOKENS.stCreuser

  // Fix du scroll (mandat) : le corps est le SEUL conteneur défilant ; le header reste (sticky/shrink-0),
  // les ancres y sautent via scrollIntoView sur le corps.
  const bodyRef = useRef<HTMLDivElement>(null)
  const jump = (id: string) => {
    const el = bodyRef.current?.querySelector(`[data-anchor="${id}"]`)
    if (el) (el as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* HEADER STICKY — nom + signal marché + ancres. Reste visible pendant le défilement du corps. */}
      <div className="shrink-0 border-b border-line pb-2">
        <div className="flex items-center justify-between gap-2">
          <button data-communes-retour onClick={onBack} className="text-[11px] text-mint hover:underline">‹ Toutes les communes</button>
          <button data-communes-parcelles onClick={() => { setCommune(commune); setModule(null) }}
            className="rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25">
            Voir ses parcelles →
          </button>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <h3 className="text-[15px] font-semibold text-txt-hi">{commune}</h3>
          {sigLabel && (
            <span data-fiche-signal className="rounded-full border px-2 py-0.5 text-[10.5px] font-medium"
              style={{ color: sigCol, borderColor: `${sigCol}55`, background: `${sigCol}22` }}>
              signal : {sigLabel}
            </span>
          )}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-1">
          {FICHE_ANCRES.map(([id, lbl]) => (
            <button key={id} data-fiche-ancre={id} onClick={() => jump(id)}
              className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">
              {lbl}
            </button>
          ))}
        </div>
      </div>

      {/* CORPS — scroll UNIQUE : toute l'info atteignable à zoom 100 % (le nested-scroll de MarcheCommune,
          qui bridait, est désactivé en mode embarqué). */}
      <div ref={bodyRef} className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pt-2">
        {/* MARCHÉ — les 9 lignes sourcées (Prix / Dynamique / Offre / Loyer), via communeProp. */}
        <section data-anchor="marche" className="flex flex-col">
          <p className="label-caps text-[9.5px]">Marché</p>
          {/* Réconciliation € ancien (mandat, point 3) : ICI = prix LOCAL (secteur autour de la parcelle
              centrale, appartements priorisés) ; le tableau des 24 communes = médiane COMMUNE ENTIÈRE.
              Deux séries légitimes → un écart est normal, pas une erreur. */}
          <p className="mb-1 text-[9px] leading-snug text-txt-dim">
            Prix ancien = médiane <b>locale</b> (secteur autour de la parcelle centrale). Le tableau des
            24 communes affiche la médiane <b>commune entière</b> — les deux diffèrent normalement.
          </p>
          <MarcheCommune communeProp={commune} />
        </section>

        {/* RARETÉ & ZAN — M137-Z : le STOCK porte « foncier » ; « reste ZAN » = un droit à artificialiser.
            audit-zan : l'enveloppe ZAN de l'ex-Simulateur ZAN vit désormais ICI (budget en %). */}
        <section data-anchor="zan" className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
          <p className="label-caps text-[9.5px]">Rareté &amp; ZAN</p>
          {r ? (
            <div className="mt-1 flex flex-col gap-0.5 text-[11px]">
              <Row lbl="Foncier repéré — stock de parcelles promues" val={fmt(r['stock_opportunites_ha'], ' ha')} strong />
              {/* Budget ZAN en % D'ABORD (c'est lui qui parle), caveat ESTIMÉ collé au chiffre. */}
              {r['pct_budget_consomme'] != null && (
                <div className="mt-0.5 rounded-md bg-surface-3 px-2 py-1">
                  <div className="flex items-baseline gap-1.5">
                    <b className={`tnum text-[14px] ${(r['pct_budget_restant'] as number) < 0 ? 'text-st-ecartee' : 'text-st-creuser'}`}>{r['pct_budget_consomme']} %</b>
                    <span className="text-[10px] text-txt-mut">du budget ZAN consommé</span>
                    <span className={`ml-auto tnum text-[11px] ${(r['pct_budget_restant'] as number) < 0 ? 'text-st-ecartee' : 'text-txt'}`}>{r['pct_budget_restant']} % restant</span>
                  </div>
                  <p className="mt-0.5 text-[9px] leading-snug text-st-creuser"><b>Estimé</b> (règle -50 %, SAR non territorialisé) — <b>pas un droit à construire</b>.</p>
                </div>
              )}
              <Row lbl="Droit à artificialiser restant (ZAN, estimé)" val={fmt(r['reste_zan_ha'], ' ha')} />
              <Row lbl="Budget ZAN 2021-31 (estimé)" val={fmt(r['budget_zan_ha'], ' ha')} />
              <Row lbl="Rythme de consommation" val={fmt(r['rythme_conso_ha_an'], ' ha/an')} />
              <Row lbl="Horizon d'épuisement de l'enveloppe ZAN" val={r['horizon_epuisement_ans'] == null ? 'non projetable' : `${r['horizon_epuisement_ans']} ans`} />
              <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{rar.data?.caveat}</p>
            </div>
          ) : <p className="mt-1 text-[11px] text-txt-dim">Donnée ENAF/ZAN indisponible pour cette commune.</p>}
        </section>

        {/* VÉLOCITÉ — M137-Z : TRANCHE p25-p75 (plus de médiane classée), homogénéité dite. */}
        <section className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
          <p className="label-caps text-[9.5px]">Vélocité administrative</p>
          {v ? (
            <div className="mt-1 text-[11px] text-txt">
              <p>Délai d'instruction (dépôt → autorisation) :{' '}
                <b className="tnum">{fmt(v['delai_p25_mois'])} à {fmt(v['delai_p75_mois'])} mois</b>{' '}
                <span className="text-txt-dim">(tranche p25–p75, {fmt(v['n_valide'])} dossiers)</span></p>
              {homogene && <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{vel.data?.['note_homogeneite'] as string}</p>}
            </div>
          ) : <p className="mt-1 text-[11px] text-txt-dim">Donnée délais indisponible pour cette commune.</p>}
        </section>
      </div>
    </div>
  )
}

export function Communes() {
  // Prefill (fiche « Voir le marché de X ») consommé au montage → ouvre directement la fiche commune,
  // puis reset. Sans prefill (menu) → entrée sur la table des 24 communes.
  const communePrefill = useApp((s) => s.communePrefill)
  const setCommunePrefill = useApp((s) => s.setCommunePrefill)
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const [sel, setSel] = useState<string | null>(() => useApp.getState().communePrefill)
  useEffect(() => {
    if (communePrefill) { setSel(communePrefill); setCommunePrefill(null) }
  }, [communePrefill, setCommunePrefill])
  // onglet au niveau de la table : « Les 24 » (comparateur) · « Évolution » (ex-Baromètre, île entière).
  const [vue, setVue] = useState<'table' | 'evolution'>('table')
  // §4 — la table des 24 communes s'ouvre en GRAND (section flottante plein écran, patron ex-Comparateur),
  // pas dans le panneau étroit. Elle est ouverte ssi on est sur l'onglet « table » ET pas sur une fiche ;
  // la fiche commune et l'onglet « Évolution » restent dans le panneau. Nettoyage au démontage de l'outil.
  useEffect(() => {
    setCommunesTableOpen(vue === 'table' && !sel)
    return () => setCommunesTableOpen(false)
  }, [vue, sel, setCommunesTableOpen])

  if (sel) return <CommuneFiche commune={sel} onBack={() => setSel(null)} />
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <div className="flex shrink-0 gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
        {([['table', 'Les 24 communes'], ['evolution', 'Évolution du marché']] as const).map(([k, lbl]) => (
          <button key={k} data-communes-vue={k} onClick={() => setVue(k)}
            className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${vue === k ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>{lbl}</button>
        ))}
      </div>
      {vue === 'table' ? (
        // La table est en grand (overlay CommunesTablePanel, monté au niveau App). Le panneau garde un
        // rappel + un bouton pour la rouvrir si on l'a fermée ; cliquer une commune dans la table ouvre
        // sa fiche ICI (via communePrefill).
        <div className="flex min-h-0 flex-1 flex-col items-start gap-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-3 text-[11px] leading-snug text-txt-mut">
          <p>Les <b className="text-txt">24 communes</b> s'affichent en grand, à droite — comparez-les d'un coup d'œil.
            Cliquez une commune pour ouvrir sa fiche <b>ici</b> (marché, rareté, ZAN, délais).</p>
          <button data-communes-rouvrir onClick={() => setCommunesTableOpen(true)}
            className="rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25">
            Rouvrir le tableau ↗
          </button>
        </div>
      ) : <M18 />}
    </div>
  )
}

/** §4 — SECTION FLOTTANTE plein écran de la table des 24 communes (patron ex-Comparateur : overlay
 *  `absolute inset-0 z-40 bg-black/50` + carte `floating`). Montée au niveau App tant que l'outil
 *  Communes est ouvert sur l'onglet table (drapeau `communesTableOpen`). Cliquer une commune pose son
 *  prefill → le panneau ouvre sa fiche, et la table se referme. La table n'est PLUS bridée par les
 *  320 px du panneau. */
export function CommunesTablePanel() {
  const module = useApp((s) => s.module)
  const communesTableOpen = useApp((s) => s.communesTableOpen)
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const setCommunePrefill = useApp((s) => s.setCommunePrefill)
  if (module !== 'communes' || !communesTableOpen) return null
  return (
    <div data-communes-table-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6"
      onClick={() => setCommunesTableOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1100px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">Les 24 communes</h2>
            <p className="text-[10.5px] text-txt-dim">Comparez-les, puis cliquez pour ouvrir une fiche.</p>
          </div>
          <button onClick={() => setCommunesTableOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        {/* flex column bornée : O6Comparateur gère son propre scroll interne (rangs) + légende permanente.
            Pas d'overflow ICI (sinon double scroll + légende poussée hors écran). */}
        <div className="flex min-h-0 flex-1 flex-col p-3">
          <O6Comparateur onSelect={(c) => { setCommunePrefill(c); setCommunesTableOpen(false) }} />
        </div>
      </div>
    </div>
  )
}
