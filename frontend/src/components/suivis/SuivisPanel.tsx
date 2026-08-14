// M85-B — panneau « Suivis » : les parcelles suivies du compte + la date du DERNIER changement
// détecté. Une parcelle qui n'a jamais bougé le DIT (information, pas un vide). Secteurs et Suivis
// sont deux échelles du même geste (ce que je surveille). DA vert/neutre, jamais mauve.
import { useQuery } from '@tanstack/react-query'
import { getSuivis } from '../../lib/api'
import { useApp } from '../../store/useApp'

export function SuivisPanel() {
  const { toggleSuivis, select, setView } = useApp()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const plafond = q.data?.plafond ?? 50
  return (
    <div data-suivis-panel className="absolute left-4 top-4 z-30 flex max-h-[80vh] w-[340px] flex-col overflow-hidden rounded-xl border border-line bg-surface-1 shadow-xl">
      <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2.5">
        <p className="label-caps">Suivis <span className="text-txt-dim">· {suivis.length}/{plafond}</span></p>
        <button onClick={() => toggleSuivis()} aria-label="Fermer" className="text-txt-dim hover:text-txt">✕</button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {suivis.length === 0 && (
          <p className="p-3 text-[11.5px] leading-snug text-txt-dim">
            Aucune parcelle suivie. Ouvrez une fiche et cliquez sur la <b className="text-txt">cloche « Suivre »</b> —
            vous serez prévenu ici (et au digest du matin) dès qu'elle change : vente, permis, procédure, zonage, classement.
          </p>
        )}
        {suivis.map((s) => (
          <button key={s.idu} data-suivi onClick={() => { setView('cartes'); select(s.idu); toggleSuivis() }}
            className="mb-1 flex w-full flex-col items-start rounded-lg border border-line-2 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/40">
            <span className="text-xs font-medium text-txt">
              {s.commune ?? 'Parcelle'} <span className="font-mono text-[10px] text-txt-dim">{s.idu.slice(8)}</span>
            </span>
            <span className="mt-0.5 text-[10.5px] text-txt-dim">
              {s.dernier_changement
                ? <>Dernier changement : <b className="text-txt-mut">{new Date(s.dernier_changement).toLocaleDateString('fr-FR')}</b></>
                : 'Aucun changement détecté depuis le suivi.'}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
