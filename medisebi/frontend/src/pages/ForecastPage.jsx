import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  TrendingUp, AlertTriangle, Shield, RefreshCw, Filter,
  ChevronLeft, ChevronRight, Loader2, Activity, X,
} from 'lucide-react';
import { forecastAPI, shopsAPI } from '../services/api';

const STATUS_STYLES = {
  DEFICIT: 'bg-red-500/10 text-red-400 border-red-500/30',
  CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/30',
  OK: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  SURPLUS: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
};

export default function ForecastPage() {
  const [summary, setSummary] = useState(null);
  const [topDeficits, setTopDeficits] = useState([]);
  const [shops, setShops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deficitsLoading, setDeficitsLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [shopFilter, setShopFilter] = useState('');
  const [deficitOnly, setDeficitOnly] = useState(false);
  const [confidenceMin, setConfidenceMin] = useState(0);

  // Pagination
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 15;

  useEffect(() => {
    fetchShops();
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchTopDeficits();
  }, [page, shopFilter, deficitOnly, confidenceMin]);

  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (e) {
      console.error('Failed to fetch shops:', e);
    }
  };

  const fetchSummary = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await forecastAPI.summary();
      setSummary(data || {});
    } catch (e) {
      console.error('Failed to fetch forecast summary:', e);
      setError('Failed to load forecast summary.');
    } finally {
      setLoading(false);
    }
  };

  const fetchTopDeficits = async () => {
    setDeficitsLoading(true);
    try {
      const params = { page, size: pageSize };
      if (shopFilter) params.shop_id = shopFilter;
      if (deficitOnly) params.deficit_only = 'true';
      if (confidenceMin > 0) params.confidence_min = confidenceMin;
      const { data } = await forecastAPI.topDeficits(params);
      setTopDeficits(data?.items || data || []);
      setTotal(data?.total || (Array.isArray(data) ? data.length : 0));
    } catch (e) {
      console.error('Failed to fetch top deficits:', e);
    } finally {
      setDeficitsLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      await forecastAPI.generate();
      await fetchSummary();
      setPage(1);
      await fetchTopDeficits();
    } catch (e) {
      console.error('Forecast generation failed:', e);
      setError('Forecast generation failed. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  // Shop breakdown chart data
  const shopChartData = useMemo(() => {
    if (!summary?.shop_breakdown) return [];
    return summary.shop_breakdown.map((s) => ({
      name: s.shop_name || `Shop #${s.shop_id}`,
      deficit: s.deficit || s.deficit_count || 0,
      ok: s.ok || s.ok_count || 0,
      critical: s.critical || s.critical_count || 0,
    }));
  }, [summary]);

  const totalPages = Math.ceil(total / pageSize);

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

  const getConfidenceColor = (confidence) => {
    if (confidence == null) return 'bg-slate-600';
    if (confidence >= 0.8) return 'bg-emerald-500';
    if (confidence >= 0.6) return 'bg-amber-500';
    return 'bg-red-500';
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
            <TrendingUp className="w-6 h-6 text-indigo-400" />
            Demand Forecasting
          </h1>
          <p className="text-sm text-slate-400 mt-1">AI-powered demand predictions and deficit analysis</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
        >
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {generating ? 'Generating...' : 'Generate Forecasts'}
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

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <ForecastCard
          title="Total Items"
          value={summary?.total_items ?? summary?.total ?? 0}
          icon={Activity}
          colorKey="indigo"
        />
        <ForecastCard
          title="OK Items"
          value={summary?.ok_items ?? summary?.ok_count ?? 0}
          icon={Shield}
          colorKey="emerald"
        />
        <ForecastCard
          title="Deficit Items"
          value={summary?.deficit_items ?? summary?.deficit_count ?? 0}
          icon={AlertTriangle}
          colorKey="orange"
          highlight={!!(summary?.deficit_items ?? summary?.deficit_count)}
        />
        <ForecastCard
          title="Critical Items"
          value={summary?.critical_items ?? summary?.critical_count ?? 0}
          icon={AlertTriangle}
          colorKey="red"
          highlight={!!(summary?.critical_items ?? summary?.critical_count)}
        />
        <ForecastCard
          title="Overall Deficit"
          value={summary?.overall_deficit ?? 0}
          icon={TrendingUp}
          colorKey="red"
          highlight={!!(summary?.overall_deficit && summary.overall_deficit > 0)}
        />
      </div>

      {/* Shop Breakdown Chart */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          Shop Deficit Breakdown
        </h3>
        {shopChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={shopChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="critical" name="Critical" fill="#EF4444" radius={[2, 2, 0, 0]} />
              <Bar dataKey="deficit" name="Deficit" fill="#F97316" radius={[2, 2, 0, 0]} />
              <Bar dataKey="ok" name="OK" fill="#10B981" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
            No shop breakdown data available. Click "Generate Forecasts" to get started.
          </div>
        )}
      </div>

      {/* Filter Controls */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Filters</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={shopFilter}
            onChange={(e) => { setShopFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <option value="">All Shops</option>
            {shops.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <label className="inline-flex items-center gap-2 px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg cursor-pointer hover:border-slate-500 transition-colors">
            <input
              type="checkbox"
              checked={deficitOnly}
              onChange={(e) => { setDeficitOnly(e.target.checked); setPage(1); }}
              className="w-4 h-4 rounded border-slate-600 text-red-500 focus:ring-red-500/50 bg-slate-700"
            />
            <span className="text-sm text-slate-300">Deficit Only</span>
          </label>

          <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg">
            <span className="text-xs text-slate-400 whitespace-nowrap">Min Confidence</span>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={confidenceMin * 100}
              onChange={(e) => { setConfidenceMin(parseInt(e.target.value) / 100); setPage(1); }}
              className="w-24 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
            <span className="text-xs text-indigo-400 font-medium w-8 text-right">{Math.round(confidenceMin * 100)}%</span>
          </div>

          {(shopFilter || deficitOnly || confidenceMin > 0) && (
            <button
              onClick={() => { setShopFilter(''); setDeficitOnly(false); setConfidenceMin(0); setPage(1); }}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Top Deficit Items Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/50">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Top Deficit Items
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Shop</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">City</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Predicted 7d</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Current Stock</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Deficit</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Confidence</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {deficitsLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : topDeficits.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-sm text-slate-500">
                    No deficit items found
                  </td>
                </tr>
              ) : (
                topDeficits.map((item, idx) => {
                  const status = (item.status || 'OK').toUpperCase();
                  const statusStyle = STATUS_STYLES[status] || STATUS_STYLES.OK;
                  const confidence = item.confidence ?? item.confidence_score ?? 0;
                  const confidencePct = Math.round(confidence * 100);
                  return (
                    <tr key={item.id || idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-slate-200">
                          {item.medicine_name || item.brand_name || item.name || `#${item.med_id || item.medicine_id}`}
                        </p>
                        <p className="text-xs text-slate-500">{item.salt_name || item.salt || ''}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {item.shop_name || `#${item.shop_id}`}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {item.city || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-indigo-400">
                        {item.predicted_7d ?? item.predicted_demand ?? item.forecasted_demand ?? 0}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-slate-300">
                        {item.current_stock ?? item.stock ?? 0}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        <span className={`font-medium ${status === 'DEFICIT' || status === 'CRITICAL' ? 'text-red-400' : 'text-emerald-400'}`}>
                          {item.deficit ?? 0}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden max-w-[100px]">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${getConfidenceColor(confidence)}`}
                              style={{ width: `${confidencePct}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400 w-8">{confidencePct}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${statusStyle}`}>
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/50">
            <p className="text-xs text-slate-500">
              Showing {((page - 1) * pageSize) + 1}&ndash;{Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                if (pageNum > totalPages) return null;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                      pageNum === page
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Forecast Summary Card ──────────────────────────────
function ForecastCard({ title, value, icon: Icon, colorKey, highlight }) {
  const colorMap = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  };

  const iconColorMap = {
    indigo: 'bg-indigo-500/15 text-indigo-400',
    red: 'bg-red-500/15 text-red-400',
    orange: 'bg-orange-500/15 text-orange-400',
    amber: 'bg-amber-500/15 text-amber-400',
    emerald: 'bg-emerald-500/15 text-emerald-400',
  };

  return (
    <div className={`bg-slate-900/80 border ${highlight ? colorMap[colorKey] : 'border-slate-700/50'} rounded-xl p-5 transition-all duration-200`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-white mt-2">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
        <div className={`w-10 h-10 rounded-lg ${iconColorMap[colorKey]} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
