const palette = [
  "#45b7d1", // blue
  "#96ceb4", // green
  "#feca57", // yellow
  "#ff6f69", // red
  "#b39ddb", // purple
]

export const gray = "#ddd"

export function assignColors(items: string[]): { [item: string]: string } {
  const map: { [item: string]: string } = {}
  for (const item of items) {
    map[item] = palette[item.length % palette.length]
  }
  return map
}
