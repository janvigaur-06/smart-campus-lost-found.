import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date

# --------------------------------------------------
# 1. PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Campus Lost & Found",
    page_icon="🔎",
    layout="wide"
)


# --------------------------------------------------
# 2. MYSQL DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )


# --------------------------------------------------
# 3. LOAD LOST AND FOUND ITEMS
# --------------------------------------------------

def load_items(item_type):
    if item_type == "lost":
        query = """
            SELECT
                L.lost_id AS ID,
                L.item_name AS Item,
                L.category AS Category,
                L.description AS Description,
                LC.location_name AS Location,
                L.lost_date AS Date,
                L.status AS Status
            FROM Lost_Items L
            JOIN Locations LC
                ON L.location_id = LC.location_id
            ORDER BY L.lost_id DESC
        """
    else:
        query = """
            SELECT
                F.found_id AS ID,
                F.item_name AS Item,
                F.category AS Category,
                F.description AS Description,
                LC.location_name AS Location,
                F.found_date AS Date,
                F.status AS Status
            FROM Found_Items F
            JOIN Locations LC
                ON F.location_id = LC.location_id
            ORDER BY F.found_id DESC
        """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        return pd.DataFrame(rows, columns=columns)

    finally:
        if connection.is_connected():
            connection.close()


# --------------------------------------------------
# 4. SAVE A LOST OR FOUND ITEM
# --------------------------------------------------

def save_item(
    item_type,
    name,
    category,
    description,
    location,
    item_date
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT location_id
            FROM Locations
            WHERE location_name = %s
            """,
            (location,)
        )

        location_result = cursor.fetchone()

        if location_result is None:
            st.error("Location not found in the database.")
            return False

        location_id = location_result[0]

        # Demo account for this prototype
        cursor.execute(
            """
            SELECT user_id
            FROM Users
            ORDER BY user_id
            LIMIT 1
            """
        )

        user_result = cursor.fetchone()

        if user_result is None:
            st.error("No users exist in the database.")
            return False

        user_id = user_result[0]

        if item_type == "lost":
            cursor.execute(
                """
                INSERT INTO Lost_Items
                (
                    user_id,
                    item_name,
                    category,
                    description,
                    location_id,
                    lost_date
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    name,
                    category,
                    description,
                    location_id,
                    item_date
                )
            )

        else:
            cursor.execute(
                """
                INSERT INTO Found_Items
                (
                    user_id,
                    item_name,
                    category,
                    description,
                    location_id,
                    found_date
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    name,
                    category,
                    description,
                    location_id,
                    item_date
                )
            )

        connection.commit()
        return True

    except mysql.connector.Error as error:
        connection.rollback()
        st.error("Could not save the item.")
        st.code(str(error))
        return False

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 5. APP HEADER AND NAVIGATION
# --------------------------------------------------

st.title("🔎 Smart Campus Lost & Found")

st.write(
    "A central campus platform to report lost belongings, "
    "report found items, discover possible matches, "
    "and manage claims."
)

st.sidebar.title("Campus Navigation")

page = st.sidebar.radio(
    "Choose a page",
    [
        "Dashboard",
        "Report Lost Item",
        "Report Found Item",
        "Find Matches",
        "Claim Found Item",
        "Admin Review Claims"
    ]
)


# --------------------------------------------------
# 6. LOAD DATABASE DATA
# --------------------------------------------------

try:
    lost_df = load_items("lost")
    found_df = load_items("found")

    st.sidebar.success("MySQL database connected")

except Exception as error:
    st.error("Could not load data from MySQL.")
    st.code(str(error))
    st.info(
        "Check that MySQL is running and that "
        ".streamlit/secrets.toml is configured correctly."
    )
    st.stop()


# --------------------------------------------------
# 7. DASHBOARD
# --------------------------------------------------

if page == "Dashboard":

    st.header("Campus Dashboard")
    st.write("Overview of reported campus belongings.")

    col1, col2, col3 = st.columns(3)

    col1.metric("Lost Items", len(lost_df))
    col2.metric("Found Items", len(found_df))

    available_count = (
        int(found_df["Status"].eq("Available").sum())
        if not found_df.empty else 0
    )

    col3.metric("Available Found Items", available_count)

    st.divider()

    st.subheader("Reported Lost Items")

    if lost_df.empty:
        st.info("No lost items have been reported.")
    else:
        st.dataframe(
            lost_df,
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Reported Found Items")

    if found_df.empty:
        st.info("No found items have been reported.")
    else:
        st.dataframe(
            found_df,
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# 8. REPORT LOST ITEM
# --------------------------------------------------

elif page == "Report Lost Item":

    st.header("Report a Lost Item")

    with st.form("lost_form", clear_on_submit=True):

        name = st.text_input("Item name")

        category = st.selectbox(
            "Category",
            [
                "Electronics",
                "Accessories",
                "ID Card",
                "Stationery",
                "Other"
            ]
        )

        location = st.selectbox(
            "Where did you lose it?",
            [
                "Library",
                "Cafeteria",
                "Computer Lab",
                "Auditorium",
                "Parking Area"
            ]
        )

        item_date = st.date_input(
            "Date lost",
            value=date.today(),
            max_value=date.today()
        )

        description = st.text_area("Description")

        submitted = st.form_submit_button("Submit Lost Item")

    if submitted:

        if not name.strip():
            st.error("Please enter the item name.")

        else:
            if save_item(
                "lost",
                name.strip(),
                category,
                description.strip(),
                location,
                item_date
            ):
                st.success("Lost item saved to MySQL!")
                st.rerun()


# --------------------------------------------------
# 9. REPORT FOUND ITEM
# --------------------------------------------------

elif page == "Report Found Item":

    st.header("Report a Found Item")

    with st.form("found_form", clear_on_submit=True):

        name = st.text_input("Found item name")

        category = st.selectbox(
            "Category",
            [
                "Electronics",
                "Accessories",
                "ID Card",
                "Stationery",
                "Other"
            ]
        )

        location = st.selectbox(
            "Where did you find it?",
            [
                "Library",
                "Cafeteria",
                "Computer Lab",
                "Auditorium",
                "Parking Area"
            ]
         
        )

        item_date = st.date_input(
            "Date found",
            value=date.today(),
            max_value=date.today()
        )

        description = st.text_area("Description")

        submitted = st.form_submit_button("Submit Found Item")

    if submitted:

        if not name.strip():
            st.error("Please enter the item name.")

        else:
            if save_item(
                "found",
                name.strip(),
                category,
                description.strip(),
                location,
                item_date
            ):
                st.success("Found item saved to MySQL!")
                st.rerun()

        
# --------------------------------------------------
# 10. FIND MATCHES
# --------------------------------------------------

elif page == "Find Matches":

    st.header("Find Matches")
    st.write("Compare lost items with available found items.")

    if lost_df.empty or found_df.empty:
        st.info("Report lost and found items first to find matches.")
    else:
        available_items = found_df[
            found_df["Status"] == "Available"
        ]

        matches = []

        for _, lost in lost_df.iterrows():
            if lost["Status"] not in ["Lost", "Matched"]:
                continue

            for _, found in available_items.iterrows():
                score = 0
                reasons = []

                if str(lost["Item"]).strip().lower() == str(found["Item"]).strip().lower():
                    score += 3
                    reasons.append("Same item name")

                if str(lost["Category"]).strip().lower() == str(found["Category"]).strip().lower():
                    score += 2
                    reasons.append("Same category")

                if str(lost["Location"]).strip().lower() == str(found["Location"]).strip().lower():
                    score += 1
                    reasons.append("Same location")

                if score > 0:
                    matches.append({
                        "Lost ID": lost["ID"],
                        "Lost Item": lost["Item"],
                        "Found ID": found["ID"],
                        "Found Item": found["Item"],
                        "Category": lost["Category"],
                        "Lost Location": lost["Location"],
                        "Found Location": found["Location"],
                        "Match Score": score,
                        "Possible Reasons": ", ".join(reasons)
                    })

        if matches:
            matches_df = pd.DataFrame(matches)
            matches_df = matches_df.sort_values(
                by="Match Score",
                ascending=False
            ).reset_index(drop=True)

            st.dataframe(
                matches_df,
                use_container_width=True,
                hide_index=True
            )
            st.caption(
                "These are rule-based suggestions, not confirmed matches. "
                "Verify item ownership before returning anything."
            )
        else:
            st.info(
                "No possible matches found yet. "
                "Try adding more item details or checking again later."
            )


# --------------------------------------------------
# 11. CLAIM FOUND ITEM
# --------------------------------------------------

elif page == "Claim Found Item":

    st.header("Claim a Found Item")
    st.write("Submit a claim for a found item that may belong to you.")

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT lost_id, item_name, category
            FROM Lost_Items
            WHERE status IN ('Lost', 'Matched')
            ORDER BY lost_id DESC
        """)
        lost_options = cursor.fetchall()

        cursor.execute("""
            SELECT found_id, item_name, category
            FROM Found_Items
            WHERE status = 'Available'
            ORDER BY found_id DESC
        """)
        found_options = cursor.fetchall()

        cursor.execute("""
            SELECT user_id, full_name
            FROM Users
            WHERE role = 'Student'
            ORDER BY user_id
        """)
        user_options = cursor.fetchall()

        if not lost_options:
            st.warning("There are no eligible lost-item records to link to a claim.")
        elif not found_options:
            st.warning("There are no currently available found items to claim.")
        elif not user_options:
            st.warning("No student accounts were found in the database.")
        else:
            lost_labels = {
                f"Lost #{row[0]} — {row[1]} ({row[2]})": row[0]
                for row in lost_options
            }
            found_labels = {
                f"Found #{row[0]} — {row[1]} ({row[2]})": row[0]
                for row in found_options
            }
            user_labels = {
                f"{row[1]} (User ID: {row[0]})": row[0]
                for row in user_options
            }

            with st.form("claim_found_item_form"):
                lost_label = st.selectbox(
                    "Select your lost-item record",
                    list(lost_labels.keys())
                )
                found_label = st.selectbox(
                    "Select the found item",
                    list(found_labels.keys())
                )
                user_label = st.selectbox(
                    "Select claimant/student",
                    list(user_labels.keys())
                )

                claim_submitted = st.form_submit_button("Submit Claim")

            if claim_submitted:
                connection2 = None
                try:
                    connection2 = get_connection()
                    cursor2 = connection2.cursor()

                    cursor2.execute("""
                        INSERT INTO Claims
                        (lost_id, found_id, claimant_id, claim_date, claim_status)
                        VALUES (%s, %s, %s, %s, 'Pending')
                    """, (
                        lost_labels[lost_label],
                        found_labels[found_label],
                        user_labels[user_label],
                        date.today()
                    ))

                    connection2.commit()
                    st.success(
                        "Claim submitted successfully! Status: Pending."
                    )

                except Exception as error:
                    if connection2 and connection2.is_connected():
                        connection2.rollback()
                    st.error("Could not submit the claim.")
                    st.code(str(error))

                finally:
                    if connection2 and connection2.is_connected():
                        connection2.close()

    except Exception as error:
        st.error("Could not load claim options.")
        st.code(str(error))

    finally:
        if "connection" in locals() and connection.is_connected():
            connection.close()


# --------------------------------------------------
# 12. ADMIN REVIEW CLAIMS
# --------------------------------------------------

elif page == "Admin Review Claims":

    st.header("Admin Review Claims")
    st.write("Review pending claims and approve or reject them.")

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                C.claim_id,
                C.lost_id,
                L.item_name AS lost_item,
                C.found_id,
                F.item_name AS found_item,
                C.claimant_id,
                U.full_name AS claimant_name,
                C.claim_date,
                C.claim_status
            FROM Claims C
            JOIN Lost_Items L ON C.lost_id = L.lost_id
            JOIN Found_Items F ON C.found_id = F.found_id
            JOIN Users U ON C.claimant_id = U.user_id
            ORDER BY C.claim_id DESC
        """)

        claims = cursor.fetchall()

        if not claims:
            st.info("No claims have been submitted yet.")
        else:
            claims_df = pd.DataFrame(claims)
            st.subheader("All Claims")
            st.dataframe(
                claims_df,
                use_container_width=True,
                hide_index=True
            )

            pending_claims = [
                claim for claim in claims
                if claim["claim_status"] == "Pending"
            ]

            if pending_claims:
                st.subheader("Review a Pending Claim")

                claim_labels = {
                    f"Claim #{claim['claim_id']} — "
                    f"{claim['lost_item']} / {claim['found_item']} "
                    f"(Claimant: {claim['claimant_name']})":
                    claim["claim_id"]
                    for claim in pending_claims
                }

                with st.form("review_claim_form"):
                    selected_label = st.selectbox(
                        "Select pending claim",
                        list(claim_labels.keys())
                    )

                    decision = st.radio(
                        "Decision",
                        ["Approved", "Rejected"],
                        horizontal=True
                    )

                    review_submitted = st.form_submit_button(
                        "Save Decision"
                    )

                if review_submitted:
                    selected_claim_id = claim_labels[selected_label]

                    update_connection = None

                    try:
                        update_connection = get_connection()
                        update_cursor = update_connection.cursor()

                        update_cursor.execute("""
                            SELECT lost_id, found_id
                            FROM Claims
                            WHERE claim_id = %s
                              AND claim_status = 'Pending'
                        """, (selected_claim_id,))

                        claim_pair = update_cursor.fetchone()

                        if claim_pair is None:
                            st.warning(
                                "This claim is no longer pending. Refresh and try again."
                            )
                        elif decision == "Approved":
                            lost_id, found_id = claim_pair

                            update_cursor.execute("""
                                UPDATE Claims
                                SET claim_status = 'Approved'
                                WHERE claim_id = %s
                                  AND claim_status = 'Pending'
                            """, (selected_claim_id,))

                            update_cursor.execute("""
                                UPDATE Found_Items
                                SET status = 'Claimed'
                                WHERE found_id = %s
                                  AND status = 'Available'
                            """, (found_id,))

                            if update_cursor.rowcount != 1:
                                update_connection.rollback()
                                st.error(
                                    "This found item is no longer available. "
                                    "The claim was not approved."
                                )
                            else:
                                update_cursor.execute("""
                                    UPDATE Lost_Items
                                    SET status = 'Returned'
                                    WHERE lost_id = %s
                                """, (lost_id,))

                                update_connection.commit()
                                st.success("Claim approved successfully.")
                                st.rerun()

                        else:
                            update_cursor.execute("""
                                UPDATE Claims
                                SET claim_status = 'Rejected'
                                WHERE claim_id = %s
                                  AND claim_status = 'Pending'
                            """, (selected_claim_id,))

                            update_connection.commit()
                            st.success("Claim rejected.")
                            st.rerun()

                    except Exception as error:
                        if (
                            update_connection
                            and update_connection.is_connected()
                        ):
                            update_connection.rollback()

                        st.error("Could not save the review decision.")
                        st.code(str(error))

                    finally:
                        if (
                            update_connection
                            and update_connection.is_connected()
                        ):
                            update_connection.close()
            else:
                st.info("There are no pending claims to review.")

    except Exception as error:
        st.error("Could not load claims from MySQL.")
        st.code(str(error))

    finally:
        if connection and connection.is_connected():
            connection.close()
