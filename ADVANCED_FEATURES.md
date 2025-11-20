# Advanced Features Guide

## 🚀 New Advanced Features

### 1. **Kelly Criterion Bet Sizing** (`advanced_analytics.py`)
- **Optimal bet sizing** based on edge and bankroll
- Calculates the mathematically optimal stake for each bet
- Uses fractional Kelly (25%) for risk management
- Integrated into parlay generation - shows recommended stake percentage

**Usage:**
```python
from advanced_analytics import KellyCriterion

kelly = KellyCriterion()
fraction = kelly.calculate_kelly_fraction(win_prob=0.55, odds=-110, bankroll=1000)
recommended_stake = bankroll * fraction
```

### 2. **Advanced Correlation Matrix** (`advanced_analytics.py`)
- **Correlation analysis** between betting legs
- Optimizes parlay selection for diversification
- Penalizes high correlation (same game, related markets)
- Rewards diversification across games and markets

**Features:**
- Market correlation detection
- Team correlation analysis
- Automatic parlay optimization based on correlation

### 3. **Portfolio Optimization** (`advanced_analytics.py`)
- **Multi-parlay portfolio management**
- Calculates portfolio expected value and variance
- Sharpe ratio calculation for risk-adjusted returns
- Optimal stake allocation across multiple parlays

**Usage:**
```python
from advanced_analytics import PortfolioOptimizer

optimizer = PortfolioOptimizer(bankroll=1000)
stakes = optimizer.optimize_stakes(parlays, max_total_stake=100)
sharpe = optimizer.calculate_sharpe_ratio(parlays, stakes)
```

### 4. **Risk Management System** (`advanced_analytics.py`)
- **Bankroll protection** with daily risk limits
- Drawdown monitoring (20% max drawdown)
- Automatic bet size limits
- Prevents over-betting

**Features:**
- Max daily risk percentage (default 5%)
- Per-bet stake limits
- Drawdown alerts

### 5. **Backtesting Framework** (`backtesting.py`)
- **Test strategies on historical data**
- Multiple strategy comparison
- Performance metrics (ROI, hit rate, drawdown)
- Bankroll simulation over time

**Strategies:**
- **Kelly**: Optimal bet sizing using Kelly Criterion
- **Fixed**: Fixed stake per bet
- **Proportional**: Percentage of bankroll
- **Conservative**: Only high-confidence bets

**Usage:**
```python
from backtesting import Backtester

backtester = Backtester(initial_bankroll=1000)
results = backtester.simulate_period(start_date, end_date, strategy="kelly")
comparison = backtester.compare_strategies(start_date, end_date)
```

### 6. **Real-Time Odds Monitoring** (`odds_monitor.py`)
- **Monitor odds changes** in real-time
- Alert system for significant movements
- Tracks odds history
- Configurable change thresholds

**Features:**
- Continuous monitoring
- Change detection (10% threshold)
- Alert callbacks
- Multi-sport support

**Usage:**
```python
from odds_monitor import OddsMonitor

monitor = OddsMonitor(check_interval=300)  # 5 minutes
monitor.register_alert(lambda game, changes: print(f"Alert: {changes}"))
monitor.start_monitoring(sport="basketball_nba", duration=3600)
```

### 7. **Advanced Analytics Dashboard**
New dashboard pages with:
- **ROI by Sport**: Performance breakdown
- **Confidence Accuracy**: Validate your confidence ratings
- **Parlay Size Performance**: Which size parlays perform best
- **Kelly Calculator**: Interactive bet sizing tool

### 8. **Enhanced Parlay Generation**
- **Correlation-optimized** parlay selection
- **Kelly Criterion** stake recommendations
- **Diversification scoring**
- **Adjusted confidence ratings**

## 📊 Dashboard Enhancements

### New Pages:
1. **Advanced Analytics** - Deep performance insights
2. **Backtesting** - Strategy validation
3. **Odds Monitor** - Real-time odds tracking
4. **Enhanced Settings** - Risk management configuration

### Enhanced Features:
- Kelly Criterion calculator
- Portfolio optimization tools
- Strategy comparison charts
- Advanced performance metrics

## 🎯 Usage Examples

### Calculate Optimal Stake
```python
from advanced_analytics import KellyCriterion

kelly = KellyCriterion()
# 55% win probability, -110 odds, $1000 bankroll
fraction = kelly.calculate_kelly_fraction(0.55, -110, 1000)
stake = 1000 * fraction  # Recommended stake
```

### Optimize Parlay Portfolio
```python
from advanced_analytics import PortfolioOptimizer

optimizer = PortfolioOptimizer(bankroll=1000)
parlays = [...]  # Your parlay candidates
stakes = optimizer.optimize_stakes(parlays, max_total_stake=100)
```

### Backtest Strategy
```python
from backtesting import Backtester
from datetime import datetime, timedelta

backtester = Backtester(1000)
results = backtester.simulate_period(
    datetime.now() - timedelta(days=30),
    datetime.now(),
    strategy="kelly"
)
print(f"ROI: {results['roi']:.1f}%")
print(f"Hit Rate: {results['hit_rate']*100:.1f}%")
```

### Monitor Odds
```python
from odds_monitor import OddsMonitor

def alert_handler(game, changes):
    print(f"Odds changed for {game['home_team']} vs {game['away_team']}")
    for change in changes:
        print(f"  {change['market']}: {change['old']} → {change['new']}")

monitor = OddsMonitor()
monitor.register_alert(alert_handler)
monitor.start_monitoring("basketball_nba", duration=3600)
```

## 🔧 Configuration

### Risk Management Settings
- **Bankroll**: Set your total bankroll
- **Max Daily Risk**: Percentage of bankroll at risk per day (default 5%)
- **Max Drawdown**: Maximum allowed drawdown (default 20%)

### Kelly Criterion Settings
- **Fractional Kelly**: Uses 25% of full Kelly for safety
- **Max Stake**: Capped at 5% of bankroll per bet

### Correlation Settings
- **Same Game Penalty**: 0.5 correlation penalty
- **Same Team Penalty**: 0.3 correlation penalty
- **Diversification Bonus**: Up to 0.2 score boost

## 📈 Performance Metrics

### New Metrics Available:
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Portfolio EV**: Expected value of entire portfolio
- **Correlation Score**: Diversification metric
- **Kelly Fraction**: Optimal bet size percentage

## 🎓 Best Practices

1. **Use Kelly Criterion** for optimal bet sizing
2. **Diversify** across games and markets
3. **Backtest** strategies before live betting
4. **Monitor odds** for value opportunities
5. **Set risk limits** to protect bankroll
6. **Track performance** by sport and parlay size

## 🚨 Risk Warnings

- Kelly Criterion can be aggressive - fractional Kelly recommended
- Always set daily risk limits
- Monitor drawdowns closely
- Backtest thoroughly before live betting
- Never bet more than you can afford to lose

