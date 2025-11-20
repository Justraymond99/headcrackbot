"""Streamlit dashboard for the sports betting parlay system."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models import Game, Parlay, Leg, DailyReport, PlayerProp, SessionLocal
from research_engine import ResearchEngine
from result_tracker import ResultTracker
from data_intake import DataIntake
from advanced_analytics import KellyCriterion, PortfolioOptimizer, RiskManager, AdvancedMetrics
from backtesting import Backtester
from odds_monitor import OddsMonitor
from auto_results import AutoResultUpdater
from ai_picks import AIPicks
from stat_shack import StatShack
from sport_research import SportResearch
from dice_gpt import DICEgpt
from picks_dashboard import PicksDashboard
from ml_models import MLPredictor
from bankroll_manager import BankrollManager
from value_bet_finder import ValueBetFinder
from line_shopper import LineShopper
from parlay_optimizer import ParlayOptimizer
from performance_analyzer import PerformanceAnalyzer
from clv_tracker import CLVTracker
from streak_tracker import StreakTracker
from notification_system import NotificationSystem
from bet_slip_builder import BetSlipBuilder
from market_efficiency_tracker import MarketEfficiencyTracker
from historical_matchup_analyzer import HistoricalMatchupAnalyzer
from live_betting_tracker import LiveBettingTracker
from export_reporter import ExportReporter
from refund_push_handler import RefundPushHandler
from smart_alerts import SmartAlerts
from custom_stat_builder import CustomStatBuilder
from social_features import SocialFeatures
from advanced_filters import AdvancedFilters
from weather_injury_impact import WeatherInjuryImpact
from auto_betting import AutoBetting
from config import DEFAULT_SPORTS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config with custom styling
st.set_page_config(
    page_title="RayBets",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .parlay-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .recommended-badge {
        background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .payout-display {
        font-size: 2rem;
        font-weight: bold;
        color: #10b981;
        text-align: center;
        padding: 1rem;
        background: #ecfdf5;
        border-radius: 10px;
        border: 2px solid #10b981;
    }
    .confidence-high {
        color: #10b981;
        font-weight: bold;
    }
    .confidence-moderate {
        color: #f59e0b;
        font-weight: bold;
    }
    .confidence-low {
        color: #ef4444;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db_session' not in st.session_state:
    st.session_state.db_session = SessionLocal()
if 'research_engine' not in st.session_state:
    st.session_state.research_engine = ResearchEngine()
if 'result_tracker' not in st.session_state:
    st.session_state.result_tracker = ResultTracker()
if 'data_intake' not in st.session_state:
    st.session_state.data_intake = DataIntake()
# Initialize services (don't store in session state to avoid pickle issues)
# Create fresh instances when needed instead


def calculate_payout(stake: float, odds: float) -> float:
    """Calculate payout from stake and American odds."""
    if odds > 0:
        return stake * (odds / 100) + stake
    else:
        return stake * (100 / abs(odds)) + stake

def calculate_profit(stake: float, odds: float) -> float:
    """Calculate profit (payout - stake)."""
    return calculate_payout(stake, odds) - stake

def main():
    st.markdown('<h1 class="main-header">🎲 RayBets</h1>', unsafe_allow_html=True)
    
    # Sidebar with enhanced styling
    with st.sidebar:
        st.markdown("### 🎯 Navigation")
        page = st.selectbox(
            "Choose a page",
            ["🏠 Dashboard", "🎲 DICEgpt", "📋 Picks Dashboard", "🤖 AI Picks", "📊 Stat Shack", 
             "✨ Recommended Plays", "🎲 Generate Parlays", "🔒 Lock Parlays", "📊 Update Results", 
             "📈 Performance", "🔬 Advanced Analytics", "🧪 Backtesting", "📡 Odds Monitor",
             "💰 Bankroll", "💎 Value Bets", "🛒 Line Shopping", "🎯 Parlay Optimizer",
             "📊 Performance Breakdown", "📉 CLV Tracker", "🔥 Streaks", "📝 Bet Slip",
             "📱 Live Betting", "📬 Notifications", "📤 Export", "🔍 Advanced Filters",
             "🌤️ Weather & Injuries", "🤖 Auto-Betting", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        # Extract page name (remove emoji)
        page = page.split(" ", 1)[1] if " " in page else page
        
        st.markdown("---")
        st.markdown("### 💰 Quick Stats")
        
        # Get quick stats
        db = st.session_state.db_session
        total_parlays = db.query(Parlay).count()
        locked_parlays = db.query(Parlay).filter_by(locked=True).count()
        pending_parlays = db.query(Parlay).filter_by(status="pending", locked=False).count()
        
        st.metric("Total Parlays", total_parlays)
        st.metric("Locked", locked_parlays)
        st.metric("Pending", pending_parlays)
        
        # Notification badge
        if 'notification_system' not in st.session_state:
            st.session_state.notification_system = NotificationSystem()
        unread_count = st.session_state.notification_system.get_notification_count()
        if unread_count > 0:
            st.markdown(f"### 🔔 Notifications")
            st.markdown(f"**{unread_count} unread**")
    
    # Auto-update results on dashboard load (background)
    if page == "Dashboard":
        # Check if we should auto-update (once per session)
        if 'results_updated' not in st.session_state:
            with st.spinner("🔄 Checking for game results..."):
                try:
                    auto_updater = AutoResultUpdater()
                    auto_updater.update_all_pending_results()
                    st.session_state.results_updated = True
                except:
                    pass  # Fail silently
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "DICEgpt":
        show_dice_gpt()
    elif page == "Picks Dashboard":
        show_picks_dashboard()
    elif page == "AI Picks":
        show_ai_picks()
    elif page == "Stat Shack":
        show_stat_shack()
    elif page == "Recommended Plays":
        show_recommended_plays()
    elif page == "Generate Parlays":
        show_generate_parlays()
    elif page == "Lock Parlays":
        show_lock_parlays()
    elif page == "Update Results":
        show_update_results()
    elif page == "Performance":
        show_performance()
    elif page == "Advanced Analytics":
        show_advanced_analytics()
    elif page == "Backtesting":
        show_backtesting()
    elif page == "Odds Monitor":
        show_odds_monitor()
    elif page == "Bankroll":
        show_bankroll()
    elif page == "Value Bets":
        show_value_bets()
    elif page == "Line Shopping":
        show_line_shopping()
    elif page == "Parlay Optimizer":
        show_parlay_optimizer()
    elif page == "Performance Breakdown":
        show_performance_breakdown()
    elif page == "CLV Tracker":
        show_clv_tracker()
    elif page == "Streaks":
        show_streaks()
    elif page == "Bet Slip":
        show_bet_slip()
    elif page == "Live Betting":
        show_live_betting()
    elif page == "Notifications":
        show_notifications()
    elif page == "Export":
        show_export()
    elif page == "Advanced Filters":
        show_advanced_filters()
    elif page == "Weather & Injuries":
        show_weather_injuries()
    elif page == "Auto-Betting":
        show_auto_betting()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    """Main dashboard view."""
    st.markdown("## 📊 Dashboard Overview")
    
    # Get today's stats
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    report = st.session_state.result_tracker.generate_daily_report(today)
    
    # Enhanced metrics with styling
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📋 Total Parlays", report.total_parlays, delta=None)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🔒 Locked Parlays", report.locked_parlays, delta=None)
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        hit_rate_display = f"{report.hit_rate * 100:.1f}%" if report.hit_rate else "N/A"
        delta = f"+{report.hit_rate * 100:.1f}%" if report.hit_rate and report.hit_rate > 0.5 else None
        st.metric("🎯 Hit Rate", hit_rate_display, delta=delta)
    with col4:
        roi_display = f"{report.roi:.1f}%" if report.roi else "N/A"
        delta = f"+{report.roi:.1f}%" if report.roi and report.roi > 0 else None
        st.metric("💰 ROI", roi_display, delta=delta)
    
    # Recent parlays with enhanced display
    st.markdown("---")
    st.markdown("### 📋 Recent Parlays")
    recent_parlays = st.session_state.db_session.query(Parlay).order_by(
        Parlay.created_at.desc()
    ).limit(10).all()
    
    if recent_parlays:
        for parlay in recent_parlays:
            with st.container():
                # Calculate payout if stake is set
                payout_display = "N/A"
                if parlay.stake and parlay.combined_odds:
                    payout = calculate_payout(parlay.stake, parlay.combined_odds)
                    profit = calculate_profit(parlay.stake, parlay.combined_odds)
                    payout_display = f"${payout:.2f} (${profit:+.2f})"
                
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                
                with col1:
                    st.markdown(f"**{parlay.name}**")
                    st.caption(f"{parlay.sport or 'Mixed'} • {parlay.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                with col2:
                    # Confidence badge
                    conf_class = {
                        "High": "confidence-high",
                        "Moderate": "confidence-moderate",
                        "Low": "confidence-low"
                    }.get(parlay.confidence_rating, "")
                    st.markdown(f'<span class="{conf_class}">🎯 {parlay.confidence_rating}</span>', unsafe_allow_html=True)
                    st.caption(f"Odds: {parlay.combined_odds:.0f}")
                
                with col3:
                    # Status badge
                    status_colors = {
                        "pending": "🟡",
                        "locked": "🔒",
                        "won": "🟢",
                        "lost": "🔴"
                    }
                    status_emoji = status_colors.get(parlay.status, "⚪")
                    st.markdown(f"{status_emoji} **{parlay.status.title()}**")
                    if parlay.result:
                        st.caption(f"Result: {parlay.result}")
                
                with col4:
                    # Payout display
                    st.markdown("**💰 Payout**")
                    st.caption(payout_display)
                
                with col5:
                    # Quick actions
                    if parlay.status == "pending" and not parlay.locked:
                        if st.button("🔒 Lock", key=f"quick_lock_{parlay.id}", use_container_width=True):
                            parlay.locked = True
                            parlay.locked_at = datetime.utcnow()
                            parlay.status = "locked"
                            st.session_state.db_session.commit()
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("📝 No parlays yet. Generate some parlays to get started!")


def show_recommended_plays():
    """Show recommended plays with estimated payouts."""
    st.markdown("## ✨ Recommended Plays")
    st.markdown("Top value parlays based on expected value and confidence")
    
    # Get top parlays
    db = st.session_state.db_session
    top_parlays = db.query(Parlay).filter_by(
        status="pending",
        locked=False
    ).order_by(
        Parlay.confidence_score.desc(),
        Parlay.expected_value.desc()
    ).limit(10).all()
    
    if not top_parlays:
        st.warning("⚠️ No recommended plays available. Generate some parlays first!")
        return
    
    # Stake input
    default_stake = st.number_input("💰 Default Stake ($)", min_value=1.0, value=10.0, step=1.0, key="rec_stake")
    
    st.markdown("---")
    
    # Display recommended plays
    for i, parlay in enumerate(top_parlays, 1):
        # Calculate payout
        payout = calculate_payout(default_stake, parlay.combined_odds)
        profit = calculate_profit(default_stake, parlay.combined_odds)
        roi = (profit / default_stake) * 100 if default_stake > 0 else 0
        
        # Confidence badge
        conf_badge = {
            "High": "🟢 HIGH CONFIDENCE",
            "Moderate": "🟡 MODERATE CONFIDENCE",
            "Low": "🔴 LOW CONFIDENCE"
        }.get(parlay.confidence_rating, "⚪ UNKNOWN")
        
        with st.expander(f"#{i} {parlay.name} - {conf_badge}", expanded=(i <= 3)):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("### 💵 Payout")
                st.markdown(f'<div class="payout-display">${payout:.2f}</div>', unsafe_allow_html=True)
                st.caption(f"Profit: ${profit:.2f} ({roi:.1f}% ROI)")
            
            with col2:
                st.markdown("### 📊 Metrics")
                st.metric("Expected Value", f"{parlay.expected_value*100:.1f}%")
                st.metric("Implied Prob", f"{parlay.implied_probability*100:.1f}%")
                st.metric("Combined Odds", f"{parlay.combined_odds:.0f}")
            
            with col3:
                st.markdown("### 🎯 Confidence")
                conf_score = parlay.confidence_score
                st.progress(conf_score, text=f"{conf_score*100:.0f}%")
                st.caption(f"Rating: {parlay.confidence_rating}")
            
            with col4:
                st.markdown("### 📈 Kelly Criterion")
                kelly = KellyCriterion()
                legs = db.query(Leg).filter_by(parlay_id=parlay.id).all()
                if legs:
                    leg_probs = [l.implied_probability or 0.5 for l in legs]
                    kelly_fraction = kelly.calculate_parlay_kelly(parlay, leg_probs)
                    recommended_stake = 1000 * kelly_fraction
                    st.metric("Recommended Stake", f"${recommended_stake:.2f}")
                    st.caption(f"Kelly: {kelly_fraction*100:.2f}%")
            
            # Legs breakdown
            st.markdown("#### 🎲 Legs Breakdown")
            legs = db.query(Leg).filter_by(parlay_id=parlay.id).all()
            
            for leg in legs:
                game = db.query(Game).filter_by(id=leg.game_id).first()
                if game:
                    leg_payout = calculate_payout(default_stake / len(legs), leg.odds)
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        if leg.bet_type == 'prop':
                            if leg.prop_value:
                                st.write(f"**PROP**: {leg.player_name} {leg.prop_type} {leg.selection} {leg.prop_value}")
                            else:
                                st.write(f"**PROP**: {leg.player_name} {leg.prop_type} - {leg.selection}")
                        elif leg.bet_type == 'fighter_moneyline':
                            st.write(f"**UFC**: {leg.selection}")
                        else:
                            st.write(f"**{leg.bet_type.upper()}**: {leg.selection}")
                        
                        game_display = f"{game.away_team or game.fighter2} @ {game.home_team or game.fighter1}" if game.sport != "UFC" else f"{game.fighter1} vs {game.fighter2}"
                        st.caption(f"{game.sport}: {game_display}")
                    
                    with col2:
                        st.write(f"**Odds**: {leg.odds:.0f}")
                        st.write(f"**EV**: {leg.expected_value*100:.1f}%" if leg.expected_value else "**EV**: N/A")
                        st.caption(leg.reasoning or "No reasoning provided")
                    
                    with col3:
                        st.metric("Leg Payout", f"${leg_payout:.2f}")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"🔒 Lock This Parlay", key=f"lock_rec_{parlay.id}"):
                    parlay.locked = True
                    parlay.locked_at = datetime.utcnow()
                    parlay.status = "locked"
                    parlay.stake = default_stake
                    db.commit()
                    st.success(f"✅ Locked: {parlay.name}")
                    st.rerun()
            
            with col2:
                if st.button(f"📋 View Details", key=f"view_{parlay.id}"):
                    st.info("Navigate to 'Lock Parlays' page for full details")
            
            with col3:
                if st.button(f"🗑️ Delete", key=f"delete_rec_{parlay.id}"):
                    db.delete(parlay)
                    db.commit()
                    st.success("Deleted!")
                    st.rerun()
            
            st.markdown("---")


def show_generate_parlays():
    """Generate new parlays."""
    st.markdown("## 🎲 Generate Parlays")
    st.markdown("Create optimized parlay combinations from available games")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sports = st.multiselect(
            "🏀 Select Sports",
            DEFAULT_SPORTS,
            default=DEFAULT_SPORTS[:2] if len(DEFAULT_SPORTS) >= 2 else DEFAULT_SPORTS
        )
    
    with col2:
        max_parlays = st.number_input("📊 Max Parlays to Generate", min_value=1, max_value=20, value=10)
    
    with col3:
        default_stake = st.number_input("💰 Default Stake ($)", min_value=1.0, value=10.0, step=1.0)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Fetch Latest Data", type="primary", use_container_width=True):
            with st.spinner("Fetching data from APIs..."):
                st.session_state.data_intake.fetch_all_data(sports)
            st.success("✅ Data fetched successfully!")
    
    with col2:
        include_sgp = st.checkbox("🎯 Include Same Game Parlays (SGP)", value=True, help="Generate parlays with all legs from the same game")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Generate Parlays", type="primary", use_container_width=True):
            with st.spinner("Analyzing games and generating optimal parlays..."):
                # Get games
                games = st.session_state.db_session.query(Game).filter(
                    Game.sport.in_(sports),
                    Game.status == "scheduled"
                ).all()
                
                if not games:
                    st.warning("⚠️ No games found. Please fetch data first.")
                else:
                    parlays = st.session_state.research_engine.generate_parlays(games, max_parlays, include_sgp=include_sgp)
                    
                    if parlays:
                        st.success(f"✨ Generated {len(parlays)} parlays!")
                        st.markdown("---")
                        
                        for i, parlay_data in enumerate(parlays, 1):
                            # Calculate payout
                            payout = calculate_payout(default_stake, parlay_data['combined_odds'])
                            profit = calculate_profit(default_stake, parlay_data['combined_odds'])
                            
                            # Confidence badge
                            conf_badge = {
                                "High": "🟢 HIGH",
                                "Moderate": "🟡 MODERATE",
                                "Low": "🔴 LOW"
                            }.get(parlay_data['confidence_rating'], "⚪")
                            
                            # SGP badge
                            sgp_badge = "🎯 SGP" if parlay_data.get('is_sgp') else ""
                            prop_count = parlay_data.get('prop_count', 0)
                            prop_badge = f"📊 {prop_count} Props" if prop_count > 0 else ""
                            
                            title_parts = [f"#{i}", conf_badge, parlay_data['confidence_rating'] + " Confidence"]
                            if sgp_badge:
                                title_parts.insert(1, sgp_badge)
                            if prop_badge:
                                title_parts.append(prop_badge)
                            title_parts.append(f"${payout:.2f} Payout (${profit:.2f} profit)")
                            
                            with st.expander(
                                " - ".join(title_parts),
                                expanded=(i <= 3)
                            ):
                                # Show game info for SGP
                                if parlay_data.get('is_sgp') and parlay_data.get('game'):
                                    game = parlay_data['game']
                                    if game.sport == "UFC":
                                        st.markdown(f"**🎯 Same Game Parlay:** {game.fighter1} vs {game.fighter2}")
                                    else:
                                        st.markdown(f"**🎯 Same Game Parlay:** {game.away_team} @ {game.home_team}")
                                    st.caption(f"{game.sport} • {game.game_date.strftime('%Y-%m-%d %H:%M')}")
                                    st.markdown("---")
                                # Top metrics row
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.markdown("### 💵 Payout")
                                    st.markdown(f'<div class="payout-display">${payout:.2f}</div>', unsafe_allow_html=True)
                                    st.caption(f"Profit: ${profit:.2f}")
                                
                                with col2:
                                    st.markdown("### 📊 Metrics")
                                    st.metric("Expected Value", f"{parlay_data['expected_value']*100:.1f}%")
                                    st.metric("Implied Prob", f"{parlay_data['implied_probability']*100:.1f}%")
                                    st.metric("Combined Odds", f"{parlay_data['combined_odds']:.0f}")
                                
                                with col3:
                                    st.markdown("### 🎯 Confidence")
                                    conf_score = parlay_data['confidence_score']
                                    st.progress(conf_score, text=f"{conf_score*100:.0f}%")
                                    st.caption(f"Rating: {parlay_data['confidence_rating']}")
                                
                                with col4:
                                    st.markdown("### 📈 Score")
                                    st.metric("Parlay Score", f"{parlay_data['score']:.3f}")
                                    if 'recommended_stake_pct' in parlay_data:
                                        st.caption(f"Kelly: {parlay_data['recommended_stake_pct']:.2f}%")
                                
                                st.markdown("---")
                                st.markdown("#### 🎲 Legs Breakdown")
                                
                                for j, leg in enumerate(parlay_data['legs'], 1):
                                    game = leg['game']
                                    leg_payout = calculate_payout(default_stake / parlay_data['num_legs'], leg['odds'])
                                    
                                    with st.container():
                                        col1, col2, col3 = st.columns([3, 2, 1])
                                        
                                        with col1:
                                            if leg['bet_type'] == 'prop':
                                                player_name = leg.get('player_name', 'Player')
                                                prop_type = leg.get('prop_type', '')
                                                selection = leg['selection']
                                                prop_value = leg.get('prop_value')
                                                
                                                if prop_value is not None:
                                                    st.write(f"**#{j} PROP**: {player_name} {prop_type} {selection} {prop_value} @ {leg['odds']:.0f}")
                                                else:
                                                    st.write(f"**#{j} PROP**: {player_name} {prop_type} - {selection} @ {leg['odds']:.0f}")
                                            elif leg['bet_type'] == 'fighter_moneyline':
                                                st.write(f"**#{j} UFC**: {leg['selection']} @ {leg['odds']:.0f}")
                                            else:
                                                st.write(f"**#{j} {leg['bet_type'].upper()}**: {leg['selection']} @ {leg['odds']:.0f}")
                                            
                                            game_display = f"{game.away_team or game.fighter2} @ {game.home_team or game.fighter1}" if game.sport != "UFC" else f"{game.fighter1} vs {game.fighter2}"
                                            st.caption(f"📍 {game.sport}: {game_display}")
                                        
                                        with col2:
                                            st.write(f"**EV**: {leg['expected_value']*100:.1f}%" if leg.get('expected_value') else "**EV**: N/A")
                                            st.write(f"**Confidence**: {leg['confidence_score']*100:.0f}%")
                                            st.caption(leg['reasoning'] or "No reasoning")
                                        
                                        with col3:
                                            st.metric("Leg Payout", f"${leg_payout:.2f}")
                                        
                                        if j < len(parlay_data['legs']):
                                            st.markdown("---")
                                
                                st.markdown("---")
                                
                                # Save parlay section
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    parlay_name = st.text_input(
                                        f"Parlay Name",
                                        value=f"{parlay_data['confidence_rating']} {parlay_data['num_legs']}-Leg Parlay",
                                        key=f"parlay_name_{i}"
                                    )
                                
                                with col2:
                                    if st.button(f"💾 Save Parlay", key=f"save_{i}", use_container_width=True):
                                        sport = sports[0] if len(sports) == 1 else None
                                        parlay = st.session_state.research_engine.save_parlay(
                                            parlay_data, parlay_name, sport
                                        )
                                        st.success(f"✅ Saved: {parlay.name}")
                                        st.rerun()
                    else:
                        st.warning("⚠️ No qualifying parlays found. Try adjusting your criteria or fetching more data.")


def show_lock_parlays():
    """Lock in parlays for the day."""
    st.markdown("## 🔒 Lock Parlays")
    st.markdown("Review and lock in your final parlay selections for the day")
    
    # Get pending parlays
    pending_parlays = st.session_state.db_session.query(Parlay).filter(
        Parlay.status == "pending",
        Parlay.locked == False
    ).order_by(Parlay.confidence_score.desc()).all()
    
    if not pending_parlays:
        st.info("No pending parlays to lock.")
        return
    
    for i, parlay in enumerate(pending_parlays, 1):
        # Calculate estimated payout
        default_stake = 10.0
        estimated_payout = calculate_payout(default_stake, parlay.combined_odds)
        estimated_profit = calculate_profit(default_stake, parlay.combined_odds)
        
        conf_badge = {
            "High": "🟢",
            "Moderate": "🟡",
            "Low": "🔴"
        }.get(parlay.confidence_rating, "⚪")
        
        with st.expander(
            f"#{i} {conf_badge} {parlay.name} - ${estimated_payout:.2f} Payout (${estimated_profit:.2f} profit)",
            expanded=(i <= 2)
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📊 Metrics")
                st.metric("Expected Value", f"{parlay.expected_value*100:.1f}%")
                st.metric("Confidence Score", f"{parlay.confidence_score:.2f}")
                st.metric("Combined Odds", f"{parlay.combined_odds:.0f}")
                st.caption(f"Status: {parlay.status}")
            
            with col2:
                st.markdown("### 💵 Payout Calculator")
                stake = st.number_input(
                    f"💰 Stake ($)",
                    min_value=0.0,
                    value=default_stake,
                    step=1.0,
                    key=f"stake_{parlay.id}"
                )
                
                # Calculate real-time payout
                payout = calculate_payout(stake, parlay.combined_odds)
                profit = calculate_profit(stake, parlay.combined_odds)
                roi = (profit / stake * 100) if stake > 0 else 0
                
                st.markdown(f'<div class="payout-display">${payout:.2f}</div>', unsafe_allow_html=True)
                st.caption(f"Profit: ${profit:.2f} ({roi:.1f}% ROI)")
            
            with col3:
                st.markdown("### 🎯 Confidence")
                st.progress(parlay.confidence_score, text=f"{parlay.confidence_score*100:.0f}%")
                st.caption(f"Rating: {parlay.confidence_rating}")
                
                # Kelly recommendation
                kelly = KellyCriterion()
                legs = st.session_state.db_session.query(Leg).filter_by(parlay_id=parlay.id).all()
                if legs:
                    leg_probs = [l.implied_probability or 0.5 for l in legs]
                    kelly_fraction = kelly.calculate_parlay_kelly(parlay, leg_probs)
                    kelly_stake = 1000 * kelly_fraction
                    st.metric("Kelly Stake", f"${kelly_stake:.2f}")
                    st.caption(f"({kelly_fraction*100:.2f}% of bankroll)")
            
            st.write("**Legs:**")
            legs = st.session_state.db_session.query(Leg).filter_by(parlay_id=parlay.id).all()
            for leg in legs:
                game = st.session_state.db_session.query(Game).filter_by(id=leg.game_id).first()
                
                if leg.bet_type == 'prop':
                    game_display = f"{game.away_team or game.fighter2} @ {game.home_team or game.fighter1}" if game.sport != "UFC" else f"{game.fighter1} vs {game.fighter2}"
                    if leg.prop_value is not None:
                        # Over/Under prop
                        st.write(f"- **PROP**: {leg.player_name or 'Player'} {leg.prop_type or ''} {leg.selection} {leg.prop_value} @ {leg.odds:.0f}")
                    else:
                        # Yes/No prop
                        st.write(f"- **PROP**: {leg.player_name or 'Player'} {leg.prop_type or ''} - {leg.selection} @ {leg.odds:.0f}")
                    st.write(f"  {game.sport}: {game_display}")
                elif leg.bet_type == 'fighter_moneyline':
                    st.write(f"- **UFC**: {leg.selection} @ {leg.odds:.0f}")
                    st.write(f"  {game.fighter1} vs {game.fighter2}")
                else:
                    game_display = f"{game.away_team or game.fighter2} @ {game.home_team or game.fighter1}" if game.sport != "UFC" else f"{game.fighter1} vs {game.fighter2}"
                    st.write(f"- **{leg.bet_type.upper()}**: {leg.selection} @ {leg.odds:.0f}")
                    st.write(f"  {game.sport}: {game_display}")
                
                st.write(f"  Reasoning: {leg.reasoning}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Lock Parlay", key=f"lock_{parlay.id}"):
                    parlay.locked = True
                    parlay.locked_at = datetime.utcnow()
                    parlay.status = "locked"
                    parlay.stake = stake
                    st.session_state.db_session.commit()
                    st.success(f"Locked: {parlay.name}")
                    st.rerun()
            
            with col2:
                if st.button(f"Delete Parlay", key=f"delete_{parlay.id}"):
                    st.session_state.db_session.delete(parlay)
                    st.session_state.db_session.commit()
                    st.success(f"Deleted: {parlay.name}")
                    st.rerun()


def show_update_results():
    """Update game results."""
    st.header("Update Results")
    
    # Get finished games that need results
    games = st.session_state.db_session.query(Game).filter(
        Game.status == "finished"
    ).all()
    
    # Get scheduled games (for manual result entry)
    scheduled_games = st.session_state.db_session.query(Game).filter(
        Game.status == "scheduled"
    ).order_by(Game.game_date).all()
    
    st.subheader("Enter Game Results")
    
    for game in scheduled_games:
        with st.expander(f"{game.sport}: {game.away_team} @ {game.home_team} - {game.game_date.strftime('%Y-%m-%d')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                home_score = st.number_input(
                    f"{game.home_team} Score",
                    min_value=0,
                    value=0,
                    key=f"home_{game.id}"
                )
            
            with col2:
                away_score = st.number_input(
                    f"{game.away_team} Score",
                    min_value=0,
                    value=0,
                    key=f"away_{game.id}"
                )
            
            if st.button(f"Update Result", key=f"update_{game.id}"):
                st.session_state.result_tracker.update_game_result(
                    game.id, home_score, away_score
                )
                
                # Update parlay results
                parlays = st.session_state.db_session.query(Parlay).join(Leg).filter(
                    Leg.game_id == game.id
                ).distinct().all()
                
                for parlay in parlays:
                    st.session_state.result_tracker.update_parlay_result(parlay.id)
                
                st.success("Results updated!")
                st.rerun()


def show_performance():
    """Performance analytics."""
    st.header("Performance Analytics")
    
    # Get trends
    days = st.slider("Days to analyze", min_value=7, max_value=90, value=30)
    trends = st.session_state.result_tracker.get_performance_trends(days)
    
    if len(trends) > 0:
        # ROI Chart
        fig_roi = px.line(
            trends,
            x="date",
            y="roi",
            title="ROI Over Time",
            labels={"roi": "ROI (%)", "date": "Date"}
        )
        st.plotly_chart(fig_roi, use_container_width=True)
        
        # Hit Rate Chart
        fig_hit = px.line(
            trends,
            x="date",
            y="hit_rate",
            title="Hit Rate Over Time",
            labels={"hit_rate": "Hit Rate (%)", "date": "Date"}
        )
        st.plotly_chart(fig_hit, use_container_width=True)
        
        # Win/Loss Chart
        fig_wl = go.Figure()
        fig_wl.add_trace(go.Bar(x=trends["date"], y=trends["wins"], name="Wins", marker_color="green"))
        fig_wl.add_trace(go.Bar(x=trends["date"], y=trends["losses"], name="Losses", marker_color="red"))
        fig_wl.update_layout(title="Wins vs Losses", xaxis_title="Date", yaxis_title="Count")
        st.plotly_chart(fig_wl, use_container_width=True)
        
        # Summary stats
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Average ROI", f"{trends['roi'].mean():.1f}%")
        with col2:
            st.metric("Average Hit Rate", f"{trends['hit_rate'].mean()*100:.1f}%")
        with col3:
            total_wins = trends["wins"].sum()
            total_losses = trends["losses"].sum()
            st.metric("Total W/L", f"{total_wins}-{total_losses}")
    else:
        st.info("No performance data available yet.")


def show_advanced_analytics():
    """Advanced analytics and metrics."""
    st.header("Advanced Analytics")
    
    # Get all finished parlays
    parlays = st.session_state.db_session.query(Parlay).filter(
        Parlay.result.in_(["win", "loss"])
    ).all()
    
    if not parlays:
        st.info("No completed parlays yet. Complete some bets to see analytics.")
        return
    
    metrics = AdvancedMetrics()
    
    # ROI by Sport
    st.subheader("ROI by Sport")
    sport_roi = metrics.calculate_roi_by_sport(parlays)
    if sport_roi:
        df_sport = pd.DataFrame(list(sport_roi.items()), columns=["Sport", "ROI"])
        fig = px.bar(df_sport, x="Sport", y="ROI", title="ROI by Sport")
        st.plotly_chart(fig, use_container_width=True)
    
    # Confidence Accuracy
    st.subheader("Confidence Rating Accuracy")
    confidence_acc = metrics.calculate_confidence_accuracy(parlays)
    if confidence_acc:
        df_conf = pd.DataFrame(list(confidence_acc.items()), columns=["Confidence", "Accuracy"])
        fig = px.bar(df_conf, x="Confidence", y="Accuracy", title="Hit Rate by Confidence Level")
        st.plotly_chart(fig, use_container_width=True)
    
    # Kelly Criterion Calculator
    st.subheader("Kelly Criterion Calculator")
    col1, col2, col3 = st.columns(3)
    with col1:
        win_prob = st.number_input("Win Probability", 0.0, 1.0, 0.55, 0.01)
    with col2:
        odds = st.number_input("American Odds", -500, 500, -110, 1)
    with col3:
        bankroll = st.number_input("Bankroll ($)", 100, 100000, 1000, 100)
    
    kelly = KellyCriterion()
    kelly_fraction = kelly.calculate_kelly_fraction(win_prob, odds, bankroll)
    recommended_stake = bankroll * kelly_fraction
    
    st.metric("Kelly Fraction", f"{kelly_fraction*100:.2f}%")
    st.metric("Recommended Stake", f"${recommended_stake:.2f}")


def show_backtesting():
    """Backtesting interface."""
    st.header("Strategy Backtesting")
    
    st.write("Test your betting strategies on historical data")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    strategy = st.selectbox("Strategy", ["kelly", "fixed", "proportional", "conservative"])
    initial_bankroll = st.number_input("Initial Bankroll", 100, 100000, 1000, 100)
    
    if st.button("Run Backtest", type="primary"):
        with st.spinner("Running backtest..."):
            backtester = Backtester(initial_bankroll)
            results = backtester.simulate_period(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                strategy
            )
            
            st.subheader("Backtest Results")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Final Bankroll", f"${results['final_bankroll']:.2f}")
            with col2:
                st.metric("Profit", f"${results['profit']:.2f}")
            with col3:
                st.metric("ROI", f"{results['roi']:.1f}%")
            with col4:
                st.metric("Hit Rate", f"{results['hit_rate']*100:.1f}%")
            
            st.write(f"**Total Bets:** {results['total_bets']}")
            st.write(f"**Wins:** {results['wins']} | **Losses:** {results['losses']}")


def show_odds_monitor():
    """Real-time odds monitoring."""
    st.header("Odds Monitor")
    
    st.write("Monitor odds changes in real-time")
    
    sport = st.selectbox("Sport", ["basketball_nba", "americanfootball_nfl", "baseball_mlb"])
    
    if st.button("Check Odds Changes"):
        monitor = OddsMonitor()
        alerts = monitor.check_odds_changes(sport)
        
        if alerts:
            st.success(f"Found {len(alerts)} odds changes!")
            for alert in alerts:
                with st.expander(f"Game: {alert['game'].get('home_team')} vs {alert['game'].get('away_team')}"):
                    for change in alert['changes']:
                        st.write(f"**{change['market']}**: {change['old']} → {change['new']} ({change['change_pct']:.1f}% change)")
        else:
            st.info("No significant odds changes detected")


def show_ai_picks():
    """AI Picks - Scans data and finds best plays."""
    st.markdown("## 🤖 AI Picks")
    st.markdown("**DICEgpt** scans thousands of lines and finds the best plays backed by hundreds of data points and historical outcomes.")
    
    col1, col2 = st.columns(2)
    with col1:
        sports = st.multiselect("Select Sports", DEFAULT_SPORTS, default=DEFAULT_SPORTS[:2])
    with col2:
        max_picks = st.number_input("Max Picks", min_value=5, max_value=50, value=10)
    
    if st.button("🔍 Generate AI Picks", type="primary"):
        with st.spinner("AI analyzing data points and historical outcomes..."):
            games = st.session_state.db_session.query(Game).filter(
                Game.sport.in_(sports),
                Game.status == "scheduled"
            ).all()
            
            if not games:
                st.warning("No games found. Fetch data first.")
            else:
                ai_picks = AIPicks()
                picks = ai_picks.generate_ai_picks(games, max_picks)
                
                if picks:
                    st.success(f"✨ Generated {len(picks)} AI picks!")
                    st.markdown("---")
                    
                    for i, pick in enumerate(picks, 1):
                        game = pick["game"]
                        leg = pick["leg"]
                        ai_picks = AIPicks()
                        confidence_level = ai_picks.get_pick_confidence_level(pick["confidence"])
                        
                        with st.expander(
                            f"#{i} {confidence_level} - {pick['ai_score']:.3f} AI Score",
                            expanded=(i <= 3)
                        ):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("### 📊 AI Analysis")
                                st.metric("AI Score", f"{pick['ai_score']:.3f}")
                                st.metric("Confidence", f"{pick['confidence']*100:.1f}%")
                                st.metric("Expected Value", f"{pick['expected_value']*100:.1f}%")
                            
                            with col2:
                                st.markdown("### 📈 Historical Data")
                                st.metric("Win Rate", f"{pick['historical_win_rate']*100:.1f}%")
                                st.metric("Data Points", pick['data_points'])
                                trend_emoji = {"hot": "🔥", "cold": "❄️", "neutral": "➡️"}.get(pick['recent_trend'], "➡️")
                                st.metric("Recent Trend", f"{trend_emoji} {pick['recent_trend'].title()}")
                            
                            with col3:
                                st.markdown("### 🎯 Bet Details")
                                if leg['bet_type'] == 'prop':
                                    if leg.get('prop_value'):
                                        st.write(f"**PROP**: {leg.get('player_name')} {leg.get('prop_type')} {leg['selection']} {leg['prop_value']}")
                                    else:
                                        st.write(f"**PROP**: {leg.get('player_name')} {leg.get('prop_type')} - {leg['selection']}")
                                else:
                                    st.write(f"**{leg['bet_type'].upper()}**: {leg['selection']}")
                                st.metric("Odds", f"{pick['odds']:.0f}")
                            
                            if pick['key_insights']:
                                st.markdown("### 💡 Key Insights")
                                for insight in pick['key_insights']:
                                    st.write(f"• {insight}")
                            
                            st.caption(f"Game: {game.away_team or game.fighter2} @ {game.home_team or game.fighter1} ({game.sport})")
                else:
                    st.warning("No AI picks found. Need more historical data.")


def show_stat_shack():
    """Stat Shack - Advanced metrics lookup."""
    st.markdown("## 📊 Stat Shack")
    st.markdown("Interface for looking up advanced player and team metrics to help you do in-depth research.")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Player Search", "🏀 Team Search", "📈 Head-to-Head", "📊 Prop Trends"])
    
    with tab1:
        st.markdown("### Player Statistics")
        col1, col2 = st.columns(2)
        with col1:
            player_query = st.text_input("Player Name")
        with col2:
            sport = st.selectbox("Sport", DEFAULT_SPORTS)
        
        if player_query and st.button("Search Player"):
            stat_shack = StatShack()
            players = stat_shack.search_players(player_query, sport)
            if players:
                selected_player = st.selectbox("Select Player", players)
                if selected_player:
                    stats = stat_shack.get_player_stats(selected_player, sport)
                    
                    st.markdown(f"### {stats['player_name']} - {stats['sport']}")
                    st.metric("Games Analyzed", stats['games_analyzed'])
                    
                    if stats['props']:
                        st.markdown("#### Prop Statistics")
                        for prop_type, prop_data in stats['props'].items():
                            with st.expander(prop_type):
                                st.metric("Average Line", f"{prop_data['average_line']:.1f}")
                                st.metric("Props Count", prop_data['count'])
    
    with tab2:
        st.markdown("### Team Statistics")
        col1, col2 = st.columns(2)
        with col1:
            team_query = st.text_input("Team Name", key="team_search")
        with col2:
            sport = st.selectbox("Sport", DEFAULT_SPORTS, key="team_sport")
        
        if team_query and st.button("Search Team"):
            stat_shack = StatShack()
            teams = stat_shack.search_teams(team_query, sport)
            if teams:
                selected_team = st.selectbox("Select Team", teams, key="team_select")
                if selected_team:
                    stats = stat_shack.get_team_stats(selected_team, sport)
                    
                    st.markdown(f"### {stats['team_name']} - {stats['sport']}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Wins", stats['win_loss']['wins'])
                    with col2:
                        st.metric("Losses", stats['win_loss']['losses'])
                    with col3:
                        win_pct = (stats['win_loss']['wins'] / (stats['win_loss']['wins'] + stats['win_loss']['losses'])) * 100 if (stats['win_loss']['wins'] + stats['win_loss']['losses']) > 0 else 0
                        st.metric("Win %", f"{win_pct:.1f}%")
    
    with tab3:
        st.markdown("### Head-to-Head Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            team1 = st.text_input("Team 1")
        with col2:
            team2 = st.text_input("Team 2")
        with col3:
            sport = st.selectbox("Sport", DEFAULT_SPORTS, key="h2h_sport")
        
        if team1 and team2 and st.button("Get H2H Stats"):
            stat_shack = StatShack()
            h2h = stat_shack.get_head_to_head(team1, team2, sport)
            st.markdown(f"### {h2h['team1']} vs {h2h['team2']}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{h2h['team1']} Wins", h2h['team1_wins'])
            with col2:
                st.metric(f"{h2h['team2']} Wins", h2h['team2_wins'])
            with col3:
                st.metric("Total Games", h2h['total_games'])
    
    with tab4:
        st.markdown("### Prop Trends")
        col1, col2, col3 = st.columns(3)
        with col1:
            player = st.text_input("Player Name", key="trend_player")
        with col2:
            prop_type = st.text_input("Prop Type (e.g., player_points)", key="trend_prop")
        with col3:
            sport = st.selectbox("Sport", DEFAULT_SPORTS, key="trend_sport")
        
        if player and prop_type and st.button("Get Trends"):
            stat_shack = StatShack()
            trends = stat_shack.get_prop_trends(player, prop_type, sport)
            st.markdown(f"### {trends['player_name']} - {trends['prop_type']}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Props", trends['total_props'])
            with col2:
                st.metric("Average Line", f"{trends['average_line']:.1f}")
            with col3:
                trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(trends['line_trend'], "➡️")
                st.metric("Trend", f"{trend_emoji} {trends['line_trend'].title()}")
    
    # Add Sport-Specific Research tab
    st.markdown("---")
    st.markdown("### 🏀 Sport-Specific Research")
    st.markdown("No sport is the same, so the features for each shouldn't be either. Get sport-specific analysis.")
    
    col1, col2 = st.columns(2)
    with col1:
        sport = st.selectbox("Select Sport", DEFAULT_SPORTS, key="sport_research")
    with col2:
        games = st.session_state.db_session.query(Game).filter(
            Game.sport == sport,
            Game.status == "scheduled"
        ).all()
        game_options = [f"{g.away_team or g.fighter2} @ {g.home_team or g.fighter1}" for g in games]
        selected_game_idx = st.selectbox("Select Game", range(len(game_options)), format_func=lambda x: game_options[x] if x < len(game_options) else "No games")
    
    if games and selected_game_idx < len(games) and st.button("Analyze Game"):
        game = games[selected_game_idx]
        sport_research = SportResearch()
        analysis = sport_research.analyze_game(game)
        
        st.markdown(f"### {sport} Analysis: {game.away_team or game.fighter2} @ {game.home_team or game.fighter1}")
        
        if analysis.get("key_insights"):
            st.markdown("#### 💡 Key Insights")
            for insight in analysis["key_insights"]:
                st.write(f"• {insight}")
        
        # Sport-specific metrics
        if sport == "NBA" and analysis.get("top_players"):
            st.markdown("#### 🏀 Top Players")
            for player, data in list(analysis["top_players"].items())[:5]:
                st.write(f"**{player}**: {len(data['props'])} props, Avg Line: {data['avg_line']:.1f}")
        
        if sport == "NFL" and analysis.get("positions"):
            st.markdown("#### 🏈 Position Breakdown")
            for pos, count in analysis["positions"].items():
                st.write(f"**{pos}**: {count} props")
        
        if sport == "MLB":
            st.markdown("#### ⚾ MLB Analysis")
            if analysis.get("batter_count"):
                st.metric("Batter Props", analysis["batter_count"])
            if analysis.get("pitcher_count"):
                st.metric("Pitcher Props", analysis["pitcher_count"])
        
        if sport == "NHL":
            st.markdown("#### 🏒 NHL Analysis")
            if analysis.get("goalie_props"):
                st.metric("Goalie Props", analysis["goalie_props"])
            if analysis.get("skater_props"):
                st.metric("Skater Props", analysis["skater_props"])
        
        if sport == "UFC" and analysis.get("fighters"):
            st.markdown("#### 🥊 UFC Fight Analysis")
            st.write(f"**{analysis['fighters']['fighter1']}** vs **{analysis['fighters']['fighter2']}**")
            if analysis.get("odds_favorite"):
                st.write(f"Favorite: {analysis['odds_favorite']}")


def show_dice_gpt():
    """DICEgpt - AI-powered betting assistant."""
    # Custom CSS for DICEgpt styling
    st.markdown("""
        <style>
        .dice-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .dice-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: white;
        }
        .bet-card {
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .bet-analysis {
            color: #ccc;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        .bet-details {
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #333;
        }
        .bet-detail-item {
            display: flex;
            flex-direction: column;
        }
        .bet-detail-label {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 0.25rem;
        }
        .bet-detail-value {
            font-size: 1.1rem;
            font-weight: bold;
            color: #fff;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="dice-header">
            <div class="dice-icon">🎲</div>
            <div>
                <h1 style="margin: 0; color: white;">DICEgpt</h1>
                <p style="margin: 0; color: #888;">Your personal sports betting analyst powered by RayBets</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history
    if "dice_gpt_history" not in st.session_state:
        st.session_state.dice_gpt_history = []
    
    # Quick action buttons
    st.markdown("### Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    quick_actions = [
        ("Top 10 NBA Bets", "What are the top 10 NBA bets today"),
        ("Best Player Props", "Show me the 5 best player props today"),
        ("Build Parlay", "Build a 3-leg parlay"),
        ("Research Matchup", "Research the Celtics vs Lakers matchup")
    ]
    
    for i, (label, query) in enumerate(quick_actions):
        col = [col1, col2, col3, col4][i]
        with col:
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                st.session_state.dice_gpt_query = query
    
    st.markdown("---")
    
    # Chat input
    st.markdown("### Ask DICEgpt")
    
    query = st.text_input(
        "",
        value=st.session_state.get("dice_gpt_query", ""),
        key="dice_gpt_input",
        placeholder="Ask me anything... Start Winning More! Use @ to focus on a select game, team or player.",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([10, 1])
    with col1:
        if st.button("Send", type="primary", use_container_width=True):
            if query:
                dice_gpt = DICEgpt()
                response = dice_gpt.process_query(query)
                
                st.session_state.dice_gpt_history.append({
                    "query": query,
                    "response": response,
                    "timestamp": datetime.now()
                })
                st.session_state.dice_gpt_query = ""
                st.rerun()
    
    with col2:
        if st.button("New Chat", use_container_width=True):
            st.session_state.dice_gpt_history = []
            st.session_state.dice_gpt_query = ""
            st.rerun()
    
    # Display results
    if st.session_state.dice_gpt_history:
        latest = st.session_state.dice_gpt_history[-1]
        response = latest["response"]
        
        st.markdown(f"### 💬 Query: {latest['query']}")
        
        if response["success"]:
            if response["intent"] == "get_picks" and response["results"]:
                st.markdown(f"#### Top {len(response['results'])} Betting Opportunities")
                st.markdown(f"*{response['message']}*")
                st.markdown("---")
                
                for i, pick in enumerate(response["results"], 1):
                    leg = pick["leg"]
                    game = pick["game"]
                    
                    analysis_text = _generate_detailed_analysis(pick, game, leg)
                    pick_text = _format_pick(leg)
                    
                    st.markdown(f"""
                        <div class="bet-card">
                            <h3 style="color: white; margin-top: 0;">{i}. {game.away_team or game.fighter2} @ {game.home_team or game.fighter1}</h3>
                            <div class="bet-analysis">
                                {analysis_text}
                            </div>
                            <div class="bet-details">
                                <div class="bet-detail-item">
                                    <span class="bet-detail-label">PICK</span>
                                    <span class="bet-detail-value">{pick_text}</span>
                                </div>
                                <div class="bet-detail-item">
                                    <span class="bet-detail-label">ODDS</span>
                                    <span class="bet-detail-value">{pick['odds']:.0f}</span>
                                </div>
                                <div class="bet-detail-item">
                                    <span class="bet-detail-label">BOOKMAKER</span>
                                    <span class="bet-detail-value">DRAFTKINGS</span>
                                </div>
                                <div class="bet-detail-item">
                                    <span class="bet-detail-label">CONFIDENCE</span>
                                    <span class="bet-detail-value">{pick['confidence']*100:.0f}%</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            
            elif response["intent"] == "build_parlay" and response["results"]:
                parlay = response["results"][0]
                st.markdown("#### Built Parlay")
                st.markdown(f"**{parlay.get('num_legs', 0)}-Leg Parlay** | Odds: {parlay.get('combined_odds', 0):.0f}")
                st.markdown("**Legs:**")
                for leg in parlay.get('legs', []):
                    st.write(f"- {leg.get('selection', 'N/A')} @ {leg.get('odds', 0):.0f}")
            
            else:
                st.info(response["message"])
        else:
            st.error(response["message"])
    
    st.markdown("---")
    st.caption("💎 Credits: Unlimited (Demo Mode)")


def _generate_detailed_analysis(pick: Dict, game: Game, leg: Dict) -> str:
    """Generate detailed analysis text for a pick (like DICEgpt style)."""
    analysis_parts = []
    
    # Start with team/player context
    if leg["bet_type"] == "prop" and leg.get("player_name"):
        player = leg["player_name"]
        analysis_parts.append(f"{player} presents a strong betting opportunity in this matchup.")
    elif game.sport != "UFC":
        home = game.home_team or game.fighter1
        away = game.away_team or game.fighter2
        analysis_parts.append(f"The {away} face the {home} in this {game.sport} matchup.")
    
    # Add statistical analysis
    if pick["confidence"] > 0.75:
        analysis_parts.append(f"This pick has a very high confidence score of {pick['confidence']*100:.1f}% based on comprehensive analysis of team and player advanced statistics, playtype efficiencies, and matchup advantages.")
    elif pick["confidence"] > 0.65:
        analysis_parts.append(f"This pick shows strong statistical support with a {pick['confidence']*100:.1f}% confidence score derived from multiple data points.")
    
    # Expected value analysis
    if pick["expected_value"] > 0.08:
        analysis_parts.append(f"The expected value of {pick['expected_value']*100:.1f}% indicates exceptional positive value, suggesting significant edge against the books.")
    elif pick["expected_value"] > 0.05:
        analysis_parts.append(f"With an expected value of {pick['expected_value']*100:.1f}%, this bet offers strong positive value.")
    
    # Historical performance
    if pick["historical_win_rate"] > 0.65:
        analysis_parts.append(f"Historical data shows a strong {pick['historical_win_rate']*100:.1f}% win rate for similar bets, indicating consistent profitability.")
    elif pick["historical_win_rate"] > 0.55:
        analysis_parts.append(f"Historical performance data shows a {pick['historical_win_rate']*100:.1f}% win rate for similar betting scenarios.")
    
    if pick["data_points"] > 50:
        analysis_parts.append(f"This analysis is backed by {pick['data_points']} historical data points, providing robust statistical foundation.")
    elif pick["data_points"] > 0:
        analysis_parts.append(f"Based on {pick['data_points']} historical data points, this pick shows promise.")
    
    # Recent trends
    if pick["recent_trend"] == "hot":
        analysis_parts.append("Recent trends show this type of bet has been performing significantly above average, indicating current market conditions favor this selection.")
    elif pick["recent_trend"] == "cold":
        analysis_parts.append("Note: Recent trends show below-average performance, though current analysis suggests value.")
    
    # Bet-specific reasoning
    if leg.get("reasoning"):
        analysis_parts.append(leg["reasoning"])
    
    # Key insights
    if pick["key_insights"]:
        for insight in pick["key_insights"][:3]:  # Include up to 3 insights
            analysis_parts.append(insight)
    
    # Add matchup-specific details for spreads/totals
    if leg["bet_type"] in ["spread", "total"] and game.sport != "UFC":
        analysis_parts.append(f"The matchup dynamics between {game.away_team or game.fighter2} and {game.home_team or game.fighter1} create favorable conditions for this bet.")
    
    return " ".join(analysis_parts)


def _format_pick(leg: Dict) -> str:
    """Format pick for display."""
    if leg["bet_type"] == "prop":
        player = leg.get("player_name", "Player")
        prop_type = leg.get("prop_type", "")
        selection = leg["selection"]
        prop_value = leg.get("prop_value")
        
        if prop_value:
            return f"{player} {prop_type} {selection} {prop_value}"
        else:
            return f"{player} {prop_type} - {selection}"
    elif leg["bet_type"] == "fighter_moneyline":
        return leg["selection"]
    else:
        return f"{leg['selection']} ({leg['bet_type']})"


def show_picks_dashboard():
    """Picks Dashboard with visual pick cards."""
    st.markdown("## 📋 Picks Dashboard")
    st.markdown("Your picks dashboard uses millions of data points to find significant edges")
    
    picks_dashboard = PicksDashboard()
    
    # Filters sidebar
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        
        # Get available filters
        available = picks_dashboard.get_available_filters()
        
        # Sport filter
        selected_sport = st.selectbox(
            "Sport",
            ["All"] + available["sports"],
            key="picks_sport"
        )
        
        # Bet type filter
        selected_bet_type = st.selectbox(
            "Bet Type",
            ["All"] + available["bet_types"],
            key="picks_bet_type"
        )
        
        # Prop type filter (if props selected)
        selected_prop_type = None
        if selected_bet_type == "prop" or selected_bet_type == "All":
            selected_prop_type = st.selectbox(
                "Prop Type",
                ["All"] + available["prop_types"],
                key="picks_prop_type"
            )
        
        # Player filter
        selected_player = st.selectbox(
            "Player",
            ["All"] + available["players"],
            key="picks_player"
        )
        
        # Game filter
        selected_game = st.selectbox(
            "Game",
            ["All"] + [g["display"] for g in available["games"]],
            key="picks_game"
        )
    
    # Build filters dict
    filters = {}
    if selected_sport != "All":
        filters["sport"] = selected_sport
    if selected_bet_type != "All":
        filters["bet_type"] = selected_bet_type
    if selected_prop_type and selected_prop_type != "All":
        filters["prop_type"] = selected_prop_type
    if selected_player and selected_player != "All":
        filters["player"] = selected_player
    if selected_game and selected_game != "All":
        game_id = next((g["id"] for g in available["games"] if g["display"] == selected_game), None)
        if game_id:
            filters["game_id"] = game_id
    
    # Get pick cards
    cards = picks_dashboard.get_pick_cards(filters)
    
    st.markdown(f"### Found {len(cards)} Picks")
    
    # Display pick cards
    for i, card in enumerate(cards):
        with st.expander(
            f"📊 {card['confidence_level']} | {card['bet_type'].upper()} | {card['selection']} @ {card['odds']:.0f}",
            expanded=(i < 3)
        ):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("### 📊 Confidence")
                st.metric("Score", f"{card['confidence']*100:.1f}%")
                st.caption(card['confidence_level'])
                st.metric("AI Score", f"{card['ai_score']:.3f}")
            
            with col2:
                st.markdown("### 📈 Historical")
                st.metric("Win Rate", f"{card['historical_performance']['win_rate']*100:.1f}%")
                st.metric("Data Points", card['historical_performance']['data_points'])
                trend_emoji = {"hot": "🔥", "cold": "❄️", "neutral": "➡️"}.get(
                    card['historical_performance']['trend'], "➡️"
                )
                st.caption(f"Trend: {trend_emoji} {card['historical_performance']['trend']}")
            
            with col3:
                st.markdown("### 🔁 Line Movement")
                movement = card['line_movement']
                st.metric("Current", f"{movement['current_odds']:.0f}")
                st.metric("Opening", f"{movement['opening_odds']:.0f}")
                movement_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(movement['movement'], "➡️")
                st.caption(f"{movement_emoji} {movement['movement']}")
                st.caption(f"Books: {', '.join(movement['sportsbooks'][:2])}")
            
            with col4:
                st.markdown("### 💰 Value")
                st.metric("Expected Value", f"{card['expected_value']*100:.1f}%")
                st.metric("Odds", f"{card['odds']:.0f}")
            
            # Game info
            game = card['game']
            st.markdown("---")
            st.markdown(f"**Game:** {game['away_team']} @ {game['home_team']} ({game['sport']})")
            if card.get('player_name'):
                st.markdown(f"**Player:** {card['player_name']}")
            
            # AI Analysis
            if card['ai_analysis']['key_insights']:
                st.markdown("#### 🤖 AI Analysis")
                for insight in card['ai_analysis']['key_insights']:
                    st.write(f"• {insight}")
                if card['ai_analysis']['reasoning']:
                    st.caption(f"Reasoning: {card['ai_analysis']['reasoning']}")


def show_settings():
    """Settings and configuration."""
    st.header("Settings")
    
    st.subheader("API Configuration")
    st.info("Configure API keys in the .env file")
    
    st.subheader("Model Weights")
    st.write("Adjust research engine weights:")
    
    weights = st.session_state.research_engine.weights
    
    new_weights = {}
    new_weights["value"] = st.slider("Value Weight", 0.0, 1.0, weights["value"], 0.1)
    new_weights["confidence"] = st.slider("Confidence Weight", 0.0, 1.0, weights["confidence"], 0.1)
    new_weights["correlation"] = st.slider("Correlation Weight", 0.0, 1.0, weights["correlation"], 0.1)
    new_weights["diversification"] = st.slider("Diversification Weight", 0.0, 1.0, weights["diversification"], 0.1)
    
    total = sum(new_weights.values())
    if abs(total - 1.0) > 0.01:
        st.warning(f"Weights sum to {total:.2f}. They should sum to 1.0")
    else:
        if st.button("Update Weights"):
            st.session_state.research_engine.weights = new_weights
            st.success("Weights updated!")
    
    st.subheader("Risk Management")
    bankroll = st.number_input("Bankroll ($)", 100, 100000, 1000, 100)
    max_daily_risk = st.slider("Max Daily Risk (%)", 1, 20, 5, 1) / 100
    
    if st.button("Update Risk Settings"):
        st.session_state.risk_manager = RiskManager(bankroll, max_daily_risk)
        st.success("Risk settings updated!")
    
    st.markdown("---")
    st.subheader("🤖 ML Model Training")
    st.write("Train machine learning models on historical data to improve predictions.")
    
    # Check model status
    ml_predictor = MLPredictor()
    model_status = []
    
    if ml_predictor.moneyline_model is not None:
        model_status.append("✅ Moneyline Model: Trained")
    else:
        model_status.append("❌ Moneyline Model: Not Trained")
    
    if ml_predictor.spread_model is not None:
        model_status.append("✅ Spread Model: Trained")
    else:
        model_status.append("❌ Spread Model: Not Trained")
    
    if ml_predictor.total_model is not None:
        model_status.append("✅ Total Model: Trained")
    else:
        model_status.append("❌ Total Model: Not Trained")
    
    for status in model_status:
        st.write(status)
    
    # Training options
    st.write("**Training Options:**")
    sport_filter = st.selectbox(
        "Filter by Sport (optional)",
        ["All Sports"] + list(DEFAULT_SPORTS),
        key="ml_training_sport"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Train All Models", use_container_width=True):
            with st.spinner("Training ML models... This may take a few minutes."):
                try:
                    sport = None if sport_filter == "All Sports" else sport_filter
                    ml_predictor.train_all_models(sport=sport)
                    st.success("✅ Models trained successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error training models: {str(e)}")
                    logger.error(f"ML training error: {e}", exc_info=True)
    
    with col2:
        if st.button("📊 Check Training Data", use_container_width=True):
            with st.spinner("Checking available training data..."):
                try:
                    sport = None if sport_filter == "All Sports" else sport_filter
                    ml_data, spread_data, total_data = ml_predictor.prepare_training_data(
                        sport=sport, min_games=1
                    )
                    
                    st.write("**Available Training Data:**")
                    if ml_data is not None:
                        st.write(f"✅ Moneyline: {len(ml_data)} samples")
                    else:
                        st.write("❌ Moneyline: No data available")
                    
                    if spread_data is not None:
                        st.write(f"✅ Spread: {len(spread_data)} samples")
                    else:
                        st.write("❌ Spread: No data available")
                    
                    if total_data is not None:
                        st.write(f"✅ Total: {len(total_data)} samples")
                    else:
                        st.write("❌ Total: No data available")
                    
                    if ml_data is None and spread_data is None and total_data is None:
                        st.warning("⚠️ No training data found. You need finished games with results in the database.")
                        st.info("💡 Tip: Update game results first, then train models.")
                except Exception as e:
                    st.error(f"Error checking data: {str(e)}")
    
    st.info("💡 **Note:** Models are automatically loaded when available. Train models after you have at least 30 finished games with results in the database.")


def show_bankroll():
    """Bankroll management page."""
    st.header("💰 Bankroll Management")
    
    if 'bankroll_manager' not in st.session_state:
        st.session_state.bankroll_manager = BankrollManager()
    
    bm = st.session_state.bankroll_manager
    bankroll = bm.get_bankroll()
    status = bm.get_budget_status()
    
    # Current balance
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Balance", f"${status['current_balance']:.2f}")
    with col2:
        st.metric("Total Profit", f"${status['total_profit']:.2f}", f"{status['roi']:.1f}%")
    with col3:
        if status['daily_remaining'] is not None:
            st.metric("Daily Remaining", f"${status['daily_remaining']:.2f}")
    with col4:
        if status['weekly_remaining'] is not None:
            st.metric("Weekly Remaining", f"${status['weekly_remaining']:.2f}")
    
    st.markdown("---")
    
    # Settings
    st.subheader("Bankroll Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        new_balance = st.number_input("Current Balance", value=bankroll.current_balance, min_value=0.0, step=100.0)
        daily_budget = st.number_input("Daily Budget", value=bankroll.daily_budget or 0.0, min_value=0.0, step=50.0)
        weekly_budget = st.number_input("Weekly Budget", value=bankroll.weekly_budget or 0.0, min_value=0.0, step=100.0)
        monthly_budget = st.number_input("Monthly Budget", value=bankroll.monthly_budget or 0.0, min_value=0.0, step=500.0)
    
    with col2:
        base_unit = st.slider("Base Unit Size (%)", 0.5, 5.0, bankroll.base_unit_size or 1.0, 0.1)
        kelly_fraction = st.slider("Kelly Fraction", 0.1, 1.0, bankroll.kelly_fraction or 0.25, 0.05)
        max_bet = st.number_input("Max Bet Size", value=bankroll.max_bet_size or 0.0, min_value=0.0, step=50.0)
        max_parlay = st.number_input("Max Parlay Stake", value=bankroll.max_parlay_stake or 0.0, min_value=0.0, step=50.0)
    
    if st.button("💾 Update Settings"):
        bm.update_settings(
            current_balance=new_balance,
            daily_budget=daily_budget if daily_budget > 0 else None,
            weekly_budget=weekly_budget if weekly_budget > 0 else None,
            monthly_budget=monthly_budget if monthly_budget > 0 else None,
            base_unit_size=base_unit,
            kelly_fraction=kelly_fraction,
            max_bet_size=max_bet if max_bet > 0 else None,
            max_parlay_stake=max_parlay if max_parlay > 0 else None
        )
        st.success("Settings updated!")
        st.rerun()
    
    # Transactions
    st.markdown("---")
    st.subheader("Transactions")
    col1, col2 = st.columns(2)
    
    with col1:
        deposit_amount = st.number_input("Deposit Amount", min_value=0.0, step=50.0)
        if st.button("➕ Deposit"):
            bm.update_balance(deposit_amount, "deposit")
            st.success(f"Deposited ${deposit_amount:.2f}")
            st.rerun()
    
    with col2:
        withdrawal_amount = st.number_input("Withdrawal Amount", min_value=0.0, step=50.0)
        if st.button("➖ Withdraw"):
            if withdrawal_amount <= bankroll.current_balance:
                bm.update_balance(withdrawal_amount, "withdrawal")
                st.success(f"Withdrew ${withdrawal_amount:.2f}")
                st.rerun()
            else:
                st.error("Insufficient balance")


def show_value_bets():
    """Value bet finder page."""
    st.header("💎 Value Bet Finder")
    
    if 'value_finder' not in st.session_state:
        st.session_state.value_finder = ValueBetFinder()
    
    vf = st.session_state.value_finder
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        min_ev = st.slider("Minimum EV (%)", 0.0, 20.0, 5.0, 0.5) / 100
    with col2:
        min_confidence = st.slider("Minimum Confidence", 0.5, 1.0, 0.6, 0.05)
    with col3:
        selected_sports = st.multiselect("Sports", DEFAULT_SPORTS, default=DEFAULT_SPORTS)
    
    if st.button("🔍 Find Value Bets"):
        with st.spinner("Scanning all games for value bets..."):
            value_bets = vf.find_value_bets(
                min_ev=min_ev,
                min_confidence=min_confidence,
                sports=selected_sports if selected_sports else None,
                max_results=50
            )
            
            if value_bets:
                vf.save_value_bets(value_bets)
                st.session_state.value_bets = value_bets
                st.success(f"Found {len(value_bets)} value bets!")
            else:
                st.warning("No value bets found matching criteria.")
    
    # Display value bets
    if 'value_bets' in st.session_state:
        value_bets = st.session_state.value_bets
        
        st.markdown("---")
        st.subheader(f"💰 Top {len(value_bets)} Value Bets")
        
        for i, vb in enumerate(value_bets[:20], 1):
            game = vb["game"]
            with st.expander(f"#{i} {vb['bet_type'].title()}: {vb['selection']} @ {vb['odds']:.0f} | {vb['edge_percentage']:.1f}% Edge"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Game:** {game.sport}")
                    if game.sport == "UFC":
                        st.write(f"{game.fighter1} vs {game.fighter2}")
                    else:
                        st.write(f"{game.away_team} @ {game.home_team}")
                    st.write(f"**Bet Type:** {vb['bet_type']}")
                    st.write(f"**Selection:** {vb['selection']}")
                    st.write(f"**Odds:** {vb['odds']:.0f}")
                
                with col2:
                    st.metric("Expected Value", f"{vb['edge_percentage']:.2f}%")
                    st.metric("Confidence", f"{vb['confidence_score']*100:.0f}%", vb['confidence_level'])
                    st.metric("Value Score", f"{vb['value_score']:.3f}")
                    st.write(f"**True Prob:** {vb['true_probability']*100:.1f}%")
                    st.write(f"**Implied Prob:** {vb['implied_probability']*100:.1f}%")
                
                st.write(f"**Reasoning:** {vb['reasoning']}")
                
                if st.button(f"Add to Bet Slip", key=f"add_vb_{i}"):
                    st.info("Feature: Add to bet slip (coming soon)")


def show_line_shopping():
    """Line shopping page."""
    st.header("🛒 Line Shopping")
    
    if 'line_shopper' not in st.session_state:
        st.session_state.line_shopper = LineShopper()
    
    ls = st.session_state.line_shopper
    
    # Select game
    games = st.session_state.db_session.query(Game).filter(
        Game.status == "scheduled"
    ).order_by(Game.game_date).all()
    
    if not games:
        st.warning("No scheduled games found.")
        return
    
    game_options = {}
    for game in games:
        if game.sport == "UFC":
            label = f"{game.sport}: {game.fighter1} vs {game.fighter2} - {game.game_date.strftime('%m/%d')}"
        else:
            label = f"{game.sport}: {game.away_team} @ {game.home_team} - {game.game_date.strftime('%m/%d')}"
        game_options[label] = game
    
    selected_label = st.selectbox("Select Game", list(game_options.keys()))
    selected_game = game_options[selected_label]
    
    # Select bet type
    bet_type = st.selectbox("Bet Type", ["moneyline", "spread", "total"])
    
    # Get selection based on bet type
    selection = None
    if bet_type == "moneyline":
        if selected_game.sport == "UFC":
            selection = st.selectbox("Selection", [selected_game.fighter1, selected_game.fighter2])
        else:
            selection = st.selectbox("Selection", [selected_game.home_team, selected_game.away_team])
    elif bet_type == "spread":
        selection = st.selectbox("Selection", [
            f"{selected_game.home_team} {selected_game.spread}",
            f"{selected_game.away_team} {-selected_game.spread if selected_game.spread else 0}"
        ])
    elif bet_type == "total":
        selection = st.selectbox("Selection", ["Over", "Under"])
        if selected_game.total:
            selection = f"{selection} {selected_game.total}"
    
    if st.button("🔍 Compare Odds"):
        with st.spinner("Comparing odds across sportsbooks..."):
            comparisons = ls.compare_odds(selected_game, bet_type, selection)
            
            if comparisons:
                st.markdown("---")
                st.subheader("📊 Odds Comparison")
                
                # Find best
                best = max(comparisons, key=lambda x: x["odds"])
                
                # Display comparison table
                df = pd.DataFrame(comparisons)
                df["Bookmaker"] = df["bookmaker"]
                df["Odds"] = df["odds"].apply(lambda x: f"{x:.0f}")
                df["Implied Prob"] = df["implied_probability"].apply(lambda x: f"{x*100:.1f}%")
                df["Edge vs Avg"] = df["edge_vs_average"].apply(lambda x: f"{x:+.1f}")
                df["Best"] = df.apply(lambda row: "⭐" if row == best else "", axis=1)
                
                st.dataframe(df[["Bookmaker", "Odds", "Implied Prob", "Edge vs Avg", "Best"]], use_container_width=True)
                
                st.success(f"🏆 Best Odds: {best['bookmaker']} @ {best['odds']:.0f} (+{best['edge_vs_average']:.1f} vs average)")


def show_parlay_optimizer():
    """Parlay optimizer page."""
    st.header("🎯 Parlay Optimizer")
    
    if 'parlay_optimizer' not in st.session_state:
        st.session_state.parlay_optimizer = ParlayOptimizer()
    
    po = st.session_state.parlay_optimizer
    
    # Mode selection
    mode = st.radio("Optimization Mode", ["Target Odds", "Maximize EV"], horizontal=True)
    
    # Get games
    selected_sports = st.multiselect("Select Sports", DEFAULT_SPORTS, default=DEFAULT_SPORTS)
    games = st.session_state.db_session.query(Game).filter(
        Game.status == "scheduled",
        Game.sport.in_(selected_sports) if selected_sports else True
    ).all()
    
    if not games:
        st.warning("No games found.")
        return
    
    if mode == "Target Odds":
        target_odds = st.number_input("Target Odds", min_value=-500, max_value=500, value=200, step=10)
        tolerance = st.slider("Tolerance (%)", 1, 20, 10) / 100
        min_legs = st.slider("Min Legs", 2, 5, 2)
        max_legs = st.slider("Max Legs", 3, 8, 5)
        
        if st.button("🎯 Optimize for Target Odds"):
            with st.spinner("Finding optimal parlay combinations..."):
                optimized = po.optimize_for_target_odds(
                    games, target_odds, tolerance, min_legs, max_legs
                )
                
                if optimized:
                    st.success(f"Found {len(optimized)} parlay combinations!")
                    st.session_state.optimized_parlays = optimized
                else:
                    st.warning("No combinations found matching criteria.")
    
    else:  # Maximize EV
        min_confidence = st.slider("Minimum Confidence", 0.5, 1.0, 0.6, 0.05)
        max_legs = st.slider("Max Legs", 2, 6, 5)
        
        if st.button("💰 Maximize Expected Value"):
            with st.spinner("Finding highest EV parlays..."):
                optimized = po.maximize_ev(games, max_legs, min_confidence)
                
                if optimized:
                    st.success(f"Found {len(optimized)} high-EV parlays!")
                    st.session_state.optimized_parlays = optimized
                else:
                    st.warning("No high-EV parlays found.")
    
    # Display results
    if 'optimized_parlays' in st.session_state:
        optimized = st.session_state.optimized_parlays
        
        st.markdown("---")
        st.subheader("🎯 Optimized Parlays")
        
        for i, parlay in enumerate(optimized[:10], 1):
            with st.expander(f"Parlay #{i}: {parlay['num_legs']} legs | Odds: {parlay['combined_odds']:.0f} | EV: {parlay['expected_value']*100:.1f}%"):
                st.write(f"**Combined Odds:** {parlay['combined_odds']:.0f}")
                st.write(f"**Expected Value:** {parlay['expected_value']*100:.2f}%")
                st.write(f"**Confidence:** {parlay['confidence_score']*100:.0f}%")
                st.write(f"**Implied Probability:** {parlay['implied_probability']*100:.2f}%")
                
                st.write("**Legs:**")
                for j, leg in enumerate(parlay['legs'], 1):
                    game = leg['game']
                    game_display = f"{game.away_team or game.fighter2} @ {game.home_team or game.fighter1}" if game.sport != "UFC" else f"{game.fighter1} vs {game.fighter2}"
                    st.write(f"{j}. {game.sport}: {game_display}")
                    st.write(f"   {leg['bet_type']}: {leg['selection']} @ {leg['odds']:.0f}")


def show_performance_breakdown():
    """Performance breakdown page."""
    st.header("📊 Performance Breakdown")
    
    if 'performance_analyzer' not in st.session_state:
        st.session_state.performance_analyzer = PerformanceAnalyzer()
    
    pa = st.session_state.performance_analyzer
    
    days = st.slider("Time Period (days)", 7, 365, 30)
    
    # By Sport
    st.subheader("📈 Performance by Sport")
    sport_stats = pa.get_performance_by_sport(days)
    
    if sport_stats:
        sport_df = pd.DataFrame(sport_stats).T
        sport_df = sport_df.reset_index()
        sport_df.columns = ["Sport", "Total", "Wins", "Losses", "Stake", "Payout", "Hit Rate", "Profit", "ROI"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(sport_df[["Sport", "Total", "Wins", "Losses", "Hit Rate", "ROI"]], use_container_width=True)
        with col2:
            fig = px.bar(sport_df, x="Sport", y="ROI", title="ROI by Sport", color="ROI", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig, use_container_width=True)
    
    # By Bet Type
    st.subheader("🎲 Performance by Bet Type")
    type_stats = pa.get_performance_by_bet_type(days)
    
    if type_stats:
        type_df = pd.DataFrame(type_stats).T
        type_df = type_df.reset_index()
        type_df.columns = ["Bet Type", "Total", "Wins", "Losses", "Hit Rate"]
        st.dataframe(type_df, use_container_width=True)
    
    # By Confidence
    st.subheader("🎯 Performance by Confidence Level")
    conf_stats = pa.get_performance_by_confidence(days)
    
    if conf_stats:
        conf_df = pd.DataFrame(conf_stats).T
        conf_df = conf_df.reset_index()
        conf_df.columns = ["Confidence", "Total", "Wins", "Losses", "Stake", "Payout", "Hit Rate", "Profit", "ROI"]
        st.dataframe(conf_df[["Confidence", "Total", "Wins", "Losses", "Hit Rate", "ROI"]], use_container_width=True)
    
    # By Day of Week
    st.subheader("📅 Performance by Day of Week")
    day_stats = pa.get_performance_by_day_of_week(days)
    
    if day_stats:
        day_df = pd.DataFrame(day_stats).T
        day_df = day_df.reset_index()
        day_df.columns = ["Day", "Total", "Wins", "Losses", "Stake", "Payout", "Hit Rate", "Profit", "ROI"]
        st.dataframe(day_df[["Day", "Total", "Wins", "Losses", "Hit Rate", "ROI"]], use_container_width=True)


def show_clv_tracker():
    """CLV tracker page."""
    st.header("📉 Closing Line Value Tracker")
    
    if 'clv_tracker' not in st.session_state:
        st.session_state.clv_tracker = CLVTracker()
    
    clv = st.session_state.clv_tracker
    
    # Overall stats
    avg_clv = clv.get_average_clv(30)
    sharp_score = clv.get_sharp_score()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average CLV (30 days)", f"{avg_clv:.2f}%")
    with col2:
        st.metric("Sharp Score", f"{sharp_score:.2f}", "0-1 scale")
    with col3:
        if 'performance_analyzer' in st.session_state:
            pa = st.session_state.performance_analyzer
            clv_stats = pa.get_closing_line_value_stats()
            beat_rate = clv_stats.get("beat_closing_rate", 0) * 100
            st.metric("Beat Closing Line Rate", f"{beat_rate:.1f}%")
        else:
            st.metric("Beat Closing Line Rate", "N/A")
    
    st.markdown("---")
    
    # CLV records
    from models import ClosingLineValue
    clv_records = st.session_state.db_session.query(ClosingLineValue).join(Leg).join(Parlay).filter(
        Parlay.result.in_(["win", "loss"])
    ).order_by(ClosingLineValue.created_at.desc()).limit(50).all()
    
    if clv_records:
        st.subheader("Recent CLV Records")
        
        clv_data = []
        for record in clv_records:
            leg = record.leg
            clv_data.append({
                "Date": record.created_at.strftime("%Y-%m-%d"),
                "Bet": f"{leg.bet_type}: {leg.selection}",
                "Your Odds": f"{record.your_odds:.0f}",
                "Closing Odds": f"{record.closing_odds:.0f}" if record.closing_odds else "N/A",
                "CLV": f"{record.clv_percentage:.2f}%" if record.clv_percentage else "N/A",
                "Beat Closing": "✅" if record.beat_closing_line else "❌",
                "Sharp Score": f"{record.sharp_indicator:.2f}" if record.sharp_indicator else "N/A"
            })
        
        df = pd.DataFrame(clv_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No CLV records yet. CLV is tracked when you place bets and games finish.")


def show_streaks():
    """Streak tracker page."""
    st.header("🔥 Streak Tracker")
    
    if 'streak_tracker' not in st.session_state:
        st.session_state.streak_tracker = StreakTracker()
    
    st_tracker = st.session_state.streak_tracker
    
    # Current streaks
    overall_streak = st_tracker.get_current_streak()
    all_streaks = st_tracker.get_all_streaks()
    
    st.subheader("Current Streaks")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        streak_emoji = "🔥" if overall_streak["type"] == "win" else "❄️"
        st.metric("Overall Streak", f"{streak_emoji} {overall_streak['current']}", f"Longest: {overall_streak['longest']}")
    
    # Sport-specific streaks
    if all_streaks:
        st.markdown("---")
        st.subheader("Streaks by Sport")
        
        for sport, streak_info in all_streaks.items():
            if sport != "Overall":
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**{sport}**")
                with col2:
                    streak_type_emoji = "🔥" if streak_info["type"] == "win" else "❄️"
                    st.write(f"{streak_type_emoji} Current: {streak_info['current']}")
                with col3:
                    st.write(f"Longest: {streak_info['longest']}")


def show_bet_slip():
    """Bet slip builder page."""
    st.header("📝 Bet Slip Builder")
    
    if 'bet_slip_builder' not in st.session_state:
        st.session_state.bet_slip_builder = BetSlipBuilder()
    
    bsb = st.session_state.bet_slip_builder
    
    # Create new or load existing
    tab1, tab2 = st.tabs(["New Bet Slip", "Saved Slips"])
    
    with tab1:
        slip_name = st.text_input("Bet Slip Name", value=f"Slip {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if st.button("➕ Create New Slip"):
            new_slip = bsb.create_bet_slip(slip_name)
            st.session_state.current_slip = new_slip
            st.success("New bet slip created!")
        
        # Current slip
        if 'current_slip' in st.session_state:
            slip = st.session_state.current_slip
            st.subheader(f"Current Slip: {slip.name}")
            
            legs = slip.legs or []
            
            if legs:
                st.write(f"**{len(legs)} legs** | **Odds:** {slip.total_odds:.0f}")
                
                for i, leg in enumerate(legs):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"{i+1}. {leg.get('bet_type')}: {leg.get('selection')} @ {leg.get('odds'):.0f}")
                    with col2:
                        if st.button("❌", key=f"remove_{i}"):
                            bsb.remove_leg(slip, i)
                            st.rerun()
                
                st.markdown("---")
                stake = st.number_input("Stake ($)", min_value=0.0, value=slip.stake or 0.0, step=10.0)
                bsb.update_stake(slip, stake)
                
                st.metric("Potential Payout", f"${slip.potential_payout:.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save Slip"):
                        bsb.save_slip(slip)
                        st.success("Slip saved!")
                with col2:
                    if st.button("🎲 Convert to Parlay"):
                        parlay_data = bsb.convert_to_parlay(slip)
                        st.session_state.parlay_to_save = parlay_data
                        st.info("Ready to save as parlay!")
            else:
                st.info("Add legs to your bet slip from Value Bets or Generate Parlays pages.")
    
    with tab2:
        saved_slips = bsb.get_user_slips(include_drafts=False)
        
        if saved_slips:
            for slip in saved_slips:
                with st.expander(f"{slip.name} - {len(slip.legs or [])} legs | {slip.total_odds:.0f} odds"):
                    st.write(f"**Stake:** ${slip.stake:.2f}")
                    st.write(f"**Potential Payout:** ${slip.potential_payout:.2f}")
                    if st.button("Load", key=f"load_{slip.id}"):
                        st.session_state.current_slip = slip
                        st.rerun()
        else:
            st.info("No saved bet slips.")


def show_live_betting():
    """Live betting tracker page."""
    st.header("📱 Live Betting Tracker")
    
    if 'live_tracker' not in st.session_state:
        st.session_state.live_tracker = LiveBettingTracker()
    
    lt = st.session_state.live_tracker
    
    if st.button("🔄 Refresh Live Games"):
        live_games = lt.get_live_games()
        st.session_state.live_games = live_games
    
    if 'live_games' in st.session_state:
        live_games = st.session_state.live_games
        
        if live_games:
            st.subheader(f"🔴 {len(live_games)} Live Games")
            
            for game in live_games:
                with st.expander(f"{game.sport}: {game.away_team or game.fighter2} @ {game.home_team or game.fighter1}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if game.home_moneyline:
                            st.write(f"**Home:** {game.home_moneyline:.0f}")
                        if game.away_moneyline:
                            st.write(f"**Away:** {game.away_moneyline:.0f}")
                    
                    with col2:
                        if st.button("Update Odds", key=f"update_{game.id}"):
                            lt.update_live_odds(game)
                            st.rerun()
        else:
            st.info("No live games currently.")
    else:
        st.info("Click 'Refresh Live Games' to check for live games.")


def show_notifications():
    """Notifications page."""
    st.header("📬 Notifications")
    
    if 'notification_system' not in st.session_state:
        st.session_state.notification_system = NotificationSystem()
    
    ns = st.session_state.notification_system
    
    # Unread count
    unread_count = ns.get_notification_count()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Notifications ({unread_count} unread)")
    with col2:
        if st.button("Mark All Read"):
            ns.mark_all_as_read()
            st.rerun()
    
    # Get notifications
    notifications = ns.get_unread_notifications(50)
    
    if notifications:
        for notif in notifications:
            priority_color = {
                "urgent": "🔴",
                "high": "🟠",
                "normal": "🔵",
                "low": "⚪"
            }
            
            with st.expander(f"{priority_color.get(notif.priority, '⚪')} {notif.title} - {notif.created_at.strftime('%m/%d %H:%M')}"):
                st.write(notif.message)
                st.write(f"**Type:** {notif.notification_type}")
                
                if st.button("Mark as Read", key=f"read_{notif.id}"):
                    ns.mark_as_read(notif.id)
                    st.rerun()
    else:
        st.info("No unread notifications.")


def show_export():
    """Export and reporting page."""
    st.header("📤 Export & Reports")
    
    if 'export_reporter' not in st.session_state:
        st.session_state.export_reporter = ExportReporter()
    
    er = st.session_state.export_reporter
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now().date())
    
    st.markdown("---")
    
    # Export options
    st.subheader("Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export to CSV"):
            filepath = f"export_{start_date}_{end_date}.csv"
            er.export_to_csv(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                filepath
            )
            st.success(f"Exported to {filepath}")
            with open(filepath, 'rb') as f:
                st.download_button("Download CSV", f.read(), filepath, "text/csv")
    
    with col2:
        if st.button("📈 Export to Excel"):
            filepath = f"export_{start_date}_{end_date}.xlsx"
            er.export_to_excel(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                filepath
            )
            st.success(f"Exported to {filepath}")
            with open(filepath, 'rb') as f:
                st.download_button("Download Excel", f.read(), filepath, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    with col3:
        if st.button("📄 Export to JSON"):
            filepath = f"export_{start_date}_{end_date}.json"
            er.export_to_json(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                filepath
            )
            st.success(f"Exported to {filepath}")
            with open(filepath, 'rb') as f:
                st.download_button("Download JSON", f.read(), filepath, "application/json")
    
    st.markdown("---")
    
    # Tax report
    st.subheader("Tax Report")
    year = st.number_input("Year", min_value=2020, max_value=datetime.now().year, value=datetime.now().year)
    
    if st.button("📋 Generate Tax Report"):
        filepath = f"tax_report_{year}.csv"
        report = er.generate_tax_report(year, filepath)
        
        st.success("Tax report generated!")
        st.json(report)
        
        with open(filepath, 'rb') as f:
            st.download_button("Download Tax Report", f.read(), filepath, "text/csv")


def show_advanced_filters():
    """Advanced filtering page."""
    st.header("🔍 Advanced Filters")
    
    if 'advanced_filters' not in st.session_state:
        st.session_state.advanced_filters = AdvancedFilters()
    
    af = st.session_state.advanced_filters
    
    # Filter type
    filter_type = st.radio("Filter Type", ["Games", "Parlays", "Value Bets"], horizontal=True)
    
    if filter_type == "Games":
        st.subheader("Filter Games")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_sports = st.multiselect("Sports", DEFAULT_SPORTS, default=DEFAULT_SPORTS)
            date_range = st.date_input("Date Range", value=[datetime.now().date(), datetime.now().date() + timedelta(days=7)])
        with col2:
            min_odds = st.number_input("Min Odds", value=None, placeholder="Any")
            max_odds = st.number_input("Max Odds", value=None, placeholder="Any")
        
        if st.button("🔍 Filter Games"):
            start_date = datetime.combine(date_range[0], datetime.min.time())
            end_date = datetime.combine(date_range[1] if len(date_range) > 1 else date_range[0], datetime.max.time())
            
            games = af.filter_games(
                sports=selected_sports if selected_sports else None,
                date_range=(start_date, end_date),
                min_odds=min_odds,
                max_odds=max_odds
            )
            
            st.success(f"Found {len(games)} games")
            st.session_state.filtered_games = games
    
    elif filter_type == "Parlays":
        st.subheader("Filter Parlays")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_sports = st.multiselect("Sports", DEFAULT_SPORTS, default=DEFAULT_SPORTS)
            min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.6, 0.05)
            min_ev = st.slider("Min EV (%)", 0.0, 20.0, 0.0, 0.5) / 100
        with col2:
            status = st.selectbox("Status", ["All", "pending", "locked", "won", "lost"])
            has_props = st.selectbox("Has Props", ["All", "Yes", "No"])
        
        if st.button("🔍 Filter Parlays"):
            date_range = (datetime.now() - timedelta(days=30), datetime.now())
            parlays = af.filter_parlays(
                sports=selected_sports if selected_sports else None,
                date_range=date_range,
                min_confidence=min_confidence,
                min_ev=min_ev,
                status=status if status != "All" else None,
                has_props=True if has_props == "Yes" else False if has_props == "No" else None
            )
            
            st.success(f"Found {len(parlays)} parlays")
            st.session_state.filtered_parlays = parlays
    
    # Display results
    if 'filtered_games' in st.session_state:
        games = st.session_state.filtered_games
        for game in games[:20]:
            st.write(f"{game.sport}: {game.away_team or game.fighter2} @ {game.home_team or game.fighter1}")
    
    if 'filtered_parlays' in st.session_state:
        parlays = st.session_state.filtered_parlays
        for parlay in parlays[:20]:
            st.write(f"{parlay.name}: {parlay.combined_odds:.0f} odds | {parlay.confidence_rating}")


def show_weather_injuries():
    """Weather and injury impact page."""
    st.header("🌤️ Weather & Injury Impact")
    
    if 'weather_injury' not in st.session_state:
        st.session_state.weather_injury = WeatherInjuryImpact()
    
    wi = st.session_state.weather_injury
    
    # Select game
    games = st.session_state.db_session.query(Game).filter(
        Game.status == "scheduled"
    ).order_by(Game.game_date).all()
    
    if not games:
        st.warning("No scheduled games found.")
        return
    
    game_options = {}
    for game in games:
        if game.sport == "UFC":
            label = f"{game.sport}: {game.fighter1} vs {game.fighter2}"
        else:
            label = f"{game.sport}: {game.away_team} @ {game.home_team}"
        game_options[label] = game
    
    selected_label = st.selectbox("Select Game", list(game_options.keys()))
    selected_game = game_options[selected_label]
    
    # Injury impact
    st.subheader("🏥 Injury Impact")
    injury_data = wi.get_injury_impact(selected_game)
    
    if injury_data["impact"] != "none":
        st.write(f"**Impact:** {injury_data['impact']}")
        st.write(f"**Impact Score:** {injury_data['impact_score']*100:.1f}%")
        st.write(f"**Message:** {injury_data['message']}")
        
        if injury_data.get("home_injuries"):
            st.write("**Home Team Injuries:**")
            for injury in injury_data["home_injuries"]:
                st.write(f"- {injury['player']} ({injury['position']}): {injury['status']}")
        
        if injury_data.get("away_injuries"):
            st.write("**Away Team Injuries:**")
            for injury in injury_data["away_injuries"]:
                st.write(f"- {injury['player']} ({injury['position']}): {injury['status']}")
    else:
        st.info(injury_data["message"])
    
    # Weather impact
    if selected_game.sport in ["NFL", "MLB"]:
        st.subheader("🌦️ Weather Impact")
        weather_data = wi.get_weather_impact(selected_game)
        st.info(weather_data["message"])


def show_auto_betting():
    """Auto-betting page."""
    st.header("🤖 Auto-Betting")
    
    if 'auto_betting' not in st.session_state:
        st.session_state.auto_betting = AutoBetting()
    
    ab = st.session_state.auto_betting
    
    st.warning("⚠️ Auto-betting requires sportsbook API integration. This is a placeholder for future implementation.")
    
    # Sportsbook connections
    st.subheader("Sportsbook Connections")
    
    for sportsbook in ["draftkings", "fanduel", "betmgm"]:
        with st.expander(f"{sportsbook.title()}"):
            connected = ab.sportsbooks[sportsbook]["connected"]
            st.write(f"**Status:** {'✅ Connected' if connected else '❌ Not Connected'}")
            
            if not connected:
                api_key = st.text_input(f"{sportsbook.title()} API Key", type="password", key=f"key_{sportsbook}")
                if st.button(f"Connect to {sportsbook.title()}", key=f"connect_{sportsbook}"):
                    if api_key:
                        if ab.connect_sportsbook(sportsbook, api_key):
                            st.success(f"Connected to {sportsbook.title()}!")
                            st.rerun()
                    else:
                        st.error("Please enter API key")
    
    # Enable/disable
    st.markdown("---")
    st.subheader("Auto-Betting Settings")
    
    enabled = st.checkbox("Enable Auto-Betting", value=ab.enabled)
    if enabled != ab.enabled:
        if enabled:
            ab.enable()
        else:
            ab.disable()
        st.rerun()
    
    if ab.enabled:
        st.info("✅ Auto-betting is enabled. Parlays will be automatically placed when criteria are met.")
    else:
        st.info("❌ Auto-betting is disabled.")


if __name__ == "__main__":
    main()

