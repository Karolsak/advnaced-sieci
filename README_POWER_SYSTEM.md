# Power System ODE Solver with Tkinter GUI

## Overview

This application provides a comprehensive simulation tool for **Example 8.10: Two Power Stations Operating in Parallel** from power system operation and control theory. It features dynamic simulation using ODE solvers, real-time visualization, and interactive parameter control.

## Features

### 1. **Dual ODE Solvers**
- **RK45 (Runge-Kutta 4-5th order)**: Adaptive step-size solver from SciPy for high accuracy
- **Euler Method**: Fixed step-size solver for comparison and educational purposes

### 2. **Dynamic Simulation**
- Real-time power system dynamics modeling
- Governor response simulation
- Frequency deviation tracking
- Tie-line power flow calculation

### 3. **Interactive Controls**
- **20+ Parameter Sliders** for complete system customization:
  - Station capacities (A: 75 MW, B: 200 MW)
  - Speed regulations (A: 4%, B: 2%)
  - Load conditions
  - Inertia constants
  - Damping coefficients
  - Simulation parameters

### 4. **Three Predefined Scenarios**
- **(a)** Load on each station = 100 MW
- **(b)** Loads: 50 MW @ Station A, 150 MW @ Station B
- **(c)** Load: 130 MW @ Station A only

### 5. **Comprehensive Visualization**
Six dynamic plots showing:
1. **Frequency Deviation** - System frequency response over time
2. **Power Output Station A** - Generation profile with capacity limits
3. **Power Output Station B** - Generation profile with capacity limits
4. **Tie-Line Power** - Interconnection power flow (A → B)
5. **Total Generation vs Load** - System balance verification
6. **Steady-State Analysis** - Bar chart of final power distribution

### 6. **Responsive Design**
- Automatic window resizing
- Adaptive plot scaling
- Scrollable parameter panel
- Grid-based responsive layout

## Problem Statement (Example 8.10)

Two power stations A and B of capacities **75 MW** and **200 MW** respectively, are operating in parallel and interconnected by a short transmission line. The generators have speed regulations of **4%** and **2%** respectively.

### Key Equations

**Speed Regulation:**
```
Speed Regulation = (N₀ - N) / N₀ = (f₀ - f) / f₀
```

**Power-Frequency Relationship:**
```
For Station A: P₁ = 75(1-f) / 0.04
For Station B: P₂ = 200(1-f) / 0.02
```

**Load Sharing:**
```
5.33 P₁ = P₂
P₁ + P₂ = Total Load
```

### Analytical Solutions

#### Scenario (a): Load on each station = 100 MW
- Total Load = 200 MW
- **P₁ = 31.60 MW**
- **P₂ = 168.40 MW**
- Tie-line power = 68.40 MW (from B to A)

#### Scenario (b): 50 MW @ A, 150 MW @ B
- Total Load = 200 MW
- **P₁ = 31.60 MW**
- **P₂ = 168.40 MW**
- Tie-line from A = -18.40 MW (118.40 MW from B to A)

#### Scenario (c): 130 MW @ A only
- Total Load = 130 MW
- **P₁ = 20.537 MW**
- **P₂ = 109.462 MW**
- Tie-line power = 109.462 MW (from B to A)

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually comes with Python)

### Install Dependencies
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install numpy scipy matplotlib
```

## Usage

### Running the Application
```bash
python3 power_system_ode_solver.py
```

### Using the Interface

1. **Select a Scenario**
   - Choose from the three radio button options
   - Loads will automatically adjust

2. **Adjust Parameters**
   - Use sliders to modify system parameters
   - Values update in real-time
   - Scroll down for more parameters

3. **Choose ODE Solver**
   - Select RK45 for accuracy
   - Select Euler for educational comparison

4. **Run Simulation**
   - Click "Start Simulation"
   - Watch dynamic plots update
   - Status bar shows progress and results

5. **Analyze Results**
   - View transient response in time-domain plots
   - Check steady-state values in bar chart
   - Compare with analytical solutions

6. **Reset**
   - Click "Reset" to restore default values

## System Dynamics Model

### State Variables
The ODE system models 5 state variables:
- `f`: System frequency deviation (p.u.)
- `P_A`: Power output of Station A (MW)
- `P_B`: Power output of Station B (MW)
- `Δf_A`: Frequency deviation at Station A
- `Δf_B`: Frequency deviation at Station B

### Differential Equations

**Governor Dynamics:**
```
dP_A/dt = (P_A_target - P_A) / τ_gov
dP_B/dt = (P_B_target - P_B) / τ_gov
```

**Frequency Dynamics:**
```
H df/dt = P_gen - P_load - D·f
```

where:
- `H` = Inertia constant (seconds)
- `D` = Damping coefficient
- `τ_gov` = Governor time constant (0.5 s)

## Technical Details

### File Structure
```
power_system_ode_solver.py
├── PowerSystemODESolver (Class)
│   ├── power_system_dynamics()    # ODE system definition
│   ├── solve_rk45()                # RK45 solver
│   ├── solve_euler()               # Euler solver
│   └── calculate_steady_state()    # Analytical solution
└── PowerSystemGUI (Class)
    ├── setup_gui()                 # Main GUI layout
    ├── setup_sliders()             # Parameter controls
    ├── setup_plots()               # Matplotlib integration
    ├── run_simulation()            # Simulation thread
    └── update_plots()              # Dynamic visualization
```

### Performance
- **RK45 Method**: Adaptive step size, 1000 evaluation points
- **Euler Method**: Fixed step size (default 0.01s)
- **Simulation Time**: Default 20 seconds, adjustable 5-60s
- **Threading**: Non-blocking UI during computation

### Validation
The steady-state results match the analytical solutions from Example 8.10:
- Scenario (a): ✓ P₁ = 31.60 MW, P₂ = 168.40 MW
- Scenario (b): ✓ P₁ = 31.60 MW, P₂ = 168.40 MW
- Scenario (c): ✓ P₁ = 20.537 MW, P₂ = 109.462 MW

## Troubleshooting

### Common Issues

**1. Import Error: No module named 'matplotlib'**
```bash
pip install matplotlib
```

**2. Tkinter not found**
- On Ubuntu/Debian: `sudo apt-get install python3-tk`
- On macOS: Tkinter comes with Python
- On Windows: Reinstall Python with tcl/tk option

**3. Plots not updating**
- Ensure matplotlib backend is compatible
- Try running with: `python3 -m tkinter` to test tkinter

**4. Window too small**
- Resize window manually
- Plots will auto-adjust

## Advanced Usage

### Customizing Parameters

**Increase System Inertia:**
- Higher inertia → slower frequency response
- Adjust "Inertia A" and "Inertia B" sliders

**Change Speed Regulation:**
- Lower regulation % → more power output variation
- Adjust "Regulation A" and "Regulation B" sliders

**Compare Solvers:**
- Run with RK45, note results
- Run with Euler, compare accuracy
- Decrease Euler dt for better accuracy

### Exploring Scenarios

**Unbalanced Loads:**
- Set different loads on each station
- Observe tie-line power flow direction

**Capacity Limits:**
- Increase load beyond combined capacity
- Watch frequency drop

**Governor Response:**
- Increase simulation time to 60s
- Observe settling behavior

## Educational Value

This tool demonstrates:
1. **Load-Frequency Control** in interconnected power systems
2. **Droop Control** mechanism via speed regulation
3. **Governor Dynamics** and primary frequency response
4. **Tie-Line Power Flow** in parallel operation
5. **ODE Solver Comparison** (RK45 vs Euler)
6. **Steady-State vs Transient** behavior

## References

- Example 8.10: Power System Operation and Control (Chapter 8)
- Load Frequency Control-II (Section 8.x)
- Speed regulation and droop characteristics
- Automatic generation control (AGC)

## License

This educational tool is provided as-is for learning purposes.

## Author

Created for power system analysis and control education.

---

**Version:** 1.0
**Last Updated:** 2025-11-13
**Python Version:** 3.7+
