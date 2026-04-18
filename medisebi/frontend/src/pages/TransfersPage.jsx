import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  ArrowLeftRight, RefreshCw, Filter, CheckCircle, XCircle, AlertTriangle,
  Package, TrendingUp, Loader2, ChevronLeft, ChevronRight, Search, Zap,
  BarChart3, Clock, History, Send, Ban, Play,
} from 'lucide-react';
import { transfersAPI, shopsAPI } from '../services/api';

const TABS = ['Analyze', 'Requests', 'Analytics', 'History'];

const PRIORITY_CONFIG = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/30', dot: 'bg-red-400' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/15 border-orange-500/30', dot: 'bg-orange-400' },
  medium: { color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/30', dot: 'bg-blue-400' },
  low: { color: 'text-slate-400', bg: 'bg-slate-500/15 border-slate-500/30', dot: 'bg-slate-400' },
};

const STATUS_CONFIG = {
  pending: { color: 'text-amber-400', bg: 'bg-amber-500/15' },
  approved: { color: 'text-blue-400', bg: 'bg-blue-500/15' },
  completed: { color: 'text-emerald-400', bg: 'bg-emerald-500/15' },
  rejected: { color: 'text-red-400', bg: 'bg-red-500/15' },
  cancelled: { color: 'text-slate-400', bg: 'bg-slate-500/15' },
};

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

const formatDate = (d) => {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

function PriorityBadge({ priority }) {
  const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.low;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide border ${cfg.bg} ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {priority}
    </span>
  );
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide ${cfg.bg} ${cfg.color}`}>
      {status}
    </span>
  );
}

function ScoreBar({ score }) {
  const pct = Math.min(100, Math.max(0, score || 0));
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 font-mono w-8 text-right">{pct.toFixed(0)}</span>
    </div>
  );
}

export default function TransfersPage() {
  const [activeTab, setActiveTab] = useState('Analyze');

  // Analyze tab state
  const [opportunities, setOpportunities] = useState([]);
  const [totalOpps, setTotalOpps] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [expandedOpp, setExpandedOpp] = useState(null);
  const [createForm, setCreateForm] = useState({ quantity: '', notes: '' });
  const [creating, setCreating] = useState(false);

  // Requests tab state
  const [requests, setRequests] = useState([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [shopFilter, setShopFilter] = useState('');
  const [shops, setShops] = useState([]);
  const [requestPage, setRequestPage] = useState(1);
  const [requestTotal, setRequestTotal] = useState(0);
  const [rejectModal, setRejectModal] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  // Analytics tab state
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // History tab state
  const [historyShop, setHistoryShop] = useState('');
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);

  const pageSize = 15;

  // Fetch shops on mount
  useEffect(() => {
    fetchShops();
  }, []);

  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (e) {
      console.error('Failed to fetch shops:', e);
    }
  };

  // Fetch tab-specific data when tab changes
  useEffect(() => {
    if (activeTab === 'Requests') fetchRequests();
    if (activeTab === 'Analytics') fetchAnalytics();
  }, [activeTab, statusFilter, shopFilter, requestPage]);

  useEffect(() => {
    if (activeTab === 'History' && historyShop) fetchHistory();
  }, [activeTab, historyShop, historyPage]);

  // ─── Analyze Handlers ───────────────────────
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setOpportunities([]);
    setTotalOpps(0);
    try {
      const { data } = await transfersAPI.analyze();
      const items = Array.isArray(data) ? data : data?.opportunities || data?.items || [];
      setOpportunities(items);
      setTotalOpps(items.length);
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCreateTransfer = async (opp) => {
    if (!createForm.quantity) return;
    setCreating(true);
    try {
      await transfersAPI.create({
        from_shop_id: opp.from_shop_id,
        to_shop_id: opp.to_shop_id,
        med_id: opp.med_id,
        quantity: parseInt(createForm.quantity),
        notes: createForm.notes || opp.reason || `Transfer: ${opp.brand_name || opp.salt_name}`,
      });
      setExpandedOpp(null);
      setCreateForm({ quantity: '', notes: '' });
    } catch (err) {
      console.error('Create transfer failed:', err);
    } finally {
      setCreating(false);
    }
  };

  // ─── Requests Handlers ──────────────────────
  const fetchRequests = async () => {
    setRequestsLoading(true);
    try {
      const params = { page: requestPage, size: pageSize };
      if (statusFilter) params.status = statusFilter;
      if (shopFilter) params.shop_id = shopFilter;
      const { data } = await transfersAPI.list(params);
      setRequests(data?.items || []);
      setRequestTotal(data?.total || 0);
    } catch (err) {
      console.error('Failed to fetch requests:', err);
    } finally {
      setRequestsLoading(false);
    }
  };

  const handleApprove = async (id) => {
    setActionLoading(id);
    try {
      await transfersAPI.approve(id);
      fetchRequests();
    } catch (err) {
      console.error('Approve failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleExecute = async (id) => {
    setActionLoading(id);
    try {
      await transfersAPI.execute(id);
      fetchRequests();
    } catch (err) {
      console.error('Execute failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal || !rejectReason.trim()) return;
    setActionLoading(rejectModal.id);
    try {
      await transfersAPI.reject(rejectModal.id, { reason: rejectReason });
      setRejectModal(null);
      setRejectReason('');
      fetchRequests();
    } catch (err) {
      console.error('Reject failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  // ─── Analytics Handlers ─────────────────────
  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const { data } = await transfersAPI.analytics();
      setAnalytics(data);
    } catch (err) {
      console.error('Analytics fetch failed:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  // ─── History Handlers ───────────────────────
  const fetchHistory = async () => {
    if (!historyShop) return;
    setHistoryLoading(true);
    try {
      const { data } = await transfersAPI.shopHistory(historyShop, { page: historyPage, size: pageSize });
      setHistoryData(data?.items || data || []);
      setHistoryTotal(data?.total || (Array.isArray(data) ? data.length : 0));
    } catch (err) {
      console.error('History fetch failed:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const totalPages = (total) => Math.ceil(total / pageSize);

  const Pagination = ({ page, total, onPage }) => {
    const tp = totalPages(total);
    if (tp <= 1) return null;
    return (
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/50">
        <p className="text-xs text-slate-500">
          Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
        </p>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          {Array.from({ length: Math.min(5, tp) }, (_, i) => {
            const pn = Math.max(1, Math.min(page - 2, tp - 4)) + i;
            if (pn > tp) return null;
            return (
              <button
                key={pn}
                onClick={() => onPage(pn)}
                className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                  pn === page ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {pn}
              </button>
            );
          })}
          <button
            onClick={() => onPage((p) => Math.min(tp, p + 1))}
            disabled={page === tp}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ArrowLeftRight className="w-6 h-6 text-indigo-400" />
            Transfer Redistribution
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Analyze opportunities, manage requests, and track redistribution flow
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900/80 border border-slate-700/50 rounded-xl p-1 overflow-x-auto">
        {TABS.map((tab) => {
          const icons = {
            Analyze: Zap,
            Requests: Send,
            Analytics: BarChart3,
            History: History,
          };
          const Icon = icons[tab];
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════ ANALYZE TAB ═══════════════════ */}
      {activeTab === 'Analyze' && (
        <div className="space-y-6">
          {/* Action Bar */}
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
              >
                {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                Run Analysis
              </button>
              {totalOpps > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-medium text-emerald-400">
                  <TrendingUp className="w-3.5 h-3.5" />
                  {totalOpps} opportunities found
                </span>
              )}
            </div>
            {analyzing && (
              <p className="text-sm text-slate-400 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                Scanning all shops for redistribution opportunities...
              </p>
            )}
          </div>

          {/* Opportunity Cards */}
          {analyzing ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : opportunities.length === 0 ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
              <ArrowLeftRight className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-300 mb-2">No Analysis Run Yet</h3>
              <p className="text-sm text-slate-500 max-w-md mx-auto">
                Click "Run Analysis" to scan all shops and identify redistribution opportunities based on surplus, deficits, expiry risk, and proximity.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {opportunities.map((opp, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden transition-all hover:border-slate-600/50"
                >
                  <div className="p-4 sm:p-5">
                    <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                      {/* Route Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="text-sm font-medium text-white truncate">
                            {opp.from_shop_name || `Shop #${opp.from_shop_id}`}
                          </span>
                          <ArrowLeftRight className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                          <span className="text-sm font-medium text-white truncate">
                            {opp.to_shop_name || `Shop #${opp.to_shop_id}`}
                          </span>
                          {opp.distance && (
                            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400">
                              {typeof opp.distance === 'number' ? `${opp.distance.toFixed(1)} km` : opp.distance}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-sm text-slate-300 font-medium">
                            <Package className="w-3.5 h-3.5 inline mr-1 text-slate-500" />
                            {opp.brand_name || opp.salt_name || `Med #${opp.med_id}`}
                          </span>
                          {opp.salt_name && opp.brand_name && (
                            <span className="text-xs text-slate-500">{opp.salt_name}</span>
                          )}
                        </div>
                      </div>

                      {/* Meta */}
                      <div className="flex items-center gap-4 flex-wrap">
                        <div className="text-center">
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Qty</p>
                          <p className="text-lg font-bold text-white">{opp.suggested_quantity || opp.quantity || 0}</p>
                        </div>
                        <PriorityBadge priority={opp.priority || 'low'} />
                      </div>

                      {/* Score */}
                      <div className="w-40 flex-shrink-0">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Score</p>
                        <ScoreBar score={opp.composite_score || opp.score} />
                      </div>

                      {/* Reason */}
                      {opp.reason && (
                        <div className="hidden xl:block w-48 flex-shrink-0">
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Reason</p>
                          <p className="text-xs text-slate-400 line-clamp-2">{opp.reason}</p>
                        </div>
                      )}

                      {/* Action */}
                      <div className="flex-shrink-0">
                        {expandedOpp === idx ? (
                          <button
                            onClick={() => setExpandedOpp(null)}
                            className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-800"
                          >
                            Cancel
                          </button>
                        ) : (
                          <button
                            onClick={() => setExpandedOpp(idx)}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600/80 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
                          >
                            <Send className="w-3.5 h-3.5" />
                            Request Transfer
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Mobile reason */}
                    <div className="mt-2 xl:hidden">
                      {opp.reason && (
                        <p className="text-xs text-slate-500">
                          <span className="text-slate-400">Reason:</span> {opp.reason}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Inline Create Form */}
                  {expandedOpp === idx && (
                    <div className="border-t border-slate-700/50 bg-slate-800/30 p-4 sm:p-5">
                      <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                        <Send className="w-4 h-4 text-indigo-400" />
                        Create Transfer Request
                      </h4>
                      <div className="flex flex-col sm:flex-row gap-3 items-end">
                        <div className="flex-1 w-full">
                          <label className="block text-xs font-medium text-slate-400 mb-1">Quantity</label>
                          <input
                            type="number"
                            min="1"
                            max={opp.suggested_quantity || opp.quantity || 999}
                            value={createForm.quantity}
                            onChange={(e) => setCreateForm({ ...createForm, quantity: e.target.value })}
                            placeholder={String(opp.suggested_quantity || opp.quantity || '')}
                            className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                          />
                        </div>
                        <div className="flex-[2] w-full">
                          <label className="block text-xs font-medium text-slate-400 mb-1">Notes (optional)</label>
                          <input
                            type="text"
                            value={createForm.notes}
                            onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                            placeholder="Add a note..."
                            className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                          />
                        </div>
                        <button
                          onClick={() => handleCreateTransfer(opp)}
                          disabled={creating || !createForm.quantity}
                          className="inline-flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
                        >
                          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                          Submit Request
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════ REQUESTS TAB ═══════════════════ */}
      {activeTab === 'Requests' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Filters</span>
            </div>
            <div className="flex flex-wrap gap-3">
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setRequestPage(1); }}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="completed">Completed</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <select
                value={shopFilter}
                onChange={(e) => { setShopFilter(e.target.value); setRequestPage(1); }}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Shops</option>
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              {(statusFilter || shopFilter) && (
                <button
                  onClick={() => { setStatusFilter(''); setShopFilter(''); setRequestPage(1); }}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">ID</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Route</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Priority</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Created</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {requestsLoading ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : requests.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center text-sm text-slate-500">
                        No transfer requests found
                      </td>
                    </tr>
                  ) : (
                    requests.map((req) => (
                      <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-slate-400">#{req.id}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5 text-sm">
                            <span className="text-slate-200">{req.from_shop_name || `#${req.from_shop_id}`}</span>
                            <ArrowLeftRight className="w-3 h-3 text-indigo-400" />
                            <span className="text-slate-200">{req.to_shop_name || `#${req.to_shop_id}`}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-slate-200">{req.brand_name || req.salt_name || `#${req.med_id}`}</p>
                          {req.salt_name && req.brand_name && (
                            <p className="text-xs text-slate-500">{req.salt_name}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-medium text-white">{req.quantity}</td>
                        <td className="px-4 py-3 text-center">
                          <PriorityBadge priority={req.priority || 'low'} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <StatusBadge status={req.status || 'pending'} />
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-400">{formatDate(req.created_at)}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {req.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => handleApprove(req.id)}
                                  disabled={actionLoading === req.id}
                                  title="Approve"
                                  className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-30"
                                >
                                  {actionLoading === req.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <CheckCircle className="w-4 h-4" />
                                  )}
                                </button>
                                <button
                                  onClick={() => setRejectModal(req)}
                                  disabled={actionLoading === req.id}
                                  title="Reject"
                                  className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30"
                                >
                                  <XCircle className="w-4 h-4" />
                                </button>
                              </>
                            )}
                            {req.status === 'approved' && (
                              <button
                                onClick={() => handleExecute(req.id)}
                                disabled={actionLoading === req.id}
                                title="Execute Transfer"
                                className="p-1.5 rounded-lg text-blue-400 hover:bg-blue-500/10 transition-colors disabled:opacity-30"
                              >
                                {actionLoading === req.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Play className="w-4 h-4" />
                                )}
                              </button>
                            )}
                            {(req.status === 'completed' || req.status === 'rejected' || req.status === 'cancelled') && (
                              <span className="text-xs text-slate-600 px-2">—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <Pagination page={requestPage} total={requestTotal} onPage={setRequestPage} />
          </div>

          {/* Reject Modal */}
          {rejectModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => { setRejectModal(null); setRejectReason(''); }} />
              <div className="relative bg-slate-900 border border-slate-700/50 rounded-2xl w-full max-w-md p-6 shadow-2xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-red-500/15 flex items-center justify-center">
                    <Ban className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Reject Transfer</h2>
                    <p className="text-xs text-slate-400">Request #{rejectModal.id}</p>
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Reason <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Provide a reason for rejection..."
                    rows={3}
                    className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500 resize-none"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => { setRejectModal(null); setRejectReason(''); }}
                    className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={!rejectReason.trim() || actionLoading === rejectModal.id}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-red-600/50 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    {actionLoading === rejectModal.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    Reject
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════ ANALYTICS TAB ═══════════════════ */}
      {activeTab === 'Analytics' && (
        <div className="space-y-6">
          {analyticsLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : !analytics ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
              <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-300 mb-2">No Analytics Data</h3>
              <p className="text-sm text-slate-500">Analytics data will be available after transfer activities are recorded.</p>
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <SummaryStatCard
                  title="Total Transfers"
                  value={analytics.total_transfers || 0}
                  icon={ArrowLeftRight}
                  color="indigo"
                  subtitle="All time"
                />
                <SummaryStatCard
                  title="Units Redistributed"
                  value={analytics.total_units || analytics.units_redistributed || 0}
                  icon={Package}
                  color="emerald"
                  subtitle="Total quantity moved"
                />
                <SummaryStatCard
                  title="Pending Requests"
                  value={analytics.pending_count || 0}
                  icon={Clock}
                  color="amber"
                  subtitle="Awaiting approval"
                  highlight={(analytics.pending_count || 0) > 0}
                />
                <SummaryStatCard
                  title="Completed This Month"
                  value={analytics.completed_this_month || analytics.monthly_completed || 0}
                  icon={CheckCircle}
                  color="blue"
                  subtitle="Current month"
                />
              </div>

              {/* Chart + Flow Table */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Most Transferred Medicines */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-indigo-400" />
                    Most Transferred Medicines
                  </h3>
                  {analytics.most_transferred && analytics.most_transferred.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={analytics.most_transferred} margin={{ top: 5, right: 20, left: 0, bottom: 60 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: '#94a3b8', fontSize: 10 }}
                          angle={-35}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="count" name="Transfers" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
                      No transfer data available
                    </div>
                  )}
                </div>

                {/* Shop-to-Shop Flow */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <ArrowLeftRight className="w-4 h-4 text-emerald-400" />
                    Shop-to-Shop Flow
                  </h3>
                  <div className="max-h-[340px] overflow-y-auto">
                    {analytics.shop_flow && analytics.shop_flow.length > 0 ? (
                      <table className="w-full">
                        <thead className="sticky top-0">
                          <tr className="text-xs text-slate-400 uppercase tracking-wider">
                            <th className="text-left pb-3 px-2">From</th>
                            <th className="text-center pb-3 px-2"></th>
                            <th className="text-left pb-3 px-2">To</th>
                            <th className="text-right pb-3 px-2">Count</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/30">
                          {analytics.shop_flow.map((flow, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                              <td className="py-2.5 px-2 text-sm text-slate-300">{flow.from_shop || flow.from}</td>
                              <td className="py-2.5 px-2 text-center">
                                <ArrowLeftRight className="w-3.5 h-3.5 text-indigo-400" />
                              </td>
                              <td className="py-2.5 px-2 text-sm text-slate-300">{flow.to_shop || flow.to}</td>
                              <td className="py-2.5 px-2 text-sm text-right font-medium text-indigo-400">
                                {flow.count || flow.transfers || 0}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
                        No flow data available
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ═══════════════════ HISTORY TAB ═══════════════════ */}
      {activeTab === 'History' && (
        <div className="space-y-4">
          {/* Shop Selector */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <History className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Shop Transfer History</span>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={historyShop}
                onChange={(e) => { setHistoryShop(e.target.value); setHistoryPage(1); }}
                className="flex-1 px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Select a shop...</option>
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} — {s.city || ''}</option>
                ))}
              </select>
              {historyShop && (
                <button
                  onClick={() => { setHistoryShop(''); setHistoryData([]); setHistoryTotal(0); }}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* History Table */}
          {historyShop && (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-800/50">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">ID</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Direction</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                      <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Priority</th>
                      <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {historyLoading ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center">
                          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                        </td>
                      </tr>
                    ) : historyData.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                          No transfer history for this shop
                        </td>
                      </tr>
                    ) : (
                      historyData.map((item, idx) => (
                        <tr key={item.id || idx} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-4 py-3 text-sm font-mono text-slate-400">#{item.id}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5 text-sm">
                              <span className="text-slate-200">{item.from_shop_name || `#${item.from_shop_id}`}</span>
                              <ArrowLeftRight className="w-3 h-3 text-indigo-400" />
                              <span className="text-slate-200">{item.to_shop_name || `#${item.to_shop_id}`}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-slate-200">{item.brand_name || item.salt_name || `#${item.med_id}`}</p>
                          </td>
                          <td className="px-4 py-3 text-sm text-right font-medium text-white">{item.quantity}</td>
                          <td className="px-4 py-3 text-center">
                            <PriorityBadge priority={item.priority || 'low'} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge status={item.status || 'pending'} />
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-400">{formatDate(item.created_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <Pagination page={historyPage} total={historyTotal} onPage={setHistoryPage} />
            </div>
          )}

          {!historyShop && (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
              <History className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-300 mb-2">Select a Shop</h3>
              <p className="text-sm text-slate-500">Choose a shop from the dropdown above to view its transfer history.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Summary Stat Card ──────────────────────────────
function SummaryStatCard({ title, value, icon: Icon, color, subtitle, highlight }) {
  const colorMap = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  };

  const iconColorMap = {
    indigo: 'bg-indigo-500/15 text-indigo-400',
    red: 'bg-red-500/15 text-red-400',
    amber: 'bg-amber-500/15 text-amber-400',
    emerald: 'bg-emerald-500/15 text-emerald-400',
    blue: 'bg-blue-500/15 text-blue-400',
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
