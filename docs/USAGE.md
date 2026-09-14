# Użycie

`python app.py scan --plan plan.json`
`python app.py preview --plan plan.json`
`python app.py clean --plan plan.json --quarantine D:/Kwarantanna/nowa --apply`
`python app.py restore --quarantine D:/Kwarantanna/nowa --apply`

Można skanować dowolny jawnie wskazany folder, np. Downloads, instalatory, cache,
thumbnails lub logi. Raport obejmuje pliki starsze niż podana liczba dni i ich rozmiary.
CLEAN jest dopuszczone tylko w rzeczywistych katalogach TEMP systemu/użytkownika.
Kosz i foldery osobiste nie są automatycznie opróżniane. Kwarantanna musi być poza
czyszczonym TEMP i nie może wcześniej istnieć. Nie ma trwałego kasowania.
Wersja MVP nie obsługuje katalogów specjalnych kosza ani listy cache każdej aplikacji.

## Rozszerzenia 0.2.0

`python app.py profiles` pokazuje dostępne katalogi. `scan --profile directx-cache`
i `scan --profile thumbnails` przygotowują kandydatów do kwarantanny. Profil miniatur
obejmuje wyłącznie thumbcache_*.db, nie cały katalog Explorer. Pliki zablokowane przez system
mogą nie zostać przeniesione; manifest zachowuje dane odtwarzania.
`scan --profile windows-logs` i `scan --profile downloads` służą do analizy. Raport oznacza
logi, pliki >=100 MiB i potencjalne instalatory; wiek nie dowodzi zbędności pliku.
CLEAN odmówi zmiany tych katalogów. Kosz obsługuje obecnie osobny Windows Toolkit.
