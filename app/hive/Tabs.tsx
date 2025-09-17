"use client"

import { cn } from "@/lib/utils"
import Link from "next/link"
import { usePathname } from "next/navigation"

export default function Tabs() {
  const pathname = usePathname()
  const isMain = pathname === "/hive" || pathname === "/hive/"
  const isRecent = pathname?.startsWith("/hive/recent")

  return (
    <div className="flex justify-center gap-4 mb-6">
      <Link
        href="/hive"
        className={cn(
          "px-4 py-2 rounded font-medium transition-colors",
          isMain
            ? "bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-100"
            : "bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800/60 dark:hover:bg-gray-700/60 dark:text-gray-200",
        )}
      >
        Player stats
      </Link>
      <Link
        href="/hive/recent"
        className={cn(
          "px-4 py-2 rounded font-medium transition-colors",
          isRecent
            ? "bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-100"
            : "bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800/60 dark:hover:bg-gray-700/60 dark:text-gray-200",
        )}
      >
        Recent games
      </Link>
    </div>
  )
}
