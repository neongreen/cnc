import { defineConfig } from "vitest/config"

export default defineConfig({
  test: {
    includeSource: ["./lib/**/*.{ts,tsx}"],
    coverage: {
      provider: "v8",
    },
  },
})
