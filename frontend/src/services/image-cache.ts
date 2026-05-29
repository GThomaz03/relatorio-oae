const MAX_CACHE = 300
const cached = new Set<string>()

export function preloadImage(src: string | null | undefined): void {
  if (!src || cached.has(src)) return
  if (cached.size >= MAX_CACHE) {
    const first = cached.values().next().value as string | undefined
    if (first) cached.delete(first)
  }
  const img = new Image()
  img.decoding = 'async'
  img.src = src
  cached.add(src)
}

export function preloadAround(urls: Array<string | null | undefined>): void {
  urls.forEach((url) => preloadImage(url))
}
