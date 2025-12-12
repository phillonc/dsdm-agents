"""
Example API client demonstrating how to interact with the Visual Strategy Builder REST API.

This script shows:
1. Creating strategies via API
2. Adding legs to strategies
3. Getting payoff diagrams
4. Running scenario analysis
5. Tracking P&L
6. Getting risk metrics
"""

import requests
import json
from datetime import date, timedelta


class StrategyBuilderClient:
    """Client for interacting with the Visual Strategy Builder API."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """Initialize the client."""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def health_check(self):
        """Check API health."""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def create_strategy_from_template(self, template_data: dict):
        """Create a strategy from a template."""
        response = self.session.post(
            f"{self.base_url}/api/v1/strategies",
            json=template_data
        )
        response.raise_for_status()
        return response.json()['data']
    
    def create_custom_strategy(self, name: str, symbol: str):
        """Create a custom strategy."""
        response = self.session.post(
            f"{self.base_url}/api/v1/strategies",
            json={
                "name": name,
                "underlying_symbol": symbol,
                "strategy_type": "CUSTOM"
            }
        )
        response.raise_for_status()
        return response.json()['data']
    
    def add_leg(self, strategy_id: str, leg_data: dict):
        """Add a leg to a strategy."""
        response = self.session.post(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/legs",
            json=leg_data
        )
        response.raise_for_status()
        return response.json()['data']
    
    def get_payoff_diagram(self, strategy_id: str, current_price: float):
        """Get payoff diagram data."""
        response = self.session.get(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/payoff",
            params={"current_price": current_price}
        )
        response.raise_for_status()
        return response.json()['data']
    
    def run_scenario(self, strategy_id: str, scenario_data: dict):
        """Run scenario analysis."""
        response = self.session.post(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/scenarios",
            json=scenario_data
        )
        response.raise_for_status()
        return response.json()['data']
    
    def get_risk_metrics(self, strategy_id: str, current_price: float):
        """Get risk metrics."""
        response = self.session.get(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/risk-metrics",
            params={"current_price": current_price}
        )
        response.raise_for_status()
        return response.json()['data']
    
    def update_pnl(self, strategy_id: str, current_price: float):
        """Update P&L."""
        response = self.session.post(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/pnl",
            json={"current_price": current_price}
        )
        response.raise_for_status()
        return response.json()['data']
    
    def get_pnl_history(self, strategy_id: str):
        """Get P&L history."""
        response = self.session.get(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/pnl/history"
        )
        response.raise_for_status()
        return response.json()['data']


def example_1_iron_condor_via_api():
    """Example 1: Create and analyze Iron Condor via API."""
    print("\n" + "=" * 70)
    print("Example 1: Iron Condor via API")
    print("=" * 70 + "\n")
    
    client = StrategyBuilderClient()
    
    # Check health
    health = client.health_check()
    print(f"✓ API Status: {health['status']}")
    
    # Create Iron Condor
    expiration = (date.today() + timedelta(days=45)).isoformat()
    strategy_data = {
        "template_type": "IRON_CONDOR",
        "underlying_symbol": "SPY",
        "current_price": 450.0,
        "expiration": expiration,
        "params": {
            "wing_width": 5.0,
            "body_width": 10.0
        }
    }
    
    strategy = client.create_strategy_from_template(strategy_data)
    print(f"✓ Created: {strategy['name']}")
    print(f"  ID: {strategy['id']}")
    print(f"  Legs: {len(strategy['legs'])}")
    print(f"  Net Credit: ${strategy['total_cost']:.2f}")
    
    # Get Greeks
    greeks = strategy['aggregated_greeks']
    print(f"\n  Portfolio Greeks:")
    for greek, value in greeks.items():
        print(f"    {greek.capitalize():8s}: {value:+.4f}")
    
    return client, strategy


def example_2_custom_strategy_via_api(client: StrategyBuilderClient):
    """Example 2: Build custom strategy via API."""
    print("\n" + "=" * 70)
    print("Example 2: Custom Bull Call Spread via API")
    print("=" * 70 + "\n")
    
    # Create custom strategy
    strategy = client.create_custom_strategy("AAPL Bull Call Spread", "AAPL")
    print(f"✓ Created: {strategy['name']}")
    
    expiration = (date.today() + timedelta(days=30)).isoformat()
    
    # Add long call
    long_call = client.add_leg(strategy['id'], {
        "option_type": "CALL",
        "position_type": "LONG",
        "strike": 170.0,
        "expiration": expiration,
        "quantity": 1,
        "premium": 5.50,
        "implied_volatility": 0.28,
        "greeks": {
            "delta": 0.55,
            "gamma": 0.03,
            "theta": -0.08,
            "vega": 0.18,
            "rho": 0.05
        }
    })
    print(f"  + Long call @ ${long_call['strike']}")
    
    # Add short call
    short_call = client.add_leg(strategy['id'], {
        "option_type": "CALL",
        "position_type": "SHORT",
        "strike": 180.0,
        "expiration": expiration,
        "quantity": 1,
        "premium": 2.50,
        "implied_volatility": 0.26,
        "greeks": {
            "delta": 0.35,
            "gamma": 0.02,
            "theta": -0.05,
            "vega": 0.12,
            "rho": 0.03
        }
    })
    print(f"  + Short call @ ${short_call['strike']}")
    
    return strategy


def example_3_payoff_diagram(client: StrategyBuilderClient, strategy_id: str):
    """Example 3: Get and analyze payoff diagram."""
    print("\n" + "=" * 70)
    print("Example 3: Payoff Diagram Analysis")
    print("=" * 70 + "\n")
    
    payoff = client.get_payoff_diagram(strategy_id, 450.0)
    
    print(f"Payoff Analysis:")
    print(f"  Max Profit:    ${payoff['max_profit']:8.2f}")
    print(f"  Max Loss:      ${payoff['max_loss']:8.2f}")
    print(f"  Current P&L:   ${payoff['current_pnl']:8.2f}")
    print(f"  Breakevens:    {[f'${x:.2f}' for x in payoff['breakeven_points']]}")
    print(f"  Price Points:  {len(payoff['price_range'])}")


def example_4_scenario_analysis(client: StrategyBuilderClient, strategy_id: str):
    """Example 4: Run scenario analysis."""
    print("\n" + "=" * 70)
    print("Example 4: Scenario Analysis")
    print("=" * 70 + "\n")
    
    # Price scenarios
    print("Price Scenarios:")
    price_result = client.run_scenario(strategy_id, {
        "current_price": 450.0,
        "scenario_type": "price",
        "params": {"price_changes": [-10, -5, 0, 5, 10]}
    })
    
    for scenario in price_result['results']:
        print(f"  {scenario['price_change_percent']:+3.0f}%: "
              f"${scenario['new_price']:6.2f} → "
              f"P&L ${scenario['pnl']:+7.2f}")
    
    # Stress test
    print("\nStress Test:")
    stress_result = client.run_scenario(strategy_id, {
        "current_price": 450.0,
        "scenario_type": "stress"
    })
    
    for scenario_name, result in stress_result['results'].items():
        print(f"  {scenario_name.replace('_', ' ').title():20s}: "
              f"${result['estimated_total_pnl']:+8.2f}")


def example_5_risk_metrics(client: StrategyBuilderClient, strategy_id: str):
    """Example 5: Get comprehensive risk metrics."""
    print("\n" + "=" * 70)
    print("Example 5: Risk Metrics")
    print("=" * 70 + "\n")
    
    metrics = client.get_risk_metrics(strategy_id, 450.0)
    
    print("Risk/Reward Analysis:")
    rr = metrics['risk_reward']
    print(f"  Max Profit:         ${rr['max_profit']:8.2f}")
    print(f"  Max Loss:           ${rr['max_loss']:8.2f}")
    print(f"  Risk/Reward Ratio:   {rr['risk_reward_ratio']:8.2f}")
    print(f"  Return on Risk:      {rr['return_on_risk_percent']:7.1f}%")
    
    print("\nProbability Analysis:")
    prob = metrics['probability_analysis']
    print(f"  Win Rate:           {prob['probability_of_profit']:7.1f}%")
    print(f"  Average Profit:     ${prob['average_profit']:8.2f}")
    print(f"  Average Loss:       ${prob['average_loss']:8.2f}")
    print(f"  Expected Value:     ${prob['expected_value']:8.2f}")
    print(f"  Simulations:        {prob['simulations']:8d}")


def example_6_pnl_tracking(client: StrategyBuilderClient, strategy_id: str):
    """Example 6: Real-time P&L tracking."""
    print("\n" + "=" * 70)
    print("Example 6: Real-Time P&L Tracking")
    print("=" * 70 + "\n")
    
    prices = [450.0, 452.0, 455.0, 453.0, 451.0]
    
    print("Price Updates:")
    print("  Price    P&L      Delta")
    print("  " + "-" * 30)
    
    for price in prices:
        snapshot = client.update_pnl(strategy_id, price)
        delta = snapshot['greeks']['delta']
        print(f"  ${price:6.2f}  ${snapshot['pnl']:+7.2f}  {delta:+.4f}")
    
    # Get history
    history = client.get_pnl_history(strategy_id)
    print(f"\n✓ Tracked {len(history)} updates")


def main():
    """Run all API examples."""
    print("\n" + "=" * 70)
    print("  Visual Strategy Builder - API Client Examples")
    print("=" * 70)
    
    try:
        # Example 1: Iron Condor
        client, iron_condor = example_1_iron_condor_via_api()
        
        # Example 2: Custom Strategy
        bull_call = example_2_custom_strategy_via_api(client)
        
        # Example 3: Payoff Diagram
        example_3_payoff_diagram(client, iron_condor['id'])
        
        # Example 4: Scenario Analysis
        example_4_scenario_analysis(client, iron_condor['id'])
        
        # Example 5: Risk Metrics
        example_5_risk_metrics(client, iron_condor['id'])
        
        # Example 6: P&L Tracking
        example_6_pnl_tracking(client, iron_condor['id'])
        
        print("\n" + "=" * 70)
        print("✓ All API examples completed successfully!")
        print("=" * 70 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server")
        print("   Please start the server with: python -m src.api")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
