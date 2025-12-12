"""
OPTIX Visual Strategy Builder - Usage Examples

This file demonstrates how to use the Visual Strategy Builder API
to create and analyze options strategies.
"""

from datetime import datetime, timedelta
from src.api.strategy_api import StrategyAPI


def example_1_create_iron_condor():
    """Example 1: Create an Iron Condor strategy"""
    print("=" * 60)
    print("EXAMPLE 1: Creating an Iron Condor Strategy")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create Iron Condor on SPY
    expiration = (datetime.utcnow() + timedelta(days=45)).isoformat()
    
    result = api.create_from_template(
        template_name='IRON_CONDOR',
        underlying_symbol='SPY',
        underlying_price=450.0,
        expiration_date=expiration,
        put_short_strike=445.0,
        put_long_strike=440.0,
        call_short_strike=455.0,
        call_long_strike=460.0
    )
    
    print(f"\nStrategy Created: {result['strategy']['name']}")
    print(f"Number of Legs: {result['strategy']['num_legs']}")
    print(f"Total Cost/Credit: ${result['strategy']['total_cost']:.2f}")
    print(f"Strategy Type: {'Credit' if result['strategy']['is_credit'] else 'Debit'}")
    
    # Get risk metrics
    print("\n--- Risk Metrics ---")
    risk_metrics = result['risk_metrics']
    print(f"Max Profit: ${risk_metrics['risk_reward']['max_profit']:.2f}")
    print(f"Max Loss: ${risk_metrics['risk_reward']['max_loss']:.2f}")
    print(f"Risk/Reward Ratio: {risk_metrics['risk_reward']['risk_reward_ratio']:.2f}")
    print(f"Probability of Profit: {risk_metrics['probability_metrics']['probability_of_profit_pct']:.1f}%")
    
    # Get Greeks
    print("\n--- Greeks ---")
    greeks = result['greeks']
    print(f"Delta: {greeks['total_delta']:.2f}")
    print(f"Theta (daily): {greeks['total_theta']:.2f}")
    print(f"Vega: {greeks['total_vega']:.2f}")
    
    return api


def example_2_custom_strategy():
    """Example 2: Build a custom strategy with drag-and-drop simulation"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Building a Custom Strategy")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create custom strategy
    api.create_custom_strategy(
        name="My Bull Call Spread",
        description="Custom bull call spread on AAPL"
    )
    
    expiration = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    # Add first leg: Buy 180 Call
    print("\n1. Adding Long Call at $180...")
    api.add_option_leg(
        symbol="AAPL_C180",
        underlying_symbol="AAPL",
        option_type="CALL",
        strike_price=180.0,
        expiration_date=expiration,
        quantity=1,
        position="LONG",
        premium=8.50,
        underlying_price=182.0,
        implied_volatility=0.28
    )
    
    # Add second leg: Sell 185 Call
    print("2. Adding Short Call at $185...")
    result = api.add_option_leg(
        symbol="AAPL_C185",
        underlying_symbol="AAPL",
        option_type="CALL",
        strike_price=185.0,
        expiration_date=expiration,
        quantity=1,
        position="SHORT",
        premium=5.75,
        underlying_price=182.0,
        implied_volatility=0.26
    )
    
    print(f"\nStrategy Summary:")
    summary = result['strategy_summary']
    print(f"Total Cost: ${summary['total_cost']:.2f}")
    print(f"Number of Legs: {summary['num_legs']}")
    
    # Analyze the strategy
    print("\n--- Complete Analysis ---")
    analysis = api.get_strategy_analysis()
    
    print(f"Max Profit: ${analysis['risk_reward']['max_profit']:.2f}")
    print(f"Max Loss: ${analysis['risk_reward']['max_loss']:.2f}")
    print(f"Breakeven Points: {analysis['payoff_diagram']['breakeven_points']}")
    
    return api


def example_3_scenario_analysis():
    """Example 3: Perform what-if scenario analysis"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: What-If Scenario Analysis")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create a straddle
    expiration = (datetime.utcnow() + timedelta(days=60)).isoformat()
    
    api.create_from_template(
        template_name='STRADDLE',
        underlying_symbol='TSLA',
        underlying_price=250.0,
        expiration_date=expiration
    )
    
    print("Created Long Straddle on TSLA at $250")
    
    # Run scenarios
    scenarios = [
        (240.0, "Down 4%"),
        (250.0, "Unchanged"),
        (260.0, "Up 4%"),
        (270.0, "Up 8%")
    ]
    
    print("\n--- Scenario Analysis (30 days passed) ---")
    print(f"{'Scenario':<15} {'Stock Price':<15} {'P&L':<15} {'Delta':<10}")
    print("-" * 60)
    
    for price, description in scenarios:
        scenario = api.run_scenario_analysis(
            scenario_price=price,
            days_passed=30
        )
        
        print(f"{description:<15} ${price:<14.2f} ${scenario['current_pnl']:<14.2f} {scenario['greeks']['total_delta']:<9.2f}")
    
    return api


def example_4_greeks_analysis():
    """Example 4: Detailed Greeks analysis"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Detailed Greeks Analysis")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create a butterfly spread
    expiration = (datetime.utcnow() + timedelta(days=45)).isoformat()
    
    result = api.create_from_template(
        template_name='BUTTERFLY',
        underlying_symbol='SPX',
        underlying_price=4500.0,
        expiration_date=expiration,
        lower_strike=4450.0,
        middle_strike=4500.0,
        upper_strike=4550.0
    )
    
    print("Created Butterfly Spread on SPX")
    
    # Get detailed Greeks analysis
    greeks_analysis = api.get_greeks_analysis()
    
    print("\n--- Current Greeks ---")
    current = greeks_analysis['current_greeks']
    print(f"Delta: {current['total_delta']:.2f}")
    print(f"Gamma: {current['total_gamma']:.4f}")
    print(f"Theta: {current['total_theta']:.2f}")
    print(f"Vega: {current['total_vega']:.2f}")
    print(f"Rho: {current['total_rho']:.2f}")
    
    print("\n--- Risk Profile ---")
    risk_profile = greeks_analysis['risk_profile']
    for key, value in risk_profile.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n--- Greeks Interpretations ---")
    for greek, interp in greeks_analysis['interpretations'].items():
        print(f"\n{greek.upper()}:")
        print(f"  Value: {interp['value']:.4f}")
        print(f"  Meaning: {interp['meaning']}")
        print(f"  Description: {interp['description']}")
    
    return api


def example_5_payoff_visualization():
    """Example 5: Generate payoff diagram data"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Payoff Diagram Data")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create a strangle
    expiration = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    api.create_from_template(
        template_name='STRANGLE',
        underlying_symbol='NVDA',
        underlying_price=500.0,
        expiration_date=expiration,
        put_strike=480.0,
        call_strike=520.0
    )
    
    print("Created Long Strangle on NVDA")
    
    # Get payoff diagram
    payoff = api.get_payoff_diagram(min_price=450.0, max_price=550.0)
    
    print(f"\nBreakeven Points: {payoff['breakeven_points']}")
    print(f"Max Profit: ${payoff['max_profit']['value']:.2f} at ${payoff['max_profit']['price']:.2f}")
    print(f"Max Loss: ${payoff['max_loss']['value']:.2f} at ${payoff['max_loss']['price']:.2f}")
    print(f"Initial Cost: ${payoff['initial_cost']:.2f}")
    
    # Display sample payoff values
    print("\n--- Sample Payoff Values ---")
    exp_payoff = payoff['expiration_payoff']
    prices = exp_payoff['prices']
    pnl = exp_payoff['pnl']
    
    # Print every 20th point
    step = len(prices) // 5
    print(f"{'Price':<12} {'P&L at Expiration':<20}")
    print("-" * 32)
    for i in range(0, len(prices), step):
        print(f"${prices[i]:<11.2f} ${pnl[i]:<19.2f}")
    
    return api


def example_6_time_decay_and_volatility():
    """Example 6: Analyze time decay and volatility impact"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Time Decay & Volatility Analysis")
    print("=" * 60)
    
    api = StrategyAPI()
    
    # Create strategy
    expiration = (datetime.utcnow() + timedelta(days=90)).isoformat()
    
    api.create_custom_strategy("Short Straddle Analysis")
    
    api.add_option_leg(
        symbol="AAPL_C175",
        underlying_symbol="AAPL",
        option_type="CALL",
        strike_price=175.0,
        expiration_date=expiration,
        quantity=1,
        position="SHORT",
        premium=7.50,
        underlying_price=175.0,
        implied_volatility=0.30
    )
    
    api.add_option_leg(
        symbol="AAPL_P175",
        underlying_symbol="AAPL",
        option_type="PUT",
        strike_price=175.0,
        expiration_date=expiration,
        quantity=1,
        position="SHORT",
        premium=7.00,
        underlying_price=175.0,
        implied_volatility=0.30
    )
    
    print("Created Short Straddle on AAPL")
    
    # Time decay analysis
    print("\n--- Time Decay Analysis ---")
    time_decay = api.get_time_decay_analysis(
        underlying_price=175.0,
        days_points=[0, 15, 30, 45, 60, 75, 90]
    )
    
    print(f"{'Days Passed':<15} {'Days Remaining':<15} {'P&L':<15}")
    print("-" * 45)
    for point in time_decay['time_series']:
        print(f"{point['days_passed']:<15} {point['days_remaining']:<15} ${point['pnl']:<14.2f}")
    
    # Volatility analysis
    print("\n--- Volatility Impact Analysis ---")
    vol_analysis = api.get_volatility_analysis(
        underlying_price=175.0,
        iv_changes=[-0.10, -0.05, 0.0, 0.05, 0.10]
    )
    
    print(f"{'IV Change':<15} {'P&L':<15} {'P&L Change':<15}")
    print("-" * 45)
    for point in vol_analysis['volatility_series']:
        print(f"{point['iv_change_pct']:+.1f}%{'':<10} ${point['pnl']:<14.2f} ${point['pnl_change']:<14.2f}")
    
    return api


def example_7_export_import():
    """Example 7: Export and import strategies"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Export and Import Strategies")
    print("=" * 60)
    
    # Create a strategy
    api1 = StrategyAPI()
    
    expiration = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    api1.create_from_template(
        template_name='BULL_CALL_SPREAD',
        underlying_symbol='QQQ',
        underlying_price=380.0,
        expiration_date=expiration,
        long_strike=375.0,
        short_strike=385.0
    )
    
    print("Created Bull Call Spread on QQQ")
    
    # Export the strategy
    export_data = api1.export_strategy()
    print(f"\nExported strategy data (version {export_data['export_version']})")
    print(f"Strategy ID: {export_data['strategy']['strategy_id']}")
    
    # Import into new API instance
    api2 = StrategyAPI()
    imported = api2.import_strategy(export_data)
    
    print(f"\nImported strategy: {imported['name']}")
    print(f"Number of legs: {imported['num_legs']}")
    print(f"Total cost: ${imported['total_cost']:.2f}")
    
    return api2


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("OPTIX VISUAL STRATEGY BUILDER - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        # Run all examples
        example_1_create_iron_condor()
        example_2_custom_strategy()
        example_3_scenario_analysis()
        example_4_greeks_analysis()
        example_5_payoff_visualization()
        example_6_time_decay_and_volatility()
        example_7_export_import()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
