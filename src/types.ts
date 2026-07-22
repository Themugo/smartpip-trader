export type Tab =
  | 'dashboard'
  | 'regimes'
  | 'sizing'
  | 'evidence'
  | 'mlaudit'
  | 'shadow'
  | 'journal'
  | 'validation'
  | 'review';

export type Workspace =
  | 'dashboard'
  | 'live_trading'
  | 'paper_trading'
  | 'backtesting'
  | 'strategy_builder'
  | 'analytics'
  | 'risk_center'
  | 'notifications'
  | 'ai_command_center'
  | 'developer_console'
  | 'settings';

export type BotStatus = 'RUNNING' | 'STOPPED' | 'PAUSED';
