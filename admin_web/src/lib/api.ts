import { API_BASE_URL } from './env';
import { clearAuthTokens, getAccessToken } from './auth';

type RequestOptions = RequestInit & { auth?: boolean };

function extractMessage(payload: unknown, fallback: string): string {
  if (typeof payload === 'string' && payload.trim()) {
    return payload.trim();
  }

  if (payload && typeof payload === 'object') {
    const rec = payload as Record<string, unknown>;
    const detail = rec.detail;

    if (typeof detail === 'string' && detail.trim()) {
      if (detail === 'Invalid access token') {
        return 'Session expired. Please login again.';
      }
      return detail.trim();
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as Record<string, unknown>;
      if (typeof first?.msg === 'string' && first.msg.trim()) {
        return first.msg.trim();
      }
    }

    if (typeof rec.message === 'string' && rec.message.trim()) {
      return rec.message.trim();
    }
  }

  return fallback;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers ?? {});

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (!headers.has('Content-Type') && options.body !== undefined && !isFormData) {
    headers.set('Content-Type', 'application/json');
  }

  if (options.auth !== false && token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      cache: 'no-store',
    });
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error('Cannot reach server. Check backend host/port and API_BASE_URL.');
    }
    throw err;
  }

  const rawText = await response.text();
  const fallback = `Request failed with ${response.status}`;

  let parsed: unknown = null;
  if (rawText) {
    try {
      parsed = JSON.parse(rawText);
    } catch {
      parsed = rawText;
    }
  }

  if (!response.ok) {
    const message = extractMessage(parsed, fallback);

    if (response.status === 401 && options.auth !== false) {
      clearAuthTokens();
      if (typeof window !== 'undefined') {
        window.setTimeout(() => {
          window.location.replace('/login');
        }, 50);
      }
    }

    throw new Error(message);
  }

  if (response.status === 204 || rawText.length === 0) {
    return {} as T;
  }

  return parsed as T;
}
