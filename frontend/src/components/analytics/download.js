import client from '../../api/client'

// Fetch an xlsx export with the auth header and save it as `filename`.
export async function downloadXlsx(path, params, filename) {
  const res = await client.get(path, { params, responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
