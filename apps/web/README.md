# web

Thin React console for the agentic portfolio and paper-trading workbench.

## Scope

- Shows the operator dashboard plus focused workflow pages for screeners, strategy/backtest review, paper approvals, reports, and provider settings with guided configured-source onboarding, configured-source setup, required env keys, active adapter modes, setup-gap feedback, schema/template guidance, configured-file validation, provider profiles, refresh readiness, full-refresh controls, per-provider backoff state, and import-job feedback.
- Reads from `GET /console/overview` and `GET /console/workflows` on the agent service.
- Calls only policy-controlled console workflow endpoints for paper strategy drafts, simulated backtest requests, paper order proposals, human approval, simulated paper fills, and sanitized provider profile refreshes.
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
