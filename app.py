from datetime import date

import streamlit as st

from classifier import classify_client_message
from config import get_secret
from database import (
    add_client_alias,
    create_client,
    database_healthcheck,
    delete_client_alias,
    get_client_aliases,
    get_client_messages,
    get_clients,
    get_messages_for_client,
    save_client_message,
    update_client,
    update_message_client,
    update_message_status,
)
from gmail_client import get_gmail_service, sync_adviseur_emails


st.set_page_config(page_title="Adviseur", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px;}
        [data-testid="stMetricValue"] {font-size: 2rem;}
        .adviseur-muted {color: #9ca3af; font-size: 0.92rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def client_label(client):
    return f"{client['name']} — {client['email']}"


def client_options(clients):
    return {client_label(client): client for client in clients}


def urgency_icon(urgency):
    return {
        "CRITICAL": "🚨",
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }.get(urgency, "⚪")


def source_label(source):
    return "📧 Gmail" if source == "GMAIL" else "✍️ Manual"


def render_message_details(msg):
    st.write("**Client message**")
    st.write(msg["message"])
    st.write("**Reason**")
    st.write(msg["reason"])
    st.write("**Recommended action**")
    st.write(msg["recommended_action"])
    st.write("**Human review:**", "YES" if msg["requires_human"] else "NO")
    if msg.get("created_at"):
        st.caption(f"Received: {msg['created_at'].strftime('%d %b %Y %H:%M')}")


def page_dashboard():
    st.header("Dashboard")
    messages = get_client_messages()

    total = len(messages)
    new = sum(1 for m in messages if m["status"] == "NEW")
    in_review = sum(1 for m in messages if m["status"] == "IN REVIEW")
    high = sum(1 for m in messages if m["urgency"] in ["HIGH", "CRITICAL"])
    human = sum(1 for m in messages if m["requires_human"])

    cols = st.columns(5)
    labels = [
        ("Total", total),
        ("New", new),
        ("In review", in_review),
        ("High priority", high),
        ("Human review", human),
    ]
    for col, (label, value) in zip(cols, labels):
        with col:
            st.metric(label, value)

    st.divider()
    st.subheader("Action queue")
    action_queue = [
        m
        for m in messages
        if m["status"] != "RESOLVED"
        and (m["requires_human"] or m["urgency"] in ["HIGH", "CRITICAL"])
    ][:10]

    if not action_queue:
        st.success("No high-priority items waiting for attention.")
        return

    for msg in action_queue:
        client = msg["client_name"] or "Unknown Client"
        with st.expander(
            f"{urgency_icon(msg['urgency'])} {client} — {msg['category']} — "
            f"{msg['urgency']} — {msg['status']}"
        ):
            render_message_details(msg)


def page_inbox():
    st.header("Inbox")
    messages = get_client_messages()
    clients = get_clients()
    options = client_options(clients)

    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Status", ["ALL", "NEW", "IN REVIEW", "RESOLVED"])
    with col2:
        urgency_filter = st.selectbox("Urgency", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    with col3:
        source_filter = st.selectbox("Source", ["ALL", "GMAIL", "MANUAL"])

    filtered = messages
    if status_filter != "ALL":
        filtered = [m for m in filtered if m["status"] == status_filter]
    if urgency_filter != "ALL":
        filtered = [m for m in filtered if m["urgency"] == urgency_filter]
    if source_filter != "ALL":
        filtered = [m for m in filtered if m["source"] == source_filter]

    st.caption(f"Showing {len(filtered)} of {len(messages)} messages")
    st.divider()

    if not filtered:
        st.info("No messages match the selected filters.")
        return

    for msg in filtered:
        client_name = msg["client_name"] or "Unknown Client"
        title = (
            f"{urgency_icon(msg['urgency'])} {client_name} — {msg['category']} — "
            f"{msg['urgency']} — {source_label(msg['source'])} — {msg['status']}"
        )
        with st.expander(title):
            render_message_details(msg)

            if not msg["client_name"] and clients:
                st.divider()
                st.write("**Assign client**")
                assignment = st.selectbox(
                    "Select client",
                    ["Select client..."] + list(options.keys()),
                    key=f"assign_client_{msg['id']}",
                )
                if assignment != "Select client..." and st.button(
                    "Assign message", key=f"assign_button_{msg['id']}"
                ):
                    selected = options[assignment]
                    update_message_client(msg["id"], selected["id"])
                    st.success(f"Message assigned to {selected['name']}.")
                    st.rerun()

            st.divider()
            status_options = ["NEW", "IN REVIEW", "RESOLVED"]
            current_status = msg["status"] if msg["status"] in status_options else "NEW"
            new_status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status),
                key=f"status_{msg['id']}",
            )
            if new_status != msg["status"]:
                update_message_status(msg["id"], new_status)
                st.rerun()


def page_clients():
    st.header("Clients")

    with st.expander("➕ Add new client"):
        with st.form("create_client_form"):
            new_name = st.text_input("Client name")
            new_email = st.text_input("Primary email")
            submitted = st.form_submit_button("Create client")
            if submitted:
                if not new_name.strip() or not new_email.strip():
                    st.warning("Enter both a client name and email.")
                else:
                    client = create_client(new_name, new_email)
                    if client:
                        st.success(f"Client created: {client['name']}")
                        st.rerun()
                    else:
                        st.warning("That email is already linked to an existing client.")

    clients = get_clients()
    if not clients:
        st.info("No clients found.")
        return

    options = client_options(clients)
    selected_label = st.selectbox("Select client", list(options.keys()))
    selected = options[selected_label]

    st.subheader(selected["name"])
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**Client reference**")
        st.write(selected["client_ref"] or "—")
        st.write("**Phone**")
        st.write(selected["phone"] or "—")
    with c2:
        st.write("**Status**")
        st.write(selected["status"] or "—")
        st.write("**Risk profile**")
        st.write(selected["risk_profile"] or "—")
    with c3:
        st.write("**Primary email**")
        st.write(selected["email"])
        st.write("**Date joined**")
        st.write(selected["date_joined"] or "—")

    if selected["notes"]:
        st.info(f"📝 {selected['notes']}")

    with st.expander("✏️ Edit client details"):
        with st.form(f"edit_client_{selected['id']}"):
            phone = st.text_input("Phone", value=selected["phone"] or "")
            client_ref = st.text_input("Client reference", value=selected["client_ref"] or "")
            status_options = ["ACTIVE", "INACTIVE"]
            status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(selected["status"])
                if selected["status"] in status_options
                else 0,
            )
            risk_options = ["LOW", "MODERATE", "HIGH"]
            risk = st.selectbox(
                "Risk profile",
                risk_options,
                index=risk_options.index(selected["risk_profile"])
                if selected["risk_profile"] in risk_options
                else 0,
            )
            joined = st.date_input(
                "Date joined",
                value=selected["date_joined"] or date.today(),
            )
            notes = st.text_area("Notes", value=selected["notes"] or "")
            save = st.form_submit_button("Save client changes")
            if save:
                update_client(
                    selected["id"],
                    phone.strip(),
                    client_ref.strip(),
                    status,
                    risk,
                    joined,
                    notes.strip(),
                )
                st.success("Client updated successfully.")
                st.rerun()

    st.subheader("Email addresses")
    st.write(f"**Primary:** {selected['email']}")
    aliases = get_client_aliases(selected["id"])

    if aliases:
        st.write("**Alternate emails**")
        for alias in aliases:
            alias_col, delete_col = st.columns([6, 1])
            with alias_col:
                st.write(alias["email"])
            with delete_col:
                if st.button("Delete", key=f"delete_alias_{alias['id']}"):
                    if delete_client_alias(alias["id"]):
                        st.rerun()
    else:
        st.caption("No alternate email addresses.")

    with st.form(f"alias_form_{selected['id']}"):
        alias_email = st.text_input("Add alternate email")
        alias_submit = st.form_submit_button("Add email")
        if alias_submit:
            result = add_client_alias(selected["id"], alias_email)
            if result["status"] == "added":
                st.success(result["message"])
                st.rerun()
            elif result["status"] == "exists":
                st.warning(result["message"])
            else:
                st.error(result["message"])

    st.divider()
    st.subheader("Message history")
    history = get_messages_for_client(selected["id"])
    if not history:
        st.info("No messages recorded for this client yet.")
        return

    for msg in history:
        with st.expander(
            f"{urgency_icon(msg['urgency'])} {msg['category']} — {msg['urgency']} — "
            f"{msg['status']} — {source_label(msg['source'])}"
        ):
            render_message_details(msg)


def page_triage():
    st.header("Manual triage")
    st.caption("Paste a client message to classify and add it to the Adviseur workflow.")

    clients = get_clients()
    options = client_options(clients)
    selected_label = st.selectbox(
        "Client",
        ["Unknown / Unassigned"] + list(options.keys()),
    )
    message = st.text_area(
        "Incoming client message",
        height=220,
        placeholder="Paste a client message here...",
    )

    if st.button("Analyse message", type="primary"):
        if not message.strip():
            st.warning("Enter a client message first.")
            return

        with st.spinner("Analysing message..."):
            result = classify_client_message(message)

        client_id = None
        if selected_label != "Unknown / Unassigned":
            client_id = options[selected_label]["id"]

        save_client_message(message, result, client_id=client_id, source="MANUAL")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Category", result.category)
        with c2:
            st.metric("Urgency", result.urgency)
        with c3:
            st.metric("Human review", "YES" if result.requires_human else "NO")

        st.write("### Reason")
        st.write(result.reason)
        st.write("### Recommended action")
        st.write(result.recommended_action)

        if result.urgency == "CRITICAL":
            st.error("🚨 CRITICAL — ESCALATE IMMEDIATELY")
        elif result.urgency == "HIGH" and result.requires_human:
            st.error("⚠️ HIGH PRIORITY — SEND TO ADVISER")
        elif result.requires_human:
            st.warning("👤 HUMAN REVIEW REQUIRED")
        else:
            st.success("✅ ROUTINE — APPROVED PA WORKFLOW")


def page_gmail():
    st.header("Gmail")
    st.caption("Sync messages carrying the ADVISEUR Gmail label into the triage workflow.")

    if not get_secret("GOOGLE_TOKEN_JSON"):
        st.info(
            "Local mode uses token.json. For cloud deployment, configure GOOGLE_TOKEN_JSON "
            "in Streamlit secrets."
        )

    if st.button("📨 Sync ADVISEUR emails", type="primary"):
        try:
            with st.spinner("Checking Gmail..."):
                service = get_gmail_service()
                results = sync_adviseur_emails(service, limit=50)

            processed = sum(1 for item in results if item["status"] == "PROCESSED")
            skipped = sum(1 for item in results if item["status"] == "SKIPPED")
            st.success(
                f"Gmail sync complete — {processed} processed, "
                f"{skipped} already processed."
            )
        except Exception as error:
            st.error(f"Gmail sync failed: {error}")


def page_settings():
    st.header("Settings & health")
    st.write("**Database:**", "✅ Connected" if database_healthcheck() else "❌ Not connected")
    st.write("**OpenAI API key:**", "✅ Configured" if get_secret("OPENAI_API_KEY") else "❌ Missing")
    gmail_configured = bool(get_secret("GOOGLE_TOKEN_JSON"))
    st.write(
        "**Cloud Gmail token:**",
        "✅ Configured" if gmail_configured else "⚪ Using local token.json / not configured",
    )
    st.caption("Secret values are never displayed here.")


st.sidebar.title("Adviseur")
st.sidebar.caption("AI workflow assistant")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Inbox", "Clients", "Manual triage", "Gmail", "Settings"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("Human oversight remains required for regulated or sensitive actions.")

st.title("Adviseur")
st.caption("AI-assisted client communication triage and workflow management for financial advisers.")
st.divider()

try:
    if page == "Dashboard":
        page_dashboard()
    elif page == "Inbox":
        page_inbox()
    elif page == "Clients":
        page_clients()
    elif page == "Manual triage":
        page_triage()
    elif page == "Gmail":
        page_gmail()
    else:
        page_settings()
except Exception as error:
    st.error(f"Adviseur encountered an error: {error}")
    st.caption("Check the app configuration and database connection, then retry.")
