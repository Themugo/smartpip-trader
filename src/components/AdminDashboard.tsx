import { useState } from 'react';
import { 
  Users, 
  CreditCard, 
  Activity, 
  TrendingUp,

  Settings,
  Search,
  Filter,
  ChevronDown,
  UserPlus,
  Shield,
  BarChart3,
  DollarSign
} from 'lucide-react';

// Mock data types
interface User {
  id: string;
  email: string;
  name: string;
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  status: 'active' | 'suspended' | 'trial';
  joinedAt: string;
  lastActive: string;
  trades: number;
  revenue: number;
}

interface AdminDashboardProps {
  isAdmin?: boolean;
}

export function AdminDashboard({ isAdmin = false }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'subscriptions' | 'activity'>('overview');
  const [searchQuery, setSearchQuery] = useState('');

  // Mock data
  const stats = {
    totalUsers: 1247,
    activeUsers: 892,
    monthlyRevenue: 45890,
    conversionRate: 3.2,
    growth: 12.5,
  };

  const recentUsers: User[] = [
    { id: '1', email: 'james.trader@example.com', name: 'James Mwangi', plan: 'professional', status: 'active', joinedAt: '2024-01-15', lastActive: '2 hours ago', trades: 456, revenue: 588 },
    { id: '2', email: 'sarah.k@example.com', name: 'Sarah Kimani', plan: 'starter', status: 'active', joinedAt: '2024-02-20', lastActive: '5 hours ago', trades: 123, revenue: 228 },
    { id: '3', email: 'alex.o@example.com', name: 'Alex Ochieng', plan: 'free', status: 'trial', joinedAt: '2024-03-01', lastActive: '1 day ago', trades: 12, revenue: 0 },
    { id: '4', email: 'mike.a@example.com', name: 'Mike Adeyemi', plan: 'enterprise', status: 'active', joinedAt: '2023-11-05', lastActive: '30 mins ago', trades: 2341, revenue: 2388 },
  ];

  const planDistribution = [
    { plan: 'Free', count: 687, percentage: 55 },
    { plan: 'Starter', count: 312, percentage: 25 },
    { plan: 'Professional', count: 198, percentage: 16 },
    { plan: 'Enterprise', count: 50, percentage: 4 },
  ];

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-slate-400">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-white">Admin Dashboard</h1>
            <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full">Beta</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search users..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
              />
            </div>
            <button className="p-2 bg-slate-800 rounded-lg text-slate-400 hover:text-white">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-slate-800 px-6">
        <nav className="flex gap-6">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'users', label: 'Users', icon: Users },
            { id: 'subscriptions', label: 'Subscriptions', icon: CreditCard },
            { id: 'activity', label: 'Activity', icon: Activity },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-4 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: 'Total Users', value: stats.totalUsers.toLocaleString(), icon: Users, color: 'blue', change: '+12%' },
                { label: 'Active Users', value: stats.activeUsers.toLocaleString(), icon: Activity, color: 'emerald', change: '+8%' },
                { label: 'Monthly Revenue', value: `$${stats.monthlyRevenue.toLocaleString()}`, icon: DollarSign, color: 'amber', change: '+15%' },
                { label: 'Conversion Rate', value: `${stats.conversionRate}%`, icon: TrendingUp, color: 'purple', change: '+0.5%' },
              ].map((stat, i) => (
                <div key={i} className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center bg-${stat.color}-500/20`}>
                      <stat.icon className={`w-6 h-6 text-${stat.color}-400`} />
                    </div>
                    <span className="text-xs text-emerald-400 font-medium">{stat.change}</span>
                  </div>
                  <p className="text-2xl font-bold text-white mb-1">{stat.value}</p>
                  <p className="text-sm text-slate-400">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Plan Distribution */}
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-6">Plan Distribution</h3>
                <div className="space-y-4">
                  {planDistribution.map((item, i) => (
                    <div key={i}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-300">{item.plan}</span>
                        <span className="text-sm text-slate-400">{item.count} users</span>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Alerts */}
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-6">Recent Alerts</h3>
                <div className="space-y-4">
                  {[
                    { type: 'warning', message: '3 users approaching usage limits', time: '5 min ago' },
                    { type: 'success', message: 'New enterprise signup: Mike Adeyemi', time: '1 hour ago' },
                    { type: 'error', message: 'API rate limit reached for user #456', time: '2 hours ago' },
                    { type: 'info', message: 'Scheduled maintenance in 24 hours', time: '3 hours ago' },
                  ].map((alert, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        alert.type === 'warning' ? 'bg-amber-400' :
                        alert.type === 'success' ? 'bg-emerald-400' :
                        alert.type === 'error' ? 'bg-red-400' : 'bg-blue-400'
                      }`} />
                      <div className="flex-1">
                        <p className="text-sm text-white">{alert.message}</p>
                        <p className="text-xs text-slate-500">{alert.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="space-y-6">
            {/* Actions Bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors">
                  <UserPlus className="w-4 h-4" />
                  Add User
                </button>
                <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium text-sm transition-colors">
                  <Filter className="w-4 h-4" />
                  Filters
                </button>
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-800/50">
                  <tr>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">User</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">Plan</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">Status</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">Trades</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">Revenue</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-slate-400 uppercase">Last Active</th>
                    <th className="text-right px-6 py-4 text-xs font-medium text-slate-400 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {recentUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-800/50">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-medium">
                            {user.name.charAt(0)}
                          </div>
                          <div>
                            <p className="font-medium text-white">{user.name}</p>
                            <p className="text-sm text-slate-400">{user.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.plan === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                          user.plan === 'professional' ? 'bg-purple-500/20 text-purple-400' :
                          user.plan === 'starter' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-slate-700 text-slate-400'
                        }`}>
                          {user.plan.charAt(0).toUpperCase() + user.plan.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' :
                          user.status === 'trial' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {user.status.charAt(0).toUpperCase() + user.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-300">{user.trades.toLocaleString()}</td>
                      <td className="px-6 py-4 text-slate-300">${user.revenue}</td>
                      <td className="px-6 py-4 text-slate-400">{user.lastActive}</td>
                      <td className="px-6 py-4">
                        <button className="text-slate-400 hover:text-white">
                          <ChevronDown className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'subscriptions' && (
          <div className="text-center py-12">
            <CreditCard className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Subscription Management</h3>
            <p className="text-slate-400">Manage billing, invoices, and subscription changes.</p>
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="text-center py-12">
            <Activity className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Activity Log</h3>
            <p className="text-slate-400">View system activity and audit logs.</p>
          </div>
        )}
      </div>
    </div>
  );
}
