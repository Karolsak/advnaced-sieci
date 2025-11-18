"""
Advanced DC Shunt Motor Speed Control and Multi-Physics Simulation
Complete solution with Tkinter GUI, ODE solvers, and thermal analysis
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
from scipy.integrate import solve_ivp, odeint
from dataclasses import dataclass
import math
from typing import List, Tuple, Dict
import threading
import time


@dataclass
class MotorParameters:
    """Motor physical and electrical parameters"""
    voltage: float = 220.0  # Terminal voltage (V)
    power_hp: float = 10.0  # Rated power (HP)
    field_resistance: float = 122.0  # Field winding resistance (Ω)
    armature_resistance: float = 0.3  # Armature resistance (Ω)
    efficiency: float = 0.8  # Motor efficiency
    speed_reduction: float = 0.8  # Speed reduction factor

    # Additional physical parameters
    armature_inductance: float = 0.05  # Armature inductance (H)
    moment_of_inertia: float = 0.5  # Moment of inertia (kg·m²)
    friction_coefficient: float = 0.01  # Viscous friction (N·m·s/rad)

    # Thermal parameters
    thermal_resistance: float = 2.5  # Thermal resistance (°C/W)
    thermal_capacitance: float = 500.0  # Thermal capacitance (J/°C)
    ambient_temperature: float = 25.0  # Ambient temperature (°C)

    # Economic parameters
    electricity_cost: float = 0.12  # Cost per kWh ($/kWh)
    operating_hours: float = 8.0  # Operating hours per day

    # Mechanical parameters
    shaft_diameter: float = 0.05  # Shaft diameter (m)
    bearing_friction: float = 5.0  # Bearing friction (N·m)


class MotorCalculator:
    """Core calculation engine for motor analysis"""

    def __init__(self, params: MotorParameters):
        self.params = params
        self.reset_calculations()

    def reset_calculations(self):
        """Reset all calculated values"""
        self.power_watts = self.params.power_hp * 746  # Convert HP to Watts
        self.input_power = self.power_watts / self.params.efficiency
        self.field_current = self.params.voltage / self.params.field_resistance
        self.armature_current = (self.input_power - self.params.voltage * self.field_current) / self.params.voltage
        self.back_emf = self.params.voltage - self.armature_current * self.params.armature_resistance

        # Calculate motor constant
        self.k_motor = self.back_emf / (2 * np.pi * 1500 / 60)  # Assuming 1500 RPM base speed

    def calculate_resistance_constant_torque(self) -> Tuple[float, Dict]:
        """
        Case (a): Calculate resistance for constant torque

        Returns:
            Resistance to add (Ω) and detailed results
        """
        # At constant torque: T1 = T2, so Ia1 = Ia2
        ia_new = self.armature_current

        # New back EMF at 80% speed
        eb_new = self.params.speed_reduction * self.back_emf

        # Required total resistance
        total_resistance = (self.params.voltage - eb_new) / ia_new

        # Additional resistance needed
        r_add = total_resistance - self.params.armature_resistance

        results = {
            'armature_current_initial': self.armature_current,
            'armature_current_new': ia_new,
            'back_emf_initial': self.back_emf,
            'back_emf_new': eb_new,
            'resistance_added': r_add,
            'total_resistance': total_resistance,
            'power_loss': ia_new**2 * r_add,
            'efficiency_new': (eb_new * ia_new) / (self.params.voltage * ia_new) * 100
        }

        return r_add, results

    def calculate_resistance_square_law_torque(self) -> Tuple[float, Dict]:
        """
        Case (b): Calculate resistance when torque ∝ speed²

        Returns:
            Resistance to add (Ω) and detailed results
        """
        # Torque ratio = (N2/N1)² = speed_reduction²
        torque_ratio = self.params.speed_reduction ** 2

        # Since T ∝ Ia (for constant flux), Ia2 = torque_ratio × Ia1
        ia_new = torque_ratio * self.armature_current

        # New back EMF at 80% speed
        eb_new = self.params.speed_reduction * self.back_emf

        # Required total resistance
        total_resistance = (self.params.voltage - eb_new) / ia_new

        # Additional resistance needed
        r_add = total_resistance - self.params.armature_resistance

        results = {
            'armature_current_initial': self.armature_current,
            'armature_current_new': ia_new,
            'back_emf_initial': self.back_emf,
            'back_emf_new': eb_new,
            'resistance_added': r_add,
            'total_resistance': total_resistance,
            'torque_ratio': torque_ratio,
            'power_loss': ia_new**2 * r_add,
            'efficiency_new': (eb_new * ia_new) / (self.params.voltage * ia_new) * 100
        }

        return r_add, results

    def calculate_losses(self, ia: float, speed_rpm: float) -> Dict[str, float]:
        """
        Calculate detailed loss breakdown

        Args:
            ia: Armature current (A)
            speed_rpm: Motor speed (RPM)

        Returns:
            Dictionary of losses
        """
        # Copper losses
        armature_copper_loss = ia**2 * self.params.armature_resistance
        field_copper_loss = self.field_current**2 * self.params.field_resistance

        # Iron losses (core losses) - proportional to speed²
        iron_loss_constant = 50  # Base iron loss at rated speed (W)
        speed_ratio = speed_rpm / 1500
        iron_losses = iron_loss_constant * speed_ratio**1.5

        # Mechanical losses
        mechanical_friction = self.params.bearing_friction * (2 * np.pi * speed_rpm / 60)
        windage_loss = 0.01 * (speed_rpm / 1500)**3 * 100  # Windage proportional to speed³

        # Stray load losses (typically 1% of output power)
        stray_losses = 0.01 * self.power_watts * (ia / self.armature_current)

        total_losses = (armature_copper_loss + field_copper_loss +
                       iron_losses + mechanical_friction + windage_loss + stray_losses)

        return {
            'armature_copper_loss': armature_copper_loss,
            'field_copper_loss': field_copper_loss,
            'iron_losses': iron_losses,
            'mechanical_friction': mechanical_friction,
            'windage_loss': windage_loss,
            'stray_losses': stray_losses,
            'total_losses': total_losses
        }


class ODESolver:
    """ODE solver for dynamic motor simulation"""

    def __init__(self, params: MotorParameters):
        self.params = params
        self.calc = MotorCalculator(params)

    def motor_dynamics_rk45(self, t: float, y: np.ndarray, load_torque: float,
                            applied_voltage: float, r_external: float = 0.0) -> np.ndarray:
        """
        Motor differential equations for RK45 solver

        State variables: [ia, omega, theta]
        ia: armature current (A)
        omega: angular velocity (rad/s)
        theta: angular position (rad)
        temperature: winding temperature (°C)

        Args:
            t: Time (s)
            y: State vector [ia, omega, theta, temperature]
            load_torque: Load torque (N·m)
            applied_voltage: Applied voltage (V)
            r_external: External resistance (Ω)

        Returns:
            Derivative vector [dia/dt, domega/dt, dtheta/dt, dT/dt]
        """
        ia, omega, theta, temperature = y

        # Back EMF
        k_phi = self.calc.k_motor
        eb = k_phi * omega

        # Armature current dynamics
        total_resistance = self.params.armature_resistance + r_external
        dia_dt = (applied_voltage - eb - ia * total_resistance) / self.params.armature_inductance

        # Electromagnetic torque
        torque_em = k_phi * ia

        # Friction torque
        torque_friction = self.params.friction_coefficient * omega

        # Angular acceleration
        domega_dt = (torque_em - load_torque - torque_friction) / self.params.moment_of_inertia

        # Angular position
        dtheta_dt = omega

        # Thermal dynamics
        power_loss = ia**2 * total_resistance + self.params.field_current**2 * self.params.field_resistance
        dT_dt = (power_loss - (temperature - self.params.ambient_temperature) / self.params.thermal_resistance) / self.params.thermal_capacitance

        return np.array([dia_dt, domega_dt, dtheta_dt, dT_dt])

    def motor_dynamics_euler(self, y: np.ndarray, dt: float, load_torque: float,
                            applied_voltage: float, r_external: float = 0.0) -> np.ndarray:
        """
        Euler method for motor dynamics

        Args:
            y: Current state [ia, omega, theta, temperature]
            dt: Time step (s)
            load_torque: Load torque (N·m)
            applied_voltage: Applied voltage (V)
            r_external: External resistance (Ω)

        Returns:
            Next state vector
        """
        dy_dt = self.motor_dynamics_rk45(0, y, load_torque, applied_voltage, r_external)
        return y + dy_dt * dt

    def simulate_transient(self, t_span: Tuple[float, float], initial_conditions: np.ndarray,
                          load_torque: float, applied_voltage: float,
                          r_external: float = 0.0, method='RK45') -> Dict:
        """
        Simulate motor transient response

        Args:
            t_span: Time span (t_start, t_end)
            initial_conditions: Initial state [ia0, omega0, theta0, T0]
            load_torque: Load torque (N·m)
            applied_voltage: Applied voltage (V)
            r_external: External resistance (Ω)
            method: Integration method ('RK45' or 'Euler')

        Returns:
            Dictionary with time series results
        """
        if method == 'RK45':
            sol = solve_ivp(
                lambda t, y: self.motor_dynamics_rk45(t, y, load_torque, applied_voltage, r_external),
                t_span,
                initial_conditions,
                method='RK45',
                dense_output=True,
                max_step=0.001
            )

            t_eval = np.linspace(t_span[0], t_span[1], 1000)
            y_eval = sol.sol(t_eval)

            return {
                't': t_eval,
                'ia': y_eval[0],
                'omega': y_eval[1],
                'theta': y_eval[2],
                'temperature': y_eval[3],
                'speed_rpm': y_eval[1] * 60 / (2 * np.pi),
                'torque': self.calc.k_motor * y_eval[0]
            }
        else:  # Euler method
            dt = 0.001
            t_eval = np.arange(t_span[0], t_span[1], dt)
            n_steps = len(t_eval)

            ia = np.zeros(n_steps)
            omega = np.zeros(n_steps)
            theta = np.zeros(n_steps)
            temperature = np.zeros(n_steps)

            # Initial conditions
            ia[0], omega[0], theta[0], temperature[0] = initial_conditions

            for i in range(1, n_steps):
                y = np.array([ia[i-1], omega[i-1], theta[i-1], temperature[i-1]])
                y_new = self.motor_dynamics_euler(y, dt, load_torque, applied_voltage, r_external)
                ia[i], omega[i], theta[i], temperature[i] = y_new

            return {
                't': t_eval,
                'ia': ia,
                'omega': omega,
                'theta': theta,
                'temperature': temperature,
                'speed_rpm': omega * 60 / (2 * np.pi),
                'torque': self.calc.k_motor * ia
            }


class ThermalAnalysis:
    """Thermal and derating analysis"""

    def __init__(self, params: MotorParameters):
        self.params = params

    def calculate_temperature_rise(self, power_loss: float, time: float) -> float:
        """
        Calculate temperature rise over time

        Args:
            power_loss: Total power loss (W)
            time: Time duration (s)

        Returns:
            Temperature rise (°C)
        """
        # Steady-state temperature rise
        temp_rise_ss = power_loss * self.params.thermal_resistance

        # Time constant
        tau = self.params.thermal_resistance * self.params.thermal_capacitance

        # Transient temperature rise
        temp_rise = temp_rise_ss * (1 - np.exp(-time / tau))

        return temp_rise

    def calculate_derating_factor(self, ambient_temp: float) -> float:
        """
        Calculate derating factor based on ambient temperature

        Args:
            ambient_temp: Ambient temperature (°C)

        Returns:
            Derating factor (0-1)
        """
        max_operating_temp = 155  # Class F insulation (°C)
        rated_ambient_temp = 40  # Rated ambient temperature (°C)

        if ambient_temp <= rated_ambient_temp:
            return 1.0

        # Linear derating above rated temperature
        derating = 1.0 - 0.01 * (ambient_temp - rated_ambient_temp)
        return max(0, derating)

    def thermal_stress_analysis(self, current_profile: np.ndarray, time: np.ndarray) -> Dict:
        """
        Analyze thermal stress from current profile

        Args:
            current_profile: Array of current values (A)
            time: Time array (s)

        Returns:
            Dictionary with thermal analysis results
        """
        # Calculate I²t for thermal stress
        i2t = np.trapz(current_profile**2, time)

        # Calculate peak temperature
        max_power_loss = max(current_profile)**2 * self.params.armature_resistance
        peak_temp_rise = self.calculate_temperature_rise(max_power_loss, max(time))
        peak_temp = self.params.ambient_temperature + peak_temp_rise

        # Check if within limits
        max_allowable_temp = 155  # Class F
        thermal_margin = max_allowable_temp - peak_temp

        return {
            'i2t': i2t,
            'peak_temperature': peak_temp,
            'thermal_margin': thermal_margin,
            'safe': thermal_margin > 0
        }


class MechanicalAnalysis:
    """Mechanical stress and bearing analysis"""

    def __init__(self, params: MotorParameters):
        self.params = params

    def calculate_shaft_stress(self, torque: float) -> Dict:
        """
        Calculate shaft torsional stress

        Args:
            torque: Shaft torque (N·m)

        Returns:
            Dictionary with stress analysis
        """
        # Shaft polar moment of inertia
        J = np.pi * self.params.shaft_diameter**4 / 32

        # Maximum shear stress
        r = self.params.shaft_diameter / 2
        tau_max = torque * r / J

        # Allowable shear stress for steel shaft (typically 40-80 MPa)
        tau_allowable = 60e6  # Pa

        safety_factor = tau_allowable / tau_max if tau_max > 0 else float('inf')

        return {
            'shaft_diameter': self.params.shaft_diameter,
            'polar_moment': J,
            'max_shear_stress': tau_max,
            'allowable_stress': tau_allowable,
            'safety_factor': safety_factor,
            'safe': safety_factor > 2.0
        }

    def bearing_load_analysis(self, torque: float, speed_rpm: float) -> Dict:
        """
        Analyze bearing loads and life

        Args:
            torque: Operating torque (N·m)
            speed_rpm: Speed (RPM)

        Returns:
            Dictionary with bearing analysis
        """
        # Radial load on bearing (simplified)
        radial_load = torque / (self.params.shaft_diameter / 2)

        # Bearing life calculation (simplified L10 life)
        # Using bearing load rating C = 10000 N (example)
        C = 10000  # Dynamic load rating (N)
        P = radial_load  # Equivalent load (N)

        # Life in millions of revolutions
        L10 = (C / P)**3 if P > 0 else float('inf')

        # Life in hours
        L10_hours = (L10 * 1e6) / (speed_rpm * 60)

        return {
            'radial_load': radial_load,
            'bearing_rating': C,
            'L10_revolutions': L10,
            'L10_hours': L10_hours,
            'bearing_friction_loss': self.params.bearing_friction * (2 * np.pi * speed_rpm / 60)
        }


class EconomicAnalysis:
    """Economic and cost analysis"""

    def __init__(self, params: MotorParameters):
        self.params = params

    def calculate_operating_cost(self, avg_power_kw: float, days_per_year: float = 365) -> Dict:
        """
        Calculate annual operating costs

        Args:
            avg_power_kw: Average power consumption (kW)
            days_per_year: Operating days per year

        Returns:
            Dictionary with cost analysis
        """
        # Daily energy consumption
        daily_energy = avg_power_kw * self.params.operating_hours  # kWh

        # Annual energy consumption
        annual_energy = daily_energy * days_per_year  # kWh

        # Annual cost
        annual_cost = annual_energy * self.params.electricity_cost

        return {
            'daily_energy_kwh': daily_energy,
            'annual_energy_kwh': annual_energy,
            'daily_cost': daily_energy * self.params.electricity_cost,
            'annual_cost': annual_cost,
            'electricity_rate': self.params.electricity_cost
        }

    def efficiency_comparison(self, scenario1: Dict, scenario2: Dict) -> Dict:
        """
        Compare two operating scenarios economically

        Args:
            scenario1: First scenario {'power': kW, 'efficiency': %}
            scenario2: Second scenario {'power': kW, 'efficiency': %}

        Returns:
            Comparison results
        """
        cost1 = self.calculate_operating_cost(scenario1['power'])
        cost2 = self.calculate_operating_cost(scenario2['power'])

        savings = cost1['annual_cost'] - cost2['annual_cost']
        savings_percent = (savings / cost1['annual_cost'] * 100) if cost1['annual_cost'] > 0 else 0

        return {
            'scenario1_cost': cost1,
            'scenario2_cost': cost2,
            'annual_savings': savings,
            'savings_percent': savings_percent,
            'payback_period_years': 0  # Would need investment cost to calculate
        }


class MotorControlGUI:
    """Main Tkinter GUI application"""

    def __init__(self, root):
        self.root = root
        self.root.title("Advanced DC Shunt Motor Speed Control & Multi-Physics Simulation")
        self.root.geometry("1400x900")

        # Initialize parameters
        self.params = MotorParameters()
        self.calculator = MotorCalculator(self.params)
        self.ode_solver = ODESolver(self.params)
        self.thermal = ThermalAnalysis(self.params)
        self.mechanical = MechanicalAnalysis(self.params)
        self.economic = EconomicAnalysis(self.params)

        # Simulation control
        self.simulation_running = False
        self.simulation_thread = None

        # Setup GUI
        self.setup_menu()
        self.setup_gui()

        # Bind resize event
        self.root.bind('<Configure>', self.on_window_resize)

    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Analysis", command=self.reset_all)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Calculate Speed Control", command=self.calculate_speed_control)
        tools_menu.add_command(label="Run Dynamic Simulation", command=self.run_dynamic_simulation)
        tools_menu.add_separator()
        tools_menu.add_command(label="Loss Analysis", command=self.show_loss_analysis)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)

    def setup_gui(self):
        """Setup main GUI layout"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.setup_main_tab()
        self.setup_dynamic_simulation_tab()
        self.setup_thermal_tab()
        self.setup_mechanical_tab()
        self.setup_economic_tab()
        self.setup_multiphysics_tab()

    def setup_main_tab(self):
        """Setup main analysis tab"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Speed Control Analysis")

        # Left panel - Input parameters
        left_panel = ttk.LabelFrame(main_frame, text="Motor Parameters", padding=10)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # Parameter inputs
        params_list = [
            ("Voltage (V):", "voltage", 220.0),
            ("Power (HP):", "power_hp", 10.0),
            ("Field Resistance (Ω):", "field_resistance", 122.0),
            ("Armature Resistance (Ω):", "armature_resistance", 0.3),
            ("Efficiency (%):", "efficiency_pct", 80.0),
            ("Speed Reduction (%):", "speed_reduction_pct", 80.0),
        ]

        self.param_vars = {}
        for idx, (label, var_name, default) in enumerate(params_list):
            ttk.Label(left_panel, text=label).grid(row=idx, column=0, sticky='w', pady=3)
            var = tk.DoubleVar(value=default)
            self.param_vars[var_name] = var
            entry = ttk.Entry(left_panel, textvariable=var, width=15)
            entry.grid(row=idx, column=1, pady=3, padx=5)

            # Add slider for some parameters
            if var_name in ['speed_reduction_pct', 'efficiency_pct']:
                slider = ttk.Scale(left_panel, from_=0, to=100, orient='horizontal',
                                  variable=var, length=150)
                slider.grid(row=idx, column=2, pady=3, padx=5)

        # Control buttons
        btn_frame = ttk.Frame(left_panel)
        btn_frame.grid(row=len(params_list), column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Calculate", command=self.calculate_speed_control,
                  style='Accent.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_parameters).pack(side='left', padx=5)

        # Right panel - Results
        right_panel = ttk.LabelFrame(main_frame, text="Results", padding=10)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

        self.results_text = scrolledtext.ScrolledText(right_panel, width=60, height=25,
                                                      wrap=tk.WORD, font=('Courier', 9))
        self.results_text.pack(fill='both', expand=True)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

    def setup_dynamic_simulation_tab(self):
        """Setup dynamic simulation tab"""
        sim_frame = ttk.Frame(self.notebook)
        self.notebook.add(sim_frame, text="Dynamic Simulation")

        # Control panel
        control_panel = ttk.LabelFrame(sim_frame, text="Simulation Control", padding=10)
        control_panel.pack(side='top', fill='x', padx=5, pady=5)

        # Simulation parameters
        ttk.Label(control_panel, text="Simulation Time (s):").grid(row=0, column=0, sticky='w')
        self.sim_time_var = tk.DoubleVar(value=2.0)
        ttk.Entry(control_panel, textvariable=self.sim_time_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(control_panel, text="Load Torque (N·m):").grid(row=0, column=2, sticky='w', padx=10)
        self.load_torque_var = tk.DoubleVar(value=40.0)
        ttk.Scale(control_panel, from_=0, to=100, variable=self.load_torque_var,
                 orient='horizontal', length=200).grid(row=0, column=3, padx=5)
        ttk.Label(control_panel, textvariable=self.load_torque_var).grid(row=0, column=4)

        ttk.Label(control_panel, text="External R (Ω):").grid(row=1, column=0, sticky='w')
        self.ext_r_var = tk.DoubleVar(value=0.0)
        ttk.Scale(control_panel, from_=0, to=5, variable=self.ext_r_var,
                 orient='horizontal', length=200).grid(row=1, column=1, columnspan=2, padx=5)

        ttk.Label(control_panel, text="Solver:").grid(row=1, column=2, sticky='w', padx=10)
        self.solver_var = tk.StringVar(value='RK45')
        ttk.Combobox(control_panel, textvariable=self.solver_var,
                    values=['RK45', 'Euler'], width=10, state='readonly').grid(row=1, column=3)

        # Buttons
        btn_frame = ttk.Frame(control_panel)
        btn_frame.grid(row=2, column=0, columnspan=5, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_simulation)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_simulation, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Reset", command=self.reset_simulation).pack(side='left', padx=5)

        # Plot panel
        plot_panel = ttk.Frame(sim_frame)
        plot_panel.pack(side='top', fill='both', expand=True, padx=5, pady=5)

        # Create figure with subplots
        self.sim_fig = Figure(figsize=(12, 8))
        self.sim_axes = []

        # Create 2x2 subplot grid
        self.sim_axes.append(self.sim_fig.add_subplot(2, 2, 1))  # Speed
        self.sim_axes.append(self.sim_fig.add_subplot(2, 2, 2))  # Current
        self.sim_axes.append(self.sim_fig.add_subplot(2, 2, 3))  # Torque
        self.sim_axes.append(self.sim_fig.add_subplot(2, 2, 4))  # Temperature

        self.sim_fig.tight_layout()

        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, plot_panel)
        self.sim_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Add toolbar
        toolbar = NavigationToolbar2Tk(self.sim_canvas, plot_panel)
        toolbar.update()

    def setup_thermal_tab(self):
        """Setup thermal analysis tab"""
        thermal_frame = ttk.Frame(self.notebook)
        self.notebook.add(thermal_frame, text="Thermal Analysis")

        # Control panel
        control_panel = ttk.LabelFrame(thermal_frame, text="Thermal Parameters", padding=10)
        control_panel.pack(side='top', fill='x', padx=5, pady=5)

        # Parameters
        ttk.Label(control_panel, text="Ambient Temp (°C):").grid(row=0, column=0, sticky='w')
        self.ambient_temp_var = tk.DoubleVar(value=25.0)
        ttk.Entry(control_panel, textvariable=self.ambient_temp_var, width=10).grid(row=0, column=1)

        ttk.Label(control_panel, text="Operating Current (A):").grid(row=0, column=2, padx=10, sticky='w')
        self.thermal_current_var = tk.DoubleVar(value=40.0)
        ttk.Entry(control_panel, textvariable=self.thermal_current_var, width=10).grid(row=0, column=3)

        ttk.Button(control_panel, text="Analyze", command=self.run_thermal_analysis).grid(row=0, column=4, padx=10)

        # Results panel
        results_panel = ttk.Frame(thermal_frame)
        results_panel.pack(side='top', fill='both', expand=True, padx=5, pady=5)

        # Text results
        self.thermal_text = scrolledtext.ScrolledText(results_panel, height=10, wrap=tk.WORD)
        self.thermal_text.pack(side='top', fill='x', padx=5, pady=5)

        # Plot
        self.thermal_fig = Figure(figsize=(10, 6))
        self.thermal_ax = self.thermal_fig.add_subplot(111)
        self.thermal_canvas = FigureCanvasTkAgg(self.thermal_fig, results_panel)
        self.thermal_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_mechanical_tab(self):
        """Setup mechanical analysis tab"""
        mech_frame = ttk.Frame(self.notebook)
        self.notebook.add(mech_frame, text="Mechanical Analysis")

        # Control panel
        control_panel = ttk.LabelFrame(mech_frame, text="Mechanical Parameters", padding=10)
        control_panel.pack(side='top', fill='x', padx=5, pady=5)

        ttk.Label(control_panel, text="Operating Torque (N·m):").grid(row=0, column=0, sticky='w')
        self.mech_torque_var = tk.DoubleVar(value=50.0)
        ttk.Entry(control_panel, textvariable=self.mech_torque_var, width=10).grid(row=0, column=1)

        ttk.Label(control_panel, text="Speed (RPM):").grid(row=0, column=2, padx=10, sticky='w')
        self.mech_speed_var = tk.DoubleVar(value=1500.0)
        ttk.Entry(control_panel, textvariable=self.mech_speed_var, width=10).grid(row=0, column=3)

        ttk.Button(control_panel, text="Analyze", command=self.run_mechanical_analysis).grid(row=0, column=4, padx=10)

        # Results
        self.mechanical_text = scrolledtext.ScrolledText(mech_frame, height=25, wrap=tk.WORD)
        self.mechanical_text.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_economic_tab(self):
        """Setup economic analysis tab"""
        econ_frame = ttk.Frame(self.notebook)
        self.notebook.add(econ_frame, text="Economic Analysis")

        # Input panel
        input_panel = ttk.LabelFrame(econ_frame, text="Economic Parameters", padding=10)
        input_panel.pack(side='top', fill='x', padx=5, pady=5)

        params = [
            ("Electricity Cost ($/kWh):", "elec_cost", 0.12),
            ("Operating Hours/Day:", "op_hours", 8.0),
            ("Operating Days/Year:", "op_days", 365.0),
            ("Average Power (kW):", "avg_power", 7.46),
        ]

        self.econ_vars = {}
        for idx, (label, var_name, default) in enumerate(params):
            ttk.Label(input_panel, text=label).grid(row=idx//2, column=(idx%2)*2, sticky='w', padx=5)
            var = tk.DoubleVar(value=default)
            self.econ_vars[var_name] = var
            ttk.Entry(input_panel, textvariable=var, width=15).grid(row=idx//2, column=(idx%2)*2+1, padx=5)

        ttk.Button(input_panel, text="Calculate", command=self.run_economic_analysis).grid(
            row=len(params)//2+1, column=0, columnspan=4, pady=10)

        # Results panel
        self.economic_text = scrolledtext.ScrolledText(econ_frame, height=15, wrap=tk.WORD)
        self.economic_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Chart
        self.econ_fig = Figure(figsize=(10, 4))
        self.econ_ax = self.econ_fig.add_subplot(111)
        self.econ_canvas = FigureCanvasTkAgg(self.econ_fig, econ_frame)
        self.econ_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_multiphysics_tab(self):
        """Setup multi-physics simulation tab"""
        mp_frame = ttk.Frame(self.notebook)
        self.notebook.add(mp_frame, text="Multi-Physics Simulation")

        # Control panel
        control_panel = ttk.LabelFrame(mp_frame, text="Multi-Physics Control", padding=10)
        control_panel.pack(side='top', fill='x', padx=5, pady=5)

        ttk.Label(control_panel, text="Simulation Duration (s):").grid(row=0, column=0, sticky='w')
        self.mp_time_var = tk.DoubleVar(value=5.0)
        ttk.Entry(control_panel, textvariable=self.mp_time_var, width=10).grid(row=0, column=1)

        ttk.Button(control_panel, text="Run Multi-Physics", command=self.run_multiphysics).grid(
            row=0, column=2, padx=10)

        # Create 3x2 subplot for multi-physics
        self.mp_fig = Figure(figsize=(12, 10))

        self.mp_axes = []
        for i in range(6):
            self.mp_axes.append(self.mp_fig.add_subplot(3, 2, i+1))

        self.mp_fig.tight_layout()

        self.mp_canvas = FigureCanvasTkAgg(self.mp_fig, mp_frame)
        self.mp_canvas.get_tk_widget().pack(fill='both', expand=True)

        toolbar = NavigationToolbar2Tk(self.mp_canvas, mp_frame)
        toolbar.update()

    def update_parameters(self):
        """Update motor parameters from GUI inputs"""
        self.params.voltage = self.param_vars['voltage'].get()
        self.params.power_hp = self.param_vars['power_hp'].get()
        self.params.field_resistance = self.param_vars['field_resistance'].get()
        self.params.armature_resistance = self.param_vars['armature_resistance'].get()
        self.params.efficiency = self.param_vars['efficiency_pct'].get() / 100.0
        self.params.speed_reduction = self.param_vars['speed_reduction_pct'].get() / 100.0

        # Recreate calculator with new parameters
        self.calculator = MotorCalculator(self.params)
        self.calculator.reset_calculations()

    def calculate_speed_control(self):
        """Calculate speed control resistance"""
        self.update_parameters()

        # Calculate both cases
        r_const_torque, results_const = self.calculator.calculate_resistance_constant_torque()
        r_square_law, results_square = self.calculator.calculate_resistance_square_law_torque()

        # Calculate losses
        losses_initial = self.calculator.calculate_losses(
            self.calculator.armature_current, 1500)
        losses_const = self.calculator.calculate_losses(
            results_const['armature_current_new'], 1500 * self.params.speed_reduction)
        losses_square = self.calculator.calculate_losses(
            results_square['armature_current_new'], 1500 * self.params.speed_reduction)

        # Display results
        self.results_text.delete(1.0, tk.END)

        output = "="*70 + "\n"
        output += "DC SHUNT MOTOR SPEED CONTROL ANALYSIS\n"
        output += "="*70 + "\n\n"

        output += "MOTOR PARAMETERS:\n"
        output += f"  Terminal Voltage: {self.params.voltage} V\n"
        output += f"  Rated Power: {self.params.power_hp} HP ({self.calculator.power_watts:.1f} W)\n"
        output += f"  Field Resistance: {self.params.field_resistance} Ω\n"
        output += f"  Armature Resistance: {self.params.armature_resistance} Ω\n"
        output += f"  Efficiency: {self.params.efficiency*100}%\n"
        output += f"  Speed Reduction: {self.params.speed_reduction*100}%\n\n"

        output += "INITIAL OPERATING CONDITIONS:\n"
        output += f"  Input Power: {self.calculator.input_power:.2f} W\n"
        output += f"  Field Current: {self.calculator.field_current:.3f} A\n"
        output += f"  Armature Current: {self.calculator.armature_current:.3f} A\n"
        output += f"  Back EMF: {self.calculator.back_emf:.2f} V\n\n"

        output += "INITIAL LOSSES BREAKDOWN:\n"
        output += f"  Armature Copper Loss: {losses_initial['armature_copper_loss']:.2f} W\n"
        output += f"  Field Copper Loss: {losses_initial['field_copper_loss']:.2f} W\n"
        output += f"  Iron Losses: {losses_initial['iron_losses']:.2f} W\n"
        output += f"  Mechanical Friction: {losses_initial['mechanical_friction']:.2f} W\n"
        output += f"  Windage Loss: {losses_initial['windage_loss']:.2f} W\n"
        output += f"  Stray Load Losses: {losses_initial['stray_losses']:.2f} W\n"
        output += f"  Total Losses: {losses_initial['total_losses']:.2f} W\n\n"

        output += "="*70 + "\n"
        output += "CASE (a): CONSTANT TORQUE OPERATION\n"
        output += "="*70 + "\n"
        output += f"  Resistance to Add: {r_const_torque:.3f} Ω\n"
        output += f"  Total Resistance: {results_const['total_resistance']:.3f} Ω\n"
        output += f"  New Armature Current: {results_const['armature_current_new']:.3f} A\n"
        output += f"  New Back EMF: {results_const['back_emf_new']:.2f} V\n"
        output += f"  Power Loss in Added R: {results_const['power_loss']:.2f} W\n"
        output += f"  New Efficiency: {results_const['efficiency_new']:.2f}%\n\n"

        output += "  LOSSES AT REDUCED SPEED (Constant Torque):\n"
        output += f"    Armature Copper Loss: {losses_const['armature_copper_loss']:.2f} W\n"
        output += f"    Field Copper Loss: {losses_const['field_copper_loss']:.2f} W\n"
        output += f"    Iron Losses: {losses_const['iron_losses']:.2f} W\n"
        output += f"    Total Losses: {losses_const['total_losses']:.2f} W\n\n"

        output += "="*70 + "\n"
        output += "CASE (b): TORQUE PROPORTIONAL TO SPEED SQUARED\n"
        output += "="*70 + "\n"
        output += f"  Torque Ratio: {results_square['torque_ratio']:.3f}\n"
        output += f"  Resistance to Add: {r_square_law:.3f} Ω\n"
        output += f"  Total Resistance: {results_square['total_resistance']:.3f} Ω\n"
        output += f"  New Armature Current: {results_square['armature_current_new']:.3f} A\n"
        output += f"  New Back EMF: {results_square['back_emf_new']:.2f} V\n"
        output += f"  Power Loss in Added R: {results_square['power_loss']:.2f} W\n"
        output += f"  New Efficiency: {results_square['efficiency_new']:.2f}%\n\n"

        output += "  LOSSES AT REDUCED SPEED (Square Law):\n"
        output += f"    Armature Copper Loss: {losses_square['armature_copper_loss']:.2f} W\n"
        output += f"    Field Copper Loss: {losses_square['field_copper_loss']:.2f} W\n"
        output += f"    Iron Losses: {losses_square['iron_losses']:.2f} W\n"
        output += f"    Total Losses: {losses_square['total_losses']:.2f} W\n\n"

        output += "="*70 + "\n"
        output += "SUMMARY:\n"
        output += "="*70 + "\n"
        output += f"The resistance method is inefficient due to high I²R losses.\n"
        output += f"For constant torque: Loss = {results_const['power_loss']:.2f} W\n"
        output += f"For square law torque: Loss = {results_square['power_loss']:.2f} W\n"
        output += f"\nAlternative methods (field control, PWM) are recommended for\n"
        output += f"better efficiency in practical applications.\n"

        self.results_text.insert(1.0, output)

    def start_simulation(self):
        """Start dynamic simulation"""
        if self.simulation_running:
            return

        self.simulation_running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        # Run simulation in thread
        self.simulation_thread = threading.Thread(target=self.run_simulation_thread)
        self.simulation_thread.start()

    def stop_simulation(self):
        """Stop simulation"""
        self.simulation_running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def run_simulation_thread(self):
        """Run simulation in separate thread"""
        self.update_parameters()

        # Get simulation parameters
        t_end = self.sim_time_var.get()
        load_torque = self.load_torque_var.get()
        r_external = self.ext_r_var.get()
        solver = self.solver_var.get()

        # Initial conditions [ia, omega, theta, temperature]
        initial_conditions = np.array([0.0, 0.0, 0.0, self.params.ambient_temperature])

        # Run simulation
        results = self.ode_solver.simulate_transient(
            (0, t_end),
            initial_conditions,
            load_torque,
            self.params.voltage,
            r_external,
            method=solver
        )

        # Update plots
        self.root.after(0, self.update_simulation_plots, results)

        self.simulation_running = False
        self.root.after(0, lambda: self.start_btn.config(state='normal'))
        self.root.after(0, lambda: self.stop_btn.config(state='disabled'))

    def update_simulation_plots(self, results):
        """Update simulation plots"""
        # Clear axes
        for ax in self.sim_axes:
            ax.clear()

        # Plot speed
        self.sim_axes[0].plot(results['t'], results['speed_rpm'], 'b-', linewidth=2)
        self.sim_axes[0].set_xlabel('Time (s)')
        self.sim_axes[0].set_ylabel('Speed (RPM)')
        self.sim_axes[0].set_title('Motor Speed')
        self.sim_axes[0].grid(True, alpha=0.3)

        # Plot current
        self.sim_axes[1].plot(results['t'], results['ia'], 'r-', linewidth=2)
        self.sim_axes[1].set_xlabel('Time (s)')
        self.sim_axes[1].set_ylabel('Current (A)')
        self.sim_axes[1].set_title('Armature Current')
        self.sim_axes[1].grid(True, alpha=0.3)

        # Plot torque
        self.sim_axes[2].plot(results['t'], results['torque'], 'g-', linewidth=2)
        self.sim_axes[2].set_xlabel('Time (s)')
        self.sim_axes[2].set_ylabel('Torque (N·m)')
        self.sim_axes[2].set_title('Electromagnetic Torque')
        self.sim_axes[2].grid(True, alpha=0.3)

        # Plot temperature
        self.sim_axes[3].plot(results['t'], results['temperature'], 'm-', linewidth=2)
        self.sim_axes[3].axhline(y=155, color='r', linestyle='--', label='Max Temp (Class F)')
        self.sim_axes[3].set_xlabel('Time (s)')
        self.sim_axes[3].set_ylabel('Temperature (°C)')
        self.sim_axes[3].set_title('Winding Temperature')
        self.sim_axes[3].legend()
        self.sim_axes[3].grid(True, alpha=0.3)

        self.sim_fig.tight_layout()
        self.sim_canvas.draw()

    def reset_simulation(self):
        """Reset simulation"""
        self.stop_simulation()
        for ax in self.sim_axes:
            ax.clear()
        self.sim_canvas.draw()

    def run_dynamic_simulation(self):
        """Switch to dynamic simulation tab and start"""
        self.notebook.select(1)
        self.start_simulation()

    def run_thermal_analysis(self):
        """Run thermal analysis"""
        ambient = self.ambient_temp_var.get()
        current = self.thermal_current_var.get()

        # Calculate temperature rise over time
        time = np.linspace(0, 3600, 1000)  # 1 hour
        power_loss = current**2 * self.params.armature_resistance + \
                    self.calculator.field_current**2 * self.params.field_resistance

        temp_rise = np.array([self.thermal.calculate_temperature_rise(power_loss, t) for t in time])
        temperature = ambient + temp_rise

        # Derating factor
        derating = self.thermal.calculate_derating_factor(ambient)

        # Display results
        self.thermal_text.delete(1.0, tk.END)
        output = "THERMAL ANALYSIS RESULTS\n"
        output += "="*60 + "\n"
        output += f"Ambient Temperature: {ambient} °C\n"
        output += f"Operating Current: {current} A\n"
        output += f"Total Power Loss: {power_loss:.2f} W\n"
        output += f"Steady-State Temp Rise: {temp_rise[-1]:.2f} °C\n"
        output += f"Final Temperature: {temperature[-1]:.2f} °C\n"
        output += f"Thermal Time Constant: {self.params.thermal_resistance * self.params.thermal_capacitance:.1f} s\n"
        output += f"Derating Factor: {derating:.3f}\n"
        output += f"Max Allowable Temp: 155 °C (Class F)\n"
        output += f"Thermal Margin: {155 - temperature[-1]:.2f} °C\n"

        if temperature[-1] > 155:
            output += "\nWARNING: Temperature exceeds safe limit!\n"
        else:
            output += "\nTemperature within safe operating limits.\n"

        self.thermal_text.insert(1.0, output)

        # Plot
        self.thermal_ax.clear()
        self.thermal_ax.plot(time/60, temperature, 'b-', linewidth=2, label='Winding Temp')
        self.thermal_ax.axhline(y=155, color='r', linestyle='--', label='Max Temp (155°C)')
        self.thermal_ax.axhline(y=ambient, color='g', linestyle=':', label=f'Ambient ({ambient}°C)')
        self.thermal_ax.set_xlabel('Time (minutes)')
        self.thermal_ax.set_ylabel('Temperature (°C)')
        self.thermal_ax.set_title('Thermal Transient Response')
        self.thermal_ax.legend()
        self.thermal_ax.grid(True, alpha=0.3)
        self.thermal_fig.tight_layout()
        self.thermal_canvas.draw()

    def run_mechanical_analysis(self):
        """Run mechanical analysis"""
        torque = self.mech_torque_var.get()
        speed = self.mech_speed_var.get()

        # Shaft stress analysis
        shaft_results = self.mechanical.calculate_shaft_stress(torque)

        # Bearing analysis
        bearing_results = self.mechanical.bearing_load_analysis(torque, speed)

        # Display results
        self.mechanical_text.delete(1.0, tk.END)
        output = "MECHANICAL STRESS ANALYSIS\n"
        output += "="*70 + "\n\n"

        output += "SHAFT TORSIONAL STRESS ANALYSIS:\n"
        output += f"  Shaft Diameter: {shaft_results['shaft_diameter']*1000:.1f} mm\n"
        output += f"  Polar Moment of Inertia: {shaft_results['polar_moment']:.2e} m⁴\n"
        output += f"  Applied Torque: {torque:.2f} N·m\n"
        output += f"  Maximum Shear Stress: {shaft_results['max_shear_stress']/1e6:.2f} MPa\n"
        output += f"  Allowable Shear Stress: {shaft_results['allowable_stress']/1e6:.2f} MPa\n"
        output += f"  Safety Factor: {shaft_results['safety_factor']:.2f}\n"

        if shaft_results['safe']:
            output += f"  Status: SAFE ✓\n\n"
        else:
            output += f"  Status: UNSAFE - Increase shaft diameter! ✗\n\n"

        output += "BEARING LOAD ANALYSIS:\n"
        output += f"  Operating Speed: {speed:.1f} RPM\n"
        output += f"  Radial Load on Bearing: {bearing_results['radial_load']:.2f} N\n"
        output += f"  Bearing Dynamic Rating: {bearing_results['bearing_rating']:.2f} N\n"
        output += f"  L10 Life (revolutions): {bearing_results['L10_revolutions']:.2e}\n"
        output += f"  L10 Life (hours): {bearing_results['L10_hours']:.1f} hours\n"
        output += f"  L10 Life (years @ 8h/day): {bearing_results['L10_hours']/(8*365):.1f} years\n"
        output += f"  Bearing Friction Loss: {bearing_results['bearing_friction_loss']:.2f} W\n\n"

        output += "MECHANICAL POWER FLOW:\n"
        output += f"  Mechanical Output Power: {torque * (2*np.pi*speed/60):.2f} W\n"
        output += f"  Bearing Friction Loss: {bearing_results['bearing_friction_loss']:.2f} W\n"
        output += f"  Net Shaft Power: {torque * (2*np.pi*speed/60) - bearing_results['bearing_friction_loss']:.2f} W\n"

        self.mechanical_text.insert(1.0, output)

    def run_economic_analysis(self):
        """Run economic analysis"""
        elec_cost = self.econ_vars['elec_cost'].get()
        op_hours = self.econ_vars['op_hours'].get()
        op_days = self.econ_vars['op_days'].get()
        avg_power = self.econ_vars['avg_power'].get()

        # Update parameters
        self.params.electricity_cost = elec_cost
        self.params.operating_hours = op_hours

        # Calculate costs
        results = self.economic.calculate_operating_cost(avg_power, op_days)

        # Display results
        self.economic_text.delete(1.0, tk.END)
        output = "ECONOMIC ANALYSIS\n"
        output += "="*70 + "\n\n"

        output += "OPERATING PARAMETERS:\n"
        output += f"  Average Power Consumption: {avg_power:.2f} kW\n"
        output += f"  Operating Hours per Day: {op_hours:.1f} hours\n"
        output += f"  Operating Days per Year: {op_days:.0f} days\n"
        output += f"  Electricity Rate: ${elec_cost:.3f}/kWh\n\n"

        output += "ENERGY CONSUMPTION:\n"
        output += f"  Daily Energy: {results['daily_energy_kwh']:.2f} kWh\n"
        output += f"  Monthly Energy: {results['daily_energy_kwh']*30:.2f} kWh\n"
        output += f"  Annual Energy: {results['annual_energy_kwh']:.2f} kWh\n\n"

        output += "OPERATING COSTS:\n"
        output += f"  Daily Cost: ${results['daily_cost']:.2f}\n"
        output += f"  Monthly Cost: ${results['daily_cost']*30:.2f}\n"
        output += f"  Annual Cost: ${results['annual_cost']:.2f}\n\n"

        # Calculate comparison with higher efficiency motor
        output += "EFFICIENCY IMPROVEMENT ANALYSIS:\n"
        output += f"  Current Efficiency: {self.params.efficiency*100:.1f}%\n"

        improved_efficiency = 0.92
        improved_power = avg_power * (self.params.efficiency / improved_efficiency)
        scenario1 = {'power': avg_power, 'efficiency': self.params.efficiency*100}
        scenario2 = {'power': improved_power, 'efficiency': improved_efficiency*100}

        comparison = self.economic.efficiency_comparison(scenario1, scenario2)

        output += f"  Improved Efficiency: {improved_efficiency*100:.1f}%\n"
        output += f"  Improved Power: {improved_power:.2f} kW\n"
        output += f"  Annual Savings: ${comparison['annual_savings']:.2f}\n"
        output += f"  Savings Percentage: {comparison['savings_percent']:.2f}%\n"

        self.economic_text.insert(1.0, output)

        # Plot cost breakdown
        self.econ_ax.clear()

        months = np.arange(1, 13)
        monthly_cost = results['daily_cost'] * 30
        cumulative_cost = monthly_cost * months

        self.econ_ax.bar(months, [monthly_cost]*12, alpha=0.7, label='Monthly Cost')
        self.econ_ax.plot(months, cumulative_cost, 'r-', marker='o', linewidth=2, label='Cumulative Cost')
        self.econ_ax.set_xlabel('Month')
        self.econ_ax.set_ylabel('Cost ($)')
        self.econ_ax.set_title('Annual Operating Cost Projection')
        self.econ_ax.legend()
        self.econ_ax.grid(True, alpha=0.3)
        self.econ_fig.tight_layout()
        self.econ_canvas.draw()

    def run_multiphysics(self):
        """Run comprehensive multi-physics simulation"""
        self.update_parameters()

        t_end = self.mp_time_var.get()

        # Run simulation with varying load
        initial_conditions = np.array([0.0, 0.0, 0.0, self.params.ambient_temperature])

        # Simulate with step load change
        t1 = t_end / 2

        # First half: light load
        results1 = self.ode_solver.simulate_transient(
            (0, t1), initial_conditions, 20.0, self.params.voltage, 0.0, method='RK45'
        )

        # Second half: heavy load
        final_state1 = np.array([results1['ia'][-1], results1['omega'][-1],
                                 results1['theta'][-1], results1['temperature'][-1]])
        results2 = self.ode_solver.simulate_transient(
            (t1, t_end), final_state1, 60.0, self.params.voltage, 0.0, method='RK45'
        )

        # Combine results
        t_combined = np.concatenate([results1['t'], results2['t']])
        ia_combined = np.concatenate([results1['ia'], results2['ia']])
        speed_combined = np.concatenate([results1['speed_rpm'], results2['speed_rpm']])
        torque_combined = np.concatenate([results1['torque'], results2['torque']])
        temp_combined = np.concatenate([results1['temperature'], results2['temperature']])

        # Calculate electromagnetic field strength (simplified)
        field_strength = ia_combined * 1000  # Simplified: AT/m

        # Calculate mechanical stress
        shaft_stress = []
        for torque in torque_combined:
            stress_result = self.mechanical.calculate_shaft_stress(torque)
            shaft_stress.append(stress_result['max_shear_stress'] / 1e6)  # MPa

        # Plot all results
        for ax in self.mp_axes:
            ax.clear()

        # 1. Speed vs Time
        self.mp_axes[0].plot(t_combined, speed_combined, 'b-', linewidth=2)
        self.mp_axes[0].set_xlabel('Time (s)')
        self.mp_axes[0].set_ylabel('Speed (RPM)')
        self.mp_axes[0].set_title('Motor Speed Response')
        self.mp_axes[0].grid(True, alpha=0.3)

        # 2. Current vs Time
        self.mp_axes[1].plot(t_combined, ia_combined, 'r-', linewidth=2)
        self.mp_axes[1].set_xlabel('Time (s)')
        self.mp_axes[1].set_ylabel('Current (A)')
        self.mp_axes[1].set_title('Armature Current')
        self.mp_axes[1].grid(True, alpha=0.3)

        # 3. Torque vs Time
        self.mp_axes[2].plot(t_combined, torque_combined, 'g-', linewidth=2)
        self.mp_axes[2].set_xlabel('Time (s)')
        self.mp_axes[2].set_ylabel('Torque (N·m)')
        self.mp_axes[2].set_title('Electromagnetic Torque')
        self.mp_axes[2].grid(True, alpha=0.3)

        # 4. Temperature vs Time
        self.mp_axes[3].plot(t_combined, temp_combined, 'm-', linewidth=2)
        self.mp_axes[3].axhline(y=155, color='r', linestyle='--', label='Max Temp')
        self.mp_axes[3].set_xlabel('Time (s)')
        self.mp_axes[3].set_ylabel('Temperature (°C)')
        self.mp_axes[3].set_title('Thermal Response')
        self.mp_axes[3].legend()
        self.mp_axes[3].grid(True, alpha=0.3)

        # 5. Electromagnetic Field
        self.mp_axes[4].plot(t_combined, field_strength, 'c-', linewidth=2)
        self.mp_axes[4].set_xlabel('Time (s)')
        self.mp_axes[4].set_ylabel('Field Strength (AT/m)')
        self.mp_axes[4].set_title('Electromagnetic Field')
        self.mp_axes[4].grid(True, alpha=0.3)

        # 6. Mechanical Stress
        self.mp_axes[5].plot(t_combined, shaft_stress, 'orange', linewidth=2)
        self.mp_axes[5].axhline(y=60, color='r', linestyle='--', label='Allowable')
        self.mp_axes[5].set_xlabel('Time (s)')
        self.mp_axes[5].set_ylabel('Shear Stress (MPa)')
        self.mp_axes[5].set_title('Shaft Mechanical Stress')
        self.mp_axes[5].legend()
        self.mp_axes[5].grid(True, alpha=0.3)

        self.mp_fig.tight_layout()
        self.mp_canvas.draw()

        messagebox.showinfo("Multi-Physics Complete",
                           "Multi-physics simulation completed successfully!\n\n"
                           "The simulation includes:\n"
                           "• Electrical dynamics (current, voltage)\n"
                           "• Electromagnetic coupling (torque, field)\n"
                           "• Thermal analysis (temperature rise)\n"
                           "• Mechanical stress (shaft stress)\n"
                           "• Dynamic load response")

    def show_loss_analysis(self):
        """Show detailed loss analysis"""
        self.update_parameters()

        # Calculate losses at different operating points
        speeds = np.linspace(500, 2000, 10)
        currents = np.linspace(20, 60, 10)

        total_losses = []
        efficiencies = []

        for speed, current in zip(speeds, currents):
            losses = self.calculator.calculate_losses(current, speed)
            total_losses.append(losses['total_losses'])

            output_power = self.calculator.k_motor * (2*np.pi*speed/60) * current
            input_power = self.params.voltage * current
            eff = (output_power / input_power * 100) if input_power > 0 else 0
            efficiencies.append(eff)

        # Create analysis window
        loss_window = tk.Toplevel(self.root)
        loss_window.title("Detailed Loss Analysis")
        loss_window.geometry("800x600")

        fig = Figure(figsize=(10, 8))

        ax1 = fig.add_subplot(2, 1, 1)
        ax1.plot(speeds, total_losses, 'r-', marker='o', linewidth=2)
        ax1.set_xlabel('Speed (RPM)')
        ax1.set_ylabel('Total Losses (W)')
        ax1.set_title('Losses vs Speed')
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(2, 1, 2)
        ax2.plot(speeds, efficiencies, 'b-', marker='s', linewidth=2)
        ax2.set_xlabel('Speed (RPM)')
        ax2.set_ylabel('Efficiency (%)')
        ax2.set_title('Efficiency vs Speed')
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, loss_window)
        canvas.get_tk_widget().pack(fill='both', expand=True)

        toolbar = NavigationToolbar2Tk(canvas, loss_window)
        toolbar.update()

    def reset_parameters(self):
        """Reset parameters to defaults"""
        defaults = {
            'voltage': 220.0,
            'power_hp': 10.0,
            'field_resistance': 122.0,
            'armature_resistance': 0.3,
            'efficiency_pct': 80.0,
            'speed_reduction_pct': 80.0,
        }

        for key, value in defaults.items():
            if key in self.param_vars:
                self.param_vars[key].set(value)

        self.results_text.delete(1.0, tk.END)

    def reset_all(self):
        """Reset entire application"""
        self.reset_parameters()
        self.reset_simulation()

    def save_results(self):
        """Save results to file"""
        filename = f"motor_analysis_{time.strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(filename, 'w') as f:
                f.write("MOTOR ANALYSIS RESULTS\n")
                f.write("="*70 + "\n\n")
                f.write(self.results_text.get(1.0, tk.END))

            messagebox.showinfo("Success", f"Results saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")

    def on_window_resize(self, event):
        """Handle window resize for auto-scaling"""
        # This is called frequently, so we just let tkinter handle most of it
        # The pack and grid managers with proper weights handle auto-scaling
        pass

    def show_about(self):
        """Show about dialog"""
        about_text = """
Advanced DC Shunt Motor Speed Control & Multi-Physics Simulation

Version 1.0

Features:
• Speed control resistance calculation (constant torque & square law)
• Dynamic simulation with RK45 and Euler ODE solvers
• Comprehensive loss analysis (copper, iron, mechanical, stray)
• Thermal analysis with temperature rise calculation
• Mechanical stress and bearing life analysis
• Economic analysis and operating cost calculation
• Multi-physics coupled simulation
• Real-time visualization and control

Developed for advanced electrical engineering education and practical applications.
        """
        messagebox.showinfo("About", about_text)

    def show_user_guide(self):
        """Show user guide"""
        guide_text = """
USER GUIDE

1. SPEED CONTROL ANALYSIS
   - Enter motor parameters in the main tab
   - Click "Calculate" to get resistance values for both cases
   - Review detailed loss breakdown

2. DYNAMIC SIMULATION
   - Set simulation time, load torque, and external resistance
   - Choose solver (RK45 recommended for accuracy, Euler for speed)
   - Click "Start" to run simulation
   - Observe speed, current, torque, and temperature responses

3. THERMAL ANALYSIS
   - Enter ambient temperature and operating current
   - Click "Analyze" for temperature rise calculation
   - Check thermal margin and derating factor

4. MECHANICAL ANALYSIS
   - Enter operating torque and speed
   - Review shaft stress and bearing life calculations

5. ECONOMIC ANALYSIS
   - Set electricity cost and operating hours
   - Calculate daily, monthly, and annual costs
   - Compare efficiency improvements

6. MULTI-PHYSICS SIMULATION
   - Run comprehensive coupled simulation
   - Observe electromagnetic, thermal, and mechanical behavior
   - Analyze system interactions

Use the menu for additional tools and options.
        """

        guide_window = tk.Toplevel(self.root)
        guide_window.title("User Guide")
        guide_window.geometry("600x500")

        text = scrolledtext.ScrolledText(guide_window, wrap=tk.WORD, font=('Arial', 10))
        text.pack(fill='both', expand=True, padx=10, pady=10)
        text.insert(1.0, guide_text)
        text.config(state='disabled')


def main():
    """Main entry point"""
    root = tk.Tk()

    # Set theme
    style = ttk.Style()
    available_themes = style.theme_names()

    # Try to use a modern theme
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'alt' in available_themes:
        style.theme_use('alt')

    # Create application
    app = MotorControlGUI(root)

    # Run
    root.mainloop()


if __name__ == "__main__":
    main()
