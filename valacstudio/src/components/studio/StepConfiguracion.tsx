import { CATEGORIAS, type Sexo, type Modo, type StudioState } from "@/lib/studio-types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

function ToggleGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="mb-6">
      <label className="text-sm font-body font-medium text-foreground mb-2 block">
        {label}
      </label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-body font-medium transition-all border",
              value === opt.value
                ? "bg-primary text-primary-foreground border-primary shadow-sm"
                : "bg-card text-foreground border-border hover:border-primary/40"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function StepConfiguracion({ state, update }: Props) {
  const categorias = CATEGORIAS[state.sexo];
  const canContinue = state.sexo && state.categoria && state.modo;

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold mb-1">Configuración</h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        Define el tipo de joya que vas a fotografiar
      </p>

      <ToggleGroup
        label="Sexo"
        options={[
          { value: "hombre", label: "Hombre" },
          { value: "mujer", label: "Mujer" },
        ]}
        value={state.sexo}
        onChange={(v) => update({ sexo: v as Sexo, categoria: "" })}
      />

      <ToggleGroup
        label="Categoría"
        options={categorias.map((c) => ({ value: c, label: c }))}
        value={state.categoria}
        onChange={(v) => update({ categoria: v })}
      />

      <ToggleGroup
        label="Modo"
        options={[
          { value: "individual", label: "Individual" },
          { value: "bulk", label: "Bulk" },
        ]}
        value={state.modo}
        onChange={(v) => update({ modo: v as Modo })}
      />

      <Button
        variant="gold"
        size="lg"
        className="w-full mt-4"
        disabled={!canContinue}
        onClick={() => update({ step: 2 })}
      >
        Continuar
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    </div>
  );
}
