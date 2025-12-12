"""
Complete demonstration of the Collective Intelligence Network.

This example shows a complete workflow from trader creation through
all major features of the system.
"""

from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collective_intelligence_api import CollectiveIntelligenceAPI
from src.models import TradeType, Trade, TradeStatus, SentimentType


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    """Run the complete demo."""
    print_section("OPTIX Collective Intelligence Network - Demo")
    
    # Initialize API
    api = CollectiveIntelligenceAPI()
    
    # ==================== TRADER SETUP ====================
    print_section("1. Creating Trader Profiles")
    
    # Create multiple traders
    traders = []
    for i in range(5):
        trader = api.create_trader(
            username=f"trader_{i+1}",
            display_name=f"Trader {i+1}",
            bio=f"Professional trader specializing in {'crypto' if i < 3 else 'forex'}",
            tags=["crypto" if i < 3 else "forex", "technical-analysis"]
        )
        traders.append(trader)
        print(f"✓ Created {trader.display_name} (@{trader.username})")
    
    # ==================== SOCIAL CONNECTIONS ====================
    print_section("2. Building Social Network")
    
    # Traders follow each other
    api.follow_trader(traders[0].trader_id, traders[1].trader_id)
    api.follow_trader(traders[0].trader_id, traders[2].trader_id)
    api.follow_trader(traders[1].trader_id, traders[0].trader_id)
    api.follow_trader(traders[2].trader_id, traders[0].trader_id)
    api.follow_trader(traders[3].trader_id, traders[0].trader_id)
    
    print(f"✓ {traders[0].display_name} now has {len(api.get_followers(traders[0].trader_id))} followers")
    print(f"✓ {traders[0].display_name} is following {len(api.get_following(traders[0].trader_id))} traders")
    
    # ==================== TRADE IDEAS ====================
    print_section("3. Creating and Publishing Trade Ideas")
    
    # Create trade ideas
    ideas = []
    
    # Bullish BTC idea
    idea1 = api.create_trade_idea(
        trader_id=traders[0].trader_id,
        title="Bitcoin Breaking Out - Long Setup",
        description="BTC showing strong bullish momentum with ascending triangle pattern. Target $55k.",
        asset="BTC/USD",
        trade_type=TradeType.BUY,
        entry_price=50000.0,
        target_price=55000.0,
        stop_loss=48000.0,
        timeframe="4H",
        confidence=80.0,
        sentiment=SentimentType.BULLISH,
        tags=["bitcoin", "breakout", "long"]
    )
    api.publish_trade_idea(idea1.idea_id, traders[0].trader_id)
    ideas.append(idea1)
    print(f"✓ Published: {idea1.title}")
    
    # Bullish ETH idea
    idea2 = api.create_trade_idea(
        trader_id=traders[1].trader_id,
        title="Ethereum - Support Level Hold",
        description="ETH holding support at $3000. Expecting bounce to $3500.",
        asset="ETH/USD",
        trade_type=TradeType.BUY,
        entry_price=3000.0,
        target_price=3500.0,
        stop_loss=2900.0,
        sentiment=SentimentType.BULLISH,
        tags=["ethereum", "support", "long"]
    )
    api.publish_trade_idea(idea2.idea_id, traders[1].trader_id)
    ideas.append(idea2)
    print(f"✓ Published: {idea2.title}")
    
    # Bearish BTC idea
    idea3 = api.create_trade_idea(
        trader_id=traders[2].trader_id,
        title="Bitcoin Overbought - Short Setup",
        description="BTC RSI at 75, looking for correction to $48k.",
        asset="BTC/USD",
        trade_type=TradeType.SHORT,
        entry_price=51000.0,
        target_price=48000.0,
        stop_loss=52000.0,
        sentiment=SentimentType.BEARISH,
        tags=["bitcoin", "short", "overbought"]
    )
    api.publish_trade_idea(idea3.idea_id, traders[2].trader_id)
    ideas.append(idea3)
    print(f"✓ Published: {idea3.title}")
    
    # ==================== ENGAGEMENT ====================
    print_section("4. Community Engagement")
    
    # Like ideas
    api.like_idea(idea1.idea_id, traders[1].trader_id)
    api.like_idea(idea1.idea_id, traders[2].trader_id)
    api.like_idea(idea1.idea_id, traders[3].trader_id)
    
    # Add comments
    api.add_comment(idea1.idea_id, traders[1].trader_id, "Great analysis! I'm in on this trade.")
    api.add_comment(idea1.idea_id, traders[2].trader_id, "What about the resistance at $52k?")
    api.add_comment(idea2.idea_id, traders[0].trader_id, "I like this setup. Strong support level.")
    
    # Share ideas
    api.share_idea(idea1.idea_id)
    api.share_idea(idea1.idea_id)
    
    print(f"✓ {idea1.title}: {idea1.likes_count} likes, {idea1.comments_count} comments")
    
    # ==================== PERFORMANCE TRACKING ====================
    print_section("5. Recording Trades and Performance")
    
    # Simulate trading activity for trader 1 (winning trader)
    print(f"\nRecording trades for {traders[0].display_name}...")
    for i in range(20):
        is_winner = i < 15  # 75% win rate
        trade = Trade(
            trader_id=traders[0].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            entry_price=50000.0,
            exit_price=52000.0 if is_winner else 49000.0,
            quantity=1.0,
            status=TradeStatus.CLOSED,
            opened_at=datetime.utcnow() - timedelta(days=i),
            closed_at=datetime.utcnow() - timedelta(days=i, hours=12),
            profit_loss=2000.0 if is_winner else -1000.0,
            profit_loss_percentage=4.0 if is_winner else -2.0
        )
        api.record_trade(trade)
    
    # Simulate for trader 2 (moderate performer)
    print(f"Recording trades for {traders[1].display_name}...")
    for i in range(15):
        is_winner = i < 9  # 60% win rate
        trade = Trade(
            trader_id=traders[1].trader_id,
            asset="ETH/USD",
            trade_type=TradeType.BUY,
            status=TradeStatus.CLOSED,
            profit_loss=1500.0 if is_winner else -800.0,
            profit_loss_percentage=3.5 if is_winner else -1.8
        )
        api.record_trade(trade)
    
    # Get performance metrics
    metrics1 = api.get_performance_metrics(traders[0].trader_id)
    metrics2 = api.get_performance_metrics(traders[1].trader_id)
    
    print(f"\n{traders[0].display_name} Performance:")
    print(f"  Total Trades: {metrics1.total_trades}")
    print(f"  Win Rate: {metrics1.win_rate:.1f}%")
    print(f"  Total Return: {metrics1.total_return:.2f}%")
    print(f"  Sharpe Ratio: {metrics1.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {metrics1.max_drawdown:.2f}%")
    
    print(f"\n{traders[1].display_name} Performance:")
    print(f"  Total Trades: {metrics2.total_trades}")
    print(f"  Win Rate: {metrics2.win_rate:.1f}%")
    print(f"  Total Return: {metrics2.total_return:.2f}%")
    
    # ==================== LEADERBOARDS ====================
    print_section("6. Leaderboard Rankings")
    
    # Get leaderboard
    leaderboard = api.get_leaderboard(metric="total_return", limit=10)
    
    print("\nTop Traders by Total Return:")
    for entry in leaderboard[:3]:
        print(f"  {entry.rank}. {entry.display_name}")
        print(f"     Return: {entry.metric_value:.2f}%")
        print(f"     Score: {entry.score:.1f}")
    
    # Check rank
    rank = api.get_trader_rank(traders[0].trader_id)
    print(f"\n{traders[0].display_name} is ranked #{rank}")
    
    # ==================== SENTIMENT ANALYSIS ====================
    print_section("7. Community Sentiment Analysis")
    
    # Get BTC sentiment
    btc_sentiment = api.get_asset_sentiment("BTC/USD")
    
    print(f"\nBTC/USD Sentiment:")
    print(f"  Overall: {btc_sentiment.overall_sentiment.value.upper()}")
    print(f"  Score: {btc_sentiment.sentiment_score:.1f}/100")
    print(f"  Bullish Ideas: {btc_sentiment.bullish_count}")
    print(f"  Bearish Ideas: {btc_sentiment.bearish_count}")
    print(f"  24h Volume: {btc_sentiment.volume_24h} ideas")
    
    # Get distribution
    distribution = api.get_sentiment_distribution("BTC/USD")
    print(f"\nSentiment Distribution:")
    print(f"  Bullish: {distribution['bullish']:.1f}%")
    print(f"  Bearish: {distribution['bearish']:.1f}%")
    print(f"  Neutral: {distribution['neutral']:.1f}%")
    
    # Get trending assets
    trending = api.get_trending_assets(limit=5)
    print(f"\nTrending Assets:")
    for sentiment in trending:
        print(f"  {sentiment.asset}: {sentiment.overall_sentiment.value}")
    
    # ==================== COPY TRADING ====================
    print_section("8. Copy Trading Setup")
    
    # Follower wants to copy the top trader
    follower = traders[4]
    leader = traders[0]  # Best performer
    
    # Follow first
    api.follow_trader(follower.trader_id, leader.trader_id)
    
    # Enable copy trading
    copy_settings = {
        "enabled": True,
        "copy_percentage": 50.0,
        "max_position_size": 1000.0,
        "copy_stop_loss": True,
        "asset_whitelist": ["BTC/USD", "ETH/USD"]
    }
    
    relationship = api.enable_copy_trading(
        follower.trader_id,
        leader.trader_id,
        copy_settings
    )
    
    print(f"\n✓ {follower.display_name} is now copying {leader.display_name}")
    print(f"  Copy Percentage: {copy_settings['copy_percentage']}%")
    print(f"  Max Position: ${copy_settings['max_position_size']}")
    print(f"  Assets: {', '.join(copy_settings['asset_whitelist'])}")
    
    # ==================== DISCOVERY ====================
    print_section("9. Discovery Features")
    
    # Search traders
    crypto_traders = api.search_traders(query="crypto", limit=10)
    print(f"\nFound {len(crypto_traders)} traders interested in crypto")
    
    # Search ideas
    btc_ideas = api.search_trade_ideas(asset="BTC/USD", limit=10)
    print(f"Found {len(btc_ideas)} ideas for BTC/USD")
    
    # Get trending ideas
    trending_ideas = api.get_trending_ideas(limit=5)
    print(f"\nTrending Ideas:")
    for idea in trending_ideas:
        print(f"  • {idea.title}")
        print(f"    Engagement: {idea.likes_count} likes, {idea.comments_count} comments")
    
    # ==================== SYSTEM STATS ====================
    print_section("10. System Statistics")
    
    stats = api.get_system_stats()
    print(f"\nSystem Overview:")
    print(f"  Total Traders: {stats['total_traders']}")
    print(f"  Total Ideas: {stats['total_ideas']}")
    print(f"  Total Comments: {stats['total_comments']}")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Active Copy Relationships: {stats['active_copy_relationships']}")
    
    # ==================== SUMMARY ====================
    print_section("Demo Complete!")
    
    print("\nThe Collective Intelligence Network provides:")
    print("  ✓ Social trading with followers and following")
    print("  ✓ Trade idea sharing and collaboration")
    print("  ✓ Performance tracking and analytics")
    print("  ✓ Competitive leaderboards")
    print("  ✓ Community sentiment analysis")
    print("  ✓ Automated copy trading")
    print("  ✓ Discovery and search features")
    
    print("\nNext Steps:")
    print("  • Explore the API documentation")
    print("  • Review the test suite for more examples")
    print("  • Integrate with your trading platform")
    print("  • Build your trading community!")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
