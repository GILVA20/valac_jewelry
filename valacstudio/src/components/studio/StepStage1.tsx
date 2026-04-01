import { useState, useEffect } from "react";
import type { StudioState } from "@/lib/studio-types";
import { generateStage1 } from "@/lib/studio-api";
import { ProcessingStatus } from "./ProcessingStatus";
import { ResultCard } from "./ResultCard";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

export function StepStage1({ state, update }: Props) {
  const [loading, setLoading] = useState(false);
  const [retryingIndices, setRetryingIndices] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<"analyzing" | "generating">("analyzing");
  const [error, setError] = useState("");
  const isBulk = state.modo === "bulk";
  const hasResults = state.stage1Results.length > 0;

  useEffect(() => {
    if (!hasResults && !loading) {
      runGeneration();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runGeneration() {
    setLoading(true);
    setError("");
    setPhase("analyzing");

    // Simulate two-phase UX (backend handles it all in one call)
    const phaseTimer = setTimeout(() => setPhase("generating"), 3000);

    try {
      const images = state.rawImages.map((img) =>
        img.startsWith("data:") ? img.split(",")[1] : img
      );
      const res = await generateStage1({
        images,
        sexo: state.sexo,
        categoria: state.categoria,
        modo: state.modo,
      });
      clearTimeout(phaseTimer);

      const approved = res.results
        .map((_, i) => i)
        .filter((i) => res.results[i].status === "approved");

      update({
        stage1Results: res.results,
        selectedResults: approved,
      });
    } catch (e) {
      setError("Error al generar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  const toggleSelect = (i: number) => {
    const sel = state.selectedResults.includes(i)
      ? state.selectedResults.filter((x) => x !== i)
      : [...state.selectedResults, i];
    update({ selectedResults: sel });
  };

  async function retrySingle(index: number, feedback?: string) {
    setRetryingIndices((prev) => new Set(prev).add(index));
    try {
      const img = state.rawImages[index];
      const image = img.startsWith("data:") ? img.split(",")[1] : img;
      const res = await generateStage1({
        images: [image],
        sexo: state.sexo,
        categoria: state.categoria,
        modo: "individual",
        feedback: feedback ? [feedback] : undefined,
      });
      if (res.results.length > 0) {
        const newResults = [...state.stage1Results];
        newResults[index] = res.results[0];
        const wasSelected = state.selectedResults.includes(index);
        const isNowApproved = res.results[0].status === "approved";
        let newSelected = state.selectedResults;
        if (isNowApproved && !wasSelected) {
          newSelected = [...newSelected, index];
        } else if (!isNowApproved && wasSelected) {
          newSelected = newSelected.filter((x) => x !== index);
        }
        update({ stage1Results: newResults, selectedResults: newSelected });
      }
    } catch {
      // keep existing result on error
    } finally {
      setRetryingIndices((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  }

  if (loading) {
    return (
      <ProcessingStatus
        phase={phase}
        isBulk={isBulk}
        completed={0}
        total={state.rawImages.length}
      />
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 space-y-4">
        <p className="text-destructive font-body">{error}</p>
        <Button variant="gold-outline" onClick={runGeneration}>
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold mb-1">
        Imagen de producto
      </h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        Revisa los resultados generados
      </p>

      <div className={isBulk ? "grid grid-cols-2 sm:grid-cols-3 gap-4" : "max-w-sm mx-auto"}>
        {state.stage1Results.map((result, i) => (
          <ResultCard
            key={i}
            result={result}
            index={i}
            isSelected={state.selectedResults.includes(i)}
            onSelect={() => toggleSelect(i)}
            onRetry={(feedback?: string) => retrySingle(i, feedback)}
            onSkip={() => {
              update({
                selectedResults: state.selectedResults.filter((x) => x !== i),
              });
            }}
            showDescription
            displayImage={result.product_image_base64}
            retrying={retryingIndices.has(i)}
          />
        ))}
      </div>

      <Button
        variant="gold"
        size="lg"
        className="w-full mt-6"
        disabled={state.selectedResults.length === 0}
        onClick={() => update({ step: 4 })}
      >
        Montar en base
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    </div>
  );
}
