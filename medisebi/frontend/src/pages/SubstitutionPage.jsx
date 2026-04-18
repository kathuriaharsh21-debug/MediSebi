import { useState, useEffect } from 'react';
import { ArrowLeftRight, Search, Loader2, Star, Zap, Award } from 'lucide-react';
import { medicinesAPI, shopsAPI, substitutionAPI } from '../services/api';

export default function SubstitutionPage() {
  const [medicines, setMedicines] = useState([]);
  const [shops, setShops] = useState([]);
  const [selectedMed, setSelectedMed] = useState('');
  const [selectedShop, setSelectedShop] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDropdowns();
  }, []);

  const fetchDropdowns = async () => {
    try {
      const [medsRes, shopsRes] = await Promise.all([
        medicinesAPI.list({ size: 200 }),
        shopsAPI.list({ size: 100 }),
      ]);
      setMedicines(medsRes.data?.items || []);
      setShops(shopsRes.data?.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFind = async () => {
    if (!selectedMed || !selectedShop) return;
    setLoading(true);
    setError('');
    setResults(null);
    try {
      const { data } = await substitutionAPI.findAlternatives(
        parseInt(selectedMed),
        parseInt(selectedShop)
      );
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to find alternatives');
    } finally {
      setLoading(false);
    }
  };

  // Determine best match: highest stock, furthest from expiry
  const getBestMatch = (alternatives) => {
    if (!alternatives?.length) return null;
    const now = new Date();
    return alternatives.reduce((best, alt) => {
      const altExpiry = new Date(alt.expiry_date);
      const bestExpiry = new Date(best.expiry_date);
      const altScore = alt.available_quantity * 10 + (altExpiry - now) / (1000 * 60 * 60 * 24);
      const bestScore = best.available_quantity * 10 + (bestExpiry - now) / (1000 * 60 * 60 * 24);
      return altScore > bestScore ? alt : best;
    });
  };

  const bestMatch = results?.alternatives ? getBestMatch(results.alternatives) : null;

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <ArrowLeftRight className="w-6 h-6 text-purple-400" />
          Substitution Engine
        </h1>
        <p className="text-sm text-slate-400 mt-1">Find alternative brands with the same salt available at a shop</p>
      </div>

      {/* Selection Panel */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Search className="w-4 h-4 text-purple-400" />
          Find Alternatives
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Medicine</label>
            <select
              value={selectedMed}
              onChange={(e) => setSelectedMed(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500"
            >
              <option value="">Select a medicine...</option>
              {medicines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.brand_name} — {m.salt_name || 'Unknown Salt'}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Shop</label>
            <select
              value={selectedShop}
              onChange={(e) => setSelectedShop(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500"
            >
              <option value="">Select a shop...</option>
              {shops.map((s) => (
                <option key={s.id} value={s.id}>{s.name} — {s.city}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleFind}
              disabled={!selectedMed || !selectedShop || loading}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-purple-600/20"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              Find Alternatives
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4">
          {/* Results Header */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-sm text-slate-400">Requested</p>
                <p className="text-lg font-semibold text-white">{results.requested_medicine}</p>
                <p className="text-sm text-slate-400 mt-0.5">
                  Salt: <span className="text-indigo-400">{results.salt_name}</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-400">Total Available</p>
                <p className="text-2xl font-bold text-emerald-400">{results.total_available}</p>
                <p className="text-xs text-slate-500">units across alternatives</p>
              </div>
            </div>
          </div>

          {/* Alternatives List */}
          {results.alternatives.length === 0 ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-8 text-center">
              <ArrowLeftRight className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No alternatives found for this medicine at the selected shop.</p>
              <p className="text-xs text-slate-500 mt-1">Try a different medicine or shop.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.alternatives.map((alt, idx) => {
                const isBest = bestMatch && alt.medicine_id === bestMatch.medicine_id;
                return (
                  <div
                    key={idx}
                    className={`bg-slate-900/80 border rounded-xl p-5 transition-all duration-200 ${
                      isBest
                        ? 'border-emerald-500/50 ring-1 ring-emerald-500/20'
                        : 'border-slate-700/50 hover:border-slate-600/50'
                    }`}
                  >
                    {isBest && (
                      <div className="flex items-center gap-1.5 mb-3">
                        <Award className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Best Match</span>
                      </div>
                    )}
                    <h4 className="text-base font-semibold text-white mb-1">{alt.brand_name}</h4>
                    <p className="text-xs text-slate-500 mb-4">{alt.salt_name}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-slate-800/50 rounded-lg p-3">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Qty Available</p>
                        <p className={`text-lg font-bold ${isBest ? 'text-emerald-400' : 'text-slate-200'}`}>
                          {alt.available_quantity}
                        </p>
                      </div>
                      <div className="bg-slate-800/50 rounded-lg p-3">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Expiry</p>
                        <p className="text-sm font-medium text-slate-300">{formatDate(alt.expiry_date)}</p>
                      </div>
                    </div>
                    {alt.unit_price != null && (
                      <div className="mt-3 bg-slate-800/50 rounded-lg p-3">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Unit Price</p>
                        <p className="text-sm font-medium text-slate-300">₹{alt.unit_price}</p>
                      </div>
                    )}
                    <div className="mt-3 text-xs text-slate-500">
                      {alt.shop_name}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!results && !loading && !error && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <ArrowLeftRight className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400 mb-2">Select a medicine and shop</h3>
          <p className="text-sm text-slate-500">
            The substitution engine will find alternative brands sharing the same active salt(s) that have stock at the selected shop.
          </p>
        </div>
      )}
    </div>
  );
}
