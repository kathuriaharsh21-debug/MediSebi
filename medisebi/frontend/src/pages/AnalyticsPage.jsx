import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, Legend, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import {
  BarChart3, TrendingUp, TrendingDown, ShoppingBag, Package, Calendar,
  Loader2, Filter, AlertTriangle, Zap, Sun, CloudRain, Snowflake, Leaf,
  ChevronLeft, ChevronRight, RefreshCw, ArrowUpRight, Activity,
} from 'lucide-react';
import { analyticsAPI, shopsAPI } from '../services/api';

// ─── Constants ──────────────────────────────────────────
const SEASON_COLORS = {
  Winter: '#3B82F6',
  Spring: '#10B981',
  Summer: '#F59E0B',
  Monsoon: '#6366F1',
};

const SEASON_ICONS = {
  Winter: Snowflake,
  Spring: Leaf,
  Summer: Sun,
  Monsoon: CloudRain,
};

const SEASONS = ['Winter', 'Spring', 'Summer', 'Monsoon'];

const PRIORITY_STYLES = {
  HIGH: 'bg-red-500/15 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  LOW: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
};

const TABS = [
  { id: 'seasonal', label: 'Seasonal Trends', icon: BarChart3 },
  { id: 'frequency', label: 'Medicine Frequency', icon: Activity },
  { id: 'ordering', label: 'Ordering Guide', icon: ShoppingBag },
  { id: 'comparison', label: 'Season Comparison', icon: TrendingUp },
];

const YEARS = [2026, 2025, 2024];

// ─── Custom Tooltip ─────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-600/50 rounded-lg p-3 shadow-xl">
      <p className="text-sm text-slate-300 font-medium mb-1">{label}</p>
      {payload.map((entry, idx) => (
        <p key={idx} className="text-sm" style={{ color: entry.color || entry.fill }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </div>
  );
}

// ─── Helper: format currency ────────────────────────────
function formatCurrency(val) {
  if (val == null) return '—';
  if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
  if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
  return `₹${val.toLocaleString()}`;
}

function formatNumber(val) {
  if (val == null) return '—';
  return val.toLocaleString();
}

// ─── Season pill component ──────────────────────────────
function SeasonPill({ season, size = 'sm' }) {
  const colors = {
    Winter: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    Spring: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    Summer: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    Monsoon: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
  };
  const sizeClasses = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${colors[season] || ''} ${sizeClasses}`}>
      {season}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════
export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState('seasonal');

  // ── Shared state ──
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState('');
  const [loadingShops, setLoadingShops] = useState(false);

  // ── Tab 1: Seasonal Trends ──
  const [seasonalYear, setSeasonalYear] = useState(2026);
  const [seasonalData, setSeasonalData] = useState(null);
  const [loadingSeasonal, setLoadingSeasonal] = useState(false);

  // ── Tab 2: Medicine Frequency ──
  const [freqSeason, setFreqSeason] = useState('');
  const [freqSort, setFreqSort] = useState('total_units_sold');
  const [freqPage, setFreqPage] = useState(1);
  const [freqData, setFreqData] = useState(null);
  const [loadingFreq, setLoadingFreq] = useState(false);

  // ── Tab 3: Ordering Guide ──
  const [orderData, setOrderData] = useState(null);
  const [loadingOrder, setLoadingOrder] = useState(false);

  // Fetch shops on mount
  useEffect(() => {
    const fetchShops = async () => {
      setLoadingShops(true);
      try {
        const res = await shopsAPI.list({ size: 100 });
        setShops(res.data?.items || []);
      } catch (err) {
        console.error('Failed to fetch shops:', err);
      } finally {
        setLoadingShops(false);
      }
    };
    fetchShops();
  }, []);

  // Fetch seasonal data when tab/year/shop changes
  useEffect(() => {
    if (activeTab !== 'seasonal') return;
    const fetchSeasonal = async () => {
      setLoadingSeasonal(true);
      try {
        const params = { year: seasonalYear };
        if (selectedShop) params.shop_id = selectedShop;
        const res = await analyticsAPI.seasonal(params);
        setSeasonalData(res.data);
      } catch (err) {
        console.error('Failed to fetch seasonal data:', err);
        setSeasonalData(null);
      } finally {
        setLoadingSeasonal(false);
      }
    };
    fetchSeasonal();
  }, [activeTab, seasonalYear, selectedShop]);

  // Fetch frequency data
  useEffect(() => {
    if (activeTab !== 'frequency') return;
    const fetchFreq = async () => {
      setLoadingFreq(true);
      try {
        const params = { page: freqPage, size: 20, sort_by: freqSort, sort_dir: 'desc' };
        if (selectedShop) params.shop_id = selectedShop;
        if (freqSeason) params.season = freqSeason;
        const res = await analyticsAPI.frequency(params);
        setFreqData(res.data);
      } catch (err) {
        console.error('Failed to fetch frequency data:', err);
        setFreqData(null);
      } finally {
        setLoadingFreq(false);
      }
    };
    fetchFreq();
  }, [activeTab, freqPage, freqSort, freqSeason, selectedShop]);

  // Fetch ordering guide data
  useEffect(() => {
    if (activeTab !== 'ordering') return;
    const fetchOrder = async () => {
      setLoadingOrder(true);
      try {
        const params = {};
        if (selectedShop) params.shop_id = selectedShop;
        const res = await analyticsAPI.orderingGuide(params);
        setOrderData(res.data);
      } catch (err) {
        console.error('Failed to fetch ordering guide:', err);
        setOrderData(null);
      } finally {
        setLoadingOrder(false);
      }
    };
    fetchOrder();
  }, [activeTab, selectedShop]);

  // Reset page when filters change for frequency tab
  useEffect(() => {
    setFreqPage(1);
  }, [freqSort, freqSeason, selectedShop]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-indigo-400" />
            Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Sales trends, medicine frequency &amp; seasonal insights
          </p>
        </div>

        {/* Global Shop Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={selectedShop}
            onChange={(e) => setSelectedShop(e.target.value)}
            className="bg-slate-800/80 border border-slate-700/50 text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          >
            <option value="">All Shops</option>
            {shops.map((s) => (
              <option key={s.id || s.shop_id} value={s.id || s.shop_id}>
                {s.name || s.shop_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-700/50 rounded-xl p-1 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-150 ${
              activeTab === id
                ? 'bg-indigo-600/20 text-indigo-400 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'seasonal' && (
        <SeasonalTrendsTab
          data={seasonalData}
          loading={loadingSeasonal}
          year={seasonalYear}
          setYear={setSeasonalYear}
        />
      )}
      {activeTab === 'frequency' && (
        <MedicineFrequencyTab
          data={freqData}
          loading={loadingFreq}
          season={freqSeason}
          setSeason={setFreqSeason}
          sort={freqSort}
          setSort={setFreqSort}
          page={freqPage}
          setPage={setFreqPage}
        />
      )}
      {activeTab === 'ordering' && (
        <OrderingGuideTab data={orderData} loading={loadingOrder} />
      )}
      {activeTab === 'comparison' && (
        <SeasonComparisonTab data={seasonalData} loading={loadingSeasonal} />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Tab 1: Seasonal Trends
// ═══════════════════════════════════════════════════════════
function SeasonalTrendsTab({ data, loading, year, setYear }) {
  const monthlyTrend = data?.monthly_trend || [];
  const seasonTotals = data?.season_totals || {};
  const topMedicines = data?.top_medicines_by_season?.top_overall || [];

  // Build bar chart data with season color
  const revenueChartData = monthlyTrend.map((m) => ({
    name: m.month,
    Revenue: m.total_sales,
    fill: SEASON_COLORS[m.season] || '#64748b',
    season: m.season,
  }));

  const unitsChartData = monthlyTrend.map((m) => ({
    name: m.month,
    Units: m.total_units,
    Bills: m.bill_count,
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Year Selector */}
      <div className="flex items-center gap-3">
        <Calendar className="w-4 h-4 text-slate-400" />
        <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-700/50 rounded-lg p-1">
          {YEARS.map((y) => (
            <button
              key={y}
              onClick={() => setYear(y)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                year === y
                  ? 'bg-indigo-600/20 text-indigo-400'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {y}
            </button>
          ))}
        </div>
        {data?.period && (
          <span className="text-xs text-slate-500">Showing data for {data.period}</span>
        )}
      </div>

      {/* Season Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {SEASONS.map((season) => {
          const totals = seasonTotals[season] || {};
          const Icon = SEASON_ICONS[season];
          const color = SEASON_COLORS[season];
          const bgMap = {
            Winter: 'from-blue-500/10 to-blue-500/5 border-blue-500/20',
            Spring: 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20',
            Summer: 'from-amber-500/10 to-amber-500/5 border-amber-500/20',
            Monsoon: 'from-indigo-500/10 to-indigo-500/5 border-indigo-500/20',
          };
          const iconBgMap = {
            Winter: 'bg-blue-500/15 text-blue-400',
            Spring: 'bg-emerald-500/15 text-emerald-400',
            Summer: 'bg-amber-500/15 text-amber-400',
            Monsoon: 'bg-indigo-500/15 text-indigo-400',
          };

          return (
            <div
              key={season}
              className={`bg-gradient-to-br ${bgMap[season]} border rounded-xl p-5 transition-all duration-200 hover:shadow-lg`}
            >
              <div className="flex items-center justify-between mb-3">
                <SeasonPill season={season} size="md" />
                <div className={`w-8 h-8 rounded-lg ${iconBgMap[season]} flex items-center justify-center`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <p className="text-2xl font-bold text-white">{formatCurrency(totals.total_sales)}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className="text-xs text-slate-400">
                  <Package className="w-3 h-3 inline mr-1" />
                  {formatNumber(totals.total_units)} units
                </span>
                <span className="text-xs text-slate-400">
                  <ShoppingBag className="w-3 h-3 inline mr-1" />
                  {formatNumber(totals.bill_count)} bills
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Revenue Bar Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-indigo-400" />
            Monthly Revenue
          </h3>
          <p className="text-xs text-slate-500 mb-4">Color-coded by season</p>
          {revenueChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={revenueChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="Revenue" radius={[4, 4, 0, 0]}>
                  {revenueChartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
          {/* Season Legend */}
          <div className="flex items-center justify-center gap-4 mt-3">
            {SEASONS.map((s) => (
              <div key={s} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: SEASON_COLORS[s] }} />
                <span className="text-xs text-slate-400">{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Monthly Units Area Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            Monthly Units Sold
          </h3>
          <p className="text-xs text-slate-500 mb-4">Trend across the year</p>
          {unitsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={unitsChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="unitsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="billsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="Units" stroke="#10B981" fill="url(#unitsGradient)" strokeWidth={2} />
                <Area type="monotone" dataKey="Bills" stroke="#6366F1" fill="url(#billsGradient)" strokeWidth={2} />
                <Legend
                  wrapperStyle={{ paddingTop: '12px' }}
                  formatter={(value) => <span className="text-xs text-slate-400">{value}</span>}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
        </div>
      </div>

      {/* Top Medicines Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          Top Medicines — Overall
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 font-medium">
            Top {topMedicines.length}
          </span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wider">
                <th className="text-left pb-3 px-3">#</th>
                <th className="text-left pb-3 px-3">Medicine</th>
                <th className="text-right pb-3 px-3">Units Sold</th>
                <th className="text-right pb-3 px-3">Revenue</th>
                <th className="text-right pb-3 px-3 w-32">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {topMedicines.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                    No data available
                  </td>
                </tr>
              ) : (
                topMedicines.slice(0, 15).map((med, idx) => {
                  const maxRevenue = topMedicines[0]?.revenue || 1;
                  const share = (med.revenue / maxRevenue) * 100;
                  return (
                    <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3 text-sm text-slate-500 font-mono">{idx + 1}</td>
                      <td className="py-3 px-3 text-sm font-medium text-slate-200">{med.name}</td>
                      <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                        {formatNumber(med.units_sold)}
                      </td>
                      <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                        {formatCurrency(med.revenue)}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                              style={{ width: `${share}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500 w-10 text-right">{share.toFixed(0)}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Tab 2: Medicine Frequency
// ═══════════════════════════════════════════════════════════
function MedicineFrequencyTab({ data, loading, season, setSeason, sort, setSort, page, setPage }) {
  const medicines = data?.medicines || [];
  const totalPages = data?.total ? Math.ceil(data.total / 20) : 1;

  // Top 3 summary cards
  const mostSold = useMemo(() => {
    if (!medicines.length) return null;
    return medicines.reduce((max, m) => (m.total_units_sold > (max?.total_units_sold || 0) ? m : max), medicines[0]);
  }, [medicines]);

  const highestRevenue = useMemo(() => {
    if (!medicines.length) return null;
    return medicines.reduce((max, m) => (m.total_revenue > (max?.total_revenue || 0) ? m : max), medicines[0]);
  }, [medicines]);

  const mostFrequent = useMemo(() => {
    if (!medicines.length) return null;
    return medicines.reduce((max, m) => (m.total_bills > (max?.total_bills || 0) ? m : max), medicines[0]);
  }, [medicines]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Filters:</span>
        </div>
        {/* Season Dropdown */}
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="bg-slate-800/80 border border-slate-700/50 text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
        >
          <option value="">All Seasons</option>
          {SEASONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {/* Sort Dropdown */}
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="bg-slate-800/80 border border-slate-700/50 text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
        >
          <option value="total_units_sold">Sort by Units Sold</option>
          <option value="total_revenue">Sort by Revenue</option>
          <option value="total_bills">Sort by Bill Count</option>
        </select>
      </div>

      {/* Top 3 Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Most Sold"
          subtitle={mostSold?.medicine_name || '—'}
          value={formatNumber(mostSold?.total_units_sold)}
          icon={Package}
          color="blue"
          extra={`${formatNumber(mostSold?.total_bills)} bills`}
        />
        <StatCard
          title="Highest Revenue"
          subtitle={highestRevenue?.medicine_name || '—'}
          value={formatCurrency(highestRevenue?.total_revenue)}
          icon={TrendingUp}
          color="emerald"
          extra={`${formatNumber(highestRevenue?.total_units_sold)} units`}
        />
        <StatCard
          title="Most Frequent"
          subtitle={mostFrequent?.medicine_name || '—'}
          value={`${formatNumber(mostFrequent?.total_bills)} bills`}
          icon={ShoppingBag}
          color="amber"
          extra={`Avg ${mostFrequent?.avg_quantity_per_bill?.toFixed(1) || 0} qty/bill`}
        />
      </div>

      {/* Full Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Medicine Frequency
          </h3>
          <span className="text-xs text-slate-500">
            {data?.total || 0} medicines total
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wider">
                <th className="text-left pb-3 px-3">Medicine</th>
                <th className="text-left pb-3 px-3">Salt</th>
                <th className="text-right pb-3 px-3">Units Sold</th>
                <th className="text-right pb-3 px-3">Revenue</th>
                <th className="text-right pb-3 px-3">Total Bills</th>
                <th className="text-right pb-3 px-3">Avg Qty/Bill</th>
                <th className="text-left pb-3 px-3">Season Breakdown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {medicines.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                    No frequency data available
                  </td>
                </tr>
              ) : (
                medicines.map((med) => (
                  <tr key={med.med_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 text-sm font-medium text-slate-200 max-w-[200px] truncate">
                      {med.medicine_name}
                    </td>
                    <td className="py-3 px-3 text-sm text-slate-400 max-w-[150px] truncate">
                      {med.salt_name}
                    </td>
                    <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                      {formatNumber(med.total_units_sold)}
                    </td>
                    <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                      {formatCurrency(med.total_revenue)}
                    </td>
                    <td className="py-3 px-3 text-sm text-right text-slate-300">
                      {formatNumber(med.total_bills)}
                    </td>
                    <td className="py-3 px-3 text-sm text-right text-slate-400">
                      {med.avg_quantity_per_bill?.toFixed(1) || '—'}
                    </td>
                    <td className="py-3 px-3">
                      <SeasonBreakdown breakdown={med.season_breakdown} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-800/50">
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 border border-slate-700/50 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-3 h-3" />
                Prev
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 border border-slate-700/50 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Season Breakdown mini-visual ────────────────────────
function SeasonBreakdown({ breakdown }) {
  if (!breakdown) return <span className="text-xs text-slate-500">—</span>;

  const maxVal = Math.max(...Object.values(breakdown), 1);

  return (
    <div className="flex items-center gap-1">
      {SEASONS.map((s) => {
        const val = breakdown[s] || 0;
        const width = Math.max(4, (val / maxVal) * 36);
        return (
          <div
            key={s}
            className="flex flex-col items-center gap-0.5"
            title={`${s}: ${val}`}
          >
            <div
              className="rounded-sm transition-all duration-300"
              style={{
                width: `${width}px`,
                height: '14px',
                backgroundColor: val > 0 ? SEASON_COLORS[s] : '#334155',
                opacity: val > 0 ? 1 : 0.4,
              }}
            />
            <span className="text-[9px] text-slate-500 leading-none">{val}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Stat Card (for frequency tab) ───────────────────────
function StatCard({ title, subtitle, value, icon: Icon, color, extra }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  };
  const iconClasses = {
    blue: 'bg-blue-500/15 text-blue-400',
    emerald: 'bg-emerald-500/15 text-emerald-400',
    amber: 'bg-amber-500/15 text-amber-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-5`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-xl font-bold text-white mt-1">{value}</p>
          <p className="text-xs text-slate-500 mt-1 truncate max-w-[200px]">{subtitle}</p>
          {extra && <p className="text-[11px] text-slate-500 mt-0.5">{extra}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg ${iconClasses[color]} flex items-center justify-center flex-shrink-0`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Tab 3: Ordering Guide
// ═══════════════════════════════════════════════════════════
function OrderingGuideTab({ data, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const currentSeason = data?.current_season || '—';
  const nextSeason = data?.next_season || '—';
  const currentMonth = data?.current_month || '—';
  const basedOnYear = data?.based_on_year || '—';
  const recommendations = data?.recommendations || [];

  const CurrentSeasonIcon = SEASON_ICONS[currentSeason] || Sun;
  const NextSeasonIcon = SEASON_ICONS[nextSeason] || CloudRain;

  const highCount = recommendations.filter((r) => r.priority === 'HIGH').length;
  const medCount = recommendations.filter((r) => r.priority === 'MEDIUM').length;
  const lowCount = recommendations.filter((r) => r.priority === 'LOW').length;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-indigo-500/10 via-slate-900/80 to-amber-500/10 border border-slate-700/50 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/15 flex items-center justify-center">
              <CurrentSeasonIcon className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Current Season</p>
              <p className="text-lg font-bold text-white">{currentSeason} &middot; {currentMonth}</p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-slate-500">
            <ArrowUpRight className="w-5 h-5" />
            <span className="text-sm font-medium">Prepare for</span>
          </div>
          <div className="flex sm:hidden items-center gap-2 text-slate-500">
            <ArrowUpRight className="w-4 h-4 rotate-90" />
          </div>

          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-amber-500/15 flex items-center justify-center">
              <NextSeasonIcon className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Next Season</p>
              <p className="text-lg font-bold text-white">{nextSeason}</p>
            </div>
          </div>

          <div className="sm:ml-auto">
            <p className="text-xs text-slate-500">Based on historical data from</p>
            <p className="text-sm font-medium text-slate-300">{basedOnYear}</p>
          </div>
        </div>
      </div>

      {/* Priority Summary */}
      {recommendations.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/15 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-400">{highCount}</p>
              <p className="text-xs text-slate-400">High Priority</p>
            </div>
          </div>
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/15 flex items-center justify-center">
              <Zap className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-400">{medCount}</p>
              <p className="text-xs text-slate-400">Medium Priority</p>
            </div>
          </div>
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/15 flex items-center justify-center">
              <RefreshCw className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-400">{lowCount}</p>
              <p className="text-xs text-slate-400">Low Priority</p>
            </div>
          </div>
        </div>
      )}

      {/* Recommendation Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <ShoppingBag className="w-4 h-4 text-indigo-400" />
          Stocking Recommendations for {nextSeason}
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 font-medium">
            {recommendations.length} items
          </span>
        </h3>

        {recommendations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <CloudRain className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm font-medium">No historical data available</p>
            <p className="text-xs mt-1">Recommendations will appear once sales data for the upcoming season is available</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-slate-400 uppercase tracking-wider">
                  <th className="text-left pb-3 px-3">Medicine</th>
                  <th className="text-left pb-3 px-3">Salt</th>
                  <th className="text-right pb-3 px-3">Hist. Units</th>
                  <th className="text-right pb-3 px-3">Hist. Revenue</th>
                  <th className="text-center pb-3 px-3">Priority</th>
                  <th className="text-left pb-3 px-3">Suggested Action</th>
                  <th className="text-center pb-3 px-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {recommendations.map((rec, idx) => (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-800/30 transition-colors ${
                      rec.priority === 'HIGH' ? 'bg-red-500/[0.03]' : ''
                    }`}
                  >
                    <td className="py-3 px-3 text-sm font-medium text-slate-200">
                      {rec.medicine_name}
                    </td>
                    <td className="py-3 px-3 text-sm text-slate-400">{rec.salt_name}</td>
                    <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                      {formatNumber(rec.historical_units_sold)}
                    </td>
                    <td className="py-3 px-3 text-sm text-right text-slate-300 font-medium">
                      {formatCurrency(rec.historical_revenue)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${PRIORITY_STYLES[rec.priority]}`}>
                        {rec.priority === 'HIGH' && <AlertTriangle className="w-3 h-3" />}
                        {rec.priority === 'MEDIUM' && <Zap className="w-3 h-3" />}
                        {rec.priority}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-sm text-slate-400 max-w-[200px]">
                      {rec.suggested_action}
                    </td>
                    <td className="py-3 px-3 text-center">
                      {rec.priority === 'HIGH' ? (
                        <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-xs font-medium text-indigo-400 hover:bg-indigo-600/30 transition-colors">
                          <ShoppingBag className="w-3 h-3" />
                          Quick Order
                        </button>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Tab 4: Season Comparison
// ═══════════════════════════════════════════════════════════
function SeasonComparisonTab({ data, loading }) {
  const [seasonA, setSeasonA] = useState('Winter');
  const [seasonB, setSeasonB] = useState('Summer');

  const seasonTotals = data?.season_totals || {};

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  // Radar chart data: normalize values to 0-100 scale
  const a = seasonTotals[seasonA] || {};
  const b = seasonTotals[seasonB] || {};

  const maxSales = Math.max(a.total_sales || 0, b.total_sales || 0, 1);
  const maxUnits = Math.max(a.total_units || 0, b.total_units || 0, 1);
  const maxBills = Math.max(a.bill_count || 0, b.bill_count || 0, 1);

  const radarData = [
    {
      metric: 'Revenue',
      [seasonA]: Math.round(((a.total_sales || 0) / maxSales) * 100),
      [seasonB]: Math.round(((b.total_sales || 0) / maxSales) * 100),
    },
    {
      metric: 'Units Sold',
      [seasonA]: Math.round(((a.total_units || 0) / maxUnits) * 100),
      [seasonB]: Math.round(((b.total_units || 0) / maxUnits) * 100),
    },
    {
      metric: 'Bill Count',
      [seasonA]: Math.round(((a.bill_count || 0) / maxBills) * 100),
      [seasonB]: Math.round(((b.bill_count || 0) / maxBills) * 100),
    },
  ];

  // Side-by-side bar chart data
  const barData = [
    {
      metric: 'Revenue (₹)',
      [seasonA]: a.total_sales || 0,
      [seasonB]: b.total_sales || 0,
    },
    {
      metric: 'Units Sold',
      [seasonA]: a.total_units || 0,
      [seasonB]: b.total_units || 0,
    },
    {
      metric: 'Bills',
      [seasonA]: a.bill_count || 0,
      [seasonB]: b.bill_count || 0,
    },
  ];

  // Percentage differences
  const pctDiff = (aVal, bVal) => {
    if (!bVal) return aVal ? '∞' : '0';
    return (((aVal - bVal) / bVal) * 100).toFixed(1);
  };

  const salesDiff = pctDiff(a.total_sales, b.total_sales);
  const unitsDiff = pctDiff(a.total_units, b.total_units);
  const billsDiff = pctDiff(a.bill_count, b.bill_count);

  // Auto-generated key insights
  const insights = useMemo(() => {
    const items = [];

    if (a.total_sales && b.total_sales) {
      const higher = a.total_sales > b.total_sales ? seasonA : seasonB;
      const lower = a.total_sales > b.total_sales ? seasonB : seasonA;
      const diff = Math.abs(salesDiff);
      items.push({
        icon: TrendingUp,
        color: 'text-indigo-400',
        text: `${higher} has ${diff}% higher revenue than ${lower}`,
      });
    }

    if (a.total_units && b.total_units) {
      const higher = a.total_units > b.total_units ? seasonA : seasonB;
      const lower = a.total_units > b.total_units ? seasonB : seasonA;
      const diff = Math.abs(unitsDiff);
      items.push({
        icon: Package,
        color: 'text-emerald-400',
        text: `${higher} shows ${diff}% more units sold compared to ${lower}`,
      });
    }

    if (a.bill_count && b.bill_count) {
      const higher = a.bill_count > b.bill_count ? seasonA : seasonB;
      const lower = a.bill_count > b.bill_count ? seasonB : seasonA;
      const diff = Math.abs(billsDiff);
      items.push({
        icon: ShoppingBag,
        color: 'text-amber-400',
        text: `${higher} generated ${diff}% more bills than ${lower}`,
      });
    }

    return items;
  }, [seasonA, seasonB, a, b]);

  const aColor = SEASON_COLORS[seasonA] || '#3B82F6';
  const bColor = SEASON_COLORS[seasonB] || '#F59E0B';

  return (
    <div className="space-y-6">
      {/* Season Selectors */}
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-sm text-slate-400 font-medium">Compare:</span>
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: aColor }}
          />
          <select
            value={seasonA}
            onChange={(e) => setSeasonA(e.target.value)}
            className="bg-slate-800/80 border border-slate-700/50 text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          >
            {SEASONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <span className="text-sm text-slate-600 font-bold">vs</span>
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: bColor }}
          />
          <select
            value={seasonB}
            onChange={(e) => setSeasonB(e.target.value)}
            className="bg-slate-800/80 border border-slate-700/50 text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          >
            {SEASONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Performance Radar
          </h3>
          <p className="text-xs text-slate-500 mb-4">Normalized comparison (0–100)</p>
          {Object.keys(seasonTotals).length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar
                  name={seasonA}
                  dataKey={seasonA}
                  stroke={aColor}
                  fill={aColor}
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Radar
                  name={seasonB}
                  dataKey={seasonB}
                  stroke={bColor}
                  fill={bColor}
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '12px' }}
                  formatter={(value) => (
                    <span className="text-xs" style={{ color: SEASON_COLORS[value] }}>{value}</span>
                  )}
                />
                <Tooltip content={<ChartTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
        </div>

        {/* Side-by-side Bar Chart */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-amber-400" />
            Side-by-Side Metrics
          </h3>
          <p className="text-xs text-slate-500 mb-4">Absolute values comparison</p>
          {Object.keys(seasonTotals).length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={barData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey={seasonA} fill={aColor} radius={[4, 4, 0, 0]} />
                <Bar dataKey={seasonB} fill={bColor} radius={[4, 4, 0, 0]} />
                <Legend
                  wrapperStyle={{ paddingTop: '12px' }}
                  formatter={(value) => (
                    <span className="text-xs" style={{ color: SEASON_COLORS[value] }}>{value}</span>
                  )}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
        </div>
      </div>

      {/* Detailed Comparison Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          Detailed Comparison
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wider">
                <th className="text-left pb-3 px-4">Metric</th>
                <th className="text-right pb-3 px-4">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: aColor }} />
                    {seasonA}
                  </div>
                </th>
                <th className="text-right pb-3 px-4">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: bColor }} />
                    {seasonB}
                  </div>
                </th>
                <th className="text-right pb-3 px-4">Difference</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {[
                { label: 'Total Revenue', aVal: a.total_sales, bVal: b.total_sales, diff: salesDiff, format: formatCurrency },
                { label: 'Units Sold', aVal: a.total_units, bVal: b.total_units, diff: unitsDiff, format: formatNumber },
                { label: 'Bill Count', aVal: a.bill_count, bVal: b.bill_count, diff: billsDiff, format: formatNumber },
              ].map(({ label, aVal, bVal, diff, format }) => (
                <tr key={label} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-sm font-medium text-slate-200">{label}</td>
                  <td className="py-3 px-4 text-sm text-right text-slate-300 font-medium">{format(aVal)}</td>
                  <td className="py-3 px-4 text-sm text-right text-slate-300 font-medium">{format(bVal)}</td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span
                      className={`inline-flex items-center gap-1 font-medium ${
                        diff > 0 ? 'text-emerald-400' : diff < 0 ? 'text-red-400' : 'text-slate-500'
                      }`}
                    >
                      {diff > 0 && <TrendingUp className="w-3 h-3" />}
                      {diff < 0 && <TrendingDown className="w-3 h-3" />}
                      {diff === 0 ? '—' : `${Math.abs(diff)}%`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Key Insights */}
      {insights.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            Key Insights
          </h3>
          <div className="space-y-3">
            {insights.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/30"
                >
                  <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${item.color}`} />
                  <p className="text-sm text-slate-300">{item.text}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Shared: Empty Chart Message ─────────────────────────
function EmptyChartMessage() {
  return (
    <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
      <div className="text-center">
        <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-30" />
        <p>No data available</p>
      </div>
    </div>
  );
}
