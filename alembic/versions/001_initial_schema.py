"""
Initial schema creation for AlphaDesk Factor Backtester.

Revision ID: 001
Revises:
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables."""

    # Security master table
    op.create_table(
        'security',
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('cusip', sa.String(), nullable=True),
        sa.Column('isin', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('ticker'),
        sa.Index('idx_created_at', 'created_at'),
        sa.Index('idx_ticker', 'ticker'),
        sa.Index('idx_cusip', 'cusip'),
        sa.Index('idx_isin', 'isin'),
    )

    # Security lifecycle events
    op.create_table(
        'security_lifecycle_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_effective_date', 'effective_date'),
        sa.Index('idx_event_type', 'event_type'),
        sa.Index('idx_ticker_event_date', 'ticker', 'event_date'),
        sa.Index('idx_ticker', 'ticker'),
    )

    # Price history
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open_price', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('high_price', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('low_price', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('adjusted_close', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('data_source', sa.String(), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'date', 'data_source', name='uq_price_ticker_date_source'),
        sa.Index('idx_price_created', 'created_at'),
        sa.Index('idx_price_date_range', 'ticker', 'date', 'ingestion_timestamp'),
        sa.Index('idx_price_ingestion_pit', 'ticker', 'ingestion_timestamp'),
        sa.Index('idx_price_ticker_date', 'ticker', 'date'),
        sa.Index('idx_data_source', 'data_source'),
        sa.Index('idx_date', 'date'),
        sa.Index('idx_ticker', 'ticker'),
    )

    # Fundamentals snapshot
    op.create_table(
        'fundamentals_snapshot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_period_end', sa.Date(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('source_document_date', sa.Date(), nullable=False),
        sa.Column('document_type', sa.String(), nullable=False),
        sa.Column('data_source', sa.String(), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'fiscal_period_end', 'metric_name', 'source_document_date', 'data_source', name='uq_fundamentals_ticker_period_metric_source'),
        sa.Index('idx_fundamentals_created', 'created_at'),
        sa.Index('idx_fundamentals_date_range', 'ticker', 'fiscal_period_end', 'source_document_date'),
        sa.Index('idx_fundamentals_ingestion', 'ingestion_timestamp'),
        sa.Index('idx_fundamentals_pit', 'ticker', 'source_document_date', 'ingestion_timestamp'),
        sa.Index('idx_fundamentals_ticker_metric', 'ticker', 'metric_name'),
        sa.Index('idx_data_source', 'data_source'),
        sa.Index('idx_document_type', 'document_type'),
        sa.Index('idx_fiscal_period_end', 'fiscal_period_end'),
        sa.Index('idx_metric_name', 'metric_name'),
        sa.Index('idx_source_document_date', 'source_document_date'),
        sa.Index('idx_ticker', 'ticker'),
    )

    # Factor definitions
    op.create_table(
        'factor_definition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('factor_name', sa.String(), nullable=False),
        sa.Column('factor_type', sa.Enum('fama_french', 'custom', 'technical', name='factortype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('frequency', sa.Enum('daily', 'monthly', 'quarterly', 'annual', name='factorfrequency'), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('calculation_formula', sa.Text(), nullable=True),
        sa.Column('data_requirements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('factor_name', name='uq_factor_name'),
        sa.Index('idx_factor_published', 'is_published'),
        sa.Index('idx_factor_type', 'factor_type'),
        sa.Index('idx_factor_name', 'factor_name'),
    )

    # Fama-French factors
    op.create_table(
        'fama_french_factor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('return_value', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('factor_id', 'date', name='uq_ff_factor_date'),
        sa.Index('idx_ff_created', 'created_at'),
        sa.Index('idx_ff_factor_date', 'factor_id', 'date'),
        sa.Index('idx_ff_ingestion', 'ingestion_timestamp'),
        sa.Index('idx_date', 'date'),
    )

    # Custom factor scores
    op.create_table(
        'custom_factor_score',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('factor_value', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('percentile_rank', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('factor_id', 'ticker', 'calculation_date', name='uq_custom_factor_ticker_date'),
        sa.Index('idx_custom_created', 'created_at'),
        sa.Index('idx_custom_factor_ticker', 'factor_id', 'ticker'),
        sa.Index('idx_custom_ingestion', 'ingestion_timestamp'),
        sa.Index('idx_custom_ticker_date', 'ticker', 'calculation_date'),
    )

    # Backtests
    op.create_table(
        'backtest',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('backtest_type', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'RUNNING', 'COMPLETED', 'FAILED', name='backteststatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_backtest_created', 'created_at'),
        sa.Index('idx_backtest_status', 'status'),
        sa.Index('idx_backtest_completed', 'completed_at'),
        sa.Index('idx_name', 'name'),
    )

    # Backtest configuration
    op.create_table(
        'backtest_configuration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('rebalance_frequency', sa.String(), nullable=False),
        sa.Column('universe_selection', sa.String(), nullable=False),
        sa.Column('commission_bps', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('benchmark_ticker', sa.String(), nullable=False),
        sa.Column('rolling_window_months', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_id', name='uq_config_backtest_id'),
        sa.Index('idx_config_dates', 'start_date', 'end_date'),
    )

    # Backtest factor allocations
    op.create_table(
        'backtest_factor_allocation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_id', 'factor_id', name='uq_alloc_backtest_factor'),
        sa.Index('idx_alloc_backtest', 'backtest_id'),
        sa.Index('idx_alloc_weight', 'weight'),
    )

    # Backtest results
    op.create_table(
        'backtest_result',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('portfolio_value', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('daily_return', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('benchmark_return', sa.Numeric(precision=15, scale=8), nullable=True),
        sa.Column('turnover', sa.Numeric(precision=15, scale=8), nullable=True),
        sa.Column('factor_exposures', sa.JSON(), nullable=True),
        sa.Column('holdings_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_id', 'date', name='uq_result_backtest_date'),
        sa.Index('idx_result_created', 'created_at'),
        sa.Index('idx_result_backtest_date', 'backtest_id', 'date'),
        sa.Index('idx_result_date', 'date'),
    )

    # Backtest statistics
    op.create_table(
        'backtest_statistic',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_stat_backtest_metric', 'backtest_id', 'metric_name'),
        sa.Index('idx_stat_period', 'period_start', 'period_end'),
    )

    # Factor correlations
    op.create_table(
        'factor_correlation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('factor_1_id', sa.Integer(), nullable=False),
        sa.Column('factor_2_id', sa.Integer(), nullable=False),
        sa.Column('correlation_value', sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.ForeignKeyConstraint(['factor_1_id'], ['factor_definition.id'], ),
        sa.ForeignKeyConstraint(['factor_2_id'], ['factor_definition.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_id', 'factor_1_id', 'factor_2_id', 'as_of_date', name='uq_corr_backtest_factors_date'),
        sa.Index('idx_corr_backtest', 'backtest_id'),
        sa.Index('idx_corr_date', 'as_of_date'),
        sa.Index('idx_corr_factors', 'factor_1_id', 'factor_2_id'),
    )

    # Alpha decay analysis
    op.create_table(
        'alpha_decay_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('pre_publication_return', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('post_publication_return', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('decay_percentage', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('months_post_publication', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest.id'], ),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('factor_id', 'backtest_id', 'months_post_publication', name='uq_decay_factor_backtest_months'),
        sa.Index('idx_decay_backtest', 'backtest_id'),
        sa.Index('idx_decay_factor', 'factor_id'),
        sa.Index('idx_decay_months', 'months_post_publication'),
    )

    # Screener factor scores
    op.create_table(
        'screener_factor_score',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('score_date', sa.Date(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('factor_score', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('quintile', sa.Integer(), nullable=True),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'factor_id', 'score_date', name='uq_screener_ticker_factor_date'),
        sa.Index('idx_screener_date', 'score_date'),
        sa.Index('idx_screener_factor', 'factor_id'),
        sa.Index('idx_screener_ingestion', 'ingestion_timestamp'),
        sa.Index('idx_screener_quintile', 'quintile'),
        sa.Index('idx_screener_ticker', 'ticker'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('screener_factor_score')
    op.drop_table('alpha_decay_analysis')
    op.drop_table('factor_correlation')
    op.drop_table('backtest_statistic')
    op.drop_table('backtest_result')
    op.drop_table('backtest_factor_allocation')
    op.drop_table('backtest_configuration')
    op.drop_table('backtest')
    op.drop_table('custom_factor_score')
    op.drop_table('fama_french_factor')
    op.drop_table('factor_definition')
    op.drop_table('fundamentals_snapshot')
    op.drop_table('price_history')
    op.drop_table('security_lifecycle_event')
    op.drop_table('security')
