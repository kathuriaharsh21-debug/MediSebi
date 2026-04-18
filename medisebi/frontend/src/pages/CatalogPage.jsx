import { useState, useEffect, useCallback, useRef } from 'react';
import {
  BookOpen, Search, Package, CheckCircle, XCircle, Plus,
  RefreshCw, ShoppingCart, AlertCircle, Info, Loader2,
  ChevronLeft, ChevronRight, X, PackageCheck,
} from 'lucide-react';
import { catalogAPI, shopsAPI } from '../services/api';

// ─── Constants ──────────────────────────────────────
const TABS = [
  { key: 'browse', label: 'Browse', icon: BookOpen },
  { key: 'quick-add', label: 'Quick Add', icon: Plus },
  { key: 'stock-check', label: 'Stock Check', icon: PackageCheck },
];

const ABC_COLORS = {
  A: 'bg-red-500/15 text-red-400 border border-red-500/30',
  B: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  C: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
};

const PAGE_SIZE = 20;

// ─── Main Component ────────────────────────────────
export default function CatalogPage() {
  const [activeTab, setActiveTab] = useState('browse');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-indigo-400" />
          Medicine Catalog
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Master catalog browser, quick stock additions, and shop stock verification
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 bg-slate-900/80 border border-slate-700/50 rounded-xl p-1.5">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === key
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      {activeTab === 'browse' && <BrowseTab />}
      {activeTab === 'quick-add' && <QuickAddTab />}
      {activeTab === 'stock-check' && <StockCheckTab />}
    </div>
  );
}

// ─── Browse Tab ────────────────────────────────────
function BrowseTab() {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const debounceRef = useRef(null);
  const isSearchRef = useRef(false);

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchCatalog();
  }, [page, activeCategory]);

  const fetchCategories = async () => {
    setCategoriesLoading(true);
    try {
      const { data } = await catalogAPI.categories();
      setCategories(Array.isArray(data) ? data : data?.items || data?.categories || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    } finally {
      setCategoriesLoading(false);
    }
  };

  const fetchCatalog = async (query = '') => {
    setLoading(true);
    setError('');
    try {
      const params = { page, size: PAGE_SIZE };
      if (query) {
        const { data } = await catalogAPI.search({ q: query, page, size: PAGE_SIZE });
        setItems(data?.items || data?.results || []);
        setTotal(data?.total || data?.count || 0);
      } else {
        if (activeCategory) params.category = activeCategory;
        const { data } = await catalogAPI.browse(params);
        setItems(data?.items || data?.results || []);
        setTotal(data?.total || data?.count || 0);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (value) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    isSearchRef.current = !!value;
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetchCatalog(value);
    }, 300);
  };

  const handleCategoryClick = (cat) => {
    setActiveCategory(cat === activeCategory ? '' : cat);
    setSearch('');
    setPage(1);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search catalog by brand name, salt, manufacturer..."
            className="w-full pl-9 pr-4 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
          />
          {search && (
            <button
              onClick={() => handleSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap gap-2 mt-3">
          {!categoriesLoading && categories.length > 0 && (
            <button
              onClick={() => handleCategoryClick('')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                !activeCategory
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-500 hover:text-slate-300'
              }`}
            >
              All
            </button>
          )}
          {categoriesLoading ? (
            <div className="flex gap-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-6 w-16 rounded-full bg-slate-800 animate-pulse" />
              ))}
            </div>
          ) : (
            categories.map((cat) => {
              const catName = typeof cat === 'string' ? cat : cat.name || cat.category || cat;
              return (
                <button
                  key={catName}
                  onClick={() => handleCategoryClick(catName)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    activeCategory === catName
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-500 hover:text-slate-300'
                  }`}
                >
                  {catName}
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
        {error && (
          <div className="mx-4 mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Brand Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Salt Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Strength</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Form</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Manufacturer</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Price</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">ABC</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Reorder</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Safety</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-sm text-slate-500">
                    {search ? 'No results found for your search' : 'No catalog items available'}
                  </td>
                </tr>
              ) : (
                items.map((item, idx) => (
                  <tr key={item.id || item.catalog_index || idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-slate-200">{item.brand_name || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.salt_name || '—'}</td>
                    <td className="px-4 py-3">
                      {item.category ? (
                        <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-700/50 text-slate-300 border border-slate-600/50">
                          {item.category}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.strength || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.form || item.dosage_form || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.manufacturer || '—'}</td>
                    <td className="px-4 py-3 text-sm text-right text-slate-300 font-medium">
                      {item.price != null ? `₹${item.price}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.abc_class ? (
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${ABC_COLORS[item.abc_class] || 'bg-slate-700 text-slate-400'}`}>
                          {item.abc_class}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-slate-400">
                      {item.reorder_level != null ? item.reorder_level : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-slate-400">
                      {item.safety_stock != null ? item.safety_stock : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.is_critical ? (
                        <AlertCircle className="w-4 h-4 text-red-400 mx-auto" />
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/50">
            <p className="text-xs text-slate-500">
              Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
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

// ─── Quick Add Tab ─────────────────────────────────
function QuickAddTab() {
  const [step, setStep] = useState(1);
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState('');
  const [catalogItems, setCatalogItems] = useState([]);
  const [selectedMedicine, setSelectedMedicine] = useState(null);
  const [medSearch, setMedSearch] = useState('');
  const [form, setForm] = useState({
    quantity: '',
    batch_number: '',
    expiry_date: '',
    cost_price: '',
    selling_price: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState('');
  const [recentAdditions, setRecentAdditions] = useState([]);
  const [loading, setLoading] = useState({ shops: false, catalog: false });
  const debounceRef = useRef(null);

  useEffect(() => {
    fetchShops();
  }, []);

  const fetchShops = async () => {
    setLoading((prev) => ({ ...prev, shops: true }));
    try {
      const { data } = await shopsAPI.list({ size: 200 });
      setShops(data?.items || []);
    } catch (err) {
      console.error('Failed to fetch shops:', err);
    } finally {
      setLoading((prev) => ({ ...prev, shops: false }));
    }
  };

  const fetchCatalogForSelection = useCallback(async (query = '') => {
    setLoading((prev) => ({ ...prev, catalog: true }));
    try {
      let result;
      if (query) {
        const { data } = await catalogAPI.search({ q: query, page: 1, size: 50 });
        result = data?.items || data?.results || [];
      } else {
        const { data } = await catalogAPI.browse({ page: 1, size: 50 });
        result = data?.items || data?.results || [];
      }
      setCatalogItems(result);
    } catch (err) {
      console.error('Failed to fetch catalog:', err);
    } finally {
      setLoading((prev) => ({ ...prev, catalog: false }));
    }
  }, []);

  useEffect(() => {
    if (step === 2) {
      fetchCatalogForSelection('');
    }
  }, [step, fetchCatalogForSelection]);

  const handleMedSearch = (value) => {
    setMedSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchCatalogForSelection(value);
    }, 300);
  };

  const handleSelectMedicine = (item) => {
    setSelectedMedicine(item);
    setStep(3);
  };

  const handleAddToInventory = async (e) => {
    e.preventDefault();
    if (!selectedShop || !selectedMedicine) return;

    setSubmitting(true);
    setAddError('');
    try {
      const payload = {
        shop_id: parseInt(selectedShop),
        catalog_index: selectedMedicine.catalog_index || selectedMedicine.id,
        med_id: selectedMedicine.med_id || selectedMedicine.id,
        brand_name: selectedMedicine.brand_name,
        salt_name: selectedMedicine.salt_name,
        quantity: parseInt(form.quantity),
        batch_number: form.batch_number || null,
        expiry_date: form.expiry_date,
        cost_price: form.cost_price ? parseFloat(form.cost_price) : null,
        selling_price: form.selling_price ? parseFloat(form.selling_price) : null,
      };

      await catalogAPI.quickAdd(payload);

      // Add to recent
      setRecentAdditions((prev) => [
        {
          ...payload,
          added_at: new Date().toISOString(),
        },
        ...prev,
      ]);

      // Reset form
      setForm({ quantity: '', batch_number: '', expiry_date: '', cost_price: '', selling_price: '' });
      setSelectedMedicine(null);
      setStep(1);
      setSelectedShop('');
      setMedSearch('');
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to add to inventory');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-4">
      {/* Stepper */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center gap-3">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-3 flex-1">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold transition-colors ${
                step >= s
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-500 border border-slate-700'
              }`}>
                {step > s ? <CheckCircle className="w-4 h-4" /> : s}
              </div>
              <span className={`text-xs font-medium transition-colors ${
                step >= s ? 'text-slate-200' : 'text-slate-500'
              }`}>
                {s === 1 ? 'Select Shop' : s === 2 ? 'Pick Medicine' : 'Details'}
              </span>
              {s < 3 && (
                <div className={`flex-1 h-px ${step > s ? 'bg-indigo-500/50' : 'bg-slate-700'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step 1: Shop Selection */}
      {step === 1 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Package className="w-4 h-4 text-indigo-400" />
            Step 1: Select a Shop
          </h3>
          {loading.shops ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
              {shops.map((shop) => (
                <button
                  key={shop.id}
                  onClick={() => {
                    setSelectedShop(String(shop.id));
                    setStep(2);
                  }}
                  className={`p-4 rounded-lg border text-left transition-all duration-200 ${
                    selectedShop === String(shop.id)
                      ? 'bg-indigo-500/10 border-indigo-500/40 text-white'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800'
                  }`}
                >
                  <p className="text-sm font-medium">{shop.name}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {shop.address || shop.city || `Shop #${shop.id}`}
                  </p>
                </button>
              ))}
              {shops.length === 0 && (
                <div className="col-span-full py-8 text-center text-sm text-slate-500">
                  No shops available
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Medicine Selection */}
      {step === 2 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Search className="w-4 h-4 text-indigo-400" />
              Step 2: Pick a Medicine
            </h3>
            <button
              onClick={() => setStep(1)}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              ← Back to shops
            </button>
          </div>

          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={medSearch}
              onChange={(e) => handleMedSearch(e.target.value)}
              placeholder="Search by brand name, salt, or manufacturer..."
              className="w-full pl-9 pr-4 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
            />
          </div>

          <div className="max-h-96 overflow-y-auto space-y-2">
            {loading.catalog ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
              </div>
            ) : catalogItems.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-8">No medicines found</p>
            ) : (
              catalogItems.map((item, idx) => (
                <button
                  key={item.id || item.catalog_index || idx}
                  onClick={() => handleSelectMedicine(item)}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:border-indigo-500/40 hover:bg-slate-800 transition-all duration-200 text-left"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200 truncate">{item.brand_name || '—'}</p>
                    <p className="text-xs text-slate-500 truncate">
                      {item.salt_name || ''} {item.strength ? `· ${item.strength}` : ''} {item.form ? `· ${item.form}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-3">
                    {item.price != null && (
                      <span className="text-sm font-medium text-indigo-400">₹{item.price}</span>
                    )}
                    <Plus className="w-4 h-4 text-slate-500" />
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Step 3: Details Form */}
      {step === 3 && selectedMedicine && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-indigo-400" />
                Step 3: Stock Details
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                {selectedMedicine.brand_name} — {selectedMedicine.salt_name}
              </p>
            </div>
            <button
              onClick={() => {
                setStep(2);
                setSelectedMedicine(null);
              }}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              ← Back to catalog
            </button>
          </div>

          {addError && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">{addError}</p>
            </div>
          )}

          <form onSubmit={handleAddToInventory} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Quantity *</label>
                <input
                  type="number"
                  min="1"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  required
                  placeholder="e.g. 100"
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Batch Number</label>
                <input
                  type="text"
                  value={form.batch_number}
                  onChange={(e) => setForm({ ...form, batch_number: e.target.value })}
                  placeholder="e.g. BTH20240101"
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Expiry Date *</label>
              <input
                type="date"
                value={form.expiry_date}
                onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                required
                className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Cost Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.cost_price}
                  onChange={(e) => setForm({ ...form, cost_price: e.target.value })}
                  placeholder="0.00"
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Selling Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.selling_price}
                  onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
                  placeholder="0.00"
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setStep(2);
                  setSelectedMedicine(null);
                }}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                Add to Inventory
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Recent Additions */}
      {recentAdditions.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Recent Additions
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">
              {recentAdditions.length}
            </span>
          </h3>
          <div className="max-h-48 overflow-y-auto space-y-2">
            {recentAdditions.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-emerald-500/5 border-l-2 border-l-emerald-500"
              >
                <div>
                  <p className="text-sm font-medium text-slate-200">{item.brand_name || `Med #${item.med_id}`}</p>
                  <p className="text-xs text-slate-500">
                    {item.salt_name || ''} · Qty: {item.quantity} · Batch: {item.batch_number || 'N/A'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">{formatDate(item.added_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Stock Check Tab ───────────────────────────────
function StockCheckTab() {
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [shopsLoading, setShopsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showMissingSummary, setShowMissingSummary] = useState(false);

  useEffect(() => {
    fetchShops();
  }, []);

  const fetchShops = async () => {
    setShopsLoading(true);
    try {
      const { data } = await shopsAPI.list({ size: 200 });
      setShops(data?.items || []);
    } catch (err) {
      console.error('Failed to fetch shops:', err);
    } finally {
      setShopsLoading(false);
    }
  };

  const handleStockCheck = async () => {
    if (!selectedShop) return;
    setLoading(true);
    setError('');
    setShowMissingSummary(false);
    try {
      const { data } = await catalogAPI.stockCheck(selectedShop);
      setResults(Array.isArray(data) ? data : data?.items || data?.results || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to check stock');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const inStockItems = results.filter((r) => r.in_stock);
  const missingItems = results.filter((r) => !r.in_stock);

  return (
    <div className="space-y-4">
      {/* Shop Selector */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-slate-300 mb-1">Select Shop</label>
            {shopsLoading ? (
              <div className="h-10 rounded-lg bg-slate-800 animate-pulse" />
            ) : (
              <select
                value={selectedShop}
                onChange={(e) => {
                  setSelectedShop(e.target.value);
                  setResults([]);
                  setShowMissingSummary(false);
                }}
                className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Choose a shop...</option>
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} — {s.city || s.address || `Shop #${s.id}`}
                  </option>
                ))}
              </select>
            )}
          </div>
          <button
            onClick={handleStockCheck}
            disabled={!selectedShop || loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/30 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Check Stock
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          {/* Summary bar */}
          <div className="flex items-center gap-4">
            <span className="text-xs text-slate-400">
              Total: <span className="font-medium text-white">{results.length}</span>
            </span>
            <span className="text-xs text-emerald-400">
              In Stock: <span className="font-medium">{inStockItems.length}</span>
            </span>
            <span className="text-xs text-red-400">
              Missing: <span className="font-medium">{missingItems.length}</span>
            </span>
          </div>

          {/* Results Table */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Brand Name</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Salt Name</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">In Stock</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Quantity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {results.map((item, idx) => {
                    const inStock = item.in_stock;
                    return (
                      <tr
                        key={idx}
                        className={`transition-colors ${
                          inStock
                            ? 'bg-emerald-500/5 hover:bg-emerald-500/10'
                            : 'bg-red-500/5 hover:bg-red-500/10'
                        }`}
                      >
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-slate-200">{item.brand_name || '—'}</p>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-400">{item.salt_name || '—'}</td>
                        <td className="px-4 py-3 text-center">
                          {inStock ? (
                            <CheckCircle className="w-5 h-5 text-emerald-400 mx-auto" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-400 mx-auto" />
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          <span className={`font-medium ${inStock ? 'text-emerald-400' : 'text-red-400'}`}>
                            {item.quantity != null ? item.quantity : '0'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Order Missing Button */}
          {missingItems.length > 0 && (
            <div className="flex justify-end">
              <button
                onClick={() => setShowMissingSummary(!showMissingSummary)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-red-600/20"
              >
                <ShoppingCart className="w-4 h-4" />
                Order All Missing ({missingItems.length})
              </button>
            </div>
          )}

          {/* Missing Summary */}
          {showMissingSummary && missingItems.length > 0 && (
            <div className="bg-slate-900/80 border border-red-500/20 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                Missing Items Summary
              </h3>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {missingItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-red-500/5 border-l-2 border-l-red-500"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-200">{item.brand_name || '—'}</p>
                      <p className="text-xs text-slate-500">{item.salt_name || ''}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-red-400">
                        {item.quantity != null ? item.quantity : 0} units
                      </p>
                      <p className="text-xs text-slate-500">
                        Reorder: {item.reorder_level != null ? item.reorder_level : '—'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/50 text-xs text-slate-500">
                Total missing items: {missingItems.length}
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state when no results yet */}
      {!loading && !error && results.length === 0 && selectedShop && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <Package className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">Click "Check Stock" to see the inventory status for this shop</p>
        </div>
      )}

      {/* Empty state when no shop selected */}
      {!selectedShop && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <Package className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">Select a shop above to check stock availability</p>
        </div>
      )}
    </div>
  );
}
