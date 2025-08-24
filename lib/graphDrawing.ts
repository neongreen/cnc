/**
 * Copyright (c) 2025 Emily
 *
 * This work is licensed under the Creative Commons Zero v1.0 Universal License.
 *
 * To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
 *
 * You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
 */

import * as d3 from "d3"

import "./graph.css"

export type Node = {
  id: string
  name: string
  inactive?: boolean
  x: number
  y: number
  fx: number
  fy: number
}

type Edge = {
  source: Node
  target: Node
  index?: number
}

interface XY {
  x: number
  y: number
}

export type GraphData = {
  nodes: Node[]
  edges: Edge[]
  ties?: { source: string; target: string }[]
}

/**
 * Darkens a hex color by a given percentage.
 * @param {string} hex - The color in hex format (e.g., "#rrggbb").
 * @param {number} percent - The fraction to darken (0 to 1).
 * @returns {string} The darkened hex color.
 */
function darkenColor(hex: string, percent: number): string {
  const f = parseInt(hex.slice(1), 16)
  let R = f >> 16,
    G = (f >> 8) & 0x00ff,
    B = f & 0x0000ff

  R = Math.round(R * (1 - percent))
  G = Math.round(G * (1 - percent))
  B = Math.round(B * (1 - percent))

  return "#" + ((1 << 24) + (R << 16) + (G << 8) + B).toString(16).slice(1)
}

/**
 * Creates a unique arrowhead marker in the SVG defs.
 */
function createArrowhead(
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
  id: string,
  color: string,
  arrowSize: number
): void {
  svg
    .append("defs")
    .append("marker")
    .attr("id", id)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 0)
    .attr("refY", 0)
    .attr("markerWidth", arrowSize)
    .attr("markerHeight", arrowSize)
    .attr("orient", "auto")
    .append("path")
    .attr("class", "arrowhead")
    .attr("fill", color)
    .attr("d", "M0,-5L10,0L0,5")
}

/**
 * Renders node circles and labels on the SVG.
 */
function drawNodesAndLabels(
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
  graphData: GraphData,
  nodeColors: Map<string, string>,
  radius: number
): void {
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(graphData.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", radius)
    .attr("fill", (d: Node) =>
      d.inactive ? "#cccccc" : trust(nodeColors.get(d.id))
    )
    .attr("stroke", (d: Node) =>
      d.inactive
        ? darkenColor("#cccccc", 0.2)
        : darkenColor(trust(nodeColors.get(d.id)), 0.2)
    )

  const nodeText = svg
    .append("g")
    .selectAll("text")
    .data(graphData.nodes)
    .enter()
    .append("text")
    .attr("class", "node-text")
    .attr("fill", (d: Node) => (d.inactive ? "#666666" : "#000000"))
    .text((d: Node) => d.name)

  node.attr("cx", (d: Node) => d.x).attr("cy", (d: Node) => d.y)
  nodeText.attr("x", (d: Node) => d.x).attr("y", (d: Node) => d.y)
}

/**
 * Draws directed edges with arrowheads and angled paths to avoid overlap.
 */
function drawDirectedEdges(
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
  graphData: GraphData,
  nodeColors: Map<string, string>,
  radius: number,
  arrowSize: number,
  arrowheadAdjustment: number
): void {
  console.log("Creating edges...")
  // Create arrowheads for each edge
  graphData.edges.forEach((edge: Edge) => {
    const color = darkenColor(trust(nodeColors.get(edge.source.id)), 0.2)
    const id = `arrowhead-${edge.index}`
    console.log(
      `Processing edge: Source=${edge.source.id}, Target=${edge.target.id}, Arrowhead ID=${id}`
    )
    createArrowhead(svg, id, color, arrowSize)
  })

  const d3_linkHorizontal: () => d3.Link<any, { source: XY; target: XY }, XY> =
    d3.linkHorizontal

  // Draw edge paths
  svg
    .append("g")
    .selectAll("path.edge")
    .data(graphData.edges)
    .enter()
    .append("path")
    .attr("class", "edge")
    .attr("stroke", (d: Edge) =>
      darkenColor(trust(nodeColors.get(d.source.id)), 0.2)
    )
    .attr("marker-end", (d: Edge) => `url(#arrowhead-${d.index})`)
    .attr("d", (d: Edge) => {
      const coords: {
        source: XY
        target: XY
      } = computeEdgeCoordinates(
        d,
        graphData.edges,
        radius,
        arrowSize,
        arrowheadAdjustment
      )
      return d3_linkHorizontal()
        .x((p: XY) => p.x)
        .y((p: XY) => p.y)(coords)
    })
}

/**
 * Compute offset source and target points for an edge to avoid overlap.
 */
function computeEdgeCoordinates(
  edge: Edge,
  edges: Edge[],
  radius: number,
  arrowSize: number,
  arrowheadAdjustment: number
): { source: XY; target: XY } {
  const sourceEdges = edges
    .filter((e: Edge) => e.source === edge.source)
    .sort((a: Edge, b: Edge) => a.target.y - b.target.y)
  const targetEdges = edges
    .filter((e: Edge) => e.target === edge.target)
    .sort((a: Edge, b: Edge) => b.source.y - a.source.y)

  function angle(i: number, total: number): number {
    return (((i - (total - 1) / 2) / total) * Math.PI) / 2
  }

  const sourceAngle = angle(
    sourceEdges.findIndex((e: Edge) => e.target === edge.target),
    sourceEdges.length
  )
  const targetAngle = angle(
    targetEdges.findIndex((e: Edge) => e.source === edge.source),
    targetEdges.length
  )
  return {
    source: {
      x: edge.source.x + radius * Math.cos(sourceAngle),
      y: edge.source.y + radius * Math.sin(sourceAngle),
    },
    target: {
      x:
        edge.target.x -
        (radius + arrowSize + arrowheadAdjustment) * Math.cos(targetAngle),
      y:
        edge.target.y -
        (radius + arrowSize + arrowheadAdjustment) * Math.sin(targetAngle),
    },
  }
}

/**
 * Draws tie edges as dashed lines between nodes that tied.
 */
function drawTieEdges(
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
  graphData: GraphData,
  radius: number
): void {
  console.log("Creating tie edges...")
  const tieLinks = (graphData.ties || [])
    .map((t: { source: string; target: string }) => ({
      source: graphData.nodes.find((n: Node) => n.id === t.source),
      target: graphData.nodes.find((n: Node) => n.id === t.target),
    }))
    .filter(
      (link: { source: Node | undefined; target: Node | undefined }) =>
        link.source && link.target
    )
  svg
    .append("g")
    .selectAll("path.tie")
    .data(tieLinks)
    .enter()
    .append("path")
    .attr("class", "tie")
    .attr("stroke", "#999")
    .attr("stroke-dasharray", "4,2")
    .attr("stroke-width", 3)
    .attr("fill", "none")
    .attr("d", (d) => {
      const [s, t] = [trust(d.source), trust(d.target)]
      const [dx, dy] = [t.x - s.x, t.y - s.y]
      const dist = Math.hypot(dx, dy)
      const [ux, uy] = [dx / dist, dy / dist]
      const start = { x: s.x + radius * ux, y: s.y + radius * uy }
      const end = { x: t.x - radius * ux, y: t.y - radius * uy }
      return `M${start.x},${start.y}L${end.x},${end.y}`
    })
}

/**
 * Computes node positions and assigns colors based on hierarchical levels.
 * @param levels - Topological levels of node IDs.
 * @param width - Available width for layout.
 * @param height - Available height for layout.
 * @param palette - Array of colors for levels.
 * @param inactiveSet - Set of node IDs that are inactive.
 * @param radius - Node radius in pixels.
 */
function computeNodeLayout(
  levels: string[][],
  width: number,
  height: number,
  palette: string[],
  inactiveSet: Set<string>,
  radius: number
): {
  nodePositions: Map<string, XY>
  nodeColors: Map<string, string>
} {
  const nodePositions = new Map<string, XY>()
  const nodeColors = new Map<string, string>()
  levels.forEach((level: string[], levelIndex: number) => {
    const x = (levelIndex + 0.5) * (width / levels.length)
    const activeIds = level.filter((id: string) => !inactiveSet.has(id))
    const inactiveIds = level.filter((id: string) => inactiveSet.has(id))

    const activeCount = activeIds.length
    const inactiveCount = inactiveIds.length

    // 1) Place actives as if only they existed (true centering)
    let maxActiveY = 0
    if (activeCount > 0) {
      const stepActive = height / activeCount
      activeIds.forEach((nodeName: string, nodeIndex: number) => {
        const y = (nodeIndex + 0.5) * stepActive
        nodePositions.set(nodeName, { x, y })
        nodeColors.set(nodeName, palette[levelIndex % palette.length])
        if (y > maxActiveY) maxActiveY = y
      })
    }

    // 2) Place inactives glued to the bottom of the graph, stacked upward
    if (inactiveCount > 0) {
      const yFloor = height - radius - 4
      const spacing = radius * 2 + 8
      inactiveIds.forEach((nodeName: string, j: number) => {
        const y = yFloor - j * spacing
        nodePositions.set(nodeName, { x, y })
        nodeColors.set(nodeName, palette[levelIndex % palette.length])
      })
    }
  })
  return { nodePositions, nodeColors }
}

/**
 * Initialize and size the SVG container.
 */
function initSVG(
  svgNode: SVGSVGElement,
  height: number
): {
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
  width: number
  height: number
} {
  const svg = d3.select(svgNode)
  const width = Math.max(
    trust(document.querySelector("table")).offsetWidth,
    window.innerWidth - 40
  )
  // Match original behavior: set intrinsic SVG viewport via attributes.
  // Keep CSS width for responsiveness, but avoid setting CSS height.
  svg
    .attr("width", width)
    .attr("height", height)
    .style("width", width + "px")
  return { svg, width, height }
}

/**
 * Fix node coordinates to computed positions.
 * @param nodes - Graph nodes.
 * @param nodePositions - Map of node IDs to positions.
 */
function setFixedPositions(
  nodes: Node[],
  nodePositions: Map<string, XY>
): void {
  console.log("Setting fixed positions for nodes...")
  nodes.forEach((node: Node) => {
    const pos = nodePositions.get(node.id)
    if (pos) {
      node.x = pos.x
      node.y = pos.y
      node.fx = pos.x
      node.fy = pos.y
    }
  })
}

/**
 * Setup a force simulation for links, then stop (nodes are fixed).
 * @param {Array<Node>} nodes - Graph nodes.
 * @param {Array<Edge>} edges - Graph edges.
 */
function forceLinks(nodes: Node[], edges: Edge[]): void {
  const d3_forceLink = d3.forceLink

  d3.forceSimulation(nodes)
    .force(
      "link",
      d3_forceLink(edges)
        .id((d: d3.SimulationNodeDatum) => (d as Node).id)
        .distance(100)
        .strength(0)
    )
    .stop()
}

/**
 * Draws a graph using D3.js.
 * @param {GraphData} graphData - The graph data.
 * @param {number} graphHeight - The height of the graph SVG.
 * @param {Array<Array<string>>} levels - An array of arrays, where each inner array represents a level of nodes in the graph.
 */
export function drawGraph(
  svgNode: SVGSVGElement,
  graphData: GraphData,
  graphHeight: number,
  levels: string[][]
): void {
  console.log("drawGraph called with:", { graphData, graphHeight, levels })
  const { svg, width, height } = initSVG(svgNode, graphHeight)
  console.log("SVG dimensions:", { width, height })

  const radius = 34 // Radius for nodes
  const arrowSize = 5 // Size of the arrow marker
  const arrowheadAdjustment = 6 // Arrowheads shouldn't overlap with the node circles

  const colorPalette = [
    "#ff3d3d", // red
    "#ffb72a", // orange
    "#e0e000", // yellow
    "#4bde3c", // green
    "#25bfe2", // light blue
    "#317de9", // blue
    "#4a3c95", // purple
    "#a55b99", // pink/purple
    "#6a3f42", // brown-ish
    "#353f50", // blueish gray
  ]
  console.log("Calculating node positions...")
  const inactiveSet = new Set(
    graphData.nodes.filter((n: Node) => n.inactive).map((n: Node) => n.id)
  )
  const { nodePositions, nodeColors } = computeNodeLayout(
    levels,
    width,
    height,
    colorPalette,
    inactiveSet,
    radius
  )

  setFixedPositions(graphData.nodes, nodePositions)

  forceLinks(graphData.nodes, graphData.edges)

  drawDirectedEdges(
    svg,
    graphData,
    nodeColors,
    radius,
    arrowSize,
    arrowheadAdjustment
  )

  drawTieEdges(svg, graphData, radius)

  drawNodesAndLabels(svg, graphData, nodeColors, radius)
}

/**
 * Throwing an error if the value is undefined.
 *
 * @template T
 * @param {T | undefined | null} value
 * @returns {T}
 */
function trust<T>(value: T | undefined | null): T {
  if (value === undefined || value === null) {
    throw new Error(`Expected a value, but got ${value}.`)
  }
  return value
}
