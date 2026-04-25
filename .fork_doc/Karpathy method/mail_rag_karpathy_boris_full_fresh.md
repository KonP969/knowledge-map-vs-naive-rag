# Konrad, co mają wspólnego R w RAG, Andrej Karpathy i Boris Cherny?

## TL;DR

W ostatnich tygodniach trzy głośne sygnały poruszyły świat AI: Andrej Karpathy zebrał 18 milionów wyświetleń na poście o bazach wiedzy bez wektorów, Boris Cherny z Anthropic wyrzucił RAG z lokalną bazą wektorową z Claude Code, a PageIndex z hasłem "vectorless retrieval" przekroczył 24 tysiące gwiazdek. Większość wyciągnie z tego złe wnioski. Konrad, wyjaśnię, co naprawdę się dzieje - i dlaczego to mnie nie zaskoczyło (i wcale nie chodzi o ignorancję, po prostu rzeczy stają na swoje miejsca).

Konrad, mamy czwartek, prawda? Dla jednych owocowy. Dla nas - merytoryczny. Merytoryczny Czwartek - raz w tygodniu, jeden temat, moja perspektywa. Tydzień temu zaczęliśmy. Dziś drugi odcinek.

Jeśli tu jesteś, zakładam, że masz już dość czytania o kolejnym "game-changerze", który za miesiąc znika. To jest właściwe miejsce. Nie piszę o tym, co jest modne w tym tygodniu. Piszę o tym, nad czym chodziłem długo - i co przetestowałem zanim powiedziałem. To, co tu czytasz, jest przefiltrowane. Jest jedna zasada, której trzymam się celowo: zostawiam wątki. Nie tłumaczę wszystkiego do końca.

Dlaczego? Bo kompetencja - ta prawdziwa - nie rośnie przez konsumowanie gotowych wniosków. Rośnie, kiedy człowiek sam zaczyna łączyć kropki. Więc jeśli po tym mailu zadasz sobie pytanie "a co to oznacza dla mnie?" - o to właśnie chodzi.

Dziś: trzy sygnały z AI, które przez ostatnie tygodnie zdominowały branżę (jeden z nich jest gorący w ciągu ostatniego tygodnia). I jeden wniosek, który większość wyciągnie błędnie.

## 1. Andrej Karpathy

Andrej Karpathy - były dyrektor AI w Tesli, współzałożyciel OpenAI - opublikował post, który zebrał ponad 18 milionów wyświetleń.

Temat: jak buduje osobiste bazy wiedzy za pomocą LLM-ów.

Bez bazy wektorowej. Bez chunkingu. Inaczej.

Sygnał numer jeden.

## 2. Claude Code: dlaczego agentic search pokonał lokalną bazę wektorową

Z kolei Anthropic wyrzuciło bazę wektorową z Claude Code.

Nie dlatego, że nie działała.

Dlatego, że coś innego działało lepiej.

Boris Cherny, odpowiedzialny za Claude Code w Anthropic, napisał publicznie:

> "Wczesne wersje Claude Code korzystały z RAG + lokalnej bazy wektorowej, ale dość szybko odkryliśmy, że wyszukiwanie agentowe zazwyczaj działa lepiej. Jest też prostsze i nie ma tych samych problemów związanych z bezpieczeństwem, prywatnością, nieaktualnością danych oraz niezawodnością."

Przeczytaj to jeszcze raz. Powoli.

Jeden z najważniejszych zespołów developerskich na świecie miał RAG z bazą wektorową. Przetestował. Wyrzucił. Przeszedł na coś innego.

Sygnał numer dwa.

I trzeci: narzędzie o nazwie PageIndex, z hasłem "vectorless, reasoning-based RAG", zebrało ponad 24 tysiące gwiazdek na GitHubie.

Trzy sygnały. Trzy różne konteksty.

Z tego łatwo wyciągnąć dwa błędne wnioski.

- Pierwszy: pojawiła się zupełnie nowa klasa idei.
- Drugi: RAG właśnie umarł.

Oba są błędne.

To, co naprawdę obserwujemy, to nie śmierć RAG. To moment, w którym rynek zaczyna dojrzewać do prostszej, ale znacznie bardziej fundamentalnej prawdy:

> R w RAG nigdy nie oznaczało: wrzuć cokolwiek do bazy wektorowej i licz, że model sobie poradzi.

R oznacza: dobrze zorganizuj dane, zbuduj sensowną warstwę wiedzy, dopiero potem dobierz retrieval do natury problemu. To jest zupełnie inna rzecz.

I właśnie dlatego, kiedy dużo osób biegło w stronę najprostszego hasła pod tytułem chunking + vector DB, ja dużo mocniej kładłem nacisk na coś innego:

- na reprezentację danych,
- na mapę wiedzy,
- na audytowalność,
- na jakość kontekstu,
- i na to, że retrieval to nie magia narzędzia, tylko bardzo konkretna praca z danymi.

Dzisiaj zaczyna być po prostu głośniej o tym samym kierunku. Nie dlatego, że nagle stał się prawdziwy. Tylko dlatego, że coraz więcej mocnych przykładów rynkowych zaczyna go potwierdzać. Pozwól, że wyjaśnię każdy z tych sygnałów. Krok po kroku.

1. Claude Code: dlaczego agentic search pokonał lokalną bazę wektorową

Zacznę od Borisa Cherny'ego, bo to sygnał, który pojawił się najwcześniej - w lutym 2026.

Co to znaczy w praktyce, że Claude Code wyrzucił RAG + local vector db na rzecz agentic search?

Stary system: wrzucasz kod do bazy wektorowej, przy każdym pytaniu szukasz "semantycznie podobnych fragmentów", podajesz je modelowi.

Nowy system: model sam aktywnie przeszukuje repozytorium.

- Decyduje, czego szukać
- Czyta pliki bezpośrednio, na żywo
- Jeśli wynik nie wystarczy - zmienia zapytanie i szuka dalej
- Zarządza kontekstem przez warstwy instrukcyjne (CLAUDE.md, commands, skills)
- Weryfikuje rezultat, angażuje subagentów

To jest iteracyjny, sterowany proces dochodzenia do właściwego kontekstu. Nie jednorazowe "weź top-5 najlepszych chunków i miej nadzieję."

Dlaczego akurat dla kodu baza wektorowa sprawdza się gorzej?

Bo kod ma specyficzną naturę:

- Liczy się dokładność - konkretna nazwa funkcji, import, ścieżka pliku. Nie "semantycznie podobny fragment"
- Kod zmienia się szybko - indeks na embeddingach starzeje się z każdym commitem
- Indeksowanie kodu rodzi realne pytania o bezpieczeństwo i prywatność

Boris nie mówi, że retrieval jest niepotrzebny. Mówi, że chunking + vector DB - ten popularny schemat, którego przez ostatnie lata uczono tysiące ludzi - nie jest dobrym punktem startowym dla tego typu danych.

Mówiłem o tym od dawna. W DataWorkshop nie uczyliśmy tego podejścia już w 2023 - sprawdziliśmy, nie działało, nie było zgodne z tym, w co wierzymy. Uczymy tego, co przetestowaliśmy.

Temat stał się niemodny. Część rynku zmieniła agendę cicho, bez erraty. Albo wręcz przeciwnie - z dumą: "mamy prawie 100% nową agendę." Firmy i ludzie zostali z tym na produkcji. Echo chunking + vector DB będzie długo dawać o sobie znać. Niestety teraz potrzeba znacznie więcej wysiłku, żeby to wyprostować, niż żeby zbudować to poprawnie od początku.

Mówię to ze spokojem, nie z satysfakcją. Czas weryfikuje kierunek. I właśnie weryfikuje.

2. Karpathy: wiedza powinna się kumulować, nie być odkrywana od zera

Teraz Karpathy i te 18+ milionów wyświetleń.

W dużym skrócie jego pomysł wygląda tak

- wrzucasz surowe źródła do raw/,
- model czyta je i kompiluje do wiki w Markdownzie,
- powstają strony pojęć, encji, summary, linki i indeksy,
- pytasz już nie surowe dokumenty, tylko skompilowaną warstwę wiedzy,
- wartościowe odpowiedzi wracają do wiki i dalej ją wzbogacają.

To, co jest tu naprawdę ważne, nie sprowadza się ani do Obsidiana, ani do Markdowna. Najważniejsza zmiana polega na przesunięciu ciężaru z czasu pytania do czasu porządkowania wiedzy.

Zamiast: "query -> szukaj podobnych chunków -> generuj"

Pojawia się coś bliższego temu:

"źródło -> kompilacja wiedzy -> struktura -> pytanie do lepszej warstwy"

To ogromny ma sens, bo dobra odpowiedź bardzo często nie zależy tylko od tego, czy model "coś znajdzie". Dobra odpowiedź zależy od tego, czy wcześniej powstała sensowna warstwa pośrednia między surowym źródłem a finalnym wnioskiem. I właśnie to jest dla mnie najcenniejsze u Karpathy’ego: nie to, że pokazał nowy gadżet, ale to, że bardzo dobrze pokazał wartość skompilowanej, narastającej wiedzy.

Jednocześnie nadal trzeba zachować zdrowy rozsądek:

- Taki wariant działa bardzo dobrze przy małej i średniej skali.
- Ale jeśli korpus rośnie, sama płaska wiki zaczyna się męczyć.
- Wtedy trzeba dołożyć lepszą nawigację, lepszy search, hierarchię, provenance i bardziej świadome skalowanie.

Czyli nawet tutaj nie chodzi o religię "wiki zamiast wszystkiego". Chodzi o dobrą warstwę syntezy, która potem może być rozszerzana.

Swoją drogą - to, co Karpathy nazywa "bazą wiedzy", my w DataWorkshop od dawna nazywamy "mapą wiedzy". Nazwy mnie zwykle mało interesują. Ale w tym przypadku warto na to zwrócić uwagę. Mapa wiedzy jest dokładniejsza. Masz raw/ - to jest prawdziwa baza wiedzy: surowe, niezmienne źródła. I masz warstwę, którą budujesz na górze: organizujesz, opisujesz, strukturyzujesz. Mapujesz, żeby łatwo było trafić.

U Karpathy'ego tą mapą jest wiki w Obsidianie. To jedna implementacja. Może być wygodna - ale nie jedyna. Mapą może być cokolwiek, co rozwiązuje Twój problem i da się utrzymać. Wiki. Drzewo dokumentu. Metadane. Hybryda.

Mapa ma służyć problemowi - nie odwrotnie.

3. PageIndex: nie pytaj o podobieństwo, pytaj o strukturę

Trzeci sygnał.

24+ tysiące gwiazdek. Hasło: vectorless, reasoning-based RAG. To narzędzie jest o tyle interesujące, że pokazuje podobny kierunek, ale na innym typie danych. Tu nie chodzi o budowę pełnej wiki między dokumentami, tylko o to, jak rozsądnie poruszać się po długim dokumencie.

Schemat jest prosty:

- bierzesz dokument, najczęściej długi PDF,
- system buduje z niego hierarchiczne drzewo,
- to drzewo przypomina spis treści i mapę sekcji,
- model wybiera nie "najbardziej podobne chunki", tylko najbardziej prawdopodobne węzły struktury,
- dopiero potem schodzi do odpowiednich fragmentów i zwraca odpowiedź z odniesieniem do stron i sekcji.

To jest bardzo ważne, bo pokazuje coś, o czym mówiłem wcześniej w bardziej ogólnej formie: nie każda reprezentacja danych jest równie dobra.

Jeśli pracujesz na:

- raportach finansowych,
- filingach,
- dokumentach regulacyjnych,
- długich manualach,

to problemem nie jest tylko "jak znaleźć podobny kawałek tekstu". Problemem jest też:

- zachowanie struktury,
- relacji sekcja -> podsekcja,
- naturalnej granularności źródła,
- i możliwości prześledzenia, skąd odpowiedź w ogóle pochodzi.

Zamiast kroić dokument na kawałki i wrzucać do bazy wektorowej, PageIndex buduje hierarchiczny indeks - coś pomiędzy inteligentnym spisem treści a mapą sekcji dokumentu. Kiedy zadajesz pytanie, LLM nie szuka "najbardziej podobnego wektora." Nawiguje po drzewie dokumentu jak ekspert:

- Patrzy na strukturę
- Rozumuje, które sekcje mogą zawierać odpowiedź
- Schodzi głębiej do odpowiednich fragmentów
- Zwraca wynik z odniesieniem do konkretnych stron i sekcji

Pomyśl, jak ekspert czyta 200-stronicowy raport finansowy.

Nie kroi go na 800-tokenowe kawałki. Patrzy na spis treści, idzie do właściwej sekcji, sprawdza szczegóły. PageIndex symuluje dokładnie ten sposób poruszania się po dokumencie.

PageIndex robi tutaj bardzo rozsądny ruch: najpierw buduje warstwę struktury, dopiero potem odpala retrieval. I to jest dokładnie ten rodzaj zdrowego rozsądku, który warto umieć zauważyć. Nie dlatego, że to jest "anty-vector". Tylko dlatego, że pokazuje znacznie ważniejszą rzecz: najpierw reprezentacja wiedzy, potem search.

To podejście też wpisuje się w to co nazywamy "mapę wiedzy". Drzewo dokumentu to reprezentacja, po której można nawigować jak ekspert - precyzyjnie, do właściwej informacji. Nie tylko model. Człowiek też.

Co ciekawe, PageIndex też nie kończy na czystej ideologii. Oficjalne materiały pokazują też hybrydowe rozszerzenia. I bardzo dobrze. Bo właśnie tak powinno się myśleć:

- bez religii wobec vector DB,
- bez religii wobec "zero vectors",
- bez przywiązania do jednej sztuczki.

Jeśli problem tego wymaga, dokładasz:

- metadata search,
- Query-to-SQL,
- search po opisach,
- scoring,
- elementy hybrydy.

To nie osłabia idei. To pokazuje dojrzałość. I to mnie naprawdę cieszy. Świat Software 3.0 dojrzewa. Dzieje się dokładnie to, co zawsze dzieje się z technologią: doświadczenie się kumuluje, standardy zaczynają się kształtować. To dopiero początek. Ale czas szamanów w AI powoli mija...

Konrad, jak myślisz co łączy te trzy podejścia?

Trzy niezależne zespoły. Trzy różne domeny: kod, długie dokumenty, osobisty research.

Wszystkie trzy odchodzą od naiwnego "pokrój na kawałki, wrzuć do bazy wektorowej, wyszukaj podobne, miej nadzieję."

I wszystkie trzy dochodzą do jednego wniosku:

Zanim zapytasz model, musisz mieć sensowną warstwę pośrednią między surowym źródłem a odpowiedzią.

W jednym przypadku tą warstwą jest wiki. W drugim - drzewo dokumentu. W trzecim - instrukcyjna warstwa pracy z repozytorium.

Różne formy. Ten sam rdzeń.

I jeden warunek, który spina je wszystkie:

Ta warstwa pośrednia nie może zastąpić źródeł prawdy. Raw/, oryginalny dokument, żywe repozytorium - muszą pozostać punktem odniesienia. Wiki i tree index pomagają nawigować i syntetyzować. Jeśli odetniemy je od proweniencji i źródeł, zamienią się w ładny, ale coraz mniej wiarygodny slop.

Zatrzymuję się tutaj na chwilę.

Zanim przejdę do tego, co to oznacza praktycznie - jedno pytanie. Wystarczy jedno kliknięcie:

Na czym chcesz się skupić w najbliższych tygodniach?

- Lepiej wykorzystywać LLM-y w codziennej pracy
- Budować agentów AI i automatyzacje procesów
- Ułożyć sobie pełną ścieżkę rozwoju w AI - dopiero zaczynam z AI/LLM

Sekundę. Pomoże mi dostosować materiały, które będę wysyłał.

## Pytania, które widzę w internecie

### Czy RAG umarł?

Nie. Retrieval + generation jako koncept nigdzie się nie wybiera. Zmienia się forma retrievalu. Domyślny wzorzec (chunking + vector DB) jest coraz częściej kwestionowany przez ludzi, którzy budują najbardziej wymagające systemy. Ale idea, że model potrzebuje zewnętrznej wiedzy - ta zostaje.

### Czy duże okna kontekstowe nie rozwiążą tego za nas?

Duży kontekst podnosi sufit. Ale nie rozwiązuje problemu wyboru tego, co istotne, nawigacji po wiedzy, utrzymania wiedzy w czasie, ani audytu - skąd model wziął informację. Model z milionem tokenów śmieciowego kontekstu da gorsze odpowiedzi niż model z 10 tysiącami tokenów precyzyjnie dobranego kontekstu.

### Czy to się skaluje?

Na małej i średniej skali - tak, świetnie. Na dużej - trzeba rozszerzać. Karpathy przyznaje to wprost. PageIndex dodaje hybrydowe metody. Claude Code ma subagentów i worktrees. Skalowanie wymaga powrotu do fundamentów: reprezentacja, search, hierarchia. Ale te fundamenty pozwalają skalować cokolwiek.

### Czy wiki nie zamieni się w slop?

Tak, to może być realne ryzyko. Dlatego Karpathy rozdziela surowe źródła od wiki - źródła są niezmienne. Dlatego proponuje linting. Dlatego wiki zawiera odniesienia do źródeł. Warstwa skompilowana nie zastępuje źródeł - pomaga po nich nawigować. Jeśli odetniemy ją od provenance, zamieni się w ładny, ale coraz mniej wiarygodny szum.

## Co łączy te trzy przykłady

Karpathy, PageIndex i Claude Code nie opowiadają trzech różnych religii. One pokazują trzy szczególne przypadki tej samej większej zasady. Ta zasada brzmi tak:

- nie zaczynasz od narzędzia,
- zaczynasz od natury danych,
- tworzysz odpowiednią reprezentację pośrednią,
- dopiero potem dobierasz retrieval,
- pilnujesz audytowalności i jakości kontekstu,
- przy większej skali dokładnie tam, gdzie trzeba, dokładasz lepszy search,
- albo hybrydę.

## Dlaczego mówię o tym spokojnie

Te trzy sygnały nie są dla mnie zaskoczeniem. Naprawdę!

Gdy tworzyłem Praktycznego LLM - na długo przed tymi postami (ponad 2 lat temu) - uczyłem i nadal uczę dokładnie tego rdzenia. Nie mówię tego, aby tylko się pochwalić. Mówię to po to, żebyś zobaczył coś ważniejszego. Kiedy większość rynku skupiała się na haśle "chunking plus vector DB i zadziała", w DataWorkshop Lab pracowaliśmy nad czymś trudniejszym:

- Dlaczego naiwny chunking niszczy strukturę danych - na konkretnym przykładzie: tabela finansowa rozerwana na kawałki traci sens, nagłówki znikają, wiersze się rwą, model dostaje śmieciowy kontekst
- Jak używać LLM do opisu i klasyfikacji danych na etapie wejścia, zanim cokolwiek trafi do retrievalu
- Co to jest mapa wiedzy i dlaczego jest ważniejsza od wyboru narzędzia
- Jak budować retrieval wieloetapowy - pytanie rozbite na pytania pomocnicze, kontekst budowany z referencjami do źródeł
- Dlaczego każda odpowiedź musi mieć audytowalne źródło - document_id, sekcja, confidence

To nie było najmodniejsze podejście w 2024 roku. Czułem się wtedy samotny - może zabrzmi to trochę dziwnie, ale uznałem, że zdrowy rozsądek jest ważniejszy niż podążanie za tłumem ludzi ulegających chwilowemu hype'owi. Mało kto rozumiało wówczas, że to właściwa droga w podejściu do RAG. Ale właśnie takie rzeczy najlepiej przechodzą próbę czasu. Karpathy dopracował i świetnie pokazał wiki w Obsidianie (kwiecień 2026). Boris Cherny podjął odważną architektoniczną decyzję w Claude Code (luty 2026). PageIndex dopracowało tree-based retrieval (~2026).

To są świetne, konkretne implementacje. Fundamenty, z których wynikają, są szersze. I właśnie dlatego, kiedy patrzę na te trzy sygnały razem, nie widzę rewolucji. Widzę dojrzewanie rynku!

Narzędzia będą pojawiać się z gigantyczną prędkością. Nie masz już komfortu "nie ma czego śledzić." Masz coraz większy deficyt uwagi - i coraz ważniejsze staje się pytanie nie co śledzić, ale na czym się skupić. Najcenniejszą umiejętnością nie jest znajomość najnowszego frameworka. Jest nią rozumienie zasad, które pozwalają Ci samodzielnie ocenić - co jest wartościowe, a co za pół roku zniknie.

Dobra wiadomość dla Ciebie: nie musisz czekać na tweet z 18 milionami wyświetleń, żeby wiedzieć, co działa.

Chcesz zgłębić temat? Prosta rada: musisz rozumieć fundamenty.

Jak? To już tłumaczę jak to zrobić.

## Szkolenie

We wtorek 14 kwietnia (11:00-13:00) prowadzę szkolenie na żywo dla zamkniętej grupy. Online, Google Meet, bloki Q&A - nie webinar.

Temat: literka R w RAG - jak reprezentować dane, budować mapę wiedzy i retrieval, który naprawdę działa.

Online, Google Meet, bloki Q&A - nie webinar. Dwie godziny, skoncentrowany format.

### Przez dwie godziny pokryjemy:

- Dlaczego każdy X-RAG - bez względu na nazwę - sprowadza się do jednej fazy. Co to oznacza, kiedy projektujesz system, i jak uniknąć najczęstszych pułapek
- Jak Karpathy, PageIndex i decyzja Claude Code przekładają się na praktykę - nie jako kolejny tutorial, tylko jako mapa decyzji
- Konkretna mapa przez chaos RAG-owych nazw i podejść - co czytać, co testować, a co pominąć

### Co dostajesz:

- Nagranie całości - oglądasz kiedy chcesz, tyle razy ile chcesz
- Skondensowane notatki z kluczowymi myślami
- Zestaw linków jako system nawigacji
- Sesja Q&A - pytania wysyłasz wcześniej mailem albo zadajesz podczas szkolenia
- Miesiąc dostępu do DWthon - w cenie szkolenia. W kwietniu robimy DWthon w tym samym temacie. Dostajesz dostęp przez cały miesiąc - miejsce, gdzie to, o czym będziemy mówić, możesz przetestować w praktyce, zadawać pytania i zobaczyć jak inni to robią.

## R w RAG - jak reprezentować dane, budować mapę wiedzy i retrieval, który naprawdę działa

**Szkolenie / 14 kwietnia / Google Meet / 2 godziny / 490 PLN**

Zamknięta grupa. Zależy mi, żeby w sali były osoby z konkretnym projektem, konkretnym problemem albo serio budujące kompetencje.

Ale to jeszcze nie wszystko... jak dołączysz teraz, to dostaniesz jeszcze jeden prezent jako kontynuacja.

## Bonus

🎁 **Bonus: miesiąc dostępu do DWthon**

W kwietniu robimy DWthon w tym temacie - trzy dni głębszego zanurzenia w RAG. Szczegóły wkrótce. DWthon to nasze cykliczne wydarzenie (w kwietniu właśnie będzie o RAG) - ale wyjątkowo dostaniesz wtedy do niego dostęp przez cały miesiąc (nie 3 dni) w cenie tego szkolenia. Dzięki temu na spokojnie sobie podziałasz w swoim tempie. Miejsce, gdzie to, o czym będziemy mówić, możesz przetestować w praktyce. Nie zostawić w głowie - sprawdzić w projekcie, zadać pytania, zobaczyć jak inni to robią.

Dobrego czwartku.

P.S. Jeśli masz pytania do dzisiejszego tematu - odpowiedz na tego maila. Czytam każdą wiadomość.
