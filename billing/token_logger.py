import threading
import time


MODEL_PRICING_USD_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING_USD_PER_1M.get(model, {"input": 0.15, "output": 0.60})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 8)


class TokenUsageLogger:
    def __init__(self):
        self._lock = threading.Lock()
        self._events = []

    def log(self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, request_id: str = ""):
        cost_usd = estimate_cost_usd(model, prompt_tokens, completion_tokens)
        event = {
            "timestamp": int(time.time()),
            "request_id": request_id,
            "model": model,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "estimated_cost_usd": cost_usd,
        }
        with self._lock:
            self._events.append(event)
        return event

    def summary(self):
        with self._lock:
            events = list(self._events)

        if not events:
            return {
                "events_count": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "estimated_total_cost_usd": 0.0,
                "models": {},
            }

        total_prompt = sum(e["prompt_tokens"] for e in events)
        total_completion = sum(e["completion_tokens"] for e in events)
        total_tokens = sum(e["total_tokens"] for e in events)
        total_cost = round(sum(e["estimated_cost_usd"] for e in events), 8)

        models = {}
        for e in events:
            model = e["model"]
            bucket = models.setdefault(model, {"requests": 0, "total_tokens": 0, "estimated_cost_usd": 0.0})
            bucket["requests"] += 1
            bucket["total_tokens"] += e["total_tokens"]
            bucket["estimated_cost_usd"] = round(bucket["estimated_cost_usd"] + e["estimated_cost_usd"], 8)

        return {
            "events_count": len(events),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "estimated_total_cost_usd": total_cost,
            "models": models,
        }


token_logger = TokenUsageLogger()
