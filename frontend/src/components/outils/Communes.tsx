import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { modVelocite, motRarete } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { O6Comparateur } from './blocB'
import { MarcheCommune } from './moteurs'

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

function CommuneFiche({ commune, onBack }: { commune: string; onBack: () => void }) {
  const setCommune = useApp((s) => s.setCommune)
  const setModule = useApp((s) => s.setModule)
  const rar = useQuery({ queryKey: ['communes-rarete'], queryFn: motRarete })
  const vel = useQuery({ queryKey: ['communes-velocite'], queryFn: () => modVelocite() })
  const r = (rar.data?.communes ?? []).find((c) => c['commune'] === commune) as Record<string, any> | undefined
  const v = (vel.data?.communes ?? []).find((c) => c['commune'] === commune) as Record<string, any> | undefined
  const homogene = vel.data?.['communes_homogenes'] as boolean | undefined

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="flex items-center justify-between gap-2">
        <button data-communes-retour onClick={onBack} className="text-[11px] text-mint hover:underline">‹ Toutes les communes</button>
        <button data-communes-parcelles onClick={() => { setCommune(commune); setModule(null) }}
          className="rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25">
          Voir ses parcelles →
        </button>
      </div>
      <h3 className="text-[15px] font-semibold text-txt-hi">{commune}</h3>

      {/* RARETÉ & ZAN — M137-Z : le STOCK porte « foncier » ; « reste ZAN » = un droit à artificialiser.
          audit-zan : l'enveloppe ZAN de l'ex-Simulateur ZAN vit désormais ICI (budget en %). */}
      <section className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
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

      {/* MARCHÉ — les 9 lignes sourcées, réutilisées via communeProp (une seule source de vérité). */}
      <section className="flex min-h-0 flex-col">
        <p className="label-caps text-[9.5px]">Marché</p>
        <div className="flex min-h-0 flex-col gap-1.5">
          <MarcheCommune communeProp={commune} />
        </div>
      </section>
    </div>
  )
}

export function Communes() {
  // Prefill (fiche « Voir le marché de X ») consommé au montage → ouvre directement la fiche commune,
  // puis reset. Sans prefill (menu) → entrée sur la table des 24 communes.
  const communePrefill = useApp((s) => s.communePrefill)
  const setCommunePrefill = useApp((s) => s.setCommunePrefill)
  const [sel, setSel] = useState<string | null>(() => useApp.getState().communePrefill)
  useEffect(() => {
    if (communePrefill) { setSel(communePrefill); setCommunePrefill(null) }
  }, [communePrefill, setCommunePrefill])
  if (sel) return <CommuneFiche commune={sel} onBack={() => setSel(null)} />
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <O6Comparateur onSelect={setSel} />
    </div>
  )
}
