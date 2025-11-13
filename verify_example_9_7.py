#!/usr/bin/env python3
"""
Verification script for Example 9.7 calculations
Tests the mathematical calculations without GUI
"""

import math


def verify_example_9_7():
    """Verify calculations for Example 9.7"""

    print("="*80)
    print("EXAMPLE 9.7: POWER FACTOR CORRECTION VERIFICATION")
    print("="*80)

    # Input parameters
    power_hp = 600  # HP
    voltage = 2500  # V (line-to-line)
    frequency = 50  # Hz
    pf1 = 0.8  # Initial power factor (lagging)
    pf2 = 1.0  # Final power factor (unity)
    efficiency = 0.9
    n_capacitors = 5  # Capacitors in series

    print("\nINPUT PARAMETERS:")
    print(f"  Motor Output Power        : {power_hp} HP")
    print(f"  Supply Voltage (L-L)      : {voltage} V")
    print(f"  Frequency                 : {frequency} Hz")
    print(f"  Initial Power Factor      : {pf1} lagging")
    print(f"  Final Power Factor        : {pf2}")
    print(f"  Motor Efficiency          : {efficiency}")
    print(f"  Capacitors in Series      : {n_capacitors}")

    # Step 1: Calculate motor input power
    motor_input_kw = (power_hp * 746) / (efficiency * 1000)
    print(f"\nSTEP 1: Motor Input Power")
    print(f"  P_input = (Output × 746) / (η × 1000)")
    print(f"  P_input = ({power_hp} × 746) / ({efficiency} × 1000)")
    print(f"  P_input = {motor_input_kw:.2f} kW")

    # Expected value from textbook
    expected_input = 497.33
    print(f"  Expected (from textbook): {expected_input} kW")
    print(f"  Match: {'✓' if abs(motor_input_kw - expected_input) < 0.5 else '✗'}")

    # Step 2: Calculate angles
    phi1 = math.acos(pf1)
    phi2 = math.acos(pf2)
    tan_phi1 = math.tan(phi1)
    tan_phi2 = math.tan(phi2)

    print(f"\nSTEP 2: Calculate Power Angles")
    print(f"  φ₁ = cos⁻¹({pf1}) = {math.degrees(phi1):.2f}°")
    print(f"  φ₂ = cos⁻¹({pf2}) = {math.degrees(phi2):.2f}°")
    print(f"  tan(φ₁) = {tan_phi1:.4f}")
    print(f"  tan(φ₂) = {tan_phi2:.4f}")

    # Expected value
    expected_tan_phi1 = 0.75
    print(f"  Expected tan(φ₁): {expected_tan_phi1}")
    print(f"  Match: {'✓' if abs(tan_phi1 - expected_tan_phi1) < 0.01 else '✗'}")

    # Step 3: Calculate leading kVAr
    kvar_total = motor_input_kw * (tan_phi1 - tan_phi2)
    print(f"\nSTEP 3: Leading kVAr Required")
    print(f"  kVAr_total = P × (tan φ₁ - tan φ₂)")
    print(f"  kVAr_total = {motor_input_kw:.2f} × ({tan_phi1:.4f} - {tan_phi2:.4f})")
    print(f"  kVAr_total = {kvar_total:.2f} kVAr")

    # Expected value
    expected_kvar = 373
    print(f"  Expected (from textbook): {expected_kvar} kVAr")
    print(f"  Match: {'✓' if abs(kvar_total - expected_kvar) < 1 else '✗'}")

    # Step 4: kVAr per phase (delta connection)
    kvar_per_phase = kvar_total / 3
    print(f"\nSTEP 4: kVAr per Phase (Delta Connection)")
    print(f"  kVAr_per_phase = {kvar_total:.2f} / 3")
    print(f"  kVAr_per_phase = {kvar_per_phase:.2f} kVAr")

    # Expected value
    expected_kvar_phase = 124.33
    print(f"  Expected (from textbook): {expected_kvar_phase} kVAr")
    print(f"  Match: {'✓' if abs(kvar_per_phase - expected_kvar_phase) < 0.5 else '✗'}")

    # Step 5: Phase voltage (for delta connection, V_ph = V_line)
    v_ph = voltage
    print(f"\nSTEP 5: Phase Voltage (Delta Connection)")
    print(f"  V_ph = V_line = {v_ph} V")

    # Step 6: Calculate capacitance per phase
    omega = 2 * math.pi * frequency
    print(f"\nSTEP 6: Calculate Capacitance")
    print(f"  ω = 2π × f = 2π × {frequency} = {omega:.4f} rad/s")

    # Using the formula: kVAr = ω × C × V_ph²
    # Rearranging: C = kVAr / (ω × V_ph²) × 1000
    C_phase_farad = (kvar_per_phase * 1000) / (omega * v_ph * v_ph)
    C_phase_uf = C_phase_farad * 1e6

    print(f"  Formula: kVAr = ω × C × V_ph² / 1000")
    print(f"  Rearranging: C = (kVAr × 1000) / (ω × V_ph²)")
    print(f"  C_phase = ({kvar_per_phase:.2f} × 1000) / ({omega:.4f} × {v_ph}²)")
    print(f"  C_phase = {C_phase_farad:.10f} F")
    print(f"  C_phase = {C_phase_uf:.2f} μF")

    # Expected value
    expected_c_phase = 63.32
    print(f"  Expected (from textbook): {expected_c_phase} μF")
    print(f"  Match: {'✓' if abs(C_phase_uf - expected_c_phase) < 0.5 else '✗'}")

    # Step 7: Calculate capacitance of each unit
    C_unit_uf = C_phase_uf * n_capacitors
    print(f"\nSTEP 7: Capacitance of Each Unit")
    print(f"  (5 capacitors in series, so each capacitor = 5 × combined capacitance)")
    print(f"  C_unit = {n_capacitors} × {C_phase_uf:.2f} μF")
    print(f"  C_unit = {C_unit_uf:.2f} μF")

    # Expected value
    expected_c_unit = 316.6
    print(f"  Expected (from textbook): {expected_c_unit} μF")
    print(f"  Match: {'✓' if abs(C_unit_uf - expected_c_unit) < 1 else '✗'}")

    # Step 8: Verification - Calculate kVAr using found capacitance
    kvar_check = omega * C_phase_farad * v_ph * v_ph / 1000
    print(f"\nSTEP 8: Verification")
    print(f"  kVAr_check = ω × C × V_ph² / 1000")
    print(f"  kVAr_check = {omega:.4f} × {C_phase_farad:.10f} × {v_ph}² / 1000")
    print(f"  kVAr_check = {kvar_check:.2f} kVAr")
    print(f"  Should equal: {kvar_per_phase:.2f} kVAr")
    print(f"  Match: {'✓' if abs(kvar_check - kvar_per_phase) < 0.1 else '✗'}")

    # Step 9: Capacitor current
    I_c = omega * C_phase_farad * v_ph
    print(f"\nSTEP 9: Capacitor Current per Phase")
    print(f"  I_C = ω × C × V_ph")
    print(f"  I_C = {omega:.4f} × {C_phase_farad:.10f} × {v_ph}")
    print(f"  I_C = {I_c:.2f} A")

    # Alternative calculation: I_C = kVAr / V_ph
    I_c_alt = (kvar_per_phase * 1000) / v_ph
    print(f"  Alternative: I_C = kVAr × 1000 / V_ph = {kvar_per_phase:.2f} × 1000 / {v_ph} = {I_c_alt:.2f} A")
    print(f"  Match: {'✓' if abs(I_c - I_c_alt) < 0.1 else '✗'}")

    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)

    # Summary
    print("\nSUMMARY OF RESULTS:")
    print(f"  ✓ Motor Input Power       : {motor_input_kw:.2f} kW")
    print(f"  ✓ Total kVAr Required     : {kvar_total:.2f} kVAr")
    print(f"  ✓ kVAr per Phase          : {kvar_per_phase:.2f} kVAr")
    print(f"  ✓ Combined Capacitance    : {C_phase_uf:.2f} μF per phase")
    print(f"  ✓ Each Capacitor Unit     : {C_unit_uf:.2f} μF")
    print(f"  ✓ Capacitor Current       : {I_c:.2f} A per phase")

    print("\nNote: Small differences from textbook values are due to rounding at different steps.")
    print("="*80)

    return True


if __name__ == "__main__":
    verify_example_9_7()
