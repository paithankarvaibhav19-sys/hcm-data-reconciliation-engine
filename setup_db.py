import sqlite3

def init_db(db_name="hcm_audit.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Drop existing tables to start fresh
    cursor.executescript("""
    DROP TABLE IF EXISTS target_erp_employee;
    DROP TABLE IF EXISTS source_hr_system;
    DROP TABLE IF EXISTS cost_centers;

    -- Master reference: Cost Centers
    CREATE TABLE cost_centers (
        cost_center_id TEXT PRIMARY KEY,
        department_name TEXT,
        is_active INTEGER DEFAULT 1
    );

    -- Table 1: Source HR records (Legacy / Upstream)
    CREATE TABLE source_hr_system (
        source_emp_id TEXT PRIMARY KEY,
        national_id TEXT,
        full_name TEXT,
        email TEXT,
        cost_center_id TEXT,
        employment_status TEXT,
        termination_date TEXT
    );

    -- Table 2: Target ERP records (Cloud Downstream)
    CREATE TABLE target_erp_employee (
        target_emp_id TEXT PRIMARY KEY,
        national_id TEXT,
        full_name TEXT,
        email TEXT,
        cost_center_id TEXT,
        employment_status TEXT,
        sync_status TEXT DEFAULT 'Synced'
    );
    """)

    # 1. Seed Cost Centers
    cost_centers = [
        ('CC_100', 'HR Operations', 1),
        ('CC_200', 'Finance & Payroll', 1),
        ('CC_300', 'Engineering', 1),
        ('CC_999', 'Deprecated Operations', 0)
    ]
    cursor.executemany("INSERT INTO cost_centers VALUES (?, ?, ?);", cost_centers)

    # 2. Seed Source HR Records (Contains deliberate test anomalies)
    source_records = [
        ('EMP001', 'NID-1001', 'Arun Kumar', 'arun.k@company.com', 'CC_100', 'Active', None),
        ('EMP002', 'NID-1002', 'Neha Sharma', 'neha.s@company.com', 'CC_200', 'Terminated', '2026-03-31'),
        ('EMP003', 'NID-1003', 'Rohan Verma', 'rohan.v@company.com', 'CC_888', 'Active', None),
        ('EMP004', 'NID-1004', 'Sita Patel', None, 'CC_300', 'Active', None),
        ('EMP005', 'NID-1005', 'Amit Singh', 'amit.s@company.com', 'CC_100', 'Active', None),
        ('EMP006', 'NID-1006', 'Kiran Das', 'kiran.d@company.com', 'CC_200', 'Active', None),
        ('EMP007', 'NID-1007', 'Pooja Nair', 'pooja.n@company.com', 'CC_999', 'Active', None)
    ]
    cursor.executemany("INSERT INTO source_hr_system VALUES (?, ?, ?, ?, ?, ?, ?);", source_records)

    # 3. Seed Target ERP Records
    target_records = [
        ('EMP001', 'NID-1001', 'Arun Kumar', 'arun.k@company.com', 'CC_100', 'Active', 'Synced'),
        ('EMP002', 'NID-1002', 'Neha Sharma', 'neha.s@company.com', 'CC_200', 'Active', 'Synced'), # Status mismatch
        ('EMP004', 'NID-1004', 'Sita Patel', None, 'CC_300', 'Active', 'Synced'),
        ('EMP005', 'NID-1005', 'Amit Singh', 'amit.s@company.com', 'CC_200', 'Active', 'Synced'), # Cost center mismatch
        ('EMP999', 'NID-9999', 'Ghost Record', 'ghost@company.com', 'CC_300', 'Active', 'Synced') # Orphan target record
    ]
    cursor.executemany("INSERT INTO target_erp_employee VALUES (?, ?, ?, ?, ?, ?, ?);", target_records)

    conn.commit()
    conn.close()
    print("Database initialized and seed data successfully written to hcm_audit.db")

if __name__ == "__main__":
    init_db()