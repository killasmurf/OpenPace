"""
Layout Serializer

Handles serialization and deserialization of panel layouts to/from JSON.
Provides functionality to save layouts to files and load them back.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LayoutSerializer:
    """
    Serializes and deserializes panel layouts.

    Handles:
    - Converting layout data to/from JSON
    - Saving layouts to files
    - Loading layouts from files
    - Validating layout data
    """

    @staticmethod
    def serialize(grid_manager) -> Dict[str, Any]:
        """
        Serialize a grid layout manager to a dictionary.

        Args:
            grid_manager: GridLayoutManager instance

        Returns:
            Dictionary containing serialized layout data
        """
        layout_data = grid_manager.serialize_layout()

        # Add metadata
        layout_data['version'] = '1.0'
        layout_data['timestamp'] = datetime.now().isoformat()

        return layout_data

    @staticmethod
    def deserialize(layout_data: Dict[str, Any], grid_manager) -> bool:
        """
        Deserialize layout data and apply it to a grid manager.

        Args:
            layout_data: Dictionary containing layout data
            grid_manager: GridLayoutManager instance to apply layout to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate version (for future compatibility)
            version = layout_data.get('version', '1.0')
            if version != '1.0':
                logger.warning(f"Layout version {version} may not be fully compatible")

            # Remove metadata before passing to grid manager
            layout_copy = layout_data.copy()
            layout_copy.pop('version', None)
            layout_copy.pop('timestamp', None)

            # Apply layout
            grid_manager.restore_layout(layout_copy)

            return True

        except Exception as e:
            logger.error(f"Failed to deserialize layout: {e}")
            return False

    @staticmethod
    def save_to_file(layout_data: Dict[str, Any], file_path: Path) -> bool:
        """
        Save layout data to a JSON file.

        Args:
            layout_data: Dictionary containing layout data
            file_path: Path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(layout_data, f, indent=2)

            logger.info(f"Layout saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save layout to {file_path}: {e}")
            return False

    @staticmethod
    def load_from_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load layout data from a JSON file.

        Args:
            file_path: Path to the layout file

        Returns:
            Dictionary containing layout data, or None if failed
        """
        try:
            if not file_path.exists():
                logger.warning(f"Layout file not found: {file_path}")
                return None

            with open(file_path, 'r') as f:
                layout_data = json.load(f)

            logger.info(f"Layout loaded from {file_path}")
            return layout_data

        except Exception as e:
            logger.error(f"Failed to load layout from {file_path}: {e}")
            return None

    @staticmethod
    def get_default_layout_path() -> Path:
        """
        Get the default path for saving layouts.

        Returns:
            Path to default layout file
        """
        return Path.home() / ".openpace" / "panel_layouts.json"

    @staticmethod
    def get_presets_directory() -> Path:
        """
        Get the directory for layout presets.

        Returns:
            Path to presets directory
        """
        return Path.home() / ".openpace" / "layout_presets"

    @staticmethod
    def save_preset(layout_data: Dict[str, Any], preset_name: str) -> bool:
        """
        Save a layout as a named preset.

        Args:
            layout_data: Dictionary containing layout data
            preset_name: Name for the preset

        Returns:
            True if successful, False otherwise
        """
        presets_dir = LayoutSerializer.get_presets_directory()
        preset_path = presets_dir / f"{preset_name}.json"

        return LayoutSerializer.save_to_file(layout_data, preset_path)

    @staticmethod
    def load_preset(preset_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a named layout preset.

        Args:
            preset_name: Name of the preset

        Returns:
            Dictionary containing layout data, or None if failed
        """
        presets_dir = LayoutSerializer.get_presets_directory()
        preset_path = presets_dir / f"{preset_name}.json"

        return LayoutSerializer.load_from_file(preset_path)

    @staticmethod
    def list_presets() -> list[str]:
        """
        List all available layout presets.

        Returns:
            List of preset names
        """
        presets_dir = LayoutSerializer.get_presets_directory()

        if not presets_dir.exists():
            return []

        try:
            preset_files = presets_dir.glob("*.json")
            return [f.stem for f in preset_files]

        except Exception as e:
            logger.error(f"Failed to list presets: {e}")
            return []

    @staticmethod
    def delete_preset(preset_name: str) -> bool:
        """
        Delete a layout preset.

        Args:
            preset_name: Name of the preset to delete

        Returns:
            True if successful, False otherwise
        """
        presets_dir = LayoutSerializer.get_presets_directory()
        preset_path = presets_dir / f"{preset_name}.json"

        try:
            if preset_path.exists():
                preset_path.unlink()
                logger.info(f"Deleted preset: {preset_name}")
                return True
            else:
                logger.warning(f"Preset not found: {preset_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete preset {preset_name}: {e}")
            return False

    @staticmethod
    def validate_layout(layout_data: Dict[str, Any]) -> bool:
        """
        Validate layout data structure.

        Args:
            layout_data: Dictionary containing layout data

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['layout_mode', 'grid_rows', 'grid_cols', 'panels']
            for field in required_fields:
                if field not in layout_data:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Validate panels
            panels = layout_data.get('panels', {})
            if not isinstance(panels, dict):
                logger.error("Panels must be a dictionary")
                return False

            for panel_id, panel_data in panels.items():
                required_panel_fields = ['row', 'col', 'row_span', 'col_span']
                for field in required_panel_fields:
                    if field not in panel_data:
                        logger.error(f"Panel {panel_id} missing field: {field}")
                        return False

                # Validate numeric values
                if (panel_data['row'] < 0 or panel_data['col'] < 0 or
                    panel_data['row_span'] <= 0 or panel_data['col_span'] <= 0):
                    logger.error(f"Panel {panel_id} has invalid dimensions")
                    return False

            return True

        except Exception as e:
            logger.error(f"Layout validation failed: {e}")
            return False

    @staticmethod
    def create_default_vertical_layout() -> Dict[str, Any]:
        """
        Create default 3x2 grid layout data.

        Returns:
            Dictionary containing default grid layout
        """
        return {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'layout_mode': 'vertical',
            'grid_rows': 12,
            'grid_cols': 12,
            'panels': {
                'battery': {
                    'row': 0,
                    'col': 0,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                },
                'atrial_impedance': {
                    'row': 0,
                    'col': 4,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                },
                'vent_impedance': {
                    'row': 0,
                    'col': 8,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                },
                'burden': {
                    'row': 6,
                    'col': 0,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                },
                'settings': {
                    'row': 6,
                    'col': 4,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                },
                'device_settings': {
                    'row': 6,
                    'col': 8,
                    'row_span': 6,
                    'col_span': 4,
                    'visible': True,
                    'collapsed': False
                }
            }
        }

    @staticmethod
    def create_default_horizontal_layout() -> Dict[str, Any]:
        """
        Create default horizontal layout data.

        Returns:
            Dictionary containing default horizontal layout
        """
        return {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'layout_mode': 'horizontal',
            'grid_rows': 12,
            'grid_cols': 12,
            'panels': {
                'battery': {
                    'row': 0,
                    'col': 0,
                    'row_span': 2,
                    'col_span': 12,
                    'visible': True,
                    'collapsed': False
                },
                'atrial_impedance': {
                    'row': 2,
                    'col': 0,
                    'row_span': 3,
                    'col_span': 6,
                    'visible': True,
                    'collapsed': False
                },
                'vent_impedance': {
                    'row': 2,
                    'col': 6,
                    'row_span': 3,
                    'col_span': 6,
                    'visible': True,
                    'collapsed': False
                },
                'burden': {
                    'row': 5,
                    'col': 0,
                    'row_span': 3,
                    'col_span': 6,
                    'visible': True,
                    'collapsed': False
                },
                'settings': {
                    'row': 5,
                    'col': 6,
                    'row_span': 3,
                    'col_span': 6,
                    'visible': True,
                    'collapsed': False
                },
                'device_settings': {
                    'row': 8,
                    'col': 0,
                    'row_span': 4,
                    'col_span': 12,
                    'visible': True,
                    'collapsed': False
                }
            }
        }
