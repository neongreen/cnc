const FALLBACK_BASE_PATH = "/cnc"

function normalizeBasePath(value: string | undefined): string {
  if (!value) return ""
  if (value === "/") return ""
  const trimmed = value.endsWith("/") ? value.slice(0, -1) : value
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`
}

export function getBasePath(): string {
  const candidates = [
    process.env.NEXT_PUBLIC_BASE_PATH,
    process.env.BASE_PATH,
    process.env.__NEXT_ROUTER_BASEPATH,
  ]

  for (const candidate of candidates) {
    if (candidate !== undefined) {
      return normalizeBasePath(candidate)
    }
  }

  return normalizeBasePath(FALLBACK_BASE_PATH)
}

export function withBasePath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  const basePath = getBasePath()
  if (!basePath) return normalizedPath
  return `${basePath}${normalizedPath}`
}
