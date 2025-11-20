"""Social features - sharing, following, leaderboards."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import SocialParlay, UserFollow, Parlay, SessionLocal
import logging

logger = logging.getLogger(__name__)


class SocialFeatures:
    """Social features for sharing and following."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
    
    def share_parlay(self, parlay: Parlay, public: bool = True, tags: Optional[List[str]] = None) -> SocialParlay:
        """Share a parlay publicly."""
        social = self.session.query(SocialParlay).filter_by(parlay_id=parlay.id).first()
        
        if not social:
            social = SocialParlay(
                parlay_id=parlay.id,
                user_id=self.user_id,
                public=public,
                tags=tags or []
            )
            self.session.add(social)
        else:
            social.public = public
            social.tags = tags or []
        
        self.session.commit()
        return social
    
    def like_parlay(self, social_parlay: SocialParlay):
        """Like a shared parlay."""
        social_parlay.likes += 1
        self.session.commit()
    
    def share_parlay_link(self, social_parlay: SocialParlay):
        """Increment share count."""
        social_parlay.shares += 1
        self.session.commit()
    
    def copy_parlay(self, social_parlay: SocialParlay):
        """Copy a shared parlay."""
        social_parlay.copied += 1
        self.session.commit()
        return social_parlay.parlay
    
    def get_public_parlays(self, limit: int = 20, sort_by: str = "likes") -> List[SocialParlay]:
        """Get public shared parlays."""
        query = self.session.query(SocialParlay).filter_by(public=True)
        
        if sort_by == "likes":
            query = query.order_by(SocialParlay.likes.desc())
        elif sort_by == "recent":
            query = query.order_by(SocialParlay.created_at.desc())
        elif sort_by == "copied":
            query = query.order_by(SocialParlay.copied.desc())
        
        return query.limit(limit).all()
    
    def follow_user(self, user_id: str):
        """Follow another user."""
        # Check if already following
        existing = self.session.query(UserFollow).filter_by(
            follower_id=self.user_id,
            following_id=user_id
        ).first()
        
        if not existing and user_id != self.user_id:
            follow = UserFollow(
                follower_id=self.user_id,
                following_id=user_id
            )
            self.session.add(follow)
            self.session.commit()
    
    def unfollow_user(self, user_id: str):
        """Unfollow a user."""
        follow = self.session.query(UserFollow).filter_by(
            follower_id=self.user_id,
            following_id=user_id
        ).first()
        
        if follow:
            self.session.delete(follow)
            self.session.commit()
    
    def get_following(self) -> List[str]:
        """Get list of users you're following."""
        follows = self.session.query(UserFollow).filter_by(follower_id=self.user_id).all()
        return [f.following_id for f in follows]
    
    def get_followers(self) -> List[str]:
        """Get list of your followers."""
        follows = self.session.query(UserFollow).filter_by(following_id=self.user_id).all()
        return [f.follower_id for f in follows]
    
    def get_leaderboard(self, metric: str = "roi", days: int = 30) -> List[Dict]:
        """Get leaderboard of top users."""
        # This would require user performance tracking
        # For now, return empty (would need UserPerformance model)
        return []
    
    def get_feed(self) -> List[SocialParlay]:
        """Get feed of followed users' parlays."""
        following = self.get_following()
        
        if not following:
            return []
        
        # Get public parlays from followed users
        return self.session.query(SocialParlay).filter(
            SocialParlay.user_id.in_(following),
            SocialParlay.public == True
        ).order_by(SocialParlay.created_at.desc()).limit(50).all()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

