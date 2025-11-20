"""Bet slip builder for creating custom parlays."""
from typing import List, Dict, Optional
from datetime import datetime
from models import BetSlip, Game, SessionLocal
from research_engine import ResearchEngine
import logging

logger = logging.getLogger(__name__)


class BetSlipBuilder:
    """Build and manage bet slips."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
        self.research_engine = ResearchEngine()
    
    def create_bet_slip(self, name: Optional[str] = None) -> BetSlip:
        """Create a new bet slip."""
        bet_slip = BetSlip(
            user_id=self.user_id,
            name=name or f"Bet Slip {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            legs=[],
            total_odds=1.0,
            stake=0.0,
            potential_payout=0.0
        )
        self.session.add(bet_slip)
        self.session.commit()
        return bet_slip
    
    def add_leg(self, bet_slip: BetSlip, leg_data: Dict):
        """Add a leg to bet slip."""
        legs = bet_slip.legs or []
        legs.append(leg_data)
        bet_slip.legs = legs
        self._recalculate_slip(bet_slip)
        self.session.commit()
    
    def remove_leg(self, bet_slip: BetSlip, leg_index: int):
        """Remove a leg from bet slip."""
        legs = bet_slip.legs or []
        if 0 <= leg_index < len(legs):
            legs.pop(leg_index)
            bet_slip.legs = legs
            self._recalculate_slip(bet_slip)
            self.session.commit()
    
    def update_stake(self, bet_slip: BetSlip, stake: float):
        """Update stake amount."""
        bet_slip.stake = stake
        self._recalculate_slip(bet_slip)
        self.session.commit()
    
    def _recalculate_slip(self, bet_slip: BetSlip):
        """Recalculate slip odds and payout."""
        legs = bet_slip.legs or []
        if not legs:
            bet_slip.total_odds = 1.0
            bet_slip.potential_payout = 0.0
            return
        
        # Calculate combined odds
        combined_decimal = 1.0
        for leg in legs:
            odds = leg.get("odds", 0)
            if odds > 0:
                decimal = (odds / 100) + 1
            else:
                decimal = (100 / abs(odds)) + 1
            combined_decimal *= decimal
        
        combined_decimal -= 1
        combined_american = (combined_decimal * 100) if combined_decimal >= 1 else (-100 / combined_decimal)
        
        bet_slip.total_odds = combined_american
        bet_slip.potential_payout = bet_slip.stake * combined_decimal if bet_slip.stake else 0.0
        bet_slip.updated_at = datetime.utcnow()
    
    def save_slip(self, bet_slip: BetSlip):
        """Save bet slip."""
        bet_slip.saved = True
        bet_slip.status = "saved"
        bet_slip.updated_at = datetime.utcnow()
        self.session.commit()
    
    def get_user_slips(self, include_drafts: bool = True) -> List[BetSlip]:
        """Get user's bet slips."""
        query = self.session.query(BetSlip).filter_by(user_id=self.user_id)
        if not include_drafts:
            query = query.filter_by(saved=True)
        return query.order_by(BetSlip.updated_at.desc()).all()
    
    def get_slip(self, slip_id: int) -> Optional[BetSlip]:
        """Get a specific bet slip."""
        return self.session.query(BetSlip).filter_by(
            id=slip_id,
            user_id=self.user_id
        ).first()
    
    def delete_slip(self, bet_slip: BetSlip):
        """Delete a bet slip."""
        self.session.delete(bet_slip)
        self.session.commit()
    
    def convert_to_parlay(self, bet_slip: BetSlip) -> Dict:
        """Convert bet slip to parlay format."""
        legs = bet_slip.legs or []
        if not legs:
            return None
        
        # Calculate parlay metrics
        combined_implied = 1.0
        total_ev = 0.0
        total_confidence = 0.0
        
        for leg in legs:
            implied = leg.get("implied_probability", 0.5)
            combined_implied *= implied
            total_ev += leg.get("expected_value", 0)
            total_confidence += leg.get("confidence_score", 0.5)
        
        avg_ev = total_ev / len(legs) if legs else 0
        avg_confidence = total_confidence / len(legs) if legs else 0
        
        return {
            "legs": legs,
            "num_legs": len(legs),
            "combined_odds": bet_slip.total_odds,
            "implied_probability": combined_implied,
            "expected_value": avg_ev,
            "confidence_score": avg_confidence,
            "stake": bet_slip.stake,
            "potential_payout": bet_slip.potential_payout
        }
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

