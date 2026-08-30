// RADAR (pige) · P1 V3 — page admin « Radar », pensée MOBILE (Vic saisit depuis son téléphone).
// Quatre zones : Saisie du jour · File d'extraction · Re-vérification (2 niveaux) · Check quotidien.
// Doctrine : on n'affiche JAMAIS l'annonce (ni photo, ni titre, ni texte) — des FAITS + le lien
// sortant. Le mauve est réservé aux champs IA « à vérifier » (sous le seuil de confiance).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getRadarAInstruire, getRadarCheck, getRadarDepotAgenceEtat, getRadarExtraction, getRadarReverif,
  radarDeposer, radarDeposerHtml, radarDepotAgenceAnalyser, radarDepotAgencePublier,
  radarInstruire, radarPrix, radarRattacherHumain, radarRetiree, radarToujoursEnLigne, radarValider,
  type DepotRec, type RadarAInstruire, type RadarBrouillon, type RadarCritere, type RadarDepotHtml, type RadarPiste,
} from '../../lib/api'
import { Declaratif } from '../outils/RadarDeclaratif'
import { ParcelInput } from '../ParcelInput'
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
    <section className="rounded-xl border border-line-2 bg-surface-2 p-4">
      <Lbl>2 · File d’extraction <span className="text-txt-dim">— {data?.n ?? 0} à valider</span></Lbl>
      {data?.n === 0 && <div className="py-4 text-center text-[12px] text-txt-dim">file vidée ✓</div>}
      <div className="flex flex-col gap-2">
        {data?.file.map((b) => <BrouillonCard key={b.bien_id} b={b} onValide={() => valider(b.bien_id)} />)}
      </div>
    </section>
  )
}

// ── Zone 3 — Re-vérification à deux niveaux (léger en volume · attentif sur prix/retrait) ──
function Reverif() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['radar-reverif'], queryFn: getRadarReverif })
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-reverif'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  return (
    <section className="rounded-xl border border-line-2 bg-surface-2 p-4">
      <Lbl>3 · Re-vérification <span className="text-txt-dim">— {data?.n ?? 0} · priorisée</span></Lbl>
      <div className="flex flex-col divide-y divide-line-2">
        {data?.file.map((r) => (
          <div key={r.bien_id} className="flex flex-wrap items-center gap-2 py-2 text-[12px]">
            <span className="font-medium text-txt-hi">{r.commune}</span>
            <span className="text-txt-mut">{fmtEur(r.prix)}</span>
            {r.suivi_client && <Chip tone="ok">suivi client</Chip>}
            {r.proche_longue && <Chip tone="warn">≈ 90 j</Chip>}
            <a href={r.url_sortante} target="_blank" rel="noopener noreferrer"
              className="font-mono text-[10px] text-txt-dim underline decoration-dotted">source ↗</a>
            <span className="ml-auto flex gap-1.5">
              <button onClick={() => radarToujoursEnLigne(r.bien_id).then(inval)}
                className="rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt hover:border-mint/40">Toujours en ligne</button>
              <button onClick={() => { const p = prompt('Nouveau prix (€) :'); if (p) radarPrix(r.bien_id, Number(p)).then(inval) }}
                className="rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt">Prix modifié</button>
              <button onClick={() => radarRetiree(r.bien_id).then(inval)}
                className="rounded-md border border-coral/30 px-2 py-1 text-[11px] text-coral">Retirée</button>
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

// ── Zone 3bis — INSTRUCTION (D3, ADMIN SEULEMENT) : rattacher un bien en piste via l'ortho ──
// RADAR-DEPOT-2 D3 — le rattachement humain est un geste ADMIN (un rattachement client erroné serait
// servi à tous). On relance la cascade à la demande, on compare les toits (ortho BD ORTHO 20 cm) avec
// les critères ✓/✗, la zone DÉCLARÉE aide à trancher, puis « C'est cette parcelle » (fait foi).
function InstructionCard({ b, onTranche }: { b: RadarAInstruire; onTranche: () => void }) {
  const [instr, setInstr] = useState<{ busy: boolean; ouvert: boolean; cands?: RadarPiste[]; motif?: string | null }>({ busy: false, ouvert: false })
  const [choix, setChoix] = useState<{ busy: boolean; idu?: string }>({ busy: false })
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
  return (
    <div data-radar-instruction className="rounded-lg border border-line-2 bg-surface-1 p-3">
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        <span className="font-medium text-txt-hi">{b.commune}</span>
        <span className="text-txt-mut">{(b.type_bien ?? '—')}{specs ? ` · ${specs}` : ''}</span>
        <span className="text-txt-mut">{fmtEur(b.prix)}</span>
        <Chip tone="warn">{b.n_candidates} candidate{b.n_candidates > 1 ? 's' : ''}</Chip>
        {b.url_sortante && <a href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          className="font-mono text-[10px] text-txt-dim underline decoration-dotted">source ↗</a>}
        <button data-radar-instruire onClick={instruire}
          className="ml-auto rounded-md border border-amber/50 bg-amber/10 px-2.5 py-1 text-[11.5px] font-medium text-amber hover:bg-amber/20">
          {instr.busy ? 'Instruction…' : instr.ouvert ? 'Fermer' : 'Instruire'}
        </button>
      </div>
      {/* la zone DÉCLARÉE (page d'annonce) aide à trier les candidates — déclaratif vendeur. */}
      {b.declaratif && <div className="mt-2"><Declaratif d={b.declaratif} /></div>}
      {instr.ouvert && instr.cands && (
        <div className="mt-2.5 flex flex-col gap-2">
          {instr.cands.length === 0 && <span className="text-[11px] text-txt-dim">{instr.motif || 'aucune candidate exploitable'}</span>}
          {instr.cands.map((c) => (
            <div key={c.idu} data-radar-candidate className="overflow-hidden rounded-xl border border-line-2 bg-surface-2">
              <div className="grid grid-cols-[96px_1fr]">
                {c.ortho_url
                  ? <img src={c.ortho_url} alt={`ortho ${c.idu}`} className="h-24 w-24 object-cover" loading="lazy" />
                  : <div className="flex h-24 w-24 items-center justify-center bg-surface-3 text-[9px] text-txt-dim">ortho indispo.</div>}
                <div className="min-w-0 px-2.5 py-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-txt">{c.idu}</span>
                    <span className="text-[10px] text-txt-dim">{c.distance_m != null ? `${Math.round(c.distance_m)} m` : ''}</span>
                  </div>
                  <ul className="mt-1 flex flex-col gap-0.5 text-[10px] leading-snug">
                    {(c.criteres_detail ?? []).map((x: RadarCritere, i: number) => (
                      <li key={i} className={x.converge ? 'text-mint' : 'text-txt-dim'}>
                        {x.converge ? '✓' : '✗'} <span className="text-txt-mut">{x.critere}</span> {x.valeur}
                      </li>
                    ))}
                  </ul>
                  <button data-radar-choisir disabled={choix.busy}
                    onClick={() => { setChoix({ busy: true, idu: c.idu }); radarRattacherHumain(b.bien_id, c.idu)
                      .then(() => { setChoix({ busy: false }); onTranche() })
                      .catch(() => setChoix({ busy: false })) }}
                    className="mt-1.5 rounded-md border border-mint/50 bg-mint/10 px-2 py-1 text-[10.5px] font-medium text-mint hover:bg-mint/20 disabled:opacity-60">
                    {choix.busy && choix.idu === c.idu ? 'Enregistrement…' : "C'est cette parcelle"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
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

// ── RADAR-VEILLE-1 (R3) — DÉPÔT AGENCE « Publier une annonce », 4 étapes. DERRIÈRE LE DRAPEAU :
//    si radar_depot_agence_actif est false, l'état renvoie {actif:false} et ce bloc ne rend RIEN
//    (rien ne s'ouvre, ni admin ni client). Question Hoguet en attente chez l'avocat de Vic. ──
function DepotAgence() {
  const etat = useQuery({ queryKey: ['radar-depot-agence-etat'], queryFn: getRadarDepotAgenceEtat, retry: false })
  const [step, setStep] = useState(1)
  const [html, setHtml] = useState('')
  const [rec, setRec] = useState<DepotRec | null>(null)
  const [adresse, setAdresse] = useState('')
  const [idu, setIdu] = useState('')
  const [agence, setAgence] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [publie, setPublie] = useState<{ bien_id: number; idu?: string } | null>(null)
  const analyser = useMutation({
    mutationFn: () => radarDepotAgenceAnalyser(html),
    onSuccess: (r) => { if (r.ok && r.records?.length) { setRec(r.records[0]); setStep(2); setMsg(null) } else setMsg(r.motif ?? 'Aucune annonce reconnue dans la page.') },
  })
  const publier = useMutation({
    mutationFn: () => radarDepotAgencePublier({ rec: rec as DepotRec, idu, adresse_exacte: adresse, agence_nom: agence }),
    onSuccess: (r) => { if (r.ok) { setPublie({ bien_id: r.bien_id as number, idu: r.idu }); setStep(4); setMsg(null) } else setMsg(r.motif ?? 'Publication refusée.') },
  })
  if (etat.isLoading || !etat.data?.actif) return null   // drapeau fermé → le parcours n'apparaît pas
  const setF = (k: keyof DepotRec, v: unknown) => setRec((p) => (p ? { ...p, [k]: v } : p))
  const inp = 'h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt'
  const reset = () => { setStep(1); setHtml(''); setRec(null); setAdresse(''); setIdu(''); setAgence(''); setPublie(null); setMsg(null) }

  return (
    <div data-depot-agence className="rounded-xl border border-viz-cyan/30 bg-viz-cyan/[0.04] p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="rounded bg-viz-cyan/15 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-viz-cyan">DÉPÔT AGENCE · BÊTA</span>
        <span className="font-mono text-[10px] text-txt-mut">ÉTAPE {step}/4</span>
      </div>
      {msg && <p className="mb-2 text-[11px] text-st-ecartee">{msg}</p>}

      {step === 1 && (
        <div data-depot-etape="1" className="flex flex-col gap-2">
          <p className="text-[11px] leading-snug text-txt-mut">L'agence colle SA page d'annonce (Cmd+S → « page web complète », puis colle le HTML). Le parseur reconstruit tout — rien à ressaisir.</p>
          <textarea data-depot-html value={html} onChange={(e) => setHtml(e.target.value)} rows={4}
            placeholder="Collez ici le HTML de la page de l'annonce…" className="w-full rounded-md border border-line-2 bg-surface-1 p-2 font-mono text-[11px] text-txt" />
          <button data-depot-analyser disabled={!html || analyser.isPending} onClick={() => analyser.mutate()}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">
            {analyser.isPending ? 'Analyse…' : 'Analyser la page →'}
          </button>
        </div>
      )}

      {step === 2 && rec && (
        <div data-depot-etape="2" className="flex flex-col gap-1.5">
          <p className="text-[11px] leading-snug text-txt-mut">Annonce reconstruite{rec.url ? <> depuis <span className="font-mono text-[10px]">{rec.url}</span></> : ''} — vérifiez, corrigez si besoin.</p>
          <div className="grid grid-cols-2 gap-1.5">
            <label className="text-[10px] text-txt-dim">Type<input className={inp} value={rec.type ?? ''} onChange={(e) => setF('type', e.target.value)} /></label>
            <label className="text-[10px] text-txt-dim">Prix (€)<input className={inp} type="number" value={rec.prix ?? ''} onChange={(e) => setF('prix', Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface hab (m²)<input className={inp} type="number" value={rec.surface_hab ?? ''} onChange={(e) => setF('surface_hab', Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface terrain (m²)<input className={inp} type="number" value={rec.surface_terrain ?? ''} onChange={(e) => setF('surface_terrain', Number(e.target.value))} /></label>
          </div>
          <label className="text-[10px] text-txt-dim">Description (confiée — s'affichera)<textarea className="w-full rounded-md border border-line-2 bg-surface-1 p-1.5 text-[11px] text-txt" rows={2} value={rec.description ?? ''} onChange={(e) => setF('description', e.target.value)} /></label>
          <p className="text-[10px] text-txt-dim">{(rec.photos?.length ?? 0)} photo(s) reprise(s) de l'annonce.</p>
          <button data-depot-continuer-adresse disabled={!rec.type || !rec.prix} onClick={() => setStep(3)}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">Continuer → l'adresse</button>
        </div>
      )}

      {step === 3 && rec && (
        <div data-depot-etape="3" className="flex flex-col gap-2">
          <label className="text-[10px] text-txt-dim">Adresse exacte <span className="text-viz-cyan">visible des seuls abonnés, jamais publique</span>
            <input data-depot-adresse className={inp} value={adresse} onChange={(e) => setAdresse(e.target.value)} placeholder="27 chemin Vidot, La Bretagne, 97490 Saint-Denis" /></label>
          <div>
            <p className="mb-1 text-[10px] text-txt-dim">Parcelle (résolue de l'adresse) — rattachement CERTAIN, source déclarée</p>
            <ParcelInput dataAttr="depot-parcelle" placeholder="Adresse ou IDU de la parcelle" onPick={(i) => setIdu(i)} onAddress={() => setMsg("Précisez un IDU : l'adresse n'a pas de parcelle rattachée.")} />
            {idu && <p className="mt-1 font-mono text-[11px] text-mint">✓ {idu} — Rattachée, certaine</p>}
          </div>
          <label className="text-[10px] text-txt-dim">Agence déposante<input data-depot-agence-nom className={inp} value={agence} onChange={(e) => setAgence(e.target.value)} placeholder="Agence Immo Transac" /></label>
          <div className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
            <div className="mb-1 font-mono text-[9px] tracking-[0.18em] text-txt-mut">CE QUE LABUSE AJOUTE — AUTOMATIQUEMENT</div>
            <ul className="list-disc pl-4 text-[10.5px] leading-snug text-txt-mut">
              <li>Zone PLU calibrée, servitudes et prescriptions</li>
              <li>Risques : inondation, mouvement de terrain, CatNat</li>
              <li>Marché du secteur : DVF, prix demandés, écart demandé/acté</li>
              <li>Potentiel : emprise constructible, contexte foncier</li>
            </ul>
            <p className="mt-1 text-[10px] text-txt-dim">Votre annonce ici est plus riche que partout ailleurs — l'argument du dépôt.</p>
          </div>
          <button data-depot-publier disabled={!adresse || !idu || !agence || publier.isPending} onClick={() => publier.mutate()}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">{publier.isPending ? 'Publication…' : 'Publier l\'annonce →'}</button>
        </div>
      )}

      {step === 4 && publie && (
        <div data-depot-etape="4" className="flex flex-col gap-2">
          <div className="rounded-lg border border-mint/30 bg-mint/[0.06] p-3">
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded-md bg-mint/15 px-2 py-0.5 font-mono text-[10px] text-mint">✓ Rattachée — déposée par l'agence</span>
            </div>
            <p className="text-[11.5px] text-txt">Annonce publiée au Radar — bien #{publie.bien_id}{publie.idu ? <> · parcelle <span className="font-mono">{publie.idu}</span></> : ''}. Les abonnés voient la fiche complète (photos, texte, adresse) et le bouton « Intéressé ».</p>
          </div>
          <button data-depot-nouveau onClick={reset} className="self-start rounded-md border border-line-2 px-3 py-1.5 text-[12px] text-txt-mut hover:text-txt">Nouveau dépôt</button>
        </div>
      )}
    </div>
  )
}

export function RadarSection() {
  const qc = useQueryClient()
  const refresh = () => { qc.invalidateQueries({ queryKey: ['radar-extraction'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[12.5px] text-txt-mut">
        Faits extraits d’annonces publiques + lien vers la source. Aucune photo ni texte d’annonce n’est
        stocké ni affiché — les pages déposées restent des documents de travail privés.
      </p>
      <DepotHtml onDepose={refresh} />
      <DepotAgence />
      <details className="rounded-xl border border-line-2 bg-surface-2/50">
        <summary className="cursor-pointer px-4 py-2 text-[11.5px] text-txt-dim">
          Saisie par capture d’écran (chemin historique — remplacé par le dépôt HTML)
        </summary>
        <div className="p-3 pt-0">
          <CapturesAlerte />
          <Saisie onDepose={refresh} />
        </div>
      </details>
      <Extraction />
      <Reverif />
      <Instruction />
      <Check />
    </div>
  )
}
