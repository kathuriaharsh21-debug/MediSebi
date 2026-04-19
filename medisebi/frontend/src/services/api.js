import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: auto-refresh on 401
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        isRefreshing = false;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── Auth ──────────────────────────────────────────
export const authAPI = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),
  getMe: () => api.get('/auth/me'),
  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
};

// ─── Salts ─────────────────────────────────────────
export const saltsAPI = {
  list: (params = {}) => api.get('/salts', { params }),
};

// ─── Medicines ─────────────────────────────────────
export const medicinesAPI = {
  list: (params = {}) => api.get('/medicines', { params }),
};

// ─── Shops ─────────────────────────────────────────
export const shopsAPI = {
  list: (params = {}) => api.get('/shops', { params }),
};

// ─── Inventory ─────────────────────────────────────
export const inventoryAPI = {
  list: (params = {}) => api.get('/inventory', { params }),
  create: (data) => api.post('/inventory', data),
  update: (id, data) => api.put(`/inventory/${id}`, data),
  expiringAlerts: (params = {}) => api.get('/inventory/alerts/expiring', { params }),
  lowStockAlerts: (params = {}) => api.get('/inventory/alerts/low-stock', { params }),
  scanMedicine: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/inventory/scan-medicine', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ─── Substitution ──────────────────────────────────
export const substitutionAPI = {
  findAlternatives: (medId, shopId) =>
    api.post('/substitution/find-alternatives', { med_id: medId, shop_id: shopId }),
};

// ─── Expiry Watchdog ──────────────────────────
export const expiryAPI = {
  scan: () => api.get('/expiry/scan'),
  summary: () => api.get('/expiry/summary'),
  items: (params = {}) => api.get('/expiry/items', { params }),
  shopStatus: (shopId) => api.get(`/expiry/shop/${shopId}`),
  byCategory: () => api.get('/expiry/stats/by-category'),
};

// ─── Climate Intelligence ─────────────────────
export const climateAPI = {
  scan: () => api.get('/climate/scan'),
  shopAlerts: (shopId) => api.get(`/climate/shop/${shopId}`),
  dashboard: (params = {}) => api.get('/climate/dashboard', { params }),
  shopWeather: (shopId) => api.get(`/climate/weather/${shopId}`),
};

// ─── Demand Forecast ──────────────────────────
export const forecastAPI = {
  generate: () => api.post('/forecast/generate'),
  summary: () => api.get('/forecast/summary'),
  items: (params = {}) => api.get('/forecast/items', { params }),
  topDeficits: (params = {}) => api.get('/forecast/top-deficits', { params }),
  demandTrend: (medId, shopId) => api.get('/forecast/charts/demand-trend', { params: { med_id: medId, shop_id: shopId } }),
};

// ─── Transfers / Redistribution ───────────────
export const transfersAPI = {
  analyze: () => api.get('/transfers/analyze'),
  analyzeShop: (shopId) => api.get(`/transfers/analyze/shop/${shopId}`),
  list: (params = {}) => api.get('/transfers/', { params }),
  get: (id) => api.get(`/transfers/${id}`),
  create: (data) => api.post('/transfers/request', data),
  approve: (id) => api.put(`/transfers/${id}/approve`),
  execute: (id) => api.put(`/transfers/${id}/execute`),
  reject: (id, data) => api.put(`/transfers/${id}/reject`, data),
  analytics: () => api.get('/transfers/analytics'),
  shopHistory: (shopId, params = {}) => api.get(`/transfers/shop/${shopId}/history`, { params }),
};

// ─── Marketplace ──────────────────────────────
export const marketplaceAPI = {
  expiringListings: (params = {}) => api.get('/marketplace/expiring-listings', { params }),
  demandMatches: () => api.get('/marketplace/demand-matches'),
  createOffer: (data) => api.post('/marketplace/create-offer', data),
  listOffers: (params = {}) => api.get('/marketplace/offers', { params }),
  acceptOffer: (id) => api.put(`/marketplace/offers/${id}/accept`),
  rejectOffer: (id, data) => api.put(`/marketplace/offers/${id}/reject`, data),
  completeOffer: (id) => api.put(`/marketplace/offers/${id}/complete`),
  dashboard: () => api.get('/marketplace/dashboard'),
  shopListings: (shopId) => api.get(`/marketplace/shop/${shopId}/listings`),
  shopOpportunities: (shopId) => api.get(`/marketplace/shop/${shopId}/opportunities`),
};

// ─── Catalog ─────────────────────────────────
export const catalogAPI = {
  browse: (params = {}) => api.get('/catalog/', { params }),
  search: (params = {}) => api.get('/catalog/search', { params }),
  categories: () => api.get('/catalog/categories'),
  get: (index) => api.get(`/catalog/${index}`),
  quickAdd: (data) => api.post('/catalog/quick-add', data),
  bulkAdd: (data) => api.post('/catalog/bulk-add', data),
  stockCheck: (shopId) => api.get(`/catalog/stock-check/${shopId}`),
};

// ─── Billing ──────────────────────────────────
export const billingAPI = {
  create: (data) => api.post('/bills/', data),
  list: (params) => api.get('/bills/', { params }),
  get: (id) => api.get(`/bills/${id}`),
  todayBills: (shopId) => api.get(`/bills/shop/${shopId}/today`),
  revenue: (shopId, params) => api.get(`/bills/shop/${shopId}/revenue`, { params }),
  cancel: (id) => api.put(`/bills/${id}/cancel`),
};

// ─── Notifications ────────────────────────────
export const notificationsAPI = {
  list: () => api.get('/notifications/'),
};

// ─── Analytics ───────────────────────────────
export const analyticsAPI = {
  seasonal: (params) => api.get('/analytics/seasonal', { params }),
  frequency: (params) => api.get('/analytics/frequency', { params }),
  orderingGuide: (params) => api.get('/analytics/ordering-guide', { params }),
};

export default api;
