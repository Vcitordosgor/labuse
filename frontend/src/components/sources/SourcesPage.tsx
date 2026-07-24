import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getSources } from '../../lib/api'
import { CLIENT } from '../../lib/strings'
import { TOKENS } from '../../lib/tokens'
import type { SourceInfo } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const STATUS_DOT: Record<string, string> = {
  active: TOKENS.mint, ok: TOKENS.mint, connecte: TOKENS.mint, partial: TOKENS.stCreuser, partiel: TOKENS.stCreuser,
  degraded: TOKENS.stCreuser, manuel: TOKENS.stCreuser, planned: TOKENS.txtDim, todo: TOKENS.txtDim, a_faire: TOKENS.txtDim,
  error: TOKENS.stEcartee, down: TOKENS.stEcartee,
}

// P4.2 (dernière passe) — « version la plus récente publiée » : rassure que LABUSE n'est pas
// en retard, c'est la SOURCE qui publie par millésime. Notes VÉRIFIÉES + repli sur l'année du nom.
const MILLESIME_VERIFIE: Record<string, string> = {
  'DVF / valeurs foncières': 'ventes jusqu’à déc. 2025',
  // M14 E2 (QA) : millésime réel de la donnée ingérée, renseigné là où il n'est ni dans le
  // nom ni dans un job daté. Filosofi carroyé 200 m = millésime 2021 (directive M14). BPE et
  // SAFER : millésime NON tracé en base localement → consigné, jamais inventé (voir Row).
  'Filosofi INSEE (carreaux 200 m)': 'millésime 2021',
}
function millesimeNote(s: SourceInfo): string | null {
  if (MILLESIME_VERIFIE[s.name]) return MILLESIME_VERIFIE[s.name]
  const y = s.name.match(/\b(19|20)\d{2}\b/)
  return y ? `millésime ${y[0]}` : null
}

// ── M6 Phase 2a (audit §1.11) : licence RÉELLE par source — plus jamais le repli
// « Données publiques » (R6). Le libellé est lu dans legal_notes (rempli ligne à ligne
// au 2a-p1, seed_sources.py = source de vérité) ; le référentiel par nom ne garde que
// les cas particuliers (usage encadré, non intégré, lignes hors seed).
const LICENCE_PAR_SOURCE: Record<string, string> = {
  'DVF / valeurs foncières': 'Licence Ouverte — usage encadré (art. L.112 A LPF)',
  'INPI RNE (dirigeants)': 'Licence INPI — réutilisation encadrée (L. 323-2 CRPA)',
  'Fichiers fonciers (Cerema)': 'Convention Cerema — non intégré',
  'PLH des 5 EPCI (extraction documentaire)': 'Documents publics — licence à confirmer',
  'RTAA DOM (textes réglementaires)': 'Textes officiels (Légifrance) — réutilisation libre',
  'DEAL Réunion (WMS/WFS)': 'Licence Ouverte (données État)',
  'DEAL Réunion — PPR / aléas': 'Licence Ouverte (données État)',
  '50 pas géométriques — limite haute (DEAL)': 'Licence Ouverte (données État)',
}
function licence(s: SourceInfo): string {
  if (LICENCE_PAR_SOURCE[s.name]) return LICENCE_PAR_SOURCE[s.name]
  const notes = s.legal_notes ?? ''
  if (/licence ouverte/i.test(notes)) return 'Licence Ouverte 2.0 (Etalab)'
  if (/odbl/i.test(notes)) return 'ODbL 1.0 (OpenStreetMap)'
  if (/CC BY 4\.0/i.test(notes)) return 'CC BY 4.0'
  // Jamais un libellé inventé : sans licence vérifiée à l'audit, on l'affiche tel quel.
  return 'Licence à confirmer'
}
// Lien vers le TEXTE de la licence (audit §1.11 : « lien licence » exigé par le mandat).
const LICENCE_URL: Record<string, string> = {
  'Licence Ouverte 2.0 (Etalab)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'Licence Ouverte (données État)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'Licence Ouverte — usage encadré (art. L.112 A LPF)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'ODbL 1.0 (OpenStreetMap)': 'https://www.openstreetmap.org/copyright',
  'CC BY 4.0': 'https://creativecommons.org/licenses/by/4.0/deed.fr',
  'Licence INPI — réutilisation encadrée (L. 323-2 CRPA)':
    'https://www.inpi.fr/sites/default/files/Licence%20donnees%20RNE_2024_0.pdf',
}

/** La date de mise à jour AFFICHÉE : la plus récente entre last_sync_at (posé par les jobs)
 *  et la dernière ingestion tracée dans ingestion_runs (servie par l'API — jamais en dur). */
function majReelle(s: SourceInfo): string | null {
  const a = s.last_sync_at, b = s.derniere_ingestion
  if (a && b) return b > a ? b : a
  return b ?? a
}

// M13-F1 (QA-55) : la fiche source ne porte plus AUCUN vocabulaire de statut (« Cadence non
// sondable », « fiabilité à confirmer », « manuel / grande passe — non sondable », « pas encore
// contrôlée manuellement »). DEUX informations, pas plus :
//   1. LA VERSION EN SERVICE  — millésime ou date de la donnée effectivement en base.
//   2. LE DERNIER CONTRÔLE     — quand LABUSE a vérifié pour la dernière fois que c'est bien
//      la version la plus récente (source_checks.verified_at). Si cette date n'existe pas en
//      base, on affiche la version SEULE — on n'invente jamais de date.
function Row({ s, focused }: { s: SourceInfo; focused: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: 'center' })
  }, [focused])

  // 1) VERSION EN SERVICE : la date de la DONNÉE en base d'abord (derniere_donnee), sinon le
  //    millésime que la source publie, sinon la date d'ingestion tracée. Jamais rien d'inventé ;
  //    si aucune de ces informations n'existe → repli HONNÊTE (jamais un « — » nu).
  const mil = millesimeNote(s)
  const donneeJusquau = s.derniere_donnee ? new Date(s.derniere_donnee).toLocaleDateString('fr-FR') : null
  const ingIso = majReelle(s)
  const version = donneeJusquau
    ? `données jusqu’au ${donneeJusquau}`
    : mil
      ? mil
      : ingIso
        ? `donnée du ${new Date(ingIso).toLocaleDateString('fr-FR')}`
        : 'millésime non tracé en base'

  // 2) M15 H1 — STATUT DE FRAÎCHEUR centré sur la VERSION (ce qui compte : « c'est bien la
  //    dernière version qui existe », pas « vérifié tel jour »). Trois états, selon le radar (LOT A) :
  //  • sondable + À JOUR ('a_jour')            → « ✓ Dernière version disponible » — le ✓ est
  //    VÉRIFIÉ par le radar (aucune version plus récente côté producteur), jamais déclaratif.
  //  • sondable + EN RETARD ('nouvelle_publication') → « Nouvelle version publiée » — ré-ingestion à faire.
  //  • NON SONDABLE ('non_sondable' / pas de radar) → factuel : « le producteur publie [cadence] ».
  //    Aucune promesse de vérification (pas d'URL datée) — mais PAS une source douteuse (cf. H2).
  const statut = s.radar?.statut ?? 'non_sondable'
  const sondable = statut === 'a_jour' || statut === 'nouvelle_publication'
  const verifieIso = s.radar?.derniere_verif ?? null
  const cadence = s.radar?.cadence ?? null

  const lic = licence(s)
  return (
    <div ref={ref} data-source-row
      className={`flex items-center gap-3 rounded-[10px] border px-4 py-3 ${
        focused ? 'border-mint bg-mint/[0.06]' : 'border-line-2 bg-surface-3'}`}>
      <span className="h-2 w-2 shrink-0 rounded-full print:hidden" style={{ background: STATUS_DOT[s.status ?? ''] ?? TOKENS.txtDim }}
        title={`Statut : ${s.status ?? 'inconnu'}`} />
      <div className="min-w-0 flex-1">
        {/* Ligne 1 : le nom de la source + marqueur sondable/déclaratif + producteur + licence + lien. */}
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-xs font-medium text-txt">{s.name}</span>
          {/* M15 H2 : marqueur DISCRET — vérifiée automatiquement (radar) vs déclarative. Non
              anxiogène : une source déclarative N'EST PAS douteuse, son producteur n'expose
              simplement pas de date interrogeable. */}
          {sondable ? (
            <span data-source-marqueur="auto" className="shrink-0 rounded-full bg-mint/10 px-1.5 py-px text-[8.5px] font-medium text-mint"
              title="Fraîcheur vérifiée automatiquement par notre radar (cette source expose une date interrogeable).">
              ✓ vérifiée auto
            </span>
          ) : (
            <span data-source-marqueur="declaratif" className="shrink-0 rounded-full bg-surface-2 px-1.5 py-px text-[8.5px] text-txt-dim"
              title="Fraîcheur déclarative : le producteur n'expose pas de date interrogeable, on s'appuie sur sa cadence de publication. Ce n'est PAS une source douteuse.">
              cadence producteur
            </span>
          )}
          {s.provider && <span className="text-[11px] text-txt-dim">{s.provider}</span>}
          {LICENCE_URL[lic] ? (
            <a data-source-licence href={LICENCE_URL[lic]} target="_blank" rel="noreferrer"
              className="text-[11px] text-txt-dim hover:underline" title="Texte de la licence">{lic}</a>
          ) : (
            <span data-source-licence className="text-[11px] text-txt-dim">{lic}</span>
          )}
          {s.documentation_url && (
            <a href={s.documentation_url} target="_blank" rel="noreferrer"
              className="text-[11px] font-medium text-mint hover:underline print:hidden" title={s.documentation_url}>
              Source officielle ↗
            </a>
          )}
        </div>
        {/* Ligne 2 (M15 H1) : version en service + STATUT de fraîcheur à trois états. Jamais de « — » nu. */}
        <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-0.5 text-[11px]">
          <span data-source-version className="text-txt">
            <span className="text-txt-dim">Version en service :</span>{' '}
            <span className="font-medium">{version}</span>
          </span>
          {statut === 'a_jour' ? (
            <span data-source-statut="a_jour" className="font-medium text-mint"
              title={`Vérifié par notre radar${verifieIso ? ` (dernier passage le ${new Date(verifieIso).toLocaleDateString('fr-FR')})` : ''} : aucune version plus récente n'existe côté producteur.`}>
              ✓ Dernière version disponible
            </span>
          ) : statut === 'nouvelle_publication' ? (
            <span data-source-statut="nouvelle" className="font-medium text-st-creuser"
              title="Le radar a détecté une publication plus récente côté producteur — ré-ingestion à lancer.">
              ▲ Nouvelle version publiée
            </span>
          ) : cadence ? (
            <span data-source-statut="cadence" className="text-txt-dim"
              title="Source non sondable automatiquement — fraîcheur fondée sur la cadence connue du producteur, pas sur une vérification.">
              le producteur publie <span className="text-txt-mut">{cadence}</span>
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const sourcesFocus = useApp((s) => s.sourcesFocus)

  // M5 : version du modèle P v2 (sha court + gel) et avertissement censure — additif.
  const modele = useQuery({
    queryKey: ['v2-modele'],
    queryFn: async () => {
      const r = await fetch('/v2/modele')
      if (!r.ok) throw new Error(`v2 ${r.status}`)
      return r.json() as Promise<{ model_version: string; sha256_court: string; gel: string;
        avertissement_censure: string; politique_recalibration: string }>
    },
    retry: false, staleTime: 5 * 60_000,
  }).data

  const cats = new Map<string, SourceInfo[]>()
  for (const s of data ?? []) {
    const k = s.category || 'Autres'
    cats.set(k, [...(cats.get(k) ?? []), s])
  }
  return (
    <div data-sources-page className="sources-print flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">Sources & fraîcheur</h2>
            {/* UX V1 ajout A : la phrase de positionnement — l'écran de crédibilité en rendez-vous */}
            <p data-sources-positionnement className="mt-1 text-[13px] font-medium leading-snug text-txt">
              Chaque réponse LABUSE est traçable jusqu'à sa source publique.
            </p>
          </div>
        </div>
        {/* M15 H1 : ce qui compte = « c'est bien la dernière version qui existe », pas « vérifié
            tel jour ». Statut de fraîcheur à trois états + marqueur sondable/déclaratif. */}
        <p className="mt-1.5 text-[11px] leading-relaxed text-txt-dim">
          Ce qui compte n'est pas de tout re-vérifier chaque jour, mais que <b className="text-txt-mut">la
          version consultée soit la dernière qui existe</b>. Un fichier INSEE de 2021 est à jour si
          l'INSEE n'a rien publié depuis. Pour les sources qui exposent une date interrogeable
          (<span className="text-mint">✓ vérifiée auto</span>), notre radar confirme
          <b className="text-txt-mut"> « ✓ Dernière version disponible »</b> — ou signale
          <b className="text-txt-mut"> « Nouvelle version publiée »</b> quand il faut ré-ingérer.
          Pour les autres (INSEE, SAFER… <span className="text-txt-dim">cadence producteur</span>),
          pas de vérification possible : on affiche la version et le rythme de publication du
          producteur. Une source non vérifiable n'est <b className="text-txt-mut">pas</b> une source
          douteuse.
        </p>

        {/* M13-F2 (QA-56) : le bloc « Ce que LABUSE mesure » (BAN 99,99 %, jamais de SQL généré,
            signal ANC) a été RETIRÉ de l'interface. Son contenu est conservé pour l'argumentaire
            commercial dans docs/ARGUMENTAIRE_PRECISION.md. */}

        {/* B4 (M12) : le bloc modèle est scindé. VISIBLE = le seul point de CONFIANCE (les niveaux
            récents sont provisoires, mais le CLASSEMENT reste fiable). REPLIÉ derrière « détail
            technique » = version/sha/gel/mécanique de recalage. */}
        {modele && (
          <div data-sources-modele className="mt-4 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5">
            <p className="text-[11px] leading-snug text-txt">{CLIENT.modele.confiance}</p>
            <details className="mt-1.5">
              <summary className="cursor-pointer list-none text-[10.5px] font-medium text-txt-dim hover:text-txt">
                ▸ {CLIENT.modele.detailToggle}
              </summary>
              <p className="mt-1 text-[10.5px] font-medium text-txt">
                Modèle de scoring : <span className="font-mono">{modele.model_version}</span>
                <span className="ml-1.5 font-mono text-[10px] text-txt-dim">
                  sha {modele.sha256_court} — gelé le {modele.gel.slice(0, 10)}
                </span>
              </p>
              <p className="mt-1 text-[10.5px] leading-snug text-st-creuser">▲ {modele.avertissement_censure}.</p>
              <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">{modele.politique_recalibration}.</p>
            </details>
          </div>
        )}

        {isLoading && <div className="mt-6"><Loading label="Chargement des sources" className="text-xs" /></div>}
        {isError && <p className="mt-6 text-xs text-st-ecartee">Sources inaccessibles — vérifiez votre réseau ou réessayez.</p>}
        {[...cats.entries()].map(([cat, list]) => (
          <div key={cat} className="mt-6">
            <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">{cat.toUpperCase()}</p>
            <div className="flex flex-col gap-2">
              {list.map((s) => <Row key={s.id} s={s} focused={s.name === sourcesFocus} />)}
            </div>
          </div>
        ))}
        <p className="mt-6 text-[11px] leading-relaxed text-txt-dim">
          Le contrôle automatique de fraîcheur est assuré par le <b className="text-txt-mut">radar</b>
          des sources (sonde des métadonnées amont, sans téléchargement), aujourd'hui hebdomadaire.
          Il ne couvre que les sources qui exposent une date interrogeable ; pour les autres, la
          fraîcheur repose sur la cadence connue du producteur.
        </p>
      </div>
    </div>
  )
}
