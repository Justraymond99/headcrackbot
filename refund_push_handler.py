"""Handle refunds and pushes automatically."""
from typing import Optional, Dict
from datetime import datetime
from models import Leg, Parlay, SessionLocal
import logging

logger = logging.getLogger(__name__)


class RefundPushHandler:
    """Automatically detect and handle refunds/pushes."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def check_for_push(self, leg: Leg, actual_score: Optional[Dict] = None) -> bool:
        """Check if a leg resulted in a push."""
        if leg.bet_type == "spread":
            # Push if actual margin equals spread
            game = leg.game
            if actual_score and game.spread:
                home_score = actual_score.get("home_score", 0)
                away_score = actual_score.get("away_score", 0)
                margin = home_score - away_score
                
                if abs(margin - game.spread) < 0.5:  # Within 0.5 (push)
                    leg.result = "push"
                    leg.actual_outcome = "Push"
                    leg.updated_at = datetime.utcnow()
                    self.session.commit()
                    return True
        
        elif leg.bet_type == "total":
            # Push if total equals exactly
            game = leg.game
            if actual_score and game.total:
                home_score = actual_score.get("home_score", 0)
                away_score = actual_score.get("away_score", 0)
                total = home_score + away_score
                
                if abs(total - game.total) < 0.5:  # Push
                    leg.result = "push"
                    leg.actual_outcome = "Push"
                    leg.updated_at = datetime.utcnow()
                    self.session.commit()
                    return True
        
        return False
    
    def handle_parlay_with_push(self, parlay: Parlay):
        """Handle parlay when one or more legs push."""
        legs = parlay.legs
        push_count = sum(1 for leg in legs if leg.result == "push")
        win_count = sum(1 for leg in legs if leg.result == "win")
        loss_count = sum(1 for leg in legs if leg.result == "loss")
        
        # If all legs push, refund
        if push_count == len(legs):
            parlay.result = "push"
            parlay.payout = parlay.stake  # Full refund
            parlay.status = "finished"
            self.session.commit()
            return "refund"
        
        # If any leg loses, parlay loses (even with pushes)
        if loss_count > 0:
            parlay.result = "loss"
            parlay.payout = 0
            parlay.status = "finished"
            self.session.commit()
            return "loss"
        
        # If all non-push legs win, recalculate parlay
        if win_count > 0 and loss_count == 0:
            # Recalculate odds without push legs
            active_legs = [leg for leg in legs if leg.result != "push"]
            if len(active_legs) >= 2:  # Minimum legs for parlay
                # Recalculate combined odds
                combined_decimal = 1.0
                for leg in active_legs:
                    if leg.odds > 0:
                        decimal = (leg.odds / 100) + 1
                    else:
                        decimal = (100 / abs(leg.odds)) + 1
                    combined_decimal *= decimal
                
                combined_decimal -= 1
                combined_american = (combined_decimal * 100) if combined_decimal >= 1 else (-100 / combined_decimal)
                
                # Calculate new payout
                new_payout = parlay.stake * combined_decimal
                parlay.combined_odds = combined_american
                parlay.payout = new_payout
                parlay.result = "win"
                parlay.status = "finished"
                self.session.commit()
                return "adjusted_win"
            else:
                # Not enough legs, refund
                parlay.result = "push"
                parlay.payout = parlay.stake
                parlay.status = "finished"
                self.session.commit()
                return "refund"
        
        return "pending"
    
    def process_refunds(self):
        """Process all pending refunds."""
        # Find legs with push results that haven't been processed
        push_legs = self.session.query(Leg).filter_by(result="push").all()
        
        processed_parlays = set()
        for leg in push_legs:
            if leg.parlay_id not in processed_parlays:
                self.handle_parlay_with_push(leg.parlay)
                processed_parlays.add(leg.parlay_id)
        
        logger.info(f"Processed {len(processed_parlays)} parlays with pushes/refunds")
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

