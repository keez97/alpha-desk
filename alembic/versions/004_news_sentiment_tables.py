"""News sentiment scoring tables for Phase 4.

Revision ID: 004
Revises: 003
Create Date: 2025-03-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sentiment tables."""
    # Create news_article table
    op.create_table(
        'news_article',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('headline', sa.String(), nullable=False),
        sa.Column('body_snippet', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tickers_mentioned', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('finbert_positive', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('finbert_negative', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('finbert_neutral', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('lm_categories', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('dedup_hash', sa.String(), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_hash', name='uq_news_article_hash'),
    )
    op.create_index('idx_news_article_dedup_hash', 'news_article', ['dedup_hash'])
    op.create_index('idx_news_article_ingestion_timestamp', 'news_article', ['ingestion_timestamp'])
    op.create_index('idx_news_article_published_at', 'news_article', ['published_at'])
    op.create_index('idx_news_article_sentiment_score', 'news_article', ['sentiment_score'])
    op.create_index('idx_news_article_source', 'news_article', ['source'])
    op.create_index('idx_news_article_ticker', 'news_article', ['ticker'])

    # Create ticker_sentiment table
    op.create_table(
        'ticker_sentiment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('window_type', sa.String(), nullable=False),
        sa.Column('sentiment_score', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('sentiment_velocity', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'window_type', 'computed_at', name='uq_ticker_sentiment_composite'),
    )
    op.create_index('idx_ticker_sentiment_computed_at', 'ticker_sentiment', ['computed_at'])
    op.create_index('idx_ticker_sentiment_ticker', 'ticker_sentiment', ['ticker'])
    op.create_index('idx_ticker_sentiment_ticker_window', 'ticker_sentiment', ['ticker', 'window_type'])
    op.create_index('idx_ticker_sentiment_window', 'ticker_sentiment', ['window_type'])

    # Create sentiment_alert table
    op.create_table(
        'sentiment_alert',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('sentiment_score', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('price_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('divergence_magnitude', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('alert_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'alert_date', 'alert_type', name='uq_sentiment_alert_composite'),
    )
    op.create_index('idx_sentiment_alert_active', 'sentiment_alert', ['ticker', 'resolved_at'])
    op.create_index('idx_sentiment_alert_date', 'sentiment_alert', ['alert_date'])
    op.create_index('idx_sentiment_alert_resolved', 'sentiment_alert', ['resolved_at'])
    op.create_index('idx_sentiment_alert_ticker', 'sentiment_alert', ['ticker'])
    op.create_index('idx_sentiment_alert_type', 'sentiment_alert', ['alert_type'])

    # Create sentiment_heatmap_cache table
    op.create_table(
        'sentiment_heatmap_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sector', sa.String(), nullable=False),
        sa.Column('window_type', sa.String(), nullable=False),
        sa.Column('avg_sentiment', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False),
        sa.Column('top_movers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sector', 'window_type', 'computed_at', name='uq_sentiment_heatmap_composite'),
    )
    op.create_index('idx_sentiment_heatmap_computed_at', 'sentiment_heatmap_cache', ['computed_at'])
    op.create_index('idx_sentiment_heatmap_sector', 'sentiment_heatmap_cache', ['sector'])
    op.create_index('idx_sentiment_heatmap_window', 'sentiment_heatmap_cache', ['window_type'])


def downgrade() -> None:
    """Drop sentiment tables."""
    op.drop_index('idx_sentiment_heatmap_window', table_name='sentiment_heatmap_cache')
    op.drop_index('idx_sentiment_heatmap_sector', table_name='sentiment_heatmap_cache')
    op.drop_index('idx_sentiment_heatmap_computed_at', table_name='sentiment_heatmap_cache')
    op.drop_table('sentiment_heatmap_cache')

    op.drop_index('idx_sentiment_alert_active', table_name='sentiment_alert')
    op.drop_index('idx_sentiment_alert_type', table_name='sentiment_alert')
    op.drop_index('idx_sentiment_alert_resolved', table_name='sentiment_alert')
    op.drop_index('idx_sentiment_alert_date', table_name='sentiment_alert')
    op.drop_index('idx_sentiment_alert_ticker', table_name='sentiment_alert')
    op.drop_table('sentiment_alert')

    op.drop_index('idx_ticker_sentiment_ticker_window', table_name='ticker_sentiment')
    op.drop_index('idx_ticker_sentiment_window', table_name='ticker_sentiment')
    op.drop_index('idx_ticker_sentiment_ticker', table_name='ticker_sentiment')
    op.drop_index('idx_ticker_sentiment_computed_at', table_name='ticker_sentiment')
    op.drop_table('ticker_sentiment')

    op.drop_index('idx_news_article_ticker', table_name='news_article')
    op.drop_index('idx_news_article_source', table_name='news_article')
    op.drop_index('idx_news_article_sentiment_score', table_name='news_article')
    op.drop_index('idx_news_article_published_at', table_name='news_article')
    op.drop_index('idx_news_article_ingestion_timestamp', table_name='news_article')
    op.drop_index('idx_news_article_dedup_hash', table_name='news_article')
    op.drop_table('news_article')
