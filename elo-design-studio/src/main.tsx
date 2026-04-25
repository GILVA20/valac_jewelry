import { createRoot } from "react-dom/client";
import { Configurator } from "@/components/valac/Configurator";
import type { Selections } from "@/components/valac/Configurator";
import "./styles.css";

const WHATSAPP_NUMBER = "527718574647";

function buildWaUrl(sel: Selections | null): string {
  const parts = sel
    ? [
        sel.forWhom && `Para: ${sel.forWhom}`,
        sel.diamond && `💎 Diamante: ${sel.diamond}${sel.diamond === "Natural" ? " (GIA)" : " (IGI)"}`,
        sel.diamondSize && `✨ Presencia: ${sel.diamondSize}`,
        sel.diamondCut && `🔥 Corte: ${sel.diamondCut}`,
        sel.diamondClarity && `🔍 Pureza: ${sel.diamondClarity}`,
        sel.diamondColor && `🎨 Color: ${sel.diamondColor}`,
        sel.shape && `💍 Forma: ${sel.shape}`,
        sel.metal && `⚙️ Metal: ${sel.metal}`,
        sel.style && `🎀 Estilo: ${sel.style}`,
        sel.setting && `Montura: ${sel.setting}`,
        sel.size && `📏 Talla: ${sel.size}`,
      ].filter(Boolean) as string[]
    : [];
  const text = parts.length
    ? `✨ *Mi Anillo de Compromiso VALAC* ✨\n\n${parts.join("\n")}\n\n📅 Entrega estimada: 4-6 semanas\n\nMe encantaría recibir mi cotización personalizada 💕`
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
