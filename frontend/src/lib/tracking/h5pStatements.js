// Turns H5P xAPI statements into AIDEA learning events (see
// docs/superpowers/specs/2026-10-08-h5p-activities-design.md). Kept: answers
// (one per question answered) and finished attempts (the whole activity, top
// level). Everything else ("interacted", "progressed", …) is ignored.

const MAX_TEXT = 500
const DEDUPE_MS = 1500 // H5P can report one finish as both "answered" and "completed"

const verbOf = (s) => String(s?.verb?.id ?? '').split('/').pop()
const subContentId = (s) => /[?&]subContentId=([^&#]+)/.exec(String(s?.object?.id ?? ''))?.[1] ?? null

export function langText(map) {
  if (!map || typeof map !== 'object') return ''
  const value = map['en-US'] ?? Object.values(map)[0] ?? ''
  return String(value).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT)
}

export function durationSeconds(iso) {
  const m = /^PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$/.exec(String(iso ?? ''))
  if (!m) return null
  const seconds = Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0)
  return Math.round(seconds * 10) / 10
}

const score = (result) => {
  const raw = result?.score?.raw
  const max = result?.score?.max
  return Number.isFinite(raw) && Number.isFinite(max) ? { raw, max } : {}
}

// One session per H5P resource on the page.
export function createH5PSession({ language, packageId, packageVersion }) {
  let attempt = 1
  let lastFinishAt = -Infinity
  return {
    handle(statement, now) {
      const events = []
      let finished = null
      if (!statement || typeof statement !== 'object') return { events, finished }
      const verb = verbOf(statement)
      const result = statement.result && typeof statement.result === 'object' ? statement.result : null
      const sub = subContentId(statement)
      const seconds = durationSeconds(result?.duration)

      const isFinish = !sub && (verb === 'completed' || verb === 'answered')
        && result && result.completion !== false
      if (isFinish && now - lastFinishAt <= DEDUPE_MS) {
        // Second report of the same finish: record neither answer nor attempt.
        return { events, finished }
      }

      if (verb === 'answered' && result) {
        const definition = statement.object?.definition
        events.push({ type: 'h5p_answer', data: {
          question: langText(definition?.description) || langText(definition?.name),
          response: typeof result.response === 'string' ? result.response.slice(0, MAX_TEXT) : '',
          ...(typeof result.success === 'boolean' && { correct: result.success }),
          ...score(result),
          ...(seconds != null && { seconds }),
          attempt,
          ...(sub && { sub_content_id: sub.slice(0, 64) }),
        } })
      }

      if (isFinish) {
        lastFinishAt = now
        finished = {
          ...score(result),
          ...(typeof result.success === 'boolean' && { success: result.success }),
          ...(seconds != null && { duration_s: seconds }),
          attempt, language, package_id: packageId, package_version: packageVersion,
        }
        events.push({ type: 'h5p_attempt', data: finished })
        attempt += 1
      }
      return { events, finished }
    },
  }
}
