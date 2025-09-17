"use client"

import { useEffect } from "react"

/**
 * Keeps the Hive pages in sync with the user's preferred color scheme.
 *
 * When mounted we apply the system preference and listen for changes.
 * On unmount we restore the previous dark-mode state so that other routes
 * are unaffected by the Hive pages' automatic theming.
 */
export default function HiveThemeWatcher() {
  useEffect(() => {
    if (typeof window === "undefined") return

    const root = document.documentElement
    const hadDarkClass = root.classList.contains("dark")
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")

    const applyTheme = () => {
      if (mediaQuery.matches) root.classList.add("dark")
      else root.classList.remove("dark")
    }

    applyTheme()
    mediaQuery.addEventListener("change", applyTheme)

    return () => {
      mediaQuery.removeEventListener("change", applyTheme)
      if (hadDarkClass) root.classList.add("dark")
      else root.classList.remove("dark")
    }
  }, [])

  return null
}
