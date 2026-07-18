import { useState } from 'react';
import {
  Activity,
  Server,
  Database,
  Shield,
  Bell,
  Clock,
  CheckCircle2,
  AlertCircle,
  XCircle,
  RefreshCw,
  Zap,


  FileText,
  HardDrive,
  Wifi,
  Cpu,
  Gauge,



  Settings,

} from 'lucide-react';

export function OperationalExcellence() {
  const [activeTab, setActiveTab] = useState<'health' | 'audit' | 'monitoring' | 'notifications'>('health');

  // System Health
  const systemHealth = {
    overall: 98,
    uptime: 99.9,
    responseTime: 145,
    requestsPerMinute: 1250,
  };

  // Service Status
  const services = [
    { name: 'Frontend', status: 'healthy', latency: 45, uptime: 99.9 },
    { name: 'API Gateway', status: 'healthy', latency: 32, uptime: 99.95 },
    { name: 'Database', status: 'healthy', latency: 12, uptime: 99.99 },
    { name: 'Redis Cache', status: 'healthy', latency: 2, uptime: 99.99 },
    { name: 'AI Engine', status: 'healthy', latency: 85, uptime: 99.5 },
    { name: 'Trading Engine', status: 'healthy', latency: 15, uptime: 99.99 },
    { name: 'Notification Service', status: 'healthy', latency: 25, uptime: 99.8 },
  ];

  // Audit Trail
  const auditTrail = [
    { action: 'USER_LOGIN', user: 'trader@example.com', timestamp: '2026-07-17 14:32:15', details: 'Successful login' },
    { action: 'BROKER_CONNECT', user: 'trader@example.com', timestamp: '2026-07-17 14:33:42', details: 'Connected to Deriv Demo' },
    { action: 'TRADE_EXECUTE', user: 'trader@example.com', timestamp: '2026-07-17 14:35:18', details: 'Bought V-75 UP @ 1845.32' },
    { action: 'SETTINGS_UPDATE', user: 'trader@example.com', timestamp: '2026-07-17 14:38:55', details: 'Changed risk limit to $500' },
    { action: 'STRATEGY_CREATE', user: 'admin@example.com', timestamp: '2026-07-17 13:22:10', details: 'Created new strategy: Grid Pro' },
    { action: 'SUBSCRIPTION_UPGRADE', user: 'user@example.com', timestamp: '2026-07-17 12:45:33', details: 'Upgraded to Professional plan' },
  ];

  // Background Jobs
  const backgroundJobs = [
    { name: 'AI Model Training', status: 'running', progress: 67, nextRun: 'In 2 hours' },
    { name: 'Daily Report Generation', status: 'completed', progress: 100, nextRun: 'Tomorrow 00:00' },
    { name: 'Data Backup', status: 'scheduled', progress: 0, nextRun: 'In 30 minutes' },
    { name: 'Analytics Sync', status: 'running', progress: 45, nextRun: 'Continuous' },
    { name: 'Model Retraining', status: 'scheduled', progress: 0, nextRun: 'Weekly' },
  ];

  // Notifications
  const notifications = [
    { id: 1, type: 'info', title: 'System Update', message: 'AI models updated to version 2.3.1', time: '5 min ago', read: false },
    { id: 2, type: 'success', title: 'Backup Complete', message: 'Daily backup completed successfully', time: '1 hour ago', read: true },
    { id: 3, type: 'warning', title: 'High Latency', message: 'API response time above threshold', time: '2 hours ago', read: true },
    { id: 4, type: 'info', title: 'New Feature', message: 'Replay Intelligence now available', time: '1 day ago', read: true },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-amber-400" />;
      case 'error':
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'running':
        return <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Operational Excellence</h1>
            <p className="text-slate-400">Monitor system health, audit trail, and operational metrics</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors">
              <Settings className="w-4 h-4" />
              Configure
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* System Health Banner */}
        <div className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 rounded-xl border border-emerald-500/30 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center">
                  <Gauge className="w-8 h-8 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-400">System Health</p>
                  <p className="text-3xl font-bold text-white">{systemHealth.overall}%</p>
                </div>
              </div>
              <div className="h-12 w-px bg-slate-700" />
              <div className="grid grid-cols-3 gap-8">
                <div>
                  <p className="text-sm text-slate-500">Uptime (30 days)</p>
                  <p className="text-xl font-bold text-emerald-400">{systemHealth.uptime}%</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Avg Response</p>
                  <p className="text-xl font-bold text-white">{systemHealth.responseTime}ms</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Requests/min</p>
                  <p className="text-xl font-bold text-white">{systemHealth.requestsPerMinute.toLocaleString()}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
              All Systems Operational
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-800 pb-4">
          {[
            { id: 'health', label: 'Service Health', icon: Server },
            { id: 'audit', label: 'Audit Trail', icon: FileText },
            { id: 'monitoring', label: 'Background Jobs', icon: Activity },
            { id: 'notifications', label: 'Notifications', icon: Bell },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'health' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Service Status */}
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
                <h3 className="text-lg font-semibold text-white mb-4">Service Status</h3>
                <div className="space-y-3">
                  {services.map((service, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(service.status)}
                        <div>
                          <p className="font-medium text-white">{service.name}</p>
                          <p className="text-xs text-slate-500">Latency: {service.latency}ms</p>
                        </div>
                      </div>
                      <span className="text-sm text-slate-400">{service.uptime}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Infrastructure Metrics */}
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
                <h3 className="text-lg font-semibold text-white mb-4">Infrastructure</h3>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                      <Cpu className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">45%</p>
                      <p className="text-xs text-slate-500">CPU Usage</p>
                    </div>
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                      <HardDrive className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">68%</p>
                      <p className="text-xs text-slate-500">Memory</p>
                    </div>
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                      <Wifi className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">12MB/s</p>
                      <p className="text-xs text-slate-500">Network I/O</p>
                    </div>
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                      <Database className="w-6 h-6 text-amber-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">2.4GB</p>
                      <p className="text-xs text-slate-500">Storage</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Database & API Metrics */}
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-blue-400" />
                  <h3 className="text-lg font-semibold text-white">Database</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Connections</span>
                    <span className="text-white">24 / 100</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Queries/sec</span>
                    <span className="text-white">1,245</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Replication Lag</span>
                    <span className="text-emerald-400">0ms</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="w-5 h-5 text-amber-400" />
                  <h3 className="text-lg font-semibold text-white">API</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Requests</span>
                    <span className="text-white">12.5M / day</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Error Rate</span>
                    <span className="text-emerald-400">0.01%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">P99 Latency</span>
                    <span className="text-white">230ms</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-lg font-semibold text-white">Security</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Failed Logins</span>
                    <span className="text-white">3 / day</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">SSL Valid</span>
                    <span className="text-emerald-400">Yes</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Encryption</span>
                    <span className="text-emerald-400">AES-256</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'audit' && (
          <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div className="p-5 border-b border-slate-800">
              <h3 className="text-lg font-semibold text-white">Audit Trail</h3>
              <p className="text-sm text-slate-400 mt-1">Complete record of all system actions and user activities</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-800/50">
                  <tr className="text-slate-400 text-left">
                    <th className="px-5 py-3 font-medium">Action</th>
                    <th className="px-5 py-3 font-medium">User</th>
                    <th className="px-5 py-3 font-medium">Timestamp</th>
                    <th className="px-5 py-3 font-medium">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditTrail.map((entry, i) => (
                    <tr key={i} className="border-t border-slate-800 hover:bg-slate-800/50">
                      <td className="px-5 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          entry.action.includes('LOGIN') ? 'bg-blue-500/20 text-blue-400' :
                          entry.action.includes('TRADE') ? 'bg-emerald-500/20 text-emerald-400' :
                          entry.action.includes('SETTINGS') ? 'bg-amber-500/20 text-amber-400' :
                          entry.action.includes('SUBSCRIPTION') ? 'bg-purple-500/20 text-purple-400' :
                          'bg-slate-700 text-slate-400'
                        }`}>
                          {entry.action}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-300">{entry.user}</td>
                      <td className="px-5 py-4 text-slate-500">{entry.timestamp}</td>
                      <td className="px-5 py-4 text-slate-400">{entry.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'monitoring' && (
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <h3 className="text-lg font-semibold text-white mb-4">Background Jobs</h3>
            <div className="space-y-4">
              {backgroundJobs.map((job, i) => (
                <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <div>
                        <p className="font-medium text-white">{job.name}</p>
                        <p className="text-xs text-slate-500">Next run: {job.nextRun}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${
                      job.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                      job.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                      'bg-slate-700 text-slate-400'
                    }`}>
                      {job.status}
                    </span>
                  </div>
                  {job.status === 'running' && (
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Notifications</h3>
              <button className="text-sm text-blue-400 hover:text-blue-300">Mark all read</button>
            </div>
            <div className="divide-y divide-slate-800">
              {notifications.map((notif, i) => (
                <div key={i} className={`p-4 flex items-start gap-4 ${!notif.read ? 'bg-blue-500/5' : ''}`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    notif.type === 'success' ? 'bg-emerald-500/20' :
                    notif.type === 'warning' ? 'bg-amber-500/20' :
                    'bg-blue-500/20'
                  }`}>
                    {notif.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> :
                     notif.type === 'warning' ? <AlertCircle className="w-5 h-5 text-amber-400" /> :
                     <Bell className="w-5 h-5 text-blue-400" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-white">{notif.title}</p>
                      <span className="text-xs text-slate-500">{notif.time}</span>
                    </div>
                    <p className="text-sm text-slate-400">{notif.message}</p>
                  </div>
                  {!notif.read && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
