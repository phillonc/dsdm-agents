# Collective Intelligence Network - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Trader Profile Setup](#trader-profile-setup)
3. [Creating Trade Ideas](#creating-trade-ideas)
4. [Social Features](#social-features)
5. [Tracking Performance](#tracking-performance)
6. [Using Leaderboards](#using-leaderboards)
7. [Sentiment Analysis](#sentiment-analysis)
8. [Copy Trading](#copy-trading)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

```bash
# Install the package
pip install -r requirements.txt

# Run tests to verify installation
pytest
```

### First Steps

```python
from src.collective_intelligence_api import CollectiveIntelligenceAPI
from src.models import TradeType, SentimentType

# Initialize the API
api = CollectiveIntelligenceAPI()

# You're ready to go!
```

## Trader Profile Setup

### Creating Your Profile

```python
# Create your trader profile
my_profile = api.create_trader(
    username="crypto_trader_john",
    display_name="John - Crypto Trader",
    bio="Day trader specializing in crypto markets. 5 years experience.",
    tags=["crypto", "day-trading", "technical-analysis"]
)

print(f"Welcome {my_profile.display_name}!")
print(f"Your trader ID: {my_profile.trader_id}")
```

**Tips:**
- Choose a memorable username (3-30 characters)
- Write a clear bio explaining your trading style
- Add relevant tags to help others find you

### Updating Your Profile

```python
# Update your profile
api.update_trader(
    my_profile.trader_id,
    bio="Day trader specializing in crypto markets. 5 years experience. Focus on BTC and ETH.",
    avatar_url="https://example.com/avatar.jpg",
    verified=True  # After verification process
)
```

### Finding Your Profile

```python
# Get your profile by ID
profile = api.get_trader(my_profile.trader_id)

# Or by username
profile = api.get_trader_by_username("crypto_trader_john")
```

## Creating Trade Ideas

### Your First Trade Idea

```python
# Create a draft trade idea
idea = api.create_trade_idea(
    trader_id=my_profile.trader_id,
    title="BTC Breaking Out of Ascending Triangle",
    description="""
    Bitcoin is forming a clear ascending triangle pattern on the 4H chart.
    
    Technical Analysis:
    - Triangle formation over 2 weeks
    - Volume declining (typical for triangles)
    - RSI at 55 (neutral)
    - MACD showing bullish divergence
    
    Entry Strategy:
    - Wait for breakout above $51,000 with volume confirmation
    - Target: $55,000 (measured move)
    - Stop loss: $48,500 (below triangle support)
    
    Risk/Reward: 1:3
    """,
    asset="BTC/USD",
    trade_type=TradeType.BUY,
    entry_price=51000.0,
    target_price=55000.0,
    stop_loss=48500.0,
    timeframe="4H",
    confidence=75.0,
    sentiment=SentimentType.BULLISH,
    tags=["bitcoin", "breakout", "triangle-pattern"]
)

print(f"Draft created: {idea.idea_id}")
```

### Publishing Your Idea

```python
# Publish when you're ready
published_idea = api.publish_trade_idea(idea.idea_id, my_profile.trader_id)

print(f"Published at: {published_idea.published_at}")
print(f"View it at: /ideas/{published_idea.idea_id}")
```

### Updating Your Idea

```python
# Update entry/exit parameters as market evolves
api.update_trade_idea(
    idea.idea_id,
    my_profile.trader_id,
    target_price=56000.0,  # Raised target
    description=published_idea.description + "\n\nUPDATE: Raised target to $56,000 due to strong momentum."
)
```

### Interacting with Others' Ideas

```python
# Find interesting ideas
ideas = api.search_trade_ideas(
    asset="BTC/USD",
    sentiment=SentimentType.BULLISH,
    limit=10
)

for idea in ideas:
    print(f"{idea.title} by {idea.trader_id}")
    
# Like an idea
api.like_idea(ideas[0].idea_id, my_profile.trader_id)

# Comment on an idea
comment = api.add_comment(
    ideas[0].idea_id,
    my_profile.trader_id,
    "Great analysis! I also noticed the volume divergence."
)

# Reply to a comment
reply = api.add_comment(
    ideas[0].idea_id,
    my_profile.trader_id,
    "Thanks for the feedback!",
    parent_comment_id=comment.comment_id
)
```

## Social Features

### Following Traders

```python
# Search for traders to follow
traders = api.search_traders(
    query="crypto",
    min_reputation=70.0,
    verified_only=True
)

# Follow a trader
for trader in traders[:3]:
    api.follow_trader(my_profile.trader_id, trader.trader_id)
    print(f"Now following {trader.display_name}")

# View who you're following
following = api.get_following(my_profile.trader_id)
print(f"You follow {len(following)} traders")

# View your followers
followers = api.get_followers(my_profile.trader_id)
print(f"You have {len(followers)} followers")
```

### Unfollow

```python
# Unfollow a trader
api.unfollow_trader(my_profile.trader_id, trader_to_unfollow.trader_id)
```

## Tracking Performance

### Recording Your Trades

```python
from src.models import Trade, TradeStatus
from datetime import datetime

# Open a trade
trade = Trade(
    trader_id=my_profile.trader_id,
    idea_id=idea.idea_id,  # Optional: link to your trade idea
    asset="BTC/USD",
    trade_type=TradeType.BUY,
    entry_price=51200.0,
    quantity=0.5,
    status=TradeStatus.OPEN,
    opened_at=datetime.utcnow()
)

api.record_trade(trade)

# Close the trade later
trade.status = TradeStatus.CLOSED
trade.exit_price=54800.0
trade.closed_at = datetime.utcnow()
trade.profit_loss = (54800.0 - 51200.0) * 0.5
trade.profit_loss_percentage = ((54800.0 - 51200.0) / 51200.0) * 100

api.record_trade(trade)
```

### Viewing Your Performance

```python
# Get your performance metrics
metrics = api.get_performance_metrics(
    my_profile.trader_id,
    period="1m"  # Last month
)

print(f"Performance (Last Month):")
print(f"Total Trades: {metrics.total_trades}")
print(f"Win Rate: {metrics.win_rate:.1f}%")
print(f"Total Return: {metrics.total_return:.2f}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
print(f"Consistency Score: {metrics.consistency_score:.1f}/100")
```

### Comparing with Others

```python
# Compare your performance with other traders
comparison = api.compare_trader_performance(
    [my_profile.trader_id, trader1.trader_id, trader2.trader_id],
    period="3m"
)

for trader_id, metrics in comparison.items():
    print(f"\nTrader {trader_id}:")
    print(f"  Return: {metrics.total_return:.2f}%")
    print(f"  Win Rate: {metrics.win_rate:.1f}%")
```

## Using Leaderboards

### Viewing Leaderboards

```python
# Top performers this month
top_performers = api.get_top_performers(period="1m", limit=10)

print("Top 10 Performers (This Month):")
for entry in top_performers:
    print(f"{entry.rank}. {entry.display_name} - Return: {entry.metric_value:.2f}%")
    if entry.verified:
        print("   ✓ Verified")

# Most consistent traders
consistent = api.get_most_consistent_traders(period="3m", limit=10)

print("\nMost Consistent Traders (3 Months):")
for entry in consistent:
    print(f"{entry.rank}. {entry.display_name} - Score: {entry.metric_value:.1f}")

# Rising stars
rising = api.get_rising_stars(limit=10)

print("\nRising Stars:")
for entry in rising:
    print(f"{entry.rank}. {entry.display_name}")
```

### Finding Your Rank

```python
# See where you rank
my_rank = api.get_trader_rank(
    my_profile.trader_id,
    metric="total_return",
    period="1m"
)

if my_rank:
    print(f"Your rank: #{my_rank}")
else:
    print("Keep trading to get ranked! (Need 10+ trades)")
```

## Sentiment Analysis

### Checking Asset Sentiment

```python
from datetime import timedelta

# Get current sentiment for BTC
btc_sentiment = api.get_asset_sentiment("BTC/USD")

print(f"BTC/USD Sentiment:")
print(f"Overall: {btc_sentiment.overall_sentiment.value}")
print(f"Score: {btc_sentiment.sentiment_score:.1f}/100")
print(f"Bullish: {btc_sentiment.bullish_count}")
print(f"Bearish: {btc_sentiment.bearish_count}")
print(f"24h Volume: {btc_sentiment.volume_24h} ideas")

# Get detailed distribution
distribution = api.get_sentiment_distribution("BTC/USD")
print(f"\nDistribution:")
print(f"Bullish: {distribution['bullish']:.1f}%")
print(f"Bearish: {distribution['bearish']:.1f}%")
print(f"Neutral: {distribution['neutral']:.1f}%")
```

### Finding Trending Assets

```python
# What's trending?
trending = api.get_trending_assets(limit=10)

print("Trending Assets:")
for sentiment in trending:
    print(f"{sentiment.asset}: {sentiment.overall_sentiment.value}")
    print(f"  Trending Score: {sentiment.trending_score:.1f}")
    print(f"  24h Ideas: {sentiment.volume_24h}")

# Most bullish assets
bullish_assets = api.get_bullish_assets(limit=5, min_volume=10)

print("\nMost Bullish Assets:")
for sentiment in bullish_assets:
    print(f"{sentiment.asset}: {sentiment.sentiment_score:.1f}")
```

### Sentiment History

```python
# View sentiment trend over time
history = api.get_sentiment_history("BTC/USD", days=7)

print("BTC/USD Sentiment History (7 days):")
for day in history:
    print(f"{day['date']}: Score {day['score']:.1f} ({day['bullish']} bullish, {day['bearish']} bearish)")
```

## Copy Trading

### Following a Top Trader

```python
# Find a trader to copy
top_trader = top_performers[0]  # Get from leaderboard

# Follow them first
api.follow_trader(my_profile.trader_id, top_trader.trader_id)

# Enable copy trading with settings
copy_settings = {
    "enabled": True,
    "copy_percentage": 25.0,  # Use 25% of capital
    "max_position_size": 1000.0,  # Max $1000 per trade
    "min_position_size": 50.0,  # Min $50 per trade
    "copy_stop_loss": True,
    "copy_take_profit": True,
    "slippage_tolerance": 0.5,  # 0.5% max slippage
    "asset_whitelist": ["BTC/USD", "ETH/USD"],  # Only copy these
}

relationship = api.enable_copy_trading(
    my_profile.trader_id,
    top_trader.trader_id,
    copy_settings
)

print("Copy trading enabled!")
```

### Advanced Copy Trading

```python
# Copy with filters
advanced_settings = {
    "enabled": True,
    "copy_percentage": 50.0,
    "asset_blacklist": ["DOGE/USD", "SHIB/USD"],  # Exclude meme coins
    "max_concurrent_positions": 5,  # Max 5 open positions
    "reverse_trades": False,  # Set to True to reverse signals
}

api.update_copy_settings(
    my_profile.trader_id,
    top_trader.trader_id,
    advanced_settings
)
```

### Monitoring Copy Trading

```python
# Check copy trading statistics
stats = api.get_copy_statistics(
    my_profile.trader_id,
    top_trader.trader_id
)

print("Copy Trading Stats:")
print(f"Total Copied: {stats['total_copied_trades']}")
print(f"Successful: {stats['successful_copies']}")
print(f"P&L: ${stats['total_profit_loss']:.2f}")
```

### Disabling Copy Trading

```python
# Stop copying (keep positions open)
api.disable_copy_trading(
    my_profile.trader_id,
    top_trader.trader_id,
    close_positions=False
)

# Or close all positions immediately
api.disable_copy_trading(
    my_profile.trader_id,
    top_trader.trader_id,
    close_positions=True
)
```

## Best Practices

### For Trade Ideas

1. **Be Specific**: Include clear entry, target, and stop loss levels
2. **Explain Your Analysis**: Help others learn from your reasoning
3. **Use Tags**: Make your ideas discoverable
4. **Update Ideas**: Keep followers informed of changes
5. **Respond to Comments**: Engage with the community

### For Performance Tracking

1. **Record All Trades**: Even losses help improve metrics
2. **Be Consistent**: Regular trading gives better metrics
3. **Link to Ideas**: Connect trades to your published ideas
4. **Review Metrics**: Check performance regularly

### For Copy Trading

1. **Start Small**: Use low copy percentages initially
2. **Diversify**: Copy multiple traders
3. **Set Limits**: Always use position size limits
4. **Monitor Regularly**: Check performance weekly
5. **Adjust Settings**: Refine based on results

### For Social Engagement

1. **Quality Over Quantity**: Post thoughtful ideas
2. **Be Respectful**: Constructive feedback only
3. **Give Credit**: Acknowledge others' insights
4. **Stay Active**: Regular engagement builds reputation

## Troubleshooting

### Common Issues

**"Trader not found"**
```python
# Make sure trader_id is correct
try:
    trader = api.get_trader(trader_id)
except NotFoundError:
    print("Trader doesn't exist")
```

**"Permission denied"**
```python
# Only idea owner can publish/update
if idea.trader_id != my_profile.trader_id:
    print("Can't modify someone else's idea")
```

**"Already following"**
```python
# Check if already following before following again
if not api.is_following(my_id, their_id):
    api.follow_trader(my_id, their_id)
```

**"Not ranked on leaderboard"**
- Need minimum trades (usually 10)
- Check with: `metrics.total_trades >= 10`

### Getting Help

```python
# Get system statistics
stats = api.get_system_stats()
print(f"Total traders: {stats['total_traders']}")
print(f"Total ideas: {stats['total_ideas']}")
```

## Examples

### Complete Workflow Example

```python
# 1. Create profile
trader = api.create_trader(
    username="demo_trader",
    display_name="Demo Trader"
)

# 2. Create and publish idea
idea = api.create_trade_idea(
    trader_id=trader.trader_id,
    title="ETH Long Setup",
    description="Ethereum bullish pattern",
    asset="ETH/USD",
    sentiment=SentimentType.BULLISH
)
api.publish_trade_idea(idea.idea_id, trader.trader_id)

# 3. Record trades
for i in range(15):
    trade = Trade(
        trader_id=trader.trader_id,
        asset="ETH/USD",
        trade_type=TradeType.BUY,
        status=TradeStatus.CLOSED,
        profit_loss=1000.0,
        profit_loss_percentage=5.0
    )
    api.record_trade(trade)

# 4. Check performance
metrics = api.get_performance_metrics(trader.trader_id)
print(f"Performance: {metrics.total_return:.2f}%")

# 5. View rank
rank = api.get_trader_rank(trader.trader_id)
print(f"Rank: #{rank}")

# 6. Check sentiment
sentiment = api.get_asset_sentiment("ETH/USD")
print(f"ETH Sentiment: {sentiment.overall_sentiment.value}")
```

## Next Steps

- Explore the [API Documentation](API_DOCUMENTATION.md)
- Read the [Architecture Guide](ARCHITECTURE.md)
- Review [Technical Requirements](TECHNICAL_REQUIREMENTS.md)
- Check the test suite for more examples

Happy Trading! 📈
