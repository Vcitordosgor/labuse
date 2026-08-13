// M78 · 5 — LE COPILOTE EMBARQUÉ. Les copilotes adoptés vivent DANS les vues de travail, pas sur une
// page à part. Même API (copiloteV2Ask), AUCUN nouveau moteur : le routeur reçoit un `contexte`
// (idu | selection) que la surface remplit. La réponse RESTE dans la vue (panneau) ; « ouvrir dans le
// Copilote » continue en plein écran, conversation transférée (ouvrirEntretien).
import { useState } from 'react'
import { copiloteV2Ask, type CopiloteV2Reponse } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { ReponseInline } from './ReponseInline'

export function CopiloteEmbarque({ contexte, placeholder, exemples }: {
  contexte: Record<string, unknown>            // {idu} sur la fiche · {selection} sur une shortlist
  placeholder?: string
  exemples?: string[]                          // clics qui remplissent la barre (ne lancent pas)
}) {
  const [q, setQ] = useState('')
  const [rep, setRep] = useState<CopiloteV2Reponse | null>(null)
  const [busy, setBusy] = useState(false)
  const ouvrirEntretien = useApp((s) => s.ouvrirEntretien)

  const soumettre = async () => {
    const m = q.trim()
    if (!m || busy) return
    setBusy(true); setRep(null)
    try { setRep(await copiloteV2Ask(m, { contexte })) }
    catch (e) { setRep({ text: e instanceof Error ? e.message : String(e), intent: null }) }
    finally { setBusy(false) }
  }

  return (
    <div data-copilote-embarque className="rounded-xl border border-mint/25 bg-mint/[0.04] p-3">
      <div className="flex items-center gap-2">
        <span aria-hidden className="shrink-0 text-[13px] text-mint">✦</span>
        <input data-embarque-bar value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && q.trim()) void soumettre() }}
          placeholder={placeholder ?? 'Demander au Copilote…'}
          className="min-w-0 flex-1 bg-transparent text-[13px] text-txt outline-none placeholder:text-txt-faint" />
        <button data-embarque-envoyer onClick={() => void soumettre()} disabled={!q.trim() || busy}
          className="shrink-0 rounded-lg bg-mint px-3.5 py-1.5 text-[12px] font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {busy ? '…' : 'Demander'}
        </button>
      </div>
      {exemples && exemples.length > 0 && !rep && (
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 pl-6">
          {exemples.map((e) => (
            <button key={e} data-embarque-ex onClick={() => setQ(e)}
              className="text-[10.5px] italic text-txt-faint hover:text-txt-mut">« {e} »</button>
          ))}
        </div>
      )}
      {rep && <div className="mt-3"><ReponseInline v2={rep} /></div>}
      {rep && (
        <button data-embarque-plein onClick={() => ouvrirEntretien(q)}
          className="mt-2 pl-6 text-[11px] font-medium text-mint hover:underline">
          Ouvrir dans le Copilote →
        </button>
      )}
    </div>
  )
}
