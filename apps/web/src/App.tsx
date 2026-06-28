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
      run_summary: {
        provider_import_reconciliation: {
          in_sync: 0,
          pending_refresh: 0,
          source_changed: 0,
          store_mismatch: 0,
          needs_attention: 0,
          provider_statuses: {},
        },
      },
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
      risk_gates: [
        { name: 'provider_import_reconciliation', status: 'pass', reason: 'Fixture mode has no active import reconciliation issues.' },
      ],
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
        readiness_preflight_count: 0,
      },
      sections: {
        paper_order_readiness: {
          schema_version: 'paper-order-readiness-report/v1',
          preflight_count: 0,
          ready_for_approval_count: 0,
          blocked_count: 0,
          latest_preflight: null,
          preflights: [],
        },
      },
      audit_export: {
        schema_version: 'paper-audit-export/v1',
        redaction_status: 'redacted',
      },
    },
  },
};

const fallbackProviderProfiles: JsonRecord[] = [
  {
    profile_id: 'profile-configured-market-data',
    provider_id: 'configured_market_data',
    kind: 'market_data',
    display_name: 'Configured Market Data',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_MARKET_DATA_PROVIDER', 'PORTFOLIO_MARKET_DATA_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_MARKET_DATA_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
  {
    profile_id: 'profile-configured-universe',
    provider_id: 'configured_universe',
    kind: 'universe',
    display_name: 'Configured Universe',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_UNIVERSE_PROVIDER', 'PORTFOLIO_UNIVERSE_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_UNIVERSE_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
  {
    profile_id: 'profile-configured-fundamentals',
    provider_id: 'configured_fundamentals',
    kind: 'fundamentals',
    display_name: 'Configured Fundamentals',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_FUNDAMENTALS_PROVIDER', 'PORTFOLIO_FUNDAMENTALS_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_FUNDAMENTALS_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
  {
    profile_id: 'profile-configured-sentiment',
    provider_id: 'configured_sentiment',
    kind: 'sentiment',
    display_name: 'Configured Sentiment',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_SENTIMENT_PROVIDER', 'PORTFOLIO_SENTIMENT_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_SENTIMENT_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
  {
    profile_id: 'profile-configured-volatility',
    provider_id: 'configured_volatility',
    kind: 'volatility',
    display_name: 'Configured Volatility',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_VOLATILITY_PROVIDER', 'PORTFOLIO_VOLATILITY_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_VOLATILITY_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
  {
    profile_id: 'profile-configured-macro',
    provider_id: 'configured_macro',
    kind: 'macro',
    display_name: 'Configured Macro',
    configured: false,
    provider_mode: 'fixture',
    required_env: ['PORTFOLIO_MACRO_PROVIDER', 'PORTFOLIO_MACRO_JSON_PATH'],
    missing_env: [],
    path_env: 'PORTFOLIO_MACRO_JSON_PATH',
    source_label: 'fixture_provider',
    last_validation_status: 'not_configured',
  },
];

const fallbackTemplateByKind: JsonRecord = {
  market_data: {
    snapshots: [
      {
        symbol: 'SAMPLE_EQTY',
        as_of: '2026-06-22',
        bars: [
          {
            date: '2026-06-22',
            open: 100,
            high: 104,
            low: 99,
            close: 103,
            volume: 123000,
          },
        ],
        metrics: { atr_pct: 2.5, median_turnover_cr: 8.1, roc20_pct: 7.2, rsi14: 59.4 },
      },
    ],
  },
  universe: {
    universes: [
      {
        universe_id: 'sample_universe',
        name: 'Sample Universe',
        as_of: '2026-06-22',
        symbols: ['SAMPLE_EQTY'],
      },
    ],
  },
  fundamentals: {
    fundamentals: [
      {
        symbol: 'SAMPLE_EQTY',
        as_of: '2026-06-22',
        metrics: { quality_score: 0.65, value_score: 0.55, growth_score: 0.61 },
      },
    ],
  },
  sentiment: {
    sentiment: [
      {
        symbol: 'SAMPLE_EQTY',
        as_of: '2026-06-22',
        metrics: { news_score: 0.57, investor_score: 0.55, contradiction_score: 0.25 },
      },
    ],
  },
  volatility: {
    volatility: [
      {
        symbol: 'SAMPLE_EQTY',
        as_of: '2026-06-22',
        metrics: { india_vix: 15.2, vix_change_pct: 1.4, regime_score: 0.58 },
      },
    ],
  },
  macro: {
    macro: [
      {
        symbol: 'SAMPLE_EQTY',
        as_of: '2026-06-22',
        metrics: { market_regime_score: 0.62, breadth_score: 0.57, event_risk_score: 0.31 },
      },
    ],
  },
};

const fallbackProviderSourceTemplates: JsonRecord[] = fallbackProviderProfiles.map((profile) => ({
  provider_id: profile.provider_id,
  kind: profile.kind,
  display_name: profile.display_name,
  provider_mode: 'json_file',
  required_env: profile.required_env,
  path_env: profile.path_env,
  accepted_wrappers:
    profile.kind === 'universe'
      ? ['list', 'universes', 'single_object_with_universe_id']
      : [
          'list',
          profile.kind === 'market_data' ? 'snapshots' : profile.kind,
          'single_object_with_symbol',
        ],
  required_fields:
    profile.kind === 'market_data'
      ? ['symbol', 'bars[].date', 'bars[].open', 'bars[].high', 'bars[].low', 'bars[].close', 'bars[].volume']
      : profile.kind === 'universe'
        ? ['universe_id', 'symbols[]']
        : ['symbol', 'metrics'],
  optional_fields:
    profile.kind === 'market_data'
      ? ['as_of', 'latest_close', 'metrics', 'notes', 'source']
      : profile.kind === 'universe'
        ? ['name', 'as_of', 'notes', 'source']
        : ['as_of', 'notes', 'source'],
  template_json: fallbackTemplateByKind[profile.kind],
}));

const fallbackProviderSourceOnboarding: JsonRecord[] = fallbackProviderProfiles.map((profile) => {
  const template = fallbackProviderSourceTemplates.find(
    (item) => item.provider_id === profile.provider_id,
  ) ?? {};
  return {
    provider_id: profile.provider_id,
    kind: profile.kind,
    display_name: profile.display_name,
    provider_mode: profile.provider_mode,
    setup_state: 'optional_fixture_mode',
    recommended_next_step: 'configure_provider_env',
    operator_steps: [
      'Use fixture mode or configure JSON source env keys.',
      'Create JSON from the matching template.',
      'Validate imports before refresh.',
    ],
    required_env: profile.required_env,
    missing_env: profile.missing_env,
    template: {
      path_env: profile.path_env,
      accepted_wrappers: template.accepted_wrappers ?? [],
      required_fields: template.required_fields ?? [],
      optional_fields: template.optional_fields ?? [],
      template_json: template.template_json ?? {},
    },
    validation: {
      status: 'not_configured',
      configured: false,
      message: 'Fixture provider remains active.',
      payload_count: null,
      sample_identifiers: [],
    },
    profile: {
      source_label: profile.source_label,
      last_validation_status: profile.last_validation_status,
      payload_count: null,
      sample_identifiers: [],
    },
    refresh_readiness: {
      status: 'not_configured',
      needs_refresh: false,
      latest_status: 'none',
      latest_job_id: '',
      retry_after_seconds: 0,
      next_attempt_at: '',
    },
    safe_actions: [
      {
        label: 'Review JSON template',
        tool: 'list_provider_source_templates',
        tier: 'read_only',
        enabled: true,
      },
      {
        label: 'Validate configured import',
        tool: 'validate_data_provider_imports',
        tier: 'read_only',
        enabled: true,
      },
      {
        label: 'Refresh provider profile',
        tool: 'refresh_provider_import_profile',
        tier: 'draft_only',
        enabled: false,
      },
    ],
  };
});

const fallbackProviderImportPreviews: JsonRecord[] = fallbackProviderProfiles.map((profile) => ({
  preview_id: `provider-import-preview-${String(profile.provider_id).replace(/_/g, '-')}`,
  provider_id: profile.provider_id,
  kind: profile.kind,
  display_name: profile.display_name,
  status: 'skipped',
  provider_mode: profile.provider_mode,
  configured: false,
  validation_status: 'not_configured',
  source_label: profile.source_label,
  target_store: 'none',
  payload_count: null,
  normalized_count: 0,
  skipped_count: 0,
  would_write: false,
  sample_identifiers: [],
  warnings: ['Fixture provider remains active; no configured import would run.'],
  safe_actions: [
    {
      label: 'Refresh provider profile',
      tool: 'refresh_provider_import_profile',
      tier: 'draft_only',
      enabled: false,
    },
    {
      label: 'Validate configured import',
      tool: 'validate_data_provider_imports',
      tier: 'read_only',
      enabled: true,
    },
  ],
}));

const fallbackProviderImportReconciliation: JsonRecord[] = fallbackProviderImportPreviews.map((preview) => ({
  reconciliation_id: `provider-import-reconciliation-${String(preview.provider_id).replace(/_/g, '-')}`,
  provider_id: preview.provider_id,
  kind: preview.kind,
  display_name: preview.display_name,
  configured: preview.configured,
  provider_mode: preview.provider_mode,
  source_label: preview.source_label,
  reconciliation_status: 'not_configured',
  preview: {
    status: preview.status,
    validation_status: preview.validation_status,
    target_store: preview.target_store,
    normalized_count: preview.normalized_count,
    would_write: preview.would_write,
    sample_identifiers: preview.sample_identifiers,
  },
  latest_job: {
    job_id: '',
    status: 'none',
    validation_status: 'none',
    imported_count: 0,
    skipped_count: 0,
    target_store: 'none',
    completed_at: '',
  },
  store: {
    target_store: preview.target_store,
    stored_count: 0,
  },
  deltas: {
    preview_minus_store: 0,
    latest_job_minus_store: 0,
  },
  warnings: [],
  next_step: 'configure_provider_env',
  safe_actions: [
    {
      label: 'Review dry-run preview',
      tool: 'list_provider_import_previews',
      tier: 'read_only',
      enabled: true,
    },
    {
      label: 'Refresh provider profile',
      tool: 'refresh_provider_import_profile',
      tier: 'draft_only',
      enabled: false,
    },
  ],
}));

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
    provider_profiles: {
      status: 'success',
      summary: { total: 6, configured: 0, needs_attention: 0 },
      profiles: fallbackProviderProfiles,
    },
    provider_source_templates: {
      status: 'success',
      template_version: 'configured-provider-json/v1',
      provider_mode_options: ['fixture', 'json_file'],
      summary: { total: 6, market_data: 1, context: 5 },
      templates: fallbackProviderSourceTemplates,
    },
    provider_source_onboarding: {
      status: 'success',
      summary: { total: 6, configured: 0, ready_for_refresh: 0, ready: 0, needs_setup: 0 },
      onboarding_cards: fallbackProviderSourceOnboarding,
    },
    provider_import_previews: {
      status: 'success',
      summary: { total: 6, configured: 0, would_write: 0, normalized_count: 0, needs_attention: 0 },
      previews: fallbackProviderImportPreviews,
      next_step: 'review_dry_run_before_refresh',
    },
    provider_import_reconciliation: {
      status: 'success',
      summary: { total: 6, in_sync: 0, pending_refresh: 0, source_changed: 0, store_mismatch: 0, needs_attention: 0 },
      reconciliations: fallbackProviderImportReconciliation,
      next_step: 'review_reconciliation_before_configured_screening',
    },
    provider_import_jobs: {
      status: 'success',
      summary: { total: 0, needs_attention: 0 },
      import_jobs: [],
    },
    provider_refresh_readiness: {
      status: 'success',
      summary: { total: 6, ready: 0, stale: 0, needs_attention: 0 },
      readiness: [],
    },
    provider_refresh_actions: {
      run_schedule: { tier: 'draft_only' },
      read_readiness: { tier: 'read_only' },
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

function paperPreflightTone(status: string): 'good' | 'warn' | 'danger' | 'info' | 'neutral' {
  if (status === 'ready_for_approval' || status === 'pass') {
    return 'good';
  }
  if (status === 'blocked' || status === 'fail') {
    return 'danger';
  }
  if (status === 'review' || status === 'pending') {
    return 'warn';
  }
  return status ? 'info' : 'neutral';
}

function gateByName(preflight: JsonRecord, name: string): JsonRecord {
  return (
    (preflight.risk_gates ?? []).find((gate: JsonRecord) => gate.name === name) ?? {
      name,
      status: 'unknown',
      reason: 'Gate was not recorded.',
    }
  );
}

function submittedStrategyGate(preflight: JsonRecord): JsonRecord {
  return preflight.submitted_strategy_gate ?? gateByName(preflight, 'submitted_strategy');
}

function latestReportPreflight(report: JsonRecord): JsonRecord | null {
  return report.sections?.paper_order_readiness?.latest_preflight ?? null;
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

function pickScreenerRun(payload: JsonRecord, fallback: JsonRecord = {}) {
  return (
    payload.screener?.run?.screener_run ??
    payload.screener?.run?.result ??
    payload.screener?.screener_run ??
    payload.screener?.result ??
    fallback.screener?.screener_run ??
    {}
  );
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

function ImportGateSummary({
  summary,
  gate,
  compact = false,
}: {
  summary: JsonRecord;
  gate?: JsonRecord;
  compact?: boolean;
}) {
  const sourceChanged = Number(summary.source_changed ?? 0);
  const storeMismatch = Number(summary.store_mismatch ?? 0);
  const needsAttention = Number(summary.needs_attention ?? 0);
  const pendingRefresh = Number(summary.pending_refresh ?? 0);
  const blocked = sourceChanged + storeMismatch + needsAttention;
  const tone = blocked > 0 ? 'danger' : pendingRefresh > 0 ? 'warn' : 'good';
  return (
    <div className={`import-gate ${compact ? 'compact' : ''}`}>
      <div className="import-gate-title">
        {tone === 'good' ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : (
          <AlertTriangle size={16} aria-hidden="true" />
        )}
        <div>
          <span>Import gate</span>
          <strong>{gate?.status ? humanize(String(gate.status)) : 'review'}</strong>
        </div>
      </div>
      <div className="import-gate-stats">
        <div>
          <span>In sync</span>
          <strong>{summary.in_sync ?? 0}</strong>
        </div>
        <div>
          <span>Source changed</span>
          <strong>{sourceChanged}</strong>
        </div>
        <div>
          <span>Store mismatch</span>
          <strong>{storeMismatch}</strong>
        </div>
      </div>
      <StatusPill tone={tone}>{blocked > 0 ? 'Paper gate blocked' : 'Paper gate ready'}</StatusPill>
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
  const screenerRun = pickScreenerRun(workflows, overview);
  const importGateSummary = screenerRun.run_summary?.provider_import_reconciliation ?? {
    in_sync: 0,
    pending_refresh: 0,
    source_changed: 0,
    store_mismatch: 0,
    needs_attention: 0,
    provider_statuses: {},
  };
  const recommendationImportGate = (recommendation.risk_gates ?? []).find(
    (gate: JsonRecord) => gate.name === 'provider_import_reconciliation',
  );
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
  const providerProfiles =
    workflows.settings?.provider_profiles?.profiles ??
    fallbackWorkflows.settings.provider_profiles.profiles;
  const providerSourceTemplates =
    workflows.settings?.provider_source_templates ??
    fallbackWorkflows.settings.provider_source_templates;
  const providerSourceOnboarding =
    workflows.settings?.provider_source_onboarding ??
    fallbackWorkflows.settings.provider_source_onboarding;
  const providerImportPreviews =
    workflows.settings?.provider_import_previews ??
    fallbackWorkflows.settings.provider_import_previews;
  const providerImportReconciliation =
    workflows.settings?.provider_import_reconciliation ??
    fallbackWorkflows.settings.provider_import_reconciliation;
  const providerImportJobs =
    workflows.settings?.provider_import_jobs?.import_jobs ??
    fallbackWorkflows.settings.provider_import_jobs.import_jobs;
  const providerRefreshReadiness =
    workflows.settings?.provider_refresh_readiness ??
    fallbackWorkflows.settings.provider_refresh_readiness;
  const providerRefreshActions =
    workflows.settings?.provider_refresh_actions ??
    fallbackWorkflows.settings.provider_refresh_actions;
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
      const action = payload.action ?? {};
      const preflight = action.readiness_preflight ?? action.paper_order?.readiness_preflight;
      const actionStatus = String(action.status ?? 'completed');
      const preflightStatus = String(preflight?.status ?? '');
      const blockingReasons = preflight?.blocking_reasons ?? [];
      const isBlocked = actionStatus === 'blocked' || preflightStatus === 'blocked';
      setActionResult({
        tone: isBlocked ? 'warn' : 'good',
        title: label,
        message: preflight
          ? `${humanize(actionStatus)} via ${action.policy?.tier ?? 'policy'} action / preflight ${humanize(preflightStatus)}`
          : `${actionStatus} via ${action.policy?.tier ?? 'policy'} action`,
        preflight,
        blockingReasons,
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
    void postWorkflowAction(
      '/console/workflows/paper-orders',
      {
        strategy_id: latestStrategyId,
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

  function runProviderProfileRefresh(providerId: string) {
    void postWorkflowAction(
      `/console/workflows/provider-profiles/${providerId}/refresh`,
      {},
      'Refresh profile',
    );
  }

  function runProviderRefreshSchedule() {
    void postWorkflowAction(
      '/console/workflows/provider-profiles/refresh-schedule',
      {},
      'Run full refresh',
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
            <div>
              <strong>{actionResult.title}</strong>
              <span>{actionResult.message}</span>
            </div>
            {actionResult.preflight ? (
              <PaperPreflightSummary compact preflight={actionResult.preflight} />
            ) : null}
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
              <ImportGateSummary summary={importGateSummary} gate={recommendationImportGate} />
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
              <ImportGateSummary summary={importGateSummary} gate={recommendationImportGate} compact />
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
              <ApprovalList approvals={approvals} orders={paperOrders} />
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
              <ImportGateSummary summary={importGateSummary} gate={recommendationImportGate} />
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
              <ApprovalList approvals={approvals} orders={paperOrders} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Orders"
                title="Paper proposals"
                icon={<ListChecks size={19} aria-hidden="true" />}
              />
              <div className="detail-list">
                {paperOrders.length ? (
                  <PaperOrderList orders={paperOrders} />
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

            <section className="panel wide-panel onboarding-panel">
              <PanelHeading
                label="Onboarding flow"
                title="Configured source path"
                icon={<ListChecks size={19} aria-hidden="true" />}
              />
              <ProviderSourceOnboarding onboarding={providerSourceOnboarding} />
            </section>

            <section className="panel wide-panel preview-panel">
              <PanelHeading
                label="Dry-run preview"
                title="Configured import impact"
                icon={<Gauge size={19} aria-hidden="true" />}
              />
              <ProviderImportPreviews previews={providerImportPreviews} />
            </section>

            <section className="panel wide-panel reconciliation-panel">
              <PanelHeading
                label="Import reconciliation"
                title="Configured store alignment"
                icon={<CheckCircle2 size={19} aria-hidden="true" />}
              />
              <ProviderImportReconciliation reconciliation={providerImportReconciliation} />
            </section>

            <section className="panel wide-panel source-panel">
              <PanelHeading
                label="Source setup"
                title="Configured source management"
                icon={<Settings size={19} aria-hidden="true" />}
              />
              <ProviderSourceSetup profiles={providerProfiles} />
            </section>

            <section className="panel wide-panel template-panel">
              <PanelHeading
                label="Schema guidance"
                title="JSON templates"
                icon={<ClipboardCheck size={19} aria-hidden="true" />}
              />
              <ProviderSourceTemplates guidance={providerSourceTemplates} />
            </section>

            <section className="panel">
              <PanelHeading
                label="Provider profiles"
                title="Last validation"
                icon={<ListChecks size={19} aria-hidden="true" />}
              />
              <ProviderProfiles
                busyAction={busyAction}
                profiles={providerProfiles}
                onRefresh={runProviderProfileRefresh}
              />
            </section>

            <section className="panel">
              <PanelHeading
                label="Refresh readiness"
                title="Backoff state"
                icon={<RefreshCw size={19} aria-hidden="true" />}
              />
              <ProviderRefreshReadiness
                actionPolicy={providerRefreshActions.run_schedule}
                busyAction={busyAction}
                readiness={providerRefreshReadiness}
                onRunSchedule={runProviderRefreshSchedule}
              />
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
                label="Import jobs"
                title="Refresh history"
                icon={<RefreshCw size={19} aria-hidden="true" />}
              />
              <ProviderImportJobs jobs={providerImportJobs} />
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

function ApprovalList({ approvals, orders }: { approvals: JsonRecord[]; orders: JsonRecord[] }) {
  if (!approvals.length) {
    return <div className="empty-state">No pending approvals</div>;
  }
  return (
    <>
      {approvals.slice(0, 4).map((approval: JsonRecord) => {
        const relatedOrder = orders.find((order: JsonRecord) => order.order_id === approval.related_id);
        const preflight = relatedOrder?.readiness_preflight;
        return (
          <div className="approval-card" key={approval.approval_id ?? approval.entity_id}>
            <div className="approval-row">
              <AlertTriangle size={17} aria-hidden="true" />
              <div>
                <strong>{approval.action_type ?? approval.requested_action ?? 'simulate_paper_fill'}</strong>
                <span>{approval.related_id ?? approval.entity_id ?? approval.approval_id}</span>
              </div>
              <StatusPill tone={approval.status === 'approved' ? 'good' : 'warn'}>
                {approval.status ?? 'pending'}
              </StatusPill>
            </div>
            {preflight ? <PaperPreflightSummary compact preflight={preflight} /> : null}
          </div>
        );
      })}
    </>
  );
}

function PaperOrderList({ orders }: { orders: JsonRecord[] }) {
  return (
    <>
      {orders.map((order: JsonRecord) => (
        <div className="paper-order-card" key={order.order_id}>
          <div className="detail-row">
            <strong>{order.symbol}</strong>
            <span>
              {order.side} {order.quantity} / {order.status}
            </span>
          </div>
          <PaperPreflightSummary compact preflight={order.readiness_preflight} />
        </div>
      ))}
    </>
  );
}

function PaperPreflightSummary({
  preflight,
  compact = false,
}: {
  preflight: JsonRecord | null | undefined;
  compact?: boolean;
}) {
  if (!preflight) {
    return <div className="empty-state">No readiness preflight captured</div>;
  }
  const importStatus = String(preflight.provider_import_reconciliation?.status ?? 'unknown');
  const refreshStatus = String(preflight.provider_refresh_readiness?.status ?? 'unknown');
  const strategyGate = submittedStrategyGate(preflight);
  const approval = String(preflight.required_approval ?? 'human');
  const policy = preflight.paper_only_policy ?? {};
  const blockingReasons = Array.isArray(preflight.blocking_reasons)
    ? preflight.blocking_reasons
    : [];
  return (
    <div className={`paper-preflight ${compact ? 'compact' : ''}`} aria-label="Readiness preflight">
      <div className="preflight-head">
        <span>Readiness preflight</span>
        <StatusPill tone={paperPreflightTone(String(preflight.status ?? 'unknown'))}>
          {humanize(String(preflight.status ?? 'unknown'))}
        </StatusPill>
      </div>
      <div className="preflight-grid">
        <div>
          <span>Provider reconciliation</span>
          <strong>{humanize(importStatus)}</strong>
        </div>
        <div>
          <span>Provider refresh</span>
          <strong>{humanize(refreshStatus)}</strong>
        </div>
        <div>
          <span>Submitted strategy</span>
          <strong>{humanize(String(strategyGate.status ?? 'unknown'))}</strong>
        </div>
        <div>
          <span>Human approval</span>
          <strong>{humanize(approval)}</strong>
        </div>
      </div>
      <div className="preflight-policy">
        <span>Paper policy</span>
        <strong>
          live {policy.live_trading ?? 'disabled'} / fills {policy.simulated_fills ?? 'approval_required'}
        </strong>
      </div>
      <div className="preflight-blockers">
        <strong>Blocking reasons</strong>
        {blockingReasons.length ? (
          <ul>
            {blockingReasons.slice(0, 3).map((reason: string) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <span>None</span>
        )}
      </div>
    </div>
  );
}

function ReportStack({ report }: { report: JsonRecord }) {
  const latestPreflight = latestReportPreflight(report);
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
      <div>
        <span>Readiness preflights</span>
        <strong>{report.summary?.readiness_preflight_count ?? 0}</strong>
      </div>
      <PaperPreflightSummary preflight={latestPreflight} />
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

function setupGapLabels(profile: JsonRecord) {
  const missingEnv = profile.missing_env ?? [];
  if (missingEnv.length) {
    return missingEnv;
  }
  if (profile.last_validation_status === 'valid') {
    return ['Ready'];
  }
  if (profile.last_validation_status === 'unsupported_provider') {
    return ['Use fixture or json_file mode'];
  }
  if (profile.last_validation_status === 'not_configured') {
    return ['Optional: configure env keys to enable'];
  }
  return [humanize(profile.last_validation_status ?? 'review_required')];
}

function ProviderSourceSetup({ profiles }: { profiles: JsonRecord[] }) {
  if (!profiles.length) {
    return <div className="empty-state">Fixture providers active</div>;
  }
  const configuredCount = profiles.filter((profile: JsonRecord) => profile.configured).length;
  const gapCount = profiles.filter((profile: JsonRecord) => (profile.missing_env ?? []).length > 0).length;
  const requiredKeyCount = profiles.reduce(
    (total: number, profile: JsonRecord) => total + (profile.required_env?.length ?? 0),
    0,
  );
  return (
    <div className="source-setup-stack">
      <div className="source-summary" aria-label="Configured provider source setup summary">
        <div>
          <span>Configured sources</span>
          <strong>{configuredCount}</strong>
        </div>
        <div>
          <span>Required env keys</span>
          <strong>{requiredKeyCount}</strong>
        </div>
        <div>
          <span>Setup gaps</span>
          <strong>{gapCount}</strong>
        </div>
      </div>
      <div className="source-list">
        {profiles.slice(0, 6).map((profile: JsonRecord) => (
          <div className="source-row" key={profile.profile_id ?? profile.provider_id}>
            <div className="source-main">
              <strong>{profile.display_name ?? profile.provider_id}</strong>
              <span>{profile.provider_id}</span>
              <small>{profile.source_label ?? 'fixture_provider'}</small>
            </div>
            <div className="source-fields">
              <div>
                <span>Active mode</span>
                <StatusPill tone={profile.provider_mode === 'json_file' ? 'info' : 'neutral'}>
                  {humanize(profile.provider_mode ?? 'fixture')}
                </StatusPill>
              </div>
              <div>
                <span>Required env keys</span>
                <div className="env-chip-list">
                  {(profile.required_env ?? []).map((envKey: string) => (
                    <code key={`${profile.provider_id}-${envKey}`}>{envKey}</code>
                  ))}
                </div>
              </div>
              <div>
                <span>Setup gaps</span>
                <div className="setup-gap-list">
                  {setupGapLabels(profile).map((gap: string) => (
                    <StatusPill
                      key={`${profile.provider_id}-${gap}`}
                      tone={
                        profile.missing_env?.includes(gap)
                          ? 'warn'
                          : profile.last_validation_status === 'valid'
                            ? 'good'
                            : 'neutral'
                      }
                    >
                      {gap}
                    </StatusPill>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProviderSourceTemplates({ guidance }: { guidance: JsonRecord }) {
  const templates = guidance.templates ?? [];
  if (!templates.length) {
    return <div className="empty-state">No source templates available</div>;
  }
  return (
    <div className="template-guidance-stack">
      <div className="template-summary" aria-label="Configured provider schema guidance summary">
        <div>
          <span>Template version</span>
          <strong>{guidance.template_version ?? 'configured-provider-json/v1'}</strong>
        </div>
        <div>
          <span>Provider modes</span>
          <strong>{(guidance.provider_mode_options ?? ['fixture', 'json_file']).join(' / ')}</strong>
        </div>
        <div>
          <span>Template count</span>
          <strong>{guidance.summary?.total ?? templates.length}</strong>
        </div>
      </div>
      <div className="template-list">
        {templates.slice(0, 6).map((template: JsonRecord) => (
          <div className="template-row" key={template.provider_id}>
            <div className="template-main">
              <strong>{template.display_name ?? template.provider_id}</strong>
              <span>{template.path_env ?? template.kind}</span>
              <small>JSON template for {humanize(template.kind ?? 'provider')}</small>
            </div>
            <div className="template-fields">
              <div>
                <span>Accepted wrappers</span>
                <div className="env-chip-list">
                  {(template.accepted_wrappers ?? []).map((wrapper: string) => (
                    <code key={`${template.provider_id}-${wrapper}`}>{wrapper}</code>
                  ))}
                </div>
              </div>
              <div>
                <span>Required fields</span>
                <div className="env-chip-list">
                  {(template.required_fields ?? []).slice(0, 7).map((field: string) => (
                    <code key={`${template.provider_id}-${field}`}>{field}</code>
                  ))}
                </div>
              </div>
              <div>
                <span>JSON template</span>
                <pre>{JSON.stringify(template.template_json ?? {}, null, 2)}</pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProviderSourceOnboarding({ onboarding }: { onboarding: JsonRecord }) {
  const cards = onboarding.onboarding_cards ?? [];
  const summary = onboarding.summary ?? {};
  if (!cards.length) {
    return <div className="empty-state">No configured source onboarding available</div>;
  }
  return (
    <div className="onboarding-stack">
      <div className="onboarding-summary" aria-label="Configured provider onboarding summary">
        <div>
          <span>Configured</span>
          <strong>{summary.configured ?? 0}</strong>
        </div>
        <div>
          <span>Ready to refresh</span>
          <strong>{summary.ready_for_refresh ?? 0}</strong>
        </div>
        <div>
          <span>Needs setup</span>
          <strong>{summary.needs_setup ?? 0}</strong>
        </div>
      </div>
      <div className="onboarding-list">
        {cards.slice(0, 6).map((card: JsonRecord) => (
          <div className="onboarding-row" key={card.provider_id}>
            <div className="onboarding-main">
              <strong>{card.display_name ?? card.provider_id}</strong>
              <span>{card.template?.path_env ?? card.kind}</span>
              <StatusPill tone={readinessTone(card.refresh_readiness?.status ?? 'unknown')}>
                {humanize(card.setup_state ?? 'review_required')}
              </StatusPill>
            </div>
            <div className="onboarding-status-grid">
              <div>
                <span>Validation</span>
                <StatusPill
                  tone={
                    card.validation?.status === 'valid'
                      ? 'good'
                      : card.validation?.status === 'not_configured'
                        ? 'neutral'
                        : 'warn'
                  }
                >
                  {humanize(card.validation?.status ?? 'unknown')}
                </StatusPill>
              </div>
              <div>
                <span>Refresh readiness</span>
                <StatusPill tone={readinessTone(card.refresh_readiness?.status ?? 'unknown')}>
                  {humanize(card.refresh_readiness?.status ?? 'unknown')}
                </StatusPill>
              </div>
              <div>
                <span>Safe next step</span>
                <strong>{humanize(card.recommended_next_step ?? 'review_provider_state')}</strong>
              </div>
            </div>
            <div className="onboarding-guidance">
              <div>
                <span>Operator steps</span>
                <ol>
                  {(card.operator_steps ?? []).slice(0, 3).map((step: string) => (
                    <li key={`${card.provider_id}-${step}`}>{step}</li>
                  ))}
                </ol>
              </div>
              <div>
                <span>Safe actions</span>
                <div className="action-chip-list">
                  {(card.safe_actions ?? []).map((action: JsonRecord) => (
                    <StatusPill
                      key={`${card.provider_id}-${action.tool}`}
                      tone={action.enabled ? 'info' : 'neutral'}
                    >
                      {`${action.label ?? humanize(action.tool ?? 'action')} / ${action.tier ?? 'read_only'}`}
                    </StatusPill>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProviderImportPreviews({ previews }: { previews: JsonRecord }) {
  const rows = previews.previews ?? [];
  const summary = previews.summary ?? {};
  if (!rows.length) {
    return <div className="empty-state">No import previews available</div>;
  }
  return (
    <div className="preview-stack">
      <div className="preview-summary" aria-label="Configured import dry-run summary">
        <div>
          <span>Would write</span>
          <strong>{summary.would_write ?? 0}</strong>
        </div>
        <div>
          <span>Normalized count</span>
          <strong>{summary.normalized_count ?? 0}</strong>
        </div>
        <div>
          <span>Needs attention</span>
          <strong>{summary.needs_attention ?? 0}</strong>
        </div>
      </div>
      <div className="preview-list">
        {rows.slice(0, 6).map((preview: JsonRecord) => (
          <div className="preview-row" key={preview.preview_id ?? preview.provider_id}>
            <div className="preview-main">
              <strong>{preview.display_name ?? preview.provider_id}</strong>
              <span>{preview.source_label ?? preview.kind}</span>
              <StatusPill
                tone={
                  preview.status === 'ready'
                    ? 'good'
                    : preview.status === 'needs_attention'
                      ? 'warn'
                      : 'neutral'
                }
              >
                {humanize(preview.status ?? 'unknown')}
              </StatusPill>
            </div>
            <div className="preview-fields">
              <div>
                <span>Target store</span>
                <strong>{humanize(preview.target_store ?? 'none')}</strong>
              </div>
              <div>
                <span>Normalized count</span>
                <strong>{preview.normalized_count ?? 0}</strong>
              </div>
              <div>
                <span>Would write</span>
                <StatusPill tone={preview.would_write ? 'info' : 'neutral'}>
                  {preview.would_write ? 'yes' : 'no'}
                </StatusPill>
              </div>
            </div>
            <div className="preview-context">
              <div>
                <span>Sample identifiers</span>
                <div className="env-chip-list">
                  {(preview.sample_identifiers ?? []).length ? (
                    preview.sample_identifiers.slice(0, 4).map((identifier: string) => (
                      <code key={`${preview.provider_id}-${identifier}`}>{identifier}</code>
                    ))
                  ) : (
                    <small>None</small>
                  )}
                </div>
              </div>
              <div>
                <span>Warnings</span>
                <small>{(preview.warnings ?? [])[0] ?? 'No preview warnings'}</small>
              </div>
              <div>
                <span>Safe action</span>
                <div className="action-chip-list">
                  {(preview.safe_actions ?? []).slice(0, 2).map((action: JsonRecord) => (
                    <StatusPill
                      key={`${preview.provider_id}-${action.tool}`}
                      tone={action.enabled ? 'info' : 'neutral'}
                    >
                      {`${action.label ?? humanize(action.tool ?? 'action')} / ${action.tier ?? 'read_only'}`}
                    </StatusPill>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function reconciliationTone(status: string): 'good' | 'warn' | 'danger' | 'info' | 'neutral' {
  if (status === 'in_sync') {
    return 'good';
  }
  if (status === 'pending_refresh' || status === 'source_changed') {
    return 'warn';
  }
  if (status === 'store_mismatch' || status === 'needs_attention') {
    return 'danger';
  }
  if (status === 'not_configured') {
    return 'neutral';
  }
  return 'info';
}

function ProviderImportReconciliation({ reconciliation }: { reconciliation: JsonRecord }) {
  const rows = reconciliation.reconciliations ?? [];
  const summary = reconciliation.summary ?? {};
  if (!rows.length) {
    return <div className="empty-state">No import reconciliation available</div>;
  }
  return (
    <div className="reconciliation-stack">
      <div className="reconciliation-summary" aria-label="Configured import reconciliation summary">
        <div>
          <span>In sync</span>
          <strong>{summary.in_sync ?? 0}</strong>
        </div>
        <div>
          <span>Pending refresh</span>
          <strong>{summary.pending_refresh ?? 0}</strong>
        </div>
        <div>
          <span>Source changed</span>
          <strong>{summary.source_changed ?? 0}</strong>
        </div>
      </div>
      <div className="reconciliation-list">
        {rows.slice(0, 6).map((item: JsonRecord) => (
          <div className="reconciliation-row" key={item.reconciliation_id ?? item.provider_id}>
            <div className="reconciliation-main">
              <strong>{item.display_name ?? item.provider_id}</strong>
              <span>{item.source_label ?? item.kind}</span>
              <StatusPill tone={reconciliationTone(item.reconciliation_status ?? 'unknown')}>
                {humanize(item.reconciliation_status ?? 'unknown')}
              </StatusPill>
            </div>
            <div className="reconciliation-fields">
              <div>
                <span>Preview count</span>
                <strong>{item.preview?.normalized_count ?? 0}</strong>
              </div>
              <div>
                <span>Latest job count</span>
                <strong>{item.latest_job?.imported_count ?? 0}</strong>
              </div>
              <div>
                <span>Stored rows</span>
                <strong>{item.store?.stored_count ?? 0}</strong>
              </div>
            </div>
            <div className="reconciliation-context">
              <div>
                <span>Target store</span>
                <strong>{humanize(item.store?.target_store ?? 'none')}</strong>
              </div>
              <div>
                <span>Deltas</span>
                <small>
                  Preview {item.deltas?.preview_minus_store ?? 0} / Job{' '}
                  {item.deltas?.latest_job_minus_store ?? 0}
                </small>
              </div>
              <div>
                <span>Safe action</span>
                <div className="action-chip-list">
                  {(item.safe_actions ?? []).slice(0, 2).map((action: JsonRecord) => (
                    <StatusPill
                      key={`${item.provider_id}-${action.tool}`}
                      tone={action.enabled ? 'info' : 'neutral'}
                    >
                      {`${action.label ?? humanize(action.tool ?? 'action')} / ${action.tier ?? 'read_only'}`}
                    </StatusPill>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProviderProfiles({
  busyAction,
  onRefresh,
  profiles,
}: {
  busyAction: string;
  onRefresh: (providerId: string) => void;
  profiles: JsonRecord[];
}) {
  return (
    <div className="validation-stack">
      <div className="detail-list">
        {profiles.length ? (
          profiles.slice(0, 6).map((profile: JsonRecord) => (
            <div className="profile-row" key={profile.profile_id ?? profile.provider_id}>
              <div>
                <strong>{profile.provider_id}</strong>
                <span>{profile.source_label ?? 'fixture_provider'}</span>
                <small>{profile.path_env ?? 'provider env'}</small>
              </div>
              <div className="profile-actions">
                <StatusPill
                  tone={
                    profile.last_validation_status === 'valid'
                      ? 'good'
                      : profile.last_validation_status === 'not_configured'
                        ? 'neutral'
                        : 'warn'
                  }
                >
                  {humanize(profile.last_validation_status ?? 'unknown')}
                </StatusPill>
                <button
                  className="command-button compact-button"
                  disabled={busyAction === 'Refresh profile'}
                  onClick={() => onRefresh(String(profile.provider_id))}
                >
                  <RefreshCw size={14} aria-hidden="true" />
                  <span>Refresh profile</span>
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">Fixture profiles active</div>
        )}
      </div>
    </div>
  );
}

function readinessTone(status: string): 'good' | 'warn' | 'danger' | 'info' | 'neutral' {
  if (status === 'ready') {
    return 'good';
  }
  if (status === 'stale' || status === 'retry_due' || status === 'pending_refresh') {
    return 'warn';
  }
  if (status === 'backoff' || status === 'needs_attention') {
    return 'danger';
  }
  if (status === 'not_configured') {
    return 'neutral';
  }
  return 'info';
}

function ProviderRefreshReadiness({
  actionPolicy,
  busyAction,
  onRunSchedule,
  readiness,
}: {
  actionPolicy: JsonRecord;
  busyAction: string;
  onRunSchedule: () => void;
  readiness: JsonRecord;
}) {
  const summary = readiness.summary ?? {};
  const rows = readiness.readiness ?? [];
  return (
    <div className="readiness-stack">
      <div className="readiness-summary" aria-label="Provider refresh readiness summary">
        <div>
          <span>Total providers</span>
          <strong>{summary.total ?? rows.length ?? 0}</strong>
        </div>
        <div>
          <span>Ready</span>
          <strong>{summary.ready ?? 0}</strong>
        </div>
        <div>
          <span>Needs attention</span>
          <strong>{summary.needs_attention ?? 0}</strong>
        </div>
      </div>
      <div className="command-row tight-row">
        <ActionButton busy={busyAction === 'Run full refresh'} onClick={onRunSchedule}>
          <RefreshCw size={14} aria-hidden="true" />
          <span>Run full refresh</span>
        </ActionButton>
        <StatusPill tone="info">{actionPolicy?.tier ?? 'draft_only'}</StatusPill>
      </div>
      <div className="detail-list">
        {rows.length ? (
          rows.slice(0, 6).map((item: JsonRecord) => (
            <div className="readiness-row" key={item.provider_id}>
              <div>
                <strong>{item.provider_id}</strong>
                <span>{item.source_label ?? item.kind ?? 'configured provider'}</span>
                <small>
                  Retry after {item.retry_after_seconds ?? 0}s
                  {item.next_attempt_at ? ` / Next attempt ${item.next_attempt_at}` : ' / Next attempt not scheduled'}
                </small>
              </div>
              <StatusPill tone={readinessTone(item.readiness_status ?? 'unknown')}>
                {humanize(item.readiness_status ?? 'unknown')}
              </StatusPill>
            </div>
          ))
        ) : (
          <div className="empty-state">No provider refresh jobs yet</div>
        )}
      </div>
    </div>
  );
}

function ProviderImportJobs({ jobs }: { jobs: JsonRecord[] }) {
  return (
    <div className="detail-list">
      {jobs.length ? (
        jobs.slice(0, 5).map((job: JsonRecord) => (
          <div className="detail-row" key={job.job_id}>
            <strong>{job.provider_id}</strong>
            <span>{`${humanize(job.status ?? 'unknown')} / ${humanize(job.validation_status ?? 'unknown')}`}</span>
          </div>
        ))
      ) : (
        <div className="empty-state">No import jobs yet</div>
      )}
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
