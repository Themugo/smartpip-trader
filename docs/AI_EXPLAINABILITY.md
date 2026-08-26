# AI Explainability System

## Overview

This module provides comprehensive explainability for all AI trading decisions. Every decision made by the AI system is fully documented, explained, and permanently stored for audit and compliance purposes.

## Features

### Explanation Levels

The system generates explanations at four levels of detail:

1. **Beginner** - Simple, non-technical explanations suitable for users without trading experience
2. **Advanced** - Detailed trading explanations with signal breakdowns and risk metrics
3. **Developer** - Technical implementation details including code references and data structures
4. **Researcher** - Research-grade analysis with full methodology and statistical analysis

### Core Components

#### 1. AI Explainer (`explainer.py`)

The core engine that generates comprehensive explanations for every AI decision.

**Key Capabilities:**
- Executive summary generation
- Why opportunity exists analysis
- Why confidence has this value
- Historical analogues identification
- Expected value estimation
- Risk assessment
- Feature importance analysis
- Decision tree construction
- Alternative actions consideration
- Rejection reasons documentation

#### 2. Explanation Storage (`storage.py`)

Permanent storage for all explanations with full evidence chains.

**Database Schema:**
- `explanations` - Main explanation records
- `evidence_items` - Evidence chain items
- `analyzer_signals` - Individual analyzer signals
- `alternative_actions` - Alternative actions considered
- `historical_analogues` - Similar past decisions
- `feature_importance` - Feature importance scores
- `decision_tree_steps` - Decision tree steps

#### 3. Search (`search.py`)

Full-text and structured search for historical explanations.

**Search Capabilities:**
- Text search across all explanation content
- Filter by action, symbol, confidence, risk level
- Date range queries
- Analyzer-specific searches
- Relevance-ranked results

#### 4. Audit Viewer (`audit_viewer.py`)

Reconstruct and audit historical decisions.

**Audit Capabilities:**
- Decision reconstruction from stored evidence
- Integrity verification
- Validity assessment
- Finding generation
- Recommendation generation
- Audit package export

### Output Formats

The system supports multiple output formats:

- **JSON** - For API responses and programmatic access
- **HTML** - For web display with interactive tabs
- **Markdown** - For documentation and export
- **PDF** - For compliance reports (stub implementation)

## API Endpoints

### Explanation Generation
- `POST /api/explainability/explain` - Generate explanation for a decision

### Explanation Retrieval
- `GET /api/explainability/explanation/{id}` - Get explanation by ID
- `GET /api/explainability/explanation/decision/{decision_id}` - Get by decision ID

### Search
- `GET /api/explainability/search` - Search explanations
- `GET /api/explainability/recent` - Get recent explanations

### Audit
- `GET /api/explainability/audit/{id}` - Generate audit report
- `GET /api/explainability/reconstruct/{id}` - Reconstruct decision
- `GET /api/explainability/audit-package/{id}` - Export audit package

### Replay
- `GET /api/explainability/replay/{id}` - Replay explanation at specific level

### Statistics
- `GET /api/explainability/stats` - Get explanation statistics

### Formatted Output
- `GET /api/explainability/html/{id}` - Get as HTML
- `GET /api/explainability/markdown/{id}` - Get as Markdown
- `GET /api/explainability/json/{id}` - Get as JSON

## Usage

### Python API

```python
from ai_explainability import init_integration, ExplanationStorage

# Initialize integration
integrator = init_integration({'storage_path': 'explanations.db'})

# Generate explanation for a decision
explanation_id = await integrator.explain_decision(
    decision_id="dec-123",
    decision_result=result,
    context=context_data,
)

# Search explanations
results = integrator.search_explanations(
    query="EUR/USD",
    min_confidence=70,
)

# Get statistics
stats = integrator.get_statistics()

# Use storage directly
storage = ExplanationStorage('explanations.db')
explanation = storage.get_explanation(explanation_id)
```

### REST API

```bash
# Generate explanation
curl -X POST /api/explainability/explain \
  -H "Content-Type: application/json" \
  -d '{"decision_id": "dec-123", "action": "BUY", ...}'

# Get explanation
curl /api/explainability/explanation/dec-123

# Search
curl /api/explainability/search?q=EUR/USD&min_confidence=70

# Get audit report
curl /api/explainability/audit/{explanation_id}
```

## Data Stored

### For Each Decision, We Store:

1. **Executive Summary**
   - Action taken
   - Confidence level
   - Risk level
   - Expected value
   - Why opportunity exists
   - Why confidence has this value

2. **Evidence Chain**
   - Market regime evidence
   - Analyzer signals
   - Consensus data
   - Feature importance
   - Historical analogues

3. **Analysis at Each Level**
   - Beginner explanation
   - Advanced explanation
   - Developer explanation
   - Researcher explanation

4. **Audit Trail**
   - Decision tree
   - Alternatives considered
   - Rejection reasons
   - Integrity verification

## Integration

### With AI Core Orchestrator

```python
from ai_explainability import ExplainabilityMiddleware

# Create middleware
middleware = ExplainabilityMiddleware(integrator)

# Add as validator
orchestrator.add_validator(middleware)
```

### With Frontend

```tsx
import AIAuditViewer from './components/AIAuditViewer';

function App() {
  return (
    <div>
      <AIAuditViewer />
    </div>
  );
}
```

## Compliance

This system satisfies requirements for:
- AI decision auditability
- Regulatory compliance documentation
- Model transparency
- Explanation generation for end users
- Historical decision reconstruction
