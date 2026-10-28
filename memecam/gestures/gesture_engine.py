"""Intentional, edge-triggered gesture confirmation using monotonic seconds."""
import logging

LOG = logging.getLogger(__name__)


class GestureEngine:
    def __init__(self, confirmation=.35, release=.25, cooldown=.8):
        self.confirmation, self.release, self.cooldown = confirmation, release, cooldown
        self.candidate = None
        self.since = 0.0
        self.latched = None
        self.away_since = None
        self.last_trigger = float("-inf")
        self.progress = 0.0
        self.confirmed = None

    def update(self, gesture, now):
        if self.latched is not None:
            if gesture == self.latched:
                self.away_since = None
            elif self.away_since is None:
                self.away_since = now
            elif now - self.away_since >= self.release:
                self.latched = None
                self.away_since = None
        if gesture != self.candidate:
            self.candidate, self.since = gesture, now
            LOG.debug("Gesture candidate: %s", gesture)
        self.progress = min(1.0, max(0.0, (now - self.since) / self.confirmation)) if gesture else 0
        if (gesture and self.latched is None and self.progress >= 1
                and now - self.last_trigger >= self.cooldown):
            self.latched = self.confirmed = gesture
            self.last_trigger = now
            LOG.info("Gesture confirmed: %s", gesture)
            return gesture
        return None
