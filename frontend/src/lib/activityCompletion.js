// The activity's single "Mark activity as done" button (spec 2026-10-21 §3).
// Quizzes, assignments and H5P that report their own finish complete themselves.

const SELF_COMPLETED_TYPES = ['text', 'image', 'video', 'pdf', 'presentation']

export const selfCompletes = (resource) =>
  SELF_COMPLETED_TYPES.includes(resource.type) || (resource.type === 'h5p' && Boolean(resource.h5p_self_complete))

export function activityButtonState(resources) {
  const covered = resources.filter(selfCompletes)
  const pendingIds = covered.filter(res => !res.is_completed).map(res => res.id)
  const others = resources.filter(res => !selfCompletes(res))
  return {
    show: covered.length > 0,
    done: covered.length > 0 && pendingIds.length === 0,
    pendingIds,
    showNote: covered.length > 0 && others.some(res => !res.is_completed),
  }
}
