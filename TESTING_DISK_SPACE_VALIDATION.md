# Testing Guide: Disk Space Validation

This guide provides safe testing procedures for the disk space validation feature.

---

## Overview

The disk space validation feature calculates the required storage for a scan pattern and validates it against available disk space **before** connecting the scan pattern. This prevents scan failures due to running out of storage mid-scan.

---

## Test 1: Normal Operation (Should Pass)

**Purpose:** Verify the validation works correctly when sufficient disk space is available.

### Steps:

1. **Start the application**
   ```bash
   python test_scanner_gui.py
   ```

2. **Connect Probe Controller**
   - Click "Configure" for Probe
   - Select a probe plugin
   - Configure and connect to probe

3. **Configure Scan Pattern (Small)**
   - Click "Configure" for Scan Pattern
   - Create a small pattern (e.g., 10×10 = 100 points)
   - Click "Connect" on scan pattern

4. **Expected Result:**
   - Console shows:
     ```
     ✓ Scan storage validation passed:
       Required: 1.25 MB
       Available: 50.00 GB
       Remaining after scan: 49.99 GB
     ```
   - Scan pattern connects successfully
   - UI shows post-connect settings

### What This Tests:
✅ Memory calculation logic
✅ Disk space query
✅ Normal connection flow
✅ Console feedback

---

## Test 2: Simulated Low Disk Space (Should Fail)

**Purpose:** Verify error handling when disk space is insufficient, WITHOUT actually filling your disk.

### Setup:

1. **Enable Debug Mode**

   Edit `test_scanner_gui.py` around line 49:

   ```python
   # Change these two lines:
   DEBUG_DISK_SPACE_TEST = True      # Was: False
   DEBUG_SIMULATED_DISK_SPACE_MB = 10  # Was: 100 (simulate only 10 MB available)
   ```

2. **Save the file** (the application will use these values next time it runs)

### Steps:

1. **Restart the application**
   ```bash
   python test_scanner_gui.py
   ```

2. **Connect Probe Controller** (same as Test 1)

3. **Configure Scan Pattern (Medium/Large)**
   - Create a pattern that will need more than 10 MB
   - Example: 100×100 = 10,000 points with 501 frequencies
   - This will need approximately 500-800 MB

4. **Try to Connect Scan Pattern**
   - Click "Connect"

5. **Expected Result:**

   **Console Output:**
   ```
   ⚠️  DEBUG MODE: Simulating 10 MB available disk space
      Actual available space: 50.00 GB
   Scan pattern connection aborted due to insufficient disk space
   ```

   **Error Dialog:**
   ```
   ╔═══════════════════════════════════════════╗
   ║     Insufficient Disk Space               ║
   ╠═══════════════════════════════════════════╣
   ║ The scan pattern requires more storage   ║
   ║ than available on disk.                  ║
   ║                                          ║
   ║ Scan Details:                            ║
   ║   • Number of scan points: 10,000        ║
   ║   • Required storage: 641.28 MB          ║
   ║   • Available storage: 10.00 MB          ║
   ║   • Shortage: 631.28 MB                  ║
   ║                                          ║
   ║ Please reduce the number of scan points  ║
   ║ or free up disk space.                   ║
   ╚═══════════════════════════════════════════╝
   ```

   - Scan pattern **remains in pre-connected state**
   - Can adjust settings and try again

### What This Tests:
✅ Error detection logic
✅ Error dialog display
✅ Pre-connected state preservation
✅ Human-readable size formatting
✅ Debug mode functionality

---

## Test 3: Edge Cases

### Test 3a: Probe Not Connected

1. **Configure scan pattern WITHOUT connecting probe first**
2. Try to connect scan pattern
3. **Expected:** Error message "Please connect to probe controller before configuring scan pattern."

### Test 3b: Large Scan Pattern

1. **Disable debug mode** (set `DEBUG_DISK_SPACE_TEST = False`)
2. Create a very large scan pattern (e.g., 1000×1000 = 1,000,000 points)
3. Try to connect
4. **Expected:**
   - If sufficient space: Shows large storage requirement (e.g., "64.12 GB") but allows connection
   - If insufficient space: Shows appropriate error

### Test 3c: Different S-Parameter Counts

Test with different probe plugins:
- **Single S-parameter** (1×1 VNA): Lower storage requirements
- **Four S-parameters** (4-port VNA): 4× storage requirements

### Test 3d: Different Frequency Counts

- **Low frequency points** (101 points): Lower storage
- **High frequency points** (5001 points): Higher storage

---

## Test 4: After Validation Passes

**Purpose:** Verify scan actually works after validation passes.

1. Use **small scan pattern** (10×10)
2. Validation should pass
3. Run actual scan with "Test Scan" button
4. **Expected:** Scan completes successfully, HDF5 file created

---

## Safety Margin Verification

The system adds a **10% safety margin** to prevent edge cases.

### Test:

1. Calculate expected size manually:
   ```
   S-parameters: 4
   Scan points: 100
   Frequencies: 501

   Storage = 4 × 100 × 501 × 16 bytes = 3,206,400 bytes
   Coordinates = 3 × 100 × 8 = 2,400 bytes
   Frequencies = 501 × 8 = 4,008 bytes
   Metadata = 50 KB = 51,200 bytes

   Total = 3,264,008 bytes ≈ 3.11 MB
   With 10% margin = 3.42 MB
   ```

2. Check console output matches calculation (within rounding)

---

## Disabling Debug Mode (IMPORTANT!)

**After testing, remember to disable debug mode:**

```python
# In test_scanner_gui.py, line ~49:
DEBUG_DISK_SPACE_TEST = False  # Back to False
DEBUG_SIMULATED_DISK_SPACE_MB = 100  # Restore default
```

**Why:** Leaving debug mode enabled will always simulate low disk space, causing false errors in production use.

---

## Troubleshooting

### Issue: Validation always fails even with debug mode off

**Solution:**
- Verify `DEBUG_DISK_SPACE_TEST = False`
- Check actual available disk space: `df -h` (Linux) or File Explorer (Windows)
- Verify save directory is correct in scan file settings

### Issue: Calculation seems incorrect

**Solution:**
- Check number of S-parameters: `probe_controller.get_channel_names()`
- Check number of frequencies: `probe_controller.get_xaxis_coords()`
- Check scan points: `len(scan_controller.matrix[0])`
- Verify complex128 = 16 bytes (8 real + 8 imag)

### Issue: Error dialog doesn't show

**Solution:**
- Check console output for error messages
- Verify tkinter messagebox is working
- Try running with elevated permissions if file access issues

---

## Quick Test Checklist

Use this checklist for regression testing:

- [ ] Test 1: Small scan pattern with sufficient space (should pass)
- [ ] Test 2: Debug mode with simulated low space (should fail gracefully)
- [ ] Test 3a: Probe not connected (should show error)
- [ ] Test 3b: Very large scan pattern (should calculate correctly)
- [ ] Test 4: Actual scan after validation (should complete)
- [ ] Debug mode disabled after testing
- [ ] Console output shows correct calculations
- [ ] Error dialog is user-friendly and informative

---

## Storage Calculation Reference

### Formula:

```python
# S-parameter data (complex128)
s_param_bytes = num_s_params × num_points × num_freqs × 16 bytes

# Coordinates (float64)
coords_bytes = 3 × num_points × 8 bytes

# Frequencies (float64)
freq_bytes = num_freqs × 8 bytes

# Metadata
metadata_bytes = 50 KB (estimate)

# Camera image (if present)
camera_bytes = 500 KB (estimate)

# Total with 10% safety margin
total = (s_param_bytes + coords_bytes + freq_bytes + metadata_bytes + camera_bytes) × 1.1
```

### Example Calculations:

| Scan Size | S-Params | Freqs | Storage Required |
|-----------|----------|-------|------------------|
| 10×10     | 4        | 501   | ~3.5 MB          |
| 100×100   | 4        | 501   | ~350 MB          |
| 500×500   | 4        | 501   | ~8.7 GB          |
| 1000×1000 | 4        | 501   | ~35 GB           |

---

## Production Use

Once testing is complete and debug mode is disabled, the feature will:

1. ✅ Automatically validate on every scan pattern connection attempt
2. ✅ Show error dialog if insufficient space
3. ✅ Keep scan pattern in pre-connected state on failure
4. ✅ Allow user to reduce scan points or free up space
5. ✅ Proceed normally if validation passes

**No user action required** - the validation runs automatically!

---

**Document Version:** 1.0
**Last Updated:** January 2026
