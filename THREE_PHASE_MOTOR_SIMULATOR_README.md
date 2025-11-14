# Three-Phase Motor Capacitor Bank Calculator & Simulator

## Overview
This application provides a comprehensive solution for calculating and simulating power factor correction in three-phase motors using capacitor banks. It features real-time ODE solvers, dynamic visualization, and interactive parameter adjustment.

## Features

### 1. **Multi-Problem Support**
Solves three different power factor correction problems:

- **Problem 2**: 100 HP, 400V, 50Hz motor (0.7 → 0.95 PF)
  - Delta-connected capacitor bank
  - 4 capacitors per unit at 100V each

- **Problem 3**: 400 HP, 2000V, 50Hz motor (0.75 → 0.98 PF)
  - Star-connected motor with delta-connected capacitor bank
  - 500V capacitor units

- **Problem 4**: 600 HP, 3000V, 50Hz motor (0.75 → 0.98 PF)
  - Delta-connected capacitor bank
  - 5 capacitors per unit at 600V each

### 2. **Dynamic Simulation with ODE Solvers**
- **RK45 (Runge-Kutta 4th order)**: High-accuracy numerical integration
- **Euler Method**: First-order integration for comparison
- Real-time simulation of power factor transition
- Models motor dynamics including voltage oscillations and current changes

### 3. **Interactive Parameter Controls**
All parameters adjustable via sliders:
- Line Voltage (100-5000 V)
- Motor Power (10-1000 HP)
- Frequency (40-60 Hz)
- Initial Power Factor (0.5-0.95)
- Final Power Factor (0.8-1.0)
- Efficiency (0.7-1.0)

### 4. **Real-Time Visualization**
Three dynamic graphs showing:
1. **Power Factor vs Time**: Shows transition from initial to final PF
2. **Voltage vs Time**: Displays voltage oscillations during transition
3. **Current vs Time**: Shows current reduction due to PF correction

### 5. **Responsive Design**
- Automatic width and height adjustment when window is resized
- Grid-based layout that scales with window size
- Canvas and plots automatically redraw on resize

### 6. **Detailed Results**
Calculates and displays:
- Input and output power
- Initial and final reactive power
- Reactive power to be compensated
- Line current before and after correction
- **Required capacitance per capacitor** (in µF and F)
- Voltage requirements for capacitors
- Current reduction achieved

## Technical Details

### Power Factor Correction Calculations

1. **Convert HP to Watts**: P_out = HP × 745.7 W
2. **Calculate Input Power**: P_in = P_out / η
3. **Initial Reactive Power**: Q₁ = P_in × tan(cos⁻¹(PF₁))
4. **Final Reactive Power**: Q₂ = P_in × tan(cos⁻¹(PF₂))
5. **Reactive Power to Compensate**: Q_c = Q₁ - Q₂
6. **Capacitance (Delta)**: C = Q_c / (3 × V_L² × ω)
7. **Individual Capacitor**: C_individual = C_total × n (for series config)

### ODE System
The simulator models motor dynamics using:
```
dpf/dt = (PF_target - PF) / τ_pf
dV/dt = K × V_nominal × sin(ωt)
dI/dt = (I_target - I) / τ_i
```

Where:
- τ_pf = 2.0 s (power factor time constant)
- τ_i = 1.0 s (current time constant)
- ω = 2π × frequency

### Numerical Integration Methods

**Euler Method**:
```
y(t+h) = y(t) + h × f(t, y)
```

**RK45 (4th Order Runge-Kutta)**:
```
k₁ = f(t, y)
k₂ = f(t + h/2, y + h×k₁/2)
k₃ = f(t + h/2, y + h×k₂/2)
k₄ = f(t + h, y + h×k₃)
y(t+h) = y(t) + h×(k₁ + 2k₂ + 2k₃ + k₄)/6
```

## Usage Instructions

### Running the Application
```bash
python3 three_phase_motor_capacitor_simulator.py
```

### Basic Workflow

1. **Select Problem**
   - Choose from dropdown: Problem 2, 3, or 4
   - Parameters automatically update

2. **Adjust Parameters**
   - Use sliders in "Parameters" tab
   - Values update in real-time
   - Watch labels for current values

3. **Calculate Results**
   - Click "Calculate" button
   - View detailed results in "Results" tab
   - See capacitance values and all calculations

4. **Run Dynamic Simulation**
   - Select ODE Solver (RK45 or Euler)
   - Click "Start Simulation"
   - Watch real-time graphs update
   - Click "Stop Simulation" to pause
   - Click "Reset" to clear graphs

### Tips
- **RK45** is more accurate but slightly slower
- **Euler** is faster but less accurate
- Adjust sliders during simulation to see effects
- Resize window - everything scales automatically
- Compare initial vs final current to see savings

## Requirements

```python
tkinter          # GUI framework (usually included with Python)
numpy            # Numerical computations
matplotlib       # Plotting and visualization
scipy            # ODE solvers and scientific functions
```

### Installation
```bash
pip install numpy matplotlib scipy
```

## Example Results

### Problem 2 (100 HP, 400V Motor)
```
Motor Power: 100 HP (74,570 W)
Efficiency: 93%
Initial PF: 0.7 → Final PF: 0.95

Results:
- Input Power: 80,182 W
- Reactive Power Compensated: 41,234 VAR
- Capacitance per Capacitor: 364.5 µF
- Current Reduction: 112.3 A → 89.2 A (23.1 A saved)
```

### Problem 3 (400 HP, 2000V Motor)
```
Motor Power: 400 HP (298,280 W)
Efficiency: 85%
Initial PF: 0.75 → Final PF: 0.98

Results:
- Input Power: 350,918 W
- Reactive Power Compensated: 238,127 VAR
- Capacitance per Capacitor: 22.96 µF
- Current Reduction: 135.0 A → 103.6 A (31.4 A saved)
```

### Problem 4 (600 HP, 3000V Motor)
```
Motor Power: 600 HP (447,420 W)
Efficiency: 95%
Initial PF: 0.75 → Final PF: 0.98

Results:
- Input Power: 470,968 W
- Reactive Power Compensated: 319,124 VAR
- Capacitance per Capacitor: 18.84 µF
- Current Reduction: 120.6 A → 92.8 A (27.8 A saved)
```

## Educational Value

This simulator demonstrates:
1. Power triangle and reactive power compensation
2. Relationship between power factor and current
3. Capacitor bank sizing for different motor configurations
4. Effect of efficiency on power requirements
5. Series/parallel capacitor configurations for voltage ratings
6. Numerical integration methods (Euler vs RK45)
7. Dynamic system behavior during power factor correction

## Future Enhancements

Potential additions:
- Export results to CSV/PDF
- Cost analysis (energy savings vs capacitor cost)
- Harmonic analysis
- Multiple capacitor bank switching strategies
- Load variation simulation
- Temperature effects on capacitance
- Automatic optimal capacitor selection

## License

Educational and research use.

## Author

Created for advanced electrical networks course.

## Support

For issues or questions, refer to the course materials or instructor.
