import { describe, expect, it } from 'vitest'
import { cadastreGeoportailUrl, googleMapsUrl, pagesJaunes, type Coords } from './liensExternes'

// RETOURS-10 (T4.3) — chaque lien de l'en-tête mène à la BONNE donnée : les cartes (Cadastre/Maps)
// centrées sur le centroïde de la parcelle, Pages jaunes sur l'adresse exacte (repli commune annoncé).
// Parcelle témoin (maquette) : 97408000AP1599, La Possession. Centroïde fictif [lon, lat].
const COORDS: Coords = [55.335, -20.925] // [longitude, latitude]

describe('T4 — liens externes de la fiche', () => {
  it('Cadastre Géoportail : centré sur le centroïde (c=lon,lat), zoom parcellaire, couche cadastre', () => {
    const u = new URL(cadastreGeoportailUrl(COORDS))
    expect(u.host).toBe('www.geoportail.gouv.fr')
    expect(u.searchParams.get('c')).toBe('55.335,-20.925') // lon,lat — ordre Géoportail
    expect(u.searchParams.get('z')).toBe('19')             // zoom parcellaire
    // la couche PARCELLAIRE_EXPRESS (cadastre) est allumée → la parcelle est identifiable
    expect(u.search).toContain('CADASTRALPARCELS.PARCELLAIRE_EXPRESS')
  })

  it('Google Maps : épingle l\'emplacement (query=lat,lon), pas une recherche texte', () => {
    const u = new URL(googleMapsUrl(COORDS))
    expect(u.host).toBe('www.google.com')
    expect(u.searchParams.get('api')).toBe('1')
    expect(u.searchParams.get('query')).toBe('-20.925,55.335') // lat,lon — ordre Google Maps
  })

  it('Cadastre et Maps ne confondent JAMAIS lat et lon', () => {
    // même centroïde, deux ordres : la latitude (négative à La Réunion) doit tomber au bon endroit.
    expect(cadastreGeoportailUrl(COORDS)).toContain('c=55.335,-20.925')
    expect(googleMapsUrl(COORDS)).toContain('query=-20.925,55.335')
  })

  it('Pages jaunes AVEC adresse : porte l\'adresse exacte + la commune', () => {
    const { url, commune_seule } = pagesJaunes('14 rue Françoise-Dolto', 'La Possession')
    expect(commune_seule).toBe(false)
    const u = new URL(url!)
    expect(u.host).toBe('www.pagesjaunes.fr')
    expect(u.searchParams.get('ou')).toBe('14 rue Françoise-Dolto La Possession')
  })

  it('Pages jaunes SANS adresse : commune seule + drapeau commune_seule', () => {
    const { url, commune_seule } = pagesJaunes(null, 'Saint-Joseph')
    expect(commune_seule).toBe(true)
    expect(new URL(url!).searchParams.get('ou')).toBe('Saint-Joseph')
  })

  it('Pages jaunes sans adresse NI commune : aucun lien (jamais un lien vide)', () => {
    expect(pagesJaunes(null, null).url).toBeNull()
    expect(pagesJaunes('', '  ').url).toBeNull()
  })
})
