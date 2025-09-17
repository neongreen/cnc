import { ReactNode } from "react"

import HiveThemeWatcher from "./HiveThemeWatcher"
import Tabs from "./Tabs"

export default function HiveLayout({ children }: { children: ReactNode }) {
  return (
    <div className="w-[100vw] m-0 bg-background text-foreground rounded-none shadow-none overflow-visible">
      <HiveThemeWatcher />
      <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-purple-600 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900 text-white p-[30px] text-center shadow-sm">
        <h1 className="m-0 text-[2.5em] font-light">🐝 Hive</h1>
      </div>
      <div className="p-5">
        <Tabs />
        {children}
      </div>
    </div>
  )
}
