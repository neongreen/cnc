/**
 * Copyright (c) 2025 Emily
 *
 * This work is licensed under the Creative Commons Zero v1.0 Universal License.
 *
 * To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
 *
 * You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
 */

import * as d3 from "https://esm.sh/d3"

/**
 * @typedef {object} Node
 * @property {string} id - The unique identifier for the node.
 * @property {string} name - The name of the node.
 * @property {boolean} [inactive] - Whether the player is inactive.
 * @property {number} x - The x-coordinate of the node.
 * @property {number} y - The y-coordinate of the node.
 * @property {number} fx - The fixed x-coordinate of the node.
 * @property {number} fy - The fixed y-coordinate of the node.
 */

/**
 * @typedef {object} Edge
 * @property {Node} source - The source node object.
 * @property {Node} target - The target node object.
 * @property {number} [index] - The optional index, assigned by D3.
 */

/**
 * @typedef {object} GraphData
 * @property {Array<Node>} nodes - An array of node objects.
 * @property {Array<Edge>} edges - An array of edge objects.
 * @property {Array<{source: string, target: string}>} [ties] - Optional array of tie edges.
 */

/**
 * Darkens a hex color by a given percentage.
 * @param {string} hex - The color in hex format (e.g., "#rrggbb").
 * @param {number} percent - The fraction to darken (0 to 1).
 * @returns {string} The darkened hex color.
 */
function darkenColor(hex, percent) {
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
 * @param {d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>} svg - The D3 SVG selection.
 * @param {string} id - The marker ID.
 * @param {string} color - Fill color for the arrowhead.
 * @param {number} arrowSize - Size of the arrow marker.
 */
function createArrowhead(svg, id, color, arrowSize) {
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
 * @param {d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>} svg - The D3 SVG container.
 * @param {GraphData} graphData - The graph data object.
 * @param {Map<string, string>} nodeColors - Map of node ID to fill color.
 * @param {number} radius - Radius for each node circle.
 */
function drawNodesAndLabels(svg, graphData, nodeColors, radius) {
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(graphData.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", radius)
    .attr("fill", (d) => (d.inactive ? "#cccccc" : trust(nodeColors.get(d.id))))
    .attr("stroke", (d) =>
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
    .attr("fill", (d) => (d.inactive ? "#666666" : "#000000"))
    .text((d) => d.name)

  node.attr("cx", (d) => d.x).attr("cy", (d) => d.y)
  nodeText.attr("x", (d) => d.x).attr("y", (d) => d.y)
}

/**
 * Draws directed edges with arrowheads and angled paths to avoid overlap.
 * @param {d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>} svg - The D3 SVG container.
 * @param {GraphData} graphData - The graph data containing nodes and edges.
 * @param {Map<string, string>} nodeColors - Map of node ID to color.
 * @param {number} radius - Radius of node circles.
 * @param {number} arrowSize - Size of the arrow marker.
 * @param {number} arrowheadAdjustment - Additional offset for arrow placement.
 */
function drawDirectedEdges(
  svg,
  graphData,
  nodeColors,
  radius,
  arrowSize,
  arrowheadAdjustment
) {
  console.log("Creating edges...")
  // Create arrowheads for each edge
  graphData.edges.forEach((edge) => {
    const color = darkenColor(trust(nodeColors.get(edge.source.id)), 0.2)
    const id = `arrowhead-${edge.index}`
    console.log(
      `Processing edge: Source=${edge.source.id}, Target=${edge.target.id}, Arrowhead ID=${id}`
    )
    createArrowhead(svg, id, color, arrowSize)
  })

  /** @type {typeof d3.linkHorizontal<unknown, Node> } */
  const d3_linkHorizontal = d3.linkHorizontal

  // Draw edge paths
  svg
    .append("g")
    .selectAll("path.edge")
    .data(graphData.edges)
    .enter()
    .append("path")
    .attr("class", "edge")
    .attr("stroke", (d) => darkenColor(trust(nodeColors.get(d.source.id)), 0.2))
    .attr("marker-end", (d) => `url(#arrowhead-${d.index})`)
    .attr("d", (d) =>
      d3_linkHorizontal()
        .x((p) => p.x)
        .y((p) => p.y)(
        computeEdgeCoordinates(
          d,
          graphData.edges,
          radius,
          arrowSize,
          arrowheadAdjustment
        )
      )
    )
}

/**
 * Compute offset source and target points for an edge to avoid overlap.
 * @param {Edge} edge - The edge with source and target nodes.
 * @param {Array<Edge>} edges - All edges in the graph.
 * @param {number} radius - Radius of the node circles.
 * @param {number} arrowSize - Size of the arrow marker.
 * @param {number} arrowheadAdjustment - Extra offset for arrowheads.
 * @returns {{source:{x:number,y:number}, target:{x:number,y:number}}}
 */
function computeEdgeCoordinates(
  edge,
  edges,
  radius,
  arrowSize,
  arrowheadAdjustment
) {
  const sourceEdges = edges
    .filter((e) => e.source === edge.source)
    .sort((a, b) => a.target.y - b.target.y)
  const targetEdges = edges
    .filter((e) => e.target === edge.target)
    .sort((a, b) => b.source.y - a.source.y)
  /**
   * @param {number} i
   * @param {number} total
   */
  function angle(i, total) {
    return (((i - (total - 1) / 2) / total) * Math.PI) / 2
  }
  const sourceAngle = angle(
    sourceEdges.findIndex((e) => e.target === edge.target),
    sourceEdges.length
  )
  const targetAngle = angle(
    targetEdges.findIndex((e) => e.source === edge.source),
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
 * @param {d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>} svg - The D3 SVG container.
 * @param {GraphData} graphData - The graph data with tie edge info.
 * @param {number} radius - Radius of node circles for offset calculations.
 */
function drawTieEdges(svg, graphData, radius) {
  console.log("Creating tie edges...")
  const tieLinks = (graphData.ties || [])
    .map((t) => ({
      source: graphData.nodes.find((n) => n.id === t.source),
      target: graphData.nodes.find((n) => n.id === t.target),
    }))
    .filter((link) => link.source && link.target)
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
      const s = trust(d.source),
        t = trust(d.target)
      const dx = t.x - s.x,
        dy = t.y - s.y
      const dist = Math.hypot(dx, dy)
      const ux = dx / dist,
        uy = dy / dist
      const start = { x: s.x + radius * ux, y: s.y + radius * uy }
      const end = { x: t.x - radius * ux, y: t.y - radius * uy }
      return `M${start.x},${start.y}L${end.x},${end.y}`
    })
}

/**
 * Computes node positions and assigns colors based on hierarchical levels.
 * @param {Array<Array<string>>} levels - Topological levels of node IDs.
 * @param {number} width - Available width for layout.
 * @param {number} height - Available height for layout.
 * @param {Array<string>} palette - Array of colors for levels.
 * @param {Set<string>} inactiveSet - Set of node IDs that are inactive.
 * @param {number} radius - Node radius in pixels.
 * @returns {{nodePositions: Map<string,{x:number,y:number}>, nodeColors: Map<string,string>}}
 */
function computeNodeLayout(
  levels,
  width,
  height,
  palette,
  inactiveSet,
  radius
) {
  const nodePositions = new Map()
  const nodeColors = new Map()
  levels.forEach((level, levelIndex) => {
    const x = (levelIndex + 0.5) * (width / levels.length)
    const activeIds = level.filter((id) => !inactiveSet.has(id))
    const inactiveIds = level.filter((id) => inactiveSet.has(id))

    const activeCount = activeIds.length
    const inactiveCount = inactiveIds.length

    // 1) Place actives as if only they existed (true centering)
    let maxActiveY = 0
    if (activeCount > 0) {
      const stepActive = height / activeCount
      activeIds.forEach((nodeName, nodeIndex) => {
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
      inactiveIds.forEach((nodeName, j) => {
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
 * @param {string} selector - CSS selector for the SVG element.
 * @param {number} height - Desired SVG height.
 * @returns {{svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>, width: number, height: number}}
 */
function initSVG(selector, height) {
  /** @type {d3.Selection<SVGSVGElement, unknown, HTMLElement, undefined>} */
  const svg = d3.select(selector)
  const width = Math.max(
    trust(document.querySelector("table")).offsetWidth,
    // deno-lint-ignore no-window
    window.innerWidth - 40
  )
  svg
    .attr("width", width)
    .attr("height", height)
    .style("width", width + "px")
  return { svg, width, height }
}

/**
 * Fix node coordinates to computed positions.
 * @param {Array<Node>} nodes - Graph nodes.
 * @param {Map<string, {x:number,y:number}>} nodePositions - Map of node IDs to positions.
 */
function setFixedPositions(nodes, nodePositions) {
  console.log("Setting fixed positions for nodes...")
  nodes.forEach((node) => {
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
function forceLinks(nodes, edges) {
  /** @type {typeof d3.forceLink<Node, Edge>} */
  const d3_forceLink = d3.forceLink

  d3.forceSimulation(nodes)
    .force(
      "link",
      d3_forceLink(edges)
        .id((d) => d.id)
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
export function drawGraph(graphData, graphHeight, levels) {
  console.log("drawGraph called with:", { graphData, graphHeight, levels })
  const { svg, width, height } = initSVG("#graph-svg", graphHeight)
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
    graphData.nodes.filter((n) => n.inactive).map((n) => n.id)
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
function trust(value) {
  if (value === undefined || value === null) {
    throw new Error(`Expected a value, but got ${value}.`)
  }
  return value
}
