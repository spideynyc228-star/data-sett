"""Generate a reproducible synthetic dataset for the KROK Prompt Radar hackathon.

The logs deliberately contain no real people, companies, credentials, or customer data.
Each session is padded with realistic tool-return evidence to roughly 60k tokens by a
character-based estimate; measure with the target model tokenizer before production use.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


DATASET_DIR = Path(__file__).resolve().parent
OUT_DIR = DATASET_DIR / "dialogs"
TARGET_CHARS = 220_000  # approximately 55–70k tokens depending on tokenizer
SEED = 20260725

PEOPLE = [
    "Марина", "Илья", "Анна", "Дмитрий", "Олег", "Елена", "Сергей", "Наталья",
    "Алексей", "Вера", "Михаил", "Ксения", "Роман", "Дарья", "Павел",
]
COMPANIES = ["Альтаир", "НордЛайн", "Вектор Плюс", "СеверСофт", "Гелиос", "Маяк", "Орбита"]
DEPARTMENTS = ["Продажи", "Проектный офис", "Разработка", "HR", "Финансы", "Маркетинг"]


SCENARIOS = [
    ("Генерация текста и документов", "Деловое письмо клиенту", "Нужно ответить клиенту после вчерашней встречи: собери из переписки договорённости и подготовь спокойное письмо с планом следующих шагов.", ["gmail.search", "gmail.get_thread", "crm.get_company", "confluence.search"]),
    ("Генерация текста и документов", "Черновик технического задания", "Собери черновик ТЗ по итогам обсуждения: интеграция CRM с витриной, роли пользователей, сроки и открытые вопросы. Без канцелярита, пожалуйста.", ["confluence.search", "jira.search_issue", "gmail.search", "drive.search"]),
    ("Поиск и сбор информации", "Исследование клиента", "Найди по компании клиента {company}: кто принимает решения в дочерних обществах, какие у нас были сделки и что нового появилось в открытых источниках.", ["crm.get_company", "crm.search_deals", "web.search", "web.open"]),
    ("Поиск и сбор информации", "Поиск внутренних регламентов", "Не могу быстро найти актуальный порядок согласования закупки. Посмотри в базе знаний и дай ссылки именно на действующие документы.", ["confluence.search", "confluence.get_page", "sharepoint.search", "drive.search"]),
    ("Анализ данных и отчетность", "Отчёт по выигранным тендерам", "Сделай короткий отчёт по выигранным тендерам за последние семь дней: сумма, ответственный, отрасль и что важно вынести на планёрку.", ["crm.search_deals", "database.query", "excel.read", "crm.get_company"]),
    ("Анализ данных и отчетность", "Выгрузка CRM в Excel", "Нужна выгрузка по клиентам из CRM для руководителя: активные сделки, стадия, сумма и последняя активность. Проверь, чтобы не было дублей.", ["crm.search_deals", "database.query", "crm.get_company", "excel.create"]),
    ("Работа с задачами и проектами", "Разбор задач Jira", "Покажи мои задачи на эту неделю, отдельно просроченные и блокированные. Для двух самых срочных собери контекст из комментариев.", ["jira.search_issue", "jira.get_issue", "jira.get_comments", "confluence.search"]),
    ("Работа с задачами и проектами", "Мониторинг статусов проектов", "Проверь статусы проектов в ИСУП. Интересуют переходы в риск, просрочки контрольных точек и проекты без обновления больше недели.", ["isup.search_projects", "isup.get_project", "isup.get_milestones", "jira.search_issue"]),
    ("Управление коммуникациями", "Разбор почты и ответ клиенту", "Прочитай цепочку с {company}, скажи, где мы обещали вернуться с расчётом, и предложи ответ без обещаний, которые пока не можем выполнить.", ["gmail.search", "gmail.get_thread", "crm.get_company", "calendar.get_events"]),
    ("Управление коммуникациями", "Итоги встречи", "Собери из записи встречи итоги, решения, владельцев и дедлайны. Потом подготовь короткое сообщение в командный чат.", ["calendar.get_event", "meeting.transcript", "contacts.lookup", "slack.get_channel_history"]),
    ("Помощь с кодом и техническими вопросами", "Разбор инцидента", "Почему контейнер API упал утром? Посмотри логи, последние деплои и связанные задачи. Нужен человеческий вывод: причина, влияние, что уже сделано.", ["monitoring.get_metrics", "docker.get_containers", "git.get_commits", "jira.search_issue"]),
    ("Помощь с кодом и техническими вопросами", "Ревью Python-кода", "Посмотри изменения в сервисе расчёта скидок. Найди рискованные места, особенно обработку пустых данных и округление денег.", ["git.get_diff", "code.analyze", "jira.search_issue", "confluence.search"]),
    ("Планирование и календарь", "Поиск общего слота", "Найди на следующей неделе 45 минут для встречи с командой проекта и заказчиком. Лучше не утром и нужна переговорная на восемь человек.", ["calendar.find_slots", "contacts.lookup", "rooms.search", "calendar.get_events"]),
    ("Планирование и календарь", "Подготовка к завтрашним встречам", "Что у меня завтра по встречам? Для встреч с клиентами вытащи последние договорённости и напомни, что нужно подготовить.", ["calendar.get_events", "crm.get_company", "gmail.search", "confluence.search"]),
    ("Автоматизация рабочих процессов", "Контроль писем без ответа", "Хочу, чтобы агент каждые два часа проверял письма с запросом цены и напоминал мне, если клиенту не ответили вовремя. Сначала покажи, по каким правилам это будет работать.", ["gmail.search", "workflow.get_rules", "crm.search_deals", "notifications.preview"]),
    ("Автоматизация рабочих процессов", "Еженедельная рассылка продаж", "Настрой еженедельную сводку по выигранным тендерам для команды продаж: собираем CRM, формируем таблицу и отправляем в понедельник в 10:00.", ["crm.search_deals", "workflow.get_rules", "excel.create", "gmail.draft"]),
    ("Обучение и объяснение", "Объяснение корпоративного процесса", "Объясни простыми словами, как у нас проходит согласование договора: что делает менеджер, юрист и финансовый контролёр. С примерами типичных задержек.", ["confluence.search", "confluence.get_page", "sharepoint.search", "jira.search_issue"]),
    ("Обучение и объяснение", "Разбор SQL-ошибки", "Объясни, почему мой SQL-запрос дублирует строки после join. Не просто исправь, а покажи на маленьком примере, где я ошибся.", ["code.analyze", "database.query", "confluence.search", "web.search"]),
    ("Общие вопросы и нерабочие запросы", "Планирование отпуска", "Помоги прикинуть бюджет поездки в Калининград на неделю для двоих в конце сентября: дорога, жильё, еда и пара экскурсий. Нужен диапазон, а не точность до рубля.", ["web.search", "travel.search", "calculator", "maps.search"]),
    ("Общие вопросы и нерабочие запросы", "Домашний рецепт", "Хочу на выходных сделать оладьи. Дай надёжный рецепт на четыре порции и подскажи, как не переборщить с маслом.", ["web.search", "recipe.search", "calculator", "notes.search"]),
]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tool_record(rng: random.Random, session_no: int, tool_name: str, n: int, topic: str, company: str) -> dict:
    authors = rng.sample(PEOPLE, k=3)
    detail = (
        f"Запись {n + 1} по контексту «{topic}». В источнике упомянуты этап, ответственный и зависимость от смежной команды. "
        f"Для {company} зафиксировано, что решение нужно сверить с последним письмом и не переносить в итог без подтверждения владельца. "
        f"{authors[0]} отметил, что срок ориентировочный; {authors[1]} ждёт входные данные; {authors[2]} попросил добавить риск в следующую сводку. "
        f"Техническая деталь: версия артефакта {rng.randint(2, 9)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}, приоритет {rng.choice(['обычный', 'высокий', 'критический'])}, "
        f"следующее действие — {rng.choice(['проверить ограничения', 'сверить цифры', 'получить согласование', 'назначить владельца', 'обновить комментарий'])}."
    )
    return {
        "record_id": f"rec_{session_no:03d}_{tool_name.replace('.', '_')}_{n:03d}",
        "timestamp": iso(datetime(2026, 5, 1, tzinfo=timezone.utc) + timedelta(days=rng.randrange(90), minutes=rng.randrange(1440))),
        "title": f"{topic}: рабочая запись {n + 1}",
        "author": authors[0],
        "status": rng.choice(["актуально", "нужна проверка", "в работе", "ожидает ответа"]),
        "excerpt": detail,
        "source_url": f"synthetic://{tool_name}/{session_no}/{n}",
    }


def large_tool_result(rng: random.Random, session_no: int, tool_name: str, topic: str, company: str, call_no: int) -> dict:
    count = rng.randint(27, 34)
    return {
        "status": "ok",
        "source": tool_name.split(".")[0],
        "query_context": topic,
        "fetched_at": iso(datetime(2026, 7, 25, tzinfo=timezone.utc) + timedelta(minutes=session_no * 7 + call_no)),
        "total_found": count + rng.randint(0, 25),
        "records": [tool_record(rng, session_no, tool_name, n, topic, company) for n in range(count)],
        "synthetic_notice": "Synthetic source payload for hackathon evaluation; not a real corporate-system response.",
    }


def message(role: str, content: str, ts: datetime, **extra: object) -> dict:
    data = {"role": role, "timestamp": iso(ts), "content": content}
    data.update(extra)
    return data


def generate_session(index: int, rng: random.Random) -> dict:
    category, scenario, request_template, tools = SCENARIOS[index % len(SCENARIOS)]
    company = rng.choice(COMPANIES)
    request = request_template.format(company=company)
    start = datetime(2026, 5, 1, 8, tzinfo=timezone.utc) + timedelta(days=rng.randrange(91), minutes=rng.randrange(600))
    user_id = f"usr_{rng.randrange(1, 26):06d}"
    session_id = f"sess_2026{start.strftime('%m%d')}_{index + 1:06d}"
    agent_id = rng.choice(["agent_workplace_01", "agent_sales_02", "agent_project_03", "agent_engineering_04"])
    is_error_case = index < 10
    is_personal = category == "Общие вопросы и нерабочие запросы"
    messages = [
        message("user", request, start),
        message("assistant", rng.choice([
            "Понял. Сначала соберу контекст из доступных источников, потом сверю противоречия и дам короткий вывод с деталями по запросу.",
            "Да, проверю это последовательно. Если в источниках будут расхождения, отмечу их отдельно, а не буду угадывать.",
            "Возьму в работу. Начну с первичных данных, затем проверю связанные записи и вернусь с понятной сводкой.",
        ]), start + timedelta(seconds=3)),
    ]

    # Ten sizeable retrieval calls make the long context plausible: the agent gathers source evidence.
    expanded_tools = [tools[n % len(tools)] for n in range(10)]
    for call_no, tool_name in enumerate(expanded_tools):
        call_time = start + timedelta(seconds=7 + call_no * 18)
        messages.append({
            "role": "tool",
            "timestamp": iso(call_time),
            "tool_name": tool_name,
            "arguments": {
                "query": f"{topic_for(category, scenario)}; {company}; batch={call_no + 1}",
                "limit": 100,
                "include_archived": False,
            },
            "result": large_tool_result(rng, index + 1, tool_name, topic_for(category, scenario), company, call_no),
        })
        if call_no in (2, 6):
            messages.append(message(
                "assistant",
                rng.choice([
                    "Нашёл несколько связанных записей. Проверяю, не относятся ли старые комментарии к другой версии задачи.",
                    "Вижу расхождение по дате. Сверяю первоисточник, чтобы не включить устаревшую информацию.",
                    "Контекста много, поэтому отсекаю дубли и оставляю только записи, которые влияют на решение.",
                ]),
                call_time + timedelta(seconds=6),
            ))

    if is_error_case:
        messages.extend([
            message("assistant", "Предварительно вижу, что последняя активность относится к текущему периоду; могу уже сформулировать итог.", start + timedelta(minutes=4)),
            message("user", rng.choice([
                "Стоп, кажется, ты взял не тот период: мне нужен именно текущий месяц, без старого архива.",
                "Проверь ещё раз: это не тот проект. Нужен контур клиента, а не внутренний пилот.",
                "Не отправляй итог. В списке есть запись другого подразделения — исключи её и пересчитай.",
            ]), start + timedelta(minutes=4, seconds=18)),
            message("assistant", "Вы правы, спасибо, что заметили. Я смешал запись из соседнего контура с целевой выборкой. Исправляю фильтр, повторно проверяю первоисточник и отмечу исправление в результате.", start + timedelta(minutes=4, seconds=25)),
            {
                "role": "tool",
                "timestamp": iso(start + timedelta(minutes=4, seconds=35)),
                "tool_name": expanded_tools[0],
                "arguments": {"query": f"{topic_for(category, scenario)}; {company}; corrected_scope=true", "date_from": start.strftime("%Y-%m-01")},
                "result": {"status": "ok", "correction_applied": True, "excluded_records": rng.randint(3, 11), "records": [tool_record(rng, index + 1, expanded_tools[0], n, scenario, company) for n in range(36)]},
            },
        ])

    work_label = "личному" if is_personal else "рабочему"
    final = (
        f"Готово. Я собрал контекст по сценарию «{scenario}» и сверил данные из {len(set(expanded_tools))} типов источников. "
        f"Коротко: по {work_label} запросу есть {rng.randint(4, 12)} значимых пункта, {rng.randint(1, 4)} требуют решения владельца и "
        f"{rng.randint(1, 3)} стоит перепроверить перед отправкой дальше.\n\n"
        f"Что важно:\n"
        f"• Основной результат: {rng.choice(['данные согласованы между источниками', 'есть зависимость от ответа коллеги', 'часть сведений устарела и не включена', 'следующий шаг можно автоматизировать'])}.\n"
        f"• Риск: {rng.choice(['не подтверждён срок', 'есть дублирующая запись', 'нужен доступ к смежному контуру', 'требуется уточнение формата'])}.\n"
        f"• Рекомендация: {rng.choice(['зафиксировать владельца и дедлайн', 'сначала согласовать короткий черновик', 'настроить регулярную проверку', 'вернуться к вопросу после обновления данных'])}."
    )
    if is_error_case:
        final += "\n\nИсправление: первоначально в выборку попали данные из неверного контура. Я исключил их, повторил поиск с корректным фильтром и сформировал итог только по целевой выборке."
    messages.append(message("assistant", final, start + timedelta(minutes=6)))

    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "model_id": "synthetic-corporate-agent-v1",
        "department": rng.choice(DEPARTMENTS) if not is_personal else "Личное",
        "created_at": iso(start),
        "scenario_type": category,
        "scenario": scenario,
        "is_synthetic": True,
        "error_corrected": is_error_case,
        "messages": messages,
    }
    return payload


def topic_for(category: str, scenario: str) -> str:
    return f"{category}: {scenario}"


def pad_to_target(payload: dict, rng: random.Random) -> None:
    """Add evidence records to the final tool call until the JSON reaches the target size."""
    while len(json.dumps(payload, ensure_ascii=False)) < TARGET_CHARS:
        tool_messages = [m for m in payload["messages"] if m["role"] == "tool"]
        target = tool_messages[-1]
        records = target["result"].setdefault("records", [])
        n = len(records)
        records.append(tool_record(rng, n + 1000, target["tool_name"], n, payload["scenario"], rng.choice(COMPANIES)))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # The generator owns its output directory; remove only prior generated JSON sessions.
    for path in OUT_DIR.glob("session_*.json"):
        path.unlink()

    manifest = []
    for index in range(100):
        rng = random.Random(SEED + index)
        payload = generate_session(index, rng)
        pad_to_target(payload, rng)
        path = OUT_DIR / f"session_{index + 1:04d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        chars = len(path.read_text(encoding="utf-8"))
        manifest.append({
            "file": str(path),
            "estimated_tokens": round(chars / 4),
            "characters": chars,
            "scenario_type": payload["scenario_type"],
            "error_corrected": payload["error_corrected"],
            "is_non_work": payload["department"] == "Личное",
        })

    (DATASET_DIR / "manifest.json").write_text(json.dumps({"seed": SEED, "sessions": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} files in {OUT_DIR}")
    print(f"Character range: {min(x['characters'] for x in manifest)}–{max(x['characters'] for x in manifest)}")
    print(f"Estimated token range: {min(x['estimated_tokens'] for x in manifest)}–{max(x['estimated_tokens'] for x in manifest)}")


if __name__ == "__main__":
    main()
