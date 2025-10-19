# FlyBossDS – Narzędzie do zarządzania konfiguracjami JBoss/WildFly Datasource

## Cel projektu
FlyBossDS to narzędzie GUI do zarządzania plikami datasource JBoss/WildFly. Pozwala automatycznie przełączać aktywne `connection-url` (adresy baz danych) oraz bloki `<security>` (użytkownicy bazy), eliminując ręczną edycję XML i minimalizując ryzyko błędów.

## Główne funkcjonalności

### 1. Parsowanie i normalizacja XML
- Obsługa aktywnych i zakomentowanych konfiguracji.
- Zamiana konfiguracji na komentarze blokowe:
  <!--
  <connection-url>...</connection-url>
  -->
- Zachowanie poprawnego formatowania i wcięć.
- Rozdzielanie sklejonych komentarzy (`<!--...--><!--...-->` → osobne linie).

### 2. Tryb ZBIORCZY (synchronizacja wielu plików)
- Jednoczesna zmiana URL i/lub użytkownika we wszystkich plikach.
- Jeśli konfiguracja nie występuje we wszystkich plikach:
  - wyświetlane jest ostrzeżenie,
  - użytkownik może kontynuować,
  - konfiguracja stosowana jest tylko tam, gdzie to możliwe,
  - pozostałe pliki są pomijane.
- Szczegółowy raport z nazwami konkretnych plików (co zmieniono / co pominięto).

### 3. Tryb INDYWIDUALNY (pojedynczy plik)
- Użytkownik wybiera konkretny plik z listy.
- Zmiana tylko w tym pliku.
- Jeśli plik nie zawiera wybranego URL/USER:
  - wyświetlany jest komunikat:
    "Nie da się zmienić konfiguracji w wybranym pliku (zmodyfikuj plik samodzielnie)"
  - plik nie jest modyfikowany (bez dodawania konfiguracji na siłę).

### 4. Kopie zapasowe (backup)
- Możliwość ustawienia katalogu backupów oraz limitu kopii w Ustawieniach.
- Struktura:
  <backup_root>/<nazwa_pliku>_backup/<YYYY-MM-DD_HH-MM-SS>.xml
- Automatyczne usuwanie najstarszych kopii powyżej limitu.
- Przycisk "Otwórz folder kopii" w Ustawieniach.

### 5. Dodatkowe możliwości
- Podgląd zmian (1 plik) przed zapisem.
- Zapamiętywanie ostatnio wybranego URL i użytkownika.
- Motywy jasny / ciemny.
- Ręczne stylowanie Listbox dla trybu ciemnego.

## Logika działania narzędzia

1. Wczytanie listy plików XML (ustawienia).
2. Normalizacja każdego pliku (formatowanie, komentarze blokowe).
3. Analiza dostępnych URL i USER.
4. Użytkownik wybiera docelowy URL i/lub USER.
5. Tryb zbiorczy:
   - sprawdzenie, które pliki zawierają konfigurację,
   - w razie braku – ostrzeżenie i możliwość kontynuacji częściowej,
   - zastosowanie zmian tylko tam, gdzie to możliwe.
6. Tryb indywidualny:
   - zmiana tylko w jednym pliku,
   - jeśli konfiguracja nie istnieje – informacja i brak zmian.
7. Backup przed modyfikacją.
8. Zapis sformatowanego XML.
9. Wyświetlenie raportu (nazwy plików, co zmieniono / co pominięto).

## Aktualny stan projektu
✔ Stabilna logika działania XML (komentarze blokowe, odkomentowanie, formatowanie)  
✔ Pełne wsparcie trybu zbiorczego (z ostrzeżeniami i raportami)  
✔ Pełne wsparcie trybu indywidualnego (bez niechcianych zmian)  
✔ System kopii zapasowych z konfiguracją lokalizacji i limitu  
✔ Interfejs CustomTkinter (theme dark/light, stylowanie Listbox)  
✔ Gotowe do użycia w środowisku developerskim i produkcyjnym

## Wymagania techniczne
Python 3.14+ (działa również na 3.10 – 3.13)

Instalacja zależności:
```
pip install customtkinter
pip install lxml
pip install tkinterdnd2
```

## Uruchomienie
python main.py

## Struktura projektu (najważniejsze pliki)
```
ui/
  main_view.py       – logika trybów, obsługa UI
  settings_view.py   – zarządzanie ścieżkami, backupami, motywem
  app.py             – inicjalizacja aplikacji

core/
  processor.py       – logika edycji XML (URL / USER)
  utils.py           – parsowanie, normalizacja, komentarze blokowe
  backup.py          – tworzenie i czyszczenie kopii zapasowych

config/
  settings_manager.py – zapis/odczyt ustawień (JSON)
```

## Docelowi użytkownicy
- Administratorzy JBoss/WildFly
- DevOps / CI/CD
- Developerzy zarządzający wieloma środowiskami
- Każdy, kto chce bezpiecznie i szybko przełączać konfiguracje datasource

## Dlaczego warto?
- Narzędzie rozumie strukturę XML (nie używa "search+replace")
- Obsługuje zakomentowane konfiguracje
- Nie uszkadza formatowania
- Tworzy backupy automatycznie
- Zapewnia tryb zbiorczy i indywidualny
- Pokazuje szczegółowe raporty zmian
- Pozwala uniknąć błędów i ręcznej edycji

## Status
Projekt jest funkcjonalnym, stabilnym narzędziem produkcyjnym z rozbudowanymi opcjami bezpieczeństwa, konfiguracji i kontroli zmian.
