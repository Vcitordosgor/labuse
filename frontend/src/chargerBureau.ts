import { estAppareilMobile } from './lib/appareil'

// Commencer le téléchargement du bureau pendant le chargement du point d’entrée.
export const bureau = estAppareilMobile() ? null : import('./App')
