"""
Interactive three-phase induction motor starting calculator and simulator.

This tool models a three-phase, four-pole, Y-connected cage induction motor
and provides:
- Analytical starting torque and starting current ratio calculations.
- Parameter controls for rated conditions and machine constants.
- Real-time dynamic simulation of rotor speed using selectable ODE solvers.

Assumptions:
- Stator resistance and excitation current are neglected.
- Heyland's coefficient approach for the torque-slip curve is applied.
- Constant terminal voltage during the simulation.
"""
from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover - optional dependency safeguard
    Figure = None
    FigureCanvasTkAgg = None


@dataclass
class MotorParameters:
    rated_power_kw: float = 210.0
    rated_speed_rpm: float = 1485.0
    frequency_hz: float = 50.0
    line_voltage_v: float = 500.0
    poles: int = 4
    critical_slip: float = 0.044
    rated_slip: float = 0.01
    inertia_kgm2: float = 8.0
    damping_coeff: float = 0.02
    base_load_torque_nm: float = 800.0

    def synchronous_speed_rpm(self) -> float:
        return 120.0 * self.frequency_hz / self.poles

    def synchronous_speed_rad_s(self) -> float:
        return self.synchronous_speed_rpm() * 2.0 * math.pi / 60.0

    def rated_torque_nm(self) -> float:
        omega = self.rated_speed_rpm * 2.0 * math.pi / 60.0
        return (self.rated_power_kw * 1000.0) / max(omega, 1e-6)


@dataclass
class MotorState:
    speed_rad_s: float = 0.0
    time_s: float = 0.0
    history: list[tuple[float, float]] = field(default_factory=list)

    def reset(self) -> None:
        self.speed_rad_s = 0.0
        self.time_s = 0.0
        self.history.clear()


class InductionMotorModel:
    def __init__(self, params: MotorParameters):
        self.params = params

    def max_torque_nm(self) -> float:
        p = self.params
        sn = max(p.rated_slip, 1e-4)
        scr = max(p.critical_slip, 1e-6)
        tn = p.rated_torque_nm()
        return tn * (sn**2 + scr**2) / (2.0 * scr * sn)

    def torque_nm(self, slip: float) -> float:
        slip = max(min(slip, 2.0), 0.0)
        scr = max(self.params.critical_slip, 1e-6)
        tmax = self.max_torque_nm()
        numerator = 2.0 * scr * slip
        denominator = slip**2 + scr**2
        return tmax * numerator / max(denominator, 1e-9)

    def starting_torque_nm(self) -> float:
        scr = max(self.params.critical_slip, 1e-6)
        tmax = self.max_torque_nm()
        return tmax * (2.0 * scr**2) / (1.0 + scr**2)

    def starting_current_ratio(self) -> float:
        p = self.params
        scr = max(p.critical_slip, 1e-6)
        sn = max(p.rated_slip, 1e-6)
        return math.sqrt(((scr / sn) ** 2 + 1.0) / (scr**2 + 1.0))

    def slip_from_speed(self, speed_rad_s: float) -> float:
        ws = self.params.synchronous_speed_rad_s()
        speed_rad_s = min(speed_rad_s, ws)
        return max((ws - speed_rad_s) / ws, 0.0)

    def electrical_torque_nm(self, speed_rad_s: float) -> float:
        slip = self.slip_from_speed(speed_rad_s)
        return self.torque_nm(slip)

    def load_torque_nm(self, speed_rad_s: float) -> float:
        p = self.params
        return p.base_load_torque_nm + p.damping_coeff * speed_rad_s

    def deriv(self, t: float, speed_rad_s: float) -> float:
        p = self.params
        te = self.electrical_torque_nm(speed_rad_s)
        tl = self.load_torque_nm(speed_rad_s)
        return (te - tl) / max(p.inertia_kgm2, 1e-6)


class MotorSimulatorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Three-Phase Induction Motor Simulator")
        for idx in range(3):
            self.root.columnconfigure(idx, weight=1)
        for idx in range(4):
            self.root.rowconfigure(idx, weight=1)

        self.params = MotorParameters()
        self.model = InductionMotorModel(self.params)
        self.state = MotorState()

        self.running = False
        self.solver_method = tk.StringVar(value="RK45")
        self.dt = tk.DoubleVar(value=0.01)

        self._build_inputs()
        self._build_controls()
        self._build_results()
        self._build_plot()

    def _build_inputs(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Input Parameters")
        frame.grid(row=0, column=0, columnspan=3, padx=6, pady=6, sticky="nsew")
        for idx in range(6):
            frame.columnconfigure(idx, weight=1)

        entries = [
            ("Rated power [kW]", "rated_power_kw"),
            ("Rated speed [rpm]", "rated_speed_rpm"),
            ("Frequency [Hz]", "frequency_hz"),
            ("Line voltage [V]", "line_voltage_v"),
            ("Critical slip", "critical_slip"),
            ("Rated slip", "rated_slip"),
            ("Inertia J [kg·m²]", "inertia_kgm2"),
            ("Load torque [N·m]", "base_load_torque_nm"),
            ("Damping coeff", "damping_coeff"),
        ]

        self.param_vars: dict[str, tk.DoubleVar] = {}
        for idx, (label, attr) in enumerate(entries):
            var = tk.DoubleVar(value=getattr(self.params, attr))
            self.param_vars[attr] = var
            ttk.Label(frame, text=label).grid(row=idx // 3, column=2 * (idx % 3), padx=4, pady=2, sticky="e")
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.grid(row=idx // 3, column=2 * (idx % 3) + 1, padx=4, pady=2, sticky="we")
            frame.rowconfigure(idx // 3, weight=1)

    def _build_controls(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Controls")
        frame.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")
        for idx in range(2):
            frame.columnconfigure(idx, weight=1)

        ttk.Label(frame, text="Solver").grid(row=0, column=0, padx=4, pady=2, sticky="e")
        solver_menu = ttk.OptionMenu(frame, self.solver_method, "RK45", "RK45", "Euler")
        solver_menu.grid(row=0, column=1, padx=4, pady=2, sticky="we")

        ttk.Label(frame, text="Time step [s]").grid(row=1, column=0, padx=4, pady=2, sticky="e")
        ttk.Spinbox(frame, from_=0.001, to=0.1, increment=0.001, textvariable=self.dt, width=10).grid(
            row=1, column=1, padx=4, pady=2, sticky="we"
        )

        ttk.Button(frame, text="Start", command=self.start_simulation).grid(row=2, column=0, padx=4, pady=4, sticky="we")
        ttk.Button(frame, text="Stop", command=self.stop_simulation).grid(row=2, column=1, padx=4, pady=4, sticky="we")
        ttk.Button(frame, text="Reset", command=self.reset_simulation).grid(row=3, column=0, columnspan=2, padx=4, pady=4, sticky="we")

        slider_frame = ttk.LabelFrame(self.root, text="Adjustments")
        slider_frame.grid(row=1, column=1, columnspan=2, padx=6, pady=6, sticky="nsew")
        for idx in range(3):
            slider_frame.columnconfigure(idx, weight=1)

        self.load_scale = tk.Scale(slider_frame, from_=0, to=2000, orient=tk.HORIZONTAL, label="Load torque [N·m]", command=self._on_load_change)
        self.load_scale.set(self.params.base_load_torque_nm)
        self.load_scale.grid(row=0, column=0, padx=4, pady=2, sticky="we")

        self.inertia_scale = tk.Scale(slider_frame, from_=1, to=20, resolution=0.5, orient=tk.HORIZONTAL, label="Inertia J [kg·m²]", command=self._on_inertia_change)
        self.inertia_scale.set(self.params.inertia_kgm2)
        self.inertia_scale.grid(row=0, column=1, padx=4, pady=2, sticky="we")

        self.damping_scale = tk.Scale(slider_frame, from_=0.0, to=0.2, resolution=0.005, orient=tk.HORIZONTAL, label="Damping coeff", command=self._on_damping_change)
        self.damping_scale.set(self.params.damping_coeff)
        self.damping_scale.grid(row=0, column=2, padx=4, pady=2, sticky="we")

    def _build_results(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Results")
        frame.grid(row=2, column=0, columnspan=3, padx=6, pady=6, sticky="nsew")
        for idx in range(6):
            frame.columnconfigure(idx, weight=1)
        self.results_labels = {}
        labels = [
            "Synchronous speed [rpm]",
            "Rated torque [N·m]",
            "Max torque [N·m]",
            "Starting torque [N·m]",
            "Starting current ratio",
            "Current slip",
        ]
        for idx, label in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=idx // 3, column=2 * (idx % 3), padx=4, pady=2, sticky="e")
            value = ttk.Label(frame, text="-")
            value.grid(row=idx // 3, column=2 * (idx % 3) + 1, padx=4, pady=2, sticky="w")
            self.results_labels[label] = value
        self._update_static_results()

    def _build_plot(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Dynamic Visualization")
        frame.grid(row=3, column=0, columnspan=3, padx=6, pady=6, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        if Figure is None or FigureCanvasTkAgg is None:
            self.canvas = None
            ttk.Label(frame, text="matplotlib not available; plotting disabled").grid(row=0, column=0, padx=4, pady=4)
            return

        self.figure = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time [s]")
        self.ax.set_ylabel("Speed [rpm]")
        self.line, = self.ax.plot([], [], label="Rotor speed")
        self.ax.legend()
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _on_load_change(self, value: str) -> None:
        self.params.base_load_torque_nm = float(value)
        self.param_vars["base_load_torque_nm"].set(self.params.base_load_torque_nm)
        self._update_static_results()

    def _on_inertia_change(self, value: str) -> None:
        self.params.inertia_kgm2 = float(value)
        self.param_vars["inertia_kgm2"].set(self.params.inertia_kgm2)

    def _on_damping_change(self, value: str) -> None:
        self.params.damping_coeff = float(value)
        self.param_vars["damping_coeff"].set(self.params.damping_coeff)

    def _update_parameters_from_inputs(self) -> None:
        for attr, var in self.param_vars.items():
            setattr(self.params, attr, float(var.get()))
        self.model = InductionMotorModel(self.params)

    def _update_static_results(self) -> None:
        self._update_parameters_from_inputs()
        synchronous_rpm = self.params.synchronous_speed_rpm()
        rated_torque = self.params.rated_torque_nm()
        max_torque = self.model.max_torque_nm()
        start_torque = self.model.starting_torque_nm()
        scr = self.model.starting_current_ratio()
        slip = self.model.slip_from_speed(self.state.speed_rad_s)

        values = {
            "Synchronous speed [rpm]": f"{synchronous_rpm:,.1f}",
            "Rated torque [N·m]": f"{rated_torque:,.1f}",
            "Max torque [N·m]": f"{max_torque:,.1f}",
            "Starting torque [N·m]": f"{start_torque:,.1f}",
            "Starting current ratio": f"{scr:,.2f} × Iₙ",
            "Current slip": f"{slip:.4f}",
        }
        for key, label in self.results_labels.items():
            label.config(text=values.get(key, "-"))

    def start_simulation(self) -> None:
        self._update_parameters_from_inputs()
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._run_simulation, daemon=True).start()

    def stop_simulation(self) -> None:
        self.running = False

    def reset_simulation(self) -> None:
        self.stop_simulation()
        self.state.reset()
        self._update_static_results()
        self._redraw_plot()

    def _run_simulation(self) -> None:
        last_update = time.time()
        while self.running:
            now = time.time()
            elapsed = now - last_update
            last_update = now
            self._step_simulation(max(self.dt.get(), 1e-4))
            time.sleep(max(self.dt.get() - elapsed, 0.0))

    def _step_simulation(self, dt: float) -> None:
        if not self.running:
            return
        solver = self.solver_method.get()
        if solver == "Euler":
            self._euler_step(dt)
        else:
            self._rk45_step(dt)
        self._update_static_results()
        self._record_history()
        self._redraw_plot()

    def _euler_step(self, dt: float) -> None:
        deriv = self.model.deriv(self.state.time_s, self.state.speed_rad_s)
        self.state.speed_rad_s += deriv * dt
        self.state.time_s += dt
        self.state.speed_rad_s = max(self.state.speed_rad_s, 0.0)

    def _rk45_step(self, dt: float) -> None:
        f = self.model.deriv
        t = self.state.time_s
        y = self.state.speed_rad_s

        k1 = f(t, y)
        k2 = f(t + 0.25 * dt, y + 0.25 * dt * k1)
        k3 = f(t + 3.0 / 8.0 * dt, y + dt * (3.0 / 32.0 * k1 + 9.0 / 32.0 * k2))
        k4 = f(t + 12.0 / 13.0 * dt, y + dt * (1932.0 / 2197.0 * k1 - 7200.0 / 2197.0 * k2 + 7296.0 / 2197.0 * k3))
        k5 = f(t + dt, y + dt * (439.0 / 216.0 * k1 - 8.0 * k2 + 3680.0 / 513.0 * k3 - 845.0 / 4104.0 * k4))
        k6 = f(t + 0.5 * dt, y + dt * (-8.0 / 27.0 * k1 + 2.0 * k2 - 3544.0 / 2565.0 * k3 + 1859.0 / 4104.0 * k4 - 11.0 / 40.0 * k5))

        y_next = y + dt * (
            16.0 / 135.0 * k1
            + 6656.0 / 12825.0 * k3
            + 28561.0 / 56430.0 * k4
            - 9.0 / 50.0 * k5
            + 2.0 / 55.0 * k6
        )

        self.state.speed_rad_s = max(y_next, 0.0)
        self.state.time_s += dt

    def _record_history(self) -> None:
        rpm = self.state.speed_rad_s * 60.0 / (2.0 * math.pi)
        self.state.history.append((self.state.time_s, rpm))
        if len(self.state.history) > 3000:
            self.state.history = self.state.history[-3000:]

    def _redraw_plot(self) -> None:
        if self.canvas is None:
            return
        times = [pt[0] for pt in self.state.history]
        speeds = [pt[1] for pt in self.state.history]
        self.line.set_data(times, speeds)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    app = MotorSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
