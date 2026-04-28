"""Grounded answer generation."""

from __future__ import annotations

from mediaexpert_laptops.rag.models import AnswerResponse, SearchRequest, SearchResult
from mediaexpert_laptops.rag.search import SearchService


class AnswerService:
    """Generate short Polish recommendations from retrieved laptops."""

    def __init__(self, *, search_service: SearchService, api_key: str, model: str) -> None:
        self._search_service = search_service
        self._api_key = api_key
        self._model = model

    def answer(self, request: SearchRequest) -> AnswerResponse:
        """Return grounded answer plus source results."""

        search_response = self._search_service.search(request)
        answer_context = self._build_answer_context(search_response.results)
        trace = search_response.trace.model_copy(
            update={"context_sent_to_answer_llm": answer_context or None}
        )
        if trace.decision.action == "ask_clarification":
            return AnswerResponse(
                query=request.query,
                parsed_query=search_response.parsed_query,
                answer=trace.decision.clarifying_question
                or "Doprecyzuj proszę, jakiego laptopa szukasz.",
                results=[],
                trace=trace,
            )

        if not search_response.results:
            return AnswerResponse(
                query=request.query,
                parsed_query=search_response.parsed_query,
                answer="Nie znalazłem w danych laptopów spełniających jawne warunki z zapytania.",
                results=[],
                trace=trace,
            )

        if not self._api_key:
            answer = self._fallback_answer(request.query, search_response.results)
        else:
            answer = self._llm_answer(request.query, answer_context, search_response.results)

        return AnswerResponse(
            query=request.query,
            parsed_query=search_response.parsed_query,
            answer=answer,
            results=search_response.results,
            trace=trace,
        )

    def _llm_answer(
        self,
        query: str,
        answer_context: str,
        results: list[SearchResult],
    ) -> str:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key)
            response = client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Odpowiadasz po polsku jako asystent zakupowy. Korzystaj wyłącznie "
                            "z przekazanych laptopów. Nie wymyślaj modeli ani parametrów."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Zapytanie: {query}\n\nLaptopy:\n{answer_context}",
                    },
                ],
            )
            return response.output_text
        except Exception:
            return self._fallback_answer(query, results)

    def _fallback_answer(self, query: str, results: list[SearchResult]) -> str:
        best = results[0].laptop
        alternatives = ", ".join(result.laptop.name for result in results[1:3])
        answer = (
            f"Najlepiej pasuje {best.name} za {best.price_pln:.2f} zł. "
            f"{best.semantic_description}"
        )
        if alternatives:
            answer += f" Warto porównać go też z: {alternatives}."
        return answer

    def _build_answer_context(self, results: list[SearchResult]) -> str:
        return "\n\n".join(
            (
                f"Nazwa: {result.laptop.name}\n"
                f"Cena: {result.laptop.price_pln:.2f} zł\n"
                f"Marka: {result.laptop.brand}\n"
                f"RAM: {result.laptop.ram}\n"
                f"SSD: {result.laptop.ssd}\n"
                f"GPU: {result.laptop.gpu}\n"
                f"Ekran: {result.laptop.screen}\n"
                f"System: {result.laptop.operating_system}\n"
                f"Opis semantyczny: {result.laptop.semantic_description}\n"
                f"URL: {result.laptop.url}"
            )
            for result in results
        )
