"""Testy modeli z rozdziału 9 - porównanie z wynikami z książki."""
import numpy as np
import transmission_models as tm


def test_example1_matches_book():
    _, best = tm.ex1_solve_all(tm.Ex1Data())
    assert best[0] == "2-3B"                                   # rys. 9.6
    assert np.allclose(best[2]["Pg"], [4.0, 3.4, 0.4], atol=1e-6)
    assert abs(best[2]["total"] - 11.3) < 1e-6


def test_example2_backward_search_and_costs():
    final, _ = tm.ex2_backward_search(10.0)
    assert sorted(final) == [5, 7, 8]                          # tab. 9.6
    assert abs(tm.ex2_cost({5: .16, 7: .16, 8: .088}, {}) - 0.451) < 1e-3   # tab. 9.7
    assert abs(tm.ex2_cost({5: .131}, {"5-7A": .03}) - 0.41) < 1e-3        # tab. 9.8


def test_example3_equilibria():
    for mode, d0 in {1: 0.8342, 2: 0.4603, 4: 0.4400}.items():  # tab. 9.10
        assert abs(tm.smib_equilibrium(tm.EX3_MODES[mode][2])[0] - d0) < 2e-3
    t = tm.smib_critical_switch_time(0.3, 0.1, 0.5, 2.25)
    assert 0.3 < t < 0.6        # 0.3 s ratuje, ~0.53 s już nie (rys. 9.13)


def test_example4_market_failure_and_pigou():
    s = tm.ex4_solve(tm.Ex4Params())
    assert s["I_mkt"] > s["I_soc"] and s["loss"] > 0
    s0 = tm.ex4_solve(tm.Ex4Params(alpha_depends=False))
    assert abs(s0["I_mkt"] - s0["I_soc"]) < 1e-6


def test_example5_efficiency():
    p = tm.Ex5Params()
    s = tm.ex5_solve(p)
    r = s["res"]
    assert abs(s["I"] - s["I_grid"]) < 0.2
    assert abs(r["eta"] - 2 * p.cI * s["I"]) < 1e-6           # C'(I*) = eta
    assert abs(r["pi3"] - (r["pi2"] + r["eta"] / 4)) < 1e-6    # no-arbitrage from bus 2
