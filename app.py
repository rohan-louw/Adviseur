import streamlit as st
from classifier import classify_client_message
from database import (
    save_client_message,
    get_client_messages,
    update_message_status,
    get_client_by_email,
    create_client,
    get_clients,
    get_messages_for_client,
    update_client,
)


st.set_page_config(
    page_title="AI Practice Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("AI Practice Assistant")
st.caption("Client communication triage for a financial advisory practice")

st.divider()

with st.expander("➕ Add new client"):
    new_client_name = st.text_input(
        "Client name",
        key="new_client_name"
    )

    new_client_email = st.text_input(
        "Client email",
        key="new_client_email"
    )

    if st.button("Create client"):
        if not new_client_name.strip() or not new_client_email.strip():
            st.warning("Enter both a client name and email.")

        else:
            client = create_client(
                new_client_name.strip(),
                new_client_email.strip().lower()
            )

            if client:
                st.success(
                    f"Client created: {client['name']} ({client['email']})"
                )
            else:
                st.warning("A client with this email already exists.")

with st.expander("👥 Client Directory"):
    clients = get_clients()

    if not clients:
        st.info("No clients found.")

    else:
        for client in clients:
            st.write(f"**{client['name']}**")
            st.caption(client["email"])

clients = get_clients()

client_options = {
    client["name"]: client
    for client in clients
}

st.subheader("Client Profile")

clients = get_clients()

if clients:

    client_options = {
        client["name"]: client
        for client in clients
    }

    selected_profile_name = st.selectbox(
        "Select client profile",
        options=list(client_options.keys()),
        key="profile_client"
    )

    selected_profile = client_options[selected_profile_name]

    st.markdown(f"### {selected_profile['name']}")

    col1, col2, col3 = st.columns(3)

    with col1:
            st.write("**Client Reference**")
            st.write(selected_profile["client_ref"] or "—")

            st.write("**Phone**")
            st.write(selected_profile["phone"] or "—")

    with col2:
            st.write("**Status**")
            st.write(selected_profile["status"] or "—")

            st.write("**Risk Profile**")
            st.write(selected_profile["risk_profile"] or "—")

    with col3:
            st.write("**Email**")
            st.write(selected_profile["email"])

            st.write("**Date Joined**")
            st.write(selected_profile["date_joined"] or "—")

    if selected_profile["notes"]:
            st.info(f"📝 {selected_profile['notes']}")

    with st.expander("✏️ Edit client details"):

        edit_phone = st.text_input(
        "Phone",
        value=selected_profile["phone"] or "",
        key=f"edit_phone_{selected_profile['id']}"
    )

    edit_client_ref = st.text_input(
        "Client reference",
        value=selected_profile["client_ref"] or "",
        key=f"edit_client_ref_{selected_profile['id']}"
    )

    edit_status = st.selectbox(
        "Status",
        ["ACTIVE", "INACTIVE"],
        index=0 if selected_profile["status"] == "ACTIVE" else 1,
        key=f"edit_status_{selected_profile['id']}"
    )

    risk_options = ["LOW", "MODERATE", "HIGH"]

    current_risk = selected_profile["risk_profile"]

    risk_index = (
        risk_options.index(current_risk)
        if current_risk in risk_options
        else 0
    )

    edit_risk_profile = st.selectbox(
        "Risk profile",
        risk_options,
        index=risk_index,
        key=f"edit_risk_profile_{selected_profile['id']}"
    )

    edit_date_joined = st.date_input(
        "Date joined",
        value=selected_profile["date_joined"],
        key=f"edit_date_joined_{selected_profile['id']}"
    )

    edit_notes = st.text_area(
        "Notes",
        value=selected_profile["notes"] or "",
        key=f"edit_notes_{selected_profile['id']}"
    )

    if st.button("Save client changes"):

        update_client(
            selected_profile["id"],
            edit_phone.strip(),
            edit_client_ref.strip(),
            edit_status,
            edit_risk_profile,
            edit_date_joined,
            edit_notes.strip(),
        )

        st.success("Client updated successfully.")
        st.rerun()

    client_history = get_messages_for_client(
        selected_profile["id"]
    )

    st.markdown("#### Message History")

    if client_history:

        for msg in client_history:

            with st.expander(
                f"{msg['category']} — {msg['urgency']} — {msg['status']}"
            ):
                st.write("**Message**")
                st.write(msg["message"])

                st.write("**AI Reason**")
                st.write(msg["reason"])

                st.write("**Recommended Action**")
                st.write(msg["recommended_action"])

                st.write(
                    f"**Human review:** "
                    f"{'Yes' if msg['requires_human'] else 'No'}"
                )

                st.caption(
                    f"Received: {msg['created_at']}"
                )

    else:
        st.info("No messages recorded for this client yet.")

    st.divider()

    selected_client_name = st.selectbox(
        "Client",
        options=["Unknown / Unassigned"] + list(client_options.keys())
    )

    message = st.text_area(
        "Incoming client message",
        height=150,
        placeholder="Paste a client message here..."
    )

if st.button("Analyse message", type="primary"):

    if not message.strip():
        st.warning("Enter a client message first.")

    else:
        with st.spinner("Analysing message..."):
            result = classify_client_message(message)

        if selected_client_name == "Unknown / Unassigned":
            client_id = None
        else:
            selected_client = client_options[selected_client_name]
            client_id = selected_client["id"]

        save_client_message(
            message,
            result,
            client_id=client_id
            )   

        st.subheader("Triage Result")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Category", result.category)

        with col2:
            st.metric("Urgency", result.urgency)

        with col3:
            st.metric(
                "Human Required",
                "YES" if result.requires_human else "NO"
            )

        st.divider()

        st.write("### Reason")
        st.write(result.reason)

        st.write("### Recommended Action")
        st.write(result.recommended_action)

        st.divider()

        if result.urgency == "CRITICAL":
            st.error("🚨 CRITICAL — ESCALATE IMMEDIATELY")

        elif result.urgency == "HIGH" and result.requires_human:
            st.error("⚠️ HIGH PRIORITY — SEND TO ADVISER")

        elif result.requires_human:
            st.warning("👤 HUMAN REVIEW REQUIRED")

        else:
            st.success("✅ ROUTINE — APPROVED PA WORKFLOW")

            st.divider()

st.header("Advisor Inbox")

messages = get_client_messages()

total_messages = len(messages)

new_messages = sum(
    1 for msg in messages
    if msg["status"] == "NEW"
)

in_review = sum(
    1 for msg in messages
    if msg["status"] == "IN REVIEW"
)

human_required = sum(
    1 for msg in messages
    if msg["requires_human"]
)

high_priority = sum(
    1 for msg in messages
    if msg["urgency"] in ["HIGH", "CRITICAL"]
)

st.subheader("Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Messages", total_messages)

with col2:
    st.metric("New", new_messages)

with col3:
    st.metric("High Priority", high_priority)

with col4:
    st.metric("Human Review", human_required)

st.divider()

st.subheader("Inbox Filters")

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    status_filter = st.selectbox(
        "Status",
        ["ALL", "NEW", "IN REVIEW", "RESOLVED"]
    )

with filter_col2:
    urgency_filter = st.selectbox(
        "Urgency",
        ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
    )

filtered_messages = messages

if status_filter != "ALL":
    filtered_messages = [
        msg for msg in filtered_messages
        if msg["status"] == status_filter
    ]

if urgency_filter != "ALL":
    filtered_messages = [
        msg for msg in filtered_messages
        if msg["urgency"] == urgency_filter
    ]

st.divider()

if not messages:
    st.info("No client messages yet.")

else:
    for msg in filtered_messages:

        if msg["urgency"] == "CRITICAL":
            icon = "🚨"
        elif msg["urgency"] == "HIGH":
            icon = "🔴"
        elif msg["urgency"] == "MEDIUM":
            icon = "🟡"
        else:
            icon = "🟢"

        client = msg["client_name"] or "Unknown Client"

        with st.expander(
            f'{icon} {client} — {msg["category"]} — {msg["urgency"]}'
        ):
            st.write("**Client message**")
            st.write(msg["message"])

            st.write("**Reason**")
            st.write(msg["reason"])

            st.write("**Recommended action**")
            st.write(msg["recommended_action"])

            st.write(
                "**Human review:**",
                "YES" if msg["requires_human"] else "NO"
            )

            st.caption(
                f'Received: {msg["created_at"].strftime("%d %b %Y %H:%M")}'
            )

            st.write(f"**Status:** {msg['status']}")

            status_options = ["NEW", "IN REVIEW", "RESOLVED"]

            new_status = st.selectbox(
                "Update status",
                status_options,
                index=status_options.index(msg["status"]),
                key=f"status_{msg['id']}",
            )

            if new_status != msg["status"]:
                update_message_status(msg["id"], new_status)
                st.rerun()
            