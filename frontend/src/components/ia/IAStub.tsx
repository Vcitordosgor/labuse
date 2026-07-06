export function IAStub() {
  return (
    <div className="flex min-w-0 flex-1 items-center justify-center">
      <div className="max-w-sm px-8 text-center">
        <svg viewBox="0 0 20 20" className="mx-auto h-10 w-10 text-txt-dim">
          <path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z"
            fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        </svg>
        <h2 className="mt-4 font-display text-base font-bold text-txt-hi">Assistant IA</h2>
        <p className="mt-2 text-xs leading-relaxed text-txt-mut">
          Poser une question en langage naturel — « trouve-moi 3 parcelles vue mer à Saint-Gilles
          avec un gérant proche de la retraite » — arrive en V1.x.
        </p>
        <p className="mt-3 text-[11px] leading-relaxed text-txt-dim">
          Le scoring, lui, reste 100 % déterministe et tracé : l'IA racontera, elle ne notera pas.
        </p>
      </div>
    </div>
  )
}
