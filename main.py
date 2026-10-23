import sys
import os
from minidb import MiniDB, print_table

# Настройка UTF-8 для Windows консоли
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

HELP_TEXT="""
============================== MiniDB CLI ==============================
Поддерживаемые команды:
  HELP                        - показать эту справку
  INIT                        - создать таблицы и заполнить демо-данными (5 datasets, 5 models, 20 experiments)
  SHOW TABLES                 - список всех таблиц
  DESCRIBE <таблица>          - структура таблицы (поля, типы, PK/FK)
  
  SQL-запросы:
  SELECT * FROM <таблица>
  SELECT col1, col2 FROM <таблица> WHERE col1 >= 10 AND col2 = 'val'
  SELECT col1, col2 FROM <таблица> WHERE col1 = 'val1' OR col2 = 'val2'
  SELECT exp.id, d.name, m.name, exp.accuracy FROM experiments exp 
      JOIN datasets ON experiments.dataset_id = datasets.id 
      JOIN models ON experiments.model_id = models.id
  
  INSERT INTO <таблица> VALUES (v1, v2, ...)
  INSERT INTO <таблица> (c1, c2) VALUES (v1, v2)
  UPDATE <таблица> SET c1 = v1, c2 = v2 WHERE id = 1
  DELETE FROM <таблица> WHERE id = 5
  
  Специальные команды:
  BENCHMARK [N]               - тест скорости: линейный поиск vs индекс id->offset (N записей)
  BACKUP [папка]              - резервная копия базы данных
  RESTORE [папка]             - восстановление базы данных из копии
  
  EXIT / QUIT                 - выход из программы
========================================================================
"""

def start_cli():
    print("=================================================")
    print("      MiniDB - Файловая реляционная СУБД        ")
    print("   Лабораторная работа №1    ")
    print("=================================================")
    print("Введите 'HELP' для просмотра команд или 'INIT' для быстрой загрузки данных.\n")

    db=MiniDB("minidb_data")

    # Если база пустая, сообщаем пользователю
    if not db.tables:
        print("[!] База пока пуста. Напишите 'INIT' чтобы создать datasets, models, experiments.")

    while True:
        try:
            cmd=input("MiniDB> ").strip()
            if not cmd:
                continue

            # Выход
            if cmd.upper() in ("EXIT", "QUIT", "Q"):
                print("Выход из MiniDB. Все данные сохранены на диске в minidb_data/.")
                break

            # Справка
            if cmd.upper()=="HELP":
                print(HELP_TEXT)
                continue

            # Инициализация демо-данных
            if cmd.upper()=="INIT":
                msg=db.init_default_data()
                print(f"[OK] {msg}")
                continue

            # Выполнение SQL или служебной команды
            res=db.execute_sql(cmd)
            if res is not None:
                if isinstance(res, list):
                    print_table(res)
                elif isinstance(res, dict):
                    # Если словарь - выводим в виде таблички
                    print_table([res])
                else:
                    print(f"[OK] {res}")

        except KeyboardInterrupt:
            print("\nВыход из MiniDB.")
            break
        except Exception as e:
            print(f"[Ошибка] {e}")

if __name__=="__main__":
    start_cli()
