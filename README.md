# MiniDBshka — Моя личная файловая мини-СУБД

Лабораторная работа №1 по курсу «Базы данных».  

Проект представляет собой полностью независимую реляционную мини-СУБД, написанную на Python без использования сторонних СУБД, ORM или pandas. Основное хранилище — собственные текстовые файлы со структурированным хранением и индексным доступом.

---

## 1. Возможности

- **Файловое хранилище (Persistence):** Данные и схема сохраняются в файлы на диске (`schema.txt`, `.tbl`, `.idx`) и переживают полный перезапуск программы.
- **3 связанные таблицы:** `datasets`, `models`, `experiments`.
- **Поддержка типов данных:** `INT`, `FLOAT`, `STRING` с валидацией при вставке и обновлении.
- **Первичные ключи (PRIMARY KEY):** Автогенерация ID при отсутствии значения, строгий запрет дубликатов PK.
- **Внешние ключи (FOREIGN KEY) и ссылочная целостность:** 
  - `experiments.dataset_id -> datasets.id`
  - `experiments.model_id -> models.id`
  - Запрет добавления экспериментов с несуществующими датасетами/моделями.
- **Полный CRUD:** `CREATE TABLE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`.
- **SELECT:** 
  - Выбор отдельных столбцов (`SELECT id, name`) или всех (`SELECT *`).
  - Операторы сравнения: `=`, `!=`, `>`, `<`, `>=`, `<=`.
  - Составные условия с логикой `AND` и `OR`.
- **INNER JOIN:** Поддержка соединения двух и трех таблиц (например, объединение эксперимента с названиями датасета и модели).
- **Простой индекс `id -> offset`:** Файл `.idx` хранит байтовые смещения записей. Поиск по ID выполняется мгновенно через вызов `seek(offset)` без линейного перебора строк.
- **Бенчмарк индекса:** Команда `BENCHMARK` наглядно сравнивает время 100 запросов по ID без индекса (линейное чтение) и с индексом (seek), демонстрируя ускорение в 15–30 раз на 1500+ записях.
- **Backup & Restore:** Команды `BACKUP <каталог>` и `RESTORE <каталог>` для создания резервной копии и восстановления базы.
- **Интерактивный CLI и SQL-парсер:** Удобная командная строка с табличным выводом результатов.

---

## 2. Структура проекта

```text
bd/
│
├── minidb.py           # Ядро СУБД: Table, MiniDB, файловый менеджер, индекс, SQL-парсер
├── main.py             # Интерактивная CLI-консоль для работы с базой
├── test_minidb.py      # Модульные автотесты всех требований 
├── README.md           # Документация и инструкция по запуску
├── REPORT.md           # Подробный отчет 
│
└── minidb_data/        # Каталог с файлами хранилища базы данных
    ├── schema.txt      # Описание структуры таблиц, типов, PK и связей FK
    ├── datasets.tbl    # Данные таблицы datasets
    ├── datasets.idx    # Индекс id -> offset для datasets
    ├── models.tbl      # Данные таблицы models
    ├── models.idx      # Индекс id -> offset для models
    ├── experiments.tbl # Данные таблицы experiments
    └── experiments.idx # Индекс id -> offset для experiments
```

---

## 3. Запуск программы

Для работы нужен только стандартный Python 3. Дополнительные библиотеки устанавливать не требуется.

### Запуск интерактивной консоли:
```bash
python3 main.py
```
После запуска напишите `INIT` (если база еще не инициализирована) или `HELP` для просмотра справки.

### Запуск демонстрационного сценария защиты:
Скрипт автоматически шаг за шагом выполняет сценарий, описанный в методичке:
```bash
py demo.py
```

### Запуск полного набора автотестов:
```bash
py test_minidb.py
```

---

## 4. Формат собственного файлового хранилища

### 4.1. Схема (`schema.txt`)
Текстовый конфигурационный файл с директивами:
```text
TABLE datasets
PK id
COL id INT
COL name STRING
COL task STRING
COL size INT

TABLE experiments
PK id
COL id INT
COL dataset_id INT FK datasets.id
COL model_id INT FK models.id
COL accuracy FLOAT
COL status STRING
```

### 4.2. Файл данных (`<имя_таблицы>.tbl`)
Текстовый файл, в котором каждая запись занимает одну строку, а значения полей разделены символом `|`:
```text
1|MNIST|classification|70000
2|CIFAR-10|image recognition|60000
3|ImageNet|computer vision|1400000
```

### 4.3. Файл индекса (`<имя_таблицы>.idx`)
Файл ассоциативного соответствия первичного ключа и байтового смещения начала строки в `.tbl`:
```text
1:0
2:30
3:66
```
При поиске `id=2` база считывает `offset=30`, выполняет `file.seek(30)` и читает ровно одну нужную строку за время $O(1)$.

---

## 6. Примеры команд в консоли MiniDB

### Выборка данных:
```sql
SELECT * FROM datasets
SELECT id, name, size FROM datasets WHERE size >= 60000
SELECT * FROM experiments WHERE accuracy >= 0.85 AND status = 'completed'
SELECT * FROM experiments WHERE status = 'running' OR status = 'failed'
```

### Соединение таблиц (INNER JOIN):
```sql
SELECT experiments.id, datasets.name, models.name, experiments.accuracy, experiments.status FROM experiments JOIN datasets ON experiments.dataset_id = datasets.id JOIN models ON experiments.model_id = models.id WHERE experiments.accuracy >= 0.85
```

### Вставка, изменение и удаление:
```sql
INSERT INTO datasets VALUES (6, 'WikiText', 'language modeling', 150000)
UPDATE experiments SET status = 'completed', accuracy = 0.92 WHERE id = 3
DELETE FROM experiments WHERE id = 20
```

### Бенчмарк, Бэкап и Восстановление:
```sql
BENCHMARK 1500
BACKUP my_backup
RESTORE my_backup
```
