import { useCallback, useLayoutEffect, useRef, useState } from 'react'

/**
 * L'ouverture de LABUSE — l'oiseau arrive, se pose, « LABUSE » s'écrit, puis il
 * redécolle et va se ranger sur le logo du rail pendant que l'app apparaît.
 *
 * Reprise de l'intro de la vidéo du site (docs/refonte/video/logo.html dans le dépôt
 * labuse.immo). Mêmes durées, mêmes amortissements, même battement d'ailes.
 *
 * Trois règles :
 *  — une fois par session, pas à chaque navigation ;
 *  — « animations réduites » dans le système → on passe directement à l'app ;
 *  — un clic ou une touche écourte l'animation.
 *
 * L'arrivée est MESURÉE sur l'élément qui porte `data-logo-cible` (l'oiseau du rail).
 * Sans lui, on retombe sur un coin haut-gauche plausible — mais posez l'attribut.
 */

// Les 19 points du tracé de l'oiseau. On les PLIE autour de l'axe du corps (x = 120) :
// l'angle croît avec l'éloignement du centre, donc le centre ne bouge jamais et l'aile se
// courbe comme une vraie aile. L'ancienne version faisait pivoter deux moitiés découpées,
// et au plus fort du battement un coin sombre s'ouvrait au milieu.
const PTS: [number, number][] = [[2,15],[58,10],[100,18],[120,27],[140,18],[182,10],[238,15],[202,29],[162,40],[135,46],[127,49],[122,53],[120,60],[118,53],[113,49],[105,46],[78,40],[38,29],[2,15]];
const AXE = 120, PIVOT = 30, DEMI = 118, COURBE = 1.6;

function plie(deg: number): string {
  const P = PTS.map(([x, y]) => {
    const u = (x - AXE) / DEMI
    const phi = (deg * Math.PI) / 180 * Math.pow(Math.abs(u), COURBE) * (u < 0 ? -1 : 1)
    const dx = x - AXE, dy = y - PIVOT, c = Math.cos(phi), s = Math.sin(phi)
    return [AXE + dx * c - dy * s, PIVOT + dx * s + dy * c] as [number, number]
  })
  const f = (i: number) => P[i]![0].toFixed(2) + ' ' + P[i]![1].toFixed(2)
  return `M${f(0)} C${f(1)} ${f(2)} ${f(3)} C${f(4)} ${f(5)} ${f(6)} C${f(7)} ${f(8)} ${f(9)} C${f(10)} ${f(11)} ${f(12)} C${f(13)} ${f(14)} ${f(15)} C${f(16)} ${f(17)} ${f(18)} Z`
}

/** Repères de la timeline, en secondes. Ne pas y toucher sans revoir la vidéo du site. */
const ARRIVEE = 1.3   // vol d'arrivée
const POSE = 1.7      // le battement s'amortit jusqu'ici
const DECOLLAGE = 2.2 // il repart vers le rail
const VOL = 0.6       // durée de ce dernier vol
const FIN = DECOLLAGE + VOL + 0.1

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x))
const smooth = (x: number) => { const c = clamp(x, 0, 1); return c * c * (3 - 2 * c) }

export function LogoIntro({ onFini }: { onFini?: () => void }) {
  const oiseau = useRef<SVGSVGElement>(null)
  const aile = useRef<SVGPathElement>(null)
  const mot = useRef<HTMLDivElement>(null)
  const voile = useRef<HTMLDivElement>(null)
  const [parti, setParti] = useState(false)
  // onFini gardé dans une ref : si l'app re-rend pendant l'animation (chargement des
  // données), une nouvelle fonction ne doit PAS relancer l'effet — sinon l'oiseau repart de zéro.
  const rappel = useRef(onFini)
  rappel.current = onFini

  // CORRECTIF (premières images) — useLayoutEffect : la toute première image peinte doit DÉJÀ porter
  // la bonne transformation (pas l'oiseau en haut à gauche, taille réelle, l'espace d'une frame).
  useLayoutEffect(() => {
    let brut = 0
    let termine = false
    const fini = () => {
      if (termine) return
      termine = true
      cancelAnimationFrame(brut)
      setParti(true)
      rappel.current?.()
    }

    // Système réglé sur « animations réduites » : on n'impose rien.
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { fini(); return }

    const W = window.innerWidth
    const H = window.innerHeight

    // Où l'oiseau va se ranger : le logo du rail, mesuré à l'écran.
    const cible = document.querySelector<HTMLElement>('[data-logo-cible]')
    const r = cible?.getBoundingClientRect()
    const FIN_X = r ? r.left + r.width / 2 : 35
    const FIN_Y = r ? r.top + r.height / 2 : 28
    const FIN_L = r && r.width > 8 ? r.width : 40

    // Tailles relatives à la fenêtre, reprises des proportions de la vidéo.
    const AU_REPOS = clamp(W * 0.18, 190, 520)
    const DEPART = AU_REPOS * 0.58
    const POSE_Y = H * 0.42

    const debut = performance.now()

    const dessine = (t: number) => {
      let cx: number, cy: number, l: number, amp: number
      if (t < ARRIVEE) {
        const u = ease(t / ARRIVEE)
        cx = lerp(-AU_REPOS, W / 2, u)
        cy = lerp(H * 0.69, POSE_Y, u) - Math.sin(u * Math.PI) * H * 0.067
        l = lerp(DEPART, AU_REPOS, u)
        amp = 34
      } else if (t < DECOLLAGE) {
        // Il se pose : le bob et le battement s'éteignent ensemble.
        const d = 1 - smooth((t - ARRIVEE) / (POSE - ARRIVEE))
        cx = W / 2
        cy = POSE_Y + Math.sin((t - ARRIVEE) * 4) * (H * 0.0056) * d
        l = AU_REPOS
        amp = 34 * d
      } else {
        const v = clamp((t - DECOLLAGE) / VOL, 0, 1)
        const u = ease(v)
        cx = lerp(W / 2, FIN_X, u)
        cy = lerp(POSE_Y, FIN_Y, u)
        l = lerp(AU_REPOS, FIN_L, u)
        amp = 26 * Math.sin(Math.PI * v) // un seul coup d'aile, pour repartir
      }

      const a = amp * Math.sin(2 * Math.PI * (t < ARRIVEE ? 3.4 : 2.6) * t)
      const s = l / 240
      if (oiseau.current) {
        oiseau.current.style.transform = `translate(${cx - 120}px, ${cy - 30}px) scale(${s})`
      }
      aile.current?.setAttribute('d', plie(a))

      // « LABUSE » s'écrit une fois l'oiseau posé, et s'efface quand il repart.
      const o = t < 1.45 ? 0
        : t < 1.85 ? (t - 1.45) / 0.4
        : t < DECOLLAGE ? 1
        : Math.max(0, 1 - (t - DECOLLAGE) / 0.25)
      if (mot.current) mot.current.style.opacity = String(o)

      // Le voile s'ouvre sur l'app pendant le dernier vol.
      if (voile.current) voile.current.style.opacity = String(clamp(1 - (t - 2.5) / 0.35, 0, 1))
    }

    const image = (maintenant: number) => {
      const t = Math.max(0, (maintenant - debut) / 1000)   // CORRECTIF : jamais de t négatif (frame 0)
      if (t >= FIN) { fini(); return }
      dessine(t)
      brut = requestAnimationFrame(image)
    }
    dessine(0)   // CORRECTIF : peint la position de départ AVANT la première frame (plus de saut)
    brut = requestAnimationFrame(image)

    const ecourter = () => fini()
    window.addEventListener('pointerdown', ecourter)
    window.addEventListener('keydown', ecourter)
    return () => {
      cancelAnimationFrame(brut)
      window.removeEventListener('pointerdown', ecourter)
      window.removeEventListener('keydown', ecourter)
    }
  }, [])

  if (parti) return null

  return (
    <div
      ref={voile}
      role="presentation"
      style={{
        position: 'fixed', inset: 0, zIndex: 9999, background: '#0A0C0B',
        overflow: 'hidden', pointerEvents: 'none',
      }}
    >
      <svg
        ref={oiseau}
        viewBox="0 0 240 82"
        width={240}
        height={82}
        overflow="visible"
        aria-hidden
        // CORRECTIF : hors écran tant que la 1re transformation n'est pas appliquée (ceinture + bretelles).
        style={{ position: 'absolute', left: 0, top: 0, transformOrigin: '120px 30px', transform: 'translate(-9999px, 0)' }}
      >
        <path ref={aile} fill="#4ADE80" d={plie(0)} />
      </svg>

      <div
        ref={mot}
        aria-hidden
        style={{
          position: 'absolute', left: 0, right: 0, top: '56.7%', textAlign: 'center', opacity: 0,
          font: `700 clamp(34px, 5.2vw, 150px)/1 'Space Grotesk', ui-sans-serif, system-ui, sans-serif`,
          letterSpacing: '.04em', color: '#E8EFEA',
        }}
      >
        LA<span style={{ color: '#4ADE80' }}>BUSE</span>
      </div>
    </div>
  )
}

/** Une seule ouverture par session : au rechargement d'une page, pas à chaque navigation. */
export function useOuvertureUneFois(): [boolean, () => void] {
  const [montre, setMontre] = useState(() => {
    try { return sessionStorage.getItem('labuse.intro') !== 'vue' } catch { return true }
  })
  const fini = useCallback(() => {
    try { sessionStorage.setItem('labuse.intro', 'vue') } catch { /* navigation privée */ }
    setMontre(false)
  }, [])
  return [montre, fini]
}
