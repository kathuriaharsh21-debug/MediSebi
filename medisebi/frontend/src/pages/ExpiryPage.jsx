import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import {
  Clock, AlertTriangle, Shield, RefreshCw, Filter, ChevronLeft, ChevronRight,
  Loader2, Activity, Package,
} from 'lucide-react';
import { expiryAPI, shopsAPI, saltsAPI } from '../services/api';

const PIE_COLORS = ['#EF4444', '#F59E0B', '#10B981', '#4F46E5', '#8B5CF6', '#06B6D4', '#F97316', '#EC4899'];

const SEVERITY_STYLES = {
  EXPIRED: 'bg-red-500/10 text-red-400 border-red-500/30',
  URGENT: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  WARNING: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  SAFE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
};

const SEVERITY_ICON_COLORS = {
  EXPIRED: 'bg-red-500/15 text-red-400',
  URGENT: 'bg-orange-500/15 text-orange-400',
  WARNING: 'bg-yellow-500/15 text-yellow-400',
  SAFE: 'bg-emerald-500/15 text-emerald-400',
};

export default function ExpiryPage() {
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [shops, setShops] = useState([]);
  const [saltCategories, setSaltCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [shopFilter, setShopFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 15;

  useEffect(() => {
    fetchShops();
    fetchSaltCategories();
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchItems();
  }, [page, shopFilter, severityFilter, categoryFilter]);

  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (e) {
      console.error('Failed to fetch shops:', e);
    }
  };

  const fetchSaltCategories = async () => {
    try {
      const { data } = await saltsAPI.list({ size: 200 });
      const cats = [...new Set((data?.items || []).map((s) => s.category || s.name).filter(Boolean))];
      setSaltCategories(cats);
    } catch (e) {
      console.error('Failed to fetch salt categories:', e);
    }
  };

  const fetchSummary = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await expiryAPI.summary();
      setSummary(data || {});
    } catch (e) {
      console.error('Failed to fetch expiry summary:', e);
      setError('Failed to load expiry summary.');
    } finally {
      setLoading(false);
    }
  };

  const fetchItems = async () => {
    setItemsLoading(true);
    try {
      const params = { page, size: pageSize };
      if (shopFilter) params.shop_id = shopFilter;
      if (severityFilter) params.severity = severityFilter;
      if (categoryFilter) params.category = categoryFilter;
      const { data } = await expiryAPI.items(params);
      setItems(data?.items || data || []);
      setTotal(data?.total || (Array.isArray(data) ? data.length : 0));
    } catch (e) {
      console.error('Failed to fetch expiry items:', e);
    } finally {
      setItemsLoading(false);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    setError('');
    try {
      await expiryAPI.scan();
      await fetchSummary();
      setPage(1);
      await fetchItems();
    } catch (e) {
      console.error('Scan failed:', e);
      setError('Expiry scan failed. Please try again.');
    } finally {
      setScanning(false);
    }
  };

  // Chart data from summary
  const shopChartData = useMemo(() => {
    if (!summary?.by_shop) return [];
    return summary.by_shop.map((s) => ({
      name: s.shop_name || `Shop #${s.shop_id}`,
      expired: s.expired || 0,
      urgent: s.urgent || 0,
      warning: s.warning || 0,
    }));
  }, [summary]);

  const categoryChartData = useMemo(() => {
    if (!summary?.by_category) return [];
    return summary.by_category.map((c) => ({
      name: c.category || c.name || 'Other',
      value: c.count || c.total || 0,
    }));
  }, [summary]);

  const totalPages = Math.ceil(total / pageSize);

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
            <Clock className="w-6 h-6 text-indigo-400" />
            Expiry Watchdog
          </h1>
          <p className="text-sm text-slate-400 mt-1">Monitor and manage medicine expiry across all shops</p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
        >
          {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {scanning ? 'Scanning...' : 'Run Scan'}
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
        <ExpiryCard
          title="Total Items"
          value={summary?.total_items ?? summary?.total ?? 0}
          icon={Package}
          colorKey="total"
        />
        <ExpiryCard
          title="Expired"
          value={summary?.expired ?? summary?.expired_count ?? 0}
          icon={AlertTriangle}
          colorKey="EXPIRED"
        />
        <ExpiryCard
          title="Urgent"
          value={summary?.urgent ?? summary?.urgent_count ?? 0}
          icon={Clock}
          colorKey="URGENT"
        />
        <ExpiryCard
          title="Warning"
          value={summary?.warning ?? summary?.warning_count ?? 0}
          icon={Shield}
          colorKey="WARNING"
        />
        <ExpiryCard
          title="Safe"
          value={summary?.safe ?? summary?.safe_count ?? 0}
          icon={Shield}
          colorKey="SAFE"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity by Shop Bar Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Severity by Shop
          </h3>
          {shopChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={shopChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="expired" name="Expired" fill="#EF4444" radius={[2, 2, 0, 0]} />
                <Bar dataKey="urgent" name="Urgent" fill="#F97316" radius={[2, 2, 0, 0]} />
                <Bar dataKey="warning" name="Warning" fill="#EAB308" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No shop severity data available
            </div>
          )}
        </div>

        {/* Category Pie Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Package className="w-4 h-4 text-emerald-400" />
            Severity by Category
          </h3>
          {categoryChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={{ stroke: '#475569' }}
                >
                  {categoryChartData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No category data available
            </div>
          )}
        </div>
      </div>

      {/* Filter Controls */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Filters</span>
        </div>
        <div className="flex flex-wrap gap-3">
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
          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <option value="">All Severities</option>
            <option value="expired">Expired</option>
            <option value="urgent">Urgent</option>
            <option value="warning">Warning</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <option value="">All Categories</option>
            {saltCategories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          {(shopFilter || severityFilter || categoryFilter) && (
            <button
              onClick={() => { setShopFilter(''); setSeverityFilter(''); setCategoryFilter(''); setPage(1); }}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Expiring Items Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/50">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Expiring Items
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Brand Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Salt</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Shop</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Batch</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Expiry Date</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {itemsLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-sm text-slate-500">
                    No expiring items found
                  </td>
                </tr>
              ) : (
                items.map((item, idx) => {
                  const severity = (item.severity || item.category || 'SAFE').toUpperCase();
                  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.SAFE;
                  return (
                    <tr key={item.id || idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 text-sm font-medium text-slate-200">
                        {item.brand_name || `#${item.med_id || item.medicine_id}`}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {item.salt_name || item.salt || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {item.shop_name || `#${item.shop_id}`}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400 font-mono">
                        {item.batch_number || item.batch || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-slate-200">
                        {item.quantity ?? item.qty ?? 0}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-slate-400">
                        {formatDate(item.expiry_date)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${style}`}>
                          {severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${style}`}>
                          {(item.severity || 'SAFE').toUpperCase()}
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

// ─── Expiry Summary Card ──────────────────────────────
function ExpiryCard({ title, value, icon: Icon, colorKey }) {
  const style = SEVERITY_STYLES[colorKey] || 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
  const iconStyle = SEVERITY_ICON_COLORS[colorKey] || 'bg-indigo-500/15 text-indigo-400';

  return (
    <div className={`bg-slate-900/80 border ${colorKey === 'EXPIRED' || colorKey === 'URGENT' ? style : 'border-slate-700/50'} rounded-xl p-5 transition-all duration-200`}>
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
