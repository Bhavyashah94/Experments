/**
 * Browser-native SHA-256 digest using SubtleCrypto.
 * Returns lowercase 64-character hexadecimal string.
 */
export async function calculateSha256(file: Blob): Promise<string> {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
}
