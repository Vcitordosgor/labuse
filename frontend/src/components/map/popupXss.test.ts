// MAPLIBRE-1 Lot A — preuve que les bulles de carte n'exécutent plus aucune donnée en HTML.
// Un nom d'ICPE / de servitude contenant un vecteur XSS doit s'afficher TEL QUEL (texte), sans créer
// de nœud <img>/<script> ni d'attribut onerror. Verrou : empêche toute régression vers setHTML.
import { describe, it, expect } from 'vitest'
import { popupNode, popupDetailNode, type TuyauCouche } from './CouchesTuyau'

const XSS = '<img src=x onerror=alert(1)>'

const coucheICPE = {
  kind: 'icpe', nom: 'Installations classées (ICPE)', famille: 'risques', geometrie: 'point',
  zoom_min: 0, rang_carte: 1, style: {}, niveaux: null, legende: '', statut_juridique: null,
  tuiles_url: '', popup: [{ champ: 'raison_sociale', libelle: 'Exploitant' }, { champ: 'url', libelle: 'Fiche', lien: true }],
} as unknown as TuyauCouche

describe('bulles carte — texte pur (anti-XSS)', () => {
  it('popupNode : un nom malveillant s\'affiche en texte, aucun <img>/<script> créé', () => {
    const el = popupNode(coucheICPE, { raison_sociale: XSS, url: 'javascript:alert(1)' })
    expect(el.querySelector('img')).toBeNull()
    expect(el.querySelector('script')).toBeNull()
    expect(el.textContent).toContain(XSS)            // la chaîne brute est visible telle quelle
    expect(el.innerHTML).toContain('&lt;img')        // sérialisée ÉCHAPPÉE = texte inerte
    expect(el.innerHTML).not.toContain('<img ')      // jamais une vraie balise <img>
  })

  it('popupNode : une URL non http(s) ne devient jamais un href (retombe en texte)', () => {
    const el = popupNode(coucheICPE, { raison_sociale: 'ACME', url: 'javascript:alert(1)' })
    expect(el.querySelector('a')).toBeNull()         // pas de lien exécutable
  })

  it('popupNode : une URL http(s) reste un lien « ouvrir » normal', () => {
    const el = popupNode(coucheICPE, { raison_sociale: 'ACME', url: 'https://georisques.gouv.fr/x' })
    const a = el.querySelector('a')
    expect(a?.getAttribute('href')).toBe('https://georisques.gouv.fr/x')
    expect(a?.textContent).toBe('ouvrir')
  })

  it('popupDetailNode : servitude malveillante affichée en texte, aucun nœud injecté', () => {
    const couche = { ...coucheICPE, nom: 'SUP', popup_detail: [{ champ: 'intitule', libelle: 'Servitude' }] } as unknown as TuyauCouche
    const el = popupDetailNode(couche, [{ intitule: XSS }])
    expect(el.querySelector('img')).toBeNull()
    expect(el.textContent).toContain(XSS)
  })
})
