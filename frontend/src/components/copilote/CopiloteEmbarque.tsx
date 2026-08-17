// M78 · 5 — LE COPILOTE EMBARQUÉ. Les copilotes adoptés vivent DANS les vues de travail, pas sur une
// page à part. Même API (copiloteV2Ask), AUCUN nouveau moteur : le routeur reçoit un `contexte`
// (idu | selection) que la surface remplit. La réponse RESTE dans la vue ; « ouvrir dans le Copilote »
// continue en plein écran, conversation transférée (ouvrirEntretien).
//
// Deux déclinaisons (arbitrage Vic) : `compact` + `ton='violet'` sur la FICHE — une LIGNE discrète, en
// MAUVE (le seul endroit de la fiche où l'IA parle) ; plein + mint dans le Copilote (shortlist).
import { useState } from 'react'
import { copiloteV2Ask, type CopiloteV2Reponse } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { ReponseInline } from './ReponseInline'

export function CopiloteEmbarque({ contexte, placeholder, exemples, ton = 'mint', compact = false }: {
  contexte: Record<string, unknown>            // {idu} sur la fiche · {selection} sur une shortlist
  placeholder?: string
  exemples?: string[]                          // clics qui remplissent la barre (ne lancent pas)
  ton?: 'mint' | 'violet'
  compact?: boolean                            // fiche : une ligne discrète, pas un encart
}) {
  const [q, setQ] = useState('')
  const [derniereQ, setDerniereQ] = useState('')   // M107 — la question envoyée (Corriger la ramène)
  const [rep, setRep] = useState<CopiloteV2Reponse | null>(null)
  const [reponse, setReponse] = useState('')       // M107 — réponse à une clarification, SUR PLACE
  const [convId, setConvId] = useState<number | null>(null)  // M107 — le fil embarqué est chaîné
  const [busy, setBusy] = useState(false)
  const ouvrirEntretien = useApp((s) => s.ouvrirEntretien)

  const envoyer = async (m: string) => {
    if (!m.trim() || busy) return
    setBusy(true); setRep(null); setDerniereQ(m.trim())
    // M107 P2.3 — la barre se vide après envoi (elle ne garde plus la question à l'écran)
    setQ(''); setReponse('')
    try {
      const r = await copiloteV2Ask(m.trim(), { contexte, conversation_id: convId })
      if (r.conversation_id != null) setConvId(r.conversation_id)
      setRep(r)
    } catch (e) { setRep({ text: e instanceof Error ? e.message : String(e), intent: null }) }
    finally { setBusy(false) }
  }
  const soumettre = () => void envoyer(q)

  const suite = rep && (
    <>
      <div className="mt-3">
        {/* M107 — le récap systématique a AUSSI son Corriger ici (la barre embarquée le reçoit) */}
        <ReponseInline v2={rep} ton={ton} onCorriger={() => setQ(derniereQ)} />
      </div>
      {rep.clarification && (
        /* M107 — la question posée a SON champ de réponse, au même endroit, autofocus. */
        <div data-embarque-reponse className="mt-2 flex items-center gap-2">
          <input autoFocus value={reponse} onChange={(e) => setReponse(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && reponse.trim()) void envoyer(reponse) }}
            placeholder="Votre réponse…"
            className={`min-w-0 flex-1 rounded-lg border bg-transparent px-3 py-1.5 text-[12.5px] text-txt outline-none placeholder:text-txt-faint ${
              ton === 'violet' ? 'border-violet/30 focus:border-violet' : 'border-mint/30 focus:border-mint'}`} />
          <button data-embarque-repondre disabled={!reponse.trim()} onClick={() => void envoyer(reponse)}
            className={`shrink-0 text-[11.5px] font-medium hover:underline disabled:opacity-30 ${
              ton === 'violet' ? 'text-violet' : 'text-mint'}`}>
            Répondre
          </button>
        </div>
      )}
      <button data-embarque-plein onClick={() => ouvrirEntretien(derniereQ)}
        className={`mt-2 text-[11px] font-medium hover:underline ${ton === 'violet' ? 'text-violet' : 'text-mint'}`}>
        Ouvrir dans le Copilote →
      </button>
    </>
  )

  // ── FICHE : une LIGNE discrète, mauve (pas un encart qui casse la lecture) ──
  if (compact) {
    return (
      <div data-copilote-embarque>
        <div className="flex items-center gap-2 border-b border-violet/20 pb-1.5">
          <span aria-hidden className="shrink-0 text-[12px] text-violet">✦</span>
          <input data-embarque-bar value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && q.trim()) void soumettre() }}
            placeholder={placeholder ?? 'Demander au Copilote…'}
            className="min-w-0 flex-1 bg-transparent text-[12.5px] text-txt outline-none placeholder:text-txt-faint" />
          <button data-embarque-envoyer onClick={() => void soumettre()} disabled={!q.trim() || busy}
            className="shrink-0 text-[11px] font-medium text-violet transition-opacity duration-quick hover:underline disabled:opacity-30">
            {busy ? '…' : 'demander →'}
          </button>
        </div>
        {suite}
      </div>
    )
  }

  // ── SHORTLIST / plein : panneau mint (idiome du Copilote) ──
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
      {suite}
    </div>
  )
}
