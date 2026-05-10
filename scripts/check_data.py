import pymysql
import json

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root123456",
    "database": "fuzzing_db",
    "charset": "utf8mb4"
}

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

sql = """
    SELECT case_uid, error_message, parameters 
    FROM test_case_metadata 
    WHERE error_message LIKE '%Segmentation Fault%'
"""
cursor.execute(sql)
rows = cursor.fetchall()

print(f"Found {len(rows)} cases with 'Segmentation Fault':")
for row in rows:
    params = json.loads(row['parameters'])
    operators = params.get('model_structure', {}).get('operators', [])
    has_conv2d = "Conv2d" in operators
    print(f"- {row['case_uid']}: Has Conv2d={has_conv2d}, Operators={operators}")

conn.close()
