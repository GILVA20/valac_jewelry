import { useState } from "react";
import type { StageResult } from "@/lib/studio-types";
import { Button } from "@/components/ui/button";
import { Check, AlertTriangle, ChevronDown, ChevronUp, RotateCcw, SkipForward, Loader2, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  result: StageResult;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onRetry: (feedback?: string) => void;
  onSkip: () => void;
  showDescription?: boolean;
  displayImage?: string;
  retrying?: boolean;
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
  retrying = false,
}: Props) {
  const [showDesc, setShowDesc] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const approved = result.status === "approved";
  const imageSrc = displayImage || result.image_base64;

  const handleRetry = () => {
    const fb = feedback.trim();
    onRetry(fb || undefined);
    setFeedback("");
    setShowFeedback(false);
  };

  return (
    <div
      className={cn(
        "rounded-xl border bg-card overflow-hidden transition-all",
        retrying && "opacity-60",
        isSelected ? "border-primary ring-2 ring-primary/20" : "border-border"
      )}
    >
      <div className="relative">
        <img
          src={`data:image/png;base64,${imageSrc}`}
          alt={`Resultado ${index + 1}`}
          className="w-full aspect-square object-cover"
        />
        {retrying && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/60">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}
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
            disabled={retrying}
          >
            <Check className="h-3 w-3 mr-1" />
            {isSelected ? "Seleccionada" : "Usar esta"}
          </Button>
          <Button
            variant={showFeedback ? "default" : "outline"}
            size="sm"
            onClick={() => setShowFeedback(!showFeedback)}
            className="text-xs"
            disabled={retrying}
          >
            <MessageSquare className="h-3 w-3" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleRetry} className="text-xs" disabled={retrying}>
            <RotateCcw className={cn("h-3 w-3", retrying && "animate-spin")} />
          </Button>
          <Button variant="ghost" size="sm" onClick={onSkip} className="text-xs" disabled={retrying}>
            <SkipForward className="h-3 w-3" />
          </Button>
        </div>

        {showFeedback && (
          <div className="space-y-2">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Ej: El oro se ve muy amarillo, debería ser más rosado. La cadena está muy gruesa..."
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs font-body placeholder:text-muted-foreground/60 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none resize-none"
              rows={3}
              disabled={retrying}
            />
            <Button
              variant="gold"
              size="sm"
              className="w-full text-xs"
              onClick={handleRetry}
              disabled={retrying || !feedback.trim()}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Regenerar con correcciones
            </Button>
          </div>
        )}

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
