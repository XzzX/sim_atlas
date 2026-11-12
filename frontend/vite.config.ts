import type { ViteUserConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vitejs.dev/config/
export default {
  plugins: [react(), tailwindcss()],
  resolve: {
    // Keep the symlinked sim-atlas-api-schema under node_modules so its zod
    // import resolves to this app's copy (ADR-0027).
    preserveSymlinks: true,
    alias: {
      "@": "/src",
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ide": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
} satisfies ViteUserConfig;
