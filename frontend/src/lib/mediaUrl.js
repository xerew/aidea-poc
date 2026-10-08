import client from '../api/client'

// A site-relative media path ("/media/…") as an absolute URL on the API's host
// (the dev server serves media from the backend, not from Vite).
export const mediaUrl = (path) => new URL(path, client.defaults.baseURL).href
