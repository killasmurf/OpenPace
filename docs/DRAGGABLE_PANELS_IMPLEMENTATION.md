# Draggable and Resizable Panels Implementation

## Overview

This document describes the implementation of user-moveable and resizable widgets/panels in the OpenPace application. The implementation provides a flexible grid-based layout system that allows users to customize their workspace by dragging and resizing panels.

## Implementation Date

January 2026

## Key Features

### 1. Draggable Panels
- Panels can be dragged by clicking and holding the drag handle (⣿) in the panel header
- Visual feedback during drag operations (semi-transparent overlay and drop zone highlighting)
- Drop zones are calculated based on a 12x12 grid system
- Panels snap to grid positions for consistent layout

### 2. Layout Modes
Three layout modes are supported:
- **Vertical (Stacked)**: All panels span full width, stacked vertically (Ctrl+1)
- **Horizontal (Side-by-Side)**: Panels arranged in columns side-by-side (Ctrl+2)
- **Free Grid**: Panels can be positioned anywhere on the grid (Ctrl+3)

### 3. Layout Persistence
- Layouts are automatically saved after changes (with 1-second debounce)
- Saved layouts persist across application sessions
- Saved to `~/.openpace/panel_layouts.json`
- Also stored in config file

### 4. Layout Presets
- Save current layout as a named preset (Ctrl+Shift+S)
- Load previously saved presets (Ctrl+Shift+L)
- Presets stored in `~/.openpace/layout_presets/`
- Built-in default layouts for vertical and horizontal modes

### 5. Grid Settings
- Configurable grid dimensions (6-24 rows/columns)
- Adjustable minimum panel sizes
- Enable/disable snap-to-grid behavior
- Enable/disable auto-save
- Default layout mode selection

### 6. Backward Compatibility
- Feature flag (`use_grid_layout`) allows switching between old and new systems
- Legacy QSplitter layout still available
- Controlled via config: `config.ui.use_grid_layout`

## Architecture

### Core Components

#### 1. DraggablePanel (`openpace/gui/widgets/draggable_panel.py`)
Extends `CollapsiblePanel` with drag-and-drop functionality.

**Key Features:**
- Drag handle in panel header
- Mouse event handling for drag operations
- Signals for drag start/move/end
- Panel locking capability
- Visual feedback during drag

**Signals:**
- `drag_started(panel_id, start_position)`
- `drag_moved(panel_id, current_position)`
- `drag_ended(panel_id, end_position)`
- `resize_requested(panel_id, new_size)`

#### 2. GridLayoutManager (`openpace/gui/layouts/grid_layout_manager.py`)
Manages panel positioning in a flexible grid system.

**Key Features:**
- 12x12 grid (configurable)
- Panel position tracking
- Drop zone calculation
- Overlap detection
- Layout mode support (Vertical, Horizontal, Free Grid)
- Serialization/deserialization

**Main Methods:**
- `add_panel(panel_id, widget, row, col, row_span, col_span)`
- `move_panel(panel_id, new_row, new_col)`
- `resize_panel(panel_id, new_row_span, new_col_span)`
- `get_drop_zone(position) -> (row, col)`
- `serialize_layout() -> dict`
- `restore_layout(layout_data)`

#### 3. ResizeHandle (`openpace/gui/widgets/resize_handle.py`)
Provides visual handles for resizing panels.

**Key Features:**
- Corner and edge handles
- Cursor changes on hover
- Minimum/maximum size constraints
- Snap-to-grid behavior

**Handle Positions:**
- Corners: TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT
- Edges: TOP, BOTTOM, LEFT, RIGHT

**Note:** Currently implemented but not integrated into DraggablePanel. Can be added in future updates.

#### 4. LayoutSerializer (`openpace/gui/layouts/layout_serializer.py`)
Handles serialization and deserialization of layouts.

**Key Features:**
- JSON-based serialization
- Version tracking for compatibility
- Validation of layout data
- Preset management
- Default layout generation

**Layout Data Structure:**
```json
{
  "version": "1.0",
  "timestamp": "2026-01-13T12:00:00",
  "layout_mode": "vertical",
  "grid_rows": 12,
  "grid_cols": 12,
  "panels": {
    "battery": {
      "row": 0,
      "col": 0,
      "row_span": 2,
      "col_span": 12,
      "visible": true,
      "collapsed": false
    }
    // ... more panels
  }
}
```

#### 5. TimelineView Updates (`openpace/gui/widgets/timeline_view.py`)
Refactored to support grid-based layout.

**Key Changes:**
- Added `use_grid_layout` parameter
- Integrated GridLayoutManager
- Added drag event handlers
- Added drop zone visualization
- Layout save/load methods
- Support for both grid and splitter modes

#### 6. UIConfig Extensions (`openpace/config.py`)
Extended with layout-related settings.

**New Fields:**
```python
use_grid_layout: bool = True              # Enable grid layout
save_panel_layouts: bool = True           # Auto-save layouts
panel_layouts: Dict[str, Any] = {}        # Stored layouts
default_layout_mode: str = "vertical"     # Default mode
panel_min_height: int = 150               # Min height
panel_min_width: int = 200                # Min width
grid_rows: int = 12                       # Grid rows
grid_cols: int = 12                       # Grid columns
snap_to_grid: bool = True                 # Snap behavior
```

#### 7. MainWindow Menu Enhancements (`openpace/gui/main_window.py`)
Added layout management to View menu.

**New Menu Items:**
- Layout Mode submenu
  - Vertical (Stacked) - Ctrl+1
  - Horizontal (Side-by-Side) - Ctrl+2
  - Free Grid - Ctrl+3
- Save Layout As... - Ctrl+Shift+S
- Load Layout... - Ctrl+Shift+L
- Reset to Default
- Grid Settings...

#### 8. GridSettingsDialog (`openpace/gui/dialogs/grid_settings_dialog.py`)
Dialog for configuring grid settings.

**Settings:**
- Grid dimensions (rows/columns)
- Panel minimum sizes
- Snap-to-grid toggle
- Auto-save toggle
- Enable/disable grid layout
- Default layout mode

## Usage Guide

### For End Users

#### Moving Panels
1. Locate the drag handle (⣿) on the left side of the panel header
2. Click and hold the drag handle
3. Drag the panel to the desired position
4. Release to drop the panel
5. The panel will snap to the nearest grid position

#### Changing Layout Modes
1. Go to **View → Layout → Layout Mode**
2. Select desired mode:
   - **Vertical**: All panels stacked vertically
   - **Horizontal**: Panels arranged side-by-side
   - **Free Grid**: Position panels anywhere

**Keyboard Shortcuts:**
- `Ctrl+1`: Vertical layout
- `Ctrl+2`: Horizontal layout
- `Ctrl+3`: Free grid layout

#### Saving Layouts
1. Arrange panels as desired
2. Go to **View → Layout → Save Layout As...**
3. Enter a name for the preset
4. Click OK

**Shortcut:** `Ctrl+Shift+S`

#### Loading Layouts
1. Go to **View → Layout → Load Layout...**
2. Select a saved preset from the list
3. Click OK

**Shortcut:** `Ctrl+Shift+L`

#### Resetting Layout
1. Go to **View → Layout → Reset to Default**
2. Confirm the reset
3. Layout will reset to default for current mode

#### Configuring Grid Settings
1. Go to **View → Layout → Grid Settings...**
2. Adjust settings as desired:
   - Grid dimensions
   - Panel minimum sizes
   - Snap-to-grid behavior
   - Auto-save behavior
3. Click OK to save

### For Developers

#### Creating a Draggable Panel

```python
from openpace.gui.widgets.draggable_panel import DraggablePanel

# Create panel with unique ID, title, and content widget
panel = DraggablePanel(
    panel_id="my_panel",
    title="My Panel",
    content_widget=my_widget
)

# Connect drag signals
panel.drag_started.connect(lambda panel_id, pos: print(f"Drag started: {panel_id}"))
panel.drag_moved.connect(lambda panel_id, pos: print(f"Drag moved: {panel_id}"))
panel.drag_ended.connect(lambda panel_id, pos: print(f"Drag ended: {panel_id}"))

# Lock/unlock panel
panel.set_locked(True)  # Prevent dragging
panel.set_locked(False)  # Allow dragging
```

#### Using GridLayoutManager

```python
from openpace.gui.layouts import GridLayoutManager, LayoutMode

# Create grid manager
container = QWidget()
grid_manager = GridLayoutManager(container, rows=12, cols=12)

# Add panel to grid
grid_manager.add_panel(
    panel_id="panel1",
    widget=panel,
    row=0,
    col=0,
    row_span=3,
    col_span=6
)

# Move panel
grid_manager.move_panel("panel1", new_row=3, new_col=0)

# Resize panel
grid_manager.resize_panel("panel1", new_row_span=4, new_col_span=8)

# Change layout mode
grid_manager.set_mode(LayoutMode.HORIZONTAL)

# Serialize layout
layout_data = grid_manager.serialize_layout()

# Restore layout
grid_manager.restore_layout(layout_data)
```

#### Saving and Loading Layouts

```python
from openpace.gui.layouts import LayoutSerializer

# Save to file
layout_data = grid_manager.serialize_layout()
LayoutSerializer.save_to_file(layout_data, Path("my_layout.json"))

# Load from file
layout_data = LayoutSerializer.load_from_file(Path("my_layout.json"))
grid_manager.restore_layout(layout_data)

# Save as preset
LayoutSerializer.save_preset(layout_data, "My Preset")

# Load preset
layout_data = LayoutSerializer.load_preset("My Preset")

# List presets
presets = LayoutSerializer.list_presets()
```

#### Toggling Between Grid and Splitter Modes

In TimelineView initialization:
```python
# Use new grid layout
timeline = TimelineView(db_session, use_grid_layout=True)

# Use legacy splitter layout
timeline = TimelineView(db_session, use_grid_layout=False)
```

Or via config:
```python
from openpace.config import get_config

config = get_config()
config.ui.use_grid_layout = True  # Enable grid layout
config.save_to_file()
```

## Testing

### Manual Testing Checklist

- [ ] Drag panel to different positions
- [ ] Drag panel with each layout mode active
- [ ] Switch between layout modes
- [ ] Save a layout preset
- [ ] Load a saved preset
- [ ] Reset layout to default
- [ ] Open Grid Settings dialog and modify settings
- [ ] Verify layout persists after restarting application
- [ ] Test with all panels visible
- [ ] Test with some panels hidden
- [ ] Test panel collapse/expand
- [ ] Verify drop zone visualization appears during drag
- [ ] Test keyboard shortcuts (Ctrl+1, Ctrl+2, Ctrl+3, Ctrl+Shift+S, Ctrl+Shift+L)
- [ ] Test with legacy splitter mode (`use_grid_layout=False`)

### Unit Testing

Unit test files should be created for:
- `tests/gui/test_grid_layout_manager.py`
- `tests/gui/test_draggable_panel.py`
- `tests/gui/test_layout_serializer.py`

Example test structure:
```python
def test_grid_layout_manager_add_panel():
    container = QWidget()
    manager = GridLayoutManager(container, rows=12, cols=12)
    panel = QWidget()

    manager.add_panel("test", panel, row=0, col=0, row_span=2, col_span=4)

    assert "test" in manager.panels
    assert manager.panels["test"].row == 0
    assert manager.panels["test"].col == 0
```

## Future Enhancements

### Short Term
1. **Integrate ResizeHandles with DraggablePanel**
   - Add resize handles to panel corners
   - Enable manual panel resizing via handles

2. **Enhanced Visual Feedback**
   - Smooth animations for panel movements
   - Better drop zone indicators
   - Panel dimension overlay during resize

3. **Keyboard Navigation**
   - Arrow keys to move focused panel
   - Tab to cycle through panels
   - Ctrl+Arrow to resize panels

### Long Term
1. **Floating Panels**
   - Allow panels to float as separate windows
   - Multi-monitor support

2. **Panel Grouping**
   - Create tabbed groups of panels
   - Collapsible panel groups

3. **Advanced Layout Features**
   - Workspace management (multiple named workspaces)
   - Layout templates
   - Cloud sync for layouts

4. **Accessibility**
   - Screen reader support
   - High contrast mode
   - Keyboard-only operation

## Known Limitations

1. **Resize Handles Not Integrated**: ResizeHandle widget is implemented but not yet integrated with DraggablePanel. Manual resizing currently happens through grid cell spanning only.

2. **Grid Cell Granularity**: The 12x12 grid provides good flexibility but may not suit all use cases. Users can adjust in settings.

3. **Layout Migration**: No automatic migration from old layouts to new format. First-time users will see default layout.

4. **Performance**: With many panels (>10), drag operations may lag on slower systems. Consider optimization for large panel counts.

## Configuration Files

### Config Location
- Main config: `~/.openpace/config.json`
- Layout file: `~/.openpace/panel_layouts.json`
- Presets directory: `~/.openpace/layout_presets/`

### Example Config Section
```json
{
  "ui": {
    "theme": "default",
    "default_window_width": 1400,
    "default_window_height": 900,
    "use_grid_layout": true,
    "save_panel_layouts": true,
    "panel_layouts": {
      "default": {
        "version": "1.0",
        "layout_mode": "vertical",
        ...
      }
    },
    "default_layout_mode": "vertical",
    "panel_min_height": 150,
    "panel_min_width": 200,
    "grid_rows": 12,
    "grid_cols": 12,
    "snap_to_grid": true
  }
}
```

## Troubleshooting

### Panels Not Dragging
- Check if panel is locked (lock icon in header)
- Verify `use_grid_layout` is enabled in config
- Ensure you're clicking the drag handle (⣿), not other header elements

### Layout Not Saving
- Check `save_panel_layouts` setting in config
- Verify write permissions for `~/.openpace/` directory
- Check logs for serialization errors

### Panels Overlapping
- This shouldn't happen in normal operation
- If it occurs, reset layout to default
- Check for corrupted layout file

### Application Crashes on Startup
- Delete `~/.openpace/panel_layouts.json`
- Set `use_grid_layout: false` in config
- Check logs for specific error

## Contributing

When contributing to this feature:

1. **Follow Existing Patterns**: Use the established signal/slot pattern for communication
2. **Add Unit Tests**: All new functionality should have tests
3. **Update Documentation**: Keep this file and docstrings up to date
4. **Consider Backward Compatibility**: Don't break existing layouts
5. **Test Both Modes**: Verify changes work with both grid and splitter modes

## License

This implementation is part of the OpenPace project and follows the same license terms.

## Acknowledgments

- Inspired by OSCAR's flexible panel layout
- Uses PyQt6's layout system as foundation
- Grid system inspired by CSS Grid and Bootstrap's 12-column grid
