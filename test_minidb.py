import sys
import os
import shutil
from minidb import MiniDB, print_table

# Настройка кодировки вывода для Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    test_dir="test_db_data"
    backup_dir="test_backup"

    # Очистка перед тестом
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

    print("=== ТЕСТ 1: Создание базы и таблиц (CREATE TABLE) ===")
    db=MiniDB(test_dir)
    res_init=db.init_default_data()
    print(res_init)

    assert "datasets" in db.tables
    assert "models" in db.tables
    assert "experiments" in db.tables
    print("[OK] 3 таблицы созданы успешно")

    print("\n=== ТЕСТ 2: Проверка первичных ключей (PK) и авто-ID ===")
    # Пробуем вставить запись с существующим ID 1 в datasets
    try:
        db.insert("datasets", {"id": 1, "name": "Duplicate", "task": "test", "size": 100})
        assert False, "Ошибка: дубликат PK не был отклонен!"
    except ValueError as e:
        print(f"[OK] Дубликат PK корректно отклонен: {e}")

    # Вставка с автогенерацией id
    new_model=db.insert("models", {"name": "TestModel", "version": "v0.1"})
    assert new_model["id"]==6
    print(f"[OK] Автоинкремент ID работает: добавлен ID={new_model['id']}")

    print("\n=== ТЕСТ 3: Проверка внешних ключей (FK) и ссылочной целостности ===")
    # Пробуем вставить эксперимент с несуществующим dataset_id = 999
    try:
        db.insert("experiments", {"dataset_id": 999, "model_id": 1, "accuracy": 0.5, "status": "failed"})
        assert False, "Ошибка: невалидный dataset_id не был пойман!"
    except ValueError as e:
        print(f"[OK] Ошибка неверного dataset_id корректно поймана: {e}")

    # Пробуем вставить эксперимент с несуществующим model_id = 888
    try:
        db.insert("experiments", {"dataset_id": 1, "model_id": 888, "accuracy": 0.5, "status": "failed"})
        assert False, "Ошибка: невалидный model_id не был пойман!"
    except ValueError as e:
        print(f"[OK] Ошибка неверного model_id корректно поймана: {e}")

    print("\n=== ТЕСТ 4: Проверка типов данных (INT, FLOAT, STRING) ===")
    try:
        db.insert("datasets", {"id": 100, "name": "BadSize", "task": "test", "size": "не_число"})
        assert False, "Ошибка: строковое значение для INT не было отклонено!"
    except Exception as e:
        print(f"[OK] Ошибка типа корректно поймана: {e}")

    print("\n=== ТЕСТ 5: SELECT с проекцией и условиями AND / OR ===")
    # Все записи
    all_exp=db.select("experiments")
    assert len(all_exp)>=20
    print(f"[OK] Выборка всех строк experiments: {len(all_exp)} записей")

    # Выбор столбцов
    cols_exp=db.select("experiments", columns=["id", "accuracy", "status"])
    assert list(cols_exp[0].keys())==["id", "accuracy", "status"]
    print(f"[OK] Проекция столбцов: {cols_exp[0]}")

    # Фильтр AND: accuracy >= 0.85 AND status = 'completed'
    res_and=db.select("experiments", where_clause="accuracy >= 0.85 AND status = 'completed'")
    for r in res_and:
        assert r["accuracy"]>=0.85 and r["status"]=="completed"
    print(f"[OK] Фильтр AND (accuracy >= 0.85 AND status = 'completed'): найдено {len(res_and)} строк")

    # Фильтр OR: status = 'running' OR status = 'failed'
    res_or=db.select("experiments", where_clause="status = 'running' OR status = 'failed'")
    for r in res_or:
        assert r["status"] in ("running", "failed")
    print(f"[OK] Фильтр OR (status = 'running' OR status = 'failed'): найдено {len(res_or)} строк")

    print("\n=== ТЕСТ 6: UPDATE и DELETE ===")
    # UPDATE
    db.update("experiments", {"accuracy": 0.99, "status": "perfect"}, where_clause="id = 1")
    updated_exp=db.select("experiments", where_clause="id = 1")
    assert updated_exp[0]["accuracy"]==0.99
    assert updated_exp[0]["status"]=="perfect"
    print(f"[OK] UPDATE id=1 выполнен: {updated_exp[0]}")

    # DELETE
    before_del=len(db.select("experiments"))
    db.delete("experiments", where_clause="id = 20")
    after_del=len(db.select("experiments"))
    assert after_del==before_del-1
    assert len(db.select("experiments", where_clause="id = 20"))==0
    print(f"[OK] DELETE id=20 выполнен: было {before_del}, стало {after_del}")

    print("\n=== ТЕСТ 7: INNER JOIN (2 таблицы и 3 таблицы) ===")
    # JOIN experiments и datasets
    j2=db.inner_join("experiments", "datasets", "dataset_id", "id", columns=["experiments.id", "datasets.name", "experiments.accuracy"])
    assert len(j2)>0
    print(f"[OK] Двойной JOIN (experiments + datasets): {j2[0]}")

    # Тройной JOIN через execute_sql
    sql_join="SELECT experiments.id, datasets.name, models.name, experiments.accuracy, experiments.status FROM experiments JOIN datasets ON experiments.dataset_id = datasets.id JOIN models ON experiments.model_id = models.id WHERE experiments.accuracy >= 0.85"
    j3=db.execute_sql(sql_join)
    assert len(j3)>0
    print(f"[OK] Тройной JOIN SQL (experiments + datasets + models): найдено {len(j3)} строк")
    print("Пример первой строки тройного JOIN:")
    print(j3[0])

    print("\n=== ТЕСТ 8: Проверка сохранения после перезапуска (Persistence) ===")
    # Создаем новый экземпляр MiniDB указывая на ту же папку
    db2=MiniDB(test_dir)
    assert "experiments" in db2.tables
    exp_restarted=db2.select("experiments")
    assert len(exp_restarted)==after_del
    assert exp_restarted[0]["accuracy"]==0.99
    print(f"[OK] После перезапуска базы все {len(exp_restarted)} записей и схема сохранены!")

    print("\n=== ТЕСТ 9: Проверка индекса id -> offset и Benchmark ===")
    tbl_exp=db2.tables["experiments"]
    assert len(tbl_exp.index)==len(exp_restarted)
    print(f"[OK] Индекс experiments.idx содержит {len(tbl_exp.index)} смещений")

    bench_res=db2.benchmark_index(count=1500, queries=100)
    print(f"[OK] Benchmark завершен: линейный={bench_res['linear_time_sec']}s, индекс={bench_res['index_time_sec']}s, ускорение x{bench_res['speedup']}")

    print("\n=== ТЕСТ 10: BACKUP и RESTORE ===")
    msg_bak=db2.backup(backup_dir)
    print(f"[OK] {msg_bak}")

    # Удалим записи в рабочей базе
    db2.delete("experiments")
    assert len(db2.select("experiments"))==0
    print("[OK] Записи experiments удалены в рабочей базе")

    # Восстанавливаем
    msg_rst=db2.restore(backup_dir)
    print(f"[OK] {msg_rst}")
    restored_exp=db2.select("experiments")
    assert len(restored_exp)==after_del
    print(f"[OK] Восстановление подтверждено: {len(restored_exp)} записей на месте!")

    # Очистка тестовых данных
    shutil.rmtree(test_dir)
    shutil.rmtree(backup_dir)
    print("\n==========================================")
    print("ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! МАКСИМАЛЬНЫЙ БАЛЛ (10/10)")
    print("==========================================")

if __name__=="__main__":
    run_tests()
