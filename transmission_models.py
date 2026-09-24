"""
Modele obliczeniowe do rozdziału 9:
"Models for Transmission Expansion Planning Based on Reconfigurable Capacitor Switching"
(McCalley, Kumar, Ajjarapu, Volij, Liu, Jin, Shang - Iowa State University).

Moduł nie zależy od tkintera - można go testować i używać samodzielnie.
Każdy przykład (Example 1..5) ma tu swoją funkcję/klasę obliczeniową.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog, brentq


# =============================================================================
# PRZYKŁAD 1 - planowanie nowych linii (DC power flow + wybór 0/1 linii)
# =============================================================================
@dataclass
class Ex1Data:
    """Dane z rys. 9.5 i tab. 9.2 (wszystko w jednostkach względnych p.u.)."""
    Cg: tuple = (1.0, 1.5, 3.0)            # koszt produkcji 1 p.u. w węzłach 1,2,3
    Pg_max: tuple = (4.0, 4.0, 1.5)        # moc maksymalna generatorów
    Pd: tuple = (4.0, 0.8, 3.0)            # obciążenia węzłów
    growth: float = 1.0                    # współczynnik wzrostu (a >= 1)
    # linie: (od, do, X, Pmax, koszt budowy, kandydat?)
    lines: list = field(default_factory=lambda: [
        ["1-2", 0, 1, 0.2, 1.5, 0.0, False],
        ["1-3", 0, 2, 0.3, 1.0, 0.0, False],
        ["2-3", 1, 2, 0.3, 1.0, 0.0, False],
        # kandydaci - reaktancja nie jest podana w książce, przyjęto
        # identyczną jak linia równoległa (0.3 p.u.), co odtwarza wynik rys. 9.6
        ["1-3B", 0, 2, 0.3, 1.0, 1.0, True],
        ["2-3B", 1, 2, 0.3, 1.0, 1.0, True],
    ])


def ex1_dispatch(data: Ex1Data, built: tuple):
    """Optymalny rozdział obciążeń (DC-OPF) dla ustalonego zestawu linii.

    Zmienne: [Pg1,Pg2,Pg3, th1,th2 (th3=0 - węzeł odniesienia)].
    Zwraca słownik z wynikami lub None gdy zadanie niewykonalne.
    """
    active = [ln for ln in data.lines if (not ln[6]) or built[[l[0] for l in data.lines if l[6]].index(ln[0])]]
    n_var = 5
    c = np.array(list(data.Cg) + [0, 0])
    a = data.growth
    Pd = np.array(data.Pd) * a
    # Bilans mocy w każdym węźle: Pg_i - suma przepływów wychodzących = Pd_i
    A_eq = np.zeros((3, n_var))
    for i in range(3):
        A_eq[i, i] = 1.0
    for _, f, t, X, _, _, _ in active:
        for node, sgn in ((f, 1), (t, -1)):
            # przepływ f->t = (th_f - th_t)/X
            if f < 2:
                A_eq[node, 3 + f] -= sgn / X
            if t < 2:
                A_eq[node, 3 + t] += sgn / X
    b_eq = Pd
    # Ograniczenia przepustowości |P_b| <= Pmax
    A_ub, b_ub = [], []
    for _, f, t, X, Pmax, _, _ in active:
        row = np.zeros(n_var)
        if f < 2:
            row[3 + f] += 1 / X
        if t < 2:
            row[3 + t] -= 1 / X
        A_ub += [row, -row]
        b_ub += [Pmax, Pmax]
    bounds = [(0, pm * a) for pm in data.Pg_max] + [(None, None)] * 2
    res = linprog(c, A_ub=np.array(A_ub), b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if res.status != 0:
        return None
    th = np.array([res.x[3], res.x[4], 0.0])
    flows = {ln[0]: (th[ln[1]] - th[ln[2]]) / ln[3] for ln in active}
    inv = sum(ln[5] for ln in active if ln[6])
    lmp = np.array(res.eqlin.marginals) if res.eqlin is not None else None
    return dict(Pg=res.x[:3], theta=th, flows=flows, prod_cost=res.fun,
                inv_cost=inv, total=res.fun + inv, lmp=lmp)


def ex1_solve_all(data: Ex1Data):
    """Pełny przegląd (branch & bound w wersji 'na siłę' - 2^n kombinacji)."""
    cands = [ln[0] for ln in data.lines if ln[6]]
    out = []
    for combo in itertools.product((0, 1), repeat=len(cands)):
        r = ex1_dispatch(data, combo)
        name = "+".join(c for c, z in zip(cands, combo) if z) or "brak nowych"
        out.append((name, combo, r))
    feas = [o for o in out if o[2] is not None]
    best = min(feas, key=lambda o: o[2]["total"]) if feas else None
    return out, best


# =============================================================================
# PRZYKŁAD 2 - kompensacja bocznikowa/szeregowa i zapas stabilności napięciowej
# =============================================================================
# Tab. 9.6 - czułości zapasu na kondensator w danym węźle (dla kolejnych kroków)
EX2_BUSES = [5, 7, 8, 9, 6, 4]
EX2_SENS = {  # kolumny: brak, 6, 5, 4, 3, 2 kondensatory
    5: [0.738, 0.809, 0.808, 0.807, 0.804, 0.756],
    7: [0.334, 0.360, 0.359, 0.358, 0.357, 0.352],
    8: [0.240, 0.263, 0.262, 0.261, 0.260, None],
    9: [0.089, 0.098, 0.097, 0.096, None, None],
    6: [0.046, 0.051, 0.051, None, None, None],
    4: [0.019, 0.021, None, None, None, None],
}
EX2_LOADABILITY = [389.8, 414.4, 414.0, 413.2, 411.7, 407.6]
EX2_MARGIN = [4.73, 11.34, 11.24, 11.02, 10.61, 9.51]
EX2_BASE_LOAD = 372.2
EX2_COSTS = dict(Cv_sh=0.15, Cf_sh=0.13, Cv_se=0.35, Cf_se=0.25)


def ex2_margin_linear(sizes: dict, Bmax=0.16):
    """Liniowe oszacowanie zapasu [%] z czułości (kolumna '6 cntrls').

    Model skalibrowany tak, by 6 kondensatorów po 0.16 p.u. dawało 11.34 %.
    To jest dokładnie idea z książki: margines ~ margines0 + sum(s_i * dB_i).
    """
    s6 = {b: EX2_SENS[b][1] for b in EX2_BUSES}
    k = (EX2_MARGIN[1] - EX2_MARGIN[0]) / (sum(s6.values()) * Bmax)
    return EX2_MARGIN[0] + k * sum(s6[b] * sizes.get(b, 0.0) for b in EX2_BUSES)


def ex2_backward_search(required=10.0, Bmax=0.16):
    """Wyszukiwanie wsteczne: zaczynamy od wszystkich kondensatorów i usuwamy
    ten o najmniejszej czułości, dopóki zapas >= wymagany."""
    on = list(EX2_BUSES)
    steps = [(list(on), ex2_margin_linear({b: Bmax for b in on}, Bmax))]
    while len(on) > 1:
        weakest = min(on, key=lambda b: EX2_SENS[b][1])
        trial = [b for b in on if b != weakest]
        m = ex2_margin_linear({b: Bmax for b in trial}, Bmax)
        steps.append((trial, m))
        if m < required:
            break
        on = trial
    return on, steps


def ex2_cost(shunt: dict, series: dict, c=EX2_COSTS):
    """Koszt = suma (koszt stały + koszt zmienny * rozmiar) dla użytych urządzeń."""
    tot = 0.0
    for v in shunt.values():
        if v > 0:
            tot += c["Cf_sh"] + c["Cv_sh"] * v
    for v in series.values():
        if v > 0:
            tot += c["Cf_se"] + c["Cv_se"] * v
    return tot


def pv_curve(Qc=0.0, Xc=0.0, X=0.5, E=1.0, pf=0.95, npts=400):
    """Krzywa 'nosa' P-V dla układu 2-węzłowego: źródło E -- jX -- odbiór.

    Qc - moc kondensatora bocznikowego przy odbiorze (B=Qc przy V=1),
    Xc - reaktancja kondensatora szeregowego (zmniejsza X).
    Zwraca (P_górna, V_górna, P_dolna, V_dolna, Pmax).
    """
    Xe = max(X - Xc, 1e-3)
    tanphi = np.tan(np.arccos(pf))
    V = np.linspace(0.05, 1.6, npts * 4)
    # Dla odbioru P + jQ z Q = P tanphi - B V^2 (bocznik jako susceptancja)
    # równanie: (P Xe)^2 + (Q Xe + V^2)^2 = (E V)^2  -> rozwiązujemy względem P
    B = Qc
    # (1+tan^2) Xe^2 P^2 + 2 Xe tan (V^2 - B Xe V^2) P + (V^2 - B Xe V^2)^2 - E^2 V^2 = 0
    w = V ** 2 * (1 - B * Xe)
    a = (1 + tanphi ** 2) * Xe ** 2
    b = 2 * Xe * tanphi * w
    cc = w ** 2 - E ** 2 * V ** 2
    disc = b ** 2 - 4 * a * cc
    ok = disc >= 0
    P = (-b[ok] + np.sqrt(disc[ok])) / (2 * a)
    Vv = V[ok]
    mask = P >= 0
    P, Vv = P[mask], Vv[mask]
    if len(P) == 0:
        return np.array([]), np.array([]), 0.0, 0.0
    i = int(np.argmax(P))
    return P, Vv, float(P[i]), float(Vv[i])


# =============================================================================
# PRZYKŁAD 3 - obszar stabilności układu maszyna - sieć sztywna (SMIB)
# =============================================================================
EX3_M = 0.026     # s^2/rad
EX3_D = 0.12
EX3_PM = 1.0
EX3_MODES = {  # tryb: (szeregowy, bocznikowy, PeM) - tab. 9.10
    1: ("wył.", "wył.", 1.35),
    2: ("zał.", "wył.", 2.25),
    3: ("wył.", "zał.", 1.543),
    4: ("zał.", "zał.", 2.3478),
}


def smib_rhs(delta, omega, PeM, M=EX3_M, D=EX3_D, Pm=EX3_PM):
    """dδ/dt = ω ;  M dω/dt = Pm - PeM sin δ - D ω"""
    return omega, (Pm - PeM * np.sin(delta) - D * omega) / M


def smib_equilibrium(PeM, Pm=EX3_PM):
    """Stabilny punkt równowagi (SEP) i niestabilny (UEP)."""
    if Pm > PeM:
        return None, None
    d0 = np.arcsin(Pm / PeM)
    return d0, np.pi - d0


def smib_simulate(segments, x0=None, dt=1e-3, Pm=EX3_PM):
    """Symulacja RK4 z kolejnymi odcinkami [(PeM, czas_trwania), ...].

    Zwraca t, delta, omega oraz indeksy przełączeń.
    """
    if x0 is None:
        x0 = (smib_equilibrium(EX3_MODES[1][2])[0], 0.0)
    d, w = x0
    T, Dl, Wl, marks = [0.0], [d], [w], []
    t = 0.0
    for PeM, dur in segments:
        n = max(1, int(round(dur / dt)))
        for _ in range(n):
            k1 = smib_rhs(d, w, PeM, Pm=Pm)
            k2 = smib_rhs(d + dt / 2 * k1[0], w + dt / 2 * k1[1], PeM, Pm=Pm)
            k3 = smib_rhs(d + dt / 2 * k2[0], w + dt / 2 * k2[1], PeM, Pm=Pm)
            k4 = smib_rhs(d + dt * k3[0], w + dt * k3[1], PeM, Pm=Pm)
            d += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            w += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            t += dt
            T.append(t); Dl.append(d); Wl.append(w)
            if abs(d) > 50:     # utrata synchronizmu - dalej nie ma sensu liczyć
                break
        marks.append(len(T) - 1)
    return np.array(T), np.array(Dl), np.array(Wl), marks


def smib_region(PeM, dlim=(-5, 5), wlim=(-20, 20), n=161, T=4.0, dt=4e-3,
                eps=0.15, Pm=EX3_PM):
    """Obszar przyciągania (obszar stabilności) SEP na siatce stanu.

    Zamiast równania HJI (jak w książce) używamy równoważnej idei:
    punkt należy do obszaru, jeśli trajektoria z niego wpada do małej kuli
    o promieniu eps wokół SEP (lub jej okresowej kopii d0 + 2k*pi -
    w modelu wahadła te kopie to fizycznie ten sam stan wirnika po poślizgu
    biegunów, więc liczymy je jako niestabilne - poślizg to utrata synchronizmu).
    """
    d0, _ = smib_equilibrium(PeM, Pm)
    dd = np.linspace(*dlim, n)
    ww = np.linspace(*wlim, n)
    Dg, Wg = np.meshgrid(dd, ww)
    d, w = Dg.copy(), Wg.copy()
    inside = np.zeros_like(d, dtype=bool)
    steps = int(T / dt)
    for _ in range(steps):
        k1 = smib_rhs(d, w, PeM, Pm=Pm)
        k2 = smib_rhs(d + dt / 2 * k1[0], w + dt / 2 * k1[1], PeM, Pm=Pm)
        k3 = smib_rhs(d + dt / 2 * k2[0], w + dt / 2 * k2[1], PeM, Pm=Pm)
        k4 = smib_rhs(d + dt * k3[0], w + dt * k3[1], PeM, Pm=Pm)
        d = d + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        w = w + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        d = np.clip(d, -60, 60)
        inside |= ((d - d0) ** 2 + (w / 10) ** 2) < eps ** 2
    return dd, ww, inside.astype(float)


def smib_critical_switch_time(PeM_fault, t_clear, PeM_post, PeM_ctrl,
                              tmax=2.0, Pm=EX3_PM):
    """Najpóźniejszy moment załączenia kondensatora, który jeszcze ratuje
    stabilność (bisekcja po czasie przełączenia)."""
    def stable(ts):
        segs = [(PeM_fault, t_clear), (PeM_post, max(ts - t_clear, 0)),
                (PeM_ctrl, 4.0)]
        _, D, W, _ = smib_simulate(segs, dt=2e-3, Pm=Pm)
        d0 = smib_equilibrium(PeM_ctrl, Pm)[0]
        return d0 is not None and abs(D[-1] - d0) < 0.1 and abs(W[-1]) < 0.5
    if not stable(t_clear):
        return None
    if stable(tmax):
        return tmax
    lo, hi = t_clear, tmax
    for _ in range(25):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if stable(mid) else (lo, mid)
    return lo


# =============================================================================
# PRZYKŁAD 4 - inwestycja w linię zmienia rozpływ -> zawodność rynku
# =============================================================================
@dataclass
class Ex4Params:
    load: float = 1000.0     # MW w węźle 3
    a1: float = 10.0         # C1 = a1 P + b1 P^2  [$/h]
    b1: float = 0.01
    a2: float = 10.0
    b2: float = 0.03
    k0: float = 100.0        # początkowa przepustowość linii 3 [MW]
    kr: float = 100.0        # przepustowość "odniesienia" (dla niej alfa=1/3)
    cI: float = 0.05         # C(I) = cI * I^2  [$/h]
    alpha_depends: bool = True  # False -> alfa stałe (brak zawodności rynku)


def ex4_alpha(k, p: Ex4Params):
    """Współczynnik rozpływu linii 3 (1->2).  Linie 1 i 2 mają reaktancję x,
    linia 3 ma x3 = x*kr/k (więcej przewodów = mniejsza impedancja).
    Z prawa Kirchhoffa: P12 = (Pg1-Pg2) / (2 + x3/x) = (Pg1-Pg2) * k/(2k+kr)."""
    if not p.alpha_depends:
        return 1.0 / 3.0
    return k / (2 * k + p.kr)


def ex4_dalpha(k, p: Ex4Params):
    if not p.alpha_depends:
        return 0.0
    return p.kr / (2 * k + p.kr) ** 2


def ex4_dispatch(I, p: Ex4Params):
    """Najtańszy rozdział mocy przy danej inwestycji I (1 zmienna: Pg1)."""
    k = p.k0 + I
    al = ex4_alpha(k, p)
    # bez ograniczeń: a1 + 2 b1 P1 = a2 + 2 b2 (L - P1)
    P1 = (p.a2 - p.a1 + 2 * p.b2 * p.load) / (2 * (p.b1 + p.b2))
    P1 = min(max(P1, 0.0), p.load)
    mu = 0.0
    if al * (2 * P1 - p.load) > k:        # linia przeciążona -> ograniczamy
        P1 = (k / al + p.load) / 2
        mc1 = p.a1 + 2 * p.b1 * P1
        mc2 = p.a2 + 2 * p.b2 * (p.load - P1)
        mu = (mc2 - mc1) / (2 * al)        # cena cienia przepustowości [$/MWh]
    P2 = p.load - P1
    gen = p.a1 * P1 + p.b1 * P1 ** 2 + p.a2 * P2 + p.b2 * P2 ** 2
    return dict(P1=P1, P2=P2, flow=al * (P1 - P2), k=k, alpha=al, mu=mu,
                gen_cost=gen, inv_cost=p.cI * I ** 2, total=gen + p.cI * I ** 2,
                pi1=p.a1 + 2 * p.b1 * P1, pi2=p.a2 + 2 * p.b2 * P2)


def ex4_marginal(I, p: Ex4Params):
    """Krańcowa korzyść społeczna, krańcowa korzyść rynkowa inwestora i koszt."""
    r = ex4_dispatch(I, p)
    k = r["k"]
    social = r["mu"] * (1 - ex4_dalpha(k, p) * (r["P1"] - r["P2"]))
    market = r["mu"]
    return social, market, 2 * p.cI * I


def ex4_solve(p: Ex4Params, Imax=600.0):
    def root(fun):
        if fun(0.0) <= 0:
            return 0.0
        if fun(Imax) > 0:
            return Imax
        return brentq(fun, 0.0, Imax)
    I_soc = root(lambda I: ex4_marginal(I, p)[0] - ex4_marginal(I, p)[2])
    I_mkt = root(lambda I: ex4_marginal(I, p)[1] - ex4_marginal(I, p)[2])
    rs, rm = ex4_dispatch(I_soc, p), ex4_dispatch(I_mkt, p)
    # Podatek Pigou: t* = dα/dk * (Pg1-Pg2)  (ad-valorem, ułamek ceny)
    tax = ex4_dalpha(rs["k"], p) * (rs["P1"] - rs["P2"])
    return dict(I_soc=I_soc, I_mkt=I_mkt, soc=rs, mkt=rm, tax=tax,
                loss=rm["total"] - rs["total"])


# =============================================================================
# PRZYKŁAD 5 - kondensator załączany tylko przy awarii
# =============================================================================
@dataclass
class Ex5Params:
    Pd: float = 400.0     # MW
    a1: float = 10.0
    b1: float = 0.05
    a2: float = 20.0
    b2: float = 0.05
    k1: float = 100.0     # przepustowość każdej z linii 21 i 22 [MW]
    margin: float = 0.10  # k2 = (1+margin) k1
    cI: float = 2.0       # C(I) = cI * I^2


def ex5_flows(P1, P2):
    """Przepływ normalny w linii 21 (= w 22) i awaryjny w linii 22."""
    return P1 / 3 + P2 / 6, P1 / 2 + P2 / 4


def ex5_dispatch(I, p: Ex5Params):
    """Najtańszy rozdział przy danej zdolności kondensatora I.
    Zwraca też mnożniki Lagrange'a: mu (stan normalny), eta (awaria)."""
    k2 = (1 + p.margin) * p.k1
    P1u = (p.a2 - p.a1 + 2 * p.b2 * p.Pd) / (2 * (p.b1 + p.b2))
    P1u = min(max(P1u, 0.0), p.Pd)
    # ograniczenia jako górne limity P1 (bo P2 = Pd - P1):
    lim_n = (p.k1 - p.Pd / 6) / (1 / 3 - 1 / 6)          # normalny
    lim_c = (k2 + I - p.Pd / 4) / (1 / 2 - 1 / 4)        # awaryjny
    P1 = min(P1u, lim_n, lim_c)
    P1 = max(P1, 0.0)
    P2 = p.Pd - P1
    mc1 = p.a1 + 2 * p.b1 * P1
    mc2 = p.a2 + 2 * p.b2 * P2
    mu = eta = 0.0
    if P1 < P1u - 1e-9:
        gap = mc2 - mc1
        if lim_c <= lim_n:
            eta = gap / (1 / 2 - 1 / 4)     # = 4 * (mc2 - mc1)
        else:
            mu = gap / (1 / 3 - 1 / 6) / 2  # dwie równoległe linie
    gen = p.a1 * P1 + p.b1 * P1 ** 2 + p.a2 * P2 + p.b2 * P2 ** 2
    fn, fc = ex5_flows(P1, P2)
    # ceny węzłowe: lambda = cena w węźle 3 (odbiór)
    pi1, pi2 = mc1, mc2
    pi3 = pi1 + 2 * mu / 3 + eta / 2       # warunek braku arbitrażu (9.94)
    return dict(P1=P1, P2=P2, fn=fn, fc=fc, k2=k2, mu=mu, eta=eta,
                gen_cost=gen, inv_cost=p.cI * I ** 2, total=gen + p.cI * I ** 2,
                pi1=pi1, pi2=pi2, pi3=pi3, lim_n=lim_n, lim_c=lim_c)


def ex5_solve(p: Ex5Params, Imax=300.0):
    """Optimum: C'(I) = eta(I)  (koszt krańcowy = oszczędność krańcowa)."""
    f = lambda I: ex5_dispatch(I, p)["eta"] - 2 * p.cI * I
    if f(0.0) <= 0:
        I = 0.0
    elif f(Imax) > 0:
        I = Imax
    else:
        I = brentq(f, 0.0, Imax)
    r = ex5_dispatch(I, p)
    # sprawdzenie "na siłę" - minimum kosztu całkowitego po siatce
    grid = np.linspace(0, Imax, 3001)
    tot = [ex5_dispatch(g, p)["total"] for g in grid]
    return dict(I=I, res=r, I_grid=float(grid[int(np.argmin(tot))]))
