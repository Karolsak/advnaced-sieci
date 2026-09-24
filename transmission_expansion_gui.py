"""
Interaktywna aplikacja Tkinter do rozdziału 9:
"Models for Transmission Expansion Planning Based on Reconfigurable Capacitor Switching"

Zakładki:
  0. Wstęp - o co chodzi w planowaniu rozbudowy sieci, kryteria N-1 / N-2 (tab. 9.1)
  1. Przykład 1 - budowa nowych linii w sieci 3-węzłowej (DC-OPF + decyzje 0/1)
  2. Przykład 2 - kondensatory bocznikowe/szeregowe a zapas stabilności napięciowej
  3. Przykład 3 - obszar stabilności generatora (SMIB) w 4 trybach sterowania
  4. Przykład 4 - inwestycja w linię a zawodność rynku (podatek Pigou)
  5. Przykład 5 - kondensator załączany w awarii - rynek działa efektywnie

Uruchomienie:  python transmission_expansion_gui.py
Wymagania:     numpy, scipy, matplotlib, tkinter
"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import FancyArrowPatch, Circle

import transmission_models as tm

BLUE, ORANGE, GREEN, RED, PURPLE, GRAY = "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#7f7f7f"


# =============================================================================
# Wspólna baza zakładki: lewa kolumna (sterowanie + wyjaśnienie), prawa (wykres)
# =============================================================================
class ExampleTab(ttk.Frame):
    title = ""
    explanation = ""

    def __init__(self, master):
        super().__init__(master)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, width=420)
        right = ttk.Frame(paned)
        paned.add(left, weight=0)
        paned.add(right, weight=1)

        inner = ttk.Notebook(left)
        inner.pack(fill=tk.BOTH, expand=True)
        self.ctrl = ttk.Frame(inner, padding=6)
        expl = ttk.Frame(inner)
        inner.add(self.ctrl, text="⚙ Sterowanie")
        inner.add(expl, text="📖 Wyjaśnienie")

        txt = ScrolledText(expl, wrap=tk.WORD, font=("DejaVu Sans", 10), width=52)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.tag_configure("h", font=("DejaVu Sans", 12, "bold"), foreground="#0b4f8a")
        for line in self.explanation.strip("\n").splitlines():
            if line.startswith("## "):
                txt.insert(tk.END, line[3:] + "\n", "h")
            else:
                txt.insert(tk.END, line + "\n")
        txt.configure(state=tk.DISABLED)

        self.fig = Figure(figsize=(9, 6.5), dpi=90, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        NavigationToolbar2Tk(self.canvas, right).update()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.result = tk.StringVar()
        self.build_controls()
        ttk.Label(self.ctrl, textvariable=self.result, justify=tk.LEFT,
                  font=("DejaVu Sans Mono", 9), foreground="#003366",
                  wraplength=400).pack(fill=tk.X, pady=6)
        self._pending = None
        self.update_plot()

    # --- pomocnicze widżety ---------------------------------------------------
    def slider(self, label, var_from, var_to, init, res=0.01, fmt="{:.2f}", parent=None):
        parent = parent or self.ctrl
        fr = ttk.Frame(parent)
        fr.pack(fill=tk.X, pady=1)
        var = tk.DoubleVar(value=init)
        lab = ttk.Label(fr, text=f"{label}: {fmt.format(init)}", width=44, anchor="w")
        lab.pack(anchor="w")

        def moved(_=None):
            v = round(var.get() / res) * res
            lab.config(text=f"{label}: {fmt.format(v)}")
            self.schedule()
        ttk.Scale(fr, from_=var_from, to=var_to, variable=var, command=moved).pack(fill=tk.X)
        var.get_r = lambda: round(var.get() / res) * res
        return var

    def check(self, label, init=False, parent=None):
        var = tk.BooleanVar(value=init)
        ttk.Checkbutton(parent or self.ctrl, text=label, variable=var,
                        command=self.schedule).pack(anchor="w")
        return var

    def section(self, text):
        ttk.Label(self.ctrl, text=text, font=("DejaVu Sans", 10, "bold"),
                  foreground="#0b4f8a").pack(anchor="w", pady=(8, 2))

    def schedule(self):
        """Opóźnione odświeżenie - suwak nie zamraża okna przy każdym pikselu."""
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(120, self._do_update)

    def _do_update(self):
        self._pending = None
        self.update_plot()

    def build_controls(self):
        pass

    def update_plot(self):
        pass


# =============================================================================
# ZAKŁADKA 0 - Wstęp
# =============================================================================
class IntroTab(ExampleTab):
    title = "Wstęp"
    explanation = """
## Po co w ogóle planować sieć przesyłową?
Wyobraź sobie autostradę między miastami. Jeśli ruch rośnie co roku o kilka procent, a nowa autostrada powstaje 5-10 lat, trzeba zdecydować DZIŚ, co zbudować na przyszłość. Tak samo jest z liniami wysokiego napięcia: prąd płynie „autostradami" 110/220/400 kV z elektrowni do miast.

## Problem z wykresu 9.1
W USA od lat 80. zapotrzebowanie na energię rosło szybciej niż długość linii przesyłowych. Skutek: sieć jest coraz bardziej „zakorkowana" (ang. congestion). Korek w sieci oznacza, że tania elektrownia nie może oddać całej mocy i trzeba uruchamiać droższe - rachunek płaci odbiorca.

## Dwa sposoby na korek
1. Zbudować nową linię (drogie, wolne, trudne pozwolenia).
2. „Zmądrzyć" istniejącą sieć: dodać kondensatory szeregowe (skracają elektrycznie linię) lub bocznikowe (podtrzymują napięcie), włączane przełącznikami, gdy są potrzebne. To tańsze i szybsze - i właśnie o tym jest rozdział 9.

## Kryteria niezawodności (tab. 9.1 - po prawej)
Inżynier sprawdza nie tylko stan normalny, ale też awarie:
• N-0 - wszystko działa: napięcia i prądy w normie.
• N-1 - wyłącza się JEDEN element (linia, trafo, generator) - system nadal musi działać bez wyłączania odbiorców. Spadek napięcia chwilowo max 25 %, po ustaleniu max 5 %.
• N-2 - dwa elementy naraz: dopuszczamy więcej (np. kontrolowane odłączenie części odbiorców).
• Zdarzenia ekstremalne - ocenia inżynier.
Im rzadsze zdarzenie, tym łagodniejsze wymagania - to rozsądny kompromis między kosztem a bezpieczeństwem.

## Jak czytać aplikację
Każda zakładka to jeden przykład z rozdziału. Po lewej: suwaki (⚙) i wyjaśnienie (📖). Po prawej: wykresy, które przeliczają się na żywo. Pasek narzędzi pod wykresem pozwala powiększać (lupa), przesuwać (krzyżyk) i zapisać obraz (dyskietka).

## Słowniczek
• p.u. (per unit) - wartość względna, np. 1.0 p.u. = 100 MW.
• DC power flow - uproszczony model rozpływu mocy: moc płynąca linią = różnica kątów napięć / reaktancja. Jak woda płynąca z wyższego zbiornika do niższego.
• Reaktancja X - „opór" linii dla prądu przemiennego. Mniejsze X = więcej mocy płynie tą drogą.
• Kondensator szeregowy - zmniejsza X linii → linia „przyciąga" więcej mocy i przesyła ją stabilniej.
• Kondensator bocznikowy - dostarcza mocy biernej, podnosi napięcie.
"""

    def build_controls(self):
        self.section("Tabela 9.1 i trendy (rys. 9.1)")
        self.growth = self.slider("Roczny wzrost obciążenia [%]", 0, 5, 2.0, 0.1, "{:.1f}")
        self.tgrowth = self.slider("Roczny wzrost długości linii [%]", 0, 5, 0.8, 0.1, "{:.1f}")

    def update_plot(self):
        self.fig.clear()
        ax = self.fig.add_subplot(2, 1, 1)
        yrs = np.arange(0, 31)
        L = (1 + self.growth.get_r() / 100) ** yrs
        T = (1 + self.tgrowth.get_r() / 100) ** yrs
        ax.plot(1990 + yrs, 100 * L, color=RED, lw=2, label="Obciążenie (zapotrzebowanie)")
        ax.plot(1990 + yrs, 100 * T, color=BLUE, lw=2, label="Długość linii przesyłowych")
        ax.fill_between(1990 + yrs, 100 * T, 100 * L, where=L > T, color=RED, alpha=.12,
                        label="Rosnący „korek” w sieci")
        ax.set_title("Dlaczego sieć się korkuje: indeks (1990 = 100)")
        ax.set_xlabel("Rok"); ax.set_ylabel("Indeks"); ax.grid(alpha=.3); ax.legend(loc="upper left")
        ratio = T[-1] / L[-1]
        self.result.set(f"Po 30 latach na 1 MW obciążenia przypada\n{ratio*100:.0f}% zdolności przesyłowej z 1990 r.")

        ax2 = self.fig.add_subplot(2, 1, 2)
        ax2.axis("off")
        rows = [["A (N-0)", "Brak awarii", "normalne", "normalne", "nie"],
                ["B (N-1)", "1 element", "ΔU≤25%, ΔU>20% max 20 cykli,\nf>59.6 Hz (max 6 cykli)", "ΔU≤5%, obciąż.≤znamion.", "nie"],
                ["C (N-2)", "2 elementy", "ΔU≤30%, ΔU>20% max 40 cykli,\nf>59.0 Hz (max 6 cykli)", "ΔU≤10%, obciąż.≤awaryjne", "planowo"],
                ["D", "Ekstremalne", "ocena inżyniera", "ocena inżyniera", "tak"]]
        t = ax2.table(cellText=rows, colLabels=["Poziom", "Zdarzenie", "Stan przejściowy",
                                                "Stan ustalony", "Odłączenie odbiorców"],
                      loc="center", cellLoc="center")
        t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 2.6)
        for (r, c), cell in t.get_celld().items():
            if r == 0:
                cell.set_facecolor("#cfe2f3"); cell.set_text_props(weight="bold")
        ax2.set_title("Tab. 9.1 - typowe kryteria zakłócenie/wymagania (wersja poglądowa)")
        self.canvas.draw_idle()


# =============================================================================
# ZAKŁADKA 1 - Przykład 1
# =============================================================================
class Example1Tab(ExampleTab):
    title = "Przykład 1: nowe linie"
    explanation = """
## Przykład 1 - którą linię zbudować?
Mamy 3 węzły (miasta/stacje). W każdym jest elektrownia i odbiorcy:
• Węzeł 1: tania elektrownia (koszt 1.0 za p.u.), odbiór 4.0 p.u.
• Węzeł 2: średnia (1.5), odbiór tylko 0.8 → może wysyłać nadwyżkę.
• Węzeł 3: droga elektrownia (3.0), max 1.5, odbiór 3.0 → musi importować.
Kandydaci do budowy: druga linia 1-3 („1-3B") i druga linia 2-3 („2-3B"), każda kosztuje 1.0.

## Jak płynie moc (model DC)
Moc w linii = (θ_od − θ_do) / X. Kąt θ to „wysokość" napięcia - moc spływa z wyższego kąta do niższego, jak woda. Ważne: NIE da się wskazać, którędy moc ma płynąć! Rozkłada się sama według reaktancji (prawa Kirchhoffa). Dlatego dołożenie linii zmienia przepływy w całej sieci.

## Co liczy program
Dla każdej z 4 kombinacji (nic / 1-3B / 2-3B / obie) rozwiązuje zadanie programowania liniowego: „wyprodukuj energię jak najtaniej, nie przeciążając żadnej linii". Potem dodaje koszt budowy i wybiera minimum. W książce to zadanie mieszane całkowitoliczbowe (MIP) rozwiązywane metodą podziału i ograniczeń (branch & bound) - dla 2 kandydatów możemy po prostu sprawdzić wszystkie 2² = 4 przypadki.

## Wynik (jak w książce, rys. 9.6)
Bez nowych linii linia 2-3 (limit 1.0) jest „zakorkowana", więc węzeł 3 musi włączyć drogą elektrownię (1.4 p.u. × 3.0). Po zbudowaniu 2-3B tania moc z węzła 2 dociera do 3: Pg1=4.0, Pg2=3.4, Pg3=0.4. Koszt: 10.3 + 1.0 (linia) = 11.3 < 11.8.
Ciekawostka: linia 1-3B jest gorsza niż nic! Zmienia rozpływ tak, że linia 2-3 nadal się korkuje, a przez 1-2 płynie więcej.

## Ceny węzłowe (LMP)
Program pokazuje też cenę energii w każdym węźle - ile kosztuje dostarczenie JEDNEGO dodatkowego MW właśnie tam. Różne ceny w węzłach = sygnał korka. To fundament rynków energii (np. PJM w USA).

## Pobaw się
• Zwiększ „wzrost obciążenia" - od pewnego momentu zadanie staje się niewykonalne (brakuje mocy lub przepustowości).
• Podnieś koszt linii 2-3B powyżej 0.5 - opłaca się dopiero budowa... niczego.
• Zmniejsz koszt elektrowni 3 - korek przestaje „boleć".
"""

    def build_controls(self):
        self.section("Parametry (tab. 9.2)")
        self.cg1 = self.slider("Koszt Cg1", 0.5, 4, 1.0)
        self.cg2 = self.slider("Koszt Cg2", 0.5, 4, 1.5)
        self.cg3 = self.slider("Koszt Cg3", 0.5, 6, 3.0)
        self.c13 = self.slider("Koszt budowy linii 1-3B", 0, 3, 1.0)
        self.c23 = self.slider("Koszt budowy linii 2-3B", 0, 3, 1.0)
        self.p23 = self.slider("Limit linii 2-3 [p.u.]", 0.3, 3, 1.0)
        self.grow = self.slider("Wzrost obciążenia a", 0.8, 1.3, 1.0, 0.01)
        self.section("Pokaż na schemacie wariant")
        self.show = tk.StringVar(value="optymalny")
        for v in ("optymalny", "brak nowych", "1-3B", "2-3B", "1-3B+2-3B"):
            ttk.Radiobutton(self.ctrl, text=v, value=v, variable=self.show,
                            command=self.schedule).pack(anchor="w")

    def update_plot(self):
        d = tm.Ex1Data(Cg=(self.cg1.get_r(), self.cg2.get_r(), self.cg3.get_r()),
                       growth=self.grow.get_r())
        d.lines[2][4] = self.p23.get_r()
        d.lines[3][5] = self.c13.get_r()
        d.lines[4][5] = self.c23.get_r()
        out, best = tm.ex1_solve_all(d)
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 2)
        ax = self.fig.add_subplot(gs[0, 0])
        names = [o[0] for o in out]
        prod = [o[2]["prod_cost"] if o[2] else 0 for o in out]
        inv = [o[2]["inv_cost"] if o[2] else 0 for o in out]
        x = np.arange(len(out))
        ax.bar(x, prod, color=BLUE, label="Koszt produkcji")
        ax.bar(x, inv, bottom=prod, color=ORANGE, label="Koszt budowy")
        for i, o in enumerate(out):
            if o[2] is None:
                ax.text(i, 0.3, "niewyko-\nnalne", ha="center", color=RED)
            else:
                ax.text(i, o[2]["total"] + .1, f"{o[2]['total']:.2f}", ha="center",
                        fontweight="bold" if best and o[0] == best[0] else None)
        if best:
            bi = names.index(best[0])
            ax.patches[bi].set_edgecolor(GREEN); ax.patches[bi].set_linewidth(3)
        ax.set_xticks(x, names, rotation=15, fontsize=8)
        ax.set_title("Koszt całkowity wariantów"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3)

        choice = best if self.show.get() == "optymalny" else next(o for o in out if o[0] == self.show.get())
        axn = self.fig.add_subplot(gs[:, 1])
        self.draw_network(axn, d, choice)

        ax3 = self.fig.add_subplot(gs[1, 0])
        if choice and choice[2]:
            r = choice[2]
            pmax = np.array(d.Pg_max) * d.growth
            xb = np.arange(3)
            ax3.bar(xb - .2, pmax, .4, color="#cccccc", label="Pg max")
            ax3.bar(xb - .2, r["Pg"], .4, color=GREEN, label="Pg")
            ax3.bar(xb + .2, np.array(d.Pd) * d.growth, .4, color=RED, alpha=.7, label="Pd")
            ax3.set_xticks(xb, ["Węzeł 1", "Węzeł 2", "Węzeł 3"])
            ax32 = ax3.twinx()
            ax32.plot(xb, r["lmp"], "k--o", label="Cena węzłowa")
            ax32.set_ylabel("Cena węzłowa (LMP)")
            ax3.set_title(f"Generacja i ceny: {choice[0]}")
            ax3.legend(loc="upper left", fontsize=8); ax32.legend(loc="upper right", fontsize=8)
        if best:
            r = best[2]
            self.result.set(f"OPTIMUM: {best[0]}\nPg = {np.round(r['Pg'], 3)}\n"
                            f"Produkcja {r['prod_cost']:.3f} + budowa {r['inv_cost']:.2f} = {r['total']:.3f}")
        else:
            self.result.set("Żaden wariant nie jest wykonalny - za mało mocy / przepustowości!")
        self.canvas.draw_idle()

    def draw_network(self, ax, d, choice):
        pos = {0: (0, 1), 1: (2, 1), 2: (1, -0.4)}
        ax.set_xlim(-.8, 2.8); ax.set_ylim(-1.1, 1.7); ax.axis("off"); ax.set_aspect("equal")
        if not choice or choice[2] is None:
            ax.set_title("Wariant niewykonalny"); return
        r = choice[2]
        offs = {"1-3": -0.12, "1-3B": 0.12, "2-3": 0.12, "2-3B": -0.12, "1-2": 0}
        for ln in d.lines:
            nm = ln[0]
            (x1, y1), (x2, y2) = pos[ln[1]], pos[ln[2]]
            dx, dy = x2 - x1, y2 - y1
            L = np.hypot(dx, dy); nx, ny = -dy / L * offs[nm], dx / L * offs[nm]
            built = nm in r["flows"]
            f = r["flows"].get(nm, 0.0)
            load = abs(f) / ln[4]
            col = RED if load > .999 else (ORANGE if load > .8 else GREEN)
            if not built:
                ax.plot([x1 + nx, x2 + nx], [y1 + ny, y2 + ny], ls=":", color=GRAY)
                continue
            ax.plot([x1 + nx, x2 + nx], [y1 + ny, y2 + ny], color=col, lw=2 + 3 * load,
                    ls="--" if ln[6] else "-")
            a, b = ((x1, y1), (x2, y2)) if f >= 0 else ((x2, y2), (x1, y1))
            mx, my = (a[0] + b[0]) / 2 + nx, (a[1] + b[1]) / 2 + ny
            ax.add_patch(FancyArrowPatch((mx - (b[0] - a[0]) * .08, my - (b[1] - a[1]) * .08),
                                         (mx + (b[0] - a[0]) * .08, my + (b[1] - a[1]) * .08),
                                         arrowstyle="-|>", mutation_scale=18, color="k"))
            ax.text(mx + nx * 2.2, my + ny * 2.2 + .08, f"{nm}\n{abs(f):.2f}/{ln[4]:.1f}",
                    fontsize=8, ha="center", color=col)
        for i, (x, y) in pos.items():
            ax.add_patch(Circle((x, y), .17, color="#0b4f8a"))
            ax.text(x, y, str(i + 1), color="w", ha="center", va="center", fontweight="bold")
            ax.text(x, y + (.3 if y > 0 else -.45),
                    f"Pg={r['Pg'][i]:.2f}\nPd={d.Pd[i]*d.growth:.2f}\nθ={r['theta'][i]:.3f}",
                    ha="center", fontsize=8)
        ax.set_title(f"Rozpływ mocy: {choice[0]}\n(zielona <80%, pomarańcz. >80%,\nczerwona = 100% obciążenia)")


# =============================================================================
# ZAKŁADKA 2 - Przykład 2
# =============================================================================
class Example2Tab(ExampleTab):
    title = "Przykład 2: kondensatory"
    explanation = """
## Przykład 2 - zamiast linii: kondensatory
System testowy WSCC 9-węzłowy (3 generatory, 3 odbiory A, B, C; łącznie 372.2 MW). Problem nie jest „korek cieplny", lecz STABILNOŚĆ NAPIĘCIOWA.

## Co to jest zapas stabilności napięciowej?
Gdy zwiększamy pobór mocy, napięcie u odbiorcy spada - najpierw powoli, potem gwałtownie, aż w punkcie „nosa" krzywej P-V (wykres u góry) sieć nie jest w stanie dostarczyć więcej. Dalej następuje lawinowy spadek napięcia (blackout - tak było np. w USA w 2003 r.).
Zapas = (moc na nosie − moc obecna) / moc obecna. Wymaganie: ≥ 10 % po awarii N-2.

## Dwie groźne awarie (tab. 9.5)
1. Wyłączenie obu linii 5-4A i 5-4B → zapas 4.73 %
2. Wyłączenie trafo T1 i linii 4-6 → zapas 4.67 %
Oba < 10 % → trzeba coś zrobić!

## Czułość - klucz do rozwiązania
Czułość mówi: „o ile wzrośnie zapas, jeśli w tym węźle dołożę trochę kondensatora". Kondensator w węźle 5 (przy największym odbiorze A, zasilanym promieniowo długą linią) ma czułość 0.8, a w węźle 4 tylko 0.02 - 40 razy mniej!

## Wyszukiwanie wsteczne (tab. 9.6, wykres środkowy)
Start: kondensatory we wszystkich 6 węzłach (zapas 11.34 %). W każdym kroku usuwamy ten o najmniejszej czułości: 4 → 6 → 9 → 8. Po usunięciu 8 zapas spada do 9.51 % < 10 %, więc 8 wraca. Wynik: węzły 5, 7, 8. To tzw. algorytm zachłanny - tani obliczeniowo, dlatego działa nawet dla tysięcy węzłów.

## Kondensator szeregowy vs bocznikowy (wykres dolny, tab. 9.7-9.8)
Koszt = koszt stały (przełącznik, montaż) + koszt zmienny × rozmiar.
• Tylko bocznikowe: 0.16 + 0.16 + 0.088 p.u. w węzłach 5, 7, 8 → koszt 0.451
• Szeregowy 0.03 p.u. w linii 5-7A + bocznik 0.131 w węźle 5 → koszt 0.41, czyli ~10 % taniej!
Szeregowy kondensator „skraca" linię elektrycznie - nos krzywej P-V przesuwa się w prawo mocniej niż przy boczniku.

## Pobaw się
• Suwakami Qc (bocznik) i Xc (szeregowy) zobacz, jak rośnie nos krzywej.
• Zmień wymagany zapas - algorytm wybierze inny zestaw węzłów.
• Zmień koszty jednostkowe - czy nadal opłaca się kondensator szeregowy?
"""

    def build_controls(self):
        self.section("Krzywa P-V (układ 2-węzłowy poglądowo)")
        self.qc = self.slider("Kondensator bocznikowy B [p.u.]", 0, 0.8, 0.0)
        self.xc = self.slider("Kondensator szeregowy Xc [p.u.]", 0, 0.3, 0.0)
        self.pf = self.slider("Współczynnik mocy odbioru cosφ", 0.8, 1.0, 0.95)
        self.section("Wyszukiwanie wsteczne (tab. 9.6)")
        self.req = self.slider("Wymagany zapas [%]", 5, 12, 10.0, 0.1, "{:.1f}")
        self.step = self.slider("Pokaż krok algorytmu", 0, 5, 5, 1, "{:.0f}")
        self.section("Koszty (tab. 9.4)")
        self.cfsh = self.slider("Koszt stały bocznika Cf", 0, 0.5, 0.13, 0.005, "{:.3f}")
        self.cvsh = self.slider("Koszt zmienny bocznika Cv", 0, 1, 0.15, 0.005, "{:.3f}")
        self.cfse = self.slider("Koszt stały szeregowego Cf", 0, 0.5, 0.25, 0.005, "{:.3f}")
        self.cvse = self.slider("Koszt zmienny szeregowego Cv", 0, 1, 0.35, 0.005, "{:.3f}")

    def update_plot(self):
        self.fig.clear()
        gs = self.fig.add_gridspec(3, 1, height_ratios=[1.1, 1, 0.9])
        # --- PV
        ax = self.fig.add_subplot(gs[0])
        pf = self.pf.get_r()
        P0, V0, pm0, vm0 = tm.pv_curve(0, 0, pf=pf)
        P, V, pm, vm = tm.pv_curve(self.qc.get_r(), self.xc.get_r(), pf=pf)
        ax.plot(P0, V0, color=GRAY, ls="--", label=f"bez kompensacji (Pmax={pm0:.3f})")
        ax.plot(P, V, color=BLUE, lw=2, label=f"z kompensacją (Pmax={pm:.3f})")
        ax.plot(pm, vm, "o", color=RED); ax.annotate("„nos” = granica stabilności", (pm, vm),
                                                     xytext=(10, -15), textcoords="offset points")
        Pop = 0.9 * pm0
        ax.axvline(Pop, color=GREEN, ls=":", label=f"punkt pracy P={Pop:.3f}")
        ax.set_xlabel("Moc czynna odbioru P [p.u.]"); ax.set_ylabel("Napięcie V [p.u.]")
        ax.set_ylim(0, 1.6); ax.grid(alpha=.3); ax.legend(fontsize=8, loc="lower left")
        ax.set_title(f"Krzywa P-V: zapas {100*(pm/Pop-1):.1f}% (bez kompensacji {100*(pm0/Pop-1):.1f}%)")
        # --- backward search
        ax2 = self.fig.add_subplot(gs[1])
        req = self.req.get_r()
        final, steps = tm.ex2_backward_search(req)
        k = min(int(self.step.get_r()), len(steps) - 1)
        on, m = steps[k]
        cols = [GREEN if b in on else "#dddddd" for b in tm.EX2_BUSES]
        sens = [tm.EX2_SENS[b][1] for b in tm.EX2_BUSES]
        ax2.bar([f"bus {b}" for b in tm.EX2_BUSES], sens, color=cols, edgecolor="k")
        ax2.set_ylabel("czułość zapasu")
        ax2b = ax2.twinx()
        ms = [s[1] for s in steps]
        ax2b.plot(np.linspace(0, 5, len(ms)), ms, "o-", color=PURPLE, label="zapas po kroku")
        ax2b.plot(np.linspace(0, 5, len(ms))[k], m, "s", ms=12, mfc="none", mec=RED, mew=2)
        ax2b.axhline(req, color=RED, ls="--", label=f"wymagane {req:.1f}%")
        ax2b.set_ylabel("zapas [%]"); ax2b.legend(fontsize=8, loc="upper right")
        ax2.set_title(f"Krok {k}: włączone {on} → zapas {m:.2f}%   |   WYNIK: {final}")
        # --- costs
        ax3 = self.fig.add_subplot(gs[2])
        c = dict(Cf_sh=self.cfsh.get_r(), Cv_sh=self.cvsh.get_r(),
                 Cf_se=self.cfse.get_r(), Cv_se=self.cvse.get_r())
        c1 = tm.ex2_cost({5: .16, 7: .16, 8: .088}, {}, c)
        c2 = tm.ex2_cost({5: .131}, {"5-7A": .03}, c)
        bars = ax3.barh(["Case 1: tylko boczniki\n(5,7,8)", "Case 2: szeregowy 5-7A\n+ bocznik 5"],
                        [c1, c2], color=[ORANGE, BLUE])
        for b, v in zip(bars, (c1, c2)):
            ax3.text(v, b.get_y() + b.get_height() / 2, f" {v:.3f}", va="center")
        ax3.set_xlim(0, max(c1, c2) * 1.25 + 1e-3)
        ax3.set_title(f"Koszt rozwiązania (tab. 9.7/9.8): Case 2 tańszy o {100*(1-c2/c1):.1f}%"
                      if c1 > 0 else "Koszt rozwiązania")
        self.result.set(f"Algorytm wsteczny wybrał węzły: {final}\n"
                        f"Koszt Case1 = {c1:.3f}, Case2 = {c2:.3f}\n"
                        f"Nos P-V: {pm0:.3f} → {pm:.3f} p.u. (+{100*(pm/pm0-1):.1f}%)")
        self.canvas.draw_idle()


# =============================================================================
# ZAKŁADKA 3 - Przykład 3
# =============================================================================
class Example3Tab(ExampleTab):
    title = "Przykład 3: obszar stabilności"
    explanation = """
## Przykład 3 - czy generator „utrzyma się w siodle"?
Generator połączony linią z bardzo dużą siecią (tzw. szyna nieskończona). Wirnik generatora to wielki wirujący walec. W stanie normalnym moc z turbiny (Pm = 1.0) = moc oddana do sieci Pe = PeM·sin δ, gdzie δ to kąt wirnika.

## Równanie ruchu (jak wahadło!)
dδ/dt = ω,   M·dω/dt = Pm − PeM·sin δ − D·ω
To dokładnie równanie wahadła z tarciem: δ - wychylenie, ω - prędkość. Jeśli wahadło dostanie za mocnego „kopa", przekręci się przez górę - generator traci synchronizm (tzw. poślizg biegunów) i zabezpieczenia muszą go wyłączyć.

## Co robi zwarcie?
W czasie zwarcia (t = 0…0.1 s) sieć nie odbiera mocy (PeM spada np. do 0.3), a turbina dalej pcha - wirnik przyspiesza. Po wyłączeniu zwarcia uszkodzona linia jest odłączona, więc sieć jest słabsza (PeM_post < Pm) - bez pomocy generator by „uciekł".

## 4 tryby sterowania (tab. 9.10)
Tryb 1: nic, PeM=1.35 | Tryb 2: kondensator szeregowy, PeM=2.25 | Tryb 3: bocznikowy, PeM=1.543 | Tryb 4: oba, PeM=2.348.
Kondensator szeregowy zmniejsza reaktancję X, więc PeM = E·U/X rośnie - „mocniejsza sprężyna" wahadła.

## Obszar stabilności (obszar przyciągania)
To zbiór wszystkich stanów (δ, ω), z których system SAM wróci do równowagi. Na wykresie po lewej każdy tryb ma swój obszar (kolorowe kontury). Książka liczy go metodą zbiorów osiągalnych wstecz (równanie Hamiltona-Jacobiego-Isaacsa). My robimy to samo prościej: z każdego punktu siatki puszczamy symulację i sprawdzamy, czy trafi do małej „kulki" wokół punktu równowagi. Obszar trybu 2/4 jest dużo większy niż trybu 1!

## Czas przełączenia - najważniejsza lekcja
Czarna trajektoria: zwarcie → słaba sieć → załączenie kondensatora. Jeżeli załączymy go, gdy stan jest jeszcze WEWNĄTRZ obszaru stabilności nowego trybu, system się uratuje. Za późno - już nic nie pomoże. Program liczy krytyczny czas przełączenia (bisekcją). W książce: 0.3 s ratuje, 0.527 s - za późno.

## Pobaw się
• Przesuwaj „czas załączenia" i obserwuj, kiedy trajektoria wychodzi poza kontur.
• Zmień tryb sterowania na 3 (tylko bocznik) - krytyczny czas się skraca.
• Wydłuż czas zwarcia - zabezpieczenia muszą działać szybko!
"""

    def build_controls(self):
        self.section("Scenariusz zakłócenia")
        self.pf = self.slider("PeM w czasie zwarcia", 0, 1.0, 0.3)
        self.tc = self.slider("Czas trwania zwarcia [s]", 0.02, 0.4, 0.1, 0.01)
        self.pp = self.slider("PeM po zwarciu, przed sterowaniem", 0.3, 1.35, 0.5)
        self.ts = self.slider("Czas załączenia kondensatora [s]", 0.1, 1.2, 0.3, 0.005, "{:.3f}")
        self.section("Tryb sterowania po przełączeniu")
        self.mode = tk.IntVar(value=2)
        for k, (se, sh, pem) in tm.EX3_MODES.items():
            ttk.Radiobutton(self.ctrl, text=f"Tryb {k}: szer. {se}, bocz. {sh}, PeM={pem}",
                            value=k, variable=self.mode, command=self.schedule).pack(anchor="w")
        self.section("Obszary stabilności do narysowania")
        self.show = {k: self.check(f"Tryb {k}", init=k in (1, 2)) for k in tm.EX3_MODES}
        self._regions = {}

    def region(self, k):
        if k not in self._regions:
            self.config(cursor="watch"); self.update_idletasks()
            self._regions[k] = tm.smib_region(tm.EX3_MODES[k][2], n=141)
            self.config(cursor="")
        return self._regions[k]

    def update_plot(self):
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 2, width_ratios=[1.4, 1])
        ax = self.fig.add_subplot(gs[:, 0])
        cols = {1: GRAY, 2: BLUE, 3: ORANGE, 4: GREEN}
        styles = {1: ":", 2: "-.", 3: "--", 4: "-"}
        handles = []
        for k, v in self.show.items():
            if v.get():
                dd, ww, R = self.region(k)
                cs = ax.contour(dd, ww, R, levels=[0.5], colors=cols[k], linestyles=styles[k], linewidths=2)
                d0 = tm.smib_equilibrium(tm.EX3_MODES[k][2])[0]
                ax.plot(d0, 0, "o", color=cols[k])
                handles.append(matplotlib.lines.Line2D([], [], color=cols[k], ls=styles[k],
                                                       label=f"obszar trybu {k}"))
        mode = self.mode.get()
        pem_c = tm.EX3_MODES[mode][2]
        tc, ts = self.tc.get_r(), max(self.ts.get_r(), self.tc.get_r())
        segs = [(self.pf.get_r(), tc), (self.pp.get_r(), ts - tc), (pem_c, 3.0)]
        T, D, W, marks = tm.smib_simulate(segs, dt=2e-3)
        # bez sterowania (dla porównania)
        T0, D0, W0, _ = tm.smib_simulate(segs[:2] + [(self.pp.get_r(), 3.0)], dt=2e-3)
        ax.plot(D0, W0, color=RED, lw=1, alpha=.6)
        ax.plot(D[:marks[0] + 1], W[:marks[0] + 1], "k-.", lw=1.5)
        ax.plot(D[marks[0]:marks[1] + 1], W[marks[0]:marks[1] + 1], "k--", lw=1.5)
        ax.plot(D[marks[1]:], W[marks[1]:], "k-", lw=2)
        ax.plot(D[0], W[0], "k^", ms=8); ax.plot(D[marks[0]], W[marks[0]], "ks")
        ax.plot(D[marks[1]], W[marks[1]], "*", color=RED, ms=14)
        handles += [matplotlib.lines.Line2D([], [], color="k", ls="-.", label="zwarcie"),
                    matplotlib.lines.Line2D([], [], color="k", ls="--", label="po zwarciu, przed ster."),
                    matplotlib.lines.Line2D([], [], color="k", label="po załączeniu"),
                    matplotlib.lines.Line2D([], [], color=RED, alpha=.6, label="bez sterowania"),
                    matplotlib.lines.Line2D([], [], color=RED, marker="*", ls="", ms=10, label="chwila załączenia")]
        ax.set_xlim(-5, 5); ax.set_ylim(-20, 20)
        ax.set_xlabel("δ [rad]"); ax.set_ylabel("ω [rad/s]"); ax.grid(alpha=.3)
        ax.legend(handles=handles, fontsize=7, loc="lower left")
        d0c = tm.smib_equilibrium(pem_c)[0]
        stable = abs(D[-1] - d0c) < 0.1 and abs(W[-1]) < 0.5
        ax.set_title(("STABILNY ✓" if stable else "NIESTABILNY ✗") + f" (tryb {mode}, załączenie t={ts:.3f}s)",
                     color=GREEN if stable else RED)

        ax2 = self.fig.add_subplot(gs[0, 1])
        ax2.plot(T, D, "k", label="ze sterowaniem"); ax2.plot(T0, D0, color=RED, alpha=.6, label="bez")
        for t_ in (tc, ts):
            ax2.axvline(t_, color=GRAY, ls=":")
        ax2.set_ylim(-2, 8); ax2.set_xlim(0, 3); ax2.set_ylabel("δ [rad]"); ax2.grid(alpha=.3)
        ax2.legend(fontsize=8); ax2.set_title("Kąt wirnika w czasie")
        ax3 = self.fig.add_subplot(gs[1, 1])
        dl = np.linspace(0, np.pi, 200)
        for k in tm.EX3_MODES:
            ax3.plot(dl, tm.EX3_MODES[k][2] * np.sin(dl), color=cols[k], ls=styles[k], label=f"tryb {k}")
        ax3.plot(dl, self.pp.get_r() * np.sin(dl), color=RED, alpha=.6, label="po zwarciu")
        ax3.axhline(tm.EX3_PM, color="k", label="Pm")
        ax3.set_xlabel("δ [rad]"); ax3.set_ylabel("Pe [p.u.]"); ax3.grid(alpha=.3)
        ax3.legend(fontsize=7, ncol=2); ax3.set_title("Charakterystyki mocy Pe = PeM·sin δ")

        tcrit = tm.smib_critical_switch_time(self.pf.get_r(), tc, self.pp.get_r(), pem_c)
        crit = ("niestabilny nawet przy natychm. załączeniu" if tcrit is None
                else ("stabilny dla każdego czasu ≤ 2 s" if tcrit >= 2.0 else f"{tcrit:.3f} s"))
        self.result.set(f"Punkt równowagi trybu {mode}: δ0 = {d0c:.4f} rad\n"
                        f"Krytyczny czas załączenia: {crit}\n"
                        f"Wynik symulacji: {'stabilny' if stable else 'utrata synchronizmu'}")
        self.canvas.draw_idle()


# =============================================================================
# ZAKŁADKA 4 - Przykład 4
# =============================================================================
class Example4Tab(ExampleTab):
    title = "Przykład 4: rynek i linia"
    explanation = """
## Przykład 4 - czy wolny rynek zbuduje „dobrą" ilość sieci?
Trzy węzły: tani generator G1 (węzeł 1), droższy G2 (węzeł 2), odbiór 1000 MW (węzeł 3). Linie 1 i 2 są bardzo mocne, ale linia 3 (między 1 a 2) ma tylko k0 = 100 MW. Prywatna firma może ją rozbudować o I MW, płacąc C(I) = c·I².

## Zaskakujące zjawisko fizyczne
Przez linię 3 płynie P12 = α(k)·(Pg1 − Pg2). Gdy rozbudujemy linię (więcej przewodów = mniejsza reaktancja), linia „przyciąga" większą część mocy - α rośnie! Na wykresie po prawej u góry: α(k) = k/(2k + kr).
Czyli: dokładamy 10 MW przepustowości, ale część tego od razu „zjada" większy przepływ. To tzw. efekt zewnętrzny (ang. externality) przepływów kołowych (loop flows).

## Dwa rozwiązania
• Planista społeczny (dobry „dyktator" znający wszystkie koszty) minimalizuje łączny koszt produkcji + inwestycji. Liczy prawdziwą korzyść z 1 MW: μ·(1 − α'·(Pg1−Pg2)).
• Rynek konkurencyjny: firma dostaje za każdy MW przepustowości cenę τ = μ (cenę korka) i buduje, dopóki C'(I) = μ. Nie widzi, że jej inwestycja zmienia rozpływ w całej sieci.

## Wniosek z książki
Rynek NIE jest efektywny, jeśli ∂α/∂k ≠ 0. W naszych danych rynek buduje ZA DUŻO (ok. 51.5 MW zamiast 44.4 MW) i łączny koszt jest wyższy (strata dobrobytu, „deadweight loss").
Lekarstwo: podatek Pigou (od ekonomisty A. C. Pigou) t* = ∂α/∂k·(Pg1*−Pg2*). Firma dostaje (1−t)·τ, co dokładnie koryguje sygnał cenowy.

## Pobaw się
• Odznacz „α zależy od k" - obie krzywe się pokrywają, rynek jest efektywny!
• Zmień koszt inwestycji c - przy dużym c opłaca się mniej budować.
• Zmień koszt G2 - im droższy G2, tym cenniejsza przepustowość.
"""

    def build_controls(self):
        self.section("Parametry (dane przykładowe)")
        self.load = self.slider("Obciążenie w węźle 3 [MW]", 500, 1500, 1000, 10, "{:.0f}")
        self.b1 = self.slider("G1: b1 w C1 = 10P + b1 P²", 0.002, 0.05, 0.01, 0.001, "{:.3f}")
        self.b2 = self.slider("G2: b2 w C2 = 10P + b2 P²", 0.002, 0.08, 0.03, 0.001, "{:.3f}")
        self.k0 = self.slider("Początkowa przepustowość k0 [MW]", 20, 200, 100, 1, "{:.0f}")
        self.cI = self.slider("Koszt inwestycji c w C(I)=cI²", 0.005, 0.3, 0.05, 0.005, "{:.3f}")
        self.dep = self.check("α zależy od k (fizyka loop-flow)", True)
        self.tax_on = self.check("Zastosuj podatek Pigou dla rynku", False)

    def update_plot(self):
        p = tm.Ex4Params(load=self.load.get_r(), b1=self.b1.get_r(), b2=self.b2.get_r(),
                         k0=self.k0.get_r(), cI=self.cI.get_r(), alpha_depends=self.dep.get())
        s = tm.ex4_solve(p)
        I_m = s["I_soc"] if self.tax_on.get() else s["I_mkt"]
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 2)
        Imax = max(3 * s["I_soc"], 50, 1.5 * s["I_mkt"])
        Ig = np.linspace(0, Imax, 300)
        mg = np.array([tm.ex4_marginal(i, p) for i in Ig])
        ax = self.fig.add_subplot(gs[0, 0])
        ax.plot(Ig, mg[:, 0], color=GREEN, lw=2, label="korzyść społeczna μ(1−α'Δ)")
        ax.plot(Ig, mg[:, 1], color=ORANGE, lw=2, ls="--", label="przychód inwestora τ = μ")
        ax.plot(Ig, mg[:, 2], color="k", label="koszt krańcowy C'(I)")
        ax.axvline(s["I_soc"], color=GREEN, ls=":"); ax.axvline(s["I_mkt"], color=ORANGE, ls=":")
        ax.set_xlabel("Inwestycja I [MW]"); ax.set_ylabel("$/MWh"); ax.grid(alpha=.3)
        ax.legend(fontsize=7); ax.set_title("Wartości krańcowe - gdzie przecięcia?")

        ax2 = self.fig.add_subplot(gs[0, 1])
        k = np.linspace(10, 400, 200)
        ax2.plot(k, [tm.ex4_alpha(x, p) for x in k], color=PURPLE, lw=2)
        ax2.axhline(0.5, color=GRAY, ls=":"); ax2.set_xlabel("przepustowość linii 3, k [MW]")
        ax2.set_ylabel("α(k)"); ax2.grid(alpha=.3); ax2.set_title("Udział rozpływu linii 3: α(k)")

        ax3 = self.fig.add_subplot(gs[1, 0])
        tot = np.array([tm.ex4_dispatch(i, p)["total"] for i in Ig])
        ax3.plot(Ig, tot, color=BLUE, lw=2)
        for I_, c, lab in ((s["I_soc"], GREEN, "optimum społeczne"), (I_m, ORANGE, "rynek")):
            ax3.plot(I_, tm.ex4_dispatch(I_, p)["total"], "o", color=c, ms=9, label=f"{lab}: I={I_:.1f}")
        ax3.set_xlabel("I [MW]"); ax3.set_ylabel("koszt całkowity [$/h]"); ax3.grid(alpha=.3)
        ax3.legend(fontsize=8); ax3.set_title("Koszt produkcji + inwestycji")

        ax4 = self.fig.add_subplot(gs[1, 1])
        rs, rm = s["soc"], tm.ex4_dispatch(I_m, p)
        lab = ["Pg1", "Pg2", "przepływ 1→2", "k"]
        x = np.arange(4)
        ax4.bar(x - .2, [rs["P1"], rs["P2"], rs["flow"], rs["k"]], .4, color=GREEN, label="społeczne")
        ax4.bar(x + .2, [rm["P1"], rm["P2"], rm["flow"], rm["k"]], .4, color=ORANGE, label="rynek")
        ax4.set_xticks(x, lab); ax4.set_ylabel("MW"); ax4.legend(fontsize=8); ax4.grid(axis="y", alpha=.3)
        ax4.set_title("Porównanie alokacji")
        loss = rm["total"] - rs["total"]
        self.result.set(f"I* społeczne = {s['I_soc']:.2f} MW, I rynkowe = {s['I_mkt']:.2f} MW\n"
                        f"Podatek Pigou t* = {s['tax']:.3f} ({100*s['tax']:.1f}% ceny τ)\n"
                        f"Strata dobrobytu rynku{' (z podatkiem)' if self.tax_on.get() else ''}: {loss:.2f} $/h\n"
                        f"Ceny węzłowe (optimum): π1={rs['pi1']:.2f}, π2={rs['pi2']:.2f} $/MWh")
        self.canvas.draw_idle()


# =============================================================================
# ZAKŁADKA 5 - Przykład 5
# =============================================================================
class Example5Tab(ExampleTab):
    title = "Przykład 5: kondensator awaryjny"
    explanation = """
## Przykład 5 - kondensator włączany tylko podczas awarii
Węzeł 1 (tani G1) łączy się z odbiorem w węźle 3 dwiema równoległymi liniami 21 i 22 (każda impedancja 2, razem 1). Każda ma limit k1 = 100 MW.

## Rozpływ (prawa Kirchhoffa)
Stan normalny: z 1 MW wstrzykniętego w węźle 1 do linii 21 trafia 1/3, do 22 też 1/3 (reszta okrężnie przez węzeł 2). Wzór: P21 = P22 = Pg1/3 + Pg2/6 ≤ k1.
Awaria (linia 21 wypada): cała droga 1-3 to linia 22: P22c = Pg1/2 + Pg2/4 ≤ k2 + I.
Limit awaryjny k2 = 110 % k1 (operator trzyma małą rezerwę).

## Gdzie jest haczyk?
Zauważ: P22c = 1.5 × P21. Ponieważ k2 = 1.1·k1 < 1.5·k1, to ograniczenie AWARYJNE jest ostrzejsze. Linie w stanie normalnym są wykorzystane tylko w ~73 %! Marnujemy przepustowość, bo musimy być gotowi na awarię, która zdarza się rzadko.

## Rozwiązanie: kondensator szeregowy
Instalujemy kondensator włączany TYLKO w czasie awarii - podnosi limit awaryjny o I. Normalnie jest wyłączony, więc nie zmienia rozpływu (α się nie zmienia!) - to kluczowa różnica względem przykładu 4.
Każdy 1 MW dodatkowej zdolności awaryjnej pozwala przenieść 4 MW produkcji z drogiego G2 do taniego G1 (bo ΔPg1/2 − ΔPg1/4 = 1 → ΔPg1 = 4).

## Optimum
Budujemy tak długo, jak koszt krańcowy C'(I) < oszczędność krańcowa η = 4·(C2' − C1'). Na wykresie to przecięcie dwóch krzywych.

## Rynek działa!
Książka dowodzi: jeśli inwestor dostaje cenę ω za każdy MW zdolności awaryjnej, a generatory ceny węzłowe π1, π2, π3, to równowaga rynkowa = optimum społeczne. Warunek braku arbitrażu: π3 = π1 + (2/3)τ + (1/2)ω. Program to sprawdza.
Morał: kondensatory przełączalne to inwestycja, którą można zostawić wolnemu rynkowi - w przeciwieństwie do nowych linii.

## Pobaw się
• Zwiększ koszt kondensatora c - optimum I spada.
• Zmień rezerwę (margin) - przy 50 % ograniczenie awaryjne przestaje być wiążące i kondensator jest zbędny.
• Obserwuj obszar dopuszczalny na wykresie (Pg1, I).
"""

    def build_controls(self):
        self.section("Parametry (dane przykładowe)")
        self.pd = self.slider("Obciążenie Pd [MW]", 200, 600, 400, 5, "{:.0f}")
        self.a2 = self.slider("G2: a2 w C2 = a2 P + b P²", 10, 60, 20, 0.5, "{:.1f}")
        self.k1 = self.slider("Limit linii k1 [MW]", 50, 200, 100, 1, "{:.0f}")
        self.mg = self.slider("Rezerwa k2/k1 − 1 [%]", 0, 60, 10, 1, "{:.0f}")
        self.cI = self.slider("Koszt kondensatora c w C(I)=cI²", 0.1, 10, 2.0, 0.1, "{:.1f}")

    def update_plot(self):
        p = tm.Ex5Params(Pd=self.pd.get_r(), a2=self.a2.get_r(), k1=self.k1.get_r(),
                         margin=self.mg.get_r() / 100, cI=self.cI.get_r())
        s = tm.ex5_solve(p)
        r = s["res"]
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 2)
        Imax = max(2.5 * s["I"], 1.6 * p.k1 - r["k2"] + 10, 20)
        Ig = np.linspace(0, Imax, 300)
        rr = [tm.ex5_dispatch(i, p) for i in Ig]
        ax = self.fig.add_subplot(gs[0, 0])
        ax.plot(Ig, [x["eta"] for x in rr], color=GREEN, lw=2, label="oszczędność krańcowa η")
        ax.plot(Ig, 2 * p.cI * Ig, "k", label="koszt krańcowy C'(I)")
        ax.axvline(s["I"], color=RED, ls=":", label=f"I* = {s['I']:.2f} MW")
        ax.set_xlabel("I [MW]"); ax.set_ylabel("$/MWh"); ax.legend(fontsize=8); ax.grid(alpha=.3)
        ax.set_title("Optimum: C'(I*) = η")

        ax2 = self.fig.add_subplot(gs[0, 1])
        ax2.plot(Ig, [x["total"] for x in rr], color=BLUE, lw=2, label="całkowity")
        ax2.plot(Ig, [x["gen_cost"] for x in rr], color=ORANGE, ls="--", label="produkcja")
        ax2.plot(s["I"], r["total"], "o", color=RED, ms=9)
        ax2.set_xlabel("I [MW]"); ax2.set_ylabel("$/h"); ax2.legend(fontsize=8); ax2.grid(alpha=.3)
        ax2.set_title("Koszty w funkcji I")

        ax3 = self.fig.add_subplot(gs[1, 0])
        P1 = np.linspace(0, p.Pd, 300)
        In = np.linspace(0, Imax, 300)
        PP, II = np.meshgrid(P1, In)
        fn, fc = tm.ex5_flows(PP, p.Pd - PP)
        feas = (fn <= p.k1) & (fc <= r["k2"] + II)
        ax3.contourf(PP, II, feas, levels=[0.5, 1.5], colors=["#d9ead3"])
        cost = (p.a1 * PP + p.b1 * PP ** 2 + p.a2 * (p.Pd - PP) + p.b2 * (p.Pd - PP) ** 2 + p.cI * II ** 2)
        cs = ax3.contour(PP, II, cost, 12, cmap="viridis", linewidths=.8)
        ax3.clabel(cs, fontsize=6, fmt="%.0f")
        ax3.plot(P1, P1 / 2 + (p.Pd - P1) / 4 - r["k2"], color=RED, label="granica awaryjna")
        ax3.axvline(r["lim_n"], color=PURPLE, ls="--", label="granica normalna")
        ax3.plot(r["P1"], s["I"], "*", color=RED, ms=15, label="optimum")
        ax3.set_xlim(0, p.Pd); ax3.set_ylim(0, Imax)
        ax3.set_xlabel("Pg1 [MW]"); ax3.set_ylabel("I [MW]"); ax3.legend(fontsize=7)
        ax3.set_title("Obszar dopuszczalny (zielony) i poziomice kosztu")

        ax4 = self.fig.add_subplot(gs[1, 1])
        r0 = tm.ex5_dispatch(0, p)
        cats = ["P21 norm.", "P22 awaria", "Pg1", "Pg2"]
        x = np.arange(4)
        ax4.bar(x - .2, [r0["fn"], r0["fc"], r0["P1"], r0["P2"]], .4, color=GRAY, label="bez kondensatora")
        ax4.bar(x + .2, [r["fn"], r["fc"], r["P1"], r["P2"]], .4, color=BLUE, label=f"z I*={s['I']:.1f}")
        ax4.axhline(p.k1, color=PURPLE, ls="--", lw=1)
        ax4.axhline(r["k2"], color=RED, ls="--", lw=1)
        ax4.set_xticks(x, cats, fontsize=8); ax4.set_ylabel("MW"); ax4.legend(fontsize=8)
        ax4.grid(axis="y", alpha=.3)
        ax4.set_title(f"Wykorzystanie linii (st. normalny):\n{100*r0['fn']/p.k1:.0f}% → {100*r['fn']/p.k1:.0f}%")
        omega = r["eta"]
        noarb = r["pi1"] + 2 * r["mu"] / 3 + omega / 2
        self.result.set(f"I* = {s['I']:.2f} MW (kontrola siatką: {s['I_grid']:.1f})\n"
                        f"Pg1 = {r['P1']:.1f}, Pg2 = {r['P2']:.1f} MW\n"
                        f"Ceny: π1={r['pi1']:.2f}, π2={r['pi2']:.2f}, π3={r['pi3']:.2f} $/MWh\n"
                        f"ω = η = {omega:.2f} = C'(I*) = {2*p.cI*s['I']:.2f}  ✓\n"
                        f"Brak arbitrażu: π1+⅔τ+½ω = {noarb:.2f} = π3\n"
                        f"Oszczędność vs I=0: {r0['total']-r['total']:.1f} $/h")
        self.canvas.draw_idle()


# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rozdział 9 - Planowanie rozbudowy sieci przesyłowej z przełączanymi kondensatorami")
        self.geometry("1400x860")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        for cls in (IntroTab, Example1Tab, Example2Tab, Example3Tab, Example4Tab, Example5Tab):
            tab = cls(nb)
            nb.add(tab, text=cls.title)
        self.nb = nb


if __name__ == "__main__":
    App().mainloop()
