// JOHN-TAYLOR-2 — « John Taylor », une PAGE à part entière de l'admin, en conversation (même forme que
// le Copilote de COPILOTE-4) : à gauche la liste des conversations + « + Nouvelle conversation » ; au
// centre le fil ; à droite un volet repliable (résumé du matin, veille, carnet, coût du mois).
//
// Doctrine (inchangée) : John lit tout, cite sa source, agit sur ordre (liste fermée). Ici c'est la FORME
// qui change. Réponses lisibles (paragraphes courts, chiffres en gras, sources en étiquettes datées,
// boutons vers l'écran concerné). Une action = une ligne d'état. Plus jamais d'erreur brute : si un outil
// échoue, John le dit en une phrase (le détail part au journal serveur). L'enquête d'une carte s'affiche
// comme une QUESTION de John, pas comme un message de Vic. Rendu dans le scope `.cxp` (DA du Circuit).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import {
  deleteJohnConversation, getAdminJohn, getJohnConversation, getJohnConversations,
  postJohnCarnetRejeter, postJohnCarnetValider, postJohnChat, postJohnEnquete,
  type JohnConversation,
} from '../../../lib/api'
import { ageConversation } from '../../../lib/format'   // CHASSE-FIX-1 (A-3) — âge relatif unique
import { useApp, type JohnEnquete } from '../../../store/useApp'
import { CIRCUIT_CSS } from './style'

export type EnqueteDemande = JohnEnquete   // compat : certains appelants importent encore ce nom.

type Source = { label: string; heure?: string }
type Bouton = { ecran: string; label: string }
type ActionRes = { ok?: boolean; resume?: string } | null
type Tour = {
  role: 'user' | 'john'
  texte: string
  confirmation?: boolean
  mandat?: string | null
  sources?: Source[]
  boutons?: Bouton[]
  action?: ActionRes
  enquete?: boolean       // tour d'ouverture d'enquête (John pose la question)
  erreur?: boolean
}

const SUGG_ICONES = ['✔', '↺', '⌖']

const JT_CSS = `
.cxp .jt2{display:grid;grid-template-columns:262px minmax(0,1fr) 340px;height:100%;min-height:0;background:var(--bg)}
.cxp .jt2.sans-volet{grid-template-columns:262px minmax(0,1fr)}
.cxp .jt-mobbar{display:none}

/* ─ colonne gauche : conversations ─ */
.cxp .jt-gauche{display:flex;flex-direction:column;border-right:1px solid var(--line);min-height:0;background:var(--panel)}
.cxp .jt-neuve{margin:12px;padding:9px 12px;border:1px solid var(--mauve);border-radius:9px;background:rgba(192,132,252,.08);color:var(--mauve);font-weight:600;font-size:12.5px;cursor:pointer}
.cxp .jt-neuve:hover{background:rgba(192,132,252,.16)}
.cxp .jt-convs{flex:1;overflow:auto;padding:0 8px;display:flex;flex-direction:column;gap:2px;min-height:0}
.cxp .jt-conv{position:relative;display:flex;flex-direction:column;gap:1px;border-left:2px solid transparent;border-radius:8px;padding:8px 32px 8px 10px;cursor:pointer;text-align:left;width:100%;background:none;color:var(--text)}
.cxp .jt-conv:hover{background:var(--panel-2)}
.cxp .jt-conv.on{border-left-color:var(--mauve);background:var(--panel-2)}
.cxp .jt-conv .ti{font-size:12.5px;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cxp .jt-conv .ag{font-family:var(--mono);font-size:10px;color:var(--faint)}
.cxp .jt-conv .x{position:absolute;right:6px;top:50%;transform:translateY(-50%);border:0;background:none;color:var(--faint);font-size:13px;cursor:pointer;opacity:0;padding:3px 5px;border-radius:6px}
.cxp .jt-conv:hover .x{opacity:1}
.cxp .jt-conv .x:hover{color:var(--rouge)}
.cxp .jt-confsup{display:flex;align-items:center;justify-content:space-between;gap:6px;border:1px solid var(--rouge);border-radius:8px;padding:7px 9px;margin:0 0 2px;font-size:11.5px}
.cxp .jt-confsup button{border:0;background:none;cursor:pointer;font-size:11.5px}
.cxp .jt-confsup .oui{color:var(--rouge);font-weight:600}
.cxp .jt-confsup .non{color:var(--muted)}
.cxp .jt-ret{border-top:1px solid var(--line);padding:10px 12px;font-size:10.5px;line-height:1.45;color:var(--faint)}
.cxp .jt-vide{padding:14px 12px;font-size:12px;color:var(--faint)}

/* ─ colonne centre : le fil ─ */
.cxp .jt-centre{display:flex;flex-direction:column;min-height:0;min-width:0}
.cxp .jt-tete{display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:1px solid var(--line);padding:11px 16px}
.cxp .jt-tete .t{min-width:0}
.cxp .jt-tete .t b{font-size:13.5px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cxp .jt-tete .t .s{font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.cxp .jt-volet-btn{flex-shrink:0;border:1px solid var(--line-2);background:var(--panel);color:var(--muted);border-radius:7px;padding:5px 9px;font-size:11.5px;cursor:pointer}
.cxp .jt-volet-btn:hover{color:var(--text)}
.cxp .jt-fil2{flex:1;overflow:auto;padding:18px 16px;display:flex;flex-direction:column;gap:14px;min-height:0}

/* accueil */
.cxp .jt-acc{margin:auto;max-width:620px;width:100%;text-align:center;padding:16px}
.cxp .jt-acc .av{width:46px;height:46px;border-radius:50%;margin:0 auto 14px;display:grid;place-items:center;border:1px solid var(--mauve);background:rgba(192,132,252,.1);color:var(--mauve);font-weight:700;font-size:16px}
.cxp .jt-acc h2{font-size:21px;font-weight:600;letter-spacing:-.01em;margin:0 0 8px;line-height:1.25}
.cxp .jt-acc p{font-size:12.5px;color:var(--muted);margin:0 0 20px}
.cxp .jt-sugg{display:grid;grid-template-columns:1fr 1fr;gap:9px;text-align:left}
.cxp .jt-sugg button{display:flex;align-items:center;gap:9px;border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:11px 12px;font-size:12.5px;color:var(--text);cursor:pointer}
.cxp .jt-sugg button:hover{border-color:var(--mauve)}
.cxp .jt-sugg .ic{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;background:rgba(192,132,252,.14);color:var(--mauve);flex-shrink:0}

/* bulles */
.cxp .jt-tour{display:flex;flex-direction:column;gap:7px}
.cxp .jt-q{align-self:flex-end;max-width:84%;background:var(--mint-soft);border:1px solid var(--line-2);border-radius:13px 13px 3px 13px;padding:8px 12px;font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
.cxp .jt-r{align-self:flex-start;max-width:92%;background:var(--panel);border:1px solid var(--line);border-radius:13px 13px 13px 3px;padding:11px 14px;font-size:13px;line-height:1.55}
.cxp .jt-r.conf{border-color:var(--ambre)}
.cxp .jt-r.err{border-color:var(--rouge);background:rgba(248,113,113,.06)}
.cxp .jt-r.enq{border-style:dashed;border-color:var(--mauve)}
.cxp .jt-r p{margin:0 0 7px;word-break:break-word}.cxp .jt-r p:last-child{margin:0}
.cxp .jt-r b{font-weight:650;font-variant-numeric:tabular-nums}
.cxp .jt-etat{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;color:var(--mint);background:var(--mint-soft);border:1px solid var(--line-2);border-radius:7px;padding:6px 10px}
.cxp .jt-etat.ko{color:var(--rouge);background:rgba(248,113,113,.08)}
.cxp .jt-mandat2{margin-top:6px;padding:9px 11px;border:1px dashed var(--mauve);border-radius:8px;font-family:var(--mono);font-size:11.5px;white-space:pre-wrap;word-break:break-word}
.cxp .jt-src{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}
.cxp .jt-chip{font-family:var(--mono);font-size:10px;color:var(--muted);border:1px solid var(--line-2);background:var(--panel-2);border-radius:6px;padding:2px 7px}
.cxp .jt-liens{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
.cxp .jt-lien{border:1px solid var(--line-2);background:var(--panel-2);color:var(--text);border-radius:8px;padding:5px 11px;font-size:12px;cursor:pointer}
.cxp .jt-lien:hover{border-color:var(--mauve)}
.cxp .jt-conf2{display:flex;gap:8px;margin-top:9px}
.cxp .jt-pense{align-self:flex-start;font-size:12.5px;color:var(--faint)}

/* saisie */
.cxp .jt-saisie{border-top:1px solid var(--line);padding:12px 16px}
.cxp .jt-saisie .boite{display:flex;align-items:flex-end;gap:9px;border:1px solid var(--line-2);border-radius:11px;background:var(--bg);padding:7px 7px 7px 13px}
.cxp .jt-saisie .boite:focus-within{border-color:var(--mauve)}
.cxp .jt-saisie textarea{flex:1;resize:none;background:none;border:0;outline:none;color:var(--text);font:inherit;font-size:13.5px;line-height:1.4;max-height:120px;min-height:22px;padding:4px 0}
.cxp .jt-saisie .note{margin-top:7px;font-size:10.5px;color:var(--faint)}

/* ─ colonne droite : volet ─ */
.cxp .jt-droite{display:flex;flex-direction:column;gap:13px;border-left:1px solid var(--line);background:var(--panel);overflow:auto;padding:14px;min-height:0}
.cxp .jt-card2{border:1px solid var(--line);border-radius:10px;background:var(--bg);padding:12px 13px}
.cxp .jt-card2 h3{margin:0 0 8px;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.cxp .jt-cout2{display:flex;align-items:baseline;gap:5px}
.cxp .jt-cout2 .v{font-size:22px;font-weight:650;letter-spacing:-.02em}.cxp .jt-cout2 .v small{font-size:12px;color:var(--muted);font-weight:400}
.cxp .jt-pause2{display:inline-block;margin-top:7px;padding:2px 8px;border-radius:999px;font-size:10.5px;background:rgba(248,113,113,.15);color:var(--rouge);border:1px solid var(--rouge)}
.cxp .jt-ve2{padding:7px 0;border-bottom:1px solid var(--line)}.cxp .jt-ve2:last-child{border:0}
.cxp .jt-ve2 .tg{display:inline-block;font-size:10px;padding:1px 7px;border-radius:999px;border:1px solid var(--line-2);color:var(--muted);margin-right:6px}
.cxp .jt-ve2 .tg.integrer{color:var(--ambre);border-color:var(--ambre)}.cxp .jt-ve2 .tg.b{color:var(--mauve);border-color:var(--mauve)}.cxp .jt-ve2 .tg.conc{color:var(--mint);border-color:var(--mint)}
.cxp .jt-ve2 .s{color:var(--faint);font-size:11px;margin-top:2px}
.cxp .jt-cb2{padding:6px 0;border-bottom:1px solid var(--line);font-size:12px}.cxp .jt-cb2:last-child{border:0}
.cxp .jt-cb2 .ty{color:var(--faint);font-size:10px;text-transform:uppercase;letter-spacing:.04em}
.cxp .jt-prop2{border:1px solid var(--ambre);border-radius:8px;padding:8px 10px;margin-bottom:8px}
.cxp .jt-empty2{color:var(--faint);font-size:12px;padding:3px 0}

/* ─ drawers mobile ─ */
.cxp .jt-scrim{display:none}
@media (max-width:760px){
  .cxp .jt2,.cxp .jt2.sans-volet{grid-template-columns:1fr}
  .cxp .jt-mobbar{display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding:9px 12px}
  .cxp .jt-mobbar button{border:1px solid var(--line-2);background:var(--panel);color:var(--muted);border-radius:7px;padding:5px 9px;font-size:14px;line-height:1;cursor:pointer}
  .cxp .jt-mobbar .ti{flex:1;min-width:0;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .cxp .jt-tete{display:none}
  .cxp .jt-gauche,.cxp .jt-droite{display:none}
  .cxp .jt-scrim{display:block;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:40}
  .cxp .jt-drawer{position:fixed;top:0;bottom:0;z-index:41;width:min(300px,86vw);display:flex;flex-direction:column}
  .cxp .jt-drawer.g{left:0}.cxp .jt-drawer.d{right:0;width:min(330px,90vw)}
  .cxp .jt-gauche.ouvert,.cxp .jt-droite.ouvert{display:flex}
  .cxp .jt-sugg{grid-template-columns:1fr}
}
`

const tgClass = (lib: string) =>
  lib === 'à intégrer' ? 'integrer' : lib === 'source B à valider' ? 'b' : lib === 'concurrence' ? 'conc' : ''

// âge lisible d'une conversation (« aujourd'hui » / « hier » / « il y a 3 j »).
// CHASSE-FIX-1 (A-3) — via le formateur unique (fuseau Réunion), plus de calcul d'âge local.
const ageConv = ageConversation

// réponses lisibles : les **gras** du modèle ET les nombres (+ unité) passent en gras. L'anti-invention
// garantit déjà qu'un nombre affiché est sourcé — on ne fait que le mettre en valeur.
const NOMBRE = /(\d[\d .,  ]*(?:\s?(?:%|€|Go|Mo|ko|Ko|h|min|j|m²|m|°C))?)/g
function rendreRiche(texte: string): ReactNode {
  const paras = texte.split(/\n{2,}/)
  return paras.map((para, pi) => (
    <p key={pi}>{para.split('\n').flatMap((ligne, li) => {
      const noeuds: ReactNode[] = []
      if (li > 0) noeuds.push(<br key={`br${li}`} />)
      ligne.split(/(\*\*[^*]+\*\*)/g).forEach((seg, si) => {
        if (seg.startsWith('**') && seg.endsWith('**')) { noeuds.push(<b key={`g${li}-${si}`}>{seg.slice(2, -2)}</b>); return }
        seg.split(NOMBRE).forEach((bout, bi) => {
          if (!bout) return
          if (/^\s*\d/.test(bout) && /\d/.test(bout)) noeuds.push(<b key={`n${li}-${si}-${bi}`}>{bout}</b>)
          else noeuds.push(<span key={`t${li}-${si}-${bi}`}>{bout}</span>)
        })
      })
      return noeuds
    })}</p>
  ))
}

// ════════════════════════════════ Colonne gauche : les conversations ════════════════════════════════
function JohnSidebar({ conversations, activeId, retentionJours, onNouvelle, onOuvrir, onSupprimer, mobile, onFermer }: {
  conversations: JohnConversation[]; activeId: number | null; retentionJours: number
  onNouvelle: () => void; onOuvrir: (c: JohnConversation) => void; onSupprimer: (c: JohnConversation) => void
  mobile?: boolean; onFermer?: () => void
}) {
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const geste = (f: () => void) => { if (mobile) onFermer?.(); f() }
  return (
    <nav className={`jt-gauche${mobile ? ' jt-drawer g ouvert' : ''}`} aria-label="Vos conversations avec John">
      <button className="jt-neuve" data-jt-nouvelle onClick={() => geste(onNouvelle)}>+ Nouvelle conversation</button>
      <div className="jt-convs">
        {conversations.length === 0 && <div className="jt-vide">Aucune conversation pour l'instant.</div>}
        {conversations.map((c) => confirmId === c.id ? (
          <div className="jt-confsup" key={c.id} data-jt-confirm>
            <span>Supprimer ?</span>
            <span>
              <button className="oui" data-jt-suppr-oui onClick={() => { setConfirmId(null); geste(() => onSupprimer(c)) }}>Oui</button>
              {' · '}
              <button className="non" onClick={() => setConfirmId(null)}>Annuler</button>
            </span>
          </div>
        ) : (
          <button key={c.id} className={`jt-conv${c.id === activeId ? ' on' : ''}`} data-jt-conv data-jt-active={c.id === activeId}
            onClick={() => geste(() => onOuvrir(c))}>
            <span className="ti">{c.titre}</span>
            <span className="ag">{ageConv(c.maj_at)}</span>
            <span className="x" role="button" aria-label={`Supprimer « ${c.titre} »`}
              onClick={(e) => { e.stopPropagation(); setConfirmId(c.id) }}>✕</span>
          </button>
        ))}
      </div>
      <p className="jt-ret">Conservées {retentionJours} jours, supprimables à tout moment. John ne cite que ce que l'exploitation porte.</p>
    </nav>
  )
}

// ════════════════════════════════ Colonne droite : le volet ════════════════════════════════
function VoletInfos({ d, onValider, onRejeter, busy, mobile, onFermer }: {
  d: any; onValider: (id: number) => void; onRejeter: (id: number) => void; busy?: boolean
  mobile?: boolean; onFermer?: () => void
}) {
  const cout = d?.cout; const resume = d?.resume_matin
  const veille: any[] = d?.veille ?? []; const carnet: any[] = d?.carnet ?? []
  const propositions: any[] = d?.carnet_propositions ?? []
  return (
    <aside className={`jt-droite${mobile ? ' jt-drawer d ouvert' : ''}`} aria-label="Résumé, veille, carnet, coût">
      {mobile && <button className="jt-volet-btn" style={{ alignSelf: 'flex-end' }} onClick={onFermer}>Fermer ✕</button>}
      <div className="jt-card2">
        <h3>Coût du mois</h3>
        <div className="jt-cout2">
          <span className="v">{cout ? cout.depense_eur.toFixed(2) : '0.00'} €<small> / {cout ? cout.plafond_eur.toFixed(0) : '50'} €</small></span>
        </div>
        <div className="muted" style={{ fontSize: 11.5, marginTop: 4, color: 'var(--muted)' }}>{cout?.appels ?? 0} appel(s) ce mois</div>
        {cout?.en_pause && <span className="jt-pause2">En pause — plafond atteint</span>}
      </div>

      <div className="jt-card2">
        <h3>Résumé du matin</h3>
        {resume
          ? <><div style={{ fontWeight: 600, fontSize: 12.5 }}>{resume.sujet}</div>
              <div style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 6, color: 'var(--muted)' }}>{resume.corps}</div>
              <div style={{ fontSize: 10.5, marginTop: 6, color: 'var(--faint)' }}>écrit par {resume.par === 'john' ? 'John' : 'le résumé automatique (repli)'}</div></>
          : <div className="jt-empty2">Pas encore de résumé — il paraît chaque matin à 07h30.</div>}
      </div>

      <div className="jt-card2">
        <h3>Veille</h3>
        {veille.length === 0
          ? <div className="jt-empty2">Rien pour l'instant — la veille passe chaque nuit.</div>
          : veille.slice(0, 8).map((v, i) => (
            <div className="jt-ve2" key={i}>
              <span className={`tg ${tgClass(v.libelle)}`}>{v.libelle}</span>
              <span style={{ fontSize: 12.5 }}>{v.titre}</span>
              <div className="s">{v.source}{v.date_vue ? ` · ${v.date_vue}` : ''}</div>
            </div>
          ))}
      </div>

      <div className="jt-card2">
        <h3>Carnet de bord</h3>
        {propositions.map((p) => (
          <div className="jt-prop2" key={p.id}>
            <div style={{ fontWeight: 600, fontSize: 12 }}>{p.titre}</div>
            <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>{p.corps}</div>
            <div className="jt-conf2">
              <button className="btn mint" disabled={busy} onClick={() => onValider(p.id)}>Valider</button>
              <button className="btn" disabled={busy} onClick={() => onRejeter(p.id)}>Rejeter</button>
            </div>
          </div>
        ))}
        {carnet.length === 0
          ? <div className="jt-empty2">Carnet vide.</div>
          : carnet.slice(0, 12).map((l, i) => (
            <div className="jt-cb2" key={i}><span className="ty">{l.type}</span> <b>{l.titre}</b></div>
          ))}
      </div>
    </aside>
  )
}

// ════════════════════════════════ La page ════════════════════════════════
export function JohnTaylor({ enquete: enqueteProp }: { enquete?: JohnEnquete | null } = {}) {
  const qc = useQueryClient()
  const goAdminSection = useApp((s) => s.goAdminSection)
  const enqueteStore = useApp((s) => s.adminJohnEnquete)
  const clearJohnEnquete = useApp((s) => s.clearJohnEnquete)
  const enquete = enqueteProp ?? enqueteStore

  const d = useQuery({ queryKey: ['admin-john'], queryFn: getAdminJohn, refetchInterval: 60_000 })
  const convs = useQuery({ queryKey: ['john-conversations'], queryFn: getJohnConversations })

  const [fil, setFil] = useState<Tour[]>([])
  const [convId, setConvId] = useState<number | null>(null)
  const [saisie, setSaisie] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [voletOpen, setVoletOpen] = useState(true)       // volet déplié par défaut (desktop)
  const [voletMob, setVoletMob] = useState(false)        // volet en tiroir (mobile)
  const filRef = useRef<HTMLDivElement>(null)
  const saisieRef = useRef<HTMLTextAreaElement>(null)
  const enqueteFaite = useRef<string | null>(null)

  const chat = useMutation({
    mutationFn: (message: string) => postJohnChat(message, convId),
    onSuccess: (r: any) => {
      setConvId(r.conversation_id ?? convId)
      setFil((f) => [...f, {
        role: 'john', texte: r.texte || '…', confirmation: !!r.besoin_confirmation,
        sources: r.sources, boutons: r.boutons, action: r.action, erreur: !!r.erreur,
      }])
      qc.invalidateQueries({ queryKey: ['admin-john'] })          // le coût du mois bouge
      qc.invalidateQueries({ queryKey: ['john-conversations'] })  // le titre de la conversation apparaît
    },
  })

  const envoyer = (texte: string) => {
    const t = texte.trim()
    if (!t || chat.isPending) return
    setFil((f) => [...f, { role: 'user', texte: t }])
    setSaisie('')
    chat.mutate(t)
  }

  // une enquête (bouton « Demander à John » d'une carte) : John OUVRE la conversation (sa question),
  // puis rend cause + correction. Jamais un message de Vic.
  const faireEnquete = useMutation({
    mutationFn: (e: JohnEnquete) => postJohnEnquete(e),
    onSuccess: (r: any) => {
      const txt = r.ok
        ? `**Cause probable** — ${r.cause_probable}\n\n**Correction** — ${r.correction}`
        : (r.message || r.erreur || "Je n'ai pas pu conclure pour l'instant.")
      setFil((f) => [...f, { role: 'john', texte: txt, mandat: r.mandat_claude_code || null, erreur: !r.ok }])
      qc.invalidateQueries({ queryKey: ['admin-john'] })
    },
  })
  useEffect(() => {
    if (!enquete) return
    const cle = `${enquete.cle ?? ''}|${enquete.titre ?? ''}|${enquete.mode ?? ''}`
    if (enqueteFaite.current === cle) return
    enqueteFaite.current = cle
    setConvId(null)
    setFil([{ role: 'john', enquete: true,
      texte: `Tu m'as demandé de regarder « ${enquete.titre || enquete.cle} ». Je creuse les journaux…` }])
    faireEnquete.mutate(enquete)
    clearJohnEnquete()
  }, [enquete])   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { filRef.current?.scrollTo?.({ top: 1e9 }) }, [fil, chat.isPending, faireEnquete.isPending])
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') { setMenuOpen(false); setVoletMob(false) } }
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h)
  }, [])

  const valider = useMutation({ mutationFn: (id: number) => postJohnCarnetValider(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-john'] }) })
  const rejeter = useMutation({ mutationFn: (id: number) => postJohnCarnetRejeter(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-john'] }) })

  const nouvelle = () => { setConvId(null); setFil([]); enqueteFaite.current = null; saisieRef.current?.focus() }
  const ouvrir = async (c: JohnConversation) => {
    enqueteFaite.current = null
    try {
      const conv = await getJohnConversation(c.id)
      setConvId(conv.id)
      setFil(conv.messages.map((m): Tour => m.role === 'user'
        ? { role: 'user', texte: m.texte }
        : { role: 'john', texte: m.texte, sources: m.meta?.lectures, boutons: m.meta?.boutons,
            action: m.meta?.action, erreur: !!m.meta?.erreur }))
    } catch { /* une conversation introuvable : on reste sur l'accueil */ nouvelle() }
  }
  const supprimer = async (c: JohnConversation) => {
    await deleteJohnConversation(c.id)
    if (c.id === convId) nouvelle()
    qc.invalidateQueries({ queryKey: ['john-conversations'] })
  }

  const conversations = convs.data?.conversations ?? []
  const retention = convs.data?.retention_jours ?? 90
  const accueil = d.data?.accueil
  const enFil = fil.length > 0
  const titreConv = useMemo(() => fil.find((t) => t.role === 'user')?.texte
    ?? (fil[0]?.enquete ? 'Enquête de John' : 'John Taylor'), [fil])
  const occupe = chat.isPending || faireEnquete.isPending

  if (d.isLoading) return <div className="cxp" style={{ padding: 20 }}><style>{CIRCUIT_CSS}</style><div className="muted">John Taylor — chargement…</div></div>

  const sidebar = (mobile = false) => (
    <JohnSidebar conversations={conversations} activeId={convId} retentionJours={retention}
      onNouvelle={nouvelle} onOuvrir={ouvrir} onSupprimer={supprimer} mobile={mobile}
      onFermer={() => setMenuOpen(false)} />
  )
  const volet = (mobile = false) => (
    <VoletInfos d={d.data} onValider={(id) => valider.mutate(id)} onRejeter={(id) => rejeter.mutate(id)}
      busy={valider.isPending || rejeter.isPending} mobile={mobile} onFermer={() => setVoletMob(false)} />
  )

  return (
    <div className="cxp" style={{ height: '100%', minHeight: 0 }}>
      <style>{CIRCUIT_CSS}</style>
      <style>{JT_CSS}</style>
      <div className={`jt2${voletOpen ? '' : ' sans-volet'}`}>
        {/* ─ barre mobile ─ */}
        <div className="jt-mobbar">
          <button aria-label="Conversations" onClick={() => setMenuOpen(true)}>☰</button>
          <span className="ti">{enFil ? titreConv : 'John Taylor'}</span>
          <button aria-label="Infos" onClick={() => setVoletMob(true)}>ⓘ</button>
        </div>

        {/* ─ gauche (desktop) ─ */}
        {sidebar(false)}

        {/* ─ centre ─ */}
        <main className="jt-centre">
          <div className="jt-tete">
            <div className="t">
              <b>{enFil ? titreConv : 'John Taylor — ton second de bord'}</b>
              <span className="s">{enFil ? 'John cite ce que l’exploitation porte' : 'Exploitation de LABUSE · admin'}</span>
            </div>
            <button className="jt-volet-btn" onClick={() => setVoletOpen((v) => !v)}>
              {voletOpen ? 'Masquer le volet' : 'Afficher le volet'}
            </button>
          </div>

          <div className="jt-fil2" ref={filRef} role="log" aria-live="polite">
            {!enFil && (
              <div className="jt-acc" data-jt-accueil>
                <div className="av">J</div>
                <h2>{accueil?.phrase ?? 'Bonjour Vic.'}</h2>
                <p>Demande-moi l'état de l'app — jobs, incidents, sources, runs, sauvegardes, Radar.
                  Je lis tout, je cite d'où ça vient, et j'agis sur ton ordre.</p>
                <div className="jt-sugg">
                  {(accueil?.suggestions ?? ['Tout est à jour ?', 'Qu’est-ce qui a changé depuis hier ?', 'Où en est q_v21 ?']).map((s: string, i: number) => (
                    <button key={s} data-jt-suggestion disabled={occupe} onClick={() => envoyer(s)}>
                      <span className="ic">{SUGG_ICONES[i] ?? '›'}</span>{s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {fil.map((t, i) => t.role === 'user' ? (
              <div className="jt-tour" key={i}><div className="jt-q">{t.texte}</div></div>
            ) : (
              <div className="jt-tour" key={i}>
                <div className={`jt-r${t.confirmation ? ' conf' : ''}${t.erreur ? ' err' : ''}${t.enquete ? ' enq' : ''}`} data-jt-reponse>
                  {t.action?.resume && (
                    <div className={`jt-etat${t.action.ok === false ? ' ko' : ''}`} data-jt-etat>
                      <span>{t.action.ok === false ? '✕' : '⚙'}</span>{t.action.resume}
                    </div>
                  )}
                  {rendreRiche(t.texte)}
                  {t.mandat && <div className="jt-mandat2" data-jt-mandat>{t.mandat}</div>}
                  {!!t.sources?.length && (
                    <div className="jt-src" data-jt-sources>
                      {t.sources.map((s, k) => <span className="jt-chip" data-jt-chip key={k}>{s.label}{s.heure ? ` · ${s.heure}` : ''}</span>)}
                    </div>
                  )}
                  {!!t.boutons?.length && (
                    <div className="jt-liens">
                      {t.boutons.map((b, k) => (
                        <button className="jt-lien" data-jt-lien key={k} onClick={() => goAdminSection(b.ecran)}>{b.label} →</button>
                      ))}
                    </div>
                  )}
                  {t.confirmation && (
                    <div className="jt-conf2">
                      <button className="btn mint" disabled={occupe} onClick={() => envoyer('oui')}>Oui, confirme</button>
                      <button className="btn" disabled={occupe} onClick={() => envoyer('non')}>Non, laisse</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {occupe && <div className="jt-pense">John réfléchit…</div>}
          </div>

          <div className="jt-saisie">
            <div className="boite">
              <textarea ref={saisieRef} rows={1} value={saisie} data-jt-saisie
                placeholder={enFil ? 'Continue la conversation…' : 'Écris comme à un collègue…'}
                aria-label="Ton message à John"
                onChange={(e) => setSaisie(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyer(saisie) } }} />
              <button className="btn mint" disabled={occupe || !saisie.trim()} onClick={() => envoyer(saisie)}>Envoyer</button>
            </div>
            <div className="note">{enFil
              ? 'John ne dit que ce que les données portent. Un chiffre vient toujours d’une lecture.'
              : 'Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne'}</div>
          </div>
        </main>

        {/* ─ droite (desktop, repliable) ─ */}
        {voletOpen && volet(false)}

        {/* ─ tiroirs mobile ─ */}
        {menuOpen && <><div className="jt-scrim" onClick={() => setMenuOpen(false)} />{sidebar(true)}</>}
        {voletMob && <><div className="jt-scrim" onClick={() => setVoletMob(false)} />{volet(true)}</>}
      </div>
    </div>
  )
}
