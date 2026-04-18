import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import {
  Package, AlertTriangle, Clock, Store, TrendingDown, Activity,
  Loader2, Shield,
} from 'lucide-react';
import { inventoryAPI, medicinesAPI, shopsAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const PIE_COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#EC4899'];

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState({
    medicines: [],
    shops: [],
    inventory: [],
    expiringAlerts: [],
    lowStockAlerts: [],
  });
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalMedicines: 0,
    lowStockCount: 0,
    expiringCount: 0,
    totalShops: 0,
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [medsRes, shopsRes, invRes, expRes, lowRes] = await Promise.allSettled([
        medicinesAPI.list({ size: 200 }),
        shopsAPI.list({ size: 100 }),
        inventoryAPI.list({ size: 200 }),
        inventoryAPI.expiringAlerts({ expiring_within_days: 30 }),
        inventoryAPI.lowStockAlerts(),
      ]);

      const medicines = medsRes.status === 'fulfilled' ? medsRes.value.data?.items || [] : [];
      const shops = shopsRes.status === 'fulfilled' ? shopsRes.value.data?.items || [] : [];
      const inventory = invRes.status === 'fulfilled' ? invRes.value.data?.items || [] : [];
      const expiringAlerts = expRes.status === 'fulfilled' ? (Array.isArray(expRes.value.data) ? expRes.value.data : []) : [];
      const lowStockAlerts = lowRes.status === 'fulfilled' ? (Array.isArray(lowRes.value.data) ? lowRes.value.data : []) : [];

      setData({ medicines, shops, inventory, expiringAlerts, lowStockAlerts });
      setStats({
        totalMedicines: medicines.length,
        lowStockCount: lowStockAlerts.length,
        expiringCount: Array.isArray(expiringAlerts) ? expiringAlerts.length : 0,
        totalShops: shops.length,
      });
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Bar chart data: stock by shop
  const shopChartData = (() => {
    const shopMap = {};
    data.inventory.forEach((item) => {
      const name = item.shop_name || `Shop #${item.shop_id}`;
      shopMap[name] = (shopMap[name] || 0) + (item.quantity || 0);
    });
    return Object.entries(shopMap)
      .map(([name, total]) => ({ name, total }))
      .sort((a, b) => b.total - a.total);
  })();

  // Pie chart data: medicine categories via salt
  const categoryData = (() => {
    const catMap = {};
    data.medicines.forEach((med) => {
      // We don't have category directly on medicine, use generic salt_name info
      const salt = med.salt_name || 'Other';
      catMap[salt] = (catMap[salt] || 0) + 1;
    });
    return Object.entries(catMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  })();

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

  const getExpiryRowColor = (expiryDate) => {
    if (!expiryDate) return '';
    const now = new Date();
    const expiry = new Date(expiryDate);
    const daysUntil = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
    if (daysUntil < 0) return 'bg-red-500/10 border-l-2 border-l-red-500';
    if (daysUntil <= 7) return 'bg-red-500/10 border-l-2 border-l-red-500';
    if (daysUntil <= 30) return 'bg-amber-500/10 border-l-2 border-l-amber-500';
    return '';
  };

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Welcome back, {user?.full_name || 'User'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs font-medium text-indigo-400">
            <Shield className="w-3.5 h-3.5" />
            {user?.role?.toUpperCase() || 'USER'}
          </span>
          <span className="text-xs text-slate-500">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Total Medicines"
          value={stats.totalMedicines}
          icon={Package}
          color="indigo"
          subtitle="Registered products"
        />
        <SummaryCard
          title="Low Stock Alerts"
          value={stats.lowStockCount}
          icon={TrendingDown}
          color="red"
          subtitle={stats.lowStockCount > 0 ? 'Requires attention' : 'All stocked up'}
          highlight={stats.lowStockCount > 0}
        />
        <SummaryCard
          title="Expiring Soon"
          value={stats.expiringCount}
          icon={Clock}
          color="amber"
          subtitle="Within 30 days"
          highlight={stats.expiringCount > 0}
        />
        <SummaryCard
          title="Total Shops"
          value={stats.totalShops}
          icon={Store}
          color="emerald"
          subtitle="Active locations"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart - Stock by Shop */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Stock Distribution by Shop
          </h3>
          {shopChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={shopChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="total" name="Total Stock" fill="#4F46E5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No inventory data available
            </div>
          )}
        </div>

        {/* Pie Chart - Medicine Categories */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Package className="w-4 h-4 text-emerald-400" />
            Medicine Salt Distribution
          </h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={{ stroke: '#475569' }}
                >
                  {categoryData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No medicine data available
            </div>
          )}
        </div>
      </div>

      {/* Alerts Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expiring Soon */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Expiring Soon
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium">
              {stats.expiringCount} items
            </span>
          </h3>
          <div className="max-h-80 overflow-y-auto space-y-2">
            {data.expiringAlerts.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-8">No items expiring within 30 days</p>
            ) : (
              data.expiringAlerts.slice(0, 20).map((item, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-3 rounded-lg ${getExpiryRowColor(item.expiry_date)}`}
                >
                  <div>
                    <p className="text-sm font-medium text-slate-200">{item.brand_name || `Med #${item.med_id}`}</p>
                    <p className="text-xs text-slate-400">{item.shop_name || `Shop #${item.shop_id}`}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-300">{item.quantity} units</p>
                    <p className="text-xs text-slate-500">{formatDate(item.expiry_date)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Low Stock */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            Low Stock Alerts
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 font-medium">
              {stats.lowStockCount} items
            </span>
          </h3>
          <div className="max-h-80 overflow-y-auto space-y-2">
            {data.lowStockAlerts.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-8">All items are above reorder level</p>
            ) : (
              data.lowStockAlerts.slice(0, 20).map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-red-500/5 border-l-2 border-l-red-500"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-200">{item.brand_name || `Med #${item.med_id}`}</p>
                    <p className="text-xs text-slate-400">{item.shop_name || `Shop #${item.shop_id}`}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-red-400">{item.quantity} units</p>
                    <p className="text-xs text-slate-500">
                      {item.reorder_level ? `Reorder: ${item.reorder_level}` : 'Below threshold'}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity / Inventory Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Package className="w-4 h-4 text-indigo-400" />
          Recent Inventory Overview
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wider">
                <th className="text-left pb-3 px-3">Medicine</th>
                <th className="text-left pb-3 px-3">Shop</th>
                <th className="text-left pb-3 px-3">Salt</th>
                <th className="text-right pb-3 px-3">Qty</th>
                <th className="text-right pb-3 px-3">Price</th>
                <th className="text-right pb-3 px-3">Expiry</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {data.inventory.slice(0, 15).map((item) => (
                <tr key={item.id} className={`${getExpiryRowColor(item.expiry_date)} hover:bg-slate-800/30 transition-colors`}>
                  <td className="py-3 px-3 text-sm font-medium text-slate-200">{item.brand_name || `#${item.med_id}`}</td>
                  <td className="py-3 px-3 text-sm text-slate-400">{item.shop_name || `#${item.shop_id}`}</td>
                  <td className="py-3 px-3 text-sm text-slate-400">{item.salt_name || '—'}</td>
                  <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">{item.quantity}</td>
                  <td className="py-3 px-3 text-sm text-right text-slate-400">{item.selling_price != null ? `₹${item.selling_price}` : '—'}</td>
                  <td className="py-3 px-3 text-sm text-right text-slate-400">{formatDate(item.expiry_date)}</td>
                </tr>
              ))}
              {data.inventory.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                    No inventory data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Summary Card Component ──────────────────────
function SummaryCard({ title, value, icon: Icon, color, subtitle, highlight }) {
  const colorMap = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  };

  const iconColorMap = {
    indigo: 'bg-indigo-500/15 text-indigo-400',
    red: 'bg-red-500/15 text-red-400',
    amber: 'bg-amber-500/15 text-amber-400',
    emerald: 'bg-emerald-500/15 text-emerald-400',
  };

  return (
    <div className={`bg-slate-900/80 border ${highlight ? colorMap[color] : 'border-slate-700/50'} rounded-xl p-5 transition-all duration-200`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
          <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
        </div>
        <div className={`w-10 h-10 rounded-lg ${iconColorMap[color]} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
