import { useState, useEffect, useMemo, useRef } from 'react';
import {
  Package, Search, Filter, Plus, X, Loader2, AlertTriangle,
  ChevronLeft, ChevronRight, Camera, Upload,
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
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanImage, setScanImage] = useState(null);
  const [scanImagePreview, setScanImagePreview] = useState(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState('');
  const pageSize = 20;

  const cameraRef = useRef(null);
  const fileRef = useRef(null);

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

  const handleScanImageSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setScanError('Please select an image file');
      return;
    }
    setScanImage(file);
    setScanError('');
    const reader = new FileReader();
    reader.onload = () => setScanImagePreview(reader.result);
    reader.readAsDataURL(file);
  };

  const handleScanSubmit = async () => {
    if (!scanImage) return;
    setScanLoading(true);
    setScanError('');
    setScanResult(null);
    try {
      const { data } = await inventoryAPI.scanMedicine(scanImage);
      setScanResult(data);
      // Auto-fill the add form with scanned data
      if (data.brand_name || data.salt_name) {
        setAddForm(prev => ({
          ...prev,
          batch_number: data.batch_number || prev.batch_number,
          expiry_date: data.expiry_date || prev.expiry_date,
          quantity: data.quantity ? String(data.quantity) : prev.quantity,
          selling_price: data.mrp ? String(data.mrp) : prev.selling_price,
        }));
      }
    } catch (err) {
      setScanError(err.response?.data?.detail || 'Failed to analyze image. Please try again.');
    } finally {
      setScanLoading(false);
    }
  };

  const handleScanUseData = () => {
    setShowScanModal(false);
    // Reset scan state
    setScanImage(null);
    setScanImagePreview(null);
    setScanResult(null);
    setScanError('');
    // Open add modal with pre-filled data
    setShowAddModal(true);
  };

  const resetScan = () => {
    setScanImage(null);
    setScanImagePreview(null);
    setScanResult(null);
    setScanError('');
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
        <div className="flex items-center gap-3">
          <button
            onClick={() => { resetScan(); setShowScanModal(true); }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-emerald-600/20"
          >
            <Camera className="w-4 h-4" />
            Scan Medicine
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            Add Stock
          </button>
        </div>
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
      {/* Scan Medicine Modal */}
      {showScanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowScanModal(false)} />
          <div className="relative bg-slate-900 border border-slate-700/50 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Camera className="w-5 h-5 text-emerald-400" />
                Scan Medicine Packaging
              </h2>
              <button onClick={() => setShowScanModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Hidden file inputs */}
            <input type="file" accept="image/*" capture="environment" onChange={handleScanImageSelect} className="hidden" ref={cameraRef} />
            <input type="file" accept="image/*" onChange={handleScanImageSelect} className="hidden" ref={fileRef} />

            {/* Source selection buttons */}
            {!scanImagePreview && !scanLoading && (
              <div className="space-y-3 mb-4">
                <p className="text-sm text-slate-400">Capture or upload a photo of the medicine packaging to automatically extract details.</p>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => cameraRef.current?.click()}
                    className="flex flex-col items-center gap-2 p-4 bg-slate-800/80 border border-slate-600/50 rounded-xl hover:border-emerald-500/50 hover:bg-slate-800 transition-all"
                  >
                    <Camera className="w-6 h-6 text-emerald-400" />
                    <span className="text-sm font-medium text-slate-300">Camera</span>
                    <span className="text-[11px] text-slate-500">Take a photo</span>
                  </button>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="flex flex-col items-center gap-2 p-4 bg-slate-800/80 border border-slate-600/50 rounded-xl hover:border-emerald-500/50 hover:bg-slate-800 transition-all"
                  >
                    <Upload className="w-6 h-6 text-emerald-400" />
                    <span className="text-sm font-medium text-slate-300">Upload</span>
                    <span className="text-[11px] text-slate-500">Choose a file</span>
                  </button>
                </div>
              </div>
            )}

            {/* Image preview area */}
            {scanImagePreview && !scanLoading && (
              <div className="mb-4">
                <div className={`relative rounded-xl overflow-hidden border-2 border-dashed ${scanResult ? 'border-emerald-500/50' : 'border-slate-600/50'} transition-colors`}>
                  <img
                    src={scanImagePreview}
                    alt="Scanned medicine packaging"
                    className="w-full max-h-64 object-contain bg-slate-800/60"
                  />
                  {!scanResult && (
                    <button
                      onClick={() => fileRef.current?.click()}
                      className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity"
                    >
                      <span className="px-3 py-1.5 bg-slate-900/90 text-sm text-slate-300 rounded-lg">Change Image</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Loading state */}
            {scanLoading && (
              <div className="flex flex-col items-center gap-3 py-8">
                <div className="relative">
                  <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
                  <Camera className="w-5 h-5 text-emerald-300 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                </div>
                <p className="text-sm text-slate-400">Analyzing medicine packaging...</p>
              </div>
            )}

            {/* Error display */}
            {scanError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-sm text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  {scanError}
                </p>
              </div>
            )}

            {/* Extracted results */}
            {scanResult && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-emerald-400">Extracted Information</h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                    scanResult.confidence === 'high'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : scanResult.confidence === 'partial'
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'bg-red-500/10 text-red-400'
                  }`}>
                    {scanResult.confidence === 'high' ? '✓ Extracted' : scanResult.confidence === 'partial' ? '~ Partial' : '⚠ Low confidence'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['Brand Name', scanResult.brand_name],
                    ['Salt / Active Ingredient', scanResult.salt_name],
                    ['Manufacturer', scanResult.manufacturer],
                    ['Strength', scanResult.strength],
                    ['Dosage Form', scanResult.dosage_form],
                    ['Batch Number', scanResult.batch_number],
                    ['Expiry Date', scanResult.expiry_date],
                    ['Quantity', scanResult.quantity],
                    ['MRP', scanResult.mrp ? `₹${scanResult.mrp}` : null],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-slate-800/60 rounded-lg p-3">
                      <p className="text-[11px] text-slate-500 uppercase tracking-wider">{label}</p>
                      <p className="text-sm font-medium text-slate-200 mt-0.5">
                        {value || <span className="text-slate-600 italic">Not detected</span>}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex justify-end gap-3 pt-5 mt-4 border-t border-slate-800/50">
              {scanResult ? (
                <>
                  <button
                    onClick={resetScan}
                    className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={handleScanUseData}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    Use This Data
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setShowScanModal(false)}
                    className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  {scanImagePreview && !scanLoading && (
                    <button
                      onClick={handleScanSubmit}
                      disabled={scanLoading}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      <Camera className="w-4 h-4" />
                      Analyze
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
