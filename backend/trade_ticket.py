"""
Trade Ticket Module

Every proposed trade must be wrapped in a ``TradeTicket`` so that the
``RiskEngine`` can evaluate the incremental impact on the portfolio.

Required fields per ticket
--------------------------
- symbol
- strategy (e.g. 'short_straddle', 'iron_condor')
- legs (list of individual option legs)
- credit (net credit received, or negative for debit)
- max_loss (maximum possible loss in dollars)
- breakevens (list of breakeven prices)

After the ``RiskEngine`` evaluates the ticket it attaches:
- portfolio_risk_after_trade (dict of risk metrics post-trade)
"""

from datetime import datetime


def build_trade_ticket(
    symbol,
    strategy,
    legs,
    credit,
    max_loss,
    breakevens,
    quantity=1,
    expiry=None,
    notes=None,
):
    """
    Construct a trade-ticket dict.

    Parameters
    ----------
    symbol : str
        Underlying ticker.
    strategy : str
        Strategy name (e.g. 'short_straddle', 'iron_condor').
    legs : list[dict]
        Each leg must contain at minimum:
            - option_type ('call' or 'put')
            - strike (float)
            - action ('buy' or 'sell')
            - quantity (int)
            - price (float, per-contract premium)
    credit : float
        Net credit (positive) or debit (negative) of the trade.
    max_loss : float
        Worst-case loss in dollars (always expressed as a positive number).
    breakevens : list[float]
        Breakeven prices for the combined structure.
    quantity : int
        Number of contracts / units.
    expiry : str or None
        Expiration date string (ISO-8601).
    notes : str or None
        Free-form notes.

    Returns
    -------
    dict – fully populated trade ticket.
    """
    return {
        'symbol': symbol,
        'strategy': strategy,
        'legs': legs,
        'credit': float(credit),
        'max_loss': float(max_loss),
        'breakevens': [float(b) for b in breakevens],
        'quantity': int(quantity),
        'expiry': expiry,
        'notes': notes,
        'portfolio_risk_after_trade': None,   # filled by RiskEngine
        'created_at': datetime.now().isoformat(),
    }


def evaluate_ticket(ticket, risk_engine, existing_positions):
    """
    Ask the ``RiskEngine`` to compute portfolio risk **after** the proposed
    trade is added, and attach the result to the ticket.

    Parameters
    ----------
    ticket : dict
        Output of ``build_trade_ticket()``.
    risk_engine : RiskEngine
        Instance of the portfolio risk calculator.
    existing_positions : list[dict]
        Current portfolio positions (same schema accepted by
        ``risk_engine.calculate_portfolio_risk``).

    Returns
    -------
    dict – the ticket with ``portfolio_risk_after_trade`` populated.
    """
    # Build a synthetic position entry from the ticket
    combined_delta = 0.0
    combined_vega = 0.0
    combined_gamma = 0.0
    combined_notional = 0.0

    for leg in ticket.get('legs', []):
        sign = 1.0 if leg.get('action') == 'buy' else -1.0
        qty = leg.get('quantity', 1) * ticket.get('quantity', 1)
        combined_delta += sign * qty * leg.get('delta', 0.0)
        combined_vega += sign * qty * leg.get('vega', 0.0)
        combined_gamma += sign * qty * leg.get('gamma', 0.0)
        combined_notional += abs(qty * leg.get('price', 0.0) * 100)

    new_position = {
        'symbol': ticket['symbol'],
        'delta': combined_delta,
        'vega': combined_vega,
        'gamma': combined_gamma,
        'notional': combined_notional,
        'earnings_date': None,
        'expiry_bucket': None,
    }

    # Merge with existing positions
    all_positions = list(existing_positions) + [new_position]
    risk_after = risk_engine.calculate_portfolio_risk(all_positions)

    ticket['portfolio_risk_after_trade'] = risk_after
    return ticket
