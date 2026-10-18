import { clearSession, get, post, setStoredUser, setToken } from './api';
import type { LoginResponse, SessionUser } from './types';

export async function login(email: string, password: string): Promise<LoginResponse> {
  const result = await post<LoginResponse>('/auth/login', { email, password }, false);
  setToken(result.access_token);
  const user: SessionUser = {
    id: result.user_id,
    email: result.email,
    full_name: result.full_name,
    organization_id: result.organization_id,
    roles: result.roles ?? [],
  };
  setStoredUser(user);
  return result;
}

export function fetchMe(): Promise<SessionUser> {
  return get<SessionUser>('/auth/me');
}

export function logout(): void {
  clearSession();
}
