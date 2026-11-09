// RETOURS-21 — DRAPEAU DE MODALITÉ D'ENTRÉE, source unique du focus de toute l'app.
//
// Problème WebKit/Safari : un champ texte matche `:focus-visible` MÊME au clic souris (la spec
// considère le focus éditable comme « visible »). Une règle `:focus-visible { outline }` peindrait
// donc un contour quand on CLIQUE un champ dans Safari — ce que l'on ne veut pas.
//
// Solution : on marque la dernière modalité sur `<html data-input>` — `mouse` dès qu'un pointeur
// agit, `key` dès qu'une touche DÉPLACE le focus (Tab/flèches/Home/Fin/PagePrec-Suiv/Échap). La
// feuille de styles (index.css) supprime tout focus visible sous `html[data-input="mouse"]`, et ne
// laisse le contour vert `:focus-visible` que sinon (clavier). Les touches de SAISIE (lettres) ne
// basculent pas en `key` : taper dans un champ cliqué ne fait pas apparaître de contour.
const CLAVIER_FOCUS = new Set([
  'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
  'Home', 'End', 'PageUp', 'PageDown', 'Escape',
])

export function installFocusModality(): void {
  if (typeof document === 'undefined') return
  const set = (mode: 'mouse' | 'key') => {
    if (document.documentElement.getAttribute('data-input') !== mode) {
      document.documentElement.setAttribute('data-input', mode)
    }
  }
  // pointeur (souris/tactile/stylet) → aucun focus visible
  window.addEventListener('pointerdown', () => set('mouse'), true)
  // au repos, on démarre en « souris » : aucun contour tant qu'on n'a pas navigué au clavier
  set('mouse')
  // touche qui DÉPLACE le focus → on autorise le contour vert clavier
  window.addEventListener('keydown', (e) => {
    if (CLAVIER_FOCUS.has(e.key)) set('key')
  }, true)
}
