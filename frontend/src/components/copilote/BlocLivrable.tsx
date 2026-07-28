// M26-B — bloc livrable : le journal (event log) est disponible et consultable dès
// maintenant ; le PDF de la note d'opportunité arrive au mandat M26-C (« bientôt »,
// arbitrage GO — on n'affiche pas un bouton qui ment).
import { CLIENT } from '../../lib/strings'
import type { RecapAssemblage } from '../../lib/copilote'

const S = CLIENT.copilote.livrable

export function BlocLivrable({ recap, nMoteurs, ouvrirJournal }: {
  recap: RecapAssemblage
  nMoteurs: number
  ouvrirJournal: () => void
}) {
  return (
    <div data-livrable
      className="mt-4 flex flex-wrap items-center gap-4 rounded-2xl border border-cp-violet/30 bg-gradient-to-br from-cp-violet/10 to-cp-violet/[0.03] px-5 py-4">
      <div className="min-w-[200px] flex-1">
        <h4 className="font-display text-sm font-semibold text-cp-txt">{S.titre}</h4>
        <p className="mt-1 text-[11.5px] text-cp-muted">
          {S.desc(recap.n_restituees, recap.n_ecartees, nMoteurs)}
        </p>
      </div>
      <button data-journal-ouvrir onClick={ouvrirJournal}
        className="rounded-xl border border-cp-line2 px-4 py-3 font-display text-[12.5px] font-semibold text-cp-txt transition-colors duration-quick hover:border-cp-violet">
        {S.journal}
      </button>
      <button data-pdf-bientot disabled
        className="cursor-not-allowed rounded-xl bg-cp-violet/40 px-5 py-3 font-display text-[12.5px] font-bold text-[#150E22]/70">
        {S.pdf}
        <span className="ml-2 rounded-md bg-[#150E22]/25 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[.1em]">
          {S.pdfBientot}
        </span>
      </button>
    </div>
  )
}
