"""
Historical market data provider
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

from ..models.option import OptionQuote, OptionContract, MarketConditions


class MarketDataProvider(ABC):
    """Abstract base class for market data providers"""
    
    @abstractmethod
    async def get_option_chain(
        self,
        symbol: str,
        date: datetime,
        expiration: Optional[datetime] = None
    ) -> List[OptionQuote]:
        """Get option chain for a symbol at a specific date"""
        pass
    
    @abstractmethod
    async def get_underlying_price(
        self,
        symbol: str,
        date: datetime
    ) -> float:
        """Get underlying stock price"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1day"
    ) -> pd.DataFrame:
        """Get historical price data"""
        pass


class HistoricalDataReplayer:
    """Replay historical market data with accurate conditions simulation"""
    
    def __init__(self, data_provider: MarketDataProvider):
        self.data_provider = data_provider
        self.cache: Dict[str, Any] = {}
        
    async def replay_session(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        frequency: str = "1min"
    ) -> List[MarketConditions]:
        """
        Replay a trading session with market conditions
        
        Args:
            symbol: Underlying symbol
            start_time: Session start
            end_time: Session end
            frequency: Data frequency
            
        Returns:
            List of market conditions snapshots
        """
        conditions: List[MarketConditions] = []
        
        # Get historical data
        hist_data = await self.data_provider.get_historical_data(
            symbol, start_time, end_time, frequency
        )
        
        if hist_data.empty:
            return conditions
        
        # Calculate rolling volatility
        hist_data['returns'] = hist_data['close'].pct_change()
        hist_data['hist_vol'] = hist_data['returns'].rolling(20).std() * np.sqrt(252)
        
        for idx, row in hist_data.iterrows():
            timestamp = row.name if isinstance(row.name, datetime) else idx
            
            condition = MarketConditions(
                timestamp=timestamp,
                underlying_price=row['close'],
                underlying_symbol=symbol,
                historical_volatility=row.get('hist_vol'),
                volume=int(row.get('volume', 0))
            )
            conditions.append(condition)
        
        return conditions
    
    async def get_option_quotes_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        expirations: Optional[List[datetime]] = None
    ) -> List[OptionQuote]:
        """
        Get option quotes at a specific time
        
        Args:
            symbol: Underlying symbol
            timestamp: Time to get quotes
            expirations: Optional list of expiration dates to filter
            
        Returns:
            List of option quotes
        """
        cache_key = f"{symbol}_{timestamp.isoformat()}"
        
        if cache_key in self.cache:
            quotes = self.cache[cache_key]
        else:
            quotes = await self.data_provider.get_option_chain(
                symbol, timestamp, None
            )
            self.cache[cache_key] = quotes
        
        if expirations:
            quotes = [q for q in quotes if q.contract.expiration in expirations]
        
        return quotes
    
    def calculate_implied_volatility_surface(
        self,
        quotes: List[OptionQuote],
        underlying_price: float
    ) -> pd.DataFrame:
        """
        Calculate implied volatility surface from quotes
        
        Args:
            quotes: List of option quotes
            underlying_price: Current underlying price
            
        Returns:
            DataFrame with IV surface (rows=strikes, cols=expirations)
        """
        data = []
        for quote in quotes:
            if quote.implied_volatility is not None:
                moneyness = quote.contract.strike / underlying_price
                data.append({
                    'strike': quote.contract.strike,
                    'expiration': quote.contract.expiration,
                    'moneyness': moneyness,
                    'iv': quote.implied_volatility,
                    'type': quote.contract.option_type
                })
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Pivot to create surface
        surface = df.pivot_table(
            index='strike',
            columns='expiration',
            values='iv',
            aggfunc='mean'
        )
        
        return surface
    
    async def get_market_regime(
        self,
        symbol: str,
        timestamp: datetime,
        lookback_days: int = 30
    ) -> str:
        """
        Classify market volatility regime
        
        Args:
            symbol: Underlying symbol
            timestamp: Current time
            lookback_days: Days to look back for classification
            
        Returns:
            Regime classification: 'low', 'medium', 'high', 'extreme'
        """
        start_date = timestamp - timedelta(days=lookback_days)
        
        hist_data = await self.data_provider.get_historical_data(
            symbol, start_date, timestamp, "1day"
        )
        
        if len(hist_data) < 10:
            return 'unknown'
        
        # Calculate realized volatility
        returns = hist_data['close'].pct_change()
        realized_vol = returns.std() * np.sqrt(252)
        
        # Classify regime
        if realized_vol < 0.15:
            return 'low'
        elif realized_vol < 0.25:
            return 'medium'
        elif realized_vol < 0.40:
            return 'high'
        else:
            return 'extreme'


class SimulatedMarketDataProvider(MarketDataProvider):
    """Simulated market data for testing"""
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed:
            np.random.seed(seed)
    
    async def get_option_chain(
        self,
        symbol: str,
        date: datetime,
        expiration: Optional[datetime] = None
    ) -> List[OptionQuote]:
        """Generate simulated option chain"""
        underlying_price = await self.get_underlying_price(symbol, date)
        
        if expiration is None:
            expiration = date + timedelta(days=30)
        
        quotes: List[OptionQuote] = []
        
        # Generate strikes around the money
        strikes = np.arange(
            underlying_price * 0.8,
            underlying_price * 1.2,
            underlying_price * 0.05
        )
        
        for strike in strikes:
            # Simulate call
            call_iv = self._simulate_iv(underlying_price, strike, expiration, date)
            call_price = self._black_scholes_call(
                underlying_price, strike, 
                (expiration - date).days / 365,
                0.04, call_iv
            )
            
            call_quote = OptionQuote(
                contract=OptionContract(
                    symbol=symbol,
                    expiration=expiration.date(),
                    strike=strike,
                    option_type="call"
                ),
                timestamp=date,
                bid=call_price * 0.95,
                ask=call_price * 1.05,
                last=call_price,
                volume=int(np.random.randint(10, 1000)),
                open_interest=int(np.random.randint(100, 10000)),
                implied_volatility=call_iv,
                delta=self._calculate_delta(underlying_price, strike, call_iv, True)
            )
            quotes.append(call_quote)
            
            # Simulate put
            put_iv = self._simulate_iv(underlying_price, strike, expiration, date)
            put_price = self._black_scholes_put(
                underlying_price, strike,
                (expiration - date).days / 365,
                0.04, put_iv
            )
            
            put_quote = OptionQuote(
                contract=OptionContract(
                    symbol=symbol,
                    expiration=expiration.date(),
                    strike=strike,
                    option_type="put"
                ),
                timestamp=date,
                bid=put_price * 0.95,
                ask=put_price * 1.05,
                last=put_price,
                volume=int(np.random.randint(10, 1000)),
                open_interest=int(np.random.randint(100, 10000)),
                implied_volatility=put_iv,
                delta=self._calculate_delta(underlying_price, strike, put_iv, False)
            )
            quotes.append(put_quote)
        
        return quotes
    
    async def get_underlying_price(
        self,
        symbol: str,
        date: datetime
    ) -> float:
        """Generate simulated underlying price"""
        # Simple price simulation based on date
        days_offset = (date - datetime(2020, 1, 1)).days
        base_price = 100.0
        drift = 0.0001 * days_offset
        noise = np.random.randn() * 2
        return base_price + drift + noise
    
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1day"
    ) -> pd.DataFrame:
        """Generate simulated historical data"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate price series
        returns = np.random.randn(len(dates)) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'open': prices * (1 + np.random.randn(len(dates)) * 0.01),
            'high': prices * (1 + np.abs(np.random.randn(len(dates))) * 0.02),
            'low': prices * (1 - np.abs(np.random.randn(len(dates))) * 0.02),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
        
        return df
    
    def _simulate_iv(
        self,
        spot: float,
        strike: float,
        expiration: datetime,
        current: datetime
    ) -> float:
        """Simulate implied volatility with smile"""
        moneyness = strike / spot
        base_iv = 0.25
        
        # Volatility smile
        smile = 0.1 * (moneyness - 1.0) ** 2
        
        return base_iv + smile
    
    def _black_scholes_call(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float
    ) -> float:
        """Black-Scholes call price"""
        from scipy.stats import norm
        
        if T <= 0:
            return max(S - K, 0)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    def _black_scholes_put(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float
    ) -> float:
        """Black-Scholes put price"""
        from scipy.stats import norm
        
        if T <= 0:
            return max(K - S, 0)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    def _calculate_delta(
        self,
        S: float,
        K: float,
        sigma: float,
        is_call: bool
    ) -> float:
        """Calculate option delta"""
        from scipy.stats import norm
        
        T = 30 / 365  # Assume 30 days
        r = 0.04
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        
        if is_call:
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
