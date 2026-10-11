import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "ktff.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]

# 1. Standard / General Schema JSON
general_schema = {
    "database": "ktff.db",
    "tables": []
}

# 2. Azimutt Schema JSON format
azimutt_tables = []
azimutt_relations = []

for t in tables:
    cols_info = cur.execute(f"PRAGMA table_info({t})").fetchall()
    fks_info = cur.execute(f"PRAGMA foreign_key_list({t})").fetchall()
    
    t_obj = {
        "name": t,
        "columns": [],
        "primary_keys": [],
        "foreign_keys": []
    }
    
    az_cols = []
    az_pk_cols = []
    
    for c in cols_info:
        col_name = c[1]
        col_type = c[2]
        is_pk = bool(c[5])
        not_null = bool(c[3])
        
        t_obj["columns"].append({
            "name": col_name,
            "type": col_type,
            "is_primary_key": is_pk,
            "nullable": not not_null
        })
        
        az_cols.append({
            "name": col_name,
            "type": col_type,
            "nullable": not not_null
        })
        
        if is_pk:
            t_obj["primary_keys"].append(col_name)
            az_pk_cols.append(col_name)
            
    for fk in fks_info:
        t_obj["foreign_keys"].append({
            "column": fk[3],
            "ref_table": fk[2],
            "ref_column": fk[4],
            "on_delete": fk[6]
        })
        
        azimutt_relations.append({
            "name": f"fk_{t}_{fk[3]}_{fk[2]}",
            "src": {"schema": "main", "table": t, "column": fk[3]},
            "ref": {"schema": "main", "table": fk[2], "column": fk[4]}
        })
        
    general_schema["tables"].append(t_obj)
    
    az_table = {
        "schema": "main",
        "table": t,
        "columns": az_cols
    }
    if az_pk_cols:
        az_table["primaryKey"] = {"name": f"pk_{t}", "columns": az_pk_cols}
    azimutt_tables.append(az_table)

azimutt_json = {
    "tables": azimutt_tables,
    "relations": azimutt_relations
}

path_general = os.path.join(BASE_DIR, "ktff_schema.json")
path_azimutt = os.path.join(BASE_DIR, "ktff_azimutt.json")
path_sql = os.path.join(BASE_DIR, "ktff_schema.sql")

with open(path_general, "w", encoding="utf-8") as f:
    json.dump(general_schema, f, indent=2, ensure_ascii=False)

with open(path_azimutt, "w", encoding="utf-8") as f:
    json.dump(azimutt_json, f, indent=2, ensure_ascii=False)

sql_ddl = []
for r in cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
    sql_ddl.append(r[0] + ";")

with open(path_sql, "w", encoding="utf-8") as f:
    f.write("\n\n".join(sql_ddl))

conn.close()
print("Saved successfully:")
print("1.", path_general)
print("2.", path_azimutt)
print("3.", path_sql)
