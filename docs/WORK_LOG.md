# Журнал работ (контекст для разработки)

Подробные записи о нетривиальных изменениях, экспериментах и интеграциях. Цель — сохранять контекст между сессиями и для новых участников.

---

## 2026-03-23 — Выборка 10 листингов Qobrix → Databricks (ручной CLI-ингест)

### Задача

Проверить цепочку: REST API Qobrix → локальный скрипт → запись в Unity Catalog / Delta в Databricks, без запуска полного ноутбука bronze-ETL.

### Контекст репозитория

- Основной промышленный путь: ноутбук `notebooks/00_full_refresh_qobrix_bronze.py` (выполняется **внутри Databricks**), тянет данные из Qobrix и пишет нормализованные bronze-таблицы в схему `qobrix_bronze` (в т.ч. `properties` — все поля как строки после `pd.json_normalize`).
- Локальный RESO API (`api/`) ходит в Databricks через **SQL Statements HTTP API** (`api/services/databricks.py`), без Spark на машине разработчика.

### Принятое решение

Добавлен **разовый** скрипт на Python в каталоге `tmp/` (временные артефакты по правилам проекта):

| Элемент | Значение |
|--------|----------|
| Файл | `tmp/load_qobrix_listings_sample_to_databricks.py` |
| Зависимость | `databricks-sql-connector` (установлен в `api/venv`, не добавлен в `api/requirements.txt` — только для этого эксперимента; при необходимости закрепить в requirements) |
| Каталог UC | Из `.env`: `DATABRICKS_CATALOG` (по умолчанию `mls2`) |
| Схема | **`qobrix_bronze`** — осознанно **не** `DATABRICKS_SCHEMA` из `.env` (там часто `reso_gold` для API), чтобы не смешивать staging с gold. |
| Таблица | `tmp_qobrix_listings_cli_ingest` |

### Схема staging-таблицы

| Колонка | Тип | Назначение |
|---------|-----|------------|
| `property_id` | STRING | ID объекта в Qobrix (`data[].id` из API) |
| `raw_json` | STRING | Полный JSON объекта листинга (`json.dumps` с `ensure_ascii=False`) |
| `ingested_at` | TIMESTAMP | UTC время загрузки |
| `source_tag` | STRING | Константа-метка источника скрипта (отладка / аудит) |

Формат **намеренно упрощён** относительно таблицы `properties` в bronze-ноутбуке: не дублируем 200+ колонок вручную из локальной машины; при необходимости дальнейшая нормализация — в SQL/ноутбуке в Databricks (`from_json`, `variant` и т.д.).

### Переменные окружения (`.env`)

**Qobrix** (как в `scripts/verify_api_integrity.sh`):

- `QOBRIX_API_BASE_URL`, `QOBRIX_API_USER`, `QOBRIX_API_KEY`  
  **или** `SRC_1_API_URL`, `SRC_1_API_USER`, `SRC_1_API_KEY`

**Databricks**:

- `DATABRICKS_HOST` (с `https://` или без)
- `DATABRICKS_TOKEN`
- `DATABRICKS_HTTP_PATH` **или** `DATABRICKS_WAREHOUSE_ID` (скрипт соберёт path вида `/sql/1.0/warehouses/<id>`)
- `DATABRICKS_CATALOG` (опционально, по умолчанию `mls2`)

Опционально:

- `QOBRIX_SAMPLE_LIMIT` — число листингов (по умолчанию `10`).

### Запуск

Из корня репозитория:

```bash
# один раз, если venv ещё без коннектора
api/venv/bin/pip install 'databricks-sql-connector>=3.0.0'

api/venv/bin/python tmp/load_qobrix_listings_sample_to_databricks.py
```

### Идемпотентность

Перед `INSERT` выполняется `DELETE` по тем же `property_id`, что пришли в текущем батче — повторный запуск **заменяет** строки для этих объектов, а не дублирует (общее число строк в таблице может быть больше 10, если в разных запусках подтягивались разные наборы id).

### Проверка в Databricks

```sql
SELECT property_id, length(raw_json) AS json_len, ingested_at, source_tag
FROM mls2.qobrix_bronze.tmp_qobrix_listings_cli_ingest
ORDER BY ingested_at DESC
LIMIT 20;
```

(Подставьте свой каталог, если не `mls2`.)

### Результат прогона (среда разработки, 2026-03-23)

- Успешно: **10** записей из Qobrix, в таблице после загрузки — **10** строк.
- В логе возможны предупреждения: `python-dotenv could not parse statement starting at line 85` — относится к синтаксису строки в пользовательском `.env`, не к скрипту; при необходимости поправить проблемную строку в `.env`.
- `databricks-sql-connector` 4.x предупреждает об отсутствии `pyarrow` — для `executemany` INSERT не требуется; для Arrow-фетча можно поставить `pyarrow`.

### Связь с основным пайплайном

- Эта таблица **не** участвует в стандартных ноутбуках silver/gold; это **изолированный staging-слой для экспериментов**.
- Для продакшен-потока по-прежнему использовать `00_full_refresh_qobrix_bronze.py` / CDC-ноутбуки и целевую таблицу `qobrix_bronze.properties`.

### Установленные зависимости (вне commit)

- В `api/venv`: `databricks-sql-connector>=3.0.0` (фактическая установка может подтянуть 4.x).

---

*Дальнейшие записи добавлять с датой и тем же уровнем детализации: цель, решение, файлы, env, команды, отличия от основного пайплайна.*

## 2026-03-23 — Unity Catalog `mls_2_0` (изоляция, greenfield)

### Цель

Вынести все Delta-таблицы MLS 2.0 в отдельный UC-каталог **`mls_2_0`**, параметризовать код через `DATABRICKS_CATALOG` / widget, не писать в legacy `mls2`. Миграция данных из `mls2` не выполнялась (greenfield).

### Изменения в репозитории

| Область | Файлы / действия |
|---------|------------------|
| Bootstrap UC | [scripts/sql/init_uc_catalog_mls_2_0.sql](scripts/sql/init_uc_catalog_mls_2_0.sql) — `CREATE CATALOG` / схемы + закомментированные GRANT |
| CDC SQL для bash | [scripts/sql/cdc_bronze_counts.sql](scripts/sql/cdc_bronze_counts.sql) — плейсхолдер `__CATALOG__`, подстановка в [scripts/run_pipeline.sh](scripts/run_pipeline.sh) через Python |
| Pipeline | [scripts/run_pipeline.sh](scripts/run_pipeline.sh) — после `.env`: `DATABRICKS_CATALOG`, `MLS_NOTEBOOK_BASE`; все `runs submit` передают `DATABRICKS_CATALOG`; пути ноутбуков `${MLS_NOTEBOOK_BASE}/...` |
| Импорт ноутбуков | [scripts/import_notebooks.sh](scripts/import_notebooks.sh) — `MLS_NOTEBOOK_BASE` (default `/Shared/mls_2_0`) |
| Проверки / cron | [scripts/verify_data_integrity.sh](scripts/verify_data_integrity.sh), [scripts/cron_all_sources_cdc.sh](scripts/cron_all_sources_cdc.sh), [scripts/load_dash_data.sh](scripts/load_dash_data.sh) |
| Dash bronze loader | [scripts/load_dash_bronze.py](scripts/load_dash_bronze.py) — `databricks_catalog` из Settings |
| RESO API default | [api/config.py](api/config.py) — `databricks_catalog` default `mls_2_0` |
| Пример env | [.env.example](.env.example) — `DATABRICKS_CATALOG=mls_2_0`, комментарии `MLS_NOTEBOOK_BASE` |
| Ноутбуки | Все `notebooks/*.py` с `catalog = "mls2"`: widget `DATABRICKS_CATALOG` (default `mls_2_0`), резолв через `os.getenv` \| widget; в MAGIC-доках `mls2.` заменено на `<uc_catalog>.` |

### Чеклист после мержа

1. В Databricks выполнить [scripts/sql/init_uc_catalog_mls_2_0.sql](scripts/sql/init_uc_catalog_mls_2_0.sql) (или создать каталог в UI) и выдать права ETL-роли.
2. В `.env`: `DATABRICKS_CATALOG=mls_2_0`, при необходимости `MLS_NOTEBOOK_BASE=/mls_etl/notebooks`.
3. `./scripts/import_notebooks.sh` затем `./scripts/run_pipeline.sh bronze` (или `all`).
4. Перезапустить RESO API (`./scripts/pm2-manage.sh restart`).
5. Поиск остатков старого имени: `rg 'catalog = "mls2"'` и `rg 'mls2\\.' --glob '*.py'` (в репозитории не должно остаться в коде).

