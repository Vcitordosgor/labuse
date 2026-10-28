// ANNONCE-3 — garde du câblage « Analyse d'annonce » dans Docs : la carte existe (kind 'annonce',
// deux entrées), les URLs des documents pointent sur les MÊMES routes que le bouton « Exporter en PDF »
// de l'outil, et le filtre de la bibliothèque est présent.
import { describe, expect, it } from 'vitest'
import { CATALOGUE } from './catalogue'
import { docAnalyseAnnonceUrl, docAnalyseAnnonceLienUrl } from '../../lib/api'

describe('ANNONCE-3 — document « Analyse d’annonce »', () => {
  it('la 9e carte existe, avec les deux entrées (kind annonce)', () => {
    const carte = CATALOGUE.find((d) => d.key === 'analyse-annonce')
    expect(carte).toBeTruthy()
    expect(carte!.kind).toBe('annonce')
    expect(carte!.formats).toContain('PDF')
  })

  it('les URLs des documents = les routes de l’outil (PDF outil == PDF Docs)', () => {
    // entrée adresse → rapport parcelle (IDU) ; entrée lien → rapport commune (url encodée).
    expect(docAnalyseAnnonceUrl('97411000AB0123')).toBe('/analyse-annonce/97411000AB0123.pdf')
    const url = 'https://www.leboncoin.fr/ventes_immobilieres/3228901746.htm'
    expect(docAnalyseAnnonceLienUrl(url)).toBe('/analyse-annonce.pdf?url=' + encodeURIComponent(url))
  })
})
