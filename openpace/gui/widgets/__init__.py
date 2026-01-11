"""
Custom widgets for OpenPace GUI.
"""

from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget
from .timeline_view import TimelineView

__all__ = [
    'BatteryTrendWidget',
    'ImpedanceTrendWidget',
    'BurdenWidget',
    'TimelineView',
]
