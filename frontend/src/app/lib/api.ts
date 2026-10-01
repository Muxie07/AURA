export class APIError extends Error {
  status: number;
  details: any;

  constructor(status: number, message: string, details?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.details = details;
  }
}

export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {


  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }


  let response: Response;
  try {
    response = await fetch(API_URL + endpoint, {
      ...options,
      headers,
    });
  } catch (err: any) {
    console.error(`[Network/Fetch Error] ${options.method || 'GET'} ${API_URL}${endpoint} - ${err.message}`);
    throw new APIError(0, err.message || 'Failed to fetch', err);
  }


  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    throw new APIError(401, 'Unauthorized - redirecting to login');
  }

  if (!response.ok) {
    let errorDetail = `API Error: ${response.status} ${response.statusText}`;
    let parsedDetails = null;
    try {
      const data = await response.json();
      parsedDetails = data.error || data.detail || data;
      
      if (data.error && typeof data.error.message === 'string') {
        errorDetail = data.error.message;
      } else if (typeof data.detail === 'string') {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = data.detail.map((d: any) => `${d.loc?.join('.')} ${d.msg}`).join(', ');
      }
    } catch (e) {
      // no json body
    }
    console.error(`[API Error ${response.status}] ${endpoint}:`, parsedDetails);
    throw new APIError(response.status, errorDetail, parsedDetails);
  }

  return response;
}

export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('token');
}

export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('organization_id');
    localStorage.removeItem('full_name');
    window.location.href = '/login';
  }
}
