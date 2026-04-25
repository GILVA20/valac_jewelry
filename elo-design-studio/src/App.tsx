import { useCallback, useEffect, useRef, useState } from "react";
import heroImg from "@/assets/hero-compromiso.jpg";
import ringSolitario from "@/assets/ring-solitario.jpg";
import ringHalo from "@/assets/ring-halo.jpg";
import ringPave from "@/assets/ring-pave.jpg";
import ringTres from "@/assets/ring-tres.jpg";
import { Configurator, type Selections } from "@/components/valac/Configurator";

const WHATSAPP_NUMBER = "5213320471076";

const PRODUCTS = [
  { name: "Solitario Clásico 14k", price: 8500, img: ringSolitario },
  { name: "Halo Brillante 14k", price: 12900, img: ringHalo },
  { name: "Pavé Rosé 14k", price: 9800, img: ringPave },
  { name: "Tres Piedras Oval", price: 14500, img: ringTres },
];

export default function App() {
  const [sel, setSel] = useState<Selections | null>(null);
  const [, setCount] = useState(0);
  const [, setReady] = useState(false);
  const stableSel = useRef<Selections | null>(null);
  stableSel.current = sel;

  const handleChange = useCallback((s: Selections, c: number, ready: boolean) => {
    setSel(s); setCount(c); setReady(ready);
  }, []);

  const buildWaUrl = useCallback(() => {
    const s = stableSel.current;
    const parts = s
      ? [
          s.forWhom && `Para: ${s.forWhom}`,
          s.diamond && `Diamante: ${s.diamond}`,
          s.cut && `Corte: ${s.cut}`,
          s.metal && `Metal: ${s.metal}`,
          s.style && `Estilo: ${s.style}`,
          s.setting && `Montura: ${s.setting}`,
          s.size && `Talla: ${s.size}`,
        ].filter(Boolean) as string[]
      : [];
    const text = parts.length
      ? `Hola VALAC, quiero solicitar mi cotización personalizada:\n\n· ${parts.join("\n· ")}\n\n¿Me ayudan?`
      : "Hola, quiero información sobre anillos de compromiso VALAC.";
    return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(text)}`;
  }, []);

  const handleRequestQuote = useCallback(() => {
    window.open(buildWaUrl(), "_blank", "noopener,noreferrer");
  }, [buildWaUrl]);

  useEffect(() => {
    const els = document.querySelectorAll(".fade-on-scroll");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <>
      {/* ───────── MINI NAV ───────── */}
      <div className="bg-white/95 backdrop-blur border-b border-[var(--hairline)] px-4 py-3 flex items-center justify-between sticky top-0 z-50">
        <a href="/" className="text-lg font-display font-semibold text-[var(--ink)] hover:text-[var(--gold)] transition-colors">
          VALAC Joyas
        </a>
        <a href="/" className="text-sm text-[var(--mute)] hover:text-[var(--gold)] transition-colors flex items-center gap-1">
          ← Volver a la tienda
        </a>
      </div>

      <main className="bg-[var(--bg-page)] text-[var(--ink)]">
        {/* ───────── HERO ───────── */}
        <section className="relative w-full overflow-hidden" style={{ height: "min(48vh, 480px)" }}>
          <img
            src={heroImg}
            alt="Anillo de compromiso VALAC en oro real"
            className="absolute inset-0 w-full h-full object-cover object-center"
            width={1600}
            height={900}
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to top, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.35) 50%, rgba(0,0,0,0.15) 100%)",
            }}
          />
          <div className="relative z-10 h-full flex flex-col items-center justify-end text-center px-4 pb-10 max-w-3xl mx-auto">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--gold-light)] mb-3">
              VALAC · Colección Compromiso
            </div>
            <h1 className="font-display text-3xl sm:text-4xl md:text-5xl text-white leading-tight font-semibold">
              El anillo que merece <em className="font-accent italic font-normal">su historia</em>
            </h1>
            <p className="mt-3 font-accent italic text-base sm:text-lg text-white/85 max-w-xl">
              Diseñado contigo, paso a paso. Oro real 10k y 14k, hecho a mano en México.
            </p>
            <a
              href="#configurador"
              aria-label="Comenzar a diseñar mi anillo"
              className="btn-cta inline-block mt-6 px-8 py-3.5"
            >
              Comenzar mi diseño →
            </a>
          </div>
        </section>

        {/* ───────── CONFIGURADOR (FULL WIDTH) ───────── */}
        <section id="configurador" className="max-w-3xl mx-auto px-4 sm:px-6 py-12 md:py-16">
          <div className="text-center mb-8 fade-on-scroll">
            <span className="label-eyebrow">El configurador VALAC</span>
            <h2 className="font-display text-3xl sm:text-4xl text-[var(--ink)] mt-2 font-semibold">
              Crea el anillo que solo existe para <em className="font-accent italic font-normal">ustedes</em>
            </h2>
            <p className="font-accent italic text-base sm:text-lg text-[var(--mute)] mt-2">
              Siete pasos. Una pieza única. Cero compromisos.
            </p>
          </div>

          <div className="fade-on-scroll">
            <Configurator onSelectionsChange={handleChange} onRequestQuote={handleRequestQuote} />
          </div>
        </section>

        {/* ───────── TRUST BADGES ───────── */}
        <section className="max-w-5xl mx-auto px-4 pb-12 fade-on-scroll">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { t: "Oro real certificado", d: "Sin chapados, sin relleno. Solo oro puro 10k y 14k." },
              { t: "Diseño a tu medida", d: "Trabajamos tu visión. Cada pieza es única e irrepetible." },
              { t: "Cotización en 24h", d: "Hablamos contigo, sin presión, con pasión." },
            ].map((p) => (
              <div
                key={p.t}
                className="bg-white rounded-lg p-5 flex items-start gap-3"
                style={{ borderLeft: "4px solid var(--gold)", boxShadow: "0 2px 10px rgba(31,41,55,0.04)" }}
              >
                <SparkIcon />
                <div>
                  <h3 className="text-base font-semibold font-sans text-[var(--ink)]">{p.t}</h3>
                  <p className="text-sm text-[var(--mute)] mt-1 leading-relaxed">{p.d}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ───────── ANILLOS LISTOS (CAROUSEL) ───────── */}
        <section className="max-w-7xl mx-auto px-4 py-12 fade-on-scroll">
          <div className="text-center mb-8">
            <span className="label-eyebrow">Disponibles ahora</span>
            <h2 className="font-display text-3xl sm:text-4xl text-[var(--ink)] mt-2 font-semibold">
              ¿Prefieres elegir uno <em className="font-accent italic font-normal">listo</em>?
            </h2>
            <p className="font-accent italic text-base sm:text-lg text-[var(--mute)] mt-2">
              Descubre nuestros anillos disponibles para envío inmediato
            </p>
          </div>

          <div className="overflow-x-auto no-scrollbar -mx-4 px-4 pb-2">
            <div className="flex gap-4 snap-x snap-mandatory" style={{ scrollPaddingLeft: "16px" }}>
              {PRODUCTS.map((p) => (
                <article
                  key={p.name}
                  className="snap-start shrink-0 w-[260px] sm:w-[280px] bg-white rounded-xl border border-[var(--gold-soft)] overflow-hidden hover:shadow-[0_8px_24px_rgba(213,163,0,0.15)] transition-shadow"
                >
                  <div className="relative aspect-square bg-[var(--ivory)]">
                    <img
                      src={p.img}
                      alt={p.name}
                      loading="lazy"
                      width={800}
                      height={800}
                      className="absolute inset-0 w-full h-full object-cover"
                    />
                    <span className="absolute top-2 left-2 text-[9px] font-semibold uppercase tracking-wider bg-white text-[var(--ink)] border border-[var(--gold-soft)] rounded-full px-2 py-0.5">
                      Envío gratis
                    </span>
                  </div>
                  <div className="p-4">
                    <h3 className="text-sm font-semibold text-[var(--ink)] leading-tight font-sans">
                      {p.name}
                    </h3>
                    <p className="mt-1.5 font-display text-lg text-[var(--ink)] font-semibold">
                      ${p.price.toLocaleString("es-MX")}{" "}
                      <span className="text-xs text-[var(--mute)] font-sans font-normal">MXN</span>
                    </p>
                    <button
                      type="button"
                      className="mt-3 w-full text-xs font-semibold uppercase tracking-wider py-2 rounded-lg border border-[var(--ink)] text-[var(--ink)] hover:bg-[var(--ink)] hover:text-[var(--gold)] transition-colors"
                    >
                      Ver detalles
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="mt-6 text-center">
            <a
              href="#"
              className="text-sm font-semibold text-[var(--gold)] hover:text-[var(--gold-hover)] transition-colors"
            >
              Ver todos los anillos →
            </a>
          </div>
        </section>

        {/* ───────── CTA FINAL ───────── */}
        <section className="max-w-7xl mx-auto px-4 pb-14">
          <div
            className="rounded-2xl px-6 py-12 sm:py-14 text-center fade-on-scroll relative overflow-hidden"
            style={{
              background: "linear-gradient(135deg, #1f2937 0%, #2a3340 100%)",
            }}
          >
            <div
              className="absolute inset-0 opacity-30 pointer-events-none"
              style={{
                background:
                  "radial-gradient(circle at 20% 20%, rgba(213,163,0,0.4), transparent 50%), radial-gradient(circle at 80% 80%, rgba(250,204,21,0.25), transparent 50%)",
              }}
            />
            <div className="relative">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--gold-light)]">
                El momento más importante
              </span>
              <h2 className="font-display text-3xl sm:text-4xl md:text-5xl text-white mt-3 font-semibold">
                ¿Listo para el <em className="font-accent italic font-normal text-[var(--gold-light)]">momento</em>?
              </h2>
              <p className="mt-3 font-accent italic text-base sm:text-lg text-white/80 max-w-md mx-auto">
                Habla con un asesor VALAC. Sin presión, con pasión.
              </p>
              <a
                href={buildWaUrl()}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Escríbenos por WhatsApp"
                className="inline-flex items-center gap-2 mt-7 rounded-lg px-8 py-3.5 text-sm uppercase tracking-wider font-bold transition-all"
                style={{ background: "var(--whatsapp)", color: "#fff" }}
              >
                <WhatsAppIcon />
                Escríbenos por WhatsApp
              </a>
              <p className="mt-4 text-xs text-white/60">
                Respondemos en menos de 2 horas · Lun a Sáb 9am–8pm
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor" aria-hidden="true">
      <path d="M.057 24l1.687-6.163a11.867 11.867 0 01-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 018.413 3.488 11.824 11.824 0 013.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 01-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 001.594 5.355l-.999 3.648 3.894-1.702zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-6 h-6 shrink-0 text-[var(--gold)]" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" strokeLinejoin="round"/>
    </svg>
  );
}
