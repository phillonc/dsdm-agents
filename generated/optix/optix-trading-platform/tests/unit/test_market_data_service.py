"""
Unit Tests for Market Data Service
Tests quotes, options chains, and market data
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from src.market_data_service.models import (
    Quote, OptionContract, OptionsChain, Greeks, OptionType, QuoteStatus
)
from src.market_data_service.provider import MockMarketDataProvider
from src.market_data_service.cache import MarketDataCache


class TestMarketDataProvider:
    """Test market data provider"""
    
    @pytest.fixture
    def provider(self):
        return MockMarketDataProvider()
    
    @pytest.mark.asyncio
    async def test_get_quote(self, provider):
        """Test getting single quote"""
        quote = await provider.get_quote("AAPL")
        
        assert quote.symbol == "AAPL"
        assert quote.last_price > 0
        assert quote.bid is not None
        assert quote.ask is not None
        assert quote.volume >= 0
    
    @pytest.mark.asyncio
    async def test_get_quotes_batch(self, provider):
        """Test getting multiple quotes"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        quotes = await provider.get_quotes_batch(symbols)
        
        assert len(quotes) == 3
        assert all(q.symbol in symbols for q in quotes)
    
    @pytest.mark.asyncio
    async def test_get_options_expirations(self, provider):
        """Test getting option expirations"""
        expirations = await provider.get_options_expirations("SPY")
        
        assert expirations.symbol == "SPY"
        assert len(expirations.expirations) > 0
        assert all(isinstance(exp, date) for exp in expirations.expirations)
        
        # Expirations should be in future
        today = date.today()
        assert all(exp >= today for exp in expirations.expirations)
    
    @pytest.mark.asyncio
    async def test_get_options_chain(self, provider):
        """Test getting options chain"""
        expiration = date.today() + timedelta(days=30)
        chain = await provider.get_options_chain("SPY", expiration)
        
        assert chain.symbol == "SPY"
        assert chain.expiration_date == expiration
        assert len(chain.calls) > 0
        assert len(chain.puts) > 0
        
        # Verify strikes match between calls and puts
        call_strikes = {c.strike for c in chain.calls}
        put_strikes = {p.strike for p in chain.puts}
        assert call_strikes == put_strikes
    
    @pytest.mark.asyncio
    async def test_options_chain_greeks(self, provider):
        """Test option Greeks in chain"""
        expiration = date.today() + timedelta(days=30)
        chain = await provider.get_options_chain("SPY", expiration)
        
        call = chain.calls[0]
        assert call.greeks.delta > 0
        assert call.greeks.gamma > 0
        assert call.greeks.theta < 0  # Theta decay
        assert call.greeks.vega > 0
        
        put = chain.puts[0]
        assert put.greeks.delta < 0
        assert put.greeks.gamma > 0


class TestMarketDataCache:
    """Test market data caching"""
    
    @pytest.fixture
    def cache(self):
        return MarketDataCache()
    
    @pytest.fixture
    def sample_quote(self):
        return Quote(
            symbol="AAPL",
            last_price=Decimal("150.25"),
            bid=Decimal("150.24"),
            ask=Decimal("150.26"),
            volume=5000000
        )
    
    def test_set_and_get_quote(self, cache, sample_quote):
        """Test caching quote"""
        cache.set_quote("AAPL", sample_quote, ttl=60)
        
        retrieved = cache.get_quote("AAPL")
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.last_price == Decimal("150.25")
    
    def test_get_nonexistent_quote(self, cache):
        """Test getting non-cached quote"""
        quote = cache.get_quote("MSFT")
        assert quote is None
    
    def test_invalidate_symbol(self, cache, sample_quote):
        """Test invalidating symbol cache"""
        cache.set_quote("AAPL", sample_quote, ttl=60)
        cache.invalidate_symbol("AAPL")
        
        retrieved = cache.get_quote("AAPL")
        assert retrieved is None
    
    def test_clear_all(self, cache, sample_quote):
        """Test clearing entire cache"""
        cache.set_quote("AAPL", sample_quote, ttl=60)
        cache.set_quote("MSFT", sample_quote, ttl=60)
        
        cache.clear_all()
        
        assert cache.get_quote("AAPL") is None
        assert cache.get_quote("MSFT") is None


class TestMarketDataModels:
    """Test market data models"""
    
    def test_quote_model(self):
        """Test Quote model"""
        quote = Quote(
            symbol="AAPL",
            last_price=Decimal("150.25"),
            bid=Decimal("150.24"),
            ask=Decimal("150.26"),
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            volume=5000000
        )
        
        assert quote.symbol == "AAPL"
        assert quote.status == QuoteStatus.REAL_TIME
        assert isinstance(quote.timestamp, datetime)
    
    def test_greeks_model(self):
        """Test Greeks model"""
        greeks = Greeks(
            delta=Decimal("0.55"),
            gamma=Decimal("0.05"),
            theta=Decimal("-0.10"),
            vega=Decimal("0.15")
        )
        
        assert greeks.delta == Decimal("0.55")
        assert greeks.theta < 0
    
    def test_option_contract_model(self):
        """Test OptionContract model"""
        contract = OptionContract(
            symbol="AAPL",
            option_symbol="AAPL250117C00150000",
            strike=Decimal("150.00"),
            expiration_date=date(2025, 1, 17),
            option_type=OptionType.CALL,
            last_price=Decimal("5.50"),
            bid=Decimal("5.45"),
            ask=Decimal("5.55"),
            greeks=Greeks(
                delta=Decimal("0.55"),
                gamma=Decimal("0.05"),
                theta=Decimal("-0.10"),
                vega=Decimal("0.15")
            ),
            implied_volatility=Decimal("0.35"),
            volume=1000,
            open_interest=5000
        )
        
        assert contract.symbol == "AAPL"
        assert contract.option_type == OptionType.CALL
        assert contract.strike == Decimal("150.00")
    
    def test_options_chain_model(self):
        """Test OptionsChain model"""
        expiration = date(2025, 1, 17)
        
        greeks = Greeks(
            delta=Decimal("0.55"),
            gamma=Decimal("0.05"),
            theta=Decimal("-0.10"),
            vega=Decimal("0.15")
        )
        
        call = OptionContract(
            symbol="AAPL",
            option_symbol="AAPL250117C00150000",
            strike=Decimal("150.00"),
            expiration_date=expiration,
            option_type=OptionType.CALL,
            last_price=Decimal("5.50"),
            greeks=greeks,
            implied_volatility=Decimal("0.35"),
            volume=1000
        )
        
        put = OptionContract(
            symbol="AAPL",
            option_symbol="AAPL250117P00150000",
            strike=Decimal("150.00"),
            expiration_date=expiration,
            option_type=OptionType.PUT,
            last_price=Decimal("4.50"),
            greeks=greeks,
            implied_volatility=Decimal("0.35"),
            volume=800
        )
        
        chain = OptionsChain(
            symbol="AAPL",
            expiration_date=expiration,
            underlying_price=Decimal("150.00"),
            calls=[call],
            puts=[put],
            total_call_volume=1000,
            total_put_volume=800
        )
        
        assert chain.symbol == "AAPL"
        assert len(chain.calls) == 1
        assert len(chain.puts) == 1
        assert chain.total_call_volume == 1000
