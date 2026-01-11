"""
Episode Selector Widget

Lists and manages EGM episodes from pacemaker transmissions:
- Displays all available EGM strips
- Filters by date, type, and event
- Quick preview and selection
- Export multiple episodes
"""

from typing import List, Optional
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QPushButton,
                             QGroupBox, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session

from openpace.database.models import Observation, Transmission


class EpisodeListItem(QListWidgetItem):
    """Custom list item for EGM episodes."""

    def __init__(self, observation: Observation):
        self.observation = observation

        # Create display text
        trans_date = observation.transmission.transmission_date
        date_str = trans_date.strftime('%Y-%m-%d %H:%M')

        # Get observation description
        obs_text = observation.vendor_code or observation.variable_name or "EGM"

        display_text = f"{date_str} - {obs_text}"

        super().__init__(display_text)

        # Store observation
        self.setData(Qt.ItemDataRole.UserRole, observation)


class EpisodeSelectorWidget(QWidget):
    """
    Widget for selecting and managing EGM episodes.

    Displays list of available EGM strips and allows selection
    for viewing in the EGM viewer.
    """

    # Signals
    episode_selected = pyqtSignal(object)  # Emits Observation object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Episode Selector")

        # Data
        self.session = None
        self.current_patient_id = None
        self.episodes = []

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header_label = QLabel("EGM Episodes")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(header_label)

        # Filter controls
        filter_group = self._create_filter_controls()
        layout.addWidget(filter_group)

        # Episode list
        self.episode_list = QListWidget()
        self.episode_list.itemClicked.connect(self._on_episode_clicked)
        self.episode_list.itemDoubleClicked.connect(self._on_episode_double_clicked)
        layout.addWidget(self.episode_list)

        # Summary
        self.summary_label = QLabel("No episodes loaded")
        self.summary_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.summary_label)

        # Action buttons
        button_layout = QHBoxLayout()

        self.view_button = QPushButton("View Episode")
        self.view_button.setEnabled(False)
        self.view_button.clicked.connect(self._view_selected)
        button_layout.addWidget(self.view_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

    def _create_filter_controls(self) -> QGroupBox:
        """Create filter control group."""
        group = QGroupBox("Filters")
        layout = QVBoxLayout()
        group.setLayout(layout)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by description...")
        self.search_box.textChanged.connect(self._apply_filters)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Type filter
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "EGM Strip", "Event Recording", "AF Episode"])
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        return group

    def set_session(self, session: Session):
        """
        Set database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def load_episodes(self, patient_id: str):
        """
        Load EGM episodes for a patient.

        Args:
            patient_id: Patient identifier
        """
        if not self.session:
            self.summary_label.setText("No database session")
            return

        self.current_patient_id = patient_id

        try:
            # Query all EGM observations for this patient
            observations = self.session.query(Observation).join(
                Observation.transmission
            ).filter(
                Observation.transmission.has(patient_id=patient_id),
                Observation.value_blob.isnot(None)  # Only observations with EGM blobs
            ).order_by(
                Observation.observation_time.desc()
            ).all()

            self.episodes = observations
            self._populate_list(observations)

            count = len(observations)
            self.summary_label.setText(f"{count} episode{'s' if count != 1 else ''} found")

        except Exception as e:
            self.summary_label.setText(f"Error loading episodes: {str(e)}")
            self.episodes = []

    def _populate_list(self, observations: List[Observation]):
        """Populate episode list."""
        self.episode_list.clear()

        for obs in observations:
            item = EpisodeListItem(obs)
            self.episode_list.addItem(item)

        if observations:
            self.episode_list.setCurrentRow(0)
            self.view_button.setEnabled(True)
        else:
            self.view_button.setEnabled(False)

    def _apply_filters(self):
        """Apply search and type filters."""
        if not self.episodes:
            return

        search_text = self.search_box.text().lower()
        type_filter = self.type_combo.currentText()

        filtered_episodes = []

        for obs in self.episodes:
            # Apply search filter
            obs_text = (obs.vendor_code or obs.variable_name or "").lower()
            if search_text and search_text not in obs_text:
                continue

            # Apply type filter
            if type_filter != "All":
                # Simple type matching (can be enhanced)
                if type_filter.lower() not in obs_text:
                    continue

            filtered_episodes.append(obs)

        self._populate_list(filtered_episodes)

        count = len(filtered_episodes)
        total = len(self.episodes)
        self.summary_label.setText(
            f"{count} of {total} episode{'s' if total != 1 else ''} shown"
        )

    def _on_episode_clicked(self, item: QListWidgetItem):
        """Handle episode click."""
        self.view_button.setEnabled(True)

    def _on_episode_double_clicked(self, item: QListWidgetItem):
        """Handle episode double-click."""
        self._view_selected()

    def _view_selected(self):
        """View selected episode."""
        current_item = self.episode_list.currentItem()
        if not current_item:
            return

        observation = current_item.data(Qt.ItemDataRole.UserRole)
        if observation:
            self.episode_selected.emit(observation)

    def refresh(self):
        """Refresh episode list."""
        if self.current_patient_id:
            self.load_episodes(self.current_patient_id)

    def clear(self):
        """Clear episode list."""
        self.episode_list.clear()
        self.episodes = []
        self.current_patient_id = None
        self.view_button.setEnabled(False)
        self.summary_label.setText("No episodes loaded")
