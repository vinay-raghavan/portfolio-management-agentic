from __future__ import annotations

import re
from datetime import date

from .models import (
    ApprovalRequest,
    AuditEvent,
    BacktestRequest,
    BacktestResult,
    BacktestTrade,
    PaperOrder,
    PaperPosition,
)

OFFLINE_SOURCE = "offline_fixture"
FIXTURE_TIMESTAMP = "2026-06-22T09:15:00+05:30"
SUPPORTED_ORDER_SIDES = {"buy", "sell"}
SUPPORTED_ORDER_TYPES = {"market", "limit"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")
    return normalized


def _normalize_setup(setup: str) -> str:
    normalized = setup.strip().lower()
    if not normalized:
        raise ValueError("Setup is required.")
    return normalized


def _validate_date_window(start_date: str, end_date: str) -> None:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("Backtest dates must use YYYY-MM-DD format.") from exc
    if start > end:
        raise ValueError("Backtest start_date must be on or before end_date.")


class BacktestStore:
    """Deterministic offline backtest contract store."""

    def __init__(self) -> None:
        self._requests: dict[str, BacktestRequest] = {}

    def create_request(
        self,
        symbol: str,
        setup: str,
        start_date: str,
        end_date: str,
    ) -> BacktestRequest:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_setup = _normalize_setup(setup)
        _validate_date_window(start_date, end_date)
        request_id = "-".join(
            (
                "backtest",
                _slug(normalized_symbol),
                _slug(normalized_setup),
                _slug(start_date),
                _slug(end_date),
            )
        )
        request = BacktestRequest(
            request_id=request_id,
            symbol=normalized_symbol,
            setup=normalized_setup,
            start_date=start_date,
            end_date=end_date,
            mode="paper",
            status="draft",
            source=OFFLINE_SOURCE,
            assumptions=[
                "Offline fixture bars and deterministic fills are used.",
                "Costs, slippage, taxes, and broker constraints are simplified.",
                "Position sizing is illustrative and capped for paper review.",
            ],
            notes=[
                "Backtest request is a simulation draft, not an order.",
                "Live trading is forbidden by policy.",
            ],
        )
        self._requests[request.request_id] = request
        return request

    def get_result(self, request_id: str) -> BacktestResult:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError(f"Unknown backtest request_id: {request_id}")

        trades = _fixture_trades(request.symbol, request.setup)
        total_pnl = round(sum(trade.pnl for trade in trades), 2)
        average_return = round(
            sum(trade.return_pct for trade in trades) / len(trades),
            2,
        )
        wins = [trade for trade in trades if trade.pnl > 0]
        metrics: dict[str, float | int | str] = {
            "trade_count": len(trades),
            "winning_trades": len(wins),
            "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
            "total_pnl": total_pnl,
            "total_return_pct": round(total_pnl / 100000 * 100, 2),
            "average_trade_return_pct": average_return,
            "max_drawdown_pct": -3.4,
            "exposure_cap_pct": 8.0,
        }
        return BacktestResult(
            request_id=request.request_id,
            symbol=request.symbol,
            setup=request.setup,
            mode="paper",
            status="simulated",
            source=OFFLINE_SOURCE,
            metrics=metrics,
            trades=trades,
            warnings=[
                "Simulated backtest is not predictive and is not investment advice.",
                "No live order, broker API, or trading credential is used.",
            ],
            citations=[
                "breakout-continuation-v1",
                "volatility-regime-sizing-v1",
            ],
            generated_at=FIXTURE_TIMESTAMP,
        )


class PaperLedgerStore:
    """In-memory paper-only ledger used until durable persistence is added."""

    def __init__(self) -> None:
        self._orders: dict[str, PaperOrder] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_events: list[AuditEvent] = []
        self._positions = [
            PaperPosition(
                symbol="TATAMOTORS",
                quantity=10,
                average_price=912.50,
                last_price=975.20,
                mode="paper",
                source=OFFLINE_SOURCE,
                notes=["Fixture paper position from a prior simulated fill."],
            ),
            PaperPosition(
                symbol="SBIN",
                quantity=20,
                average_price=805.00,
                last_price=821.40,
                mode="paper",
                source=OFFLINE_SOURCE,
                notes=["Fixture paper position used for exposure review."],
            ),
        ]

    def create_order_proposal(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        requested_price: float | None = None,
    ) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_side = side.strip().lower()
        normalized_order_type = order_type.strip().lower()
        if normalized_side not in SUPPORTED_ORDER_SIDES:
            raise ValueError("Paper order side must be buy or sell.")
        if normalized_order_type not in SUPPORTED_ORDER_TYPES:
            raise ValueError("Paper order type must be market or limit.")
        if quantity <= 0:
            raise ValueError("Paper order quantity must be greater than zero.")
        if requested_price is not None and requested_price <= 0:
            raise ValueError("Requested price must be greater than zero when provided.")

        normalized_strategy = strategy_id.strip()
        if not normalized_strategy:
            raise ValueError("Strategy id is required.")

        order_id = "-".join(
            (
                "paper-order",
                _slug(normalized_strategy),
                _slug(normalized_symbol),
                normalized_side,
                str(quantity),
                normalized_order_type,
            )
        )
        approval_id = f"approval-{order_id}"
        existing_order = self._orders.get(order_id)
        existing_approval = self._approvals.get(approval_id)
        if existing_order is not None and existing_approval is not None:
            event = self._event_for_order(order_id)
            return existing_order, existing_approval, event

        order = PaperOrder(
            order_id=order_id,
            strategy_id=normalized_strategy,
            symbol=normalized_symbol,
            side=normalized_side,
            quantity=quantity,
            order_type=normalized_order_type,
            mode="paper",
            status="pending_approval",
            requested_price=requested_price,
            filled_quantity=0,
            fill_ids=[],
            approval_request_id=approval_id,
            created_at=FIXTURE_TIMESTAMP,
            notes=[
                "Draft paper order only; no fill has been simulated.",
                "Human approval is required before any future simulated execution.",
                "Live broker order placement is forbidden.",
            ],
        )
        approval = ApprovalRequest(
            approval_id=approval_id,
            action_type="paper_order_simulation",
            status="pending",
            summary=(
                f"Review simulated {normalized_side} {quantity} "
                f"{normalized_symbol} order for strategy {normalized_strategy}."
            ),
            related_id=order_id,
            required_approval="human",
            requested_at=FIXTURE_TIMESTAMP,
            risk_notes=[
                "Confirm paper sizing, drawdown budget, and concentration before simulation.",
                "Approval cannot authorize live trading.",
            ],
        )
        event = AuditEvent(
            event_id=f"audit-{order_id}",
            event_type="paper_order_proposed",
            entity_type="paper_order",
            entity_id=order_id,
            message="Paper order proposal created and queued for human approval.",
            created_at=FIXTURE_TIMESTAMP,
            actor="agent",
            redacted_payload={
                "symbol": normalized_symbol,
                "side": normalized_side,
                "quantity": quantity,
                "order_type": normalized_order_type,
                "mode": "paper",
                "live_trading": "forbidden",
            },
        )
        self._orders[order.order_id] = order
        self._approvals[approval.approval_id] = approval
        self._audit_events.append(event)
        return order, approval, event

    def list_orders(self) -> list[PaperOrder]:
        return list(self._orders.values())

    def list_positions(self) -> list[PaperPosition]:
        return list(self._positions)

    def approval_queue(self) -> list[ApprovalRequest]:
        return [
            approval
            for approval in self._approvals.values()
            if approval.status == "pending"
        ]

    def audit_events(self) -> list[AuditEvent]:
        return list(self._audit_events)

    def _event_for_order(self, order_id: str) -> AuditEvent:
        for event in self._audit_events:
            if event.entity_id == order_id:
                return event
        raise ValueError(f"Missing audit event for order_id: {order_id}")


def _fixture_trades(symbol: str, setup: str) -> list[BacktestTrade]:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_setup = _normalize_setup(setup)
    return [
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-1",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-02-05",
            exit_date="2026-02-20",
            quantity=10,
            entry_price=912.50,
            exit_price=948.20,
            pnl=357.00,
            return_pct=3.91,
            status="closed_simulated",
        ),
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-2",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-04-03",
            exit_date="2026-04-18",
            quantity=8,
            entry_price=955.00,
            exit_price=932.40,
            pnl=-180.80,
            return_pct=-2.37,
            status="closed_simulated",
        ),
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-3",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-05-10",
            exit_date="2026-06-07",
            quantity=8,
            entry_price=944.30,
            exit_price=986.10,
            pnl=334.40,
            return_pct=4.43,
            status="closed_simulated",
        ),
    ]


_BACKTEST_STORE = BacktestStore()
_PAPER_LEDGER_STORE = PaperLedgerStore()


def create_fixture_backtest_request(
    symbol: str,
    setup: str,
    start_date: str,
    end_date: str,
) -> BacktestRequest:
    return _BACKTEST_STORE.create_request(symbol, setup, start_date, end_date)


def get_fixture_backtest_result(request_id: str) -> BacktestResult:
    return _BACKTEST_STORE.get_result(request_id)


def create_fixture_paper_order_proposal(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    requested_price: float | None = None,
) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
    return _PAPER_LEDGER_STORE.create_order_proposal(
        strategy_id,
        symbol,
        side,
        quantity,
        order_type,
        requested_price,
    )


def list_fixture_paper_orders() -> list[PaperOrder]:
    return _PAPER_LEDGER_STORE.list_orders()


def list_fixture_paper_positions() -> list[PaperPosition]:
    return _PAPER_LEDGER_STORE.list_positions()


def list_fixture_approval_queue() -> list[ApprovalRequest]:
    return _PAPER_LEDGER_STORE.approval_queue()


def list_fixture_audit_events() -> list[AuditEvent]:
    return _PAPER_LEDGER_STORE.audit_events()
