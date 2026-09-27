import { describe, expect, it } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import {
  Verdict, Tuiles, Lignes, Ligne, Jauge3, BarreEmpilee, CasesEtat, Frise,
  Pastilles, Reglette, Tableau3, Repli, OutilsSection,
} from './formes'

// KELFONCIER-FIX-2 (Partie B) — SNAPSHOTS DES 12 FORMES. Chaque forme est rendue avec des données
// représentatives (identiques à la maquette v3) : le snapshot verrouille sa STRUCTURE (un data-forme
// par composant, la DA figée). Un changement de rendu non voulu casse ici avant la revue visuelle.
const noop = () => {}

describe('formes de la fiche (maquette v3) — 12 composants', () => {
  it('Verdict', () => {
    const { container } = render(<Verdict ton="ambre" reponse="AU1est, à urbaniser" contexte="le règlement fixe la hauteur et se tait sur le reste." />)
    expect(container.querySelector('[data-forme="verdict"]')).toBeTruthy()
    expect(container.querySelector('b')?.textContent).toContain('AU1est')
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Tuiles', () => {
    const { container } = render(<Tuiles cols={3} items={[
      { label: 'Hauteur max', valeur: '4 m', sous: 'art. 10 · p. 59' },
      { label: 'Emprise', valeur: '—', sous: 'non réglementée', ton: 'gris' },
      { label: 'Destinations', valeur: '1', sous: '22 interdites', ton: 'ambre' },
    ]} />)
    expect(container.querySelector('[data-forme="tuiles"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Ligne / Lignes', () => {
    const { container } = render(<Lignes>
      <Ligne label="PLU" valeur="approuvé 17/12/2025" />
      <Ligne label="Préemption" valeur="DPU simple" ton="ambre" />
    </Lignes>)
    expect(container.querySelectorAll('[data-forme="ligne"]').length).toBe(2)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Jauge3', () => {
    const { container } = render(<><Jauge3 label="Inondation" niveau={1} pct="100 %" /><Jauge3 label="Mouvement" niveau={3} pct="100 %" /></>)
    expect(container.querySelectorAll('[data-forme="jauge3"]').length).toBe(2)
    expect(container).toMatchSnapshot()
  })

  it('BarreEmpilee', () => {
    const { container } = render(<BarreEmpilee parts={[
      { pct: 63.6, color: '#6b7280', label: 'Imperméabilisé 63,6 %' },
      { pct: 26.1, color: 'var(--mint)', label: 'Végétalisé 26,1 %' },
    ]} />)
    expect(container.querySelector('[data-forme="barre-empilee"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('CasesEtat', () => {
    const { container } = render(<CasesEtat cases={[
      { etat: 'ok', label: 'Voirie', valeur: '≤ 10 m' },
      { etat: 'ok', label: 'Fibre', valeur: 'FttH' },
      { etat: 'ok', label: 'Bus', valeur: '135 m' },
      { etat: 'q', label: 'Assainis.', valeur: '19 %' },
    ]} />)
    expect(container.querySelector('[data-forme="cases-etat"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Frise', () => {
    const { container } = render(<Frise segments={[
      { annee: '2019', label: 'TCO', ton: 'ancien' },
      { annee: '2022', label: 'EPF Réunion', ton: 'actuel' },
    ]} />)
    expect(container.querySelector('[data-forme="frise"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Pastilles', () => {
    const { container } = render(<Pastilles items={[
      { label: 'ZFANG', date: '2019', on: true },
      { label: 'QPV', on: false },
    ]} />)
    expect(container.querySelector('[data-forme="pastilles"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Reglette', () => {
    const { container } = render(<Reglette communePct={50} secteurPct={62} gauche="commune 3 633 €/m²" droite="secteur +7 %" />)
    expect(container.querySelector('[data-forme="reglette"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Tableau3', () => {
    const { container } = render(<Tableau3 lignes={[
      { label: 'Habitants', zone: '35', commune: '104 k', ile: '876 k' },
      { label: 'Moins de 25 ans', zone: '30 %', commune: '36 %', ile: '37 %' },
    ]} />)
    expect(container.querySelector('[data-forme="tableau3"]')).toBeTruthy()
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Repli (fermé par défaut, ouvre au clic)', () => {
    const { container, getByRole } = render(<Repli compteur="10 couches" label="sans objet"><div data-contenu>caché</div></Repli>)
    expect(container.querySelector('[data-forme="repli"]')).toBeTruthy()
    expect(container.querySelector('[data-contenu]')).toBeNull()   // replié par défaut
    fireEvent.click(getByRole('button'))
    expect(container.querySelector('[data-contenu]')).toBeTruthy() // ouvert au clic
    expect(container.firstChild).toMatchSnapshot()
  })

  it('OutilsSection (un seul principal vert)', () => {
    const { container } = render(<OutilsSection outils={[
      { label: 'Simuler l\'ouverture', onClick: noop, principal: true, data: 'plu' },
      { label: 'Voir l\'article', onClick: noop },
      { label: 'Annuaire PLU', onClick: noop },
      { label: 'Vérif procédure', onClick: noop },
    ]} />)
    expect(container.querySelector('[data-forme="outils-section"]')).toBeTruthy()
    expect(container.querySelectorAll('button').length).toBe(4)
    expect(container.firstChild).toMatchSnapshot()
  })
})
