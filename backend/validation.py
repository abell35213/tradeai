"""
Pydantic validation models for API request schemas.

Provides strict type checking and value constraints for all JSON
request bodies accepted by the Flask endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class GreeksRequest(BaseModel):
    """Schema for POST /api/greeks/<symbol>."""
    spot_price: float = Field(..., gt=0, description="Current spot price")
    strike: float = Field(..., gt=0, description="Strike price")
    time_to_expiry: float = Field(..., ge=0, description="Time to expiry in years")
    volatility: float = Field(..., gt=0, le=10.0, description="Annualized volatility")
    risk_free_rate: float = Field(default=0.05, ge=-0.1, le=1.0)
    option_type: str = Field(default='call')
    dividend_yield: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator('option_type')
    @classmethod
    def validate_option_type(cls, v):
        if v not in ('call', 'put'):
            raise ValueError("option_type must be 'call' or 'put'")
        return v


class TradeTicketRequest(BaseModel):
    """Schema for POST /api/trade-ticket."""
    symbol: str = Field(..., min_length=1, max_length=10)
    strategy: str = Field(..., min_length=1)
    legs: list
    credit: float = 0.0
    max_loss: float = 0.0
    width: float = 0.0
    expiry: Optional[str] = None
    existing_positions: Optional[list] = Field(default=[])


class PositionSizeRequest(BaseModel):
    """Schema for POST /api/position-size."""
    symbol: Optional[str] = None
    confidence_score: float = Field(default=3, ge=1, le=5)
    historical_edge: float = Field(default=0.5, ge=0.0, le=10.0)
    implied_edge: Optional[float] = Field(default=None, ge=0.0)
    base_risk: Optional[float] = Field(default=None, gt=0)
    liquidity_score: float = Field(default=0.5, ge=0.0, le=1.0)


class CircuitBreakerRequest(BaseModel):
    """Schema for POST /api/circuit-breaker."""
    weekly_pnl_pct: float = Field(default=0.0)
    vix_percentile: float = Field(default=50.0, ge=0.0, le=100.0)
    vix_day_change_pct: float = Field(default=0.0)
    regime_label: Optional[str] = None
    macro_proximity_elevated: Optional[bool] = None


class OpportunitiesRequest(BaseModel):
    """Schema for POST /api/opportunities."""
    symbols: List[str] = Field(default=['SPY', 'QQQ', 'IWM'])
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class PortfolioRiskRequest(BaseModel):
    """Schema for POST /api/risk/portfolio."""
    positions: list = Field(default=[])


class IndexVolTicketRequest(BaseModel):
    """Schema for POST /api/trade-ticket/index-vol."""
    symbol: str = Field(default='SPY', min_length=1, max_length=10)
    existing_positions: list = Field(default=[])


class ExecuteRequest(BaseModel):
    """Schema for POST /api/execute."""
    ticket_id: str = Field(..., min_length=1)
    action: str

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v.lower() not in ('approve', 'reject'):
            raise ValueError("action must be 'approve' or 'reject'")
        return v.lower()
