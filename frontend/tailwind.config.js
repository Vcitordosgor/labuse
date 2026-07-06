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
    },
  },
  plugins: [],
}
