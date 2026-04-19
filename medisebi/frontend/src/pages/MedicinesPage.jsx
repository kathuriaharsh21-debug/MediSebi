import { useState, useEffect, useMemo } from 'react';
import { Pill, Search, ChevronLeft, ChevronRight, Loader2, X } from 'lucide-react';
import { medicinesAPI, saltsAPI, inventoryAPI } from '../services/api';

export default function MedicinesPage() {
  const [medicines, setMedicines] = useState([]);
  const [salts, setSalts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedMed, setSelectedMed] = useState(null);
  const [stockDetails, setStockDetails] = useState([]);
  const [loadingStock, setLoadingStock] = useState(false);
  const pageSize = 20;

  useEffect(() => {
    fetchSalts();
  }, []);

  useEffect(() => {
    fetchMedicines();
  }, [page, categoryFilter]);

  const fetchSalts = async () => {
    try {
      const { data } = await saltsAPI.list({ size: 200 });
      setSalts(data?.items || []);
    } catch (e) { console.error(e); }
  };

  const fetchMedicines = async () => {
    setLoading(true);
    try {
      const params = { page, size: pageSize };
      if (categoryFilter) params.category = categoryFilter;
      const { data } = await medicinesAPI.list(params);
      setMedicines(data?.items || []);
      setTotal(data?.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const categories = useMemo(() => {
    const cats = new Set(salts.map((s) => s.category).filter(Boolean));
    return [...cats].sort();
  }, [salts]);

  const filteredMedicines = useMemo(() => {
    if (!search) return medicines;
    const q = search.toLowerCase();
    return medicines.filter(
      (med) =>
        (med.brand_name || '').toLowerCase().includes(q) ||
        (med.generic_name || '').toLowerCase().includes(q) ||
        (med.salt_name || '').toLowerCase().includes(q) ||
        (med.manufacturer || '').toLowerCase().includes(q) ||
        (med.strength || '').toLowerCase().includes(q)
    );
  }, [medicines, search]);

  const handleViewStock = async (medId) => {
    setSelectedMed(medId);
    setLoadingStock(true);
    try {
      const { data } = await inventoryAPI.list({ med_id: medId, size: 100 });
      setStockDetails(data?.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingStock(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Pill className="w-6 h-6 text-emerald-400" />
          Medicines
        </h1>
        <p className="text-sm text-slate-400 mt-1">Browse and manage registered medicines</p>
      </div>

      {/* Filters */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by brand, generic name, salt, manufacturer..."
              className="w-full pl-9 pr-4 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          {categoryFilter && (
            <button
              onClick={() => { setCategoryFilter(''); setPage(1); }}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" /> Clear
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
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Brand Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Salt</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Manufacturer</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Form</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Strength</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Price</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Stock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : filteredMedicines.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                    No medicines found
                  </td>
                </tr>
              ) : (
                filteredMedicines.map((med) => (
                  <tr key={med.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-slate-200">{med.brand_name}</p>
                      <p className="text-xs text-slate-500">{med.generic_name || ''}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{med.salt_name || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{med.manufacturer || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-300">
                        {med.dosage_form || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{med.strength || '—'}</td>
                    <td className="px-4 py-3 text-sm text-right text-slate-300 font-medium">
                      {med.unit_price != null ? `₹${med.unit_price}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleViewStock(med.id)}
                        className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                          selectedMed === med.id
                            ? 'bg-indigo-600 text-white'
                            : 'bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20'
                        }`}
                      >
                        View Stock
                      </button>
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
              Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                if (p > totalPages) return null;
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${p === page ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}>
                    {p}
                  </button>
                );
              })}
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Stock Details Panel */}
      {selectedMed && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Stock Details</h3>
            <button onClick={() => setSelectedMed(null)} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          {loadingStock ? (
            <div className="py-8 text-center">
              <Loader2 className="w-5 h-5 text-indigo-500 animate-spin mx-auto" />
            </div>
          ) : stockDetails.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-6">No stock available for this medicine</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-slate-400 uppercase tracking-wider">
                    <th className="text-left pb-3 px-3">Shop</th>
                    <th className="text-left pb-3 px-3">Batch</th>
                    <th className="text-right pb-3 px-3">Quantity</th>
                    <th className="text-right pb-3 px-3">Selling Price</th>
                    <th className="text-right pb-3 px-3">Expiry</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {stockDetails.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 text-sm text-slate-200">{item.shop_name || `#${item.shop_id}`}</td>
                      <td className="py-2.5 px-3 text-sm text-slate-400 font-mono">{item.batch_number || '—'}</td>
                      <td className="py-2.5 px-3 text-sm text-right text-slate-200 font-medium">{item.quantity}</td>
                      <td className="py-2.5 px-3 text-sm text-right text-slate-400">
                        {item.selling_price != null ? `₹${item.selling_price}` : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-sm text-right text-slate-400">{formatDate(item.expiry_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
