import { useCallback, useRef } from "react";
import type { StudioState } from "@/lib/studio-types";
import { Button } from "@/components/ui/button";
import { Upload, X, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function StepUpload({ state, update }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const isIndividual = state.modo === "individual";
  const maxImages = isIndividual ? 1 : 6;

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files) return;
      const remaining = maxImages - state.rawImages.length;
      const toProcess = Array.from(files).slice(0, remaining);
      const base64s = await Promise.all(toProcess.map(fileToBase64));
      if (isIndividual) {
        update({ rawImages: base64s.slice(0, 1) });
      } else {
        update({ rawImages: [...state.rawImages, ...base64s] });
      }
    },
    [state.rawImages, maxImages, isIndividual, update]
  );

  const removeImage = (index: number) => {
    update({ rawImages: state.rawImages.filter((_, i) => i !== index) });
  };

  const canContinue = state.rawImages.length > 0;

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold mb-1">
        Subir foto{!isIndividual ? "s" : ""} cruda{!isIndividual ? "s" : ""}
      </h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        Sube la foto sobre la mesa, cualquier fondo está bien
      </p>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
          "border-border hover:border-primary/50 bg-card"
        )}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm font-body text-muted-foreground">
          {isIndividual
            ? "Haz clic o arrastra una imagen"
            : `Haz clic o arrastra hasta ${maxImages} imágenes`}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple={!isIndividual}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Previews */}
      {state.rawImages.length > 0 && (
        <div
          className={cn(
            "mt-4 gap-3",
            isIndividual ? "flex justify-center" : "grid grid-cols-3 sm:grid-cols-6"
          )}
        >
          {state.rawImages.map((img, i) => (
            <div key={i} className="relative group">
              <img
                src={img}
                alt={`Imagen ${i + 1}`}
                className={cn(
                  "rounded-lg object-cover border border-border",
                  isIndividual ? "w-48 h-48" : "w-full aspect-square"
                )}
              />
              <button
                onClick={() => removeImage(i)}
                className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {!isIndividual && state.rawImages.length > 0 && (
        <p className="text-xs text-muted-foreground font-body mt-2">
          {state.rawImages.length} de {maxImages} imágenes
        </p>
      )}

      <Button
        variant="gold"
        size="lg"
        className="w-full mt-6"
        disabled={!canContinue}
        onClick={() => update({ step: 3 })}
      >
        Generar imagen de producto
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    </div>
  );
}
