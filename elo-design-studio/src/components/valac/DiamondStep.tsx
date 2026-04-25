import React, { useState, useEffect } from "react";
import {
  DIAMOND_SIZE_TIERS,
  CUT_TIERS,
  CLARITY_TIERS,
  COLOR_TIERS,
  isYellowGold,
  type SizeTier,
  type CutTier,
  type ClarityTier,
  type ColorTier,
} from "./diamondData";

interface DiamondStepProps {
  diamondType: string; // "Natural" | "Lab-Grown"
  metal: string;
  diamondSize: string;
  diamondCut: string;
  diamondClarity: string;
  diamondColor: string;
  onUpdate: (field: string, value: string) => void;
}

/* ── Badge ── */
function Badge({ text, color }: { text: string; color: "oxblood" | "gold" }) {
  const cls =
    color === "oxblood"
      ? "bg-[#7A0019]/15 text-[#E8819A] border-[#7A0019]/30"
      : "bg-[#D5A300]/15 text-[#D5A300] border-[#D5A300]/30";
  return (
    <span className={`inline-flex items-center text-[10px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${cls}`}>
      {text}
    </span>
  );
}

/* ── Sub-step mini progress ── */
function MiniProgress({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i < current
              ? "w-8 bg-[var(--gold)]"
              : i === current
                ? "w-8 bg-[var(--gold)]/50"
                : "w-4 bg-[var(--hairline)]"
          }`}
        />
      ))}
    </div>
  );
}

/* ── Hand Silhouette SVG ── */
function HandWithDiamond({ scale }: { scale: number }) {
  return (
    <svg viewBox="0 0 120 160" className="w-20 h-28 mx-auto" fill="none">
      {/* Elegant hand silhouette */}
      <path
        d="M60 155 C40 150 25 130 25 110 L25 70 C25 60 30 55 35 55 C40 55 43 58 43 63 L43 85
           M43 63 L43 40 C43 35 46 32 50 32 C54 32 57 35 57 40 L57 75
           M57 40 L57 28 C57 23 60 20 64 20 C68 20 71 23 71 28 L71 75
           M71 28 L71 38 C71 33 74 30 78 30 C82 30 85 33 85 38 L85 80 C85 120 75 150 60 155Z"
        stroke="var(--mute)"
        strokeWidth="1.2"
        strokeLinejoin="round"
        opacity="0.4"
      />
      {/* Ring on finger */}
      <ellipse cx="64" cy="58" rx="10" ry="4" stroke="var(--gold)" strokeWidth="1.5" opacity="0.6" />
      {/* Diamond - scales with tier */}
      <g transform={`translate(64, 48) scale(${scale})`} className="transition-transform duration-500">
        <path
          d="M0 -10 L8 -3 L5 8 L-5 8 L-8 -3 Z"
          fill="var(--gold)"
          fillOpacity="0.2"
          stroke="var(--gold)"
          strokeWidth="1.2"
        />
        <path d="M-8 -3 L0 4 L8 -3" stroke="var(--gold)" strokeWidth="0.8" opacity="0.5" />
        <path d="M0 -10 L0 4" stroke="var(--gold)" strokeWidth="0.6" opacity="0.4" />
      </g>
    </svg>
  );
}

/* ── Sparkle Animation SVG ── */
function SparkleViz({ level }: { level: number }) {
  const sparkles = level === 1 ? 3 : level === 2 ? 6 : 10;
  return (
    <svg viewBox="0 0 80 80" className="w-16 h-16 mx-auto">
      {/* Central diamond */}
      <path
        d="M40 20 L50 35 L45 55 L35 55 L30 35 Z"
        fill="var(--gold)"
        fillOpacity="0.15"
        stroke="var(--gold)"
        strokeWidth="1"
      />
      {/* Sparkle points */}
      {Array.from({ length: sparkles }).map((_, i) => {
        const angle = (360 / sparkles) * i - 90;
        const rad = (angle * Math.PI) / 180;
        const r = 28 + (i % 2) * 6;
        const cx = 40 + Math.cos(rad) * r;
        const cy = 38 + Math.sin(rad) * r;
        const size = level >= 3 ? 2.5 : level >= 2 ? 2 : 1.5;
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={size}
            fill="var(--gold)"
            className="sparkle-dot"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        );
      })}
      {/* Rainbow flashes for Ideal */}
      {level >= 3 &&
        [0, 120, 240].map((angle, i) => {
          const rad = ((angle - 90) * Math.PI) / 180;
          const cx = 40 + Math.cos(rad) * 20;
          const cy = 38 + Math.sin(rad) * 20;
          const colors = ["#FF6B6B", "#4ECDC4", "#7C9CF5"];
          return (
            <circle
              key={`rainbow-${i}`}
              cx={cx}
              cy={cy}
              r={1.8}
              fill={colors[i]}
              className="sparkle-rainbow"
              style={{ animationDelay: `${i * 200 + 100}ms` }}
            />
          );
        })}
    </svg>
  );
}

/* ── Clarity Loupe SVG ── */
function ClarityViz({ level }: { level: number }) {
  // level 3 = most inclusions (SI), 2 = few (VS), 1 = none (VVS-IF)
  const inclusions = level === 3 ? 5 : level === 2 ? 2 : 0;
  return (
    <svg viewBox="0 0 80 80" className="w-16 h-16 mx-auto">
      {/* Loupe circle */}
      <circle cx="40" cy="38" r="24" fill="var(--gold)" fillOpacity="0.05" stroke="var(--gold)" strokeWidth="1" />
      <circle cx="40" cy="38" r="28" fill="none" stroke="var(--gold)" strokeWidth="0.5" opacity="0.3" />
      {/* Loupe handle */}
      <line x1="58" y1="56" x2="70" y2="68" stroke="var(--mute)" strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />
      {/* Inclusions */}
      {Array.from({ length: inclusions }).map((_, i) => {
        const positions = [
          [35, 32], [45, 42], [38, 44], [48, 34], [42, 36],
        ];
        const [cx, cy] = positions[i];
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={1.5}
            fill="var(--mute)"
            opacity="0.35"
          />
        );
      })}
      {/* Center sparkle for clean stones */}
      {level <= 1 && (
        <path
          d="M40 30 L41 37 L48 38 L41 39 L40 46 L39 39 L32 38 L39 37 Z"
          fill="var(--gold)"
          fillOpacity="0.4"
          className="sparkle-dot"
        />
      )}
    </svg>
  );
}

/* ── Sub-step titles ── */
const SUB_TITLES: Record<number, { title: string; sub: string }> = {
  1: { title: "Presencia", sub: "El tamaño que se siente perfecto" },
  2: { title: "Fuego", sub: "La intensidad de su brillo" },
  3: { title: "Pureza", sub: "La perfección de su interior" },
  4: { title: "Color", sub: "El tono de blancura que prefieres" },
};

/* ── Main Component ── */
export function DiamondStep({
  diamondType,
  metal,
  diamondSize,
  diamondCut,
  diamondClarity,
  diamondColor,
  onUpdate,
}: DiamondStepProps) {
  const [subStep, setSubStep] = useState(1);
  const totalSubs = 4;

  // Determine if color step should auto-skip
  const autoSkipColor = isYellowGold(metal);

  // Auto-advance sub-step when selection made
  const advanceAfter = (field: string, value: string) => {
    onUpdate(field, value);
    setTimeout(() => {
      if (field === "diamondSize" && subStep === 1) setSubStep(2);
      else if (field === "diamondCut" && subStep === 2) setSubStep(3);
      else if (field === "diamondClarity" && subStep === 3) {
        if (autoSkipColor) {
          onUpdate("diamondColor", "H – I");
          // Stay at sub-step 3 briefly, parent will detect completion
        } else {
          setSubStep(4);
        }
      }
    }, 320);
  };

  // Auto-skip color for yellow gold
  useEffect(() => {
    if (autoSkipColor && diamondClarity && !diamondColor) {
      onUpdate("diamondColor", "H – I");
    }
  }, [autoSkipColor, diamondClarity, diamondColor, onUpdate]);

  // Determine which sub-step to show based on what's filled
  useEffect(() => {
    if (!diamondSize) setSubStep(1);
    else if (!diamondCut) setSubStep(2);
    else if (!diamondClarity) setSubStep(3);
    else if (!diamondColor && !autoSkipColor) setSubStep(4);
  }, [diamondSize, diamondCut, diamondClarity, diamondColor, autoSkipColor]);

  const tiers = DIAMOND_SIZE_TIERS[diamondType] ?? DIAMOND_SIZE_TIERS["Natural"];
  const { title, sub } = SUB_TITLES[subStep];
  const diamondScales = [0.6, 0.8, 1.0, 1.3];

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-2">
        <h2 className="font-display text-2xl sm:text-3xl text-[var(--ink)] font-semibold leading-snug">
          {title}
        </h2>
        <p className="font-accent italic text-base sm:text-lg text-[var(--mute)] mt-1.5">
          {sub}
        </p>
      </div>

      <MiniProgress current={subStep - 1} total={autoSkipColor ? 3 : totalSubs} />

      <div key={subStep} className="step-enter">
        {/* ── Sub-step 1: Presencia (Size) ── */}
        {subStep === 1 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {tiers.map((tier: SizeTier, idx: number) => {
              const active = diamondSize === tier.label;
              return (
                <button
                  key={tier.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => advanceAfter("diamondSize", tier.label)}
                  className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-5 px-3 relative`}
                >
                  {tier.badge && (
                    <div className="absolute -top-0 left-1/2 -translate-x-1/2 -translate-y-1/2">
                      <Badge text={tier.badge} color={tier.badgeColor ?? "gold"} />
                    </div>
                  )}
                  <HandWithDiamond scale={diamondScales[idx]} />
                  <div className="font-display text-base text-[var(--ink)] font-semibold mt-2">
                    {tier.emotionalName}
                  </div>
                  <div className="text-xs text-[var(--mute)] mt-1">{tier.caratRange}</div>
                  <div className="text-xs text-[var(--gold)] font-semibold mt-2">
                    ${tier.priceRange[0].toLocaleString("es-MX")} — ${tier.priceRange[1].toLocaleString("es-MX")}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Sub-step 2: Fuego (Cut Quality) ── */}
        {subStep === 2 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            {CUT_TIERS.map((tier: CutTier) => {
              const active = diamondCut === tier.technicalName;
              return (
                <button
                  key={tier.technicalName}
                  type="button"
                  aria-pressed={active}
                  onClick={() => advanceAfter("diamondCut", tier.technicalName)}
                  className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-6 px-4 relative`}
                >
                  {tier.badge && (
                    <div className="absolute top-2 right-2">
                      <Badge text={tier.badge} color={tier.badgeColor ?? "gold"} />
                    </div>
                  )}
                  <SparkleViz level={tier.sparkleLevel} />
                  <div className="font-display text-lg text-[var(--ink)] font-semibold mt-3">
                    {tier.label}
                  </div>
                  <div className="text-[11px] text-[var(--mute)] uppercase tracking-wider mt-1">
                    {tier.technicalName}
                  </div>
                  <div className="font-accent italic text-sm text-[var(--mute)] mt-2 text-center leading-snug">
                    {tier.description}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Sub-step 3: Pureza (Clarity) ── */}
        {subStep === 3 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            {CLARITY_TIERS.map((tier: ClarityTier) => {
              const active = diamondClarity === tier.technicalName;
              return (
                <button
                  key={tier.technicalName}
                  type="button"
                  aria-pressed={active}
                  onClick={() => advanceAfter("diamondClarity", tier.technicalName)}
                  className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-6 px-4 relative`}
                >
                  {tier.badge && (
                    <div className="absolute top-2 right-2">
                      <Badge text={tier.badge} color={tier.badgeColor ?? "gold"} />
                    </div>
                  )}
                  <ClarityViz level={tier.inclusionLevel} />
                  <div className="font-display text-lg text-[var(--ink)] font-semibold mt-3">
                    {tier.label}
                  </div>
                  <div className="text-[11px] text-[var(--mute)] uppercase tracking-wider mt-1">
                    {tier.technicalName}
                  </div>
                  <div className="font-accent italic text-sm text-[var(--mute)] mt-2 text-center leading-snug">
                    {tier.description}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Sub-step 4: Color ── */}
        {subStep === 4 && !autoSkipColor && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            {COLOR_TIERS.map((tier: ColorTier) => {
              const active = diamondColor === tier.technicalName;
              return (
                <button
                  key={tier.technicalName}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onUpdate("diamondColor", tier.technicalName)}
                  className={`card-soft ${active ? "is-active" : ""} flex flex-col items-center py-6 px-4 relative`}
                >
                  {tier.badge && (
                    <div className="absolute top-2 right-2">
                      <Badge text={tier.badge} color={tier.badgeColor ?? "gold"} />
                    </div>
                  )}
                  {/* Color gradient circle */}
                  <div
                    className="w-14 h-14 rounded-full border border-[var(--glass-border)]"
                    style={{
                      background:
                        tier.technicalName === "D – F"
                          ? "radial-gradient(circle at 35% 30%, #fff 0%, #F8F8FF 50%, #E8E8F0 100%)"
                          : tier.technicalName === "G"
                            ? "radial-gradient(circle at 35% 30%, #fff 0%, #F5F0E8 50%, #E8E0D0 100%)"
                            : "radial-gradient(circle at 35% 30%, #fff 0%, #F0E8D8 50%, #E0D4C0 100%)",
                    }}
                  />
                  <div className="font-display text-lg text-[var(--ink)] font-semibold mt-3">
                    {tier.label}
                  </div>
                  <div className="text-[11px] text-[var(--mute)] uppercase tracking-wider mt-1">
                    {tier.technicalName}
                  </div>
                  <div className="font-accent italic text-sm text-[var(--mute)] mt-2 text-center leading-snug">
                    {tier.description}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Auto-skip color toast for yellow gold */}
        {subStep === 4 && autoSkipColor && (
          <div className="text-center py-6">
            <div className="inline-flex items-center gap-2 bg-[var(--gold)]/10 border border-[var(--gold)]/20 rounded-xl px-5 py-3">
              <span className="text-[var(--gold)]">✦</span>
              <span className="text-sm text-[var(--ink)]">
                Seleccionamos <strong>H – I</strong>, el tono ideal para oro amarillo
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Sub-step navigation */}
      <div className="mt-6 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setSubStep(Math.max(1, subStep - 1))}
          disabled={subStep === 1}
          className="text-xs font-semibold text-[var(--mute)] hover:text-[var(--ink)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          ← Anterior detalle
        </button>
        <div className="text-[11px] text-[var(--mute)] uppercase tracking-wider">
          Detalle {subStep} de {autoSkipColor ? 3 : totalSubs}
        </div>
        <button
          type="button"
          onClick={() => setSubStep(Math.min(autoSkipColor ? 3 : totalSubs, subStep + 1))}
          disabled={
            (subStep === 1 && !diamondSize) ||
            (subStep === 2 && !diamondCut) ||
            (subStep === 3 && !diamondClarity) ||
            subStep === (autoSkipColor ? 3 : totalSubs)
          }
          className="text-xs font-semibold text-[var(--gold)] hover:text-[var(--gold-hover)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Siguiente detalle →
        </button>
      </div>
    </div>
  );
}
