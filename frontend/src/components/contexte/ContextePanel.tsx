import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { deleteCommuneContact, getCommuneAcquisitions, getCommuneContacts, getContexteCommune, getMoi, motMarcheCommune, motRarete, postCommuneContact } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { Trace } from '../../lib/trace'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { CONTACT_VIDE, ContactEdit, trimContact, type ContactForm } from '../shared/ContactEdit'  // RETOURS-8 (R6)
import { Chevron } from '../ui/Chevron'
import { GrilleOutils, OutilCase } from '../shared/GrilleOutils'   // COMMUNE-FIX-1 (C9) — grille d'outils PARTAGÉE (même rendu que la fiche parcelle)

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))
const fmtV = (v: unknown, s = '') => (v == null ? '—' : `${Number(v).toLocaleString('fr-FR')}${s}`)
const fmtDec = (n: number | null | undefined, s = '') => (n == null ? '—' : `${Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}${s}`)

function RowT({ lbl, val, strong }: { lbl: string; val: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-0.5">
      <span className="min-w-0 text-txt-mut">{lbl}</span>
      <span className={`tnum shrink-0 text-right ${strong ? 'font-semibold text-mint' : 'text-txt'}`}>{val}</span>
    </div>
  )
}

//: statut SRU → couleur + lecture métier (une phrase sobre — le ciblage de la promotrice)
const SRU_META: Record<string, { color: string; label: string; lecture: string }> = {
  carencee: { color: TOKENS.stEcartee, label: 'CARENCÉE',
    lecture: 'Commune en carence SRU : forte pression de production de logement social — les programmes avec part LLS y sont attendus (et souvent facilités).' },
  deficitaire: { color: TOKENS.stCreuser, label: 'DÉFICITAIRE',
    lecture: 'Sous l’objectif légal : la commune doit produire du logement social — un programme mixte y répond à une obligation réelle.' },
  exemptee: { color: TOKENS.txtMut, label: 'EXEMPTÉE 2023-2025',
    lecture: 'Soumise SRU mais exemptée d’obligations sur la période (décret) — pression de production sociale suspendue.' },
  conforme: { color: TOKENS.stChaude, label: 'CONFORME',
    lecture: 'Objectif SRU atteint — pas de pression réglementaire de rattrapage social.' },
}

function Source({ nom, url }: { nom?: string | null; url?: string | null }) {
  if (!nom) return null
  return (
    <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">
      Source :{' '}
      {url ? <a href={url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{nom} ↗</a> : nom}
    </p>
  )
}

function Bar({ parts }: { parts: { label: string; pct: number; color: string }[] }) {
  return (
    <div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-line">
        {parts.map((p) => <span key={p.label} style={{ width: `${p.pct}%`, background: p.color }} />)}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-1 text-[11px] text-txt-mut">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: p.color }} />{p.label} {p.pct.toLocaleString('fr-FR')} %
          </span>
        ))}
      </div>
    </div>
  )
}

// OUTILS-6 C4 — l'accordéon. Son état ouvert/fermé est MÉMORISÉ d'une fiche à l'autre (localStorage,
// par identifiant de section) : un client retrouve ses sections de prédilection. `dot` = pastille de
// signal (couleur), `cle` = le chiffre-clé porté SUR LA LIGNE FERMÉE (on lit l'essentiel sans ouvrir).
const ACC_LS = 'labuse.fiche.acc'
function readAcc(id: string, def: boolean): boolean {
  try { const o = JSON.parse(localStorage.getItem(ACC_LS) || '{}'); return typeof o[id] === 'boolean' ? o[id] : def }
  catch { return def }
}
function writeAcc(id: string, v: boolean) {
  try { const o = JSON.parse(localStorage.getItem(ACC_LS) || '{}'); o[id] = v; localStorage.setItem(ACC_LS, JSON.stringify(o)) }
  catch { /* localStorage indisponible — l'accordéon reste fonctionnel, sans mémoire */ }
}
// K2 — une ligne de coordonnée mairie : valeur, lien optionnel, ou « Absent » (jamais inventé).
function MairieLigne({ label, val, href }: { label: string; val: string | null; href?: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-[74px] shrink-0 text-txt-dim">{label}</dt>
      <dd className="min-w-0 flex-1 break-words text-txt">
        {val == null ? <span className="italic text-txt-dim">Absent</span>
          : href ? <a href={href} target="_blank" rel="noreferrer" className="text-mint hover:underline">{val}</a> : val}
      </dd>
    </div>
  )
}

function fmtDateFr(iso: string): string {
  try { return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(iso)) }
  catch { return iso }
}

// ADMIN-1 (AD10) — contacts NOMMÉS de la commune, servis sous le standard officiel de la carte Mairie.
// Lecture ouverte à tous les comptes ; l'ajout/suppression n'est proposé qu'à l'admin (getMoi.role).
function ContactsMairie({ insee, commune }: { insee: string | null; commune: string }) {
  const qc = useQueryClient()
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const admin = moi.data?.role === 'admin'
  const q = useQuery({ queryKey: ['commune-contacts', insee], queryFn: () => getCommuneContacts(insee!), enabled: !!insee })
  const [ajout, setAjout] = useState(false)
  const invalider = () => qc.invalidateQueries({ queryKey: ['commune-contacts', insee] })
  // RETOURS-8 (R6) — même geste d'ajout que la page admin Contacts (composant ContactEdit partagé).
  const creer = useMutation({
    mutationFn: (f: ContactForm) => postCommuneContact({ insee: insee!, commune_nom: commune, ...trimContact(f) }),
    onSuccess: () => { setAjout(false); invalider() },
  })
  const suppr = useMutation({ mutationFn: (id: number) => deleteCommuneContact(id), onSuccess: invalider })
  const contacts = q.data?.contacts ?? []
  if (!insee) return null
  return (
    <div className="mt-2.5 border-t border-line pt-2">
      {contacts.map((c) => (
        <div key={c.id} className="mb-1.5 text-[12px]">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <b className="text-txt">{c.nom}</b>{c.role && <span className="ml-1.5 rounded bg-mint/12 px-1.5 py-0.5 text-[10px] text-mint">{c.role}</span>}
              <div className="mt-0.5 text-txt-mut">
                {c.telephone && <a href={`tel:${c.telephone.replace(/\s/g, '')}`} className="text-mint hover:underline">{c.telephone}</a>}
                {c.telephone && c.email && '  ·  '}
                {c.email && <a href={`mailto:${c.email}`} className="text-mint hover:underline">{c.email}</a>}
              </div>
              {c.note && <div className="mt-0.5 text-[10.5px] text-txt-dim">note : {c.note}</div>}
            </div>
            {admin && (
              <button onClick={() => { if (window.confirm(`Supprimer « ${c.nom} » ?`)) suppr.mutate(c.id) }}
                className="shrink-0 text-[11px] text-coral hover:underline">🗑</button>
            )}
          </div>
        </div>
      ))}
      {admin && !ajout && (
        <button onClick={() => setAjout(true)} className="mt-1 text-[11.5px] text-mint hover:underline">+ Ajouter un contact</button>
      )}
      {admin && ajout && (
        <ContactEdit init={CONTACT_VIDE} busy={creer.isPending}
          onCancel={() => setAjout(false)} onSave={(f) => creer.mutate(f)} />
      )}
    </div>
  )
}

// COMMUNE-FIX-1 (D13) — LES ACQUÉREURS RÉCENTS (PM) de la commune, servis par l'endpoint dédié
// /communes/{c}/acquisitions-pm (même point de calcul que l'outil Communes) — l'endpoint existait mais
// n'avait plus de carte sur la fiche. On montre les 5 premiers acquéreurs (par volume), chacun ouvre
// Scan patrimoine (m02Prefill + module 'patrimoine'). Constat sourcé (changement de millésime PM,
// n'affirme pas une vente), hors scoring.
function AcquereursPmCommune({ commune }: { commune: string }) {
  const q = useQuery({ queryKey: ['commune-acq', commune], queryFn: () => getCommuneAcquisitions(commune, 200), enabled: !!commune })
  const d = q.data
  if (!d || !d.acquisitions?.length) return null
  const parAcq = new Map<string, { siren: string | null; nom: string | null; n: number; dernier: number }>()
  for (const a of d.acquisitions) {
    const cle = a.siren_apres ?? '∅'
    const g = parAcq.get(cle)
    if (g) { g.n += 1; g.dernier = Math.max(g.dernier, a.a_millesime) }
    else parAcq.set(cle, { siren: a.siren_apres, nom: a.denomination_apres, n: 1, dernier: a.a_millesime })
  }
  const top = [...parAcq.values()].sort((x, y) => y.n - x.n || y.dernier - x.dernier).slice(0, 5)
  const ouvrirScan = (siren: string) => { const s = useApp.getState(); s.setM02Prefill(siren); s.setModule('patrimoine'); s.setContexteCommune(null) }
  return (
    <div className="mt-2 border-t border-line pt-2">
      <p className="mb-1 text-[11px] text-txt-dim">Acquéreurs récents (personnes morales) <span className="text-txt-mut">depuis {d.depuis_millesime}</span></p>
      <div className="flex flex-col gap-0.5 text-[12px]">
        {top.map((g) => (
          g.siren
            ? <button key={g.siren} data-acquereur-pm onClick={() => ouvrirScan(g.siren!)}
                className="flex items-baseline justify-between gap-2 py-0.5 text-left hover:text-mint">
                <span className="min-w-0 truncate">{g.nom ?? g.siren}</span>
                <span className="tnum shrink-0 text-txt-mut">{g.n} parc. · {g.dernier}</span>
              </button>
            : <div key="anon" className="flex items-baseline justify-between gap-2 py-0.5 text-txt-mut">
                <span className="min-w-0 truncate">Acquéreur non identifié</span><span className="tnum shrink-0">{g.n} parc.</span>
              </div>
        ))}
      </div>
      {d.n_total > top.length && (
        <button data-acquereurs-scan onClick={() => { const s = useApp.getState(); s.setCommune(commune); s.setModule('communes'); s.setCommunesTableOpen(true); s.setContexteCommune(null) }}
          className="mt-1 text-[11px] text-mint hover:underline">Tous les acquéreurs ({d.n_total}) dans l'outil Communes</button>
      )}
      <p className="mt-1 text-[10px] leading-snug text-txt-dim">{d.source ?? 'Fichiers fonciers (changement de propriétaire PM entre millésimes) — un constat, pas une vente affirmée.'}</p>
    </div>
  )
}

// OUTILS-6 C6 — ouvrir un outil AVEC LA COMMUNE DÉJÀ SÉLECTIONNÉE (jamais un formulaire vide). On pose la
// commune (filtre global lu par la plupart des outils) puis on ouvre le module et on ferme la fiche.
function ouvrirOutil(commune: string, insee: string | null, quoi: string) {
  const s = useApp.getState()
  s.setCommune(commune)
  s.setCommunesFilter([commune])
  if (quoi === 'plu') { if (insee) s.setPluPrefill({ insee, zone: null }); s.setModule('plu') }
  else if (quoi === 'radar') { s.openRadar() }
  else if (quoi === 'communes') { s.setModule('communes'); s.setCommunesTableOpen(true) }
  else { s.setModule(quoi) }
  s.setContexteCommune(null)
}

// FICHE-COMMUNE-2 (C2) — la MÊME grammaire que la fiche parcelle : une LIGNE-CARTE (fond carte, bordure,
// coins arrondis, icône à gauche, titre + sous-titre, valeur ou badge à droite, chevron). Fermée, elle dit
// déjà l'essentiel ; un clic ouvre son détail (rien de perdu d'OUTILS-6). L'état ouvert/fermé est mémorisé.
const TON_COL: Record<string, string> = { vert: TOKENS.mint, orange: TOKENS.stCreuser, rouge: TOKENS.stEcartee, violet: 'var(--iris)' }
function LigneCarte({ id, ic, titre, sous, val, ton, badge, defaultOpen, chiffre, children }: {
  id: string; ic: string; titre: string; sous?: string; val?: string | null
  ton?: 'vert' | 'orange' | 'rouge' | 'violet'; badge?: boolean; defaultOpen?: boolean
  // CIRCUIT-1 lot 7.2 — chiffre_id du registre : traçage allumé, la valeur porte son étiquette.
  chiffre?: string; children: React.ReactNode
}) {
  const [open, setOpen] = useState(() => readAcc(id, !!defaultOpen))
  const col = ton ? TON_COL[ton] : undefined
  return (
    <details data-acc={id} open={open} className="group mb-2"
      onToggle={(e) => { const o = (e.currentTarget as HTMLDetailsElement).open; setOpen(o); writeAcc(id, o) }}>
      {/* RETOURS-6 U2 — survol PLEIN (aplat vert dégradé, encre sombre) via .hover-fill, comme partout ailleurs :
          titre, sous-ligne, valeur/chip de droite et chevron s'inversent en encre sombre (`* { color: ink }`).
          Une carte de la fiche commune sent la même main que les cases d'outils et les lignes de la fiche parcelle. */}
      <summary data-ligne-carte={id} className="hover-fill flex cursor-pointer list-none items-center gap-2.5 rounded-xl border border-line-2 bg-surface-2 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
        {/* `lc-ic` : au survol plein, le carré d'icône s'éclaircit (aplat ink translucide) pour que le glyphe
            passé en encre sombre reste lisible — sinon sombre-sur-sombre. Réglé dans index.css (gaté pointeur fin). */}
        <span className="lc-ic flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line-2 bg-surface-3 text-[14px] text-txt-mut">{ic}</span>
        <span className="min-w-0 flex-1">
          <b className="block text-[13px] font-semibold text-txt-hi">{titre}</b>
          {sous && <span className="block truncate text-[11px] text-txt-mut">{sous}</span>}
        </span>
        {val != null && val !== '' && (() => {
          const rendu = badge
            ? <span className="shrink-0 rounded-md border px-1.5 py-0.5 text-[11px] font-medium" style={{ color: col, borderColor: `${col}55`, background: `${col}1a` }}>{val}</span>
            : <span className="shrink-0 text-[12.5px] font-semibold" style={col ? { color: col } : undefined}>{val}</span>
          return chiffre ? <Trace id={chiffre}>{rendu}</Trace> : rendu
        })()}
        <Chevron open={open} className="shrink-0" />
      </summary>
      <div className="mb-1 mt-1.5 rounded-lg border border-line-2 bg-surface-1 px-3 py-2.5">{children}</div>
    </details>
  )
}

// PROJETS-V5 (E11) — aligné sur le libellé de groupe de la FICHE PARCELLE (`.sec` DA-FICHE-v6) :
// mono 10px UPPERCASE tracking .13em + filet horizontal — pour que les deux fiches sentent la même main.
function GroupeLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 mt-5 flex items-center gap-2 px-1">
      <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.13em] text-txt-dim">{children}</span>
      <span className="h-px flex-1 bg-line-2" />
    </div>
  )
}

/** FICHE COMMUNE (OUTILS-6) — un en-tête qui décide + des accordéons ordonnés selon la question d'un
 *  promoteur (constat → action → contexte). Chaque section porte son chiffre-clé sur la ligne fermée, sa
 *  ligne de sources datées, et — quand c'est utile — une passerelle vers l'outil pré-rempli sur la commune.
 *  Un seul moteur, une seule donnée : tout vient du payload `getContexteCommune` (aucun chiffre en dur). */
export function ContextePanel() {
  const { contexteCommune, setContexteCommune } = useApp()
  const q = useQuery({ queryKey: ['contexte', contexteCommune], queryFn: () => getContexteCommune(contexteCommune!), enabled: !!contexteCommune })
  const rar = useQuery({ queryKey: ['communes-rarete'], queryFn: motRarete, enabled: !!contexteCommune })
  const mar = useQuery({ queryKey: ['mu-marche', contexteCommune], queryFn: () => motMarcheCommune(contexteCommune!), enabled: !!contexteCommune })
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setContexteCommune(null)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setContexteCommune])
  if (!contexteCommune) return null
  const d = q.data
  const r = (rar.data?.communes ?? []).find((c) => (c as Record<string, unknown>)['commune'] === contexteCommune) as Record<string, any> | undefined
  // FICHE-COMMUNE-2 (C2) — `market_signal` (« prudence ») N'EST PLUS servi en badge : remplacé par
  // `d.signaux` (règles nommées). On garde les lignes du même moteur Marché commune pour la tendance.
  const signauxNommes = d?.signaux ?? []
  // tendance / liquidité : lues sur les lignes du MÊME moteur Marché commune (build_marche_commune)
  const marLignes = (mar.data?.['lignes'] ?? []) as Record<string, any>[]
  const ligneMar = (cle: string) => marLignes.find((l) => l['cle'] === cle)?.['valeurs'] as Record<string, any> | undefined
  // COMMUNE-RANGEMENT-1 (lot 1) — la tendance 12 mois se lit sur `delta_pct`, LA clé émise par le moteur
  // Marché commune (`build_marche_commune`, `ligne4_tendance` → `valeurs.delta_pct`) et déjà lue par
  // l'outil Marché (moteurs.tsx). L'ancien `tend['pct']` n'existait nulle part → la tendance ne
  // s'affichait jamais. Absente (fenêtre sous le seuil DVF) → `delta_pct` manque et rien n'est rendu.
  const tend = ligneMar('tendance_12m')
  const tendPct = tend?.['delta_pct'] as number | null | undefined
  const commune = contexteCommune
  const insee = d?.insee ?? null

  return (
    <aside data-contexte-panel className="absolute right-0 top-0 z-30 flex h-full w-[420px] flex-col border-l border-line bg-surface-1 shadow-elev-3">
      <div className="flex shrink-0 items-start justify-between border-b border-line px-5 py-3">
        <div className="min-w-0">
          <p className="label-caps text-txt-mut">Fiche commune</p>
          <div className="flex flex-wrap items-center gap-2">
            {/* FICHE-COMMUNE-2 (C2) — le badge « signal : prudence » est RETIRÉ (boîte noire sans règle
                lisible, market_signal score<40). Les signaux nommés (règle en constante) le remplacent, en puces plus bas. */}
            <h2 className="font-display text-lg font-bold text-txt-hi">{commune}</h2>
          </div>
          {d?.epci && <p className="text-[10.5px] text-txt-mut">{d.epci} — {d.epci_nom}</p>}
          {d?.foncier && (
            <p className="mt-0.5 text-[10.5px] text-txt-dim">{fmt(d.foncier.surface_ha)} ha · {fmt(d.foncier.n_parcelles)} parcelles</p>
          )}
        </div>
        <button onClick={() => setContexteCommune(null)} className="shrink-0 text-txt-dim hover:text-txt-hi" aria-label="Fermer">✕</button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {q.isLoading && <div className="p-5"><Squelette lignes={5} /></div>}
        {q.isError && <ErrorState className="p-5" message="Erreur de chargement — réessayez." retry={() => q.refetch()} />}
        {d && (
          <>
            {/* ── EN-TÊTE (maquette v1) — bandeau 6 chiffres en 3×3 + 3 raccourcis. Pas de rang comparatif. ── */}
            <div className="border-b border-line bg-surface-2/40 px-5 py-3">
              <div data-bandeau-chiffres className="grid grid-cols-3 gap-2">
                {[
                  { v: `${fmt(d.foncier?.n_parcelles)}`, n: 'Parcelles', s: 'Cadastre' },
                  // COHERENCE-FIX-1 (lot E) — l'année de la population légale au client, partout.
                  { v: d.population?.habitants != null ? `${fmt(d.population.habitants)}` : '—', n: 'Habitants',
                    s: d.population?.habitants_millesime ? `INSEE ${d.population.habitants_millesime}` : 'INSEE' },
                  { v: `${fmt(d.permis_bloc?.permis_12m)}`, n: 'Permis / an', s: 'SITADEL' },
                  { v: d.comparable?.ancien_median_eur_m2 != null ? `${fmt(d.comparable.ancien_median_eur_m2)} €/m²` : '—', n: 'Prix ancien', s: 'DVF' },
                  { v: tendPct != null ? `${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %` : '—', n: 'Tendance 12 m', s: 'DVF' },
                  { v: d.plu_statut?.statut ?? '—', n: 'État du PLU', s: 'GPU · Sudocuh' },
                ].map((c) => (
                  <div key={c.n} className="rounded-lg bg-surface-3 px-2.5 py-1.5">
                    <p className="tnum font-display text-[14px] font-bold leading-tight text-txt-hi">{c.v}</p>
                    <p className="mt-0.5 text-[9.5px] uppercase tracking-[0.04em] text-txt-mut">{c.n}</p>
                    <p className="text-[9px] text-txt-dim">{c.s}</p>
                  </div>
                ))}
              </div>
              {/* RETOURS-15 C10 — le bouton « Voir ses parcelles → » est RETIRÉ de la fiche commune. */}
              {/* COMMUNE-FIX-1 (C9) — « Étudier cette commune » : le MÊME composant partagé que la section
                  « Étudier ce bien » de la fiche parcelle (GrilleOutils/OutilCase, tuiles icône+nom, survol
                  vert plein). Tuiles pré-remplies sur la commune (ouvrirOutil pose commune + module).
                  RETOURS-15 C10 — la tuile « Densifier » est RETIRÉE de « Étudier cette commune ». */}
              <div data-etudier-commune className="mt-3">
                <p className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.13em] text-txt-dim">Étudier cette commune</p>
                <GrilleOutils>
                  <OutilCase ic="§" nom="PLU" data-tuile-plu onClick={() => ouvrirOutil(commune, insee, 'plu')} />
                  <OutilCase ic="▤" nom="Permis" data-tuile-permis onClick={() => ouvrirOutil(commune, insee, 'permis')} />
                  <OutilCase ic="◎" nom="Étude de zone" data-tuile-etude-zone onClick={() => ouvrirOutil(commune, insee, 'etude-zone')} />
                  <OutilCase ic="▦" nom="Communes" data-tuile-communes onClick={() => ouvrirOutil(commune, insee, 'communes')} />
                </GrilleOutils>
              </div>
              {signauxNommes.length > 0 && (
                <div data-fiche-signaux className="mt-3">
                  <p className="label-caps text-txt-dim">Signaux</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {signauxNommes.map((s) => {
                      const col = s.ton === 'rouge' ? TOKENS.stEcartee : TOKENS.stCreuser
                      return (
                        <span key={s.code} data-fiche-signal={s.code}
                          className="rounded-md border px-2 py-0.5 text-[11px] font-medium"
                          style={{ color: col, borderColor: `${col}55`, background: `${col}1a` }}>{s.libelle}</span>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {d.rnu && (
              <div data-rnu-bandeau className="border-b border-line px-5 py-3">
                <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.10] px-3 py-2.5">
                  <p className="flex items-center gap-1.5 text-[12.5px] font-semibold text-st-creuser"><span aria-hidden>⚑</span>{d.rnu.libelle}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-txt">{d.rnu.detail}</p>
                </div>
              </div>
            )}

            {/* ── 5 GROUPES · 10 CARTES (maquette v1). Les 70 lignes des 19 cartes d'avant, redistribuées
                par NATURE d'information. La grammaire LigneCarte (accordéon mémorisé) reste. ── */}
            <div className="px-5 pt-3">

              {/* ═══ LE TERRITOIRE ═══ */}
              <GroupeLabel>Le territoire</GroupeLabel>

              <LigneCarte id="identite" ic="I" titre="Identité"
                sous={`${d.epci ?? ''}${d.population?.quartiers ? ` · ${d.population.quartiers.n_iris} IRIS` : ''}`}
                val={insee ?? undefined}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Intercommunalité" val={d.epci ?? '—'} />
                  {d.epci_nom && <p className="-mt-0.5 mb-0.5 text-[10.5px] text-txt-dim">{d.epci_nom}</p>}
                  {d.population?.quartiers && (
                    <RowT lbl={`Par quartier (${d.population.quartiers.n_iris} IRIS)`}
                      val={`vacance ${fmtDec(d.population.quartiers.vacance_min_pct)} → ${fmtDec(d.population.quartiers.vacance_max_pct)} % (méd. ${fmtDec(d.population.quartiers.vacance_mediane_pct)} %)`} />
                  )}
                </div>
                {d.mairie && (
                  <div className="mt-2 border-t border-line pt-2">
                    <dl className="space-y-1.5 text-[12px]">
                      <MairieLigne label="Adresse" val={[d.mairie.adresse, [d.mairie.code_postal, d.mairie.commune].filter(Boolean).join(' ')].filter(Boolean).join(', ') || null} />
                      <MairieLigne label="Téléphone" val={d.mairie.telephone} href={d.mairie.telephone ? `tel:${d.mairie.telephone.replace(/\s/g, '')}` : undefined} />
                      <MairieLigne label="E-mail" val={d.mairie.email} href={d.mairie.email ? `mailto:${d.mairie.email}` : undefined} />
                      <MairieLigne label="Site officiel" val={d.mairie.site_officiel} href={d.mairie.site_officiel ?? undefined} />
                      <MairieLigne label="Annuaire" val={d.mairie.url_annuaire ? 'Fiche service-public' : null} href={d.mairie.url_annuaire ?? undefined} />
                    </dl>
                    <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{d.mairie.source}{d.mairie.date_import ? ` · relevé le ${fmtDateFr(d.mairie.date_import)}` : ''}</p>
                    <ContactsMairie insee={insee} commune={commune} />
                  </div>
                )}
                <Source nom="INSEE · IGN contours IRIS · Annuaire de l'administration" />
              </LigneCarte>

              {/* RETOURS-15 C10 — toutes les sections FERMÉES par défaut (plus de defaultOpen). */}
              <LigneCarte id="population" chiffre="habitants_n" ic="P" titre="Population et logement"
                sous={`${d.population.logements != null ? `${fmt(d.population.logements)} logts` : ''}${d.population.vacance_pct != null ? ` · ${fmtDec(d.population.vacance_pct)} % vacants` : ''} · INSEE`}
                val={d.population.habitants != null ? `${fmt(d.population.habitants)} hab.` : null}>
                <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                  {/* COMMUNE-FIX-1 (A1) — habitants = population LÉGALE (municipale) INSEE, plus l'agrégat
                      Filosofi qui sous-estimait ; ménages = résidences principales (RP). Filosofi ne sert
                      plus QUE le niveau de vie. */}
                  {d.population.habitants != null && <RowT lbl="Habitants (population municipale)" val={fmt(d.population.habitants)} strong />}
                  {/* COHERENCE-FIX-1 (lot E) — l'étiquette du back (« Population légale 2023 (INSEE) ») :
                      la source et SON année, jamais un chiffre daté sans date. */}
                  {(d.population.habitants_etiquette || d.population.habitants_millesime) && <p className="-mt-0.5 mb-0.5 text-[10.5px] text-txt-dim">{d.population.habitants_etiquette ?? `Population municipale légale INSEE · millésime ${d.population.habitants_millesime}`}{d.population.habitants_pop_totale != null ? ` · population totale ${fmt(d.population.habitants_pop_totale)}` : ''}</p>}
                  {d.population.menages != null && <RowT lbl="Ménages (résidences principales)" val={fmt(d.population.menages)} />}
                  {d.population.niveau_vie_moyen_eur != null && <RowT lbl="Niveau de vie moyen (Filosofi)" val={`${fmt(d.population.niveau_vie_moyen_eur)} €/an`} />}
                  {d.population.logements != null && <RowT lbl="Logements" val={`${fmt(d.population.logements)}${d.population.vacants != null ? ` · ${fmt(d.population.vacants)} vacants (${fmtDec(d.population.vacance_pct)} %)` : ''}`} />}
                  {/* DONNEES-1 lot 2.4 — âge du parc (RP2022) : part construit avant 1991 = stock ancien. */}
                  {d.population.parc_ancien_pct != null && <RowT lbl="Parc construit avant 1991" val={`${fmtDec(d.population.parc_ancien_pct)} %`} />}
                  {d.parc_social?.logements != null && <RowT lbl="Parc social (RPLS)" val={`${fmt(d.parc_social.logements)} logts${d.parc_social.construct_median != null ? ` · constr. médiane ${d.parc_social.construct_median}` : ''}`} />}
                </div>
                {d.marche && (
                  <div className="mb-2 flex flex-col gap-2.5">
                    {(() => {
                      const loc = Number(d.marche.locataires_pct); const prop = Number(d.marche.proprietaires_pct)
                      const autres = (d.marche as any).autres_loges_pct != null
                        ? Number((d.marche as any).autres_loges_pct)
                        : Math.max(0, Math.round((100 - loc - prop) * 10) / 10)
                      return <Bar parts={[
                        { label: 'locataires', pct: loc, color: TOKENS.vizCyan },
                        { label: 'propriétaires', pct: prop, color: TOKENS.mint },
                        ...(autres >= 1 ? [{ label: 'logés gratuitement', pct: autres, color: TOKENS.txtMut }] : []),
                      ]} />
                    })()}
                    <Bar parts={[
                      { label: 'maisons', pct: Number(d.marche.maisons_pct), color: TOKENS.stSurveiller },
                      { label: 'appartements', pct: Number(d.marche.apparts_pct), color: TOKENS.vizCyan },
                    ]} />
                  </div>
                )}
                {/* Parc social / SRU — taux et objectif (maquette : « Parc social RPLS, taux SRU, objectif »). */}
                {d.sru && (() => {
                  const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                  const nbLls = d.sru.detail?.nb_lls
                  const taux = Number(d.sru.taux_lls)
                  // COMMUNE-FIX-1 (A3) — la base du taux SRU est le nombre de RÉSIDENCES PRINCIPALES
                  // (base légale SRU), pas les ménages Filosofi ni le parc de logements : on la reconstitue
                  // (nb_lls / taux) et on l'écrit, pour que 7 499 LLS et 18,33 % soient lus cohéremment.
                  const baseSru = (nbLls != null && taux > 0) ? Math.round(nbLls / (taux / 100)) : null
                  return (
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: `${m.color}14` }}>
                      <span className="font-display text-[13px] font-bold" style={{ color: m.color }}>SRU {taux.toLocaleString('fr-FR')} %</span>
                      <span className="ml-2 text-[11px] text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %</span>
                      {nbLls != null && (
                        <p className="mt-1 text-[11px] text-txt"><b>{fmt(nbLls)} logements sociaux (LLS)</b> — stock au dernier inventaire SRU{d.sru.millesime ? ` · ${d.sru.millesime}` : ''}.</p>
                      )}
                      {baseSru != null && (
                        <p className="mt-0.5 text-[10.5px] text-txt-dim">Le taux de {taux.toLocaleString('fr-FR')} % rapporte ces LLS aux résidences principales retenues pour la SRU (≈ {fmt(baseSru)}) — base différente des ménages ci-dessus.</p>
                      )}
                      <p className="mt-1 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                    </div>
                  )
                })()}
                <Source nom={`${d.population.source}${d.parc_social ? ` · ${d.parc_social.source}` : ''} · Inventaire SRU (DHUP)`} />
              </LigneCarte>

              {/* ═══ LE MARCHÉ ═══ */}
              <GroupeLabel>Le marché</GroupeLabel>

              <LigneCarte id="marche" chiffre="prix_ancien_median_eur_m2" ic="↗" titre="Prix"
                sous={`ancien ${fmt(d.comparable?.ancien_median_eur_m2)} · neuf ${fmt(d.comparable?.neuf_eur_m2)} €/m²`}
                val={tendPct != null ? `${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %` : null}
                ton={tendPct != null && Number(tendPct) < 0 ? 'rouge' : 'vert'}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Ancien médian (commune entière)" val={`${fmt(d.comparable?.ancien_median_eur_m2)} €/m²`} strong />
                  <RowT lbl="Neuf VEFA (prix de sortie)" val={`${fmt(d.comparable?.neuf_eur_m2)} €/m²`} />
                  <RowT lbl="Neuf observé (ventes récentes)" val={d.prix_neuf_observe?.eur_m2 != null ? `${fmt(d.prix_neuf_observe.eur_m2)} €/m²` : '—'} />
                  {tendPct != null && <RowT lbl="Tendance 12 mois" val={`${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %`} />}
                </div>
                {d.foncier?.prix_terrain_nu.par_zone && (
                  <div className="mt-2 flex gap-5 border-t border-line pt-2">
                    {(['U', 'AU'] as const).map((fam) => {
                      const pz = d.foncier!.prix_terrain_nu.par_zone?.[fam]
                      return pz?.calculable
                        ? <div key={fam}><p className="font-display text-base font-bold text-txt-hi">{fmt(pz.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone {fam} · {fmt(pz.n)} ventes</p></div>
                        : <div key={fam}><p className="font-display text-sm text-txt-mut">zone {fam} —</p><p className="text-[10.5px] text-txt-dim">&lt; {d.foncier!.prix_terrain_nu.seuil_n} ventes</p></div>
                    })}
                  </div>
                )}
                {d.loyer && (
                  <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                    <RowT lbl={`Loyer médian${d.loyer.type ? ` (${d.loyer.type})` : ''}`} val={`${fmtDec(d.loyer.median_eur_m2)} €/m²`} strong />
                  </div>
                )}
                <Source nom={`DVF — médiane commune entière · terrain nu par zone PLU${d.loyer ? ` · ${d.loyer.source}` : ''}`} />
              </LigneCarte>

              {/* Activité — TOUJOURS présente ; sans annonce Radar, elle le dit. */}
              {(() => {
                const ma = d.marche_annonces
                const vide = !ma || ma.sous_seuil
                return (
                <LigneCarte id="annonces" chiffre="annonces_actives_n" ic="◉" titre="Activité"
                  sous={`${fmt(d.foncier?.mutations_12m)} mutations/12m${ma ? ` · ${fmt(ma.biens)} biens en vente` : ''}`}
                  val={ma && !ma.sous_seuil && ma.ecart_demande_acte_pct != null ? `${ma.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(ma.ecart_demande_acte_pct)} %` : null}
                  ton={ma?.ecart_demande_acte_pct != null && ma.ecart_demande_acte_pct < 0 ? 'vert' : undefined}>
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl="Mutations (12 mois, DVF)" val={fmt(d.foncier?.mutations_12m)} />
                  </div>
                  {vide ? (
                    <p data-annonces-sans-objet className="mt-1 text-[12px] text-txt-mut">Pas d'annonce repérée sur cette commune{ma ? ` (${ma.biens} bien(s), seuil ${ma.seuil_n})` : ''}. Le Radar affine la couverture au fil des relevés.</p>
                  ) : (
                    <>
                      {(() => {
                        // COMMUNE-FIX-1 (A2) — sous le seuil Radar (30 biens), on n'affiche NI médian NI
                        // pourcentage : « sous le seuil (N biens) », jamais un −31 % tiré de 5 annonces.
                        const n = ma!.prix_demande_n ?? 0
                        const sous = ma!.demande_sous_seuil
                        const libSeuil = `sous le seuil (${fmt(n)} bien${n > 1 ? 's' : ''})`
                        return (
                          <div className="flex flex-col gap-0.5 text-[12px]">
                            <RowT lbl="Biens en vente" val={fmt(ma!.biens)} />
                            <RowT lbl="Prix demandé médian" val={sous ? libSeuil : (ma!.prix_demande_median_eur_m2 != null ? `${fmt(ma!.prix_demande_median_eur_m2)} €/m²` : '—')} />
                            <RowT lbl="Écart demandé / acté" strong={!sous && ma!.ecart_demande_acte_pct != null}
                              val={sous ? libSeuil : (ma!.ecart_demande_acte_pct != null ? `${ma!.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(ma!.ecart_demande_acte_pct)} %` : '—')} />
                            {sous && <p className="text-[10.5px] text-txt-dim">Prix demandé et écart servis à partir de {ma!.demande_seuil_n} biens relevés (robustesse Radar).</p>}
                          </div>
                        )
                      })()}
                    </>
                  )}
                  {/* COMMUNE-FIX-1 (D13) — acquéreurs récents (PM) : endpoint dédié, 5 premiers + Scan patrimoine. */}
                  <AcquereursPmCommune commune={commune} />
                  <Source nom={`DVF (mutations)${ma ? ` · ${ma.source}` : ' · Radar LABUSE'}`} />
                </LigneCarte>
                )
              })()}

              {/* ═══ LA CONSTRUCTION ═══ */}
              <GroupeLabel>La construction</GroupeLabel>

              <LigneCarte id="construire" chiffre="permis_12m_n" ic="▤" titre="Permis et rythme"
                sous={`${fmt(d.permis_bloc.permis_12m)} permis / 12 mois${d.permis_bloc.logements_12m != null ? ` · ${fmt(d.permis_bloc.logements_12m)} logts` : ''}`}
                val={d.permis_bloc.delai_median_mois != null ? `${fmtDec(d.permis_bloc.delai_median_mois)} mois` : null}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Permis autorisés (12 mois)" val={`${fmt(d.permis_bloc.permis_12m)}${d.permis_bloc.permis_5a != null ? ` · ${fmt(d.permis_bloc.permis_5a)} sur 5 ans` : ''}`} strong />
                  {/* KELFONCIER-FIX-2 (Lot D) — ventilation PC / PA / DP (+ PD) sur 12 mois, à côté du chiffre
                      existant. Servie par le back (permis_type_12m, KELFONCIER-FIX-1 Lot C), même source SITADEL.
                      Ordre stable PC · PA · DP · PD ; seuls les types présents s'affichent. */}
                  {d.permis_bloc.permis_type_12m && Object.keys(d.permis_bloc.permis_type_12m).length > 0 && (
                    <RowT lbl="Dont, par type (12 mois)"
                      val={(['PC', 'PA', 'DP', 'PD'] as const)
                        .filter((t) => (d.permis_bloc.permis_type_12m?.[t] ?? 0) > 0)
                        .map((t) => `${t} ${fmt(d.permis_bloc.permis_type_12m![t])}`).join(' · ') || '—'} />
                  )}
                  {/* Annulés (ETAT_DAU=4) — séparés des autorisés, même fenêtre 12 mois. Silencieux si 0. */}
                  {(d.permis_bloc.permis_annules_12m ?? 0) > 0 && (
                    <RowT lbl="Annulés (12 mois)" val={fmt(d.permis_bloc.permis_annules_12m!)} />
                  )}
                  {d.permis_bloc.delai_median_mois != null && <RowT lbl="Délai d'instruction médian" val={`${fmtDec(d.permis_bloc.delai_median_mois)} mois`} />}
                  {d.permis_bloc.logements_12m != null && <RowT lbl="Offre engagée" val={`${fmt(d.permis_bloc.logements_12m)} logts / 12 mois`} />}
                  {/* OUTILS-FIX-5 L5 — « Permis dormants » : d.permis_bloc.point_mort sert désormais
                      le MÊME id que l'outil Permis (point_mort_n / permis_point_mort, unifié dans
                      fiche_commune.permis_bloc) — un seul mot, un seul chiffre, fiche commune == outil. */}
                  <RowT lbl="Permis dormants" val={fmt(d.permis_bloc.point_mort)} />
                </div>
                <Source nom={d.permis_bloc.source} />
              </LigneCarte>

              <LigneCarte id="foncier" chiffre="n_parcelles_commune" ic="◫" titre="Foncier et rareté"
                // RETOURS-15 B2 — la ligne « N parcelles promues » (classement LABUSE, hors périmètre)
                // est retirée du sous-titre ; on garde l'horizon ZAN, sinon le compte factuel de parcelles.
                sous={r?.['horizon_epuisement_ans'] != null ? `ZAN ${fmtDec(r['horizon_epuisement_ans'])} ans` : `${fmt(d.foncier?.n_parcelles)} parcelles`}
                val={d.foncier ? `${fmt(d.foncier.stock_opportunites.ha)} ha` : null} ton="orange">
                {d.foncier && (
                  <>
                    <div className="mb-3 flex gap-5">
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.n_parcelles)}</p><p className="text-[11px] text-txt-dim">parcelles<i className="block not-italic text-[10px]">{fmt(d.foncier.surface_ha)} ha</i></p></div>
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.stock_opportunites.n)}</p><p className="text-[11px] text-txt-dim">stock foncier repéré<i className="block not-italic text-[10px]">{fmt(d.foncier.stock_opportunites.ha)} ha promus</i></p></div>
                    </div>
                    {d.densifiables?.parcelles != null && (
                      <div className="mb-2 flex gap-5">
                        <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.densifiables.parcelles)}</p><p className="text-[11px] text-txt-dim">densifiables<i className="block not-italic text-[10px]">capacité résiduelle</i></p></div>
                        {d.densifiables.sdp_residuelle_m2 != null && <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(Math.round(d.densifiables.sdp_residuelle_m2 / 1e6 * 10) / 10)} M m²</p><p className="text-[11px] text-txt-dim">SDP résiduelle théorique</p></div>}
                      </div>
                    )}
                  </>
                )}
                <div className="flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                  <RowT lbl="Consommation NAF (budget ZAN consommé)" val={r?.['pct_budget_consomme'] != null ? `${fmtDec(r['pct_budget_consomme'])} %${r?.['budget_zan_ha'] != null ? ` de ${fmtV(r['budget_zan_ha'], ' ha')}` : ''}` : '—'} />
                  <RowT lbl="Budget ZAN restant (estimé)" val={fmtV(r?.['reste_zan_ha'], ' ha')} />
                  <RowT lbl="Rythme de consommation" val={fmtV(r?.['rythme_conso_ha_an'], ' ha/an')} />
                  <RowT lbl="Horizon d'épuisement" val={r?.['horizon_epuisement_ans'] != null ? `${fmtDec(r['horizon_epuisement_ans'])} ans` : '—'} strong />
                </div>
                <Source nom={`Cadastre DGFiP · ${d.densifiables?.source ?? 'analyse LABUSE'} · Consommation ENAF Cerema (estimé)`} />
              </LigneCarte>

              {/* ═══ LES RÈGLES ═══ */}
              <GroupeLabel>Les règles</GroupeLabel>

              <LigneCarte id="regle-plu" chiffre="statut_plu" ic="§" titre="Urbanisme"
                sous={`PLU ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}`}
                val={d.plu_statut.statut} badge ton={d.plu_statut.statut === 'RNU' ? 'orange' : 'vert'}>
                <p className="text-[12px] leading-relaxed text-txt">
                  {d.plu_statut.statut === 'RNU' ? "Pas de PLU opposable : c'est le Règlement National d'Urbanisme qui s'applique."
                    : d.plu_statut.statut === 'à jour' ? `Le PLU est opposable${d.plu_statut.date_reglement ? ` (approuvé le ${d.plu_statut.date_reglement})` : ''}.`
                      : `Document local — ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}.`}
                </p>
                {/* COMMUNE-FIX-1 (D12) — procédure PLU en cours au dernier relevé Sudocuh (révision, modification…). */}
                {d.plu_statut.procedure_sudocuh?.etat && (
                  <p className="mt-1 text-[11px] leading-relaxed text-txt-mut">
                    <b className="text-txt">Procédure (Sudocuh{d.plu_statut.procedure_sudocuh.millesime ? ` ${d.plu_statut.procedure_sudocuh.millesime}` : ''})</b> : {d.plu_statut.procedure_sudocuh.etat}{d.plu_statut.procedure_sudocuh.prescription ? ` · prescrite le ${d.plu_statut.procedure_sudocuh.prescription}` : ''}.
                  </p>
                )}
                {/* GEOPF-3 — SCOT (planification supra-communale, GPU) : nom + date d'approbation. */}
                {d.scot?.nom && (
                  <p data-scot className="mt-1 text-[11px] leading-relaxed text-txt-mut">
                    <b className="text-txt">SCOT</b> : {d.scot.nom}
                    {d.scot.date_approbation ? ` — approuvé le ${d.scot.date_approbation}`
                      : d.scot.statut ? ` — ${d.scot.statut}` : ''}.
                  </p>
                )}
                {d.foncier?.repartition_zonage && (() => {
                  const f = d.foncier.repartition_zonage.familles
                  return (
                    <div className="mt-2 border-t border-line pt-2">
                      <p className="mb-1 flex items-center gap-1.5 text-[11px] text-txt-dim">Zones du PLU <span className="text-txt-mut">(parts de surface)</span>
                        <span className="rounded bg-mint/10 px-1 text-[9px] text-mint">{d.foncier!.repartition_zonage!.total_ha.toLocaleString('fr-FR')} ha</span></p>
                      <Bar parts={[
                        { label: 'U', pct: f.U.pct, color: TOKENS.mint },
                        { label: 'AU', pct: f.AU.pct, color: TOKENS.vizCyan },
                        { label: 'A', pct: f.A.pct, color: TOKENS.stCreuser },
                        { label: 'N', pct: f.N.pct, color: TOKENS.vizGreenDeep },
                      ]} />
                    </div>
                  )
                })()}
                <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                  {d.plh ? (
                    <>
                      <RowT lbl={`PLH ${d.epci ?? ''} — objectif`} val={d.plh.obj_logements_an != null ? `${fmt(d.plh.obj_logements_an)} logts/an` : '—'} />
                      {d.plh.part_sociale_pct != null && <RowT lbl="Part sociale visée" val={`${Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %`} />}
                    </>
                  ) : (
                    <p data-plh-sans-objet className="text-[12px] text-txt-mut">Aucun programme local de l'habitat recensé pour l'intercommunalité {d.epci ?? ''}.</p>
                  )}
                </div>
                <Source nom={`${d.plu_statut.source ?? 'GPU'} · Zonage PLU (GPU) · PLH (EPCI)`} />
              </LigneCarte>

              {/* Fiscalité et dispositifs — taxes + zonages + QPV/ORT (creux dits). */}
              {(() => {
                const o = d.ort
                const horsOrt = !o || o.statut === 'hors'
                const aucunQpv = d.qpv.length === 0 && d.anru.length === 0
                return (
                <LigneCarte id="fiscalite" chiffre="tfpb_taux_pct" ic="₣" titre="Fiscalité et dispositifs"
                  sous={`${d.fiscalite?.tfpb_commune_pct != null ? `TFPB ${fmtDec(d.fiscalite.tfpb_commune_pct)} %` : 'taxes'}${d.zonage_abc ? ` · zone ${d.zonage_abc.zone}` : ''}`}
                  val={horsOrt ? null : (o!.statut === 'acv' ? 'ACV' : o!.statut === 'pvd' ? 'PVD' : 'ORT')}>
                  {d.fiscalite && (
                    <div className="flex flex-col gap-0.5 text-[12px]">
                      <RowT lbl="TFPB commune" val={d.fiscalite.tfpb_commune_pct != null ? `${fmtDec(d.fiscalite.tfpb_commune_pct)} %` : '—'} strong />
                      <RowT lbl="TFPB intercommunalité" val={d.fiscalite.tfpb_epci_pct != null ? `${fmtDec(d.fiscalite.tfpb_epci_pct)} %` : '—'} />
                      <RowT lbl="TFPNB commune (non bâti)" val={d.fiscalite.tfpnb_commune_pct != null ? `${fmtDec(d.fiscalite.tfpnb_commune_pct)} %` : '—'} />
                      <RowT lbl="TFPNB intercommunalité" val={d.fiscalite.tfpnb_epci_pct != null ? `${fmtDec(d.fiscalite.tfpnb_epci_pct)} %` : '—'} />
                      <RowT lbl="TEOM (taux plein)" val={d.fiscalite.teom_pct != null ? `${fmtDec(d.fiscalite.teom_pct)} %` : '—'} />
                    </div>
                  )}
                  {/* COMMUNE-FIX-1 (D10) — taux communal de la taxe d'aménagement (même source que l'outil Taxe). */}
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl="Taxe d'aménagement (part communale)" val={d.taxe_amenagement?.part_communale_pct != null ? `${fmtDec(d.taxe_amenagement.part_communale_pct)} %` : 'non déterminée'} />
                  </div>
                  {d.fiscalite?.perime && (
                    <p data-fiscalite-perime className="mt-1 text-[11px] text-st-creuser">Donnée ingérée il y a plus d'un an — à rafraîchir (fichier REI annuel).</p>
                  )}
                  <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                    <RowT lbl="Classe de la commune" val={d.zonage_abc ? `zone ${d.zonage_abc.zone}` : 'non déterminée'} />
                    {d.zfang_frr && <RowT lbl="ZFANG" val={d.zfang_frr.zfang.regime === 'renforce' ? 'Régime renforcé' : 'Régime standard'} />}
                    {d.zfang_frr && <RowT lbl="FRR" val={d.zfang_frr.frr.classement === 'totalite' ? 'Classée en totalité' : d.zfang_frr.frr.classement === 'partie' ? 'Classée en partie (les Hauts)' : 'Hors dispositif'} />}
                    {/* COMMUNE-FIX-1 (B8) — le libellé distingue les 3 états réels : la commune SIGNATAIRE
                        d'une ORT (ort_signee), une commune de l'EPCI où existe une ORT mais NON signataire,
                        ou aucune. Avant : « ORT (autre commune signataire) » — faux pour Saint-Paul, qui
                        signe l'ORT du TCO. */}
                    <RowT lbl="Dispositif" val={
                      horsOrt ? 'Aucune ORT'
                        : o!.statut === 'acv' ? 'Action Cœur de Ville (signataire)'
                          : o!.statut === 'pvd' ? 'Petites Villes de Demain (signataire)'
                            : o!.ort_signee ? 'ORT — commune signataire'
                              : "ORT dans l'EPCI — commune non signataire"} />
                    <RowT lbl="QPV" val={aucunQpv ? 'aucun' : `${d.qpv.length} quartier(s)`} />
                    <RowT lbl="NPNRU" val={d.anru.length > 0 ? `${d.anru.length} périmètre(s)` : 'aucun'} />
                  </div>
                  {(horsOrt || aucunQpv) && (
                    <p data-fiscalite-sans-objet className="mt-1.5 text-[11px] text-txt-dim">{[aucunQpv ? 'Aucun quartier prioritaire' : null, horsOrt ? 'hors ORT' : null].filter(Boolean).join(' · ')} — dit, jamais une carte absente.</p>
                  )}
                  <Source nom="DGFiP REI · DHUP (zonage A/B/C) · territoire_fiscal (ZFANG/FRR) · DGALN (ORT) · ANCT (QPV/NPNRU)" />
                </LigneCarte>
                )
              })()}

              {/* ═══ LE CADRE DE VIE ═══ */}
              <GroupeLabel>Le cadre de vie</GroupeLabel>

              <LigneCarte id="risques" chiffre="ppr_pct" ic="⚠" titre="Risques et contraintes"
                sous="PPR · mouvement de terrain · CatNat"
                val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % en PPR` : (d.risques.parc_national ? 'Parc National' : null)}
                badge={d.risques.ppr_pct != null} ton="orange">
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="PPR (risque naturel)" val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % des parcelles` : '—'} />
                  <RowT lbl="Mouvement de terrain" val={d.risques.mouvement_terrain_pct != null ? `${fmtDec(d.risques.mouvement_terrain_pct)} %` : '—'} />
                  <RowT lbl="Arrêtés CatNat" val={fmt(d.risques.catnat_arretes)} />
                  {d.risques.catnat_detail?.length ? (
                    <div className="ml-2 flex flex-col gap-0.5 border-l border-line pl-2">
                      {d.risques.catnat_detail.slice(0, 6).map((a, i) => (
                        <RowT key={a.code_national ?? i} lbl={a.type_peril}
                          val={[a.date_debut && a.date_fin ? `${a.date_debut} → ${a.date_fin}` : (a.date_arrete ?? ''),
                                a.code_national].filter(Boolean).join(' · ')} />
                      ))}
                      {d.risques.catnat_arretes > 6 ? (
                        <div className="text-[11px] text-txt-dim">et {d.risques.catnat_arretes - 6} autre{d.risques.catnat_arretes - 6 > 1 ? 's' : ''}…</div>
                      ) : null}
                    </div>
                  ) : null}
                  {d.risques.azi_tri && (d.risques.azi_tri.azi?.length || d.risques.azi_tri.tri?.length) ? (
                    <RowT lbl="Inondation (AZI / TRI)"
                      val={[...(d.risques.azi_tri.azi ?? []).map((x: { libelle?: string }) => `AZI ${x.libelle ?? ''}`),
                            ...(d.risques.azi_tri.tri ?? []).map((x: { libelle?: string }) => `TRI ${x.libelle ?? ''}`)].join(' · ')} />
                  ) : d.risques.azi_tri ? (
                    <RowT lbl="Inondation (AZI / TRI)" val="aucun document recensé (GASPAR)" />
                  ) : null}
                  <RowT lbl="Aire d'adhésion Parc National" val={d.risques.parc_national ? 'oui' : 'non'} />
                </div>
                <Source nom={d.risques.source} />
              </LigneCarte>

              <LigneCarte id="equipements" ic="⌘" titre="Équipements et desserte"
                sous="services, transport, réseaux"
                val={undefined}>
                <p className="text-[12px] leading-relaxed text-txt-mut">Équipements (écoles, santé, commerces), transport public, trafic, fibre, assainissement et productible
                  solaire de la commune se lisent au plus près dans l'Étude de zone (autour d'un point) — tuile « Étude de zone » en tête de fiche.</p>
                <Source nom="BPE INSEE · GTFS PAN · OSM · Arcep · INSEE RP · PVGIS (via Étude de zone)" />
              </LigneCarte>
            </div>

            {/* FICHE-COMMUNE-2 (C1) — pied : les compteurs sont PRÉCALCULÉS chaque nuit et servis tels quels
                (ouverture < 500 ms). La date du calcul est dite. `cache_calcule_le === null` = calcul en direct. */}
            {/* COMMUNE-FIX-1 (A4) — le job nocturne fiche-commune-cache est RÉINSCRIT au registre CRON
                (précalcul quotidien réel, wrapper run-job.sh) : le pied affiche la VRAIE date du dernier
                précalcul et peut de nouveau dire « rafraîchis chaque nuit » sans mentir. */}
            <p data-fiche-pied className="px-5 py-3 text-[10.5px] leading-relaxed text-txt-dim">
              {d.cache_calcule_le
                ? `Compteurs précalculés le ${fmtDateFr(d.cache_calcule_le)} (rafraîchis chaque nuit).`
                : 'Compteurs calculés en direct.'}
              {' '}Données de contexte — aucune n'entre dans le scoring.
            </p>
          </>
        )}
      </div>
    </aside>
  )
}
