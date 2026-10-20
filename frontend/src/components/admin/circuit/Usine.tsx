// COCKPIT-1 (Lot B) — « L'usine » : la page atteinte depuis « Voir l'usine » du Tableau de bord.
// Lue du REGISTRE des jobs (/admin/usine, rafraîchie toutes les 60 s) : 4 colonnes (familles), chaque
// poste avec son libellé/rôle, dernier & prochain passage, pastille (vert/violet/rouge/gris) et le
// bouton possible — « Lancer maintenant » (sans risque), « Démarrer » (agents IA, coût/plafond),
// « Voir le détail » (échec). La famille « Le moteur » porte en tête les étapes Calculer/Basculer/
// Envoyer en prod. Les gelés vivent dans un bandeau en bas (« Réveiller… », confirmation).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  getAdminUsine, postAdminCircuitAgents, postAdminFluxBascule, postAdminFluxLancerRun,
  postCockpitEnvoyerProd, postJobLancer, type UsinePoste,
} from '../../../lib/api'

import type { CircuitData, CockpitEtape } from './types'

const quand = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

const resultat = (s: string | null) =>
  s === 'ok' ? 'ok' : s === 'dry-run' ? 'ok (à vide)' : s === 'echec' ? 'échec'
    : s === 'timeout' ? 'trop long' : s === 'en_cours' ? 'en cours' : 'jamais'

export function Usine({ data, onBack }: { data: CircuitData; onBack: () => void }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-usine'], queryFn: getAdminUsine, refetchInterval: 60_000 })
  const [detail, setDetail] = useState<UsinePoste | null>(null)
  const [copie, setCopie] = useState(false)
  const [msg, setMsg] = useState<{ t: string; err?: boolean } | null>(null)

  const apres = (t: string) => { setMsg({ t }); q.refetch(); qc.invalidateQueries({ queryKey: ['admin-circuit'] }) }
  const surErreur = (e: any) => setMsg({ t: e?.detail || e?.message || 'Action impossible.', err: true })

  const lancer = useMutation({ mutationFn: (nom: string) => postJobLancer(nom),
    onSuccess: (r) => apres(r.reveil ? 'Poste réveillé — suivi dans le Journal.' : 'Lancé — suivi dans le Journal.'), onError: surErreur })
  const agents = useMutation({ mutationFn: () => postAdminCircuitAgents({ portee: 'sans_amont' }),
    onSuccess: (r: any) => (r && r.ok === false ? setMsg({ t: r.message || 'Crédit API indisponible.', err: true }) : apres('Enquêteurs lancés — suivi dans le Journal.')), onError: surErreur })
  const calculer = useMutation({ mutationFn: () => postAdminFluxLancerRun('m36'),
    onSuccess: () => apres('Calcul lancé — suivi dans le Journal.'), onError: surErreur })
  const basculer = useMutation({ mutationFn: (run: string) => postAdminFluxBascule(run),
    onSuccess: () => apres('Bascule faite.'), onError: surErreur })
  const envoyer = useMutation({ mutationFn: postCockpitEnvoyerProd,
    onSuccess: () => apres('Envoi en prod lancé — suivi dans le Journal.'), onError: surErreur })

  const d = q.data
  const enCours = lancer.isPending || agents.isPending || calculer.isPending || basculer.isPending || envoyer.isPending
  const etapes = data.cockpit?.mise_a_jour.etapes ?? []

  const bouton = (p: UsinePoste) => {
    if (!p.bouton) return null
    const b = p.bouton
    const clic = () => {
      if (b.action === 'agents') { agents.mutate(); return }
      if (b.action === 'reveiller') {
        if (window.confirm(`Réveiller « ${p.libelle} » ? Ce poste est volontairement à l'arrêt ; il tournera une fois, maintenant.`)) lancer.mutate(p.nom)
        return
      }
      if (b.action === 'lancer') lancer.mutate(p.nom)
    }
    return <button className="btn mint" disabled={enCours} onClick={clic}>{b.label}</button>
  }

  const poste = (p: UsinePoste) => (
    <div className="us-poste" key={p.nom}>
      <div className="us-ph">
        <span className={`us-dot ${p.pastille}`} />
        <span className="nm">{p.libelle}</span>
        {p.heure_reunion && !p.gel && <span className="hr">{p.heure_reunion}</span>}
      </div>
      <div className="ro">{p.role}</div>
      <div className="mt">
        <span>passé {quand(p.dernier.fin)} · <span className={`r ${p.dernier.statut === 'echec' || p.dernier.statut === 'timeout' ? 'rouge' : ''}`}>{resultat(p.dernier.statut)}</span></span>
        {p.prochaine && <span>prochain {p.prochaine}</span>}
      </div>
      {(p.bouton || p.voir_detail) && (
        <div className="act">
          {bouton(p)}
          {p.voir_detail && p.detail && <button className="btn" onClick={() => { setDetail(p); setCopie(false) }}>Voir le détail</button>}
        </div>
      )}
    </div>
  )

  // le bloc « Le moteur » (étapes Calculer → Basculer → Envoyer en prod), en tête de la 3ᵉ colonne.
  const moteur = () => {
    const act = (e: CockpitEtape) => {
      if (!e.bouton) return null
      const b = e.bouton
      const clic = () => {
        if (b.action === 'calculer') calculer.mutate()
        else if (b.action === 'basculer' && b.candidat) basculer.mutate(b.candidat)
        else if (b.action === 'envoyer-prod') {
          if (window.confirm(`Envoyer la version calculée en prod ?\n\nVersion : ${data.run_servi}\nDurée : ~20 min, le site reste ouvert.`)) envoyer.mutate()
        }
      }
      if (b.action === 'voir-cartes') return null
      return <button className="btn mint" disabled={enCours} onClick={clic}>{b.label}</button>
    }
    return (
      <div className="us-moteur">
        <h4>Le calcul &amp; la mise en ligne</h4>
        {etapes.map((e) => (
          <div className="us-step" key={e.id}>
            <span className="n">{e.ordre}</span>
            <span>{e.titre} <span className="muted" style={{ fontSize: 11 }}>· {e.ligne}</span></span>
            <span className={`s ${e.fait ? '' : 'todo'}`}>{e.fait ? 'fait' : 'à faire'}</span>
          </div>
        ))}
        <div className="act">{etapes.map((e) => <span key={e.id}>{act(e)}</span>)}</div>
      </div>
    )
  }

  return (
    <div className="ck">
      <div className="ck-head" style={{ marginBottom: 10 }}>
        <span className="right" />
        <button className="btn" onClick={onBack}>← Tableau de bord</button>
      </div>
      {msg && <div className={`ck-msg ${msg.err ? 'err' : ''}`}>{msg.t}
        <button className="btn" style={{ marginLeft: 12, padding: '3px 9px' }} onClick={() => setMsg(null)}>OK</button></div>}

      <div className="us-top">
        <h2>L'usine</h2>
        <span className="sub">{d ? `${d.resume.postes} postes · ${d.resume.vert} au vert${d.resume.echec ? ` · ${d.resume.echec} en échec` : ''}${d.resume.arret ? ` · ${d.resume.arret} à l'arrêt` : ''}` : 'chargement…'}</span>
      </div>
      {d && <div className="us-leg">{d.legende.map(([c, l]) => <span key={c}><i className={`us-dot ${c}`} style={{ display: 'inline-block' }} />{l}</span>)}</div>}

      {!d ? <div className="muted">L'usine — chargement…</div> : (
        <>
          <div className="us-cols">
            {d.familles.map((f) => (
              <div className="us-col" key={f.n}>
                <h3>{f.n} · {f.nom}</h3>
                {f.n === 3 && moteur()}
                {f.postes.map(poste)}
                {f.postes.length === 0 && f.n !== 3 && <div className="muted" style={{ fontSize: 12, padding: '4px 2px' }}>aucun poste actif</div>}
              </div>
            ))}
          </div>

          {d.geles.length > 0 && (
            <div className="us-geles">
              <b>En attente des premiers clients, volontairement à l'arrêt :</b>
              {d.geles.map((p, i) => (
                <span key={p.nom}>
                  <span className="g">{p.libelle}</span>
                  <button className="btn" style={{ marginLeft: 6, padding: '3px 9px' }} disabled={enCours}
                    onClick={() => { if (window.confirm(`Réveiller « ${p.libelle} » ? Il tournera une fois, maintenant.`)) lancer.mutate(p.nom) }}>Réveiller…</button>
                  {i < d.geles.length - 1 ? '  ' : ''}
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {detail && (
        <div className="ck-modal" onClick={() => setDetail(null)}>
          <div className="ck-dlg" onClick={(ev) => ev.stopPropagation()}>
            <h3>{detail.libelle}<button className="x" onClick={() => setDetail(null)}>✕</button></h3>
            <pre className="ck-pre">{detail.detail?.texte}</pre>
            <div className="foot">
              <button className="btn mint" onClick={() => { navigator.clipboard?.writeText(detail.detail?.texte || ''); setCopie(true) }}>{copie ? 'Copié ✓' : 'Copier le détail'}</button>
              <button className="btn solid" onClick={() => setDetail(null)}>OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
