import { useState, useEffect } from 'react';
import {
  Store, MapPin, Phone, Mail, Package, AlertTriangle,
  Loader2, Map,
} from 'lucide-react';
import { shopsAPI, inventoryAPI } from '../services/api';

export default function ShopsPage() {
  const [shops, setShops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [shopStats, setShopStats] = useState({});

  useEffect(() => {
    fetchShops();
  }, []);

  const fetchShops = async () => {
    setLoading(true);
    try {
      const { data } = await shopsAPI.list({ size: 100 });
      const shopList = data?.items || [];
      setShops(shopList);

      // Fetch inventory for each shop to get stats
      const statsPromises = shopList.map(async (shop) => {
        try {
          const [invRes, expRes] = await Promise.allSettled([
            inventoryAPI.list({ shop_id: shop.id, size: 1 }),
            inventoryAPI.expiringAlerts({ expiring_within_days: 30 }),
          ]);
          const totalItems = invRes.status === 'fulfilled' ? (invRes.value.data?.total || 0) : 0;
          const expiringItems = expRes.status === 'fulfilled'
            ? (Array.isArray(expRes.value.data) ? expRes.value.data.filter(i => i.shop_id === shop.id).length : 0)
            : 0;
          return { [shop.id]: { totalItems, expiringItems } };
        } catch {
          return { [shop.id]: { totalItems: shop.inventory_count || 0, expiringItems: 0 } };
        }
      });

      const statsResults = await Promise.all(statsPromises);
      const statsMap = statsResults.reduce((acc, stat) => ({ ...acc, ...stat }), {});
      setShopStats(statsMap);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
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
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Store className="w-6 h-6 text-cyan-400" />
          Shops & Locations
        </h1>
        <p className="text-sm text-slate-400 mt-1">{shops.length} registered pharmacy locations</p>
      </div>

      {/* Map Placeholder */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-6">
        <div className="bg-slate-800/40 border-2 border-dashed border-slate-700/50 rounded-xl h-48 flex flex-col items-center justify-center">
          <Map className="w-10 h-10 text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-500">Map Integration Coming Soon</p>
          <p className="text-xs text-slate-600 mt-1">Interactive map showing all pharmacy locations</p>
        </div>
      </div>

      {/* Shop Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {shops.map((shop) => {
          const stats = shopStats[shop.id] || { totalItems: shop.inventory_count || 0, expiringItems: 0 };
          return (
            <div
              key={shop.id}
              className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5 hover:border-slate-600/50 transition-all duration-200"
            >
              {/* Shop Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-base font-semibold text-white">{shop.name}</h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{shop.code}</p>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  shop.is_active !== false
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-slate-700/50 text-slate-400'
                }`}>
                  {shop.is_active !== false ? 'Active' : 'Inactive'}
                </span>
              </div>

              {/* Location */}
              <div className="space-y-2 mb-4">
                {shop.address && (
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                    <p className="text-sm text-slate-400">{shop.address}, {shop.city}{shop.state ? `, ${shop.state}` : ''}{shop.pincode ? ` ${shop.pincode}` : ''}</p>
                  </div>
                )}
                {shop.contact_phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <p className="text-sm text-slate-400">{shop.contact_phone}</p>
                  </div>
                )}
                {shop.contact_email && (
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <p className="text-sm text-slate-400">{shop.contact_email}</p>
                  </div>
                )}
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-800/50">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Package className="w-3 h-3 text-indigo-400" />
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Total Items</p>
                  </div>
                  <p className="text-lg font-bold text-slate-200">{stats.totalItems}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Expiring</p>
                  </div>
                  <p className={`text-lg font-bold ${stats.expiringItems > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                    {stats.expiringItems}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {shops.length === 0 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <Store className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-sm text-slate-500">No shops registered yet.</p>
        </div>
      )}
    </div>
  );
}
