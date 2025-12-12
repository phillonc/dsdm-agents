"""
Pattern Recognition Service - Detects chart patterns, unusual options activity, and volume anomalies
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, argrelextrema
from scipy.stats import zscore

from ..models.pattern_models import (
    ChartPattern, PatternType, TrendDirection,
    OptionsActivity, OptionsActivityType,
    VolumeAnomaly, VolumeAnomalyType,
    SupportResistanceLevel
)


class PatternRecognitionService:
    """
    Service for detecting chart patterns, unusual options activity,
    and volume anomalies using technical analysis algorithms
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_pattern_confidence = self.config.get('min_pattern_confidence', 0.6)
        self.lookback_periods = self.config.get('lookback_periods', 100)
        
    async def detect_chart_patterns(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame] = None
    ) -> List[ChartPattern]:
        """
        Detect various chart patterns in price data
        
        Args:
            symbol: Trading symbol
            price_data: DataFrame with OHLC data
            volume_data: Optional DataFrame with volume data
            
        Returns:
            List of detected chart patterns
        """
        patterns = []
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in price_data.columns for col in required_cols):
            raise ValueError(f"Price data must contain columns: {required_cols}")
        
        # Detect various pattern types concurrently
        pattern_tasks = [
            self._detect_head_shoulders(symbol, price_data, volume_data),
            self._detect_double_tops_bottoms(symbol, price_data, volume_data),
            self._detect_triangles(symbol, price_data),
            self._detect_flags_wedges(symbol, price_data),
            self._detect_breakouts(symbol, price_data, volume_data),
        ]
        
        pattern_results = await asyncio.gather(*pattern_tasks, return_exceptions=True)
        
        for result in pattern_results:
            if isinstance(result, list):
                patterns.extend(result)
        
        # Filter by confidence threshold
        patterns = [p for p in patterns if p.confidence >= self.min_pattern_confidence]
        
        return patterns
    
    async def _detect_head_shoulders(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame]
    ) -> List[ChartPattern]:
        """Detect head and shoulders patterns"""
        patterns = []
        highs = price_data['high'].values
        lows = price_data['low'].values
        closes = price_data['close'].values
        
        # Find local maxima for head & shoulders
        peaks, _ = find_peaks(highs, distance=5, prominence=highs.std() * 0.5)
        
        if len(peaks) >= 3:
            # Check for head & shoulders formation
            for i in range(len(peaks) - 2):
                left_shoulder = highs[peaks[i]]
                head = highs[peaks[i + 1]]
                right_shoulder = highs[peaks[i + 2]]
                
                # Head should be higher than both shoulders
                if head > left_shoulder and head > right_shoulder:
                    # Shoulders should be roughly equal
                    shoulder_diff = abs(left_shoulder - right_shoulder) / head
                    
                    if shoulder_diff < 0.05:  # Within 5%
                        # Calculate neckline and price target
                        neckline = min(lows[peaks[i]:peaks[i + 2]])
                        head_height = head - neckline
                        price_target = neckline - head_height
                        
                        # Calculate confidence based on pattern quality
                        confidence = self._calculate_pattern_confidence(
                            shoulder_symmetry=1 - shoulder_diff,
                            volume_confirmation=self._check_volume_confirmation(
                                volume_data, peaks[i], peaks[i + 2]
                            ) if volume_data is not None else 0.5
                        )
                        
                        pattern = ChartPattern(
                            pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                            symbol=symbol,
                            pattern_type=PatternType.HEAD_SHOULDERS,
                            confidence=confidence,
                            start_time=price_data.index[peaks[i]],
                            end_time=price_data.index[peaks[i + 2]],
                            trend_direction=TrendDirection.BEARISH,
                            price_target=price_target,
                            stop_loss=head * 1.02,
                            support_level=neckline,
                            resistance_level=head,
                            volume_confirmation=volume_data is not None,
                            key_levels=[
                                {"level": "neckline", "price": neckline},
                                {"level": "head", "price": head},
                                {"level": "left_shoulder", "price": left_shoulder},
                                {"level": "right_shoulder", "price": right_shoulder}
                            ]
                        )
                        patterns.append(pattern)
        
        # Detect inverse head & shoulders (on lows)
        troughs, _ = find_peaks(-lows, distance=5, prominence=lows.std() * 0.5)
        
        if len(troughs) >= 3:
            for i in range(len(troughs) - 2):
                left_shoulder = lows[troughs[i]]
                head = lows[troughs[i + 1]]
                right_shoulder = lows[troughs[i + 2]]
                
                if head < left_shoulder and head < right_shoulder:
                    shoulder_diff = abs(left_shoulder - right_shoulder) / head
                    
                    if shoulder_diff < 0.05:
                        neckline = max(highs[troughs[i]:troughs[i + 2]])
                        head_depth = neckline - head
                        price_target = neckline + head_depth
                        
                        confidence = self._calculate_pattern_confidence(
                            shoulder_symmetry=1 - shoulder_diff,
                            volume_confirmation=self._check_volume_confirmation(
                                volume_data, troughs[i], troughs[i + 2]
                            ) if volume_data is not None else 0.5
                        )
                        
                        pattern = ChartPattern(
                            pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                            symbol=symbol,
                            pattern_type=PatternType.INVERSE_HEAD_SHOULDERS,
                            confidence=confidence,
                            start_time=price_data.index[troughs[i]],
                            end_time=price_data.index[troughs[i + 2]],
                            trend_direction=TrendDirection.BULLISH,
                            price_target=price_target,
                            stop_loss=head * 0.98,
                            support_level=head,
                            resistance_level=neckline,
                            volume_confirmation=volume_data is not None,
                            key_levels=[
                                {"level": "neckline", "price": neckline},
                                {"level": "head", "price": head},
                                {"level": "left_shoulder", "price": left_shoulder},
                                {"level": "right_shoulder", "price": right_shoulder}
                            ]
                        )
                        patterns.append(pattern)
        
        return patterns
    
    async def _detect_double_tops_bottoms(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame]
    ) -> List[ChartPattern]:
        """Detect double top and double bottom patterns"""
        patterns = []
        highs = price_data['high'].values
        lows = price_data['low'].values
        
        # Double tops
        peaks, _ = find_peaks(highs, distance=10, prominence=highs.std() * 0.5)
        
        for i in range(len(peaks) - 1):
            peak1 = highs[peaks[i]]
            peak2 = highs[peaks[i + 1]]
            
            # Peaks should be roughly equal (within 2%)
            if abs(peak1 - peak2) / peak1 < 0.02:
                trough_between = min(lows[peaks[i]:peaks[i + 1]])
                price_target = trough_between - (peak1 - trough_between)
                
                confidence = self._calculate_pattern_confidence(
                    peak_similarity=1 - abs(peak1 - peak2) / peak1,
                    volume_confirmation=0.7
                )
                
                pattern = ChartPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    pattern_type=PatternType.DOUBLE_TOP,
                    confidence=confidence,
                    start_time=price_data.index[peaks[i]],
                    end_time=price_data.index[peaks[i + 1]],
                    trend_direction=TrendDirection.BEARISH,
                    price_target=price_target,
                    stop_loss=max(peak1, peak2) * 1.02,
                    resistance_level=max(peak1, peak2),
                    support_level=trough_between
                )
                patterns.append(pattern)
        
        # Double bottoms
        troughs, _ = find_peaks(-lows, distance=10, prominence=lows.std() * 0.5)
        
        for i in range(len(troughs) - 1):
            bottom1 = lows[troughs[i]]
            bottom2 = lows[troughs[i + 1]]
            
            if abs(bottom1 - bottom2) / bottom1 < 0.02:
                peak_between = max(highs[troughs[i]:troughs[i + 1]])
                price_target = peak_between + (peak_between - bottom1)
                
                confidence = self._calculate_pattern_confidence(
                    peak_similarity=1 - abs(bottom1 - bottom2) / bottom1,
                    volume_confirmation=0.7
                )
                
                pattern = ChartPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    pattern_type=PatternType.DOUBLE_BOTTOM,
                    confidence=confidence,
                    start_time=price_data.index[troughs[i]],
                    end_time=price_data.index[troughs[i + 1]],
                    trend_direction=TrendDirection.BULLISH,
                    price_target=price_target,
                    stop_loss=min(bottom1, bottom2) * 0.98,
                    support_level=min(bottom1, bottom2),
                    resistance_level=peak_between
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_triangles(
        self,
        symbol: str,
        price_data: pd.DataFrame
    ) -> List[ChartPattern]:
        """Detect triangle patterns (ascending, descending, symmetrical)"""
        patterns = []
        highs = price_data['high'].values
        lows = price_data['low'].values
        
        window = min(30, len(price_data) // 2)
        if window < 10:
            return patterns
        
        # Analyze recent price action
        recent_highs = highs[-window:]
        recent_lows = lows[-window:]
        
        # Fit trend lines
        x = np.arange(len(recent_highs))
        upper_trend = np.polyfit(x, recent_highs, 1)
        lower_trend = np.polyfit(x, recent_lows, 1)
        
        upper_slope = upper_trend[0]
        lower_slope = lower_trend[0]
        
        # Ascending triangle: flat top, rising bottom
        if abs(upper_slope) < 0.01 and lower_slope > 0.05:
            resistance = np.mean(recent_highs[-5:])
            confidence = min(0.9, lower_slope * 10)
            
            pattern = ChartPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                pattern_type=PatternType.ASCENDING_TRIANGLE,
                confidence=confidence,
                start_time=price_data.index[-window],
                trend_direction=TrendDirection.BULLISH,
                resistance_level=resistance,
                price_target=resistance * 1.05
            )
            patterns.append(pattern)
        
        # Descending triangle: declining top, flat bottom
        elif upper_slope < -0.05 and abs(lower_slope) < 0.01:
            support = np.mean(recent_lows[-5:])
            confidence = min(0.9, abs(upper_slope) * 10)
            
            pattern = ChartPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                pattern_type=PatternType.DESCENDING_TRIANGLE,
                confidence=confidence,
                start_time=price_data.index[-window],
                trend_direction=TrendDirection.BEARISH,
                support_level=support,
                price_target=support * 0.95
            )
            patterns.append(pattern)
        
        # Symmetrical triangle: converging trend lines
        elif upper_slope < 0 and lower_slope > 0:
            confidence = min(0.8, (abs(upper_slope) + lower_slope) * 5)
            
            pattern = ChartPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                confidence=confidence,
                start_time=price_data.index[-window],
                trend_direction=TrendDirection.NEUTRAL
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _detect_flags_wedges(
        self,
        symbol: str,
        price_data: pd.DataFrame
    ) -> List[ChartPattern]:
        """Detect flag and wedge patterns"""
        patterns = []
        closes = price_data['close'].values
        
        if len(closes) < 20:
            return patterns
        
        # Calculate short-term trend
        recent_closes = closes[-20:]
        x = np.arange(len(recent_closes))
        trend = np.polyfit(x, recent_closes, 1)
        slope = trend[0]
        
        # Bull flag: uptrend followed by slight downward consolidation
        if len(closes) > 40:
            prev_trend = np.polyfit(np.arange(20), closes[-40:-20], 1)[0]
            if prev_trend > 0.1 and -0.05 < slope < 0:
                confidence = 0.75
                
                pattern = ChartPattern(
                    pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    pattern_type=PatternType.BULL_FLAG,
                    confidence=confidence,
                    start_time=price_data.index[-20],
                    trend_direction=TrendDirection.BULLISH,
                    price_target=closes[-1] * 1.05
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_breakouts(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame]
    ) -> List[ChartPattern]:
        """Detect breakout patterns"""
        patterns = []
        closes = price_data['close'].values
        
        if len(closes) < 20:
            return patterns
        
        # Identify recent range
        recent_high = max(closes[-20:-1])
        recent_low = min(closes[-20:-1])
        current_close = closes[-1]
        
        # Breakout above resistance
        if current_close > recent_high * 1.01:
            confidence = 0.75
            if volume_data is not None:
                # Higher confidence with volume confirmation
                recent_vol = volume_data['volume'].values[-1]
                avg_vol = np.mean(volume_data['volume'].values[-20:-1])
                if recent_vol > avg_vol * 1.5:
                    confidence = 0.85
            
            pattern = ChartPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                pattern_type=PatternType.BREAKOUT,
                confidence=confidence,
                detected_at=datetime.utcnow(),
                start_time=price_data.index[-20],
                trend_direction=TrendDirection.BULLISH,
                resistance_level=recent_high,
                price_target=current_close + (current_close - recent_low),
                volume_confirmation=volume_data is not None
            )
            patterns.append(pattern)
        
        # Breakdown below support
        elif current_close < recent_low * 0.99:
            confidence = 0.75
            if volume_data is not None:
                recent_vol = volume_data['volume'].values[-1]
                avg_vol = np.mean(volume_data['volume'].values[-20:-1])
                if recent_vol > avg_vol * 1.5:
                    confidence = 0.85
            
            pattern = ChartPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                pattern_type=PatternType.BREAKDOWN,
                confidence=confidence,
                detected_at=datetime.utcnow(),
                start_time=price_data.index[-20],
                trend_direction=TrendDirection.BEARISH,
                support_level=recent_low,
                price_target=current_close - (recent_high - current_close),
                volume_confirmation=volume_data is not None
            )
            patterns.append(pattern)
        
        return patterns
    
    async def detect_support_resistance(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame] = None
    ) -> List[SupportResistanceLevel]:
        """
        Detect support and resistance levels
        
        Args:
            symbol: Trading symbol
            price_data: DataFrame with OHLC data
            volume_data: Optional DataFrame with volume data
            
        Returns:
            List of support and resistance levels
        """
        levels = []
        highs = price_data['high'].values
        lows = price_data['low'].values
        closes = price_data['close'].values
        
        # Find resistance levels (local maxima)
        resistance_indices = argrelextrema(highs, np.greater, order=5)[0]
        
        for idx in resistance_indices:
            if idx >= len(price_data):
                continue
                
            price_level = highs[idx]
            
            # Count touches (price came within 1% of level)
            touches = sum(1 for h in highs if abs(h - price_level) / price_level < 0.01)
            
            if touches >= 2:
                # Calculate strength based on touches and time relevance
                time_diff = (datetime.utcnow() - price_data.index[idx]).days
                time_relevance = max(0.1, 1.0 - (time_diff / 365))
                strength = min(1.0, (touches / 10) * time_relevance)
                
                level = SupportResistanceLevel(
                    level_id=f"level_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    price_level=price_level,
                    level_type="resistance",
                    strength=strength,
                    touches=touches,
                    first_touch=price_data.index[idx],
                    last_touch=price_data.index[-1] if closes[-1] > price_level * 0.99 else price_data.index[idx],
                    time_relevance=time_relevance,
                    volume_at_level=volume_data['volume'].iloc[idx] if volume_data is not None else 0.0,
                    broken=closes[-1] > price_level
                )
                levels.append(level)
        
        # Find support levels (local minima)
        support_indices = argrelextrema(lows, np.less, order=5)[0]
        
        for idx in support_indices:
            if idx >= len(price_data):
                continue
                
            price_level = lows[idx]
            touches = sum(1 for l in lows if abs(l - price_level) / price_level < 0.01)
            
            if touches >= 2:
                time_diff = (datetime.utcnow() - price_data.index[idx]).days
                time_relevance = max(0.1, 1.0 - (time_diff / 365))
                strength = min(1.0, (touches / 10) * time_relevance)
                
                level = SupportResistanceLevel(
                    level_id=f"level_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    price_level=price_level,
                    level_type="support",
                    strength=strength,
                    touches=touches,
                    first_touch=price_data.index[idx],
                    last_touch=price_data.index[-1] if closes[-1] < price_level * 1.01 else price_data.index[idx],
                    time_relevance=time_relevance,
                    volume_at_level=volume_data['volume'].iloc[idx] if volume_data is not None else 0.0,
                    broken=closes[-1] < price_level
                )
                levels.append(level)
        
        return levels
    
    async def detect_unusual_options_activity(
        self,
        symbol: str,
        options_data: pd.DataFrame,
        historical_data: Optional[pd.DataFrame] = None
    ) -> List[OptionsActivity]:
        """
        Detect unusual options activity
        
        Args:
            symbol: Trading symbol
            options_data: Current options chain data
            historical_data: Historical options data for comparison
            
        Returns:
            List of unusual options activities
        """
        activities = []
        
        for _, option in options_data.iterrows():
            volume = option.get('volume', 0)
            open_interest = option.get('open_interest', 1)
            avg_volume = option.get('avg_volume', volume * 0.5)
            
            if avg_volume == 0:
                avg_volume = 1
            
            volume_multiple = volume / avg_volume
            volume_oi_ratio = volume / max(open_interest, 1)
            
            # Detect unusual volume
            if volume_multiple > 3.0:
                activity_type = OptionsActivityType.UNUSUAL_VOLUME
                confidence = min(0.95, 0.5 + (volume_multiple / 20))
                
                # Detect sweeps (aggressive buying)
                if volume_multiple > 5.0 and volume_oi_ratio > 0.5:
                    activity_type = OptionsActivityType.SWEEP
                    confidence = min(0.95, confidence + 0.1)
                
                # Golden sweep (very large and aggressive)
                if volume_multiple > 10.0:
                    activity_type = OptionsActivityType.GOLDEN_SWEEP
                    confidence = 0.95
                
                # Determine sentiment
                sentiment = TrendDirection.BULLISH if option['option_type'] == 'call' else TrendDirection.BEARISH
                
                activity = OptionsActivity(
                    activity_id=f"act_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    activity_type=activity_type,
                    strike=option['strike'],
                    expiration=option['expiration'],
                    option_type=option['option_type'],
                    volume=int(volume),
                    open_interest=int(open_interest),
                    volume_oi_ratio=volume_oi_ratio,
                    avg_volume=avg_volume,
                    volume_multiple=volume_multiple,
                    premium=option.get('premium', 0.0),
                    implied_volatility=option.get('implied_volatility', 0.0),
                    delta=option.get('delta'),
                    sentiment=sentiment,
                    confidence=confidence
                )
                activities.append(activity)
        
        return activities
    
    async def detect_volume_anomalies(
        self,
        symbol: str,
        volume_data: pd.DataFrame,
        price_data: pd.DataFrame,
        timeframe: str = "1D"
    ) -> List[VolumeAnomaly]:
        """
        Detect volume anomalies
        
        Args:
            symbol: Trading symbol
            volume_data: Volume data
            price_data: Price data for correlation
            timeframe: Timeframe for analysis
            
        Returns:
            List of volume anomalies
        """
        anomalies = []
        volumes = volume_data['volume'].values
        prices = price_data['close'].values
        
        if len(volumes) < 20:
            return anomalies
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:-1])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate price-volume correlation
        if len(prices) >= 20:
            price_changes = np.diff(prices[-20:])
            volume_changes = np.diff(volumes[-20:])
            correlation = np.corrcoef(price_changes, volume_changes)[0, 1]
        else:
            correlation = 0.0
        
        # Volume spike
        if volume_ratio > 2.0:
            price_change = (prices[-1] - prices[-2]) / prices[-2] if len(prices) > 1 else 0.0
            
            anomaly = VolumeAnomaly(
                anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                anomaly_type=VolumeAnomalyType.SPIKE,
                current_volume=int(current_volume),
                average_volume=avg_volume,
                volume_ratio=volume_ratio,
                price_change=price_change,
                price_volume_correlation=correlation,
                significance=min(0.95, volume_ratio / 10),
                timeframe=timeframe
            )
            anomalies.append(anomaly)
        
        # Volume divergence (price moving but volume declining)
        if len(volumes) >= 5:
            recent_price_trend = (prices[-1] - prices[-5]) / prices[-5]
            recent_volume_trend = (volumes[-1] - np.mean(volumes[-5:-1])) / np.mean(volumes[-5:-1])
            
            if abs(recent_price_trend) > 0.02 and recent_volume_trend < -0.3:
                anomaly = VolumeAnomaly(
                    anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    anomaly_type=VolumeAnomalyType.DIVERGENCE,
                    current_volume=int(current_volume),
                    average_volume=avg_volume,
                    volume_ratio=volume_ratio,
                    price_change=recent_price_trend,
                    price_volume_correlation=correlation,
                    significance=min(0.9, abs(recent_volume_trend)),
                    timeframe=timeframe
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _calculate_pattern_confidence(self, **factors) -> float:
        """Calculate pattern confidence from multiple factors"""
        weights = {
            'shoulder_symmetry': 0.4,
            'peak_similarity': 0.4,
            'volume_confirmation': 0.3,
            'trend_alignment': 0.2,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for factor, value in factors.items():
            if factor in weights:
                weighted_sum += value * weights[factor]
                total_weight += weights[factor]
        
        if total_weight == 0:
            return 0.5
        
        return min(0.95, max(0.0, weighted_sum / total_weight))
    
    def _check_volume_confirmation(
        self,
        volume_data: Optional[pd.DataFrame],
        start_idx: int,
        end_idx: int
    ) -> float:
        """Check if volume confirms the pattern"""
        if volume_data is None:
            return 0.5
        
        try:
            volumes = volume_data['volume'].values[start_idx:end_idx + 1]
            if len(volumes) < 2:
                return 0.5
            
            avg_volume = np.mean(volumes[:-1])
            final_volume = volumes[-1]
            
            if final_volume > avg_volume * 1.5:
                return 0.9
            elif final_volume > avg_volume:
                return 0.7
            else:
                return 0.5
        except Exception:
            return 0.5
