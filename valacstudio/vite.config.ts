import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  // In production the built files live under Flask's /static/studio/
  base: mode === "production" ? "/static/studio/" : "/",
  build: {
    outDir: "../static/studio",
    emptyOutDir: false,          // keep bases/ folder intact
  },
  server: {
    host: "::",
    port: 8080,
    hmr: { overlay: false },
    proxy: {
      // API calls → Flask dev server
      "/admin/studio/generate": "http://localhost:5000",
      "/admin/studio/products": "http://localhost:5000",
      "/admin/studio/save": "http://localhost:5000",
      // Base images served by Flask
      "/static/studio/bases": "http://localhost:5000",
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "@tanstack/react-query", "@tanstack/query-core"],
  },
}));
