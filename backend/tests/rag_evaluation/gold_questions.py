# -*- coding: utf-8 -*-
"""Gold-set pytan do ewaluacji retrievalu (Phase 4 planu semantic-retrieval-over-graph).

Pytania sa napisane pod AKTUALNA zawartosc vaultu `wiki_data/default` (5 zrodel:
2x PORTA po polsku, 3x measureschool o customer analytics po angielsku). Po kazdej
przebudowie korpusu gold-set trzeba przejrzec — `verify_gold_set.py` sprawdza, czy
oczekiwane tematy da sie jeszcze znalezc w claimach.

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
