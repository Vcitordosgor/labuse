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
  getAdminCircuitCompteur, getAdminCircuitNoteVersion, getAdminCircuitPompe,
  getAdminCircuitReservoir, getAdminCircuitRobinet,
  postAdminCircuitAgents, postAdminCircuitFiltreRevenir, postAdminCircuitFiltreServir,
  postAdminCircuitRevenir, postAdminFluxBascule, postAdminFluxLancerRun, postAdminSourceVeilleInjecter,
} from '../../../lib/api'

import type { CircuitData, Couleur } from './types'

type Ouvrir = (type: 'reservoir' | 'robinet' | 'pompe' | 'compteur', id: number | string) => void
type Props = { type: 'reservoir' | 'robinet' | 'pompe' | 'compteur'; id: number | string; data: CircuitData; onClose: () => void; onOpen: Ouvrir }

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
  if (type === 'compteur') return <DetailCompteur back={back} onOpen={onOpen} />
  return <DetailPompe back={back} rafraichir={rafraichir} />
}

// ── COMPTEUR (lot 2.2) — les réservoirs par état + les lignes en base non servies ──────────────
function DetailCompteur({ back, onOpen }: { back: JSX.Element; onOpen: Ouvrir }) {
  const q = useQuery({ queryKey: ['circuit-detail', 'compteur'], queryFn: getAdminCircuitCompteur })
  if (q.isLoading || !q.data) return <div className="detail on">{back}<div className="muted">Chargement…</div></div>
  const { compteurs: cpt, definition, groupes, non_servies, carte } = q.data
  return (
    <div className="detail on">
      {back}
      <div className="dh">
        <div><h1>{cpt.reservoirs} réservoirs</h1>
          <div className="m">{cpt.a_jour} à jour et vérifiés · {cpt.a_regarder} à regarder · {cpt.vides} vides ou manuels</div></div>
      </div>
      <div className="card"><h3>« À jour et vérifiés », c'est quoi ?</h3><div className="muted">{definition}</div></div>
      {groupes.map((g: any) => (
        <div key={g.cle} className="card"><h3>{g.titre} · {g.reservoirs.length}</h3>
          {g.reservoirs.length ? <div>{g.reservoirs.map((r: any) => (
            <span key={r.id} className={`chip ${['mint', 'gris'].includes(r.etat[0]) ? '' : r.etat[0]}`}
              title={`${r.producteur || ''} — ${r.etat[1]}`} onClick={() => onOpen('reservoir', r.id)}>{r.nom}</span>
          ))}</div> : <div className="muted">aucun</div>}
        </div>
      ))}
      <div className="card"><h3>{non_servies.length} ligne{non_servies.length > 1 ? 's' : ''} en base non servie{non_servies.length > 1 ? 's' : ''}</h3>
        <div className="muted" style={{ marginBottom: 8 }}>Ces lignes de <code>data_sources</code> ne sont pas des réservoirs (retirées, doublons, hubs dormants) : elles n'entrent dans aucun compteur.</div>
        {non_servies.length ? <ul className="list">{non_servies.map((n: any) => (
          <li key={n.id}><span>{n.nom}</span><span className="muted">{n.raison}</span></li>
        ))}</ul> : <div className="muted">aucune</div>}
      </div>
      {/* CIRCUIT-5 (lot 6.2) — LA CARTE table → réservoir : ce que chaque réservoir sert
          physiquement en base (registre/tables.py, la même déclaration que le verrou V1). */}
      {Array.isArray(carte) && carte.length > 0 && (
        <div className="card"><h3>La carte : chaque réservoir, ses tables</h3>
          <div className="muted" style={{ marginBottom: 8 }}>
            Ce que chaque réservoir sert en base (tables, couches <code>spatial_layers</code>, millésime) —
            la déclaration que les verrous font respecter : aucun moteur ne lit une table hors de cette carte.
          </div>
          <ul className="list">{carte.map((r: any) => (
            <li key={r.id}>
              <span>{r.nom}</span>
              <span className="muted">
                {r.tables.length
                  ? r.tables.map((t: string) => (
                    <code key={t} style={{ marginRight: 6 }}>
                      {t}{t === 'spatial_layers' && r.couches.length ? `(${r.couches.join(', ')})` : ''}
                    </code>
                  ))
                  : (r.note || 'aucune table')}
                {r.millesime ? ` · ${r.millesime}` : ''}
              </span>
            </li>
          ))}</ul>
        </div>
      )}
    </div>
  )
}

// ── RÉSERVOIR ────────────────────────────────────────────────────────────────────────────────
function DetailReservoir({ id, data, back, onOpen, rafraichir }:
  { id: number; data: CircuitData; back: JSX.Element; onOpen: Ouvrir; rafraichir: () => void }) {
  const q = useQuery({ queryKey: ['circuit-detail', 'reservoir', id], queryFn: () => getAdminCircuitReservoir(id) })
  const [msgAgent, setMsgAgent] = useState<string | null>(null)
  // CIRCUIT-P2 (lot 3.3) — « Envoyer un agent » : jamais grisé sans mot (sans crédit → message).
  const agent = useMutation({
    mutationFn: () => postAdminCircuitAgents(id),
    onSuccess: (r: any) => {
      if (r && r.ok === false) setMsgAgent(r.message || 'Crédit API indisponible.')
      else { setMsgAgent(r?.message || 'Agent envoyé — le retour arrive au journal.'); rafraichir() }
    },
  })
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
              <button className="btn mauve" disabled={agent.isPending}
                onClick={() => agent.mutate()}>{agent.isPending ? 'Agent en route…' : 'Envoyer un agent'}</button>
              {r.vanne?.type === 'injecter' && <button className="btn ambre" disabled={injecter.isPending}
                onClick={() => injecter.mutate()}>Ouvrir la vanne, injecter</button>}
              {f.verdict === 'quarantaine' && <>
                <button className="btn ambre" disabled={servir.isPending}
                  onClick={() => { if (confirm(`Servir « ${f.source} » malgré la quarantaine ?`)) servir.mutate(f.source) }}>Servir quand même</button>
                {f.live && <button className="btn" disabled={filtreRevenir.isPending}
                  onClick={() => { if (confirm(`Revenir à la version précédente de « ${f.source} » ?`)) filtreRevenir.mutate(f.source) }}>Revenir à la précédente</button>}
              </>}
            </div>
            {msgAgent && <div className="muted" style={{ marginTop: 8 }}>{msgAgent}</div>}
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
              // CIRCUIT-P2 (lot 2.1) — « hors moteur » = sql_propre/front (ch.hors_moteur, ambre) ;
              // un passe-plat est NEUTRE (valeur brute déclarée), une constante aussi.
              const label = prefixe === 'moteur' ? 'moteur' : ch.hors_moteur ? 'hors moteur'
                : prefixe === 'passe_plat' ? 'passe-plat' : prefixe
              return (
                <li key={ch.id}><span title={ch.definition}>{ch.libelle}</span>
                  <span>
                    <span className={`tag ${prefixe === 'moteur' ? 'mint' : ch.hors_moteur ? 'ambre' : ''}`}>{label}</span>
                    {ch.portee === 'run' ? <span className="tag">run</span> : null}
                  </span></li>
              )
            })}</ul> : <div className="muted">Aucun chiffre : tuiles ou géométries seulement, hors registre.</div>}
            {r.hors_moteur ? <div style={{ color: 'var(--ambre)', marginTop: 10 }}>{r.hors_moteur} calculé{r.hors_moteur > 1 ? 's' : ''} hors moteur (SQL brut ou front), à rebrancher.</div> : null}
          </div>
          {/* CIRCUIT-4 (lot 5.2) — LA RÈGLE DERRIÈRE CES CALCULS : un badge par donnée —
              conforme (mint) · écart (rouge) · référence introuvable / partiel (ambre) ·
              choix LABUSE (gris, définition au survol) · modèle (mauve) — et le lien vers
              l'extrait de référence. */}
          {(chiffres || []).some((ch: any) => ch.regle) && (
            <div className="card"><h3>La règle derrière ces calculs</h3>
              <ul className="list">{chiffres.filter((ch: any) => ch.regle).map((ch: any) => {
                const rg = ch.regle
                const badge = rg.verdict === 'conforme' ? ['mint', 'conforme']
                  : rg.verdict === 'ecart' ? ['rouge', 'écart à la règle']
                    : rg.verdict === 'partiel' ? ['ambre', 'partiel']
                      : rg.verdict === 'reference_introuvable' ? ['ambre', 'référence introuvable']
                        : rg.verdict === 'choix_assume' ? ['gris', 'choix LABUSE']
                          : ['mauve', 'modèle validé']
                const ref = rg.reference
                return (
                  <li key={ch.id}>
                    <span title={rg.choix || rg.ecart || ''}>{ch.libelle}</span>
                    <span>
                      <span className={`tag ${badge[0] === 'mint' ? 'mint' : badge[0]}`}
                        title={(rg.ecart || rg.choix || '') + (ref ? `\n— ${ref.titre}, ${ref.article} (${ref.version})` : '')}>
                        {badge[1]}</span>
                      {ref?.url?.startsWith('http') && (
                        <a className="tag" href={ref.url} target="_blank" rel="noreferrer"
                          title={`${ref.titre} — ${ref.article} · ${ref.version}\n« ${(ref.extrait || '').slice(0, 300)}… »`}>
                          référence ↗</a>
                      )}
                    </span>
                  </li>
                )
              })}</ul>
            </div>
          )}
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
