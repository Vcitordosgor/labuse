// M78 · 2a — PAGE D'ACCUEIL du Copilote v2. Recopiée de docs/DA-COPILOTE-ACCUEIL.html (fait foi) :
// promesse + tagline ([N] = comptage DYNAMIQUE du bandeau, jamais en dur), une barre unique, trois
// cartes Chercher/Vérifier/Veiller à deux exemples cliquables (le clic REMPLIT la barre, ne lance
// rien), pied de garanties. Retirés (mandat) : onglets « BIENTÔT », paragraphe défensif, pitch « il
// ne calcule rien ». Tokens cp-*/mint = palette de la maquette (--mint #4ADE80, --carte #101612).
import { useEffect, useRef, type ReactNode } from 'react'
import { fmtInt } from '../../lib/format'
import type { AccueilChiffres } from '../../lib/api'

type Carte = { past: string; titre: string; desc: (parc: string) => string; ex: [string, string] }

const CARTES: Carte[] = [
  { past: '⌕', titre: 'Chercher',
    desc: (parc) => `Décrivez le terrain ou le programme. Les moteurs passent les ${parc} parcelles au crible.`,
    ex: ['Terrain de 1 200 m² constructible à Saint-André',
         '15 logements, budget 800 k€, hors zone inondable'] },
  { past: '⚖', titre: 'Vérifier',
    desc: () => "Une parcelle qu'on vous propose. Le Copilote instruit à charge et à décharge, et rend un avis sourcé.",
    ex: ['On me propose 97411000AK0043 à 340 000 € — je me fais avoir ?',
         'Quelles contraintes sur cette parcelle avant de signer ?'] },
  { past: '🔔', titre: 'Veiller',
    desc: () => "Votre secteur sous surveillance. Alerte dès qu'une vente, un permis ou une procédure PLU bouge.",
    ex: ['Préviens-moi de tout nouveau permis à Saint-Paul',
         'Alerte-moi si la zone AU de Cambaie change au PLU'] },
]

export function AccueilCopilote({ value, onChange, onSubmit, onPick, chiffres, occupe, reponse }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  onPick: (ex: string) => void
  chiffres: AccueilChiffres | null
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => { ref.current?.focus() }, [])

  // [N] et [parc] DYNAMIQUES — masqués (pas inventés) si le bandeau ne les a pas encore.
  const nSources = chiffres?.sources != null ? String(chiffres.sources) : null
  const parc = chiffres?.parcelles != null ? fmtInt(chiffres.parcelles) : 'toutes les'

  return (
    <div data-accueil className="mx-auto max-w-[640px] px-2 pt-6">
      <div className="mb-2 text-center">
        <span className="font-mono text-[10px] tracking-[.16em] text-cp-muted">COPILOTE</span>
      </div>
      <h1 className="mb-2.5 text-center font-display text-[30px] font-semibold leading-[1.2] tracking-[-.5px] text-cp-txt">
        Dites ce que vous cherchez.<br />Le Copilote <span className="text-mint">instruit</span>.
      </h1>
      <p data-accueil-tagline className="mb-8 text-center text-[13px] text-cp-muted">
        Une parcelle instruite en une minute{nSources ? <> — <b className="text-cp-txt">{nSources}</b> sources</> : null}, chaque chiffre daté.
      </p>

      {/* barre unique */}
      <div data-accueil-barre className="mb-3.5 flex items-center gap-3 rounded-xl border border-cp-line2 bg-cp-card/60 py-2 pl-[18px] pr-2">
        <textarea ref={ref} data-brief rows={1} value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim()) onSubmit() } }}
          placeholder="15 logements à Saint-Denis, budget foncier 800 k€…"
          className="max-h-24 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-normal text-cp-txt outline-none placeholder:text-cp-faint" />
        <button data-accueil-envoyer onClick={() => value.trim() && onSubmit()} disabled={!value.trim() || occupe}
          className="shrink-0 rounded-lg bg-mint px-5 py-2.5 text-[13px] font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {occupe ? '…' : 'Envoyer'}
        </button>
      </div>
      <p className="mb-6 text-center text-[11px] text-cp-faint">
        Écrivez librement — le Copilote comprend s'il faut chercher, vérifier ou veiller.
      </p>

      {reponse && <div data-accueil-reponse className="mb-8">{reponse}</div>}

      {/* trois missions — exemples cliquables : REMPLISSENT la barre, ne lancent rien */}
      <div className="mb-8 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        {CARTES.map((c) => (
          <div key={c.titre} data-mission-carte className="rounded-[9px] bg-cp-card p-4">
            <div className="mb-2 flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-[#12291D] text-[14px] text-mint">{c.past}</div>
              <span className="font-display text-[13.5px] font-medium text-cp-txt">{c.titre}</span>
            </div>
            <p className="mb-3 text-[11px] leading-[1.5] text-cp-muted">{c.desc(parc)}</p>
            <div className="border-t border-cp-line pt-2.5">
              {c.ex.map((e) => (
                <p key={e} data-accueil-ex onClick={() => onPick(e)}
                  className="mb-1.5 cursor-pointer text-[10.5px] italic leading-[1.5] text-cp-faint last:mb-0 hover:text-cp-muted">
                  « {e} »
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* pied de garanties */}
      <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 border-t border-cp-line pt-4">
        <span className="text-[10px] text-cp-faint">✓ Chaque étape journalisée</span>
        <span className="text-[10px] text-cp-faint">◆ Sourcé, estimé ou absent — jamais autre chose</span>
        <span className="text-[10px] text-cp-faint">◉ La Réunion uniquement</span>
      </div>
    </div>
  )
}
