"""Options chain data service."""
from typing import List, Optional
from decimal import Decimal
from datetime import date
import httpx

from src.models.schemas import OptionContract
from config.settings import settings


class OptionsDataService:
    """
    Service for fetching options chain data from external sources.
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> None:
        """
        Initialize options data service.
        
        Args:
            api_url: Options data API URL
            api_key: API authentication key
        """
        self.api_url = api_url or settings.options_chain_api_url
        self.api_key = api_key or settings.options_chain_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_options_chain(
        self,
        symbol: str,
        expiration: Optional[date] = None
    ) -> List[OptionContract]:
        """
        Fetch options chain data for a symbol.
        
        Args:
            symbol: Underlying symbol
            expiration: Specific expiration date (optional)
            
        Returns:
            List of OptionContract objects
        """
        if not self.api_url:
            # Return mock data for testing
            return self._generate_mock_data(symbol)
        
        # Build API request
        params = {
            "symbol": symbol,
            "api_key": self.api_key
        }
        
        if expiration:
            params["expiration"] = expiration.isoformat()
        
        try:
            response = await self.client.get(
                f"{self.api_url}/options/chain",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response to OptionContract objects
            return self._parse_options_data(data)
            
        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch options data: {str(e)}")
    
    def _parse_options_data(self, data: dict) -> List[OptionContract]:
        """
        Parse API response to OptionContract objects.
        
        Args:
            data: Raw API response data
            
        Returns:
            List of OptionContract objects
        """
        contracts = []
        
        for option in data.get("options", []):
            try:
                contract = OptionContract(
                    symbol=option["symbol"],
                    strike=Decimal(str(option["strike"])),
                    expiration=date.fromisoformat(option["expiration"]),
                    option_type=option["type"],
                    bid=Decimal(str(option["bid"])),
                    ask=Decimal(str(option["ask"])),
                    last=Decimal(str(option.get("last"))) if option.get("last") else None,
                    volume=option.get("volume", 0),
                    open_interest=option.get("open_interest", 0),
                    implied_volatility=option.get("implied_volatility"),
                    delta=option.get("delta"),
                    gamma=option.get("gamma"),
                    theta=option.get("theta"),
                    vega=option.get("vega")
                )
                contracts.append(contract)
            except Exception as e:
                # Skip malformed contracts
                continue
        
        return contracts
    
    def _generate_mock_data(self, symbol: str) -> List[OptionContract]:
        """
        Generate mock options data for testing.
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            List of mock OptionContract objects
        """
        import random
        from datetime import timedelta
        
        spot_price = Decimal("450.00")
        contracts = []
        
        # Generate strikes around spot
        strikes = [
            spot_price + Decimal(str(i))
            for i in range(-50, 55, 5)
        ]
        
        # Generate expirations
        expirations = [
            date.today() + timedelta(days=days)
            for days in [7, 14, 30, 60, 90]
        ]
        
        for expiration in expirations:
            for strike in strikes:
                # Call option
                call = OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiration=expiration,
                    option_type="call",
                    bid=Decimal(str(max(0.5, float(spot_price - strike) * 0.1 + random.uniform(0, 5)))),
                    ask=Decimal(str(max(1.0, float(spot_price - strike) * 0.1 + random.uniform(0, 5) + 0.5))),
                    last=Decimal(str(max(0.75, float(spot_price - strike) * 0.1 + random.uniform(0, 5) + 0.25))),
                    volume=random.randint(0, 1000),
                    open_interest=random.randint(100, 10000),
                    implied_volatility=random.uniform(0.15, 0.45),
                    delta=max(0.01, min(0.99, 0.5 + (float(spot_price - strike) / float(spot_price)) * 2)),
                    gamma=random.uniform(0.001, 0.02),
                    theta=-random.uniform(0.01, 0.5),
                    vega=random.uniform(0.05, 0.3)
                )
                contracts.append(call)
                
                # Put option
                put = OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiration=expiration,
                    option_type="put",
                    bid=Decimal(str(max(0.5, float(strike - spot_price) * 0.1 + random.uniform(0, 5)))),
                    ask=Decimal(str(max(1.0, float(strike - spot_price) * 0.1 + random.uniform(0, 5) + 0.5))),
                    last=Decimal(str(max(0.75, float(strike - spot_price) * 0.1 + random.uniform(0, 5) + 0.25))),
                    volume=random.randint(0, 1000),
                    open_interest=random.randint(100, 10000),
                    implied_volatility=random.uniform(0.15, 0.45),
                    delta=-max(0.01, min(0.99, 0.5 + (float(strike - spot_price) / float(spot_price)) * 2)),
                    gamma=random.uniform(0.001, 0.02),
                    theta=-random.uniform(0.01, 0.5),
                    vega=random.uniform(0.05, 0.3)
                )
                contracts.append(put)
        
        return contracts
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
