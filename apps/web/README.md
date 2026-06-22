# web

Thin React console for the agentic portfolio and paper-trading workbench.

## Scope

- Shows the first operator dashboard for briefing, provider health, screener candidates, recommendation evidence, paper-ledger approvals, risk switches, and report/audit readiness.
- Reads from `GET /console/overview` on the agent service.
- Falls back to deterministic fixture data when the API is unavailable, so local UI checks remain reproducible.
- Exposes no live-trading or credential workflow.

## Commands

```bash
npm ci
npm run typecheck
npm run build
npm run dev
```

The default API base is `http://localhost:8000`. Override it with:

```bash
VITE_AGENT_API_URL=http://localhost:8000
```
