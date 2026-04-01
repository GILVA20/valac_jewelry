import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  phase: "analyzing" | "generating";
  isBulk?: boolean;
  completed?: number;
  total?: number;
}

const LABELS = {
  analyzing: "🔍 Analizando joya con Claude...",
  generating: "✨ Generando imagen con Gemini...",
};

export function ProcessingStatus({ phase, isBulk, completed = 0, total = 1 }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-4">
      <Loader2 className="h-10 w-10 text-primary animate-spin" />
      <p className="text-base font-body font-medium text-foreground">
        {LABELS[phase]}
      </p>

      {isBulk && (
        <>
          <div className="w-full max-w-xs bg-secondary rounded-full h-2 overflow-hidden">
            <div
              className={cn("h-full bg-primary rounded-full transition-all duration-500")}
              style={{ width: `${(completed / total) * 100}%` }}
            />
          </div>
          <p className="text-sm text-muted-foreground font-body">
            {completed} de {total} completadas
          </p>
        </>
      )}
    </div>
  );
}
