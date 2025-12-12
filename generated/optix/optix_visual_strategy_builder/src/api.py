"""
REST API interface for the Visual Strategy Builder.

This module provides a Flask-based REST API for the strategy builder.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import date, datetime
from typing import Dict, Any
import traceback

from .strategy_builder import StrategyBuilder
from .models import OptionType, PositionType, StrategyType, Greeks


app = Flask(__name__)
CORS(app)

# Global strategy builder instance
builder = StrategyBuilder()


def error_response(message: str, status_code: int = 400) -> tuple:
    """Create an error response."""
    return jsonify({'error': message}), status_code


def success_response(data: Any, message: str = None) -> Dict:
    """Create a success response."""
    response = {'success': True, 'data': data}
    if message:
        response['message'] = message
    return jsonify(response)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Visual Strategy Builder',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/v1/strategies', methods=['POST'])
def create_strategy():
    """Create a new strategy."""
    try:
        data = request.json
        
        if 'template_type' in data:
            # Create from template
            strategy = builder.create_from_template(
                template_type=StrategyType(data['template_type']),
                underlying_symbol=data['underlying_symbol'],
                current_price=data['current_price'],
                expiration=date.fromisoformat(data['expiration']),
                **data.get('params', {})
            )
        else:
            # Create custom strategy
            strategy = builder.create_strategy(
                name=data.get('name', 'Untitled Strategy'),
                underlying_symbol=data['underlying_symbol'],
                strategy_type=StrategyType(data.get('strategy_type', 'CUSTOM'))
            )
        
        return success_response(strategy.to_dict(), 'Strategy created successfully')
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies', methods=['GET'])
def list_strategies():
    """List all strategies."""
    try:
        strategies = builder.list_strategies()
        return success_response([s.to_dict() for s in strategies])
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>', methods=['GET'])
def get_strategy(strategy_id: str):
    """Get a specific strategy."""
    try:
        strategy = builder.get_strategy(strategy_id)
        if not strategy:
            return error_response('Strategy not found', 404)
        
        return success_response(strategy.to_dict())
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id: str):
    """Delete a strategy."""
    try:
        if builder.delete_strategy(strategy_id):
            return success_response(None, 'Strategy deleted successfully')
        else:
            return error_response('Strategy not found', 404)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/legs', methods=['POST'])
def add_leg(strategy_id: str):
    """Add a leg to a strategy."""
    try:
        data = request.json
        
        greeks = None
        if 'greeks' in data:
            greeks = Greeks(**data['greeks'])
        
        leg = builder.add_leg_to_strategy(
            strategy_id=strategy_id,
            option_type=OptionType(data['option_type']),
            position_type=PositionType(data['position_type']),
            strike=data['strike'],
            expiration=date.fromisoformat(data['expiration']),
            quantity=data['quantity'],
            premium=data['premium'],
            implied_volatility=data.get('implied_volatility', 0.25),
            greeks=greeks
        )
        
        return success_response(leg.to_dict(), 'Leg added successfully')
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/legs/<leg_id>', methods=['DELETE'])
def remove_leg(strategy_id: str, leg_id: str):
    """Remove a leg from a strategy."""
    try:
        if builder.remove_leg_from_strategy(strategy_id, leg_id):
            return success_response(None, 'Leg removed successfully')
        else:
            return error_response('Leg not found', 404)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/payoff', methods=['GET'])
def get_payoff_diagram(strategy_id: str):
    """Get payoff diagram data."""
    try:
        current_price = request.args.get('current_price', type=float)
        
        payoff_data = builder.calculate_payoff_diagram(
            strategy_id=strategy_id,
            current_price=current_price
        )
        
        return success_response(payoff_data)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/pnl', methods=['POST'])
def update_pnl(strategy_id: str):
    """Update P&L for a strategy."""
    try:
        data = request.json
        current_price = data['current_price']
        timestamp = data.get('timestamp')
        
        pnl_snapshot = builder.update_pnl(
            strategy_id=strategy_id,
            current_price=current_price,
            timestamp=timestamp
        )
        
        return success_response(pnl_snapshot)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/pnl/history', methods=['GET'])
def get_pnl_history(strategy_id: str):
    """Get P&L history for a strategy."""
    try:
        history = builder.get_pnl_history(strategy_id)
        return success_response(history)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/scenarios', methods=['POST'])
def run_scenario(strategy_id: str):
    """Run scenario analysis."""
    try:
        data = request.json
        current_price = data['current_price']
        scenario_type = data['scenario_type']
        params = data.get('params', {})
        
        results = builder.analyze_scenario(
            strategy_id=strategy_id,
            current_price=current_price,
            scenario_type=scenario_type,
            **params
        )
        
        return success_response(results)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/risk-metrics', methods=['GET'])
def get_risk_metrics(strategy_id: str):
    """Get risk metrics for a strategy."""
    try:
        current_price = request.args.get('current_price', type=float, required=True)
        
        metrics = builder.get_risk_metrics(
            strategy_id=strategy_id,
            current_price=current_price
        )
        
        return success_response(metrics)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/<strategy_id>/export', methods=['GET'])
def export_strategy(strategy_id: str):
    """Export a strategy."""
    try:
        strategy_data = builder.export_strategy(strategy_id)
        return success_response(strategy_data)
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/strategies/import', methods=['POST'])
def import_strategy():
    """Import a strategy."""
    try:
        data = request.json
        strategy = builder.import_strategy(data)
        return success_response(strategy.to_dict(), 'Strategy imported successfully')
    
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/v1/templates', methods=['GET'])
def list_templates():
    """List available strategy templates."""
    templates = [
        {
            'type': 'IRON_CONDOR',
            'name': 'Iron Condor',
            'description': 'Four-leg strategy for low volatility markets',
            'required_params': ['underlying_symbol', 'current_price', 'expiration'],
            'optional_params': ['wing_width', 'body_width', 'quantity']
        },
        {
            'type': 'BUTTERFLY',
            'name': 'Butterfly Spread',
            'description': 'Three-strike strategy for minimal price movement',
            'required_params': ['underlying_symbol', 'current_price', 'expiration'],
            'optional_params': ['wing_width', 'quantity', 'option_type']
        },
        {
            'type': 'STRADDLE',
            'name': 'Straddle',
            'description': 'Same-strike call and put for volatility plays',
            'required_params': ['underlying_symbol', 'strike', 'expiration'],
            'optional_params': ['quantity', 'position_type']
        },
        {
            'type': 'STRANGLE',
            'name': 'Strangle',
            'description': 'OTM call and put for volatility with lower cost',
            'required_params': ['underlying_symbol', 'current_price', 'expiration'],
            'optional_params': ['strike_distance', 'quantity', 'position_type']
        },
        {
            'type': 'VERTICAL_SPREAD',
            'name': 'Vertical Spread',
            'description': 'Directional two-leg spread strategy',
            'required_params': ['underlying_symbol', 'current_price', 'expiration'],
            'optional_params': ['spread_width', 'quantity', 'option_type', 'is_debit']
        },
        {
            'type': 'COVERED_CALL',
            'name': 'Covered Call',
            'description': 'Stock ownership with short call',
            'required_params': ['underlying_symbol', 'current_price', 'expiration', 'call_strike'],
            'optional_params': ['quantity', 'stock_quantity']
        },
        {
            'type': 'PROTECTIVE_PUT',
            'name': 'Protective Put',
            'description': 'Stock ownership with long put protection',
            'required_params': ['underlying_symbol', 'current_price', 'expiration', 'put_strike'],
            'optional_params': ['quantity', 'stock_quantity']
        }
    ]
    
    return success_response(templates)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return error_response('Endpoint not found', 404)


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return error_response('Internal server error', 500)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
