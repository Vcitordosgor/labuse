// JOHN-TAYLOR-1 — l'onglet « John Taylor » de la page Données (admin seul).
// Maquette validée : chat à gauche ; à droite, le résumé du matin, la veille, le carnet de bord et le
// coût du mois. Rendu DANS le scope `.cxp` (réutilise les tokens/boutons du Circuit) + un petit habillage
// propre à l'onglet. John lit tout, agit sur ordre de Vic (liste fermée), ne fabrique rien.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import {
  getAdminJohn, postJohnCarnetRejeter, postJohnCarnetValider, postJohnChat, postJohnEnquete,
} from '../../../lib/api'

export type EnqueteDemande = { cle?: string; titre?: string; mode?: 'casse' | 'code' }
type Tour = { role: 'user' | 'john'; texte: string; confirmation?: boolean; mandat?: string | null }

const JT_CSS = `
.cxp .jt{display:grid;grid-template-columns:1fr 360px;gap:18px;align-items:start}
.cxp .jt-chat{border:1px solid var(--line);border-radius:10px;background:var(--panel);display:flex;flex-direction:column;min-height:440px;max-height:72vh}
.cxp .jt-fil{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.cxp .jt-b{max-width:88%;padding:9px 12px;border-radius:10px;font-size:13.5px;white-space:pre-wrap;line-height:1.45}
.cxp .jt-b.user{align-self:flex-end;background:var(--mint-soft);border:1px solid var(--line-2)}
.cxp .jt-b.john{align-self:flex-start;background:var(--panel-2);border:1px solid var(--line)}
.cxp .jt-b.john.conf{border-color:var(--ambre)}
.cxp .jt-mandat{margin-top:8px;padding:8px 10px;border:1px dashed var(--mauve);border-radius:8px;font-family:var(--mono);font-size:12px;color:var(--text);white-space:pre-wrap}
.cxp .jt-conf{display:flex;gap:8px;margin-top:8px}
.cxp .jt-bar{display:flex;gap:8px;padding:10px;border-top:1px solid var(--line)}
.cxp .jt-bar input{flex:1;background:var(--bg);border:1px solid var(--line-2);color:var(--text);padding:8px 11px;border-radius:7px;font:inherit}
.cxp .jt-side{display:flex;flex-direction:column;gap:14px}
.cxp .jt-card{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:12px 14px}
.cxp .jt-card h3{margin:0 0 8px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.cxp .jt-cout{display:flex;align-items:baseline;gap:6px}
.cxp .jt-cout .v{font-size:22px;font-weight:650;letter-spacing:-.02em} .cxp .jt-cout .v small{font-size:13px;color:var(--muted)}
.cxp .jt-pause{display:inline-block;margin-top:6px;padding:2px 8px;border-radius:999px;font-size:11px;background:rgba(248,113,113,.15);color:var(--rouge);border:1px solid var(--rouge)}
.cxp .jt-ve{padding:8px 0;border-bottom:1px solid var(--line)} .cxp .jt-ve:last-child{border:0}
.cxp .jt-ve .tg{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:999px;border:1px solid var(--line-2);color:var(--muted);margin-right:6px}
.cxp .jt-ve .tg.integrer{color:var(--ambre);border-color:var(--ambre)} .cxp .jt-ve .tg.b{color:var(--mauve);border-color:var(--mauve)} .cxp .jt-ve .tg.conc{color:var(--mint);border-color:var(--mint)}
.cxp .jt-ve .s{color:var(--faint);font-size:11.5px;margin-top:2px}
.cxp .jt-cb{padding:7px 0;border-bottom:1px solid var(--line);font-size:12.5px} .cxp .jt-cb:last-child{border:0}
.cxp .jt-cb .ty{color:var(--faint);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em}
.cxp .jt-prop{border:1px solid var(--ambre);border-radius:8px;padding:8px 10px;margin-top:8px}
.cxp .jt-empty{color:var(--faint);font-size:12.5px;padding:4px 0}
`

const tgClass = (lib: string) =>
  lib === 'à intégrer' ? 'integrer' : lib === 'source B à valider' ? 'b' : lib === 'concurrence' ? 'conc' : ''

export function JohnTaylor({ enquete }: { enquete?: EnqueteDemande | null }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-john'], queryFn: getAdminJohn, refetchInterval: 60_000 })
  const [fil, setFil] = useState<Tour[]>([])
  const [convId, setConvId] = useState<number | null>(null)
  const [saisie, setSaisie] = useState('')
  const filRef = useRef<HTMLDivElement>(null)
  const enqueteFaite = useRef(false)

  const d = q.data

  const chat = useMutation({
    mutationFn: (message: string) => postJohnChat(message, convId),
    onSuccess: (r: any) => {
      setConvId(r.conversation_id ?? convId)
      setFil((f) => [...f, { role: 'john', texte: r.texte || '…', confirmation: !!r.besoin_confirmation }])
      qc.invalidateQueries({ queryKey: ['admin-john'] })   // le coût du mois bouge
    },
  })

  const envoyer = (texte: string) => {
    const t = texte.trim()
    if (!t || chat.isPending) return
    setFil((f) => [...f, { role: 'user', texte: t }])
    setSaisie('')
    chat.mutate(t)
  }

  // une demande d'enquête (bouton « Demander à John » du Tableau de bord) : John répond dans le fil.
  const faireEnquete = useMutation({
    mutationFn: (e: EnqueteDemande) => postJohnEnquete(e),
    onSuccess: (r: any) => {
      const txt = r.ok
        ? `Cause probable : ${r.cause_probable}\n\nCorrection : ${r.correction}`
        : (r.message || r.erreur || 'Je n’ai pas pu conclure.')
      setFil((f) => [...f, { role: 'john', texte: txt, mandat: r.mandat_claude_code || null }])
      qc.invalidateQueries({ queryKey: ['admin-john'] })
    },
  })
  useEffect(() => {
    if (enquete && !enqueteFaite.current) {
      enqueteFaite.current = true
      setFil((f) => [...f, { role: 'user', texte: `Enquête sur « ${enquete.titre || enquete.cle} »` }])
      faireEnquete.mutate(enquete)
    }
  }, [enquete])   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { filRef.current?.scrollTo?.({ top: 1e9 }) }, [fil, chat.isPending])

  const valider = useMutation({ mutationFn: (id: number) => postJohnCarnetValider(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-john'] }) })
  const rejeter = useMutation({ mutationFn: (id: number) => postJohnCarnetRejeter(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-john'] }) })

  if (q.isLoading) return <div className="muted">John Taylor — chargement…</div>
  const cout = d?.cout
  const resume = d?.resume_matin
  const veille: any[] = d?.veille ?? []
  const carnet: any[] = d?.carnet ?? []
  const propositions: any[] = d?.carnet_propositions ?? []

  return (
    <div className="jt">
      <style>{JT_CSS}</style>

      {/* ─────────── Chat (gauche) ─────────── */}
      <div className="jt-chat">
        <div className="jt-fil" ref={filRef}>
          {fil.length === 0 && (
            <div className="jt-b john">Salut Vic. Je suis John, ton second de bord. Demande-moi
              l'état de l'app — jobs, incidents, sources, runs, sauvegardes, Radar… Je lis tout et je
              cite d'où vient chaque chose. Pour agir, donne-moi un ordre : j'exécute la liste convenue.</div>
          )}
          {fil.map((t, i) => (
            <div key={i} className={`jt-b ${t.role}${t.confirmation ? ' conf' : ''}`}>
              {t.texte}
              {t.mandat && <div className="jt-mandat">{t.mandat}</div>}
              {t.confirmation && (
                <div className="jt-conf">
                  <button className="btn mint" disabled={chat.isPending} onClick={() => envoyer('oui')}>Oui, confirme</button>
                  <button className="btn" disabled={chat.isPending} onClick={() => envoyer('non')}>Non, laisse</button>
                </div>
              )}
            </div>
          ))}
          {chat.isPending && <div className="jt-b john muted">John réfléchit…</div>}
        </div>
        <div className="jt-bar">
          <input value={saisie} placeholder="Pose ta question ou donne un ordre…"
            onChange={(e) => setSaisie(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') envoyer(saisie) }} />
          <button className="btn mint" disabled={chat.isPending || !saisie.trim()} onClick={() => envoyer(saisie)}>Envoyer</button>
        </div>
      </div>

      {/* ─────────── Panneau (droite) ─────────── */}
      <div className="jt-side">
        <div className="jt-card">
          <h3>Coût du mois</h3>
          <div className="jt-cout">
            <span className="v">{cout ? cout.depense_eur.toFixed(2) : '0.00'} €<small> / {cout ? cout.plafond_eur.toFixed(0) : '50'} €</small></span>
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{cout?.appels ?? 0} appel(s) ce mois</div>
          {cout?.en_pause && <span className="jt-pause">En pause — plafond atteint</span>}
        </div>

        <div className="jt-card">
          <h3>Résumé du matin</h3>
          {resume
            ? <><div style={{ fontWeight: 600, fontSize: 13 }}>{resume.sujet}</div>
                <div className="muted" style={{ fontSize: 12.5, whiteSpace: 'pre-wrap', marginTop: 6 }}>{resume.corps}</div>
                <div className="faint" style={{ fontSize: 11, marginTop: 6 }}>écrit par {resume.par === 'john' ? 'John' : 'le résumé automatique (repli)'}</div></>
            : <div className="jt-empty">Pas encore de résumé — il paraît chaque matin à 07h30.</div>}
        </div>

        <div className="jt-card">
          <h3>Veille</h3>
          {veille.length === 0
            ? <div className="jt-empty">Rien pour l'instant — la veille passe chaque nuit.</div>
            : veille.slice(0, 8).map((v, i) => (
              <div className="jt-ve" key={i}>
                <span className={`tg ${tgClass(v.libelle)}`}>{v.libelle}</span>
                <span style={{ fontSize: 13 }}>{v.titre}</span>
                <div className="s">{v.source}{v.date_vue ? ` · ${v.date_vue}` : ''}</div>
              </div>
            ))}
        </div>

        <div className="jt-card">
          <h3>Carnet de bord</h3>
          {propositions.map((p) => (
            <div className="jt-prop" key={p.id}>
              <div style={{ fontWeight: 600, fontSize: 12.5 }}>{p.titre}</div>
              <div className="muted" style={{ fontSize: 12 }}>{p.corps}</div>
              <div className="jt-conf">
                <button className="btn mint" disabled={valider.isPending} onClick={() => valider.mutate(p.id)}>Valider</button>
                <button className="btn" disabled={rejeter.isPending} onClick={() => rejeter.mutate(p.id)}>Rejeter</button>
              </div>
            </div>
          ))}
          {carnet.length === 0
            ? <div className="jt-empty">Carnet vide.</div>
            : carnet.slice(0, 12).map((l, i) => (
              <div className="jt-cb" key={i}>
                <span className="ty">{l.type}</span> <b>{l.titre}</b>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
