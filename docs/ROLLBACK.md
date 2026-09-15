# Odtwarzanie kwarantanny

Wersja 0.3.3 sprawdza kompletność przed pierwszym odtworzeniem. Gdy pliku
brakuje zarówno w kwarantannie, jak i pod oryginalną ścieżką, operacja odmawia
wykonania. Nie oznacza takiego przypadku jako sukcesu.

Powtórny rollback pomija wyłącznie pliki już odtworzone z poprawnym SHA256.
Wynik podaje `already_restored`. Zmieniona treść powoduje odmowę.
Powtórzone ścieżki i nazwy magazynowe w manifeście są odrzucane.

Plik docelowy jest tworzony wyłącznie jako nowy (`xb`). Plik, który pojawił się
po wstępnej kontroli, nie jest nadpisywany. Kwarantanna jest usuwana dla danego
pliku dopiero po skopiowaniu i sprawdzeniu obu hashy. Po błędzie mogą pozostać
dwie kopie; nie nadpisuj ich bez sprawdzenia zawartości.
