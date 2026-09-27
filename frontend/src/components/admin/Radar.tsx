// RADAR (pige) · DASHBOARD-2 (Lot 4) — page admin « Radar », grammaire de la maquette v1 : une seule
// page qui descend. Dépôt HTML en drop zone + bilan du DERNIER dépôt · « À faire » (à valider · à
// re-vérifier, listes dépliables) · « Le flux » (en vie · rattachées · copros non servies · paires DVF ·
// drapeau dépôt agence). Le chemin par CAPTURES D'ÉCRAN est RETIRÉ (répertoire /srv en lecture seule,
// remplacé par le dépôt HTML). Doctrine intacte : on n'affiche jamais l'annonce — des FAITS + le lien.
// Un seul compteur « en vie » (RadarCheck.flux.en_vie), le même qu'au Pilotage.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getRadarCheck, getRadarDepotAgenceEtat, getRadarExtraction, getRadarReverif,
  postRadarDepotAgenceToggle, radarDeposerHtml, radarPrix, radarRattacherHumain,
  radarRetiree, radarToujoursEnLigne, radarValider,
  type RadarBrouillon, type RadarCheck, type RadarDepotHtml, type RadarReverif,
} from '../../lib/api'
import { Chip, Panel, PHead } from './AdminView'

const NIV: Record<string, { label: string; tone: 'ok' | 'warn' | 'off' }> = {
  source: { label: 'Sourcé', tone: 'ok' }, estime: { label: 'Estimé', tone: 'warn' },
  absent: { label: 'Non rattachée', tone: 'off' },
}
const fmtEur = (v: number | null) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')
const fmtReu = (iso?: string | null) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(iso)).replace(',', '')
  } catch { return '—' }
}

// ── Dépôt du jour : la page de résultats HTML (remplace la capture + vision) ──
function DepotHtml({ onDepose }: { onDepose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [rap, setRap] = useState<RadarDepotHtml | null>(null)
  const deposer = async (files: FileList | null) => {
    const f = files?.[0]
    if (!f) return
    setBusy(true); setRap(null)
    try {
      const html = await f.text()
      setRap(await radarDeposerHtml(html, f.name))
      onDepose()
    } catch {
      setRap({ ok: false, motif: 'le dépôt a échoué (réseau ou serveur) — réessayer' })
    } finally { setBusy(false) }
  }
  return (
    <section className="flex flex-col rounded-xl border border-dashed border-line-3 bg-surface-2 p-5 text-center">
      <b className="text-[13.5px] font-medium text-txt-hi">Déposer la page de résultats du jour</b>
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-txt-mut">
        <b>⌘S → « page web complète »</b> sur le portail, puis glisser le <span className="font-mono">.html</span> ici.
        Toutes les annonces de la page sont lues d’un coup, sans doublon.
      </p>
      <label className={`mx-auto mt-3 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-mint px-3.5 py-2 text-[12px] font-medium text-mint-on hover:brightness-110 ${busy ? 'pointer-events-none opacity-60' : ''}`}>
        <input data-radar-depot-html type="file" accept=".html,.htm,text/html" className="hidden"
               onChange={(e) => deposer(e.target.files)} />
        {busy ? 'Lecture de la page…' : 'Choisir un fichier'}
      </label>
      {rap && !rap.ok && (
        <div data-radar-depot-erreur className="mt-3 rounded-lg border border-st-ecartee/50 bg-st-ecartee/10 px-3 py-2 text-left text-[11.5px] leading-relaxed text-st-ecartee">
          <b>{rap.erreur === 'stockage' ? 'Archivage impossible' : 'Dépôt refusé'}</b> — {rap.motif || 'structure inattendue'}.
          {rap.erreur !== 'stockage' && <> La page doit être enregistrée en « page web complète » ;</>} rien n’a été enregistré.
        </div>
      )}
      {rap && rap.ok && (
        <div data-radar-depot-ok className="mt-3 rounded-lg border border-line-2 bg-surface-1 px-3 py-2.5 text-left text-[11.5px] text-txt">
          <b>{rap.nb_annonces} annonces lues</b> — {rap.nb_nouvelles} nouvelle{(rap.nb_nouvelles ?? 0) > 1 ? 's' : ''},
          {' '}{rap.nb_maj} mise{(rap.nb_maj ?? 0) > 1 ? 's' : ''} à jour
          {(rap.nb_a_qualifier ?? 0) > 0 && <>, <span className="text-st-attention">{rap.nb_a_qualifier} à qualifier</span></>}.
        </div>
      )}
    </section>
  )
}

// ── Bilan du DERNIER dépôt (persistant, table pige_depots) ──
function DernierDepot({ dep }: { dep: RadarCheck['dernier_depot'] }) {
  const L = ({ k, v }: { k: string; v: React.ReactNode }) => (
    <div className="flex items-center justify-between border-b border-line py-1.5 text-[12.5px] last:border-b-0">
      <span className="text-txt-mut">{k}</span><span className="font-mono text-txt">{v}</span>
    </div>
  )
  return (
    <Panel className="mb-0">
      <PHead>Dernier dépôt {dep?.date_depot ? <span className="ml-auto normal-case tracking-normal text-txt-mut">{fmtReu(dep.date_depot)}</span> : null}</PHead>
      <div className="px-4 py-2">
        {!dep ? <div className="py-4 text-center text-[12px] text-txt-dim">Aucun dépôt encore — déposez une page à gauche.</div> : (
          <>
            <L k="Annonces dans la page" v={dep.nb_annonces ?? '—'} />
            <L k="Nouvelles" v={dep.nb_nouvelles ?? '—'} />
            <L k="Mises à jour" v={dep.nb_maj ?? '—'} />
            <L k="À qualifier" v={dep.nb_a_qualifier ?? 0} />
          </>
        )}
      </div>
    </Panel>
  )
}

// ── RADAR-FIX-1 (3) — dernière capture AUTOMATIQUE de l'extension (pige_passes, jamais un dépôt manuel).
//    Rend visible que l'automate tourne ; en retard (> 26 h) → bandeau « Déposer Radar ». ──
function CaptureAuto({ cap, enRetard }: { cap: RadarCheck['capture_auto']; enRetard: boolean }) {
  return (
    <div data-radar-capture-auto
      className={`flex flex-wrap items-center gap-2 rounded-lg border px-3.5 py-2 text-[12px] ${enRetard ? 'border-st-attention/50 bg-st-attention/10' : 'border-line bg-surface-2'}`}>
      <span className="font-mono text-[10px] uppercase tracking-wider text-txt-dim">Dernière capture automatique</span>
      {cap?.captured_at
        ? <span className="text-txt">{fmtReu(cap.captured_at)} · <b className="font-medium">{cap.pages}</b> page{cap.pages > 1 ? 's' : ''} · {cap.nouvelles} nouvelle{cap.nouvelles > 1 ? 's' : ''}</span>
        : <span className="text-txt-mut">aucune capture automatique encore reçue de l’extension</span>}
      {enRetard && <span data-radar-capture-retard className="ml-auto font-medium text-st-attention">⚠ rien depuis plus de 26 h — Déposer Radar</span>}
    </div>
  )
}

// ── À valider : fiche pré-remplie, champs à vérifier en mauve, Valider ──
function Champ({ nom, valeur, aVerifier }: { nom: string; valeur: React.ReactNode; aVerifier: boolean }) {
  return (
    <div className={`rounded-md px-2 py-1 text-[12px] ${aVerifier ? 'border border-cp-ia/40 bg-cp-ia-bg/50 text-cp-ia' : 'text-txt'}`}>
      <span className="font-mono text-[9.5px] uppercase tracking-wider text-txt-dim">{nom}</span>{' '}
      <b className="font-medium">{valeur ?? '—'}</b>{aVerifier && <span className="ml-1 text-[9px]">à vérifier</span>}
    </div>
  )
}
function BrouillonCard({ b, onValide }: { b: RadarBrouillon; onValide: () => void }) {
  const av = new Set(b.a_verifier || [])
  return (
    <div className="rounded-lg border border-line-2 bg-surface-1 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[13px] font-medium text-txt-hi">{b.commune}</span>
        <Chip tone={NIV[b.rattachement_niveau]?.tone ?? 'off'}>{NIV[b.rattachement_niveau]?.label ?? '—'}</Chip>
        <span className="ml-auto font-mono text-[10px] text-txt-dim">{b.portail}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
        <Champ nom="prix" valeur={fmtEur(b.prix)} aVerifier={av.has('prix')} />
        <Champ nom="type" valeur={b.type_bien} aVerifier={av.has('type')} />
        <Champ nom="pièces" valeur={b.pieces} aVerifier={av.has('pieces')} />
        <Champ nom="surf. hab" valeur={b.surface_hab} aVerifier={av.has('surface_hab')} />
        <Champ nom="terrain" valeur={b.surface_terrain} aVerifier={av.has('surface_terrain')} />
        <Champ nom="DPE" valeur={b.dpe_classe} aVerifier={av.has('dpe_classe')} />
      </div>
      <div className="mt-2 flex items-center gap-2">
        <a href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          className="font-mono text-[10.5px] text-txt-dim underline decoration-dotted">voir la source ↗</a>
        <button onClick={onValide}
          className="ml-auto rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-on">Valider</button>
      </div>
    </div>
  )
}
function Extraction() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['radar-extraction'], queryFn: getRadarExtraction })
  const valider = async (id: number) => {
    await radarValider(id, {})
    qc.invalidateQueries({ queryKey: ['radar-extraction'] })
    qc.invalidateQueries({ queryKey: ['radar-reverif'] })
    qc.invalidateQueries({ queryKey: ['radar-check'] })
  }
  return (
    <div className="flex flex-col gap-2">
      {data?.n === 0 && <div className="py-3 text-center text-[12px] text-txt-dim">file d’extraction vidée ✓</div>}
      {data?.file.map((b) => <BrouillonCard key={b.bien_id} b={b} onValide={() => valider(b.bien_id)} />)}
    </div>
  )
}

// ── Re-vérification : groupée par commune, la plus ancienne d'abord ──
function joursDepuis(iso: string | null): number {
  if (!iso) return Number.POSITIVE_INFINITY
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
}
function LigneReverif({ r, onInval }: { r: RadarReverif; onInval: () => void }) {
  const [ratt, setRatt] = useState(false)
  const rattacher = () => {
    if (!r.piste_idu) return
    setRatt(true)
    radarRattacherHumain(r.bien_id, r.piste_idu).then(onInval).catch(() => setRatt(false))
  }
  return (
    <div className="flex flex-wrap items-center gap-2 py-2 text-[12px]">
      <span className="text-txt-mut">{fmtEur(r.prix)}</span>
      {r.non_rattachee && <Chip tone="warn">non rattachée</Chip>}
      {r.rattachable_forte && (
        <button data-radar-rattacher disabled={ratt} onClick={rattacher}
          className="rounded-md bg-mint px-2.5 py-1 text-[11px] font-medium text-mint-ink hover:brightness-110">
          {ratt ? 'Rattachement…' : 'Rattacher'}
        </button>
      )}
      {r.suivi_client && <Chip tone="ok">suivi client</Chip>}
      {r.proche_longue && <Chip tone="warn">≈ 90 j</Chip>}
      <a href={r.url_sortante} target="_blank" rel="noopener noreferrer"
        className="font-mono text-[10px] text-txt-dim underline decoration-dotted">source ↗</a>
      <span className="ml-auto flex gap-1.5">
        <button onClick={() => radarToujoursEnLigne(r.bien_id).then(onInval)}
          className="rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt hover:border-mint/40">Toujours en ligne</button>
        <button onClick={() => { const p = prompt('Nouveau prix (€) :'); if (p) radarPrix(r.bien_id, Number(p)).then(onInval) }}
          className="rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt">Prix modifié</button>
        <button onClick={() => radarRetiree(r.bien_id).then(onInval)}
          className="rounded-md border border-coral/30 px-2 py-1 text-[11px] text-coral">Retirée</button>
      </span>
    </div>
  )
}
function Reverif() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['radar-reverif'], queryFn: getRadarReverif })
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-reverif'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  const items = data?.file ?? []
  const parCommune = new Map<string, RadarReverif[]>()
  for (const r of items) { const arr = parCommune.get(r.commune) ?? []; arr.push(r); parCommune.set(r.commune, arr) }
  const groupes = [...parCommune.entries()].map(([commune, rows]) => {
    rows.sort((a, b) => Number(!!b.non_rattachee) - Number(!!a.non_rattachee)
      || joursDepuis(b.date_derniere_confirmation) - joursDepuis(a.date_derniere_confirmation))
    const nonRatt = rows.filter((r) => r.non_rattachee).length
    return { commune, rows, nonRatt, plusAncien: joursDepuis(rows[0].date_derniere_confirmation) }
  }).sort((a, b) => (b.nonRatt > 0 ? 1 : 0) - (a.nonRatt > 0 ? 1 : 0) || b.plusAncien - a.plusAncien)
  const ageLabel = (j: number) => (j === Number.POSITIVE_INFINITY ? 'jamais contrôlé' : `plus ancien contrôle : ${j} j`)
  return (
    <div className="flex flex-col gap-3">
      {items.length === 0 && <div className="py-3 text-center text-[12px] text-txt-dim">file de re-vérification vidée ✓</div>}
      {groupes.map((g) => (
        <div key={g.commune}>
          <div className="flex items-center gap-2 border-b border-line-2 pb-1 font-mono text-[10.5px] uppercase tracking-[0.1em] text-txt-dim">
            <span className="text-txt">{g.commune}</span> · {g.rows.length}
            {g.nonRatt > 0 && <span className="normal-case tracking-normal text-amber">· {g.nonRatt} à rattacher</span>}
            <span className="ml-auto normal-case tracking-normal">{ageLabel(g.plusAncien)}</span>
          </div>
          <div className="flex flex-col divide-y divide-line-2">
            {g.rows.map((r) => <LigneReverif key={r.bien_id} r={r} onInval={inval} />)}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── petite ligne « À faire » dépliable ──
function AFaire({ n, titre, phrase, ouvert, onToggle, children }: {
  n: number; titre: string; phrase?: string; ouvert: boolean; onToggle: () => void; children: React.ReactNode
}) {
  const actif = n > 0
  return (
    <div className={`rounded-lg border ${actif ? 'border-amber/40' : 'border-line'} bg-surface-2`}>
      <button onClick={() => actif && onToggle()} disabled={!actif}
        className={`grid w-full grid-cols-[44px_1fr_auto] items-center gap-3.5 px-3.5 py-2.5 text-left ${actif ? '' : 'cursor-default'}`}>
        <div className={`text-right font-mono text-[20px] font-medium ${actif ? 'text-amber' : 'text-txt-dim'}`}>{n}</div>
        <div className="text-[13.5px] text-txt">{titre}{phrase && <small className="block text-[12px] text-txt-mut">{phrase}</small>}</div>
        <span className={`text-[13px] ${actif ? 'text-mint' : 'text-txt-dim'}`}>{actif ? (ouvert ? 'replier' : 'traiter →') : '—'}</span>
      </button>
      {actif && ouvert && <div className="border-t border-line px-3.5 py-2.5">{children}</div>}
    </div>
  )
}

// DASHBOARD-4 (R1) — le bandeau descriptif « Faits extraits d'annonces publiques… » et son bouton
// « J'ai lu — replier » ont été retirés (bruit d'exploitation, jamais une action).

export function RadarSection() {
  const qc = useQueryClient()
  const check = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck, refetchInterval: 120_000 })
  const agence = useQuery({ queryKey: ['depot-agence-etat'], queryFn: getRadarDepotAgenceEtat })
  const togAgence = useMutation({
    mutationFn: (actif: boolean) => postRadarDepotAgenceToggle(actif),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['depot-agence-etat'] }),
  })
  const [ouvert, setOuvert] = useState<'valider' | 'reverifier' | null>(null)
  const onDepose = () => {
    qc.invalidateQueries({ queryKey: ['radar-extraction'] })
    qc.invalidateQueries({ queryKey: ['radar-check'] })
  }
  const d = check.data
  const flux = d?.flux
  const aValider = d?.file_extraction ?? 0
  const reverifDues = d?.reverif_dues ?? 0
  const reverifJour = d?.reverif_du_jour ?? 0
  const actifAgence = agence.data?.actif

  const KpiFlux = ({ n, sub, tone, onClick }: { n: React.ReactNode; sub: string; tone?: 'g'; onClick?: () => void; title?: string }) => (
    <button type="button" onClick={onClick} disabled={!onClick}
      className={`flex flex-col items-start rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-left ${onClick ? 'hover:border-line-2' : 'cursor-default'}`}>
      <div className={`text-[19px] font-bold ${tone === 'g' ? 'text-mint' : 'text-txt-hi'}`}>{n}</div>
      <div className="mt-0.5 text-[10.5px] text-txt-mut">{sub}</div>
    </button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Section 1 — dépôt du jour + bilan du dernier dépôt */}
      <div className="grid grid-cols-2 gap-3.5 max-[1100px]:grid-cols-1">
        <DepotHtml onDepose={onDepose} />
        <DernierDepot dep={d?.dernier_depot ?? null} />
      </div>

      {/* RADAR-FIX-1 (3) — l'automate tourne-t-il ? Dernière capture automatique + retard éventuel. */}
      <CaptureAuto cap={d?.capture_auto ?? null} enRetard={!!d?.capture_auto_en_retard} />

      {/* Section 2 — À faire (à valider · à re-vérifier), listes dépliables */}
      <div>
        <h2 className="mb-2 mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-txt-dim">À faire</h2>
        <div className="flex flex-col gap-1.5">
          {d?.capture_auto_en_retard && (
            <div data-radar-deposer-afaire className="flex items-center gap-2 rounded-lg border border-st-attention/50 bg-st-attention/10 px-3.5 py-2.5 text-[12.5px] text-st-attention">
              <b className="font-medium">Déposer Radar</b>
              <span className="text-txt-mut">— aucune capture automatique depuis plus de 26 h (Mac éteint ou extension bloquée) : déposer la page du jour à la main ci-dessus (⌘S).</span>
            </div>
          )}
          <AFaire n={aValider} titre="annonces à valider (extraction)"
            ouvert={ouvert === 'valider'} onToggle={() => setOuvert((o) => o === 'valider' ? null : 'valider')}>
            <Extraction />
          </AFaire>
          <AFaire n={reverifDues} titre="liens à re-vérifier aujourd’hui"
            phrase={reverifDues === 0 ? 'rien à re-vérifier — prochaine vague plus tard' : undefined}
            ouvert={ouvert === 'reverifier'} onToggle={() => setOuvert((o) => o === 'reverifier' ? null : 'reverifier')}>
            <Reverif />
          </AFaire>
        </div>
      </div>

      {/* Section 3 — Le flux */}
      <div>
        <h2 className="mb-2 mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-txt-dim">Le flux</h2>
        <div className="grid grid-cols-5 gap-2 max-[1100px]:grid-cols-2">
          <KpiFlux n={flux?.en_vie ?? '—'} sub="annonces en vie" tone="g" />
          <KpiFlux n={flux ? `${flux.rattachees} / ${flux.biens}` : '—'} sub="rattachées à une parcelle" />
          <KpiFlux n={flux?.copros_non_servies ?? '—'} sub="copropriétés non servies" title="Collectées mais jamais servies au client (est_copro)" />
          <KpiFlux n={flux?.paires ?? '—'} sub="paires DVF (vendue)" />
          <KpiFlux n={actifAgence == null ? '—' : actifAgence ? 'ouvert' : 'fermé'} sub="dépôt agence"
            onClick={() => { if (actifAgence === undefined) return; if (window.confirm(actifAgence
              ? 'Fermer le dépôt agence ? Les clients ne verront plus le parcours ni les dépôts agence.'
              : 'Ouvrir le dépôt agence aux clients ? (question Hoguet — n’ouvrir qu’avec l’accord avocat.)')) togAgence.mutate(!actifAgence) }}
            title="Drapeau « Publier une annonce » (parcours agence), lu en base — cliquer pour ouvrir/fermer" />
        </div>
        <p className="mt-2 text-[11px] text-txt-mut">
          <b className="text-txt">{reverifJour}</b> vérifiée{reverifJour > 1 ? 's' : ''} aujourd’hui ·
          un seul compteur « en vie », le même qu’au Pilotage. Le chemin par captures d’écran est retiré.
        </p>
      </div>
    </div>
  )
}
