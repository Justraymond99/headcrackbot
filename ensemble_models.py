"""Ensemble ML models - combine multiple models."""
from typing import List, Dict, Tuple
from models import Game, SessionLocal
from ml_models import MLPredictor
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EnsembleModels:
    """Combine multiple ML models for better predictions."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.models = []
        self.weights = []
    
    def add_model(self, model: MLPredictor, weight: float = 1.0):
        """Add a model to the ensemble."""
        self.models.append(model)
        self.weights.append(weight)
        # Normalize weights
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]
    
    def predict_moneyline_ensemble(self, game: Game) -> Tuple[float, float]:
        """Predict using ensemble of models."""
        if not self.models:
            # Fallback to single model
            predictor = MLPredictor()
            return predictor.predict_moneyline_probability(game)
        
        predictions = []
        for model in self.models:
            try:
                pred = model.predict_moneyline_probability(game)
                predictions.append(pred)
            except:
                continue
        
        if not predictions:
            return 0.5, 0.5
        
        # Weighted average
        home_probs = [p[0] for p in predictions]
        away_probs = [p[1] for p in predictions]
        
        # Use equal weights if not set
        if len(self.weights) != len(predictions):
            weights = [1.0 / len(predictions)] * len(predictions)
        else:
            weights = self.weights[:len(predictions)]
        
        home_prob = sum(h * w for h, w in zip(home_probs, weights))
        away_prob = sum(a * w for a, w in zip(away_probs, weights))
        
        # Normalize
        total = home_prob + away_prob
        if total > 0:
            return home_prob / total, away_prob / total
        
        return 0.5, 0.5
    
    def get_model_performance(self) -> Dict:
        """Get performance metrics for each model."""
        # In real implementation, would track model performance
        return {
            "model_count": len(self.models),
            "weights": self.weights
        }
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

