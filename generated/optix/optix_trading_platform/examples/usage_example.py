"""
Example usage of the Options Flow Intelligence Engine.

This demonstrates the main features:
- Processing options trades
- Detecting sweeps, blocks, and dark pool activity
- Analyzing market maker positioning
- Subscribing to real-time alerts
"""
from datetime import datetime
from decimal import Decimal

from src.options_flow_intelligence import OptionsFlowIntelligence
from src.models import OptionsTrade, OrderType, TradeType


def create_sample_trade(
    symbol: str,
    strike: Decimal,
    order_type: OrderType,
    size: int,
    premium: Decimal,
    exchange: str = "CBOE",
) -> OptionsTrade:
    """Create a sample options trade."""
    return OptionsTrade(
        trade_id=f"TRADE_{datetime.now().timestamp()}",
        symbol=f"{symbol}250117{'C' if order_type == OrderType.CALL else 'P'}{int(strike * 1000):08d}",
        underlying_symbol=symbol,
        order_type=order_type,
        strike=strike,
        expiration=datetime(2025, 1, 17),
        premium=premium,
        size=size,
        price=strike + Decimal('2.50'),
        timestamp=datetime.now(),
        trade_type=TradeType.REGULAR,
        exchange=exchange,
        execution_side="ask",
        is_aggressive=True,
        underlying_price=strike - Decimal('2.00'),
        open_interest=5000,
    )


def alert_callback(alert):
    """Callback for real-time alerts."""
    print(f"\n🔔 REAL-TIME ALERT:")
    print(f"   Type: {alert.alert_type.value}")
    print(f"   Severity: {alert.severity.value}")
    print(f"   {alert.title}")
    print(f"   {alert.description}")


def main():
    """Run example scenarios."""
    print("=" * 80)
    print("OPTIX Trading Platform - Options Flow Intelligence")
    print("=" * 80)
    
    # Initialize engine
    engine = OptionsFlowIntelligence(enable_alerts=True)
    
    # Subscribe to real-time alerts
    engine.subscribe_to_alerts(alert_callback)
    
    print("\n1. SIMULATING OPTIONS SWEEP...")
    print("-" * 80)
    
    # Simulate a sweep across multiple exchanges
    for exchange in ["CBOE", "PHLX", "ISE", "AMEX", "NASDAQ"]:
        trade = create_sample_trade(
            symbol="AAPL",
            strike=Decimal('150.00'),
            order_type=OrderType.CALL,
            size=100,
            premium=Decimal('5.50'),
            exchange=exchange,
        )
        
        result = engine.process_trade(trade)
        print(f"   Processed trade on {exchange}: {result['trade_id']}")
    
    print("\n2. SIMULATING BLOCK TRADE...")
    print("-" * 80)
    
    # Simulate institutional block trade
    block_trade = create_sample_trade(
        symbol="TSLA",
        strike=Decimal('200.00'),
        order_type=OrderType.CALL,
        size=750,
        premium=Decimal('12.50'),
    )
    block_trade.execution_side = "mid"
    block_trade.is_opening = True
    
    result = engine.process_trade(block_trade)
    print(f"   Block trade processed: {result['trade_id']}")
    print(f"   Detections: {result['detections']}")
    
    print("\n3. SIMULATING DARK POOL ACTIVITY...")
    print("-" * 80)
    
    # Simulate dark pool print
    dark_pool_trade = create_sample_trade(
        symbol="NVDA",
        strike=Decimal('500.00'),
        order_type=OrderType.PUT,
        size=300,
        premium=Decimal('8.75'),
        exchange="EDGX",
    )
    dark_pool_trade.is_aggressive = False
    
    result = engine.process_trade(dark_pool_trade)
    print(f"   Dark pool trade processed: {result['trade_id']}")
    
    print("\n4. SIMULATING AGGRESSIVE CALL BUYING...")
    print("-" * 80)
    
    # Simulate aggressive call buying pattern
    for i in range(6):
        trade = create_sample_trade(
            symbol="SPY",
            strike=Decimal('450.00'),
            order_type=OrderType.CALL,
            size=200 + i * 25,
            premium=Decimal('4.50'),
        )
        trade.above_ask = True
        
        result = engine.process_trade(trade)
        if result['patterns']:
            print(f"   Pattern detected: {result['patterns']}")
    
    print("\n5. ORDER FLOW SUMMARY...")
    print("-" * 80)
    
    for symbol in ["AAPL", "TSLA", "NVDA", "SPY"]:
        summary = engine.get_order_flow_summary(symbol)
        if summary['total_trades'] > 0:
            print(f"\n   {symbol}:")
            print(f"      Total Trades: {summary['total_trades']}")
            print(f"      Total Premium: ${float(summary['total_premium']):,.0f}")
            print(f"      Sentiment: {summary['sentiment']}")
            print(f"      Call/Put Ratio: {summary['call_put_ratio']['premium']}")
    
    print("\n6. MARKET MAKER POSITIONING...")
    print("-" * 80)
    
    for symbol in ["AAPL", "SPY"]:
        position = engine.calculate_market_maker_position(symbol)
        print(f"\n   {symbol}:")
        print(f"      Net Delta: {position.net_delta}")
        print(f"      Net Gamma: {position.net_gamma}")
        print(f"      Position Bias: {position.position_bias.value}")
        print(f"      Hedge Pressure: {position.hedge_pressure}")
        print(f"      Gamma Squeeze Risk: {position.is_gamma_squeeze_risk}")
    
    print("\n7. INSTITUTIONAL FLOW...")
    print("-" * 80)
    
    inst_flow = engine.get_institutional_flow()
    print(f"   Total Institutional Trades: {inst_flow['total_trades']}")
    print(f"   Total Premium: ${float(inst_flow['total_premium']):,.0f}")
    print(f"   Unique Symbols: {inst_flow['unique_symbols']}")
    
    if inst_flow['symbols']:
        print("\n   Top Institutional Flow:")
        for sym_data in inst_flow['symbols'][:5]:
            print(f"      {sym_data['symbol']}: ${float(sym_data['premium']):,.0f} ({sym_data['sentiment']})")
    
    print("\n8. ACTIVE ALERTS...")
    print("-" * 80)
    
    alerts = engine.get_active_alerts(min_severity='medium')
    print(f"   Total Active Alerts: {len(alerts)}")
    
    for alert in alerts[:5]:
        print(f"\n   Alert: {alert['title']}")
        print(f"      Severity: {alert['severity']}")
        print(f"      Confidence: {alert['confidence_score']:.1%}")
        print(f"      Premium: ${float(alert['total_premium']):,.0f}" if alert['total_premium'] else "")
    
    print("\n9. ENGINE STATISTICS...")
    print("-" * 80)
    
    stats = engine.get_statistics()
    print(f"   Trades Processed: {stats['engine']['trades_processed']}")
    print(f"   Sweeps Detected: {stats['engine']['sweeps_detected']}")
    print(f"   Blocks Detected: {stats['engine']['blocks_detected']}")
    print(f"   Dark Pools Detected: {stats['engine']['dark_pools_detected']}")
    print(f"   Patterns Detected: {stats['engine']['patterns_detected']}")
    print(f"   Alerts Created: {stats['engine']['alerts_created']}")
    
    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
