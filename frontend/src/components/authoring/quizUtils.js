// Quiz helpers shared by the activity and resource editors.

export function emptyQuestion() {
  return {
    question: '',
    options: [
      { text: '', is_correct: false },
      { text: '', is_correct: false },
      { text: '', is_correct: false },
      { text: '', is_correct: false },
    ],
  }
}

// Merge a lesson or resource's base quiz structure (is_correct + option/question order —
// always authoritative) with its translated text for `lang`. Falls back to
// blank text (not the source text) when nothing has been translated yet, so
// translated-mode inputs never masquerade untranslated source text as a
// translation.
export function mergedQuizData(item, lang) {
  const base = item.quiz_data ?? []
  if (lang === 'original') return base
  const translated = item.translations?.[lang]?.quiz_data
  if (Array.isArray(translated) && translated.length === base.length) {
    return base.map((q, qi) => ({
      question: translated[qi]?.question ?? '',
      options: q.options.map((o, oi) => ({
        text: translated[qi]?.options?.[oi]?.text ?? '',
        is_correct: o.is_correct,
      })),
    }))
  }
  return base.map((q) => ({
    question: '',
    options: q.options.map((o) => ({ text: '', is_correct: o.is_correct })),
  }))
}
