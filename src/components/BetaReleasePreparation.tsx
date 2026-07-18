import { useState } from 'react';
import {
  Rocket,
  Book,
  PlayCircle,
  MessageSquare,
  Bug,
  Lightbulb,
  FileText,
  ExternalLink,
  CheckCircle2,
  Circle,



  Shield,


} from 'lucide-react';

export function BetaReleasePreparation() {
  const [feedback, setFeedback] = useState('');

  // Release Checklist
  const checklist = {
    documentation: [
      { id: 1, text: 'User handbook created', completed: true },
      { id: 2, text: 'Administrator handbook created', completed: true },
      { id: 3, text: 'API documentation complete', completed: false },
      { id: 4, text: 'Quick start guide ready', completed: true },
      { id: 5, text: 'Video tutorials planned', completed: false },
    ],
    legal: [
      { id: 1, text: 'Terms of Service published', completed: true },
      { id: 2, text: 'Privacy Policy published', completed: true },
      { id: 3, text: 'Cookie consent implemented', completed: true },
      { id: 4, text: 'Risk disclaimer displayed', completed: true },
      { id: 5, text: 'GDPR compliance verified', completed: false },
    ],
    support: [
      { id: 1, text: 'Help center configured', completed: false },
      { id: 2, text: 'Support email set up', completed: true },
      { id: 3, text: 'FAQ section complete', completed: true },
      { id: 4, text: 'Community forum configured', completed: false },
      { id: 5, text: 'Status page created', completed: false },
    ],
    launch: [
      { id: 1, text: 'Landing page deployed', completed: true },
      { id: 2, text: 'Social media accounts prepared', completed: false },
      { id: 3, text: 'Email marketing set up', completed: false },
      { id: 4, text: 'Beta tester invitations ready', completed: true },
      { id: 5, text: 'Analytics configured', completed: true },
    ],
  };

  const renderChecklist = (items: { id: number; text: string; completed: boolean }[], category: string) => (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
      <h3 className="text-lg font-semibold text-white mb-4 capitalize">{category}</h3>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.id} className="flex items-center gap-3">
            {item.completed ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <Circle className="w-5 h-5 text-slate-600" />
            )}
            <span className={item.completed ? 'text-slate-400 line-through' : 'text-white'}>
              {item.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center py-8 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl border border-blue-500/30">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Rocket className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Beta Release Preparation</h1>
          <p className="text-slate-400 max-w-2xl mx-auto">
            SmartPip Trader is ready for public beta. Complete the following checklist and prepare for launch.
          </p>
        </div>

        {/* Release Readiness Score */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 text-center">
            <div className="text-3xl font-bold text-emerald-400 mb-1">80%</div>
            <p className="text-sm text-slate-400">Overall Ready</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 text-center">
            <div className="text-3xl font-bold text-blue-400 mb-1">80%</div>
            <p className="text-sm text-slate-400">Documentation</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 text-center">
            <div className="text-3xl font-bold text-emerald-400 mb-1">80%</div>
            <p className="text-sm text-slate-400">Legal</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 text-center">
            <div className="text-3xl font-bold text-amber-400 mb-1">40%</div>
            <p className="text-sm text-slate-400">Support</p>
          </div>
        </div>

        {/* Checklist Grid */}
        <div className="grid grid-cols-2 gap-6">
          {renderChecklist(checklist.documentation, 'Documentation')}
          {renderChecklist(checklist.legal, 'Legal & Compliance')}
          {renderChecklist(checklist.support, 'Support Infrastructure')}
          {renderChecklist(checklist.launch, 'Launch Readiness')}
        </div>

        {/* Quick Links */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <h3 className="text-lg font-semibold text-white mb-4">Quick Links & Resources</h3>
          <div className="grid grid-cols-4 gap-4">
            {[
              { icon: Book, label: 'User Handbook', url: '/docs/handbook', color: 'blue' },
              { icon: Shield, label: 'Privacy Policy', url: '/privacy', color: 'emerald' },
              { icon: FileText, label: 'Terms of Service', url: '/terms', color: 'purple' },
              { icon: ExternalLink, label: 'API Docs', url: '/api/docs', color: 'amber' },
            ].map((link, i) => (
              <a
                key={i}
                href={link.url}
                className={`flex items-center gap-3 p-4 bg-${link.color}-500/10 border border-${link.color}-500/30 rounded-xl hover:bg-${link.color}-500/20 transition-colors`}
              >
                <link.icon className={`w-6 h-6 text-${link.color}-400`} />
                <span className="text-white font-medium">{link.label}</span>
              </a>
            ))}
          </div>
        </div>

        {/* Feedback Forms */}
        <div className="grid grid-cols-3 gap-6">
          {/* General Feedback */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">General Feedback</h3>
            </div>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Share your thoughts about SmartPip..."
              className="w-full h-32 px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
            <button className="mt-3 w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
              Submit Feedback
            </button>
          </div>

          {/* Bug Report */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Bug className="w-5 h-5 text-red-400" />
              <h3 className="text-lg font-semibold text-white">Report a Bug</h3>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Bug title"
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <textarea
                placeholder="Describe the bug..."
                className="w-full h-20 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <select className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="low">Low Severity</option>
                <option value="medium">Medium Severity</option>
                <option value="high">High Severity</option>
                <option value="critical">Critical</option>
              </select>
              <button className="w-full px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium transition-colors">
                Report Bug
              </button>
            </div>
          </div>

          {/* Feature Request */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-semibold text-white">Feature Request</h3>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Feature title"
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <textarea
                placeholder="Describe the feature..."
                className="w-full h-20 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <button className="w-full px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-medium transition-colors">
                Submit Request
              </button>
            </div>
          </div>
        </div>

        {/* Demo Mode */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
                <PlayCircle className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Demo Mode</h3>
                <p className="text-sm text-slate-400">Try SmartPip without creating an account</p>
              </div>
            </div>
            <button className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors">
              <PlayCircle className="w-5 h-5" />
              Launch Demo
            </button>
          </div>
        </div>

        {/* Changelog Preview */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Latest Updates</h3>
            <button className="text-sm text-blue-400 hover:text-blue-300">View full changelog</button>
          </div>
          <div className="space-y-4">
            {[
              { version: 'v1.0.0-beta', date: 'July 17, 2026', changes: ['Initial beta release', 'AI Command Center', 'Replay Intelligence', 'Risk Intelligence', 'Strategy Marketplace'] },
              { version: 'v0.9.0', date: 'July 10, 2026', changes: ['Performance improvements', 'Bug fixes', 'Enhanced analytics'] },
              { version: 'v0.8.0', date: 'July 1, 2026', changes: ['Beta preview release', 'Core trading features'] },
            ].map((release, i) => (
              <div key={i} className="flex gap-4 p-4 bg-slate-800/50 rounded-lg">
                <div className="text-center min-w-24">
                  <p className="font-medium text-blue-400">{release.version}</p>
                  <p className="text-xs text-slate-500">{release.date}</p>
                </div>
                <div className="flex-1">
                  <ul className="space-y-1">
                    {release.changes.map((change, j) => (
                      <li key={j} className="text-sm text-slate-300 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        {change}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
