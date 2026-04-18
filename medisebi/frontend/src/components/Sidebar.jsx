import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Pill,
  ArrowLeftRight,
  Store,
  LogOut,
  Activity,
  Clock,
  CloudSun,
  TrendingUp,
  ShoppingBag,
  BookOpen,
  Bell,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const coreItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/inventory', label: 'Inventory', icon: Package },
  { path: '/medicines', label: 'Medicines', icon: Pill },
  { path: '/substitution', label: 'Substitution', icon: ArrowLeftRight },
  { path: '/shops', label: 'Shops', icon: Store },
];

const intelligenceItems = [
  { path: '/expiry', label: 'Expiry Watchdog', icon: Clock },
  { path: '/climate', label: 'Climate Intel', icon: CloudSun },
  { path: '/forecast', label: 'Demand Forecast', icon: TrendingUp },
  { path: '/transfers', label: 'Redistribution', icon: ArrowLeftRight },
  { path: '/marketplace', label: 'Marketplace', icon: ShoppingBag },
];

const toolItems = [
  { path: '/catalog', label: 'Medicine Catalog', icon: BookOpen },
];

function NavGroup({ items, location }) {
  return items.map(({ path, label, icon: Icon }) => {
    const isActive =
      path === '/'
        ? location.pathname === '/'
        : location.pathname.startsWith(path);
    return (
      <Link
        key={path}
        to={path}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
          isActive
            ? 'bg-indigo-600/15 text-indigo-400'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70'
        }`}
      >
        <Icon className="w-[18px] h-[18px]" />
        {label}
      </Link>
    );
  });
}

function SectionDivider({ label }) {
  return (
    <div className="pt-4 pb-1 px-3">
      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
        {label}
      </span>
    </div>
  );
}

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-slate-900 border-r border-slate-700/50 flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-700/50">
        <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">MediSebi</h1>
          <p className="text-[10px] text-slate-400 uppercase tracking-widest">Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {/* Core Section */}
        <NavGroup items={coreItems} location={location} />

        {/* Intelligence Section */}
        <SectionDivider label="Intelligence" />
        <NavGroup items={intelligenceItems} location={location} />

        {/* Tools Section */}
        <SectionDivider label="Tools" />
        <NavGroup items={toolItems} location={location} />
      </nav>

      {/* User info + logout */}
      <div className="px-3 py-4 border-t border-slate-700/50">
        <div className="flex items-center gap-3 px-3 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-indigo-600/20 flex items-center justify-center">
            <span className="text-xs font-semibold text-indigo-400">
              {user?.full_name?.charAt(0) || 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">
              {user?.full_name || 'User'}
            </p>
            <p className="text-[11px] text-slate-500 truncate">{user?.email || ''}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-150"
        >
          <LogOut className="w-[18px] h-[18px]" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
