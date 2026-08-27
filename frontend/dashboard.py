import os
import sys
import json
import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import db
import merchant
from agent import run_agent
from demo_scenarios import run_all_scenarios
from seed import seed_database

st.set_page_config(
    page_title="Bounded Agentic Checkout",
    page_icon="💳",
    layout="wide",
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 1.25rem;
    }
    .badge-active {
        background-color: #10b981;
        color: white;
        padding: 5px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-revoked {
        background-color: #ef4444;
        color: white;
        padding: 5px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .card-container {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💳 Bounded Agentic Checkout</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Autonomous AI buyer agent operating under cryptographically bounded spending mandates and Razorpay test-mode API.</div>', unsafe_allow_html=True)

mandates = db.get_all_mandates()
if not mandates:
    seed_database()
    mandates = db.get_all_mandates()

mandate = mandates[0]
mandate_id = mandate["id"]
is_revoked = bool(mandate["revoked"])
per_txn_cap_inr = mandate["per_txn_cap_paise"] / 100.0
total_cap_inr = mandate["total_cap_paise"] / 100.0
spent_inr = mandate["spent_paise"] / 100.0
remaining_inr = max(0.0, total_cap_inr - spent_inr)
spent_ratio = min(1.0, spent_inr / total_cap_inr) if total_cap_inr > 0 else 0.0
expiry_formatted = mandate["expiry"].replace("T", " ")[:19] + " UTC"
category_name = mandate["category"].title()

with st.container():
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.caption("MANDATE STATUS")
        if is_revoked:
            st.markdown('<span class="badge-revoked">🔴 REVOKED</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-active">🟢 ACTIVE</span>', unsafe_allow_html=True)
    with c2:
        st.caption("CATEGORY")
        st.subheader(f"🛒 {category_name}")
    with c3:
        st.caption("PER-TXN CAP")
        st.subheader(f"₹{per_txn_cap_inr:,.2f}")
    with c4:
        st.caption("TOTAL SPENDING CAP")
        st.subheader(f"₹{total_cap_inr:,.2f}")
    with c5:
        st.caption("AMOUNT SPENT")
        st.subheader(f"₹{spent_inr:,.2f}")
    with c6:
        st.caption("AMOUNT REMAINING")
        st.subheader(f"₹{remaining_inr:,.2f}")

st.progress(spent_ratio, text=f"Budget Utilization: ₹{spent_inr:,.2f} of ₹{total_cap_inr:,.2f} ({spent_ratio * 100:.1f}%)")
st.caption(f"Mandate ID: `{mandate_id}` | Agent: `{mandate['agent_id']}` | Merchant: `{mandate['merchant_id']}` | Expiry: **{expiry_formatted}**")

st.divider()

audit_logs = db.get_audit_logs()
total_attempts = len(audit_logs)
approved_count = sum(1 for log in audit_logs if log["approved"] == 1)
blocked_count = total_attempts - approved_count
total_transacted_paise = sum(log["attempted_amount_paise"] for log in audit_logs if log["approved"] == 1)
total_transacted_inr = total_transacted_paise / 100.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Attempts", total_attempts)
m2.metric("Approved Orders", approved_count)
m3.metric("Blocked Attempts", blocked_count)
m4.metric("Total Transacted", f"₹{total_transacted_inr:,.2f}")

st.divider()

tab_audit, tab_agent, tab_catalog, tab_orders = st.tabs([
    "🔍 Live Audit Trail",
    "🤖 AI Buyer Agent Studio",
    "🛒 Merchant Catalog",
    "📦 Razorpay Orders"
])

with tab_audit:
    st.subheader("Real-time Checkout Audit Log")
    if audit_logs:
        rows = []
        for log in audit_logs:
            amt_inr = log["attempted_amount_paise"] / 100.0
            is_app = bool(log["approved"])
            status_label = "✅ Approved" if is_app else "❌ Blocked"
            raw_ts = log["timestamp"]
            ts_clean = raw_ts.replace("T", " ")[:19] if "T" in raw_ts else raw_ts

            rows.append({
                "ID": log["id"],
                "Timestamp": ts_clean,
                "Agent": log["agent_id"],
                "Amount": f"₹{amt_inr:,.2f}",
                "Status": status_label,
                "Reason": log["reason"],
                "Razorpay Order ID": log["razorpay_order_id"] or "—",
            })

        df_audit = pd.DataFrame(rows)
        st.dataframe(df_audit, width=1200, hide_index=True)

        with st.expander("🔎 Inspect Audit Record Payload & Items Breakdown"):
            selected_log_id = st.selectbox("Select Audit Log ID to inspect", [log["id"] for log in audit_logs])
            selected_log = next(l for l in audit_logs if l["id"] == selected_log_id)
            
            det_col1, det_col2 = st.columns(2)
            with det_col1:
                st.write("**Attempt Details:**")
                st.json({
                    "id": selected_log["id"],
                    "timestamp": selected_log["timestamp"],
                    "mandate_id": selected_log["mandate_id"],
                    "agent_id": selected_log["agent_id"],
                    "attempted_amount_inr": selected_log["attempted_amount_paise"] / 100.0,
                    "approved": bool(selected_log["approved"]),
                    "reason": selected_log["reason"],
                    "razorpay_order_id": selected_log["razorpay_order_id"]
                })
            with det_col2:
                st.write("**Items JSON Breakdown:**")
                try:
                    items_parsed = json.loads(selected_log["items_json"])
                    st.json(items_parsed)
                except Exception:
                    st.text(selected_log["items_json"])
    else:
        st.info("No audit logs recorded yet. Run a purchase scenario or seed script.")

with tab_agent:
    st.subheader("Test Buyer Agent Live")
    st.markdown("Give instructions to the autonomous AI buyer agent. It will autonomously inspect the catalog, evaluate your spending mandate, attempt checkout via Razorpay, and adapt if limits are breached.")

    preset_col1, preset_col2, preset_col3 = st.columns(3)
    user_goal = ""
    with preset_col1:
        if st.button("🛒 Preset: Buy Atta & Cooking Oil (Within Cap)", use_container_width=True):
            user_goal = "buy 1 bag of Atta and 1 bottle of Sunflower Oil"
    with preset_col2:
        if st.button("⚡ Preset: Reorder Usual Groceries", use_container_width=True):
            user_goal = "reorder my usual groceries, staying within budget"
    with preset_col3:
        if st.button("🚨 Preset: Buy Bulk Groceries (Cap Breach Test)", use_container_width=True):
            user_goal = "buy 2 bags of Atta, 2 bottles of Oil, and Basmati Rice"

    agent_input = st.text_input("Enter goal for Buyer Agent:", value=user_goal or "reorder my usual groceries, staying within budget")

    if st.button("🚀 Run Buyer Agent", type="primary"):
        with st.spinner("AI Buyer Agent is reasoning, browsing catalog, and checking mandate bounds..."):
            agent_result = run_agent(mandate_id=mandate_id, goal=agent_input)

        st.success(f"Agent Execution Finished (Status: {agent_result.get('status')})")
        st.caption(f"Model used: `{agent_result.get('model_used')}`")
        
        st.markdown("### 💬 Agent Response")
        final_answer = agent_result.get("final_answer", "")
        st.info(final_answer)

        with st.expander("🛠️ View Agent Tool Calls & Reasoning Trace"):
            st.json(agent_result.get("messages", []))

        st.rerun()

with tab_catalog:
    st.subheader("Merchant Catalog & Instant Checkout Test")
    catalog_items = merchant.get_catalog()
    if catalog_items:
        cat_df = pd.DataFrame([
            {
                "Item ID": item["id"],
                "Product Name": item["name"],
                "Category": item["category"].title(),
                "Price": f"₹{item['price_paise'] / 100:.2f}",
                "In Stock": item["stock"],
            }
            for item in catalog_items
        ])
        st.dataframe(cat_df, width=1200, hide_index=True)

        st.markdown("#### Direct Cart Checkout Test")
        selected_item_ids = st.multiselect(
            "Select items to purchase directly under active mandate:",
            options=[item["id"] for item in catalog_items],
            format_func=lambda x: next(f"{i['name']} (₹{i['price_paise']/100:.2f})" for i in catalog_items if i["id"] == x),
            default=["item_groc_03", "item_groc_04"]
        )

        if st.button("🛍️ Checkout Selected Items"):
            if selected_item_ids:
                with st.spinner("Processing checkout through mandate guardrails..."):
                    chk_res = merchant.attempt_checkout(mandate_id=mandate_id, item_ids=selected_item_ids)
                if chk_res["approved"]:
                    st.success(f"Order Approved & Placed! Razorpay Order ID: `{chk_res['razorpay_order_id']}` | Amount: ₹{chk_res['amount_paise']/100:.2f}")
                else:
                    st.error(f"Order Blocked by Mandate! Reason: {chk_res['reason']} | Attempted: ₹{chk_res['amount_paise']/100:.2f}")
                st.rerun()
            else:
                st.warning("Please select at least one item.")
    else:
        st.info("Catalog is empty.")

with tab_orders:
    st.subheader("Razorpay Test Orders")
    all_orders = db.get_orders()
    if all_orders:
        orders_df = pd.DataFrame([
            {
                "Order ID": o["id"],
                "Mandate ID": o["mandate_id"],
                "Razorpay Order ID": o["razorpay_order_id"],
                "Amount": f"₹{o['amount_paise'] / 100:.2f}",
                "Status": o["status"],
                "Created At": o["created_at"][:19].replace("T", " ")
            }
            for o in all_orders
        ])
        st.dataframe(orders_df, width=1200, hide_index=True)
    else:
        st.info("No orders recorded in the local database yet.")

# -----------------------------------------------------------------------------
# Sidebar Controls
# -----------------------------------------------------------------------------
st.sidebar.title("⚡ Mandate Controls")
st.sidebar.markdown("Test live fail-safes and mandate state transitions on demand.")

if not is_revoked:
    if st.sidebar.button("🚨 Revoke Mandate Now", type="primary", use_container_width=True):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE mandates SET revoked = 1 WHERE id = ?", (mandate_id,))
        conn.commit()
        conn.close()
        st.sidebar.warning("Mandate revoked!")
        st.rerun()
else:
    if st.sidebar.button("🟢 Reactivate Mandate", use_container_width=True):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE mandates SET revoked = 0 WHERE id = ?", (mandate_id,))
        conn.commit()
        conn.close()
        st.sidebar.success("Mandate reactivated!")
        st.rerun()

if st.sidebar.button("🔄 Reset Spend to ₹0", use_container_width=True):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mandates SET spent_paise = 0 WHERE id = ?", (mandate_id,))
    conn.commit()
    conn.close()
    st.sidebar.success("Mandate spent reset to ₹0!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🎬 Demo Scenarios Runner")
if st.sidebar.button("▶️ Run 5 Demo Scenarios", use_container_width=True):
    with st.spinner("Running 5 demo checkout scenarios..."):
        run_all_scenarios()
    st.sidebar.success("Demo scenarios completed!")
    st.rerun()

if st.sidebar.button("🌱 Reseed Entire DB", use_container_width=True):
    seed_database()
    st.sidebar.success("Database reseeded successfully!")
    st.rerun()
