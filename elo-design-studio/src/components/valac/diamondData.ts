// Diamond pricing tiers — VALAC Joyas Engagement Rings
// Prices in MXN. Based on real market (2024-2026 sourcing).
// Reference: 0.4ct Natural + montura ≈ $50k MXN

export interface SizeTier {
  label: string;
  emotionalName: string;
  caratRange: string;
  priceRange: [number, number]; // [min, max] diamond only
  badge?: string;
  badgeColor?: "oxblood" | "gold";
}

export const DIAMOND_SIZE_TIERS: Record<string, SizeTier[]> = {
  Natural: [
    {
      label: "Sutil",
      emotionalName: "Sutil",
      caratRange: "0.25 – 0.35 ct",
      priceRange: [17_000, 29_000],
    },
    {
      label: "Clásica",
      emotionalName: "Clásica",
      caratRange: "0.40 – 0.55 ct",
      priceRange: [29_000, 50_000],
      badge: "La más elegida",
      badgeColor: "oxblood",
    },
    {
      label: "Imponente",
      emotionalName: "Imponente",
      caratRange: "0.70 – 0.90 ct",
      priceRange: [54_000, 94_000],
    },
    {
      label: "Extraordinaria",
      emotionalName: "Extraordinaria",
      caratRange: "1.00 – 1.50 ct",
      priceRange: [96_000, 168_000],
    },
  ],
  "Lab-Grown": [
    {
      label: "Brillante",
      emotionalName: "Brillante",
      caratRange: "0.50 – 0.70 ct",
      priceRange: [10_000, 18_000],
    },
    {
      label: "Espectacular",
      emotionalName: "Espectacular",
      caratRange: "0.80 – 1.00 ct",
      priceRange: [18_000, 31_000],
      badge: "La más elegida",
      badgeColor: "oxblood",
    },
    {
      label: "Icónica",
      emotionalName: "Icónica",
      caratRange: "1.20 – 1.50 ct",
      priceRange: [31_000, 54_000],
    },
    {
      label: "Legendaria",
      emotionalName: "Legendaria",
      caratRange: "2.00 – 3.00 ct",
      priceRange: [54_000, 96_000],
    },
  ],
};

export interface CutTier {
  label: string;
  technicalName: string;
  description: string;
  sparkleLevel: number; // 1-3
  badge?: string;
  badgeColor?: "oxblood" | "gold";
}

export const CUT_TIERS: CutTier[] = [
  {
    label: "Muy bueno",
    technicalName: "Very Good",
    description: "Brillo excelente con gran resplandor",
    sparkleLevel: 1,
  },
  {
    label: "Excepcional",
    technicalName: "Excellent",
    description: "Fuego y brillo superiores, perfección visible",
    sparkleLevel: 2,
    badge: "Sweet spot",
    badgeColor: "gold",
  },
  {
    label: "Ideal",
    technicalName: "Ideal",
    description: "La talla más precisa — máximo fuego y destello",
    sparkleLevel: 3,
  },
];

export interface ClarityTier {
  label: string;
  technicalName: string;
  description: string;
  inclusionLevel: number; // 3=most, 1=fewest
  badge?: string;
  badgeColor?: "oxblood" | "gold";
}

export const CLARITY_TIERS: ClarityTier[] = [
  {
    label: "Pura",
    technicalName: "SI1 – SI2",
    description: "Pequeñas inclusiones invisibles sin lupa",
    inclusionLevel: 3,
  },
  {
    label: "Cristalina",
    technicalName: "VS2 – VS1",
    description: "Casi perfecta — inclusiones mínimas aun con lupa",
    inclusionLevel: 2,
    badge: "El preferido",
    badgeColor: "gold",
  },
  {
    label: "Inmaculada",
    technicalName: "VVS1 – IF",
    description: "Perfección absoluta — nada visible en 10× lupa",
    inclusionLevel: 1,
  },
];

export interface ColorTier {
  label: string;
  technicalName: string;
  description: string;
  badge?: string;
  badgeColor?: "oxblood" | "gold";
}

export const COLOR_TIERS: ColorTier[] = [
  {
    label: "Cálido",
    technicalName: "H – I",
    description: "Tono cálido casi imperceptible — ideal para oro amarillo",
  },
  {
    label: "Blanco",
    technicalName: "G",
    description: "Blancura notable — brilla espectacular en oro blanco",
    badge: "Estándar de lujo",
    badgeColor: "gold",
  },
  {
    label: "Excepcional",
    technicalName: "D – F",
    description: "Blancura absoluta — la máxima rareza",
  },
];

// Multipliers applied to diamond base price
export const CUT_MULT: Record<string, number> = {
  "Very Good": 1.0,
  Excellent: 1.10,
  Ideal: 1.18,
};

export const CLARITY_MULT: Record<string, number> = {
  "SI1 – SI2": 1.0,
  "VS2 – VS1": 1.12,
  "VVS1 – IF": 1.28,
};

export const COLOR_MULT: Record<string, number> = {
  "H – I": 1.0,
  G: 1.08,
  "D – F": 1.15,
};

// Mounting base price by metal (includes craftsmanship)
export const MOUNTING_BASE: Record<string, [number, number]> = {
  "Amarillo 10k": [5_500, 8_000],
  "Amarillo 14k": [8_000, 11_000],
  "Amarillo 18k": [10_000, 14_000],
  "Blanco 14k":   [8_500, 11_500],
  "Blanco 18k":   [11_000, 15_000],
};
// Rosé 14k eliminado — catálogo VALAC solo ofrece amarillo y blanco

export const STYLE_MULT: Record<string, number> = {
  Solitario: 1.0,
  Halo: 1.18,
  Pavé: 1.25,
  "Tres Piedras": 1.38,
};

// Utility: is metal yellow gold?
export function isYellowGold(metal: string): boolean {
  return metal.startsWith("Amarillo");
}

// Compute estimated price range from all selections
export function computePriceRange(
  diamondType: string,
  diamondSize: string,
  cut: string,
  clarity: string,
  color: string,
  metal: string,
  style: string,
): [number, number] | null {
  const tiers = DIAMOND_SIZE_TIERS[diamondType];
  if (!tiers) return null;

  const tier = tiers.find((t) => t.label === diamondSize);
  if (!tier) return null;

  const cm = CUT_MULT[cut] ?? 1;
  const clm = CLARITY_MULT[clarity] ?? 1;
  const colm = COLOR_MULT[color] ?? 1;
  const sm = STYLE_MULT[style] ?? 1;
  const [mLo, mHi] = MOUNTING_BASE[metal] ?? [6_000, 9_000];

  const dLo = tier.priceRange[0] * cm * clm * colm;
  const dHi = tier.priceRange[1] * cm * clm * colm;

  const lo = Math.round((dLo + mLo * sm) / 1_000) * 1_000;
  const hi = Math.round((dHi + mHi * sm) / 1_000) * 1_000;

  return [lo, hi];
}
