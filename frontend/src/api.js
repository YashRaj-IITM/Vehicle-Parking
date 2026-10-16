import axios from 'axios';

// In development the Vue dev server proxies /api to Flask (see vue.config.js).
// For production builds set VUE_APP_API_URL (e.g. https://api.example.com).
const api = axios.create({ baseURL: process.env.VUE_APP_API_URL || '' });

// Attach the access token issued by Flask-Security to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers['Authentication-Token'] = token;
  return config;
});

// Expired / invalid token: clear the session and go back to the login page
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = (error.config && error.config.url) || '';
    if (error.response && error.response.status === 401 && !url.includes('/auth/login')) {
      localStorage.clear();
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login');
    }
    return Promise.reject(error);
  }
);

export function setAuthToken(token) {
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function getAuthToken() {
  return localStorage.getItem('token');
}

export function errMsg(error, fallback = 'Something went wrong') {
  return (error.response && error.response.data && (error.response.data.error || error.response.data.message)) || fallback;
}

// --- Auth ---
export const login = (email, password) => api.post('/api/auth/login', { email, password });
export const register = (email, full_name, password) => api.post('/api/auth/register', { email, full_name, password });
export const logout = () => api.post('/api/auth/logout');

// --- User ---
export const listParkingLots = (q = '') => api.get('/api/user/parking_lots', { params: { q } });
export const reserveSpot = (lot_id) => api.post('/api/user/reserve', { lot_id });
export const releaseSpot = (reservation_id) => api.post('/api/user/release', { reservation_id });
export const myReservations = () => api.get('/api/user/my_reservations');
export const deleteReservation = (id) => api.delete(`/api/user/reservations/${id}`);
export const getUserStats = () => api.get('/api/user/stats');
export const getProfile = () => api.get('/api/user/profile');
export const updateProfile = (data) => api.put('/api/user/profile', data);
export const deleteAccount = () => api.delete('/api/user/account');
export const startExport = () => api.post('/api/user/export');
export const exportStatus = (taskId) => api.get(`/api/user/export/${taskId}`, { responseType: 'blob' });

// --- Admin ---
export const getUsers = (q = '') => api.get('/api/admin/users', { params: { q } });
export const setUserStatus = (id, action) => api.put(`/api/admin/users/${id}/status`, { action });
export const deleteUser = (id) => api.delete(`/api/admin/users/${id}`);
export const getAdminStats = () => api.get('/api/admin/stats');
export const getParkingLots = (q = '') => api.get('/api/admin/parking_lots', { params: { q } });
export const createParkingLot = (prime_location_name, price_per_hour, address, pin_code, maximum_number_of_spots) =>
  api.post('/api/admin/parking_lots', { prime_location_name, price_per_hour, address, pin_code, maximum_number_of_spots });
export const updateParkingLot = (id, data) => api.put(`/api/admin/parking_lots/${id}`, data);
export const deleteParkingLot = (id) => api.delete(`/api/admin/parking_lots/${id}`);
export const getParkingSpots = (lot_id) => api.get(`/api/admin/parking_lots/${lot_id}/spots`);
export const deleteSpot = (id) => api.delete(`/api/admin/spots/${id}`);
export const scheduleBulkReminders = (user_ids, reminder_time, subject, body) =>
  api.post('/api/admin/schedule_bulk_reminders', { user_ids, reminder_time, subject, body });

export default api;
