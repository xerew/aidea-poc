// One line of the admin activity feed in the viewer's language. The server
// sends `kind` + `params`; its English `text` is the fallback for a kind this
// build doesn't know yet.
const ROLE_KEYS = { teacher: 'teacher', content_creator: 'contentCreator', aidea_partner: 'aideaPartner', admin: 'admin' }

function languageName(code, uiLanguage) {
  try {
    return new Intl.DisplayNames([uiLanguage], { type: 'language' }).of(code) || code
  } catch {
    return code
  }
}

export function roleLabel(role, t) {
  return ROLE_KEYS[role] ? t(`admin.roles.${ROLE_KEYS[role]}`) : role
}

export function feedText(item, t, i18n) {
  const p = { ...item.params, course: item.course?.title ?? item.params.course ?? '' }
  let kind = item.kind
  if (p.outcome) p.outcome = t(`admin.activity.outcomes.${p.outcome}`)
  if (kind === 'collaborator_added' && p.role) p.role = t(`admin.activity.authorRoles.${p.role}`)
  if (p.old_role) p.old_role = roleLabel(p.old_role, t)
  if (p.new_role) p.new_role = roleLabel(p.new_role, t)
  if (p.language) p.language = languageName(p.language, i18n.language)
  if (kind === 'translation_requested') p.scope = t(`admin.activity.scopes.${p.scope || 'course'}`)
  if (kind === 'competency_changed' && p.course) kind = 'competency_changed_course'
  if (kind === 'signed_in') {
    p.device = t(`admin.activity.devices.${p.device || 'unknown'}`)
    p.browser = p.browser || 'Other'
  }
  const key = `admin.activity.kinds.${kind}`
  let text = i18n.exists(key) ? t(key, p) : item.text
  if (kind === 'h5p_attempt' && p.score != null && p.max_score != null) text += ` (${p.score}/${p.max_score})`
  return text
}
