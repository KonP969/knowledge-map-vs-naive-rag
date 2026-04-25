from typing import Optional

PROMPT_PRICE_PER_M = 0.150
COMPLETION_PRICE_PER_M = 0.600


def calc_openai_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens * PROMPT_PRICE_PER_M
        + completion_tokens * COMPLETION_PRICE_PER_M
    ) / 1_000_000


class CostGuard:
    def __init__(self, threshold_usd: float = 0.10, max_usd: float = 1.00):
        self.threshold_usd = threshold_usd
        self.max_usd = max_usd
        self.rag_cost: float = 0.0
        self.eval_cost: float = 0.0
        self._last_threshold_crossed: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.rag_cost + self.eval_cost

    def add_rag_cost(self, cost: float) -> Optional[str]:
        self.rag_cost += cost
        return self._check_threshold()

    def add_eval_cost(self, cost: float) -> Optional[str]:
        self.eval_cost += cost
        return self._check_threshold()

    def _check_threshold(self) -> Optional[str]:
        total = self.total_cost
        current_multiple = int(total / self.threshold_usd)
        last_multiple = int(self._last_threshold_crossed / self.threshold_usd)
        if current_multiple > last_multiple and total >= self.threshold_usd:
            self._last_threshold_crossed = total
            return (
                f"UWAGA: Łączny koszt osiągnął ${total:.3f} "
                f"(RAG: ${self.rag_cost:.3f} | Eval: ${self.eval_cost:.3f})"
            )
        return None

    def should_stop(self) -> bool:
        return self.total_cost >= self.max_usd

    def prompt_user_to_continue(self) -> bool:
        try:
            answer = input(
                f"\nKoszt osiągnął ${self.total_cost:.3f}. Kontynuować? [T/n]: "
            ).strip().lower()
            return answer not in ("n", "nie", "no")
        except (EOFError, KeyboardInterrupt):
            return False

    def summary(self) -> str:
        return (
            f"RAG: ${self.rag_cost:.4f} | "
            f"Eval: ${self.eval_cost:.4f} | "
            f"Łącznie: ${self.total_cost:.4f}"
        )
