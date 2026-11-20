import streamlit as st
import json
import sqlite3
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(
    page_title="AI Agent & BigQuery Data Reconciliation QA Dashboard",
    page_icon="🧪",
    layout="wide"
)

@st.cache_resource
def init_qa_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE source_api_events (
            event_id TEXT PRIMARY KEY,
            user_prompt TEXT,
            expected_category TEXT,
            ingestion_ts TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE bigquery_agent_outputs (
            event_id TEXT,
            ai_category TEXT,
            confidence_score REAL,
            summary_text TEXT,
            processed_ts TEXT
        )
    """)

    source_rows = [
        ("EVT-501", "My billing invoice has an extra charge", "Billing", "2026-11-19 02:00:05"),
        ("EVT-502", "How do I reset my cloud console password?", "Account Support", "2026-11-19 02:00:12"),
        ("EVT-503", "API endpoint returns 504 timeout error", "Technical Bug", "2026-11-19 02:00:18"),
        ("EVT-504", "Requesting upgrade to enterprise tier", "Sales", "2026-11-19 02:00:25"),
        ("EVT-505", "Exporting quarterly CSV report fails", "Technical Bug", "2026-11-19 02:00:31"),
    ]

    bq_rows = [
        ("EVT-501", "Billing", 0.96, "Customer reported unexpected charge on billing invoice.", "2026-11-19 02:00:08"),
        ("EVT-502", "Account Support", 0.94, "User requested password reset instructions.", "2026-11-19 02:00:15"),
        ("EVT-503", "Technical Bug", 0.98, "API gateway timeout error 504 reported.", "2026-11-19 02:00:21"),
        ("EVT-503", "Technical Bug", 0.98, "API gateway timeout error 504 reported.", "2026-11-19 02:00:22"),
        ("EVT-505", None, 0.41, "", "2026-11-19 02:00:35"),
    ]

    cursor.executemany("INSERT INTO source_api_events VALUES (?, ?, ?, ?)", source_rows)
    cursor.executemany("INSERT INTO bigquery_agent_outputs VALUES (?, ?, ?, ?, ?)", bq_rows)
    conn.commit()
    return conn

conn = init_qa_db()

st.title("🧪 AI Agent & BigQuery Data Reconciliation QA Dashboard")
st.markdown(
    "**GCP & Agentic AI QA Sandbox** | End-to-End (E2E) Workflow Validation, Non-Deterministic AI Output Checks, "
    "BigQuery SQL Data Reconciliation, and Human-in-the-Loop Test Case Review *(Mock Data)*."
)
st.divider()

tab1, tab2, tab3 = st.tabs([
    "1️⃣ Agentic AI & Cloud Run API Validator",
    "2️⃣ BigQuery SQL Data Reconciliation",
    "3️⃣ Human-in-the-Loop AI Test Case Review"
])

with tab1:
    st.subheader("Cloud Run AI Agent Endpoint & Output Validator (E2E Check)")
    st.write("Simulate validating a JSON response from an Agentic AI workflow running on GCP Cloud Run.")

    valid_ai_json = json.dumps({
        "event_id": "EVT-601",
        "agent_model": "gemini-pro-agent",
        "workflow_status": "COMPLETED",
        "latency_ms": 840,
        "output": {
            "category": "Technical Bug",
            "confidence": 0.95,
            "summary": "User experienced a Cloud Run timeout when triggering batch job.",
            "hallucination_flag": False
        }
    }, indent=2)

    bad_ai_json = json.dumps({
        "event_id": "EVT-602",
        "agent_model": "gemini-pro-agent",
        "workflow_status": "COMPLETED",
        "latency_ms": 4850,
        "output": {
            "category": "Unknown_Category_99",
            "confidence": 0.32,
            "summary": "",
            "hallucination_flag": True
        }
    }, indent=2)

    c1, c2, _ = st.columns(3)
    if c1.button("Load Passing Agent Response"):
        st.session_state["ai_json"] = valid_ai_json
    if c2.button("Load Failing / Low-Confidence Response"):
        st.session_state["ai_json"] = bad_ai_json

    json_input = st.text_area(
        "Cloud Run JSON Response Payload:",
        value=st.session_state.get("ai_json", valid_ai_json),
        height=240
    )

    if st.button("▶️ Run Automated QA Assertions", type="primary"):
        try:
            data = json.loads(json_input)
            issues = []

            required_top = ["event_id", "workflow_status", "latency_ms", "output"]
            for key in required_top:
                if key not in data:
                    issues.append(f"Missing top-level field: `{key}`")

            out = data.get("output", {})
            allowed_categories = ["Billing", "Account Support", "Technical Bug", "Sales"]
            if out.get("category") not in allowed_categories:
                issues.append(f"Invalid category `{out.get('category')}` (Expected one of {allowed_categories})")

            if out.get("confidence", 0) < 0.75:
                issues.append(f"Confidence score `{out.get('confidence')}` is below QA threshold (0.75)")

            if not str(out.get("summary", "")).strip():
                issues.append("Empty AI-generated `summary` field (Null/Blank output defect)")

            if data.get("latency_ms", 0) > 3000:
                issues.append(f"SLA Latency Breach: `{data.get('latency_ms')}ms` exceeds 3000ms threshold")

            if out.get("hallucination_flag") is True:
                issues.append("Grounding Check Failed: `hallucination_flag` is True")

            if not issues:
                st.success("✅ **E2E QA PASSED:** JSON schema, allowed categories, confidence threshold, and latency SLA all passed.")
            else:
                st.error(f"❌ **E2E QA FAILED ({len(issues)} Defects Found):**")
                for iss in issues:
                    st.write(f"- {iss}")
                st.info("**Root Cause Note:** Log trace in GCP Cloud Logging and flag prompt/schema version for regression.")
        except json.JSONDecodeError as e:
            st.error(f"❌ **Invalid JSON Format:** {e}")

with tab2:
    st.subheader("BigQuery Dataset Reconciliation & Anomaly Detection")
    st.write("Compare incoming Cloud Scheduler/API events (`source_api_events`) against processed AI outputs (`bigquery_agent_outputs`).")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Source Table (`source_api_events`)**")
        df_src = pd.read_sql_query("SELECT * FROM source_api_events", conn)
        st.dataframe(df_src, use_container_width=True, hide_index=True)

    with col_t2:
        st.markdown("**Destination Table (`bigquery_agent_outputs`)**")
        df_bq = pd.read_sql_query("SELECT * FROM bigquery_agent_outputs", conn)
        st.dataframe(df_bq, use_container_width=True, hide_index=True)

    st.divider()
    if st.button("🔍 Run SQL Data Integrity & Reconciliation Checks", type="primary"):
        m1, m2, m3 = st.columns(3)

        missing_df = pd.read_sql_query("""
            SELECT s.event_id, s.expected_category, s.ingestion_ts
            FROM source_api_events s
            LEFT JOIN bigquery_agent_outputs b ON s.event_id = b.event_id
            WHERE b.event_id IS NULL
        """, conn)

        dup_df = pd.read_sql_query("""
            SELECT event_id, COUNT(*) AS record_count
            FROM bigquery_agent_outputs
            GROUP BY event_id
            HAVING COUNT(*) > 1
        """, conn)

        null_df = pd.read_sql_query("""
            SELECT event_id, ai_category, confidence_score, summary_text
            FROM bigquery_agent_outputs
            WHERE ai_category IS NULL OR TRIM(summary_text) = ''
        """, conn)

        m1.metric("Missing Records (Dropped)", len(missing_df), delta="FAIL" if len(missing_df) > 0 else "PASS", delta_color="inverse")
        m2.metric("Duplicate Records", len(dup_df), delta="FAIL" if len(dup_df) > 0 else "PASS", delta_color="inverse")
        m3.metric("Null / Empty AI Outputs", len(null_df), delta="FAIL" if len(null_df) > 0 else "PASS", delta_color="inverse")

        if not missing_df.empty:
            st.warning("⚠️ **Missing Record Detected (EVT-504 dropped between Cloud Run and BigQuery):**")
            st.dataframe(missing_df, use_container_width=True, hide_index=True)

        if not dup_df.empty:
            st.warning("⚠️ **Duplicate Record Detected (EVT-503 inserted twice by retry trigger):**")
            st.dataframe(dup_df, use_container_width=True, hide_index=True)

        if not null_df.empty:
            st.warning("⚠️ **Null / Incomplete AI Output Detected (EVT-505 missing category and summary):**")
            st.dataframe(null_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Human-in-the-Loop (HITL) AI Test Case Review")
    st.write("Review AI-generated test cases, validate edge-case coverage, approve or reject items, and export the final QA test plan.")

    if "tc_df" not in st.session_state:
        st.session_state["tc_df"] = pd.DataFrame([
            {"Test_ID": "TC-01", "Scenario": "Valid JSON payload triggers Cloud Run agent and writes to BigQuery", "Type": "Positive / E2E", "AI_Generated": "Yes", "Human_Review_Status": "Approved"},
            {"Test_ID": "TC-02", "Scenario": "Cloud Scheduler retries job without creating duplicate BigQuery rows", "Type": "Data Integrity", "AI_Generated": "Yes", "Human_Review_Status": "Approved"},
            {"Test_ID": "TC-03", "Scenario": "Empty prompt string returns HTTP 400 instead of hallucinated summary", "Type": "Negative / Edge Case", "AI_Generated": "Yes", "Human_Review_Status": "Approved"},
            {"Test_ID": "TC-04", "Scenario": "Agent deletes production BigQuery dataset on timeout", "Type": "Invalid AI Suggestion", "AI_Generated": "Yes", "Human_Review_Status": "Rejected - Out of Scope"},
            {"Test_ID": "TC-05", "Scenario": "Multilingual input (Spanish/English) preserves UTF-8 encoding in BigQuery", "Type": "Edge Case", "AI_Generated": "Yes", "Human_Review_Status": "Needs Refinement"},
        ])

    edited_df = st.data_editor(
        st.session_state["tc_df"],
        column_config={
            "Human_Review_Status": st.column_config.SelectboxColumn(
                "Human Review Decision",
                options=["Approved", "Needs Refinement", "Rejected - Out of Scope"],
                required=True
            )
        },
        use_container_width=True,
        hide_index=True
    )

    csv_export = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Reviewed QA Test Plan (CSV)",
        data=csv_export,
        file_name=f"AI_GCP_QA_Test_Plan_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
