# TEN_GREYMANE — odczyt katalogów z silnika 98285

To osobna mapa diagnostyczna, nie nowa wersja odzyskanego meczu. Jej zadaniem jest zapisanie numerów i nazw typów jednostek oraz umiejętności, których nie udało się wiarygodnie wyliczyć z plików XML. Nie wyłącza wykrywania desynchronizacji i nie modyfikuje replayów.

## Uruchomienie pakietu

Rozpakuj cały pakiet `hots-catalog-probe-98285.zip` do jednego folderu poza instalacją gry, najlepiej w `OneDrive/HotS Replay Upgrade - TEN_GREYMANE`. Nie uruchamiaj skryptu bezpośrednio z podglądu ZIP. Pliki `START_CATALOG_PROBE.cmd`, `run_catalog_probe.ps1` i `TEN_GREYMANE_CATALOG_PROBE_98285.StormMap` muszą pozostać razem.

Zamknij Heroes of the Storm i uruchom `START_CATALOG_PROBE.cmd`. Skrypt sprawdzi sumę mapy, odmówi działania przy uruchomionej grze i wywoła zainstalowany `HeroesSwitcher_x64.exe` z bezwzględną ścieżką do osobnej mapy. Nie nadpisuje Try Mode, nie kopiuje plików do instalacji, nie kończy procesów i nie wymaga uruchamiania jako administrator.

Jeżeli mapa się uruchomi i pojawi się `HOTS CATALOG PROBE: export requested`, opuść mapę, wróć do okna skryptu i naciśnij Enter. Skrypt zbierze wyłącznie pliki `HRC98285_20260929_P1_*.StormBank` i ograniczony zestaw informacji o wersji do nowego `catalog-output-*.zip`. Gdy pakiet uruchomiono w OneDrive, wynik pozostanie tam do synchronizacji. Sam komunikat nie jest dowodem kompletnego zapisu — kompletność jest sprawdzana osobno przy odczycie banków.

Jeżeli pojawi się błąd skryptu Galaxy, ładowania mapy albo brak eksportu, zachowaj dokładny komunikat. Nie zmieniaj instalacji i nie kopiuj mapy w miejsce mapy treningowej. Bez udanego odczytu nie powstaje wiarygodna tabela migracji.

## Niestandardowe ścieżki

Dla innego katalogu instalacji uruchom PowerShell w rozpakowanym folderze:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_catalog_probe.ps1 -GameDirectory "D:\Games\Heroes of the Storm"
```

Do samego zebrania już istniejącego eksportu użyj `-Mode Collect`. Ten tryb nie uruchamia gry i nie potwierdza aktualności banków względem nowego uruchomienia.

## Zakres i ograniczenia

Mapa bazowa odpowiada odwołaniu z autentycznego Dragon Shire z 29 września 2026, SHA-256 `f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f`. Zmieniono tylko skrypt mapy i listę wczytywanych banków; pozostawiono pierwotną inicjalizację i zależności. Normalne zachowanie inicjalizacji gry, takie jak zapis logów czy własnych ustawień gry, nie jest przez to wyłączone. Kod diagnostyczny zapisuje wyłącznie osobne banki z prefiksem HRC98285.

Eksport zachowuje indeksy zwrócone przez `CatalogEntryGet`, również gdy wskazana pozycja nie jest prawidłowym zdefiniowanym wpisem. Nie filtruje i nie numeruje katalogu ponownie. Odczyt odrzuca brakujące fragmenty, pomieszane sesje, duplikaty, niezgodne zakresy i niezakończony eksport. Porównuje 48 niezależnie zaobserwowanych numerów typów z replayów referencyjnych; nie dopisuje brakujących wartości na podstawie zgadywania.

Uruchomienie samodzielnej mapy może mieć inny kontekst niż normalny replay; dokumentacja źródłowego projektu TryMode2.0 ostrzega także o możliwym braku talentów przy takim uruchomieniu. Zgodność wszystkich 48 punktów kontrolnych będzie przydatnym sprawdzeniem, lecz sama nie dowodzi zgodności wszystkich umiejętności lub całej symulacji.

Generator mapy, parser banków i składnia PowerShell są sprawdzane automatycznie. Nie uruchomiono tutaj klienta HotS, nie potwierdzono kompilacji Galaxy ani wykonania tego skryptu na Windows. `expected_build=98285` jest opisem docelowej wersji, nie numerem odczytanym przez mapę z procesu gry. Rzeczywistą wersję trzeba porównać z nowym logiem klienta.
