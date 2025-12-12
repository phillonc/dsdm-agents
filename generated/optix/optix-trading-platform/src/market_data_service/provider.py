"""
Market Data Provider Interface
Abstract provider for market data sources
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from .models import Quote, OptionsChain, OptionsExpirations, HistoricalBar


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers
    Implementations: Polygon.io, Alpha Vantage, TD Ameritrade, etc.
    """
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for symbol"""
        pass
    
    @abstractmethod
    async def get_quotes_batch(self, symbols: List[str]) -> List[Quote]:
        """Get quotes for multiple symbols"""
        pass
    
    @abstractmethod
    async def get_options_expirations(self, symbol: str) -> OptionsExpirations:
        """Get available option expiration dates"""
        pass
    
    @abstractmethod
    async def get_options_chain(
        self,
        symbol: str,
        expiration: date
    ) -> OptionsChain:
        """Get full options chain for expiration"""
        pass
    
    @abstractmethod
    async def get_historical_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1D"
    ) -> List[HistoricalBar]:
        """Get historical OHLCV bars"""
        pass
    
    @abstractmethod
    async def subscribe_quotes(self, symbols: List[str], callback):
        """Subscribe to real-time quote updates via WebSocket"""
        pass


class MockMarketDataProvider(MarketDataProvider):
    """
    Mock market data provider for development and testing
    """
    
    async def get_quote(self, symbol: str) -> Quote:
        """Generate mock quote"""
        return Quote(
            symbol=symbol,
            last_price=Decimal("150.25"),
            bid=Decimal("150.24"),
            ask=Decimal("150.26"),
            bid_size=100,
            ask_size=200,
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            volume=5_000_000,
            high=Decimal("152.00"),
            low=Decimal("148.50"),
            open_price=Decimal("149.00"),
            previous_close=Decimal("147.75")
        )
    
    async def get_quotes_batch(self, symbols: List[str]) -> List[Quote]:
        """Generate mock quotes for multiple symbols"""
        quotes = []
        for i, symbol in enumerate(symbols):
            base_price = Decimal(f"{100 + i * 10}")
            quotes.append(Quote(
                symbol=symbol,
                last_price=base_price,
                bid=base_price - Decimal("0.01"),
                ask=base_price + Decimal("0.01"),
                change=Decimal(f"{i * 0.5}"),
                change_percent=Decimal(f"{i * 0.3}"),
                volume=1_000_000 * (i + 1)
            ))
        return quotes
    
    async def get_options_expirations(self, symbol: str) -> OptionsExpirations:
        """Generate mock expiration dates"""
        from datetime import timedelta
        today = date.today()
        
        # Generate weekly and monthly expirations
        expirations = []
        for weeks in [1, 2, 3, 4, 8, 12, 16, 24, 52]:
            exp_date = today + timedelta(weeks=weeks)
            # Adjust to Friday
            days_ahead = 4 - exp_date.weekday()
            if days_ahead < 0:
                days_ahead += 7
            exp_date = exp_date + timedelta(days=days_ahead)
            expirations.append(exp_date)
        
        return OptionsExpirations(
            symbol=symbol,
            expirations=sorted(set(expirations))
        )
    
    async def get_options_chain(
        self,
        symbol: str,
        expiration: date
    ) -> OptionsChain:
        """Generate mock options chain"""
        from .models import OptionContract, Greeks, OptionType
        
        underlying_price = Decimal("150.00")
        
        # Generate strikes around underlying
        strikes = [
            underlying_price + Decimal(str(offset))
            for offset in range(-20, 21, 5)
        ]
        
        calls = []
        puts = []
        
        for strike in strikes:
            # Calculate mock Greeks based on moneyness
            moneyness = float(underlying_price / strike)
            
            # Call Greeks
            call_delta = Decimal(str(max(0.1, min(0.9, moneyness))))
            call_greeks = Greeks(
                delta=call_delta,
                gamma=Decimal("0.05"),
                theta=Decimal("-0.10"),
                vega=Decimal("0.15"),
                rho=Decimal("0.05")
            )
            
            # Put Greeks
            put_delta = call_delta - Decimal("1.0")
            put_greeks = Greeks(
                delta=put_delta,
                gamma=Decimal("0.05"),
                theta=Decimal("-0.10"),
                vega=Decimal("0.15"),
                rho=Decimal("-0.05")
            )
            
            # Calculate prices
            intrinsic_call = max(underlying_price - strike, Decimal("0"))
            intrinsic_put = max(strike - underlying_price, Decimal("0"))
            
            extrinsic = Decimal("2.50")
            
            call_price = intrinsic_call + extrinsic
            put_price = intrinsic_put + extrinsic
            
            calls.append(OptionContract(
                symbol=symbol,
                option_symbol=f"{symbol}{expiration.strftime('%y%m%d')}C{int(strike * 1000)}",
                strike=strike,
                expiration_date=expiration,
                option_type=OptionType.CALL,
                last_price=call_price,
                bid=call_price - Decimal("0.05"),
                ask=call_price + Decimal("0.05"),
                greeks=call_greeks,
                implied_volatility=Decimal("0.35"),
                volume=1000,
                open_interest=5000,
                in_the_money=strike < underlying_price,
                intrinsic_value=intrinsic_call,
                extrinsic_value=extrinsic
            ))
            
            puts.append(OptionContract(
                symbol=symbol,
                option_symbol=f"{symbol}{expiration.strftime('%y%m%d')}P{int(strike * 1000)}",
                strike=strike,
                expiration_date=expiration,
                option_type=OptionType.PUT,
                last_price=put_price,
                bid=put_price - Decimal("0.05"),
                ask=put_price + Decimal("0.05"),
                greeks=put_greeks,
                implied_volatility=Decimal("0.35"),
                volume=800,
                open_interest=4000,
                in_the_money=strike > underlying_price,
                intrinsic_value=intrinsic_put,
                extrinsic_value=extrinsic
            ))
        
        return OptionsChain(
            symbol=symbol,
            expiration_date=expiration,
            underlying_price=underlying_price,
            calls=calls,
            puts=puts,
            total_call_volume=sum(c.volume for c in calls),
            total_put_volume=sum(p.volume for p in puts),
            total_call_open_interest=sum(c.open_interest for c in calls),
            total_put_open_interest=sum(p.open_interest for p in puts)
        )
    
    async def get_historical_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1D"
    ) -> List[HistoricalBar]:
        """Generate mock historical data"""
        bars = []
        current = start_date
        base_price = Decimal("100.00")
        
        while current <= end_date:
            # Simple random walk
            change = Decimal(str((hash(current) % 10 - 5) / 10))
            base_price += change
            
            bars.append(HistoricalBar(
                symbol=symbol,
                timestamp=current,
                open=base_price,
                high=base_price + Decimal("2.00"),
                low=base_price - Decimal("1.50"),
                close=base_price + change,
                volume=5_000_000
            ))
            
            current = current.replace(day=current.day + 1)
        
        return bars
    
    async def subscribe_quotes(self, symbols: List[str], callback):
        """Mock WebSocket subscription"""
        # In production, this would establish WebSocket connection
        pass
