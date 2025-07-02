import * as d3 from "https://esm.sh/d3"

/**
 * @typedef {object} Node
 * @property {string} id - The unique identifier for the node.
 * @property {string} name - The name of the node.
 * @property {number} x - The x-coordinate of the node.
 * @property {number} y - The y-coordinate of the node.
 * @property {number} fx - The fixed x-coordinate of the node.
 * @property {number} fy - The fixed y-coordinate of the node.
 */

/**
 * @typedef {object} Edge
 * @property {string} source - The source node ID of the edge.
 * @property {string} target - The target node ID of the edge.
 */

/**
 * @typedef {object} GraphData
 * @property {Array<Node>} nodes - An array of node objects.
 * @property {Array<Edge>} edges - An array of edge objects.
 */

/**
 * Draws a graph using D3.js.
 * @param {GraphData} graphData - The graph data.
 * @param {number} graphHeight - The height of the graph SVG.
 * @param {Array<Array<string>>} levels - An array of arrays, where each inner array represents a level of nodes in the graph.
 */

function darkenColor(hex, percent) {
  let f = parseInt(hex.slice(1), 16),
    R = f >> 16,
    G = (f >> 8) & 0x00ff,
    B = f & 0x0000ff

  R = Math.round(R * (1 - percent))
  G = Math.round(G * (1 - percent))
  B = Math.round(B * (1 - percent))

  return "#" + ((1 << 24) + (R << 16) + (G << 8) + B).toString(16).slice(1)
}

// Create a unique arrowhead marker for a given id, color, and size
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

// Render node circles and labels
function drawNodesAndLabels(svg, graphData, nodeColors, radius, darkenColorFn) {
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(graphData.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", radius)
    .attr("fill", (d) => nodeColors.get(d.id))
    .attr("stroke", (d) => darkenColorFn(nodeColors.get(d.id), 0.2))

  const nodeText = svg
    .append("g")
    .selectAll("text")
    .data(graphData.nodes)
    .enter()
    .append("text")
    .attr("class", "node-text")
    .text((d) => d.name)

  node.attr("cx", (d) => d.x).attr("cy", (d) => d.y)
  nodeText.attr("x", (d) => d.x).attr("y", (d) => d.y)
}

// Draw directed edges including arrowheads and link paths
function drawDirectedEdges(svg, graphData, nodeColors, radius, arrowSize, arrowheadAdjustment, darkenColorFn) {
  console.log("Creating edges...")
  // Create arrowheads for each edge
  graphData.edges.forEach((edge) => {
    const color = darkenColorFn(nodeColors.get(edge.source.id), 0.2)
    const id = `arrowhead-${edge.index}`
    console.log(
      `Processing edge: Source=${edge.source.id}, Target=${edge.target.id}, Arrowhead ID=${id}`
    )
    createArrowhead(svg, id, color, arrowSize)
  })

  // Draw edge paths
  svg
    .append("g")
    .selectAll("path.edge")
    .data(graphData.edges)
    .enter()
    .append("path")
    .attr("class", "edge")
    .attr("stroke", (d) => darkenColorFn(nodeColors.get(d.source.id), 0.2))
    .attr("marker-end", (d) => `url(#arrowhead-${d.index})`)
    .attr("d", (d) =>
      d3
        .linkHorizontal()
        .x((p) => p.x)
        .y((p) => p.y)(
        (() => {
          const edges = graphData.edges
          const sourceEdges = edges
            .filter((e) => e.source === d.source)
            .sort((a, b) => a.target.y - b.target.y)
          const targetEdges = edges
            .filter((e) => e.target === d.target)
            .sort((a, b) => b.source.y - a.source.y)
          const angle = (i, total) => (((i - (total - 1) / 2) / total) * Math.PI) / 2
          const sourceAngle = angle(
            sourceEdges.findIndex((e) => e.target === d.target),
            sourceEdges.length
          )
          const targetAngle = angle(
            targetEdges.findIndex((e) => e.source === d.source),
            targetEdges.length
          )
          return {
            source: {
              x: d.source.x + radius * Math.cos(sourceAngle),
              y: d.source.y + radius * Math.sin(sourceAngle),
            },
            target: {
              x:
                d.target.x -
                (radius + arrowSize + arrowheadAdjustment) *
                  Math.cos(targetAngle),
              y:
                d.target.y -
                (radius + arrowSize + arrowheadAdjustment) *
                  Math.sin(targetAngle),
            },
          }
        })()
      )
    )
}

// Draw tie edges as dashed lines between tied nodes
function drawTieEdges(svg, graphData, radius) {
  console.log("Creating tie edges...")
  const tieLinks = (graphData.ties || []).map((t) => ({
    source: graphData.nodes.find((n) => n.id === t.source),
    target: graphData.nodes.find((n) => n.id === t.target),
  }))
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
      const s = d.source,
        t = d.target
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

// Compute node positions and assign colors based on topological levels
function computeNodeLayout(levels, width, height, palette) {
  const nodePositions = new Map()
  const nodeColors = new Map()
  levels.forEach((level, levelIndex) => {
    const x = (levelIndex + 0.5) * (width / levels.length)
    level.forEach((nodeName, nodeIndex) => {
      const y = (nodeIndex + 0.5) * (height / level.length)
      nodePositions.set(nodeName, { x, y })
      nodeColors.set(nodeName, palette[levelIndex % palette.length])
    })
  })
  return { nodePositions, nodeColors }
}

export function drawGraph(graphData, graphHeight, levels) {
  console.log("drawGraph called with:", { graphData, graphHeight, levels })
  const svg = d3.select("#graph-svg")
  // width same as table width (determined dynamically), or viewport width, whichever is bigger
  const width = Math.max(
    document.querySelector("table").offsetWidth,
    window.innerWidth - 40
  )
  const height = graphHeight
  console.log("SVG dimensions:", { width, height })

  // Set SVG dimensions explicitly and ensure the element itself can extend
  // beyond the viewport when needed.
  svg
    .attr("width", width)
    .attr("height", height)
    .style("width", width + "px")

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
  const { nodePositions, nodeColors } = computeNodeLayout(
    levels,
    width,
    height,
    colorPalette
  )

  // Set fixed positions for nodes
  console.log("Setting fixed positions for nodes...")
  graphData.nodes.forEach((node) => {
    const pos = nodePositions.get(node.id)
    if (pos) {
      node.x = pos.x
      node.y = pos.y
      node.fx = pos.x // Fix x position
      node.fy = pos.y // Fix y position
    }
  })

  // Create a simple simulation just for the links
  d3.forceSimulation(graphData.nodes)
    .force(
      "link",
      d3
        .forceLink(graphData.edges)
        .id((d) => d.id)
        .distance(100)
        .strength(0)
    )
    .stop() // Don't run the simulation, we have fixed positions

  drawDirectedEdges(svg, graphData, nodeColors, radius, arrowSize, arrowheadAdjustment, darkenColor)

  drawTieEdges(svg, graphData, radius)

  // Create nodes and labels
  console.log("Creating nodes and labels...")
  drawNodesAndLabels(svg, graphData, nodeColors, radius, darkenColor)
}
