#!/usr/bin/env python3
"""
Example 9.7: Power Factor Correction with Dynamic ODE Solver
3-phase motor with capacitor bank for unity power factor
Includes real-time simulation with RK45 and Euler methods
Separate window for large, detailed plots
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp
import math


class PowerFactorCorrectionSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Example 9.7: Power Factor Correction - Control Panel")
        self.root.geometry("900x650")

        # Make window resizable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Simulation parameters
        self.is_running = False
        self.current_time = 0
        self.dt = 0.01
        self.solver_method = "RK45"

        # Data storage for plots
        self.time_data = []
        self.pf_data = []
        self.power_data = []
        self.reactive_power_data = []
        self.capacitance_data = []
        self.current_data = []

        # Visualization window
        self.viz_window = None
        self.fig = None
        self.canvas = None
        self.ax1 = None
        self.ax2 = None
        self.ax3 = None
        self.ax4 = None
        self.ax5 = None
        self.ax6 = None

        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.main_container.rowconfigure(1, weight=1)
        self.main_container.columnconfigure(0, weight=1)

        # Create GUI components
        self.create_control_panel()
        self.create_results_panel()

        # Initialize values
        self.update_calculations()

        # Create visualization window automatically
        self.create_visualization_window()

    def create_control_panel(self):
        """Create control panel with sliders and buttons"""
        control_frame = ttk.LabelFrame(self.main_container, text="Control Panel", padding=10)
        control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        control_frame.columnconfigure(1, weight=1)

        # Motor Power Output (HP)
        ttk.Label(control_frame, text="Motor Output (HP):").grid(row=0, column=0, sticky="w", pady=2)
        self.power_hp_var = tk.DoubleVar(value=600)
        self.power_hp_slider = ttk.Scale(control_frame, from_=100, to=1500,
                                         variable=self.power_hp_var, orient="horizontal",
                                         command=lambda x: self.update_calculations())
        self.power_hp_slider.grid(row=0, column=1, sticky="ew", padx=5)
        self.power_hp_label = ttk.Label(control_frame, text="600.0 HP")
        self.power_hp_label.grid(row=0, column=2, sticky="w")

        # Supply Voltage (V)
        ttk.Label(control_frame, text="Supply Voltage (V):").grid(row=1, column=0, sticky="w", pady=2)
        self.voltage_var = tk.DoubleVar(value=2500)
        self.voltage_slider = ttk.Scale(control_frame, from_=1000, to=5000,
                                       variable=self.voltage_var, orient="horizontal",
                                       command=lambda x: self.update_calculations())
        self.voltage_slider.grid(row=1, column=1, sticky="ew", padx=5)
        self.voltage_label = ttk.Label(control_frame, text="2500.0 V")
        self.voltage_label.grid(row=1, column=2, sticky="w")

        # Frequency (Hz)
        ttk.Label(control_frame, text="Frequency (Hz):").grid(row=2, column=0, sticky="w", pady=2)
        self.frequency_var = tk.DoubleVar(value=50)
        self.frequency_slider = ttk.Scale(control_frame, from_=25, to=100,
                                         variable=self.frequency_var, orient="horizontal",
                                         command=lambda x: self.update_calculations())
        self.frequency_slider.grid(row=2, column=1, sticky="ew", padx=5)
        self.frequency_label = ttk.Label(control_frame, text="50.0 Hz")
        self.frequency_label.grid(row=2, column=2, sticky="w")

        # Initial Power Factor
        ttk.Label(control_frame, text="Initial P.F. (lagging):").grid(row=3, column=0, sticky="w", pady=2)
        self.pf_initial_var = tk.DoubleVar(value=0.8)
        self.pf_initial_slider = ttk.Scale(control_frame, from_=0.5, to=0.95,
                                          variable=self.pf_initial_var, orient="horizontal",
                                          command=lambda x: self.update_calculations())
        self.pf_initial_slider.grid(row=3, column=1, sticky="ew", padx=5)
        self.pf_initial_label = ttk.Label(control_frame, text="0.80")
        self.pf_initial_label.grid(row=3, column=2, sticky="w")

        # Final Power Factor
        ttk.Label(control_frame, text="Final P.F.:").grid(row=4, column=0, sticky="w", pady=2)
        self.pf_final_var = tk.DoubleVar(value=1.0)
        self.pf_final_slider = ttk.Scale(control_frame, from_=0.8, to=1.0,
                                        variable=self.pf_final_var, orient="horizontal",
                                        command=lambda x: self.update_calculations())
        self.pf_final_slider.grid(row=4, column=1, sticky="ew", padx=5)
        self.pf_final_label = ttk.Label(control_frame, text="1.00")
        self.pf_final_label.grid(row=4, column=2, sticky="w")

        # Efficiency
        ttk.Label(control_frame, text="Efficiency:").grid(row=5, column=0, sticky="w", pady=2)
        self.efficiency_var = tk.DoubleVar(value=0.9)
        self.efficiency_slider = ttk.Scale(control_frame, from_=0.7, to=0.98,
                                          variable=self.efficiency_var, orient="horizontal",
                                          command=lambda x: self.update_calculations())
        self.efficiency_slider.grid(row=5, column=1, sticky="ew", padx=5)
        self.efficiency_label = ttk.Label(control_frame, text="0.90")
        self.efficiency_label.grid(row=5, column=2, sticky="w")

        # Capacitors in Series
        ttk.Label(control_frame, text="Capacitors in Series:").grid(row=6, column=0, sticky="w", pady=2)
        self.capacitors_series_var = tk.IntVar(value=5)
        self.capacitors_series_slider = ttk.Scale(control_frame, from_=1, to=10,
                                                 variable=self.capacitors_series_var, orient="horizontal",
                                                 command=lambda x: self.update_calculations())
        self.capacitors_series_slider.grid(row=6, column=1, sticky="ew", padx=5)
        self.capacitors_series_label = ttk.Label(control_frame, text="5")
        self.capacitors_series_label.grid(row=6, column=2, sticky="w")

        # Simulation Time Scale
        ttk.Label(control_frame, text="Simulation Time (s):").grid(row=7, column=0, sticky="w", pady=2)
        self.sim_time_var = tk.DoubleVar(value=5.0)
        self.sim_time_slider = ttk.Scale(control_frame, from_=1, to=20,
                                        variable=self.sim_time_var, orient="horizontal")
        self.sim_time_slider.grid(row=7, column=1, sticky="ew", padx=5)
        self.sim_time_label = ttk.Label(control_frame, text="5.0 s")
        self.sim_time_label.grid(row=7, column=2, sticky="w")

        # Solver selection and control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=10)

        ttk.Label(button_frame, text="Solver:").pack(side="left", padx=5)
        self.solver_var = tk.StringVar(value="RK45")
        solver_combo = ttk.Combobox(button_frame, textvariable=self.solver_var,
                                    values=["RK45", "Euler"], state="readonly", width=10)
        solver_combo.pack(side="left", padx=5)

        self.start_button = ttk.Button(button_frame, text="Start Simulation",
                                       command=self.start_simulation)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                      command=self.stop_simulation, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        self.reset_button = ttk.Button(button_frame, text="Reset",
                                       command=self.reset_simulation)
        self.reset_button.pack(side="left", padx=5)

        # Show/Hide plots button
        self.toggle_plots_button = ttk.Button(button_frame, text="Show Plots",
                                             command=self.toggle_visualization_window)
        self.toggle_plots_button.pack(side="left", padx=5)

    def create_visualization_window(self):
        """Create separate window for visualization with large plots"""
        if self.viz_window is not None and tk.Toplevel.winfo_exists(self.viz_window):
            self.viz_window.lift()
            return

        # Create new top-level window
        self.viz_window = tk.Toplevel(self.root)
        self.viz_window.title("Example 9.7: Real-Time Visualization")
        self.viz_window.geometry("1600x1000")

        # Make window resizable
        self.viz_window.rowconfigure(0, weight=1)
        self.viz_window.columnconfigure(0, weight=1)

        # Create frame for canvas
        viz_frame = ttk.Frame(self.viz_window)
        viz_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        viz_frame.rowconfigure(0, weight=1)
        viz_frame.columnconfigure(0, weight=1)

        # Create figure with larger size for better visibility
        self.fig = Figure(figsize=(16, 10), dpi=100)
        self.fig.patch.set_facecolor('#f0f0f0')

        # Create 2x3 grid of subplots with more spacing
        self.ax1 = self.fig.add_subplot(231)
        self.ax2 = self.fig.add_subplot(232)
        self.ax3 = self.fig.add_subplot(233)
        self.ax4 = self.fig.add_subplot(234)
        self.ax5 = self.fig.add_subplot(235)
        self.ax6 = self.fig.add_subplot(236)

        self.fig.tight_layout(pad=4.0)

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Add scrollbar if needed
        scrollbar_y = ttk.Scrollbar(viz_frame, orient="vertical")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        # Initialize plots
        self.init_plots()

        # Update button text
        self.toggle_plots_button.config(text="Hide Plots")

        # Handle window close event
        self.viz_window.protocol("WM_DELETE_WINDOW", self.on_viz_window_close)

        # Bind resize event
        self.viz_window.bind('<Configure>', self.on_viz_resize)

    def on_viz_window_close(self):
        """Handle visualization window close event"""
        if self.viz_window:
            self.viz_window.withdraw()
            self.toggle_plots_button.config(text="Show Plots")

    def toggle_visualization_window(self):
        """Toggle visibility of visualization window"""
        if self.viz_window is None or not tk.Toplevel.winfo_exists(self.viz_window):
            self.create_visualization_window()
        else:
            if self.viz_window.state() == 'normal':
                self.viz_window.withdraw()
                self.toggle_plots_button.config(text="Show Plots")
            else:
                self.viz_window.deiconify()
                self.toggle_plots_button.config(text="Hide Plots")

    def create_results_panel(self):
        """Create results panel showing calculated values"""
        results_frame = ttk.LabelFrame(self.main_container, text="Calculation Results", padding=10)
        results_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        # Create text widget for results
        self.results_text = tk.Text(results_frame, height=20, width=100, font=('Courier', 10))
        self.results_text.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=scrollbar.set)

    def init_plots(self):
        """Initialize all plot axes with larger fonts"""
        if self.ax1 is None:
            return

        # Power Factor vs Time
        self.ax1.set_title('Power Factor vs Time', fontsize=14, fontweight='bold')
        self.ax1.set_xlabel('Time (s)', fontsize=12)
        self.ax1.set_ylabel('Power Factor', fontsize=12)
        self.ax1.grid(True, alpha=0.3, linewidth=1.5)
        self.ax1.set_ylim([0, 1.1])
        self.ax1.tick_params(labelsize=10)

        # Real Power vs Time
        self.ax2.set_title('Real Power vs Time', fontsize=14, fontweight='bold')
        self.ax2.set_xlabel('Time (s)', fontsize=12)
        self.ax2.set_ylabel('Power (kW)', fontsize=12)
        self.ax2.grid(True, alpha=0.3, linewidth=1.5)
        self.ax2.tick_params(labelsize=10)

        # Reactive Power vs Time
        self.ax3.set_title('Reactive Power vs Time', fontsize=14, fontweight='bold')
        self.ax3.set_xlabel('Time (s)', fontsize=12)
        self.ax3.set_ylabel('Reactive Power (kVAr)', fontsize=12)
        self.ax3.grid(True, alpha=0.3, linewidth=1.5)
        self.ax3.tick_params(labelsize=10)

        # Capacitance vs Time
        self.ax4.set_title('Capacitance per Phase vs Time', fontsize=14, fontweight='bold')
        self.ax4.set_xlabel('Time (s)', fontsize=12)
        self.ax4.set_ylabel('Capacitance (μF)', fontsize=12)
        self.ax4.grid(True, alpha=0.3, linewidth=1.5)
        self.ax4.tick_params(labelsize=10)

        # Capacitor Current vs Time
        self.ax5.set_title('Capacitor Current vs Time', fontsize=14, fontweight='bold')
        self.ax5.set_xlabel('Time (s)', fontsize=12)
        self.ax5.set_ylabel('Current (A)', fontsize=12)
        self.ax5.grid(True, alpha=0.3, linewidth=1.5)
        self.ax5.tick_params(labelsize=10)

        # Power Triangle (Phasor Diagram)
        self.ax6.set_title('Power Triangle', fontsize=14, fontweight='bold')
        self.ax6.set_xlabel('Real Power (kW)', fontsize=12)
        self.ax6.set_ylabel('Reactive Power (kVAr)', fontsize=12)
        self.ax6.grid(True, alpha=0.3, linewidth=1.5)
        self.ax6.set_aspect('equal')
        self.ax6.tick_params(labelsize=10)

    def update_calculations(self):
        """Update all calculations based on current slider values"""
        # Update slider labels
        self.power_hp_label.config(text=f"{self.power_hp_var.get():.1f} HP")
        self.voltage_label.config(text=f"{self.voltage_var.get():.1f} V")
        self.frequency_label.config(text=f"{self.frequency_var.get():.1f} Hz")
        self.pf_initial_label.config(text=f"{self.pf_initial_var.get():.3f}")
        self.pf_final_label.config(text=f"{self.pf_final_var.get():.3f}")
        self.efficiency_label.config(text=f"{self.efficiency_var.get():.3f}")
        self.capacitors_series_label.config(text=f"{self.capacitors_series_var.get()}")
        self.sim_time_label.config(text=f"{self.sim_time_var.get():.1f} s")

        # Perform calculations
        power_hp = self.power_hp_var.get()
        voltage = self.voltage_var.get()
        frequency = self.frequency_var.get()
        pf1 = self.pf_initial_var.get()
        pf2 = self.pf_final_var.get()
        efficiency = self.efficiency_var.get()
        n_capacitors = self.capacitors_series_var.get()

        # Motor input power (kW)
        motor_input_kw = (power_hp * 746) / (efficiency * 1000)

        # Calculate angles
        phi1 = math.acos(pf1)
        phi2 = math.acos(pf2)

        # Reactive power calculations
        tan_phi1 = math.tan(phi1)
        tan_phi2 = math.tan(phi2)

        # Leading kVAr supplied by capacitor bank
        kvar_total = motor_input_kw * (tan_phi1 - tan_phi2)

        # Leading kVAr per phase (delta connection)
        kvar_per_phase = kvar_total / 3

        # Phase voltage (line voltage for delta connection)
        v_ph = voltage

        # Calculate capacitance per phase
        # kVAr = V_ph * I_C = V_ph * (2*pi*f*C*V_ph) = 2*pi*f*C*V_ph^2
        # C = kVAr / (2*pi*f*V_ph^2) * 1000 (to convert to Farads)
        omega = 2 * math.pi * frequency
        C_phase_farad = (kvar_per_phase * 1000) / (omega * v_ph * v_ph)
        C_phase_uf = C_phase_farad * 1e6  # Convert to microfarads

        # Capacitance of each unit (n capacitors in series)
        C_unit_uf = C_phase_uf * n_capacitors

        # Capacitor current per phase
        I_c = omega * C_phase_farad * v_ph

        # Display results
        results = f"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                        EXAMPLE 9.7: POWER FACTOR CORRECTION RESULTS                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝

INPUT PARAMETERS:
  Motor Output Power        : {power_hp:.2f} HP
  Supply Voltage (L-L)      : {voltage:.2f} V
  Frequency                 : {frequency:.2f} Hz
  Initial Power Factor      : {pf1:.3f} lagging (φ₁ = {math.degrees(phi1):.2f}°)
  Final Power Factor        : {pf2:.3f} (φ₂ = {math.degrees(phi2):.2f}°)
  Motor Efficiency          : {efficiency:.3f}
  Capacitors in Series      : {n_capacitors}

CALCULATED RESULTS:
  Motor Input Power         : {motor_input_kw:.2f} kW

  Total Leading kVAr Req.   : {kvar_total:.2f} kVAr
  kVAr per Phase (Delta)    : {kvar_per_phase:.2f} kVAr

  Phase Voltage (Delta)     : {v_ph:.2f} V
  Capacitor Current/Phase   : {I_c:.2f} A

  Combined Capacitance/Phase: {C_phase_uf:.2f} μF
  Each Capacitor Unit       : {C_unit_uf:.2f} μF

  Angular Frequency (ω)     : {omega:.2f} rad/s

VERIFICATION:
  kVAr Check                : {omega * C_phase_farad * v_ph * v_ph / 1000:.2f} kVAr (should equal {kvar_per_phase:.2f} kVAr)
  Apparent Power @ PF={pf1}: {motor_input_kw / pf1:.2f} kVA
  Apparent Power @ PF={pf2}: {motor_input_kw / pf2:.2f} kVA

POWER TRIANGLE ANALYSIS:
  Initial Reactive Power Q₁ : {motor_input_kw * tan_phi1:.2f} kVAr (lagging)
  Final Reactive Power Q₂   : {motor_input_kw * tan_phi2:.2f} kVAr
  Capacitive kVAr Required  : {kvar_total:.2f} kVAr (leading)

CAPACITOR BANK CONFIGURATION:
  Connection Type           : Delta (Δ)
  Number of Phases          : 3
  Capacitors per Phase      : {n_capacitors} in series
  Voltage Rating per Cap    : {voltage / n_capacitors:.2f} V
  Total Capacitor Units     : {3 * n_capacitors}
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, results)

        # Store calculated values for simulation
        self.motor_input_kw = motor_input_kw
        self.kvar_total = kvar_total
        self.kvar_per_phase = kvar_per_phase
        self.C_phase_uf = C_phase_uf
        self.C_unit_uf = C_unit_uf
        self.I_c = I_c
        self.phi1 = phi1
        self.phi2 = phi2

    def ode_system(self, t, y):
        """
        ODE system for dynamic simulation of power factor correction
        y[0] = current power factor
        y[1] = current capacitance (μF)
        """
        pf_current = y[0]
        C_current = y[1]

        # Get target values
        pf_target = self.pf_final_var.get()
        C_target = self.C_phase_uf

        # Time constant for capacitor charging/power factor transition
        tau = self.sim_time_var.get() / 3  # Reach steady state in ~3*tau

        # Rate of change of power factor
        dpf_dt = (pf_target - pf_current) / tau

        # Rate of change of capacitance
        dC_dt = (C_target - C_current) / tau

        return [dpf_dt, dC_dt]

    def euler_method(self, f, y0, t_span, dt):
        """Euler method for ODE integration"""
        t_start, t_end = t_span
        t = np.arange(t_start, t_end, dt)
        y = np.zeros((len(t), len(y0)))
        y[0] = y0

        for i in range(1, len(t)):
            dy = f(t[i-1], y[i-1])
            y[i] = y[i-1] + np.array(dy) * dt

        return t, y

    def start_simulation(self):
        """Start the dynamic simulation"""
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        # Make sure visualization window is open
        if self.viz_window is None or not tk.Toplevel.winfo_exists(self.viz_window):
            self.create_visualization_window()
        elif self.viz_window.state() != 'normal':
            self.viz_window.deiconify()
            self.toggle_plots_button.config(text="Hide Plots")

        # Reset data
        self.time_data = []
        self.pf_data = []
        self.power_data = []
        self.reactive_power_data = []
        self.capacitance_data = []
        self.current_data = []

        # Initial conditions
        pf_initial = self.pf_initial_var.get()
        y0 = [pf_initial, 0.0]  # [power factor, capacitance]

        # Time span
        t_span = (0, self.sim_time_var.get())

        # Solve ODE
        if self.solver_var.get() == "RK45":
            # Use scipy's RK45 solver
            sol = solve_ivp(self.ode_system, t_span, y0, method='RK45',
                           max_step=0.01, dense_output=True)
            t_eval = np.linspace(0, self.sim_time_var.get(), 500)
            solution = sol.sol(t_eval)
            self.time_data = t_eval.tolist()
            self.pf_data = solution[0].tolist()
            self.capacitance_data = solution[1].tolist()
        else:
            # Use Euler method
            t_euler, y_euler = self.euler_method(self.ode_system, y0, t_span, self.dt)
            self.time_data = t_euler.tolist()
            self.pf_data = y_euler[:, 0].tolist()
            self.capacitance_data = y_euler[:, 1].tolist()

        # Calculate derived quantities
        for i in range(len(self.time_data)):
            pf = max(0.01, min(1.0, self.pf_data[i]))  # Clamp PF between 0.01 and 1.0
            C = self.capacitance_data[i]

            # Real power (constant)
            self.power_data.append(self.motor_input_kw)

            # Reactive power based on current PF
            phi = math.acos(pf)
            Q = self.motor_input_kw * math.tan(phi) - C * 2 * math.pi * self.frequency_var.get() * self.voltage_var.get()**2 / 1e9
            self.reactive_power_data.append(Q)

            # Capacitor current
            I_cap = 2 * math.pi * self.frequency_var.get() * C * 1e-6 * self.voltage_var.get()
            self.current_data.append(I_cap)

        # Animate the plots
        self.animate_plots()

    def stop_simulation(self):
        """Stop the simulation"""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def reset_simulation(self):
        """Reset the simulation"""
        self.stop_simulation()
        self.time_data = []
        self.pf_data = []
        self.power_data = []
        self.reactive_power_data = []
        self.capacitance_data = []
        self.current_data = []

        # Clear all plots if they exist
        if self.ax1 is not None:
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]:
                ax.clear()

            self.init_plots()
            if self.canvas:
                self.canvas.draw()

    def animate_plots(self):
        """Animate the plots with simulation data"""
        if not self.is_running or len(self.time_data) == 0:
            return

        if self.ax1 is None:
            self.create_visualization_window()

        # Clear previous plots
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        self.ax5.clear()
        self.ax6.clear()

        # Reinitialize plot settings
        self.init_plots()

        # Plot Power Factor with thicker lines
        self.ax1.plot(self.time_data, self.pf_data, 'b-', linewidth=3, label='Power Factor')
        self.ax1.axhline(y=self.pf_final_var.get(), color='r', linestyle='--',
                        linewidth=2, label=f'Target: {self.pf_final_var.get():.2f}')
        self.ax1.legend(fontsize=11, loc='best')

        # Plot Real Power
        self.ax2.plot(self.time_data, self.power_data, 'g-', linewidth=3, label='Real Power')
        self.ax2.legend(fontsize=11, loc='best')

        # Plot Reactive Power
        self.ax3.plot(self.time_data, self.reactive_power_data, 'r-', linewidth=3, label='Reactive Power')
        self.ax3.axhline(y=0, color='k', linestyle='-', linewidth=1)
        self.ax3.legend(fontsize=11, loc='best')

        # Plot Capacitance
        self.ax4.plot(self.time_data, self.capacitance_data, 'm-', linewidth=3, label='Capacitance')
        self.ax4.axhline(y=self.C_phase_uf, color='r', linestyle='--',
                        linewidth=2, label=f'Target: {self.C_phase_uf:.2f} μF')
        self.ax4.legend(fontsize=11, loc='best')

        # Plot Capacitor Current
        self.ax5.plot(self.time_data, self.current_data, 'c-', linewidth=3, label='Capacitor Current')
        self.ax5.legend(fontsize=11, loc='best')

        # Plot Power Triangle (animated)
        # Show initial and final states
        P = self.motor_input_kw
        Q_initial = P * math.tan(self.phi1)
        Q_final = P * math.tan(self.phi2)

        # Initial state
        self.ax6.arrow(0, 0, P, 0, head_width=30, head_length=20, fc='green', ec='green', linewidth=3)
        self.ax6.arrow(0, 0, 0, Q_initial, head_width=20, head_length=15, fc='red', ec='red', linewidth=3, alpha=0.5)
        self.ax6.plot([0, P], [0, Q_initial], 'b--', linewidth=2, alpha=0.5, label=f'Initial PF={self.pf_initial_var.get():.2f}')

        # Final state
        self.ax6.arrow(0, 0, 0, Q_final, head_width=20, head_length=15, fc='orange', ec='orange', linewidth=3)
        self.ax6.plot([0, P], [0, Q_final], 'g-', linewidth=3, label=f'Final PF={self.pf_final_var.get():.2f}')

        # Capacitor kVAr
        self.ax6.arrow(P*0.8, Q_initial, 0, Q_final - Q_initial, head_width=20, head_length=15,
                      fc='purple', ec='purple', linewidth=3, linestyle='--', alpha=0.7)

        self.ax6.text(P/2, -50, 'Real Power (P)', ha='center', fontsize=12, fontweight='bold')
        self.ax6.text(-50, Q_initial/2, 'Reactive\nPower (Q)', ha='center', fontsize=12, fontweight='bold')
        self.ax6.legend(fontsize=11, loc='upper right')

        # Adjust plot limits
        max_Q = max(abs(Q_initial), abs(Q_final)) * 1.2
        self.ax6.set_xlim([-P*0.1, P*1.2])
        self.ax6.set_ylim([-max_Q*0.1, max_Q])

        # Update canvas
        self.fig.tight_layout(pad=4.0)
        self.canvas.draw()

        self.stop_simulation()

    def on_resize(self, event):
        """Handle window resize event for main window"""
        pass  # Main window handles resize automatically

    def on_viz_resize(self, event):
        """Handle window resize event for visualization window"""
        try:
            if self.fig and self.canvas:
                self.fig.tight_layout(pad=4.0)
                self.canvas.draw()
        except Exception:
            pass  # Ignore errors during resize


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = PowerFactorCorrectionSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
