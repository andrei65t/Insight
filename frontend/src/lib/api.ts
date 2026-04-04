const BASE_URL = 'http://localhost:8000/api/v1';

type LoginResponse = {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
};

type RegisterPayload = {
  email: string;
  password: string;
  full_name?: string;
};

type TrackedCompany = {
  id: number;
  company_name: string;
  created_at?: string;
};

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${BASE_URL}/login/access-token`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data: LoginResponse = await response.json();
    if (data.access_token) {
      localStorage.setItem('token', data.access_token);
    }
    return data;
  },

  async register(payload: RegisterPayload): Promise<LoginResponse & { user?: unknown }> {
    const response = await fetch(`${BASE_URL}/login/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('Register failed');
    }

    const data = await response.json();
    if (data.access_token) {
      localStorage.setItem('token', data.access_token);
    }
    return data;
  },

  async getTrackedCompanies(): Promise<TrackedCompany[]> {
    const response = await fetch(`${BASE_URL}/tracking/companies`, {
      method: 'GET',
      headers: authHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to load tracked companies');
    }

    const data = await response.json();
    return data.items ?? [];
  },

  async trackCompany(companyName: string): Promise<TrackedCompany> {
    const response = await fetch(`${BASE_URL}/tracking/companies`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ company_name: companyName }),
    });

    if (!response.ok) {
      throw new Error('Failed to track company');
    }

    const data = await response.json();
    return data.item;
  },

  logout() {
    localStorage.removeItem('token');
  },

  getToken() {
    return localStorage.getItem('token');
  },
};
