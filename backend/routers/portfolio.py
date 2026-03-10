from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from backend.database import get_session
from backend.models.portfolio import Portfolio, PortfolioHolding
from backend.services.data_provider import get_history
from backend.services.portfolio_math import (
    compute_correlation_matrix,
    optimize_max_sharpe,
    optimize_max_variance,
    monte_carlo_simulation
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PortfolioHoldingInput(BaseModel):
    ticker: str
    weight: Optional[float] = None


class PortfolioCreate(BaseModel):
    name: str
    capital: float = 100000.0
    holdings: List[PortfolioHoldingInput] = []


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    capital: Optional[float] = None


@router.get("/")
def list_portfolios(session: Session = Depends(get_session)):
    """List all portfolios."""
    try:
        portfolios = session.exec(select(Portfolio)).all()

        items = [
            {
                "id": p.id,
                "name": p.name,
                "capital": p.capital,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "holdings_count": len(p.holdings)
            }
            for p in portfolios
        ]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolios": items
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error listing portfolios: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolios": []
        }


@router.post("/")
def create_portfolio(data: PortfolioCreate, session: Session = Depends(get_session)):
    """Create new portfolio with holdings."""
    try:
        portfolio = Portfolio(
            name=data.name,
            capital=data.capital
        )
        session.add(portfolio)
        session.flush()

        for holding in data.holdings:
            portfolio_holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                ticker=holding.ticker.upper(),
                weight=holding.weight
            )
            session.add(portfolio_holding)

        session.commit()
        session.refresh(portfolio)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "id": portfolio.id,
            "name": portfolio.name,
            "capital": portfolio.capital,
            "created_at": portfolio.created_at.isoformat(),
            "holdings": [
                {"ticker": h.ticker, "weight": h.weight}
                for h in portfolio.holdings
            ]
        }
    except Exception as e:
        session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Error creating portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portfolio")


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """Get portfolio details with holdings."""
    portfolio = session.get(Portfolio, portfolio_id)

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "id": portfolio.id,
        "name": portfolio.name,
        "capital": portfolio.capital,
        "created_at": portfolio.created_at.isoformat(),
        "updated_at": portfolio.updated_at.isoformat(),
        "holdings": [
            {"ticker": h.ticker, "weight": h.weight}
            for h in portfolio.holdings
        ]
    }


@router.put("/{portfolio_id}")
def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    session: Session = Depends(get_session)
):
    """Update portfolio."""
    try:
        portfolio = session.get(Portfolio, portfolio_id)

        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        if data.name:
            portfolio.name = data.name
        if data.capital:
            portfolio.capital = data.capital

        portfolio.updated_at = datetime.utcnow()
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "id": portfolio.id,
            "name": portfolio.name,
            "capital": portfolio.capital,
            "updated_at": portfolio.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Error updating portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to update portfolio")


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """Delete portfolio."""
    try:
        portfolio = session.get(Portfolio, portfolio_id)

        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        session.delete(portfolio)
        session.commit()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "deleted": portfolio_id
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Error deleting portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete portfolio")


@router.post("/{portfolio_id}/analysis")
def analyze_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """Run comprehensive portfolio analysis."""
    try:
        portfolio = session.get(Portfolio, portfolio_id)

        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio has no holdings")

        tickers = [h.ticker for h in portfolio.holdings]

        # Get historical data
        all_history = {}
        for ticker in tickers:
            hist = get_history(ticker, period="1y")
            if hist:
                closes = [h["close"] for h in hist]
                all_history[ticker] = closes

        if not all_history:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "portfolio_id": portfolio_id,
                "error": "Could not fetch data for holdings"
            }

        # Create DataFrame
        try:
            min_length = min(len(v) for v in all_history.values())
        except ValueError:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "portfolio_id": portfolio_id,
                "error": "No valid historical data available"
            }

        returns_data = {}
        for ticker, closes in all_history.items():
            prices = closes[-min_length:]
            returns = pd.Series(prices).pct_change().dropna().values
            returns_data[ticker] = returns

        returns_df = pd.DataFrame(returns_data)

        # Compute analysis
        corr_result = compute_correlation_matrix(tickers, period="1y")
        sharpe_result = optimize_max_sharpe(returns_df)
        var_result = optimize_max_variance(returns_df)
        mc_result = monte_carlo_simulation(
            {h.ticker: h.weight or (1/len(tickers)) for h in portfolio.holdings},
            returns_df,
            portfolio.capital
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_id": portfolio_id,
            "capital": portfolio.capital,
            "correlation_matrix": corr_result,
            "max_sharpe_optimization": sharpe_result,
            "max_variance_optimization": var_result,
            "monte_carlo_simulation": mc_result
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Portfolio analysis error: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_id": portfolio_id,
            "error": f"Analysis failed: {str(e)}"
        }
