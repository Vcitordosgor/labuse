// VEILLE-3 — LA VEILLE EN UNE SEULE PAGE (plus de chooser « Choisissez ce que vous voulez surveiller »,
// plus de deux sous-pages « Vos parcelles suivies » / « Vos alertes »). Derrière la porte « Veille » du hub
// Radar : un en-tête (← Radar · VEILLE · « Ce que vous surveillez » · sous-titre dynamique · chips du mail)
// puis DEUX colonnes — à gauche les parcelles suivies (omnibox + liste), à droite les alertes (+ nouvelle
// alerte + liste). Les anciennes routes (veille-foncier/veille-annonces, #surveillance=…) y mènent toutes.
// Le réglage du mail partage LA MÊME source que Mon compte (VEILLE-FIX-2, /events/prefs). Aucun défilement
// horizontal, listes longues en « Voir 200 de plus », formats français, un seul « Retour ».
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import {
  ApiError, creerRadarVeille, getNotifPrefs, getRadarAlertes, getSuivis,
  modifierRadarVeille, patchDigestFrequence, pauseRadarVeille, supprimerRadarVeille, toggleWatch,
  type RadarAlerte, type SuiviItem,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { iduCourt, fmtM2, ilYA } from '../../lib/format'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { ParcelInput } from '../ParcelInput'
import { Squelette } from '../Loading'
import { EmptyState } from '../States'
import { Badge } from '../ui/Badge'
import { Bouton } from '../ui/Bouton'
import { Retour } from '../ui/Retour'

// fréquence du mail — mêmes valeurs que Mon compte (VEILLE-FIX-2). Libellés de la maquette.
const FREQ_LABEL: Record<string, string> = { quotidien: 'Chaque matin', hebdo: 'Chaque lundi', cloche_seule: 'Seulement dans la cloche' }
const FREQ_ORDRE = ['quotidien', 'hebdo', 'cloche_seule']

// communes/type/vendeur du formulaire d'alerte (inchangé depuis RADAR-2).
const COMMUNES_24 = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const TYPES_ALERTE = [['', 'Tous'], ['terrain', 'Terrain'], ['maison', 'Maison']] as const
const VENDEURS_ALERTE = [['', 'Tous'], ['particulier', 'Particulier']] as const

// combien d'éléments on montre avant le bouton « Voir … de plus » (évite une liste à rallonge).
const PAGE_INITIALE = 50
const PAGE_PAS = 200

// ══════════════════════════════ LA PAGE ══════════════════════════════
export function VeilleEcran() {
  const setRadarEcran = useApp((s) => s.setRadarEcran)
  const qc = useQueryClient()

  // données des deux colonnes + réglage du mail (une seule page → tout est chargé ici).
  const suivisQ = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const alertesQ = useQuery({ queryKey: ['radar-alertes'], queryFn: getRadarAlertes })
  const prefs = useQuery({ queryKey: ['notif-prefs'], queryFn: getNotifPrefs })
  const suivis = suivisQ.data?.suivis ?? []
  const alertes = alertesQ.data?.alertes ?? []

  // sous-titre dynamique : « N événements depuis votre dernier passage » (parcelles bougées ces 7 jours +
  // annonces tombées depuis hier) ; sinon une phrase d'explication courte. Rien d'inventé : les deux comptes
  // viennent de ce que la veille détecte déjà.
  const nEvenements = suivis.filter((s) => s.nouveau).length + alertes.reduce((n, a) => n + (a.en_pause ? 0 : a.nouveaux), 0)

  // chips du mail — même source/mutation que Mon compte.
  const freq = prefs.data?.frequence ?? 'quotidien'
  const frequences = prefs.data?.frequences?.length ? prefs.data.frequences : FREQ_ORDRE
  const setFreq = useMutation({
    mutationFn: (v: string) => patchDigestFrequence(v),
    onMutate: (v) => { qc.setQueryData(['notif-prefs'], (p: { frequence: string } | undefined) => (p ? { ...p, frequence: v } : p)) },
    onSettled: () => qc.invalidateQueries({ queryKey: ['notif-prefs'] }),
  })

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
     <div className="mx-auto w-full max-w-[1120px] px-8 py-10">
      {/* ── EN-TÊTE : un seul « ← Radar », surtitre/titre/sous-titre à gauche, chips du mail à droite ── */}
      <div className="mb-4"><Retour label="Radar" data-veille-retour-radar onClick={() => setRadarEcran('portes')} /></div>
      <div className="mb-8 flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
        <div className="min-w-0">
          <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">VEILLE</div>
          <h1 className="mt-1.5 text-[28px] font-semibold leading-tight text-txt-hi">Ce que vous surveillez</h1>
          <p data-veille-soustitre className="mt-1.5 text-[13px] leading-snug text-txt-mut">
            {nEvenements > 0
              ? `${nEvenements} événement${nEvenements > 1 ? 's' : ''} depuis votre dernier passage`
              : 'Vos parcelles suivies et vos alertes, au même endroit — prévenu dès que quelque chose bouge.'}
          </p>
        </div>
        {/* réglage du mail (chips) — en haut à droite, même réglage qu'aujourd'hui */}
        <div className="shrink-0">
          <div className="mb-1.5 text-right text-[11px] text-txt-dim">Résumé par mail</div>
          <div className="flex flex-wrap justify-end gap-2">
            {frequences.map((v) => (
              <button key={v} data-veille-freq={v} onClick={() => setFreq.mutate(v)}
                className={`h-8 rounded-full border px-3.5 text-[12.5px] transition-colors duration-quick ${
                  freq === v ? 'border-mint bg-mint text-mint-on font-medium' : 'border-line-2 text-txt hover:border-mint/50'}`}>
                {freq === v && <span className="mr-1">✓</span>}{FREQ_LABEL[v] ?? v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── DEUX COLONNES : parcelles suivies · alertes ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ColonneParcelles suivis={suivis} isLoading={suivisQ.isLoading} />
        <ColonneAlertes alertes={alertes} isLoading={alertesQ.isLoading} />
      </div>
     </div>
    </div>
  )
}

// ── petit en-tête de colonne (titre + action à droite) ──
function ColonneTete({ titre, action }: { titre: string; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-[15px] font-semibold text-txt-hi">{titre}</h2>
      {action}
    </div>
  )
}

// ══════════════════════════════ COLONNE GAUCHE · parcelles suivies ══════════════════════════════
function ColonneParcelles({ suivis, isLoading }: { suivis: SuiviItem[]; isLoading: boolean }) {
  const { focusParcelle } = useApp()
  const qc = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const [vus, setVus] = useState(PAGE_INITIALE)
  const suivre = useMutation({
    mutationFn: (idu: string) => toggleWatch(idu),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['suivis'] }); qc.invalidateQueries({ queryKey: ['watch'] })
      qc.invalidateQueries({ queryKey: ['radar-apercu'] })
      setMsg(r.watched ? '✓ Parcelle ajoutée au suivi.' : 'Parcelle retirée du suivi.')
    },
    onError: (err) => setMsg(err instanceof ApiError && err.detail ? err.detail : 'Impossible de suivre cette parcelle.'),
  })
  const reste = suivis.length - vus

  return (
    <section data-veille-colonne="parcelles" className="min-w-0">
      <ColonneTete titre="Parcelles suivies" />
      {/* omnibox d'ajout en tête (pas de carte ici → withCarte=false retire l'invite « cliquez la carte ») */}
      <div className="mb-3">
        <ParcelInput dataAttr="veille-parcelle" placeholder="Adresse, IDU ou référence (BW0917)" withCarte={false}
          onPick={(idu) => suivre.mutate(idu)}
          onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — précisez un IDU pour la suivre.")} />
        {msg && <p className="mt-1.5 text-[11px] text-txt-mut">{msg}</p>}
      </div>

      {isLoading && <Squelette lignes={4} />}
      {!isLoading && suivis.length === 0 && (
        <EmptyState className="rounded-lg border border-dashed border-line-2"
          title="Aucune parcelle suivie."
          hint={<>Ajoutez-en une ci-dessus, ou ouvrez une fiche et cliquez la <b className="text-txt">cloche « Suivre »</b>.</>} />
      )}
      {suivis.length > 0 && (
        <div className="flex flex-col gap-2">
          {suivis.slice(0, vus).map((s) => <LigneParcelle key={s.idu} s={s} onOuvrir={() => focusParcelle(s.idu, { fiche: true })} onRetirer={() => suivre.mutate(s.idu)} />)}
          {reste > 0 && (
            <button data-veille-parcelles-plus onClick={() => setVus((v) => v + PAGE_PAS)}
              className="mt-1 self-start text-[12px] text-mint underline decoration-mint/40 underline-offset-2 hover:decoration-mint">
              Voir {Math.min(PAGE_PAS, reste)} de plus
            </button>
          )}
        </div>
      )}
    </section>
  )
}

// ── une ligne « parcelle suivie » : clic = ouvre la fiche ; la croix retire du suivi ──
function LigneParcelle({ s, onOuvrir, onRetirer }: { s: SuiviItem; onOuvrir: () => void; onRetirer: () => void }) {
  // titre : l'adresse/le secteur si connu, sinon « Parcelle <section numéro>, Commune ».
  const titre = s.secteur || `Parcelle ${iduCourt(s.idu)}${s.commune ? `, ${s.commune}` : ''}`
  // ligne secondaire : IDU · surface · zone (les champs absents sont omis, jamais « — » en rafale).
  const meta = [iduCourt(s.idu), s.surface != null ? fmtM2(s.surface) : null, s.zone || null].filter(Boolean)
  const age = s.dernier_changement ? ilYA(s.dernier_changement) : ''
  return (
    <div data-suivi role="button" tabIndex={0} onClick={onOuvrir}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOuvrir() } }}
      className="group flex cursor-pointer items-start justify-between gap-3 rounded-lg border border-line-2 bg-surface-2 px-4 py-3 transition-colors hover:border-mint/40">
      <div className="min-w-0 flex-1">
        <div data-suivi-idu className="truncate text-[13px] font-medium text-txt-hi group-hover:text-mint">{titre}</div>
        <div className="mt-0.5 truncate font-mono text-[11px] text-txt-dim">{meta.join(' · ')}</div>
        <div className="mt-1.5">
          {s.dernier_evenement ? (
            <span className="inline-flex flex-wrap items-center gap-1.5">
              <Badge ton={s.nouveau ? 'vert' : 'neutre'}>{s.dernier_evenement}</Badge>
              {age && <span className="text-[11px] text-txt-mut">{age}</span>}
            </span>
          ) : <span className="text-[11.5px] text-txt-dim">Rien de nouveau</span>}
        </div>
      </div>
      <button data-suivi-retirer aria-label="Ne plus suivre cette parcelle"
        onClick={(e) => { e.stopPropagation(); onRetirer() }}
        className="shrink-0 grid h-7 w-7 place-items-center rounded-md text-txt-dim transition-colors hover:bg-line-1 hover:text-coral">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
      </button>
    </div>
  )
}

// ══════════════════════════════ COLONNE DROITE · alertes ══════════════════════════════
// criteria → chips lisibles (type · communes · budget).
function alerteChips(a: RadarAlerte): string[] {
  const c = a.criteria as Record<string, unknown>
  const out: string[] = []
  if (c.type_bien) out.push(String(c.type_bien).charAt(0).toUpperCase() + String(c.type_bien).slice(1))
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : (a.commune ? [String(a.commune)] : [])
  if (communes.length) out.push(communes.join(' · '))
  if (c.surface_min) out.push(`≥ ${Number(c.surface_min)} m²`)
  if (c.prix_max) out.push(`≤ ${Number(c.prix_max).toLocaleString('fr-FR')} €`)
  if (c.particulier_only) out.push('Particulier')
  return out.length ? out : ['Tous les biens']
}

// criteria → RadarFiltres (pour « Voir dans Radar »)
function alerteVersFiltres(a: RadarAlerte): Record<string, unknown> {
  const c = a.criteria as Record<string, unknown>
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : []
  return {
    commune: communes.length === 1 ? communes[0] : (a.commune ?? undefined),
    type_bien: c.type_bien ?? undefined,
    prix_max: c.prix_max ?? undefined, prix_min: c.prix_min ?? undefined,
    surface_terrain_min: c.surface_min ?? undefined,
    particulier_pro: c.particulier_only ? 'particulier' : undefined,
  }
}

function ColonneAlertes({ alertes, isLoading }: { alertes: RadarAlerte[]; isLoading: boolean }) {
  const { setRadarEcran, setRadarPrefill } = useApp()
  const qc = useQueryClient()
  const [form, setForm] = useState<null | { mode: 'creer' } | { mode: 'modifier'; alerte: RadarAlerte }>(null)
  const [vus, setVus] = useState(PAGE_INITIALE)
  const [menu, setMenu] = useState<number | null>(null)
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-alertes'] }); qc.invalidateQueries({ queryKey: ['radar-apercu'] }) }
  const pause = useMutation({ mutationFn: ({ id, p }: { id: number; p: boolean }) => pauseRadarVeille(id, p), onSuccess: inval })
  const suppr = useMutation({ mutationFn: (id: number) => supprimerRadarVeille(id), onSuccess: inval })
  const voirDansRadar = (a: RadarAlerte) => { setRadarPrefill(alerteVersFiltres(a)); setRadarEcran('radar') }
  const reste = alertes.length - vus

  return (
    <section data-veille-colonne="alertes" className="min-w-0">
      <ColonneTete titre="Alertes" action={
        <Bouton niveau="primaire" ton="vert" data-veille-nouvelle-alerte onClick={() => setForm(form?.mode === 'creer' ? null : { mode: 'creer' })}>
          + Nouvelle alerte
        </Bouton>
      } />

      {form?.mode === 'creer' && (
        <FormulaireAlerte onFini={() => { inval(); setForm(null) }} onAnnuler={() => setForm(null)} />
      )}

      {isLoading && <Squelette lignes={3} />}
      {!isLoading && alertes.length === 0 && !form && (
        <EmptyState className="rounded-lg border border-dashed border-line-2"
          title="Aucune alerte." hint={<>Cliquez <b className="text-txt">« + Nouvelle alerte »</b> pour surveiller des annonces selon vos critères.</>} />
      )}

      <div className="flex flex-col gap-3">
        {alertes.slice(0, vus).map((a) => (
          form?.mode === 'modifier' && form.alerte.id === a.id ? (
            <FormulaireAlerte key={a.id} edit={a} onFini={() => { inval(); setForm(null) }} onAnnuler={() => setForm(null)} />
          ) : (
            <div key={a.id} data-veille-alerte className="rounded-lg border border-line-2 bg-surface-2 px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  {alerteChips(a).map((chip, i) => <Badge key={i} ton="neutre">{chip}</Badge>)}
                </div>
                {/* menu ⋯ : Modifier · Voir dans Radar · Pause/Reprendre · Supprimer */}
                <div className="relative shrink-0">
                  <button data-alerte-menu aria-label="Actions de l’alerte" onClick={() => setMenu(menu === a.id ? null : a.id)}
                    className="grid h-7 w-7 place-items-center rounded-md text-txt-mut transition-colors hover:bg-line-1 hover:text-txt">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></svg>
                  </button>
                  {menu === a.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setMenu(null)} />
                      <div data-alerte-menu-liste className="absolute right-0 z-20 mt-1 w-44 overflow-hidden rounded-md border border-line-2 bg-surface-1 py-1 shadow-lg">
                        <MenuItem data="alerte-modifier" onClick={() => { setMenu(null); setForm({ mode: 'modifier', alerte: a }) }}>Modifier</MenuItem>
                        <MenuItem data="alerte-voir" onClick={() => { setMenu(null); voirDansRadar(a) }}>Voir dans Radar</MenuItem>
                        <MenuItem data="alerte-pause" onClick={() => { setMenu(null); pause.mutate({ id: a.id, p: !a.en_pause }) }}>{a.en_pause ? 'Reprendre' : 'Mettre en pause'}</MenuItem>
                        <MenuItem data="alerte-supprimer" danger onClick={() => { setMenu(null); suppr.mutate(a.id) }}>Supprimer</MenuItem>
                      </div>
                    </>
                  )}
                </div>
              </div>
              {/* ce qui est surveillé — une veille notifie sur TOUT événement d'un bien correspondant (V3) */}
              <p className="mt-2.5 text-[11px] text-txt-dim">Surveillé : nouvelle annonce, baisse de prix, retrait.</p>
              {/* badge : nombre d'annonces tombées depuis la dernière visite, « Rien cette semaine », ou « En pause » */}
              <div className="mt-2 flex items-center gap-3 text-[12px]">
                <span className={a.en_pause ? 'text-amber' : a.nouveaux > 0 ? 'text-mint' : 'text-txt-dim'}>
                  {a.en_pause
                    ? 'En pause'
                    : a.nouveaux > 0 ? `${a.nouveaux} annonce${a.nouveaux > 1 ? 's' : ''} depuis votre dernier passage` : 'Rien cette semaine'}
                </span>
                <span className="text-txt-dim">
                  {a.en_pause
                    ? (a.paused_at ? `En pause depuis le ${new Date(a.paused_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}` : '')
                    : (a.created_at ? `Créée le ${new Date(a.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}` : '')}
                </span>
              </div>
            </div>
          )
        ))}
        {reste > 0 && (
          <button data-veille-alertes-plus onClick={() => setVus((v) => v + PAGE_PAS)}
            className="mt-1 self-start text-[12px] text-mint underline decoration-mint/40 underline-offset-2 hover:decoration-mint">
            Voir {Math.min(PAGE_PAS, reste)} de plus
          </button>
        )}
      </div>
    </section>
  )
}

// ── une entrée du menu ⋯ ──
function MenuItem({ children, onClick, danger, data }: { children: ReactNode; onClick: () => void; danger?: boolean; data: string }) {
  return (
    <button {...{ [`data-${data}`]: true }} onClick={onClick}
      className={`block w-full px-3.5 py-2 text-left text-[12.5px] transition-colors hover:bg-line-1 ${danger ? 'text-coral' : 'text-txt'}`}>
      {children}
    </button>
  )
}

// ══════════════ le FORMULAIRE d'alerte (création OU modification) — inchangé côté saisie ══════════════
// `edit` = l'alerte à modifier (pré-remplit, enregistre en place) ; absent = création.
function FormulaireAlerte({ edit, onFini, onAnnuler }: { edit?: RadarAlerte; onFini: () => void; onAnnuler: () => void }) {
  const c = (edit?.criteria ?? {}) as Record<string, unknown>
  const communesInit = Array.isArray(c.communes) ? (c.communes as string[]) : (edit?.commune ? [edit.commune] : [])
  const [communes, setCommunes] = useState<string[]>(communesInit)
  const [ajout, setAjout] = useState('')
  const [type, setType] = useState(c.type_bien ? String(c.type_bien) : '')
  const [prixMax, setPrixMax] = useState(c.prix_max != null ? String(c.prix_max) : '')
  const [surfMin, setSurfMin] = useState(c.surface_min != null ? String(c.surface_min) : '')
  const [vendeur, setVendeur] = useState(c.particulier_only ? 'particulier' : '')
  const [msg, setMsg] = useState<string | null>(null)
  const inp = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  const payload = () => ({
    communes: communes.length ? communes : undefined,
    type_bien: type || undefined,
    prix_max: prixMax ? Number(prixMax) : undefined,
    surface_min: surfMin ? Number(surfMin) : undefined,
    particulier_only: vendeur === 'particulier' || undefined,
  })
  const enreg = useMutation({
    mutationFn: () => (edit ? modifierRadarVeille(edit.id, payload()) : creerRadarVeille(payload())),
    onSuccess: onFini,
    onError: (err) => setMsg(err instanceof ApiError && err.detail ? err.detail : (edit ? "Impossible de modifier l'alerte." : "Impossible de créer l'alerte.")),
  })
  const soumettre = () => {
    if (!communes.length && !type) { setMsg('Choisissez au moins une commune ou un type de bien.'); return }
    setMsg(null); enreg.mutate()
  }
  const ajouterCommune = (nom: string) => { if (nom && !communes.includes(nom)) setCommunes((p) => [...p, nom]); setAjout('') }

  return (
    <div data-veille-form className="mb-3 rounded-lg border border-mint/40 bg-mint/[0.04] px-5 py-4">
      <div className="mb-3 text-[13px] font-semibold text-txt-hi">{edit ? "Modifier l'alerte" : 'Nouvelle alerte'}</div>
      <div className="mb-3">
        <label className="mb-1 block text-[11px] text-txt-dim">Commune(s)</label>
        <div className="flex flex-wrap items-center gap-2">
          {communes.map((c0) => (
            <span key={c0} data-veille-form-commune className="inline-flex items-center gap-1 rounded-full bg-mint/12 px-2.5 py-1 text-[11.5px] text-mint">
              {c0}
              <button aria-label={`Retirer ${c0}`} onClick={() => setCommunes((p) => p.filter((x) => x !== c0))} className="text-mint/70 hover:text-mint">✕</button>
            </span>
          ))}
          <select data-veille-form-ajout-commune value={ajout} onChange={(e) => ajouterCommune(e.target.value)} className={`${inp} min-w-[170px]`}>
            <option value="">+ Ajouter une commune…</option>
            {COMMUNES_24.filter((c0) => !communes.includes(c0)).map((c0) => <option key={c0} value={c0}>{c0}</option>)}
          </select>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Segment label="Type" value={type} onChange={setType} options={TYPES_ALERTE} data="veille-form-type" />
        <Segment label="Vendeur" value={vendeur} onChange={setVendeur} options={VENDEURS_ALERTE} data="veille-form-vendeur" />
        <input data-veille-form-prix type="number" min={0} placeholder="Prix max" value={prixMax} onChange={(e) => setPrixMax(e.target.value)} className={`${inp} w-[120px]`} />
        <input data-veille-form-surface type="number" min={0} placeholder="Surface min" value={surfMin} onChange={(e) => setSurfMin(e.target.value)} className={`${inp} w-[120px]`} />
      </div>
      {msg && <p data-veille-form-msg className="mt-2.5 text-[11.5px] text-amber">{msg}</p>}
      <div className="mt-3.5 flex items-center gap-2">
        <Bouton niveau="primaire" ton="vert" data-veille-form-creer disabled={enreg.isPending} onClick={soumettre}>{edit ? 'Enregistrer' : "Créer l’alerte"}</Bouton>
        <Bouton niveau="secondaire" ton="vert" data-veille-form-annuler onClick={onAnnuler}>Annuler</Bouton>
      </div>
    </div>
  )
}

// petit sélecteur segmenté (repris de l'écran Radar), pour Type / Vendeur du formulaire d'alerte.
function Segment({ label, value, onChange, options, data }: {
  label: string; value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; data: string
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-txt-dim">{label}</span>
      <div data-seg={data} className="flex h-8 overflow-hidden rounded-md border border-line-2">
        {options.map(([v, l], i) => (
          <button key={v || 'tous'} data-seg-opt={v || 'tous'} onClick={() => onChange(v)}
            className={`flex items-center justify-center whitespace-nowrap px-2.5 text-[12px] ${i ? 'border-l border-line-2' : ''} ${value === v ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
    </div>
  )
}
