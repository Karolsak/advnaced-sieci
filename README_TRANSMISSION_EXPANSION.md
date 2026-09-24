# Rozdział 9 – Planowanie rozbudowy sieci przesyłowej z przełączanymi kondensatorami

Interaktywna aplikacja Tkinter + matplotlib do wszystkich 5 przykładów z rozdziału
*"Models for Transmission Expansion Planning Based on Reconfigurable Capacitor Switching"*
(McCalley i in., Iowa State University). Każda zakładka ma suwaki, wykresy liczone na żywo
oraz wyjaśnienie (📖) napisane dla ucznia liceum.

```bash
pip install -r requirements.txt       # numpy, scipy, matplotlib (+ tkinter z systemu)
python transmission_expansion_gui.py
python test_transmission_models.py    # lub: pytest test_transmission_models.py
```

| Zakładka | Co pokazuje | Zgodność z książką |
|---|---|---|
| Wstęp | Dlaczego sieć się korkuje (rys. 9.1), kryteria N-1/N-2 (tab. 9.1) | poglądowo |
| Przykład 1 | DC-OPF + wybór linii 0/1 w sieci 3-węzłowej, ceny węzłowe | budujemy 2-3B, Pg = 4.0 / 3.4 / 0.4, koszt 11.3 ✓ |
| Przykład 2 | Krzywa P-V, wyszukiwanie wsteczne wg czułości, koszt kompensacji | węzły 5, 7, 8; koszt 0.451 vs 0.41 ✓ |
| Przykład 3 | SMIB: obszary stabilności 4 trybów, trajektorie, krytyczny czas przełączenia | punkty równowagi z tab. 9.10 ✓, t_kryt ≈ 0.49 s (książka 0.527 s) |
| Przykład 4 | Rozbudowa linii zmienia α → rynek przeinwestowuje, podatek Pigou | wniosek jakościowy ✓ |
| Przykład 5 | Kondensator awaryjny: C'(I) = η, ceny węzłowe, brak arbitrażu | wniosek jakościowy ✓ (rynek efektywny) |

## Założenia inżynierskie (gdzie książka nie podaje danych)
- **Przykład 1:** reaktancja linii kandydujących = 0.3 p.u. (jak linie równoległe) – odtwarza rys. 9.6.
- **Przykład 2:** pełny 9-węzłowy CPF zastąpiono liniowym modelem czułości skalibrowanym na tab. 9.6
  (6 kondensatorów → 11.34 %); krzywa P-V to poglądowy układ 2-węzłowy.
- **Przykład 3:** nieznane PeM w czasie zwarcia (0.3) i po zwarciu (0.5) – dobrane tak, by odtworzyć
  rys. 9.13. Obszar stabilności liczony symulacją z siatki punktów zamiast równania HJI (ta sama idea:
  zbiór stanów, z których trajektoria wpada do małej kuli wokół punktu równowagi).
- **Przykłady 4 i 5:** książka ma wyprowadzenia symboliczne, więc przyjęto kwadratowe funkcje kosztów;
  w przykładzie 4 α(k) = k/(2k + k_r) wynika z praw Kirchhoffa dla linii o reaktancji ∝ 1/k.

## Pliki
- `transmission_models.py` – obliczenia (bez GUI, testowalne)
- `transmission_expansion_gui.py` – aplikacja Tkinter
- `test_transmission_models.py` – testy porównujące wyniki z tabelami w książce
