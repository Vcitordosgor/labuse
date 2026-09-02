// RETOURS-10 (T4) — les trois liens d'accès de l'en-tête de fiche, construits ICI (fonctions pures)
// pour être VÉRIFIABLES par test : chacun doit mener à la bonne parcelle (coordonnées du centroïde) ou
// à la bonne adresse, jamais à la commune par défaut ni à une recherche texte qui tombe ailleurs.
//
// Convention de coordonnées : `coords` = [longitude, latitude] (ordre GeoJSON, comme le sert /parcels/{idu}).

export type Coords = [number, number] // [lon, lat]

// Cadastre Géoportail — CENTRÉ sur la parcelle : le Géoportail n'accepte pas l'IDU dans le permalien,
// on centre donc sur le centroïde (paramètre `c=lon,lat`) au zoom parcellaire (19) avec la couche
// CADASTRALPARCELS.PARCELLAIRE_EXPRESS allumée → la parcelle est identifiable, pas la commune.
export function cadastreGeoportailUrl(coords: Coords): string {
  const [lon, lat] = coords
  return `https://www.geoportail.gouv.fr/carte?c=${lon},${lat}&z=19` +
    '&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2::GEOPORTAIL:OGC:WMTS(1)' +
    '&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes'
}

// Google Maps — ÉPINGLE l'emplacement de la parcelle (query = lat,lon), jamais une recherche par texte.
export function googleMapsUrl(coords: Coords): string {
  const [lon, lat] = coords
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`
}

// Pages jaunes — l'adresse EXACTE (numéro + voie + commune) quand elle existe ; sinon la commune seule,
// et l'appelant l'annonce (« Pages jaunes — commune »). `commune_seule` porte ce repli.
export function pagesJaunes(adresse: string | null | undefined, commune: string | null | undefined):
  { url: string | null; commune_seule: boolean } {
  const a = (adresse ?? '').trim()
  const c = (commune ?? '').trim()
  if (!a && !c) return { url: null, commune_seule: true } // ni adresse ni commune → pas de lien
  const ou = a ? `${a} ${c}`.trim() : c
  return {
    url: `https://www.pagesjaunes.fr/annuaire/chercherlespros?ou=${encodeURIComponent(ou)}`,
    commune_seule: !a,
  }
}
