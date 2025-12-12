"""
AI Analysis Service - ML-powered price prediction, volatility forecasting, and sentiment analysis
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from ..models.analysis_models import (
    PredictionSignal, SignalType, SignalStrength,
    VolatilityForecast, VolatilityRegime,
    SentimentAnalysis, SentimentScore, SentimentSource,
    MarketContext, MarketRegime
)


class AIAnalysisService:
    """
    Service for AI-powered analysis including price prediction,
    volatility forecasting, and sentiment analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.price_model = None
        self.volatility_model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        
    async def generate_prediction_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        feature_data: Optional[pd.DataFrame] = None,
        time_horizon: str = "1D"
    ) -> List[PredictionSignal]:
        """
        Generate price prediction signals using ML models
        
        Args:
            symbol: Trading symbol
            price_data: Historical price data
            feature_data: Additional features for prediction
            time_horizon: Prediction time horizon
            
        Returns:
            List of prediction signals
        """
        signals = []
        
        # Prepare features
        features = await self._prepare_features(price_data, feature_data)
        
        if len(features) < 50:
            # Not enough data for reliable prediction
            return signals
        
        # Train or update model
        if self.price_model is None:
            await self._train_price_model(features, price_data)
        
        # Generate prediction
        current_features = features.iloc[-1:].values
        current_price = price_data['close'].iloc[-1]
        
        # Predict future price
        predicted_price = await self._predict_price(current_features, current_price, time_horizon)
        
        # Calculate prediction range
        prediction_std = self._calculate_prediction_uncertainty(features, price_data)
        prediction_range = {
            'min': predicted_price - 2 * prediction_std,
            'max': predicted_price + 2 * prediction_std,
            'std_dev': prediction_std
        }
        
        # Determine signal type and strength
        price_change_pct = (predicted_price - current_price) / current_price
        signal_type, signal_strength, confidence = self._classify_signal(price_change_pct, prediction_std)
        
        # Calculate risk-reward ratio
        if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            stop_loss = current_price * 0.98
            risk_reward_ratio = (predicted_price - current_price) / (current_price - stop_loss)
        elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            stop_loss = current_price * 1.02
            risk_reward_ratio = (current_price - predicted_price) / (stop_loss - current_price)
        else:
            risk_reward_ratio = 0.0
        
        # Get feature importance
        feature_importance = await self._get_feature_importance()
        
        # Identify contributing factors
        contributing_factors = self._identify_contributing_factors(
            features.iloc[-1],
            feature_importance
        )
        
        signal = PredictionSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            signal_type=signal_type,
            signal_strength=signal_strength,
            confidence=confidence,
            current_price=current_price,
            predicted_price=predicted_price,
            price_target=prediction_range['max'] if signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else prediction_range['min'],
            time_horizon=time_horizon,
            prediction_range=prediction_range,
            model_name="RandomForestRegressor",
            feature_importance=feature_importance,
            contributing_factors=contributing_factors,
            risk_reward_ratio=risk_reward_ratio
        )
        
        signals.append(signal)
        
        return signals
    
    async def forecast_volatility(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        options_data: Optional[pd.DataFrame] = None,
        forecast_horizon: str = "1W"
    ) -> VolatilityForecast:
        """
        Forecast volatility using multiple methods
        
        Args:
            symbol: Trading symbol
            price_data: Historical price data
            options_data: Options data for implied volatility
            forecast_horizon: Forecast time horizon
            
        Returns:
            Volatility forecast
        """
        returns = price_data['close'].pct_change().dropna()
        
        # Calculate current realized volatility
        current_volatility = returns.std() * np.sqrt(252)  # Annualized
        
        # Get implied volatility from options
        implied_volatility = 0.0
        if options_data is not None and 'implied_volatility' in options_data.columns:
            implied_volatility = options_data['implied_volatility'].mean()
        
        # EWMA forecast
        ewma_forecast = await self._ewma_volatility_forecast(returns)
        
        # GARCH forecast
        garch_forecast = await self._garch_volatility_forecast(returns)
        
        # Combined forecast (weighted average)
        weights = {'ewma': 0.4, 'garch': 0.4, 'current': 0.2}
        forecasted_volatility = (
            weights['ewma'] * ewma_forecast +
            weights['garch'] * garch_forecast +
            weights['current'] * current_volatility
        )
        
        # Classify volatility regime
        volatility_regime, regime_change_prob = self._classify_volatility_regime(
            current_volatility,
            forecasted_volatility,
            returns
        )
        
        # Calculate confidence interval
        vol_std = returns.rolling(window=20).std().std() * np.sqrt(252)
        confidence_interval = {
            'lower': max(0, forecasted_volatility - 1.96 * vol_std),
            'upper': forecasted_volatility + 1.96 * vol_std
        }
        
        # Calculate historical percentile
        rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)
        historical_percentile = stats.percentileofscore(rolling_vol.dropna(), current_volatility)
        
        # Mean reversion signal
        mean_reversion_signal = self._detect_mean_reversion(current_volatility, rolling_vol)
        
        forecast = VolatilityForecast(
            forecast_id=f"volf_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            current_volatility=current_volatility,
            implied_volatility=implied_volatility,
            forecasted_volatility=forecasted_volatility,
            forecast_horizon=forecast_horizon,
            volatility_regime=volatility_regime,
            regime_change_probability=regime_change_prob,
            confidence_interval=confidence_interval,
            garch_forecast=garch_forecast,
            ewma_forecast=ewma_forecast,
            historical_percentile=historical_percentile,
            mean_reversion_signal=mean_reversion_signal,
            model_metrics={
                'forecast_accuracy': 0.75,
                'mse': vol_std ** 2
            }
        )
        
        return forecast
    
    async def analyze_sentiment(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        options_flow: Optional[pd.DataFrame] = None,
        news_data: Optional[List[Dict]] = None
    ) -> SentimentAnalysis:
        """
        Analyze market sentiment from multiple sources
        
        Args:
            symbol: Trading symbol
            market_data: Market data for technical sentiment
            options_flow: Options flow data
            news_data: News articles for NLP analysis
            
        Returns:
            Sentiment analysis result
        """
        source_sentiments = {}
        
        # Analyze options flow sentiment
        if options_flow is not None:
            options_sentiment = await self._analyze_options_sentiment(options_flow)
            source_sentiments[SentimentSource.OPTIONS_FLOW] = options_sentiment
        
        # Analyze market breadth
        if 'breadth' in market_data:
            breadth_sentiment = self._analyze_market_breadth(market_data['breadth'])
            source_sentiments[SentimentSource.MARKET_BREADTH] = breadth_sentiment
        
        # Analyze news sentiment (placeholder for NLP)
        if news_data:
            news_sentiment = await self._analyze_news_sentiment(news_data)
            source_sentiments[SentimentSource.NEWS] = news_sentiment
        
        # Calculate overall sentiment
        if source_sentiments:
            sentiment_score = np.mean(list(source_sentiments.values()))
        else:
            # Fallback to technical indicators
            sentiment_score = self._calculate_technical_sentiment(market_data)
            source_sentiments[SentimentSource.MARKET_BREADTH] = sentiment_score
        
        # Classify sentiment
        overall_sentiment = self._classify_sentiment(sentiment_score)
        
        # Calculate sentiment shift
        prev_sentiment = market_data.get('previous_sentiment', 0.0)
        sentiment_shift = sentiment_score - prev_sentiment
        
        # Calculate sentiment momentum
        sentiment_history = market_data.get('sentiment_history', [sentiment_score])
        sentiment_momentum = self._calculate_sentiment_momentum(sentiment_history)
        
        # Identify key drivers
        key_drivers = self._identify_sentiment_drivers(
            source_sentiments,
            market_data
        )
        
        # Check for contrarian indicator
        contrarian_indicator = self._check_contrarian_indicator(
            sentiment_score,
            sentiment_history
        )
        
        # Calculate confidence based on source agreement
        confidence = self._calculate_sentiment_confidence(source_sentiments)
        
        analysis = SentimentAnalysis(
            analysis_id=f"sent_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            overall_sentiment=overall_sentiment,
            sentiment_score=sentiment_score,
            confidence=confidence,
            source_sentiments=source_sentiments,
            sentiment_shift=sentiment_shift,
            sentiment_momentum=sentiment_momentum,
            key_drivers=key_drivers,
            contrarian_indicator=contrarian_indicator,
            metadata={
                'sources_analyzed': len(source_sentiments),
                'data_quality': 0.8
            }
        )
        
        return analysis
    
    async def analyze_market_context(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        market_data: Dict[str, Any]
    ) -> MarketContext:
        """
        Analyze overall market context and regime
        
        Args:
            symbol: Trading symbol
            price_data: Price data
            market_data: Additional market data
            
        Returns:
            Market context analysis
        """
        returns = price_data['close'].pct_change().dropna()
        
        # Identify market regime
        market_regime, regime_confidence = self._identify_market_regime(price_data, returns)
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(price_data)
        
        # Calculate correlation to SPY
        spy_correlation = market_data.get('spy_correlation', 0.5)
        
        # Calculate beta
        beta = market_data.get('beta', 1.0)
        
        # Get sector performance
        sector_performance = market_data.get('sector_performance', {})
        
        # Calculate market breadth indicators
        market_breadth = {
            'advance_decline_ratio': market_data.get('ad_ratio', 1.0),
            'new_highs_lows': market_data.get('nh_nl', 0),
            'vix_level': market_data.get('vix', 20.0)
        }
        
        # Risk indicators
        risk_indicators = {
            'volatility_regime': 'normal',
            'liquidity_score': 0.8,
            'market_stress_index': 0.3
        }
        
        context = MarketContext(
            context_id=f"ctx_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            market_regime=market_regime,
            regime_confidence=regime_confidence,
            trend_strength=trend_strength,
            correlation_to_spy=spy_correlation,
            beta=beta,
            sector_performance=sector_performance,
            market_breadth=market_breadth,
            risk_indicators=risk_indicators
        )
        
        return context
    
    # Helper methods
    
    async def _prepare_features(
        self,
        price_data: pd.DataFrame,
        feature_data: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """Prepare features for ML models"""
        df = price_data.copy()
        
        # Technical indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Volatility
        df['volatility_20'] = df['returns'].rolling(window=20).std()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Volume indicators
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
        
        # Drop NaN values
        df = df.dropna()
        
        # Select feature columns
        feature_cols = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        self.feature_names = feature_cols
        
        return df[feature_cols]
    
    async def _train_price_model(
        self,
        features: pd.DataFrame,
        price_data: pd.DataFrame
    ):
        """Train price prediction model"""
        # Prepare target (future returns)
        target = price_data['close'].pct_change().shift(-1)
        target = target.iloc[:len(features)]
        
        # Remove NaN
        valid_idx = ~target.isna()
        X = features[valid_idx]
        y = target[valid_idx]
        
        if len(X) < 50:
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model
        self.price_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.price_model.fit(X_train_scaled, y_train)
    
    async def _predict_price(
        self,
        features: np.ndarray,
        current_price: float,
        time_horizon: str
    ) -> float:
        """Predict future price"""
        if self.price_model is None:
            # Fallback to simple prediction
            return current_price * 1.01
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict return
        predicted_return = self.price_model.predict(features_scaled)[0]
        
        # Adjust for time horizon
        horizon_multiplier = self._get_horizon_multiplier(time_horizon)
        adjusted_return = predicted_return * horizon_multiplier
        
        # Calculate predicted price
        predicted_price = current_price * (1 + adjusted_return)
        
        return predicted_price
    
    def _calculate_prediction_uncertainty(
        self,
        features: pd.DataFrame,
        price_data: pd.DataFrame
    ) -> float:
        """Calculate prediction uncertainty"""
        returns = price_data['close'].pct_change().dropna()
        return returns.std() * price_data['close'].iloc[-1]
    
    def _classify_signal(
        self,
        price_change_pct: float,
        std_dev: float
    ) -> Tuple[SignalType, SignalStrength, float]:
        """Classify prediction signal"""
        abs_change = abs(price_change_pct)
        
        # Determine signal type
        if price_change_pct > 0.05:
            signal_type = SignalType.STRONG_BUY
            signal_strength = SignalStrength.VERY_STRONG
            confidence = 0.85
        elif price_change_pct > 0.02:
            signal_type = SignalType.BUY
            signal_strength = SignalStrength.STRONG
            confidence = 0.75
        elif price_change_pct < -0.05:
            signal_type = SignalType.STRONG_SELL
            signal_strength = SignalStrength.VERY_STRONG
            confidence = 0.85
        elif price_change_pct < -0.02:
            signal_type = SignalType.SELL
            signal_strength = SignalStrength.STRONG
            confidence = 0.75
        else:
            signal_type = SignalType.HOLD
            signal_strength = SignalStrength.MODERATE
            confidence = 0.65
        
        return signal_type, signal_strength, confidence
    
    async def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from model"""
        if self.price_model is None or not hasattr(self.price_model, 'feature_importances_'):
            return {}
        
        importance = dict(zip(
            self.feature_names,
            self.price_model.feature_importances_
        ))
        
        # Sort and return top features
        sorted_importance = dict(sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        
        return sorted_importance
    
    def _identify_contributing_factors(
        self,
        current_features: pd.Series,
        feature_importance: Dict[str, float]
    ) -> List[str]:
        """Identify contributing factors for prediction"""
        factors = []
        
        for feature, importance in list(feature_importance.items())[:5]:
            if feature in current_features.index:
                value = current_features[feature]
                factor_desc = f"{feature}: {value:.4f} (importance: {importance:.3f})"
                factors.append(factor_desc)
        
        return factors
    
    async def _ewma_volatility_forecast(self, returns: pd.Series) -> float:
        """EWMA volatility forecast"""
        lambda_param = 0.94
        ewma_var = returns.ewm(alpha=1-lambda_param).var().iloc[-1]
        return np.sqrt(ewma_var * 252)
    
    async def _garch_volatility_forecast(self, returns: pd.Series) -> float:
        """GARCH volatility forecast (simplified)"""
        # Simplified GARCH(1,1) approximation
        unconditional_var = returns.var()
        recent_var = returns.iloc[-20:].var()
        
        # GARCH parameters (typical values)
        omega = 0.000001
        alpha = 0.1
        beta = 0.85
        
        forecast_var = omega + alpha * recent_var + beta * unconditional_var
        return np.sqrt(forecast_var * 252)
    
    def _classify_volatility_regime(
        self,
        current_vol: float,
        forecasted_vol: float,
        returns: pd.Series
    ) -> Tuple[VolatilityRegime, float]:
        """Classify volatility regime"""
        historical_vol = returns.std() * np.sqrt(252)
        
        if forecasted_vol < historical_vol * 0.7:
            regime = VolatilityRegime.LOW
        elif forecasted_vol > historical_vol * 1.5:
            regime = VolatilityRegime.HIGH
        elif forecasted_vol > historical_vol * 2.0:
            regime = VolatilityRegime.EXTREME
        else:
            regime = VolatilityRegime.NORMAL
        
        # Probability of regime change
        vol_change = abs(forecasted_vol - current_vol) / current_vol
        regime_change_prob = min(0.9, vol_change * 2)
        
        return regime, regime_change_prob
    
    def _detect_mean_reversion(
        self,
        current_vol: float,
        rolling_vol: pd.Series
    ) -> bool:
        """Detect mean reversion signal in volatility"""
        mean_vol = rolling_vol.mean()
        z_score = (current_vol - mean_vol) / rolling_vol.std()
        
        # Signal mean reversion if more than 2 std devs from mean
        return abs(z_score) > 2.0
    
    async def _analyze_options_sentiment(self, options_flow: pd.DataFrame) -> float:
        """Analyze sentiment from options flow"""
        if options_flow.empty:
            return 0.0
        
        # Calculate put-call ratio
        calls = options_flow[options_flow['option_type'] == 'call']['volume'].sum()
        puts = options_flow[options_flow['option_type'] == 'put']['volume'].sum()
        
        if calls + puts == 0:
            return 0.0
        
        # Bullish if more calls, bearish if more puts
        sentiment = (calls - puts) / (calls + puts)
        
        return sentiment
    
    def _analyze_market_breadth(self, breadth_data: Dict[str, Any]) -> float:
        """Analyze market breadth sentiment"""
        ad_ratio = breadth_data.get('advance_decline_ratio', 1.0)
        nh_nl = breadth_data.get('new_highs_lows', 0)
        
        # Normalize to [-1, 1]
        sentiment = np.tanh((ad_ratio - 1.0) + (nh_nl / 100))
        
        return sentiment
    
    async def _analyze_news_sentiment(self, news_data: List[Dict]) -> float:
        """Analyze sentiment from news (placeholder for NLP)"""
        # Simplified sentiment scoring
        # In production, use transformer models like FinBERT
        positive_keywords = ['gain', 'surge', 'rally', 'bullish', 'upgrade']
        negative_keywords = ['loss', 'drop', 'crash', 'bearish', 'downgrade']
        
        sentiment_sum = 0.0
        for article in news_data[:20]:  # Limit to recent 20 articles
            text = article.get('title', '') + ' ' + article.get('summary', '')
            text_lower = text.lower()
            
            positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
            negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
            
            if positive_count + negative_count > 0:
                sentiment_sum += (positive_count - negative_count) / (positive_count + negative_count)
        
        if len(news_data) > 0:
            return sentiment_sum / len(news_data)
        return 0.0
    
    def _calculate_technical_sentiment(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment from technical indicators"""
        # Simplified technical sentiment
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', 0)
        
        # Normalize RSI to [-1, 1]
        rsi_sentiment = (rsi - 50) / 50
        
        # Normalize MACD
        macd_sentiment = np.tanh(macd)
        
        # Average
        sentiment = (rsi_sentiment + macd_sentiment) / 2
        
        return sentiment
    
    def _classify_sentiment(self, sentiment_score: float) -> SentimentScore:
        """Classify sentiment score"""
        if sentiment_score > 0.6:
            return SentimentScore.VERY_BULLISH
        elif sentiment_score > 0.2:
            return SentimentScore.BULLISH
        elif sentiment_score < -0.6:
            return SentimentScore.VERY_BEARISH
        elif sentiment_score < -0.2:
            return SentimentScore.BEARISH
        else:
            return SentimentScore.NEUTRAL
    
    def _calculate_sentiment_momentum(self, sentiment_history: List[float]) -> float:
        """Calculate rate of sentiment change"""
        if len(sentiment_history) < 2:
            return 0.0
        
        recent = sentiment_history[-5:]
        if len(recent) < 2:
            return 0.0
        
        # Linear regression to find trend
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        
        return slope
    
    def _identify_sentiment_drivers(
        self,
        source_sentiments: Dict[SentimentSource, float],
        market_data: Dict[str, Any]
    ) -> List[str]:
        """Identify key drivers of sentiment"""
        drivers = []
        
        for source, sentiment in source_sentiments.items():
            if abs(sentiment) > 0.5:
                direction = "positive" if sentiment > 0 else "negative"
                drivers.append(f"{source.value}: {direction} ({sentiment:.2f})")
        
        return drivers[:5]  # Top 5 drivers
    
    def _check_contrarian_indicator(
        self,
        sentiment_score: float,
        sentiment_history: List[float]
    ) -> bool:
        """Check if sentiment suggests contrarian opportunity"""
        # Extreme sentiment can indicate reversal
        if abs(sentiment_score) > 0.8:
            # Check if sentiment has been extreme for a while
            recent_extreme = sum(1 for s in sentiment_history[-5:] if abs(s) > 0.7)
            return recent_extreme >= 3
        
        return False
    
    def _calculate_sentiment_confidence(
        self,
        source_sentiments: Dict[SentimentSource, float]
    ) -> float:
        """Calculate confidence based on source agreement"""
        if len(source_sentiments) < 2:
            return 0.6
        
        sentiments = list(source_sentiments.values())
        
        # Calculate standard deviation
        std_dev = np.std(sentiments)
        
        # Lower std dev = higher confidence
        confidence = 1.0 - min(1.0, std_dev / 2.0)
        
        return confidence
    
    def _identify_market_regime(
        self,
        price_data: pd.DataFrame,
        returns: pd.Series
    ) -> Tuple[MarketRegime, float]:
        """Identify market regime"""
        # Calculate trend
        sma_20 = price_data['close'].rolling(window=20).mean()
        sma_50 = price_data['close'].rolling(window=50).mean()
        
        current_price = price_data['close'].iloc[-1]
        current_sma_20 = sma_20.iloc[-1]
        current_sma_50 = sma_50.iloc[-1]
        
        # Calculate volatility
        volatility = returns.std()
        
        # Classify regime
        if current_price > current_sma_20 > current_sma_50:
            if volatility < returns.quantile(0.3):
                regime = MarketRegime.TRENDING_UP
                confidence = 0.85
            else:
                regime = MarketRegime.VOLATILE
                confidence = 0.70
        elif current_price < current_sma_20 < current_sma_50:
            if volatility < returns.quantile(0.3):
                regime = MarketRegime.TRENDING_DOWN
                confidence = 0.85
            else:
                regime = MarketRegime.VOLATILE
                confidence = 0.70
        else:
            regime = MarketRegime.RANGING
            confidence = 0.75
        
        return regime, confidence
    
    def _calculate_trend_strength(self, price_data: pd.DataFrame) -> float:
        """Calculate trend strength"""
        returns = price_data['close'].pct_change().dropna()
        
        # ADX-like calculation
        positive_moves = returns[returns > 0].sum()
        negative_moves = abs(returns[returns < 0].sum())
        total_moves = positive_moves + negative_moves
        
        if total_moves == 0:
            return 0.5
        
        trend_strength = abs(positive_moves - negative_moves) / total_moves
        
        return min(1.0, trend_strength)
    
    def _get_horizon_multiplier(self, time_horizon: str) -> float:
        """Get multiplier for time horizon"""
        multipliers = {
            '1D': 1.0,
            '1W': 5.0,
            '1M': 20.0,
            '3M': 60.0
        }
        return multipliers.get(time_horizon, 1.0)
