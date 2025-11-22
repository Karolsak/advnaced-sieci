import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.integrate import solve_ivp


def calculate_break_even_load_factor(
    capacity_mva: float,
    capital_crore: float,
    recurring_crore: float,
    tariff_paise: float,
    interest_pct: float,
    depreciation_pct: float,
    loss_pct: float,
    power_factor: float,
) -> float:
    """Return the load factor that produces zero profit.

    Parameters are interpreted using standard electrical utility units. The
    result is returned as a fraction (0-1). If calculation would exceed 1,
    the value is clipped at 1.
    """
    if capacity_mva <= 0 or power_factor <= 0:
        return 0.0

    tariff_rs = tariff_paise / 100.0
    capacity_mw = capacity_mva * power_factor
    annual_hours = 8760.0
    capital_rs = capital_crore * 1e7
    recurring_rs = recurring_crore * 1e7
    capital_charges_rs = capital_rs * (interest_pct + depreciation_pct) / 100.0
    total_cost_rs = recurring_rs + capital_charges_rs

    denominator = (
        tariff_rs
        * capacity_mw
        * 1000.0
        * annual_hours
        * (1.0 - loss_pct / 100.0)
    )
    if denominator <= 0:
        return 0.0

    load_factor = total_cost_rs / denominator
    return max(0.0, min(load_factor, 1.0))


def overall_cost_per_unit(
    md_mw: float,
    load_factor: float,
    capital_cost_per_kw: float,
    fixed_charge_pct: float,
    operating_cost_paise: float,
    reserve_pct: float = 0.0,
) -> float:
    """Compute Rs/kWh cost including fixed and operating charges."""

    if md_mw <= 0 or load_factor <= 0:
        return 0.0

    installed_kw = md_mw * (1.0 + reserve_pct / 100.0) * 1000.0
    annual_generation_kwh = md_mw * load_factor * 8760.0

    capital_rs = installed_kw * capital_cost_per_kw
    fixed_charge_rs = capital_rs * fixed_charge_pct / 100.0
    operating_cost_rs_per_kwh = operating_cost_paise / 100.0

    return operating_cost_rs_per_kwh + fixed_charge_rs / max(annual_generation_kwh, 1e-9)


def swing_equation(t, state, mechanical_power, electrical_scale, inertia, damping):
    """Simple swing equation for a single machine infinite bus model."""
    delta, omega = state  # delta: electrical angle [rad], omega: speed deviation pu
    electrical_power = electrical_scale * np.sin(delta)
    d_delta = omega
    d_omega = (mechanical_power - electrical_power - damping * omega) / inertia
    return [d_delta, d_omega]


class RealTimeSolver:
    """Real-time integrator supporting Euler and RK45 (via solve_ivp)."""

    def __init__(self, dynamics):
        self.dynamics = dynamics

    def step(self, state, t, dt, method, **kwargs):
        if method == "Euler":
            deriv = self.dynamics(t, state, **kwargs)
            return [state[i] + dt * deriv[i] for i in range(len(state))]

        # Default to RK45 using SciPy for stability on stiff responses
        sol = solve_ivp(
            lambda tau, y: self.dynamics(tau, y, **kwargs),
            (t, t + dt),
            state,
            method="RK45",
            max_step=dt,
        )
        return sol.y[:, -1]


class PowerEconomicsSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Power System Economics & Dynamics Lab")
        self.geometry("1100x750")

        self.parameters = {
            "capacity_mva": tk.DoubleVar(value=344.0),
            "capital_crore": tk.DoubleVar(value=22.4),
            "recurring_crore": tk.DoubleVar(value=9.4),
            "tariff_paise": tk.DoubleVar(value=11.37),
            "interest_pct": tk.DoubleVar(value=6.0),
            "depreciation_pct": tk.DoubleVar(value=5.0),
            "loss_pct": tk.DoubleVar(value=7.84),
            "power_factor": tk.DoubleVar(value=0.86),
            "mechanical_power": tk.DoubleVar(value=0.6),
            "electrical_scale": tk.DoubleVar(value=0.9),
            "damping": tk.DoubleVar(value=1.0),
            "inertia": tk.DoubleVar(value=5.0),
            "md_mw": tk.DoubleVar(value=250.0),
            "load_factor_compare": tk.DoubleVar(value=0.45),
            "steam_capital_kw": tk.DoubleVar(value=1000.0),
            "steam_fixed_pct": tk.DoubleVar(value=15.0),
            "steam_operating_paise": tk.DoubleVar(value=5.0),
            "steam_reserve_pct": tk.DoubleVar(value=30.0),
            "nuclear_capital_kw": tk.DoubleVar(value=2000.0),
            "nuclear_fixed_pct": tk.DoubleVar(value=12.0),
            "nuclear_operating_paise": tk.DoubleVar(value=2.0),
        }

        self._build_layout()
        self._create_plot()
        self._configure_resizing()

        self.solver = RealTimeSolver(swing_equation)
        self.sim_running = False
        self.state = np.array([0.1, 0.0], dtype=float)
        self.time = 0.0
        self.time_history = []
        self.delta_history = []
        self.omega_history = []
        self.after_id = None

        self._update_break_even_display()
        self._update_cost_comparison()

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        title = ttk.Label(
            self,
            text="Integrated Load Factor Estimator & Dynamic Machine Simulator",
            font=("Helvetica", 16, "bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        input_frame = ttk.LabelFrame(self, text="Input Parameters")
        input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        sim_frame = ttk.LabelFrame(self, text="Simulation & Visualization")
        sim_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        sim_frame.columnconfigure(0, weight=1)
        sim_frame.rowconfigure(1, weight=1)

        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)

        self._add_slider(input_frame, "Installed Capacity (MVA)", "capacity_mva", 50, 600, 0)
        self._add_slider(
            input_frame, "Capital Investment (Cr)", "capital_crore", 5, 60, 1
        )
        self._add_slider(
            input_frame, "Recurring Expenses (Cr)", "recurring_crore", 1, 30, 2
        )
        self._add_slider(input_frame, "Tariff (paise/kWh)", "tariff_paise", 5, 30, 3)
        self._add_slider(input_frame, "Interest (%)", "interest_pct", 0, 15, 4)
        self._add_slider(input_frame, "Depreciation (%)", "depreciation_pct", 0, 15, 5)
        self._add_slider(input_frame, "Distribution Loss (%)", "loss_pct", 0, 20, 6)
        self._add_slider(input_frame, "Average Power Factor", "power_factor", 0.5, 1.0, 7)

        ttk.Separator(input_frame, orient=tk.HORIZONTAL).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=6
        )

        self._add_slider(
            input_frame, "Mechanical Power (pu)", "mechanical_power", 0.2, 1.2, 9
        )
        self._add_slider(
            input_frame, "Electrical Scaling (pu)", "electrical_scale", 0.5, 1.5, 10
        )
        self._add_slider(input_frame, "Damping (pu)", "damping", 0.1, 3.0, 11)
        self._add_slider(input_frame, "Inertia (MJ/MVA)", "inertia", 1.0, 10.0, 12)

        ttk.Separator(input_frame, orient=tk.HORIZONTAL).grid(
            row=13, column=0, columnspan=3, sticky="ew", pady=6
        )

        compare_label = ttk.Label(
            input_frame,
            text="Steam vs Nuclear Cost Comparison",
            font=("Helvetica", 12, "bold"),
        )
        compare_label.grid(row=14, column=0, columnspan=3, pady=(4, 2), sticky="w")

        self._add_slider(input_frame, "Max Demand (MW)", "md_mw", 50, 500, 15)
        self._add_slider(
            input_frame, "Load Factor (fraction)", "load_factor_compare", 0.1, 1.0, 16
        )
        self._add_slider(
            input_frame, "Steam Capital (Rs/kW)", "steam_capital_kw", 200, 2000, 17
        )
        self._add_slider(
            input_frame, "Steam Fixed Charges (%)", "steam_fixed_pct", 5, 25, 18
        )
        self._add_slider(
            input_frame, "Steam Operating (paise/kWh)", "steam_operating_paise", 1, 10, 19
        )
        self._add_slider(input_frame, "Steam Reserve (%)", "steam_reserve_pct", 0, 40, 20)
        self._add_slider(
            input_frame, "Nuclear Capital (Rs/kW)", "nuclear_capital_kw", 500, 3000, 21
        )
        self._add_slider(
            input_frame, "Nuclear Fixed Charges (%)", "nuclear_fixed_pct", 5, 20, 22
        )
        self._add_slider(
            input_frame, "Nuclear Operating (paise/kWh)", "nuclear_operating_paise", 0.5, 5.0, 23
        )

        self.break_even_var = tk.StringVar()
        ttk.Label(
            input_frame,
            textvariable=self.break_even_var,
            font=("Helvetica", 12, "bold"),
            foreground="blue",
        ).grid(row=24, column=0, columnspan=3, sticky="ew", pady=8)

        self.compare_var = tk.StringVar()
        ttk.Label(
            input_frame,
            textvariable=self.compare_var,
            justify=tk.LEFT,
            font=("Helvetica", 10),
            foreground="darkgreen",
        ).grid(row=25, column=0, columnspan=3, sticky="ew", pady=4)

        self.solver_choice = tk.StringVar(value="RK45")
        control_frame = ttk.Frame(sim_frame)
        control_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        control_frame.columnconfigure(4, weight=1)

        ttk.Button(control_frame, text="Start", command=self.start_sim).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(control_frame, text="Stop", command=self.stop_sim).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(control_frame, text="Reset", command=self.reset_sim).grid(
            row=0, column=2, padx=5
        )

        ttk.Label(control_frame, text="Integrator:").grid(row=0, column=3, padx=(15, 4))
        ttk.Radiobutton(
            control_frame, text="RK45", variable=self.solver_choice, value="RK45"
        ).grid(row=0, column=4, padx=2)
        ttk.Radiobutton(
            control_frame, text="Euler", variable=self.solver_choice, value="Euler"
        ).grid(row=0, column=5, padx=2)

        self.sim_frame = sim_frame

    def _add_slider(self, parent, label, key, min_val, max_val, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=3)
        scale = ttk.Scale(
            parent,
            variable=self.parameters[key],
            from_=min_val,
            to=max_val,
            orient=tk.HORIZONTAL,
            command=lambda _=None: self._on_input_change(),
        )
        scale.grid(row=row, column=1, sticky="ew", padx=6, pady=3)
        parent.columnconfigure(1, weight=1)
        value_label = ttk.Label(parent, textvariable=self.parameters[key])
        value_label.grid(row=row, column=2, sticky="w")

    def _create_plot(self):
        self.figure = Figure(figsize=(6, 5))
        self.ax_delta = self.figure.add_subplot(211)
        self.ax_omega = self.figure.add_subplot(212)
        self.ax_delta.set_ylabel("Rotor Angle (rad)")
        self.ax_omega.set_ylabel("Speed Deviation (pu)")
        self.ax_omega.set_xlabel("Time (s)")

        (self.delta_line,) = self.ax_delta.plot([], [], label="δ")
        (self.omega_line,) = self.ax_omega.plot([], [], label="ω")
        self.ax_delta.legend()
        self.ax_omega.legend()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.sim_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

    def _configure_resizing(self):
        self.rowconfigure(1, weight=1)
        self.bind("<Configure>", lambda _event: self._redraw())

    def _redraw(self):
        self.canvas.draw_idle()

    def _update_break_even_display(self):
        lf = calculate_break_even_load_factor(
            self.parameters["capacity_mva"].get(),
            self.parameters["capital_crore"].get(),
            self.parameters["recurring_crore"].get(),
            self.parameters["tariff_paise"].get(),
            self.parameters["interest_pct"].get(),
            self.parameters["depreciation_pct"].get(),
            self.parameters["loss_pct"].get(),
            self.parameters["power_factor"].get(),
        )
        percent = lf * 100.0
        self.break_even_var.set(f"Break-even annual load factor: {percent:5.2f}%")

    def _update_cost_comparison(self):
        md = self.parameters["md_mw"].get()
        lf = self.parameters["load_factor_compare"].get()

        steam_cost = overall_cost_per_unit(
            md,
            lf,
            self.parameters["steam_capital_kw"].get(),
            self.parameters["steam_fixed_pct"].get(),
            self.parameters["steam_operating_paise"].get(),
            reserve_pct=self.parameters["steam_reserve_pct"].get(),
        )

        nuclear_cost = overall_cost_per_unit(
            md,
            lf,
            self.parameters["nuclear_capital_kw"].get(),
            self.parameters["nuclear_fixed_pct"].get(),
            self.parameters["nuclear_operating_paise"].get(),
            reserve_pct=0.0,
        )

        equal_lf = self._solve_equal_load_factor()
        equal_text = "Not solvable" if equal_lf is None else f"{equal_lf*100:4.1f}%"

        self.compare_var.set(
            "\n".join(
                [
                    f"Steam cost: Rs {steam_cost:0.4f}/kWh (with reserve)",
                    f"Nuclear cost: Rs {nuclear_cost:0.4f}/kWh",
                    f"Equal-cost load factor: {equal_text}",
                ]
            )
        )

    def _solve_equal_load_factor(self):
        md = self.parameters["md_mw"].get()

        def diff(lf_value: float) -> float:
            return overall_cost_per_unit(
                md,
                lf_value,
                self.parameters["steam_capital_kw"].get(),
                self.parameters["steam_fixed_pct"].get(),
                self.parameters["steam_operating_paise"].get(),
                reserve_pct=self.parameters["steam_reserve_pct"].get(),
            ) - overall_cost_per_unit(
                md,
                lf_value,
                self.parameters["nuclear_capital_kw"].get(),
                self.parameters["nuclear_fixed_pct"].get(),
                self.parameters["nuclear_operating_paise"].get(),
                reserve_pct=0.0,
            )

        low, high = 0.05, 1.0
        d_low, d_high = diff(low), diff(high)
        if d_low == 0:
            return low
        if d_high == 0:
            return high
        if d_low * d_high > 0:
            return None

        for _ in range(40):
            mid = 0.5 * (low + high)
            d_mid = diff(mid)
            if abs(d_mid) < 1e-6:
                return mid
            if d_mid * d_low > 0:
                low, d_low = mid, d_mid
            else:
                high, d_high = mid, d_mid
        return 0.5 * (low + high)

    def _on_input_change(self):
        self._update_break_even_display()
        self._update_cost_comparison()

    def start_sim(self):
        if self.sim_running:
            return
        self.sim_running = True
        self.last_update = self.time
        self._run_step()

    def stop_sim(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.sim_running = False

    def reset_sim(self):
        self.stop_sim()
        self.state = np.array([0.1, 0.0], dtype=float)
        self.time = 0.0
        self.time_history.clear()
        self.delta_history.clear()
        self.omega_history.clear()
        self._refresh_plot()

    def _run_step(self):
        if not self.sim_running:
            return
        dt = 0.05
        self.time += dt
        self.state = self.solver.step(
            self.state,
            self.time,
            dt,
            method=self.solver_choice.get(),
            mechanical_power=self.parameters["mechanical_power"].get(),
            electrical_scale=self.parameters["electrical_scale"].get(),
            inertia=self.parameters["inertia"].get(),
            damping=self.parameters["damping"].get(),
        )

        self.time_history.append(self.time)
        self.delta_history.append(self.state[0])
        self.omega_history.append(self.state[1])

        self._refresh_plot()
        self.after_id = self.after(50, self._run_step)

    def _refresh_plot(self):
        self.delta_line.set_data(self.time_history, self.delta_history)
        self.omega_line.set_data(self.time_history, self.omega_history)

        for ax in (self.ax_delta, self.ax_omega):
            ax.relim()
            ax.autoscale_view()
        self.canvas.draw_idle()


def main():
    app = PowerEconomicsSimulator()
    app.mainloop()


if __name__ == "__main__":
    main()
