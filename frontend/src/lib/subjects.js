// The subject taxonomy is a fixed set seeded in the DB. Names come back in
// English from the API, so translate them by slug (falling back to the stored
// name if a slug ever lacks a translation key).
export function subjectLabel(subject, t) {
  if (!subject) return ''
  return subject.slug
    ? t(`subjects.${subject.slug}`, { defaultValue: subject.name })
    : subject.name
}
