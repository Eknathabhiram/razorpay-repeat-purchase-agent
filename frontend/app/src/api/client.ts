import type { components } from './generated';
export type Me = components['schemas']['Me'];
export type Workspace = components['schemas']['WorkspaceSummary'];
export type Connector = components['schemas']['Connector'];
export type UIState = components['schemas']['UIReadModel'];
export type Policy = Required<components['schemas']['PolicyPreview']>;
export type DemoState = Required<Omit<components['schemas']['DemoState'], 'policy'>> & {policy: Policy};
export type Command = components['schemas']['DemoCommand'];
let csrf = '';
export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, message: string, code = '') {
    super(message); this.name = 'ApiError'; this.status = status; this.code = code;
  }
}
export function clearSession() { csrf = ''; }
export async function voiceRequest<T>(path:string, body?:Blob, signal?:AbortSignal, audioReply=false):Promise<T>{
  const response=await fetch('/api/v1'+path,{method:'POST',credentials:'same-origin',signal:AbortSignal.any([AbortSignal.timeout(45000),...(signal?[signal]:[])]),headers:{'X-CSRF-Token':csrf,...(body?{'Content-Type':body.type}:{} )},body});
  if(response.status===401){clearSession();window.dispatchEvent(new Event('session-expired'));}
  if(!response.ok){const data=await response.json().catch(()=>null);throw new ApiError(response.status,data?.error?.message??'Voice request failed. Refresh the saved turn before retrying.',data?.error?.code);}
  return (audioReply?await response.blob():(await response.json()).data) as T;
}
export async function api<T>(path: string, method = 'GET', body?: unknown, key?: string,
  options: {signal?: AbortSignal; timeoutMs?: number} = {}): Promise<T> {
  const signal = AbortSignal.any([AbortSignal.timeout(options.timeoutMs ?? 30000), ...(options.signal ? [options.signal] : [])]);
  try {
    const response = await fetch('/api/v1' + path, {
      method, signal, credentials: 'same-origin', headers: {
        Accept: 'application/json', ...(body !== undefined ? {'Content-Type': 'application/json'} : {}),
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...(key ? { 'Idempotency-Key': key } : {}),
      }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    if (response.status === 401 && !path.startsWith('/auth/')) {
      clearSession();
      if (typeof window !== 'undefined') window.dispatchEvent(new Event('session-expired'));
    }
    if (response.status === 204 && response.ok) return undefined as T;
    const result = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(response.status,
      result?.error?.message ?? (response.status === 401 ? 'Your session has expired. Sign in again.' :
        response.status === 429 ? 'Too many requests. Wait a moment and try again.' :
        response.status >= 500 ? 'The service is temporarily unavailable. Try again shortly.' : 'The request could not be completed.'),
      result?.error?.code ?? 'REQUEST_FAILED');
    if (!result || !Object.hasOwn(result, 'data')) throw new ApiError(response.status,
      'The service returned an unexpected response. Refresh and try again.', 'INVALID_RESPONSE');
    return result.data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (options.signal?.aborted) throw error;
    const uncertain = method !== 'GET' ? ' The change may have been saved. Refresh to check its status before trying again.' : ' Try again when your connection is restored.';
    throw new ApiError(0, (signal.aborted ? 'The request took too long.' : 'Unable to reach the service.') + uncertain,
      signal.aborted ? 'TIMEOUT' : 'NETWORK_ERROR');
  }
}
export async function login(login: string, password: string) {
  const result = await api<{csrf_token: string}>('/auth/login', 'POST', { login, password });
  csrf = result.csrf_token;
}
export async function restoreSession({signal}: {signal?: AbortSignal} = {}) {
  const result = await api<{csrf_token: string}>('/auth/session', 'POST', undefined, undefined, {signal});
  csrf = result.csrf_token;
  return api<Me>('/me', 'GET', undefined, undefined, {signal});
}
export async function logout() { await api('/auth/logout', 'POST', {}); csrf = ''; }
