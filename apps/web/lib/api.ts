import type { SessionUser } from './types';

export const TOKEN_KEY = 'hannibal_token';
export const USER_KEY = 'hannibal_user';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function getStoredUser(): SessionUser | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: SessionUser): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  clearSession();
  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

function messageFromDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        const obj = item as Record<string, unknown>;
        if (typeof obj.msg === 'string') {
          const loc = Array.isArray(obj.loc) ? obj.loc.slice(1).join('.') : '';
          return loc ? `${loc}: ${obj.msg}` : obj.msg;
        }
      }
      return '';
    });
    const joined = parts.filter(Boolean).join('; ');
    if (joined) return joined;
  }
  if (detail && typeof detail === 'object') {
    const obj = detail as Record<string, unknown>;
    if (typeof obj.message === 'string') return obj.message;
    if (typeof obj.detail === 'string') return obj.detail;
    try {
      return JSON.stringify(detail);
    } catch {
      return 'Unexpected error';
    }
  }
  return 'Unexpected error';
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail: unknown = null;
  try {
    detail = await response.json();
  } catch {
    detail = null;
  }
  const message =
    detail !== null
      ? messageFromDetail((detail as Record<string, unknown>)?.detail ?? detail)
      : `Request failed with status ${response.status}`;
  return new ApiError(response.status, message, detail);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options;
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    else if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      redirectToLogin();
      throw new ApiError(401, 'Your session has expired. Sign in again.');
    }
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the Hannibal API. Check that the backend is running.');
  }

  if (response.status === 401 && auth) {
    redirectToLogin();
    throw new ApiError(401, 'Your session has expired. Sign in again.');
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export function get<T>(path: string, auth = true): Promise<T> {
  return request<T>(path, { method: 'GET', auth });
}

export function post<T>(path: string, body?: unknown, auth = true): Promise<T> {
  return request<T>(path, { method: 'POST', body, auth });
}

export function patch<T>(path: string, body?: unknown, auth = true): Promise<T> {
  return request<T>(path, { method: 'PATCH', body, auth });
}

export async function fetchBlob(path: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else {
    redirectToLogin();
    throw new ApiError(401, 'Your session has expired. Sign in again.');
  }
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { headers });
  } catch {
    throw new ApiError(0, 'Cannot reach the Hannibal API. Check that the backend is running.');
  }
  if (response.status === 401) {
    redirectToLogin();
    throw new ApiError(401, 'Your session has expired. Sign in again.');
  }
  if (!response.ok) throw await toApiError(response);
  return response.blob();
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function openBlobInNewTab(blob: Blob): boolean {
  const url = URL.createObjectURL(blob);
  const opened = window.open(url, '_blank', 'noopener,noreferrer');
  if (!opened) {
    saveBlob(blob, 'hannibal-export');
    URL.revokeObjectURL(url);
    return false;
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  return true;
}
