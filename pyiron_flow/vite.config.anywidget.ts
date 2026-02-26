import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import anywidget from "@anywidget/vite";

export default defineConfig({
  plugins: [tailwindcss(), anywidget()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "hello_widget/static",
    lib: {
      entry: ["src/widget.tsx"],
      formats: ["es"],
    },
  },
  define: {
    "process.env": {},
  },
});