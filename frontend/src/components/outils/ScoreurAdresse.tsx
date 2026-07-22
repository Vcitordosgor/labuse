import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { scoreurAdresse, type ScoreurResult } from '../../lib/api'
import { fmtEur, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { TierBadge } from './TierBadge'

// R5 (O2) — SCOREUR D'ADRESSE INVERSÉ : « je visite ce terrain, qu'en dit LABUSE ? »
// L'outil de démo « seconde opinion avant d'offrir » : collez une adresse (+ prix demandé,
// SAISI À LA MAIN — jamais scrapé) → verdict de la parcelle déjà scorée + confrontation du
// prix à la charge foncière supportable (Score É V2). Hors base → réponse honnête.
const PRIX_META: Record<string, { label: string; cls: string }> = {
  opportunite: { label: 'Opportunité', cls: 'text-mint border-mint/50 bg-mint/10' },
  dans_le_marche: { label: 'Dans le marché', cls: 'text-st-creuser border-st-creuser/50 bg-st-creuser/10' },
  cher: { label: 'Cher pour un opérateur', cls: 'text-st-ecartee border-st-ecartee/50 bg-st-ecartee/10' },
  non_estimable: { label: 'Non estimable', cls: 'text-txt-dim border-line-2 bg-surface-3' },
}

export function ScoreurAdresse({ onClose }: { onClose: () => void }) {
  const select = useApp((s) => s.select)
  const [adresse, setAdresse] = useState('')
  const [prix, setPrix] = useState<number | null>(null)
  const m = useMutation({ mutationFn: () => scoreurAdresse(adresse.trim(), prix) })
  const d: ScoreurResult | undefined = m.data
  const run = () => { if (adresse.trim().length >= 3) m.mutate() }

  return (
    <div data-scoreur-panel className="floating pointer-events-auto absolute left-1/2 top-16 z-50 w-[420px] max-w-[94vw] -translate-x-1/2 p-4 shadow-elev-3">
      <div className="flex items-center justify-between">
        <span className="label-caps">Scorer une adresse — seconde opinion</span>
        <button data-scoreur-close onClick={onClose} aria-label="Fermer"
          className="flex h-7 w-7 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-surface-3 hover:text-txt">✕</button>
      </div>

      <div className="mt-2 flex gap-1.5">
        <input data-scoreur-adresse autoFocus value={adresse} onChange={(e) => setAdresse(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="Collez une adresse (ex. 12 rue du Général de Gaulle, Saint-Paul)"
          className="min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
      </div>
      <div className="mt-1.5 flex items-center gap-1.5">
        <input data-scoreur-prix type="number" min={0} value={prix ?? ''} placeholder="Prix demandé € (optionnel)"
          onChange={(e) => setPrix(e.target.value === '' ? null : Number(e.target.value))}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          title="Le prix affiché/demandé, saisi à la main — jamais scrapé. Confronté à la charge foncière supportable (Estimé)."
          className="min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
        <button onClick={run} disabled={m.isPending || adresse.trim().length < 3}
          className="shrink-0 rounded-lg bg-mint px-3 py-1.5 text-xs font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {m.isPending ? '…' : 'Scorer'}
        </button>
      </div>

      {m.isError && <p className="mt-2 text-[11px] text-st-ecartee">Erreur — vérifiez l'adresse et réessayez.</p>}

      {d && !m.isPending && (
        <div data-scoreur-resultat className="mt-3 rounded-lg border border-line-2 bg-surface-1 p-3">
          {!d.ok ? (
            /* hors base : réponse honnête, jamais un verdict inventé */
            <p className="text-[11.5px] leading-relaxed text-txt-mut">
              <span className="text-txt">{d.adresse}</span> — {d.message}
            </p>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[11.5px] text-txt">{d.adresse}</span>
                <TierBadge tier={d.verdict?.tier} etage0={null} statut={null} />
              </div>
              <p className="mt-0.5 text-[10.5px] text-txt-mut">
                {d.commune} · {fmtM2(d.surface_m2)} · <span className="font-mono">{d.idu}</span>
              </p>
              {d.score_e?.estimable && (
                <p className="mt-1.5 text-[11px] text-txt" title={d.score_e.libelle_court}>
                  {d.score_e.libelle_court}
                </p>
              )}
              {d.prix && (
                <div className="mt-2 border-t border-line pt-2">
                  <span data-scoreur-prix-verdict className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRIX_META[d.prix.verdict]?.cls ?? PRIX_META.non_estimable.cls}`}>
                    {PRIX_META[d.prix.verdict]?.label ?? d.prix.verdict}
                  </span>
                  <p className="mt-1 text-[11px] leading-snug text-txt-mut">{d.prix.message}</p>
                  {d.prix.marge_a_ce_prix_eur != null && (
                    <p className="mt-0.5 text-[11px] text-txt">Marge résiduelle à ce prix : <b className="tnum">{fmtEur(d.prix.marge_a_ce_prix_eur)}</b></p>
                  )}
                  <p className="mt-1 text-[9.5px] text-txt-dim">{d.prix.avertissement}</p>
                </div>
              )}
              {d.idu && (
                <button data-scoreur-fiche onClick={() => { select(d.idu!); onClose() }}
                  className="mt-2 min-h-7 text-[11px] font-medium text-mint hover:underline">
                  Ouvrir la fiche complète →
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
