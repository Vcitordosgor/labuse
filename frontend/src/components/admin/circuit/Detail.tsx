// CIRCUIT-P (lot 4) — LES PAGES DE DÉTAIL. Le détail est une PAGE, pas un tiroir : elle remplace le
// dessin, avec « ← Retour au circuit » et Échap. Réservoir : versions, gestes (agent, vanne, servir
// quand même, revenir), filtre à l'entrée, rapport de l'agent, ce qu'il alimente, les chiffres qu'il
// nourrit. Robinet : fuites/eau ancienne en tête, ce qu'il affiche (badges moteur/hors-moteur,
// tampon ; la règle quand CIRCUIT-4 sera passé), alimenté par, dernier contrôle. Pompe : ce qui
// attend, gestes (calculer, basculer, revenir), note de version, moteurs, horloges.
// Les chips « alimente » / « alimenté par » naviguent d'une page à l'autre (4.2).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  getAdminCircuitNoteVersion, getAdminCircuitPompe, getAdminCircuitReservoir, getAdminCircuitRobinet,
  postAdminCircuitFiltreRevenir, postAdminCircuitFiltreServir, postAdminCircuitRevenir,
  postAdminFluxBascule, postAdminFluxLancerRun, postAdminSourceVeilleInjecter,
} from '../../../lib/api'

import type { CircuitData, Couleur } from './types'

type Ouvrir = (type: 'reservoir' | 'robinet' | 'pompe', id: number | string) => void
type Props = { type: 'reservoir' | 'robinet' | 'pompe'; id: number | string; data: CircuitData; onClose: () => void; onOpen: Ouvrir }

const dateFr = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
const cl = (c: Couleur) => (c === 'mint' ? 'mint' : c)

export function Detail({ type, id, data, onClose, onOpen }: Props) {
  const qc = useQueryClient()
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  const rafraichir = () => {
    qc.invalidateQueries({ queryKey: ['admin-circuit'] })
    qc.invalidateQueries({ queryKey: ['circuit-detail'] })
  }

  const back = <button className="back" onClick={onClose}>← Retour au circuit</button>

  if (type === 'reservoir') return <DetailReservoir id={Number(id)} data={data} back={back} onOpen={onOpen} rafraichir={rafraichir} />
  if (type === 'robinet') return <DetailRobinet id={String(id)} data={data} back={back} onOpen={onOpen} rafraichir={rafraichir} />
  return <DetailPompe back={back} rafraichir={rafraichir} />
}

// ── RÉSERVOIR ────────────────────────────────────────────────────────────────────────────────
function DetailReservoir({ id, data, back, onOpen, rafraichir }:
  { id: number; data: CircuitData; back: JSX.Element; onOpen: Ouvrir; rafraichir: () => void }) {
  const q = useQuery({ queryKey: ['circuit-detail', 'reservoir', id], queryFn: () => getAdminCircuitReservoir(id) })
  const injecter = useMutation({ mutationFn: () => postAdminSourceVeilleInjecter(id), onSuccess: rafraichir })
  const servir = useMutation({ mutationFn: (src: string) => postAdminCircuitFiltreServir(src, 'geste page Circuit'), onSuccess: rafraichir })
  const filtreRevenir = useMutation({ mutationFn: (src: string) => postAdminCircuitFiltreRevenir(src), onSuccess: rafraichir })

  if (q.isLoading || !q.data) return <div className="detail on">{back}<div className="muted">Chargement…</div></div>
  const { reservoir: r, alimente, chiffres, rapport_agent } = q.data
  const [c, l] = r.etat as [Couleur, string]
  const f = r.filtre || {}
  const cadence = r.cadence_jours ? `cadence ${r.cadence_jours} j${r.cadence_statut ? ` (${r.cadence_statut})` : ''}` : 'aucune cadence déclarée'
  const robEtat = (rid: string): Couleur => (data.robinets.find((x) => x.id === rid)?.etat?.[0] as Couleur) || 'mint'

  return (
    <div className="detail on">
      {back}
      <div className="dh">
        <div><h1>{r.nom}</h1><div className="m">{r.producteur} · {r.mode} · {cadence}</div></div>
        <div className="state"><span className={`pill ${cl(c)}`}><i />{l}</span></div>
      </div>
      <div className="dg">
        <div>
          <div className="card"><h3>Versions</h3>
            <div className="kv">
              <div>Dans le réservoir</div><div>{r.millesime || '—'}{r.ingere_le ? `, ingéré le ${dateFr(r.ingere_le)}` : ''}</div>
              <div>Chez le producteur</div><div>{r.veille?.statut === 'nouvelle_version'
                ? <span style={{ color: 'var(--ambre)' }}>nouvelle version vue</span>
                : r.veille?.statut === 'injoignable' ? <span style={{ color: 'var(--ambre)' }}>injoignable à la dernière sonde</span>
                  : r.veille?.statut ? 'la même' : <span style={{ color: 'var(--ambre)' }}>inconnue, personne n'est allé voir</span>}</div>
              <div>Dernier contrôle</div><div>{r.dernier_controle ? dateFr(r.dernier_controle) : <span style={{ color: 'var(--ambre)' }}>jamais</span>}</div>
            </div>
            <div className="actions">
              <button className="btn mauve" disabled title="Agents prêts — bouton câblé au premier crédit API.">Envoyer un agent</button>
              {r.vanne?.type === 'injecter' && <button className="btn ambre" disabled={injecter.isPending}
                onClick={() => injecter.mutate()}>Ouvrir la vanne, injecter</button>}
              {f.verdict === 'quarantaine' && <>
                <button className="btn ambre" disabled={servir.isPending}
                  onClick={() => { if (confirm(`Servir « ${f.source} » malgré la quarantaine ?`)) servir.mutate(f.source) }}>Servir quand même</button>
                {f.live && <button className="btn" disabled={filtreRevenir.isPending}
                  onClick={() => { if (confirm(`Revenir à la version précédente de « ${f.source} » ?`)) filtreRevenir.mutate(f.source) }}>Revenir à la précédente</button>}
              </>}
            </div>
          </div>
          <div className="card"><h3>Filtre à l'entrée</h3>
            {!f.source || f.verdict === 'non_filtre' ? <div className="muted">Pas encore de filtre pour ce réservoir.</div> : <>
              <div style={{ marginBottom: 8, fontWeight: 600, color: f.verdict === 'quarantaine' ? 'var(--rouge)' : f.verdict === 'avertissements' ? 'var(--ambre)' : 'var(--mint)' }}>
                {f.verdict === 'quarantaine' ? 'Version en quarantaine : ingérée, mesurée, pas servie'
                  : f.verdict === 'avertissements' ? 'Passé, avec des contrôles avertissants'
                    : f.verdict === 'jamais_joue' ? 'Filtre jamais joué' : `Passé, ${(f.controles || []).length} contrôles`}
                {f.joue_le ? ` · joué le ${dateFr(f.joue_le)}` : ''}
              </div>
              <div className="ctrl">
                {(f.controles || []).map((x: any) => (
                  <div key={x.controle} style={{ display: 'contents' }}>
                    <div className="n">{x.controle}</div><div className="v">{x.valeur}</div>
                    <div className={`verdict ${x.verdict === 'ok' ? 'ok' : x.severite === 'bloquant' ? 'bloq' : 'ko'}`}>
                      {x.verdict === 'ok' ? 'OK' : x.severite === 'bloquant' ? 'BLOQUANT' : 'KO'}</div>
                  </div>
                ))}
              </div>
            </>}
          </div>
          <div className="card rep"><h3>Rapport de l'agent</h3>
            {rapport_agent
              ? <div className="muted">Dernier agent le {dateFr(rapport_agent.ts)} : {rapport_agent.resultat}</div>
              : <div className="muted">Pas encore envoyé.</div>}
          </div>
        </div>
        <div>
          <div className="card"><h3>Ce qu'il alimente · {alimente.n_chiffres} chiffres dans {alimente.n_robinets} robinets</h3>
            {alimente.robinets.length ? alimente.robinets.map((rb: any) => (
              <span key={rb.id} className={`chip ${['mint', 'gris'].includes(robEtat(rb.id)) ? '' : robEtat(rb.id)}`}
                onClick={() => onOpen('robinet', rb.id)}>{rb.nom}</span>
            )) : <span className="muted">aucun chiffre du registre ne lit ce réservoir</span>}
          </div>
          <div className="card"><h3>Les chiffres qu'il nourrit</h3>
            <ul className="list">{chiffres.length ? chiffres.map((ch: any) => (
              <li key={ch.id}><span>{ch.libelle}</span><span className="muted">{ch.robinets} robinet{ch.robinets > 1 ? 's' : ''}</span></li>
            )) : <li className="muted">aucun</li>}</ul>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── ROBINET ──────────────────────────────────────────────────────────────────────────────────
function DetailRobinet({ id, data, back, onOpen }:
  { id: string; data: CircuitData; back: JSX.Element; onOpen: Ouvrir; rafraichir: () => void }) {
  const q = useQuery({ queryKey: ['circuit-detail', 'robinet', id], queryFn: () => getAdminCircuitRobinet(id) })
  if (q.isLoading || !q.data) return <div className="detail on">{back}<div className="muted">Chargement…</div></div>
  const { robinet: r, chiffres, amont, fuites, eau_ancienne, dernier_controle } = q.data
  const [c, l] = r.etat as [Couleur, string]
  const idReservoir = (slug: string) => data.reservoirs.find((x) => x.slug === slug)?.id
  const resEtat = (slug: string): Couleur => (data.reservoirs.find((x) => x.slug === slug)?.etat?.[0] as Couleur) || 'mint'

  return (
    <div className="detail on">
      {back}
      <div className="dh">
        <div><h1>{r.nom}</h1><div className="m">{r.categorie_nom}{r.parent ? ` · dans ${r.parent}` : ''} · <code>{r.route}</code></div></div>
        <div className="state"><span className={`pill ${cl(c)}`}><i />{l}</span></div>
      </div>
      <div className="dg">
        <div>
          {fuites.map((x: any, i: number) => (
            <div key={i} className="card" style={{ borderColor: 'var(--rouge)' }}>
              <h3 style={{ color: 'var(--rouge)' }}>Fuite · {x.chiffre_id}{x.cle ? ` · ${x.cle}` : ''}</h3>
              <div className="two">
                <div className="ok"><div className="v">{String(x.valeur_a)}</div><div className="l">{x.robinet_a}</div></div>
                <div className="ko"><div className="v">{String(x.valeur_b)}</div><div className="l">{x.robinet_b}</div></div>
              </div>
              <div className="muted">Cause : {x.cause}</div>
            </div>
          ))}
          {eau_ancienne.map((x: any, i: number) => (
            <div key={i} className="card" style={{ borderColor: 'var(--ambre)' }}>
              <h3 style={{ color: 'var(--ambre)' }}>Eau ancienne · {x.chiffre_id}</h3>
              <div className="muted">Sert {String(x.tampon)}, attendu {String(x.attendu)} — {x.mecanisme}.</div>
            </div>
          ))}
          <div className="card"><h3>Ce qu'il affiche · {(r.chiffres || []).length} chiffre{(r.chiffres || []).length > 1 ? 's' : ''}</h3>
            {(r.chiffres || []).length ? <ul className="list">{chiffres.map((ch: any) => {
              const prefixe = (ch.calcul || '').split(':')[0]
              return (
                <li key={ch.id}><span title={ch.definition}>{ch.libelle}</span>
                  <span>
                    <span className={`tag ${prefixe === 'moteur' ? 'mint' : 'ambre'}`}>{prefixe === 'moteur' ? 'moteur' : prefixe === 'passe_plat' ? 'hors moteur' : prefixe}</span>
                    {ch.portee === 'run' ? <span className="tag">run</span> : null}
                  </span></li>
              )
            })}</ul> : <div className="muted">Aucun chiffre : tuiles ou géométries seulement, hors registre.</div>}
            {r.hors_moteur ? <div style={{ color: 'var(--ambre)', marginTop: 10 }}>{r.hors_moteur} calculé{r.hors_moteur > 1 ? 's' : ''} hors moteur, à rebrancher.</div> : null}
          </div>
          {/* CIRCUIT-4 (accroche) — « La règle derrière ces calculs » : badges de règle par chiffre. */}
        </div>
        <div>
          <div className="card"><h3>Alimenté par · {amont.length} réservoirs</h3>
            {amont.length ? amont.map((a: any) => {
              const rid = idReservoir(a.slug)
              return <span key={a.slug} className={`chip ${['mint', 'gris'].includes(resEtat(a.slug)) ? '' : resEtat(a.slug)}`}
                onClick={() => rid !== undefined && onOpen('reservoir', rid)}>{a.nom}</span>
            }) : <span className="muted">aucun, par le registre</span>}
          </div>
          <div className="card"><h3>Dernier contrôle</h3>
            <div>{dernier_controle
              ? <>Le {dateFr(dernier_controle.ts)}, {dernier_controle.robinets_couverts} robinets couverts. {c === 'mint' ? <span style={{ color: 'var(--mint)' }}>Même valeur partout.</span> : ''}</>
              : <span className="muted">jamais contrôlé</span>}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── POMPE ────────────────────────────────────────────────────────────────────────────────────
function DetailPompe({ back, rafraichir }: { back: JSX.Element; rafraichir: () => void }) {
  const q = useQuery({ queryKey: ['circuit-detail', 'pompe'], queryFn: getAdminCircuitPompe })
  const [note, setNote] = useState<any>(null)
  const [noteLue, setNoteLue] = useState<string | null>(null)
  const lancer = useMutation({ mutationFn: () => postAdminFluxLancerRun('m36'), onSuccess: rafraichir })
  const basculer = useMutation({ mutationFn: (run: string) => postAdminFluxBascule(run), onSuccess: () => { setNote(null); setNoteLue(null); rafraichir() } })
  const revenir = useMutation({ mutationFn: postAdminCircuitRevenir, onSuccess: () => { setNote(null); setNoteLue(null); rafraichir() } })

  if (q.isLoading || !q.data) return <div className="detail on">{back}<div className="muted">Chargement…</div></div>
  const p = q.data
  const candidat = p.candidat as string | null
  const precedent = p.precedent?.scoring_run as string | undefined

  return (
    <div className="detail on">
      {back}
      <div className="dh">
        <div><h1>Le moteur</h1><div className="m">{p.n_moteurs} moteurs, {p.n_chiffres} chiffres, une définition chacun. Un robinet ne calcule pas, il demande ici.</div></div>
        <div className="state"><span className="pill mint"><i />run servi {p.run_servi}</span>
          {candidat && <span className="pill ambre"><i />candidat {candidat} prêt</span>}</div>
      </div>
      <div className="dg">
        <div>
          <div className="card"><h3>Ce qui attend</h3>
            <div className="kv">
              <div>Eau nouvelle</div><div>{p.residuel?.changees ? p.residuel.detail : <span className="muted">aucune</span>}</div>
              <div>Candidat</div><div>{candidat ? <b>{candidat}</b> : <span className="muted">aucun</span>}</div>
              {precedent ? <><div>Précédent</div><div>{precedent}, retour possible</div></> : null}
              <div>Pointeurs</div><div style={{ color: p.pointeurs_multiples ? 'var(--rouge)' : undefined }}>
                {p.pointeurs_multiples ? `${Object.keys(p.pointeurs).length} au lieu d'un` : 'un seul, le manifeste'}</div>
            </div>
            <div className="actions">
              <button className="btn mint" disabled={lancer.isPending || (!p.residuel?.changees && !candidat)} onClick={() => lancer.mutate()}>Faire tourner la pompe</button>
              {candidat && <button className="btn ambre" onClick={async () => { setNote(await getAdminCircuitNoteVersion(candidat)); setNoteLue(candidat) }}>Note de version</button>}
              {candidat && <button className="btn ambre" disabled={noteLue !== candidat} title={noteLue !== candidat ? 'Ouvrez la note de version d\'abord.' : ''} onClick={() => basculer.mutate(candidat)}>Basculer sur {candidat}</button>}
              {precedent && <button className="btn" disabled={revenir.isPending} onClick={() => revenir.mutate()}>Revenir à {precedent}</button>}
            </div>
            <div className="muted" style={{ marginTop: 10 }}>Calculer produit un candidat, jamais servi tout seul. Basculer déplace tous les pointeurs d'un geste.</div>
          </div>
          {note && <div className="card" style={{ borderColor: 'var(--ambre)' }}>
            <h3 style={{ color: 'var(--ambre)' }}>Note de version de {note.candidat}</h3>
            <div className="muted">réservoirs : {note.reservoirs?.length ?? 0} · chiffres recalculés : {note.chiffres_recalcules?.length ?? 0}</div>
            {note.ecart_classement?.ok === false && <div className="muted">écart : {note.ecart_classement.motif}</div>}
          </div>}
        </div>
        <div>
          <div className="card"><h3>Les {p.n_moteurs} moteurs</h3>
            <ul className="list">{p.moteurs.map((m: any) => <li key={m.nom}><span>{m.nom}</span></li>)}</ul></div>
          <div className="card"><h3>Horloges qui touchent l'eau</h3>
            <ul className="list">{p.jobs_eau.map((j: string) => <li key={j}><span>{j}</span></li>)}</ul></div>
        </div>
      </div>
    </div>
  )
}
