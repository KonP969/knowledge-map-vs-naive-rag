# -*- coding: utf-8 -*-
"""Gold-set pytan do ewaluacji retrievalu (Phase 4 planu semantic-retrieval-over-graph).

Zestawy pytan (QUESTION_SETS na dole pliku):
  default / porta_articles — korpus produkcyjny: 15 artykulow wnetrzarskich
                             porta.com.pl (vault wiki_data/default, od 2026-09-06)
  legacy_mixed             — stary mieszany korpus (2x katalog PORTA PL +
                             3x measureschool EN); tresci juz nie ma w default
  pl_articles              — eksperyment jezyk-vs-struktura (vault wiki_data/eval_lang)

Po kazdej przebudowie korpusu gold-set trzeba przejrzec, czy oczekiwane tematy
da sie jeszcze znalezc w claimach.

Kategorie sa celowo rozdzielone, bo mierza rozne rzeczy:
  factual      — prosty fakt zapisany wprost w jednym claimie
  synthesis    — odpowiedz wymaga zlozenia kilku claimow
  entity_name  — pytanie o nazwe wlasna, ktora zyje w WEZLE grafu, nie w tekscie
                 claimu; znana slabosc indeksu (embedujemy claimy, nie nazwy wezlow)
  out_of_corpus— informacji nie ma w zrodlach; system ma to przyznac, nie zmyslac
"""

GOLD_QUESTIONS = [
    # --- PORTA, kolorystyka (src_001) -------------------------------------
    {
        "id": "pl_kolor_okleiny",
        "question": "Czym różnią się okleiny i wykończenia drzwi PORTA pod względem odporności?",
        "expected_topics": ["odporność oklein", "porównanie wykończeń", "rodzaje oklein"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pl_kolor_system",
        "question": "Jak nowy system PORTA ułatwia wybór drzwi?",
        "expected_topics": ["klarowna struktura", "ułatwiony wybór", "system doboru"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pl_kolor_neutralne",
        "question": "Po co w projektowaniu kolorystyki drzwi tworzy się neutralne bazy?",
        "expected_topics": ["neutralna baza", "aranżacja wnętrza", "dopasowanie do wnętrza"],
        "category": "synthesis",
        "language": "pl",
    },
    # --- PORTA, klamki i cennik (src_002) ---------------------------------
    {
        "id": "pl_klamki_rozstaw",
        "question": "W jakich wariantach rozstawu śrub dostępne są klamki PORTA?",
        "expected_topics": ["rozstaw śrub", "warianty klamek"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pl_klamki_kolory_druk",
        "question": "Dlaczego kolory klamek na materiałach PORTA mogą różnić się od rzeczywistych?",
        "expected_topics": ["technika druku", "różnica kolorów", "prezentacja kolorów"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pl_klamki_cena",
        "question": "Od czego zależy cena klamek w ofercie PORTA?",
        "expected_topics": ["model klamki", "specyfikacja", "zróżnicowanie cen"],
        "category": "synthesis",
        "language": "pl",
    },
    # --- customer analytics (src_003, src_004, src_005) -------------------
    {
        "id": "en_strategy_first_step",
        "question": "What is the first step when building a customer analytics strategy?",
        "expected_topics": ["clear objectives", "business goals", "defining goals first"],
        "category": "factual",
        "language": "en",
    },
    {
        "id": "en_engagement_conversion",
        "question": "How does customer engagement relate to conversion rates?",
        "expected_topics": ["higher engagement", "increased conversion", "sustainable growth"],
        "category": "factual",
        "language": "en",
    },
    {
        "id": "en_journey_mapping",
        "question": "Why should a company map the customer journey?",
        "expected_topics": ["touchpoints", "customer actions", "journey stages"],
        "category": "synthesis",
        "language": "en",
    },
    {
        "id": "en_insights_purpose",
        "question": "What is the purpose of collecting customer insights?",
        "expected_topics": ["align business strategy", "customer behavior", "customer needs"],
        "category": "synthesis",
        "language": "en",
    },
    # --- nazwy wlasne: fakt siedzi w wezle grafu, nie w tekscie claimu ----
    {
        "id": "entity_ganszyniec",
        "question": "Kim jest Maja Ganszyniec i co zaprojektowała dla PORTA?",
        "expected_topics": ["projektantka", "produkty i meble", "zrównoważony rozwój"],
        "category": "entity_name",
        "language": "pl",
    },
    {
        "id": "entity_hydro_protect",
        "question": "Czym jest Hydro Protect w ofercie PORTA?",
        "expected_topics": ["hydro protect", "odporność na wilgoć", "system wykończenia"],
        "category": "entity_name",
        "language": "pl",
    },
    # --- poza korpusem: poprawna odpowiedz to przyznanie sie do niewiedzy -
    {
        "id": "oos_fire_doors",
        "question": "Ile kosztuje montaż drzwi przeciwpożarowych PORTA klasy EI30?",
        "expected_topics": ["brak informacji w źródłach"],
        "category": "out_of_corpus",
        "language": "pl",
    },
    {
        "id": "oos_ga4_setup",
        "question": "How do I configure server-side tagging in Google Tag Manager?",
        "expected_topics": ["not covered by the sources"],
        "category": "out_of_corpus",
        "language": "en",
    },
]


def by_category(category: str):
    return [q for q in GOLD_QUESTIONS if q["category"] == category]


CATEGORIES = sorted({q["category"] for q in GOLD_QUESTIONS})


# --- eksperyment „jezyk czy struktura?" -------------------------------------
# Pytania do vaultu `wiki_data/eval_lang` (3 polskie artykuly narracyjne z
# porta.com.pl). Celowo w tych samych proporcjach co pytania EN w glownym
# gold-secie (2 factual + 2 synthesis), zeby porownanie bylo uczciwe:
#   PL katalog (default) vs PL artykul (tutaj) -> izoluje strukture
#   PL artykul (tutaj)   vs EN artykul (default) -> izoluje jezyk
GOLD_QUESTIONS_PL_ARTICLES = [
    {
        "id": "pla_mocha_skojarzenia",
        "question": "Z czym kojarzy się kolor Mocha Mousse?",
        "expected_topics": ["spokój", "harmonia", "elegancja"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pla_softloft_drzwi",
        "question": "Jakie drzwi najlepiej sprawdzają się w stylu soft loft?",
        "expected_topics": ["drzwi z przeszkleniami", "styl industrialny"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pla_organic_modern",
        "question": "Co charakteryzuje styl Organic Modern we wnętrzach?",
        "expected_topics": ["nowoczesny minimalizm", "naturalność", "stonowane kolory",
                            "drewno i kamień"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "pla_softloft_sypialnia",
        "question": "Jakie drzwi wybrać do sypialni w stylu soft loft i dlaczego?",
        "expected_topics": ["matowe przeszklenie", "drzwi pełne", "prywatność"],
        "category": "synthesis",
        "language": "pl",
    },
]

# --- korpus produkcyjny: 15 artykulow wnetrzarskich porta.com.pl -----------
# Vault `wiki_data/default` przebudowany 2026-09-06 (stary mieszany korpus ->
# `legacy_mixed`). Wszystkie zrodla to narracyjna proza PL — struktura, ktora
# w eksperymencie jezyk-vs-struktura dawala 10/10. Kategorie jak w glownym
# gold-secie: factual / synthesis / entity_name / out_of_corpus.
GOLD_QUESTIONS_PORTA_ARTICLES = [
    # --- factual: fakt zapisany wprost w jednym claimie -------------------
    {
        "id": "pa_cloud_dancer_pantone",
        "question": "Jaki kolor został Kolorem Roku 2026 według Pantone?",
        "expected_topics": ["Cloud Dancer", "złamana biel", "kolor roku 2026"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pa_mocha_skojarzenia",
        "question": "Z czym kojarzy się kolor Mocha Mousse?",
        "expected_topics": ["spokój", "harmonia", "elegancja", "domowe ciepło"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pa_organic_materialy",
        "question": "Jakie materiały dominują we wnętrzach w stylu Organic Modern?",
        "expected_topics": ["drewno", "kamień", "len", "bawełna"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pa_softloft_sypialnia",
        "question": "Jakie drzwi najlepiej sprawdzają się w sypialni w stylu soft loft?",
        "expected_topics": ["matowe przeszklenie", "pełne skrzydła", "prywatność"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pa_wysokosc_skrzydel",
        "question": "W jakich wysokościach dostępne są skrzydła drzwi PORTA?",
        "expected_topics": ["200 cm", "220 cm", "wysokość podwyższona"],
        "category": "factual",
        "language": "pl",
    },
    {
        "id": "pa_biurko_gaming",
        "question": "Jakie cechy powinno mieć biurko do pokoju gamingowego?",
        "expected_topics": ["szeroki blat", "regulacja wysokości", "przepusty na kable"],
        "category": "factual",
        "language": "pl",
    },
    # --- synthesis: odpowiedz wymaga zlozenia kilku claimow --------------
    {
        "id": "pa_szary_salon_akcenty",
        "question": "Dlaczego szary salon wymaga barwnych akcentów?",
        "expected_topics": ["neutralna baza", "monotonia", "barwne akcenty", "przełamanie jednolitości"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "pa_retro_vs_vintage",
        "question": "Czym różni się styl retro od vintage w aranżacji łazienki?",
        "expected_topics": ["oryginalne stare meble", "sprzed 20-25 lat", "współczesne meble stylizowane"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "pa_boho_pochodzenie",
        "question": "Skąd wywodzi się styl boho i czym się charakteryzuje?",
        "expected_topics": ["paryscy artyści", "XIX wiek", "naturalne materiały", "barwy ziemi"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "pa_szare_drzwi_podloga",
        "question": "Jak dobrać odcień podłogi do szarych drzwi wewnętrznych?",
        "expected_topics": ["odcienie szarości", "nowoczesne aranżacje", "harmonia kolorów"],
        "category": "synthesis",
        "language": "pl",
    },
    # --- entity_name: nazwa wlasna zyjaca w WEZLE grafu -----------------
    {
        "id": "pa_entity_cloud_dancer",
        "question": "Czym jest Cloud Dancer?",
        "expected_topics": ["kolor roku 2026", "Pantone", "złamana biel", "spokój"],
        "category": "entity_name",
        "language": "pl",
    },
    {
        "id": "pa_entity_zywioly_powietrze",
        "question": "Drzwi z jakiej kolekcji PORTA pasują do łazienki w stylu retro?",
        "expected_topics": ["4 ŻYWIOŁY", "POWIETRZE", "model P.1", "model P.3"],
        "category": "entity_name",
        "language": "pl",
    },
    {
        "id": "pa_entity_portadecor_fiord",
        "question": "W jakiej okleinie PORTA dostępne są listwy ścienne do nowoczesnej sztukaterii?",
        "expected_topics": ["Portadecor Fiord", "listwy ścienne", "nielakierowane"],
        "category": "entity_name",
        "language": "pl",
    },
    # --- out_of_corpus: informacji nie ma — system ma to przyznac -------
    {
        "id": "pa_oos_ceny_drzwi",
        "question": "Ile kosztują drzwi PORTA z kolekcji PORTA DECOR?",
        "expected_topics": ["brak informacji o cenach", "cennik poza korpusem"],
        "category": "out_of_corpus",
        "language": "pl",
    },
    {
        "id": "pa_oos_gwarancja",
        "question": "Jaki okres gwarancji obejmuje drzwi wewnętrzne PORTA?",
        "expected_topics": ["brak informacji o gwarancji"],
        "category": "out_of_corpus",
        "language": "pl",
    },
]

# Multi-hop set on the same 15 PORTA articles. Every question needs facts from
# several documents at once — the terrain where a compiled knowledge map should
# beat top-k chunk retrieval. Ground truth taken from raw/*/parsed.md (2026-11-11).
GOLD_QUESTIONS_PORTA_MULTIHOP = [
    # --- aggregation: the answer is spread over many articles ---------------
    {
        "id": "mh_hide_wszystkie",
        "question": "W jakich pomieszczeniach i stylach wnętrz PORTA poleca drzwi ukryte PORTA HIDE? Wymień wszystkie.",
        "expected_topics": ["biały pokój", "Mocha Mousse", "zielony kolor we wnętrzu", "łazienka retro",
                            "sztukateria", "Organic Modern", "pokój gamingowy", "szare drzwi",
                            "zielona łazienka"],
        "category": "aggregation",
        "language": "pl",
    },
    {
        "id": "mh_grande_wszystkie",
        "question": "Do jakich aranżacji PORTA rekomenduje drzwi PORTA GRANDE? Wymień wszystkie.",
        "expected_topics": ["Cloud Dancer", "szary salon", "Mocha Mousse", "łazienka retro",
                            "łazienka francuska", "sztukateria", "szare drzwi"],
        "category": "aggregation",
        "language": "pl",
    },
    {
        "id": "mh_loft_wszystkie",
        "question": "W jakich wnętrzach polecane są drzwi z kolekcji PORTA LOFT, łącznie z PORTA LOFT STALOWE?",
        "expected_topics": ["biały pokój", "łazienka retro", "łazienka francuska", "pokój gamingowy",
                            "soft loft", "boho"],
        "category": "aggregation",
        "language": "pl",
    },
    # --- intersection: needs two articles and a join ------------------------
    {
        "id": "mh_organic_i_zielona_lazienka",
        "question": "Które kolekcje drzwi PORTA są polecane zarówno do wnętrz Organic Modern, jak i do zielonej łazienki?",
        "expected_topics": ["PORTA ART DECO", "PORTA HARMONY", "PORTA HIDE"],
        "category": "intersection",
        "language": "pl",
    },
    {
        "id": "mh_bialy_i_zielony",
        "question": "Które drzwi PORTA pojawiają się w poradach zarówno do białego pokoju, jak i do aranżacji z kolorem zielonym?",
        "expected_topics": ["PORTA BALANCE", "PORTA HIDE", "PORTA UNI KOLOR"],
        "category": "intersection",
        "language": "pl",
    },
    {
        "id": "mh_softloft_i_boho",
        "question": "Jaka kolekcja drzwi PORTA jest polecana zarówno do stylu soft loft, jak i do wnętrz boho?",
        "expected_topics": ["PORTA LOFT"],
        "category": "intersection",
        "language": "pl",
    },
    # --- comparison / synthesis across documents ----------------------------
    {
        "id": "mh_kolory_roku_2025_2026",
        "question": "Porównaj kolor roku Pantone 2025 i 2026: jakie to odcienie, jaki nastrój budują i jakie drzwi PORTA do nich pasują?",
        "expected_topics": ["Mocha Mousse 2025", "ciepły, przytulny", "Cloud Dancer 2026", "biel, spokój",
                            "PORTA BALANCE do Cloud Dancer", "PORTA GRANDE / klasyczne drzwi do Mocha Mousse"],
        "category": "comparison",
        "language": "pl",
    },
    {
        "id": "mh_drzwi_lazienkowe_zasady",
        "question": "Zbierz wszystkie wskazówki PORTA dotyczące drzwi do łazienki: wymagania, wentylacja i ościeżnice.",
        "expected_topics": ["otwieranie na zewnątrz", "80 cm szerokości i 200 cm wysokości",
                            "podcięcie wentylacyjne / kratka / skrót rekuperacyjny",
                            "stalowa ościeżnica PORTA SYSTEM ELEGANCE", "HYDRO PROTECT wodoodporna",
                            "montaż po pracach mokrych"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "mh_szary_salon_szare_drzwi",
        "question": "Mam szary salon i szare drzwi. Jak ocieplić to wnętrze i jaką podłogę dobrać?",
        "expected_topics": ["tekstylia z naturalnych włókien w beżach i brązach", "drewniane meble i dodatki",
                            "oświetlenie", "drewniana podłoga", "nie mieszać ciepłych i zimnych barw",
                            "płytki / gres"],
        "category": "synthesis",
        "language": "pl",
    },
    {
        "id": "mh_style_lazienek",
        "question": "Jakie style łazienek opisuje PORTA i czym każdy z nich się wyróżnia?",
        "expected_topics": ["retro vs vintage", "styl francuski vs prowansalski", "zielona łazienka",
                            "planowanie remontu"],
        "category": "synthesis",
        "language": "pl",
    },
]

# Conflict set: run against the vault built by scripts/build_conflict_vault.py
# (the 15 PORTA articles + 3 fixture docs in fixtures/conflict/ that contradict
# them). A good answer surfaces BOTH versions and says the sources disagree;
# silently picking one side is the failure mode.
GOLD_QUESTIONS_PORTA_CONFLICT = [
    {
        "id": "cf_drzwi_lazienka_wymiary",
        "question": "W którą stronę mają się otwierać drzwi do łazienki i jaka jest ich minimalna szerokość?",
        "expected_topics": ["na zewnątrz, min. 80 cm (poradnik remontu PORTA)",
                            "do wewnątrz, min. 70 cm (inny poradnik)",
                            "źródła są ze sobą sprzeczne"],
        "category": "conflict",
        "language": "pl",
    },
    {
        "id": "cf_kolor_roku_2026",
        "question": "Jaki jest kolor roku 2026 według Pantone?",
        "expected_topics": ["Cloud Dancer – ciepła biel (artykuł PORTA)",
                            "Mocha Mousse (inny artykuł; Mocha Mousse to kolor roku 2025)",
                            "źródła są ze sobą sprzeczne"],
        "category": "conflict",
        "language": "pl",
    },
    {
        "id": "cf_hydro_protect",
        "question": "Czy ościeżnica HYDRO PROTECT nadaje się do łazienki i pralni?",
        "expected_topics": ["tak: 100% wodoodporna, kompozyt drzewno-polimerowy (artykuł o zielonej łazience)",
                            "nie: MDF, puchnie (inny poradnik)",
                            "źródła są ze sobą sprzeczne"],
        "category": "conflict",
        "language": "pl",
    },
    {
        "id": "cf_montaz_drzwi",
        "question": "Kiedy podczas remontu łazienki montuje się drzwi?",
        "expected_topics": ["po pracach mokrych (poradnik remontu PORTA)",
                            "przed układaniem płytek (inny poradnik)",
                            "źródła są ze sobą sprzeczne"],
        "category": "conflict",
        "language": "pl",
    },
]

QUESTION_SETS = {
    "default": GOLD_QUESTIONS_PORTA_ARTICLES,
    "porta_conflict": GOLD_QUESTIONS_PORTA_CONFLICT,
    "porta_articles": GOLD_QUESTIONS_PORTA_ARTICLES,
    "porta_multihop": GOLD_QUESTIONS_PORTA_MULTIHOP,
    "legacy_mixed": GOLD_QUESTIONS,
    "pl_articles": GOLD_QUESTIONS_PL_ARTICLES,
}
