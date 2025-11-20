"""Machine Learning and simulation models for predictions."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_absolute_error, log_loss
from typing import Dict, List, Tuple, Optional
from models import Game, TeamStat, Leg, PlayerProp, SessionLocal
import logging
import pickle
import os
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLPredictor:
    """Machine learning models for game predictions."""
    
    def __init__(self, model_dir: str = "./ml_models_cache"):
        self.session = SessionLocal()
        self.moneyline_model = None
        self.spread_model = None
        self.total_model = None
        self.prop_model = None  # For player props
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Try to load existing models
        self.load_models()
    
    def extract_features(self, game: Game, for_team: str = "home") -> np.ndarray:
        """Extract features from game data for ML model."""
        features = []
        
        # Basic odds features
        home_ml = game.home_moneyline or 0
        away_ml = game.away_moneyline or 0
        spread = game.spread or 0
        total = game.total or 0
        
        # Convert odds to implied probabilities
        home_implied = self._american_to_implied_prob(home_ml) if home_ml else 0.5
        away_implied = self._american_to_implied_prob(away_ml) if away_ml else 0.5
        
        features.extend([home_ml, away_ml, spread, total, home_implied, away_implied])
        
        # Team stats (if available)
        home_stats = None
        away_stats = None
        
        if game.home_team:
            home_stats = self.session.query(TeamStat).filter_by(
                team=game.home_team, sport=game.sport
            ).first()
        
        if game.away_team:
            away_stats = self.session.query(TeamStat).filter_by(
                team=game.away_team, sport=game.sport
            ).first()
        
        # Add team stat features (home, then away)
        for stats in [home_stats, away_stats]:
            if stats:
                features.extend([
                    stats.win_streak or 0,
                    stats.loss_streak or 0,
                    stats.offensive_rating or 100.0,
                    stats.defensive_rating or 100.0,
                    stats.pace or 100.0
                ])
            else:
                features.extend([0, 0, 100.0, 100.0, 100.0])
        
        # Add relative features
        if home_stats and away_stats:
            features.extend([
                (home_stats.offensive_rating or 100) - (away_stats.defensive_rating or 100),
                (away_stats.offensive_rating or 100) - (home_stats.defensive_rating or 100),
                (home_stats.offensive_rating or 100) / max(away_stats.defensive_rating or 100, 1),
                (away_stats.offensive_rating or 100) / max(home_stats.defensive_rating or 100, 1),
            ])
        else:
            features.extend([0, 0, 1.0, 1.0])
        
        # Sport encoding (one-hot like)
        sport_map = {"NBA": 1, "NFL": 2, "MLB": 3, "NHL": 4, "UFC": 5}
        sport_encoded = [0] * 5
        if game.sport in sport_map:
            sport_encoded[sport_map[game.sport] - 1] = 1
        features.extend(sport_encoded)
        
        return np.array(features).reshape(1, -1)
    
    def prepare_training_data(self, sport: str = None, min_games: int = 50) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Prepare training data from historical games with results.
        
        Returns:
            (moneyline_data, spread_data, total_data) DataFrames with features and targets
        """
        # Get finished games with results
        query = self.session.query(Game).filter(Game.status == "finished")
        if sport:
            query = query.filter(Game.sport == sport)
        
        games = query.all()
        
        if len(games) < min_games:
            logger.warning(f"Only {len(games)} finished games found. Need at least {min_games} for training.")
            return None, None, None
        
        moneyline_data = []
        spread_data = []
        total_data = []
        
        for game in games:
            # Get game result from legs
            legs = self.session.query(Leg).filter_by(game_id=game.id).all()
            if not legs:
                continue
            
            # Extract features
            try:
                features = self.extract_features(game).flatten()
            except:
                continue
            
            # Determine outcomes from legs
            for leg in legs:
                if leg.bet_type == "moneyline" and leg.result in ["win", "loss"]:
                    # Home win = 1, Away win = 0
                    outcome = 1 if (leg.selection == game.home_team and leg.result == "win") or \
                                  (leg.selection == game.away_team and leg.result == "loss") else 0
                    moneyline_data.append({
                        "features": features,
                        "outcome": outcome,
                        "sport": game.sport
                    })
                
                elif leg.bet_type == "spread" and leg.result in ["win", "loss"]:
                    # Actual margin = spread if win, -spread if loss (simplified)
                    actual_margin = game.spread if leg.result == "win" else -game.spread
                    spread_data.append({
                        "features": features,
                        "actual_margin": actual_margin,
                        "sport": game.sport
                    })
                
                elif leg.bet_type == "total" and leg.result in ["win", "loss"]:
                    # Use game total as target (simplified - would need actual scores)
                    total_data.append({
                        "features": features,
                        "total": game.total or 0,
                        "sport": game.sport
                    })
        
        # Convert to DataFrames
        ml_df = pd.DataFrame(moneyline_data) if moneyline_data else None
        spread_df = pd.DataFrame(spread_data) if spread_data else None
        total_df = pd.DataFrame(total_data) if total_data else None
        
        return ml_df, spread_df, total_df
    
    def train_moneyline_model(self, historical_data: pd.DataFrame = None, sport: str = None):
        """Train model to predict moneyline outcomes."""
        if historical_data is None:
            historical_data, _, _ = self.prepare_training_data(sport=sport, min_games=30)
        
        if historical_data is None or len(historical_data) < 30:
            logger.warning("Not enough historical data for moneyline training. Using fallback.")
            self.is_trained = False
            return
        
        # Extract features and targets
        X = np.array([f for f in historical_data["features"]])
        y = historical_data["outcome"].values
        
        if len(np.unique(y)) < 2:
            logger.warning("Not enough class diversity for moneyline training.")
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.moneyline_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.moneyline_model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_acc = accuracy_score(y_train, self.moneyline_model.predict(X_train_scaled))
        test_acc = accuracy_score(y_test, self.moneyline_model.predict(X_test_scaled))
        
        logger.info(f"Moneyline model trained: Train Acc={train_acc:.3f}, Test Acc={test_acc:.3f}")
        self.is_trained = True
        self.save_models()
    
    def train_spread_model(self, historical_data: pd.DataFrame = None, sport: str = None):
        """Train model to predict spread outcomes."""
        if historical_data is None:
            _, historical_data, _ = self.prepare_training_data(sport=sport, min_games=30)
        
        if historical_data is None or len(historical_data) < 30:
            logger.warning("Not enough historical data for spread training.")
            return
        
        X = np.array([f for f in historical_data["features"]])
        y = historical_data["actual_margin"].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.spread_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.spread_model.fit(X_train_scaled, y_train)
        
        train_mae = mean_absolute_error(y_train, self.spread_model.predict(X_train_scaled))
        test_mae = mean_absolute_error(y_test, self.spread_model.predict(X_test_scaled))
        
        logger.info(f"Spread model trained: Train MAE={train_mae:.3f}, Test MAE={test_mae:.3f}")
        self.save_models()
    
    def train_total_model(self, historical_data: pd.DataFrame = None, sport: str = None):
        """Train model to predict total points."""
        if historical_data is None:
            _, _, historical_data = self.prepare_training_data(sport=sport, min_games=30)
        
        if historical_data is None or len(historical_data) < 30:
            logger.warning("Not enough historical data for total training.")
            return
        
        X = np.array([f for f in historical_data["features"]])
        y = historical_data["total"].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.total_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.total_model.fit(X_train_scaled, y_train)
        
        train_mae = mean_absolute_error(y_train, self.total_model.predict(X_train_scaled))
        test_mae = mean_absolute_error(y_test, self.total_model.predict(X_test_scaled))
        
        logger.info(f"Total model trained: Train MAE={train_mae:.3f}, Test MAE={test_mae:.3f}")
        self.save_models()
    
    def train_all_models(self, sport: str = None):
        """Train all models."""
        logger.info("Preparing training data...")
        ml_data, spread_data, total_data = self.prepare_training_data(sport=sport, min_games=30)
        
        if ml_data is not None:
            self.train_moneyline_model(ml_data)
        if spread_data is not None:
            self.train_spread_model(spread_data)
        if total_data is not None:
            self.train_total_model(total_data)
    
    def predict_moneyline_probability(self, game: Game) -> Tuple[float, float]:
        """
        Predict probability of home and away team winning.
        
        Returns:
            (home_prob, away_prob)
        """
        # Fallback to implied probability from odds
        if game.home_moneyline and game.away_moneyline:
            home_implied = self._american_to_implied_prob(game.home_moneyline)
            away_implied = self._american_to_implied_prob(game.away_moneyline)
            # Normalize
            total = home_implied + away_implied
            if total > 0:
                fallback_home = home_implied / total
                fallback_away = away_implied / total
            else:
                fallback_home = fallback_away = 0.5
        else:
            fallback_home = fallback_away = 0.5
        
        # Use ML model if trained
        if self.is_trained and self.moneyline_model is not None:
            try:
                features = self.extract_features(game)
                features_scaled = self.scaler.transform(features)
                prediction = self.moneyline_model.predict_proba(features_scaled)[0]
                
                # Blend ML prediction with implied probability (70% ML, 30% implied)
                home_prob = 0.7 * prediction[1] + 0.3 * fallback_home
                away_prob = 0.7 * prediction[0] + 0.3 * fallback_away
                
                # Normalize
                total = home_prob + away_prob
                if total > 0:
                    return home_prob / total, away_prob / total
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}. Using fallback.")
        
        return fallback_home, fallback_away
    
    def predict_spread(self, game: Game) -> float:
        """Predict the actual spread (margin)."""
        if self.spread_model is None:
            # Fallback to book spread
            return game.spread or 0.0
        
        try:
            features = self.extract_features(game)
            features_scaled = self.scaler.transform(features)
            predicted_margin = self.spread_model.predict(features_scaled)[0]
            
            # Blend with book spread (60% ML, 40% book)
            book_spread = game.spread or 0.0
            return 0.6 * predicted_margin + 0.4 * book_spread
        except Exception as e:
            logger.warning(f"Spread prediction failed: {e}. Using book spread.")
            return game.spread or 0.0
    
    def predict_total(self, game: Game) -> float:
        """Predict the total points."""
        if self.total_model is None:
            # Fallback to book total
            return game.total or 0.0
        
        try:
            features = self.extract_features(game)
            features_scaled = self.scaler.transform(features)
            predicted_total = self.total_model.predict(features_scaled)[0]
            
            # Blend with book total (60% ML, 40% book)
            book_total = game.total or 0.0
            return 0.6 * predicted_total + 0.4 * book_total
        except Exception as e:
            logger.warning(f"Total prediction failed: {e}. Using book total.")
            return game.total or 0.0
    
    def predict_prop_probability(self, game: Game, prop: PlayerProp, selection: str = "over") -> float:
        """
        Predict probability for a player prop.
        
        Args:
            game: The game
            prop: The player prop
            selection: "over", "under", "yes", or "no"
        """
        # For now, use implied probability with small adjustments
        # In production, you'd train a prop-specific model using historical prop results
        
        if selection == "over" and prop.over_odds:
            implied = self._american_to_implied_prob(prop.over_odds)
            # Slight edge based on player stats if available
            return min(implied * 1.05, 0.95)  # 5% boost, cap at 95%
        elif selection == "under" and prop.under_odds:
            implied = self._american_to_implied_prob(prop.under_odds)
            return min(implied * 1.05, 0.95)
        elif selection == "yes" and prop.yes_odds:
            implied = self._american_to_implied_prob(prop.yes_odds)
            return min(implied * 1.05, 0.95)
        elif selection == "no" and prop.no_odds:
            implied = self._american_to_implied_prob(prop.no_odds)
            return min(implied * 1.05, 0.95)
        
        return 0.5
    
    def _american_to_implied_prob(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def simulate_game(self, game: Game, n_simulations: int = 10000) -> Dict:
        """
        Monte Carlo simulation of game outcomes using ML predictions.
        
        Returns:
            Dictionary with win probabilities and score distributions
        """
        # Get ML predictions
        home_win_prob, away_win_prob = self.predict_moneyline_probability(game)
        predicted_total = self.predict_total(game)
        predicted_spread = self.predict_spread(game)
        
        # Get team stats for variance estimation
        home_stats = None
        away_stats = None
        
        if game.home_team:
            home_stats = self.session.query(TeamStat).filter_by(
                team=game.home_team, sport=game.sport
            ).first()
        
        if game.away_team:
            away_stats = self.session.query(TeamStat).filter_by(
                team=game.away_team, sport=game.sport
            ).first()
        
        # Use average stats if not available
        home_off_rating = home_stats.offensive_rating if home_stats and home_stats.offensive_rating else 100
        home_def_rating = home_stats.defensive_rating if home_stats and home_stats.defensive_rating else 100
        away_off_rating = away_stats.offensive_rating if away_stats and away_stats.offensive_rating else 100
        away_def_rating = away_stats.defensive_rating if away_stats and away_stats.defensive_rating else 100
        
        # Sport-specific scoring averages
        sport_totals = {"NBA": 220, "NFL": 45, "MLB": 9, "NHL": 5.5, "UFC": 0}
        avg_total = sport_totals.get(game.sport, 100)
        
        if predicted_total > 0:
            avg_total = predicted_total
        
        # Simulate scores
        home_scores = []
        away_scores = []
        home_wins = 0
        over_hits = 0
        
        # Calculate expected scores from total and spread
        expected_home = (avg_total + predicted_spread) / 2
        expected_away = (avg_total - predicted_spread) / 2
        
        # Variance based on sport
        variance_map = {"NBA": 12, "NFL": 7, "MLB": 2, "NHL": 1.5, "UFC": 0}
        variance = variance_map.get(game.sport, 10)
        
        for _ in range(n_simulations):
            # Use Poisson-like distribution for team sports
            if game.sport in ["NBA", "NFL", "NHL"]:
                # Normal distribution with sport-appropriate variance
                home_score = np.random.normal(expected_home, variance)
                away_score = np.random.normal(expected_away, variance)
            elif game.sport == "MLB":
                # Lower variance for baseball
                home_score = np.random.normal(expected_home, variance)
                away_score = np.random.normal(expected_away, variance)
            else:
                # Binary outcome for UFC
                home_score = 1 if np.random.random() < home_win_prob else 0
                away_score = 1 - home_score
            
            home_score = max(0, int(home_score))
            away_score = max(0, int(away_score))
            
            home_scores.append(home_score)
            away_scores.append(away_score)
            
            if home_score > away_score:
                home_wins += 1
            
            if game.total and (home_score + away_score) > game.total:
                over_hits += 1
        
        simulated_home_prob = home_wins / n_simulations
        simulated_away_prob = 1 - simulated_home_prob
        over_prob = over_hits / n_simulations if game.total else None
        
        # Blend ML predictions with simulation
        final_home_prob = 0.6 * home_win_prob + 0.4 * simulated_home_prob
        final_away_prob = 0.6 * away_win_prob + 0.4 * simulated_away_prob
        
        return {
            "home_win_probability": final_home_prob,
            "away_win_probability": final_away_prob,
            "average_total": np.mean([h + a for h, a in zip(home_scores, away_scores)]),
            "over_probability": over_prob,
            "home_score_distribution": home_scores[:1000],  # Limit for memory
            "away_score_distribution": away_scores[:1000],
            "predicted_spread": predicted_spread,
            "predicted_total": predicted_total
        }
    
    def bayesian_update(self, prior_prob: float, evidence: Dict) -> float:
        """
        Bayesian update of probability given evidence.
        
        Args:
            prior_prob: Prior probability
            evidence: Dictionary of evidence (e.g., injury reports, weather, line movement)
        
        Returns:
            Updated probability
        """
        # Start with prior
        posterior = prior_prob
        
        # Key player injuries
        if evidence.get("key_player_injured"):
            posterior *= 0.85  # 15% reduction
        
        if evidence.get("key_player_returning"):
            posterior *= 1.10  # 10% boost
        
        # Home advantage
        if evidence.get("home_advantage"):
            posterior *= 1.05  # 5% boost
        
        # Line movement (sharp money)
        line_movement = evidence.get("line_movement", 0)
        if abs(line_movement) > 2:  # Significant movement
            posterior *= (1 + line_movement * 0.02)  # 2% per point moved
        
        # Weather (for outdoor sports)
        if evidence.get("bad_weather"):
            posterior *= 0.95  # Slight reduction
        
        # Rest advantage
        if evidence.get("rest_advantage"):
            posterior *= 1.03  # 3% boost
        
        # Clamp between 0.01 and 0.99
        return min(max(posterior, 0.01), 0.99)
    
    def save_models(self):
        """Save trained models to disk."""
        try:
            if self.moneyline_model is not None:
                with open(os.path.join(self.model_dir, "moneyline_model.pkl"), "wb") as f:
                    pickle.dump(self.moneyline_model, f)
            
            if self.spread_model is not None:
                with open(os.path.join(self.model_dir, "spread_model.pkl"), "wb") as f:
                    pickle.dump(self.spread_model, f)
            
            if self.total_model is not None:
                with open(os.path.join(self.model_dir, "total_model.pkl"), "wb") as f:
                    pickle.dump(self.total_model, f)
            
            if hasattr(self.scaler, 'mean_'):
                with open(os.path.join(self.model_dir, "scaler.pkl"), "wb") as f:
                    pickle.dump(self.scaler, f)
            
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self):
        """Load trained models from disk."""
        try:
            moneyline_path = os.path.join(self.model_dir, "moneyline_model.pkl")
            if os.path.exists(moneyline_path):
                with open(moneyline_path, "rb") as f:
                    self.moneyline_model = pickle.load(f)
                self.is_trained = True
            
            spread_path = os.path.join(self.model_dir, "spread_model.pkl")
            if os.path.exists(spread_path):
                with open(spread_path, "rb") as f:
                    self.spread_model = pickle.load(f)
            
            total_path = os.path.join(self.model_dir, "total_model.pkl")
            if os.path.exists(total_path):
                with open(total_path, "rb") as f:
                    self.total_model = pickle.load(f)
            
            scaler_path = os.path.join(self.model_dir, "scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
            
            if self.is_trained:
                logger.info("Models loaded successfully")
        except Exception as e:
            logger.warning(f"Error loading models: {e}. Will train new models.")
            self.is_trained = False
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

