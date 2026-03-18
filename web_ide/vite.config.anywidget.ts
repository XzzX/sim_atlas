import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./js"),
    },
  },
  build: {
    outDir: "src/simflow/static",
    lib: {
      entry: ["js/widget.tsx"],
      formats: ["es"],
    },
  },
  define: {
    "process.env": {},
  },
});