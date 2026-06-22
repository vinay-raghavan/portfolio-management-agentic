import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  DatabaseZap,
  FileBarChart,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  ListChecks,
  LockKeyhole,
  Microscope,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  WalletCards,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_AGENT_API_URL ?? 'http://localhost:8000';

type JsonRecord = Record<string, any>;

const fallbackOverview: JsonRecord = {
  mode: 'paper_only',
  safety: {
    live_trading: 'blocked',
    broker_trading_tokens: 'forbidden',
    simulated_fills: 'approval_required',
  },
  workflow_actions: [
    {
      label: 'Run pre-market briefing',
      tool: 'create_pre_market_briefing',
      tier: 'read_only',
    },
    {
      label: 'Review approval queue',
      tool: 'get_approval_queue',
      tier: 'read_only',
    },
    {
      label: 'Generate paper report',
      tool: 'generate_paper_trading_report',
      tier: 'read_only',
    },
  ],
  briefing: {
    status: 'success',
    briefing: {
      portfolio: {
        currency: 'INR',
        total_value: 454592,
        day_pnl: 842.35,
        holdings: [
          { symbol: 'INFY', sector: 'Information Technology', quantity: 12, market_value: 18030 },
          { symbol: 'HDFCBANK', sector: 'Financials', quantity: 9, market_value: 14653.8 },
          { symbol: 'TCS', sector: 'Information Technology', quantity: 5, market_value: 18990 },
          { symbol: 'NIFTYBEES', sector: 'Index ETF', quantity: 40, market_value: 9976 },
        ],
      },
      signal_summary: {
        regime: 'constructive',
        confidence: 0.68,
        index_moves: {
          'NIFTY 50': 0.34,
          'NIFTY 500': 0.27,
          'BANK NIFTY': 0.12,
          'INDIA VIX': -1.8,
        },
      },
      suggested_review_actions: [
        'Review sector concentration before prioritizing candidates.',
        'Compare top watchlist setups against signal confidence and counterevidence.',
        'Confirm paper risk switches remain enabled and live trading remains disabled.',
      ],
    },
  },
  providers: {
    status: 'success',
    health: [
      { provider_id: 'market_data.fixture', status: 'available', mode: 'fixture' },
      { provider_id: 'fundamentals.fixture', status: 'available', mode: 'fixture' },
      { provider_id: 'sentiment.fixture', status: 'available', mode: 'fixture' },
    ],
  },
  screener: {
    status: 'success',
    result: {
      candidates: [
        { symbol: 'TATAMOTORS', setup: 'breakout-continuation', score: 0.82, decision: 'review' },
        { symbol: 'SBIN', setup: 'pullback-to-support', score: 0.74, decision: 'watch' },
        { symbol: 'SUNPHARMA', setup: 'trend-resumption', score: 0.7, decision: 'watch' },
      ],
    },
  },
  recommendation: {
    status: 'success',
    recommendation: {
      symbol: 'TATAMOTORS',
      setup: 'breakout-continuation',
      stance: 'paper_draft_candidate',
      confidence: 0.72,
      next_allowed_actions: ['draft_paper_strategy', 'create_backtest_request'],
    },
  },
  paper_ledger: {
    accounting: {
      status: 'success',
      accounting: {
        open_positions: 2,
        pending_orders: 1,
        approved_orders: 0,
        filled_orders: 1,
        simulated_fills: 1,
        total_market_value: 52941,
        total_unrealized_pnl: 642.4,
      },
    },
    approvals: {
      status: 'success',
      approval_queue: [
        {
          approval_id: 'approval-paper-tatamotors-001',
          entity_id: 'paper-order-tatamotors-001',
          status: 'pending',
          requested_action: 'simulate_paper_fill',
        },
      ],
    },
  },
  risk: {
    status: 'success',
    risk_review: {
      status: 'review',
      safety_switches: {
        live_trading: 'disabled',
        paper_trading: 'enabled',
        broker_token_access: 'forbidden',
      },
      recommended_pauses: [
        'Pause any strategy that requests live order placement.',
        'Review position sizing for high-ATR candidates.',
      ],
    },
  },
  report: {
    status: 'success',
    report: {
      summary: {
        audit_event_count: 4,
        pending_approval_count: 1,
        simulated_fills: 1,
      },
      audit_export: {
        schema_version: 'paper-audit-export/v1',
        redaction_status: 'redacted',
      },
    },
  },
};

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, active: true },
  { label: 'Portfolio', icon: WalletCards },
  { label: 'Briefing', icon: Gauge },
  { label: 'Screener', icon: Search },
  { label: 'Strategies', icon: Bot },
  { label: 'Backtests', icon: FlaskConical },
  { label: 'Paper Ledger', icon: ClipboardCheck },
  { label: 'Reports', icon: FileBarChart },
  { label: 'Settings', icon: Settings },
];

const workflowIcons = [Play, ListChecks, FileBarChart];

function formatCurrency(value: number, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatPercent(value: number) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function scoreLabel(value: number) {
  return `${Math.round((value || 0) * 100)}`;
}

function pickCandidates(overview: JsonRecord) {
  return (
    overview.screener?.result?.candidates ??
    overview.screener?.screener_run?.candidates ??
    overview.screener?.candidates ??
    []
  ).slice(0, 5);
}

function StatusPill({
  tone,
  children,
}: {
  tone: 'good' | 'warn' | 'danger' | 'info' | 'neutral';
  children: ReactNode;
}) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function MetricTile({
  label,
  value,
  detail,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  detail: string;
  tone?: 'good' | 'warn' | 'danger' | 'info' | 'neutral';
}) {
  return (
    <section className={`metric-tile ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </section>
  );
}

function App() {
  const [overview, setOverview] = useState<JsonRecord>(fallbackOverview);
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'fallback'>('loading');
  const [activeWorkflow, setActiveWorkflow] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/console/overview`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Console overview failed: ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        setOverview(payload);
        setLoadState('ready');
      })
      .catch(() => {
        setLoadState('fallback');
      });
    return () => controller.abort();
  }, []);

  const briefing = overview.briefing?.briefing ?? {};
  const portfolio = briefing.portfolio ?? {};
  const signal = briefing.signal_summary ?? {};
  const accounting = overview.paper_ledger?.accounting?.accounting ?? {};
  const approvals =
    overview.paper_ledger?.approvals?.approval_queue ??
    overview.paper_ledger?.approvals?.approval_requests ??
    [];
  const report = overview.report?.report ?? {};
  const risk = overview.risk?.risk_review ?? {};
  const recommendation = overview.recommendation?.recommendation ?? {};
  const candidates = useMemo(() => pickCandidates(overview), [overview]);
  const workflow = overview.workflow_actions?.[activeWorkflow] ?? overview.workflow_actions?.[0];

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-mark">
          <div className="brand-icon">
            <Activity size={20} aria-hidden="true" />
          </div>
          <div>
            <strong>Portfolio Agentic</strong>
            <span>Paper workspace</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={`nav-item ${item.active ? 'active' : ''}`} key={item.label}>
                <Icon size={17} aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <section className="safety-card">
          <LockKeyhole size={18} aria-hidden="true" />
          <strong>Live trading blocked</strong>
          <span>Paper only</span>
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>Agentic portfolio console</h1>
            <p>Pre-market review, research evidence, paper approvals, and audit reports.</p>
          </div>
          <div className="topbar-actions">
            <StatusPill tone={loadState === 'ready' ? 'good' : 'warn'}>
              {loadState === 'ready' ? 'API connected' : 'Fixture snapshot'}
            </StatusPill>
            <StatusPill tone="danger">Live trading blocked</StatusPill>
          </div>
        </header>

        <section className="metrics-grid" aria-label="Portfolio and paper ledger summary">
          <MetricTile
            label="Portfolio value"
            value={formatCurrency(portfolio.total_value ?? 0, portfolio.currency ?? 'INR')}
            detail={`${portfolio.holdings?.length ?? 0} fixture holdings`}
            tone="info"
          />
          <MetricTile
            label="Day P&L"
            value={formatCurrency(portfolio.day_pnl ?? 0, portfolio.currency ?? 'INR')}
            detail="Synthetic demo portfolio"
            tone={(portfolio.day_pnl ?? 0) >= 0 ? 'good' : 'danger'}
          />
          <MetricTile
            label="Signal regime"
            value={signal.regime ?? 'review'}
            detail={`${scoreLabel(signal.confidence ?? 0)} confidence score`}
            tone="good"
          />
          <MetricTile
            label="Paper Ledger"
            value={`${accounting.open_positions ?? 0} open`}
            detail={`${accounting.pending_orders ?? 0} pending orders`}
            tone="warn"
          />
        </section>

        <section className="main-grid">
          <section className="panel workflow-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Agent workflows</span>
                <h2>Safe action launcher</h2>
              </div>
              <ShieldCheck size={20} aria-hidden="true" />
            </div>
            <div className="workflow-list">
              {(overview.workflow_actions ?? []).map((action: JsonRecord, index: number) => {
                const Icon = workflowIcons[index] ?? Play;
                return (
                  <button
                    className={`workflow-button ${activeWorkflow === index ? 'selected' : ''}`}
                    key={action.tool}
                    onClick={() => setActiveWorkflow(index)}
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{action.label}</span>
                    <small>{action.tier}</small>
                  </button>
                );
              })}
            </div>
            <div className="selected-workflow">
              <span>Selected tool</span>
              <strong>{workflow?.tool ?? 'create_pre_market_briefing'}</strong>
              <p>{workflow?.label ?? 'Run pre-market briefing'}</p>
            </div>
          </section>

          <section className="panel briefing-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Briefing</span>
                <h2>Market open review</h2>
              </div>
              <RefreshCw size={19} aria-hidden="true" />
            </div>
            <div className="index-strip">
              {Object.entries(signal.index_moves ?? {}).map(([name, value]) => (
                <div key={name}>
                  <span>{name}</span>
                  <strong className={Number(value) >= 0 ? 'positive' : 'negative'}>
                    {formatPercent(Number(value))}
                  </strong>
                </div>
              ))}
            </div>
            <ul className="review-list">
              {(briefing.suggested_review_actions ?? []).slice(0, 3).map((item: string) => (
                <li key={item}>
                  <CheckCircle2 size={15} aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel screener-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Research</span>
                <h2>Screener candidates</h2>
              </div>
              <Search size={19} aria-hidden="true" />
            </div>
            <div className="candidate-table" role="table" aria-label="Screener candidates">
              <div className="table-row table-head" role="row">
                <span>Symbol</span>
                <span>Setup</span>
                <span>Score</span>
              </div>
              {candidates.map((candidate: JsonRecord) => (
                <div className="table-row" role="row" key={`${candidate.symbol}-${candidate.setup}`}>
                  <strong>{candidate.symbol}</strong>
                  <span>{candidate.setup}</span>
                  <span className="score-bar">
                    <i style={{ width: `${Math.round((candidate.score ?? 0) * 100)}%` }} />
                    <b>{scoreLabel(candidate.score)}</b>
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel evidence-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Recommendation</span>
                <h2>{recommendation.symbol ?? 'TATAMOTORS'} evidence</h2>
              </div>
              <Microscope size={19} aria-hidden="true" />
            </div>
            <div className="recommendation-card">
              <StatusPill tone="info">{recommendation.stance ?? 'paper_draft_candidate'}</StatusPill>
              <strong>{recommendation.setup ?? 'breakout-continuation'}</strong>
              <p>
                Confidence {scoreLabel(recommendation.confidence ?? 0)} with factor,
                history, risk, ledger, and citation context joined upstream.
              </p>
            </div>
            <div className="allowed-actions">
              {(recommendation.next_allowed_actions ?? ['draft_paper_strategy', 'create_backtest_request']).map((action: string) => (
                <span key={action}>{action}</span>
              ))}
            </div>
          </section>

          <section className="panel ledger-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Paper Ledger</span>
                <h2>Approval queue</h2>
              </div>
              <ClipboardCheck size={19} aria-hidden="true" />
            </div>
            {approvals.length ? (
              approvals.slice(0, 3).map((approval: JsonRecord) => (
                <div className="approval-row" key={approval.approval_id ?? approval.entity_id}>
                  <AlertTriangle size={17} aria-hidden="true" />
                  <div>
                    <strong>{approval.requested_action ?? 'simulate_paper_fill'}</strong>
                    <span>{approval.entity_id ?? approval.approval_id}</span>
                  </div>
                  <StatusPill tone="warn">{approval.status ?? 'pending'}</StatusPill>
                </div>
              ))
            ) : (
              <div className="empty-state">No pending approvals</div>
            )}
            <div className="ledger-stats">
              <span>{accounting.simulated_fills ?? 0} simulated fills</span>
              <span>{formatCurrency(accounting.total_unrealized_pnl ?? 0)}</span>
            </div>
          </section>

          <section className="panel reports-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Reports</span>
                <h2>Audit readiness</h2>
              </div>
              <FileBarChart size={19} aria-hidden="true" />
            </div>
            <div className="report-stack">
              <div>
                <span>Audit schema</span>
                <strong>{report.audit_export?.schema_version ?? 'paper-audit-export/v1'}</strong>
              </div>
              <div>
                <span>Redaction</span>
                <strong>{report.audit_export?.redaction_status ?? 'redacted'}</strong>
              </div>
              <div>
                <span>Audit rows</span>
                <strong>{report.summary?.audit_event_count ?? 0}</strong>
              </div>
            </div>
          </section>

          <section className="panel risk-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Risk</span>
                <h2>Safety switches</h2>
              </div>
              <LockKeyhole size={19} aria-hidden="true" />
            </div>
            <div className="switch-grid">
              <StatusPill tone="danger">Live trading blocked</StatusPill>
              <StatusPill tone="good">Paper enabled</StatusPill>
              <StatusPill tone="warn">Approval required</StatusPill>
            </div>
            <ul className="review-list compact">
              {(risk.recommended_pauses ?? []).slice(0, 2).map((pause: string) => (
                <li key={pause}>
                  <AlertTriangle size={15} aria-hidden="true" />
                  <span>{pause}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel provider-panel">
            <div className="panel-heading">
              <div>
                <span className="eyeless-label">Data</span>
                <h2>Provider health</h2>
              </div>
              <DatabaseZap size={19} aria-hidden="true" />
            </div>
            <div className="provider-list">
              {(overview.providers?.health ?? []).slice(0, 5).map((provider: JsonRecord) => (
                <div className="provider-row" key={provider.provider_id ?? provider.name}>
                  <span>{provider.provider_id ?? provider.name}</span>
                  <StatusPill tone={provider.status === 'available' ? 'good' : 'warn'}>
                    {provider.status ?? provider.mode ?? 'fixture'}
                  </StatusPill>
                </div>
              ))}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

export default App;
