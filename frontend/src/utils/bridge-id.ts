/**
 * Extrai o número principal da rodovia (ex.: BR-116 → 116, RJ-116 → 116).
 */
export function parseRodoviaNumber(rodovia: string): string | null {
  const normalized = rodovia.trim().toUpperCase()
  if (!normalized) return null

  const brMatch = normalized.match(/(?:BR|SP|RJ|MG|PR|SC|RS|GO|BA|ES|CE|PE|PA|MA|MT|MS|DF|AL|SE|PB|RN|PI|TO|RO|AC|AM|RR|AP|RO)-?(\d+)/)
  if (brMatch) return brMatch[1]!

  const suffixMatch = normalized.match(/^(\d{2,4})-([A-Z]{2})$/)
  if (suffixMatch) return suffixMatch[1]!

  const prefixMatch = normalized.match(/^([A-Z]{2})-(\d{2,4})$/)
  if (prefixMatch) return prefixMatch[2]!

  const digitsOnly = normalized.match(/(\d{2,4})/)
  return digitsOnly ? digitsOnly[1]! : null
}

/**
 * Monta o identificador RSP: prefixo (ex.: E) + número da rodovia (ex.: 116 → E116).
 */
export function buildBridgeId(prefix: string | undefined, rodovia: string): string {
  const number = parseRodoviaNumber(rodovia)
  if (!number) return ''

  const letter = ((prefix ?? 'E').trim().toUpperCase().replace(/[^A-Z]/g, '') || 'E').slice(0, 1)
  return `${letter}${number}`
}

export function formatRodoviaHint(): string {
  return 'Ex.: BR-116, 116-RJ ou RJ-116'
}
