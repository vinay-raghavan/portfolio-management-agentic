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
type LoadState = 'loading' | 'ready' | 'fallback';
type PageId =
  | 'dashboard'
  | 'screener'
  | 'strategy-backtest'
  | 'paper-approvals'
  | 'reports'
  | 'settings';

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
    screener_run: {
      candidates: [
        { symbol: 'TATAMOTORS', setup: 'breakout-continuation', score: 0.82, decision: 'review' },
        { symbol: 'SBIN', setup: 'pullback-to-support', score: 0.74, decision: 'watch' },
        { symbol: 'SUNPHARMA', setup: 'quality-momentum', score: 0.7, decision: 'watch' },
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
        pending_orders: 0,
        approved_orders: 0,
        filled_orders: 0,
        simulated_fills: 0,
        total_market_value: 52941,
        total_unrealized_pnl: 642.4,
      },
    },
    approvals: {
      status: 'success',
      approval_requests: [],
    },
  },
  risk: {
    status: 'success',
    risk_review: {
      status: 'review',
      safety_switches: {
        live_trading: 'disabled',
        paper_trading: 'enabled',
        credential_access: 'forbidden',
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
        audit_event_count: 0,
        pending_approval_count: 0,
        simulated_fills: 0,
      },
      audit_export: {
        schema_version: 'paper-audit-export/v1',
        redaction_status: 'redacted',
      },
    },
  },
};

const fallbackWorkflows: JsonRecord = {
  mode: 'paper_only',
  safety: fallbackOverview.safety,
  pages: [
    {
      id: 'dashboard',
      label: 'Dashboard',
      primary_tool: 'create_pre_market_briefing',
      tier: 'read_only',
      summary: 'Overview of safe paper-trading workflows.',
    },
    {
      id: 'screener',
      label: 'Screener',
      primary_tool: 'run_screener',
      tier: 'read_only',
      summary: 'Run deterministic screeners and inspect factor evidence.',
    },
    {
      id: 'strategy-backtest',
      label: 'Strategies & Backtests',
      primary_tool: 'draft_paper_strategy',
      tier: 'draft_only',
      summary: 'Draft paper strategies and simulated backtest requests.',
    },
    {
      id: 'paper-approvals',
      label: 'Paper Approvals',
      primary_tool: 'approve_paper_order_simulation',
      tier: 'approval_required',
      summary: 'Approve and simulate paper fills through human-gated actions.',
    },
    {
      id: 'reports',
      label: 'Reports',
      primary_tool: 'generate_paper_trading_report',
      tier: 'read_only',
      summary: 'Read paper trading reports and audit exports.',
    },
    {
      id: 'settings',
      label: 'Provider settings',
      primary_tool: 'get_data_provider_health',
      tier: 'read_only',
      summary: 'Review providers and risk switches.',
    },
  ],
  workflow_actions: fallbackOverview.workflow_actions,
  screener: {
    selected_universe: 'fixture_nifty50',
    selected_preset: 'momentum',
    universes: {
      status: 'success',
      universes: [{ universe_id: 'fixture_nifty50', name: 'Fixture NIFTY 50' }],
    },
    run: fallbackOverview.screener,
    factor_stack: {
      status: 'success',
      factor_stack: {
        symbol: 'TATAMOTORS',
        setup: 'breakout-continuation',
        factor_summary: {
          technical: { score: 0.92, weight: 0.35, evidence: ['Breakout and momentum pass.'] },
          volatility: { score: 0.52, weight: 0.15, evidence: ['ATR requires sizing review.'] },
          portfolio_fit: { score: 0.74, weight: 0.15, evidence: ['Adds non-technology exposure.'] },
        },
      },
    },
    patterns: {
      status: 'success',
      patterns: [
        {
          pattern_id: 'breakout-continuation-v1',
          setup_type: 'breakout-continuation',
          summary: 'Paper-only breakout continuation playbook.',
        },
      ],
    },
    allowed_actions: ['explain_factor_stack', 'draft_paper_strategy', 'create_backtest_request'],
  },
  strategy_backtest: {
    symbol: 'TATAMOTORS',
    setup: 'breakout-continuation',
    recommendation: fallbackOverview.recommendation,
    evidence: {
      status: 'success',
      evidence_pack: {
        evidence: ['Fixture evidence supports paper review.'],
        counterevidence: ['Live news sentiment adapter is not configured.'],
      },
    },
    strategy_drafts: { status: 'success', strategy_drafts: [] },
    backtest_requests: { status: 'success', backtest_requests: [] },
    latest_backtest: { status: 'empty', message: 'No backtest requests have been drafted yet.' },
    actions: {
      draft_strategy: { tier: 'draft_only' },
      create_backtest: { tier: 'draft_only' },
      create_paper_order: { tier: 'draft_only' },
    },
    defaults: {
      symbol: 'TATAMOTORS',
      setup: 'breakout-continuation',
      start_date: '2026-01-02',
      end_date: '2026-06-22',
    },
  },
  paper_approvals: {
    orders: { status: 'success', orders: [] },
    positions: { status: 'success', positions: [] },
    fills: { status: 'success', fills: [] },
    accounting: fallbackOverview.paper_ledger.accounting,
    approvals: fallbackOverview.paper_ledger.approvals,
    audit: { status: 'success', audit_events: [] },
    actions: {
      approve_simulation: { tier: 'approval_required' },
      simulate_fill: { tier: 'approval_required' },
    },
  },
  reports: {
    report: fallbackOverview.report,
    audit: { status: 'success', audit_events: [] },
    actions: {
      generate_report: { tier: 'read_only' },
      read_audit: { tier: 'read_only' },
    },
  },
  settings: {
    providers: { status: 'success', providers: [] },
    health: fallbackOverview.providers,
    import_validation: {
      status: 'success',
      summary: { total: 6, configured: 0, valid: 0, needs_attention: 0 },
      validations: [],
    },
    risk: fallbackOverview.risk,
    safety: fallbackOverview.safety,
  },
};

const navItems: Array<{ id: PageId; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'screener', label: 'Screener', icon: Search },
  { id: 'strategy-backtest', label: 'Strategies', icon: Bot },
  { id: 'strategy-backtest', label: 'Backtests', icon: FlaskConical },
  { id: 'paper-approvals', label: 'Paper Ledger', icon: ClipboardCheck },
  { id: 'reports', label: 'Reports', icon: FileBarChart },
  { id: 'settings', label: 'Settings', icon: Settings },
];

const workflowIcons = [Play, ListChecks, FileBarChart];
const screenerPresets = ['momentum', 'breakout', 'pullback', 'multi_factor'];

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

function humanize(value: string) {
  return value.replace(/_/g, ' ');
}

function pickCandidates(payload: JsonRecord) {
  return (
    payload.screener?.run?.screener_run?.candidates ??
    payload.screener?.run?.result?.candidates ??
    payload.screener?.screener_run?.candidates ??
    payload.screener?.result?.candidates ??
    []
  ).slice(0, 6);
}

function firstCandidate(payload: JsonRecord) {
  return pickCandidates(payload)[0] ?? { symbol: 'TATAMOTORS', setup: 'breakout-continuation' };
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

function PanelHeading({
  label,
  title,
  icon,
}: {
  label: string;
  title: string;
  icon: ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <span className="eyeless-label">{label}</span>
        <h2>{title}</h2>
      </div>
      {icon}
    </div>
  );
}

function ActionButton({
  children,
  disabled,
  busy,
  onClick,
}: {
  children: ReactNode;
  disabled?: boolean;
  busy?: boolean;
  onClick: () => void;
}) {
  return (
    <button className="command-button" disabled={disabled || busy} onClick={onClick}>
      {busy ? 'Working...' : children}
    </button>
  );
}

function App() {
  const [overview, setOverview] = useState<JsonRecord>(fallbackOverview);
  const [workflows, setWorkflows] = useState<JsonRecord>(fallbackWorkflows);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [workflowState, setWorkflowState] = useState<LoadState>('loading');
  const [activeWorkflow, setActiveWorkflow] = useState(0);
  const [activePage, setActivePage] = useState<PageId>('dashboard');
  const [screenerPreset, setScreenerPreset] = useState('momentum');
  const [busyAction, setBusyAction] = useState('');
  const [actionResult, setActionResult] = useState<JsonRecord | null>(null);

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

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      universe_id: 'fixture_nifty50',
      preset: screenerPreset,
      limit: '5',
    });
    setWorkflowState('loading');
    fetch(`${API_BASE}/console/workflows?${params.toString()}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Console workflows failed: ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        setWorkflows(payload);
        setWorkflowState('ready');
      })
      .catch(() => {
        setWorkflowState('fallback');
      });
    return () => controller.abort();
  }, [screenerPreset]);

  const briefing = overview.briefing?.briefing ?? {};
  const portfolio = briefing.portfolio ?? {};
  const signal = briefing.signal_summary ?? {};
  const accounting =
    workflows.paper_approvals?.accounting?.accounting ??
    overview.paper_ledger?.accounting?.accounting ??
    {};
  const approvals =
    workflows.paper_approvals?.approvals?.approval_requests ??
    overview.paper_ledger?.approvals?.approval_requests ??
    overview.paper_ledger?.approvals?.approval_queue ??
    [];
  const report = workflows.reports?.report?.report ?? overview.report?.report ?? {};
  const risk = workflows.settings?.risk?.risk_review ?? overview.risk?.risk_review ?? {};
  const recommendation =
    workflows.strategy_backtest?.recommendation?.recommendation ??
    overview.recommendation?.recommendation ??
    {};
  const candidates = useMemo(() => pickCandidates(workflows), [workflows]);
  const selectedCandidate = firstCandidate(workflows);
  const workflow = overview.workflow_actions?.[activeWorkflow] ?? overview.workflow_actions?.[0];
  const pages = workflows.pages ?? fallbackWorkflows.pages;
  const strategyDrafts = workflows.strategy_backtest?.strategy_drafts?.strategy_drafts ?? [];
  const backtestRequests = workflows.strategy_backtest?.backtest_requests?.backtest_requests ?? [];
  const latestBacktest = workflows.strategy_backtest?.latest_backtest ?? {};
  const paperOrders = workflows.paper_approvals?.orders?.orders ?? [];
  const paperPositions = workflows.paper_approvals?.positions?.positions ?? [];
  const paperFills = workflows.paper_approvals?.fills?.fills ?? [];
  const auditEvents = workflows.reports?.audit?.audit_events ?? [];
  const factorSummary = workflows.screener?.factor_stack?.factor_stack?.factor_summary ?? {};
  const patterns = workflows.screener?.patterns?.patterns ?? [];
  const providers = workflows.settings?.providers?.providers ?? [];
  const providerHealth = workflows.settings?.health?.health ?? overview.providers?.health ?? [];
  const importValidation = workflows.settings?.import_validation ?? fallbackWorkflows.settings.import_validation;
  const defaults = workflows.strategy_backtest?.defaults ?? {
    symbol: selectedCandidate.symbol,
    setup: selectedCandidate.setup,
    start_date: '2026-01-02',
    end_date: '2026-06-22',
  };
  const latestStrategyId =
    strategyDrafts.at(-1)?.strategy_id ??
    `paper-${String(defaults.symbol ?? 'tatamotors').toLowerCase()}-momentum-001`;
  const firstOrder = paperOrders[0];
  const pendingOrder = paperOrders.find((order: JsonRecord) => order.status === 'pending_approval');
  const approvedOrder = paperOrders.find((order: JsonRecord) => order.status === 'approved');

  async function postWorkflowAction(path: string, body: JsonRecord, label: string) {
    setBusyAction(label);
    setActionResult(null);
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? `${label} failed`);
      }
      if (payload.state) {
        setWorkflows(payload.state);
        setWorkflowState('ready');
      }
      setActionResult({
        tone: 'good',
        title: label,
        message: `${payload.action?.status ?? 'completed'} via ${payload.action?.policy?.tier ?? 'policy'} action`,
      });
    } catch (error) {
      setActionResult({
        tone: 'danger',
        title: label,
        message: error instanceof Error ? error.message : 'Action failed',
      });
    } finally {
      setBusyAction('');
    }
  }

  function runDraftStrategy() {
    void postWorkflowAction(
      '/console/workflows/strategy-drafts',
      {
        symbol: defaults.symbol,
        rationale:
          'Breakout continuation remains backed by fixture evidence, risk review, and paper-only policy gates.',
      },
      'Draft paper strategy',
    );
  }

  function runBacktestRequest() {
    void postWorkflowAction(
      '/console/workflows/backtests',
      {
        symbol: defaults.symbol,
        setup: defaults.setup,
        start_date: defaults.start_date,
        end_date: defaults.end_date,
      },
      'Create backtest request',
    );
  }

  function runPaperOrderProposal() {
    const proposalSuffix = new Date().toISOString().replace(/[^0-9]/g, '');
    void postWorkflowAction(
      '/console/workflows/paper-orders',
      {
        strategy_id: `${latestStrategyId}-proposal-${proposalSuffix}`,
        symbol: defaults.symbol,
        side: 'buy',
        quantity: 2,
        order_type: 'market',
      },
      'Create paper order proposal',
    );
  }

  function runApproval() {
    if (!pendingOrder) {
      return;
    }
    void postWorkflowAction(
      `/console/workflows/paper-orders/${pendingOrder.order_id}/approval`,
      {
        approved_by: 'web-console-reviewer',
        approval_note: 'Approve simulated fill from the web workflow page.',
      },
      'Approve simulation',
    );
  }

  function runSimulatedFill() {
    const order = approvedOrder ?? firstOrder;
    if (!order || order.status === 'filled') {
      return;
    }
    void postWorkflowAction(
      `/console/workflows/paper-orders/${order.order_id}/fill`,
      { fill_price: 982.5 },
      'Simulate paper fill',
    );
  }

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
            const active = item.id === activePage;
            return (
              <button
                className={`nav-item ${active ? 'active' : ''}`}
                key={`${item.id}-${item.label}`}
                onClick={() => setActivePage(item.id)}
              >
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
            <p>Focused workflow pages for screeners, strategy drafts, paper approvals, and reports.</p>
          </div>
          <div className="topbar-actions">
            <StatusPill tone={loadState === 'ready' && workflowState === 'ready' ? 'good' : 'warn'}>
              {loadState === 'ready' && workflowState === 'ready' ? 'API connected' : 'Fixture snapshot'}
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

        <section className="page-strip" aria-label="Focused workflow pages">
          {pages.map((page: JsonRecord) => (
            <button
              className={`page-tab ${activePage === page.id ? 'active' : ''}`}
              key={page.id}
              onClick={() => setActivePage(page.id as PageId)}
            >
              <span>{page.label}</span>
              <small>{page.tier}</small>
            </button>
          ))}
        </section>

        {actionResult ? (
          <section className={`action-result ${actionResult.tone}`}>
            <strong>{actionResult.title}</strong>
            <span>{actionResult.message}</span>
          </section>
        ) : null}

        {activePage === 'dashboard' ? (
          <section className="main-grid">
            <section className="panel workflow-panel">
              <PanelHeading
                label="Agent workflows"
                title="Safe action launcher"
                icon={<ShieldCheck size={20} aria-hidden="true" />}
              />
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
              <PanelHeading
                label="Briefing"
                title="Market open review"
                icon={<RefreshCw size={19} aria-hidden="true" />}
              />
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
              <PanelHeading
                label="Research"
                title="Screener candidates"
                icon={<Search size={19} aria-hidden="true" />}
              />
              <CandidateTable candidates={candidates} />
            </section>

            <section className="panel evidence-panel">
              <PanelHeading
                label="Recommendation"
                title={`${recommendation.symbol ?? defaults.symbol} evidence`}
                icon={<Microscope size={19} aria-hidden="true" />}
              />
              <div className="recommendation-card">
                <StatusPill tone="info">{recommendation.stance ?? 'paper_draft_candidate'}</StatusPill>
                <strong>{recommendation.setup ?? defaults.setup}</strong>
                <p>
                  Confidence {scoreLabel(recommendation.confidence ?? 0)} with factor, history,
                  risk, ledger, and citation context joined upstream.
                </p>
              </div>
              <div className="allowed-actions">
                {(recommendation.next_allowed_actions ?? ['draft_paper_strategy', 'create_backtest_request']).map(
                  (action: string) => (
                    <span key={action}>{action}</span>
                  ),
                )}
              </div>
            </section>

            <section className="panel ledger-panel">
              <PanelHeading
                label="Paper Ledger"
                title="Approval queue"
                icon={<ClipboardCheck size={19} aria-hidden="true" />}
              />
              <ApprovalList approvals={approvals} />
              <div className="ledger-stats">
                <span>{accounting.simulated_fills ?? 0} simulated fills</span>
                <span>{formatCurrency(accounting.total_unrealized_pnl ?? 0)}</span>
              </div>
            </section>

            <section className="panel reports-panel">
              <PanelHeading
                label="Reports"
                title="Audit readiness"
                icon={<FileBarChart size={19} aria-hidden="true" />}
              />
              <ReportStack report={report} />
            </section>

            <section className="panel risk-panel">
              <PanelHeading
                label="Risk"
                title="Safety switches"
                icon={<LockKeyhole size={19} aria-hidden="true" />}
              />
              <SafetySwitches risk={risk} />
            </section>

            <section className="panel provider-panel">
              <PanelHeading
                label="Data"
                title="Provider health"
                icon={<DatabaseZap size={19} aria-hidden="true" />}
              />
              <ProviderHealth providers={providerHealth} />
            </section>
          </section>
        ) : null}

        {activePage === 'screener' ? (
          <section className="focused-grid">
            <section className="panel wide-panel">
              <PanelHeading
                label="Screener preset"
                title="Run factor-gated candidates"
                icon={<Search size={19} aria-hidden="true" />}
              />
              <div className="segmented-control" role="group" aria-label="Screener preset">
                {screenerPresets.map((preset) => (
                  <button
                    className={`segment-button ${screenerPreset === preset ? 'active' : ''}`}
                    key={preset}
                    onClick={() => setScreenerPreset(preset)}
                  >
                    {humanize(preset)}
                  </button>
                ))}
              </div>
              <CandidateTable candidates={candidates} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Evidence"
                title={`${selectedCandidate.symbol} factor stack`}
                icon={<Microscope size={19} aria-hidden="true" />}
              />
              <div className="factor-grid">
                {Object.entries(factorSummary).map(([name, value]) => {
                  const factor = value as JsonRecord;
                  return (
                    <div className="factor-card" key={name}>
                      <span>{humanize(name)}</span>
                      <strong>{factor.score == null ? 'review' : scoreLabel(Number(factor.score))}</strong>
                      <small>{factor.evidence?.[0] ?? 'Evidence available in fixture stack.'}</small>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="panel">
              <PanelHeading
                label="Patterns"
                title="Read-only pattern cards"
                icon={<BarChart3 size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {patterns.map((pattern: JsonRecord) => (
                  <div className="detail-row" key={pattern.pattern_id}>
                    <strong>{pattern.setup_type ?? pattern.pattern_id}</strong>
                    <span>{pattern.summary}</span>
                  </div>
                ))}
              </div>
            </section>
          </section>
        ) : null}

        {activePage === 'strategy-backtest' ? (
          <section className="focused-grid">
            <section className="panel wide-panel">
              <PanelHeading
                label="Strategies"
                title="Draft strategy and simulated backtest"
                icon={<Bot size={19} aria-hidden="true" />}
              />
              <div className="workflow-summary">
                <div>
                  <span>Candidate</span>
                  <strong>
                    {defaults.symbol} / {defaults.setup}
                  </strong>
                </div>
                <div>
                  <span>Window</span>
                  <strong>
                    {defaults.start_date} to {defaults.end_date}
                  </strong>
                </div>
              </div>
              <div className="command-row">
                <ActionButton busy={busyAction === 'Draft paper strategy'} onClick={runDraftStrategy}>
                  Draft paper strategy
                </ActionButton>
                <ActionButton busy={busyAction === 'Create backtest request'} onClick={runBacktestRequest}>
                  Create backtest request
                </ActionButton>
                <ActionButton
                  busy={busyAction === 'Create paper order proposal'}
                  onClick={runPaperOrderProposal}
                >
                  Create paper order proposal
                </ActionButton>
              </div>
            </section>

            <section className="panel">
              <PanelHeading
                label="Drafts"
                title="Strategy history"
                icon={<ListChecks size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {strategyDrafts.length ? (
                  strategyDrafts.map((draft: JsonRecord) => (
                    <div className="detail-row" key={draft.strategy_id}>
                      <strong>{draft.strategy_id}</strong>
                      <span>{draft.rationale}</span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">No strategy drafts yet</div>
                )}
              </div>
            </section>

            <section className="panel">
              <PanelHeading
                label="Backtests"
                title="Simulation history"
                icon={<FlaskConical size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {backtestRequests.length ? (
                  backtestRequests.map((request: JsonRecord) => (
                    <div className="detail-row" key={request.request_id}>
                      <strong>{request.request_id}</strong>
                      <span>
                        {request.start_date} to {request.end_date} / {request.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">No backtest requests yet</div>
                )}
              </div>
              {latestBacktest.status === 'success' ? (
                <div className="result-band">
                  <span>Latest return</span>
                  <strong>{latestBacktest.backtest_result?.metrics?.total_return_pct ?? 0}%</strong>
                </div>
              ) : null}
            </section>
          </section>
        ) : null}

        {activePage === 'paper-approvals' ? (
          <section className="focused-grid">
            <section className="panel wide-panel">
              <PanelHeading
                label="Paper Ledger"
                title="Approvals and simulated fills"
                icon={<ClipboardCheck size={19} aria-hidden="true" />}
              />
              <div className="command-row">
                <ActionButton
                  disabled={!pendingOrder}
                  busy={busyAction === 'Approve simulation'}
                  onClick={runApproval}
                >
                  Approve simulation
                </ActionButton>
                <ActionButton
                  disabled={!approvedOrder || approvedOrder.status === 'filled'}
                  busy={busyAction === 'Simulate paper fill'}
                  onClick={runSimulatedFill}
                >
                  Simulate paper fill
                </ActionButton>
              </div>
              <ApprovalList approvals={approvals} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Orders"
                title="Paper proposals"
                icon={<ListChecks size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {paperOrders.length ? (
                  paperOrders.map((order: JsonRecord) => (
                    <div className="detail-row" key={order.order_id}>
                      <strong>{order.symbol}</strong>
                      <span>
                        {order.side} {order.quantity} / {order.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">No paper order proposals yet</div>
                )}
              </div>
            </section>

            <section className="panel">
              <PanelHeading
                label="Accounting"
                title="Positions and fills"
                icon={<WalletCards size={19} aria-hidden="true" />}
              />
              <div className="ledger-stats">
                <span>{paperPositions.length} paper positions</span>
                <span>{paperFills.length} simulated fills</span>
              </div>
              <div className="result-band">
                <span>Unrealized P&L</span>
                <strong>{formatCurrency(accounting.total_unrealized_pnl ?? 0)}</strong>
              </div>
            </section>
          </section>
        ) : null}

        {activePage === 'reports' ? (
          <section className="focused-grid">
            <section className="panel wide-panel">
              <PanelHeading
                label="Reports"
                title="Paper trading review"
                icon={<FileBarChart size={19} aria-hidden="true" />}
              />
              <ReportStack report={report} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Audit"
                title="Redacted export rows"
                icon={<ClipboardCheck size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {auditEvents.length ? (
                  auditEvents.slice(0, 5).map((event: JsonRecord) => (
                    <div className="detail-row" key={event.event_id}>
                      <strong>{event.event_type}</strong>
                      <span>{event.message}</span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">No audit events yet</div>
                )}
              </div>
            </section>
          </section>
        ) : null}

        {activePage === 'settings' ? (
          <section className="focused-grid">
            <section className="panel wide-panel">
              <PanelHeading
                label="Provider settings"
                title="Provider health"
                icon={<DatabaseZap size={19} aria-hidden="true" />}
              />
              <ProviderHealth providers={providerHealth} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Catalog"
                title="Configured adapters"
                icon={<Settings size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {providers.length ? (
                  providers.slice(0, 8).map((provider: JsonRecord) => (
                    <div className="detail-row" key={provider.provider_id ?? provider.name}>
                      <strong>{provider.provider_id ?? provider.name}</strong>
                      <span>{provider.kind ?? provider.status ?? 'fixture'}</span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">Fixture providers active</div>
                )}
              </div>
            </section>

            <section className="panel">
              <PanelHeading
                label="Import validation"
                title="Configured files"
                icon={<AlertTriangle size={19} aria-hidden="true" />}
              />
              <ProviderImportValidation validation={importValidation} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Risk"
                title="Safety switches"
                icon={<LockKeyhole size={19} aria-hidden="true" />}
              />
              <SafetySwitches risk={risk} />
            </section>
          </section>
        ) : null}
      </section>
    </main>
  );
}

function CandidateTable({ candidates }: { candidates: JsonRecord[] }) {
  return (
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
  );
}

function ApprovalList({ approvals }: { approvals: JsonRecord[] }) {
  if (!approvals.length) {
    return <div className="empty-state">No pending approvals</div>;
  }
  return (
    <>
      {approvals.slice(0, 4).map((approval: JsonRecord) => (
        <div className="approval-row" key={approval.approval_id ?? approval.entity_id}>
          <AlertTriangle size={17} aria-hidden="true" />
          <div>
            <strong>{approval.action_type ?? approval.requested_action ?? 'simulate_paper_fill'}</strong>
            <span>{approval.related_id ?? approval.entity_id ?? approval.approval_id}</span>
          </div>
          <StatusPill tone={approval.status === 'approved' ? 'good' : 'warn'}>
            {approval.status ?? 'pending'}
          </StatusPill>
        </div>
      ))}
    </>
  );
}

function ReportStack({ report }: { report: JsonRecord }) {
  return (
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
  );
}

function SafetySwitches({ risk }: { risk: JsonRecord }) {
  return (
    <>
      <div className="switch-grid">
        <StatusPill tone="danger">Live trading blocked</StatusPill>
        <StatusPill tone="good">Paper enabled</StatusPill>
        <StatusPill tone="warn">Approval required</StatusPill>
        <StatusPill tone="danger">Credential access forbidden</StatusPill>
      </div>
      <ul className="review-list compact">
        {(risk.recommended_pauses ?? []).slice(0, 2).map((pause: string) => (
          <li key={pause}>
            <AlertTriangle size={15} aria-hidden="true" />
            <span>{pause}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function ProviderHealth({ providers }: { providers: JsonRecord[] }) {
  return (
    <div className="provider-list">
      {providers.slice(0, 8).map((provider: JsonRecord) => (
        <div className="provider-row" key={provider.provider_id ?? provider.name}>
          <span>{provider.provider_id ?? provider.name}</span>
          <StatusPill tone={provider.status === 'available' ? 'good' : 'warn'}>
            {provider.status ?? provider.mode ?? 'fixture'}
          </StatusPill>
        </div>
      ))}
    </div>
  );
}

function ProviderImportValidation({ validation }: { validation: JsonRecord }) {
  const summary = validation.summary ?? {};
  const validations = validation.validations ?? [];
  const needsAttention = Number(summary.needs_attention ?? 0);
  return (
    <div className="validation-stack">
      <div className="result-band">
        <span>Needs attention</span>
        <strong>{needsAttention}</strong>
      </div>
      <div className="detail-list">
        {validations.length ? (
          validations.slice(0, 6).map((item: JsonRecord) => (
            <div className="validation-row" key={item.provider_id}>
              <div>
                <strong>{item.provider_id}</strong>
                <span>{item.message}</span>
              </div>
              <StatusPill
                tone={
                  item.status === 'valid'
                    ? 'good'
                    : item.status === 'not_configured'
                      ? 'neutral'
                      : 'warn'
                }
              >
                {humanize(item.status ?? 'unknown')}
              </StatusPill>
            </div>
          ))
        ) : (
          <div className="empty-state">Fixture providers active</div>
        )}
      </div>
    </div>
  );
}

export default App;
