import { useState } from "react";
import type { StudioState, Product } from "@/lib/studio-types";
import { fetchProducts, saveToProduct } from "@/lib/studio-api";
import { Button } from "@/components/ui/button";
import { Download, FolderOpen, RotateCcw, Check, X, Package, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  state: StudioState;
  update: (p: Partial<StudioState>) => void;
}

interface ImagePair {
  productImage: string;
  mountedImage: string;
  description?: string;
}

export function StepResultado({ state, update }: Props) {
  const [saveIndex, setSaveIndex] = useState<number | null>(null);
  const [saveType, setSaveType] = useState<"product" | "mounted">("product");
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedName, setSavedName] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(false);

  const isBulk = state.modo === "bulk";

  /** Turn a description into a short, filesystem-safe slug. */
  const slugify = (text?: string): string => {
    if (!text) return "imagen";
    return text
      .toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")   // strip accents
      .replace(/[^a-z0-9]+/g, "_")                        // non-alnum → _
      .replace(/^_|_$/g, "")                               // trim edges
      .slice(0, 60);                                       // cap length
  };

  // Build image pairs: product (from stage1) + mounted (from stage2)
  const imagePairs: ImagePair[] = state.selectedFinals.map((finalIdx) => {
    const stage1Idx = state.selectedResults[finalIdx];
    const stage1 = state.stage1Results[stage1Idx];
    const stage2 = state.stage2Results[finalIdx];
    return {
      productImage: stage1?.product_image_base64 || stage1?.image_base64 || "",
      mountedImage: stage2?.image_base64 || "",
      description: stage1?.description,
    };
  });

  const downloadImage = (base64: string, name: string) => {
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${base64}`;
    link.download = name;
    link.click();
  };

  const downloadAll = () => {
    imagePairs.forEach((pair, i) => {
      const slug = slugify(pair.description);
      downloadImage(pair.productImage, `valac_producto_${slug}.png`);
      setTimeout(() => {
        downloadImage(pair.mountedImage, `valac_montaje_${slug}.png`);
      }, 300 * (i + 1));
    });
  };

  const openSaveSheet = async (index: number, type: "product" | "mounted") => {
    setSaveIndex(index);
    setSaveType(type);
    setSavedName("");
    setSelectedProduct("");
    if (products.length === 0) {
      setLoadingProducts(true);
      try {
        const prods = await fetchProducts();
        setProducts(prods);
      } catch {
        // fail silently
      } finally {
        setLoadingProducts(false);
      }
    }
  };

  const handleSave = async () => {
    if (saveIndex === null || !selectedProduct) return;
    setSaving(true);
    try {
      const pair = imagePairs[saveIndex];
      const imageToSave = saveType === "product" ? pair.productImage : pair.mountedImage;
      await saveToProduct({
        image_base64: imageToSave,
        producto_id: selectedProduct,
      });
      const prod = products.find((p) => p.id === selectedProduct);
      setSavedName(prod?.nombre || "producto");
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const totalImages = imagePairs.length * 2;

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold mb-1">
        Resultado final
      </h2>
      <p className="text-sm text-muted-foreground font-body mb-6">
        {imagePairs.length} par{imagePairs.length !== 1 ? "es" : ""} de imágenes
        ({totalImages} archivos)
      </p>

      <div className="space-y-6">
        {imagePairs.map((pair, i) => (
          <div key={i} className="rounded-xl border border-border bg-card overflow-hidden">
            {/* Pair header */}
            <div className="px-4 pt-3 pb-1">
              <span className="text-xs font-body font-medium text-muted-foreground uppercase tracking-wider">
                {pair.description
                  ? pair.description.slice(0, 80) + (pair.description.length > 80 ? "…" : "")
                  : `Imagen ${i + 1}`}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-px bg-border">
              {/* Product image */}
              <div className="bg-card">
                <div className="relative">
                  <img
                    src={`data:image/png;base64,${pair.productImage}`}
                    alt={`Producto ${i + 1}`}
                    className="w-full aspect-square object-cover"
                  />
                  <span className="absolute top-2 left-2 inline-flex items-center gap-1 text-xs font-body font-medium px-2 py-1 rounded-full bg-card/90 text-foreground backdrop-blur-sm">
                    <Package className="h-3 w-3" /> Producto
                  </span>
                </div>
                <div className="p-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => downloadImage(pair.productImage, `valac_producto_${slugify(pair.description)}.png`)}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Descargar
                  </Button>
                  <Button
                    variant="gold-outline"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => openSaveSheet(i, "product")}
                  >
                    <FolderOpen className="h-3 w-3 mr-1" />
                    Guardar
                  </Button>
                </div>
              </div>

              {/* Mounted image */}
              <div className="bg-card">
                <div className="relative">
                  <img
                    src={`data:image/png;base64,${pair.mountedImage}`}
                    alt={`Montaje ${i + 1}`}
                    className="w-full aspect-square object-cover"
                  />
                  <span className="absolute top-2 left-2 inline-flex items-center gap-1 text-xs font-body font-medium px-2 py-1 rounded-full bg-card/90 text-foreground backdrop-blur-sm">
                    <UserRound className="h-3 w-3" /> Montaje
                  </span>
                </div>
                <div className="p-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => downloadImage(pair.mountedImage, `valac_montaje_${slugify(pair.description)}.png`)}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Descargar
                  </Button>
                  <Button
                    variant="gold-outline"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => openSaveSheet(i, "mounted")}
                  >
                    <FolderOpen className="h-3 w-3 mr-1" />
                    Guardar
                  </Button>
                </div>
              </div>
            </div>

            {/* Retry per pair */}
            <div className="px-4 pb-3 flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-muted-foreground"
                onClick={() => update({ step: 3 })}
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Regenerar
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Download all */}
      <Button
        variant="gold"
        size="lg"
        className="w-full mt-6"
        onClick={downloadAll}
      >
        <Download className="mr-2 h-4 w-4" />
        Descargar todo ({totalImages} imágenes)
      </Button>

      {/* Save bottom sheet */}
      {saveIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/40">
          <div
            className={cn(
              "w-full max-w-lg bg-card rounded-t-2xl border-t border-border p-6 space-y-4",
              "animate-in slide-in-from-bottom duration-300"
            )}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-display font-semibold">
                Guardar {saveType === "product" ? "imagen de producto" : "imagen de montaje"} en catálogo
              </h3>
              <button
                onClick={() => setSaveIndex(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {savedName ? (
              <div className="text-center py-6">
                <Check className="mx-auto h-10 w-10 text-success mb-2" />
                <p className="font-body text-sm">
                  Guardada en <strong>{savedName}</strong>
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => setSaveIndex(null)}
                >
                  Cerrar
                </Button>
              </div>
            ) : (
              <>
                {loadingProducts ? (
                  <p className="text-sm text-muted-foreground font-body">
                    Cargando productos...
                  </p>
                ) : (
                  <select
                    value={selectedProduct}
                    onChange={(e) => setSelectedProduct(e.target.value)}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-body focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                  >
                    <option value="">Seleccionar producto...</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nombre}
                      </option>
                    ))}
                  </select>
                )}

                <Button
                  variant="gold"
                  className="w-full"
                  disabled={!selectedProduct || saving}
                  onClick={handleSave}
                >
                  {saving ? "Guardando..." : "Guardar"}
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
