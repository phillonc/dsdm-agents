# Collective Intelligence Network - API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Trader Management](#trader-management)
4. [Trade Ideas](#trade-ideas)
5. [Performance Metrics](#performance-metrics)
6. [Leaderboards](#leaderboards)
7. [Sentiment Analysis](#sentiment-analysis)
8. [Copy Trading](#copy-trading)
9. [Data Models](#data-models)
10. [Error Handling](#error-handling)

## Overview

The Collective Intelligence Network API provides comprehensive social trading functionality including trader profiles, trade idea sharing, performance tracking, leaderboards, sentiment analysis, and copy trading.

### Base Usage

```python
from src.collective_intelligence_api import CollectiveIntelligenceAPI

api = CollectiveIntelligenceAPI()
```

## Authentication

*Note: Authentication is not implemented in this version. Future versions will include JWT-based authentication.*

## Trader Management

### Create Trader

Create a new trader profile.

```python
trader = api.create_trader(
    username: str,           # Required, 3-30 characters
    display_name: str,       # Required
    bio: str = "",          # Optional
    avatar_url: str = "",   # Optional
    tags: List[str] = []    # Optional
)
```

**Returns**: `Trader` object

**Raises**:
- `ValidationError`: Invalid username or parameters
- `DuplicateError`: Username already exists

### Get Trader

Retrieve a trader by ID or username.

```python
trader = api.get_trader(trader_id: str)
trader = api.get_trader_by_username(username: str)
```

**Returns**: `Trader` object

**Raises**: `NotFoundError` if trader doesn't exist

### Update Trader

Update trader profile information.

```python
trader = api.update_trader(
    trader_id: str,
    display_name: str = None,
    bio: str = None,
    avatar_url: str = None,
    verified: bool = None,
    tags: List[str] = None
)
```

**Returns**: Updated `Trader` object

### Search Traders

Search for traders with filters.

```python
traders = api.search_traders(
    query: str = None,              # Text search
    min_reputation: float = None,   # Minimum reputation score
    verified_only: bool = False,    # Only verified traders
    tags: List[str] = None,        # Filter by tags
    limit: int = 50                # Maximum results
)
```

**Returns**: List of `Trader` objects

### Social Connections

```python
# Follow a trader
relationship = api.follow_trader(follower_id: str, following_id: str)

# Unfollow a trader
success = api.unfollow_trader(follower_id: str, following_id: str)

# Get following list
following = api.get_following(trader_id: str)

# Get followers list
followers = api.get_followers(trader_id: str)

# Check if following
is_following = api.is_following(follower_id: str, following_id: str)
```

## Trade Ideas

### Create Trade Idea

Create a new trade idea.

```python
idea = api.create_trade_idea(
    trader_id: str,                    # Required
    title: str,                        # Required, 5-200 chars
    description: str,                  # Required, min 10 chars
    asset: str,                        # Required
    trade_type: TradeType = None,      # Optional
    entry_price: float = None,         # Optional
    target_price: float = None,        # Optional
    stop_loss: float = None,           # Optional
    timeframe: str = None,             # Optional
    confidence: float = None,          # Optional, 0-100
    sentiment: SentimentType = None,   # Optional
    tags: List[str] = []              # Optional
)
```

**Returns**: `TradeIdea` object (status: DRAFT)

### Publish Trade Idea

Publish a draft trade idea to the community.

```python
idea = api.publish_trade_idea(idea_id: str, trader_id: str)
```

**Returns**: Updated `TradeIdea` object (status: PUBLISHED)

**Raises**:
- `PermissionError`: If not the owner
- `ValidationError`: If not in draft status

### Update Trade Idea

Update an existing trade idea.

```python
idea = api.update_trade_idea(
    idea_id: str,
    trader_id: str,
    title: str = None,
    description: str = None,
    target_price: float = None,
    # ... other fields
)
```

**Returns**: Updated `TradeIdea` object

### Get Trade Idea

Retrieve a trade idea and increment view count.

```python
idea = api.get_trade_idea(idea_id: str)
```

**Returns**: `TradeIdea` object

### Search Trade Ideas

Search for published trade ideas.

```python
ideas = api.search_trade_ideas(
    query: str = None,              # Text search
    asset: str = None,              # Filter by asset
    tags: List[str] = None,        # Filter by tags
    sentiment: SentimentType = None, # Filter by sentiment
    limit: int = 50                # Maximum results
)
```

**Returns**: List of `TradeIdea` objects

### Get Trending Ideas

Get trending trade ideas based on engagement.

```python
trending = api.get_trending_ideas(limit: int = 10)
```

**Returns**: List of `TradeIdea` objects sorted by trending score

### Interact with Trade Ideas

```python
# Like an idea
idea = api.like_idea(idea_id: str, trader_id: str)

# Unlike an idea
idea = api.unlike_idea(idea_id: str, trader_id: str)

# Add comment
comment = api.add_comment(
    idea_id: str,
    trader_id: str,
    content: str,
    parent_comment_id: str = None  # For threaded replies
)

# Get comments
comments = api.get_comments(
    idea_id: str,
    parent_comment_id: str = None
)

# Share idea
idea = api.share_idea(idea_id: str)
```

## Performance Metrics

### Record Trade

Record a trade for performance tracking.

```python
trade = Trade(
    trader_id="trader123",
    asset="BTC/USD",
    trade_type=TradeType.BUY,
    entry_price=50000.0,
    exit_price=52000.0,
    quantity=1.0,
    status=TradeStatus.CLOSED,
    profit_loss=2000.0,
    profit_loss_percentage=4.0
)

api.record_trade(trade)
```

### Get Performance Metrics

Calculate performance metrics for a trader.

```python
metrics = api.get_performance_metrics(
    trader_id: str,
    period: str = "all_time"  # all_time, 1y, 6m, 3m, 1m, 1w
)
```

**Returns**: `PerformanceMetrics` object with:
- `total_trades`: Total number of trades
- `winning_trades`: Number of profitable trades
- `losing_trades`: Number of losing trades
- `win_rate`: Percentage of winning trades
- `total_return`: Cumulative return percentage
- `average_return`: Average return per trade
- `best_trade`: Best trade return
- `worst_trade`: Worst trade return
- `sharpe_ratio`: Risk-adjusted return metric
- `sortino_ratio`: Downside risk-adjusted return
- `max_drawdown`: Maximum peak-to-trough decline
- `profit_factor`: Gross profit / gross loss
- `consistency_score`: Return consistency (0-100)
- `risk_adjusted_return`: Return per unit of risk

### Compare Trader Performance

Compare metrics for multiple traders.

```python
comparison = api.compare_trader_performance(
    trader_ids: List[str],
    period: str = "all_time"
)
```

**Returns**: Dict mapping `trader_id` to `PerformanceMetrics`

## Leaderboards

### Get Leaderboard

Get leaderboard rankings by a specific metric.

```python
leaderboard = api.get_leaderboard(
    metric: str = "total_return",  # Metric to rank by
    period: str = "all_time",      # Time period
    limit: int = 100,              # Max entries
    min_trades: int = 10           # Minimum trades required
)
```

**Available Metrics**:
- `total_return`: Total return percentage
- `win_rate`: Win rate percentage
- `sharpe_ratio`: Sharpe ratio
- `sortino_ratio`: Sortino ratio
- `consistency_score`: Consistency score
- `risk_adjusted_return`: Risk-adjusted return

**Returns**: List of `LeaderboardEntry` objects

### Get Top Performers

Get top performing traders for a period.

```python
top = api.get_top_performers(
    period: str = "1m",
    limit: int = 10
)
```

### Get Most Consistent Traders

Get traders with most consistent returns.

```python
consistent = api.get_most_consistent_traders(
    period: str = "3m",
    limit: int = 10
)
```

### Get Rising Stars

Get recently joined traders with strong performance.

```python
rising = api.get_rising_stars(limit: int = 10)
```

### Get Trader Rank

Get a specific trader's rank.

```python
rank = api.get_trader_rank(
    trader_id: str,
    metric: str = "total_return",
    period: str = "all_time"
)
```

**Returns**: Integer rank (1-indexed) or None if not ranked

### Get All Leaderboards

Get all category leaderboards at once.

```python
all_leaderboards = api.get_all_leaderboards(period: str = "1m")
```

**Returns**: Dict with keys:
- `top_performers`
- `most_consistent`
- `best_risk_adjusted`
- `rising_stars`

## Sentiment Analysis

### Get Asset Sentiment

Get aggregated community sentiment for an asset.

```python
sentiment = api.get_asset_sentiment(
    asset: str,
    timeframe: timedelta = None  # Default: 24 hours
)
```

**Returns**: `CommunitySentiment` object with:
- `bullish_count`: Number of bullish ideas
- `bearish_count`: Number of bearish ideas
- `neutral_count`: Number of neutral ideas
- `overall_sentiment`: BULLISH, BEARISH, or NEUTRAL
- `sentiment_score`: Score from -100 (bearish) to 100 (bullish)
- `volume_24h`: Total ideas in timeframe
- `trending_score`: Trending calculation

### Get Trending Assets

Get assets with highest community activity.

```python
trending = api.get_trending_assets(
    limit: int = 10,
    timeframe: timedelta = timedelta(hours=24)
)
```

**Returns**: List of `CommunitySentiment` objects

### Get Bullish/Bearish Assets

```python
# Most bullish assets
bullish = api.get_bullish_assets(
    limit: int = 10,
    min_volume: int = 5
)

# Most bearish assets
bearish = api.get_bearish_assets(
    limit: int = 10,
    min_volume: int = 5
)
```

### Get Sentiment Distribution

Get percentage breakdown of sentiment.

```python
distribution = api.get_sentiment_distribution(asset: str)
```

**Returns**: Dict with keys `bullish`, `bearish`, `neutral` (percentages)

### Get Sentiment History

Get historical sentiment data.

```python
history = api.get_sentiment_history(
    asset: str,
    days: int = 7
)
```

**Returns**: List of daily sentiment snapshots

## Copy Trading

### Enable Copy Trading

Enable copy trading for a follow relationship.

```python
relationship = api.enable_copy_trading(
    follower_id: str,
    following_id: str,
    settings: Dict = None
)
```

**Default Settings**:
```python
{
    "enabled": True,
    "copy_percentage": 100.0,      # % of capital
    "max_position_size": None,
    "min_position_size": None,
    "copy_stop_loss": True,
    "copy_take_profit": True,
    "slippage_tolerance": 0.5,
    "asset_whitelist": None,       # None = all assets
    "asset_blacklist": None,
    "max_concurrent_positions": None,
    "reverse_trades": False
}
```

**Returns**: `FollowRelationship` object

### Disable Copy Trading

Disable copy trading for a relationship.

```python
success = api.disable_copy_trading(
    follower_id: str,
    following_id: str,
    close_positions: bool = False
)
```

### Update Copy Settings

Update copy trading configuration.

```python
relationship = api.update_copy_settings(
    follower_id: str,
    following_id: str,
    settings: Dict
)
```

### Get Copy Statistics

Get statistics for a copy trading relationship.

```python
stats = api.get_copy_statistics(
    follower_id: str,
    following_id: str
)
```

**Returns**: Dict with copy trading statistics

## Data Models

### Trader

```python
{
    "trader_id": str,
    "username": str,
    "display_name": str,
    "bio": str,
    "avatar_url": str,
    "joined_date": datetime,
    "verified": bool,
    "total_trades": int,
    "win_rate": float,
    "total_return": float,
    "followers_count": int,
    "following_count": int,
    "reputation_score": float,
    "risk_score": float,
    "tags": List[str]
}
```

### TradeIdea

```python
{
    "idea_id": str,
    "trader_id": str,
    "title": str,
    "description": str,
    "asset": str,
    "trade_type": "buy" | "sell" | "short" | "cover",
    "entry_price": float,
    "target_price": float,
    "stop_loss": float,
    "timeframe": str,
    "confidence": float,
    "status": "draft" | "published" | "closed",
    "sentiment": "bullish" | "bearish" | "neutral",
    "likes_count": int,
    "comments_count": int,
    "shares_count": int,
    "views_count": int,
    "tags": List[str],
    "created_at": datetime,
    "published_at": datetime
}
```

### Trade

```python
{
    "trade_id": str,
    "trader_id": str,
    "asset": str,
    "trade_type": "buy" | "sell" | "short" | "cover",
    "entry_price": float,
    "exit_price": float,
    "quantity": float,
    "status": "open" | "closed" | "pending" | "cancelled",
    "profit_loss": float,
    "profit_loss_percentage": float,
    "opened_at": datetime,
    "closed_at": datetime
}
```

## Error Handling

### Exception Types

- `ValidationError`: Input validation failed
- `NotFoundError`: Resource not found
- `DuplicateError`: Resource already exists
- `PermissionError`: Insufficient permissions
- `CopyTradingError`: Copy trading operation failed

### Error Handling Example

```python
from src.exceptions import ValidationError, NotFoundError

try:
    trader = api.create_trader(username="ab", display_name="Test")
except ValidationError as e:
    print(f"Validation error: {e}")
except NotFoundError as e:
    print(f"Not found: {e}")
```

## Rate Limiting

*Note: Rate limiting is not implemented in this version but should be added for production use.*

## Best Practices

1. **Caching**: Leaderboards and sentiment data are cached for 5 minutes
2. **Pagination**: Use `limit` parameter for large result sets
3. **Error Handling**: Always handle exceptions appropriately
4. **Performance**: Use specific filters to reduce result set size
5. **Copy Trading**: Start with small position sizes and test thoroughly

## Support

For questions or issues, please refer to the README.md or contact support.
