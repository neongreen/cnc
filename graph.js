function drawGraph(graphData, graphHeight, levels) {
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

  // Create arrow marker
  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", radius - 2)
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#666")

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
  const link = svg
    .append("g")
    .selectAll("line")
    .data(graphData.edges)
    .enter()
    .append("line")
    .attr("class", "edge")

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

  // Update positions function
  function updatePositions() {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y)

    node.attr("cx", (d) => d.x).attr("cy", (d) => d.y)

    nodeText.attr("x", (d) => d.x).attr("y", (d) => d.y)
  }

  // Set up simulation tick handler
  simulation.on("tick", updatePositions)

  // Trigger initial render
  updatePositions()
}
