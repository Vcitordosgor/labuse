// M104 — LA SECTION « SURVEILLANCE » : fusion Suivis + Secteurs + Critères (arbitrage 17/08/2026).
// Une entrée, trois volets — le mot « veille » est banni du vocabulaire servi (saturé, audit M104).
// LA BOUCLE EST DITE : ce qu'on surveille ici produit des alertes qui arrivent à la cloche et au
// brief du matin (raccordement M104 — plus de tuyau parallèle). Aucune régression : tout ce que
// permettaient les deux anciens panneaux (et l'encart cloche des recherches) reste possible ici.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ackAlerte, createWatchZone, creerRadarVeille, deleteSearch, deleteWatchZone, getAlertes, getRadarVeilles, getSavedSearches, getSuivis, getWatchZones, refreshAlertes, renameWatchZone, saveSearch, supprimerRadarVeille, veilleNL, type RadarVeille } from '../../lib/api'
import { filtersToHash } from '../../lib/filters'
import { fmtInt } from '../../lib/format'
import { CP_COMMUNES } from '../panel/FiltreLabuse'   // R2 — source unique des 24 communes
import { EMPTY_FILTERS, useApp } from '../../store/useApp'

const VOLETS = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'secteurs', label: 'Secteurs' },
  { key: 'criteres', label: 'Critères' },
] as const

// RADAR-CATÉGORIE (T4) — la Veille s'ouvre sur un écran d'entrée à DEUX PORTES (patron de l'outil
// Communes restructuré par RETOURS-1) : Veille interne (le foncier — l'écran existant, INCHANGÉ) et
// Veille externe (les annonces Radar — son interface propre, back type 'radar' réutilisé).
export function SurveillancePanel() {
  const { setSurveillanceOpen, tool, setTool, surveillancePorte, setSurveillancePorte } = useApp()
  const drawing = tool === 'zone'
  const fermer = () => { setSurveillanceOpen(false); if (drawing) setTool(null); setSurveillancePorte('accueil') }
  return (
    <aside data-surveillance-panel className="absolute right-0 top-0 z-30 flex h-full w-[360px] flex-col overflow-hidden border-l border-line bg-bg">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <div className="flex items-center gap-2">
          {surveillancePorte !== 'accueil' && (
            <button data-veille-retour onClick={() => setSurveillancePorte('accueil')} className="text-[11px] text-mint hover:underline">‹</button>
          )}
          <p className="label-caps">{surveillancePorte === 'externe' ? 'Veille · annonces' : surveillancePorte === 'interne' ? 'Veille · foncier' : 'Veille'}</p>
        </div>
        <button onClick={fermer} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
      </div>
      {surveillancePorte === 'accueil' && <DeuxPortes onChoisir={setSurveillancePorte} />}
      {surveillancePorte === 'interne' && <VeilleInterne />}
      {surveillancePorte === 'externe' && <VeilleExterne />}
    </aside>
  )
}

// ── L'écran d'entrée : deux gros boutons (gabarit door-hot, patron Communes R3) ──
function DeuxPortes({ onChoisir }: { onChoisir: (p: 'interne' | 'externe') => void }) {
  return (
    <div className="flex flex-col gap-2.5 p-4">
      <p className="text-[12px] leading-snug text-txt-mut">Deux veilles, deux mondes — choisissez ce que vous voulez surveiller.</p>
      <button data-veille-porte="interne" onClick={() => onChoisir('interne')}
        className="door door-hot w-full text-left transition-colors duration-quick hover:border-line-3">
        <div className="text-[13px] font-medium text-txt">Le foncier</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Parcelles suivies, secteurs dessinés et critères enregistrés — vente, permis, procédure, zonage, classement.</div>
      </button>
      <button data-veille-porte="externe" onClick={() => onChoisir('externe')}
        className="door door-hot w-full text-left transition-colors duration-quick hover:border-line-3">
        <div className="text-[13px] font-medium text-txt">Les annonces</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Vos veilles Radar — soyez alerté sur une nouvelle annonce, une baisse de prix ou un retour, selon vos critères.</div>
      </button>
    </div>
  )
}

// ── Veille interne — le foncier : l'écran existant, INCHANGÉ (boucle + trois volets). ──
function VeilleInterne() {
  const { surveillanceVolet, openSurveillance } = useApp()
  return (
    <>
      {/* LA BOUCLE, dite — pas devinée : surveiller → alertes → cloche + brief. */}
      <p data-surveillance-boucle className="border-b border-line bg-surface-2 px-4 py-2 text-[10.5px] leading-snug text-txt-mut">
        Ce que vous surveillez ici produit des alertes — elles arrivent <b className="text-txt">à la cloche</b> et
        au <b className="text-txt">brief du matin</b> (et par e-mail selon vos préférences).
      </p>
      <div className="flex shrink-0 gap-1 border-b border-line px-3 py-2">
        {VOLETS.map((v) => (
          <button key={v.key} data-volet={v.key} onClick={() => openSurveillance(v.key)}
            className={`rounded-full px-3 py-1 text-[11px] transition-colors duration-quick ${
              surveillanceVolet === v.key ? 'bg-mint/15 text-mint' : 'text-txt-mut hover:text-txt'}`}>
            {v.label}
          </button>
        ))}
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
        {surveillanceVolet === 'parcelles' && <VoletParcelles />}
        {surveillanceVolet === 'secteurs' && <VoletSecteurs />}
        {surveillanceVolet === 'criteres' && <VoletCriteres />}
      </div>
    </>
  )
}

// ── Volet PARCELLES (ex-SuivisPanel M85-B, contenu inchangé — aucune régression) ──
function VoletParcelles() {
  const { select, setView, setSurveillanceOpen } = useApp()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const plafond = q.data?.plafond ?? 50
  return (
    <div data-volet-parcelles>
      <p className="label-caps mb-1.5">Parcelles suivies <span className="text-txt-dim">· {suivis.length}/{plafond}</span></p>
      {suivis.length === 0 && (
        <p className="p-1 text-[11.5px] leading-snug text-txt-dim">
          Aucune parcelle suivie. Ouvrez une fiche et cliquez sur la <b className="text-txt">cloche « Suivre »</b> —
          vous serez prévenu dès qu'elle change : vente, permis, procédure, zonage, classement.
        </p>
      )}
      {suivis.map((s) => (
        <button key={s.idu} data-suivi onClick={() => { setView('cartes'); select(s.idu); setSurveillanceOpen(false) }}
          className="mb-1 flex w-full flex-col items-start rounded-lg border border-line-2 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/40">
          <span className="text-xs font-medium text-txt">
            {s.commune ?? 'Parcelle'} <span className="font-mono text-[10px] text-txt-dim">{s.idu.slice(8)}</span>
          </span>
          <span className="mt-0.5 text-[10.5px] text-txt-dim">
            {s.dernier_changement
              ? <>Dernier changement : <b className="text-txt-mut">{new Date(s.dernier_changement).toLocaleDateString('fr-FR')}</b></>
              : 'Aucun changement détecté depuis le suivi.'}
          </span>
        </button>
      ))}
    </div>
  )
}

// ── Volet SECTEURS (ex-VeillesPanel M54-EXPO-3) — vocabulaire ALIGNÉ (« secteur », plus
// jamais « veille ») ; alertes : ventes DVF + permis + BODACC + zonage (M104). ──
function VoletSecteurs() {
  const qc = useQueryClient()
  const { tool, setTool, zone, setZone, commune, select } = useApp()
  const [nom, setNom] = useState('')
  const [renId, setRenId] = useState<number | null>(null)
  const [renVal, setRenVal] = useState('')
  const zones = useQuery({ queryKey: ['watch-zones', commune], queryFn: getWatchZones })
  const alertes = useQuery({ queryKey: ['alertes', commune], queryFn: () => getAlertes(false) })
  const inval = () => { qc.invalidateQueries({ queryKey: ['watch-zones'] }); qc.invalidateQueries({ queryKey: ['alertes'] }) }
  const creer = useMutation({
    mutationFn: () => createWatchZone(nom.trim() || 'Secteur surveillé',
      { type: 'Polygon', coordinates: [[...zone!, zone![0]]] }),
    onSuccess: () => { setZone(null); setNom(''); inval() },
  })
  const ren = useMutation({ mutationFn: () => renameWatchZone(renId!, renVal.trim()), onSuccess: () => { setRenId(null); inval() } })
  const del = useMutation({ mutationFn: (id: number) => deleteWatchZone(id), onSuccess: inval })
  const refr = useMutation({ mutationFn: () => refreshAlertes(), onSuccess: inval })
  const ack = useMutation({ mutationFn: (id?: number) => ackAlerte(id), onSuccess: inval })
  const drawing = tool === 'zone'
  const nonLues = (alertes.data ?? []).filter((a) => !a.acknowledged)
  return (
    <div data-volet-secteurs className="flex flex-col gap-3">
      {/* CRÉER */}
      <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[11px] font-medium text-txt">Nouveau secteur surveillé</p>
        <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Dessinez une emprise sur la carte — on vous alerte des <b className="text-txt-mut">ventes, permis, procédures BODACC et changements de zonage</b> qui y surviennent.</p>
        {!commune && <p className="mt-1 text-[10.5px] text-st-creuser">Choisissez d’abord une commune (l’outil de dessin est désactivé sur toute l’île).</p>}
        {!zone && (
          <button data-secteur-dessiner disabled={!commune} onClick={() => setTool(drawing ? null : 'zone')}
            className={`mt-2 w-full rounded-md border px-3 py-1.5 text-[11px] transition-colors disabled:opacity-40 ${drawing ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 bg-surface-3 text-txt hover:border-mint/50'}`}>
            {drawing ? '✎ Dessin en cours — double-clic pour fermer' : '✎ Dessiner un secteur'}
          </button>
        )}
        {zone && (
          <div className="mt-2 flex flex-col gap-1.5">
            <p className="text-[10.5px] text-mint">Secteur tracé ({zone.length} points). Nommez-le puis enregistrez.</p>
            <input autoFocus value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du secteur (ex. Centre-bourg)"
              className="w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt placeholder:text-txt-dim" />
            <div className="flex gap-1.5">
              <button data-secteur-save disabled={creer.isPending} onClick={() => creer.mutate()}
                className="flex-1 rounded-md bg-mint py-1.5 text-[11px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-50">
                {creer.isPending ? 'Enregistrement…' : 'Enregistrer le secteur'}
              </button>
              <button onClick={() => setZone(null)} className="rounded-md border border-line-2 px-3 text-[11px] text-txt-mut hover:text-txt">Annuler</button>
            </div>
          </div>
        )}
        {creer.isSuccess && <p className="mt-1.5 text-[10.5px] text-mint">✓ Secteur créé — {creer.data?.detected?.dvf_in_zone ?? 0} vente(s) DVF déjà au dossier (l'historique reste ici : seuls les faits nouveaux notifient).</p>}
      </div>

      {/* SECTEURS */}
      <div>
        <p className="label-caps mb-1.5">Secteurs ({zones.data?.length ?? 0})</p>
        {zones.data && zones.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucun secteur pour l’instant.</p>}
        <div className="flex flex-col gap-1">
          {(zones.data ?? []).map((z) => (
            <div key={z.id} data-secteur-zone className="rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5">
              {renId === z.id ? (
                <div className="flex gap-1">
                  <input autoFocus value={renVal} onChange={(e) => setRenVal(e.target.value)}
                    className="min-w-0 flex-1 rounded border border-line-2 bg-surface-2 px-1.5 py-0.5 text-[11px] text-txt" />
                  <button onClick={() => ren.mutate()} className="text-[11px] text-mint">✓</button>
                  <button onClick={() => setRenId(null)} className="text-[11px] text-txt-dim">✕</button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-[12px] text-txt">{z.name}</span>
                  {z.n_alertes > 0 && <span className="shrink-0 rounded-full bg-mint/15 px-1.5 text-[9.5px] text-mint">{z.n_alertes}</span>}
                  <button onClick={() => { setRenId(z.id); setRenVal(z.name) }} title="Renommer" className="shrink-0 text-[11px] text-txt-dim hover:text-txt">✎</button>
                  <button data-secteur-del onClick={() => del.mutate(z.id)} title="Supprimer" className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">🗑</button>
                </div>
              )}
              {z.area_m2 != null && <p className="mt-0.5 text-[9.5px] text-txt-dim">{fmtInt(z.area_m2)} m²</p>}
            </div>
          ))}
        </div>
      </div>

      {/* ALERTES */}
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <p className="label-caps">Nouveautés{nonLues.length ? ` · ${nonLues.length}` : ''}</p>
          <button data-alertes-refresh onClick={() => refr.mutate()} disabled={refr.isPending} className="text-[10.5px] text-mint hover:underline disabled:opacity-50">{refr.isPending ? '…' : 'Rafraîchir'}</button>
          {nonLues.length > 0 && <button onClick={() => ack.mutate(undefined)} className="ml-auto text-[10.5px] text-txt-mut hover:text-txt">tout marquer lu</button>}
        </div>
        {alertes.isError && <p className="px-1 text-[10.5px] text-st-ecartee">Nouveautés indisponibles — réessayez.{/* GB-003 : l'échec réseau ne s'avale plus en silence (patron d'erreur de l'app) */}</p>}
        {refr.isError && <p className="px-1 text-[10.5px] text-st-ecartee">Le rafraîchissement a échoué — réessayez.</p>}
        {alertes.data && alertes.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucune nouveauté — ventes, permis, procédures et zonage de vos secteurs apparaîtront ici.</p>}
        <div className="flex flex-col gap-1">
          {(alertes.data ?? []).map((a) => (
            <div key={a.id} data-alerte className={`rounded-md border px-2.5 py-1.5 ${a.acknowledged ? 'border-line-2 opacity-55' : 'border-mint/30 bg-mint/[0.05]'}`}>
              <div className="flex items-start gap-2">
                <button onClick={() => a.parcel_idu && select(a.parcel_idu)} className="min-w-0 flex-1 text-left text-[11.5px] text-txt hover:text-txt-hi">{a.label}</button>
                {!a.acknowledged && <button onClick={() => ack.mutate(a.id)} title="Marquer lu" className="shrink-0 text-[11px] text-txt-dim hover:text-mint">✓</button>}
              </div>
              <p className="mt-0.5 font-mono text-[9px] text-txt-dim">{(a.detected_at || '').slice(0, 10)}{a.zone_name ? ` · ${a.zone_name}` : ''}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Volet CRITÈRES (l'ex-encart cloche « Vos veilles — alertes sur mesure », déménagé M104) :
// recherches sauvegardées — à la bascule d'une parcelle qui matche, une alerte part. ──
function VoletCriteres() {
  const qc = useQueryClient()
  const { filters, zone, setFilters } = useApp()
  const [nomCritere, setNomCritere] = useState('')
  const [nlText, setNlText] = useState('')
  const [nlResume, setNlResume] = useState<string | null>(null)
  const [nlRefus, setNlRefus] = useState<string | null>(null)
  const criteres = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches })
  const add = useMutation({ mutationFn: () => saveSearch(nomCritere, filtersToHash(filters, zone) || '#f=1'),
    onSuccess: () => { setNomCritere(''); qc.invalidateQueries({ queryKey: ['searches'] }) } })
  const del = useMutation({ mutationFn: deleteSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ['searches'] }) })
  const nl = useMutation({
    mutationFn: () => veilleNL(nlText),
    onSuccess: (r) => {
      if (r.ok && r.filters) {
        setFilters({ ...EMPTY_FILTERS, ...(r.filters as Partial<typeof EMPTY_FILTERS>) })
        setNomCritere(nlText.trim().slice(0, 80))
        setNlResume(r.resume ?? null); setNlRefus(null)
      } else {
        setNlRefus(r.refus ?? 'Critère non déclenchable.'); setNlResume(null)
      }
    },
  })
  return (
    <div data-volet-criteres>
      <p className="label-caps">Critères enregistrés</p>
      <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Enregistrez une recherche : on vous alerte dès qu'une parcelle <b>bascule</b> et correspond à vos critères.</p>
      <div className="mt-2 flex gap-1.5">
        <input data-nl-critere value={nlText}
          onChange={(e) => { setNlText(e.target.value); setNlRefus(null) }}
          onKeyDown={(e) => { if (e.key === 'Enter' && nlText.trim().length >= 3) nl.mutate() }}
          placeholder="Décrivez : « les grandes parcelles à Saint-Paul qui passent en Priorité »"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button data-nl-go onClick={() => nlText.trim().length >= 3 && nl.mutate()} disabled={nlText.trim().length < 3 || nl.isPending}
          className="shrink-0 rounded border border-mint/50 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">
          {nl.isPending ? '…' : 'Traduire'}</button>
      </div>
      {nlResume && (
        <p data-nl-resume className="mt-1 rounded-md border border-mint/40 bg-mint/[0.07] px-2 py-1 text-[10.5px] leading-snug text-mint">
          ✓ {nlResume} <span className="text-txt-dim">— vérifiez/ajustez les filtres, puis « + Critère ».</span>
        </p>
      )}
      {nlRefus && (
        <p data-nl-refus className="mt-1 rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2 py-1 text-[10.5px] leading-snug text-st-creuser">{nlRefus}</p>
      )}
      {(criteres.data ?? []).map((v) => (
        <div key={v.id} className="mt-1.5 flex items-center gap-2 text-[11px]">
          <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
          <button onClick={() => del.mutate(v.id)} aria-label="Supprimer le critère"
            className="flex h-5 w-5 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">×</button>
        </div>
      ))}
      {/* exemples = déclencheurs RÉELS uniquement (M16-B4, inchangé) */}
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <span className="text-[10px] text-txt-dim">Suivre, par exemple :</span>
        <button data-critere-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, tiers: ['chaude'] }); setNomCritere('Parcelles qui passent en À suivre') }}
          className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">parcelles qui passent en À suivre</button>
        <button data-critere-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, evenement: true }); setNomCritere('Nouvelles procédures BODACC') }}
          className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">nouvelle procédure BODACC</button>
      </div>
      <div className="mt-1.5 flex gap-1.5">
        <input value={nomCritere} onChange={(e) => setNomCritere(e.target.value)} placeholder="Nommez ce critère…"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button onClick={() => nomCritere.trim() && add.mutate()} disabled={!nomCritere.trim()}
          className="rounded bg-mint px-2 text-[11px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">+ Critère</button>
      </div>
    </div>
  )
}

// ── Veille externe — les annonces Radar : créer + gérer ses veilles (back type 'radar' réutilisé). ──
const V_COMMUNES = CP_COMMUNES.map(([, nom]) => nom).sort((a, b) => a.localeCompare(b, 'fr'))
const V_TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain'], ['immeuble', 'Immeuble']] as const
const V_EVENTS = [['nouvelle', 'Nouvelle annonce'], ['baisse', 'Baisse de prix'], ['retour', 'Retour en ligne']] as const

function resumeVeille(v: RadarVeille): string {
  const c = v.criteria as Record<string, unknown>
  const bouts: string[] = []
  if (v.commune) bouts.push(String(v.commune))
  if (c.type_bien) bouts.push(String(c.type_bien))
  if (c.prix_min || c.prix_max) bouts.push(`${c.prix_min ? Number(c.prix_min).toLocaleString('fr-FR') : '0'}–${c.prix_max ? Number(c.prix_max).toLocaleString('fr-FR') + ' €' : '∞'}`)
  if (c.surface_terrain_min) bouts.push(`terrain ≥ ${c.surface_terrain_min} m²`)
  if (c.particulier_only) bouts.push('particulier')
  return bouts.length ? bouts.join(' · ') : 'Tous les biens'
}

function VeilleExterne() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['radar-veilles'], queryFn: getRadarVeilles })
  const veilles = q.data?.veilles ?? []
  const [commune, setCommune] = useState('')
  const [type, setType] = useState('')
  const [prixMin, setPrixMin] = useState('')
  const [prixMax, setPrixMax] = useState('')
  const [surfMin, setSurfMin] = useState('')
  const [particulier, setParticulier] = useState(false)
  const [events, setEvents] = useState<string[]>(['nouvelle', 'baisse', 'retour'])
  const inval = () => qc.invalidateQueries({ queryKey: ['radar-veilles'] })
  const creer = useMutation({
    mutationFn: () => creerRadarVeille({
      commune: commune || undefined, type_bien: type || undefined,
      prix_min: prixMin ? Number(prixMin) : undefined, prix_max: prixMax ? Number(prixMax) : undefined,
      surface_terrain_min: surfMin ? Number(surfMin) : undefined,
      particulier_only: particulier || undefined, evenements: events,
    }),
    onSuccess: () => { inval(); setCommune(''); setType(''); setPrixMin(''); setPrixMax(''); setSurfMin(''); setParticulier(false) },
  })
  const suppr = useMutation({ mutationFn: (id: number) => supprimerRadarVeille(id), onSuccess: inval })
  const toggleEvent = (e: string) => setEvents((p) => p.includes(e) ? p.filter((x) => x !== e) : [...p, e])
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
      <p className="text-[10.5px] leading-snug text-txt-mut">
        Une veille sur les annonces produit une <b className="text-txt">alerte de fin de journée</b> quand un bien
        neuf, une baisse ou un retour correspond à vos critères. Des faits et un lien — jamais le contenu de l’annonce.
      </p>

      {/* création */}
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-2.5">
        <p className="label-caps">Nouvelle veille</p>
        <div className="grid grid-cols-2 gap-1.5">
          <select data-veille-ext-commune value={commune} onChange={(e) => setCommune(e.target.value)} className={sel}>
            <option value="">Toute l’île</option>
            {V_COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={type} onChange={(e) => setType(e.target.value)} className={sel}>
            {V_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input type="number" min={0} placeholder="prix min" value={prixMin} onChange={(e) => setPrixMin(e.target.value)} className={`min-w-0 ${sel}`} />
          <input type="number" min={0} placeholder="prix max" value={prixMax} onChange={(e) => setPrixMax(e.target.value)} className={`min-w-0 ${sel}`} />
          <input type="number" min={0} placeholder="surface terrain min" value={surfMin} onChange={(e) => setSurfMin(e.target.value)} className={`col-span-2 min-w-0 ${sel}`} />
        </div>
        <label className="flex items-center gap-2 text-[11.5px] text-txt-mut">
          <input type="checkbox" checked={particulier} onChange={(e) => setParticulier(e.target.checked)} className="h-3.5 w-3.5 accent-mint" />
          Particuliers seulement
        </label>
        <div className="flex flex-wrap gap-1.5">
          {V_EVENTS.map(([v, l]) => (
            <button key={v} data-veille-ext-event={v} onClick={() => toggleEvent(v)}
              className={`rounded-full border px-2 py-1 text-[11px] ${events.includes(v) ? 'border-mint/50 text-mint' : 'border-line-2 text-txt-mut'}`}>{l}</button>
          ))}
        </div>
        <button data-veille-ext-creer disabled={creer.isPending || events.length === 0} onClick={() => creer.mutate()}
          className="rounded-md bg-mint py-1.5 text-[12px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {creer.isPending ? 'Création…' : creer.isSuccess ? '✓ Veille créée' : 'Créer la veille'}
        </button>
        {events.length === 0 && <p className="text-[10px] text-st-ecartee">Cochez au moins un événement.</p>}
      </div>

      {/* liste */}
      <div className="flex flex-col gap-1.5">
        <p className="label-caps">Mes veilles annonces <span className="text-txt-dim">· {veilles.length}</span></p>
        {q.isLoading && <p className="text-[11px] text-txt-dim">Chargement…</p>}
        {!q.isLoading && veilles.length === 0 && <p className="text-[11px] leading-snug text-txt-dim">Aucune veille annonce. Créez-en une ci-dessus.</p>}
        {veilles.map((v) => (
          <div key={v.id} data-veille-ext-item className="flex items-start gap-2 rounded-lg border border-line-2 px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] text-txt">{resumeVeille(v)}</div>
              <div className="mt-0.5 text-[10px] text-txt-dim">{((v.criteria as Record<string, unknown>).evenements as string[] ?? []).map((e) => V_EVENTS.find(([k]) => k === e)?.[1] ?? e).join(' · ')}</div>
            </div>
            <button onClick={() => suppr.mutate(v.id)} className="shrink-0 text-[11px] text-txt-mut hover:text-st-ecartee">supprimer</button>
          </div>
        ))}
      </div>
    </div>
  )
}
