// Resolve a user's avatar image: an uploaded photo wins, otherwise a
// gender-based default; null means "fall back to initials".
export function getAvatarSrc(profile) {
  if (profile?.avatar_url) return profile.avatar_url
  if (profile?.gender === 'male') return '/images/avatars/male_avatar.jpg'
  if (profile?.gender === 'female') return '/images/avatars/female_avatar.jpg'
  return null
}
