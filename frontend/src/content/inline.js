// Legal texts keep their formatting as plain strings: **bold** and the
// contact address (which becomes a mailto link).
const EMAIL = 'info@aidea-hub.eu'
const TOKEN = /(\*\*[^*]+\*\*|info@aidea-hub\.eu)/g

export function inlineParts(text) {
  return text.split(TOKEN).filter(Boolean).map((piece) => {
    if (piece === EMAIL) return { email: piece }
    if (piece.startsWith('**') && piece.endsWith('**')) return { bold: piece.slice(2, -2) }
    return { text: piece }
  })
}
