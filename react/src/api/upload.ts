import { getAccessToken } from './auth'

export async function uploadImage(
  file: File
): Promise<{ file_id: string; width: number; height: number; url: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch('/api/upload_image', {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to upload image: ${response.status}`)
  }

  return await response.json()
}

export async function uploadVideo(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch('/api/upload_video', {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Failed to upload video')
  }

  return response.json()
}

export async function uploadAudio(
  file: File
): Promise<{ file_id: string; url: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch('/api/upload_audio', {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to upload audio: ${response.status}`)
  }

  return await response.json()
}
