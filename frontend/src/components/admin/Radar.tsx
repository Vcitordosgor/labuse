// RADAR (pige) · P1 V3 — page admin « Radar », pensée MOBILE (Vic saisit depuis son téléphone).
// Quatre zones : Saisie du jour · File d'extraction · Re-vérification (2 niveaux) · Check quotidien.
// Doctrine : on n'affiche JAMAIS l'annonce (ni photo, ni titre, ni texte) — des FAITS + le lien
// sortant. Le mauve est réservé aux champs IA « à vérifier » (sous le seuil de confiance).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getRadarCheck, getRadarExtraction, getRadarReverif, radarDeposer, radarPrix, radarRetiree,
  radarToujoursEnLigne, radarValider, type RadarBrouillon,
} from '../../lib/api'
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

// ── Zone 1 — Saisie du jour : dropzone + un lien par capture ──
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

export function RadarSection() {
  const qc = useQueryClient()
  const refresh = () => { qc.invalidateQueries({ queryKey: ['radar-extraction'] }); qc.invalidateQueries({ queryKey: ['radar-check'] }) }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[12.5px] text-txt-mut">
        Faits extraits d’annonces publiques + lien vers la source. Aucune photo ni texte d’annonce n’est
        stocké ni affiché — les captures restent des documents de travail privés.
      </p>
      <CapturesAlerte />
      <Saisie onDepose={refresh} />
      <Extraction />
      <Reverif />
      <Check />
    </div>
  )
}
