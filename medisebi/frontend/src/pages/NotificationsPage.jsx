import { useState, useEffect, useCallback } from 'react';
import {
  Bell, BellRing, Filter, CheckCircle, XCircle,
  AlertCircle, Info, Loader2, RefreshCw, CheckCheck,
} from 'lucide-react';
import { notificationsAPI } from '../services/api';

// ─── Constants ──────────────────────────────────────
const SEVERITY_CONFIG = {
  critical: {
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-l-red-500',
    badge: 'bg-red-500/15 text-red-400 border border-red-500/30',
    icon: AlertCircle,
    pill: 'bg-red-500/15 text-red-400',
  },
  warning: {
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-l-amber-500',
    badge: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    icon: AlertCircle,
    pill: 'bg-amber-500/15 text-amber-400',
  },
  info: {
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-l-blue-500',
    badge: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
    icon: Info,
    pill: 'bg-blue-500/15 text-blue-400',
  },
};

const SEVERITY_FILTERS = [
  { key: 'all', label: 'All', color: 'bg-slate-700 text-slate-300' },
  { key: 'critical', label: 'Critical', color: 'bg-red-500/15 text-red-400 border border-red-500/30' },
  { key: 'warning', label: 'Warning', color: 'bg-amber-500/15 text-amber-400 border border-amber-500/30' },
  { key: 'info', label: 'Info', color: 'bg-blue-500/15 text-blue-400 border border-blue-500/30' },
];

// ─── Helpers ────────────────────────────────────────
function getRelativeTime(timestamp) {
  if (!timestamp) return '';
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const SOURCE_ICONS = {
  'expiry watchdog': '⏰',
  'climate engine': '🌡️',
  'redistribution': '🔄',
  'inventory': '📦',
  'system': '⚙️',
  'forecast': '📊',
};

// ─── Sample Notifications (fallback) ──────────────
const SAMPLE_NOTIFICATIONS = [
  {
    id: 1,
    title: 'Critical: Expiry Alert',
    message: 'Paracetamol 500mg tablets in Main Pharmacy are expiring within 7 days. 45 units need immediate attention or redistribution.',
    severity: 'critical',
    source: 'Expiry Watchdog',
    timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    read: false,
    action_url: '/inventory?expiring=7',
  },
  {
    id: 2,
    title: 'Low Stock Warning',
    message: 'Amoxicillin 250mg Capsules stock has fallen below the reorder level at Downtown Branch. Current stock: 12 units, Reorder level: 50 units.',
    severity: 'warning',
    source: 'Inventory',
    timestamp: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    read: false,
    action_url: '/inventory?shop=3&low_stock=true',
  },
  {
    id: 3,
    title: 'Climate Alert: High Temperature',
    message: 'Temperature excursion detected at Storage Facility B. Insulin products may be affected. Current reading: 28.5°C (threshold: 25°C).',
    severity: 'critical',
    source: 'Climate Engine',
    timestamp: new Date(Date.now() - 1.5 * 3600 * 1000).toISOString(),
    read: false,
    action_url: null,
  },
  {
    id: 4,
    title: 'Transfer Opportunity',
    message: 'Downtown Branch has 120 units of Omeprazole 20mg approaching expiry. Eastside Pharmacy has demand for this item. Consider redistribution.',
    severity: 'info',
    source: 'Redistribution',
    timestamp: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
    read: true,
    action_url: '/transfers',
  },
  {
    id: 5,
    title: 'Demand Forecast Update',
    message: 'Weekly demand forecast generated. 15 items show significant demand increase for the next 7 days across all locations.',
    severity: 'info',
    source: 'Forecast',
    timestamp: new Date(Date.now() - 8 * 3600 * 1000).toISOString(),
    read: true,
    action_url: '/forecast',
  },
  {
    id: 6,
    title: 'Batch Expiry Notice',
    message: 'Cetirizine 10mg batch BTH20240315 has expired. 28 units need to be removed from shelves at Central Pharmacy.',
    severity: 'critical',
    source: 'Expiry Watchdog',
    timestamp: new Date(Date.now() - 1 * 24 * 3600 * 1000).toISOString(),
    read: true,
    action_url: '/inventory?batch=BTH20240315',
  },
];

// ─── Main Component ────────────────────────────────
export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [endpointAvailable, setEndpointAvailable] = useState(true);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await notificationsAPI.list();
      const data = response?.data;
      if (Array.isArray(data) && data.length > 0) {
        setNotifications(data);
        setEndpointAvailable(true);
      } else if (data?.items && Array.isArray(data.items) && data.items.length > 0) {
        setNotifications(data.items);
        setEndpointAvailable(true);
      } else {
        // Endpoint exists but returned empty — use sample data for demo
        setNotifications(SAMPLE_NOTIFICATIONS);
        setEndpointAvailable(false);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        // Endpoint not found — show sample data
        setNotifications(SAMPLE_NOTIFICATIONS);
        setEndpointAvailable(false);
      } else {
        setError(err.response?.data?.detail || 'Failed to load notifications');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const filteredNotifications = severityFilter === 'all'
    ? notifications
    : notifications.filter((n) => n.severity === severityFilter);

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleMarkRead = (id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Bell className="w-6 h-6 text-indigo-400" />
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 rounded-full bg-red-500 text-white text-[10px] font-bold">
                {unreadCount}
              </span>
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Notifications</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              {unreadCount > 0
                ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}`
                : 'All caught up!'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchNotifications}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-slate-400 hover:text-white bg-slate-900/80 border border-slate-700/50 rounded-lg hover:border-slate-600 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-300 hover:text-indigo-200 bg-indigo-500/10 border border-indigo-500/20 rounded-lg hover:bg-indigo-500/15 transition-colors"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Endpoint Warning */}
      {!endpointAvailable && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <p className="text-xs text-amber-400">
            <Info className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
            Notifications endpoint not available yet. Showing sample data for preview.
          </p>
        </div>
      )}

      {/* Severity Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-4 h-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-400 mr-1">Filter:</span>
        {SEVERITY_FILTERS.map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => setSeverityFilter(key)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              severityFilter === key
                ? color
                : 'bg-slate-800/50 text-slate-500 border border-slate-700 hover:border-slate-600 hover:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={fetchNotifications}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-white bg-slate-800 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </button>
        </div>
      )}

      {/* Notification List */}
      {!loading && !error && filteredNotifications.length > 0 && (
        <div className="space-y-2">
          {filteredNotifications.map((notification) => (
            <NotificationCard
              key={notification.id}
              notification={notification}
              onMarkRead={handleMarkRead}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredNotifications.length === 0 && notifications.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-12 text-center">
          <Filter className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">No notifications match the selected filter</p>
          <button
            onClick={() => setSeverityFilter('all')}
            className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Truly Empty State */}
      {!loading && !error && notifications.length === 0 && (
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-16 text-center">
          <div className="relative mx-auto w-16 h-16 mb-4">
            <Bell className="w-16 h-16 text-slate-700" />
            <BellRing className="w-5 h-5 text-indigo-500 absolute top-0 right-0" />
          </div>
          <h3 className="text-base font-medium text-slate-300 mb-1">No notifications</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            You're all caught up! Notifications from Expiry Watchdog, Climate Engine, and other services will appear here.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Notification Card ─────────────────────────────
function NotificationCard({ notification, onMarkRead }) {
  const {
    title,
    message,
    severity = 'info',
    source,
    timestamp,
    read,
    action_url,
  } = notification;

  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
  const SeverityIcon = config.icon;

  const sourceKey = (source || '').toLowerCase();
  const sourceEmoji = SOURCE_ICONS[sourceKey] || '📢';

  return (
    <div
      onClick={() => !read && onMarkRead(notification.id)}
      className={`group relative bg-slate-900/80 border rounded-xl p-4 transition-all duration-200 cursor-pointer ${
        read
          ? 'border-slate-700/50 hover:border-slate-600/50'
          : `border-slate-700/50 border-l-[3px] ${config.border} hover:bg-slate-900`
      }`}
    >
      {/* Unread dot */}
      {!read && (
        <div className="absolute top-4 right-4">
          <div className="w-2 h-2 rounded-full bg-indigo-500" />
        </div>
      )}

      <div className="flex items-start gap-3">
        {/* Severity icon */}
        <div className={`flex-shrink-0 w-9 h-9 rounded-lg ${config.bg} flex items-center justify-center mt-0.5`}>
          <SeverityIcon className={`w-4.5 h-4.5 ${config.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title row */}
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className={`text-sm ${read ? 'font-medium text-slate-300' : 'font-semibold text-white'}`}>
              {title}
            </h4>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${config.badge}`}>
              {severity.charAt(0).toUpperCase() + severity.slice(1)}
            </span>
          </div>

          {/* Message */}
          <p className={`text-sm mt-1.5 leading-relaxed ${read ? 'text-slate-500' : 'text-slate-400'}`}>
            {message?.length > 200 ? `${message.slice(0, 200)}...` : message || ''}
          </p>

          {/* Footer: source + timestamp + action */}
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
              <span>{sourceEmoji}</span>
              {source || 'System'}
            </span>
            <span className="text-xs text-slate-600">·</span>
            <span className="text-xs text-slate-500">{getRelativeTime(timestamp)}</span>
            {action_url && (
              <>
                <span className="text-xs text-slate-600">·</span>
                <a
                  href={action_url}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  View details →
                </a>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
