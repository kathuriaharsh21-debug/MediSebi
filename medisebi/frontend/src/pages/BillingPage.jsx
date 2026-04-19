import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Receipt, Plus, Loader2, X, Search, Filter, ChevronLeft, ChevronRight,
  Printer, Eye, Ban, TrendingUp, DollarSign, CreditCard, Banknote,
  Smartphone, Building2, Calendar, FileText, Package, AlertTriangle,
  CheckCircle2, Clock, XCircle, RefreshCw, IndianRupee, ShoppingCart,
  BarChart3, PieChart as PieChartIcon, User, Phone, Stethoscope,
  Percent, Tag, Undo2, CircleDollarSign, ChevronDown, Store,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { billingAPI, inventoryAPI, shopsAPI } from '../services/api';

// ─── Constants ───────────────────────────────────────────────────────
const PAYMENT_METHODS = [
  { value: 'cash', label: 'Cash', icon: Banknote, color: '#10B981' },
  { value: 'upi', label: 'UPI', icon: Smartphone, color: '#6366F1' },
  { value: 'card', label: 'Card', icon: CreditCard, color: '#F59E0B' },
  { value: 'net_banking', label: 'Net Banking', icon: Building2, color: '#EC4899' },
  { value: 'credit', label: 'Credit', icon: CircleDollarSign, color: '#EF4444' },
];

const STATUS_CONFIG = {
  paid: { label: 'Paid', icon: CheckCircle2, classes: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
  pending: { label: 'Pending', icon: Clock, classes: 'bg-amber-500/10 text-amber-400 border-amber-500/30' },
  cancelled: { label: 'Cancelled', icon: XCircle, classes: 'bg-red-500/10 text-red-400 border-red-500/30' },
  refunded: { label: 'Refunded', icon: Undo2, classes: 'bg-slate-500/10 text-slate-400 border-slate-500/30' },
};

const PERIOD_OPTIONS = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'year', label: 'This Year' },
  { value: 'custom', label: 'Custom' },
];

const PIE_COLORS = ['#10B981', '#6366F1', '#F59E0B', '#EC4899', '#EF4444'];

const CHART_COLORS = ['#6366F1', '#818CF8'];

// ─── Helpers ─────────────────────────────────────────────────────────
function getGSTPercent(unitPrice) {
  const p = parseFloat(unitPrice) || 0;
  if (p <= 100) return 5;
  if (p <= 500) return 12;
  return 18;
}

function formatCurrency(n) {
  return `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-IN', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

function formatDateTime(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('en-IN', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function getPaymentLabel(method) {
  const m = PAYMENT_METHODS.find((p) => p.value === method);
  return m ? m.label : method || '—';
}

function getStatusBadge(status) {
  const s = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${s.classes}`}>
      <s.icon className="w-3 h-3" />
      {s.label}
    </span>
  );
}

// ─── Custom Recharts Tooltip ─────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-600/50 rounded-lg p-3 shadow-xl">
        <p className="text-sm text-slate-300 font-medium mb-1">{label}</p>
        {payload.map((entry, idx) => (
          <p key={idx} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatCurrency(entry.value)}
          </p>
        ))}
      </div>
    );
  }
  return null;
}

function PieTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-600/50 rounded-lg p-3 shadow-xl">
        <p className="text-sm text-slate-300 font-medium">{payload[0].name}</p>
        <p className="text-sm" style={{ color: payload[0].payload.fill }}>
          {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  }
  return null;
}

// ─── Empty Item Template ─────────────────────────────────────────────
function createEmptyItem() {
  return { inventory_id: '', quantity: 1 };
}

// ═══════════════════════════════════════════════════════════════════════
//  Main Component
// ═══════════════════════════════════════════════════════════════════════
export default function BillingPage() {
  // ─── Tab State ───────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('newBill');

  // ─── Shared Data ─────────────────────────────────────────────
  const [shops, setShops] = useState([]);
  const [shopsLoading, setShopsLoading] = useState(false);

  // ─── New Bill State ───────────────────────────────────────────
  const [billShopId, setBillShopId] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [doctorName, setDoctorName] = useState('');
  const [discountPercent, setDiscountPercent] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [billItems, setBillItems] = useState([createEmptyItem()]);
  const [inventory, setInventory] = useState([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [submittingBill, setSubmittingBill] = useState(false);
  const [billError, setBillError] = useState('');
  const [billSuccess, setBillSuccess] = useState('');

  // ─── History State ────────────────────────────────────────────
  const [bills, setBills] = useState([]);
  const [billsLoading, setBillsLoading] = useState(false);
  const [billsTotal, setBillsTotal] = useState(0);
  const [billsPage, setBillsPage] = useState(1);
  const [histShopFilter, setHistShopFilter] = useState('');
  const [histStatusFilter, setHistStatusFilter] = useState('');
  const [histDateFrom, setHistDateFrom] = useState('');
  const [histDateTo, setHistDateTo] = useState('');
  const [todaySummary, setTodaySummary] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [histError, setHistError] = useState('');
  const billsPageSize = 15;

  // ─── Revenue State ────────────────────────────────────────────
  const [revPeriod, setRevPeriod] = useState('today');
  const [revShopId, setRevShopId] = useState('');
  const [revCustomFrom, setRevCustomFrom] = useState('');
  const [revCustomTo, setRevCustomTo] = useState('');
  const [revData, setRevData] = useState(null);
  const [revLoading, setRevLoading] = useState(false);
  const [revError, setRevError] = useState('');

  // ─── Receipt State ────────────────────────────────────────────
  const [receiptBill, setReceiptBill] = useState(null);
  const [receiptLoading, setReceiptLoading] = useState(false);

  // ─── Fetch Shops ──────────────────────────────────────────────
  useEffect(() => {
    const fetchShops = async () => {
      setShopsLoading(true);
      try {
        const { data } = await shopsAPI.list({ size: 100 });
        setShops(data?.items || data || []);
        if (data?.items?.length === 1 && !billShopId) {
          setBillShopId(String(data.items[0].id));
        }
      } catch (e) {
        console.error('Failed to fetch shops:', e);
      } finally {
        setShopsLoading(false);
      }
    };
    fetchShops();
  }, []);

  // ─── Fetch Inventory When Shop Changes ────────────────────────
  useEffect(() => {
    if (!billShopId) {
      setInventory([]);
      return;
    }
    const fetchInventory = async () => {
      setInventoryLoading(true);
      try {
        const { data } = await inventoryAPI.list({
          shop_id: billShopId,
          size: 500,
        });
        setInventory(data?.items || data || []);
      } catch (e) {
        console.error('Failed to fetch inventory:', e);
      } finally {
        setInventoryLoading(false);
      }
    };
    fetchInventory();
  }, [billShopId]);

  // ─── Fetch Bills History on Filter Change ─────────────────────
  useEffect(() => {
    fetchBills();
  }, [billsPage, histShopFilter, histStatusFilter, histDateFrom, histDateTo]);

  // ─── Fetch Revenue on Filter Change ───────────────────────────
  useEffect(() => {
    fetchRevenue();
  }, [revPeriod, revShopId, revCustomFrom, revCustomTo]);

  // ─── Fetch Today Summary ──────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'history') {
      fetchTodaySummary();
    }
  }, [activeTab]);

  // ─── Item Calculations ────────────────────────────────────────
  const itemCalculations = useMemo(() => {
    return billItems.map((item) => {
      const invItem = inventory.find((inv) => String(inv.id) === String(item.inventory_id));
      const unitPrice = invItem?.selling_price || 0;
      const gstPercent = getGSTPercent(unitPrice);
      const itemTotal = unitPrice * (item.quantity || 0);
      const gstAmount = (itemTotal * gstPercent) / (100 + gstPercent);
      const baseAmount = itemTotal - gstAmount;
      const cgst = gstAmount / 2;
      const sgst = gstAmount / 2;

      return {
        ...item,
        inventory: invItem,
        unitPrice,
        gstPercent,
        itemTotal,
        gstAmount,
        baseAmount,
        cgst,
        sgst,
      };
    });
  }, [billItems, inventory]);

  const billTotals = useMemo(() => {
    const subtotal = itemCalculations.reduce((s, i) => s + i.itemTotal, 0);
    const totalGST = itemCalculations.reduce((s, i) => s + i.gstAmount, 0);
    const totalCGST = totalGST / 2;
    const totalSGST = totalGST / 2;
    const discount = (subtotal * (discountPercent || 0)) / 100;
    const grandTotal = subtotal - discount;

    return { subtotal, totalGST, totalCGST, totalSGST, discount, grandTotal };
  }, [itemCalculations, discountPercent]);

  // ─── Handlers: Bill Items ─────────────────────────────────────
  const addItem = () => {
    setBillItems((prev) => [...prev, createEmptyItem()]);
  };

  const removeItem = (index) => {
    setBillItems((prev) => prev.filter((_, i) => i !== index));
  };

  const updateItem = (index, field, value) => {
    setBillItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // ─── Handlers: Submit Bill ────────────────────────────────────
  const handleSubmitBill = async (e) => {
    e.preventDefault();
    if (!billShopId) {
      setBillError('Please select a shop');
      return;
    }
    const validItems = itemCalculations.filter((i) => i.inventory_id && i.quantity > 0);
    if (validItems.length === 0) {
      setBillError('Add at least one item to the bill');
      return;
    }

    setSubmittingBill(true);
    setBillError('');
    setBillSuccess('');

    try {
      const payload = {
        shop_id: parseInt(billShopId),
        customer_name: customerName || null,
        customer_phone: customerPhone || null,
        doctor_name: doctorName || null,
        discount_percent: parseFloat(discountPercent) || 0,
        payment_method: paymentMethod,
        items: validItems.map((item) => ({
          inventory_id: parseInt(item.inventory_id),
          quantity: parseInt(item.quantity),
          unit_price: item.unitPrice,
          gst_percent: item.gstPercent,
        })),
        subtotal: billTotals.subtotal,
        total_gst: billTotals.totalGST,
        total_cgst: billTotals.totalCGST,
        total_sgst: billTotals.totalSGST,
        discount_amount: billTotals.discount,
        grand_total: billTotals.grandTotal,
      };

      const { data } = await billingAPI.create(payload);
      setBillSuccess('Bill generated successfully!');

      // Reset form
      setCustomerName('');
      setCustomerPhone('');
      setDoctorName('');
      setDiscountPercent(0);
      setPaymentMethod('cash');
      setBillItems([createEmptyItem()]);

      // Switch to receipt tab
      if (data?.id) {
        const billData = await billingAPI.get(data.id);
        setReceiptBill(billData.data || billData);
      }
      setActiveTab('receipt');

      // Refresh history
      fetchBills();
    } catch (err) {
      setBillError(err.response?.data?.detail || 'Failed to generate bill. Please try again.');
    } finally {
      setSubmittingBill(false);
    }
  };

  // ─── Handlers: Fetch Bills ────────────────────────────────────
  const fetchBills = async () => {
    setBillsLoading(true);
    setHistError('');
    try {
      const params = { page: billsPage, size: billsPageSize };
      if (histShopFilter) params.shop_id = histShopFilter;
      if (histStatusFilter) params.status = histStatusFilter;
      if (histDateFrom) params.date_from = histDateFrom;
      if (histDateTo) params.date_to = histDateTo;
      const { data } = await billingAPI.list(params);
      setBills(data?.items || data || []);
      setBillsTotal(data?.total || 0);
    } catch (e) {
      setHistError('Failed to load bills history.');
    } finally {
      setBillsLoading(false);
    }
  };

  // ─── Handlers: Today Summary ──────────────────────────────────
  const fetchTodaySummary = async () => {
    if (shops.length === 0) return;
    try {
      const results = await Promise.allSettled(
        shops.map((s) => billingAPI.todayBills(s.id))
      );
      let totalRevenue = 0;
      let totalBills = 0;
      results.forEach((r) => {
        if (r.status === 'fulfilled' && r.value.data) {
          const d = r.value.data;
          if (Array.isArray(d)) {
            totalRevenue += d.reduce((s, b) => s + (b.grand_total || 0), 0);
            totalBills += d.length;
          } else {
            totalRevenue += d.total_revenue || 0;
            totalBills += d.count || d.total_bills || 0;
          }
        }
      });
      setTodaySummary({
        revenue: totalRevenue,
        bills: totalBills,
        avg: totalBills > 0 ? totalRevenue / totalBills : 0,
      });
    } catch (e) {
      console.error('Failed to fetch today summary:', e);
    }
  };

  // ─── Handlers: Cancel Bill ────────────────────────────────────
  const handleCancelBill = async (id) => {
    if (!window.confirm('Are you sure you want to cancel this bill? This action cannot be undone.')) return;
    setCancellingId(id);
    try {
      await billingAPI.cancel(id);
      fetchBills();
    } catch (e) {
      setHistError('Failed to cancel bill.');
    } finally {
      setCancellingId(null);
    }
  };

  // ─── Handlers: View Bill ──────────────────────────────────────
  const handleViewBill = async (id) => {
    setReceiptLoading(true);
    setActiveTab('receipt');
    try {
      const { data } = await billingAPI.get(id);
      setReceiptBill(data);
    } catch (e) {
      console.error('Failed to fetch bill:', e);
    } finally {
      setReceiptLoading(false);
    }
  };

  // ─── Handlers: Fetch Revenue ──────────────────────────────────
  const fetchRevenue = async () => {
    if (!revShopId && shops.length === 0) return;
    setRevLoading(true);
    setRevError('');
    try {
      const shopId = revShopId || (shops.length === 1 ? shops[0].id : '');
      if (!shopId) {
        setRevData(null);
        setRevLoading(false);
        return;
      }
      const params = { period: revPeriod };
      if (revPeriod === 'custom' && revCustomFrom) params.date_from = revCustomFrom;
      if (revPeriod === 'custom' && revCustomTo) params.date_to = revCustomTo;
      const { data } = await billingAPI.revenue(shopId, params);
      setRevData(data || null);
    } catch (e) {
      setRevError('Failed to load revenue data.');
    } finally {
      setRevLoading(false);
    }
  };

  // ─── Handlers: Print Receipt ──────────────────────────────────
  const handlePrintReceipt = () => {
    if (!receiptBill) return;
    const bill = receiptBill;
    const items = bill.items || [];
    const shop = shops.find((s) => String(s.id) === String(bill.shop_id));
    const printWindow = window.open('', '_blank', 'width=400,height=700');
    if (!printWindow) {
      alert('Please allow popups to print receipt');
      return;
    }
    printWindow.document.write(`<!DOCTYPE html><html><head><title>Receipt #${bill.invoice_number || bill.id}</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Courier New', monospace; font-size: 11px; padding: 10px; max-width: 320px; margin: 0 auto; color: #000; }
      .center { text-align: center; }
      .bold { font-weight: bold; }
      .sep { border-top: 1px dashed #000; margin: 6px 0; }
      .row { display: flex; justify-content: space-between; padding: 2px 0; }
      .items-table { width: 100%; border-collapse: collapse; margin: 6px 0; }
      .items-table th, .items-table td { text-align: left; padding: 1px 0; font-size: 10px; }
      .items-table th { border-bottom: 1px solid #000; }
      .items-table .right { text-align: right; }
      .watermark { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 60px; color: rgba(0,0,0,0.04); font-weight: bold; pointer-events: none; z-index: -1; }
      .footer { margin-top: 8px; }
      @media print { .watermark { display: block; } }
    </style></head><body>
    <div class="watermark">MediSebi</div>
    <div class="center"><div class="bold" style="font-size:14px;">${shop?.name || 'MediSebi Pharmacy'}</div>
    <div style="font-size:10px;">${shop?.address || ''}${shop?.city ? ', ' + shop.city : ''}</div>
    <div style="font-size:10px;">Ph: ${shop?.phone || 'N/A'}</div></div>
    <div class="sep"></div>
    <div class="row"><span>Bill #: ${bill.invoice_number || bill.id}</span><span>${formatDate(bill.created_at || bill.date)}</span></div>
    <div class="row"><span>Cust: ${bill.customer_name || 'Walk-in'}</span><span>${bill.customer_phone || ''}</span></div>
    ${bill.doctor_name ? `<div class="row"><span>Dr: ${bill.doctor_name}</span><span></span></div>` : ''}
    <div class="sep"></div>
    <table class="items-table"><thead><tr><th>#</th><th>Item</th><th class="right">Qty</th><th class="right">Rate</th><th class="right">GST</th><th class="right">Total</th></tr></thead><tbody>
    ${items.map((it, i) => `<tr><td>${i + 1}</td><td>${it.brand_name || it.medicine_name || 'Item'}</td><td class="right">${it.quantity}</td><td class="right">${(it.unit_price || 0).toFixed(2)}</td><td class="right">${it.gst_percent || 0}%</td><td class="right">${(it.total || it.line_total || 0).toFixed(2)}</td></tr>`).join('')}
    </tbody></table>
    <div class="sep"></div>
    <div class="row"><span>Subtotal</span><span>${formatCurrency(bill.subtotal || 0)}</span></div>
    <div class="row"><span>Discount (${bill.discount_percent || 0}%)</span><span>-${formatCurrency(bill.discount_amount || 0)}</span></div>
    <div class="row"><span>CGST (${(bill.total_cgst / bill.subtotal * 200 || 0).toFixed(1)}%)</span><span>${formatCurrency(bill.total_cgst || 0)}</span></div>
    <div class="row"><span>SGST (${(bill.total_sgst / bill.subtotal * 200 || 0).toFixed(1)}%)</span><span>${formatCurrency(bill.total_sgst || 0)}</span></div>
    <div class="sep"></div>
    <div class="row bold" style="font-size:13px;"><span>GRAND TOTAL</span><span>${formatCurrency(bill.grand_total || 0)}</span></div>
    <div class="sep"></div>
    <div class="row"><span>Payment: ${getPaymentLabel(bill.payment_method)}</span><span>${formatCurrency(bill.grand_total || 0)}</span></div>
    <div class="footer center" style="margin-top:12px;"><div style="font-size:9px; color:#666;">Thank you for visiting!</div><div style="font-size:9px; color:#999;">Powered by MediSebi</div></div>
    </body></html>`);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 300);
  };

  // ─── Revenue Chart Data ───────────────────────────────────────
  const paymentPieData = useMemo(() => {
    if (!revData?.payment_breakdown) return [];
    return revData.payment_breakdown.map((p) => ({
      name: getPaymentLabel(p.method || p.payment_method),
      value: p.total || p.amount || 0,
    }));
  }, [revData]);

  const dailyRevenueData = useMemo(() => {
    if (!revData?.daily_revenue) return [];
    return revData.daily_revenue.map((d) => ({
      date: d.date
        ? new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
        : d.label || '',
      revenue: d.total || d.revenue || d.amount || 0,
    }));
  }, [revData]);

  const totalPages = Math.ceil(billsTotal / billsPageSize);

  // ═══════════════════════════════════════════════════════════════
  //  Render
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="space-y-6">
      {/* ─── Page Header ──────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Receipt className="w-6 h-6 text-indigo-400" />
          Billing
        </h1>
        <p className="text-sm text-slate-400 mt-1">Create and manage pharmacy bills, track revenue</p>
      </div>

      {/* ─── Tab Navigation ───────────────────────────────────── */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-1.5 flex gap-1">
        {[
          { key: 'newBill', label: 'New Bill', icon: ShoppingCart },
          { key: 'history', label: 'History', icon: FileText },
          { key: 'revenue', label: 'Revenue', icon: BarChart3 },
          { key: 'receipt', label: 'Receipt', icon: Receipt },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
              activeTab === key
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* ─── Tab: New Bill ────────────────────────────────────── */}
      {activeTab === 'newBill' && (
        <form onSubmit={handleSubmitBill} className="space-y-6">
          {/* Error / Success */}
          {billError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">{billError}</p>
              <button type="button" onClick={() => setBillError('')} className="ml-auto text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
          {billSuccess && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <p className="text-sm text-emerald-400">{billSuccess}</p>
              <button type="button" onClick={() => setBillSuccess('')} className="ml-auto text-emerald-400 hover:text-emerald-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* ─── Left: Form + Items ────────────────────────── */}
            <div className="lg:col-span-2 space-y-6">
              {/* Bill Details Card */}
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  Bill Details
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Shop */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Shop *</label>
                    <div className="relative">
                      <Store className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <select
                        value={billShopId}
                        onChange={(e) => setBillShopId(e.target.value)}
                        required
                        className="w-full pl-9 pr-8 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 appearance-none"
                      >
                        <option value="">Select shop...</option>
                        {shops.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}{s.city ? ` — ${s.city}` : ''}</option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    </div>
                  </div>

                  {/* Payment Method */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Payment Method</label>
                    <div className="grid grid-cols-5 gap-1">
                      {PAYMENT_METHODS.map((pm) => {
                        const PmIcon = pm.icon;
                        return (
                          <button
                            key={pm.value}
                            type="button"
                            onClick={() => setPaymentMethod(pm.value)}
                            className={`flex flex-col items-center gap-1 p-2 rounded-lg border text-xs transition-all ${
                              paymentMethod === pm.value
                                ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400'
                                : 'border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                            }`}
                            title={pm.label}
                          >
                            <PmIcon className="w-4 h-4" />
                            <span className="text-[10px] leading-tight">{pm.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Customer Name */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      <User className="w-3 h-3 inline mr-1" />
                      Customer Name
                    </label>
                    <input
                      type="text"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      placeholder="Walk-in customer"
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    />
                  </div>

                  {/* Customer Phone */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      <Phone className="w-3 h-3 inline mr-1" />
                      Customer Phone
                    </label>
                    <input
                      type="tel"
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    />
                  </div>

                  {/* Doctor Name */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      <Stethoscope className="w-3 h-3 inline mr-1" />
                      Doctor Name
                    </label>
                    <input
                      type="text"
                      value={doctorName}
                      onChange={(e) => setDoctorName(e.target.value)}
                      placeholder="Prescribed by"
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    />
                  </div>

                  {/* Discount */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      <Percent className="w-3 h-3 inline mr-1" />
                      Discount %
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      value={discountPercent}
                      onChange={(e) => setDiscountPercent(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    />
                  </div>
                </div>
              </div>

              {/* Items Card */}
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-800/50 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Package className="w-4 h-4 text-indigo-400" />
                    Bill Items
                  </h3>
                  <button
                    type="button"
                    onClick={addItem}
                    disabled={!billShopId}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/30 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Item
                  </button>
                </div>

                {!billShopId ? (
                  <div className="py-12 text-center">
                    <Store className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Select a shop to load inventory</p>
                  </div>
                ) : inventoryLoading ? (
                  <div className="py-12 text-center">
                    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                    <p className="text-sm text-slate-500 mt-2">Loading inventory...</p>
                  </div>
                ) : inventory.length === 0 ? (
                  <div className="py-12 text-center">
                    <Package className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">No inventory found for this shop</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    {/* Desktop Items Table */}
                    <table className="w-full hidden md:table">
                      <thead>
                        <tr className="bg-slate-800/50">
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider min-w-[250px]">Medicine</th>
                          <th className="text-left px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Batch</th>
                          <th className="text-left px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Expiry</th>
                          <th className="text-right px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Unit Price</th>
                          <th className="text-right px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                          <th className="text-center px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">GST%</th>
                          <th className="text-right px-3 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Total</th>
                          <th className="px-3 py-3 w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {itemCalculations.map((item, idx) => (
                          <BillItemRow
                            key={idx}
                            index={idx}
                            item={item}
                            inventory={inventory}
                            onUpdate={updateItem}
                            onRemove={removeItem}
                            canRemove={billItems.length > 1}
                          />
                        ))}
                      </tbody>
                    </table>

                    {/* Mobile Items Cards */}
                    <div className="md:hidden divide-y divide-slate-800/50">
                      {itemCalculations.map((item, idx) => (
                        <BillItemCard
                          key={idx}
                          index={idx}
                          item={item}
                          inventory={inventory}
                          onUpdate={updateItem}
                          onRemove={removeItem}
                          canRemove={billItems.length > 1}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ─── Right: Bill Summary ────────────────────────── */}
            <div className="lg:col-span-1">
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5 sticky top-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <IndianRupee className="w-4 h-4 text-indigo-400" />
                  Bill Summary
                </h3>

                <div className="space-y-3">
                  <SummaryRow label="Subtotal" value={billTotals.subtotal} />
                  {billTotals.discount > 0 && (
                    <SummaryRow label={`Discount (${discountPercent}%)`} value={-billTotals.discount} className="text-red-400" />
                  )}
                  <div className="border-t border-slate-800/50 pt-2">
                    <SummaryRow label="CGST" value={billTotals.totalCGST} className="text-slate-400" />
                    <SummaryRow label="SGST" value={billTotals.totalSGST} className="text-slate-400" />
                  </div>

                  <div className="border-t border-slate-700/50 pt-3 mt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-base font-bold text-white">Grand Total</span>
                      <span className="text-xl font-bold text-indigo-400">{formatCurrency(billTotals.grandTotal)}</span>
                    </div>
                  </div>

                  <div className="border-t border-slate-700/50 pt-3 mt-3 space-y-2">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <CreditCard className="w-3 h-3" />
                      {getPaymentLabel(paymentMethod)}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Package className="w-3 h-3" />
                      {itemCalculations.filter((i) => i.inventory_id).length} item(s)
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submittingBill || !billShopId || itemCalculations.filter((i) => i.inventory_id).length === 0}
                  className="w-full mt-5 inline-flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/30 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
                >
                  {submittingBill ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Receipt className="w-4 h-4" />
                      Generate Bill
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      )}

      {/* ─── Tab: History ────────────────────────────────────── */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          {histError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">{histError}</p>
              <button onClick={() => setHistError('')} className="ml-auto text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SummaryCard
              title="Today's Revenue"
              value={formatCurrency(todaySummary?.revenue || 0)}
              icon={DollarSign}
              color="emerald"
            />
            <SummaryCard
              title="Today's Bills"
              value={todaySummary?.bills || 0}
              icon={FileText}
              color="indigo"
            />
            <SummaryCard
              title="Avg Bill Amount"
              value={formatCurrency(todaySummary?.avg || 0)}
              icon={TrendingUp}
              color="amber"
            />
          </div>

          {/* Filters */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Filters</span>
            </div>
            <div className="flex flex-wrap gap-3">
              <select
                value={histShopFilter}
                onChange={(e) => { setHistShopFilter(e.target.value); setBillsPage(1); }}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Shops</option>
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <select
                value={histStatusFilter}
                onChange={(e) => { setHistStatusFilter(e.target.value); setBillsPage(1); }}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Status</option>
                <option value="paid">Paid</option>
                <option value="pending">Pending</option>
                <option value="cancelled">Cancelled</option>
                <option value="refunded">Refunded</option>
              </select>
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-500">From</label>
                <input
                  type="date"
                  value={histDateFrom}
                  onChange={(e) => { setHistDateFrom(e.target.value); setBillsPage(1); }}
                  className="px-2 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-500">To</label>
                <input
                  type="date"
                  value={histDateTo}
                  onChange={(e) => { setHistDateTo(e.target.value); setBillsPage(1); }}
                  className="px-2 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              {(histShopFilter || histStatusFilter || histDateFrom || histDateTo) && (
                <button
                  onClick={() => { setHistShopFilter(''); setHistStatusFilter(''); setHistDateFrom(''); setHistDateTo(''); setBillsPage(1); }}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Bills Table */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Invoice #</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Customer</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Items</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Total</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Payment</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Date</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {billsLoading ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : bills.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center text-sm text-slate-500">
                        No bills found
                      </td>
                    </tr>
                  ) : (
                    bills.map((bill) => (
                      <tr key={bill.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3">
                          <span className="text-sm font-medium text-indigo-400 font-mono">
                            #{bill.invoice_number || bill.id}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-sm text-slate-200">{bill.customer_name || 'Walk-in'}</p>
                          <p className="text-xs text-slate-500">{bill.customer_phone || ''}</p>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-sm text-slate-300">{bill.items_count || bill.items?.length || 0}</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-medium text-white">{formatCurrency(bill.grand_total)}</span>
                        </td>
                        <td className="px-4 py-3 text-center">{getStatusBadge(bill.status)}</td>
                        <td className="px-4 py-3 text-sm text-slate-400">
                          {getPaymentLabel(bill.payment_method)}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-400">
                          {formatDateTime(bill.created_at || bill.date)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => handleViewBill(bill.id)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
                              title="View Receipt"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {bill.status !== 'cancelled' && bill.status !== 'refunded' && (
                              <button
                                onClick={() => handleCancelBill(bill.id)}
                                disabled={cancellingId === bill.id}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                                title="Cancel Bill"
                              >
                                {cancellingId === bill.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Ban className="w-4 h-4" />
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <Pagination
                page={billsPage}
                totalPages={totalPages}
                total={billsTotal}
                pageSize={billsPageSize}
                onPageChange={setBillsPage}
              />
            )}
          </div>
        </div>
      )}

      {/* ─── Tab: Revenue ────────────────────────────────────── */}
      {activeTab === 'revenue' && (
        <div className="space-y-6">
          {revError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">{revError}</p>
              <button onClick={() => setRevError('')} className="ml-auto text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Period + Shop Filter */}
          <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Period & Shop</span>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex gap-1">
                {PERIOD_OPTIONS.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setRevPeriod(p.value)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      revPeriod === p.value
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-800/80 text-slate-400 hover:text-white border border-slate-600/50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <select
                value={revShopId}
                onChange={(e) => setRevShopId(e.target.value)}
                className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">All Shops</option>
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              {revPeriod === 'custom' && (
                <>
                  <input
                    type="date"
                    value={revCustomFrom}
                    onChange={(e) => setRevCustomFrom(e.target.value)}
                    className="px-2 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                  <input
                    type="date"
                    value={revCustomTo}
                    onChange={(e) => setRevCustomTo(e.target.value)}
                    className="px-2 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </>
              )}
            </div>
          </div>

          {revLoading ? (
            <div className="py-20 text-center">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
              <p className="text-sm text-slate-500 mt-3">Loading revenue data...</p>
            </div>
          ) : revData ? (
            <>
              {/* Revenue Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                <SummaryCard
                  title="Total Revenue"
                  value={formatCurrency(revData.total_revenue || 0)}
                  icon={DollarSign}
                  color="emerald"
                />
                <SummaryCard
                  title="Total Bills"
                  value={revData.total_bills || 0}
                  icon={FileText}
                  color="indigo"
                />
                <SummaryCard
                  title="Avg Bill Amount"
                  value={formatCurrency(revData.avg_bill_amount || 0)}
                  icon={TrendingUp}
                  color="amber"
                />
                <SummaryCard
                  title="Total GST"
                  value={formatCurrency(revData.total_gst || 0)}
                  icon={Percent}
                  color="purple"
                />
                <SummaryCard
                  title="Total Discount"
                  value={formatCurrency(revData.total_discount || 0)}
                  icon={Tag}
                  color="rose"
                />
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Payment Breakdown Pie */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <PieChartIcon className="w-4 h-4 text-indigo-400" />
                    Payment Method Breakdown
                  </h3>
                  {paymentPieData.length > 0 ? (
                    <div className="flex items-center">
                      <ResponsiveContainer width="60%" height={250}>
                        <PieChart>
                          <Pie
                            data={paymentPieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={90}
                            paddingAngle={3}
                            dataKey="value"
                          >
                            {paymentPieData.map((entry, idx) => (
                              <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip content={<PieTooltip />} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="flex-1 space-y-2">
                        {paymentPieData.map((entry, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                            <span className="text-slate-400 flex-1">{entry.name}</span>
                            <span className="text-white font-medium">{formatCurrency(entry.value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-[250px] text-slate-500 text-sm">
                      No payment breakdown data
                    </div>
                  )}
                </div>

                {/* Daily Revenue Bar Chart */}
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-indigo-400" />
                    Revenue Trend
                  </h3>
                  {dailyRevenueData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={250}>
                      <BarChart data={dailyRevenueData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-30} textAnchor="end" height={50} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="revenue" name="Revenue" fill="#6366F1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-[250px] text-slate-500 text-sm">
                      No daily revenue data for the selected period
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="py-20 text-center">
              <BarChart3 className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">Select a shop to view revenue analytics</p>
            </div>
          )}
        </div>
      )}

      {/* ─── Tab: Receipt ────────────────────────────────────── */}
      {activeTab === 'receipt' && (
        <div className="space-y-6">
          {receiptLoading ? (
            <div className="py-20 text-center">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
              <p className="text-sm text-slate-500 mt-3">Loading receipt...</p>
            </div>
          ) : receiptBill ? (
            <>
              {/* Print Button */}
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-400">
                  Bill #{receiptBill.invoice_number || receiptBill.id}
                </div>
                <button
                  onClick={handlePrintReceipt}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-emerald-600/20"
                >
                  <Printer className="w-4 h-4" />
                  Print Receipt
                </button>
              </div>

              {/* Receipt Card */}
              <div className="max-w-2xl mx-auto bg-slate-900/80 border border-slate-700/50 rounded-xl p-8 relative overflow-hidden print-area">
                {/* Watermark */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -rotate-30 text-7xl font-black text-slate-800/20 pointer-events-none select-none tracking-widest">
                  MediSebi
                </div>

                {/* Pharmacy Header */}
                <div className="text-center mb-6 relative">
                  <h2 className="text-xl font-bold text-white">
                    {(() => {
                      const shop = shops.find((s) => String(s.id) === String(receiptBill.shop_id));
                      return shop?.name || 'MediSebi Pharmacy';
                    })()}
                  </h2>
                  <p className="text-sm text-slate-400 mt-1">
                    {(() => {
                      const shop = shops.find((s) => String(s.id) === String(receiptBill.shop_id));
                      return [shop?.address, shop?.city, shop?.state].filter(Boolean).join(', ');
                    })()}
                  </p>
                  <p className="text-sm text-slate-400">
                    Ph: {(() => {
                      const shop = shops.find((s) => String(s.id) === String(receiptBill.shop_id));
                      return shop?.phone || 'N/A';
                    })()}
                  </p>
                </div>

                {/* Bill Info */}
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-5 p-4 bg-slate-800/40 rounded-lg relative">
                  <div className="flex justify-between col-span-2 border-b border-slate-700/30 pb-2 mb-1">
                    <span className="text-slate-400">Bill #:</span>
                    <span className="text-white font-mono font-medium">{receiptBill.invoice_number || receiptBill.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Date:</span>
                    <span className="text-white">{formatDateTime(receiptBill.created_at || receiptBill.date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer:</span>
                    <span className="text-white">{receiptBill.customer_name || 'Walk-in'}</span>
                  </div>
                  {receiptBill.customer_phone && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Phone:</span>
                      <span className="text-white">{receiptBill.customer_phone}</span>
                    </div>
                  )}
                  {receiptBill.doctor_name && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Doctor:</span>
                      <span className="text-white">{receiptBill.doctor_name}</span>
                    </div>
                  )}
                </div>

                {/* Items Table */}
                <div className="overflow-x-auto mb-5 relative">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-800/60">
                        <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">#</th>
                        <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">Medicine</th>
                        <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">Salt</th>
                        <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">Batch</th>
                        <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400">Qty</th>
                        <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400">Rate</th>
                        <th className="text-center px-3 py-2 text-xs font-semibold text-slate-400">GST%</th>
                        <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400">GST Amt</th>
                        <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                      {(receiptBill.items || []).map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="px-3 py-2 text-slate-400">{idx + 1}</td>
                          <td className="px-3 py-2 text-white font-medium">{item.brand_name || item.medicine_name || '—'}</td>
                          <td className="px-3 py-2 text-slate-400 text-xs">{item.salt_name || '—'}</td>
                          <td className="px-3 py-2 text-slate-400 font-mono text-xs">{item.batch_number || '—'}</td>
                          <td className="px-3 py-2 text-right text-white">{item.quantity}</td>
                          <td className="px-3 py-2 text-right text-slate-300">{formatCurrency(item.unit_price)}</td>
                          <td className="px-3 py-2 text-center text-slate-400">{item.gst_percent || getGSTPercent(item.unit_price)}%</td>
                          <td className="px-3 py-2 text-right text-slate-400">{formatCurrency(item.gst_amount || 0)}</td>
                          <td className="px-3 py-2 text-right text-white font-medium">{formatCurrency(item.total || item.line_total || 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Totals */}
                <div className="space-y-2 text-sm mb-5 relative">
                  <div className="flex justify-between px-2">
                    <span className="text-slate-400">Subtotal</span>
                    <span className="text-white">{formatCurrency(receiptBill.subtotal)}</span>
                  </div>
                  {(receiptBill.discount_amount || 0) > 0 && (
                    <div className="flex justify-between px-2">
                      <span className="text-slate-400">Discount ({receiptBill.discount_percent || 0}%)</span>
                      <span className="text-red-400">- {formatCurrency(receiptBill.discount_amount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between px-2">
                    <span className="text-slate-400">CGST</span>
                    <span className="text-slate-300">{formatCurrency(receiptBill.total_cgst)}</span>
                  </div>
                  <div className="flex justify-between px-2">
                    <span className="text-slate-400">SGST</span>
                    <span className="text-slate-300">{formatCurrency(receiptBill.total_sgst)}</span>
                  </div>
                  <div className="border-t border-slate-700/50 pt-2 mt-2">
                    <div className="flex justify-between px-2">
                      <span className="text-lg font-bold text-white">Grand Total</span>
                      <span className="text-lg font-bold text-indigo-400">{formatCurrency(receiptBill.grand_total)}</span>
                    </div>
                  </div>
                </div>

                {/* Payment Info */}
                <div className="border-t border-slate-700/50 pt-4 text-sm relative">
                  <div className="flex justify-between px-2 mb-4">
                    <span className="text-slate-400">Payment Method</span>
                    <span className="text-white font-medium">{getPaymentLabel(receiptBill.payment_method)}</span>
                  </div>
                  <div className="flex justify-between px-2 mb-6">
                    <span className="text-slate-400">Amount Paid</span>
                    <span className="text-emerald-400 font-bold text-base">{formatCurrency(receiptBill.grand_total)}</span>
                  </div>

                  {/* Footer */}
                  <div className="text-center border-t border-slate-700/30 pt-4">
                    <p className="text-xs text-slate-500">Thank you for your purchase!</p>
                    <p className="text-xs text-slate-600 mt-1">Powered by <span className="text-indigo-500 font-medium">MediSebi</span></p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="py-20 text-center">
              <Receipt className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No receipt to display</p>
              <p className="text-xs text-slate-600 mt-1">Generate a new bill or view one from History</p>
              <button
                onClick={() => setActiveTab('newBill')}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Create New Bill
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
//  Sub-Components
// ═══════════════════════════════════════════════════════════════════════

// ─── Summary Card ────────────────────────────────────────────────────
function SummaryCard({ title, value, icon: Icon, color = 'indigo' }) {
  const colorMap = {
    indigo: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/20', text: 'text-indigo-400', iconBg: 'bg-indigo-500/15' },
    emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', iconBg: 'bg-emerald-500/15' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', iconBg: 'bg-amber-500/15' },
    red: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', iconBg: 'bg-red-500/15' },
    rose: { bg: 'bg-rose-500/10', border: 'border-rose-500/20', text: 'text-rose-400', iconBg: 'bg-rose-500/15' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', iconBg: 'bg-purple-500/15' },
  };
  const c = colorMap[color] || colorMap.indigo;

  return (
    <div className={`${c.bg} ${c.border} border rounded-xl p-5 transition-all duration-200`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-white mt-2">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-lg ${c.iconBg} ${c.text} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

// ─── Summary Row (for bill summary sidebar) ─────────────────────────
function SummaryRow({ label, value, className = 'text-slate-300' }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className={className}>{formatCurrency(value)}</span>
    </div>
  );
}

// ─── Pagination ─────────────────────────────────────────────────────
function Pagination({ page, totalPages, total, pageSize, onPageChange }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/50">
      <p className="text-xs text-slate-500">
        Showing {((page - 1) * pageSize) + 1}&ndash;{Math.min(page * pageSize, total)} of {total}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange((p) => Math.max(1, p - 1))}
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
              onClick={() => onPageChange(pageNum)}
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
          onClick={() => onPageChange((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ─── Bill Item Row (Desktop) ────────────────────────────────────────
function BillItemRow({ index, item, inventory, onUpdate, onRemove, canRemove }) {
  const invItem = item.inventory;
  return (
    <tr className="hover:bg-slate-800/20 transition-colors">
      <td className="px-4 py-2">
        <div className="relative">
          <select
            value={item.inventory_id}
            onChange={(e) => onUpdate(index, 'inventory_id', e.target.value)}
            className="w-full px-3 py-1.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 pr-8 appearance-none"
          >
            <option value="">Select medicine...</option>
            {inventory.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.brand_name || 'Unknown'} {inv.salt_name ? `· ${inv.salt_name}` : ''} {inv.batch_number ? `[${inv.batch_number}]` : ''} · ₹{(inv.selling_price || 0).toFixed(2)} {inv.quantity > 0 ? `(Stock: ${inv.quantity})` : '(Out of stock)'}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
        </div>
        {invItem?.salt_name && (
          <p className="text-[10px] text-slate-500 mt-0.5 truncate max-w-[250px]">{invItem.salt_name}</p>
        )}
      </td>
      <td className="px-3 py-2 text-sm text-slate-400 font-mono">{invItem?.batch_number || '—'}</td>
      <td className="px-3 py-2">
        {invItem?.expiry_date ? (
          <span className={`text-xs font-medium ${
            new Date(invItem.expiry_date) < new Date()
              ? 'text-red-400'
              : new Date(invItem.expiry_date) < new Date(Date.now() + 90 * 86400000)
                ? 'text-amber-400'
                : 'text-slate-400'
          }`}>
            {new Date(invItem.expiry_date).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })}
          </span>
        ) : (
          <span className="text-xs text-slate-500">—</span>
        )}
      </td>
      <td className="px-3 py-2 text-sm text-right text-white font-medium">{formatCurrency(item.unitPrice)}</td>
      <td className="px-3 py-2">
        <input
          type="number"
          min="1"
          max={invItem?.quantity || 999}
          value={item.quantity}
          onChange={(e) => onUpdate(index, 'quantity', Math.max(1, parseInt(e.target.value) || 1))}
          className="w-20 px-2 py-1 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
        />
      </td>
      <td className="px-3 py-2 text-center">
        <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
          item.gstPercent === 5 ? 'bg-emerald-500/10 text-emerald-400' :
          item.gstPercent === 12 ? 'bg-amber-500/10 text-amber-400' :
          'bg-red-500/10 text-red-400'
        }`}>
          {item.gstPercent}%
        </span>
      </td>
      <td className="px-3 py-2 text-sm text-right text-white font-semibold">{formatCurrency(item.itemTotal)}</td>
      <td className="px-3 py-2">
        {canRemove ? (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        ) : null}
      </td>
    </tr>
  );
}

// ─── Bill Item Card (Mobile) ────────────────────────────────────────
function BillItemCard({ index, item, inventory, onUpdate, onRemove, canRemove }) {
  const invItem = item.inventory;
  return (
    <div className="p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1 mr-3">
          <select
            value={item.inventory_id}
            onChange={(e) => onUpdate(index, 'inventory_id', e.target.value)}
            className="w-full px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
          >
            <option value="">Select medicine...</option>
            {inventory.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.brand_name || 'Unknown'} · ₹{(inv.selling_price || 0).toFixed(2)}
              </option>
            ))}
          </select>
          {invItem && (
            <div className="flex gap-3 mt-1 text-xs text-slate-500">
              <span>{invItem.salt_name || ''}</span>
              <span className="font-mono">{invItem.batch_number || ''}</span>
              {invItem.expiry_date && (
                <span>Exp: {new Date(invItem.expiry_date).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })}</span>
              )}
            </div>
          )}
        </div>
        {canRemove && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Qty:</label>
          <input
            type="number"
            min="1"
            max={invItem?.quantity || 999}
            value={item.quantity}
            onChange={(e) => onUpdate(index, 'quantity', Math.max(1, parseInt(e.target.value) || 1))}
            className="w-16 px-2 py-1 bg-slate-800/80 border border-slate-600/50 rounded-lg text-sm text-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          />
        </div>
        <div className="flex-1" />
        <div className="text-right">
          <p className="text-xs text-slate-500">
            {formatCurrency(item.unitPrice)} × {item.quantity}
          </p>
          <p className="text-sm font-semibold text-white">{formatCurrency(item.itemTotal)}</p>
        </div>
      </div>
    </div>
  );
}
