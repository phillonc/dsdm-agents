# OPTIX Collective Intelligence Network (VS-4)

The Collective Intelligence Network is a comprehensive social trading platform that enables traders to share ideas, track performance, compete on leaderboards, and copy successful strategies.

## Features

### 🤝 Social Trading
- **Trade Idea Sharing**: Create, publish, and share detailed trade ideas with the community
- **Community Discussions**: Comment, like, and engage with trade ideas
- **Follow System**: Follow successful traders and build your network
- **Trade Idea Discovery**: Search and filter ideas by asset, sentiment, tags, and more

### 📊 Performance Tracking
- **Comprehensive Metrics**: Track win rate, total return, Sharpe ratio, Sortino ratio, and more
- **Historical Analysis**: View performance over different time periods
- **Risk Metrics**: Monitor max drawdown, profit factor, and risk-adjusted returns
- **Trade History**: Complete record of all executed trades

### 🏆 Leaderboards
- **Multiple Rankings**: Top performers, most consistent, best risk-adjusted returns
- **Rising Stars**: Discover new talented traders
- **Period-based Rankings**: Daily, weekly, monthly, and all-time leaderboards
- **Verified Traders**: Highlighted verified trader badges

### 💭 Sentiment Analysis
- **Asset Sentiment**: Aggregated community sentiment for each asset
- **Trending Assets**: Discover what the community is talking about
- **Sentiment History**: Track sentiment changes over time
- **Bullish/Bearish Lists**: See the most bullish and bearish assets

### 🔄 Copy Trading
- **Automatic Replication**: Automatically copy trades from successful traders
- **Customizable Settings**: Control position sizing, asset filters, and risk parameters
- **Reverse Trading**: Option to reverse trade directions
- **Position Limits**: Set maximum and minimum position sizes

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd optix_collective_intelligence

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## Quick Start

```python
from src.collective_intelligence_api import CollectiveIntelligenceAPI

# Initialize the API
api = CollectiveIntelligenceAPI()

# Create a trader profile
trader = api.create_trader(
    username="john_trader",
    display_name="John Trader",
    bio="Professional day trader"
)

# Create a trade idea
idea = api.create_trade_idea(
    trader_id=trader.trader_id,
    title="BTC Long Setup",
    description="Bitcoin showing bullish patterns on the 4H chart",
    asset="BTC/USD",
    entry_price=50000.0,
    target_price=55000.0,
    stop_loss=48000.0,
    sentiment=SentimentType.BULLISH
)

# Publish the idea
api.publish_trade_idea(idea.idea_id, trader.trader_id)

# Get asset sentiment
sentiment = api.get_asset_sentiment("BTC/USD")
print(f"BTC Sentiment: {sentiment.overall_sentiment}")

# View leaderboard
top_traders = api.get_top_performers(period="1m", limit=10)
for entry in top_traders:
    print(f"{entry.rank}. {entry.username} - Return: {entry.metric_value}%")
```

## Architecture

### Core Services

1. **TraderService**: Manages trader profiles and social connections
2. **TradeIdeaService**: Handles trade idea creation, publishing, and interactions
3. **PerformanceService**: Calculates and tracks performance metrics
4. **LeaderboardService**: Generates rankings and leaderboards
5. **SentimentService**: Aggregates and analyzes community sentiment
6. **CopyTradingService**: Manages copy trading functionality

### Data Models

- **Trader**: User profile with statistics and metadata
- **TradeIdea**: Shared trade ideas with engagement metrics
- **Trade**: Actual trade execution records
- **PerformanceMetrics**: Calculated performance statistics
- **CommunitySentiment**: Aggregated sentiment data
- **LeaderboardEntry**: Ranking information

## API Reference

### Trader Management

```python
# Create a trader
trader = api.create_trader(username, display_name, **kwargs)

# Get trader
trader = api.get_trader(trader_id)
trader = api.get_trader_by_username(username)

# Update profile
api.update_trader(trader_id, **updates)

# Search traders
traders = api.search_traders(query, min_reputation, verified_only)
```

### Trade Ideas

```python
# Create and publish
idea = api.create_trade_idea(trader_id, title, description, asset, **kwargs)
api.publish_trade_idea(idea_id, trader_id)

# Search and discover
ideas = api.search_trade_ideas(query, asset, tags, sentiment)
trending = api.get_trending_ideas(limit)

# Interact
api.like_idea(idea_id, trader_id)
api.add_comment(idea_id, trader_id, content)
```

### Performance

```python
# Record trades
api.record_trade(trade)

# Get metrics
metrics = api.get_performance_metrics(trader_id, period)
comparison = api.compare_trader_performance(trader_ids, period)
```

### Leaderboards

```python
# Get rankings
leaderboard = api.get_leaderboard(metric, period, limit)
top_performers = api.get_top_performers(period, limit)
consistent = api.get_most_consistent_traders(period, limit)

# Get trader rank
rank = api.get_trader_rank(trader_id, metric, period)
```

### Sentiment

```python
# Get sentiment
sentiment = api.get_asset_sentiment(asset, timeframe)
trending = api.get_trending_assets(limit, timeframe)

# Get lists
bullish = api.get_bullish_assets(limit, min_volume)
bearish = api.get_bearish_assets(limit, min_volume)

# Historical data
history = api.get_sentiment_history(asset, days)
```

### Copy Trading

```python
# Enable/disable
api.enable_copy_trading(follower_id, following_id, settings)
api.disable_copy_trading(follower_id, following_id)

# Configure
api.update_copy_settings(follower_id, following_id, settings)
stats = api.get_copy_statistics(follower_id, following_id)
```

## Testing

The project includes comprehensive unit tests with 85%+ coverage:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_trader_service.py

# Run with markers
pytest -m unit
```

## Performance Metrics

### Available Metrics

- **Win Rate**: Percentage of profitable trades
- **Total Return**: Cumulative return percentage
- **Sharpe Ratio**: Risk-adjusted return measure
- **Sortino Ratio**: Downside risk-adjusted return
- **Max Drawdown**: Maximum peak-to-trough decline
- **Profit Factor**: Ratio of gross profit to gross loss
- **Consistency Score**: Measure of return consistency (0-100)
- **Average Trade Duration**: Mean time in trades
- **Risk-Adjusted Return**: Return per unit of risk

## Configuration

### Copy Trading Settings

```python
settings = {
    "enabled": True,
    "copy_percentage": 100.0,        # % of capital to allocate
    "max_position_size": None,       # Max position size
    "min_position_size": None,       # Min position size
    "copy_stop_loss": True,          # Copy stop losses
    "copy_take_profit": True,        # Copy take profits
    "slippage_tolerance": 0.5,       # Max slippage %
    "asset_whitelist": None,         # Assets to copy (None = all)
    "asset_blacklist": None,         # Assets to exclude
    "max_concurrent_positions": None, # Max simultaneous positions
    "reverse_trades": False          # Reverse trade direction
}
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
optix_collective_intelligence/
├── src/
│   ├── models.py                          # Data models
│   ├── trader_service.py                  # Trader management
│   ├── trade_idea_service.py             # Trade ideas
│   ├── performance_service.py            # Performance metrics
│   ├── leaderboard_service.py            # Rankings
│   ├── sentiment_service.py              # Sentiment analysis
│   ├── copy_trading_service.py           # Copy trading
│   ├── collective_intelligence_api.py    # Main API
│   └── exceptions.py                      # Custom exceptions
├── tests/
│   ├── unit/                             # Unit tests
│   └── conftest.py                       # Test configuration
├── docs/                                  # Documentation
├── config/                                # Configuration files
└── README.md
```

## License

[License Information]

## Support

For questions or issues, please contact [support information].
