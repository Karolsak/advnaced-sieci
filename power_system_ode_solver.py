#!/usr/bin/env python3
"""
Power System ODE Solver with Tkinter GUI
Example 8.10: Two Power Stations Operating in Parallel

Features:
- Dynamic simulation with RK45 and Euler methods
- Real-time visualization
- Interactive sliders
- Automatic window resizing
- Three simulation scenarios
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp
import threading
import time


class PowerSystemODESolver:
    """ODE solver for power system dynamics"""

    def __init__(self):
        # Station parameters
        self.capacity_A = 75.0  # MW
        self.capacity_B = 200.0  # MW
        self.regulation_A = 0.04  # 4%
        self.regulation_B = 0.02  # 2%

        # System dynamics parameters
        self.inertia_A = 5.0  # seconds
        self.inertia_B = 10.0  # seconds
        self.damping_A = 0.1
        self.damping_B = 0.1

        # Load parameters
        self.load_A = 100.0  # MW
        self.load_B = 100.0  # MW

        # Simulation parameters
        self.simulation_time = 20.0  # seconds
        self.dt = 0.01  # time step for Euler method

        # Current scenario
        self.scenario = 1

    def power_system_dynamics(self, t, state):
        """
        ODE system for two interconnected power stations

        State vector: [f, P_A, P_B, delta_f_A, delta_f_B]
        where:
        - f: system frequency deviation (p.u.)
        - P_A: Power output of station A (MW)
        - P_B: Power output of station B (MW)
        - delta_f_A: frequency deviation at station A
        - delta_f_B: frequency deviation at station B
        """
        f, P_A, P_B, delta_f_A, delta_f_B = state

        # Total load
        total_load = self.load_A + self.load_B

        # Target power outputs based on droop characteristics
        # P = Capacity * (1 - regulation * delta_f)
        P_A_target = self.capacity_A * (1.0 - self.regulation_A * delta_f_A)
        P_B_target = self.capacity_B * (1.0 - self.regulation_B * delta_f_B)

        # Limit power outputs to physical constraints
        P_A_target = max(0, min(self.capacity_A, P_A_target))
        P_B_target = max(0, min(self.capacity_B, P_B_target))

        # Governor dynamics (first-order lag)
        tau_gov = 0.5  # governor time constant
        dP_A_dt = (P_A_target - P_A) / tau_gov
        dP_B_dt = (P_B_target - P_B) / tau_gov

        # System frequency dynamics
        # H * df/dt = P_gen - P_load - D * f
        total_inertia = self.inertia_A + self.inertia_B
        total_damping = self.damping_A + self.damping_B

        df_dt = ((P_A + P_B) - total_load - total_damping * f) / total_inertia

        # Individual station frequency deviations
        d_delta_f_A_dt = (f - delta_f_A) / 0.2  # coupling dynamics
        d_delta_f_B_dt = (f - delta_f_B) / 0.2

        return [df_dt, dP_A_dt, dP_B_dt, d_delta_f_A_dt, d_delta_f_B_dt]

    def solve_rk45(self):
        """Solve using RK45 method (scipy)"""
        # Initial conditions: [f, P_A, P_B, delta_f_A, delta_f_B]
        initial_state = [0.0, 50.0, 100.0, 0.0, 0.0]

        t_span = (0, self.simulation_time)
        t_eval = np.linspace(0, self.simulation_time, 1000)

        solution = solve_ivp(
            self.power_system_dynamics,
            t_span,
            initial_state,
            method='RK45',
            t_eval=t_eval,
            max_step=0.1
        )

        return solution.t, solution.y

    def solve_euler(self):
        """Solve using Euler method"""
        # Initial conditions
        state = np.array([0.0, 50.0, 100.0, 0.0, 0.0])

        n_steps = int(self.simulation_time / self.dt)
        t = np.zeros(n_steps)
        solution = np.zeros((5, n_steps))

        solution[:, 0] = state

        for i in range(1, n_steps):
            t[i] = i * self.dt
            derivatives = self.power_system_dynamics(t[i-1], state)
            state = state + self.dt * np.array(derivatives)
            solution[:, i] = state

        return t, solution

    def calculate_steady_state(self):
        """Calculate analytical steady-state values"""
        total_load = self.load_A + self.load_B

        # From speed regulation equations:
        # 5.33 * P_A = P_B
        # P_A + P_B = Total Load

        P_A_ss = total_load / (1.0 + 5.33)
        P_B_ss = 5.33 * P_A_ss

        # Tie-line power
        P_tie_AB = P_A_ss - self.load_A  # From A to B (negative means B to A)

        # Frequency deviation (from regulation equation)
        # (1 - f) = regulation * P / Capacity
        f_deviation_A = 1.0 - (1.0 - self.regulation_A * P_A_ss / self.capacity_A)
        f_deviation_B = 1.0 - (1.0 - self.regulation_B * P_B_ss / self.capacity_B)

        return {
            'P_A': P_A_ss,
            'P_B': P_B_ss,
            'P_tie': P_tie_AB,
            'f_dev_A': f_deviation_A,
            'f_dev_B': f_deviation_B
        }


class PowerSystemGUI:
    """Tkinter GUI for power system simulation"""

    def __init__(self, root):
        self.root = root
        self.root.title("Power System ODE Solver - Example 8.10")
        self.root.geometry("1400x900")

        # Initialize solver
        self.solver = PowerSystemODESolver()

        # Simulation state
        self.is_simulating = False
        self.animation_thread = None

        # Setup GUI
        self.setup_gui()

        # Bind resize event
        self.root.bind('<Configure>', self.on_window_resize)

    def setup_gui(self):
        """Setup the GUI layout"""
        # Main container with grid layout
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure grid weights for responsive design
        self.main_container.grid_rowconfigure(0, weight=0)  # Title
        self.main_container.grid_rowconfigure(1, weight=1)  # Main content
        self.main_container.grid_rowconfigure(2, weight=0)  # Status
        self.main_container.grid_columnconfigure(0, weight=1)

        # Title
        self.setup_title()

        # Content area (sliders + plots)
        self.content_frame = ttk.Frame(self.main_container)
        self.content_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=0)  # Sliders
        self.content_frame.grid_columnconfigure(1, weight=1)  # Plots

        # Setup components
        self.setup_sliders()
        self.setup_plots()
        self.setup_status_bar()

    def setup_title(self):
        """Setup title section"""
        title_frame = ttk.Frame(self.main_container)
        title_frame.grid(row=0, column=0, sticky='ew', pady=5)

        title_label = ttk.Label(
            title_frame,
            text="Two Power Stations Operating in Parallel - Example 8.10",
            font=('Arial', 14, 'bold')
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="Station A: 75 MW (4% regulation) | Station B: 200 MW (2% regulation)",
            font=('Arial', 10)
        )
        subtitle_label.pack()

    def setup_sliders(self):
        """Setup parameter sliders"""
        slider_frame = ttk.LabelFrame(self.content_frame, text="Parameters", padding=10)
        slider_frame.grid(row=0, column=0, sticky='nsew', padx=5)

        # Create canvas with scrollbar for sliders
        canvas = tk.Canvas(slider_frame, width=350)
        scrollbar = ttk.Scrollbar(slider_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Scenario selection
        ttk.Label(scrollable_frame, text="Scenario Selection", font=('Arial', 11, 'bold')).pack(pady=5)

        self.scenario_var = tk.IntVar(value=1)
        scenarios = [
            ("(a) Load on each station = 100 MW", 1),
            ("(b) Loads: 50 MW @ A, 150 MW @ B", 2),
            ("(c) Load: 130 MW @ A only", 3)
        ]

        for text, value in scenarios:
            ttk.Radiobutton(
                scrollable_frame,
                text=text,
                variable=self.scenario_var,
                value=value,
                command=self.on_scenario_change
            ).pack(anchor='w', padx=20)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # Station parameters
        ttk.Label(scrollable_frame, text="Station Parameters", font=('Arial', 11, 'bold')).pack(pady=5)

        self.sliders = {}

        # Capacity sliders
        self.add_slider(scrollable_frame, "Capacity A (MW)", 10, 150, 75, 'capacity_A')
        self.add_slider(scrollable_frame, "Capacity B (MW)", 50, 400, 200, 'capacity_B')

        # Regulation sliders
        self.add_slider(scrollable_frame, "Regulation A (%)", 1, 10, 4, 'regulation_A', resolution=0.1)
        self.add_slider(scrollable_frame, "Regulation B (%)", 1, 10, 2, 'regulation_B', resolution=0.1)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # Load parameters
        ttk.Label(scrollable_frame, text="Load Parameters", font=('Arial', 11, 'bold')).pack(pady=5)

        self.add_slider(scrollable_frame, "Load A (MW)", 0, 200, 100, 'load_A')
        self.add_slider(scrollable_frame, "Load B (MW)", 0, 300, 100, 'load_B')

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # System dynamics parameters
        ttk.Label(scrollable_frame, text="Dynamics Parameters", font=('Arial', 11, 'bold')).pack(pady=5)

        self.add_slider(scrollable_frame, "Inertia A (s)", 1, 20, 5, 'inertia_A', resolution=0.5)
        self.add_slider(scrollable_frame, "Inertia B (s)", 1, 20, 10, 'inertia_B', resolution=0.5)
        self.add_slider(scrollable_frame, "Damping A", 0.01, 1.0, 0.1, 'damping_A', resolution=0.01)
        self.add_slider(scrollable_frame, "Damping B", 0.01, 1.0, 0.1, 'damping_B', resolution=0.01)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # Simulation parameters
        ttk.Label(scrollable_frame, text="Simulation Parameters", font=('Arial', 11, 'bold')).pack(pady=5)

        self.add_slider(scrollable_frame, "Sim Time (s)", 5, 60, 20, 'simulation_time', resolution=1)
        self.add_slider(scrollable_frame, "Euler dt (s)", 0.001, 0.1, 0.01, 'dt', resolution=0.001)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # Solver selection
        ttk.Label(scrollable_frame, text="ODE Solver", font=('Arial', 11, 'bold')).pack(pady=5)

        self.solver_var = tk.StringVar(value="RK45")
        ttk.Radiobutton(scrollable_frame, text="RK45 (Adaptive)", variable=self.solver_var, value="RK45").pack(anchor='w', padx=20)
        ttk.Radiobutton(scrollable_frame, text="Euler (Fixed Step)", variable=self.solver_var, value="Euler").pack(anchor='w', padx=20)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        # Control buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Simulation", command=self.start_simulation)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_simulation, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Reset", command=self.reset_simulation).grid(row=1, column=0, columnspan=2, pady=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add_slider(self, parent, label, min_val, max_val, default, param_name, resolution=1):
        """Add a labeled slider"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=3, padx=5)

        label_widget = ttk.Label(frame, text=label, width=20, anchor='w')
        label_widget.pack(side='left')

        value_var = tk.DoubleVar(value=default)
        value_label = ttk.Label(frame, text=f"{default:.3f}", width=8, anchor='e')
        value_label.pack(side='right')

        slider = ttk.Scale(
            frame,
            from_=min_val,
            to=max_val,
            orient='horizontal',
            variable=value_var,
            command=lambda v: self.on_slider_change(param_name, value_var, value_label, resolution)
        )
        slider.pack(side='right', fill='x', expand=True, padx=5)

        self.sliders[param_name] = {
            'var': value_var,
            'label': value_label,
            'slider': slider,
            'resolution': resolution
        }

    def on_slider_change(self, param_name, value_var, value_label, resolution):
        """Handle slider value change"""
        value = value_var.get()

        # Round to resolution
        value = round(value / resolution) * resolution

        # Update label
        value_label.config(text=f"{value:.3f}")

        # Update solver parameter
        if param_name in ['regulation_A', 'regulation_B']:
            setattr(self.solver, param_name, value / 100.0)  # Convert percentage to decimal
        else:
            setattr(self.solver, param_name, value)

    def on_scenario_change(self):
        """Handle scenario change"""
        scenario = self.scenario_var.get()
        self.solver.scenario = scenario

        if scenario == 1:
            # (a) Load on each station = 100 MW
            self.sliders['load_A']['var'].set(100)
            self.sliders['load_B']['var'].set(100)
        elif scenario == 2:
            # (b) Loads: 50 MW @ A, 150 MW @ B
            self.sliders['load_A']['var'].set(50)
            self.sliders['load_B']['var'].set(150)
        elif scenario == 3:
            # (c) Load: 130 MW @ A only
            self.sliders['load_A']['var'].set(130)
            self.sliders['load_B']['var'].set(0)

        # Update solver
        self.solver.load_A = self.sliders['load_A']['var'].get()
        self.solver.load_B = self.sliders['load_B']['var'].get()

        # Update labels
        self.sliders['load_A']['label'].config(text=f"{self.solver.load_A:.3f}")
        self.sliders['load_B']['label'].config(text=f"{self.solver.load_B:.3f}")

    def setup_plots(self):
        """Setup matplotlib plots"""
        plot_frame = ttk.LabelFrame(self.content_frame, text="Results Visualization", padding=10)
        plot_frame.grid(row=0, column=1, sticky='nsew', padx=5)
        plot_frame.grid_rowconfigure(0, weight=1)
        plot_frame.grid_columnconfigure(0, weight=1)

        # Create figure with subplots
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.tight_layout(pad=3.0)

        # Create subplots
        self.ax1 = self.fig.add_subplot(3, 2, 1)
        self.ax2 = self.fig.add_subplot(3, 2, 2)
        self.ax3 = self.fig.add_subplot(3, 2, 3)
        self.ax4 = self.fig.add_subplot(3, 2, 4)
        self.ax5 = self.fig.add_subplot(3, 2, 5)
        self.ax6 = self.fig.add_subplot(3, 2, 6)

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

        # Initialize plots
        self.update_plots_initial()

    def update_plots_initial(self):
        """Initialize empty plots"""
        plots = [
            (self.ax1, "Frequency Deviation", "Time (s)", "Frequency (Hz)"),
            (self.ax2, "Power Output Station A", "Time (s)", "Power (MW)"),
            (self.ax3, "Power Output Station B", "Time (s)", "Power (MW)"),
            (self.ax4, "Tie-Line Power", "Time (s)", "Power (MW)"),
            (self.ax5, "Total Generation vs Load", "Time (s)", "Power (MW)"),
            (self.ax6, "Steady-State Analysis", "", "Power (MW)")
        ]

        for ax, title, xlabel, ylabel in plots:
            ax.clear()
            ax.set_title(title, fontsize=10, fontweight='bold')
            ax.set_xlabel(xlabel, fontsize=8)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)

        self.canvas.draw()

    def update_plots(self, t, solution, steady_state):
        """Update plots with simulation results"""
        # Clear all axes
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]:
            ax.clear()
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)

        # Extract solution components
        f = solution[0] * 50  # Convert to Hz (assuming 50 Hz base)
        P_A = solution[1]
        P_B = solution[2]

        # Calculate tie-line power
        P_tie = P_A - self.solver.load_A

        # Plot 1: Frequency deviation
        self.ax1.plot(t, f, 'b-', linewidth=2, label='Frequency')
        self.ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Nominal')
        self.ax1.set_title("Frequency Deviation", fontsize=10, fontweight='bold')
        self.ax1.set_xlabel("Time (s)", fontsize=8)
        self.ax1.set_ylabel("Frequency Deviation (Hz)", fontsize=8)
        self.ax1.legend(fontsize=7)

        # Plot 2: Power output Station A
        self.ax2.plot(t, P_A, 'g-', linewidth=2, label='Station A Output')
        self.ax2.axhline(y=steady_state['P_A'], color='r', linestyle='--', alpha=0.5,
                        label=f'Steady-State: {steady_state["P_A"]:.2f} MW')
        self.ax2.axhline(y=self.solver.capacity_A, color='orange', linestyle=':', alpha=0.5, label='Capacity')
        self.ax2.set_title("Power Output Station A", fontsize=10, fontweight='bold')
        self.ax2.set_xlabel("Time (s)", fontsize=8)
        self.ax2.set_ylabel("Power (MW)", fontsize=8)
        self.ax2.legend(fontsize=7)

        # Plot 3: Power output Station B
        self.ax3.plot(t, P_B, 'm-', linewidth=2, label='Station B Output')
        self.ax3.axhline(y=steady_state['P_B'], color='r', linestyle='--', alpha=0.5,
                        label=f'Steady-State: {steady_state["P_B"]:.2f} MW')
        self.ax3.axhline(y=self.solver.capacity_B, color='orange', linestyle=':', alpha=0.5, label='Capacity')
        self.ax3.set_title("Power Output Station B", fontsize=10, fontweight='bold')
        self.ax3.set_xlabel("Time (s)", fontsize=8)
        self.ax3.set_ylabel("Power (MW)", fontsize=8)
        self.ax3.legend(fontsize=7)

        # Plot 4: Tie-line power
        self.ax4.plot(t, P_tie, 'c-', linewidth=2, label='Tie-Line Power')
        self.ax4.axhline(y=steady_state['P_tie'], color='r', linestyle='--', alpha=0.5,
                        label=f'Steady-State: {steady_state["P_tie"]:.2f} MW')
        self.ax4.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        self.ax4.set_title("Tie-Line Power (A → B)", fontsize=10, fontweight='bold')
        self.ax4.set_xlabel("Time (s)", fontsize=8)
        self.ax4.set_ylabel("Power (MW)", fontsize=8)
        self.ax4.legend(fontsize=7)

        # Plot 5: Total generation vs load
        total_gen = P_A + P_B
        total_load = self.solver.load_A + self.solver.load_B

        self.ax5.plot(t, total_gen, 'b-', linewidth=2, label='Total Generation')
        self.ax5.axhline(y=total_load, color='r', linestyle='--', alpha=0.5,
                        label=f'Total Load: {total_load:.2f} MW')
        self.ax5.set_title("Total Generation vs Load", fontsize=10, fontweight='bold')
        self.ax5.set_xlabel("Time (s)", fontsize=8)
        self.ax5.set_ylabel("Power (MW)", fontsize=8)
        self.ax5.legend(fontsize=7)
        self.ax5.fill_between(t, 0, total_gen, alpha=0.2, color='blue')

        # Plot 6: Steady-state bar chart
        categories = ['Station A\nOutput', 'Station B\nOutput', 'Load A', 'Load B', 'Tie-Line\nPower']
        values = [steady_state['P_A'], steady_state['P_B'],
                 self.solver.load_A, self.solver.load_B, abs(steady_state['P_tie'])]
        colors = ['green', 'magenta', 'orange', 'orange', 'cyan']

        bars = self.ax6.bar(categories, values, color=colors, alpha=0.7, edgecolor='black')
        self.ax6.set_title("Steady-State Analysis", fontsize=10, fontweight='bold')
        self.ax6.set_ylabel("Power (MW)", fontsize=8)

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.ax6.text(bar.get_x() + bar.get_width()/2., height,
                         f'{value:.2f}',
                         ha='center', va='bottom', fontsize=7)

        self.ax6.tick_params(axis='x', labelsize=7)

        # Adjust layout
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    def setup_status_bar(self):
        """Setup status bar"""
        status_frame = ttk.Frame(self.main_container)
        status_frame.grid(row=2, column=0, sticky='ew', pady=5)

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w')
        status_label.pack(fill='x')

    def start_simulation(self):
        """Start the simulation"""
        if self.is_simulating:
            return

        self.is_simulating = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

        # Run simulation in separate thread
        self.animation_thread = threading.Thread(target=self.run_simulation)
        self.animation_thread.daemon = True
        self.animation_thread.start()

    def run_simulation(self):
        """Run the simulation"""
        try:
            self.update_status("Running simulation...")

            # Get solver method
            solver_method = self.solver_var.get()

            # Solve ODE
            if solver_method == "RK45":
                self.update_status("Solving with RK45 method...")
                t, solution = self.solver.solve_rk45()
            else:
                self.update_status("Solving with Euler method...")
                t, solution = self.solver.solve_euler()

            # Calculate steady-state
            steady_state = self.solver.calculate_steady_state()

            # Update plots
            self.update_status("Updating plots...")
            self.root.after(0, lambda: self.update_plots(t, solution, steady_state))

            # Update status with results
            status_text = (
                f"Simulation Complete | "
                f"Method: {solver_method} | "
                f"P_A: {steady_state['P_A']:.2f} MW | "
                f"P_B: {steady_state['P_B']:.2f} MW | "
                f"Tie-Line: {steady_state['P_tie']:.2f} MW"
            )
            self.update_status(status_text)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            self.is_simulating = False
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))

    def stop_simulation(self):
        """Stop the simulation"""
        self.is_simulating = False
        self.update_status("Simulation stopped")

    def reset_simulation(self):
        """Reset simulation to default values"""
        # Reset scenario
        self.scenario_var.set(1)
        self.on_scenario_change()

        # Reset sliders
        defaults = {
            'capacity_A': 75,
            'capacity_B': 200,
            'regulation_A': 4,
            'regulation_B': 2,
            'load_A': 100,
            'load_B': 100,
            'inertia_A': 5,
            'inertia_B': 10,
            'damping_A': 0.1,
            'damping_B': 0.1,
            'simulation_time': 20,
            'dt': 0.01
        }

        for param, value in defaults.items():
            self.sliders[param]['var'].set(value)
            if param in ['regulation_A', 'regulation_B']:
                setattr(self.solver, param, value / 100.0)
            else:
                setattr(self.solver, param, value)
            self.sliders[param]['label'].config(text=f"{value:.3f}")

        # Clear plots
        self.update_plots_initial()
        self.update_status("Reset to default values")

    def update_status(self, message):
        """Update status bar"""
        self.root.after(0, lambda: self.status_var.set(message))

    def on_window_resize(self, event):
        """Handle window resize event"""
        # Only process resize for main window
        if event.widget == self.root:
            try:
                # Adjust figure size based on window size
                width = event.width
                height = event.height

                # Calculate appropriate figure size
                fig_width = max(8, (width - 400) / 100)
                fig_height = max(6, (height - 200) / 100)

                self.fig.set_size_inches(fig_width, fig_height)
                self.canvas.draw()
            except:
                pass  # Ignore resize errors during initialization


def main():
    """Main entry point"""
    root = tk.Tk()
    app = PowerSystemGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
