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
