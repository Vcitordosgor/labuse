// M26-B — socle des tests front (Vitest + Testing Library).
// CI-1 : fuseau FORCÉ à « heure Réunion » (comme toute l'app) AVANT tout rendu, pour que les
// snapshots qui affichent un horodatage (ex. Journal du Circuit) soient DÉTERMINISTES — identiques
// sur le Mac (local) et sur le runner Linux/UTC (CI). Sans ça : « 06/09 09:15 » local ≠ CI.
process.env.TZ = 'Indian/Reunion'
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)
