# Quick Start Guide - Three-Phase Motor Capacitor Simulator

## Installation

```bash
# Install dependencies
pip install -r requirements_motor_simulator.txt

# Or install manually
pip install numpy matplotlib scipy
```

## Running the Simulator

### Method 1: Using the launch script
```bash
./run_motor_simulator.sh
```

### Method 2: Direct Python execution
```bash
python3 three_phase_motor_capacitor_simulator.py
```

### Method 3: Run verification tests first
```bash
# Test calculations without GUI
python3 test_motor_simulator.py

# Then launch GUI
python3 three_phase_motor_capacitor_simulator.py
```

## Quick User Guide

### Step 1: Select a Problem
- Use the dropdown menu at the top: "Problem 2", "Problem 3", or "Problem 4"
- Each problem has different motor specifications

### Step 2: Adjust Parameters (Optional)
- Click on "Parameters" tab on the left
- Use sliders to adjust:
  - Line Voltage
  - Motor Power
  - Frequency
  - Initial Power Factor
  - Final Power Factor
  - Efficiency

### Step 3: Calculate Results
- Click the **"Calculate"** button
- Switch to "Results" tab to see detailed calculations
- Key result: **Capacitance of each capacitor** in µF

### Step 4: Run Dynamic Simulation
1. Select ODE Solver: **RK45** (recommended) or **Euler**
2. Click **"Start Simulation"**
3. Watch the real-time graphs:
   - Power Factor transition
   - Voltage oscillations
   - Current reduction
4. Click **"Stop Simulation"** to pause
5. Click **"Reset"** to clear and start over

## Understanding the Results

### Power Factor Correction
The simulator calculates the capacitor bank needed to improve the motor's power factor from an initial lagging value to a higher target value.

### Key Outputs
1. **Reactive Power to Compensate (Qc)**: Amount of reactive power the capacitors must supply
2. **Capacitance per Capacitor**: The actual capacitance value needed for each capacitor unit
3. **Current Reduction**: How much the line current decreases after correction
4. **Energy Savings**: Lower current means reduced losses and smaller cables

### Example: Problem 2
```
100 HP, 400V motor
Initial PF: 0.7 → Final PF: 0.95

Result:
- Each capacitor: 1470.8 µF
- Current reduction: 43.51 A (26% reduction)
- 4 capacitors in series per unit
```

## Understanding the Graphs

### Graph 1: Power Factor vs Time
- Blue line: Current power factor
- Red dashed line: Initial power factor (0.7, 0.75)
- Green dashed line: Target power factor (0.95, 0.98)
- Shows smooth transition over ~10 seconds

### Graph 2: Voltage vs Time
- Shows small oscillations around nominal voltage
- Demonstrates voltage stability during transition
- Realistic 50 Hz oscillation pattern

### Graph 3: Current vs Time
- Shows current decreasing as power factor improves
- Lower current = less power loss in cables
- Demonstrates energy efficiency gain

## Solver Comparison

### RK45 (Runge-Kutta 4th Order)
- **Accuracy**: Very high
- **Speed**: Slightly slower
- **Best for**: Final results, presentations
- **Math**: 4th order method with adaptive step size

### Euler Method
- **Accuracy**: Good for this application
- **Speed**: Faster
- **Best for**: Quick exploration, learning
- **Math**: 1st order method (simplest)

## Tips and Tricks

1. **Resize Window**: Everything scales automatically - try it!

2. **Compare Solvers**:
   - Run simulation with RK45
   - Click Reset
   - Change to Euler
   - Run again and compare

3. **Explore Parameter Effects**:
   - Increase initial PF → less capacitance needed
   - Increase voltage → less capacitance needed
   - Increase power → more capacitance needed

4. **Real-time Adjustment**:
   - Start simulation
   - Move sliders while running
   - See immediate effects (then recalculate)

5. **Export Results**:
   - Select all text in Results tab (Ctrl+A)
   - Copy (Ctrl+C)
   - Paste into document

## Troubleshooting

### "ModuleNotFoundError: No module named 'numpy'"
```bash
pip install numpy matplotlib scipy
```

### "TclError" or GUI doesn't show
- Make sure you're running in an environment with display support
- For remote servers, use X11 forwarding or VNC

### Simulation freezes
- Click "Stop Simulation"
- Click "Reset"
- Restart simulation

### Results seem wrong
- Run test script first: `python3 test_motor_simulator.py`
- Verify calculations match expected values
- Check parameter values in sliders

## Educational Use

This simulator is perfect for:
- Understanding power factor correction concepts
- Comparing numerical integration methods
- Visualizing dynamic system behavior
- Homework problem verification
- Lab demonstrations
- Self-study and exploration

## Technical Details

### Calculation Method
Based on standard power engineering formulas:
1. Convert HP to Watts (1 HP = 745.7 W)
2. Account for efficiency losses
3. Calculate reactive power using power triangle
4. Size capacitor bank for delta connection
5. Adjust for series/parallel capacitor configuration

### ODE System
Models motor as dynamic system:
- Power factor transition (exponential approach)
- Voltage oscillations (sinusoidal at line frequency)
- Current adjustment (follows power factor change)

## Files in This Package

- `three_phase_motor_capacitor_simulator.py` - Main application (1000+ lines)
- `test_motor_simulator.py` - Calculation verification
- `THREE_PHASE_MOTOR_SIMULATOR_README.md` - Detailed documentation
- `QUICKSTART_MOTOR_SIMULATOR.md` - This file
- `requirements_motor_simulator.txt` - Python dependencies
- `run_motor_simulator.sh` - Launch script

## Need Help?

Refer to:
1. This quickstart guide
2. Full README: `THREE_PHASE_MOTOR_SIMULATOR_README.md`
3. Run tests: `python3 test_motor_simulator.py`
4. Check calculations manually using formulas in README

## Next Steps

After mastering the basics:
1. Try all three problems
2. Experiment with extreme parameter values
3. Compare RK45 vs Euler accuracy
4. Calculate cost savings from current reduction
5. Explore different capacitor configurations

---

**Enjoy exploring three-phase power factor correction!**
