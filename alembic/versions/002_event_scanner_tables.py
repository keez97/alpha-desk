"""
Event Scanner tables for AlphaDesk Phase 2.

Revision ID: 002
Revises: 001
Create Date: 2026-03-10

Adds 7 new tables for event detection, classification, alpha decay analysis,
and factor signal bridging.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Event Scanner tables."""

    # Event table - central table for all detected events
    op.create_table(
        'event',
        sa.Column('event_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('severity_score', sa.Integer(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('headline', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('event_id'),
        sa.UniqueConstraint('ticker', 'event_type', 'event_date', 'source', name='uq_event_ticker_type_date_source'),
        sa.Index('idx_event_ticker', 'ticker'),
        sa.Index('idx_event_type', 'event_type'),
        sa.Index('idx_event_severity', 'severity_score'),
        sa.Index('idx_event_detected', 'detected_at'),
        sa.Index('idx_event_date', 'event_date'),
        sa.Index('idx_event_source', 'source'),
        sa.Index('idx_event_ticker_detected', 'ticker', 'detected_at'),
    )

    # EventClassificationRule table - rules for event classification
    op.create_table(
        'event_classification_rule',
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('classification', sa.String(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=False),
        sa.Column('pattern_value', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('rule_id'),
        sa.Index('idx_rule_classification', 'classification'),
        sa.Index('idx_rule_pattern_type', 'pattern_type'),
        sa.Index('idx_rule_enabled', 'enabled'),
    )

    # AlphaDecayWindow table - alpha decay measurements per event
    op.create_table(
        'alpha_decay_window',
        sa.Column('window_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('window_type', sa.String(), nullable=False),
        sa.Column('abnormal_return', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('benchmark_return', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ),
        sa.PrimaryKeyConstraint('window_id'),
        sa.UniqueConstraint('event_id', 'window_type', 'measured_at', name='uq_decay_event_window_measured'),
        sa.Index('idx_decay_event', 'event_id'),
        sa.Index('idx_decay_window_type', 'window_type'),
        sa.Index('idx_decay_measured', 'measured_at'),
        sa.Index('idx_decay_event_measured', 'event_id', 'measured_at'),
    )

    # EventFactorBridge table - links events to factors
    op.create_table(
        'event_factor_bridge',
        sa.Column('bridge_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('signal_value', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ),
        sa.PrimaryKeyConstraint('bridge_id'),
        sa.UniqueConstraint('event_id', 'factor_id', name='uq_bridge_event_factor'),
        sa.Index('idx_bridge_event', 'event_id'),
        sa.Index('idx_bridge_factor', 'factor_id'),
        sa.Index('idx_bridge_valid_until', 'valid_until'),
    )

    # EventSourceMapping table - maps events to source references
    op.create_table(
        'event_source_mapping',
        sa.Column('mapping_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('extracted_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ),
        sa.PrimaryKeyConstraint('mapping_id'),
        sa.UniqueConstraint('event_id', 'source_type', 'source_id', name='uq_source_event_type_id'),
        sa.Index('idx_source_event', 'event_id'),
        sa.Index('idx_source_type', 'source_type'),
        sa.Index('idx_source_id', 'source_id'),
    )

    # EventAlertConfiguration table - configuration for alerts
    op.create_table(
        'event_alert_configuration',
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('event_type_filter', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('severity_threshold', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('tickers_filter', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('config_id'),
        sa.Index('idx_alert_enabled', 'enabled'),
    )

    # EventCorrelationAnalysis table - correlations between event types
    op.create_table(
        'event_correlation_analysis',
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('event_type_1', sa.String(), nullable=False),
        sa.Column('event_type_2', sa.String(), nullable=False),
        sa.Column('co_occurrence_count', sa.Integer(), nullable=False),
        sa.Column('time_window_days', sa.Integer(), nullable=False),
        sa.Column('correlation_strength', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('analyzed_period_end', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('analysis_id'),
        sa.UniqueConstraint('event_type_1', 'event_type_2', 'analyzed_period_end', name='uq_corr_event_types_period'),
        sa.Index('idx_corr_event_1', 'event_type_1'),
        sa.Index('idx_corr_event_2', 'event_type_2'),
        sa.Index('idx_corr_analyzed_period', 'analyzed_period_end'),
        sa.Index('idx_corr_strength', 'correlation_strength'),
    )


def downgrade() -> None:
    """Drop all Event Scanner tables."""
    op.drop_table('event_correlation_analysis')
    op.drop_table('event_alert_configuration')
    op.drop_table('event_source_mapping')
    op.drop_table('event_factor_bridge')
    op.drop_table('alpha_decay_window')
    op.drop_table('event_classification_rule')
    op.drop_table('event')
