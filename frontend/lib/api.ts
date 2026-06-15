// API configuration
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

export const apiFetch = async (path: string, options: RequestInit = {}) => {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-API-Key': API_KEY,
      ...(options.headers || {}),
    },
  })
  return res
}
