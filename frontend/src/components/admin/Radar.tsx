// RADAR (pige) · P1 V3 — page admin « Radar », pensée MOBILE (Vic saisit depuis son téléphone).
// Quatre zones : Saisie du jour · File d'extraction · Re-vérification (2 niveaux) · Check quotidien.
// Doctrine : on n'affiche JAMAIS l'annonce (ni photo, ni titre, ni texte) — des FAITS + le lien
// sortant. Le mauve est réservé aux champs IA « à vérifier » (sous le seuil de confiance).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getRadarAInstruire, getRadarCheck, getRadarDepotAgenceEtat, getRadarExtraction, getRadarReverif,
  postRadarDepotAgenceToggle, radarDeposer, radarDeposerHtml,
  radarInstruire, radarPrix, radarRattacherHumain, radarRetiree, radarToujoursEnLigne, radarValider,
  type RadarAInstruire, type RadarBrouillon, type RadarCritere, type RadarDepotHtml, type RadarPiste, type RadarReverif,
} from '../../lib/api'
import { Declaratif } from '../outils/RadarDeclaratif'
import { Lbl, Chip } from './AdminView'

const NIV: Record<string, { label: string; tone: 'ok' | 'warn' | 'off' }> = {
  source: { label: 'Sourcé', tone: 'ok' }, estime: { label: 'Estimé', tone: 'warn' },
  absent: { label: 'Non rattachée', tone: 'off' },
}
const fmtEur = (v: number | null) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')

async function fileToB64(f: File): Promise<string> {
  const buf = await f.arrayBuffer()
  let s = ''
  const b = new Uint8Array(buf)
  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i])
  return btoa(s)
}

// ── Zone 0 — RADAR-HTML (Lot 1) : DÉPÔT D'UNE PAGE DE RÉSULTATS (remplace la capture + vision) ──
// Vic enregistre la page de résultats du portail (Cmd+S, « page web complète ») et la dépose ici. Le
// serveur parse le bloc structuré __NEXT_DATA__ : idempotent par annonce (re-dépôt = MAJ, jamais
// doublon), échec BRUYANT si la structure a changé. Aucune requête portail — on lit un fichier déposé.
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
    <section className="rounded-xl border border-mint/40 bg-mint/5 p-4">
      <div className="mb-1 flex items-center gap-2">
        <Lbl>Dépôt du jour — page de résultats (HTML)</Lbl>
        <Chip tone="ok">nouveau</Chip>
      </div>
      <p className="mb-3 text-[11.5px] leading-relaxed text-txt-mut">
        Enregistrer la page de résultats du portail (<b>⌘S → « page web complète »</b>), puis la déposer.
        Toutes les annonces de la page sont lues d’un coup ; re-déposer la même page ne crée aucun doublon.
      </p>
      <label className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border border-mint/50 bg-mint/10 px-3 py-2 text-[12px] font-medium text-mint hover:bg-mint/20 ${busy ? 'pointer-events-none opacity-60' : ''}`}>
        <input data-radar-depot-html type="file" accept=".html,.htm,text/html" className="hidden"
               onChange={(e) => deposer(e.target.files)} />
        {busy ? 'Lecture de la page…' : '+ Déposer une page de résultats (.html)'}
      </label>
      {rap && !rap.ok && (
        <div data-radar-depot-erreur className="mt-3 rounded-lg border border-st-ecartee/50 bg-st-ecartee/10 px-3 py-2 text-[11.5px] leading-relaxed text-st-ecartee">
          {/* RADAR-RECETTE-1 D4 — un échec d'ÉCRITURE disque se dit comme tel (chemin nommé par le
              serveur), jamais « réseau ou serveur ». Le conseil « page web complète » ne vaut que pour
              une structure illisible (next_data). */}
          <b>{rap.erreur === 'stockage' ? 'Archivage impossible' : 'Dépôt refusé'}</b> — {rap.motif || 'structure inattendue'}.
          {rap.erreur !== 'stockage' && <> La page doit être enregistrée en « page web complète » ;</>} rien n’a été enregistré.
        </div>
      )}
      {rap && rap.ok && (
        <div data-radar-depot-ok className="mt-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-[11.5px] text-txt">
          <b>{rap.nb_annonces} annonces lues</b> — {rap.nb_nouvelles} nouvelle{(rap.nb_nouvelles ?? 0) > 1 ? 's' : ''},
          {' '}{rap.nb_maj} mise{(rap.nb_maj ?? 0) > 1 ? 's' : ''} à jour
          {(rap.nb_a_qualifier ?? 0) > 0 && <>, <span className="text-st-attention">{rap.nb_a_qualifier} à qualifier</span></>}
          {(rap.nb_hors_perimetre ?? 0) > 0 && <>, {rap.nb_hors_perimetre} hors périmètre</>}.
          {rap.etats && (
            <div className="mt-1 flex flex-wrap gap-1.5 text-[10.5px] text-txt-mut">
              <span>rattachement :</span>
              {Object.entries(rap.etats).map(([k, v]) => (
                <span key={k} className="rounded bg-surface-3 px-1.5 py-0.5">{k.replace('_', ' ')} {v}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}

// ── Zone 1 — Saisie du jour : dropzone + un lien par capture (chemin HISTORIQUE, remplacé par le HTML) ──
// RETOURS-1 R7 (Vic) — le dépôt doit marcher POUR DE VRAI : label visible au-dessus du champ lien
// (plus un placeholder gris seul), focus automatique dès qu'une capture est ajoutée, bordure
// d'erreur + message clair si Déposer sans lien, bouton qui réagit (« Dépôt… »), et un échec
// réseau/serveur qui S'AFFICHE (l'ancien code ne catchait pas → validation muette).
function Saisie({ onDepose }: { onDepose: () => void }) {
  const [lignes, setLignes] = useState<{ file: File; lien: string; retour?: string; erreur?: boolean }[]>([])
  const [busyIdx, setBusyIdx] = useState<number | null>(null)
  const ajouter = (files: FileList | null) => {
    if (!files) return
    setLignes((l) => [...l, ...Array.from(files).map((file) => ({ file, lien: '' }))])
  }
  const deposer = async (i: number) => {
    const ln = lignes[i]
    if (!ln.lien.trim()) {
      maj(i, { retour: 'Collez le lien de l’annonce — il est obligatoire pour déposer.', erreur: true })
      return
    }
    setBusyIdx(i)
    try {
      const b64 = await fileToB64(ln.file)
      const r = await radarDeposer(ln.lien.trim(), b64, ln.file.type || 'image/jpeg')
      const ok = r.statut === 'a_valider'
      const retour = ok ? '✓ en file d’extraction'
        : r.statut === 'doublon_url' ? `déjà connue (bien #${r.bien_id}) — mise à jour du prix proposée`
        : r.statut === 'rejet_commune' ? `rejet : ${r.motif}`
        : `échec : ${r.motif ?? 'extraction'}`
      maj(i, { retour, erreur: !ok && r.statut !== 'doublon_url' })
      onDepose()
    } catch {
      // échec réseau/serveur : il DOIT se voir (avant : promesse rejetée en silence)
      maj(i, { retour: 'Échec réseau ou serveur — rien n’a été déposé, réessayez.', erreur: true })
    } finally { setBusyIdx(null) }
  }
  const maj = (i: number, patch: Partial<{ lien: string; retour: string; erreur: boolean }>) =>
    setLignes((l) => l.map((x, k) => (k === i ? { ...x, ...patch } : x)))

  return (
    <section className="rounded-xl border border-line-2 bg-surface-2 p-4">
      <Lbl>1 · Saisie du jour</Lbl>
      <label className="flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-line-3 px-4 py-6 text-sm text-txt-mut hover:border-mint/40">
        <input data-radar-fichier type="file" accept="image/*" multiple className="hidden"
          onChange={(e) => ajouter(e.target.files)} />
        + Ajouter des captures (galerie)
      </label>
      <div className="mt-3 flex flex-col gap-2">
        {lignes.map((ln, i) => (
          <div key={i} data-radar-ligne className="rounded-lg border border-line-2 bg-surface-1 p-2.5">
            <div className="mb-1 truncate font-mono text-[11px] text-txt-dim">{ln.file.name}</div>
            <label className="label-caps mb-1 block text-[9.5px] text-txt-mut">Lien de l’annonce *</label>
            <div className="flex flex-col gap-1.5 sm:flex-row">
              <input data-radar-lien value={ln.lien}
                autoFocus={i === lignes.length - 1}
                onChange={(e) => maj(i, { lien: e.target.value, erreur: false })}
                placeholder="https://www.leboncoin.fr/…"
                aria-invalid={ln.erreur || undefined}
                className={`min-w-0 flex-1 rounded-md border bg-surface-2 px-2 py-1.5 text-[12px] text-txt focus:outline-none ${
                  ln.erreur ? 'border-st-ecartee' : 'border-line-2 focus:border-mint'}`} />
              <button data-radar-deposer disabled={busyIdx != null} onClick={() => deposer(i)}
                className="rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-50">
                {busyIdx === i ? 'Dépôt…' : 'Déposer'}
              </button>
            </div>
            {ln.retour && (
              <div data-radar-retour className={`mt-1 text-[11px] ${
                ln.erreur ? 'text-st-ecartee' : ln.retour.startsWith('✓') ? 'text-mint' : 'text-txt-mut'}`}>
                {ln.retour}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

// ── Zone 2 — File d'extraction : fiche pré-remplie, champs à vérifier en mauve, Valider ──
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
    <div>
      {data?.n === 0 && <div className="py-4 text-center text-[12px] text-txt-dim">file vidée ✓</div>}
      <div className="flex flex-col gap-2">
        {data?.file.map((b) => <BrouillonCard key={b.bien_id} b={b} onValide={() => valider(b.bien_id)} />)}
      </div>
    </div>
  )
}

// ── Zone 3 — Re-vérification (ADMIN-1 AD9) : GROUPÉE PAR COMMUNE, la plus ancienne d'abord ──
// Boutons par ligne INCHANGÉS (Toujours en ligne / Prix modifié / Retirée) — aucune mécanique réécrite.
// Compteur « N vérifiées aujourd'hui » = RadarCheck.reverif_du_jour (chiffre réel, jamais fabriqué).
function joursDepuis(iso: string | null): number {
  if (!iso) return Number.POSITIVE_INFINITY   // jamais contrôlée = la plus ancienne
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
}
// S5 — le back expose `non_rattachee` (idu IS NULL) pour trier « à rattacher d'abord » + chip.
function LigneReverif({ r, onInval }: { r: RadarReverif & { non_rattachee?: boolean }; onInval: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2 text-[12px]">
      <span className="text-txt-mut">{fmtEur(r.prix)}</span>
      {r.non_rattachee && <Chip tone="warn">non rattachée</Chip>}
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
  const check = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck })
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-reverif'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  const items = (data?.file ?? []) as (RadarReverif & { non_rattachee?: boolean })[]
  // regroupement par commune, chaque item porte son ancienneté ; on garde le plus ancien contrôle du groupe.
  const parCommune = new Map<string, (RadarReverif & { non_rattachee?: boolean })[]>()
  for (const r of items) {
    const arr = parCommune.get(r.commune) ?? []
    arr.push(r)
    parCommune.set(r.commune, arr)
  }
  const groupes = [...parCommune.entries()].map(([commune, rows]) => {
    // S5 — dans chaque commune, les NON RATTACHÉES d'abord (« à rattacher d'abord »), puis le plus ancien contrôle.
    rows.sort((a, b) => Number(!!b.non_rattachee) - Number(!!a.non_rattachee)
      || joursDepuis(b.date_derniere_confirmation) - joursDepuis(a.date_derniere_confirmation))
    const nonRatt = rows.filter((r) => r.non_rattachee).length
    return { commune, rows, nonRatt, plusAncien: joursDepuis(rows[0].date_derniere_confirmation) }
  }).sort((a, b) => (b.nonRatt > 0 ? 1 : 0) - (a.nonRatt > 0 ? 1 : 0)   // communes avec des non rattachées en tête
    || b.plusAncien - a.plusAncien)
  const ageLabel = (j: number) => (j === Number.POSITIVE_INFINITY ? 'jamais contrôlé' : `plus ancien contrôle : ${j} j`)
  return (
    <div>
      {items.length === 0 && <div className="py-4 text-center text-[12px] text-txt-dim">file de re-vérification vidée ✓</div>}
      <div className="flex flex-col gap-3">
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
      <div className="mt-3 border-t border-line-2 pt-2 text-[11px] text-txt-mut">
        {items.length} annonce{items.length > 1 ? 's' : ''} à re-vérifier · <b className="text-txt">{check.data?.reverif_du_jour ?? 0}</b> vérifiée{(check.data?.reverif_du_jour ?? 0) > 1 ? 's' : ''} aujourd’hui
      </div>
    </div>
  )
}

// ── Zone 3bis — INSTRUCTION (D3, ADMIN SEULEMENT) : rattacher un bien en piste via l'ortho ──
// RADAR-DEPOT-2 D3 — le rattachement humain est un geste ADMIN (un rattachement client erroné serait
// servi à tous). On relance la cascade à la demande, on compare les toits (ortho BD ORTHO 20 cm) avec
// les critères ✓/✗, la zone DÉCLARÉE aide à trancher, puis « C'est cette parcelle » (fait foi).
function InstructionCard({ b, onTranche }: { b: RadarAInstruire; onTranche: () => void }) {
  const [instr, setInstr] = useState<{ busy: boolean; ouvert: boolean; cands?: RadarPiste[]; motif?: string | null }>({ busy: false, ouvert: false })
  const [choix, setChoix] = useState<{ busy: boolean; idu?: string }>({ busy: false })
  const [idx, setIdx] = useState(0)   // RETOURS-9 (Q7) — candidate courante (« Suivante » fait défiler)
  const specs = b.type_bien === 'terrain'
    ? (b.surface_terrain ? `${b.surface_terrain} m² terrain` : '')
    : (b.surface_hab ? `${b.surface_hab} m² hab` : '')
  const instruire = () => {
    if (instr.ouvert) { setInstr((s) => ({ ...s, ouvert: false })); return }
    setInstr({ busy: true, ouvert: true })
    radarInstruire(b.bien_id)
      .then((r) => setInstr({ busy: false, ouvert: true, cands: r.candidates, motif: r.motif }))
      .catch(() => setInstr({ busy: false, ouvert: true, motif: 'échec — réessayer' }))
  }
  // RETOURS-8 (R5) — confiance FORTE = adresse BAN exacte ou position (rattachement à 1 clic sur la
  // 1re candidate) ; FAIBLE = surface seule (±10 %) → passer par l'Instruction (ortho). Le POURQUOI
  // vient des critères convergents déjà calculés (rattachement_criteres), jamais recalculé au front.
  const forte = b.confiance === 'forte' && !!b.premiere_piste?.idu
  const pourquoi = (b.rattachement_criteres ?? []).filter((c) => c.converge !== false)
    .map((c) => `${c.critere} ${c.valeur}`).join(' · ')
  const rattacher1clic = () => {
    const idu = b.premiere_piste?.idu
    if (!idu) return
    setChoix({ busy: true, idu })
    radarRattacherHumain(b.bien_id, idu).then(() => { setChoix({ busy: false }); onTranche() })
      .catch(() => setChoix({ busy: false }))
  }
  return (
    <div data-radar-instruction className="rounded-lg border border-line-2 bg-surface-1 p-3">
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        <span className="font-medium text-txt-hi">{b.commune}</span>
        <span className="text-txt-mut">{(b.type_bien ?? '—')}{specs ? ` · ${specs}` : ''}</span>
        <span className="text-txt-mut">{fmtEur(b.prix)}</span>
        {/* RETOURS-8 (R5) — badge CONFIANCE (forte = vert · faible = ambre) + nb candidates. */}
        <Chip tone={forte ? 'ok' : 'warn'} data-radar-confiance={b.confiance}>
          {b.n_candidates} candidate{b.n_candidates > 1 ? 's' : ''} · confiance {b.confiance}
        </Chip>
        {b.url_sortante && <a href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          className="font-mono text-[10px] text-txt-dim underline decoration-dotted">source ↗</a>}
        <span className="ml-auto flex items-center gap-1.5">
          {/* forte → Rattacher en UN clic (humain, toujours) sur la 1re candidate. */}
          {forte && (
            <button data-radar-rattacher disabled={choix.busy} onClick={rattacher1clic}
              className="rounded-md bg-mint px-2.5 py-1 text-[11.5px] font-medium text-mint-on hover:brightness-110 disabled:opacity-60">
              {choix.busy ? 'Rattachement…' : 'Rattacher'}
            </button>
          )}
          <button data-radar-instruire onClick={instruire}
            className="rounded-md border border-amber/50 bg-amber/10 px-2.5 py-1 text-[11.5px] font-medium text-amber hover:bg-amber/20">
            {instr.busy ? 'Instruction…' : instr.ouvert ? 'Fermer' : 'Instruire'}
          </button>
        </span>
      </div>
      {/* RETOURS-8 (R5) — le POURQUOI de la proposition, en clair (critères convergents). */}
      {pourquoi && <div data-radar-pourquoi className="mt-1.5 text-[11px] leading-snug text-txt-mut">{pourquoi}</div>}
      {/* la zone DÉCLARÉE (page d'annonce) aide à trier les candidates — déclaratif vendeur. */}
      {b.declaratif && <div className="mt-2"><Declaratif d={b.declaratif} /></div>}
      {/* RETOURS-9 (Q7) — écran INSTRUIRE : l'annonce et la candidate CÔTE À CÔTE, une ligne
          « ce qui concorde / ce qui diverge », puis la décision (Rattacher · Suivante · Aucune).
          Aucun calcul neuf : les faits candidate viennent de la fiche parcelle. */}
      {instr.ouvert && instr.cands && (() => {
        if (instr.cands.length === 0) return <div className="mt-2.5 text-[11px] text-txt-dim">{instr.motif || 'aucune candidate exploitable'}</div>
        const c = instr.cands[Math.min(idx, instr.cands.length - 1)]
        const fi = c.fiche
        const m2 = (v?: number | null) => v != null ? `${v.toLocaleString('fr-FR')} m²` : '—'
        const rattacher = () => { setChoix({ busy: true, idu: c.idu }); radarRattacherHumain(b.bien_id, c.idu)
          .then(() => { setChoix({ busy: false }); onTranche() }).catch(() => setChoix({ busy: false })) }
        return (
          <div data-radar-instruire-ecran className="mt-2.5">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {/* ANNONCE */}
              <div data-radar-annonce className="rounded-xl border border-line-2 bg-surface-2 p-2.5">
                <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.14em] text-txt-dim">Annonce</div>
                <Fait k="Type" v={b.type_bien ?? '—'} />
                <Fait k="Surface habitable" v={m2(b.surface_hab)} />
                <Fait k="Surface terrain" v={m2(b.surface_terrain)} />
                <Fait k="Prix" v={fmtEur(b.prix)} />
                <Fait k="Quartier / commune" v={b.commune} />
                {b.url_sortante && <a href={b.url_sortante} target="_blank" rel="noopener noreferrer"
                  className="mt-1 inline-block font-mono text-[10px] text-mint underline decoration-dotted">voir l'annonce (photos) ↗</a>}
              </div>
              {/* CANDIDATE */}
              <div data-radar-candidate data-radar-candidate-idu={c.idu} className="rounded-xl border border-line-2 bg-surface-2 p-2.5">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-txt-dim">Candidate {instr.cands.length > 1 ? `${Math.min(idx, instr.cands.length - 1) + 1}/${instr.cands.length}` : ''}</span>
                  {c.distance_m != null && <span className="text-[10px] text-txt-dim">{Math.round(c.distance_m)} m du point</span>}
                </div>
                <div className="mb-1.5 grid grid-cols-[64px_1fr] gap-2">
                  {c.ortho_url
                    ? <img src={c.ortho_url} alt={`ortho ${c.idu}`} className="h-16 w-16 rounded object-cover" loading="lazy" />
                    : <div className="flex h-16 w-16 items-center justify-center rounded bg-surface-3 text-[9px] text-txt-dim">ortho indispo.</div>}
                  <span className="self-center font-mono text-[11px] text-txt">{c.idu}</span>
                </div>
                <Fait k="Surface cadastrale" v={m2(fi?.surface_cadastrale)} />
                <Fait k="Surface bâtie (BD TOPO)" v={m2(fi?.surface_bati)} />
                <Fait k="Bâtiments" v={fi?.n_batiments != null ? String(fi.n_batiments) : '—'} />
                <Fait k="Zone PLU" v={fi?.zone_plu ?? '—'} />
                <Fait k="Adresse BAN" v={fi?.adresse_ban ?? '—'} />
              </div>
            </div>

            {/* concordance / divergence — les critères déjà calculés, en clair */}
            <div data-radar-concordance className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-0.5 rounded-lg border border-line bg-surface-1 px-2.5 py-1.5 text-[10.5px]">
              <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-txt-dim">Concorde / diverge</span>
              {(c.criteres_detail ?? []).map((x: RadarCritere, i: number) => (
                <span key={i} className={x.converge ? 'text-mint' : 'text-coral'}>
                  {x.converge ? '✓' : '✗'} <span className="text-txt-mut">{x.critere}</span> {x.valeur}
                </span>
              ))}
              {(c.criteres_detail ?? []).length === 0 && <span className="text-txt-dim">critères non disponibles</span>}
              <span className="ml-auto"><Chip tone={b.confiance === 'forte' ? 'ok' : 'warn'}>confiance {b.confiance}</Chip></span>
            </div>

            {/* décision : Rattacher · Suivante · Aucune */}
            <div className="mt-2 flex items-center gap-1.5">
              <button data-radar-choisir disabled={choix.busy} onClick={rattacher}
                className="rounded-md bg-mint px-3 py-1 text-[11.5px] font-medium text-mint-on hover:brightness-110 disabled:opacity-60">
                {choix.busy && choix.idu === c.idu ? 'Enregistrement…' : 'Rattacher'}
              </button>
              {instr.cands.length > 1 && (
                <button data-radar-suivante onClick={() => setIdx((i) => (i + 1) % instr.cands!.length)}
                  className="rounded-md border border-line-2 px-3 py-1 text-[11.5px] text-txt-mut hover:text-txt">
                  Suivante
                </button>
              )}
              <button data-radar-aucune onClick={() => setInstr((s) => ({ ...s, ouvert: false }))}
                className="rounded-md border border-line-2 px-3 py-1 text-[11.5px] text-txt-mut hover:text-txt">
                Aucune
              </button>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

// RETOURS-9 (Q7) — une ligne « clé : valeur » compacte pour les colonnes annonce/candidate.
function Fait({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-px text-[11px]">
      <span className="shrink-0 text-txt-dim">{k}</span>
      <span className={`text-right ${v === '—' ? 'text-txt-mut' : 'text-txt'}`}>{v}</span>
    </div>
  )
}

function Instruction() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['radar-a-instruire'], queryFn: getRadarAInstruire })
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-a-instruire'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  return (
    <section className="rounded-xl border border-line-2 bg-surface-2 p-4">
      <Lbl>3bis · Instruction <span className="text-txt-dim">— {data?.n ?? 0} en piste · admin</span></Lbl>
      <p className="mb-2 text-[11px] leading-relaxed text-txt-mut">
        Le rattachement d’une parcelle est un geste d’admin : le client ne rattache jamais. Comparez les
        toits (ortho) avec les critères, puis tranchez — ce choix fait foi.
      </p>
      {data?.n === 0 && <div className="py-4 text-center text-[12px] text-txt-dim">aucun bien en piste ✓</div>}
      <div className="flex flex-col gap-2">
        {data?.file.map((b) => <InstructionCard key={b.bien_id} b={b} onTranche={inval} />)}
      </div>
    </section>
  )
}

// ── Zone 4 — Arbre de check quotidien (le rituel ≤ 15 min) ──
function Check() {
  const { data } = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck })
  const item = (ok: boolean, txt: string) => (
    <div className="flex items-center gap-2 py-1 text-[12.5px] text-txt">
      <span className={ok ? 'text-mint' : 'text-txt-dim'}>{ok ? '✓' : '○'}</span>{txt}
    </div>
  )
  return (
    <section className="rounded-xl border border-line-2 bg-surface-2 p-4">
      <Lbl>4 · Check quotidien <span className="text-txt-dim">— cible ≤ {data?.cible_minutes ?? 15} min</span></Lbl>
      {item((data?.file_extraction ?? 1) === 0, 'file d’extraction vidée')}
      {item((data?.signalements_en_attente ?? 0) === 0, 'signalements clients traités')}
      {item(!data?.intake_vide_48h, 'saisie récente (< 48 h)')}
      <div className="mt-2 flex flex-wrap gap-2 border-t border-line-2 pt-2 text-[11px] text-txt-mut">
        <Chip>nouveautés {data?.compteurs.nouveautes ?? 0}</Chip>
        <Chip>en vente longue {data?.compteurs.en_vente_longue ?? 0}</Chip>
        <Chip tone={((data?.compteurs.baisses ?? 0) > 0) ? 'warn' : 'off'}>baisses {data?.compteurs.baisses ?? 0}</Chip>
      </div>
      {data?.intake_vide_48h && (
        <div className="mt-2 rounded-md border border-amber/30 bg-amber/5 px-3 py-2 text-[11.5px] text-amber">
          Aucune saisie depuis 48 h — un petit tour sur les portails quand vous avez cinq minutes.
        </div>
      )}
    </section>
  )
}

// ADMIN-1 (AD9) — les signalements clients sont désormais servis par la page PRODUIT (table
// signalements unifiée, filtres compte/statut) : retirés d'ici pour éviter le doublon. La mécanique
// (getAdminSignalements / postAdminSignalementStatut) est inchangée, seul l'emplacement change.

// RV2-V1 — bandeau d'alerte EN TÊTE : si le répertoire de captures n'est pas accessible en écriture,
// le dépôt échouera. On le dit AVANT le premier dépôt, avec le chemin fautif nommé (pas de crash).
function CapturesAlerte() {
  const { data } = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck })
  if (data == null || data.captures_dir_ok) return null
  return (
    <div data-radar-captures-alerte className="rounded-xl border border-st-ecartee/50 bg-st-ecartee/10 px-4 py-3 text-[12px] leading-relaxed text-st-ecartee">
      <b>Dépôt de captures indisponible</b> — le répertoire privé n’est pas accessible en écriture :
      <div className="mt-1 break-all font-mono text-[11px] text-txt">{data.captures_dir}</div>
      <div className="mt-1 text-txt-mut">Un dépôt échouera tant que ce n’est pas corrigé. Créer le
        répertoire et donner les droits à l’utilisateur de l’app (procédure : docs/PIGE/EXPLOITATION.md § captures).</div>
    </div>
  )
}

// CONNEXIONS-2 Lot 7.1 (N2) — TOGGLE « dépôt agence » : le drapeau (parcours « Publier une annonce »)
// se règle ICI, plus dans l'env. Bascule → visible immédiatement (réglage base relu à chaud). Défaut = fermé.
function DepotAgenceToggle() {
  const qc = useQueryClient()
  const etat = useQuery({ queryKey: ['depot-agence-etat'], queryFn: getRadarDepotAgenceEtat })
  const tog = useMutation({
    mutationFn: (actif: boolean) => postRadarDepotAgenceToggle(actif),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['depot-agence-etat'] }) },
  })
  const actif = etat.data?.actif
  return (
    <section className="flex flex-wrap items-center gap-3 rounded-xl border border-line-2 bg-surface-2/50 px-4 py-3">
      <Lbl>Dépôt agence — « Publier une annonce »</Lbl>
      <Chip tone={actif ? 'ok' : 'off'}>{actif ? 'ouvert' : 'fermé'}</Chip>
      <button data-depot-toggle disabled={tog.isPending || actif === undefined}
        onClick={() => { if (window.confirm(actif
          ? 'Fermer le dépôt agence ? Les clients ne verront plus le parcours ni les dépôts agence.'
          : 'Ouvrir le dépôt agence aux clients ? (question Hoguet — n’ouvrir qu’avec l’accord avocat.)')) tog.mutate(!actif) }}
        className="ml-auto rounded-md border border-line-2 px-2.5 py-1 text-[11.5px] text-txt-dim hover:border-mint hover:text-mint">
        {actif ? 'Fermer' : 'Ouvrir'}
      </button>
    </section>
  )
}

// ── ADMIN-1 (AD9) — bandeau descriptif qui se replie après première lecture (état mémorisé) ──
function Bandeau() {
  const [lu, setLu] = useState(() => { try { return localStorage.getItem('radar-bandeau-lu') === '1' } catch { return false } })
  if (lu) return (
    <button onClick={() => setLu(false)} className="self-start text-[11px] text-txt-dim hover:text-txt">ⓘ à propos du Radar</button>
  )
  const replier = () => { try { localStorage.setItem('radar-bandeau-lu', '1') } catch { /* localStorage indispo */ } ; setLu(true) }
  return (
    <div className="rounded-xl border border-line-2 bg-surface-2/50 px-4 py-3 text-[12.5px] leading-relaxed text-txt-mut">
      <p>Faits extraits d’annonces publiques + lien vers la source. Aucune photo ni texte d’annonce n’est
        stocké ni affiché — les pages déposées restent des documents de travail privés.</p>
      <button onClick={replier} className="mt-2 text-[11px] text-mint hover:underline">J’ai lu — replier</button>
    </div>
  )
}

// RETOURS-8 (R5) — le panneau « Déposer » (dépôt HTML + toggle agence + saisie historique repliée).
function DeposerPanel() {
  const qc = useQueryClient()
  const onDepose = () => {
    qc.invalidateQueries({ queryKey: ['radar-extraction'] })
    qc.invalidateQueries({ queryKey: ['radar-check'] })
  }
  return (
    <div className="flex flex-col gap-3">
      <DepotAgenceToggle />
      <DepotHtml onDepose={onDepose} />
      {/* SECTEUR-2b (U2) — chemin de capture HISTORIQUE (remplacé par le dépôt HTML), replié. */}
      <details className="rounded-xl border border-line-2 bg-surface-2/50">
        <summary className="cursor-pointer px-4 py-2 text-[11.5px] text-txt-dim">
          Saisie par capture d’écran (chemin historique — remplacé par le dépôt HTML)
        </summary>
        <div className="p-3 pt-0">
          <CapturesAlerte />
          <Saisie onDepose={onDepose} />
        </div>
      </details>
    </div>
  )
}

// RETOURS-8 (R5) — la pige EN ONGLETS (maquette section 1) : 4 chiffres en tête disent où en est la
// pige, puis un onglet par tâche (on n'empile plus, on ne descend plus). L'onglet ouvert par défaut est
// le PREMIER qui a du travail. Le dépôt HTML est un onglet comme les autres.
type RadarTab = 'deposer' | 'valider' | 'rattacher' | 'reverifier' | 'check'

export function RadarSection() {
  const check = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck })
  const d = check.data
  const enVie = d?.annonces_en_vie ?? 0
  const aRattacher = d?.a_rattacher ?? 0
  const aValider = d?.file_extraction ?? 0
  const reverifDues = d?.reverif_dues ?? 0
  const reverifJour = d?.reverif_du_jour ?? 0
  // onglet par défaut = le premier qui a du travail (À valider → À rattacher → Re-vérifier → Déposer).
  const defaut: RadarTab = aValider > 0 ? 'valider' : aRattacher > 0 ? 'rattacher'
    : reverifDues > 0 ? 'reverifier' : 'deposer'
  const [tab, setTab] = useState<RadarTab | null>(null)
  const actif = tab ?? defaut

  const Kpi = ({ n, sub, tone }: { n: React.ReactNode; sub: string; tone?: 'a' | 'g' }) => (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
      <div className={`text-[17px] font-bold ${tone === 'a' ? 'text-amber' : tone === 'g' ? 'text-mint' : 'text-txt-hi'}`}>{n}</div>
      <div className="text-[10.5px] text-txt-mut">{sub}</div>
    </div>
  )
  // RETOURS-9 (Q9) — onglet Radar ACTIF = plein vert, encre sombre (pas un simple soulignement).
  const Onglet = ({ k, children, n, tone }: { k: RadarTab; children: React.ReactNode; n?: number; tone?: 'a' }) => (
    <button data-radar-onglet={k} onClick={() => setTab(k)} aria-pressed={actif === k}
      className={`mb-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] transition-colors duration-quick ${
        actif === k ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
      {children}{n != null && <b className={`ml-1 ${actif === k ? 'text-mint-ink' : n > 0 && tone === 'a' ? 'text-amber' : 'text-txt-dim'}`}>{n}</b>}
    </button>
  )
  return (
    <div className="flex flex-col gap-4">
      <Bandeau />
      {/* 4 chiffres en tête (maquette) : annonces en vie · à rattacher · à valider · re-vérifiées/dues. */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Kpi n={enVie} sub="annonces en vie" />
        <Kpi n={aRattacher} sub="à rattacher à une parcelle" tone="a" />
        <Kpi n={aValider} sub="à valider (file d’extraction)" tone="g" />
        <Kpi n={<>{reverifJour} <span className="text-[11px] text-txt-dim">/ {reverifDues} dues</span></>} sub="re-vérifiées aujourd’hui" />
      </div>
      {/* les onglets : une tâche = un onglet, on n'empile plus. */}
      <div className="flex gap-5 overflow-x-auto border-b border-line">
        <Onglet k="deposer">Déposer</Onglet>
        <Onglet k="valider" n={aValider} tone="a">À valider</Onglet>
        <Onglet k="rattacher" n={aRattacher} tone="a">À rattacher</Onglet>
        <Onglet k="reverifier" n={reverifDues} tone="a">Re-vérifier</Onglet>
        <Onglet k="check">Check du jour</Onglet>
      </div>
      {actif === 'deposer' && <DeposerPanel />}
      {actif === 'valider' && <Extraction />}
      {actif === 'rattacher' && <Instruction />}
      {actif === 'reverifier' && <Reverif />}
      {actif === 'check' && <Check />}
    </div>
  )
}
