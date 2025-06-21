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
  console.log("Calculating node positions...")

  levels.forEach((level, levelIndex) => {
    const x = (levelIndex + 1) * (width / (levels.length + 1))
    level.forEach((nodeName, nodeIndex) => {
      const y = (nodeIndex + 1) * (height / (level.length + 1))
      nodePositions.set(nodeName, { x, y })
    })
  })

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
  console.log("Creating edges...")
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
        .y((d) => d.y)(
        (() => {
          // Calculate how many edges come out of the source node / into the target node
          const edges = graphData.edges
          console.log("Current edges:", edges)
          const sourceEdges = edges
            .filter((e) => e.source === d.source)
            .sort((a, b) => a.target.y - b.target.y) // Sort by target node's y-coordinate
          console.log("Source edges for current edge (sorted):", sourceEdges)
          const targetEdges = edges
            .filter((e) => e.target === d.target)
            .sort((a, b) => b.source.y - a.source.y) // Sort by source node's y-coordinate
          console.log("Target edges for current edge (sorted):", targetEdges)
          // Calculate the angles for the edge based on the number of edges
          const sourceIndex = sourceEdges.findIndex(
            (e) => e.target === d.target
          )
          console.log("Source index:", sourceIndex)
          const targetIndex = targetEdges.findIndex(
            (e) => e.source === d.source
          )
          console.log("Target index:", targetIndex)
          const angle = (i, total) =>
            (((i - (total - 1) / 2) / total) * Math.PI) / 2
          const sourceAngle = angle(sourceIndex, sourceEdges.length)
          console.log("Source angle:", sourceAngle)
          const targetAngle = angle(targetIndex, targetEdges.length)
          console.log("Target angle:", targetAngle)
          return {
            source: {
              x: d.source.x + radius * Math.cos(sourceAngle),
              y: d.source.y + radius * Math.sin(sourceAngle),
            },
            target: {
              x: d.target.x - (radius + arrowSize + 4) * Math.cos(targetAngle),
              y: d.target.y - (radius + arrowSize + 4) * Math.sin(targetAngle),
            },
          }
        })()
      )
    })

  // Create nodes
  console.log("Creating nodes...")
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(graphData.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", radius)

  // Add node labels
  console.log("Adding node labels...")
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
