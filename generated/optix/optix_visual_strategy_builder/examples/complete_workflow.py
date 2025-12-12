"""
Complete workflow example demonstrating all major features of the Visual Strategy Builder.

This script shows how to:
1. Create strategies from templates
2. Build custom strategies
3. Calculate payoff diagrams
4. Analyze Greeks
5. Run scenario analysis
6. Track real-time P&L
7. Export/import strategies
"""

from datetime import date, timedelta
import json
from src.strategy_builder import StrategyBuilder
from src.models import StrategyType, OptionType, PositionType, Greeks


def print_separator(title: str):
    """Print a formatted section separator."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def example_1_iron_condor():
    """Example 1: Create and analyze an Iron Condor."""
    print_separator("Example 1: Iron Condor Strategy")
    
    builder = StrategyBuilder()
    expiration = date.today() + timedelta(days=45)
    
    # Create Iron Condor from template
    strategy = builder.create_from_template(
        template_type=StrategyType.IRON_CONDOR,
        underlying_symbol="SPY",
        current_price=450.0,
        expiration=expiration,
        wing_width=5.0,
        body_width=10.0
    )
    
    print(f"✓ Created: {strategy.name}")
    print(f"  Legs: {len(strategy.legs)}")
    print(f"  Net Credit: ${strategy.get_total_cost():.2f}")
    
    # Get Greeks
    greeks = strategy.get_aggregated_greeks()
    print(f"\n  Portfolio Greeks:")
    print(f"    Delta: {greeks.delta:+.4f}")
    print(f"    Gamma: {greeks.gamma:+.4f}")
    print(f"    Theta: {greeks.theta:+.4f}")
    print(f"    Vega:  {greeks.vega:+.4f}")
    
    # Calculate payoff diagram
    payoff = builder.calculate_payoff_diagram(strategy.id, current_price=450.0)
    print(f"\n  Risk/Reward:")
    print(f"    Max Profit: ${payoff['max_profit']:.2f}")
    print(f"    Max Loss: ${payoff['max_loss']:.2f}")
    print(f"    Breakevens: {[f'${x:.2f}' for x in payoff['breakeven_points']]}")
    
    # Get comprehensive risk metrics
    metrics = builder.get_risk_metrics(strategy.id, 450.0)
    print(f"\n  Probability Analysis:")
    print(f"    Win Rate: {metrics['probability_analysis']['probability_of_profit']:.1f}%")
    print(f"    Expected Value: ${metrics['probability_analysis']['expected_value']:.2f}")
    
    return builder, strategy


def example_2_custom_bull_call_spread():
    """Example 2: Build a custom Bull Call Spread."""
    print_separator("Example 2: Custom Bull Call Spread")
    
    builder = StrategyBuilder()
    expiration = date.today() + timedelta(days=30)
    
    # Create custom strategy
    strategy = builder.create_strategy(
        name="AAPL Bull Call Spread",
        underlying_symbol="AAPL"
    )
    
    print(f"✓ Created custom strategy: {strategy.name}")
    
    # Add long call
    builder.add_leg_to_strategy(
        strategy_id=strategy.id,
        option_type=OptionType.CALL,
        position_type=PositionType.LONG,
        strike=170.0,
        expiration=expiration,
        quantity=1,
        premium=5.50,
        implied_volatility=0.28,
        greeks=Greeks(delta=0.55, gamma=0.03, theta=-0.08, vega=0.18, rho=0.05)
    )
    print("  + Added long call @ 170")
    
    # Add short call
    builder.add_leg_to_strategy(
        strategy_id=strategy.id,
        option_type=OptionType.CALL,
        position_type=PositionType.SHORT,
        strike=180.0,
        expiration=expiration,
        quantity=1,
        premium=2.50,
        implied_volatility=0.26,
        greeks=Greeks(delta=0.35, gamma=0.02, theta=-0.05, vega=0.12, rho=0.03)
    )
    print("  + Added short call @ 180")
    
    print(f"\n  Net Debit: ${abs(strategy.get_total_cost()):.2f}")
    
    # Analyze at current price
    payoff = builder.calculate_payoff_diagram(strategy.id, current_price=175.0)
    print(f"  Max Profit: ${payoff['max_profit']:.2f}")
    print(f"  Max Loss: ${payoff['max_loss']:.2f}")
    print(f"  Current P&L: ${payoff['current_pnl']:.2f}")
    
    return builder, strategy


def example_3_scenario_analysis(builder: StrategyBuilder, strategy_id: str):
    """Example 3: Comprehensive scenario analysis."""
    print_separator("Example 3: Scenario Analysis")
    
    current_price = 450.0
    
    # Price scenarios
    print("Price Movement Scenarios:")
    price_results = builder.analyze_scenario(
        strategy_id=strategy_id,
        current_price=current_price,
        scenario_type='price',
        price_changes=[-10, -5, 0, 5, 10]
    )
    
    for result in price_results['results']:
        print(f"  {result['price_change_percent']:+3.0f}%: "
              f"${result['new_price']:6.2f} → "
              f"P&L ${result['pnl']:+7.2f} "
              f"({result['return_percent']:+.1f}%)")
    
    # Volatility scenarios
    print("\nVolatility Change Scenarios:")
    vol_results = builder.analyze_scenario(
        strategy_id=strategy_id,
        current_price=current_price,
        scenario_type='volatility',
        volatility_changes=[-20, -10, 0, 10, 20]
    )
    
    for result in vol_results['results']:
        print(f"  {result['volatility_change_percent']:+3.0f}% IV: "
              f"P&L Impact ${result['estimated_pnl_impact']:+7.2f}")
    
    # Time decay
    print("\nTime Decay Analysis:")
    time_results = builder.analyze_scenario(
        strategy_id=strategy_id,
        current_price=current_price,
        scenario_type='time',
        days_forward=[1, 7, 14, 30]
    )
    
    for result in time_results['results']:
        print(f"  {result['days_forward']:2d} days: "
              f"P&L Impact ${result['estimated_pnl_impact']:+7.2f}")
    
    # Stress test
    print("\nStress Test Results:")
    stress = builder.analyze_scenario(
        strategy_id=strategy_id,
        current_price=current_price,
        scenario_type='stress'
    )
    
    for name, result in stress['results'].items():
        print(f"  {name.replace('_', ' ').title():20s}: ${result['estimated_total_pnl']:+8.2f}")


def example_4_real_time_tracking(builder: StrategyBuilder, strategy_id: str):
    """Example 4: Real-time P&L tracking."""
    print_separator("Example 4: Real-Time P&L Tracking")
    
    # Start tracking
    builder.start_pnl_tracking(strategy_id)
    print("✓ Started P&L tracking")
    
    # Simulate price movements
    prices = [450.0, 452.0, 455.0, 453.0, 451.0, 449.0]
    
    print("\nPrice Updates:")
    print("  Time      Price    P&L      Change")
    print("  " + "-" * 40)
    
    for i, price in enumerate(prices):
        snapshot = builder.update_pnl(strategy_id, price)
        
        # Get change if available
        change = builder.pnl_trackers[strategy_id].get_pnl_change()
        change_str = f"${change:+.2f}" if change is not None else "  -   "
        
        print(f"  T+{i}     ${price:6.2f}  ${snapshot['pnl']:+7.2f}  {change_str}")
    
    # Summary
    history = builder.get_pnl_history(strategy_id)
    print(f"\n✓ Tracked {len(history)} updates")
    print(f"  Starting P&L: ${history[0]['pnl']:+.2f}")
    print(f"  Ending P&L:   ${history[-1]['pnl']:+.2f}")
    print(f"  Net Change:   ${history[-1]['pnl'] - history[0]['pnl']:+.2f}")


def example_5_export_import(builder: StrategyBuilder, strategy_id: str):
    """Example 5: Export and import strategies."""
    print_separator("Example 5: Export/Import Strategy")
    
    # Export strategy
    exported = builder.export_strategy(strategy_id)
    
    # Save to file
    filename = "exported_strategy.json"
    with open(filename, 'w') as f:
        json.dump(exported, f, indent=2)
    
    print(f"✓ Exported strategy to {filename}")
    print(f"  Name: {exported['name']}")
    print(f"  Type: {exported['strategy_type']}")
    print(f"  Legs: {len(exported['legs'])}")
    
    # Import strategy
    with open(filename, 'r') as f:
        strategy_data = json.load(f)
    
    imported_strategy = builder.import_strategy(strategy_data)
    
    print(f"\n✓ Imported strategy as new instance")
    print(f"  New ID: {imported_strategy.id}")
    print(f"  Legs preserved: {len(imported_strategy.legs)}")
    print(f"  Greeks preserved: {imported_strategy.get_aggregated_greeks().to_dict()}")
    
    # Clean up
    import os
    os.remove(filename)


def example_6_sensitivity_analysis(builder: StrategyBuilder, strategy_id: str):
    """Example 6: Comprehensive sensitivity analysis."""
    print_separator("Example 6: Sensitivity Analysis")
    
    sensitivity = builder.analyze_scenario(
        strategy_id=strategy_id,
        current_price=450.0,
        scenario_type='sensitivity'
    )
    
    print("Current Greeks:")
    greeks = sensitivity['results']['current_greeks']
    for greek, value in greeks.items():
        print(f"  {greek.capitalize():8s}: {value:+.4f}")
    
    print("\nDelta Sensitivity (Price Changes):")
    for scenario in sensitivity['results']['delta_sensitivity'][:5]:
        print(f"  {scenario['price_change_percent']:+3.0f}%: "
              f"P&L Impact ${scenario['estimated_pnl']:+7.2f}")
    
    print("\nVega Sensitivity (IV Changes):")
    for scenario in sensitivity['results']['vega_sensitivity'][:5]:
        print(f"  {scenario['volatility_change_percent']:+3.0f}%: "
              f"P&L Impact ${scenario['estimated_pnl']:+7.2f}")
    
    print("\nTheta Sensitivity (Time Decay):")
    for scenario in sensitivity['results']['theta_sensitivity']:
        print(f"  {scenario['days_forward']:2d} days: "
              f"P&L Impact ${scenario['estimated_pnl']:+7.2f}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  OPTIX Visual Strategy Builder - Complete Workflow Examples")
    print("=" * 70)
    
    # Example 1: Iron Condor
    builder1, strategy1 = example_1_iron_condor()
    
    # Example 2: Custom Bull Call Spread
    builder2, strategy2 = example_2_custom_bull_call_spread()
    
    # Example 3: Scenario Analysis (using Iron Condor)
    example_3_scenario_analysis(builder1, strategy1.id)
    
    # Example 4: Real-time P&L Tracking
    example_4_real_time_tracking(builder1, strategy1.id)
    
    # Example 5: Export/Import
    example_5_export_import(builder1, strategy1.id)
    
    # Example 6: Sensitivity Analysis
    example_6_sensitivity_analysis(builder1, strategy1.id)
    
    # Summary
    print_separator("Summary")
    print("✓ All examples completed successfully!")
    print(f"\nTotal strategies created: {len(builder1.strategies) + len(builder2.strategies)}")
    print("\nKey Features Demonstrated:")
    print("  • Strategy templates (Iron Condor)")
    print("  • Custom strategy building (Bull Call Spread)")
    print("  • Payoff diagram generation")
    print("  • Greeks aggregation")
    print("  • Scenario analysis (price, volatility, time)")
    print("  • Stress testing")
    print("  • Real-time P&L tracking")
    print("  • Strategy export/import")
    print("  • Sensitivity analysis")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
