#!/usr/bin/env python3
"""
Validation test script for power system ODE solver
Compares calculated values with Example 8.10 analytical solutions
"""

import sys
sys.path.insert(0, '/home/user/advnaced-sieci')

from power_system_ode_solver import PowerSystemODESolver


def test_scenario_a():
    """Test scenario (a): Load on each station = 100 MW"""
    print("\n" + "="*70)
    print("TEST SCENARIO (a): Load on each station = 100 MW")
    print("="*70)

    solver = PowerSystemODESolver()
    solver.load_A = 100.0
    solver.load_B = 100.0

    result = solver.calculate_steady_state()

    expected_P_A = 31.60
    expected_P_B = 168.40

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.2f} MW")
    print(f"  P_B = {result['P_B']:.2f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.2f} MW")

    print(f"\nExpected Results:")
    print(f"  P_A = {expected_P_A:.2f} MW")
    print(f"  P_B = {expected_P_B:.2f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    if p_a_error < 0.1 and p_b_error < 0.1:
        print("  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("  ✗ FAILED - Results do not match!")
        return False


def test_scenario_b():
    """Test scenario (b): Loads: 50 MW @ A, 150 MW @ B"""
    print("\n" + "="*70)
    print("TEST SCENARIO (b): Loads: 50 MW @ A, 150 MW @ B")
    print("="*70)

    solver = PowerSystemODESolver()
    solver.load_A = 50.0
    solver.load_B = 150.0

    result = solver.calculate_steady_state()

    expected_P_A = 31.60
    expected_P_B = 168.40

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.2f} MW")
    print(f"  P_B = {result['P_B']:.2f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.2f} MW")

    print(f"\nExpected Results:")
    print(f"  P_A = {expected_P_A:.2f} MW")
    print(f"  P_B = {expected_P_B:.2f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    if p_a_error < 0.1 and p_b_error < 0.1:
        print("  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("  ✗ FAILED - Results do not match!")
        return False


def test_scenario_c():
    """Test scenario (c): Load: 130 MW @ A only"""
    print("\n" + "="*70)
    print("TEST SCENARIO (c): Load: 130 MW @ A only")
    print("="*70)

    solver = PowerSystemODESolver()
    solver.load_A = 130.0
    solver.load_B = 0.0

    result = solver.calculate_steady_state()

    expected_P_A = 20.537
    expected_P_B = 109.462

    print(f"\nCalculated Results:")
    print(f"  P_A = {result['P_A']:.3f} MW")
    print(f"  P_B = {result['P_B']:.3f} MW")
    print(f"  Tie-line Power = {result['P_tie']:.3f} MW")

    print(f"\nExpected Results:")
    print(f"  P_A = {expected_P_A:.3f} MW")
    print(f"  P_B = {expected_P_B:.3f} MW")

    print(f"\nValidation:")
    p_a_error = abs(result['P_A'] - expected_P_A)
    p_b_error = abs(result['P_B'] - expected_P_B)

    print(f"  P_A Error: {p_a_error:.4f} MW")
    print(f"  P_B Error: {p_b_error:.4f} MW")

    if p_a_error < 0.1 and p_b_error < 0.1:
        print("  ✓ PASSED - Results match expected values!")
        return True
    else:
        print("  ✗ FAILED - Results do not match!")
        return False


def test_load_sharing_ratio():
    """Test that load sharing ratio is correct (5.33:1)"""
    print("\n" + "="*70)
    print("TEST: Load Sharing Ratio")
    print("="*70)

    solver = PowerSystemODESolver()
    solver.load_A = 100.0
    solver.load_B = 100.0

    result = solver.calculate_steady_state()

    ratio = result['P_B'] / result['P_A']
    expected_ratio = 5.33

    print(f"\nCalculated Ratio P_B/P_A = {ratio:.4f}")
    print(f"Expected Ratio = {expected_ratio:.4f}")

    error = abs(ratio - expected_ratio)
    print(f"Error: {error:.4f}")

    if error < 0.01:
        print("✓ PASSED - Load sharing ratio is correct!")
        return True
    else:
        print("✗ FAILED - Load sharing ratio is incorrect!")
        return False


def test_ode_solvers():
    """Test both ODE solvers"""
    print("\n" + "="*70)
    print("TEST: ODE Solvers (RK45 and Euler)")
    print("="*70)

    solver = PowerSystemODESolver()
    solver.load_A = 100.0
    solver.load_B = 100.0
    solver.simulation_time = 10.0

    try:
        # Test RK45
        print("\nTesting RK45 solver...")
        t_rk45, sol_rk45 = solver.solve_rk45()
        print(f"  ✓ RK45 completed: {len(t_rk45)} time points")
        print(f"  Final P_A = {sol_rk45[1, -1]:.2f} MW")
        print(f"  Final P_B = {sol_rk45[2, -1]:.2f} MW")

        # Test Euler
        print("\nTesting Euler solver...")
        t_euler, sol_euler = solver.solve_euler()
        print(f"  ✓ Euler completed: {len(t_euler)} time points")
        print(f"  Final P_A = {sol_euler[1, -1]:.2f} MW")
        print(f"  Final P_B = {sol_euler[2, -1]:.2f} MW")

        # Compare final values
        p_a_diff = abs(sol_rk45[1, -1] - sol_euler[1, -1])
        p_b_diff = abs(sol_rk45[2, -1] - sol_euler[2, -1])

        print(f"\nDifference between solvers:")
        print(f"  P_A difference: {p_a_diff:.4f} MW")
        print(f"  P_B difference: {p_b_diff:.4f} MW")

        if p_a_diff < 5.0 and p_b_diff < 5.0:
            print("  ✓ PASSED - Both solvers converge to similar values!")
            return True
        else:
            print("  ✗ WARNING - Solvers show significant difference!")
            return False

    except Exception as e:
        print(f"  ✗ FAILED - Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("POWER SYSTEM ODE SOLVER - VALIDATION TESTS")
    print("="*70)
    print("\nValidating against Example 8.10 analytical solutions...")

    results = []

    results.append(("Scenario (a)", test_scenario_a()))
    results.append(("Scenario (b)", test_scenario_b()))
    results.append(("Scenario (c)", test_scenario_c()))
    results.append(("Load Sharing Ratio", test_load_sharing_ratio()))
    results.append(("ODE Solvers", test_ode_solvers()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:25s}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The implementation is correct.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())
