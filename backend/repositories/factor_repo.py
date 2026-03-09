"""
Repository for Factor definition and data queries.
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlmodel import Session, select
from backend.models.factors import (
    FactorDefinition,
    FamaFrenchFactor,
    CustomFactorScore,
)


class FactorRepository:
    """Repository for factor-related database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_factor(
        self,
        factor_name: str,
        factor_type: str,
        description: Optional[str] = None,
        frequency: str = "daily",
        is_published: bool = False,
        publication_date: Optional[date] = None,
        calculation_formula: Optional[str] = None,
        data_requirements: Optional[Dict[str, Any]] = None,
    ) -> FactorDefinition:
        """
        Create a new factor definition.

        Args:
            factor_name: Unique name of the factor
            factor_type: Type of factor
            description: Optional description
            frequency: Calculation frequency
            is_published: Whether factor is published
            publication_date: Optional publication date
            calculation_formula: Optional formula description
            data_requirements: Optional data requirements

        Returns:
            Created FactorDefinition
        """
        factor = FactorDefinition(
            factor_name=factor_name,
            factor_type=factor_type,
            description=description,
            frequency=frequency,
            is_published=is_published,
            publication_date=publication_date,
            calculation_formula=calculation_formula,
            data_requirements=data_requirements,
        )
        self.session.add(factor)
        self.session.commit()
        self.session.refresh(factor)
        return factor

    def get_factor(self, factor_id: int) -> Optional[FactorDefinition]:
        """Get a factor by ID."""
        return self.session.exec(
            select(FactorDefinition).where(FactorDefinition.id == factor_id)
        ).first()

    def get_factor_by_name(self, factor_name: str) -> Optional[FactorDefinition]:
        """Get a factor by name."""
        return self.session.exec(
            select(FactorDefinition).where(
                FactorDefinition.factor_name == factor_name
            )
        ).first()

    def list_factors(
        self,
        factor_type: Optional[str] = None,
        is_published: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FactorDefinition]:
        """
        List factors with optional filtering.

        Args:
            factor_type: Optional filter by type
            is_published: Optional filter by publication status
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            List of FactorDefinition objects
        """
        query = select(FactorDefinition).order_by(
            FactorDefinition.created_at.desc()
        )

        if factor_type:
            query = query.where(FactorDefinition.factor_type == factor_type)

        if is_published is not None:
            query = query.where(FactorDefinition.is_published == is_published)

        query = query.limit(limit).offset(offset)
        return self.session.exec(query).all()

    def get_factor_library(self) -> List[FactorDefinition]:
        """Get all published factors for the factor library."""
        return self.session.exec(
            select(FactorDefinition)
            .where(FactorDefinition.is_published == True)
            .order_by(FactorDefinition.factor_name.asc())
        ).all()

    def save_fama_french_returns(
        self,
        factor_id: int,
        returns: List[FamaFrenchFactor],
    ) -> None:
        """
        Save Fama-French factor returns.

        Args:
            factor_id: Factor ID
            returns: List of FamaFrenchFactor objects
        """
        for ret in returns:
            ret.factor_id = factor_id
            self.session.add(ret)

        self.session.commit()

    def get_fama_french_returns(
        self,
        factor_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[FamaFrenchFactor]:
        """
        Get Fama-French factor returns for a date range.

        Args:
            factor_id: Factor ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of FamaFrenchFactor objects
        """
        query = select(FamaFrenchFactor).where(
            FamaFrenchFactor.factor_id == factor_id
        )

        if start_date:
            query = query.where(FamaFrenchFactor.date >= start_date)

        if end_date:
            query = query.where(FamaFrenchFactor.date <= end_date)

        query = query.order_by(FamaFrenchFactor.date.asc())
        return self.session.exec(query).all()

    def get_fama_french_return(
        self,
        factor_id: int,
        date_val: date,
    ) -> Optional[FamaFrenchFactor]:
        """Get Fama-French return for a specific date."""
        return self.session.exec(
            select(FamaFrenchFactor).where(
                FamaFrenchFactor.factor_id == factor_id,
                FamaFrenchFactor.date == date_val,
            )
        ).first()

    def save_custom_factor_scores(
        self,
        scores: List[CustomFactorScore],
    ) -> None:
        """
        Save custom factor scores.

        Args:
            scores: List of CustomFactorScore objects
        """
        for score in scores:
            self.session.add(score)

        self.session.commit()

    def get_factor_scores(
        self,
        factor_id: int,
        ticker: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[CustomFactorScore]:
        """
        Get custom factor scores.

        Args:
            factor_id: Factor ID
            ticker: Optional filter by ticker
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of CustomFactorScore objects
        """
        query = select(CustomFactorScore).where(
            CustomFactorScore.factor_id == factor_id
        )

        if ticker:
            query = query.where(CustomFactorScore.ticker == ticker)

        if start_date:
            query = query.where(CustomFactorScore.calculation_date >= start_date)

        if end_date:
            query = query.where(CustomFactorScore.calculation_date <= end_date)

        query = query.order_by(CustomFactorScore.calculation_date.asc())
        return self.session.exec(query).all()

    def get_factor_score(
        self,
        factor_id: int,
        ticker: str,
        date_val: date,
    ) -> Optional[CustomFactorScore]:
        """Get a specific factor score."""
        return self.session.exec(
            select(CustomFactorScore).where(
                CustomFactorScore.factor_id == factor_id,
                CustomFactorScore.ticker == ticker,
                CustomFactorScore.calculation_date == date_val,
            )
        ).first()

    def get_factor_scores_for_date(
        self,
        factor_id: int,
        date_val: date,
    ) -> List[CustomFactorScore]:
        """
        Get all factor scores for a specific date (cross-sectional).

        Args:
            factor_id: Factor ID
            date_val: Date for scores

        Returns:
            List of CustomFactorScore objects for all tickers on the date
        """
        query = select(CustomFactorScore).where(
            CustomFactorScore.factor_id == factor_id,
            CustomFactorScore.calculation_date == date_val,
        )
        query = query.order_by(CustomFactorScore.factor_value.desc())
        return self.session.exec(query).all()

    def get_latest_factor_score(
        self,
        factor_id: int,
        ticker: str,
    ) -> Optional[CustomFactorScore]:
        """Get the most recent factor score for a ticker."""
        query = select(CustomFactorScore).where(
            CustomFactorScore.factor_id == factor_id,
            CustomFactorScore.ticker == ticker,
        )
        query = query.order_by(CustomFactorScore.calculation_date.desc())
        return self.session.exec(query).first()

    def update_factor(
        self,
        factor_id: int,
        **kwargs: Any,
    ) -> Optional[FactorDefinition]:
        """
        Update a factor definition.

        Args:
            factor_id: Factor ID
            **kwargs: Fields to update

        Returns:
            Updated FactorDefinition or None if not found
        """
        factor = self.get_factor(factor_id)
        if not factor:
            return None

        for key, value in kwargs.items():
            if hasattr(factor, key):
                setattr(factor, key, value)

        factor.updated_at = datetime.now(timezone.utc)
        self.session.add(factor)
        self.session.commit()
        self.session.refresh(factor)
        return factor

    def publish_factor(
        self,
        factor_id: int,
        publication_date: Optional[date] = None,
    ) -> Optional[FactorDefinition]:
        """
        Mark a factor as published.

        Args:
            factor_id: Factor ID
            publication_date: Optional publication date (defaults to today)

        Returns:
            Updated FactorDefinition or None if not found
        """
        if publication_date is None:
            publication_date = date.today()

        return self.update_factor(
            factor_id,
            is_published=True,
            publication_date=publication_date,
        )
