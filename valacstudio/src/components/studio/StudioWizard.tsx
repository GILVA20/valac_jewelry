import { useState, useCallback } from "react";
import { initialStudioState, type StudioState } from "@/lib/studio-types";
import { StepIndicator } from "./StepIndicator";
import { StepConfiguracion } from "./StepConfiguracion";
import { StepUpload } from "./StepUpload";
import { StepStage1 } from "./StepStage1";
import { StepSelectBase } from "./StepSelectBase";
import { StepStage2 } from "./StepStage2";
import { StepResultado } from "./StepResultado";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

const STEP_LABELS = [
  "Configuración",
  "Subir fotos",
  "Generando",
  "Imagen base",
  "Montando",
  "Resultado",
];

export function StudioWizard() {
  const [state, setState] = useState<StudioState>(initialStudioState);

  const update = useCallback(
    (partial: Partial<StudioState>) =>
      setState((prev) => ({ ...prev, ...partial })),
    []
  );

  const goBack = () => {
    if (state.step > 1) update({ step: state.step - 1 });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card px-4 py-4">
        <div className="mx-auto max-w-3xl flex items-center gap-3">
          <h1 className="text-xl font-display font-semibold tracking-tight text-foreground">
            VALAC Studio
          </h1>
          <span className="text-xs font-body text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">
            Beta
          </span>
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-4 py-6">
        {/* Step indicator */}
        <StepIndicator current={state.step} labels={STEP_LABELS} />

        {/* Back button */}
        {state.step > 1 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={goBack}
            className="mb-4 -ml-2 text-muted-foreground"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver
          </Button>
        )}

        {/* Steps */}
        <div className="studio-step-enter" key={state.step}>
          {state.step === 1 && <StepConfiguracion state={state} update={update} />}
          {state.step === 2 && <StepUpload state={state} update={update} />}
          {state.step === 3 && <StepStage1 state={state} update={update} />}
          {state.step === 4 && <StepSelectBase state={state} update={update} />}
          {state.step === 5 && <StepStage2 state={state} update={update} />}
          {state.step === 6 && <StepResultado state={state} update={update} />}
        </div>
      </div>
    </div>
  );
}
