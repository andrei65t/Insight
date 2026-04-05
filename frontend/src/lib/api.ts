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

type CompanyCandidate = {
  name: string;
  website: string;
};

type CompanyNewsItem = {
  id: number;
  company: string;
  title: string;
  link: string;
  source: string;
  date?: string;
  fact_label: string;
};

type CompanyDetails = {
  tracked_company: TrackedCompany;
  news: CompanyNewsItem[];
  summary: {
    total_news: number;
    factual_count: number;
    opinion_count: number;
    inference_count: number;
    latest_date?: string | null;
  };
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

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail;
    }
    if (typeof data?.message === 'string' && data.message.trim()) {
      return data.message;
    }
    return fallback;
  } catch {
    return fallback;
  }
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
      throw new Error(await getErrorMessage(response, 'Login failed'));
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, 'Register failed'));
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
      throw new Error(await getErrorMessage(response, 'Failed to load tracked companies'));
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
      throw new Error(await getErrorMessage(response, 'Failed to track company'));
    }

    const data = await response.json();
    return data.item;
  },

  async deleteTrackedCompany(companyName: string): Promise<number> {
    const encodedName = encodeURIComponent(companyName);
    const response = await fetch(`${BASE_URL}/tracking/companies/${encodedName}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, 'Failed to delete tracked company'));
    }

    const data = await response.json();
    return Number(data.deleted_count ?? 0);
  },

  async searchCompanyCandidates(query: string): Promise<CompanyCandidate[]> {
    const response = await fetch(`${BASE_URL}/tracking/company-search`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, 'Failed to search company candidates'));
    }

    const data = await response.json();
    return data.items ?? [];
  },

  async getCompanyDetails(companyName: string): Promise<CompanyDetails> {
    const encodedName = encodeURIComponent(companyName);
    // Crescem timeout-ul la 30 de secunde pentru AI
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(`${BASE_URL}/tracking/companies/${encodedName}/details`, {
        method: 'GET',
        headers: authHeaders(),
        signal: controller.signal,
      });
      clearTimeout(id);

      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'Failed to load company details'));
      }

      return await response.json();
    } catch (e: any) {
      clearTimeout(id);
      if (e.name === 'AbortError') {
        throw new Error('Timeout: Serverul a răspuns prea greu.');
      }
      throw e;
    }
  },

  async askAI(companyName: string, question: string): Promise<{ answer: string }> {
    const response = await fetch(`${BASE_URL}/tracking/chat`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ company_name: companyName, question }),
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, 'Failed to get answer from AI'));
    }

    return await response.json();
  },

  logout() {
    localStorage.removeItem('token');
  },

  getToken() {
    return localStorage.getItem('token');
  },
};

export type { CompanyCandidate, TrackedCompany, CompanyDetails, CompanyNewsItem };
