"""Seasonality calculation engine for diurnal and weekly enterprise patterns."""

import math
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SeasonalityProfile:
    """Configurable diurnal (hourly) and weekly (day-of-week) seasonality profiles."""

    # Hourly multipliers (0-23 hours UTC)
    # Reflects e-commerce diurnal cycle: overnight lull, midday surge, evening peak
    hourly_weights: list[float] = field(
        default_factory=lambda: [
            0.28,
            0.22,
            0.18,
            0.16,
            0.18,
            0.25,  # 00:00 - 05:00: Night lull
            0.45,
            0.72,
            0.95,
            1.18,
            1.25,
            1.22,  # 06:00 - 11:00: Morning ramp & midday peak
            1.20,
            1.15,
            1.12,
            1.14,
            1.18,
            1.24,  # 12:00 - 17:00: Afternoon sustained volume
            1.32,
            1.35,
            1.28,
            1.10,
            0.75,
            0.45,  # 18:00 - 23:00: Prime evening shopping & taper
        ]
    )

    # Weekly multipliers (Monday=0, Tuesday=1, ..., Sunday=6)
    weekly_weights: list[float] = field(
        default_factory=lambda: [
            1.02,  # Monday: Strong start of week
            1.00,  # Tuesday: Baseline weekday
            0.98,  # Wednesday: Midweek steady
            1.04,  # Thursday: Pre-weekend ramp
            1.15,  # Friday: Payday & weekend prep
            1.12,  # Saturday: Active leisure shopping
            1.18,  # Sunday: Highest retail conversion & cart checkout evening
        ]
    )

    def get_diurnal_factor(self, hour: int) -> float:
        """Returns diurnal traffic multiplier for given hour (0-23)."""
        if 0 <= hour < len(self.hourly_weights):
            return self.hourly_weights[hour]
        return 1.0

    def get_weekly_factor(self, weekday: int) -> float:
        """Returns weekly multiplier for given weekday (0=Monday, 6=Sunday)."""
        if 0 <= weekday < len(self.weekly_weights):
            return self.weekly_weights[weekday]
        return 1.0

    def get_combined_multiplier(self, dt: datetime) -> float:
        """Calculates combined seasonal multiplier for a given timestamp."""
        diurnal = self.get_diurnal_factor(dt.hour)
        weekly = self.get_weekly_factor(dt.weekday())

        # Subtle monthly macro trend (slight sinusoid over 90 days for realism)
        day_of_year = dt.timetuple().tm_yday
        macro_trend = 1.0 + 0.05 * math.sin(2 * math.pi * day_of_year / 365.25)

        return diurnal * weekly * macro_trend
