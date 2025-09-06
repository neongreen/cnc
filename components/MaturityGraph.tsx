"use client"

import { useEffect, useRef } from "react"
import { drawGraph, type GraphData } from "../lib/graphDrawing"

export default function MaturityGraph({
  graphData,
  levelsData,
  graphHeight,
}: {
  graphData: GraphData
  levelsData: string[][]
  graphHeight: number
}) {
  const svgRef = useRef<SVGSVGElement | null>(null)

  useEffect(() => {
    if (graphData && levelsData && svgRef.current) {
      try {
        drawGraph(svgRef.current, graphData, graphHeight, levelsData)
      } catch (error) {
        console.error("Error drawing maturity graph:", error)
        const svg = svgRef.current
        svg.innerHTML = ""
        const text = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "text",
        )
        text.setAttribute("x", "50%")
        text.setAttribute("y", "50%")
        text.setAttribute("text-anchor", "middle")
        text.setAttribute("dominant-baseline", "middle")
        text.setAttribute("fill", "#ff0000")
        text.setAttribute("font-size", "18px")
        text.textContent = "Error rendering graph"
        svg.appendChild(text)
      }
    }
  }, [graphData, levelsData, graphHeight])

  return (
    <svg
      ref={svgRef}
      id="graph-svg"
      style={{ border: "1px solid #ccc", width: "100%" }}
    />
  )
}
