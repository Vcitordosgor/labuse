import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { deleteCommuneContact, getCommuneContacts, getContexteCommune, getMoi, motMarcheCommune, motRarete, postCommuneContact } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { GrilleOutils, OutilCase } from '../shared/GrilleOutils'   // PROJETS-V5 (E9) — grille partagée
import { CONTACT_VIDE, ContactEdit, trimContact, type ContactForm } from '../shared/ContactEdit'  // RETOURS-8 (R6)

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

function Shortcut({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button data-passerelle onClick={onClick}
      className="mt-3 inline-block rounded-lg border border-mint/30 px-2.5 py-1 text-[11.5px] text-mint hover:bg-mint/10">
      {label} →
    </button>
  )
}

// FICHE-COMMUNE-2 (C2) — la MÊME grammaire que la fiche parcelle : une LIGNE-CARTE (fond carte, bordure,
// coins arrondis, icône à gauche, titre + sous-titre, valeur ou badge à droite, chevron). Fermée, elle dit
// déjà l'essentiel ; un clic ouvre son détail (rien de perdu d'OUTILS-6). L'état ouvert/fermé est mémorisé.
const TON_COL: Record<string, string> = { vert: TOKENS.mint, orange: TOKENS.stCreuser, rouge: TOKENS.stEcartee, violet: 'var(--iris)' }
function LigneCarte({ id, ic, titre, sous, val, ton, badge, defaultOpen, children }: {
  id: string; ic: string; titre: string; sous?: string; val?: string | null
  ton?: 'vert' | 'orange' | 'rouge' | 'violet'; badge?: boolean; defaultOpen?: boolean; children: React.ReactNode
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
        {val != null && val !== '' && (badge
          ? <span className="shrink-0 rounded-md border px-1.5 py-0.5 text-[11px] font-medium" style={{ color: col, borderColor: `${col}55`, background: `${col}1a` }}>{val}</span>
          : <span className="shrink-0 text-[12.5px] font-semibold" style={col ? { color: col } : undefined}>{val}</span>)}
        <span className="shrink-0 text-[15px] text-txt-dim transition-transform group-open:rotate-90">›</span>
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
  const tend = ligneMar('tendance_12m')
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
        <button onClick={() => setContexteCommune(null)} className="shrink-0 text-txt-dim hover:text-txt-hi" title="Fermer (Échap)" aria-label="Fermer">✕</button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {q.isLoading && <div className="p-5"><Loading label="Chargement de la fiche commune" className="text-xs" /></div>}
        {q.isError && <p className="p-5 text-xs text-st-ecartee">Erreur de chargement — réessayez.</p>}
        {d && (
          <>
            {/* EN-TÊTE PERMANENT — les quatre chiffres qui décident d'y aller ou non + les deux gestes. */}
            <div className="border-b border-line bg-surface-2/40 px-5 py-3">
              {/* FICHE-COMMUNE-2 (C2, maquette V2) — les QUATRE chiffres qui décident : terrain nu U (coût du
                  sol) · neuf (ce que rapporte la sortie) · SRU (l'obligation, donc le débouché VEFA) · ZAN
                  (le temps restant). L'ancien médian et le délai d'instruction restent sur leurs lignes. */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                <div><p className="font-display text-[17px] font-bold text-txt-hi">{fmt(d.foncier?.prix_terrain_nu?.par_zone?.['U']?.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone U</p></div>
                <div><p className="font-display text-[17px] font-bold text-txt-hi">{fmt(d.comparable?.neuf_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">neuf (sortie)</p></div>
                {/* RETOURS-12 O8 — SRU : on nomme EXPLICITEMENT la grandeur affichée (TAUX de logement
                    social, en %) et on montre le DÉFICIT (objectif − taux, en points) — la même grandeur
                    que la colonne « Déficit SRU (pts) » du tableau des 24 communes. Fini les deux chiffres
                    (« 18 % » vs « 6,7 ») qui semblaient se contredire : ce sont deux vues du même fait. */}
                <div><p className={`font-display text-[17px] font-bold ${d.sru && d.sru.taux_lls != null && d.sru.objectif_pct != null && d.sru.taux_lls < d.sru.objectif_pct ? 'text-st-ecartee' : 'text-txt-hi'}`}>{d.sru?.taux_lls != null ? `${fmtDec(d.sru.taux_lls)} %` : '—'}</p><p className="text-[10.5px] text-txt-dim">taux de logement social (SRU){d.sru?.deficit != null && d.sru.deficit > 0 ? ` — déficit ${fmtDec(d.sru.deficit)} pts` : ''}</p></div>
                <div><p className={`font-display text-[17px] font-bold ${(r?.['horizon_epuisement_ans'] ?? 99) < 6 ? 'text-st-creuser' : 'text-txt-hi'}`}>{r?.['horizon_epuisement_ans'] == null ? '—' : `${fmtDec(r['horizon_epuisement_ans'])} ans`}</p><p className="text-[10.5px] text-txt-dim">avant épuisement du ZAN</p></div>
              </div>
              {/* FICHE-COMMUNE-2 (C2, maquette V2) — l'action verte pleine largeur, puis DEUX actions
                  violettes (Comparer · Étude de zone). */}
              {/* PROJETS-V5 (E8) — DA : vert PLEIN = action principale. « Voir ses parcelles » devient
                  opaque (le même que « Demander à LABUSE d'analyser » sur la fiche parcelle). */}
              <button data-communes-parcelles onClick={() => {
                const s = useApp.getState()
                s.setView('cartes'); s.setCommune(commune); s.setCommunesFilter([commune])
                s.setFilter('analyseLabuse', true); s.setVerdict(true)
                s.openListing()   // C3 — Couches replié, le listing prend la place
              }} className="mt-3 w-full rounded-md border border-mint bg-mint px-2.5 py-2 text-[12.5px] font-semibold text-mint-ink transition-[filter] duration-quick hover:brightness-110">Voir ses parcelles →</button>
              {/* PROJETS-V5 (E8) — DA : le MAUVE est RÉSERVÉ au Copilote IA. « Comparer » et « Étude de zone »
                  ne sont pas des fonctions IA → boutons NEUTRES (contour gris, comme PDF / Renommer). */}
              <div className="mt-2 flex gap-2">
                <button data-communes-comparer onClick={() => ouvrirOutil(commune, insee, 'communes')}
                  className="flex-1 rounded-md border border-line-2 px-2.5 py-1.5 text-[12px] font-medium text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">⊞ Comparer aux 24</button>
                <button data-communes-etude-zone onClick={() => ouvrirOutil(commune, insee, 'etude-zone')}
                  className="flex-1 rounded-md border border-line-2 px-2.5 py-1.5 text-[12px] font-medium text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">◎ Étude de zone</button>
              </div>
              {/* FICHE-COMMUNE-2 (C2) — SIGNAUX NOMMÉS en puces (règle en constante ; n'apparaissent que si
                  vrais). Remplacent « signal : prudence ». Ton rouge = obligation/baisse, orange = contrainte. */}
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

            {/* 1 · LE FONCIER (ouvert) — qu'y a-t-il ici ? */}
            {/* FICHE-COMMUNE-2 (C2, maquette V2) — la même grammaire que la fiche parcelle : des LIGNES-CARTES
                distinctes, en trois groupes titrés. Chaque ligne dit l'essentiel fermée, et ouvre son détail. */}

            {/* ── CONSTRUIRE ICI ── */}
            <div className="px-5 pt-3">
              <GroupeLabel>Construire ici</GroupeLabel>

              <LigneCarte id="regle-plu" ic="§" titre="Règles d'urbanisme"
                sous={`PLU ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}`}
                val={d.plu_statut.statut} badge ton={d.plu_statut.statut === 'RNU' ? 'orange' : 'vert'}>
                {/* PROJETS-V5 (E10) — le statut RÉEL, jamais le stade technique brut (`libelle`, ex. « aucune »
                    = aucune procédure en cours, lu à tort « pas de PLU »). Une phrase claire + « Voir le PLU → ». */}
                <p className="text-[12px] leading-relaxed text-txt">
                  {d.plu_statut.statut === 'RNU' ? "Pas de PLU opposable : c'est le Règlement National d'Urbanisme qui s'applique."
                    : d.plu_statut.statut === 'à jour' ? `Le PLU est opposable${d.plu_statut.date_reglement ? ` (approuvé le ${d.plu_statut.date_reglement})` : ''}.`
                      : `Document local — ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}.`}
                </p>
                <button data-voir-plu onClick={() => ouvrirOutil(commune, insee, 'plu')} className="mt-2 text-[11.5px] text-mint hover:underline">Voir le PLU →</button>
                <Source nom={d.plu_statut.source ?? 'GPU'} />
              </LigneCarte>

              <LigneCarte id="regle-zan" ic="◐" titre="Enveloppe ZAN"
                sous={r ? `${fmtV(r['reste_zan_ha'], ' ha')} restants · ${fmtV(r['rythme_conso_ha_an'], ' ha/an')}` : 'horizon non projetable'}
                val={r?.['horizon_epuisement_ans'] != null ? `${fmtDec(r['horizon_epuisement_ans'])} ans` : null} ton="orange">
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Budget ZAN restant (estimé)" val={fmtV(r?.['reste_zan_ha'], ' ha')} />
                  <RowT lbl="Rythme de consommation" val={fmtV(r?.['rythme_conso_ha_an'], ' ha/an')} />
                  <RowT lbl="Horizon d'épuisement" val={r?.['horizon_epuisement_ans'] != null ? `${fmtDec(r['horizon_epuisement_ans'])} ans` : '—'} strong />
                </div>
                <Source nom="Consommation ENAF Cerema · enveloppe loi Climat (estimé)" />
              </LigneCarte>

              {d.sru && (() => {
                const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                return (
                  <LigneCarte id="regle-sru" ic="⌂" titre="Logement social — SRU"
                    sous={`${d.sru.detail?.nb_lls != null ? `${fmt(d.sru.detail.nb_lls)} LLS · ` : ''}objectif ${Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %`}
                    val={m.label.toLowerCase()} badge ton={d.sru.statut === 'carencee' ? 'rouge' : d.sru.statut === 'deficitaire' ? 'orange' : d.sru.statut === 'conforme' ? 'vert' : undefined}>
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: `${m.color}14` }}>
                      <span className="font-display text-[14px] font-bold" style={{ color: m.color }}>SRU {Number(d.sru.taux_lls).toLocaleString('fr-FR')} %</span>
                      <span className="ml-2 text-[11px] text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %</span>
                      <p className="mt-1 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                    </div>
                    <Source nom="Inventaire SRU (DHUP)" />
                  </LigneCarte>
                )
              })()}

              <LigneCarte id="construire" ic="▤" titre="Permis & délais"
                sous={`${fmt(d.permis_bloc.permis_12m)} permis / 12 mois${d.permis_bloc.logements_12m != null ? ` · ${fmt(d.permis_bloc.logements_12m)} logts` : ''}`}
                val={d.permis_bloc.delai_median_mois != null ? `${fmtDec(d.permis_bloc.delai_median_mois)} mois` : null}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Permis autorisés (12 mois)" val={`${fmt(d.permis_bloc.permis_12m)}${d.permis_bloc.permis_5a != null ? ` · ${fmt(d.permis_bloc.permis_5a)} sur 5 ans` : ''}`} strong />
                  {d.permis_bloc.delai_median_mois != null && <RowT lbl="Délai d'instruction médian" val={`${fmtDec(d.permis_bloc.delai_median_mois)} mois`} />}
                  {d.permis_bloc.logements_12m != null && <RowT lbl="Offre engagée" val={`${fmt(d.permis_bloc.logements_12m)} logts / 12 mois`} />}
                  <RowT lbl="Permis dormants" val={fmt(d.permis_bloc.point_mort)} />
                </div>
                <Shortcut label="Ouvrir Permis — cette commune" onClick={() => ouvrirOutil(commune, insee, 'permis')} />
                <Source nom={d.permis_bloc.source} />
              </LigneCarte>

              {d.plh && (
                <LigneCarte id="regle-plh" ic="≡" titre="Programme local — PLH"
                  sous={`${d.epci ?? ''}${d.plh.part_sociale_pct != null ? ` · ${Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} % part sociale` : ''}`}
                  val={d.plh.obj_logements_an != null ? `${fmt(d.plh.obj_logements_an)} logts/an` : null}>
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl={`PLH ${d.epci ?? ''} — objectif`} val={d.plh.obj_logements_an != null ? `${fmt(d.plh.obj_logements_an)} logts/an` : '—'} />
                    {d.plh.part_sociale_pct != null && <RowT lbl="Part sociale visée" val={`${Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %`} />}
                  </div>
                  <Source nom="PLH (EPCI)" />
                </LigneCarte>
              )}

              {/* ── LE MARCHÉ ── */}
              <GroupeLabel>Le marché</GroupeLabel>

              <LigneCarte id="marche" ic="↗" titre="Prix &amp; tendance" defaultOpen
                sous={`ancien ${fmt(d.comparable?.ancien_median_eur_m2)} · neuf ${fmt(d.comparable?.neuf_eur_m2)} €/m² · ${fmt(d.foncier?.mutations_12m)} mutations/12m`}
                val={tend?.['pct'] != null ? `${Number(tend['pct']) > 0 ? '+' : ''}${fmtDec(tend['pct'])} %` : null}
                ton={tend?.['pct'] != null && Number(tend['pct']) < 0 ? 'rouge' : 'vert'}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Ancien médian (commune entière)" val={`${fmt(d.comparable?.ancien_median_eur_m2)} €/m²`} strong />
                  <RowT lbl="Neuf (prix de sortie)" val={`${fmt(d.comparable?.neuf_eur_m2)} €/m²`} />
                  {tend?.['pct'] != null && <RowT lbl="Tendance 12 mois" val={`${Number(tend['pct']) > 0 ? '+' : ''}${fmtDec(tend['pct'])} %`} />}
                  <RowT lbl="Mutations (12 mois, DVF)" val={fmt(d.foncier?.mutations_12m)} />
                </div>
                <Source nom="DVF — médiane commune entière (même moteur que le comparateur)" />
              </LigneCarte>

              {d.foncier?.prix_terrain_nu.par_zone && (
                <LigneCarte id="terrain-nu" ic="▦" titre="Terrain nu"
                  sous={`zone U ${fmt(d.foncier.prix_terrain_nu.par_zone['U']?.n)} ventes · zone AU ${fmt(d.foncier.prix_terrain_nu.par_zone['AU']?.n)} ventes`}
                  val={`${fmt(d.foncier.prix_terrain_nu.par_zone['U']?.median_eur_m2)} · ${fmt(d.foncier.prix_terrain_nu.par_zone['AU']?.median_eur_m2)} €/m²`}>
                  <div className="flex gap-5">
                    {(['U', 'AU'] as const).map((fam) => {
                      const pz = d.foncier!.prix_terrain_nu.par_zone?.[fam]
                      return pz?.calculable
                        ? <div key={fam}><p className="font-display text-base font-bold text-txt-hi">{fmt(pz.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone {fam} · {fmt(pz.n)} ventes</p></div>
                        : <div key={fam}><p className="font-display text-sm text-txt-mut">zone {fam} —</p><p className="text-[10.5px] text-txt-dim">&lt; {d.foncier!.prix_terrain_nu.seuil_n} ventes</p></div>
                    })}
                  </div>
                  <Source nom="DVF terrain nu par zone PLU" />
                </LigneCarte>
              )}

              {d.marche_annonces && (
                <LigneCarte id="annonces" ic="◉" titre="Annonces en cours — Radar"
                  sous={`${fmt(d.marche_annonces.biens)} biens en vente · écart demandé / acté`}
                  val={!d.marche_annonces.sous_seuil && d.marche_annonces.ecart_demande_acte_pct != null ? `${d.marche_annonces.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(d.marche_annonces.ecart_demande_acte_pct)} %` : null}
                  ton={d.marche_annonces.ecart_demande_acte_pct != null && d.marche_annonces.ecart_demande_acte_pct < 0 ? 'vert' : undefined}>
                  {d.marche_annonces.sous_seuil ? (
                    <p className="text-[12px] text-txt-mut">Trop peu d'annonces relevées pour un signal fiable ({d.marche_annonces.biens} bien(s), seuil {d.marche_annonces.seuil_n}). Le Radar affine la couverture au fil des relevés.</p>
                  ) : (
                    <>
                      <div className="flex flex-col gap-0.5 text-[12px]">
                        <RowT lbl="Biens en vente" val={fmt(d.marche_annonces.biens)} />
                        <RowT lbl="Prix demandé médian" val={`${fmt(d.marche_annonces.prix_demande_median_eur_m2)} €/m²`} />
                        {d.marche_annonces.ecart_demande_acte_pct != null && (
                          <RowT lbl="Écart demandé / acté" strong val={`${d.marche_annonces.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(d.marche_annonces.ecart_demande_acte_pct)} %`} />
                        )}
                      </div>
                      <p className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">L'écart demandé/acté est la marge de négociation du moment — le signal exclusif LABUSE.</p>
                      <Shortcut label="Voir les annonces dans le Radar" onClick={() => ouvrirOutil(commune, insee, 'radar')} />
                    </>
                  )}
                  <Source nom={d.marche_annonces.source} />
                </LigneCarte>
              )}

              {d.loyer && (
                <LigneCarte id="loyer" ic="€" titre="Loyers"
                  sous={`${d.loyer.type ?? 'logement'} · ${d.loyer.source}`}
                  val={d.loyer.median_eur_m2 != null ? `${fmtDec(d.loyer.median_eur_m2)} €/m²` : null}>
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl={`Loyer médian${d.loyer.type ? ` (${d.loyer.type})` : ''}`} val={`${fmtDec(d.loyer.median_eur_m2)} €/m²`} strong />
                  </div>
                  <Source nom={d.loyer.source} />
                </LigneCarte>
              )}

              {/* ── LE TERRITOIRE ── */}
              <GroupeLabel>Le territoire</GroupeLabel>

              {d.foncier && (
                <LigneCarte id="foncier" ic="◫" titre="Foncier repéré" defaultOpen
                  sous={`${fmt(d.foncier.stock_opportunites.n)} parcelles promues${d.densifiables?.parcelles != null ? ` · ${fmt(d.densifiables.parcelles)} densifiables` : ''}`}
                  val={`${fmt(d.foncier.stock_opportunites.ha)} ha`}>
                  <div className="mb-3 flex gap-5">
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.n_parcelles)}</p><p className="text-[11px] text-txt-dim">parcelles<i className="block not-italic text-[10px]">{fmt(d.foncier.surface_ha)} ha</i></p></div>
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.stock_opportunites.n)}</p><p className="text-[11px] text-txt-dim">stock foncier repéré<i className="block not-italic text-[10px]">{fmt(d.foncier.stock_opportunites.ha)} ha promus</i></p></div>
                  </div>
                  {d.densifiables?.parcelles != null && (
                    <div className="mb-1 flex gap-5">
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.densifiables.parcelles)}</p><p className="text-[11px] text-txt-dim">densifiables<i className="block not-italic text-[10px]">capacité résiduelle</i></p></div>
                      {d.densifiables.sdp_residuelle_m2 != null && <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(Math.round(d.densifiables.sdp_residuelle_m2 / 1e6 * 10) / 10)} M m²</p><p className="text-[11px] text-txt-dim">SDP résiduelle théorique</p></div>}
                    </div>
                  )}
                  <Shortcut label="Densifier l'existant — cette commune" onClick={() => ouvrirOutil(commune, insee, 'renouvellement')} />
                  <Source nom={`Cadastre DGFiP · zonage PLU · ${d.densifiables?.source ?? 'analyse LABUSE'}`} />
                </LigneCarte>
              )}

              {d.foncier?.repartition_zonage && (() => {
                const f = d.foncier.repartition_zonage.familles
                return (
                  <LigneCarte id="zonage" ic="▥" titre="Zonage"
                    sous={`U ${fmtDec(f.U.pct)} · AU ${fmtDec(f.AU.pct)} · A ${fmtDec(f.A.pct)} · N ${fmtDec(f.N.pct)} % de la surface`}
                    val="4 familles">
                    <p className="mb-1 flex items-center gap-1.5 text-[11px] text-txt-dim">Répartition du zonage <span className="text-txt-mut">(parts de surface)</span>
                      <span className="rounded bg-mint/10 px-1 text-[9px] text-mint">{d.foncier!.repartition_zonage!.total_ha.toLocaleString('fr-FR')} ha</span></p>
                    <Bar parts={[
                      { label: 'U', pct: f.U.pct, color: TOKENS.mint },
                      { label: 'AU', pct: f.AU.pct, color: TOKENS.vizCyan },
                      { label: 'A', pct: f.A.pct, color: TOKENS.stCreuser },
                      { label: 'N', pct: f.N.pct, color: TOKENS.vizGreenDeep },
                    ]} />
                    <Source nom="Zonage PLU (GPU)" />
                  </LigneCarte>
                )
              })()}

              <LigneCarte id="risques" ic="⚠" titre="Risques"
                sous="PPR · mouvement de terrain · CatNat"
                val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % en PPR` : (d.risques.parc_national ? 'Parc National' : null)}
                badge={d.risques.ppr_pct != null} ton="orange">
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="PPR (risque naturel)" val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % des parcelles` : '—'} />
                  <RowT lbl="Mouvement de terrain" val={d.risques.mouvement_terrain_pct != null ? `${fmtDec(d.risques.mouvement_terrain_pct)} %` : '—'} />
                  <RowT lbl="Arrêtés CatNat" val={fmt(d.risques.catnat_arretes)} />
                  <RowT lbl="Aire d'adhésion Parc National" val={d.risques.parc_national ? 'oui' : 'non'} />
                </div>
                <Source nom={d.risques.source} />
              </LigneCarte>

              <LigneCarte id="population" ic="⚇" titre="Population &amp; logement"
                sous={`${d.population.logements != null ? `${fmt(d.population.logements)} logts` : ''}${d.population.vacance_pct != null ? ` · ${fmtDec(d.population.vacance_pct)} % vacants` : ''} · INSEE`}
                val={d.population.habitants != null ? `${fmt(d.population.habitants)} hab.` : null}>
                <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                  {d.population.habitants != null && <RowT lbl="Habitants · ménages" val={`${fmt(d.population.habitants)} · ${fmt(d.population.menages)}`} />}
                  {d.population.niveau_vie_moyen_eur != null && <RowT lbl="Niveau de vie moyen" val={`${fmt(d.population.niveau_vie_moyen_eur)} €/an`} />}
                  {d.population.logements != null && <RowT lbl="Logements" val={`${fmt(d.population.logements)}${d.population.vacants != null ? ` · ${fmt(d.population.vacants)} vacants (${fmtDec(d.population.vacance_pct)} %)` : ''}`} />}
                </div>
                {d.marche && (
                  <div className="flex flex-col gap-2.5">
                    {(() => {
                      const loc = Number(d.marche.locataires_pct); const prop = Number(d.marche.proprietaires_pct)
                      const autres = Math.max(0, Math.round((100 - loc - prop) * 10) / 10)
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
                <Source nom={d.population.source} />
              </LigneCarte>

              {(d.qpv.length > 0 || d.anru.length > 0) && (
                <LigneCarte id="qpv" ic="◈" titre="Quartiers prioritaires" sous="ANCT · NPNRU"
                  val={`${d.qpv.length} QPV`}>
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl="QPV" val={d.qpv.length > 0 ? `${d.qpv.length} quartier(s)` : 'aucun'} />
                    <RowT lbl="NPNRU" val={d.anru.length > 0 ? `${d.anru.length} périmètre(s)` : 'aucun'} />
                  </div>
                  {d.qpv.length > 0 && <p className="mt-1 text-[10.5px] leading-snug text-txt-dim">{d.qpv.map((x) => x.nom).join(' · ')}</p>}
                  <Source nom="ANCT" />
                </LigneCarte>
              )}

              {d.mairie && (
                <LigneCarte id="contacts" ic="☎" titre="Mairie &amp; service urbanisme"
                  sous={[d.mairie.adresse, d.mairie.telephone].filter(Boolean).join(' · ') || 'coordonnées'}
                  val="contacter" ton="vert">
                  <dl className="space-y-1.5 text-[12px]">
                    <MairieLigne label="Adresse" val={[d.mairie.adresse, [d.mairie.code_postal, d.mairie.commune].filter(Boolean).join(' ')].filter(Boolean).join(', ') || null} />
                    <MairieLigne label="Téléphone" val={d.mairie.telephone} href={d.mairie.telephone ? `tel:${d.mairie.telephone.replace(/\s/g, '')}` : undefined} />
                    <MairieLigne label="E-mail" val={d.mairie.email} href={d.mairie.email ? `mailto:${d.mairie.email}` : undefined} />
                    <MairieLigne label="Site officiel" val={d.mairie.site_officiel} href={d.mairie.site_officiel ?? undefined} />
                    <MairieLigne label="Annuaire" val={d.mairie.url_annuaire ? 'Fiche service-public' : null} href={d.mairie.url_annuaire ?? undefined} />
                  </dl>
                  <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{d.mairie.source}{d.mairie.date_import ? ` · relevé le ${fmtDateFr(d.mairie.date_import)}` : ''}</p>
                  {/* ADMIN-1 (AD10) — contacts NOMMÉS de la commune, sous le standard officiel (tous comptes). */}
                  <ContactsMairie insee={insee} commune={commune} />
                </LigneCarte>
              )}

              {/* ── OUTILS — PROJETS-V5 (E9) : le composant PARTAGÉ GrilleOutils (même rendu que les exports
                  de la fiche parcelle). Sous la grille, « Voir plus d'outils → » ouvre la catégorie Outils. ── */}
              <GroupeLabel>Outils — pré-remplis sur {commune}</GroupeLabel>
              <GrilleOutils>
                <OutilCase ic="§" nom="PLU" chiffre="règlement" onClick={() => ouvrirOutil(commune, insee, 'plu')} />
                <OutilCase ic="▤" nom="Permis" chiffre={d.outils.permis_en_cours > 0 ? fmt(d.outils.permis_en_cours) : '—'} onClick={() => ouvrirOutil(commune, insee, 'permis')} />
                <OutilCase ic="◫" nom="Densifier" chiffre={d.outils.densifiables > 0 ? fmt(d.outils.densifiables) : '—'} onClick={() => ouvrirOutil(commune, insee, 'renouvellement')} />
                <OutilCase ic="◉" nom="Radar" chiffre={d.outils.radar_biens > 0 ? `${fmt(d.outils.radar_biens)} biens` : '—'} onClick={() => ouvrirOutil(commune, insee, 'radar')} />
                <OutilCase ic="☰" nom="Scan patrimoine" chiffre={d.outils.scan_pm > 0 ? fmt(d.outils.scan_pm) : '—'} onClick={() => ouvrirOutil(commune, insee, 'patrimoine')} />
                <OutilCase ic="☀" nom="Solaire" chiffre={d.outils.solaire_piscines > 0 ? fmt(d.outils.solaire_piscines) : '—'} onClick={() => ouvrirOutil(commune, insee, 'prospection-solaire')} />
                <OutilCase ic="◎" nom="Étude de zone" chiffre="un point" onClick={() => ouvrirOutil(commune, insee, 'etude-zone')} />
                <OutilCase ic="⊞" nom="Comparer" chiffre="24 communes" onClick={() => ouvrirOutil(commune, insee, 'communes')} />
              </GrilleOutils>
              <button data-voir-plus-outils onClick={() => { const s = useApp.getState(); s.setContexteCommune(null); s.toggleOutils() }}
                className="mt-2 text-[11.5px] text-mint transition-colors duration-quick hover:underline">Voir plus d'outils →</button>
            </div>

            {/* FICHE-COMMUNE-2 (C1) — pied : les compteurs sont PRÉCALCULÉS chaque nuit et servis tels quels
                (ouverture < 500 ms). La date du calcul est dite. `cache_calcule_le === null` = calcul en direct. */}
            <p data-fiche-pied className="px-5 py-3 text-[10.5px] leading-relaxed text-txt-dim">
              {d.cache_calcule_le
                ? `Compteurs précalculés le ${fmtDateFr(d.cache_calcule_le)} (rafraîchis chaque nuit).`
                : 'Compteurs calculés en direct (précalcul nocturne à venir).'}
              {' '}Données de contexte — aucune n'entre dans le scoring.
            </p>
          </>
        )}
      </div>
    </aside>
  )
}
