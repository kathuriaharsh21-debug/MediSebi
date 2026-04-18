import { useState, useEffect, useMemo } from 'react';
import {
  Package, Search, Filter, Plus, X, Loader2, AlertTriangle,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { inventoryAPI, shopsAPI, medicinesAPI } from '../services/api';

export default function InventoryPage() {
  const [inventory, setInventory] = useState([]);
  const [shops, setShops] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [shopFilter, setShopFilter] = useState('');
  const [expiryFilter, setExpiryFilter] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({
    med_id: '', shop_id: '', quantity: '', batch_number: '', expiry_date: '',
    cost_price: '', selling_price: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState('');
  const pageSize = 20;

  useEffect(() => {
    fetchShops();
    fetchMedicines();
  }, []);

  useEffect(() => {
    fetchInventory();
  }, [page, shopFilter, expiryFilter, lowStockOnly]);

  const fetchShops = async () => {
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      setShops(data?.items || []);
    } catch (e) { console.error(e); }
  };

  const fetchMedicines = async () => {
    try {
      const { data } = await medicinesAPI.list({ size: 200 });
      setMedicines(data?.items || []);
    } catch (e) { console.error(e); }
  };

  const fetchInventory = async () => {
    setLoading(true);
    try {
      const params = { page, size: pageSize };
      if (shopFilter) params.shop_id = shopFilter;
      if (expiryFilter) params.expiring_within_days = expiryFilter;
      if (lowStockOnly) params.low_stock = 'true';
      const { data } = await inventoryAPI.list(params);
      setInventory(data?.items || []);
      setTotal(data?.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredInventory = useMemo(() => {
    if (!search) return inventory;
    const q = search.toLowerCase();
    return inventory.filter(
      (item) =>
        (item.brand_name || '').toLowerCase().includes(q) ||
        (item.salt_name || '').toLowerCase().includes(q) ||
        (item.shop_name || '').toLowerCase().includes(q) ||
        (item.batch_number || '').toLowerCase().includes(q)
    );
  }, [inventory, search]);

  const getExpiryInfo = (expiryDate) => {
    if (!expiryDate) return { color: 'text-slate-400', bg: '', label: '—' };
    const now = new Date();
    const expiry = new Date(expiryDate);
    const daysUntil = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
    if (daysUntil < 0) return { color: 'text-red-400', bg: 'bg-red-500/10', label: `Expired` };
    if (daysUntil <= 7) return { color: 'text-red-400', bg: 'bg-red-500/10', label: `${daysUntil}d left` };
    if (daysUntil <= 30) return { color: 'text-amber-400', bg: 'bg-amber-500/10', label: `${daysUntil}d left` };
    return { color: 'text-emerald-400', bg: 'bg-emerald-500/5', label: `${daysUntil}d left` };
  };

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const totalPages = Math.ceil(total / pageSize);

  const handleAddStock = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setAddError('');
    try {
      await inventoryAPI.create({
        med_id: parseInt(addForm.med_id),
        shop_id: parseInt(addForm.shop_id),
        quantity: parseInt(addForm.quantity),
        batch_number: addForm.batch_number || null,
        expiry_date: addForm.expiry_date,
        cost_price: addForm.cost_price ? parseFloat(addForm.cost_price) : null,
        selling_price: addForm.selling_price ? parseFloat(addForm.selling_price) : null,
      });
      setShowAddModal(false);
      setAddForm({ med_id: '', shop_id: '', quantity: '', batch_number: '', expiry_date: '', cost_price: '', selling_price: '' });
      fetchInventory();
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to add stock');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Package className="w-6 h-6 text-indigo-400" />
            Inventory Management
          </h1>
          <p className="text-sm text-slate-400 mt-1">Track stock levels, expiry dates, and pricing</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          Add Stock
        </button>
      </div>

      {/* Filters */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Filters</span>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by medicine, salt, shop, or batch..."
              className="w-full pl-9 pr-4 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
            />
          </div>
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
            value={expiryFilter}
            onChange={(e) => { setExpiryFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <option value="">All Expiry</option>
            <option value="30">Expiring within 30 days</option>
            <option value="60">Expiring within 60 days</option>
            <option value="90">Expiring within 90 days</option>
          </select>
          <label className="inline-flex items-center gap-2 px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg cursor-pointer hover:border-slate-500 transition-colors">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => { setLowStockOnly(e.target.checked); setPage(1); }}
              className="w-4 h-4 rounded border-slate-600 text-red-500 focus:ring-red-500/50 bg-slate-700"
            />
            <span className="text-sm text-slate-300">Low Stock Only</span>
          </label>
          {(shopFilter || expiryFilter || lowStockOnly) && (
            <button
              onClick={() => { setShopFilter(''); setExpiryFilter(''); setLowStockOnly(false); setPage(1); }}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" />
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
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Medicine</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Shop</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Batch</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Unit Price</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Expiry</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : filteredInventory.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                    No inventory items found
                  </td>
                </tr>
              ) : (
                filteredInventory.map((item) => {
                  const exp = getExpiryInfo(item.expiry_date);
                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-slate-200">{item.brand_name || `#${item.med_id}`}</p>
                        <p className="text-xs text-slate-500">{item.salt_name || ''}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">{item.shop_name || `#${item.shop_id}`}</td>
                      <td className="px-4 py-3 text-sm text-slate-400 font-mono">{item.batch_number || '—'}</td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-slate-200">{item.quantity}</td>
                      <td className="px-4 py-3 text-sm text-right text-slate-400">
                        {item.selling_price != null ? `₹${item.selling_price}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-slate-400">{formatDate(item.expiry_date)}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${exp.color} ${exp.bg}`}>
                          {exp.label}
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
              Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
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

      {/* Add Stock Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowAddModal(false)} />
          <div className="relative bg-slate-900 border border-slate-700/50 rounded-2xl w-full max-w-lg p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-white">Add Stock</h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {addError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-sm text-red-400">{addError}</p>
              </div>
            )}

            <form onSubmit={handleAddStock} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Medicine</label>
                <select
                  value={addForm.med_id}
                  onChange={(e) => setAddForm({ ...addForm, med_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                >
                  <option value="">Select medicine...</option>
                  {medicines.map((m) => (
                    <option key={m.id} value={m.id}>{m.brand_name} — {m.salt_name || ''}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Shop</label>
                <select
                  value={addForm.shop_id}
                  onChange={(e) => setAddForm({ ...addForm, shop_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                >
                  <option value="">Select shop...</option>
                  {shops.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} — {s.city}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Quantity</label>
                  <input
                    type="number"
                    min="0"
                    value={addForm.quantity}
                    onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })}
                    required
                    className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Batch Number</label>
                  <input
                    type="text"
                    value={addForm.batch_number}
                    onChange={(e) => setAddForm({ ...addForm, batch_number: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Expiry Date</label>
                <input
                  type="date"
                  value={addForm.expiry_date}
                  onChange={(e) => setAddForm({ ...addForm, expiry_date: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Cost Price (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={addForm.cost_price}
                    onChange={(e) => setAddForm({ ...addForm, cost_price: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Selling Price (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={addForm.selling_price}
                    onChange={(e) => setAddForm({ ...addForm, selling_price: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  Add Stock
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
