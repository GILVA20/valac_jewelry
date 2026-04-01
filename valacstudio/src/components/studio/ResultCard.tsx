import { useState } from "react";
import type { StageResult } from "@/lib/studio-types";
import { Button } from "@/components/ui/button";
import { Check, AlertTriangle, ChevronDown, ChevronUp, RotateCcw, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  result: StageResult;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onRetry: () => void;
  onSkip: () => void;
  showDescription?: boolean;
  displayImage?: string;
}

export function ResultCard({
  result,
  index,
  isSelected,
  onSelect,
  onRetry,
  onSkip,
  showDescription = false,
  displayImage,
}: Props) {
  const [showDesc, setShowDesc] = useState(false);
  const approved = result.status === "approved";
  const imageSrc = displayImage || result.image_base64;

  return (
    <div
      className={cn(
        "rounded-xl border bg-card overflow-hidden transition-all",
        isSelected ? "border-primary ring-2 ring-primary/20" : "border-border"
      )}
    >
      <div className="relative">
        <img
          src={`data:image/png;base64,${imageSrc}`}
          alt={`Resultado ${index + 1}`}
          className="w-full aspect-square object-cover"
        />
        <div className="absolute top-2 left-2">
          {approved ? (
            <span className="inline-flex items-center gap-1 text-xs font-body font-medium px-2 py-1 rounded-full bg-success text-success-foreground">
              <Check className="h-3 w-3" /> Aprobada
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-body font-medium px-2 py-1 rounded-full bg-warning text-warning-foreground">
              <AlertTriangle className="h-3 w-3" /> Revisar
            </span>
          )}
        </div>
      </div>

      <div className="p-3 space-y-2">
        {result.status === "review" && result.reason && (
          <p className="text-xs text-muted-foreground font-body">{result.reason}</p>
        )}

        <div className="flex gap-2">
          <Button
            variant={isSelected ? "gold" : "gold-outline"}
            size="sm"
            className="flex-1 text-xs"
            onClick={onSelect}
          >
            <Check className="h-3 w-3 mr-1" />
            {isSelected ? "Seleccionada" : "Usar esta"}
          </Button>
          <Button variant="outline" size="sm" onClick={onRetry} className="text-xs">
            <RotateCcw className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="sm" onClick={onSkip} className="text-xs">
            <SkipForward className="h-3 w-3" />
          </Button>
        </div>

        {showDescription && result.description && (
          <button
            onClick={() => setShowDesc(!showDesc)}
            className="flex items-center gap-1 text-xs text-primary font-body font-medium hover:underline"
          >
            Ver descripción
            {showDesc ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>
        )}
        {showDesc && result.description && (
          <p className="text-xs text-muted-foreground font-body bg-secondary rounded-lg p-2">
            {result.description}
          </p>
        )}
      </div>
    </div>
  );
}
