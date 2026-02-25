
"""
Advanced Forecasting Algorithms for Heritage Shops
Implements multiple forecasting methods for improved accuracy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. MOVING AVERAGE FORECASTING
# ============================================================================

class MovingAverageForecaster:
    """Simple Moving Average (SMA) for stable demand patterns"""

    def __init__(self, window_size=3):
        self.window_size = window_size

    def forecast(self, historical_sales: List[float], periods_ahead=1) -> float:
        """
        Forecast using simple moving average

        Args:
            historical_sales: List of historical sales quantities
            periods_ahead: Number of periods to forecast (default 1)

        Returns:
            Forecasted demand
        """
        if len(historical_sales) < self.window_size:
            return np.mean(historical_sales)

        # Take average of last N periods
        recent_sales = historical_sales[-self.window_size:]
        forecast = np.mean(recent_sales)

        return forecast

# ============================================================================
# 2. WEIGHTED MOVING AVERAGE
# ============================================================================

class WeightedMovingAverageForecaster:
    """Weighted Moving Average (WMA) - gives more weight to recent periods"""

    def __init__(self, window_size=3):
        self.window_size = window_size

    def forecast(self, historical_sales: List[float], periods_ahead=1) -> float:
        """
        Forecast using weighted moving average
        Recent periods get higher weights
        """
        if len(historical_sales) < self.window_size:
            return np.mean(historical_sales)

        recent_sales = historical_sales[-self.window_size:]

        # Create weights: most recent gets highest weight
        # Example for window=3: [1, 2, 3] -> weights become [1/6, 2/6, 3/6]
        weights = np.arange(1, len(recent_sales) + 1)
        weights = weights / weights.sum()

        forecast = np.average(recent_sales, weights=weights)

        return forecast

# ============================================================================
# 3. EXPONENTIAL SMOOTHING
# ============================================================================

class ExponentialSmoothingForecaster:
    """
    Exponential Smoothing - automatic adjustment based on recent trends
    Best for products with trend but no strong seasonality
    """

    def __init__(self, alpha=0.3):
        """
        Args:
            alpha: Smoothing parameter (0-1)
                  Higher = more weight to recent observations
                  Lower = more weight to historical average
        """
        self.alpha = alpha

    def forecast(self, historical_sales: List[float], periods_ahead=1) -> float:
        """
        Forecast using exponential smoothing
        """
        if len(historical_sales) == 0:
            return 0

        if len(historical_sales) == 1:
            return historical_sales[0]

        # Initialize with first observation
        smoothed = historical_sales[0]

        # Apply exponential smoothing
        for sale in historical_sales[1:]:
            smoothed = self.alpha * sale + (1 - self.alpha) * smoothed

        return smoothed

# ============================================================================
# 4. HOLT'S LINEAR TREND METHOD
# ============================================================================

class HoltLinearTrendForecaster:
    """
    Holt's Linear Trend - handles data with trends
    Good for products showing consistent growth or decline
    """

    def __init__(self, alpha=0.3, beta=0.1):
        """
        Args:
            alpha: Level smoothing parameter
            beta: Trend smoothing parameter
        """
        self.alpha = alpha
        self.beta = beta

    def forecast(self, historical_sales: List[float], periods_ahead=1) -> float:
        """
        Forecast using Holt's Linear Trend method
        """
        if len(historical_sales) < 2:
            return np.mean(historical_sales) if historical_sales else 0

        # Initialize level and trend
        level = historical_sales[0]
        trend = historical_sales[1] - historical_sales[0]

        # Update level and trend
        for sale in historical_sales[1:]:
            prev_level = level
            level = self.alpha * sale + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend

        # Forecast
        forecast = level + periods_ahead * trend

        return max(0, forecast)  # Ensure non-negative

# ============================================================================
# 5. SEASONAL DECOMPOSITION
# ============================================================================

class SeasonalForecaster:
    """
    Seasonal forecasting for tourism/seasonal products
    Adjusts baseline forecast by seasonal factors
    """

    def __init__(self, season_factors: Dict[int, float]):
        """
        Args:
            season_factors: Dictionary mapping month (1-12) to multiplier
                          Example: {6: 1.5, 7: 1.8, 8: 1.6, ...}
                          Summer months get > 1.0, winter months < 1.0
        """
        self.season_factors = season_factors

    def get_seasonal_factor(self, month: int) -> float:
        """Get seasonal multiplier for given month"""
        return self.season_factors.get(month, 1.0)

    def adjust_forecast(self, base_forecast: float, target_month: int) -> float:
        """
        Adjust baseline forecast for seasonality

        Args:
            base_forecast: Forecast from another method
            target_month: Month to forecast for (1-12)

        Returns:
            Seasonally adjusted forecast
        """
        factor = self.get_seasonal_factor(target_month)
        return base_forecast * factor

# ============================================================================
# 6. ENSEMBLE FORECASTER (COMBINES MULTIPLE METHODS)
# ============================================================================

class EnsembleForecaster:
    """
    Combines multiple forecasting methods for better accuracy
    Uses weighted average of different algorithms
    """

    def __init__(self):
        self.sma = MovingAverageForecaster(window_size=3)
        self.wma = WeightedMovingAverageForecaster(window_size=3)
        self.exp_smooth = ExponentialSmoothingForecaster(alpha=0.3)
        self.holt = HoltLinearTrendForecaster(alpha=0.3, beta=0.1)

    def forecast(self, historical_sales: List[float], 
                 velocity_category: str = 'Medium Mover',
                 periods_ahead: int = 1) -> Dict[str, float]:
        """
        Generate forecasts using multiple methods and combine them

        Args:
            historical_sales: Historical sales data
            velocity_category: Product velocity (affects weights)
            periods_ahead: Periods to forecast

        Returns:
            Dictionary with forecasts from each method and ensemble result
        """

        # Get forecast from each method
        forecasts = {
            'sma': self.sma.forecast(historical_sales, periods_ahead),
            'wma': self.wma.forecast(historical_sales, periods_ahead),
            'exp_smooth': self.exp_smooth.forecast(historical_sales, periods_ahead),
            'holt': self.holt.forecast(historical_sales, periods_ahead)
        }

        # Assign weights based on velocity category
        if velocity_category == 'Fast Mover':
            # Fast movers: more weight to recent data
            weights = {'sma': 0.15, 'wma': 0.30, 'exp_smooth': 0.35, 'holt': 0.20}
        elif velocity_category == 'Medium Mover':
            # Medium movers: balanced approach
            weights = {'sma': 0.25, 'wma': 0.25, 'exp_smooth': 0.25, 'holt': 0.25}
        else:
            # Slow movers: more weight to historical average
            weights = {'sma': 0.40, 'wma': 0.30, 'exp_smooth': 0.20, 'holt': 0.10}

        # Calculate ensemble forecast
        ensemble = sum(forecasts[method] * weights[method] 
                      for method in forecasts.keys())

        forecasts['ensemble'] = ensemble
        forecasts['recommended'] = ensemble  # Use ensemble as recommendation

        return forecasts

# ============================================================================
# 7. HERITAGE SHOPS SPECIFIC FORECASTER
# ============================================================================

class HeritageShopsForecaster:
    """
    Custom forecaster for Heritage Shops incorporating:
    - Tourism seasonality
    - Product velocity
    - Multiple forecasting methods
    """

    def __init__(self):
        self.ensemble = EnsembleForecaster()

        # Newfoundland & Labrador tourism seasonality
        # Based on typical cruise ship and tourism patterns
        self.nl_seasonality = {
            1: 0.4,   # January - Very Low (winter)
            2: 0.4,   # February - Very Low
            3: 0.5,   # March - Low
            4: 0.7,   # April - Starting to pick up
            5: 0.9,   # May - Spring tourists
            6: 1.3,   # June - High season starts
            7: 1.6,   # July - Peak season
            8: 1.5,   # August - Peak season
            9: 1.2,   # September - Still busy
            10: 0.8,  # October - Slowing down
            11: 0.5,  # November - Low
            12: 0.6   # December - Holiday shopping boost
        }

        self.seasonal = SeasonalForecaster(self.nl_seasonality)

    def forecast_monthly_demand(self, 
                               monthly_sales_history: List[Tuple[str, float]],
                               velocity_category: str,
                               months_ahead: int = 1) -> Dict:
        """
        Forecast demand for next N months

        Args:
            monthly_sales_history: List of (month_str, quantity) tuples
                                  Example: [('2024-01', 50), ('2024-02', 45), ...]
            velocity_category: 'Fast Mover', 'Medium Mover', etc.
            months_ahead: Number of months to forecast

        Returns:
            Dictionary with forecast details
        """

        # Extract just the quantities
        quantities = [qty for _, qty in monthly_sales_history]

        # Get base forecast using ensemble
        base_forecasts = self.ensemble.forecast(
            quantities, 
            velocity_category,
            periods_ahead=months_ahead
        )

        # Determine target month for seasonal adjustment
        if monthly_sales_history:
            last_month = datetime.strptime(monthly_sales_history[-1][0], '%Y-%m')
            target_month = last_month + timedelta(days=30 * months_ahead)
            target_month_num = target_month.month
        else:
            target_month_num = datetime.now().month

        # Apply seasonal adjustment
        base_forecast = base_forecasts['recommended']
        seasonal_forecast = self.seasonal.adjust_forecast(
            base_forecast, 
            target_month_num
        )

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(quantities, velocity_category)

        return {
            'base_forecast': round(base_forecast, 2),
            'seasonal_forecast': round(seasonal_forecast, 2),
            'seasonal_factor': self.nl_seasonality[target_month_num],
            'target_month': target_month_num,
            'confidence_score': round(confidence, 2),
            'velocity_category': velocity_category,
            'all_methods': base_forecasts
        }

    def _calculate_confidence(self, sales_history: List[float], 
                             velocity_category: str) -> float:
        """
        Calculate forecast confidence score (0-100)

        Higher confidence when:
        - More historical data
        - Lower variance
        - Fast/Medium movers (more predictable)
        """

        if len(sales_history) < 3:
            return 50.0  # Low confidence with little data

        # Base confidence on data length
        data_score = min(len(sales_history) / 12 * 40, 40)  # Max 40 points

        # Velocity score
        velocity_scores = {
            'Fast Mover': 30,
            'Medium Mover': 25,
            'Slow Mover': 15,
            'Very Slow': 10
        }
        velocity_score = velocity_scores.get(velocity_category, 15)

        # Variance score (lower variance = higher confidence)
        if len(sales_history) > 1:
            cv = np.std(sales_history) / (np.mean(sales_history) + 1)  # Coefficient of variation
            variance_score = max(30 - cv * 10, 0)  # Max 30 points
        else:
            variance_score = 15

        total_confidence = data_score + velocity_score + variance_score

        return min(total_confidence, 100.0)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Forecast for a typical Heritage Shops product

    # Historical monthly sales for "Puffin Plush" (Fast Mover)
    monthly_sales = [
        ('2024-01', 25),  # January - Low
        ('2024-02', 22),  # February - Low
        ('2024-03', 35),  # March - Picking up
        ('2024-04', 48),  # April
        ('2024-05', 62),  # May
        ('2024-06', 98),  # June - Tourism starts
        ('2024-07', 145), # July - Peak
        ('2024-08', 138), # August - Peak
        ('2024-09', 87),  # September
        ('2024-10', 52),  # October
        ('2024-11', 28),  # November
        ('2024-12', 42),  # December - Holiday boost
    ]

    forecaster = HeritageShopsForecaster()

    # Forecast next 3 months
    print("HERITAGE SHOPS FORECASTING DEMO")
    print("=" * 80)
    print("\nProduct: Puffin Plush (Fast Mover)")
    print("Historical data: 12 months (2024)")
    print("\nForecasting next 3 months...")
    print("-" * 80)

    for month_ahead in range(1, 4):
        forecast = forecaster.forecast_monthly_demand(
            monthly_sales,
            'Fast Mover',
            months_ahead=month_ahead
        )

        print(f"\nMonth {month_ahead} ahead (Month {forecast['target_month']}):")
        print(f"  Base Forecast: {forecast['base_forecast']:.0f} units")
        print(f"  Seasonal Factor: {forecast['seasonal_factor']:.1f}x")
        print(f"  Seasonal Forecast: {forecast['seasonal_forecast']:.0f} units")
        print(f"  Confidence Score: {forecast['confidence_score']:.0f}%")
