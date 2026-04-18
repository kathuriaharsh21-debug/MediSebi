import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';

// Lazy-loaded pages
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const InventoryPage = React.lazy(() => import('./pages/InventoryPage'));
const MedicinesPage = React.lazy(() => import('./pages/MedicinesPage'));
const SubstitutionPage = React.lazy(() => import('./pages/SubstitutionPage'));
const ShopsPage = React.lazy(() => import('./pages/ShopsPage'));
const ExpiryPage = React.lazy(() => import('./pages/ExpiryPage'));
const ClimatePage = React.lazy(() => import('./pages/ClimatePage'));
const ForecastPage = React.lazy(() => import('./pages/ForecastPage'));
const TransfersPage = React.lazy(() => import('./pages/TransfersPage'));
const MarketplacePage = React.lazy(() => import('./pages/MarketplacePage'));
const CatalogPage = React.lazy(() => import('./pages/CatalogPage'));
const NotificationsPage = React.lazy(() => import('./pages/NotificationsPage'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-sm text-slate-500">Loading...</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
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
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
