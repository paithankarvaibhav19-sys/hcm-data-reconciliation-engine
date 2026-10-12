import streamlit as st
import sqlite3
import pandas as pd
import io
import os
from setup_db import init_db

st.set_page_config(
    page_title="HCM Data Reconciliation Engine",
    page_icon="🔍",
    layout="wide"
)

# Ensure database exists
if not os.path.exists("hcm_audit.db"):
    init_db()

def get_connection():
    return sqlite3.connect("hcm_audit.db")

st.title("🔍 Enterprise HCM Data Reconciliation & Exception Engine")
st.markdown("""
**Domain:** Enterprise Production Support & HCM Cloud Integration  
This diagnostic dashboard identifies data divergence, unmapped organizational entities, and access compliance vulnerabilities between upstream Core HR systems and cloud ERP instances.
""")

tab_audit, tab_editor, tab_upload, tab_raw_data = st.tabs([
    "🚀 Run Exception Audit", 
    "✍️ Edit / Add Employee Data", 
    "📁 Upload Custom Files (CSV/Excel)",
    "📋 View Master Records"
])

# ---------------------------------------------------------
# TAB 1: RUN AUDIT
# ---------------------------------------------------------
with tab_audit:
    st.subheader("Automated Reconciliation Controls")
    
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        run_audit = st.button("▶ Run Full Audit", type="primary")

    if run_audit:
        conn = get_connection()
        query = """
        -- 1. Status Mismatches (Compliance & Access Risk)
        SELECT 
            s.source_emp_id AS employee_id,
            s.full_name,
            'CRITICAL' AS severity,
            'EMPLOYMENT_STATUS_MISMATCH' AS issue_category,
            'Source: ' || s.employment_status || ' | Target: ' || t.employment_status AS discrepancy_details,
            'Revoke ERP access credentials immediately to prevent unauthorized access.' AS action_required
        FROM source_hr_system s
        JOIN target_erp_employee t ON s.source_emp_id = t.target_emp_id
        WHERE s.employment_status <> t.employment_status

        UNION ALL

        -- 2. Cost Center Mismatches
        SELECT 
            s.source_emp_id,
            s.full_name,
            'MEDIUM' AS severity,
            'COST_CENTER_MISMATCH',
            'Source: ' || s.cost_center_id || ' | Target: ' || t.cost_center_id,
            'Re-map organizational assignment before next payroll run.'
        FROM source_hr_system s
        JOIN target_erp_employee t ON s.source_emp_id = t.target_emp_id
        WHERE s.cost_center_id <> t.cost_center_id

        UNION ALL

        -- 3. Delta Sync Failures (Missing in Target)
        SELECT 
            s.source_emp_id,
            s.full_name,
            'HIGH' AS severity,
            'MISSING_IN_TARGET',
            'Employee exists in HR feed but absent in target ERP',
            'Inspect interface middleware payload logs and re-trigger delta ingestion.'
        FROM source_hr_system s
        LEFT JOIN target_erp_employee t ON s.source_emp_id = t.target_emp_id
        WHERE t.target_emp_id IS NULL

        UNION ALL

        -- 4. Orphan Target Records
        SELECT 
            t.target_emp_id,
            t.full_name,
            'HIGH' AS severity,
            'ORPHAN_IN_TARGET',
            'Record exists in ERP without upstream HR master entry',
            'Audit manual user creation or ghost worker compliance anomaly.'
        FROM target_erp_employee t
        LEFT JOIN source_hr_system s ON t.target_emp_id = s.source_emp_id
        WHERE s.source_emp_id IS NULL;
        """

        df_exceptions = pd.read_sql_query(query, conn)
        conn.close()

        total_exceptions = len(df_exceptions)
        critical_count = len(df_exceptions[df_exceptions['severity'] == 'CRITICAL'])
        high_count = len(df_exceptions[df_exceptions['severity'] == 'HIGH'])
        med_count = len(df_exceptions[df_exceptions['severity'] == 'MEDIUM'])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Exceptions", total_exceptions)
        m2.metric("Critical Security Risks", critical_count, delta="Immediate Action", delta_color="inverse")
        m3.metric("Integration Failures (High)", high_count)
        m4.metric("Org Mismatches (Medium)", med_count)

        st.markdown("---")
        st.subheader("📋 Triage-Ready Exception Log")
        st.dataframe(df_exceptions, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_exceptions.to_excel(writer, index=False, sheet_name='Audit_Exceptions')
        
        st.download_button(
            label="📥 Download Audit Report (.xlsx)",
            data=buffer.getvalue(),
            file_name="HCM_Reconciliation_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ---------------------------------------------------------
# TAB 2: IN-BROWSER DATA EDITOR
# ---------------------------------------------------------
with tab_editor:
    st.subheader("Direct Data Entry & Quick Testing")
    st.info("HR users can type directly into the tables below, add new rows at the bottom, or alter statuses to test reconciliation in real time.")

    conn = get_connection()
    df_src = pd.read_sql_query("SELECT * FROM source_hr_system", conn)
    df_tgt = pd.read_sql_query("SELECT * FROM target_erp_employee", conn)
    conn.close()

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("**1. Source HR System (Upstream)**")
        edited_src = st.data_editor(df_src, num_rows="dynamic", key="editor_src", use_container_width=True)
    with col_e2:
        st.markdown("**2. Target ERP Employee (Downstream)**")
        edited_tgt = st.data_editor(df_tgt, num_rows="dynamic", key="editor_tgt", use_container_width=True)

    if st.button("💾 Save Changes to Database", type="secondary"):
        conn = get_connection()
        edited_src.to_sql("source_hr_system", conn, if_exists="replace", index=False)
        edited_tgt.to_sql("target_erp_employee", conn, if_exists="replace", index=False)
        conn.close()
        st.success("✅ Changes saved! Now switch to the 'Run Exception Audit' tab and click 'Run Full Audit' to see your new cases flagged.")

# ---------------------------------------------------------
# TAB 3: CUSTOM FILE UPLOAD (CSV / EXCEL)
# ---------------------------------------------------------
with tab_upload:
    st.subheader("Upload Enterprise File Extracts")
    st.write("Upload custom files to overwrite current tables and audit external datasets.")

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        src_file = st.file_uploader("Upload Source HR File (.csv or .xlsx)", type=["csv", "xlsx"])
    with col_u2:
        tgt_file = st.file_uploader("Upload Target ERP File (.csv or .xlsx)", type=["csv", "xlsx"])

    if st.button("📥 Load Uploaded Files into Engine"):
        if src_file is not None and tgt_file is not None:
            conn = get_connection()
            # Read Source
            df_upload_src = pd.read_csv(src_file) if src_file.name.endswith(".csv") else pd.read_excel(src_file)
            df_upload_src.to_sql("source_hr_system", conn, if_exists="replace", index=False)
            
            # Read Target
            df_upload_tgt = pd.read_csv(tgt_file) if tgt_file.name.endswith(".csv") else pd.read_excel(tgt_file)
            df_upload_tgt.to_sql("target_erp_employee", conn, if_exists="replace", index=False)
            conn.close()
            st.success("✅ Both files successfully loaded into the engine! Switch to 'Run Exception Audit' tab to analyze.")
        else:
            st.warning("Please upload both Source and Target files before loading.")

# ---------------------------------------------------------
# TAB 4: VIEW MASTER RECORDS
# ---------------------------------------------------------
with tab_raw_data:
    conn = get_connection()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Source HR Records")
        st.dataframe(pd.read_sql_query("SELECT * FROM source_hr_system", conn), use_container_width=True)
    with c2:
        st.subheader("Target ERP Records")
        st.dataframe(pd.read_sql_query("SELECT * FROM target_erp_employee", conn), use_container_width=True)
    
    st.subheader("Cost Center Master Reference")
    st.dataframe(pd.read_sql_query("SELECT * FROM cost_centers", conn), use_container_width=True)
st.download_button(
        label="📥 Download Audit Report (.xlsx)",
        data=buffer.getvalue(),
        file_name="HCM_Reconciliation_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )