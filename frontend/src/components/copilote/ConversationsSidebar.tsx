// COPILOTE-4 — la COLONNE DE GAUCHE de la conversation (maquette « Copilote en conversation »). Les
// conversations du compte, les plus récentes en haut : titre (la première question, abrégée côté
// serveur) + ancienneté. Un bouton « + Nouvelle conversation », la SUPPRESSION d'une conversation
// (geste explicite + confirmation), et le bandeau de rétention en pied. Mobile (< md) : la MÊME
// colonne devient un tiroir (menu), ouvert depuis l'en-tête du fil — pas de défilement horizontal.
import { useState } from 'react'
import type { CopiloteMission } from '../../lib/api'

// Âge court d'une conversation. La rétention est de 30 jours (COPILOTE-4) : on garde « il y a N j »
// jusqu'au bout, sans basculer sur une date absolue (le `ilYA` global le fait au-delà de 7 j).
function ageConv(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const j = Math.floor((Date.now() - t) / 86_400_000)
  if (j <= 0) return "aujourd'hui"
  return `il y a ${j} j`
}

export function ConversationsSidebar({ conversations, activeId, retentionJours, onNouvelle, onOuvrir,
  onSupprimer, onFermerMenu, mobile = false }: {
  conversations: CopiloteMission[]
  activeId: number | null
  retentionJours: number
  onNouvelle: () => void
  onOuvrir: (m: CopiloteMission) => void
  onSupprimer: (m: CopiloteMission) => void
  onFermerMenu?: () => void          // mobile : refermer le tiroir après un choix
  mobile?: boolean
}) {
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const choisir = (fn: () => void) => { fn(); onFermerMenu?.() }

  return (
    <nav aria-label="Vos conversations"
      className={`flex w-[266px] shrink-0 flex-col border-r border-cp-line bg-cp-card/30 ${mobile ? 'h-full w-[min(288px,86vw)]' : 'hidden md:flex'}`}>
      <div className="flex items-center gap-2 p-3">
        <button data-conv-nouvelle onClick={() => choisir(onNouvelle)}
          className="flex-1 rounded-lg border border-cp-ia-border bg-cp-ia/[0.06] px-4 py-2.5 font-display text-[12.5px] font-semibold text-cp-ia transition-colors duration-quick hover:border-cp-ia-border-on hover:bg-cp-ia/12">
          + Nouvelle conversation
        </button>
        {mobile && (
          <button onClick={onFermerMenu} aria-label="Fermer les conversations"
            className="shrink-0 rounded-lg border border-cp-line px-2.5 py-2 text-[14px] text-cp-muted hover:text-cp-txt">✕</button>
        )}
      </div>
      <p className="px-4 pb-1.5 pt-1 font-mono text-[10px] tracking-[.14em] text-cp-faint">VOS CONVERSATIONS</p>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 && (
          <p className="px-2 py-3 text-[12px] leading-snug text-cp-faint">Aucune conversation pour l'instant. Posez une question pour en démarrer une.</p>
        )}
        {conversations.map((c) => (
          confirmId === c.id ? (
            <div key={c.id} data-conv-confirm
              className="mb-1 flex items-center justify-between gap-2 rounded-lg border border-cp-danger-border bg-cp-danger-bg px-3 py-2.5">
              <span className="min-w-0 truncate text-[12px] text-cp-txt">Supprimer cette conversation ?</span>
              <span className="flex shrink-0 gap-2">
                <button data-conv-suppr-oui onClick={() => { setConfirmId(null); choisir(() => onSupprimer(c)) }}
                  className="font-display text-[12px] font-semibold text-cp-danger hover:underline">Oui</button>
                <button onClick={() => setConfirmId(null)}
                  className="text-[12px] text-cp-muted hover:text-cp-txt">Annuler</button>
              </span>
            </div>
          ) : (
            <div key={c.id} className="group relative">
              <button data-conv-item data-conv-active={c.id === activeId} onClick={() => choisir(() => onOuvrir(c))}
                className={`flex w-full flex-col gap-0.5 rounded-lg border-l-2 py-2.5 pl-3 pr-9 text-left transition-colors duration-quick ${
                  c.id === activeId ? 'border-cp-ia bg-cp-card2' : 'border-transparent hover:bg-cp-card2/60'}`}>
                <span className="truncate text-[13px] leading-snug text-cp-txt">{c.titre}</span>
                <span className="font-mono text-[10.5px] text-cp-faint">{ageConv(c.updated_at)}</span>
              </button>
              <button data-conv-suppr onClick={() => setConfirmId(c.id)}
                aria-label={`Supprimer la conversation « ${c.titre} »`}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md px-1.5 py-1 text-[13px] text-cp-faint opacity-0 transition-opacity duration-quick hover:text-cp-danger focus:opacity-100 focus-visible:outline focus-visible:outline-1 focus-visible:outline-cp-line2 group-hover:opacity-100">
                ✕
              </button>
            </div>
          )
        ))}
      </div>
      {/* Rétention + suppression : le pied le DIT (COPILOTE-4 : 30 jours, par compte, supprimables). */}
      <p data-conv-retention className="border-t border-cp-line px-4 py-3 text-[11px] leading-snug text-cp-faint">
        Conservées {retentionJours} jours, supprimables à tout moment. Réponses sourcées, datées — La Réunion uniquement.
      </p>
    </nav>
  )
}
