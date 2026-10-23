import os
import shutil
import time
import random
import re


TYPES=["INT", "FLOAT", "STRING"]

def cast_val(val, col_type):
    if val is None:
        return None
    val_str=str(val).strip()
    if col_type=="INT":
        return int(val_str)
    elif col_type=="FLOAT":
        return float(val_str)
    elif col_type=="STRING":
        if (val_str.startswith("'") and val_str.endswith("'")) or (val_str.startswith('"') and val_str.endswith('"')):
            val_str=val_str[1:-1]
        return val_str
    return val_str

def match_cond(row_val, op, target_val):
    if row_val is None:
        return False
    if isinstance(row_val, (int, float)):
        try:
            target_val=type(row_val)(target_val)
        except:
            return False
    else:
        target_val=str(target_val)
        row_val=str(row_val)

    if op=="=":
        return row_val==target_val
    elif op=="!=":
        return row_val!=target_val
    elif op==">":
        return row_val>target_val
    elif op=="<":
        return row_val<target_val
    elif op==">=":
        return row_val>=target_val
    elif op=="<=":
        return row_val<=target_val
    return False

def print_table(rows, headers=None):
    if not rows:
        print("(0 строк найдено)")
        return
    if headers is None:
        headers=list(rows[0].keys())

    col_widths={}
    for h in headers:
        col_widths[h]=len(str(h))
    for r in rows:
        for h in headers:
            val=str(r.get(h, ""))
            if len(val)>col_widths[h]:
                col_widths[h]=len(val)

    border="+"+"+".join("-"*(col_widths[h]+2) for h in headers)+"+"
    header_line="|"+"|".join(f" {str(h).ljust(col_widths[h])} " for h in headers)+"|"

    print(border)
    print(header_line)
    print(border)
    for r in rows:
        row_line="|"+"|".join(f" {str(r.get(h, '')).ljust(col_widths[h])} " for h in headers)+"|"
        print(row_line)
    print(border)
    print(f"Всего строк: {len(rows)}\n")

class Table:
    def __init__(self, name, db_dir, columns=None, pk="id", fks=None):
        self.name=name
        self.db_dir=db_dir
        self.columns=columns or {}
        self.pk=pk
        self.fks=fks or {}  # {col_name: (ref_table, ref_col)}
        self.data_file=os.path.join(self.db_dir, f"{self.name}.tbl")
        self.idx_file=os.path.join(self.db_dir, f"{self.name}.idx")
        self.index={}  # pk -> offset в байтах
        self.load_index()

    def load_index(self):
        # Загрузка индекса pk -> offset из файла .idx
        self.index={}
        if os.path.exists(self.idx_file) and os.path.exists(self.data_file):
            try:
                with open(self.idx_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line=line.strip()
                        if not line:
                            continue
                        parts=line.split(":")
                        if len(parts)==2:
                            pk_val=cast_val(parts[0], self.columns.get(self.pk, "INT"))
                            self.index[pk_val]=int(parts[1])
                return
            except:
                pass
        self.rebuild_index()

    def rebuild_index(self):
        # Перестроение индекса с нуля по файлу .tbl
        self.index={}
        if not os.path.exists(self.data_file):
            return

        pk_col_idx=list(self.columns.keys()).index(self.pk) if self.pk in self.columns else 0
        pk_type=self.columns.get(self.pk, "INT")

        with open(self.data_file, "rb") as f:
            while True:
                pos=f.tell()
                line=f.readline()
                if not line:
                    break
                text=line.decode("utf-8").strip()
                if not text:
                    continue
                parts=text.split("|")
                if len(parts)>pk_col_idx:
                    pk_val=cast_val(parts[pk_col_idx], pk_type)
                    self.index[pk_val]=pos

        self.save_index_to_file()

    def save_index_to_file(self):
        # Запись индекса в .idx
        with open(self.idx_file, "w", encoding="utf-8") as f:
            for pk_val, offset in sorted(self.index.items(), key=lambda x: (int(x[0]) if str(x[0]).isdigit() else str(x[0]))):
                f.write(f"{pk_val}:{offset}\n")

    def read_row_at_offset(self, offset):
        # Прямое чтение строки по смещению в файле
        if not os.path.exists(self.data_file):
            return None
        with open(self.data_file, "rb") as f:
            f.seek(offset)
            line=f.readline()
            if not line:
                return None
            text=line.decode("utf-8").strip()
            return self.parse_row_text(text)

    def parse_row_text(self, text):
        if not text:
            return None
        parts=text.split("|")
        row={}
        col_names=list(self.columns.keys())
        for i, col in enumerate(col_names):
            if i<len(parts):
                row[col]=cast_val(parts[i], self.columns[col])
            else:
                row[col]=None
        return row

    def row_to_text(self, row_dict):
        parts=[]
        for col in self.columns.keys():
            val=row_dict.get(col, "")
            if val is None:
                val=""
            parts.append(str(val))
        return "|".join(parts)

    def get_all_rows(self):
        rows=[]
        if not os.path.exists(self.data_file):
            return rows
        with open(self.data_file, "r", encoding="utf-8") as f:
            for line in f:
                text=line.strip()
                if text:
                    row=self.parse_row_text(text)
                    if row:
                        rows.append(row)
        return rows

    def get_row_by_id(self, pk_val, use_index=True):
        pk_val=cast_val(pk_val, self.columns.get(self.pk, "INT"))
        if use_index:
            if pk_val in self.index:
                offset=self.index[pk_val]
                return self.read_row_at_offset(offset)
            return None
        else:
            if not os.path.exists(self.data_file):
                return None
            with open(self.data_file, "r", encoding="utf-8") as f:
                for line in f:
                    text=line.strip()
                    if not text:
                        continue
                    row=self.parse_row_text(text)
                    if row and row.get(self.pk)==pk_val:
                        return row
            return None

    def insert(self, row_dict):
        if self.pk not in row_dict or row_dict[self.pk] is None:
            new_id=1
            if self.index:
                numeric_keys=[k for k in self.index.keys() if isinstance(k, int)]
                if numeric_keys:
                    new_id=max(numeric_keys)+1
            row_dict[self.pk]=new_id
        else:
            row_dict[self.pk]=cast_val(row_dict[self.pk], self.columns[self.pk])

        pk_val=row_dict[self.pk]
        if pk_val in self.index:
            raise ValueError(f"Ошибка PK: запись с {self.pk}={pk_val} уже существует в таблице '{self.name}'!")

        casted_row={}
        for col, col_type in self.columns.items():
            if col in row_dict:
                casted_row[col]=cast_val(row_dict[col], col_type)
            else:
                casted_row[col]=None

        row_text=self.row_to_text(casted_row)

        with open(self.data_file, "a", encoding="utf-8") as f:
            offset=f.tell()
            f.write(row_text+"\n")

        self.index[pk_val]=offset
        with open(self.idx_file, "a", encoding="utf-8") as f:
            f.write(f"{pk_val}:{offset}\n")

        return casted_row

    def update(self, set_dict, where_fn=None):
        rows=self.get_all_rows()
        updated_count=0
        new_rows=[]

        for row in rows:
            if where_fn is None or where_fn(row):
                for col, val in set_dict.items():
                    if col==self.pk and cast_val(val, self.columns[self.pk])!=row[self.pk]:
                        new_pk=cast_val(val, self.columns[self.pk])
                        if new_pk in self.index and new_pk!=row[self.pk]:
                            raise ValueError(f"Ошибка PK: id={new_pk} уже занят!")
                    if col in self.columns:
                        row[col]=cast_val(val, self.columns[col])
                updated_count+=1
            new_rows.append(row)

        if updated_count>0:
            self.rewrite_all(new_rows)

        return updated_count

    def delete(self, where_fn=None):
        rows=self.get_all_rows()
        deleted_count=0
        remaining_rows=[]

        for row in rows:
            if where_fn is None or where_fn(row):
                deleted_count+=1
            else:
                remaining_rows.append(row)

        if deleted_count>0:
            self.rewrite_all(remaining_rows)

        return deleted_count

    def rewrite_all(self, rows):
        with open(self.data_file, "w", encoding="utf-8") as f:
            for row in rows:
                line=self.row_to_text(row)
                f.write(line+"\n")
        self.rebuild_index()


class MiniDB:
    def __init__(self, db_dir="minidb_data"):
        self.db_dir=db_dir
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
        self.tables={}
        self.schema_file=os.path.join(self.db_dir, "schema.txt")
        self.load_schema()

    def load_schema(self):
        self.tables={}
        if not os.path.exists(self.schema_file):
            return

        with open(self.schema_file, "r", encoding="utf-8") as f:
            current_table=None
            columns={}
            pk="id"
            fks={}

            for line in f:
                line=line.strip()
                if not line or line.startswith("#"):
                    continue

                parts=line.split()
                cmd=parts[0].upper()

                if cmd=="TABLE":
                    if current_table:
                        self.tables[current_table]=Table(current_table, self.db_dir, columns, pk, fks)
                    current_table=parts[1]
                    columns={}
                    pk="id"
                    fks={}
                elif cmd=="PK":
                    pk=parts[1]
                elif cmd=="COL":
                    col_name=parts[1]
                    col_type=parts[2].upper()
                    columns[col_name]=col_type
                    if len(parts)>=5 and parts[3].upper()=="FK":
                        ref=parts[4].split(".")
                        fks[col_name]=(ref[0], ref[1])

            if current_table:
                self.tables[current_table]=Table(current_table, self.db_dir, columns, pk, fks)

    def save_schema(self):
        with open(self.schema_file, "w", encoding="utf-8") as f:
            for name, tbl in self.tables.items():
                f.write(f"TABLE {name}\n")
                f.write(f"PK {tbl.pk}\n")
                for col_name, col_type in tbl.columns.items():
                    line=f"COL {col_name} {col_type}"
                    if col_name in tbl.fks:
                        ref_tbl, ref_col=tbl.fks[col_name]
                        line+=f" FK {ref_tbl}.{ref_col}"
                    f.write(line+"\n")
                f.write("\n")

    def create_table(self, name, columns, pk="id", fks=None):
        if name in self.tables:
            raise ValueError(f"Таблица '{name}' уже существует!")

        for col, col_type in columns.items():
            if col_type not in TYPES:
                raise ValueError(f"Неизвестный тип данных '{col_type}'. Доступны: {TYPES}")

        fks=fks or {}
        for col, (ref_t, ref_c) in fks.items():
            if ref_t not in self.tables:
                raise ValueError(f"Ошибка FK: таблица '{ref_t}' еще не существует!")
            if ref_c not in self.tables[ref_t].columns:
                raise ValueError(f"Ошибка FK: поле '{ref_c}' не найдено в таблице '{ref_t}'!")

        tbl=Table(name, self.db_dir, columns, pk, fks)
        self.tables[name]=tbl
        self.save_schema()
        if not os.path.exists(tbl.data_file):
            open(tbl.data_file, "w", encoding="utf-8").close()
        tbl.rebuild_index()
        return tbl

    def drop_table(self, name):
        if name not in self.tables:
            raise ValueError(f"Таблица '{name}' не найдена!")
        tbl=self.tables[name]
        if os.path.exists(tbl.data_file):
            os.remove(tbl.data_file)
        if os.path.exists(tbl.idx_file):
            os.remove(tbl.idx_file)
        del self.tables[name]
        self.save_schema()

    def check_fks(self, table_name, row_dict):
        tbl=self.tables[table_name]
        for col, (ref_t, ref_c) in tbl.fks.items():
            if col in row_dict and row_dict[col] is not None:
                val=row_dict[col]
                ref_tbl=self.tables.get(ref_t)
                if not ref_tbl:
                    raise ValueError(f"Ошибка FK: таблица {ref_t} не найдена!")

                if ref_c==ref_tbl.pk:
                    row=ref_tbl.get_row_by_id(val)
                    if not row:
                        raise ValueError(f"Ошибка ссылочной целостности (FK): значение {col}={val} не существует в {ref_t}.{ref_c}!")
                else:
                    rows=ref_tbl.get_all_rows()
                    exists=any(str(r.get(ref_c))==str(val) for r in rows)
                    if not exists:
                        raise ValueError(f"Ошибка ссылочной целостности (FK): значение {col}={val} не существует в {ref_t}.{ref_c}!")

    def insert(self, table_name, row_dict):
        if table_name not in self.tables:
            raise ValueError(f"Таблица '{table_name}' не найдена!")
        self.check_fks(table_name, row_dict)
        return self.tables[table_name].insert(row_dict)

    def parse_where(self, where_clause):
        if not where_clause:
            return [], []

        raw=where_clause.strip()
        is_or=" OR " in raw.upper()
        delimiter=" OR " if is_or else " AND "
        parts=re.split(re.escape(delimiter), raw, flags=re.IGNORECASE)

        parsed_conds=[]
        ops=["<=", ">=", "!=", "=", ">", "<"]

        for part in parts:
            part=part.strip()
            matched=False
            for op in ops:
                if op in part:
                    idx=part.find(op)
                    col=part[:idx].strip()
                    val=part[idx+len(op):].strip()
                    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                        val=val[1:-1]
                    parsed_conds.append((col, op, val))
                    matched=True
                    break
            if not matched:
                raise ValueError(f"Не удалось разобрать условие фильтрации: {part}")

        if is_or:
            return [], parsed_conds
        else:
            return parsed_conds, []

    def eval_where(self, row, where_clause):
        conds_and, conds_or=self.parse_where(where_clause)

        if conds_or:
            for col, op, val in conds_or:
                cell_val=row.get(col)
                if cell_val is None:
                    col_simple=col.split(".")[-1]
                    cell_val=row.get(col_simple)
                if cell_val is not None and match_cond(cell_val, op, val):
                    return True
            return False
        else:
            for col, op, val in conds_and:
                cell_val=row.get(col)
                if cell_val is None:
                    col_simple=col.split(".")[-1]
                    cell_val=row.get(col_simple)
                if cell_val is None or not match_cond(cell_val, op, val):
                    return False
            return True

    def project_columns(self, rows, columns, tbl=None):
        if not columns or columns==["*"] or columns=="*":
            return rows

        if isinstance(columns, str):
            columns=[c.strip() for c in columns.split(",")]

        projected=[]
        for r in rows:
            new_r={}
            for c in columns:
                if c in r:
                    new_r[c]=r[c]
                else:
                    simple_c=c.split(".")[-1]
                    if simple_c in r:
                        new_r[c]=r[simple_c]
            projected.append(new_r)
        return projected

    def select(self, table_name, columns=None, where_clause=None):
        if table_name not in self.tables:
            raise ValueError(f"Таблица '{table_name}' не найдена!")

        tbl=self.tables[table_name]
        if where_clause:
            conds_and, conds_or=self.parse_where(where_clause)
            if len(conds_and)==1 and not conds_or:
                c_col, c_op, c_val=conds_and[0]
                if c_col==tbl.pk and c_op=="=":
                    single_row=tbl.get_row_by_id(c_val, use_index=True)
                    rows=[single_row] if single_row else []
                    return self.project_columns(rows, columns, tbl)

        all_rows=tbl.get_all_rows()
        if not where_clause:
            return self.project_columns(all_rows, columns, tbl)

        filtered=[r for r in all_rows if self.eval_where(r, where_clause)]
        return self.project_columns(filtered, columns, tbl)

    def update(self, table_name, set_dict, where_clause=None):
        if table_name not in self.tables:
            raise ValueError(f"Таблица '{table_name}' не найдена!")

        tbl=self.tables[table_name]
        for col, val in set_dict.items():
            if col in tbl.fks:
                ref_t, ref_c=tbl.fks[col]
                ref_tbl=self.tables.get(ref_t)
                if ref_tbl:
                    row=ref_tbl.get_row_by_id(val)
                    if not row:
                        raise ValueError(f"Ошибка FK: значение {col}={val} не найдено в {ref_t}.{ref_c}!")

        where_fn=None
        if where_clause:
            where_fn=lambda r: self.eval_where(r, where_clause)

        return tbl.update(set_dict, where_fn)

    def delete(self, table_name, where_clause=None):
        if table_name not in self.tables:
            raise ValueError(f"Таблица '{table_name}' не найдена!")

        where_fn=None
        if where_clause:
            where_fn=lambda r: self.eval_where(r, where_clause)

        return self.tables[table_name].delete(where_fn)

    def inner_join(self, table1, table2, on_col1, on_col2, columns=None, where_clause=None):
        if table1 not in self.tables:
            raise ValueError(f"Таблица '{table1}' не найдена!")
        if table2 not in self.tables:
            raise ValueError(f"Таблица '{table2}' не найдена!")

        rows1=self.tables[table1].get_all_rows()
        tbl2=self.tables[table2]

        c1=on_col1.split(".")[-1]
        c2=on_col2.split(".")[-1]

        joined=[]
        for r1 in rows1:
            val1=r1.get(c1)
            if val1 is None:
                continue

            if c2==tbl2.pk:
                r2=tbl2.get_row_by_id(val1)
                matches=[r2] if r2 else []
            else:
                matches=[r for r in tbl2.get_all_rows() if r.get(c2)==val1]

            for r2 in matches:
                combined={}
                for k, v in r1.items():
                    combined[f"{table1}.{k}"]=v
                    combined[k]=v
                for k, v in r2.items():
                    combined[f"{table2}.{k}"]=v
                    if k not in r1:
                        combined[k]=v
                joined.append(combined)

        if where_clause:
            joined=[r for r in joined if self.eval_where(r, where_clause)]

        return self.project_columns(joined, columns)

    def multi_join(self, joins_info, columns=None, where_clause=None):
        # Поддержка соединения нескольких таблиц
        # joins_info: [("experiments", None, None), ("datasets", "experiments.dataset_id", "datasets.id"), ("models", "experiments.model_id", "models.id")]
        base_table=joins_info[0][0]
        rows=self.tables[base_table].get_all_rows()

        curr=[]
        for r in rows:
            rec={}
            for k, v in r.items():
                rec[f"{base_table}.{k}"]=v
                rec[k]=v
            curr.append(rec)

        for next_table, on_left, on_right in joins_info[1:]:
            tbl2=self.tables[next_table]
            c_left=on_left.strip()
            c_right=on_right.strip().split(".")[-1]
            new_curr=[]

            for r1 in curr:
                val1=r1.get(c_left)
                if val1 is None:
                    val1=r1.get(c_left.split(".")[-1])
                if val1 is None:
                    continue

                if c_right==tbl2.pk:
                    match=tbl2.get_row_by_id(val1)
                    matches=[match] if match else []
                else:
                    matches=[r for r in tbl2.get_all_rows() if r.get(c_right)==val1]

                for m in matches:
                    combined=dict(r1)
                    for k, v in m.items():
                        combined[f"{next_table}.{k}"]=v
                        if k not in combined:
                            combined[k]=v
                    new_curr.append(combined)
            curr=new_curr

        if where_clause:
            curr=[r for r in curr if self.eval_where(r, where_clause)]

        return self.project_columns(curr, columns)

    def backup(self, backup_dir="backup"):
        # Создание резервной копии
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(self.db_dir, backup_dir)
        return f"Резервная копия создана в каталоге '{backup_dir}'"

    def restore(self, backup_dir="backup"):
        # Восстановление из резервной копии
        if not os.path.exists(backup_dir):
            raise FileNotFoundError(f"Каталог резервной копии '{backup_dir}' не найден!")
        if os.path.exists(self.db_dir):
            shutil.rmtree(self.db_dir)
        shutil.copytree(backup_dir, self.db_dir)
        self.load_schema()
        for tbl in self.tables.values():
            tbl.load_index()
        return f"База данных успешно восстановлена из '{backup_dir}'"

    def benchmark_index(self, count=1000, queries=100):
        # Замер скорости поиска с индексом и без
        bench_table="bench_dataset"
        if bench_table in self.tables:
            self.drop_table(bench_table)

        self.create_table(bench_table, {
            "id": "INT",
            "name": "STRING",
            "metric": "FLOAT"
        }, pk="id")

        tbl=self.tables[bench_table]
        rows_to_insert=[]
        for i in range(1, count+1):
            rows_to_insert.append({
                "id": i,
                "name": f"sample_{i}",
                "metric": round(random.random(), 4)
            })

        with open(tbl.data_file, "w", encoding="utf-8") as f:
            for r in rows_to_insert:
                f.write(tbl.row_to_text(r)+"\n")
        tbl.rebuild_index()

        target_ids=[random.randint(1, count) for _ in range(queries)]

        # 1. Поиск без индекса (линейный перебор строк файла)
        t0=time.perf_counter()
        for tid in target_ids:
            tbl.get_row_by_id(tid, use_index=False)
        t_linear=time.perf_counter()-t0

        # 2. Поиск с индексом (id -> seek offset в файле)
        t1=time.perf_counter()
        for tid in target_ids:
            tbl.get_row_by_id(tid, use_index=True)
        t_index=time.perf_counter()-t1

        speedup=t_linear/t_index if t_index>0 else 1.0

        self.drop_table(bench_table)

        return {
            "records": count,
            "queries": queries,
            "linear_time_sec": round(t_linear, 5),
            "index_time_sec": round(t_index, 5),
            "speedup": round(speedup, 2)
        }

    def init_default_data(self):
        # Инициализация схемы и 5 datasets, 5 models, 20 experiments
        # Сбрасываем старые таблицы если есть
        for t in ["experiments", "models", "datasets"]:
            if t in self.tables:
                self.drop_table(t)

        self.create_table("datasets", {
            "id": "INT",
            "name": "STRING",
            "task": "STRING",
            "size": "INT"
        }, pk="id")

        self.create_table("models", {
            "id": "INT",
            "name": "STRING",
            "version": "STRING"
        }, pk="id")

        self.create_table("experiments", {
            "id": "INT",
            "dataset_id": "INT",
            "model_id": "INT",
            "accuracy": "FLOAT",
            "status": "STRING"
        }, pk="id", fks={
            "dataset_id": ("datasets", "id"),
            "model_id": ("models", "id")
        })
        datasets=[
            {"id": 1, "name": "MNIST", "task": "classification", "size": 70000},
            {"id": 2, "name": "CIFAR-10", "task": "image recognition", "size": 60000},
            {"id": 3, "name": "ImageNet", "task": "computer vision", "size": 1400000},
            {"id": 4, "name": "IMDB Reviews", "task": "sentiment analysis", "size": 50000},
            {"id": 5, "name": "COCO", "task": "object detection", "size": 330000}
        ]
        for d in datasets:
            self.insert("datasets", d)

        models=[
            {"id": 1, "name": "ResNet-50", "version": "v1.5"},
            {"id": 2, "name": "BERT-base", "version": "v2.0"},
            {"id": 3, "name": "YOLOv8", "version": "v8.1"},
            {"id": 4, "name": "MobileNetV3", "version": "v3.0"},
            {"id": 5, "name": "GPT-2-small", "version": "v1.0"}
        ]
        for m in models:
            self.insert("models", m)

        experiments=[
            {"id": 1, "dataset_id": 1, "model_id": 1, "accuracy": 0.91, "status": "completed"},
            {"id": 2, "dataset_id": 1, "model_id": 2, "accuracy": 0.88, "status": "completed"},
            {"id": 3, "dataset_id": 2, "model_id": 1, "accuracy": 0.76, "status": "running"},
            {"id": 4, "dataset_id": 2, "model_id": 3, "accuracy": 0.82, "status": "completed"},
            {"id": 5, "dataset_id": 3, "model_id": 1, "accuracy": 0.74, "status": "completed"},
            {"id": 6, "dataset_id": 3, "model_id": 3, "accuracy": 0.79, "status": "running"},
            {"id": 7, "dataset_id": 4, "model_id": 2, "accuracy": 0.93, "status": "completed"},
            {"id": 8, "dataset_id": 4, "model_id": 5, "accuracy": 0.95, "status": "completed"},
            {"id": 9, "dataset_id": 5, "model_id": 3, "accuracy": 0.85, "status": "completed"},
            {"id": 10, "dataset_id": 1, "model_id": 4, "accuracy": 0.89, "status": "completed"},
            {"id": 11, "dataset_id": 2, "model_id": 4, "accuracy": 0.71, "status": "failed"},
            {"id": 12, "dataset_id": 5, "model_id": 1, "accuracy": 0.68, "status": "completed"},
            {"id": 13, "dataset_id": 4, "model_id": 1, "accuracy": 0.81, "status": "completed"},
            {"id": 14, "dataset_id": 1, "model_id": 3, "accuracy": 0.87, "status": "completed"},
            {"id": 15, "dataset_id": 2, "model_id": 2, "accuracy": 0.84, "status": "completed"},
            {"id": 16, "dataset_id": 3, "model_id": 4, "accuracy": 0.65, "status": "failed"},
            {"id": 17, "dataset_id": 4, "model_id": 4, "accuracy": 0.86, "status": "completed"},
            {"id": 18, "dataset_id": 5, "model_id": 4, "accuracy": 0.72, "status": "completed"},
            {"id": 19, "dataset_id": 1, "model_id": 5, "accuracy": 0.90, "status": "completed"},
            {"id": 20, "dataset_id": 2, "model_id": 5, "accuracy": 0.78, "status": "running"}
        ]
        for exp in experiments:
            self.insert("experiments", exp)

        return "Инициализация успешно выполнена: 5 datasets, 5 models, 20 experiments созданы."

    def execute_sql(self, sql_query):
        # Парсер и исполнитель простых SQL команд
        sql=sql_query.strip().rstrip(";")
        if not sql:
            return None

        # SHOW TABLES
        if sql.upper()=="SHOW TABLES":
            return [{"table_name": t, "records": len(self.tables[t].index)} for t in self.tables]

        # DESCRIBE / DESC <table>
        desc_match=re.match(r"^(?:DESCRIBE|DESC)\s+(\w+)", sql, re.IGNORECASE)
        if desc_match:
            tname=desc_match.group(1)
            if tname not in self.tables:
                raise ValueError(f"Таблица '{tname}' не найдена!")
            tbl=self.tables[tname]
            info=[]
            for col, ctype in tbl.columns.items():
                is_pk=(col==tbl.pk)
                fk_info=""
                if col in tbl.fks:
                    fk_info=f"{tbl.fks[col][0]}.{tbl.fks[col][1]}"
                info.append({
                    "column": col,
                    "type": ctype,
                    "primary_key": is_pk,
                    "foreign_key": fk_info
                })
            return info

        # CREATE TABLE
        if sql.upper().startswith("CREATE TABLE"):
            m=re.match(r"^CREATE\s+TABLE\s+(\w+)\s*\((.*)\)$", sql, re.IGNORECASE | re.DOTALL)
            if not m:
                raise ValueError("Синтаксис: CREATE TABLE name (col1 TYPE [PK], col2 TYPE [FK table.col], ...)")
            tbl_name=m.group(1)
            cols_def=m.group(2).strip()

            cols={}
            pk="id"
            fks={}

            # разбиваем по запятым
            raw_cols=[c.strip() for c in cols_def.split(",") if c.strip()]
            for item in raw_cols:
                parts=item.split()
                cname=parts[0]
                ctype=parts[1].upper()
                cols[cname]=ctype
                if len(parts)>=3:
                    mod=parts[2].upper()
                    if mod=="PK" or mod=="PRIMARY":
                        pk=cname
                    elif mod=="FK" and len(parts)>=4:
                        ref=parts[3].split(".")
                        fks[cname]=(ref[0], ref[1])
                    elif mod=="REFERENCES" and len(parts)>=4:
                        ref=parts[3].replace("(", ".").replace(")", "").split(".")
                        fks[cname]=(ref[0], ref[1])
            self.create_table(tbl_name, cols, pk, fks)
            return f"Таблица '{tbl_name}' успешно создана."

        # INSERT INTO
        if sql.upper().startswith("INSERT INTO"):
            m=re.match(r"^INSERT\s+INTO\s+(\w+)(?:\s*\(([^)]+)\))?\s+VALUES\s*\((.*)\)$", sql, re.IGNORECASE | re.DOTALL)
            if not m:
                raise ValueError("Синтаксис: INSERT INTO table [(col1, col2)] VALUES (val1, val2)")
            tbl_name=m.group(1)
            cols_str=m.group(2)
            vals_str=m.group(3)

            # парсим значения с учетом кавычек
            raw_vals=parse_csv_line(vals_str)

            if tbl_name not in self.tables:
                raise ValueError(f"Таблица '{tbl_name}' не существует!")
            tbl=self.tables[tbl_name]

            row_dict={}
            if cols_str:
                col_names=[c.strip() for c in cols_str.split(",")]
                if len(col_names)!=len(raw_vals):
                    raise ValueError("Количество полей не совпадает с количеством значений!")
                for c, v in zip(col_names, raw_vals):
                    row_dict[c]=v
            else:
                col_names=list(tbl.columns.keys())
                if len(col_names)!=len(raw_vals):
                    raise ValueError(f"Ожидалось {len(col_names)} значений для всех колонок таблицы!")
                for c, v in zip(col_names, raw_vals):
                    row_dict[c]=v

            inserted=self.insert(tbl_name, row_dict)
            return f"Запись успешно добавлена в '{tbl_name}': {inserted}"

        # SELECT
        if sql.upper().startswith("SELECT"):
            # Проверяем наличие JOIN
            if " JOIN " in sql.upper():
                return self.parse_and_run_join_sql(sql)

            m=re.match(r"^SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?$", sql, re.IGNORECASE | re.DOTALL)
            if not m:
                raise ValueError("Синтаксис: SELECT cols FROM table [WHERE conditions]")
            cols_part=m.group(1).strip()
            table_name=m.group(2).strip()
            where_part=m.group(3).strip() if m.group(3) else None

            cols=cols_part if cols_part=="*" else [c.strip() for c in cols_part.split(",")]
            return self.select(table_name, cols, where_part)

        # UPDATE
        if sql.upper().startswith("UPDATE"):
            m=re.match(r"^UPDATE\s+(\w+)\s+SET\s+(.*?)(?:\s+WHERE\s+(.*))?$", sql, re.IGNORECASE | re.DOTALL)
            if not m:
                raise ValueError("Синтаксис: UPDATE table SET col1 = val1, ... [WHERE condition]")
            table_name=m.group(1).strip()
            set_part=m.group(2).strip()
            where_part=m.group(3).strip() if m.group(3) else None

            set_dict={}
            assignments=parse_csv_line(set_part)
            for item in assignments:
                kv=item.split("=")
                if len(kv)==2:
                    k=kv[0].strip()
                    v=kv[1].strip()
                    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                        v=v[1:-1]
                    set_dict[k]=v

            count=self.update(table_name, set_dict, where_part)
            return f"Обновлено записей: {count}"

        # DELETE FROM
        if sql.upper().startswith("DELETE"):
            m=re.match(r"^DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?$", sql, re.IGNORECASE | re.DOTALL)
            if not m:
                raise ValueError("Синтаксис: DELETE FROM table [WHERE condition]")
            table_name=m.group(1).strip()
            where_part=m.group(2).strip() if m.group(2) else None
            count=self.delete(table_name, where_part)
            return f"Удалено записей: {count}"

        # BACKUP
        if sql.upper().startswith("BACKUP"):
            parts=sql.split()
            bdir=parts[1] if len(parts)>1 else "backup"
            return self.backup(bdir)

        # RESTORE
        if sql.upper().startswith("RESTORE"):
            parts=sql.split()
            bdir=parts[1] if len(parts)>1 else "backup"
            return self.restore(bdir)

        # BENCHMARK
        if sql.upper().startswith("BENCHMARK"):
            parts=sql.split()
            count=int(parts[1]) if len(parts)>1 else 1000
            res=self.benchmark_index(count=count)
            print("\nРезультаты бенчмарка индекса:")
            print(f"- Всего записей в таблице: {res['records']}")
            print(f"- Число тестовых запросов: {res['queries']}")
            print(f"- Время поиска БЕЗ индекса (линейное чтение): {res['linear_time_sec']} сек")
            print(f"- Время поиска С индексом (seek по смещению): {res['index_time_sec']} сек")
            print(f"- Ускорение: x{res['speedup']} раз!\n")
            return res

        raise ValueError(f"Неизвестная команда SQL: {sql}")

    def parse_and_run_join_sql(self, sql):
        # Парсинг запроса SELECT с JOIN
        # Пример: SELECT experiments.id, datasets.name, experiments.accuracy FROM experiments JOIN datasets ON experiments.dataset_id = datasets.id WHERE accuracy > 0.8
        m=re.match(r"^SELECT\s+(.*?)\s+FROM\s+(\w+)\s+(JOIN\s+.*)$", sql, re.IGNORECASE | re.DOTALL)
        if not m:
            raise ValueError("Неверный синтаксис SELECT с JOIN")

        cols_part=m.group(1).strip()
        base_table=m.group(2).strip()
        rest=m.group(3).strip()

        where_part=None
        if " WHERE " in rest.upper():
            w_idx=rest.upper().rfind(" WHERE ")
            where_part=rest[w_idx+7:].strip()
            rest=rest[:w_idx].strip()

        # Парсим цепочку JOIN table ON col1 = col2
        # Убираем начальный JOIN если rest начинается с него
        if rest.upper().startswith("JOIN "):
            rest=rest[5:].strip()

        join_tokens=re.split(r"\s+JOIN\s+", rest, flags=re.IGNORECASE)
        joins_info=[(base_table, None, None)]

        for token in join_tokens:
            token=token.strip()
            if not token:
                continue
            on_match=re.match(r"^(\w+)\s+ON\s+(.*?)\s*=\s*(.*?)$", token, re.IGNORECASE)
            if not on_match:
                raise ValueError(f"Не удалось разобрать JOIN: {token}")
            j_table=on_match.group(1).strip()
            col_l=on_match.group(2).strip()
            col_r=on_match.group(3).strip()
            joins_info.append((j_table, col_l, col_r))

        cols=cols_part if cols_part=="*" else [c.strip() for c in cols_part.split(",")]
        return self.multi_join(joins_info, columns=cols, where_clause=where_part)

def parse_csv_line(s):
    # Разбор строки со значениями через запятую с сохранением строк в кавычках
    res=[]
    curr=[]
    in_quote=False
    quote_char=None

    for ch in s:
        if ch in ("'", '"'):
            if not in_quote:
                in_quote=True
                quote_char=ch
                curr.append(ch)
            elif quote_char==ch:
                in_quote=False
                quote_char=None
                curr.append(ch)
            else:
                curr.append(ch)
        elif ch=="," and not in_quote:
            res.append("".join(curr).strip())
            curr=[]
        else:
            curr.append(ch)

    if curr:
        res.append("".join(curr).strip())

    cleaned=[]
    for v in res:
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            cleaned.append(v[1:-1])
        else:
            cleaned.append(v)
    return cleaned
