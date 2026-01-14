# Quick Start Guide: Draggable Panels

## 5-Minute Quick Start

### For Users

#### 1. Enable the Feature (First Time)
The grid layout system is **enabled by default**. If you need to toggle it:

1. Open OpenPace
2. Go to **View → Layout → Grid Settings...**
3. Check **"Use grid layout system"**
4. Restart the application

#### 2. Move a Panel
1. Look for the drag handle (⣿) on the left side of any panel header
2. Click and hold the drag handle
3. Drag the panel to a new position
4. Release to drop - the panel will snap to the grid

#### 3. Switch Layout Modes

**Quick Keyboard Shortcuts:**
- `Ctrl+1` - Vertical layout (all panels stacked)
- `Ctrl+2` - Horizontal layout (panels side-by-side)
- `Ctrl+3` - Free grid layout (position anywhere)

**Via Menu:**
- Go to **View → Layout → Layout Mode** and select your preference

#### 4. Save Your Layout
Once you've arranged panels the way you like:
- Press `Ctrl+Shift+S` OR
- Go to **View → Layout → Save Layout As...**
- Enter a name (e.g., "My Workspace")
- Click OK

Your layout is saved and will persist across sessions!

#### 5. Load a Saved Layout
- Press `Ctrl+Shift+L` OR
- Go to **View → Layout → Load Layout...**
- Select your saved layout
- Click OK

---

## Common Tasks

### Reset Layout to Default
If you mess up your layout:
1. **View → Layout → Reset to Default**
2. Confirm
3. Layout resets based on current mode

### Adjust Grid Settings
1. **View → Layout → Grid Settings...**
2. Adjust:
   - Grid size (rows/columns)
   - Minimum panel sizes
   - Snap-to-grid behavior
   - Auto-save toggle
3. Click OK

### Hide/Show Panels
- **View → Panels** → Check/uncheck panels
- Hidden panels don't take up space in the layout

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Vertical Layout | `Ctrl+1` |
| Horizontal Layout | `Ctrl+2` |
| Free Grid Layout | `Ctrl+3` |
| Save Layout As... | `Ctrl+Shift+S` |
| Load Layout... | `Ctrl+Shift+L` |

---

## For Developers

### Quick Integration Example

```python
from PyQt6.QtWidgets import QWidget, QLabel
from openpace.gui.widgets.draggable_panel import DraggablePanel
from openpace.gui.layouts import GridLayoutManager, LayoutMode

# 1. Create your content widget
my_widget = QLabel("Panel Content")

# 2. Wrap it in a DraggablePanel
panel = DraggablePanel(
    panel_id="my_panel",
    title="My Custom Panel",
    content_widget=my_widget
)

# 3. Create grid container and manager
container = QWidget()
grid_manager = GridLayoutManager(container, rows=12, cols=12)

# 4. Add panel to grid
grid_manager.add_panel(
    panel_id="my_panel",
    widget=panel,
    row=0,        # Starting row
    col=0,        # Starting column
    row_span=3,   # Height in grid cells
    col_span=6    # Width in grid cells
)

# 5. Connect drag signals (optional)
panel.drag_ended.connect(lambda panel_id, pos:
    print(f"Panel {panel_id} moved to {pos}")
)
```

### Adding a New Panel to TimelineView

```python
# In TimelineView.__init__ or _init_grid_layout

# 1. Create your widget
self.my_widget = MyCustomWidget()

# 2. Create draggable panel
self.my_panel = DraggablePanel(
    panel_id="my_custom_panel",
    title="My Custom Panel",
    content_widget=self.my_widget
)

# 3. Connect signals
self.my_panel.visibility_changed.connect(self.my_custom_visibility_changed.emit)
self.my_panel.drag_started.connect(self._on_drag_started)
self.my_panel.drag_moved.connect(self._on_drag_moved)
self.my_panel.drag_ended.connect(self._on_drag_ended)

# 4. Store reference
self.panels['my_custom_panel'] = self.my_panel

# 5. Add to grid (in _set_default_vertical_layout)
self.grid_manager.add_panel(
    "my_custom_panel",
    self.my_panel,
    row=12, col=0,
    row_span=2, col_span=12
)

# 6. Update menu (in MainWindow._create_menu_bar)
self.my_custom_action = QAction("My Custom Panel", self)
self.my_custom_action.setCheckable(True)
self.my_custom_action.setChecked(True)
self.my_custom_action.triggered.connect(
    lambda checked: self.timeline_view.toggle_panel('my_custom_panel', checked)
)
panels_menu.addAction(self.my_custom_action)
```

### Programmatic Layout Management

```python
from openpace.gui.layouts import LayoutSerializer

# Save current layout
layout_data = timeline_view.save_layout()
LayoutSerializer.save_preset(layout_data, "my_preset")

# Load a layout
layout_data = LayoutSerializer.load_preset("my_preset")
timeline_view.restore_layout(layout_data)

# Switch layout mode
from openpace.gui.layouts import LayoutMode
timeline_view.set_layout_mode(LayoutMode.FREE_GRID)

# Get current mode
current_mode = timeline_view.get_layout_mode()
```

---

## Troubleshooting

### Problem: Panels won't move
**Solution:**
- Check if panel is locked (shouldn't be by default)
- Verify you're clicking the drag handle (⣿) icon
- Ensure grid layout is enabled in settings

### Problem: Layout isn't saving
**Solution:**
- Check Grid Settings → "Automatically save layout changes"
- Verify file permissions for `~/.openpace/`
- Check application logs for errors

### Problem: Panels overlap after loading
**Solution:**
- Reset layout: **View → Layout → Reset to Default**
- If persists, delete `~/.openpace/panel_layouts.json`
- Restart application

### Problem: Grid layout not working at all
**Solution:**
- Check **View → Layout → Grid Settings...**
- Ensure "Use grid layout system" is checked
- Restart application after enabling

---

## Tips & Tricks

### Tip 1: Create Multiple Workspaces
Save different layouts for different workflows:
- "Analysis" - Focus on charts
- "Data Entry" - Settings panel prominent
- "Overview" - All panels visible

### Tip 2: Use Keyboard Shortcuts
Master the shortcuts for quick layout switching:
- `Ctrl+1/2/3` for layout modes
- `Ctrl+Shift+S/L` for save/load

### Tip 3: Start with a Template
Begin with Vertical or Horizontal mode, then:
1. Switch to Free Grid (`Ctrl+3`)
2. Customize positions
3. Save as preset

### Tip 4: Minimum Panel Sizes
If panels feel too small:
1. **View → Layout → Grid Settings...**
2. Increase "Minimum Width" and "Minimum Height"
3. Click OK

### Tip 5: Fine-Tune Grid Granularity
Default 12×12 grid might be too coarse or fine:
1. **Grid Settings** → Adjust rows/columns
2. Higher numbers = finer positioning control
3. Lower numbers = simpler, faster positioning

---

## Configuration Files

### Main Config
`~/.openpace/config.json`
```json
{
  "ui": {
    "use_grid_layout": true,
    "save_panel_layouts": true,
    "default_layout_mode": "vertical",
    "grid_rows": 12,
    "grid_cols": 12,
    "snap_to_grid": true,
    "panel_min_height": 150,
    "panel_min_width": 200
  }
}
```

### Layout Storage
`~/.openpace/panel_layouts.json` - Current layout
`~/.openpace/layout_presets/*.json` - Saved presets

---

## Video Tutorial (Coming Soon)

*(Placeholder for future video tutorial link)*

---

## Get Help

- 📖 Full Documentation: See `DRAGGABLE_PANELS_IMPLEMENTATION.md`
- 🐛 Report Issues: GitHub Issues
- 💬 Discuss: GitHub Discussions

---

## What's Next?

Planned enhancements:
- [ ] Resize handles on panel corners
- [ ] Panel grouping and tabs
- [ ] Floating panel windows
- [ ] Multi-monitor support
- [ ] Cloud sync for layouts

---

*Last Updated: January 2026*
