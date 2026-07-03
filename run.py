"""
Консольный запуск Negative Knowledge Bank.

Использование:
    python run.py "повысить жаропрочность никелевого сплава на 15%"
    python run.py "снизить себестоимость шихты без потери прочности" --constraints "бюджет ограничен, оборудование стандартное"

Требует переменную окружения OPENAI_API_KEY.
Результат печатается в консоль и сохраняется в report.md.
"""

import argparse
import os
import sys

from nkb_core import NegativeKnowledgeBank

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "failed_experiments.json")


def format_report(result: dict) -> str:
    """Форматирует результат в читаемый Markdown-отчёт."""
    lines = []
    lines.append(f"# Гипотезы для цели: {result['goal']}\n")
    if result.get("constraints"):
        lines.append(f"**Ограничения:** {result['constraints']}\n")

    lines.append("## Учтённые прошлые неудачи\n")
    if result["relevant_failures"]:
        for rf in result["relevant_failures"]:
            lines.append(f"- `{rf['id']}` — {rf['title']} (релевантность {rf['score']})")
    else:
        lines.append("- Похожих неудач в банке не найдено.")
    lines.append("")

    lines.append("## Сгенерированные гипотезы\n")
    for i, h in enumerate(result["hypotheses"], 1):
        lines.append(f"### Гипотеза {i}\n")
        lines.append(f"**Формулировка:** {h.get('statement', '—')}\n")
        lines.append(f"- **Механизм:** {h.get('mechanism', '—')}")
        lines.append(f"- **Учитывает неудачу:** {h.get('based_on_failure', '—')}")
        lines.append(f"- **Чем отличается:** {h.get('why_different', '—')}")
        lines.append(f"- **Новизна:** {h.get('novelty', '—')}")
        lines.append(f"- **Риски:** {h.get('risks', '—')}")
        lines.append(f"- **Ожидаемая ценность:** {h.get('expected_value', '—')}")
        lines.append(f"- **Проверка:** {h.get('verification', '—')}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Negative Knowledge Bank")
    parser.add_argument("goal", help="Целевое свойство или проблема")
    parser.add_argument("--constraints", default="", help="Ограничения (сырьё, бюджет, оборудование)")
    parser.add_argument("--top_k", type=int, default=3, help="Сколько прошлых неудач учитывать")
    parser.add_argument("--n", type=int, default=3, help="Сколько гипотез сгенерировать")
    args = parser.parse_args()

    if not os.environ.get("YANDEX_API_KEY") or not os.environ.get("YANDEX_FOLDER_ID"):
        print("ОШИБКА: не заданы YANDEX_API_KEY и/или YANDEX_FOLDER_ID.", file=sys.stderr)
        print("Нужны оба значения из Yandex AI Studio.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Windows (PowerShell):", file=sys.stderr)
        print('  $env:YANDEX_API_KEY="ваш-ключ"', file=sys.stderr)
        print('  $env:YANDEX_FOLDER_ID="ваш-folder-id"', file=sys.stderr)
        print("", file=sys.stderr)
        print("Mac/Linux:", file=sys.stderr)
        print("  export YANDEX_API_KEY=ваш-ключ", file=sys.stderr)
        print("  export YANDEX_FOLDER_ID=ваш-folder-id", file=sys.stderr)
        sys.exit(1)

    print("Загружаю банк неудачных экспериментов...")
    bank = NegativeKnowledgeBank()
    n = bank.load_from_json(DATA_PATH)
    print(f"Загружено записей: {n}\n")

    print(f"Ищу похожие неудачи и генерирую гипотезы для цели:\n  «{args.goal}»\n")
    result = bank.generate_hypotheses(
        goal=args.goal,
        constraints=args.constraints,
        top_k=args.top_k,
        n_hypotheses=args.n,
    )

    report = format_report(result)
    print(report)

    out_path = os.path.join(os.path.dirname(__file__), "report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nMarkdown-отчёт сохранён: {out_path}")

    # Дополнительно — экспорт в Word (.docx) для бизнес-требования отчётности
    try:
        from report_export import build_report_docx
        docx_path = os.path.join(os.path.dirname(__file__), "report.docx")
        with open(docx_path, "wb") as f:
            f.write(build_report_docx(result))
        print(f"DOCX-отчёт сохранён:      {docx_path}")
    except ImportError:
        print("Подсказка: для экспорта в .docx установите  pip install python-docx")


if __name__ == "__main__":
    main()
