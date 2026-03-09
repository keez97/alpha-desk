# AlphaDesk — Agent Roster

## Agent Responsibilities

### Orchestration Agent
- Plans full build, decomposes features into atomic tasks
- Passes full context bundles to sub-agents
- Reviews TASK_MANIFEST.md before every action
- Owns: PROJECT.md, AGENTS.md, TASK_MANIFEST.md, .context/

### Backend Agent
- Python FastAPI backend
- Owns: `/backend/` directory
- Responsible for: data fetching, caching, API routes, yfinance integration, financialdatasets.ai integration, portfolio math, Claude API calls

### Frontend Agent
- React + TypeScript + Vite
- Owns: `/frontend/src/` (except styles/)
- Responsible for: page routing, state management, data fetching hooks, chart components, UI rendering

### UI Agent
- Owns: `/frontend/src/styles/` and design tokens
- Responsible for: Tailwind config, dark mode, responsive layout, Bloomberg Terminal-inspired aesthetic

### Review Agent
- Audits all code before merge
- Checks: no hardcoded keys, no broken imports, consistent error handling, loading/error states, TypeScript types

### Merge Agent
- Executes merges after Review Agent approval
- Resolves conflicts, tags releases, updates TASK_MANIFEST.md

## File Ownership
| Directory | Owner |
|-----------|-------|
| /backend/ | Backend Agent |
| /frontend/src/styles/ | UI Agent |
| /frontend/src/ (rest) | Frontend Agent |
| /*.md, /.context/ | Orchestration Agent |

## Communication Protocol
- All context passed explicitly via task bundles (no implicit state)
- Sub-agents report completion with file list and summary
- Blocking issues escalated to Orchestration Agent

## Escalation Paths
- API integration issues → Backend Agent
- Rendering/layout issues → UI Agent
- Cross-cutting concerns → Orchestration Agent
