"""
Negative Knowledge Bank — веб-интерфейс.

Минималистичный дизайн: один акцентный цвет, тонкие бордеры,
шрифт Inter, воздух вокруг блоков. Никаких стандартных эмодзи и заливок.
"""

import json
import os
import streamlit as st

from nkb_core import NegativeKnowledgeBank

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "failed_experiments.json")

st.set_page_config(
    page_title="Negative Knowledge Bank",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Кастомный CSS. Всё, что нельзя настроить через config.toml, задаётся здесь.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Подключаем Inter — нейтральный современный шрифт */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        letter-spacing: -0.01em;
    }

    /* Прячем стандартный хедер и меню Streamlit — они мешают в кадре */
    #MainMenu {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    footer {visibility: hidden;}

    /* Убираем лишний отступ сверху основного контента */
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Заголовки — потоньше, поспокойнее */
    h1 {
        font-weight: 600 !important;
        font-size: 2rem !important;
        letter-spacing: -0.03em !important;
        margin-bottom: 0.25rem !important;
        color: #1F1F1F !important;
    }
    h2 {
        font-weight: 600 !important;
        font-size: 1.15rem !important;
        letter-spacing: -0.02em !important;
        color: #1F1F1F !important;
        margin-top: 2rem !important;
        margin-bottom: 0.75rem !important;
    }
    h3 { font-weight: 500 !important; font-size: 1rem !important; }

    /* Подзаголовок под H1 — приглушённый серый */
    .subtitle {
        color: #6B6B68;
        font-size: 0.95rem;
        margin-top: 0;
        margin-bottom: 2rem;
    }

    /* Кнопка — плоская, тонкая, с чётким состоянием */
    .stButton > button {
        background-color: #2B4C3F;
        color: #FAFAF7;
        border: 1px solid #2B4C3F;
        border-radius: 6px;
        padding: 0.55rem 1.25rem;
        font-weight: 500;
        font-size: 0.92rem;
        letter-spacing: -0.01em;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        background-color: #1F3A2E;
        border-color: #1F3A2E;
        transform: none;
    }
    .stButton > button:focus:not(:active) {
        border-color: #2B4C3F;
        color: #FAFAF7;
        box-shadow: 0 0 0 3px rgba(43, 76, 63, 0.15);
    }

    /* Поля ввода — тонкие бордеры вместо заливок */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        border: 1px solid #D6D3CB !important;
        border-radius: 6px !important;
        background-color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.92rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: #2B4C3F !important;
        box-shadow: 0 0 0 3px rgba(43, 76, 63, 0.1) !important;
    }

    /* Боковая панель — приглушённый бежевый, тонкая правая граница */
    section[data-testid="stSidebar"] {
        background-color: #F0EEE9;
        border-right: 1px solid #E5E3DD;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* Expander — плоский, без теней, с тонкой линией */
    .streamlit-expanderHeader,
    div[data-testid="stExpander"] > details > summary {
        background-color: transparent !important;
        border: 1px solid #E5E3DD !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        color: #1F1F1F !important;
        padding: 0.75rem 1rem !important;
    }
    div[data-testid="stExpander"] > details[open] > summary {
        border-bottom-left-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
        border-bottom-color: transparent !important;
    }
    div[data-testid="stExpander"] > details > div {
        border: 1px solid #E5E3DD;
        border-top: none;
        border-radius: 0 0 6px 6px;
        padding: 1rem 1.25rem 1.25rem;
        background: #FFFFFF;
    }

    /* Карточки-неудачи: тонкий бордер, воздух внутри */
    .failure-card {
        border: 1px solid #E5E3DD;
        border-left: 3px solid #B08D57;   /* тёплый акцент для "негативного знания" */
        border-radius: 6px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        background: #FFFFFF;
    }
    .failure-card .id {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.78rem;
        color: #6B6B68;
        letter-spacing: 0;
    }
    .failure-card .title {
        font-weight: 500;
        color: #1F1F1F;
        margin-top: 0.15rem;
    }
    .failure-card .score {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.78rem;
        color: #6B6B68;
        float: right;
    }

    /* Разделитель — почти невидимый */
    hr {
        border: none;
        border-top: 1px solid #E5E3DD;
        margin: 2rem 0;
    }

    /* Подписи полей — компактно, без "капса" */
    label, .stTextArea label, .stTextInput label, .stSlider label {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #4A4A47 !important;
        letter-spacing: 0 !important;
    }

    /* Слайдер под акцентный цвет */
    .stSlider [data-baseweb="slider"] > div > div > div {
        background: #2B4C3F !important;
    }

    /* Мелкий текст в сайдбаре */
    .sidebar-note {
        color: #6B6B68;
        font-size: 0.82rem;
        line-height: 1.5;
    }

    /* Убираем лишний verbose alert-стиль */
    div[data-testid="stAlert"] {
        border-radius: 6px;
        border-width: 1px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Хедер
# ---------------------------------------------------------------------------
st.markdown("# Negative Knowledge Bank")
st.markdown(
    '<p class="subtitle">Фабрика гипотез из неудачных экспериментов — '
    'система, которая не повторяет то, что уже не сработало.</p>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Боковая панель
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Доступ к Yandex AI Studio")
    api_key = st.text_input(
        "API Key",
        value=os.environ.get("YANDEX_API_KEY", ""),
        type="password",
    )
    folder_id = st.text_input(
        "Folder ID",
        value=os.environ.get("YANDEX_FOLDER_ID", ""),
    )

    st.markdown("### Параметры поиска")
    top_k = st.slider("Прошлых неудач в контексте", 1, 6, 3)
    n_hyp = st.slider("Гипотез на выходе", 1, 5, 3)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-note">'
        'Система берёт цель исследования, находит похожие прошлые провалы '
        'через векторный поиск и генерирует гипотезы, обходящие причину провала. '
        'Работает на моделях YandexGPT и text-search-embeddings.'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Форма запроса
# ---------------------------------------------------------------------------
col_a, col_b = st.columns([3, 2], gap="large")

with col_a:
    goal = st.text_area(
        "Цель исследования",
        value="Повысить жаропрочность никелевого сплава на 15% при 900°C",
        height=90,
    )

with col_b:
    constraints = st.text_area(
        "Ограничения",
        value="Стандартное литейное оборудование, без дорогих легирующих добавок",
        height=90,
    )

_, col_btn = st.columns([3, 1])
with col_btn:
    run_clicked = st.button("Сгенерировать гипотезы", use_container_width=True)


# ---------------------------------------------------------------------------
# Кэш банка
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_bank(key: str, folder: str):
    bank = NegativeKnowledgeBank(api_key=key, folder_id=folder)
    bank.load_from_json(DATA_PATH)
    return bank


# ---------------------------------------------------------------------------
# Основная логика: генерация и вывод
# ---------------------------------------------------------------------------
if run_clicked:
    if not api_key or not folder_id:
        st.error("Введите API Key и Folder ID в боковой панели.")
        st.stop()
    try:
        with st.spinner("Индексирую банк неудач…"):
            bank = load_bank(api_key, folder_id)
        with st.spinner("Ищу похожие провалы и генерирую гипотезы…"):
            result = bank.generate_hypotheses(
                goal=goal,
                constraints=constraints,
                top_k=top_k,
                n_hypotheses=n_hyp,
            )
    except Exception as e:
        st.error(f"Не удалось выполнить запрос: {e}")
        st.stop()

    st.markdown("<hr>", unsafe_allow_html=True)

    # -- Найденные неудачи --------------------------------------------------
    st.markdown("## Учтённые прошлые неудачи")
    if result["relevant_failures"]:
        for rf in result["relevant_failures"]:
            st.markdown(
                f'<div class="failure-card">'
                f'<span class="score">релевантность {rf["score"]:.2f}</span>'
                f'<div class="id">{rf["id"]}</div>'
                f'<div class="title">{rf["title"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Похожих неудач в банке не найдено — гипотезы построены с нуля.")

    # -- Гипотезы ------------------------------------------------------------
    st.markdown("## Гипотезы")
    if not result["hypotheses"]:
        st.warning("Модель не вернула структурированных гипотез. Попробуйте ещё раз.")

    for i, h in enumerate(result["hypotheses"], 1):
        header = f"{i}.  {h.get('statement', '—')}"
        with st.expander(header, expanded=(i == 1)):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**Механизм**")
                st.markdown(h.get("mechanism", "—"))
                st.markdown("")
                st.markdown("**Опирается на неудачу**")
                st.markdown(f"`{h.get('based_on_failure', '—')}`")
                st.markdown("")
                st.markdown("**Чем отличается от того, что не сработало**")
                st.markdown(h.get("why_different", "—"))
            with c2:
                st.markdown("**Новизна**")
                st.markdown(h.get("novelty", "—"))
                st.markdown("")
                st.markdown("**Риски**")
                st.markdown(h.get("risks", "—"))
                st.markdown("")
                st.markdown("**Ожидаемая ценность**")
                st.markdown(h.get("expected_value", "—"))
            st.markdown("")
            st.markdown("**Как проверить в лаборатории**")
            st.markdown(h.get("verification", "—"))

    # -- Экспорт в Word ------------------------------------------------------
    if result["hypotheses"]:
        try:
            from report_export import build_report_docx
            docx_bytes = build_report_docx(result)
            st.markdown("")
            _, col_dl = st.columns([3, 1])
            with col_dl:
                st.download_button(
                    label="Скачать отчёт (DOCX)",
                    data=docx_bytes,
                    file_name="nkb_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
        except ImportError:
            st.info(
                "Для экспорта в Word нужен пакет `python-docx`. "
                "Установите: `pip install python-docx`"
            )


# ---------------------------------------------------------------------------
# Добавление нового эксперимента в банк (свёрнуто по умолчанию)
# ---------------------------------------------------------------------------
st.markdown("<hr>", unsafe_allow_html=True)
with st.expander("Добавить новый неудачный эксперимент в банк", expanded=False):
    st.markdown(
        '<div class="sidebar-note" style="margin-bottom:1rem;">'
        'Запись сохраняется в <code>data/failed_experiments.json</code> и сразу '
        'становится доступна для поиска. Векторное представление считается '
        'автоматически.'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.form("add_experiment", clear_on_submit=True):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            new_id = st.text_input("ID записи", placeholder="EXP-007")
            new_title = st.text_input("Короткое название", placeholder="Кратко, о чём эксперимент")
            new_domain = st.selectbox(
                "Направление",
                ["металлургия", "обогащение", "гидрометаллургия",
                 "пирометаллургия", "материаловедение", "другое"],
            )
            new_source = st.text_input("Источник", placeholder="Отчёт №... / автор / дата")
        with c2:
            new_tried = st.text_area("Что пробовали", height=80)
            new_conditions = st.text_area("При каких условиях", height=80)

        new_why = st.text_area("Почему не сработало", height=80)
        new_change = st.text_area("Что можно изменить, чтобы попробовать снова", height=80)

        submitted = st.form_submit_button("Сохранить запись")

    if submitted:
        if not all([new_id, new_title, new_tried, new_why, new_conditions, new_change]):
            st.error("Заполните все поля кроме источника — он не обязателен.")
        elif not api_key or not folder_id:
            st.error("Для расчёта векторного представления нужны API Key и Folder ID.")
        else:
            new_record = {
                "id": new_id.strip(),
                "title": new_title.strip(),
                "tried": new_tried.strip(),
                "why_failed": new_why.strip(),
                "conditions": new_conditions.strip(),
                "what_to_change": new_change.strip(),
                "domain": new_domain,
                "source": new_source.strip(),
            }
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    rows = json.load(f)
                # Не допускаем дубликатов по ID
                if any(r["id"] == new_record["id"] for r in rows):
                    st.error(f"Запись с ID {new_record['id']} уже существует.")
                else:
                    rows.append(new_record)
                    with open(DATA_PATH, "w", encoding="utf-8") as f:
                        json.dump(rows, f, ensure_ascii=False, indent=2)
                    # Сбрасываем кэш банка, чтобы новая запись подхватилась
                    load_bank.clear()
                    st.success(
                        f"Запись {new_record['id']} добавлена. При следующей "
                        f"генерации гипотез она попадёт в векторный поиск."
                    )
            except Exception as e:
                st.error(f"Не удалось сохранить: {e}")


# ---------------------------------------------------------------------------
# Просмотр всего банка (свёрнуто по умолчанию)
# ---------------------------------------------------------------------------
with st.expander("Просмотреть весь банк неудачных экспериментов", expanded=False):
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = json.load(f)
    st.caption(f"Всего записей: {len(rows)}")
    for r in rows:
        st.markdown(
            f'<div class="failure-card" style="border-left-color:#B08D57;">'
            f'<div class="id">{r["id"]} · {r.get("domain", "")}</div>'
            f'<div class="title">{r["title"]}</div>'
            f'<div style="margin-top:0.5rem; font-size:0.88rem; color:#4A4A47; line-height:1.55;">'
            f'<b>Пробовали:</b> {r["tried"]}<br>'
            f'<b>Почему не сработало:</b> {r["why_failed"]}<br>'
            f'<b>Что изменить:</b> {r["what_to_change"]}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
