// COCKPIT-1 (Lot A) — l'onglet « Tableau de bord » (remplace « À faire » + « Cohérence »). Il répond
// à trois questions, dans cet ordre, en RENDANT ce que le serveur compose (`data.cockpit`) — le front
// ne recalcule rien :
//   1. « Qu'est-ce que je dois faire aujourd'hui ? »  — une carte PAR PROBLÈME, un bouton primaire
//      (Injecter · Reconstruire · Réessayer · Accepter), « demande du code » + « Voir le détail » pour
//      ce qui n'est pas un clic. Plus aucun bouton « Décider ».
//   2. « Est-ce que tout tourne ? »  — 4 tuiles + « Voir l'usine ».
//   3. « Où en est la mise à jour ? »  — 4 étapes (Injecter → Calculer → Basculer → Envoyer en prod).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import {
  getAdminCockpitEtatProd, postAdminCircuitSonder, postAdminFluxBascule, postAdminFluxLancerRun,
  postCockpitAccepterEcarts, postCockpitAccepterIncident, postCockpitEnvoyerProd, postCockpitInjecter,
  postCockpitReconstruire, postJobLancer,
} from '../../../lib/api'

import type { CircuitData, CockpitCarte, CockpitEtape } from './types'

export function TableauDeBord({ data, onVoirUsine, onDepotManuel }:
  { data: CircuitData; onVoirUsine: () => void; onDepotManuel: () => void }) {
  const qc = useQueryClient()
  const ck = data.cockpit
  const [detail, setDetail] = useState<CockpitCarte | null>(null)
  const [copie, setCopie] = useState(false)
  const [msg, setMsg] = useState<{ t: string; err?: boolean } | null>(null)
  const section1 = useRef<HTMLDivElement>(null)

  // l'état PROD (version servie chez les clients) — lu serveur→serveur, à part (appel réseau).
  const prod = useQuery({ queryKey: ['cockpit-etat-prod'], queryFn: getAdminCockpitEtatProd,
    refetchInterval: 120_000, staleTime: 60_000 })

  const apres = (t: string) => { setMsg({ t }); qc.invalidateQueries({ queryKey: ['admin-circuit'] }) }
  const surErreur = (e: any) => setMsg({ t: e?.detail || e?.message || 'Action impossible.', err: true })

  const injecter = useMutation({ mutationFn: (s: number[]) => postCockpitInjecter(s),
    onSuccess: (r) => apres(`Injection lancée pour ${r.n} source${r.n > 1 ? 's' : ''} — suivi dans le Journal.`), onError: surErreur })
  const reconstruire = useMutation({ mutationFn: postCockpitReconstruire,
    onSuccess: () => apres('Reconstruction lancée — progression dans le Journal.'), onError: surErreur })
  const reessayer = useMutation({ mutationFn: () => postAdminCircuitSonder(),
    onSuccess: () => apres('Le veilleur repart sur les sources en panne — suivi dans le Journal.'), onError: surErreur })
  const accepter = useMutation({ mutationFn: postCockpitAccepterEcarts,
    onSuccess: () => apres('Écarts acceptés (témoins regénérés) — suivi dans le Journal.'), onError: surErreur })
  const calculer = useMutation({ mutationFn: () => postAdminFluxLancerRun('m36'),
    onSuccess: () => apres('Calcul lancé sur le Mac — suivi dans le Journal.'), onError: surErreur })
  const basculer = useMutation({ mutationFn: (run: string) => postAdminFluxBascule(run),
    onSuccess: () => apres('Bascule faite — l\'app sert la nouvelle version.'), onError: surErreur })
  const envoyer = useMutation({ mutationFn: postCockpitEnvoyerProd,
    onSuccess: () => apres('Envoi en prod lancé (deploy + parité) — suivi dans le Journal.'), onError: surErreur })
  // COCKPIT-1b (point 5) — « Réessayer » d'une carte vigie (ex. sauvegarde en retard) relance le poste.
  const lancerJob = useMutation({ mutationFn: (nom: string) => postJobLancer(nom),
    onSuccess: () => apres('Relancé — suivi dans le Journal.'), onError: surErreur })
  // DONNEES-ETAT-FIX-2 (Lot C) — « Accepter » une carte d'incident : l'acquitte (rouvre si toujours réel).
  const accepterIncident = useMutation({ mutationFn: (cle: string) => postCockpitAccepterIncident(cle),
    onSuccess: () => apres('Incident accepté — il réapparaîtra au prochain contrôle s\'il est toujours réel.'), onError: surErreur })

  if (!ck) return <div className="muted">Tableau de bord indisponible.</div>

  // ── les boutons des cartes (section 1) ──
  const lancerCarte = (c: CockpitCarte) => {
    const b = c.bouton
    if (!b) return
    switch (b.action) {
      case 'injecter': injecter.mutate(b.sources || []); break
      case 'reconstruire': reconstruire.mutate(); break
      case 'reessayer': reessayer.mutate(); break
      case 'accepter-ecarts':
        if (window.confirm(`Accepter ${b.n} écart${(b.n || 0) > 1 ? 's' : ''} toléré${(b.n || 0) > 1 ? 's' : ''} ? `
          + 'Les témoins de cohérence seront regénérés (à commiter ensuite).')) accepter.mutate()
        break
      case 'deposer': onDepotManuel(); break
      case 'lancer-job': if (b.nom) lancerJob.mutate(b.nom); break
      case 'accepter-incident':
        if (b.cle && window.confirm('Accepter cet incident ? Il réapparaîtra au prochain contrôle s\'il est toujours réel.'))
          accepterIncident.mutate(b.cle)
        break
    }
  }

  // ── les boutons des étapes (section 3) ──
  const lancerEtape = (e: CockpitEtape) => {
    const b = e.bouton
    if (!b) return
    switch (b.action) {
      case 'voir-cartes': section1.current?.scrollIntoView({ behavior: 'smooth' }); break
      case 'calculer': calculer.mutate(); break
      case 'basculer': if (b.candidat) basculer.mutate(b.candidat); break
      case 'envoyer-prod': {
        const txt = `Envoyer la version calculée en prod ?\n\n`
          + `Version à envoyer : ${data.run_servi}\n`
          + `Chez les clients aujourd'hui : ${prod.data?.run || '?'}\n`
          + `Durée : ~20 minutes, le site reste ouvert.\n\n`
          + `L'envoi copie les données du Mac puis contrôle la parité. Jamais le code.`
        if (window.confirm(txt)) envoyer.mutate()
        break
      }
    }
  }

  const enCours = injecter.isPending || reconstruire.isPending || reessayer.isPending
    || accepter.isPending || calculer.isPending || basculer.isPending || envoyer.isPending || lancerJob.isPending

  const r = ck.tout_tourne.resume

  return (
    <div className="ck">
      {msg && <div className={`ck-msg ${msg.err ? 'err' : ''}`}>{msg.t}
        <button className="btn" style={{ marginLeft: 12, padding: '3px 9px' }} onClick={() => setMsg(null)}>OK</button></div>}

      {/* ─────────── 1. Qu'est-ce que je dois faire aujourd'hui ? ─────────── */}
      <div className="ck-sect" ref={section1}>
        <div className="ck-head">
          <h2>Qu'est-ce que je dois faire aujourd'hui&nbsp;?</h2>
          <span className="sub">{ck.aujourdhui.n === 0 ? 'rien pour le moment'
            : `${ck.aujourdhui.n} chose${ck.aujourdhui.n > 1 ? 's' : ''}, triée${ck.aujourdhui.n > 1 ? 's' : ''} par importance`}</span>
        </div>
        {ck.aujourdhui.cartes.length === 0
          ? <div className="okline"><i /> <b>Tout est en ordre.</b>&nbsp;Aucun geste en attente.</div>
          : ck.aujourdhui.cartes.map((c) => (
            <div className={`ck-card ${c.pastille === 'rouge' ? 'rouge' : ''}`} key={c.id}>
              <span className={`ck-dot ${c.pastille}`} />
              <div>
                <div className="ti">{c.titre}{c.code && <span className="ck-badge">demande du code</span>}</div>
                <div className="ph">{c.phrase}</div>
              </div>
              <div className="acts">
                {c.voir_detail && c.detail && (
                  <button className="btn" onClick={() => { setDetail(c); setCopie(false) }}>Voir le détail</button>)}
                {c.bouton && (
                  <button className="btn solid" disabled={enCours} onClick={() => lancerCarte(c)}>{c.bouton.label}</button>)}
              </div>
            </div>
          ))}
        <div className="ck-depot">
          Une source reçue par mail, un PDF de PLU, un fichier de la DEAL&nbsp;?{' '}
          <button onClick={onDepotManuel}>Déposer une source à la main</button>
        </div>
      </div>

      {/* ─────────── 2. Est-ce que tout tourne ? ─────────── */}
      <div className="ck-sect">
        <div className="ck-head">
          <h2>Est-ce que tout tourne&nbsp;?</h2>
          <span className="sub">{r.postes} postes dans l'usine · {r.vert} au vert
            {r.echec ? ` · ${r.echec} en échec` : ''}{r.arret ? ` · ${r.arret} à l'arrêt` : ''}</span>
          <span className="right"><button className="btn" onClick={onVoirUsine}>Voir l'usine</button></span>
        </div>
        <div className="ck-tuiles">
          {ck.tout_tourne.tuiles.map((t) => (
            <div className={`ck-tuile ${t.pastille === 'rouge' ? 'rouge' : ''}`} key={t.id}>
              <div className="th"><span className={`ck-tdot ${t.pastille}`} />{t.titre}</div>
              <div className="tl">{t.ligne}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ─────────── 3. Où en est la mise à jour ? ─────────── */}
      <div className="ck-sect">
        <div className="ck-head"><h2>Où en est la mise à jour&nbsp;?</h2></div>
        <div className="ck-etapes">
          {ck.mise_a_jour.etapes.map((e) => {
            const prodRun = e.id === 'envoyer-prod' && prod.data?.run
            return (
              <div className={`ck-etape ${!e.fait ? 'afaire' : ''}`} key={e.id}>
                <div className="no">Étape {e.ordre}</div>
                <div className="nm">{e.titre}</div>
                <div className="ln">{e.ligne}{prodRun ? ` (${prodRun})` : ''}</div>
                <div className={`fa ${e.fait ? '' : 'todo'}`}><i />{e.fait ? 'fait' : 'à faire'}</div>
                {e.bouton && <button className="btn solid" disabled={enCours} onClick={() => lancerEtape(e)}>{e.bouton.label}</button>}
                {e.id === 'envoyer-prod' && e.local === false && <span className="muted" style={{ fontSize: 12 }}>se fait depuis le Mac</span>}
              </div>
            )
          })}
        </div>
        <div className="ck-foot">Chaque étape attend la précédente. L'envoi prend ~20 minutes, le site reste ouvert.</div>
      </div>

      {/* ─────────── fenêtre « Voir le détail » (faits techniques, copiables) ─────────── */}
      {detail && (
        <div className="ck-modal" onClick={() => setDetail(null)}>
          <div className="ck-dlg" onClick={(ev) => ev.stopPropagation()}>
            <h3>{detail.titre}{detail.code && <span className="ck-badge">demande du code</span>}
              <button className="x" onClick={() => setDetail(null)}>✕</button></h3>
            <pre className="ck-pre">{detail.detail?.texte}</pre>
            <p className="note">
              {detail.code
                ? 'Ce n\'est pas un clic à faire ici. Copie ce détail et donne-le à Claude Code. Quand c\'est corrigé et mergé, cette carte disparaît toute seule au prochain contrôle.'
                : 'Les faits techniques de ce problème, prêts à copier.'}
            </p>
            <div className="foot">
              <button className="btn mint" onClick={() => {
                navigator.clipboard?.writeText(detail.detail?.texte || ''); setCopie(true)
              }}>{copie ? 'Copié ✓' : 'Copier le détail'}</button>
              <button className="btn solid" onClick={() => setDetail(null)}>OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
