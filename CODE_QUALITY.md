# SmartPip Trader - Code Quality Guide

## TypeScript Guidelines

### Types
```typescript
// ✅ Good: Explicit types for function signatures
function calculateProfit(trades: Trade[]): number {
  return trades.reduce((sum, trade) => sum + (trade.profit || 0), 0);
}

// ❌ Bad: Missing types
function calculateProfit(trades) {
  return trades.reduce((sum, trade) => sum + trade.profit, 0);
}
```

### Interfaces vs Types
```typescript
// ✅ Use interfaces for object shapes that may be extended
interface User {
  id: string;
  email: string;
  name: string;
}

// ✅ Use types for unions, intersections, or primitives
type Plan = 'free' | 'starter' | 'professional' | 'enterprise';
```

### Null Safety
```typescript
// ✅ Good: Handle null/undefined
const balance = user?.account?.balance ?? 0;

// ❌ Bad: Assumption of non-null
const balance = user.account.balance;
```

## React Best Practices

### Component Structure
```typescript
// 1. Imports
import { useState, useEffect } from 'react';
import { Button } from './Button';

// 2. Type definitions
interface Props {
  title: string;
  onClose: () => void;
}

// 3. Component definition
export function Modal({ title, onClose }: Props) {
  // 4. Hooks (state, refs, effects)
  const [isOpen, setIsOpen] = useState(true);
  
  // 5. Callbacks
  const handleClose = () => {
    setIsOpen(false);
    onClose();
  };
  
  // 6. Effects
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);
  
  // 7. Render
  if (!isOpen) return null;
  
  return (
    <div className="modal">
      <h2>{title}</h2>
      <button onClick={handleClose}>Close</button>
    </div>
  );
}
```

### Custom Hooks
```typescript
// ✅ Good: Isolated, reusable logic
function useBrokerConnection(brokerId: string) {
  const [status, setStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [balance, setBalance] = useState<number | null>(null);
  
  useEffect(() => {
    connect(brokerId).then(setStatus);
    return () => disconnect(brokerId);
  }, [brokerId]);
  
  return { status, balance };
}
```

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `TradeHistory` |
| Hooks | camelCase with `use` prefix | `useTradeHistory` |
| Types/Interfaces | PascalCase | `TradeStatistics` |
| Constants | UPPER_SNAKE_CASE | `MAX_TRADES_PER_DAY` |
| Functions | camelCase | `calculateProfit` |
| Files | kebab-case | `trade-history.tsx` |
| CSS Classes | kebab-case | `bg-slate-900` |

## File Organization

```
src/
├── components/          # React components
│   ├── ui/            # Reusable UI components
│   └── features/     # Feature-specific components
├── hooks/             # Custom React hooks
├── lib/               # Utilities, helpers, API clients
├── pages/             # Page components (if using file-based routing)
├── types/             # TypeScript type definitions
└── App.tsx            # Root component
```

## Performance Guidelines

### Bundle Size
- Lazy load routes: `const Dashboard = lazy(() => import('./Dashboard'));`
- Split large components
- Tree-shake unused imports
- Target: < 500KB gzipped main bundle

### Rendering
- Use `React.memo()` for expensive components
- Use `useMemo()` for expensive calculations
- Use `useCallback()` for callbacks passed to children
- Avoid anonymous functions in render

### Data Fetching
- Cache API responses
- Debounce search inputs
- Paginate large lists
- Use React Query or SWR for server state

## Testing Guidelines

### Test Structure
```typescript
describe('TradeCalculator', () => {
  it('calculates profit correctly', () => {
    const trades: Trade[] = [
      { profit: 10 },
      { profit: -5 },
      { profit: 15 },
    ];
    
    expect(calculateTotalProfit(trades)).toBe(20);
  });
  
  it('handles empty array', () => {
    expect(calculateTotalProfit([])).toBe(0);
  });
});
```

### Test Coverage Goals
- Components: 80%+
- Hooks: 80%+
- Utilities: 90%+
- API clients: 70%+

## Git Workflow

### Branch Naming
- `feature/*` - New features
- `fix/*` - Bug fixes
- `refactor/*` - Code refactoring
- `docs/*` - Documentation updates
- `chore/*` - Maintenance tasks

### Commit Messages
```
feat: add broker connection modal
fix: resolve token validation issue
refactor: simplify trade calculation logic
docs: update API documentation
test: add tests for shadow mode
```

### Pull Request Checklist
- [ ] Tests pass
- [ ] Linting passes
- [ ] Types compile
- [ ] No console.log statements
- [ ] Self-reviewed
- [ ] Documentation updated (if needed)

## Code Review Guidelines

### For Reviewers
- Be constructive and specific
- Focus on logic, not style (use linters)
- Ask questions, don't assume
- Approve only when confident

### For Authors
- Keep PRs small (< 400 lines)
- Write clear descriptions
- Respond to feedback promptly
- Don't take feedback personally

## Linting Configuration

The project uses ESLint with the following plugins:
- `@typescript-eslint` - TypeScript rules
- `react` - React rules
- `react-hooks` - Hooks rules
- `jsx-a11y` - Accessibility rules

Run linting:
```bash
npm run lint        # Check
npm run lint:fix    # Auto-fix
```

## Pre-commit Hooks

Before every commit, the following run:
1. TypeScript type check
2. ESLint
3. Tests (if changed)

Configure in `husky`:
```bash
npx husky add .husky/pre-commit "npm run pre-commit"
```
