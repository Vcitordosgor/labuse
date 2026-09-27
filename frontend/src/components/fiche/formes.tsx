/**
 * fiche/formes.tsx — KELFONCIER-FIX-2 (Partie B).
 * LES DOUZE FORMES de l'intérieur des sections de la fiche, telles que la maquette v3
 * (docs/audit-2026-09/fiche-fix-3/maquette-v3.html) les dessine. Un composant par forme, PUREMENT
 * présentationnel : aucune requête, AUCUN calcul (pas de somme, de %, de seuil inventé). Les valeurs,
 * phrases de verdict, « — » et « non réglementé » arrivent déjà servis par le back et sont rendus tels
 * quels. La DA passe par les tokens de l'app (var(--…), tailwind.config) — jamais une couleur en dur
 * hors mapping de la maquette. Styles INLINE (pas d'ajout à index.css) pour rester self-contained et
 * ne collisionner avec aucune classe existante (`.tiles`, `.row`, `.frise`… vivent peut-être déjà).
 */
import { useState, type CSSProperties, type ReactNode } from 'react'
import { Bouton } from '../ui/Bouton'
import { Chip } from '../ui/Chip'
import { Tip } from '../Tip'

// ── « i » PARTAGÉ (FICHE-FIX-4) ─────────────────────────────────────────────
// Le point « i » qui porte un texte d'explication : jamais un paragraphe dans le flux, toujours
// derrière ce déclencheur (clic/tap/focus, cf. Tip `garder`). Utilisable en `info` de <Ligne> ou seul.
export function InfoI({ tip, aria = 'Détails' }: { tip: ReactNode; aria?: string }) {
  return (
    <Tip tip={tip} garder side="bottom">
      <span role="button" tabIndex={0} aria-label={aria}
        style={{ marginLeft: 3, display: 'inline-flex', width: 12, height: 12, flex: 'none', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', border: '1px solid var(--line-2)', fontSize: 8, fontWeight: 700, lineHeight: 1, color: 'var(--txt-dim)', cursor: 'pointer', verticalAlign: 'middle' }}>i</span>
    </Tip>
  )
}

// Maquette v3 → tokens de l'app. Le vert redevient un SIGNAL (mint), l'ambre = attention, le rouge =
// blocage, le gris = neutre/absent. « txt » = clair (--txt-hi), « mut » = gris libellé, « dim » = discret.
export type FormeTon = 'vert' | 'ambre' | 'rouge' | 'gris'
const DOT: Record<FormeTon, string> = {
  vert: 'var(--mint)', ambre: 'var(--amber)', rouge: 'var(--st-ecartee)', gris: 'var(--txt-off)',
}
const VAL_COLOR: Partial<Record<FormeTon, string>> = {
  ambre: 'var(--amber)', rouge: 'var(--st-ecartee)', gris: 'var(--txt-dim)', vert: 'var(--mint)',
}
const mono: CSSProperties = { fontFamily: 'var(--mono, ui-monospace, Menlo, monospace)', fontVariantNumeric: 'tabular-nums' }

// ── 1 · VERDICT ─────────────────────────────────────────────────────────────
// Puce colorée + phrase : la RÉPONSE en gras, le CONTEXTE en gris. Jamais une boîte (maquette .verdict).
export function Verdict({ ton = 'vert', reponse, contexte }: {
  ton?: FormeTon; reponse: ReactNode; contexte?: ReactNode
}) {
  return (
    <div data-forme="verdict" style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 10 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', marginTop: 5, flex: 'none', background: DOT[ton] }} />
      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.4, color: 'var(--txt-hi)' }}>
        <b style={{ fontWeight: 500 }}>{reponse}</b>{contexte != null && <> <span style={{ color: 'var(--txt-dim)' }}>{contexte}</span></>}
      </p>
    </div>
  )
}

// ── 2 · TUILES ──────────────────────────────────────────────────────────────
// Grille 2 ou 3 colonnes, style du bandeau : libellé, valeur mono, sous-ligne. Variantes ambre/rouge/gris.
export type Tuile = { label: ReactNode; valeur: ReactNode; sous?: ReactNode; ton?: FormeTon }
export function Tuiles({ cols = 2, items }: { cols?: 2 | 3; items: Tuile[] }) {
  return (
    <div data-forme="tuiles" style={{ display: 'grid', gridTemplateColumns: `repeat(${cols},1fr)`, gap: 6 }}>
      {items.map((t, i) => (
        // FICHE-FIX-4 (Lot B) — libellé et sous-ligne tronqués en « … » avec le texte complet en `title`
        // (ex. Terrain › Exposition « versant (RGE ALTI, fenêtre 200 m) ») ; la valeur ne se coupe jamais.
        <div key={i} style={{ border: '1px solid var(--line)', borderRadius: 6, background: 'var(--bg-3)', padding: '7px 8px 6px', minWidth: 0 }}>
          <div title={typeof t.label === 'string' ? t.label : undefined} style={{ color: 'var(--txt-dim)', fontSize: 10.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.label}</div>
          <div style={{ ...mono, fontSize: 14, fontWeight: 500, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: (t.ton && VAL_COLOR[t.ton]) || 'var(--txt-hi)' }}>{t.valeur}</div>
          {t.sous != null && <div title={typeof t.sous === 'string' ? t.sous : undefined} style={{ fontSize: 10.5, color: 'var(--txt-off)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.sous}</div>}
        </div>
      ))}
    </div>
  )
}

// ── 3 · LIGNE ───────────────────────────────────────────────────────────────
// Clé → valeur mono à droite ; la valeur passe à la ligne (jamais de débordement). Grouper dans <Lignes>.
export function Lignes({ children }: { children: ReactNode }) {
  return <div data-forme="lignes" style={{ marginTop: 8 }}>{children}</div>
}
// FICHE-FIX-4 (Lot B) — la VALEUR ne se coupe JAMAIS en son milieu (nowrap : plus de « 17 515 € »
// rendu caractère par caractère) ; le seul retour à la ligne autorisé est ENTRE le libellé et la
// valeur (flex-wrap sur la ligne → la valeur descend en bloc si elle ne tient pas). `title` porte le
// texte complet quand la valeur est tronquée.
export function Ligne({ label, valeur, ton, info, title }: {
  label: ReactNode; valeur: ReactNode; ton?: FormeTon; info?: ReactNode; title?: string
}) {
  return (
    <div data-forme="ligne" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'baseline', gap: '2px 10px', padding: '5px 0', borderBottom: '1px solid var(--line)', fontSize: 12.5 }}>
      <span style={{ color: 'var(--txt-hi)', display: 'flex', alignItems: 'baseline', gap: 5, minWidth: 0 }}>{label}{info}</span>
      <span title={title} style={{ ...mono, textAlign: 'right', flex: 'none', marginLeft: 'auto', minWidth: 0, maxWidth: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: (ton && VAL_COLOR[ton]) || 'var(--txt-hi)' }}>{valeur}</span>
    </div>
  )
}

// ── 4 · JAUGE3 ──────────────────────────────────────────────────────────────
// Trois crans faible / moyen / fort + % de parcelle. `niveau` 1..3 ; fort = rouge, sinon ambre.
export function Jauge3({ label, niveau, pct, extra }: {
  label: ReactNode; niveau: 0 | 1 | 2 | 3; pct?: ReactNode; extra?: ReactNode
}) {
  const on = (i: number) => i < niveau
  const color = niveau >= 3 ? 'var(--st-ecartee)' : 'var(--amber)'
  return (
    <div data-forme="jauge3" style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', alignItems: 'center', columnGap: 8, padding: '5px 0', borderBottom: '1px solid var(--line)', fontSize: 12.5 }}>
      <span style={{ color: 'var(--txt-hi)' }}>{label}{extra}</span>
      <span style={{ display: 'flex', gap: 2 }}>
        {[0, 1, 2].map((i) => <i key={i} style={{ width: 14, height: 6, borderRadius: 2, background: on(i) ? color : 'var(--line-2)' }} />)}
      </span>
      <span style={{ ...mono, fontSize: 11, color: 'var(--txt-dim)', minWidth: 40, textAlign: 'right' }}>{pct}</span>
    </div>
  )
}

// ── 5 · BARRE EMPILÉE ─────────────────────────────────────────────────────────
// Parts + légende (maquette .stack / .legend). Chaque part porte SON % déjà servi (aucun recalcul).
export type Part = { pct: number; color: string; label: ReactNode }
export function BarreEmpilee({ parts }: { parts: Part[] }) {
  return (
    <div data-forme="barre-empilee">
      <div style={{ display: 'flex', height: 8, borderRadius: 999, overflow: 'hidden', background: 'var(--line-2)', marginTop: 8 }}>
        {parts.map((p, i) => <i key={i} style={{ display: 'block', height: '100%', width: `${p.pct}%`, background: p.color }} />)}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', marginTop: 6, fontSize: 11, color: 'var(--txt-dim)' }}>
        {parts.map((p, i) => (
          <span key={i}><i style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, marginRight: 4, verticalAlign: -1, background: p.color }} />{p.label}</span>
        ))}
      </div>
    </div>
  )
}

// ── 6 · CASES D'ÉTAT ─────────────────────────────────────────────────────────
// Rangée de 4 : ✓ vert / ? ambre / ✕ rouge, libellé, valeur (maquette .checks / .chk).
export type CaseEtat = { etat: 'ok' | 'q' | 'ko'; label: ReactNode; valeur?: ReactNode }
const CASE_MARK = { ok: '✓', q: '?', ko: '✕' } as const
const CASE_COLOR = { ok: 'var(--mint)', q: 'var(--amber)', ko: 'var(--st-ecartee)' } as const
export function CasesEtat({ cases }: { cases: CaseEtat[] }) {
  return (
    <div data-forme="cases-etat" style={{ display: 'grid', gridTemplateColumns: `repeat(${cases.length || 1},1fr)`, gap: 6 }}>
      {cases.map((c, i) => (
        <div key={i} style={{ border: '1px solid var(--line)', borderRadius: 6, background: 'var(--bg-3)', padding: '6px 4px', textAlign: 'center' }}>
          <div style={{ fontSize: 14, lineHeight: 1, color: CASE_COLOR[c.etat] }}>{CASE_MARK[c.etat]}</div>
          <div style={{ fontSize: 10.5, color: 'var(--txt-dim)', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.label}</div>
          {c.valeur != null && <div style={{ ...mono, fontSize: 11, marginTop: 1, color: 'var(--txt-hi)' }}>{c.valeur}</div>}
        </div>
      ))}
    </div>
  )
}

// ── 7 · FRISE ──────────────────────────────────────────────────────────────
// Segments datés (maquette .frise) : segments « anciens » (gris) puis « actuel » (vert). flex = poids.
export type Segment = { annee?: ReactNode; label: ReactNode; ton?: 'ancien' | 'actuel'; poids?: number }
export function Frise({ segments }: { segments: Segment[] }) {
  return (
    <div data-forme="frise" style={{ display: 'flex', height: 22, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--line-2)', marginTop: 6, fontSize: 10.5 }}>
      {segments.map((s, i) => {
        const actuel = s.ton === 'actuel'
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', padding: '0 8px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            flex: s.poids ?? (actuel ? 4 : 3), borderLeft: i ? '1px solid var(--line-2)' : undefined,
            background: actuel ? 'var(--mint-bg)' : 'var(--bg-3)', color: actuel ? 'var(--mint)' : 'var(--txt-dim)' }}>
            {s.annee != null && <span style={{ ...mono, marginRight: 6, color: 'var(--txt-off)' }}>{s.annee}</span>}{s.label}
          </div>
        )
      })}
    </div>
  )
}

// ── 8 · PASTILLES ─────────────────────────────────────────────────────────────
// Chip allumée (vert, avec date) / éteinte (grisée, pointillé) — maquette .disp .pill / .pill.off.
export type Pastille = { label: ReactNode; date?: ReactNode; on: boolean }
export function Pastilles({ items }: { items: Pastille[] }) {
  return (
    <div data-forme="pastilles" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
      {items.map((p, i) => (
        // allumée → Chip `on` (aplat vert) avec date ; éteinte → Chip neutre pointillé, non actif.
        <Chip key={i} ton="vert" on={p.on} aria-disabled={!p.on} tabIndex={-1}
          style={p.on ? undefined : { borderStyle: 'dashed', opacity: 0.7, cursor: 'default' }}>
          {p.label}{p.on && p.date != null && <small style={{ marginLeft: 5, opacity: 0.75, fontSize: 10 }}>{p.date}</small>}
        </Chip>
      ))}
    </div>
  )
}

// ── 9 · RÉGLETTE ──────────────────────────────────────────────────────────────
// Repère commune (trait) + curseur secteur (rond), sur une barre (maquette .range). Positions en % SERVIES.
export function Reglette({ communePct = 50, secteurPct, gauche, droite }: {
  communePct?: number; secteurPct: number; gauche?: ReactNode; droite?: ReactNode
}) {
  const clamp = (n: number) => Math.max(0, Math.min(100, n))
  return (
    <div data-forme="reglette" style={{ marginTop: 8 }}>
      <div style={{ position: 'relative', height: 6, borderRadius: 999, background: 'var(--line-2)' }}>
        <s style={{ position: 'absolute', top: -2, left: `${clamp(communePct)}%`, width: 2, height: 10, background: 'var(--txt-dim)' }} />
        <b style={{ position: 'absolute', top: -3, left: `${clamp(secteurPct)}%`, width: 12, height: 12, borderRadius: '50%', background: 'var(--mint)', border: '2px solid var(--bg-2)', transform: 'translateX(-50%)' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 10.5, color: 'var(--txt-dim)', marginTop: 4 }}>
        <span>{gauche}</span><span style={{ color: 'var(--mint)' }}>{droite}</span>
      </div>
    </div>
  )
}

// ── 10 · TABLEAU 3 COLONNES ─────────────────────────────────────────────────────
// Zone / Commune / Île, colonne Zone en vert (maquette .cmp). Valeurs mono, déjà servies.
export type Ligne3 = { label: ReactNode; zone: ReactNode; commune: ReactNode; ile: ReactNode }
export function Tableau3({ entetes = ['Zone', 'Commune', 'Île'], lignes }: {
  entetes?: [ReactNode, ReactNode, ReactNode]; lignes: Ligne3[]
}) {
  const H = ({ children, first }: { children: ReactNode; first?: boolean }) => (
    <span style={{ color: 'var(--txt-dim)', fontSize: 10.5, paddingBottom: 4, borderBottom: '1px solid var(--line)', textAlign: first ? 'left' : 'right' }}>{children}</span>
  )
  const C = ({ children, num, zone }: { children: ReactNode; num?: boolean; zone?: boolean }) => (
    <span style={{ padding: '5px 0', borderBottom: '1px solid var(--line)', ...(num ? { ...mono, textAlign: 'right' } : {}), ...(zone ? { color: 'var(--mint)' } : {}) }}>{children}</span>
  )
  return (
    <div data-forme="tableau3" style={{ display: 'grid', gridTemplateColumns: '1fr repeat(3,auto)', columnGap: 10, fontSize: 12, marginTop: 4 }}>
      <H first><>&nbsp;</></H><H>{entetes[0]}</H><H>{entetes[1]}</H><H>{entetes[2]}</H>
      {lignes.map((l, i) => (
        <Frag key={i}>
          <C>{l.label}</C><C num zone>{l.zone}</C><C num>{l.commune}</C><C num>{l.ile}</C>
        </Frag>
      ))}
    </div>
  )
}
// petit fragment pour les 4 cellules d'une ligne (la grille est à plat)
function Frag({ children }: { children: ReactNode }) { return <>{children}</> }

// ── 11 · REPLI ──────────────────────────────────────────────────────────────
// ◀ + compteur (fermé) ; ▼ vert (ouvert). Aucune donnée cachée : le contenu est rendu, replié par défaut.
export function Repli({ compteur, label, children, defaultOpen = false }: {
  compteur?: ReactNode; label: ReactNode; children: ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div data-forme="repli">
      <button type="button" data-repli-toggle aria-expanded={open} onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, color: open ? 'var(--mint)' : 'var(--txt-dim)', fontSize: 12, padding: '6px 0 0', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' }}>
        <span style={{ fontSize: 9, color: open ? 'var(--mint)' : 'var(--txt-faint)' }}>{open ? '▼' : '◀'}</span>
        {compteur != null && <b style={{ color: 'var(--txt-hi)', fontWeight: 500 }}>{compteur}</b>}
        <span>{label}</span>
      </button>
      {open && <div style={{ marginTop: 4 }}>{children}</div>}
    </div>
  )
}

// ── 12 · OUTILS DE SECTION ─────────────────────────────────────────────────────
// Grille 2 colonnes de Bouton en PIED de section. UN SEUL secondaire vert par section (le geste
// principal) ; le reste neutre. `full` = pleine largeur (maquette .tools .full).
export type OutilSection = { label: ReactNode; onClick: () => void; principal?: boolean; full?: boolean; data?: string }
// Le composant Bouton n'a pas de ton « neutre » (vert/ambre/ia/danger) ; le tool NEUTRE de la maquette
// (.tools .btn : bord --line2, texte --txt) est obtenu en neutralisant le ton vert par un override de
// classes (les seules valeurs en dur autorisées = tokens de l'app). Le PRINCIPAL garde le vert (.btn.sec).
const NEUTRE_CLS = '!border-line-2 !text-txt !bg-transparent hover:!bg-surface-3 hover:!text-txt-hi hover:!border-line-3'
export function OutilsSection({ outils }: { outils: OutilSection[] }) {
  return (
    <div data-forme="outils-section" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 10 }}>
      {outils.map((o, i) => (
        <div key={i} style={o.full ? { gridColumn: '1 / -1' } : undefined}>
          <Bouton niveau="secondaire" ton="vert" data-porte={o.data} onClick={o.onClick}
            className={`w-full justify-between ${o.principal ? '' : NEUTRE_CLS}`}>
            {o.label}<span style={{ color: o.principal ? 'var(--mint)' : 'var(--txt-faint)' }}>→</span>
          </Bouton>
        </div>
      ))}
    </div>
  )
}
