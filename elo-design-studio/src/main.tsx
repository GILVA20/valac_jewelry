import { createRoot } from "react-dom/client";
import { Configurator } from "@/components/valac/Configurator";
import type { Selections } from "@/components/valac/Configurator";
import "./styles.css";

const WHATSAPP_NUMBER = "5213320471076";

function buildWaUrl(sel: Selections | null): string {
  const parts = sel
    ? [
        sel.forWhom && `Para: ${sel.forWhom}`,
        sel.diamond && `Diamante: ${sel.diamond}`,
        sel.cut && `Corte: ${sel.cut}`,
        sel.metal && `Metal: ${sel.metal}`,
        sel.style && `Estilo: ${sel.style}`,
        sel.setting && `Montura: ${sel.setting}`,
        sel.size && `Talla: ${sel.size}`,
      ].filter(Boolean) as string[]
    : [];
  const text = parts.length
    ? `Hola VALAC, quiero solicitar mi cotización personalizada:\n\n· ${parts.join("\n· ")}\n\n¿Me ayudan?`
    : "Hola, quiero información sobre anillos de compromiso VALAC.";
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(text)}`;
}

let currentSel: Selections | null = null;

function handleChange(s: Selections, _c: number, _ready: boolean) {
  currentSel = s;
}

function handleRequestQuote() {
  window.open(buildWaUrl(currentSel), "_blank", "noopener,noreferrer");
}

const root = document.getElementById("configurador-root");
if (root) {
  createRoot(root).render(
    <Configurator onSelectionsChange={handleChange} onRequestQuote={handleRequestQuote} />
  );
}
