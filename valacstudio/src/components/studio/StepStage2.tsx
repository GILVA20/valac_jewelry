import { useState, useEffect } from "react";
import type { StudioState } from "@/lib/studio-types";
import { generateStage2 } from "@/lib/studio-api";
import { ProcessingStatus } from "./ProcessingStatus";
import { ResultCard } from "./ResultCard";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

export function StepStage2({ state, update }: Props) {
  const [loading, setLoading] = useState(false);
  const [retryingIndices, setRetryingIndices] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<"analyzing" | "generating">("analyzing");
  const [error, setError] = useState("");
  const isBulk = state.modo === "bulk";
  const hasResults = state.stage2Results.length > 0;

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

    const phaseTimer = setTimeout(() => setPhase("generating"), 3000);

    try {
      const selectedImages = state.selectedResults.map(
        (i) => state.stage1Results[i].image_base64
      );
      const productStudioImages = state.selectedResults.map(
        (i) => state.stage1Results[i].product_image_base64 || state.stage1Results[i].image_base64
      );
      const descriptions = state.selectedResults.map(
        (i) => state.stage1Results[i].description || ""
      );

      const res = await generateStage2({
        product_images: selectedImages,
        product_studio_images: productStudioImages,
        base_image: state.selectedBase,
        sexo: state.sexo,
        categoria: state.categoria,
        descriptions,
      });
      clearTimeout(phaseTimer);

      const approved = res.results
        .map((_, i) => i)
        .filter((i) => res.results[i].status === "approved");

      update({
        stage2Results: res.results,
        selectedFinals: approved,
      });
    } catch (e) {
      setError("Error al montar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  const toggleSelect = (i: number) => {
    const sel = state.selectedFinals.includes(i)
      ? state.selectedFinals.filter((x) => x !== i)
      : [...state.selectedFinals, i];
    update({ selectedFinals: sel });
  };

  async function retrySingle(index: number) {
    setRetryingIndices((prev) => new Set(prev).add(index));
    try {
      const stage1Idx = state.selectedResults[index];
      const prodImg = state.stage1Results[stage1Idx].image_base64;
      const studioImg = state.stage1Results[stage1Idx].product_image_base64 || prodImg;
      const desc = state.stage1Results[stage1Idx].description || "";

      const res = await generateStage2({
        product_images: [prodImg],
        product_studio_images: [studioImg],
        base_image: state.selectedBase,
        sexo: state.sexo,
        categoria: state.categoria,
        descriptions: [desc],
      });
      if (res.results.length > 0) {
        const newResults = [...state.stage2Results];
        newResults[index] = res.results[0];
        const wasSelected = state.selectedFinals.includes(index);
        const isNowApproved = res.results[0].status === "approved";
        let newSelected = state.selectedFinals;
        if (isNowApproved && !wasSelected) {
          newSelected = [...newSelected, index];
        } else if (!isNowApproved && wasSelected) {
          newSelected = newSelected.filter((x) => x !== index);
        }
        update({ stage2Results: newResults, selectedFinals: newSelected });
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
        total={state.selectedResults.length}
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
        Montaje en imagen base
      </h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        Revisa cómo quedó la joya montada
      </p>

      <div className={isBulk ? "grid grid-cols-2 sm:grid-cols-3 gap-4" : "max-w-sm mx-auto"}>
        {state.stage2Results.map((result, i) => (
          <ResultCard
            key={i}
            result={result}
            index={i}
            isSelected={state.selectedFinals.includes(i)}
            onSelect={() => toggleSelect(i)}
            onRetry={() => retrySingle(i)}
            onSkip={() => {
              update({
                selectedFinals: state.selectedFinals.filter((x) => x !== i),
              });
            }}
            retrying={retryingIndices.has(i)}
          />
        ))}
      </div>

      <Button
        variant="gold"
        size="lg"
        className="w-full mt-6"
        disabled={state.selectedFinals.length === 0}
        onClick={() => update({ step: 6 })}
      >
        Ver resultados finales
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    </div>
  );
}
