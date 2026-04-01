import { cn } from "@/lib/utils";

interface Props {
  current: number;
  labels: string[];
}

export function StepIndicator({ current, labels }: Props) {
  return (
    <div className="mb-8 flex items-center gap-1 overflow-x-auto pb-2">
      {labels.map((label, i) => {
        const step = i + 1;
        const isActive = step === current;
        const isDone = step < current;
        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center min-w-[56px]">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-body font-semibold transition-colors",
                  isActive && "bg-primary text-primary-foreground",
                  isDone && "bg-primary/20 text-primary",
                  !isActive && !isDone && "bg-secondary text-muted-foreground"
                )}
              >
                {isDone ? "✓" : step}
              </div>
              <span
                className={cn(
                  "text-[10px] font-body mt-1 text-center leading-tight",
                  isActive ? "text-foreground font-medium" : "text-muted-foreground"
                )}
              >
                {label}
              </span>
            </div>
            {i < labels.length - 1 && (
              <div
                className={cn(
                  "h-px w-6 mx-0.5 mt-[-12px]",
                  isDone ? "bg-primary/40" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
