#!/usr/bin/env python3
"""
Quick test script for draggable panels implementation.

This script tests the core functionality of the draggable panels system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    try:
        from openpace.gui.widgets.draggable_panel import DraggablePanel
        from openpace.gui.widgets.resize_handle import ResizeHandle, ResizeHandleManager
        from openpace.gui.layouts import GridLayoutManager, LayoutMode, LayoutSerializer
        from openpace.gui.dialogs import GridSettingsDialog
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_grid_layout_manager():
    """Test GridLayoutManager basic functionality."""
    print("\nTesting GridLayoutManager...")
    try:
        from PyQt6.QtWidgets import QWidget, QApplication
        from openpace.gui.layouts import GridLayoutManager, LayoutMode

        app = QApplication.instance() or QApplication(sys.argv)

        # Create container and manager
        container = QWidget()
        manager = GridLayoutManager(container, rows=12, cols=12)

        # Add a test panel
        panel = QWidget()
        manager.add_panel("test", panel, row=0, col=0, row_span=2, col_span=4)

        # Verify panel was added
        assert "test" in manager.panels
        assert manager.panels["test"].row == 0
        assert manager.panels["test"].col == 0

        # Test moving panel
        manager.move_panel("test", 2, 2)
        assert manager.panels["test"].row == 2
        assert manager.panels["test"].col == 2

        # Test serialization
        layout_data = manager.serialize_layout()
        assert "panels" in layout_data
        assert "test" in layout_data["panels"]

        print("✓ GridLayoutManager tests passed")
        return True
    except Exception as e:
        print(f"✗ GridLayoutManager tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_layout_serializer():
    """Test LayoutSerializer functionality."""
    print("\nTesting LayoutSerializer...")
    try:
        from openpace.gui.layouts import LayoutSerializer
        import tempfile
        from pathlib import Path

        # Test default layouts
        vertical_layout = LayoutSerializer.create_default_vertical_layout()
        assert "panels" in vertical_layout
        assert "battery" in vertical_layout["panels"]

        horizontal_layout = LayoutSerializer.create_default_horizontal_layout()
        assert "panels" in horizontal_layout
        assert "layout_mode" in horizontal_layout

        # Test validation
        assert LayoutSerializer.validate_layout(vertical_layout)

        # Test file operations
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_layout.json"
            assert LayoutSerializer.save_to_file(vertical_layout, test_file)
            loaded_layout = LayoutSerializer.load_from_file(test_file)
            assert loaded_layout is not None
            assert loaded_layout["layout_mode"] == vertical_layout["layout_mode"]

        print("✓ LayoutSerializer tests passed")
        return True
    except Exception as e:
        print(f"✗ LayoutSerializer tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_extensions():
    """Test UIConfig extensions."""
    print("\nTesting UIConfig extensions...")
    try:
        from openpace.config import UIConfig

        config = UIConfig()

        # Verify new fields exist
        assert hasattr(config, 'use_grid_layout')
        assert hasattr(config, 'save_panel_layouts')
        assert hasattr(config, 'panel_layouts')
        assert hasattr(config, 'default_layout_mode')
        assert hasattr(config, 'panel_min_height')
        assert hasattr(config, 'panel_min_width')
        assert hasattr(config, 'grid_rows')
        assert hasattr(config, 'grid_cols')
        assert hasattr(config, 'snap_to_grid')

        # Verify default values
        assert config.grid_rows == 12
        assert config.grid_cols == 12
        assert config.use_grid_layout == True

        print("✓ UIConfig extensions verified")
        return True
    except Exception as e:
        print(f"✗ UIConfig tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Draggable Panels Implementation - Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("UIConfig", test_config_extensions()))
    results.append(("GridLayoutManager", test_grid_layout_manager()))
    results.append(("LayoutSerializer", test_layout_serializer()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name:.<40} {status}")

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Implementation is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
