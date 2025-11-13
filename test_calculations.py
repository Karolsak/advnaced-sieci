#!/usr/bin/env python3
"""
Validation test for power system calculations
Tests the analytical steady-state solution without GUI
"""


class PowerSystemCalculator:
    """Analytical calculator for Example 8.10"""

    def __init__(self):
        self.capacity_A = 75.0  # MW
        self.capacity_B = 200.0  # MW
        self.regulation_A = 0.04  # 4%
        self.regulation_B = 0.02  # 2%

    def calculate_steady_state(self, load_A, load_B):
        """
        Calculate analytical steady-state values

        From Example 8.10:
        P1/75 = (1-f)/0.04  =>  (1-f) = 0.04*P1/75 = 0.000533*P1
        P2/200 = (1-f)/0.02  =>  (1-f) = 0.02*P2/200 = 0.0001*P2

        Therefore: 0.000533*P1 = 0.0001*P2
                  5.33*P1 = P2

        And: P1 + P2 = Total Load
        """
        total_load = load_A + load_B

        # From speed regulation equations:
        # 5.33 * P_A = P_B
        # P_A + P_B = Total Load

        P_A_ss = total_load / (1.0 + 5.33)
        P_B_ss = 5.33 * P_A_ss

        # Verify the relationship
        assert abs(P_A_ss + P_B_ss - total_load) < 0.01, "Power balance check failed"

        # Tie-line power (from A to B, negative means B to A)
        P_tie_AB = P_A_ss - load_A

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


def test_scenario_a():
    """Test scenario (a): Load on each station = 100 MW"""
    print("\n" + "="*70)
    print("TEST SCENARIO (a): Load on each station = 100 MW")
    print("="*70)

    calc = PowerSystemCalculator()
    result = calc.calculate_steady_state(100.0, 100.0)

    expected_P_A = 31.60
    expected_P_B = 168.40

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.2f} MW")
    print(f"  P_B = {result['P_B']:.2f} MW")
    print(f"  P_A + P_B = {result['P_A'] + result['P_B']:.2f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.2f} MW (+ means A→B, - means B→A)")

    print(f"\nExpected Results (from Example 8.10):")
    print(f"  P_A = {expected_P_A:.2f} MW")
    print(f"  P_B = {expected_P_B:.2f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    # Verify ratio
    ratio = result['P_B'] / result['P_A']
    print(f"  P_B/P_A Ratio: {ratio:.4f} (expected: 5.33)")

    if p_a_error < 0.1 and p_b_error < 0.1:
        print("\n  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("\n  ✗ FAILED - Results do not match!")
        return False


def test_scenario_b():
    """Test scenario (b): Loads: 50 MW @ A, 150 MW @ B"""
    print("\n" + "="*70)
    print("TEST SCENARIO (b): Loads: 50 MW @ A, 150 MW @ B")
    print("="*70)

    calc = PowerSystemCalculator()
    result = calc.calculate_steady_state(50.0, 150.0)

    expected_P_A = 31.60
    expected_P_B = 168.40

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.2f} MW")
    print(f"  P_B = {result['P_B']:.2f} MW")
    print(f"  P_A + P_B = {result['P_A'] + result['P_B']:.2f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.2f} MW")
    print(f"  Power flow from B to A = {result['P_A'] - 50.0:.2f} MW")

    print(f"\nExpected Results (from Example 8.10):")
    print(f"  P_A = {expected_P_A:.2f} MW")
    print(f"  P_B = {expected_P_B:.2f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    if p_a_error < 0.1 and p_b_error < 0.1:
        print("\n  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("\n  ✗ FAILED - Results do not match!")
        return False


def test_scenario_c():
    """Test scenario (c): Load: 130 MW @ A only"""
    print("\n" + "="*70)
    print("TEST SCENARIO (c): Load: 130 MW @ A only")
    print("="*70)

    calc = PowerSystemCalculator()
    result = calc.calculate_steady_state(130.0, 0.0)

    expected_P_A = 20.537
    expected_P_B = 109.462

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.3f} MW")
    print(f"  P_B = {result['P_B']:.3f} MW")
    print(f"  P_A + P_B = {result['P_A'] + result['P_B']:.3f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.3f} MW")
    print(f"  Power flow from B to A = {result['P_B']:.3f} MW")

    print(f"\nExpected Results (from Example 8.10):")
    print(f"  P_A = {expected_P_A:.3f} MW")
    print(f"  P_B = {expected_P_B:.3f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    if p_a_error < 0.01 and p_b_error < 0.01:
        print("\n  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("\n  ✗ FAILED - Results do not match!")
        return False


def test_load_sharing_ratio():
    """Test that load sharing ratio is correct (5.33:1)"""
    print("\n" + "="*70)
    print("TEST: Load Sharing Ratio")
    print("="*70)

    calc = PowerSystemCalculator()

    # Test with different loads
    test_cases = [
        (100, 100, "Load A=100, B=100"),
        (50, 150, "Load A=50, B=150"),
        (130, 0, "Load A=130, B=0"),
        (75, 75, "Load A=75, B=75"),
    ]

    all_passed = True
    expected_ratio = 5.33

    for load_a, load_b, description in test_cases:
        result = calc.calculate_steady_state(load_a, load_b)
        ratio = result['P_B'] / result['P_A']
        error = abs(ratio - expected_ratio)

        print(f"\n{description}:")
        print(f"  P_B/P_A = {ratio:.4f}")
        print(f"  Error from 5.33: {error:.6f}")

        if error > 0.01:
            all_passed = False
            print(f"  ✗ FAILED")
        else:
            print(f"  ✓ PASSED")

    if all_passed:
        print("\n✓ PASSED - Load sharing ratio is correct for all test cases!")
        return True
    else:
        print("\n✗ FAILED - Load sharing ratio is incorrect!")
        return False


def test_power_balance():
    """Test that power generation equals load"""
    print("\n" + "="*70)
    print("TEST: Power Balance")
    print("="*70)

    calc = PowerSystemCalculator()

    test_cases = [
        (100, 100),
        (50, 150),
        (130, 0),
        (0, 200),
        (75, 125),
    ]

    all_passed = True

    for load_a, load_b in test_cases:
        result = calc.calculate_steady_state(load_a, load_b)
        total_gen = result['P_A'] + result['P_B']
        total_load = load_a + load_b
        error = abs(total_gen - total_load)

        print(f"\nLoad A={load_a}, B={load_b}:")
        print(f"  Total Generation: {total_gen:.4f} MW")
        print(f"  Total Load: {total_load:.4f} MW")
        print(f"  Error: {error:.6f} MW")

        if error > 0.01:
            all_passed = False
            print(f"  ✗ FAILED - Power imbalance!")
        else:
            print(f"  ✓ PASSED")

    if all_passed:
        print("\n✓ PASSED - Power balance maintained for all cases!")
        return True
    else:
        print("\n✗ FAILED - Power balance violated!")
        return False


def verify_equations():
    """Verify the fundamental equations"""
    print("\n" + "="*70)
    print("TEST: Fundamental Equations")
    print("="*70)

    print("\nFrom Example 8.10:")
    print("  Speed regulation of Station-A: R_A = 4% = 0.04")
    print("  Speed regulation of Station-B: R_B = 2% = 0.02")
    print("  Capacity of Station-A: 75 MW")
    print("  Capacity of Station-B: 200 MW")

    print("\nDerived equations:")
    print("  For Station A: P1 = 75(1-f)/0.04")
    print("                (1-f) = 0.04*P1/75 = 0.000533*P1")
    print("\n  For Station B: P2 = 200(1-f)/0.02")
    print("                (1-f) = 0.02*P2/200 = 0.0001*P2")

    print("\nEquating frequency deviations:")
    print("  0.000533*P1 = 0.0001*P2")
    print("  5.33*P1 = P2")

    # Test with actual values
    calc = PowerSystemCalculator()
    result = calc.calculate_steady_state(100.0, 100.0)

    P1 = result['P_A']
    P2 = result['P_B']

    # Check the fundamental relationship
    ratio = P2 / P1
    expected_ratio = 0.000533 / 0.0001

    print(f"\nNumerical verification:")
    print(f"  P1 = {P1:.4f} MW")
    print(f"  P2 = {P2:.4f} MW")
    print(f"  P2/P1 = {ratio:.4f}")
    print(f"  Expected: {expected_ratio:.4f}")

    # Verify frequency equivalence
    coef_A = 0.000533
    coef_B = 0.0001
    freq_check_A = coef_A * P1
    freq_check_B = coef_B * P2

    print(f"\n  Frequency check:")
    print(f"    0.000533*P1 = {freq_check_A:.6f}")
    print(f"    0.0001*P2 = {freq_check_B:.6f}")
    print(f"    Difference = {abs(freq_check_A - freq_check_B):.8f}")

    if abs(freq_check_A - freq_check_B) < 1e-6:
        print("\n  ✓ PASSED - Fundamental equations verified!")
        return True
    else:
        print("\n  ✗ FAILED - Equation mismatch!")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("POWER SYSTEM CALCULATIONS - VALIDATION TESTS")
    print("Example 8.10: Two Power Stations Operating in Parallel")
    print("="*70)

    results = []

    results.append(("Fundamental Equations", verify_equations()))
    results.append(("Scenario (a) - Load 100/100", test_scenario_a()))
    results.append(("Scenario (b) - Load 50/150", test_scenario_b()))
    results.append(("Scenario (c) - Load 130/0", test_scenario_c()))
    results.append(("Load Sharing Ratio", test_load_sharing_ratio()))
    results.append(("Power Balance", test_power_balance()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:35s}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("The analytical calculations are correct and match Example 8.10.")
        print("\nThe GUI application can be run with:")
        print("  python3 power_system_ode_solver.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())
