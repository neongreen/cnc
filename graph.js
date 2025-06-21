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

export function drawGraph(graphData, graphHeight, levels) {
  const svg = d3.select("#graph-svg")
  // width same as table width (determined dynamically), or viewport width, whichever is bigger
  const width = Math.max(
    document.querySelector("table").offsetWidth,
    window.innerWidth
  )
  const height = graphHeight

  // Set SVG dimensions explicitly
  svg.attr("width", width).attr("height", height)

  const radius = 30 // Radius for nodes
  const arrowSize = 5 // Size of the arrow marker

  // Create arrow marker
  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 0)
    .attr("refY", 0)
    .attr("markerWidth", arrowSize)
    .attr("markerHeight", arrowSize)
    .attr("orient", "auto")
    .append("path")
    .attr("class", "arrowhead")
    .attr("d", "M0,-5L10,0L0,5")

  // Position nodes in hierarchical layout based on topological levels
  const nodePositions = new Map()

  levels.forEach((level, levelIndex) => {
    const x = (levelIndex + 1) * (width / (levels.length + 1))
    level.forEach((nodeName, nodeIndex) => {
      const y = (nodeIndex + 1) * (height / (level.length + 1))
      nodePositions.set(nodeName, { x, y })
    })
  })

  // Set fixed positions for nodes
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
  const simulation = d3
    .forceSimulation(graphData.nodes)
    .force(
      "link",
      d3
        .forceLink(graphData.edges)
        .id((d) => d.id)
        .distance(100)
        .strength(0)
    )
    .stop() // Don't run the simulation, we have fixed positions

  // Create edges
  svg
    .append("g")
    .selectAll("path")
    .data(graphData.edges)
    .enter()
    .append("path")
    .attr("class", "edge")
    .attr("marker-end", "url(#arrowhead)") // Add marker to the end of the path
    .attr("d", (d) => {
      // Adjust target point to end at the circle's edge
      return d3
        .linkHorizontal()
        .x((d) => d.x)
        .y((d) => d.y)({
        source: { x: d.source.x + radius, y: d.source.y },
        target: { x: d.target.x - radius - arrowSize - 4, y: d.target.y },
      })
    })

  // Create nodes
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(graphData.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", radius)

  // Add node labels
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
