"""
Three-Phase Motor Capacitor Bank Calculator with Dynamic Simulation
Solves power factor correction problems with real-time ODE solver
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import ode
import math

class MotorCapacitorSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("3-Phase Motor Capacitor Bank Calculator & Simulator")
        self.root.geometry("1400x900")

        # Simulation parameters
        self.time_data = []
        self.pf_data = []
        self.voltage_data = []
        self.current_data = []
        self.solver_type = "RK45"
        self.is_simulating = False
        self.current_problem = 1

        # Problem parameters (default values)
        self.params = {
            'problem1': {
                'voltage': 400,
                'power_hp': 100,
                'frequency': 50,
                'pf_initial': 0.7,
                'pf_final': 0.95,
                'efficiency': 0.93,
                'capacitors_per_unit': 4,
                'capacitor_voltage': 100,
                'connection': 'delta'
            },
            'problem2': {
                'voltage': 2000,
                'power_hp': 400,
                'frequency': 50,
                'pf_initial': 0.75,
                'pf_final': 0.98,
                'efficiency': 0.85,
                'capacitors_per_unit': 1,
                'capacitor_voltage': 500,
                'connection': 'star-motor-delta-cap'
            },
            'problem3': {
                'voltage': 3000,
                'power_hp': 600,
                'frequency': 50,
                'pf_initial': 0.75,
                'pf_final': 0.98,
                'efficiency': 0.95,
                'capacitors_per_unit': 5,
                'capacitor_voltage': 600,
                'connection': 'delta'
            }
        }

        self.setup_ui()
        self.root.bind('<Configure>', self.on_window_resize)

    def setup_ui(self):
        """Setup the user interface with responsive layout"""
        # Configure grid weights for responsive design
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        # Top control panel
        self.setup_control_panel(main_container)

        # Content area with notebook
        content_frame = ttk.Frame(main_container)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=2)
        content_frame.grid_columnconfigure(1, weight=3)

        # Left panel - Controls and sliders
        self.setup_left_panel(content_frame)

        # Right panel - Visualization
        self.setup_right_panel(content_frame)

    def setup_control_panel(self, parent):
        """Setup top control panel"""
        control_frame = ttk.LabelFrame(parent, text="Simulation Controls", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Problem selector
        ttk.Label(control_frame, text="Problem:").grid(row=0, column=0, padx=5)
        self.problem_var = tk.StringVar(value="Problem 2 (100 HP, 400V)")
        problem_combo = ttk.Combobox(control_frame, textvariable=self.problem_var,
                                     values=[
                                         "Problem 2 (100 HP, 400V)",
                                         "Problem 3 (400 HP, 2000V)",
                                         "Problem 4 (600 HP, 3000V)"
                                     ], state='readonly', width=30)
        problem_combo.grid(row=0, column=1, padx=5)
        problem_combo.bind('<<ComboboxSelected>>', self.change_problem)

        # Solver selector
        ttk.Label(control_frame, text="ODE Solver:").grid(row=0, column=2, padx=5)
        self.solver_var = tk.StringVar(value="RK45")
        solver_combo = ttk.Combobox(control_frame, textvariable=self.solver_var,
                                    values=["RK45", "Euler"], state='readonly', width=10)
        solver_combo.grid(row=0, column=3, padx=5)
        solver_combo.bind('<<ComboboxSelected>>', self.change_solver)

        # Simulation buttons
        self.start_btn = ttk.Button(control_frame, text="Start Simulation",
                                    command=self.start_simulation)
        self.start_btn.grid(row=0, column=4, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="Stop Simulation",
                                   command=self.stop_simulation, state='disabled')
        self.stop_btn.grid(row=0, column=5, padx=5)

        ttk.Button(control_frame, text="Reset", command=self.reset_simulation).grid(
            row=0, column=6, padx=5)

        ttk.Button(control_frame, text="Calculate", command=self.calculate_results).grid(
            row=0, column=7, padx=5)

    def setup_left_panel(self, parent):
        """Setup left panel with parameter sliders"""
        left_frame = ttk.Frame(parent)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # Notebook for different parameter groups
        self.notebook = ttk.Notebook(left_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Parameters tab
        params_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(params_frame, text="Parameters")

        self.sliders = {}
        self.setup_parameter_sliders(params_frame)

        # Results tab
        results_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(results_frame, text="Results")

        self.results_text = tk.Text(results_frame, height=20, width=40, wrap=tk.WORD,
                                    font=('Courier', 10))
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical",
                                         command=self.results_text.yview)
        results_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_text.configure(yscrollcommand=results_scrollbar.set)

        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

    def setup_parameter_sliders(self, parent):
        """Setup parameter sliders based on current problem"""
        # Clear existing sliders
        for widget in parent.winfo_children():
            widget.destroy()
        self.sliders.clear()

        problem_key = f'problem{self.current_problem}'
        params = self.params[problem_key]

        row = 0

        # Voltage slider
        self.create_slider(parent, row, "Line Voltage (V)",
                          100, 5000, params['voltage'], 'voltage')
        row += 1

        # Power slider
        self.create_slider(parent, row, "Motor Power (HP)",
                          10, 1000, params['power_hp'], 'power_hp')
        row += 1

        # Frequency slider
        self.create_slider(parent, row, "Frequency (Hz)",
                          40, 60, params['frequency'], 'frequency')
        row += 1

        # Initial PF slider
        self.create_slider(parent, row, "Initial Power Factor",
                          0.5, 0.95, params['pf_initial'], 'pf_initial', resolution=0.01)
        row += 1

        # Final PF slider
        self.create_slider(parent, row, "Final Power Factor",
                          0.8, 1.0, params['pf_final'], 'pf_final', resolution=0.01)
        row += 1

        # Efficiency slider
        self.create_slider(parent, row, "Efficiency",
                          0.7, 1.0, params['efficiency'], 'efficiency', resolution=0.01)
        row += 1

        # Connection type
        ttk.Label(parent, text=f"Connection: {params['connection']}").grid(
            row=row, column=0, columnspan=2, pady=10, sticky=tk.W)
        row += 1

        # Capacitor configuration
        ttk.Label(parent, text=f"Capacitors per unit: {params['capacitors_per_unit']}").grid(
            row=row, column=0, columnspan=2, pady=5, sticky=tk.W)
        row += 1

        ttk.Label(parent, text=f"Capacitor voltage rating: {params['capacitor_voltage']} V").grid(
            row=row, column=0, columnspan=2, pady=5, sticky=tk.W)

    def create_slider(self, parent, row, label, from_, to, initial, key, resolution=1):
        """Create a labeled slider"""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text=label).grid(row=0, column=0, sticky=tk.W)

        var = tk.DoubleVar(value=initial)
        slider = ttk.Scale(frame, from_=from_, to=to, variable=var, orient=tk.HORIZONTAL,
                          command=lambda v: self.update_slider_label(key, v))
        slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)

        value_label = ttk.Label(frame, text=f"{initial:.2f}")
        value_label.grid(row=0, column=2, sticky=tk.W)

        self.sliders[key] = {'var': var, 'label': value_label, 'slider': slider}

    def update_slider_label(self, key, value):
        """Update slider value label"""
        val = float(value)
        self.sliders[key]['label'].config(text=f"{val:.2f}")

    def setup_right_panel(self, parent):
        """Setup right panel with visualizations"""
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.patch.set_facecolor('#f0f0f0')

        # Create subplots
        self.ax1 = self.fig.add_subplot(3, 1, 1)
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        self.ax3 = self.fig.add_subplot(3, 1, 3)

        self.fig.tight_layout(pad=3.0)

        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initialize plots
        self.initialize_plots()

    def initialize_plots(self):
        """Initialize empty plots"""
        self.ax1.clear()
        self.ax1.set_title('Power Factor vs Time', fontsize=10, fontweight='bold')
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Power Factor')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.set_ylim([0, 1.1])

        self.ax2.clear()
        self.ax2.set_title('Voltage vs Time', fontsize=10, fontweight='bold')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Voltage (V)')
        self.ax2.grid(True, alpha=0.3)

        self.ax3.clear()
        self.ax3.set_title('Current vs Time', fontsize=10, fontweight='bold')
        self.ax3.set_xlabel('Time (s)')
        self.ax3.set_ylabel('Current (A)')
        self.ax3.grid(True, alpha=0.3)

        self.canvas.draw()

    def change_problem(self, event=None):
        """Change the current problem"""
        problem_map = {
            "Problem 2 (100 HP, 400V)": 1,
            "Problem 3 (400 HP, 2000V)": 2,
            "Problem 4 (600 HP, 3000V)": 3
        }
        self.current_problem = problem_map[self.problem_var.get()]
        self.setup_parameter_sliders(self.notebook.winfo_children()[0])
        self.reset_simulation()

    def change_solver(self, event=None):
        """Change ODE solver"""
        self.solver_type = self.solver_var.get()

    def get_current_params(self):
        """Get current parameter values from sliders"""
        problem_key = f'problem{self.current_problem}'
        params = self.params[problem_key].copy()

        for key, slider_data in self.sliders.items():
            params[key] = slider_data['var'].get()

        return params

    def calculate_capacitance(self, params):
        """Calculate required capacitance for power factor correction"""
        # Convert HP to Watts
        P_out = params['power_hp'] * 745.7  # 1 HP = 745.7 W

        # Calculate input power
        P_in = P_out / params['efficiency']

        # Calculate initial reactive power
        phi1 = math.acos(params['pf_initial'])
        Q1 = P_in * math.tan(phi1)

        # Calculate final reactive power
        phi2 = math.acos(params['pf_final'])
        Q2 = P_in * math.tan(phi2)

        # Reactive power to be compensated
        Q_c = Q1 - Q2

        # Line voltage
        V_L = params['voltage']

        # Angular frequency
        omega = 2 * math.pi * params['frequency']

        # For delta connection: Q_c = 3 * V_L^2 * omega * C
        # C = Q_c / (3 * V_L^2 * omega)
        C_total = Q_c / (3 * V_L**2 * omega)

        # Calculate current
        I_initial = P_in / (math.sqrt(3) * V_L * params['pf_initial'])
        I_final = P_in / (math.sqrt(3) * V_L * params['pf_final'])

        # Capacitor configuration
        n_caps = params['capacitors_per_unit']
        V_cap = params['capacitor_voltage']

        # For capacitors in series: C_eq = C / n
        # Voltage across each capacitor in series: V_L / n
        # Therefore: C_individual = C_total * n (for series configuration)

        # Check if voltage rating is appropriate
        if n_caps > 1:
            # Series configuration
            required_voltage = V_L / math.sqrt(3)  # Phase voltage
            C_individual = C_total * n_caps
        else:
            C_individual = C_total
            required_voltage = V_L

        results = {
            'P_out': P_out,
            'P_in': P_in,
            'Q1': Q1,
            'Q2': Q2,
            'Q_c': Q_c,
            'C_total': C_total,
            'C_individual': C_individual,
            'I_initial': I_initial,
            'I_final': I_final,
            'capacitance_uF': C_individual * 1e6,  # Convert to microfarads
            'n_capacitors': n_caps,
            'required_voltage': required_voltage
        }

        return results

    def calculate_results(self):
        """Calculate and display results"""
        params = self.get_current_params()
        results = self.calculate_capacitance(params)

        # Format results
        output = "=" * 50 + "\n"
        output += f"PROBLEM {self.current_problem} RESULTS\n"
        output += "=" * 50 + "\n\n"

        output += "MOTOR PARAMETERS:\n"
        output += f"  Line Voltage: {params['voltage']:.2f} V\n"
        output += f"  Power Output: {params['power_hp']:.2f} HP ({results['P_out']:.2f} W)\n"
        output += f"  Frequency: {params['frequency']:.2f} Hz\n"
        output += f"  Efficiency: {params['efficiency']*100:.2f}%\n"
        output += f"  Connection: {params['connection']}\n\n"

        output += "POWER FACTOR CORRECTION:\n"
        output += f"  Initial PF: {params['pf_initial']:.3f} lagging\n"
        output += f"  Final PF: {params['pf_final']:.3f} lagging\n\n"

        output += "POWER CALCULATIONS:\n"
        output += f"  Input Power (P): {results['P_in']:.2f} W\n"
        output += f"  Initial Reactive Power (Q1): {results['Q1']:.2f} VAR\n"
        output += f"  Final Reactive Power (Q2): {results['Q2']:.2f} VAR\n"
        output += f"  Compensating Reactive Power (Qc): {results['Q_c']:.2f} VAR\n\n"

        output += "CURRENT:\n"
        output += f"  Initial Line Current: {results['I_initial']:.2f} A\n"
        output += f"  Final Line Current: {results['I_final']:.2f} A\n"
        output += f"  Current Reduction: {results['I_initial'] - results['I_final']:.2f} A\n\n"

        output += "CAPACITOR BANK:\n"
        output += f"  Total Capacitance per Phase: {results['C_total']*1e6:.4f} µF\n"
        output += f"  Capacitors per Unit: {params['capacitors_per_unit']}\n"
        output += f"  Capacitor Voltage Rating: {params['capacitor_voltage']} V\n"
        output += f"  Required Voltage: {results['required_voltage']:.2f} V\n\n"

        output += "*** CAPACITANCE OF EACH CAPACITOR ***\n"
        output += f"  C = {results['capacitance_uF']:.4f} µF\n"
        output += f"  C = {results['C_individual']:.6e} F\n\n"

        # Display results
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, output)

    def motor_dynamics(self, t, y, params, target_pf):
        """
        ODE system for motor dynamics
        y[0] = power factor
        y[1] = voltage
        y[2] = current
        """
        pf, voltage, current = y

        # Time constant for power factor change (seconds)
        tau_pf = 2.0

        # Power factor dynamics (exponential approach to target)
        dpf_dt = (target_pf - pf) / tau_pf

        # Voltage dynamics (small oscillations around nominal)
        freq = 2 * math.pi * params['frequency']
        dv_dt = 0.01 * params['voltage'] * math.sin(freq * t)

        # Current calculation based on power factor
        P_out = params['power_hp'] * 745.7
        P_in = P_out / params['efficiency']

        if pf > 0.01:  # Avoid division by zero
            target_current = P_in / (math.sqrt(3) * params['voltage'] * pf)
        else:
            target_current = current

        tau_i = 1.0
        di_dt = (target_current - current) / tau_i

        return [dpf_dt, dv_dt, di_dt]

    def euler_step(self, f, t, y, h, params, target_pf):
        """Euler method integration step"""
        dydt = f(t, y, params, target_pf)
        return y + h * np.array(dydt)

    def rk45_step(self, f, t, y, h, params, target_pf):
        """RK45 (4th order Runge-Kutta) integration step"""
        k1 = np.array(f(t, y, params, target_pf))
        k2 = np.array(f(t + h/2, y + h*k1/2, params, target_pf))
        k3 = np.array(f(t + h/2, y + h*k2/2, params, target_pf))
        k4 = np.array(f(t + h, y + h*k3, params, target_pf))

        return y + h * (k1 + 2*k2 + 2*k3 + k4) / 6

    def start_simulation(self):
        """Start dynamic simulation"""
        self.is_simulating = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        # Reset data
        self.time_data = []
        self.pf_data = []
        self.voltage_data = []
        self.current_data = []

        # Get parameters
        params = self.get_current_params()

        # Initial conditions
        P_out = params['power_hp'] * 745.7
        P_in = P_out / params['efficiency']
        I_initial = P_in / (math.sqrt(3) * params['voltage'] * params['pf_initial'])

        y0 = [params['pf_initial'], params['voltage'], I_initial]

        # Simulation parameters
        t = 0
        dt = 0.05  # Time step
        t_max = 10.0  # Total simulation time

        self.run_simulation_step(t, y0, dt, t_max, params)

    def run_simulation_step(self, t, y, dt, t_max, params):
        """Run one simulation step and schedule next"""
        if not self.is_simulating or t >= t_max:
            self.stop_simulation()
            return

        # Store data
        self.time_data.append(t)
        self.pf_data.append(y[0])
        self.voltage_data.append(y[1])
        self.current_data.append(y[2])

        # Update plots
        self.update_plots()

        # Integrate one step
        if self.solver_type == "Euler":
            y_new = self.euler_step(self.motor_dynamics, t, y, dt, params, params['pf_final'])
        else:  # RK45
            y_new = self.rk45_step(self.motor_dynamics, t, y, dt, params, params['pf_final'])

        # Clamp values to physical limits
        y_new[0] = np.clip(y_new[0], 0.0, 1.0)  # Power factor
        y_new[1] = np.clip(y_new[1], 0.5 * params['voltage'], 1.5 * params['voltage'])  # Voltage
        y_new[2] = np.clip(y_new[2], 0.0, 10000.0)  # Current

        # Schedule next step
        self.root.after(50, lambda: self.run_simulation_step(t + dt, y_new, dt, t_max, params))

    def update_plots(self):
        """Update dynamic plots"""
        if len(self.time_data) < 2:
            return

        # Power Factor plot
        self.ax1.clear()
        self.ax1.plot(self.time_data, self.pf_data, 'b-', linewidth=2, label='Power Factor')
        params = self.get_current_params()
        self.ax1.axhline(y=params['pf_initial'], color='r', linestyle='--',
                        label=f'Initial PF={params["pf_initial"]:.2f}')
        self.ax1.axhline(y=params['pf_final'], color='g', linestyle='--',
                        label=f'Target PF={params["pf_final"]:.2f}')
        self.ax1.set_title('Power Factor vs Time', fontsize=10, fontweight='bold')
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Power Factor')
        self.ax1.legend(loc='best', fontsize=8)
        self.ax1.grid(True, alpha=0.3)
        self.ax1.set_ylim([0, 1.1])

        # Voltage plot
        self.ax2.clear()
        self.ax2.plot(self.time_data, self.voltage_data, 'r-', linewidth=2)
        self.ax2.set_title('Voltage vs Time', fontsize=10, fontweight='bold')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Voltage (V)')
        self.ax2.grid(True, alpha=0.3)

        # Current plot
        self.ax3.clear()
        self.ax3.plot(self.time_data, self.current_data, 'g-', linewidth=2)
        self.ax3.set_title('Current vs Time', fontsize=10, fontweight='bold')
        self.ax3.set_xlabel('Time (s)')
        self.ax3.set_ylabel('Current (A)')
        self.ax3.grid(True, alpha=0.3)

        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    def stop_simulation(self):
        """Stop simulation"""
        self.is_simulating = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def reset_simulation(self):
        """Reset simulation"""
        self.stop_simulation()
        self.time_data = []
        self.pf_data = []
        self.voltage_data = []
        self.current_data = []
        self.initialize_plots()

    def on_window_resize(self, event):
        """Handle window resize event"""
        if event.widget == self.root:
            # Redraw canvas on resize
            try:
                self.fig.tight_layout(pad=2.0)
                self.canvas.draw()
            except Exception:
                pass  # Ignore errors during resize


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = MotorCapacitorSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
