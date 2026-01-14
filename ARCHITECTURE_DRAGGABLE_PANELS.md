# Architecture: Draggable Panels System

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MainWindow                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    View Menu                               │  │
│  │  • Layout Mode (Vertical/Horizontal/Free Grid)            │  │
│  │  • Save/Load Layout                                       │  │
│  │  • Grid Settings                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   TimelineView                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │           GridLayoutManager (12×12 grid)            │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │        DraggablePanel (Battery)              │  │  │  │
│  │  │  │  [⣿ Battery Voltage       [▼] [✕]]          │  │  │  │
│  │  │  │  ┌─────────────────────────────────────────┐ │  │  │  │
│  │  │  │  │     BatteryTrendWidget                  │ │  │  │  │
│  │  │  │  └─────────────────────────────────────────┘ │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │    DraggablePanel (Atrial Impedance)         │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │    DraggablePanel (Vent Impedance)           │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │    DraggablePanel (Arrhythmia Burden)        │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │    DraggablePanel (Device Settings)          │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │   LayoutSerializer           │
               │  • save_to_file()            │
               │  • load_from_file()          │
               │  • save_preset()             │
               │  • load_preset()             │
               └──────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │  Configuration & Storage               │
         │  • ~/.openpace/config.json             │
         │  • ~/.openpace/panel_layouts.json      │
         │  • ~/.openpace/layout_presets/*.json   │
         └────────────────────────────────────────┘
```

## Component Hierarchy

```
QMainWindow (MainWindow)
└── QWidget (TimelineView)
    ├── QWidget (PatientSelectorWidget)
    └── QWidget (grid_container)
        └── GridLayoutManager
            ├── DraggablePanel (battery)
            │   └── CollapsiblePanel
            │       ├── Header (with drag handle ⣿)
            │       └── BatteryTrendWidget
            ├── DraggablePanel (atrial_impedance)
            │   └── CollapsiblePanel
            │       └── ImpedanceTrendWidget
            ├── DraggablePanel (vent_impedance)
            │   └── CollapsiblePanel
            │       └── ImpedanceTrendWidget
            ├── DraggablePanel (burden)
            │   └── CollapsiblePanel
            │       └── BurdenWidget
            └── DraggablePanel (settings)
                └── CollapsiblePanel
                    └── SettingsPanel
```

## Data Flow

### 1. Drag Operation Flow

```
User drags panel handle
        │
        ▼
DraggablePanel.mousePressEvent()
        │
        ├─► emit drag_started(panel_id, position)
        │
        ▼
TimelineView._on_drag_started()
        │
        ├─► Set dragging_panel_id
        └─► Enable mouse tracking
        │
        ▼
DraggablePanel.mouseMoveEvent()
        │
        ├─► emit drag_moved(panel_id, position)
        │
        ▼
TimelineView._on_drag_moved()
        │
        ├─► GridLayoutManager.get_drop_zone(position)
        ├─► Set drop_zone_rect
        └─► trigger repaint (shows blue overlay)
        │
        ▼
DraggablePanel.mouseReleaseEvent()
        │
        ├─► emit drag_ended(panel_id, position)
        │
        ▼
TimelineView._on_drag_ended()
        │
        ├─► GridLayoutManager.move_panel(panel_id, row, col)
        ├─► Clear drop_zone_rect
        └─► _schedule_layout_save()
        │
        ▼
(after 1 second debounce)
        │
        ▼
TimelineView._save_layout_to_file()
        │
        ├─► GridLayoutManager.serialize_layout()
        ├─► LayoutSerializer.save_to_file()
        └─► Config.save_to_file()
```

### 2. Layout Persistence Flow

```
Application Startup
        │
        ▼
TimelineView.__init__()
        │
        ├─► Create GridLayoutManager
        ├─► Create DraggablePanels
        ├─► Set default layout (vertical)
        │
        ▼
TimelineView._load_layout_from_file()
        │
        ├─► LayoutSerializer.load_from_file()
        │   └─► Read ~/.openpace/panel_layouts.json
        │
        ├─► LayoutSerializer.validate_layout()
        │
        └─► GridLayoutManager.restore_layout()
            └─► Position each panel according to saved data
```

### 3. Layout Mode Change Flow

```
User selects layout mode (Menu or Ctrl+1/2/3)
        │
        ▼
MainWindow._set_vertical_layout() [or horizontal/free_grid]
        │
        ▼
TimelineView.set_orientation() [if grid enabled]
        │
        ├─► Map Qt.Orientation to LayoutMode
        │
        ▼
TimelineView.set_layout_mode(mode)
        │
        ▼
GridLayoutManager.set_mode(mode)
        │
        ├─► Apply mode constraints
        │   ├─► VERTICAL: All panels full width, stacked
        │   ├─► HORIZONTAL: Panels in columns
        │   └─► FREE_GRID: No constraints
        │
        ├─► _rebuild_layout()
        │
        └─► emit layout_changed signal
        │
        ▼
TimelineView._on_layout_changed()
        │
        └─► _schedule_layout_save()
```

## Class Diagram

```
┌──────────────────────┐
│   CollapsiblePanel   │
│  (existing class)    │
│ ──────────────────── │
│ + title: str         │
│ + content_widget     │
│ + toggle_collapse()  │
│ + hide_panel()       │
│ + show_panel()       │
└──────────────────────┘
          △
          │ extends
          │
┌──────────────────────┐
│   DraggablePanel     │
│  (NEW)               │
│ ──────────────────── │
│ + panel_id: str      │
│ + is_locked: bool    │
│ + is_dragging: bool  │
│ ──────────────────── │
│ + set_locked(bool)   │
│ + mousePressEvent()  │
│ + mouseMoveEvent()   │
│ + mouseReleaseEvent()│
│ ──────────────────── │
│ • drag_started       │
│ • drag_moved         │
│ • drag_ended         │
│ • resize_requested   │
└──────────────────────┘

┌──────────────────────┐
│  GridLayoutManager   │
│  (NEW)               │
│ ──────────────────── │
│ + rows: int          │
│ + cols: int          │
│ + mode: LayoutMode   │
│ + panels: Dict       │
│ ──────────────────── │
│ + add_panel()        │
│ + move_panel()       │
│ + resize_panel()     │
│ + get_drop_zone()    │
│ + serialize_layout() │
│ + restore_layout()   │
│ ──────────────────── │
│ • layout_changed     │
└──────────────────────┘

┌──────────────────────┐
│   LayoutSerializer   │
│  (NEW - Static)      │
│ ──────────────────── │
│ + serialize()        │
│ + deserialize()      │
│ + save_to_file()     │
│ + load_from_file()   │
│ + save_preset()      │
│ + load_preset()      │
│ + validate_layout()  │
└──────────────────────┘

┌──────────────────────┐
│     TimelineView     │
│  (MODIFIED)          │
│ ──────────────────── │
│ + grid_manager       │
│ + use_grid_layout    │
│ + panels: Dict       │
│ ──────────────────── │
│ + set_layout_mode()  │
│ + save_layout()      │
│ + restore_layout()   │
│ + _on_drag_started() │
│ + _on_drag_moved()   │
│ + _on_drag_ended()   │
└──────────────────────┘
```

## Signal Flow Diagram

```
DraggablePanel                TimelineView              GridLayoutManager
      │                             │                           │
      ├─drag_started────────────────>│                          │
      │                             │                           │
      ├─drag_moved──────────────────>│──get_drop_zone()─────>  │
      │                             │<────(row, col)──────────  │
      │                             │                           │
      ├─drag_ended──────────────────>│                          │
      │                             │──move_panel()────────────>│
      │                             │                           │
      │                             │<────layout_changed────────┤
      │                             │                           │
      │                             ├─_schedule_layout_save()   │
      │                             │                           │
      │         (1 second later)    │                           │
      │                             │                           │
      │                             ├─serialize_layout()────────>│
      │                             │<────layout_data───────────┤
      │                             │                           │
      │                             └─> LayoutSerializer        │
      │                                 .save_to_file()         │
```

## State Machine: Panel Drag Operation

```
     ┌─────────┐
     │  IDLE   │◄────────────────────────┐
     └────┬────┘                         │
          │                              │
   [Mouse Press on Handle]               │
          │                              │
          ▼                              │
   ┌──────────┐                          │
   │ DRAGGING │                          │
   └────┬─────┘                          │
        │                                │
        ├─[Mouse Move]──► Update Position│
        │       │                        │
        │       └─> Show Drop Zone       │
        │                                │
        │                                │
   [Mouse Release]                       │
        │                                │
        ▼                                │
   ┌─────────┐                           │
   │ DROPPED │───[Move Complete]─────────┘
   └─────────┘
```

## Layout Mode State Diagram

```
        ┌──────────────┐
   ┌───►│   VERTICAL   │
   │    │  (Stacked)   │◄────┐
   │    └──────┬───────┘     │
   │           │             │
   │    [Ctrl+1/Menu]        │
   │           │             │
   │    ┌──────▼───────┐     │
   │    │  HORIZONTAL  │     │
   └────┤(Side-by-Side)│     │
        └──────┬───────┘     │
               │             │
        [Ctrl+2/Menu]        │
               │             │
        ┌──────▼───────┐     │
        │  FREE_GRID   │     │
        │ (Anywhere)   │─────┘
        └──────────────┘
         [Ctrl+3/Menu]
```

## Configuration Hierarchy

```
OpenPaceConfig
└── UIConfig
    ├── theme
    ├── default_window_width
    ├── default_window_height
    └── [LAYOUT SETTINGS]
        ├── use_grid_layout ────────► Enable/disable feature
        ├── save_panel_layouts ─────► Auto-save toggle
        ├── panel_layouts ──────────► Stored layout data
        ├── default_layout_mode ────► Startup mode
        ├── panel_min_height ───────► Min panel height (px)
        ├── panel_min_width ────────► Min panel width (px)
        ├── grid_rows ──────────────► Grid row count
        ├── grid_cols ──────────────► Grid column count
        └── snap_to_grid ───────────► Snap behavior
```

## File System Layout

```
~/.openpace/
├── config.json ─────────────────► Main configuration
│   └── ui.panel_layouts.default ► Current layout (also here)
│
├── panel_layouts.json ──────────► Current active layout
│
└── layout_presets/ ─────────────► User-saved presets
    ├── My Workspace.json
    ├── Analysis View.json
    └── Data Entry.json
```

## Memory Structure

### GridLayoutManager.panels Dictionary
```python
{
    "battery": PanelInfo(
        widget=<DraggablePanel>,
        row=0, col=0,
        row_span=2, col_span=12,
        visible=True,
        collapsed=False
    ),
    "atrial_impedance": PanelInfo(...),
    "vent_impedance": PanelInfo(...),
    "burden": PanelInfo(...),
    "settings": PanelInfo(...)
}
```

### Serialized Layout Structure
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
  }
}
```

## Integration Points

### 1. With Existing Code
- Extends CollapsiblePanel (inheritance)
- Uses existing panel widgets as content
- Integrates with existing menu system
- Preserves existing QSplitter as fallback

### 2. With Configuration System
- Reads from UIConfig on startup
- Writes to config on changes
- Validates config values
- Provides defaults if missing

### 3. With File System
- Reads/writes JSON files
- Creates directories as needed
- Handles missing files gracefully
- Validates file content

## Performance Characteristics

### Time Complexity
- Panel lookup: O(1) - dictionary access
- Drop zone calculation: O(1) - simple arithmetic
- Panel movement: O(n) - rebuild layout (n = panel count)
- Serialization: O(n) - iterate all panels
- Deserialization: O(n) - restore all panels

### Space Complexity
- Panel storage: O(n) - one PanelInfo per panel
- Layout data: O(n) - proportional to panel count
- Configuration: O(1) - fixed size settings

### Optimization Points
- Debounced auto-save (prevents excessive writes)
- Lazy layout restoration (only when needed)
- Minimal redraws during drag (only drop zone)
- Efficient grid calculations (cached cell sizes)

## Error Handling Strategy

```
Operation Error ──┐
                  │
                  ▼
        ┌─────────────────┐
        │  Log Error      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Show User      │
        │  Message?       │
        └────┬────────┬───┘
             │        │
         Yes │        │ No
             │        │
             ▼        ▼
    ┌───────────┐  ┌──────────┐
    │ QMessage  │  │ Continue │
    │ Box       │  │ Silently │
    └───────────┘  └──────────┘
             │        │
             └────┬───┘
                  │
                  ▼
        ┌─────────────────┐
        │ Graceful        │
        │ Degradation     │
        └─────────────────┘
        (Use defaults/
         fallback mode)
```

## Threading Model

```
┌─────────────────┐
│   Main Thread   │ ◄── All UI operations
│   (Qt GUI)      │     (drag, paint, menu)
└────────┬────────┘
         │
         │ QTimer.timeout
         │ (debounced)
         │
         ▼
┌─────────────────┐
│   Main Thread   │ ◄── File I/O operations
│   (Save/Load)   │     (JSON read/write)
└─────────────────┘

Note: All operations are synchronous on main thread.
No worker threads currently used.
Future: Consider async save for large layouts.
```

---

*This architecture diagram provides a comprehensive view of the draggable panels system structure, data flow, and integration points.*
