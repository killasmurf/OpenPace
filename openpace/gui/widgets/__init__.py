"""
Custom widgets for OpenPace GUI.
"""

from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget
from .timeline_view import TimelineView
from .summary_panel import SummaryPanel
from .egm_viewer import EGMViewerWidget
from .episode_selector import EpisodeSelectorWidget
from .settings_panel import SettingsPanel

__all__ = [
    'BatteryTrendWidget',
    'ImpedanceTrendWidget',
    'BurdenWidget',
    'TimelineView',
    'SummaryPanel',
    'EGMViewerWidget',
    'EpisodeSelectorWidget',
    'SettingsPanel',
]
