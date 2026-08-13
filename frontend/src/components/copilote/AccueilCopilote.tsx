// M78 · 2a — PAGE D'ACCUEIL du Copilote v2. Recopiée de docs/DA-COPILOTE-ACCUEIL.html (fait foi) :
// promesse + tagline ([N] = comptage DYNAMIQUE du bandeau, jamais en dur), une barre unique, trois
// cartes Chercher/Vérifier/Veiller à deux exemples cliquables (le clic REMPLIT la barre, ne lance
// rien), pied de garanties. Retirés (mandat) : onglets « BIENTÔT », paragraphe défensif, pitch « il
// ne calcule rien ». Tokens cp-*/mint = palette de la maquette (--mint #4ADE80, --carte #101612).
import { useEffect, useMemo, useRef, type ReactNode } from 'react'
import { fmtInt } from '../../lib/format'
import type { AccueilChiffres, CopiloteMission, CopiloteVeille } from '../../lib/api'

type Carte = { past: string; titre: string; desc: (parc: string) => string }

const CARTES: Carte[] = [
  { past: '⌕', titre: 'Chercher',
    desc: (parc) => `Décrivez le terrain ou le programme. Les moteurs passent les ${parc} parcelles au crible.` },
  { past: '⚖', titre: 'Vérifier',
    desc: () => "Une parcelle qu'on vous propose. Le Copilote instruit à charge et à décharge, et rend un avis sourcé." },
  { past: '🔔', titre: 'Veiller',
    desc: () => "Votre secteur sous surveillance. Alerte dès qu'une vente, un permis ou une procédure PLU bouge." },
]

// M78-bis §1 — POOL d'exemples VARIÉS couvrant les 7 intentions (le client comprend en un regard qu'il
// peut TOUT écrire). Beaucoup viennent du test de véracité (vérifiés → démontrables sans risque). 6 en
// rotation aléatoire à chaque visite. Un clic remplit la barre, ne lance rien.
const POOL: string[] = [
  'Combien de parcelles à Saint-Paul ?',
  'Quel est le PLU en vigueur à Saint-Denis ?',
  'Quelles parcelles appartiennent à la SIDR ?',
  'Combien de temps met un permis à Saint-Benoît ?',
  'Je cherche un terrain de 1 000 m² à La Possession, budget 300 k€',
  'Un projet de lotissement étudiant à Sainte-Marie : 6 bâtiments de 4 appartements',
  'On me propose 97411000AK0043 à 340 000 € — bon prix ?',
  'Préviens-moi de tout nouveau permis à Saint-Paul',
  'Crée un projet : résidence 12 logements à Bras-Panon',
  'Je veux écrire au propriétaire de cette parcelle',
  'Quelles communes manquent de logements sociaux ?',
  'Le marché de Saint-Pierre est-il actif en ce moment ?',
  "Combien de parcelles d'au moins 5 000 m² à Saint-Paul ?",
  'Quel est le taux de logement social à Saint-Benoît ?',
  'Cette parcelle 97414000CV0907 est-elle divisible ?',
  'Assemble des parcelles contiguës',
  // M78-ter — questions servies par le web (public hors base)
  'Qui est le maire de Saint-Denis ?',
  'Qui gère les dossiers de financement des bailleurs sociaux à la Région ?',
  'Y a-t-il un appel à projets logement en cours à La Réunion ?',
]

/** 6 exemples tirés au hasard (à chaque montage = à chaque visite). */
function sixAuHasard(): string[] {
  return [...POOL].sort(() => Math.random() - 0.5).slice(0, 6)
}

export function AccueilCopilote({ value, onChange, onSubmit, onPick, chiffres, occupe, reponse,
  missions, onReprendre, veilles, onSupprimerVeille }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  onPick: (ex: string) => void
  chiffres: AccueilChiffres | null
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
  missions?: CopiloteMission[]           // §2b — historique
  onReprendre?: (m: CopiloteMission) => void
  veilles?: CopiloteVeille[]             // §4 — écran minimal des veilles
  onSupprimerVeille?: (id: number) => void
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => { ref.current?.focus() }, [])
  const exemples6 = useMemo(sixAuHasard, [])   // §1 — 6 exemples variés, tirés à cette visite

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
      <p className="mb-4 text-center text-[11px] text-cp-faint">
        Écrivez librement — le Copilote comprend s'il faut chercher, vérifier ou veiller.
      </p>

      {/* §1 — le client voit d'un regard qu'il peut TOUT écrire : 6 exemples variés (7 intentions),
           tirés au hasard. Un clic REMPLIT la barre, ne lance rien. */}
      {!reponse && (
        <div data-accueil-exemples className="mb-8 flex flex-wrap justify-center gap-2">
          {exemples6.map((e) => (
            <button key={e} data-accueil-ex onClick={() => onPick(e)}
              className="rounded-lg border border-cp-line bg-cp-card/40 px-3 py-1.5 text-left text-[11px] italic text-cp-muted transition-colors duration-quick hover:border-mint/30 hover:text-cp-txt">
              « {e} »
            </button>
          ))}
        </div>
      )}

      {reponse && <div data-accueil-reponse className="mb-8">{reponse}</div>}

      {/* §2b — reprendre là où on s'est arrêté : les missions passées du compte */}
      {(missions?.length ?? 0) > 0 && (
        <div data-accueil-historique className="mb-8">
          <p className="mb-2 font-mono text-[10px] tracking-[.16em] text-cp-muted">REPRENDRE</p>
          <div className="flex flex-col gap-1.5">
            {missions!.slice(0, 6).map((m) => (
              <button key={m.id} data-mission-reprendre onClick={() => onReprendre?.(m)}
                className="flex items-center gap-3 rounded-lg border border-cp-line bg-cp-card/50 px-3.5 py-2 text-left transition-colors duration-quick hover:border-mint/30">
                <span className="min-w-0 flex-1 truncate text-[12px] text-cp-txt">{m.titre}</span>
                {m.run_id && <span className="shrink-0 rounded border border-mint/30 px-1.5 py-px text-[9px] uppercase tracking-wide text-mint">recherche</span>}
                <span className="shrink-0 font-mono text-[10px] text-cp-faint">{m.n_messages} msg</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* §4 — écran minimal des veilles : listées, supprimables. La notification stockée est signalée
           (le CANAL qui la pousse au client — cloche/digest — est au BACKLOG, dit au rapport). */}
      {(veilles?.length ?? 0) > 0 && (
        <div data-accueil-veilles className="mb-8">
          <p className="mb-1 font-mono text-[10px] tracking-[.16em] text-cp-muted">VEILLES</p>
          {/* §4 (arbitrage Vic) : ne PAS taire que l'alerte n'est pas encore proactive — le client ne
               doit pas rater un permis en croyant être prévenu. */}
          <p data-veilles-note className="mb-2 text-[10.5px] leading-snug text-cp-faint">
            Vos veilles sont enregistrées — les nouvelles alertes apparaîtront ici à chaque mise à jour
            des données. L'envoi par e-mail n'est pas encore actif.
          </p>
          <div className="flex flex-col gap-1.5">
            {veilles!.map((v) => (
              <div key={v.id} data-veille className="flex items-center gap-3 rounded-lg border border-cp-line bg-cp-card/50 px-3.5 py-2">
                <span className="text-[13px] text-mint">🔔</span>
                <span className="min-w-0 flex-1 truncate text-[12px] text-cp-txt">{v.type} · {v.commune}</span>
                {v.non_vues > 0 && (
                  <span data-veille-notif className="shrink-0 rounded-full bg-mint/15 px-2 py-px text-[10px] font-semibold text-mint">
                    {v.non_vues} nouvelle{v.non_vues > 1 ? 's' : ''}
                  </span>
                )}
                <button data-veille-supprimer aria-label="Supprimer la veille" onClick={() => onSupprimerVeille?.(v.id)}
                  className="shrink-0 text-cp-faint opacity-60 hover:text-cp-txt hover:opacity-100">✕</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* trois missions — les archétypes (les exemples VARIÉS vivent en pool sous la barre, §1) */}
      <div className="mb-8 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        {CARTES.map((c) => (
          <div key={c.titre} data-mission-carte className="rounded-[9px] bg-cp-card p-4">
            <div className="mb-2 flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-[#12291D] text-[14px] text-mint">{c.past}</div>
              <span className="font-display text-[13.5px] font-medium text-cp-txt">{c.titre}</span>
            </div>
            <p className="text-[11px] leading-[1.5] text-cp-muted">{c.desc(parc)}</p>
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
