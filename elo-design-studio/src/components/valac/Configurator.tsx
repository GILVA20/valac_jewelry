import React, { useEffect, useMemo, useState } from "react";

type Selections = {
  forWhom: string;
  diamond: string;
  cut: string;
  metal: string;
  style: string;
  setting: string;
  size: number;
};

const FOR_WHOM = [
  {
    id: "Para ella",
    label: "Para ella",
    sub: "Un anillo que la haga brillar",
    icon: (
      <svg viewBox="0 0 64 64" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.4">
        <ellipse cx="32" cy="44" rx="14" ry="10" />
        <path d="M22 36 L26 22 L38 22 L42 36" />
        <path d="M28 22 L32 14 L36 22" />
        <circle cx="32" cy="18" r="1.6" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: "Para él",
    label: "Para él",
    sub: "Fuerza y elegancia en cada detalle",
    icon: (
      <svg viewBox="0 0 64 64" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.4">
        <ellipse cx="32" cy="38" rx="16" ry="12" />
        <path d="M16 38 Q32 50 48 38" />
      </svg>
    ),
  },
  {
    id: "Para los dos",
    label: "Para los dos",
    sub: "Dos anillos, una sola historia",
    icon: (
      <svg viewBox="0 0 64 64" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.4">
        <circle cx="24" cy="36" r="14" />
        <circle cx="40" cy="36" r="14" />
      </svg>
    ),
  },
];

const DIAMONDS = [
  {
    id: "Natural",
    title: "Diamante Natural",
    sub: "Formado en la tierra durante millones de años",
    detail: "Certificado GIA · Máxima exclusividad",
  },
  {
    id: "Lab-Grown",
    title: "Diamante Lab-Grown",
    sub: "Idéntico en brillo y dureza, creado con tecnología",
    detail: "Certificado IGI · Hasta 60% más accesible",
  },
];

const CUTS = ["Redondo", "Princesa", "Ovalado", "Esmeralda", "Pera", "Cushion"];

const METALS = [
  { name: "Amarillo 10k", color: "#FFD700" },
  { name: "Amarillo 14k", color: "#DAA520" },
  { name: "Blanco 14k", color: "#E8E8E8" },
  { name: "Rosé 14k", color: "#E8B4B8" },
];

const STYLES = ["Solitario", "Halo", "Pavé", "Tres Piedras"];

const SETTINGS = [
  { name: "4 Dientes", desc: "Clásico, elegante" },
  { name: "6 Dientes", desc: "Máxima seguridad" },
  { name: "3 Dientes", desc: "Moderno, arriesgado" },
  { name: "Bisel", desc: "Moderno, protegido" },
  { name: "Especial", desc: "Cuéntanos tu visión" },
];

const SIZE_MM: Record<string, string> = {
  "4": "14.94", "4.5": "15.34", "5": "15.75", "5.5": "16.15",
  "6": "16.56", "6.5": "16.97", "7": "17.37", "7.5": "17.78",
  "8": "18.19", "8.5": "18.59", "9": "19.00", "9.5": "19.41",
  "10": "19.81", "10.5": "20.22", "11": "20.62", "11.5": "21.03",
  "12": "21.44",
};

// Price ranges per metal (rough MXN)
const METAL_BASE: Record<string, [number, number]> = {
  "Amarillo 10k": [6500, 18000],
  "Amarillo 14k": [9000, 26000],
  "Blanco 14k": [9500, 28000],
  "Rosé 14k": [9500, 27000],
};
const STYLE_MULT: Record<string, number> = {
  "Solitario": 1.0, "Halo": 1.35, "Pavé": 1.5, "Tres Piedras": 1.6,
};
const DIAMOND_MULT: Record<string, number> = { "Natural": 1.4, "Lab-Grown": 1.0 };

function CutIcon({ name, active }: { name: string; active: boolean }) {
  const c = active ? "var(--gold)" : "var(--gold)";
  const fill = active ? "rgba(213,163,0,0.12)" : "none";
  const sw = 1.4;
  switch (name) {
    case "Redondo":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><circle cx="20" cy="20" r="14" stroke={c} strokeWidth={sw} fill={fill}/><circle cx="20" cy="20" r="7" stroke={c} strokeWidth={sw} fill="none"/></svg>;
    case "Princesa":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><rect x="6" y="6" width="28" height="28" stroke={c} strokeWidth={sw} fill={fill}/><path d="M6 6l28 28M34 6L6 34" stroke={c} strokeWidth={sw}/></svg>;
    case "Ovalado":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><ellipse cx="20" cy="20" rx="10" ry="14" stroke={c} strokeWidth={sw} fill={fill}/></svg>;
    case "Esmeralda":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><path d="M12 6h16l4 4v20l-4 4H12l-4-4V10z" stroke={c} strokeWidth={sw} fill={fill}/></svg>;
    case "Pera":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><path d="M20 5c-6 6-9 11-9 18s4 11 9 11 9-4 9-11-3-12-9-18z" stroke={c} strokeWidth={sw} fill={fill}/></svg>;
    case "Cushion":
      return <svg viewBox="0 0 40 40" className="w-10 h-10"><path d="M12 6h16a6 6 0 016 6v16a6 6 0 01-6 6H12a6 6 0 01-6-6V12a6 6 0 016-6z" stroke={c} strokeWidth={sw} fill={fill}/></svg>;
    default:
      return null;
  }
}

function StyleIllu({ name }: { name: string }) {
  const c = "var(--gold)";
  const sw = 1.5;
  switch (name) {
    case "Solitario":
      return <svg viewBox="0 0 70 50" className="w-16 h-12"><path d="M8 38 Q35 48 62 38" stroke={c} strokeWidth={sw} fill="none"/><path d="M8 38 Q35 30 62 38" stroke={c} strokeWidth={sw} fill="none"/><circle cx="35" cy="20" r="6" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.15)"/><path d="M30 20 L35 26 L40 20 L35 14 Z" stroke={c} strokeWidth={sw} fill="none"/></svg>;
    case "Halo":
      return <svg viewBox="0 0 70 50" className="w-16 h-12"><path d="M8 38 Q35 48 62 38" stroke={c} strokeWidth={sw} fill="none"/><path d="M8 38 Q35 30 62 38" stroke={c} strokeWidth={sw} fill="none"/><circle cx="35" cy="20" r="4.5" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.2)"/><circle cx="35" cy="20" r="9" stroke={c} strokeWidth={sw} fill="none"/></svg>;
    case "Pavé":
      return <svg viewBox="0 0 70 50" className="w-16 h-12"><path d="M8 38 Q35 48 62 38" stroke={c} strokeWidth={sw} fill="none"/><path d="M8 38 Q35 30 62 38" stroke={c} strokeWidth={sw} fill="none"/><circle cx="35" cy="20" r="6" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.15)"/>{[14, 20, 26, 44, 50, 56].map((x) => <circle key={x} cx={x} cy="36" r="1.5" fill={c}/>)}</svg>;
    case "Tres Piedras":
      return <svg viewBox="0 0 70 50" className="w-16 h-12"><path d="M8 38 Q35 48 62 38" stroke={c} strokeWidth={sw} fill="none"/><path d="M8 38 Q35 30 62 38" stroke={c} strokeWidth={sw} fill="none"/><circle cx="35" cy="20" r="6" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.2)"/><circle cx="22" cy="24" r="3.5" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.1)"/><circle cx="48" cy="24" r="3.5" stroke={c} strokeWidth={sw} fill="rgba(213,163,0,0.1)"/></svg>;
    default:
      return null;
  }
}

const STEP_ICONS: Record<number, React.ReactElement> = {
  1: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2 L13.5 10 L22 12 L13.5 14 L12 22 L10.5 14 L2 12 L10.5 10 Z"/></svg>,
  2: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="6" y="6" width="12" height="12" transform="rotate(45 12 12)"/></svg>,
  3: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="8"/></svg>,
  4: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="9"/></svg>,
  5: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="10" r="3"/><path d="M6 18 Q12 14 18 18"/></svg>,
  6: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 12 L20 12 M9 8 L9 16 M15 8 L15 16"/></svg>,
  7: <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="6"/><path d="M12 4v3M12 17v3M4 12h3M17 12h3"/></svg>,
};

interface Props {
  onSelectionsChange: (s: Selections, count: number, ready: boolean) => void;
  onRequestQuote: () => void;
}

const TOTAL_STEPS = 7;

export function Configurator({ onSelectionsChange, onRequestQuote }: Props) {
  const [step, setStep] = useState(1);
  const [showDiff, setShowDiff] = useState(false);
  const [sel, setSel] = useState<Selections>({
    forWhom: "", diamond: "", cut: "", metal: "", style: "", setting: "", size: 6,
  });

  const completedFlags = [
    !!sel.forWhom, !!sel.diamond, !!sel.cut, !!sel.metal, !!sel.style, !!sel.setting, true,
  ];
  const completedCount = completedFlags.filter(Boolean).length - 1; // exclude size auto
  const allDone = completedFlags.every(Boolean);

  useEffect(() => {
    onSelectionsChange(sel, completedCount, allDone);
  }, [sel, completedCount, allDone, onSelectionsChange]);

  const update = <K extends keyof Selections>(k: K, v: Selections[K]) => {
    setSel((s) => ({ ...s, [k]: v }));
    // auto-advance after small delay
    if (k !== "size" && step < TOTAL_STEPS) {
      setTimeout(() => setStep((cur) => Math.min(TOTAL_STEPS, cur + 1)), 320);
    }
  };

  const goTo = (n: number) => {
    if (n < 1 || n > TOTAL_STEPS) return;
    // can navigate to any prior or next-already-reached step
    const reachable = n <= step || completedFlags[n - 2];
    if (reachable) setStep(n);
  };

  const priceRange = useMemo<[number, number] | null>(() => {
    if (!sel.metal) return null;
    const [lo, hi] = METAL_BASE[sel.metal] ?? [8000, 24000];
    const sm = STYLE_MULT[sel.style] ?? 1;
    const dm = DIAMOND_MULT[sel.diamond] ?? 1.1;
    return [Math.round(lo * sm * dm / 100) * 100, Math.round(hi * sm * dm / 100) * 100];
  }, [sel.metal, sel.style, sel.diamond]);

  const sliderPct = ((sel.size - 4) / 8) * 100;

  return (
    <div className="bg-white rounded-2xl border border-[var(--gold-soft)] shadow-[0_4px_16px_rgba(31,41,55,0.06)] overflow-hidden">
      {/* PROGRESS BAR */}
      <div className="px-6 sm:px-10 pt-6 pb-4 border-b border-[var(--hairline)]/60 bg-gradient-to-b from-[var(--ivory)]/40 to-white">
        <div className="flex items-center justify-between gap-1 sm:gap-2">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => {
            const n = i + 1;
            const done = n < step || (n <= step && completedFlags[n - 1]);
            const current = n === step;
            const reachable = n <= step || completedFlags[n - 2];
            return (
              <div key={n} className="flex items-center flex-1 last:flex-none">
                <button
                  type="button"
                  onClick={() => goTo(n)}
                  disabled={!reachable}
                  aria-label={`Ir al paso ${n}`}
                  className={`relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 transition-all ${
                    done
                      ? "bg-[var(--gold)] border-[var(--gold)] text-white"
                      : current
                        ? "bg-white border-[var(--gold)] text-[var(--gold)] ring-4 ring-[var(--gold)]/15"
                        : "bg-white border-[var(--disabled)] text-[var(--disabled)]"
                  } ${reachable ? "cursor-pointer" : "cursor-not-allowed"}`}
                >
                  <span className="hidden sm:block">{STEP_ICONS[n]}</span>
                  <span className="sm:hidden text-[11px] font-semibold">{n}</span>
                </button>
                {n < TOTAL_STEPS && (
                  <div className={`flex-1 h-[2px] mx-1 sm:mx-1.5 transition-colors ${
                    done ? "bg-[var(--gold)]" : "bg-[var(--hairline)]"
                  }`} />
                )}
              </div>
            );
          })}
        </div>
        <div className="mt-3 text-center text-xs text-[var(--mute)] tracking-wide">
          Paso {step} de {TOTAL_STEPS}
        </div>
      </div>

      {/* STEP CONTENT */}
      <div className="px-6 sm:px-10 py-8 sm:py-10 min-h-[420px]">
        <div key={step} className="step-enter">
          {step === 1 && (
            <StepShell title="¿Para quién es el anillo?" sub="El primer detalle que define toda la pieza">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {FOR_WHOM.map((o) => {
                  const active = sel.forWhom === o.id;
                  return (
                    <button
                      key={o.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("forWhom", o.id)}
                      className={`card-soft ${active ? "is-active" : ""} p-6 text-center flex flex-col items-center`}
                    >
                      <div className={`mb-3 ${active ? "text-[var(--gold)]" : "text-[var(--ink)]/70"}`}>
                        {o.icon}
                      </div>
                      <div className="font-display text-lg text-[var(--ink)] font-semibold">{o.label}</div>
                      <div className="font-accent italic text-sm text-[var(--mute)] mt-1.5 leading-snug">
                        {o.sub}
                      </div>
                    </button>
                  );
                })}
              </div>
            </StepShell>
          )}

          {step === 2 && (
            <StepShell title="¿Diamante natural o lab-grown?" sub="Dos caminos, la misma belleza eterna">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {DIAMONDS.map((d) => {
                  const active = sel.diamond === d.id;
                  return (
                    <button
                      key={d.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("diamond", d.id)}
                      className={`card-soft ${active ? "is-active" : ""} p-6 text-left relative overflow-hidden`}
                    >
                      <div className="absolute -right-6 -top-6 w-28 h-28 rounded-full opacity-20"
                        style={{
                          background: d.id === "Natural"
                            ? "radial-gradient(circle, rgba(213,163,0,0.6), transparent 70%)"
                            : "radial-gradient(circle, rgba(124,160,255,0.5), transparent 70%)",
                        }}
                      />
                      <div className="relative">
                        <div className="font-display text-xl text-[var(--ink)] font-semibold">{d.title}</div>
                        <div className="font-accent italic text-base text-[var(--mute)] mt-1.5">
                          {d.sub}
                        </div>
                        <div className="text-xs uppercase tracking-wider text-[var(--gold)] font-semibold mt-4">
                          {d.detail}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
              <div className="mt-5 text-center">
                <button
                  type="button"
                  onClick={() => setShowDiff(!showDiff)}
                  className="text-sm text-[var(--gold)] font-semibold hover:text-[var(--gold-hover)] transition-colors"
                >
                  ¿Cuál es la diferencia? {showDiff ? "↑" : "↓"}
                </button>
                {showDiff && (
                  <div className="mt-4 bg-[var(--ivory)] border border-[var(--gold-soft)] rounded-xl p-5 text-left">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-[var(--mute)] text-xs uppercase tracking-wider">
                          <th className="text-left pb-2">Característica</th>
                          <th className="text-left pb-2">Natural</th>
                          <th className="text-left pb-2">Lab-Grown</th>
                        </tr>
                      </thead>
                      <tbody className="text-[var(--ink)]">
                        <tr className="border-t border-[var(--gold-soft)]/60"><td className="py-2">Origen</td><td>Tierra</td><td>Laboratorio</td></tr>
                        <tr className="border-t border-[var(--gold-soft)]/60"><td className="py-2">Brillo</td><td>Idéntico</td><td>Idéntico</td></tr>
                        <tr className="border-t border-[var(--gold-soft)]/60"><td className="py-2">Dureza</td><td>10/10</td><td>10/10</td></tr>
                        <tr className="border-t border-[var(--gold-soft)]/60"><td className="py-2">Precio</td><td>Mayor</td><td>Hasta 60% menos</td></tr>
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </StepShell>
          )}

          {step === 3 && (
            <StepShell title="¿Qué forma de piedra te inspira?" sub="Cada corte cuenta una historia distinta">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
                {CUTS.map((c) => {
                  const active = sel.cut === c;
                  return (
                    <button
                      key={c}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("cut", c)}
                      className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center justify-center py-5 px-3`}
                    >
                      <CutIcon name={c} active={active} />
                      <span className="mt-2.5 text-sm font-medium text-[var(--ink)]">{c}</span>
                    </button>
                  );
                })}
              </div>
            </StepShell>
          )}

          {step === 4 && (
            <StepShell title="¿Qué tipo de oro prefieres?" sub="El metal que abrazará la piedra elegida">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                {METALS.map((m) => {
                  const active = sel.metal === m.name;
                  return (
                    <button
                      key={m.name}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("metal", m.name)}
                      className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-5 px-2`}
                    >
                      <span
                        className="w-14 h-14 rounded-full"
                        style={{
                          background: `radial-gradient(circle at 35% 30%, #fff5, transparent 50%), ${m.color}`,
                          boxShadow: active
                            ? "0 0 0 3px #fff, 0 0 0 5px var(--gold), 0 4px 14px rgba(213,163,0,0.3)"
                            : "inset 0 0 0 1px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.08)",
                        }}
                      />
                      <span className={`mt-3 text-sm text-center leading-tight ${active ? "font-semibold text-[var(--ink)]" : "font-medium text-[var(--ink)]"}`}>
                        {m.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </StepShell>
          )}

          {step === 5 && (
            <StepShell title="¿Qué estilo de anillo?" sub="La silueta que la acompañará para siempre">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                {STYLES.map((s) => {
                  const active = sel.style === s;
                  return (
                    <button
                      key={s}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("style", s)}
                      className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-5 px-2`}
                    >
                      <StyleIllu name={s} />
                      <span className="mt-2 font-display text-base text-[var(--ink)]">{s}</span>
                    </button>
                  );
                })}
              </div>
            </StepShell>
          )}

          {step === 6 && (
            <StepShell title="¿Cómo engarzar la piedra?" sub="El abrazo de oro que la sostiene">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                {SETTINGS.map((s) => {
                  const active = sel.setting === s.name;
                  return (
                    <button
                      key={s.name}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("setting", s.name)}
                      className={`card-soft ${active ? "is-active" : ""} text-left p-4`}
                    >
                      <div className="font-display text-base text-[var(--ink)] font-semibold flex items-center gap-2">
                        {s.name === "Especial" && <span className="text-[var(--gold)]">✦</span>}
                        {s.name}
                      </div>
                      <div className="font-accent italic text-sm text-[var(--mute)] mt-1">{s.desc}</div>
                    </button>
                  );
                })}
              </div>
            </StepShell>
          )}

          {step === 7 && (
            <StepShell title="¿Cuál es tu talla?" sub="El último detalle, el más íntimo">
              <div className="text-center">
                <div className="font-display text-5xl sm:text-6xl text-[var(--gold)] font-semibold mb-2">
                  {sel.size}
                </div>
                <div className="text-sm text-[var(--mute)] mb-6">
                  Diámetro interno {SIZE_MM[sel.size.toString()]} mm
                </div>
                <input
                  type="range"
                  min={4}
                  max={12}
                  step={0.5}
                  value={sel.size}
                  onChange={(e) => update("size", parseFloat(e.target.value))}
                  aria-label="Talla del anillo"
                  className="valac-slider"
                  style={{ ["--val" as string]: `${sliderPct}%` }}
                />
                <div className="flex justify-between text-xs text-[var(--mute)] mt-2 px-1">
                  <span>4</span><span>8</span><span>12</span>
                </div>
                <a
                  href="https://wa.me/5213320471076?text=Hola,%20necesito%20ayuda%20para%20saber%20mi%20talla%20de%20anillo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-6 text-sm text-[var(--gold)] font-semibold hover:text-[var(--gold-hover)] underline underline-offset-4"
                >
                  ¿No sabes tu talla? Te ayudamos →
                </a>
              </div>
            </StepShell>
          )}
        </div>

        {/* NAV */}
        <div className="mt-8 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => goTo(step - 1)}
            disabled={step === 1}
            className="text-sm font-semibold text-[var(--mute)] hover:text-[var(--ink)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ← Anterior
          </button>
          {step < TOTAL_STEPS ? (
            <button
              type="button"
              onClick={() => goTo(step + 1)}
              disabled={!completedFlags[step - 1]}
              className="text-sm font-semibold text-[var(--gold)] hover:text-[var(--gold-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente →
            </button>
          ) : (
            <span className="text-sm font-semibold text-[var(--success)]">✓ Diseño completo</span>
          )}
        </div>
      </div>

      {/* SUMMARY (after step 7) */}
      {step === TOTAL_STEPS && (
        <div className="px-6 sm:px-10 pb-2">
          <div className="bg-[var(--bg-page)] border border-[var(--gold-soft)] rounded-2xl p-5">
            <div className="text-xs uppercase tracking-widest text-[var(--gold)] font-semibold mb-3">
              Tu diseño VALAC
            </div>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-4 text-sm">
              <SummaryRow label="Para" value={sel.forWhom} onEdit={() => goTo(1)} />
              <SummaryRow label="Diamante" value={sel.diamond} onEdit={() => goTo(2)} />
              <SummaryRow label="Corte" value={sel.cut} onEdit={() => goTo(3)} />
              <SummaryRow label="Metal" value={sel.metal} onEdit={() => goTo(4)} />
              <SummaryRow label="Estilo" value={sel.style} onEdit={() => goTo(5)} />
              <SummaryRow label="Montura" value={sel.setting} onEdit={() => goTo(6)} />
              <SummaryRow label="Talla" value={String(sel.size)} onEdit={() => goTo(7)} />
            </ul>
          </div>
        </div>
      )}

      {/* PRICE RANGE FOOTER */}
      <div
        className="px-6 sm:px-10 py-5 mt-2 border-t"
        style={{ background: "var(--ivory)", borderTopColor: "var(--gold-soft)" }}
      >
        {priceRange ? (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[var(--mute)] font-semibold">
                Rango estimado
              </div>
              <div className="font-semibold text-lg text-[var(--ink)]">
                ${priceRange[0].toLocaleString("es-MX")} — ${priceRange[1].toLocaleString("es-MX")} <span className="text-sm text-[var(--mute)] font-normal">MXN</span>
              </div>
            </div>
            <span className="text-xs text-[var(--mute)] italic font-accent">
              Precio final personalizado en cotización
            </span>
          </div>
        ) : (
          <div className="text-sm text-[var(--mute)] text-center">
            Completa más opciones para ver el rango estimado
          </div>
        )}

        <button
          type="button"
          onClick={onRequestQuote}
          disabled={!allDone}
          className={`btn-cta mt-4 w-full h-14 ${allDone ? "pulse-ready" : ""}`}
        >
          Solicitar Mi Cotización
        </button>
        <p className="mt-2 text-center text-xs text-[var(--mute)]">
          Respondemos en menos de 24 horas
        </p>
      </div>
    </div>
  );
}

function StepShell({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-center mb-7">
        <h2 className="font-display text-2xl sm:text-3xl text-[var(--ink)] font-semibold leading-snug">
          {title}
        </h2>
        <p className="font-accent italic text-base sm:text-lg text-[var(--mute)] mt-1.5">
          {sub}
        </p>
      </div>
      {children}
    </div>
  );
}

function SummaryRow({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) {
  return (
    <li className="flex items-center justify-between gap-2 border-b border-[var(--gold-soft)]/40 pb-1.5">
      <span>
        <span className="text-[var(--mute)]">{label}:</span>{" "}
        <span className="font-semibold text-[var(--ink)]">{value || "—"}</span>
      </span>
      <button
        type="button"
        onClick={onEdit}
        className="text-xs text-[var(--gold)] hover:text-[var(--gold-hover)] font-semibold"
        aria-label={`Editar ${label}`}
      >
        Editar
      </button>
    </li>
  );
}

export type { Selections };
