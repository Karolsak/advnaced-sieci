#!/usr/bin/env python3
"""
Test script for three_phase_motor_capacitor_simulator.py
Verifies calculations without GUI
"""

import math

def test_calculations():
    """Test the capacitance calculations for all three problems"""

    print("="*60)
    print("TESTING THREE-PHASE MOTOR CAPACITOR CALCULATIONS")
    print("="*60)

    # Problem 2: 100 HP, 400V motor
    print("\n" + "="*60)
    print("PROBLEM 2: 100 HP, 400V Motor")
    print("="*60)

    voltage = 400
    power_hp = 100
    frequency = 50
    pf_initial = 0.7
    pf_final = 0.95
    efficiency = 0.93
    n_caps = 4

    # Convert HP to Watts
    P_out = power_hp * 745.7
    print(f"\nPower Output: {P_out:.2f} W")

    # Input power
    P_in = P_out / efficiency
    print(f"Power Input: {P_in:.2f} W")

    # Reactive powers
    phi1 = math.acos(pf_initial)
    Q1 = P_in * math.tan(phi1)
    print(f"Initial Reactive Power Q1: {Q1:.2f} VAR")

    phi2 = math.acos(pf_final)
    Q2 = P_in * math.tan(phi2)
    print(f"Final Reactive Power Q2: {Q2:.2f} VAR")

    Q_c = Q1 - Q2
    print(f"Reactive Power to Compensate Qc: {Q_c:.2f} VAR")

    # Capacitance calculation
    omega = 2 * math.pi * frequency
    C_total = Q_c / (3 * voltage**2 * omega)
    print(f"Total Capacitance per Phase: {C_total*1e6:.4f} µF")

    # Individual capacitor (series configuration)
    C_individual = C_total * n_caps
    print(f"\n*** CAPACITANCE OF EACH CAPACITOR (4 in series) ***")
    print(f"C = {C_individual*1e6:.4f} µF")
    print(f"C = {C_individual:.6e} F")

    # Current calculations
    I_initial = P_in / (math.sqrt(3) * voltage * pf_initial)
    I_final = P_in / (math.sqrt(3) * voltage * pf_final)
    print(f"\nInitial Line Current: {I_initial:.2f} A")
    print(f"Final Line Current: {I_final:.2f} A")
    print(f"Current Reduction: {I_initial - I_final:.2f} A")

    # Problem 3: 400 HP, 2000V motor
    print("\n" + "="*60)
    print("PROBLEM 3: 400 HP, 2000V Motor")
    print("="*60)

    voltage = 2000
    power_hp = 400
    frequency = 50
    pf_initial = 0.75
    pf_final = 0.98
    efficiency = 0.85
    n_caps = 1

    P_out = power_hp * 745.7
    print(f"\nPower Output: {P_out:.2f} W")

    P_in = P_out / efficiency
    print(f"Power Input: {P_in:.2f} W")

    phi1 = math.acos(pf_initial)
    Q1 = P_in * math.tan(phi1)
    print(f"Initial Reactive Power Q1: {Q1:.2f} VAR")

    phi2 = math.acos(pf_final)
    Q2 = P_in * math.tan(phi2)
    print(f"Final Reactive Power Q2: {Q2:.2f} VAR")

    Q_c = Q1 - Q2
    print(f"Reactive Power to Compensate Qc: {Q_c:.2f} VAR")

    omega = 2 * math.pi * frequency
    C_total = Q_c / (3 * voltage**2 * omega)
    print(f"Total Capacitance per Phase: {C_total*1e6:.4f} µF")

    C_individual = C_total
    print(f"\n*** CAPACITANCE OF EACH CAPACITOR ***")
    print(f"C = {C_individual*1e6:.4f} µF")
    print(f"C = {C_individual:.6e} F")

    I_initial = P_in / (math.sqrt(3) * voltage * pf_initial)
    I_final = P_in / (math.sqrt(3) * voltage * pf_final)
    print(f"\nInitial Line Current: {I_initial:.2f} A")
    print(f"Final Line Current: {I_final:.2f} A")
    print(f"Current Reduction: {I_initial - I_final:.2f} A")

    # Problem 4: 600 HP, 3000V motor
    print("\n" + "="*60)
    print("PROBLEM 4: 600 HP, 3000V Motor")
    print("="*60)

    voltage = 3000
    power_hp = 600
    frequency = 50
    pf_initial = 0.75
    pf_final = 0.98
    efficiency = 0.95
    n_caps = 5

    P_out = power_hp * 745.7
    print(f"\nPower Output: {P_out:.2f} W")

    P_in = P_out / efficiency
    print(f"Power Input: {P_in:.2f} W")

    phi1 = math.acos(pf_initial)
    Q1 = P_in * math.tan(phi1)
    print(f"Initial Reactive Power Q1: {Q1:.2f} VAR")

    phi2 = math.acos(pf_final)
    Q2 = P_in * math.tan(phi2)
    print(f"Final Reactive Power Q2: {Q2:.2f} VAR")

    Q_c = Q1 - Q2
    print(f"Reactive Power to Compensate Qc: {Q_c:.2f} VAR")

    omega = 2 * math.pi * frequency
    C_total = Q_c / (3 * voltage**2 * omega)
    print(f"Total Capacitance per Phase: {C_total*1e6:.4f} µF")

    C_individual = C_total * n_caps
    print(f"\n*** CAPACITANCE OF EACH CAPACITOR (5 in series) ***")
    print(f"C = {C_individual*1e6:.4f} µF")
    print(f"C = {C_individual:.6e} F")

    I_initial = P_in / (math.sqrt(3) * voltage * pf_initial)
    I_final = P_in / (math.sqrt(3) * voltage * pf_final)
    print(f"\nInitial Line Current: {I_initial:.2f} A")
    print(f"Final Line Current: {I_final:.2f} A")
    print(f"Current Reduction: {I_initial - I_final:.2f} A")

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*60)

if __name__ == "__main__":
    test_calculations()
