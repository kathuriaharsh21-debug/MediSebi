import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import MedicinesPage from './pages/MedicinesPage';
import SubstitutionPage from './pages/SubstitutionPage';
import ShopsPage from './pages/ShopsPage';
import ExpiryPage from './pages/ExpiryPage';
import ClimatePage from './pages/ClimatePage';
import ForecastPage from './pages/ForecastPage';
import TransfersPage from './pages/TransfersPage';
import MarketplacePage from './pages/MarketplacePage';
import CatalogPage from './pages/CatalogPage';
import NotificationsPage from './pages/NotificationsPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/medicines" element={<MedicinesPage />} />
            <Route path="/substitution" element={<SubstitutionPage />} />
            <Route path="/shops" element={<ShopsPage />} />
            <Route path="/expiry" element={<ExpiryPage />} />
            <Route path="/climate" element={<ClimatePage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/transfers" element={<TransfersPage />} />
            <Route path="/marketplace" element={<MarketplacePage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
