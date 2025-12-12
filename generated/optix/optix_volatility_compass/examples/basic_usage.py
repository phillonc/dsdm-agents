"""
Basic usage examples for Volatility Compass.
"""
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import VolatilityCompassAPI


def generate_sample_data():
    """Generate sample data for demonstration."""
    # Generate IV history with realistic pattern
    np.random.seed(42)
    iv_history = []
    base_iv = 30.0
    
    for i in range(252):
        # Add some trending and noise
        trend = np.sin(i / 50) * 5
        noise = np.random.normal(0, 2)
        iv = max(15, min(50, base_iv + trend + noise))
        iv_history.append(iv)
    
    # Generate price history
    price_history = []
    price = 150.0
    
    for i in range(100):
        change = np.random.normal(0.001, 0.015)
        price = price * (1 + change)
        price_history.append(price)
    
    # Create sample options chain
    base_date = datetime.now()
    options_chain = {
        'expirations': []
    }
    
    # Multiple expirations
    for days in [30, 60, 90]:
        exp_data = {
            'expiration_date': base_date + timedelta(days=days),
            'days_to_expiration': days,
            'atm_strike': 150.0,
            'atm_iv': 30.0 - (days * 0.01),
            'strikes': list(range(130, 171, 5)),
            'total_volume': 10000,
            'total_oi': 50000,
            'calls': [],
            'puts': []
        }
        
        # Generate options with skew
        for strike in range(140, 161, 5):
            call_iv = 30.0 - ((strike - 145) * 0.15)
            exp_data['calls'].append({
                'strike': strike,
                'iv': max(20, call_iv),
                'delta': 0.5 - ((strike - 150) * 0.05)
            })
            
            put_iv = 30.0 + ((150 - strike) * 0.25)
            exp_data['puts'].append({
                'strike': strike,
                'iv': min(45, put_iv),
                'delta': -0.5 + ((strike - 150) * 0.05)
            })
        
        options_chain['expirations'].append(exp_data)
    
    return iv_history, price_history, options_chain


def example_1_quick_metrics():
    """Example 1: Get quick IV metrics."""
    print("=" * 70)
    print("EXAMPLE 1: Quick IV Metrics")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    iv_history, price_history, _ = generate_sample_data()
    
    # Get quick metrics (no options chain needed)
    metrics = api.get_iv_metrics(
        symbol="AAPL",
        current_iv=35.0,
        iv_history=iv_history,
        price_history=price_history
    )
    
    print(f"\nSymbol: {metrics['symbol']}")
    print(f"Current IV: {metrics['current_iv']:.2f}%")
    print(f"IV Rank: {metrics['iv_rank']:.1f}%")
    print(f"IV Percentile: {metrics['iv_percentile']:.1f}%")
    print(f"Volatility Condition: {metrics['condition']}")
    print(f"\nHistorical Volatility:")
    print(f"  30-day: {metrics['historical_volatility']['30d']:.2f}%")
    print(f"  60-day: {metrics['historical_volatility']['60d']:.2f}%")
    print(f"  90-day: {metrics['historical_volatility']['90d']:.2f}%")
    print(f"IV/HV Ratio: {metrics['iv_hv_ratio']:.2f}")
    print(f"\n52-Week Range: {metrics['extremes_52w']['min']:.1f}% - {metrics['extremes_52w']['max']:.1f}%")


def example_2_trading_strategies():
    """Example 2: Get trading strategy recommendations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Trading Strategy Recommendations")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    iv_history, price_history, options_chain = generate_sample_data()
    
    # Simulate high IV scenario
    iv_history[0] = 42.0
    
    strategies = api.get_trading_strategies(
        symbol="AAPL",
        current_iv=42.0,
        iv_history=iv_history,
        price_history=price_history,
        options_chain=options_chain
    )
    
    print(f"\nFound {len(strategies)} strategies\n")
    
    for i, strategy in enumerate(strategies[:3], 1):
        print(f"Strategy {i}: {strategy['name']}")
        print(f"Type: {strategy['type']}")
        print(f"Confidence: {strategy['confidence']:.0f}%")
        print(f"Risk Level: {strategy['risk_level']}")
        print(f"Description: {strategy['description']}")
        print("\nReasoning:")
        for reason in strategy['reasoning']:
            print(f"  • {reason}")
        print("\nSuggested Actions:")
        for action in strategy['suggested_actions'][:3]:
            print(f"  ✓ {action}")
        print()


def example_3_watchlist_analysis():
    """Example 3: Analyze a watchlist."""
    print("=" * 70)
    print("EXAMPLE 3: Watchlist Analysis")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    
    # Create data for multiple symbols with different IV conditions
    symbols_data = {}
    
    for symbol, iv_level in [('AAPL', 42), ('MSFT', 18), ('GOOGL', 30), ('TSLA', 55)]:
        iv_history, price_history, _ = generate_sample_data()
        iv_history[0] = iv_level
        
        symbols_data[symbol] = {
            'current_iv': iv_level,
            'iv_history': iv_history,
            'price_history': price_history,
            'previous_iv': iv_level - 2
        }
    
    analysis = api.analyze_watchlist("Tech Portfolio", symbols_data)
    
    print(f"\nWatchlist: {analysis['watchlist_name']}")
    print(f"Total Symbols: {analysis['total_symbols']}")
    print(f"\nSummary:")
    print(f"  Average IV Rank: {analysis['summary']['average_iv_rank']:.1f}%")
    print(f"  Average IV Percentile: {analysis['summary']['average_iv_percentile']:.1f}%")
    print(f"  High IV Symbols: {analysis['summary']['high_iv_count']}")
    print(f"  Low IV Symbols: {analysis['summary']['low_iv_count']}")
    
    print("\n📈 Premium Selling Opportunities (High IV):")
    for opp in analysis['opportunities']['premium_selling']:
        print(f"  {opp['symbol']}: IV Rank {opp['iv_rank']:.1f}%")
    
    print("\n📉 Premium Buying Opportunities (Low IV):")
    for opp in analysis['opportunities']['premium_buying']:
        print(f"  {opp['symbol']}: IV Rank {opp['iv_rank']:.1f}%")
    
    if analysis['alerts']:
        print(f"\n⚠️  Active Alerts: {len(analysis['alerts'])}")
        for alert in analysis['alerts'][:3]:
            print(f"  [{alert['severity'].upper()}] {alert['symbol']}: {alert['message']}")


def example_4_volatility_alerts():
    """Example 4: Volatility alerts."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Volatility Alerts")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    iv_history, price_history, _ = generate_sample_data()
    
    # Simulate IV spike
    current_iv = 40.0
    previous_iv = 28.0
    
    alerts = api.get_volatility_alerts(
        symbol="AAPL",
        current_iv=current_iv,
        iv_history=iv_history,
        price_history=price_history,
        previous_iv=previous_iv
    )
    
    print(f"\nChecking for alerts... Found {len(alerts)} alert(s)\n")
    
    for alert in alerts:
        severity_icon = {
            'low': 'ℹ️',
            'medium': '⚠️',
            'high': '🔴',
            'critical': '🚨'
        }.get(alert['severity'], '•')
        
        print(f"{severity_icon} [{alert['severity'].upper()}] {alert['type']}")
        print(f"   {alert['message']}")
        if alert['change_percent'] != 0:
            print(f"   Change: {alert['change_percent']:+.1f}%")
        print()


def example_5_skew_and_term_structure():
    """Example 5: Volatility skew and term structure."""
    print("=" * 70)
    print("EXAMPLE 5: Skew and Term Structure Analysis")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    iv_history, price_history, options_chain = generate_sample_data()
    
    # Skew analysis
    print("\n📊 Volatility Skew Analysis:")
    skew_analyses = api.get_skew_analysis("AAPL", options_chain)
    
    for skew in skew_analyses:
        print(f"\n  Expiration: {skew['days_to_expiration']} DTE")
        print(f"  Skew Type: {skew['skew_type']}")
        print(f"  Put/Call IV Ratio: {skew['put_call_ratio']:.2f}")
        print(f"  ATM IV: {skew['atm_iv']:.1f}%")
    
    # Term structure
    print("\n\n📈 Volatility Term Structure:")
    term_structure = api.get_term_structure("AAPL", 150.0, options_chain)
    
    print(f"  Structure Shape: {term_structure['structure_shape']}")
    print(f"  Front Month IV: {term_structure['front_month_iv']:.1f}%")
    print(f"  Back Month IV: {term_structure['back_month_iv']:.1f}%")
    print(f"  Slope: {term_structure['slope']:.4f}")
    
    print("\n  Term Points:")
    for point in term_structure['term_points']:
        print(f"    {point['days_to_expiration']:3d} DTE: {point['atm_iv']:5.1f}% IV")


def example_6_complete_analysis():
    """Example 6: Complete volatility analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Complete Volatility Analysis Report")
    print("=" * 70)
    
    api = VolatilityCompassAPI()
    iv_history, price_history, options_chain = generate_sample_data()
    
    # Get complete analysis
    analysis = api.get_volatility_analysis(
        symbol="AAPL",
        current_iv=35.0,
        iv_history=iv_history,
        price_history=price_history,
        options_chain=options_chain,
        previous_iv=32.0
    )
    
    print(f"\n🎯 Complete Analysis for {analysis['symbol']}")
    print(f"   Generated: {analysis['timestamp']}")
    
    print("\n📊 Core Metrics:")
    m = analysis['metrics']
    print(f"   Current IV: {m['current_iv']:.2f}%")
    print(f"   IV Rank: {m['iv_rank']:.1f}%")
    print(f"   IV Percentile: {m['iv_percentile']:.1f}%")
    print(f"   Condition: {m['condition']}")
    
    print("\n💡 Primary Strategy:")
    if analysis['strategies']:
        s = analysis['strategies'][0]
        print(f"   {s['name']} (Confidence: {s['confidence']:.0f}%)")
        print(f"   {s['description']}")
    
    print("\n📈 Term Structure:")
    ts = analysis['term_structure']
    print(f"   Shape: {ts['shape']}")
    print(f"   Front: {ts['front_month_iv']:.1f}% | Back: {ts['back_month_iv']:.1f}%")
    
    if analysis['alerts']:
        print(f"\n⚠️  Alerts: {len(analysis['alerts'])}")
        for alert in analysis['alerts']:
            print(f"   • {alert['message']}")
    else:
        print("\n✓ No active alerts")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  VOLATILITY COMPASS - USAGE EXAMPLES".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    
    try:
        example_1_quick_metrics()
        example_2_trading_strategies()
        example_3_watchlist_analysis()
        example_4_volatility_alerts()
        example_5_skew_and_term_structure()
        example_6_complete_analysis()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
