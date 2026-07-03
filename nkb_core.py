"""
Negative Knowledge Bank (NKB) — фабрика гипотез из неудачных экспериментов.

Ядро системы. Отвечает за:
  1. Хранение записей о неудачных экспериментах в структурированном виде
     (что пробовали / почему не сработало / при каких условиях / что изменить).
  2. Семантический поиск похожих прошлых неудач по новой исследовательской цели.
  3. Генерацию проверяемых гипотез, которые ЯВНО учитывают, что уже не сработало.

Работает через Yandex AI Studio по OpenAI-совместимому API.
Зависит только от пакета `openai` и стандартной библиотеки.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict, field
from typing import Any

from openai import OpenAI

# --- Настройки Yandex AI Studio --------------------------------------------
# Базовый адрес OpenAI-совместимого API Yandex AI Studio.
YANDEX_BASE_URL = "https://ai.api.cloud.yandex.net/v1"

# Имена моделей (folder_id подставляется автоматически в _model_uri).
#   Генеративная модель — YandexGPT. Можно заменить на 'yandexgpt-lite' (дешевле/быстрее)
#   или на модель из Model Gallery (напр. 'qwen3-235b-a22b-fp8').
CHAT_MODEL_NAME = "yandexgpt/latest"

# Эмбеддинги у Yandex разделены на два типа для лучшего качества поиска:
#   text-search-doc   — для векторизации ДОКУМЕНТОВ (записей банка)
#   text-search-query — для векторизации ПОИСКОВОГО ЗАПРОСА (цели исследователя)
EMBEDDING_DOC_NAME = "text-search-doc"
EMBEDDING_QUERY_NAME = "text-search-query"
# ---------------------------------------------------------------------------


@dataclass
class FailedExperiment:
    """Одна запись негативного знания.

    Поля отражают ровно ту структуру, которую мы обещаем в презентации:
    что пробовали, почему не сработало, при каких условиях, что можно изменить.
    """
    id: str
    title: str
    tried: str            # что пробовали
    why_failed: str       # почему не сработало
    conditions: str       # при каких условиях (режимы, сырьё, оборудование)
    what_to_change: str   # что можно изменить, чтобы попробовать снова
    domain: str = "металлургия"
    source: str = ""      # источник: отчёт №, автор, дата
    embedding: list[float] | None = field(default=None, repr=False)

    def to_search_text(self) -> str:
        """Текст, по которому строится векторное представление записи."""
        return (
            f"Направление: {self.domain}. "
            f"Пробовали: {self.tried}. "
            f"Условия: {self.conditions}. "
            f"Не сработало потому что: {self.why_failed}."
        )


def _cosine(a: list[float], b: list[float]) -> float:
    """Косинусная близость двух векторов."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class NegativeKnowledgeBank:
    """Хранилище неудачных экспериментов + поиск + генерация гипотез.

    Работает через Yandex AI Studio (OpenAI-совместимый API).
    Нужны две вещи:
      - API-ключ    (переменная окружения YANDEX_API_KEY или аргумент api_key)
      - folder_id   (переменная окружения YANDEX_FOLDER_ID или аргумент folder_id)
    """

    def __init__(self, api_key: str | None = None, folder_id: str | None = None):
        key = api_key or os.environ.get("YANDEX_API_KEY")
        folder = folder_id or os.environ.get("YANDEX_FOLDER_ID")
        if not key:
            raise RuntimeError(
                "Не найден YANDEX_API_KEY. Задайте переменную окружения "
                "или передайте api_key в NegativeKnowledgeBank(...)."
            )
        if not folder:
            raise RuntimeError(
                "Не найден YANDEX_FOLDER_ID (идентификатор каталога). Задайте "
                "переменную окружения или передайте folder_id в NegativeKnowledgeBank(...)."
            )
        self.folder_id = folder
        # project=folder_id — так Yandex AI Studio понимает, в каком каталоге работать.
        self.client = OpenAI(
            api_key=key,
            base_url=YANDEX_BASE_URL,
            project=folder,
        )
        self.experiments: list[FailedExperiment] = []

    # ----------------------- Формирование URI модели -----------------------
    def _chat_uri(self) -> str:
        return f"gpt://{self.folder_id}/{CHAT_MODEL_NAME}"

    def _emb_uri(self, name: str) -> str:
        return f"emb://{self.folder_id}/{name}/latest"

    # ----------------------- Загрузка данных -------------------------------
    def add_experiment(self, exp: FailedExperiment) -> None:
        """Добавляет запись и сразу считает для неё embedding (как документ)."""
        exp.embedding = self._embed(exp.to_search_text(), is_query=False)
        self.experiments.append(exp)

    def load_from_json(self, path: str) -> int:
        """Загружает список неудачных экспериментов из JSON-файла."""
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        for row in rows:
            row.pop("embedding", None)  # игнорируем старые кэши
            self.add_experiment(FailedExperiment(**row))
        return len(rows)

    def save_to_json(self, path: str) -> None:
        """Сохраняет банк (вместе с embeddings) в JSON — как кэш."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.experiments], f,
                      ensure_ascii=False, indent=2)

    # ----------------------- Векторный поиск -------------------------------
    def _embed(self, text: str, is_query: bool) -> list[float]:
        """Считает embedding одного текста.

        Yandex использует РАЗНЫЕ модели для документов и для запросов —
        это повышает качество семантического поиска.
        """
        model_uri = self._emb_uri(
            EMBEDDING_QUERY_NAME if is_query else EMBEDDING_DOC_NAME
        )
        resp = self.client.embeddings.create(
            model=model_uri, input=text, encoding_format="float"
        )
        return resp.data[0].embedding

    def search(self, goal: str, top_k: int = 3) -> list[tuple[FailedExperiment, float]]:
        """Находит top_k прошлых неудач, наиболее релевантных цели `goal`."""
        if not self.experiments:
            return []
        q = self._embed(goal, is_query=True)
        scored = [(e, _cosine(q, e.embedding)) for e in self.experiments if e.embedding]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:top_k]

    # ----------------------- Генерация гипотез -----------------------------
    def generate_hypotheses(
        self,
        goal: str,
        constraints: str = "",
        top_k: int = 3,
        n_hypotheses: int = 3,
    ) -> dict[str, Any]:
        """Главная функция. Возвращает структуру с гипотезами и обоснованием.

        Отличие от обычного RAG: в контекст модели подаются именно НЕУДАЧИ,
        и мы прямо требуем, чтобы каждая гипотеза учитывала, почему прошлые
        попытки провалились, и предлагала конкретное изменение.
        """
        relevant = self.search(goal, top_k=top_k)

        # Собираем контекст из найденных неудач.
        if relevant:
            context_blocks = []
            for exp, score in relevant:
                context_blocks.append(
                    f"[{exp.id}] {exp.title} (релевантность {score:.2f})\n"
                    f"  Пробовали: {exp.tried}\n"
                    f"  Условия: {exp.conditions}\n"
                    f"  Почему не сработало: {exp.why_failed}\n"
                    f"  Предложенное изменение: {exp.what_to_change}\n"
                    f"  Источник: {exp.source or 'внутренний отчёт'}"
                )
            context = "\n\n".join(context_blocks)
        else:
            context = "Похожих неудачных экспериментов в банке не найдено."

        system_prompt = (
            "Ты — научный ассистент металлурга-исследователя. Твоя задача — "
            "предлагать проверяемые в лаборатории гипотезы, ОПИРАЯСЬ на банк "
            "неудачных экспериментов. Ключевой принцип: не повторять того, что "
            "уже не сработало, а предлагать конкретное изменение параметра, "
            "которое обходит причину прошлого провала. Каждая гипотеза должна "
            "быть конкретной, с указанием механизма влияния, ссылкой на "
            "релевантную прошлую неудачу (по её ID) и оценкой риска. "
            "Отвечай СТРОГО валидным JSON без markdown, без пояснений до или после."
        )

        user_prompt = (
            f"ЦЕЛЬ ИССЛЕДОВАНИЯ:\n{goal}\n\n"
            f"ОГРАНИЧЕНИЯ:\n{constraints or 'не заданы'}\n\n"
            f"БАНК РЕЛЕВАНТНЫХ НЕУДАЧНЫХ ЭКСПЕРИМЕНТОВ:\n{context}\n\n"
            f"Сформируй ровно {n_hypotheses} гипотез. Верни JSON строго вида:\n"
            "{\n"
            '  "hypotheses": [\n'
            "    {\n"
            '      "statement": "конкретная проверяемая гипотеза",\n'
            '      "mechanism": "ожидаемый физический/химический механизм",\n'
            '      "based_on_failure": "ID прошлой неудачи, которую учитываем, или null",\n'
            '      "why_different": "чем это отличается от того, что уже не сработало",\n'
            '      "novelty": "оценка новизны: низкая/средняя/высокая + пояснение",\n'
            '      "risks": "технические и экономические риски",\n'
            '      "expected_value": "ожидаемое влияние на целевой KPI",\n'
            '      "verification": "как проверить в лаборатории: шаги и критерий успеха"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        resp = self.client.chat.completions.create(
            model=self._chat_uri(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=2000,
        )

        raw = resp.choices[0].message.content
        parsed = _safe_parse_json(raw)

        return {
            "goal": goal,
            "constraints": constraints,
            "relevant_failures": [
                {"id": e.id, "title": e.title, "score": round(s, 3)}
                for e, s in relevant
            ],
            "hypotheses": parsed.get("hypotheses", []),
        }


def _safe_parse_json(raw: str) -> dict:
    """Аккуратно достаёт JSON из ответа модели.

    YandexGPT не всегда поддерживает строгий JSON-режим, поэтому модель может
    обернуть ответ в ```json ... ``` или добавить текст. Вытаскиваем аккуратно.
    """
    if not raw:
        return {"hypotheses": []}
    text = raw.strip()
    # Убираем markdown-ограждение, если есть.
    if text.startswith("```"):
        text = text.strip("`")
        # после снятия бэктиков в начале может остаться "json\n"
        if text.lower().startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Последняя попытка: найти первую { и последнюю }.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {"hypotheses": [], "raw_response": raw}
