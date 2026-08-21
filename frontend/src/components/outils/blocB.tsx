/** BLOC B · Partie 2 — les outils O sans écran (verdict Vic sur maquettes docs/mockups/).
 *  Chaque module vit dans le shell violet du registre ; tokens seulement, wording boussole
 *  (Sourcé/Estimé, « non couvert » dit — jamais un faux RAS). */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'

const jfetch = async <T,>(url: string): Promise<T> => {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

/* ───────────── O5 — SERVITUDES INVISIBLES (S46) ───────────── */

type Servitudes = {
  idu: string; n: number; synthese: string
  servitudes: { categorie: string; effet: string; source: string; date: string | null }[]
  non_couvert: string[]
}

export function O5Servitudes() {
  const { selectedIdu, select } = useApp()
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const q = useQuery({
    queryKey: ['o5', idu],
    queryFn: () => jfetch<Servitudes>(`/servitudes-invisibles/${idu.trim()}`),
    enabled: idu.trim().length === 14,
  })
  const d = q.data
  return (
    <>
      <Banner>Les contraintes <b>dormantes</b> qui ne se voient pas sur la carte — servitudes
        d'utilité publique, sols, bruit — ET ce que la base ne couvre pas (jamais un faux
        « RAS »). La due diligence notariale reste indispensable.</Banner>
      <input data-o5-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
        placeholder="IDU (ou sélectionnez une parcelle sur la carte)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-mint focus:outline-none" />
      {q.isLoading && <Loading accent="mint" label="Recherche des servitudes…" />}
      {q.isError && <ErrorState className="py-6" message="Servitudes indisponibles." retry={() => q.refetch()} />}
      {d && (
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <span className="num-key text-base text-mint">{d.n}</span>{' '}
            <span className="text-txt-mut">servitude(s)/contrainte(s) sur</span>{' '}
            <button onClick={() => select(d.idu)} className="font-mono text-txt-hi hover:text-mint hover:underline">
              {d.idu.slice(8, 10)} {d.idu.slice(10)}</button>
          </div>
          {d.servitudes.map((s, i) => (
            <div key={i} className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
              <div className="flex flex-wrap items-baseline gap-1.5">
                <b className="text-[11.5px] text-txt-hi">{s.categorie}</b>
                <span className="rounded-full border border-mint/40 bg-mint/10 px-1.5 text-[8.5px] font-medium text-mint">Sourcé</span>
                <span className="text-[9.5px] text-txt-dim">{s.source}{s.date ? ` · ${s.date}` : ''}</span>
              </div>
              <p className="mt-1 text-[11px] leading-snug text-txt">{s.effet}</p>
            </div>
          ))}
          {d.servitudes.length === 0 && (
            <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] text-txt-mut">
              Aucune servitude détectée dans les couches ingérées — voir « non couvert » ci-dessous.</p>
          )}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
            <p className="label-caps text-[9.5px]">Non couvert par la base — à vérifier ailleurs</p>
            <div className="mt-1 space-y-0.5">
              {d.non_couvert.map((n, i) => <p key={i} className="text-[10.5px] text-txt-mut">○ {n}</p>)}
            </div>
          </div>
        </div>
      )}
      {!d && !q.isLoading && !q.isError && (
        <p className="text-[11px] text-txt-dim">Saisissez un IDU complet (14 caractères) ou cliquez une parcelle.</p>
      )}
    </>
  )
}

/* ───────────── O6 — COMPARATEUR DE COMMUNES (S47) ───────────── */

type Comparateur = {
  communes: Record<string, string | number | null>[]
  indicateurs: Record<string, { libelle: string; direction: string; poids: number; source: string; nature: string }>
  methode: string; avertissement: string
}
const O6_COLS: { k: string; label: string; unite?: string }[] = [
  { k: 'score_composite', label: 'Composite' }, { k: 'stock', label: 'Stock opp.' },
  { k: 'velocite', label: 'Vélocité', unite: ' m' }, { k: 'permis', label: 'Permis 5 ans' },
  { k: 'deficit_sru', label: 'Déficit SRU', unite: ' %' }, { k: 'prix_neuf', label: '€/m² neuf' },
]
// M82 #mots-coupés : libellés COURTS pour les curseurs de pondération (les libellés verbeux du backend
// enveloppaient sur 2-3 lignes en coupant les mots dans une demi-colonne à 130 px).
const PONDER_LABELS: Record<string, string> = {
  stock: 'Stock opp.', velocite: 'Vélocité', permis: 'Permis 5 ans',
  deficit_sru: 'Déficit SRU', pression_zan: 'Pression ZAN', prix_neuf: '€/m² neuf',
}

// M137-Z — `onSelect` : dans l'outil Communes, cliquer une ligne ouvre la fiche commune.
export function O6Comparateur({ onSelect }: { onSelect?: (commune: string) => void } = {}) {
  const [poids, setPoids] = useState<Record<string, number>>({
    stock: 30, velocite: 15, permis: 15, deficit_sru: 15, pression_zan: 10, prix_neuf: 15,
  })
  const [tri, setTri] = useState('score_composite')
  const qs = Object.entries(poids).map(([k, v]) => `w_${k}=${(v / 100).toFixed(2)}`).join('&')
  const q = useQuery({ queryKey: ['o6', qs], queryFn: () => jfetch<Comparateur>(`/comparateur-communes?${qs}`) })
  const d = q.data
  const rows = [...(d?.communes ?? [])].sort((a, b) => Number(b[tri] ?? -1) - Number(a[tri] ?? -1))
  return (
    <>
      <Banner>Où investir : une ligne par commune, indicateurs <b>sourcés</b>, composite de
        commodité à pondération réglable. {d?.avertissement ?? 'Les valeurs brutes restent la référence.'}</Banner>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
        <p className="label-caps text-[9.5px]">Pondérations — renormalisées si une donnée manque</p>
        <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(poids).map(([k, v]) => (
            <label key={k} className="whitespace-nowrap text-[10px] text-txt-mut">
              {PONDER_LABELS[k] ?? k} · <b className="tnum text-txt">{v} %</b>
              <input type="range" min={0} max={100} step={5} value={v} data-o6-poids={k}
                onChange={(e) => setPoids({ ...poids, [k]: Number(e.target.value) })}
                className="w-full accent-mint" />
            </label>
          ))}
        </div>
      </div>
      {q.isLoading && <Loading accent="mint" label="Calcul du comparatif…" />}
      {q.isError && <ErrorState className="py-6" message="Comparateur indisponible." retry={() => q.refetch()} />}
      {/* M15 E4 : plus de SCROLL HORIZONTAL (RG4) — les 6 métriques ne tenaient pas dans le volet,
          poussant « €/m² neuf » hors champ (cause du « vide » vu par Vic ; la donnée existe bien).
          On choisit la métrique à comparer via des chips (dont « €/m² neuf »), et le tableau montre
          Commune · Composite · la métrique choisie. Le tri suit la métrique. */}
      <div className="flex flex-wrap gap-1">
        {O6_COLS.filter((c) => c.k !== 'score_composite').map((c) => (
          <button key={c.k} data-o6-tri={c.k} onClick={() => setTri(c.k)}
            className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors duration-quick ${
              tri === c.k ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {c.label}</button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {(() => {
          const sel = O6_COLS.find((col) => col.k === tri && col.k !== 'score_composite') ?? O6_COLS[1]
          return (
            <>
              <div className="sticky top-0 grid grid-cols-[1fr_58px_74px] gap-1 bg-surface-1 py-1">
                <span className="label-caps text-[9px]">Commune</span>
                <button data-o6-tri="score_composite" onClick={() => setTri('score_composite')}
                  className={`text-right text-[9px] uppercase tracking-wide ${tri === 'score_composite' ? 'text-mint' : 'text-txt-dim hover:text-txt-mut'}`}>
                  Composite {tri === 'score_composite' ? '↓' : ''}</button>
                <span className="text-right text-[9px] uppercase tracking-wide text-mint">{sel.label} ↓</span>
              </div>
              {rows.map((c, i) => {
                const Cell = onSelect ? 'button' : 'div'
                return (
                <Cell key={String(c['insee'])} data-o6-row {...(onSelect ? { onClick: () => onSelect(String(c['commune'])), title: 'Voir la fiche commune →' } : {})}
                  className={`grid w-full grid-cols-[1fr_58px_74px] items-baseline gap-1 border-b border-line py-1.5 text-left text-[11px] ${onSelect ? 'transition-colors duration-quick hover:bg-surface-3' : ''}`}>
                  <span className="min-w-0 truncate text-txt">
                    <span className="mr-1 font-mono text-[9px] text-txt-dim">#{i + 1}</span>{String(c['commune'])}{onSelect ? ' →' : ''}</span>
                  <span className={`tnum text-right font-mono ${i < 3 ? 'font-semibold text-mint' : 'text-txt'}`}>
                    {c['score_composite'] == null ? '—' : Number(c['score_composite']).toLocaleString('fr-FR')}</span>
                  <span data-o6-metric className="tnum text-right font-mono text-txt-mut">
                    {c[sel.k] == null ? '—' : `${Number(c[sel.k]).toLocaleString('fr-FR')}${sel.unite ?? ''}`}</span>
                </Cell>
              )})}
            </>
          )
        })()}
      </div>
      <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">
        Composite = aide de lecture (jamais un score de rendement) ; une donnée manquante reste « — »,
        jamais un zéro inventé. Choisissez la métrique à comparer par les puces ci-dessus.</p>
    </>
  )
}

/* ───────────── O7 — CARNET DE SECTEUR (S48) ───────────── */

type CarnetListe = { secteurs: { secteur: string; commune: string; opportunites: number; brulantes: number }[]; note: string }
type CarnetSecteur = {
  secteur: string; commune: string; section: string
  stock: { total: number; opportunites: number; par_tier: Record<string, number> }
  prix: { dvf: Record<string, { mediane_prix_m2: number | null; n: number }> } | null
  signaux: { type: string; n: number }[] | null
  permis_24_mois: number | null
  note: string; avertissement: string | null
}

export function O7Carnet() {
  const [secteur, setSecteur] = useState<string | null>(null)
  const liste = useQuery({ queryKey: ['o7-liste'], queryFn: () => jfetch<CarnetListe>('/carnet-secteur') })
  const page = useQuery({
    queryKey: ['o7', secteur], queryFn: () => jfetch<CarnetSecteur>(`/carnet-secteur/${secteur}`),
    enabled: !!secteur,
  })
  const d = page.data
  if (secteur && d) {
    const dvf = Object.entries(d.prix?.dvf ?? {}).filter(([, v]) => v.mediane_prix_m2 != null)
    return (
      <>
        <button onClick={() => setSecteur(null)}
          className="min-h-7 self-start text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">← Secteurs</button>
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
          <span className="font-mono text-txt-hi">{d.secteur.slice(8)}</span>
          <span className="ml-2 text-[11px] text-txt-mut">{d.commune} · section {d.section}</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Opportunités</p>
            <p className="num-key text-lg text-mint">{d.stock.opportunites}</p>
            <p className="text-[9.5px] text-txt-dim">{d.stock.par_tier['brulante'] ?? 0} brûlantes · {d.stock.total} parcelles</p>
          </div>
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Permis 24 mois</p>
            <p className="num-key text-lg">{d.permis_24_mois ?? '—'}</p>
          </div>
        </div>
        {dvf.length > 0 && (
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Prix médians DVF <span className="normal-case text-mint">Sourcé</span></p>
            {dvf.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between text-[11px]">
                <span className="text-txt-mut">{k}</span>
                <span className="tnum font-mono text-txt">{Number(v.mediane_prix_m2).toLocaleString('fr-FR')} €/m² <span className="text-txt-dim">({v.n})</span></span>
              </div>
            ))}
          </div>
        )}
        {(d.signaux?.length ?? 0) > 0 && (
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Signaux du secteur</p>
            {d.signaux!.map((sg) => (
              <div key={sg.type} className="flex items-baseline justify-between text-[11px]">
                <span className="min-w-0 truncate text-txt-mut">{sg.type}</span>
                <span className="tnum font-mono text-txt">{sg.n}</span>
              </div>
            ))}
          </div>
        )}
        <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">{d.note}</p>
      </>
    )
  }
  return (
    <>
      <Banner>Votre <b>secteur</b> (section cadastrale) suivi comme un portefeuille — stock
        d'opportunités, prix, permis, signaux, tout sourcé. L'abonnement digest arrivera avec
        les comptes utilisateurs ; le carnet se consulte à la demande.</Banner>
      {liste.isLoading && <Loading accent="mint" label="Secteurs les plus actifs…" />}
      {liste.isError && <ErrorState className="py-6" message="Carnet indisponible." retry={() => liste.refetch()} />}
      {secteur && page.isLoading && <Loading accent="mint" label="Ouverture du secteur…" />}
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {(liste.data?.secteurs ?? []).map((s) => (
          <button key={s.secteur} data-o7-secteur={s.secteur} onClick={() => setSecteur(s.secteur)}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/50">
            <span className="font-mono text-[11px] text-txt-hi">{s.secteur.slice(8)}</span>
            <span className="min-w-0 flex-1 truncate text-[10.5px] text-txt-mut">{s.commune}</span>
            <span className="tnum text-[11px] text-mint">{s.opportunites} opp.</span>
            {s.brulantes > 0 && <span className="tnum text-[10px] text-st-ecartee">{s.brulantes} brûl.</span>}
          </button>
        ))}
      </div>
    </>
  )
}

/* ───────────── O9 — PIPELINE RARETÉ (S49) ───────────── */

type Rarete = { communes: { insee: string; commune: string; rythme_conso_ha_an: number | null
  budget_zan_ha: number | null; reste_zan_ha: number | null; horizon_epuisement_ans: number | null
  statut: string; stock_opportunites_ha: number | null; source: string }[] }

export function O9Rarete() {
  const q = useQuery({ queryKey: ['o9'], queryFn: () => jfetch<Rarete>('/pipeline-rarete') })
  const rows = q.data?.communes ?? []
  return (
    <>
      <Banner>La <b>rareté</b> comme argument : au rythme de consommation observé
        (<b>Sourcé</b> Cerema), combien d'années de budget ZAN reste-t-il ? Horizon court =
        foncier qui s'apprécie. <b>Estimé</b> : budget −50 % loi Climat, enveloppes Schéma d'Aménagement Régional (SAR)/SCOT
        non publiées (caveat loi TRACE).</Banner>
      {q.isLoading && <Loading accent="mint" label="Calcul des horizons…" />}
      {q.isError && <ErrorState className="py-6" message="Pipeline rareté indisponible." retry={() => q.refetch()} />}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <p className="label-caps sticky top-0 bg-surface-1 py-1 text-[9.5px]">Horizon d'épuisement du budget ZAN (estimé)</p>
        {rows.map((c) => {
          const depasse = c.statut === 'budget dépassé'
          const pct = depasse ? 100 : c.budget_zan_ha && c.reste_zan_ha != null
            ? Math.max(4, Math.min(100, (c.reste_zan_ha / c.budget_zan_ha) * 100)) : 0
          // classes LITTÉRALES (le JIT Tailwind ne voit pas les interpolations)
          const TONES = {
            ecartee: { bar: 'bg-st-ecartee', txt: 'text-st-ecartee' },
            creuser: { bar: 'bg-st-creuser', txt: 'text-st-creuser' },
            mint: { bar: 'bg-mint', txt: 'text-mint' },
          } as const
          const tone = TONES[depasse ? 'ecartee' : (c.horizon_epuisement_ans ?? 99) < 5 ? 'creuser' : 'mint']
          return (
            <div key={c.insee} data-o9-commune={c.insee} className="flex items-center gap-2 overflow-hidden border-b border-line py-1.5 text-[11px]">
              <span className="min-w-0 flex-1 truncate text-txt">{c.commune}</span>
              <span className="relative h-2 w-12 shrink-0 overflow-hidden rounded-full bg-surface-3">
                <span className={`absolute inset-y-0 left-0 rounded-full ${tone.bar}`} style={{ width: `${pct}%` }} />
              </span>
              <span className={`tnum w-14 shrink-0 text-right font-mono ${tone.txt}`}>
                {depasse ? 'dépassé' : c.horizon_epuisement_ans != null ? `${Math.round(c.horizon_epuisement_ans)} ans` : '—'}</span>
              <span className="tnum hidden w-[62px] shrink-0 text-right font-mono text-txt-dim sm:block">
                {c.stock_opportunites_ha != null ? `${c.stock_opportunites_ha} ha opp.` : '—'}</span>
            </div>
          )
        })}
      </div>
      {rows[0] && <p className="shrink-0 text-[9px] leading-snug text-txt-dim">Source : {rows[0].source}.</p>}
    </>
  )
}

/* ───────────── O10 — BASCULES DATÉES (S50) ───────────── */

type Bascules = { unread: number; items: { id: number; date: string; kind: string; idu: string | null
  titre: string; detail: string | null; demo?: boolean }[] }
const O10_FILTRES = [['', 'tout'], ['bascule', 'bascules'], ['match', 'matches'], ['bodacc', 'BODACC']] as const

export function O10Bascules() {
  const { select, setView } = useApp()
  const [kind, setKind] = useState('')
  const q = useQuery({ queryKey: ['o10'], queryFn: () => jfetch<Bascules>('/events?limit=100') })
  const items = (q.data?.items ?? []).filter((e) => !kind || e.kind.includes(kind))
  return (
    <>
      <Banner>Les <b>bascules datées</b> du run — une parcelle qui passe en Priorité, un match de
        profil, un événement BODACC : chaque changement d'état avec sa date. Le « quoi de
        neuf » du lundi matin, en lecture (marquer lu reste dans la cloche).</Banner>
      <div className="flex flex-wrap gap-1.5">
        {O10_FILTRES.map(([v, l]) => (
          <button key={v} data-o10-filtre={v} onClick={() => setKind(v)}
            className={`min-h-7 rounded-full border px-2.5 py-1 text-[11px] transition-colors duration-quick ${
              kind === v ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
      {q.isLoading && <Loading accent="mint" label="Lecture des événements…" />}
      {q.isError && <ErrorState className="py-6" message="Événements indisponibles." retry={() => q.refetch()} />}
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.map((e) => (
          <button key={e.id} data-o10-item onClick={() => { if (e.idu) { setView('cartes'); select(e.idu) } }}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5 text-left transition-colors duration-quick hover:border-mint/50">
            <span className="shrink-0 font-mono text-[10px] text-txt-dim">{e.date}</span>
            <span className={`shrink-0 rounded-full px-1.5 text-[8.5px] font-medium ${
              e.kind === 'match' ? 'bg-mint/15 text-mint' : 'bg-st-creuser/10 text-st-creuser'}`}>{e.kind}</span>
            {e.idu && <span className="shrink-0 font-mono text-[10.5px] text-txt-hi">{e.idu.slice(8)}</span>}
            <span className="min-w-0 flex-1 truncate text-[11px] text-txt">{e.titre.replace(/^🎯 /, '')}</span>
            {e.demo && <span className="shrink-0 rounded-full bg-mint/15 px-1.5 text-[8px] text-mint">DÉMO</span>}
          </button>
        ))}
        {!q.isLoading && items.length === 0 && (
          // M15 A2 : honnêteté — une bascule est un CHANGEMENT entre deux runs de scoring. Avec un
          // seul run servi, le flux est vide tant qu'un nouveau run n'a pas été comparé au précédent
          // (ou que la démo n'a pas été semée). Ce n'est pas un bug : l'outil lit le même journal
          // d'événements que la cloche de notifications.
          <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] leading-relaxed text-txt-mut">
            Aucune bascule sur ce filtre. Une bascule apparaît quand une <b>mise à jour des données</b>
            change l'état d'une parcelle par rapport à la précédente (ou via un événement BODACC daté).
            Le flux se remplira à la prochaine mise à jour — ce sont les mêmes alertes que la cloche.
          </p>
        )}
      </div>
    </>
  )
}
