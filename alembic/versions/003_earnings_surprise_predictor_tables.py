"""
Earnings Surprise Predictor tables for AlphaDesk Phase 3.

Revision ID: 003
Revises: 002
Create Date: 2026-03-10

Adds 6 new tables for earnings estimates, actuals, SmartEstimate configuration,
analyst accuracy tracking, PEAD measurement, and earnings signals.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Earnings Surprise Predictor tables."""

    # earnings_estimate table
    op.create_table(
        'earnings_estimate',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('estimate_type', sa.String(), nullable=False),
        sa.Column('eps_estimate', sa.Numeric(19, 4), nullable=False),
        sa.Column('estimate_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analyst_broker', sa.String(), nullable=True),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'estimate_type', 'analyst_broker', 'estimate_date',
            name='uq_earnings_estimate_composite'
        ),
        sa.Index('idx_earnings_estimate_ticker', 'ticker'),
        sa.Index('idx_earnings_estimate_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_estimate_date', 'estimate_date'),
        sa.Index('idx_earnings_estimate_type', 'estimate_type'),
        sa.Index('idx_earnings_estimate_broker', 'analyst_broker'),
        sa.Index('idx_earnings_estimate_ticker_quarter', 'ticker', 'fiscal_quarter'),
        sa.Index('idx_earnings_estimate_ticker_date', 'ticker', 'estimate_date'),
    )

    # earnings_actual table
    op.create_table(
        'earnings_actual',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('actual_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('report_time', sa.String(), nullable=True),
        sa.Column('surprise_vs_consensus', sa.Numeric(19, 4), nullable=True),
        sa.Column('surprise_vs_smart', sa.Numeric(19, 4), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'report_date',
            name='uq_earnings_actual_composite'
        ),
        sa.Index('idx_earnings_actual_ticker', 'ticker'),
        sa.Index('idx_earnings_actual_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_actual_report_date', 'report_date'),
        sa.Index('idx_earnings_actual_ticker_quarter', 'ticker', 'fiscal_quarter'),
    )

    # smart_estimate_weights table
    op.create_table(
        'smart_estimate_weights',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('weight_type', sa.String(), nullable=False),
        sa.Column('parameter_name', sa.String(), nullable=False),
        sa.Column('parameter_value', sa.Numeric(19, 4), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'weight_type', 'parameter_name',
            name='uq_smart_estimate_weights_composite'
        ),
        sa.Index('idx_smart_estimate_weights_type', 'weight_type'),
    )

    # analyst_scorecard table
    op.create_table(
        'analyst_scorecard',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('analyst_broker', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('total_estimates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accurate_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('directional_accuracy', sa.Numeric(19, 4), nullable=True),
        sa.Column('avg_error_pct', sa.Numeric(19, 4), nullable=True),
        sa.Column('last_evaluated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'analyst_broker', 'ticker', 'period_start', 'period_end',
            name='uq_analyst_scorecard_composite'
        ),
        sa.Index('idx_analyst_scorecard_broker', 'analyst_broker'),
        sa.Index('idx_analyst_scorecard_ticker', 'ticker'),
        sa.Index('idx_analyst_scorecard_period', 'period_start', 'period_end'),
    )

    # pead_measurement table
    op.create_table(
        'pead_measurement',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('earnings_date', sa.Date(), nullable=False),
        sa.Column('surprise_direction', sa.String(), nullable=False),
        sa.Column('surprise_magnitude', sa.Numeric(19, 4), nullable=False),
        sa.Column('car_1d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_5d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_21d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_60d', sa.Numeric(19, 4), nullable=True),
        sa.Column('benchmark_ticker', sa.String(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'measured_at',
            name='uq_pead_measurement_composite'
        ),
        sa.Index('idx_pead_measurement_ticker', 'ticker'),
        sa.Index('idx_pead_measurement_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_pead_measurement_earnings_date', 'earnings_date'),
        sa.Index('idx_pead_measurement_surprise_direction', 'surprise_direction'),
        sa.Index('idx_pead_measurement_measured_at', 'measured_at'),
    )

    # earnings_signal table
    op.create_table(
        'earnings_signal',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('signal_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('signal_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('smart_estimate_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('consensus_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('divergence_pct', sa.Numeric(19, 4), nullable=False),
        sa.Column('days_to_earnings', sa.Integer(), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'signal_date',
            name='uq_earnings_signal_composite'
        ),
        sa.Index('idx_earnings_signal_ticker', 'ticker'),
        sa.Index('idx_earnings_signal_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_signal_date', 'signal_date'),
        sa.Index('idx_earnings_signal_type', 'signal_type'),
        sa.Index('idx_earnings_signal_valid_until', 'valid_until'),
        sa.Index('idx_earnings_signal_ticker_date', 'ticker', 'signal_date'),
    )


def downgrade() -> None:
    """Drop all Earnings Surprise Predictor tables."""

    op.drop_table('earnings_signal')
    op.drop_table('pead_measurement')
    op.drop_table('analyst_scorecard')
    op.drop_table('smart_estimate_weights')
    op.drop_table('earnings_actual')
    op.drop_table('earnings_estimate')
