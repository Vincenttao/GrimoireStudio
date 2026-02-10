import apiClient from './client';

export const authApi = {
  register: (email: string, password: string) => 
    apiClient.post(`/auth/register`, { email, password }),
    
  login: (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    return apiClient.post(`/auth/login/access-token`, formData);
  }
};