import { useState, useEffect } from 'react';
import {
  Package, AlertTriangle, TrendingUp, Loader2, ChevronLeft, ChevronRight,
  Store, ShoppingBag, Handshake, LayoutDashboard, Filter, CheckCircle,
  XCircle, Clock, Tag, ArrowRight, BarChart3, Percent, Calendar,
  RefreshCw, Plus, X, Send,
} from 'lucide-react';
import { marketplaceAPI, shopsAPI, expiryAPI } from '../services/api';

const TABS = [
  { key: 'Listings', label: 'Listings', icon: Tag },
  { key: 'Demand Matches', label: 'Demand Matches', icon: Handshake },
  { key: 'Offers', label: 'Offers', icon: ShoppingBag },
  { key: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
];

const STATUS_CONFIG = {
  pending: { color: 'text-amber-400', bg: 'bg-amber-500/15' },
  approved: { color: 'text-blue-400', bg: 'bg-blue-500/15' },
  accepted: { color: 'text-indigo-400', bg: 'bg-indigo-500/15' },
  completed: { color: 'text-emerald-400', bg: 'bg-emerald-500/15' },
  rejected: { color: 'text-red-400', bg: 'bg-red-500/15' },
  cancelled: { color: 'text-slate-400', bg: 'bg-slate-500/15' },
};

const PRIORITY_CONFIG = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/30', dot: 'bg-red-400' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/15 border-orange-500/30', dot: 'bg-orange-400' },
  medium: { color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/30', dot: 'bg-blue-400' },
  low: { color: 'text-slate-400', bg: 'bg-slate-500/15 border-slate-500/30', dot: 'bg-slate-400' },
};

const formatDate = (d) => {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide ${cfg.bg} ${cfg.color}`}>
      {status}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.low;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide border ${cfg.bg} ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {priority}
    </span>
  );
}

function UrgencyBadge({ daysLeft }) {
  if (daysLeft == null) return null;
  if (daysLeft < 0) {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-500/20 text-red-400">
        Expired
      </span>
    );
  }
  if (daysLeft < 7) {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-500/15 text-red-400">
        {daysLeft}d left
      </span>
    );
  }
  if (daysLeft < 15) {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-orange-500/15 text-orange-400">
        {daysLeft}d left
      </span>
    );
  }
  if (daysLeft < 30) {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-400">
        {daysLeft}d left
      </span>
    );
  }
  return (
    <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400">
      {daysLeft}d left
    </span>
  );
}

function getDaysLeft(expiryDate) {
  if (!expiryDate) return null;
  const now = new Date();
  const expiry = new Date(expiryDate);
  return Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
}

function getUrgencyRowBg(daysLeft) {
  if (daysLeft == null) return '';
  if (daysLeft < 7) return 'border-l-2 border-l-red-500';
  if (daysLeft < 15) return 'border-l-2 border-l-orange-500';
  if (daysLeft < 30) return 'border-l-2 border-l-amber-500';
  return '';
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

export default function MarketplacePage() {
  const [activeTab, setActiveTab] = useState('Listings');

  // Listings tab state
  const [listings, setListings] = useState([]);
  const [listingsLoading, setListingsLoading] = useState(false);
  const [listingsPage, setListingsPage] = useState(1);
  const [listingsTotal, setListingsTotal] = useState(0);

  // Demand Matches tab state
  const [demandMatches, setDemandMatches] = useState([]);
  const [demandLoading, setDemandLoading] = useState(false);

  // Offers tab state
  const [offers, setOffers] = useState([]);
  const [offersLoading, setOffersLoading] = useState(false);
  const [offerStatusFilter, setOfferStatusFilter] = useState('');
  const [offersPage, setOffersPage] = useState(1);
  const [offersTotal, setOffersTotal] = useState(0);
  const [actionLoading, setActionLoading] = useState(null);

  // Dashboard tab state
  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  // Create Offer modal state
  const [showCreateOffer, setShowCreateOffer] = useState(false);
  const [createOfferForm, setCreateOfferForm] = useState({
    from_shop_id: '',
    to_shop_id: '',
    inventory_item_id: '',
    quantity: '',
    price_per_unit: '',
    notes: '',
  });
  const [createOfferLoading, setCreateOfferLoading] = useState(false);
  const [createOfferError, setCreateOfferError] = useState('');
  const [shops, setShops] = useState([]);
  const [expiringItems, setExpiringItems] = useState([]);

  const pageSize = 15;

  // Fetch shops on mount
  useEffect(() => {
    fetchShops();
  }, []);

  // Fetch data on tab change
  useEffect(() => {
    if (activeTab === 'Listings') fetchListings();
    if (activeTab === 'Demand Matches') fetchDemandMatches();
    if (activeTab === 'Offers') fetchOffers();
    if (activeTab === 'Dashboard') fetchDashboard();
  }, [activeTab, listingsPage, offerStatusFilter, offersPage]);

  // ─── Shops & Create Offer Handlers ───────
  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (err) {
      console.error('Failed to fetch shops:', err);
    }
  };

  const fetchExpiringItems = async (shopId) => {
    if (!shopId) {
      setExpiringItems([]);
      return;
    }
    try {
      const { data } = await expiryAPI.items({ shop_id: shopId, severity: 'expired', size: 50 });
      const items = data?.items || data || [];
      setExpiringItems(Array.isArray(items) ? items : []);
    } catch (err) {
      console.error('Failed to fetch expiring items:', err);
      setExpiringItems([]);
    }
  };

  const handleCreateOffer = async (e) => {
    e.preventDefault();
    if (!createOfferForm.from_shop_id || !createOfferForm.to_shop_id || !createOfferForm.quantity) {
      setCreateOfferError('Source shop, destination shop, and quantity are required.');
      return;
    }
    if (createOfferForm.from_shop_id === createOfferForm.to_shop_id) {
      setCreateOfferError('Source and destination shops must be different.');
      return;
    }
    setCreateOfferLoading(true);
    setCreateOfferError('');
    try {
      const payload = {
        from_shop_id: parseInt(createOfferForm.from_shop_id),
        to_shop_id: parseInt(createOfferForm.to_shop_id),
        quantity: parseInt(createOfferForm.quantity),
        notes: createOfferForm.notes || undefined,
      };
      if (createOfferForm.inventory_item_id) {
        payload.inventory_item_id = parseInt(createOfferForm.inventory_item_id);
      }
      if (createOfferForm.price_per_unit) {
        payload.price_per_unit = parseFloat(createOfferForm.price_per_unit);
      }
      await marketplaceAPI.createOffer(payload);
      setShowCreateOffer(false);
      setCreateOfferForm({ from_shop_id: '', to_shop_id: '', inventory_item_id: '', quantity: '', price_per_unit: '', notes: '' });
      setExpiringItems([]);
      if (activeTab === 'Offers') fetchOffers();
    } catch (err) {
      setCreateOfferError(err.response?.data?.detail || 'Failed to create offer. Please try again.');
    } finally {
      setCreateOfferLoading(false);
    }
  };

  // ─── Listings Handlers ──────────────────────
  const fetchListings = async () => {
    setListingsLoading(true);
    try {
      const { data } = await marketplaceAPI.expiringListings({ page: listingsPage, size: pageSize });
      const items = Array.isArray(data) ? data : data?.items || data?.listings || [];
      setListings(items);
      setListingsTotal(data?.total || items.length);
    } catch (err) {
      console.error('Failed to fetch expiring listings:', err);
    } finally {
      setListingsLoading(false);
    }
  };

  // ─── Demand Matches Handlers ────────────────
  const fetchDemandMatches = async () => {
    setDemandLoading(true);
    try {
      const { data } = await marketplaceAPI.demandMatches();
      const items = Array.isArray(data) ? data : data?.items || data?.matches || [];
      setDemandMatches(items);
    } catch (err) {
      console.error('Failed to fetch demand matches:', err);
    } finally {
      setDemandLoading(false);
    }
  };

  // ─── Offers Handlers ────────────────────────
  const fetchOffers = async () => {
    setOffersLoading(true);
    try {
      const params = { page: offersPage, size: pageSize };
      if (offerStatusFilter) params.status = offerStatusFilter;
      const { data } = await marketplaceAPI.listOffers(params);
      setOffers(data?.items || []);
      setOffersTotal(data?.total || 0);
    } catch (err) {
      console.error('Failed to fetch offers:', err);
    } finally {
      setOffersLoading(false);
    }
  };

  const handleAcceptOffer = async (id) => {
    setActionLoading(id);
    try {
      await marketplaceAPI.acceptOffer(id);
      fetchOffers();
    } catch (err) {
      console.error('Accept offer failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCompleteOffer = async (id) => {
    setActionLoading(id);
    try {
      await marketplaceAPI.completeOffer(id);
      fetchOffers();
    } catch (err) {
      console.error('Complete offer failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRejectOffer = async (id) => {
    setActionLoading(id);
    try {
      await marketplaceAPI.rejectOffer(id, { reason: 'Rejected by user' });
      fetchOffers();
    } catch (err) {
      console.error('Reject offer failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  // ─── Dashboard Handlers ─────────────────────
  const fetchDashboard = async () => {
    setDashboardLoading(true);
    try {
      const { data } = await marketplaceAPI.dashboard();
      setDashboard(data);
    } catch (err) {
      console.error('Failed to fetch marketplace dashboard:', err);
    } finally {
      setDashboardLoading(false);
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
            <Store className="w-6 h-6 text-indigo-400" />
            Inter-Dispensary Marketplace
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Match expiring stock with demand, create offers, and optimize redistribution
          </p>
        </div>
        <button
          onClick={() => setShowCreateOffer(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          Create Offer
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900/80 border border-slate-700/50 rounded-xl p-1 overflow-x-auto">
        {TABS.map(({ key, label, icon: Icon }) => {
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════ LISTINGS TAB ═══════════════════ */}
      {activeTab === 'Listings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-semibold text-white">Expiring Listings</h2>
              {listingsTotal > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium">
                  {listingsTotal} items
                </span>
              )}
            </div>
            <button
              onClick={fetchListings}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>

          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Shop</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Expiry Date</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Urgency</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Discount %</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Unit Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {listingsLoading ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : listings.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                        No expiring listings found
                      </td>
                    </tr>
                  ) : (
                    listings.map((item, idx) => {
                      const daysLeft = getDaysLeft(item.expiry_date);
                      return (
                        <tr key={item.id || idx} className={`hover:bg-slate-800/30 transition-colors ${getUrgencyRowBg(daysLeft)}`}>
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-slate-200">{item.brand_name || item.name || `#${item.med_id}`}</p>
                            <p className="text-xs text-slate-500">{item.salt_name || ''}</p>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <Store className="w-3.5 h-3.5 text-slate-500" />
                              <span className="text-sm text-slate-300">{item.shop_name || `#${item.shop_id}`}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-right font-medium text-white">{item.quantity || 0}</td>
                          <td className="px-4 py-3 text-sm text-slate-400">
                            <div className="flex items-center gap-1.5">
                              <Calendar className="w-3.5 h-3.5 text-slate-500" />
                              {formatDate(item.expiry_date)}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <UrgencyBadge daysLeft={daysLeft} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`inline-flex items-center gap-1 text-sm font-medium ${
                              (item.discount_percentage || 0) >= 30 ? 'text-emerald-400' :
                              (item.discount_percentage || 0) >= 15 ? 'text-blue-400' : 'text-slate-400'
                            }`}>
                              <Percent className="w-3 h-3" />
                              {item.discount_percentage || 0}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-right text-slate-300 font-medium">
                            {item.unit_price != null ? `₹${item.unit_price}` : item.selling_price != null ? `₹${item.selling_price}` : '—'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            <Pagination page={listingsPage} total={listingsTotal} onPage={setListingsPage} />
          </div>
        </div>
      )}

      {/* ═══════════════════ DEMAND MATCHES TAB ═══════════════════ */}
      {activeTab === 'Demand Matches' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Handshake className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-white">Demand Matches</h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 font-medium">
                {demandMatches.length} matches
              </span>
            </div>
            <p className="text-xs text-slate-500 max-w-md hidden sm:block">
              Shows shops with expiring medicines that match other shops&apos; demand
            </p>
          </div>

          {demandLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : demandMatches.length === 0 ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
              <Handshake className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-300 mb-2">No Demand Matches</h3>
              <p className="text-sm text-slate-500 max-w-md mx-auto">
                No matching opportunities found between shops with expiring stock and demand. Matches will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {demandMatches.map((match, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/30 transition-all duration-200"
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-semibold text-white truncate">
                      {match.salt_name || match.brand_name || match.medicine_name || 'Unknown Medicine'}
                    </p>
                    <PriorityBadge priority={match.priority || 'low'} />
                  </div>

                  {/* Route */}
                  <div className="flex items-center gap-2 mb-3 text-sm">
                    <div className="flex items-center gap-1.5 flex-1 min-w-0">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                        <Package className="w-3 h-3 text-emerald-400" />
                      </div>
                      <span className="text-slate-300 truncate">{match.source_shop || match.from_shop_name || `Shop #${match.from_shop_id}`}</span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <div className="flex items-center gap-1.5 flex-1 min-w-0 justify-end text-right">
                      <span className="text-slate-300 truncate">{match.dest_shop || match.to_shop_name || `Shop #${match.to_shop_id}`}</span>
                      <div className="w-6 h-6 rounded-full bg-amber-500/15 flex items-center justify-center flex-shrink-0">
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                      </div>
                    </div>
                  </div>

                  {/* Quantities */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="bg-slate-800/50 rounded-lg p-2.5 text-center">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Available</p>
                      <p className="text-lg font-bold text-emerald-400">{match.available_qty || match.quantity || 0}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2.5 text-center">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Deficit</p>
                      <p className="text-lg font-bold text-amber-400">{match.deficit_qty || match.deficit || 0}</p>
                    </div>
                  </div>

                  {/* Score */}
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Match Score</p>
                    <ScoreBar score={match.priority_score || match.score || match.match_score} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════ OFFERS TAB ═══════════════════ */}
      {activeTab === 'Offers' && (
        <div className="space-y-4">
          {/* Filter */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Filters</span>
            </div>
            <div className="flex flex-wrap gap-3">
              <select
                value={offerStatusFilter}
                onChange={(e) => { setOfferStatusFilter(e.target.value); setOffersPage(1); }}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="accepted">Accepted</option>
                <option value="completed">Completed</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {offerStatusFilter && (
                <button
                  onClick={() => { setOfferStatusFilter(''); setOffersPage(1); }}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Offers Table */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">ID</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">From Shop</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">To Shop</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Priority</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Created</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {offersLoading ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : offers.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-sm text-slate-500">
                        No offers found
                      </td>
                    </tr>
                  ) : (
                    offers.map((offer) => (
                      <tr key={offer.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-slate-400">#{offer.id}</td>
                        <td className="px-4 py-3 text-sm text-slate-300">{offer.from_shop_name || `#${offer.from_shop_id}`}</td>
                        <td className="px-4 py-3 text-sm text-slate-300">{offer.to_shop_name || `#${offer.to_shop_id}`}</td>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-slate-200">{offer.brand_name || offer.salt_name || offer.medicine_name || `#${offer.med_id}`}</p>
                          {offer.salt_name && offer.brand_name && (
                            <p className="text-xs text-slate-500">{offer.salt_name}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-medium text-white">{offer.quantity || 0}</td>
                        <td className="px-4 py-3 text-center">
                          <PriorityBadge priority={offer.priority || 'low'} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <StatusBadge status={offer.status || 'pending'} />
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-400">{formatDate(offer.created_at)}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {offer.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => handleAcceptOffer(offer.id)}
                                  disabled={actionLoading === offer.id}
                                  title="Accept"
                                  className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-30"
                                >
                                  {actionLoading === offer.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <CheckCircle className="w-4 h-4" />
                                  )}
                                </button>
                                <button
                                  onClick={() => handleRejectOffer(offer.id)}
                                  disabled={actionLoading === offer.id}
                                  title="Reject"
                                  className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30"
                                >
                                  <XCircle className="w-4 h-4" />
                                </button>
                              </>
                            )}
                            {(offer.status === 'accepted' || offer.status === 'approved') && (
                              <button
                                onClick={() => handleCompleteOffer(offer.id)}
                                disabled={actionLoading === offer.id}
                                title="Complete"
                                className="p-1.5 rounded-lg text-blue-400 hover:bg-blue-500/10 transition-colors disabled:opacity-30"
                              >
                                {actionLoading === offer.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <CheckCircle className="w-4 h-4" />
                                )}
                              </button>
                            )}
                            {(offer.status === 'completed' || offer.status === 'rejected' || offer.status === 'cancelled') && (
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
            <Pagination page={offersPage} total={offersTotal} onPage={setOffersPage} />
          </div>
        </div>
      )}

      {/* ═══════════════════ DASHBOARD TAB ═══════════════════ */}
      {activeTab === 'Dashboard' && (
        <div className="space-y-6">
          {dashboardLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : !dashboard ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
              <LayoutDashboard className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-300 mb-2">No Dashboard Data</h3>
              <p className="text-sm text-slate-500">Marketplace data will populate as listings and offers are created.</p>
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <MkSummaryCard
                  title="Expiring Items"
                  value={dashboard.expiring_items || dashboard.total_expiring || 0}
                  icon={AlertTriangle}
                  color="amber"
                  subtitle="Needing attention"
                />
                <MkSummaryCard
                  title="Demand Matches"
                  value={dashboard.demand_matches || dashboard.total_matches || 0}
                  icon={Handshake}
                  color="indigo"
                  subtitle="Active opportunities"
                />
                <MkSummaryCard
                  title="Pending Offers"
                  value={dashboard.pending_offers || dashboard.offers_by_status?.pending || 0}
                  icon={Clock}
                  color="amber"
                  subtitle="Awaiting action"
                />
                <MkSummaryCard
                  title="Completed"
                  value={dashboard.completed_offers || dashboard.offers_by_status?.completed || 0}
                  icon={CheckCircle}
                  color="emerald"
                  subtitle="Successful deals"
                />
                <MkSummaryCard
                  title="Rejected"
                  value={dashboard.rejected_offers || dashboard.offers_by_status?.rejected || 0}
                  icon={XCircle}
                  color="red"
                  subtitle="Declined offers"
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Expiring Medicines */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Top Expiring Medicines
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium">
                      Soonest first
                    </span>
                  </h3>
                  <div className="max-h-96 overflow-y-auto space-y-2">
                    {(dashboard.top_expiring || []).length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-8">No expiring medicines</p>
                    ) : (
                      (dashboard.top_expiring || []).slice(0, 15).map((item, idx) => {
                        const daysLeft = getDaysLeft(item.expiry_date);
                        return (
                          <div
                            key={idx}
                            className={`flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/30 transition-colors ${getUrgencyRowBg(daysLeft)}`}
                          >
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-200 truncate">
                                {item.brand_name || item.name || item.salt_name || `Med #${item.med_id}`}
                              </p>
                              <p className="text-xs text-slate-500">
                                {item.shop_name || `Shop #${item.shop_id}`} · {item.quantity || 0} units
                              </p>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                              {item.discount_percentage != null && (
                                <span className="text-xs text-emerald-400 font-medium">{item.discount_percentage}% off</span>
                              )}
                              <UrgencyBadge daysLeft={daysLeft} />
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Shop Activity */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-indigo-400" />
                    Shop Activity
                  </h3>
                  <div className="max-h-96 overflow-y-auto space-y-2">
                    {(dashboard.shop_activity || []).length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-8">No activity recorded</p>
                    ) : (
                      (dashboard.shop_activity || []).map((shop, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/30 transition-colors"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
                              <Store className="w-4 h-4 text-indigo-400" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-slate-200 truncate">{shop.shop_name || shop.name || `Shop #${shop.shop_id}`}</p>
                              <p className="text-xs text-slate-500">
                                {shop.city || shop.location || ''}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4 flex-shrink-0 ml-3">
                            <div className="text-center">
                              <p className="text-[10px] text-slate-500 uppercase">Listings</p>
                              <p className="text-sm font-bold text-amber-400">{shop.listings || shop.expiring_count || 0}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[10px] text-slate-500 uppercase">Offers</p>
                              <p className="text-sm font-bold text-indigo-400">{shop.offers || shop.offer_count || 0}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[10px] text-slate-500 uppercase">Completed</p>
                              <p className="text-sm font-bold text-emerald-400">{shop.completed || shop.completed_count || 0}</p>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
      {/* ═══════════════════ CREATE OFFER MODAL ═══════════════════ */}
      {showCreateOffer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCreateOffer(false)} />
          <div className="relative bg-slate-900 border border-slate-700/50 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-500/15 flex items-center justify-center">
                  <Send className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">Create Marketplace Offer</h2>
                  <p className="text-xs text-slate-400">Offer expiring inventory to another shop</p>
                </div>
              </div>
              <button
                onClick={() => setShowCreateOffer(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error */}
            {createOfferError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-sm text-red-400">{createOfferError}</p>
              </div>
            )}

            <form onSubmit={handleCreateOffer} className="space-y-4">
              {/* Source Shop */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Source Shop <span className="text-red-400">*</span>
                </label>
                <select
                  value={createOfferForm.from_shop_id}
                  onChange={(e) => {
                    const val = e.target.value;
                    setCreateOfferForm({ ...createOfferForm, from_shop_id: val, inventory_item_id: '' });
                    fetchExpiringItems(val);
                  }}
                  required
                  className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                >
                  <option value="">Select source shop</option>
                  {shops.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>

              {/* Inventory Item (expiring items from source shop) */}
              {expiringItems.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Inventory Item (optional)
                  </label>
                  <select
                    value={createOfferForm.inventory_item_id}
                    onChange={(e) => {
                      const item = expiringItems.find((i) => String(i.id) === e.target.value);
                      if (item) {
                        setCreateOfferForm({
                          ...createOfferForm,
                          inventory_item_id: e.target.value,
                          quantity: String(item.quantity || ''),
                          price_per_unit: item.unit_price != null ? String(item.unit_price) : item.selling_price != null ? String(item.selling_price) : createOfferForm.price_per_unit,
                        });
                      } else {
                        setCreateOfferForm({ ...createOfferForm, inventory_item_id: e.target.value });
                      }
                    }}
                    className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                  >
                    <option value="">Select an item</option>
                    {expiringItems.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.brand_name || item.salt_name || `#${item.med_id}`} — {item.quantity || 0} units — Exp: {formatDate(item.expiry_date)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Destination Shop */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Destination Shop <span className="text-red-400">*</span>
                </label>
                <select
                  value={createOfferForm.to_shop_id}
                  onChange={(e) => setCreateOfferForm({ ...createOfferForm, to_shop_id: e.target.value })}
                  required
                  className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                >
                  <option value="">Select destination shop</option>
                  {shops
                    .filter((s) => String(s.id) !== createOfferForm.from_shop_id)
                    .map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                </select>
              </div>

              {/* Quantity + Price row */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Quantity <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={createOfferForm.quantity}
                    onChange={(e) => setCreateOfferForm({ ...createOfferForm, quantity: e.target.value })}
                    required
                    placeholder="e.g. 50"
                    className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Price per Unit (₹)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={createOfferForm.price_per_unit}
                    onChange={(e) => setCreateOfferForm({ ...createOfferForm, price_per_unit: e.target.value })}
                    placeholder="e.g. 25.00"
                    className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Notes (optional)
                </label>
                <textarea
                  value={createOfferForm.notes}
                  onChange={(e) => setCreateOfferForm({ ...createOfferForm, notes: e.target.value })}
                  placeholder="Add any additional notes..."
                  rows={3}
                  className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 resize-none"
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateOffer(false);
                    setCreateOfferError('');
                  }}
                  className="px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createOfferLoading}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
                >
                  {createOfferLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {createOfferLoading ? 'Creating...' : 'Create Offer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Summary Card Component ──────────────────────────
function MkSummaryCard({ title, value, icon: Icon, color, subtitle }) {
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
    <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5 transition-all duration-200">
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
