import { useMemo } from "react";
import type { StudioState } from "@/lib/studio-types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

// Base images available in /public/bases/
// Format: sexo_categoria (lowercase, no spaces)
function getBaseKey(sexo: string, categoria: string) {
  return `${sexo}_${categoria.toLowerCase().replace(/[\s+]/g, "_").replace(/\+/g, "")}`;
}

const ALL_BASES = [
  { key: "mujer_arete",       filename: "mujer_arete.jpg",        label: "Mujer - Arete" },
  { key: "mujer_cadena",      filename: "mujer_cadena.png",       label: "Mujer - Cadena" },
  { key: "mujer_pulso",       filename: "mujer_pulso.png",        label: "Mujer - Pulso" },
  { key: "mujer_anillo",      filename: "mujer_anillo.jpg",       label: "Mujer - Anillo" },
  { key: "mujer_dije",        filename: "mujer_dije.png",         label: "Mujer - Dije" },
  { key: "hombre_collar_dije",filename: "hombre_collar_dije.png", label: "Hombre - Collar + Dije" },
  { key: "hombre_cadena",     filename: "hombre_cadena.png",      label: "Hombre - Cadena" },
  { key: "hombre_pulso",      filename: "hombre_pulso.png",       label: "Hombre - Pulso" },
  { key: "hombre_anillo",     filename: "hombre_anillo.jpg",      label: "Hombre - Anillo" },
  { key: "hombre_arete",      filename: "hombre_arete.jpg",       label: "Hombre - Arete" },
];

export function StepSelectBase({ state, update }: Props) {
  const matchKey = useMemo(
    () => getBaseKey(state.sexo, state.categoria),
    [state.sexo, state.categoria]
  );

  // Auto-select matching base on first render
  useMemo(() => {
    if (!state.selectedBase) {
      update({ selectedBase: matchKey });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold mb-1">
        Seleccionar imagen base
      </h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        Elige la base de estilo de vida para montar la joya
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {ALL_BASES.map((base) => {
          const isMatch = base.key === matchKey;
          const isSelected = state.selectedBase === base.key;
          return (
            <button
              key={base.key}
              onClick={() => update({ selectedBase: base.key })}
              className={cn(
                "relative rounded-xl overflow-hidden border-2 transition-all",
                isSelected
                  ? "border-primary ring-2 ring-primary/20"
                  : "border-border hover:border-primary/30",
                isMatch && !isSelected && "border-primary/40"
              )}
            >
              {/* Base images served from Flask static folder */}
              <div className="aspect-[4/5] bg-secondary flex items-center justify-center">
                <img
                  src={`/static/studio/bases/${base.filename}`}
                  alt={base.label}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-foreground/70 to-transparent p-2">
                <p className="text-xs font-body font-medium text-card text-center">
                  {base.label}
                </p>
              </div>
              {isMatch && (
                <span className="absolute top-2 right-2 text-[10px] font-body font-medium bg-primary text-primary-foreground px-1.5 py-0.5 rounded-full">
                  Sugerida
                </span>
              )}
            </button>
          );
        })}
      </div>

      <Button
        variant="gold"
        size="lg"
        className="w-full mt-6"
        disabled={!state.selectedBase}
        onClick={() => update({ step: 5 })}
      >
        Montar joya
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    </div>
  );
}
