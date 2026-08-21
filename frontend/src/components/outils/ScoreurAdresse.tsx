import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { scoreurAdresse, type ScoreurResult } from '../../lib/api'
import { fmtEur, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { AddressAutocomplete, type AddressSelection } from '../AddressAutocomplete'
import { TierBadge } from './TierBadge'

// R5 (O2) — SCOREUR D'ADRESSE INVERSÉ : « je visite ce terrain, qu'en dit LABUSE ? »
// L'outil « seconde opinion avant d'offrir » : saisissez une adresse (autocomplétion BAN,
// M12-D) + prix demandé (SAISI À LA MAIN — jamais scrapé) → verdict de la parcelle déjà
// scorée + confrontation du prix à la charge foncière supportable (Score É V2). Hors base →
// réponse honnête. M12-D4 : cet outil vit désormais dans le tiroir Outils (module panel).
// M128-6-§1.3 — le prix saisi donne un CONSTAT chiffré NU : prix probable du foncier + écart,
// et marge à ce prix (charge de la méthode DOCUMENTS − prix). AUCUN verdict (« bonne affaire »,
// « au-dessus du marché », « rentable »…) : on affiche les nombres, le lecteur conclut.

// Module Outils : rendu comme un `() => JSX.Element` dans ModulePanel (en-tête/fermeture
// fournis par le panneau). D1 (AddressAutocomplete) garantit une adresse normalisée BAN.
export function ScoreurAdresse() {
  const select = useApp((s) => s.select)
  const setModule = useApp((s) => s.setModule)
  const [adresse, setAdresse] = useState('')       // adresse normalisée BAN (jamais libre)
  const [idu, setIdu] = useState<string | null>(null)   // M82 (CAS E) : parcelle déjà résolue par l'autocomplétion
  const [prix, setPrix] = useState<number | null>(null)
  const m = useMutation({ mutationFn: () => scoreurAdresse(adresse.trim(), prix, idu) })
  const d: ScoreurResult | undefined = m.data
  const run = () => { if (adresse.trim().length >= 3) m.mutate() }
  const onPick = (sel: AddressSelection) => { setAdresse(sel.label); setIdu(sel.idu ?? null); m.reset() }

  return (
    <div data-scoreur-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* M13-F4 (QA-54) : les deux champs + le bouton GROUPÉS dans l'ordre de lecture, dans
          une seule carte encadrée — l'action est évidente au premier coup d'œil. Texte d'aide
          COURT au-dessus du champ (plus de pavé). Autocomplétion BAN (B1) branchée. */}
      <div data-scoreur-form className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[10.5px] leading-snug text-txt-mut">
          Seconde opinion avant d’offrir : une adresse, un prix éventuel, le verdict de la parcelle.
        </p>

        <AddressAutocomplete
          data-scoreur-adresse
          autoFocus
          placeholder="Adresse (ex. 12 rue du Général de Gaulle, Saint-Paul)"
          onSelect={onPick}
          onClear={() => { setAdresse(''); setIdu(null); m.reset() }}
        />

        <input data-scoreur-prix type="number" min={0} value={prix ?? ''} placeholder="Prix demandé € (optionnel)"
          onChange={(e) => setPrix(e.target.value === '' ? null : Number(e.target.value))}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          title="Le prix affiché/demandé, saisi à la main — jamais scrapé. Confronté à la charge foncière supportable (Estimé)."
          className="w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />

        <button onClick={run} disabled={m.isPending || adresse.trim().length < 3}
          className="w-full rounded-lg bg-mint px-3 py-2 text-xs font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {m.isPending ? 'Analyse…' : 'Scorer cette adresse'}
        </button>
      </div>

      {m.isError && <p className="text-[11px] text-st-ecartee">Erreur — vérifiez l'adresse et réessayez.</p>}

      {d && !m.isPending && (
        <div data-scoreur-resultat className="rounded-lg border border-line-2 bg-surface-1 p-3">
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
              {d.prix && (
                <div data-scoreur-prix-constat className="mt-2 border-t border-line pt-2">
                  {/* M128-6-§1.3 : CONSTAT chiffré NU — aucun badge, aucun verdict. */}
                  {d.prix.prix_probable_foncier_eur != null && (
                    <p className="text-[11px] leading-snug text-txt-mut">
                      Prix probable du foncier : <span className="tnum text-txt">{fmtEur(d.prix.prix_probable_foncier_eur)}</span>
                      {d.prix.ecart_vs_prix_probable_pct != null && (
                        <> · écart du prix saisi : <span className="tnum text-txt">{d.prix.ecart_vs_prix_probable_pct > 0 ? '+' : ''}{d.prix.ecart_vs_prix_probable_pct} %</span></>
                      )}
                    </p>
                  )}
                  {d.prix.marge_a_ce_prix_eur != null ? (
                    <p className="mt-1.5 text-[11px] text-txt">
                      Marge à ce prix (méthode documents) : <b className="tnum">{fmtEur(d.prix.marge_a_ce_prix_eur)}</b>
                    </p>
                  ) : (
                    d.prix.message && <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">{d.prix.message}</p>
                  )}
                  {d.prix.methode && <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{d.prix.methode}</p>}
                  <p className="mt-1 text-[9.5px] text-txt-dim">{d.prix.avertissement}</p>
                </div>
              )}
              {d.idu && (
                <button data-scoreur-fiche onClick={() => { select(d.idu!); setModule(null) }}
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
