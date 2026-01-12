# Plugin Switching Logic Analysis

## Current Issues Found

### 1. **Redundant Layout Clearing**
- Lines 227-228: Clear layout at start of function
- Lines 235-236: Clear layout again if `pluginChosen_motion == False`
- **Problem**: Unnecessary double clearing, wastes cycles

### 2. **Scanner Object Recreation**
- Line 241 & 316: Creates new Scanner object when plugin first connects
- **Problem**: Destroys and recreates controllers, loses state
- **Why**: Trying to swap plugin while preserving other controller

### 3. **Recursive Call Risk**
- Line 242: Calls `self.configure_motion(True)` recursively
- Line 318: Calls `self.configure_probe(True)` recursively
- **Problem**: Calls same method that's currently executing
- **Risk**: Could cause infinite recursion or unexpected state

### 4. **Controller Disconnect/Reconnect Logic**
- Line 324: Disconnects motion controller when probe connects
- Line 358: Tries to reconnect it later
- **Problem**: Fragile timing, can leave controllers in bad state

### 5. **Hard-Coded Array Indices**
- Lines 359-362: Uses indices [4], [5], [6], [7], [8]
- **Problem**: Breaks if plugin settings change order
- **Comment**: "need to refactor this to be more general" (line 363)

### 6. **Inconsistent State Variables**
- `self.motion_connected` set to False (line 243) after creating Scanner
- But needs to be True for later logic
- `pluginChosen_motion` vs `motion_connected` - confusing naming

### 7. **Signal Scope Not Passed Consistently**
- Sometimes signal_scope is passed, sometimes not
- Could lead to signal scope being None in some code paths

## Root Cause

The fundamental problem is **trying to do two things at once**:
1. Load a new plugin
2. Preserve the other controller

Current approach: Create brand new Scanner and pass old controller
- This works but is complex, error-prone, and loses state

## Proposed Solution

### Option 1: Plugin Hot-Swap (Cleaner)
Add methods to Scanner to swap plugins without recreation:

```python
class Scanner:
    def swap_probe_plugin(self, new_probe):
        """Swap probe controller without recreating Scanner"""
        old_connected = self._probe_controller.is_connected()
        if old_connected:
            self._probe_controller.disconnect()
        self._probe_controller = ProbeController(new_probe)

    def swap_motion_plugin(self, new_motion):
        """Swap motion controller without recreating Scanner"""
        old_connected = self._motion_controller.is_connected()
        if old_connected:
            self._motion_controller.disconnect()
        self._motion_controller = MotionController(new_motion)
```

### Option 2: Simplified Recreation (Safer)
Always recreate Scanner, but do it cleanly:

```python
def recreate_scanner_with_new_probe(self, new_probe_plugin):
    """Recreate scanner preserving motion controller"""
    # Save current motion state
    old_motion = self.scanner.scanner.motion_controller
    motion_was_connected = old_motion.is_connected()
    motion_settings = self._save_motion_settings() if motion_was_connected else None

    # Create new scanner
    self.scanner.scanner = Scanner(
        motion_controller=old_motion,
        signal_scope=self.signal_scope
    )

    # Restore motion settings if needed
    if motion_was_connected and motion_settings:
        self._restore_motion_settings(motion_settings)
```

### Option 3: Deferred Initialization
Don't initialize controllers until both plugins are selected:

```python
# Phase 1: Select plugins
selected_probe_plugin = None
selected_motion_plugin = None

# Phase 2: Create Scanner with both plugins
scanner = Scanner(
    probe_controller=ProbeController(selected_probe_plugin),
    motion_controller=MotionController(selected_motion_plugin),
    signal_scope=signal_scope
)
```

## Recommendation

Use **Option 1 (Plugin Hot-Swap)** because:
- ✅ No Scanner recreation needed
- ✅ Preserves all state
- ✅ Clean separation of concerns
- ✅ Easy to understand
- ✅ No recursive calls
- ✅ Signal scope always preserved
