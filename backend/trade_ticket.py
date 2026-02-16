"""
Trade Ticket Module

Every proposed trade must be wrapped in a ``TradeTicket`` so that the
``RiskEngine`` can evaluate the incremental impact on the portfolio.

Required fields per ticket
--------------------------
- strategy (e.g. 'SPY_IRON_CONDOR', 'SPY_PUT_CREDIT_SPREAD')
- underlying (e.g. 'SPY')
- timestamp, data_timestamp
- expiry, dte
- legs: list of {type, side, strike, qty}
- mid_credit, limit_credit, width, max_loss
- pop_estimate
- edge_metrics: {iv_pct, implied_move, realized_proxy, iv_richness, skew_metric, term_structure}
- regime_gate: {passed, reasons}
- risk_gate: {passed, reasons, portfolio_after: {delta, vega, gamma, max_loss_week}}
- confidence_score
- exits: {take_profit_pct, stop_loss_multiple, time_stop_days}
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class TicketLeg(BaseModel):
    """A single option leg within a trade ticket."""
    type: str          # 'call' or 'put'
    side: str          # 'buy' or 'sell'
    strike: float
    qty: int = 1
    # Optional Greeks / pricing used by evaluate_ticket
    delta: Optional[float] = None
    vega: Optional[float] = None
    gamma: Optional[float] = None
    price: Optional[float] = None


class EdgeMetrics(BaseModel):
    """Volatility edge metrics attached to the ticket."""
    iv_pct: Optional[float] = None
    implied_move: Optional[float] = None
    realized_proxy: Optional[float] = None
    iv_richness: Optional[float] = None
    skew_metric: Optional[float] = None
    term_structure: Optional[float] = None


class RegimeGate(BaseModel):
    """Regime-based go/no-go gate."""
    passed: bool = True
    reasons: List[str] = Field(default_factory=list)


class PortfolioAfter(BaseModel):
    """Projected portfolio risk metrics after the trade."""
    delta: float = 0.0
    vega: float = 0.0
    gamma: float = 0.0
    max_loss_trade: float = 0.0
    max_loss_week: float = 0.0


class RiskGate(BaseModel):
    """Risk-based go/no-go gate with projected portfolio state."""
    passed: bool = True
    reasons: List[str] = Field(default_factory=list)
    portfolio_after: PortfolioAfter = Field(default_factory=PortfolioAfter)


class Exits(BaseModel):
    """Default exit rules for the trade."""
    take_profit_pct: float = 50.0
    stop_loss_multiple: float = 2.0
    time_stop_days: int = 21


# ---------------------------------------------------------------------------
# Main ticket model
# ---------------------------------------------------------------------------

class TradeTicket(BaseModel):
    """Structured trade ticket produced by every engine.

    All engines must produce ``TradeTicket`` instances rather than
    free-form dicts.
    """
    strategy: str
    underlying: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    data_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    expiry: Optional[str] = None
    dte: Optional[int] = None
    legs: List[TicketLeg] = Field(default_factory=list)
    mid_credit: float = 0.0
    limit_credit: float = 0.0
    width: float = 0.0
    max_loss: float = 0.0
    pop_estimate: Optional[float] = None
    edge_metrics: EdgeMetrics = Field(default_factory=EdgeMetrics)
    regime_gate: RegimeGate = Field(default_factory=RegimeGate)
    risk_gate: RiskGate = Field(default_factory=RiskGate)
    confidence_score: float = 0.0
    exits: Exits = Field(default_factory=Exits)

    # Operational / envelope fields (not part of the core spec but needed
    # by the ticket pipeline and execution workflow)
    ticket_id: Optional[str] = None
    status: str = 'pending'


# ---------------------------------------------------------------------------
# Builder helper
# ---------------------------------------------------------------------------

def build_trade_ticket(
    underlying,
    strategy,
    legs,
    mid_credit=0.0,
    max_loss=0.0,
    width=0.0,
    limit_credit=None,
    expiry=None,
    dte=None,
    pop_estimate=None,
    edge_metrics=None,
    regime_gate=None,
    risk_gate=None,
    confidence_score=0.0,
    exits=None,
    ticket_id=None,
):
    """
    Construct a validated ``TradeTicket``.

    Parameters
    ----------
    underlying : str
        Underlying ticker (e.g. ``'SPY'``).
    strategy : str
        Strategy label (e.g. ``'SPY_IRON_CONDOR'``).
    legs : list[dict]
        Each leg must contain at minimum ``type``, ``side``, ``strike``,
        ``qty``.  Optional fields: ``delta``, ``vega``, ``gamma``,
        ``price``.
    mid_credit : float
        Mid-market credit of the structure.
    max_loss : float
        Maximum possible loss (positive number).
    width : float
        Width of the spread (distance between strikes).
    limit_credit : float or None
        Limit-order credit (defaults to *mid_credit* when not given).
    expiry : str or None
        Expiration date (ISO-8601).
    dte : int or None
        Days to expiration.
    pop_estimate : float or None
        Probability-of-profit estimate (0-100).
    edge_metrics : dict or EdgeMetrics or None
        Volatility edge metrics.
    regime_gate : dict or RegimeGate or None
        Regime gate result.
    risk_gate : dict or RiskGate or None
        Risk gate result.
    confidence_score : float
        Overall confidence score (0-1).
    exits : dict or Exits or None
        Exit rule parameters.
    ticket_id : str or None
        Unique ticket identifier.

    Returns
    -------
    TradeTicket
    """
    now = datetime.now().isoformat()

    ticket_legs = []
    for leg in (legs or []):
        if isinstance(leg, TicketLeg):
            ticket_legs.append(leg)
        elif isinstance(leg, dict):
            ticket_legs.append(TicketLeg(
                type=leg.get('type', leg.get('option_type', 'put')),
                side=leg.get('side', leg.get('action', 'sell')),
                strike=float(leg.get('strike', 0)),
                qty=int(leg.get('qty', leg.get('quantity', 1))),
                delta=leg.get('delta'),
                vega=leg.get('vega'),
                gamma=leg.get('gamma'),
                price=leg.get('price'),
            ))

    return TradeTicket(
        strategy=strategy,
        underlying=underlying,
        timestamp=now,
        data_timestamp=now,
        expiry=expiry,
        dte=dte,
        legs=ticket_legs,
        mid_credit=float(mid_credit),
        limit_credit=float(limit_credit if limit_credit is not None else mid_credit),
        width=float(width),
        max_loss=float(max_loss),
        pop_estimate=pop_estimate,
        edge_metrics=(
            edge_metrics if isinstance(edge_metrics, EdgeMetrics)
            else EdgeMetrics(**(edge_metrics or {}))
        ),
        regime_gate=(
            regime_gate if isinstance(regime_gate, RegimeGate)
            else RegimeGate(**(regime_gate or {}))
        ),
        risk_gate=(
            risk_gate if isinstance(risk_gate, RiskGate)
            else RiskGate(**(risk_gate or {}))
        ),
        confidence_score=float(confidence_score),
        exits=(
            exits if isinstance(exits, Exits)
            else Exits(**(exits or {}))
        ),
        ticket_id=ticket_id,
    )


# ---------------------------------------------------------------------------
# Risk evaluation
# ---------------------------------------------------------------------------

def evaluate_ticket(ticket, risk_engine, existing_positions,
                    equity=100_000.0, weekly_realized_pnl=0.0,
                    existing_weekly_max_losses=0.0):
    """
    Ask the ``RiskEngine`` to compute portfolio risk **after** the proposed
    trade is added, and populate the ticket's ``risk_gate``.

    Parameters
    ----------
    ticket : TradeTicket
        Output of ``build_trade_ticket()``.
    risk_engine : RiskEngine
        Instance of the portfolio risk calculator.
    existing_positions : list[dict]
        Current portfolio positions (same schema accepted by
        ``risk_engine.calculate_portfolio_risk``).
    equity : float
        Total account equity (default 100 000).
    weekly_realized_pnl : float
        Realized P&L this week (negative means loss).
    existing_weekly_max_losses : float
        Sum of max-loss values for trades already opened this week.

    Returns
    -------
    TradeTicket – the ticket with ``risk_gate`` populated.
    """
    combined_delta = 0.0
    combined_vega = 0.0
    combined_gamma = 0.0
    combined_notional = 0.0

    for leg in ticket.legs:
        sign = 1.0 if leg.side == 'buy' else -1.0
        qty = leg.qty
        combined_delta += sign * qty * (leg.delta or 0.0)
        combined_vega += sign * qty * (leg.vega or 0.0)
        combined_gamma += sign * qty * (leg.gamma or 0.0)
        combined_notional += abs(qty * (leg.price or 0.0) * 100)

    new_position = {
        'symbol': ticket.underlying,
        'delta': combined_delta,
        'vega': combined_vega,
        'gamma': combined_gamma,
        'notional': combined_notional,
        'earnings_date': None,
        'expiry_bucket': None,
    }

    result = risk_engine.evaluate_ticket_risk(
        ticket_max_loss=ticket.max_loss,
        ticket_position=new_position,
        existing_positions=existing_positions,
        equity=equity,
        weekly_realized_pnl=weekly_realized_pnl,
        existing_weekly_max_losses=existing_weekly_max_losses,
    )

    portfolio_after = PortfolioAfter(
        delta=result.get('portfolio_delta_after', 0.0),
        vega=result.get('portfolio_vega_after', 0.0),
        gamma=result.get('portfolio_gamma_after', 0.0),
        max_loss_trade=result.get('max_loss_trade', ticket.max_loss),
        max_loss_week=result.get('max_loss_week', ticket.max_loss),
    )

    ticket.risk_gate = RiskGate(
        passed=result.get('risk_limits_pass', True),
        reasons=result.get('reasons', []),
        portfolio_after=portfolio_after,
    )
    return ticket
