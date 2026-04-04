const BASE_URL = 'http://localhost:8000/api/v1';

export const api = {
  async login(email, password) {
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
    
    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    return data;
  },
  
  logout() {
    localStorage.removeItem('token');
  },
  
  getToken() {
    return localStorage.getItem('token');
  }
};
