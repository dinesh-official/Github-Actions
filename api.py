"""
api.py — Fetch data from MS SQL Server (FI_ReferenceData)

Run: python api.py
Test: http://localhost:5000/api/tables
"""

import pyodbc
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# ═══════════════════════════════════════
# 🔧 YOUR MSSQL CONNECTION
# ═══════════════════════════════════════

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=192.168.100.244\OHVDB1;"
    "DATABASE=FI_ReferenceData;"
    "UID=ETL;"
    "PWD=ad@kUTgUw64y;"
    "TrustServerCertificate=yes;"
)


def get_connection():
    return pyodbc.connect(CONN_STR)


# ═══════════════════════════════════════
# 1. LIST ALL TABLES
# ═══════════════════════════════════════

@app.route("/api/tables", methods=["GET"])
def get_tables():
    """List all tables in the database."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cur.fetchall()]
        return jsonify({"success": True, "tables": tables, "count": len(tables)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════
# 2. GET TABLE COLUMNS (structure)
# ═══════════════════════════════════════

@app.route("/api/tables/<table_name>/columns", methods=["GET"])
def get_columns(table_name):
    """Get all columns of a specific table."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (table_name,))
        columns = []
        for row in cur.fetchall():
            columns.append({
                "column": row[0],
                "type": row[1],
                "max_length": row[2],
                "nullable": row[3]
            })
        if not columns:
            return jsonify({"success": False, "error": f"Table '{table_name}' not found"}), 404
        return jsonify({"success": True, "table": table_name, "columns": columns}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════
# 3. FETCH DATA FROM ANY TABLE
# ═══════════════════════════════════════

@app.route("/api/tables/<table_name>/data", methods=["GET"])
def get_table_data(table_name):
    """
    Fetch data from a table.
    
    Query params:
        ?limit=100        → Number of rows (default 100)
        ?offset=0         → Skip rows (for pagination)
    
    Examples:
        /api/tables/Bond_Documents/data
        /api/tables/Bond_Documents/data?limit=50
        /api/tables/Bond_Documents/data?limit=20&offset=40
    """
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    # Cap limit to prevent huge responses
    limit = min(limit, 1000)

    # Whitelist table name to prevent SQL injection
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Verify table exists
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?", (table_name,))
        if not cur.fetchone():
            return jsonify({"success": False, "error": f"Table '{table_name}' not found"}), 404

        # Fetch data with pagination
        cur.execute(f"""
            SELECT * FROM [{table_name}]
            ORDER BY (SELECT NULL)
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, limit))

        columns = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convert non-serializable types to string
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        # Get total count
        cur.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        total = cur.fetchone()[0]

        return jsonify({
            "success": True,
            "table": table_name,
            "total_rows": total,
            "limit": limit,
            "offset": offset,
            "returned": len(rows),
            "data": rows
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════
# 4. SEARCH IN A TABLE
# ═══════════════════════════════════════

@app.route("/api/tables/<table_name>/search", methods=["GET"])
def search_table(table_name):
    """
    Search for a value in a specific column.
    
    Query params:
        ?column=name      → Column to search in
        ?value=John       → Value to search for
        ?limit=50         → Max rows
    
    Examples:
        /api/tables/users/search?column=phone&value=9876543210
        /api/tables/users/search?column=full_name&value=John
    """
    column = request.args.get("column", "")
    value = request.args.get("value", "")
    limit = min(request.args.get("limit", 100, type=int), 1000)

    if not column or not value:
        return jsonify({"success": False, "error": "Both 'column' and 'value' params required"}), 400

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Verify table exists
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?", (table_name,))
        if not cur.fetchone():
            return jsonify({"success": False, "error": f"Table '{table_name}' not found"}), 404

        # Verify column exists
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
        """, (table_name, column))
        if not cur.fetchone():
            return jsonify({"success": False, "error": f"Column '{column}' not found in '{table_name}'"}), 404

        # Search (using LIKE for partial match)
        cur.execute(f"""
            SELECT TOP (?) * FROM [{table_name}]
            WHERE [{column}] LIKE ?
        """, (limit, f"%{value}%"))

        columns = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        return jsonify({
            "success": True,
            "table": table_name,
            "search_column": column,
            "search_value": value,
            "found": len(rows),
            "data": rows
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════
# 5. RUN CUSTOM SQL QUERY (READ-ONLY)
# ═══════════════════════════════════════

@app.route("/api/query", methods=["POST"])
def run_query():
    """
    Run a custom SELECT query (read-only).
    
    Request body:
    {
        "sql": "SELECT TOP 10 * FROM Bond_Documents"
    }
    """
    data = request.get_json()
    if not data or not data.get("sql"):
        return jsonify({"success": False, "error": "SQL query is required"}), 400

    sql = data["sql"].strip()

    # SECURITY: Only allow SELECT queries
    if not sql.upper().startswith("SELECT"):
        return jsonify({"success": False, "error": "Only SELECT queries are allowed"}), 403

    # Block dangerous keywords
    blocked = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "EXEC", "EXECUTE", "TRUNCATE"]
    sql_upper = sql.upper()
    for keyword in blocked:
        if keyword in sql_upper:
            return jsonify({"success": False, "error": f"'{keyword}' is not allowed"}), 403

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)

        columns = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        return jsonify({
            "success": True,
            "columns": columns,
            "rows": len(rows),
            "data": rows
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    """Test database connection."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "database": "FI_ReferenceData", "connection": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "connection": "failed", "error": str(e)}), 500


# ═══════════════════════════════════════
# RUN
# ═══════════════════════════════════════

if __name__ == "__main__":
    # Test connection on startup
    try:
        conn = get_connection()
        conn.close()
        print("✅ Connected to MSSQL: FI_ReferenceData")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

    print(f"\n🚀 API running on http://localhost:5000")
    print(f"\n📡 Endpoints:")
    print(f"   GET  /api/health                          →  Test DB connection")
    print(f"   GET  /api/tables                          →  List all tables")
    print(f"   GET  /api/tables/<name>/columns           →  Table structure")
    print(f"   GET  /api/tables/<name>/data?limit=100    →  Fetch rows")
    print(f"   GET  /api/tables/<name>/search?column=x&value=y  →  Search")
    print(f"   POST /api/query  {{\"sql\": \"SELECT...\"}}     →  Custom query\n")

    app.run(debug=True, port=5000)