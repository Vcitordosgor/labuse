/** Design system LABUSE — dérivé de docs/design/mockups/ (cf. frontend/DERIVATIONS.md). */
import { createRequire } from 'module'
// Source UNIQUE du vert de marque, partagée avec le back (src/labuse/brand.py lit le même JSON).
const brand = createRequire(import.meta.url)('../config/brand_colors.json')

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ═══ DA v3 (docs/DA-LABUSE.html §1) — SOURCE des couleurs. Miroir exact en
        //     :root (styles/index.css) pour les classes-composants et les styles inline,
        //     et en TOKENS (lib/tokens.ts). Une seule palette : les anciens noms
        //     (bg/surface-*/line*/txt-*/mint-ink) sont des ALIAS repointés sur les
        //     valeurs DA — pas de doublon de valeur, juste des alias de migration. ═══
        // surfaces et filets
        'bg-0': '#0A0C0B', 'bg-1': '#0C0F0D', 'bg-2': '#111614',
        'bg-stat': '#141A17', 'bg-3': '#161C19',
        'line-3': '#2C3630', 'line-card': '#1E2622', 'line-btn': '#263029',
        // alias rétro → valeurs DA
        bg: '#0A0C0B',
        'surface-1': '#0C0F0D',
        'surface-2': '#111614',
        'surface-3': '#161C19',
        line: '#1A211D',
        'line-2': '#212A25',
        // sémantique DA
        mint: brand.mint, 'mint-bg': '#12291D', 'mint-on': '#06301A', 'mint-sub': '#0B4526',
        'mint-ink': '#06301A', // alias rétro → mint-on
        amber: '#E0A94F', 'amber-bg': '#2A2113',
        coral: '#E2726A', 'coral-bg': '#2B1715',
        blue: '#8FB4F0',
        iris: '#8B7BD8', 'iris-2': '#C4B5FD', 'iris-bg': '#16121F', 'iris-line': '#2E2545',
        danger: '#8A5A5A', 'danger-line': '#3A2626',
        // M26-B · tokens de l'écran Copilote — repris de la maquette B4 validée
        // (docs/mandats/copilote_maquette_B4_reference_M26B.html), palette légèrement
        // distincte de l'app (mint plus clair, fond plus neutre). Préfixe cp-, scope
        // strict : ces tokens ne sortent pas de components/copilote/.
        'cp-bg': '#070A09',
        'cp-card': '#0D1211',
        'cp-card2': '#111716',
        // M69 B — le vert Copilote `cp-mint #63F2B8` est SUPPRIMÉ : aligné sur le vert de marque
        // unique `mint` #4ADE80 (les classes cp-mint sont devenues mint dans components/copilote/).
        'cp-violet': '#B497F0',
        // M117 · surface IA du Copilote (maquette DA-COPILOTE-v2). Le mauve #B497F0 (= violet/cp-violet)
        // est l'accent DOMINANT ici ; le mint ne reste QUE sur le brief du matin (veille ≠ IA). Ces
        // tokens portent les CARTES et bordures IA (card / porte / précision / récap-péage / projet).
        'cp-ia': '#B497F0',
        'cp-ia-on': '#14091F',
        'cp-ia-bg': '#100C1C',
        'cp-ia-border': '#2A2340',
        'cp-ia-border-on': '#4C3F73',
        'cp-ia-dim': '#1A1430',
        'cp-warn': '#D9873D', 'cp-warn-bg': '#140F08', 'cp-warn-border': '#4A3520',
        'cp-danger': '#E2725B', 'cp-danger-bg': '#140A08', 'cp-danger-border': '#4A2820',
        'cp-amber': '#F0C97A',
        'cp-red': '#F08A8A',
        'cp-tier': '#F0A87A',
        'cp-txt': '#EDF3EF',
        'cp-muted': '#8A9A92',
        'cp-faint': '#57655E',
        'cp-line': 'rgba(255,255,255,.08)',
        'cp-line2': 'rgba(255,255,255,.14)',
        // LOI-0 · violet = l'exclusivité premium/IA/outils (remplace les #B497F0 en dur,
        // migrés au fil des surfaces — jamais de nouvel hex local).
        violet: '#B497F0',
        // texte — 8 niveaux DA (valeurs repointées ; ancien txt-mut #8FA69A / txt-dim
        // #5C7268 adoptent la sémantique DA : txt-dim=libellé, txt-mut=sous-titre)
        'txt-hi': '#E8EFEA',
        txt: '#B8C4BC',
        lab: '#7C8A82',
        'txt-dim': '#8A968F',
        'txt-mut': '#6B776F',
        'txt-off': '#5E6B64',
        'txt-faint': '#4E5A53',
        'txt-ghost': '#3E4A44',
        // statuts matrice premium v2 (cf. DERIVATIONS)
        'st-chaude': '#5CE6A1',
        'st-surveiller': '#4ADE96',
        'st-creuser': '#E8B44C',
        'st-ecartee': '#E8695A',
        'st-exclue': '#6B7A72',
        'st-none': '#39463F',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      // LOI-0 · élévation : la profondeur vient du FOND + d'une ombre discrète, pas des
      // bordures dures. 3 niveaux seulement : panneau posé < flottant < sommet (toast/modal).
      boxShadow: {
        'elev-1': '0 1px 2px rgba(0,0,0,.35), 0 4px 14px -8px rgba(0,0,0,.45)',
        'elev-2': '0 2px 6px rgba(0,0,0,.4), 0 12px 32px -12px rgba(0,0,0,.6)',
        'elev-3': '0 4px 12px rgba(0,0,0,.45), 0 24px 56px -16px rgba(0,0,0,.7)',
        // DA v3 §1/§2 (règle « ni halo ni lueur ») — réservée aux surfaces qui flottent
        flottante: '0 8px 24px rgba(0,0,0,.45)',
      },
      // DA v3 §1 — rayons (carte 12=rounded-xl défaut ; groupe/porte 11 ; contrôle 10 ; pastille 20)
      borderRadius: { g: '11px', ctl: '10px', pill: '20px' },
      // DA v3 §1 — ombre flottante (la SEULE ombre autorisée : menus, notifs, infobulles)
      // + durées/courbe DA (survol 120ms, base 180ms, accordéon 200ms ; ease sans rebond)
      // LOI-0 · motion : deux durées, une courbe — 150 ms (feedback), 200 ms (entrées).
      transitionDuration: { quick: '150ms', soft: '200ms', fast: '120ms', base: '180ms' },
      transitionTimingFunction: { cockpit: 'cubic-bezier(.2,.7,.2,1)', da: 'cubic-bezier(.2,0,0,1)' },
    },
  },
  plugins: [],
}
