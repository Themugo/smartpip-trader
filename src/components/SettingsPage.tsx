import { useState } from 'react';
import { 
  User, 
  Bell, 
  Shield, 
  Palette, 
  Key, 
  LogOut,
  ChevronRight,
  Moon,
  Sun,
  Monitor,
  Globe,
  Lock,
  Eye,
  Save
} from 'lucide-react';
import { BrokerConnections } from './BrokerConnections';
import { SubscriptionPlans } from './SubscriptionPlans';

interface SettingsPageProps {
  onClose?: () => void;
}

type SettingsTab = 'profile' | 'broker' | 'notifications' | 'appearance' | 'security' | 'subscription';

export function SettingsPage({ onClose }: SettingsPageProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('dark');
  const [notifications, setNotifications] = useState({
    email: true,
    desktop: true,
    trades: true,
    alerts: true,
    reports: false,
  });

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'broker', label: 'Broker Connections', icon: Key },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'subscription', label: 'Subscription', icon: Globe },
  ];

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 p-4">
        <h2 className="text-lg font-semibold text-white mb-6">Settings</h2>
        <nav className="space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-800">
          <button className="w-full flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-slate-800 rounded-lg transition-colors">
            <LogOut className="w-5 h-5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-8">
        {activeTab === 'profile' && (
          <div className="max-w-2xl">
            <h1 className="text-2xl font-bold text-white mb-6">Profile Settings</h1>
            
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 mb-6">
              <div className="flex items-center gap-6 mb-6">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-3xl font-bold text-white">
                  U
                </div>
                <div>
                  <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-medium transition-colors">
                    Change Avatar
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Display Name</label>
                  <input
                    type="text"
                    defaultValue="Trader"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                  <input
                    type="email"
                    defaultValue="trader@example.com"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Timezone</label>
                  <select className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option>Africa/Nairobi (GMT+3)</option>
                    <option>UTC</option>
                    <option>America/New_York (GMT-5)</option>
                    <option>Europe/London (GMT+0)</option>
                  </select>
                </div>
              </div>
            </div>

            <button className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
              <Save className="w-4 h-4" />
              Save Changes
            </button>
          </div>
        )}

        {activeTab === 'broker' && (
          <div className="max-w-3xl">
            <h1 className="text-2xl font-bold text-white mb-6">Broker Connections</h1>
            <BrokerConnections />
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="max-w-2xl">
            <h1 className="text-2xl font-bold text-white mb-6">Notification Preferences</h1>
            
            <div className="space-y-4">
              {[
                { key: 'email', label: 'Email Notifications', desc: 'Receive updates via email' },
                { key: 'desktop', label: 'Desktop Notifications', desc: 'Show browser notifications' },
                { key: 'trades', label: 'Trade Alerts', desc: 'Notifications for trade events' },
                { key: 'alerts', label: 'System Alerts', desc: 'Critical system notifications' },
                { key: 'reports', label: 'Weekly Reports', desc: 'Receive weekly performance reports' },
              ].map((item) => (
                <div key={item.key} className="bg-slate-900 rounded-xl border border-slate-800 p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">{item.label}</p>
                    <p className="text-sm text-slate-400">{item.desc}</p>
                  </div>
                  <button
                    onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key as keyof typeof prev] }))}
                    className={`relative w-12 h-7 rounded-full transition-colors ${
                      notifications[item.key as keyof typeof notifications] ? 'bg-blue-600' : 'bg-slate-700'
                    }`}
                  >
                    <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                      notifications[item.key as keyof typeof notifications] ? 'left-6' : 'left-1'
                    }`} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'appearance' && (
          <div className="max-w-2xl">
            <h1 className="text-2xl font-bold text-white mb-6">Appearance</h1>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">Theme</label>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { id: 'light', label: 'Light', icon: Sun },
                    { id: 'dark', label: 'Dark', icon: Moon },
                    { id: 'system', label: 'System', icon: Monitor },
                  ].map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setTheme(item.id as any)}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        theme === item.id
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <item.icon className={`w-6 h-6 mx-auto mb-2 ${
                        theme === item.id ? 'text-blue-400' : 'text-slate-400'
                      }`} />
                      <p className={`text-sm font-medium ${
                        theme === item.id ? 'text-white' : 'text-slate-400'
                      }`}>{item.label}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">Accent Color</label>
                <div className="flex gap-3">
                  {['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444'].map((color) => (
                    <button
                      key={color}
                      className="w-10 h-10 rounded-full border-2 border-transparent hover:scale-110 transition-transform"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">Compact Mode</label>
                <button
                  className={`relative w-12 h-7 rounded-full transition-colors ${
                    false ? 'bg-blue-600' : 'bg-slate-700'
                  }`}
                >
                  <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                    false ? 'left-6' : 'left-1'
                  }`} />
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="max-w-2xl">
            <h1 className="text-2xl font-bold text-white mb-6">Security</h1>
            
            <div className="space-y-4">
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Lock className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-white">Password</p>
                      <p className="text-sm text-slate-400">Last changed 30 days ago</p>
                    </div>
                  </div>
                  <button className="text-blue-400 hover:text-blue-300 text-sm font-medium">
                    Change Password
                  </button>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Shield className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-white">Two-Factor Authentication</p>
                      <p className="text-sm text-slate-400">Add an extra layer of security</p>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-medium">
                    Enable
                  </button>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Eye className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-white">Active Sessions</p>
                      <p className="text-sm text-slate-400">2 devices currently active</p>
                    </div>
                  </div>
                  <button className="text-red-400 hover:text-red-300 text-sm font-medium">
                    View All
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'subscription' && (
          <div className="max-w-full">
            <h1 className="text-2xl font-bold text-white mb-6">Subscription & Billing</h1>
            <SubscriptionPlans />
          </div>
        )}
      </div>
    </div>
  );
}
