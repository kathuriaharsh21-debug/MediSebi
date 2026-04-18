import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  CloudSun, Thermometer, Droplets, AlertTriangle, RefreshCw, Filter,
  ChevronLeft, ChevronRight, Loader2, Activity, Shield, X,
} from 'lucide-react';
import { climateAPI, shopsAPI } from '../services/api';

const RISK_STYLES = {
  CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  MODERATE: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  LOW: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
};

const RISK_ICON_STYLES = {
  CRITICAL: 'bg-red-500/15 text-red-400',
  HIGH: 'bg-orange-500/15 text-orange-400',
  MODERATE: 'bg-blue-500/15 text-blue-400',
  LOW: 'bg-emerald-500/15 text-emerald-400',
};

export default function ClimatePage() {
  const [dashboard, setDashboard] = useState(null);
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState('');
  const [shopWeather, setShopWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');

  // Alerts pagination
  const [alertPage, setAlertPage] = useState(1);
  const alertPageSize = 10;

  useEffect(() => {
    fetchShops();
    fetchDashboard();
  }, []);

  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (e) {
      console.error('Failed to fetch shops:', e);
    }
  };

  const fetchDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await climateAPI.dashboard();
      setDashboard(data || {});
    } catch (e) {
      console.error('Failed to fetch climate dashboard:', e);
      setError('Failed to load climate dashboard.');
    } finally {
      setLoading(false);
    }
  };

  const fetchShopWeather = async (shopId) => {
    if (!shopId) {
      setShopWeather(null);
      return;
    }
    setWeatherLoading(true);
    try {
      const { data } = await climateAPI.shopWeather(shopId);
      setShopWeather(data || {});
    } catch (e) {
      console.error('Failed to fetch shop weather:', e);
      setShopWeather(null);
    } finally {
      setWeatherLoading(false);
    }
  };

  const handleShopChange = (shopId) => {
    setSelectedShop(shopId);
    setAlertPage(1);
    fetchShopWeather(shopId);
  };

  const handleScan = async () => {
    setScanning(true);
    setError('');
    try {
      await climateAPI.scan();
      await fetchDashboard();
      if (selectedShop) fetchShopWeather(selectedShop);
    } catch (e) {
      console.error('Climate scan failed:', e);
      setError('Climate scan failed. Please try again.');
    } finally {
      setScanning(false);
    }
  };

  // Alerts from dashboard
  const alerts = useMemo(() => {
    if (!dashboard?.alerts) return [];
    return Array.isArray(dashboard.alerts) ? dashboard.alerts : [];
  }, [dashboard]);

  // Disease breakdown chart data
  const diseaseChartData = useMemo(() => {
    if (!dashboard?.disease_breakdown) return [];
    return dashboard.disease_breakdown.map((d) => ({
      name: d.disease || d.name || 'Unknown',
      critical: d.critical || d.CRITICAL || 0,
      high: d.high || d.HIGH || 0,
      moderate: d.moderate || d.MODERATE || 0,
      low: d.low || d.LOW || 0,
    }));
  }, [dashboard]);

  // Paginated alerts
  const paginatedAlerts = useMemo(() => {
    const start = (alertPage - 1) * alertPageSize;
    return alerts.slice(start, start + alertPageSize);
  }, [alerts, alertPage]);

  const totalAlertPages = Math.ceil(alerts.length / alertPageSize);

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-800 border border-slate-600/50 rounded-lg p-3 shadow-xl">
          <p className="text-sm text-slate-300 font-medium">{label}</p>
          {payload.map((entry, idx) => (
            <p key={idx} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <CloudSun className="w-6 h-6 text-indigo-400" />
            Climate Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">Monitor climate-related disease risks and shop conditions</p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
        >
          {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {scanning ? 'Scanning...' : 'Run Climate Scan'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <p className="text-sm text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </p>
        </div>
      )}

      {/* Risk Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <ClimateCard
          title="Critical"
          value={dashboard?.risk_summary?.critical ?? dashboard?.critical_count ?? 0}
          icon={AlertTriangle}
          riskKey="CRITICAL"
        />
        <ClimateCard
          title="High Risk"
          value={dashboard?.risk_summary?.high ?? dashboard?.high_count ?? 0}
          icon={Thermometer}
          riskKey="HIGH"
        />
        <ClimateCard
          title="Moderate"
          value={dashboard?.risk_summary?.moderate ?? dashboard?.moderate_count ?? 0}
          icon={Droplets}
          riskKey="MODERATE"
        />
        <ClimateCard
          title="Low Risk"
          value={dashboard?.risk_summary?.low ?? dashboard?.low_count ?? 0}
          icon={Shield}
          riskKey="LOW"
        />
      </div>

      {/* Disease Breakdown Chart */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          Disease Breakdown
        </h3>
        {diseaseChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={diseaseChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="critical" name="Critical" fill="#EF4444" radius={[2, 2, 0, 0]} />
              <Bar dataKey="high" name="High" fill="#F97316" radius={[2, 2, 0, 0]} />
              <Bar dataKey="moderate" name="Moderate" fill="#3B82F6" radius={[2, 2, 0, 0]} />
              <Bar dataKey="low" name="Low" fill="#10B981" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[320px] text-slate-500 text-sm">
            No disease breakdown data available
          </div>
        )}
      </div>

      {/* Alerts Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Climate Alerts
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium">
              {alerts.length} alerts
            </span>
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">City</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Temperature</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Humidity</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Disease</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Risk Level</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Recommended Salts</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Action Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {paginatedAlerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                    No climate alerts available
                  </td>
                </tr>
              ) : (
                paginatedAlerts.map((alert, idx) => {
                  const risk = (alert.risk_level || alert.risk || 'LOW').toUpperCase();
                  const riskStyle = RISK_STYLES[risk] || RISK_STYLES.LOW;
                  return (
                    <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 text-sm font-medium text-slate-200">
                        {alert.city || alert.shop_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        <span className="inline-flex items-center gap-1">
                          <Thermometer className="w-3.5 h-3.5 text-red-400" />
                          {alert.temperature ?? alert.temp ?? '—'}°C
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        <span className="inline-flex items-center gap-1">
                          <Droplets className="w-3.5 h-3.5 text-blue-400" />
                          {alert.humidity ?? '—'}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-300">
                        {alert.disease || alert.disease_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${riskStyle}`}>
                          {risk}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400 max-w-[200px] truncate">
                        {alert.recommended_salts || alert.salts || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400 max-w-[200px] truncate">
                        {alert.action_summary || alert.action || '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalAlertPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/50">
            <p className="text-xs text-slate-500">
              Showing {((alertPage - 1) * alertPageSize) + 1}&ndash;{Math.min(alertPage * alertPageSize, alerts.length)} of {alerts.length}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setAlertPage((p) => Math.max(1, p - 1))}
                disabled={alertPage === 1}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalAlertPages) }, (_, i) => {
                const pageNum = Math.max(1, Math.min(alertPage - 2, totalAlertPages - 4)) + i;
                if (pageNum > totalAlertPages) return null;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setAlertPage(pageNum)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                      pageNum === alertPage
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => setAlertPage((p) => Math.min(totalAlertPages, p + 1))}
                disabled={alertPage === totalAlertPages}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Shop Weather Cards */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <CloudSun className="w-4 h-4 text-emerald-400" />
            Shop Weather Details
          </h3>
          <div className="flex items-center gap-2">
            <select
              value={selectedShop}
              onChange={(e) => handleShopChange(e.target.value)}
              className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="">Select a shop...</option>
              {shops.map((s) => (
                <option key={s.id} value={s.id}>{s.name} — {s.city}</option>
              ))}
            </select>
            {selectedShop && (
              <button
                onClick={() => { setSelectedShop(''); setShopWeather(null); }}
                className="p-1.5 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {weatherLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
          </div>
        ) : !selectedShop ? (
          <div className="flex items-center justify-center py-12 text-sm text-slate-500">
            Select a shop to view weather details
          </div>
        ) : shopWeather ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Temperature Card */}
            <div className="bg-slate-800/50 border border-slate-700/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Thermometer className="w-4 h-4 text-red-400" />
                <span className="text-xs font-medium text-slate-400 uppercase">Temperature</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {shopWeather.temperature ?? shopWeather.temp ?? '—'}°C
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Feels like {shopWeather.feels_like ?? '—'}°C
              </p>
            </div>

            {/* Humidity Card */}
            <div className="bg-slate-800/50 border border-slate-700/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Droplets className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-medium text-slate-400 uppercase">Humidity</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {shopWeather.humidity ?? '—'}%
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {shopWeather.humidity >= 70 ? 'High humidity zone' : shopWeather.humidity >= 40 ? 'Comfortable range' : 'Low humidity'}
              </p>
            </div>

            {/* Condition Card */}
            <div className="bg-slate-800/50 border border-slate-700/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <CloudSun className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-medium text-slate-400 uppercase">Condition</span>
              </div>
              <p className="text-lg font-bold text-white">
                {shopWeather.condition || shopWeather.weather || '—'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {shopWeather.wind_speed ? `Wind: ${shopWeather.wind_speed} km/h` : shopWeather.description || 'No additional info'}
              </p>
            </div>

            {/* Disease Risks Card */}
            <div className="bg-slate-800/50 border border-slate-700/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <span className="text-xs font-medium text-slate-400 uppercase">Disease Risks</span>
              </div>
              {shopWeather.disease_risks && shopWeather.disease_risks.length > 0 ? (
                <div className="space-y-1.5 max-h-24 overflow-y-auto">
                  {shopWeather.disease_risks.slice(0, 5).map((dr, idx) => {
                    const risk = (dr.risk_level || dr.risk || 'LOW').toUpperCase();
                    const rs = RISK_STYLES[risk] || RISK_STYLES.LOW;
                    return (
                      <div key={idx} className="flex items-center justify-between gap-2">
                        <span className="text-xs text-slate-300 truncate">{dr.disease || dr.name}</span>
                        <span className={`shrink-0 inline-block px-2 py-0.5 rounded-full text-[10px] font-medium border ${rs}`}>
                          {risk}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No disease risks identified</p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-12 text-sm text-slate-500">
            No weather data available for this shop
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Climate Risk Card ──────────────────────────────
function ClimateCard({ title, value, icon: Icon, riskKey }) {
  const style = RISK_STYLES[riskKey] || 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
  const iconStyle = RISK_ICON_STYLES[riskKey] || 'bg-indigo-500/15 text-indigo-400';
  const isHighlighted = riskKey === 'CRITICAL' || riskKey === 'HIGH';

  return (
    <div className={`bg-slate-900/80 border ${isHighlighted ? style : 'border-slate-700/50'} rounded-xl p-5 transition-all duration-200`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-white mt-2">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-lg ${iconStyle} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
