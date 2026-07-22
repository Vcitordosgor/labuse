/** Design system LABUSE — dérivé de docs/design/mockups/ (cf. frontend/DERIVATIONS.md). */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#060A08',
        'surface-1': '#0B100D',
        'surface-2': '#0D120F',
        'surface-3': '#111814',
        line: '#1B2620',
        'line-2': '#1E2A23',
        mint: '#5CE6A1',
        'mint-ink': '#06130C',
        // LOI-0 · violet = l'exclusivité premium/IA/outils (remplace les #B497F0 en dur,
        // migrés au fil des surfaces — jamais de nouvel hex local).
        violet: '#B497F0',
        'txt-hi': '#ECF5EF',
        txt: '#C9DCD1',
        'txt-mut': '#8FA69A',
        'txt-dim': '#5C7268',
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
      },
      // LOI-0 · motion : deux durées, une courbe — 150 ms (feedback), 200 ms (entrées).
      transitionDuration: { quick: '150ms', soft: '200ms' },
      transitionTimingFunction: { cockpit: 'cubic-bezier(.2,.7,.2,1)' },
    },
  },
  plugins: [],
}
