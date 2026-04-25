import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig(({ mode }) => ({
  base: mode === "production" ? "/static/anillos-compromiso/" : "/",
  build: {
    outDir: "../static/anillos-compromiso",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/configurador.js",
        assetFileNames: (info) => {
          if (info.names?.[0]?.endsWith(".css")) return "assets/configurador.css";
          return "assets/[name]-[hash][extname]";
        },
      },
    },
  },
  server: {
    host: "::",
    port: 8081,
    hmr: { overlay: false },
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
