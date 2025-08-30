import Link from "next/link"
import { ReactNode } from "react"
import { cn } from "@/lib/utils"
import Tabs from "./Tabs"

export default function HiveLayout({ children }: { children: ReactNode }) {
  return (
    <div className="w-[100vw] m-0 bg-white rounded-none shadow-none overflow-visible">
      <div className="bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] text-white p-[30px] text-center">
        <h1 className="m-0 text-[2.5em] font-light">🐝 Hive</h1>
      </div>
      <div className="p-5">
        <Tabs />
        {children}
      </div>
    </div>
  )
}
