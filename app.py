import json
import os
from datetime import date, datetime, timedelta

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium
from supabase import Client, create_client
from supabase.client import ClientOptions

st.set_page_config(page_title="Cool Dudes Window Cleaning", page_icon="🧽", layout="wide")

DEFAULT_PROFILE = {
    "full_name": "Jacob",
    "business_name": "Cool Dudes Window Cleaning",
    "email": "",
    "phone": "",
    "monthly_goal": 1000.0,
}


def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


def money(v):
    return "$" + f"{float(v or 0):,.2f}"


def iso_now():
    return datetime.utcnow().isoformat()


def is_demo():
    return st.session_state.sb is None


if "sb" not in st.session_state:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_PUBLISHABLE_KEY") or get_secret("SUPABASE_ANON_KEY")
    st.session_state.sb = (
        create_client(
            url,
            key,
            options=ClientOptions(auto_refresh_token=True, persist_session=False),
        )
        if url and key
        else None
    )

sb: Client | None = st.session_state.sb

if "demo" not in st.session_state:
    st.session_state.demo = {
        t: [] for t in ["customers", "bookings", "leads", "doorsteps", "territories", "expenses"]
    }
if "profile" not in st.session_state:
    st.session_state.profile = DEFAULT_PROFILE.copy()


def rows(table, order="created_at", desc=True):
    if is_demo():
        return st.session_state.demo[table]
    try:
        r = sb.table(table).select("*").order(order, desc=desc).execute()
        return r.data or []
    except Exception as e:
        st.error(f"Could not load {table}: {e}")
        return []


def insert(table, payload):
    if is_demo():
        item = dict(payload)
        item["id"] = f"demo-{datetime.now().timestamp()}"
        item["created_at"] = iso_now()
        st.session_state.demo[table].append(item)
        return item
    try:
        r = sb.table(table).insert(payload).select("*").execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Could not save {table}: {e}")
        return None


def update(table, row_id, payload):
    if is_demo():
        for r in st.session_state.demo[table]:
            if r["id"] == row_id:
                r.update(payload)
                return r
        return None
    try:
        r = sb.table(table).update(payload).eq("id", row_id).select("*").execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Could not update {table}: {e}")
        return None


def remove(table, row_id):
    if is_demo():
        st.session_state.demo[table] = [r for r in st.session_state.demo[table] if r["id"] != row_id]
        return True
    try:
        sb.table(table).delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Could not delete {table}: {e}")
        return False


def get_profile(user_id):
    if is_demo():
        return st.session_state.profile
    try:
        r = sb.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
        if r.data:
            return r.data
        profile = {**DEFAULT_PROFILE, "id": user_id}
        sb.table("profiles").upsert(profile).execute()
        return profile
    except Exception as e:
        st.error(f"Could not load profile: {e}")
        return {**DEFAULT_PROFILE, "id": user_id}


def current_user():
    if is_demo() or not st.session_state.get("auth_session"):
        return None
    try:
        return sb.auth.get_user().user
    except Exception:
        return None


def sign_out():
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("auth_session", None)
    st.session_state.pop("auth_user", None)
    st.rerun()


user = current_user()
if not is_demo() and user is None:
    st.markdown("## Cool Dudes Window Cleaning")
    st.write("Your private business workspace")

    sign_in, sign_up = st.tabs(["Sign in", "Create account"])
    with sign_in:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", type="primary")
        if go:
            try:
                r = sb.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.auth_session = r.session
                st.session_state.auth_user = r.user
                st.rerun()
            except Exception as e:
                st.error(f"Sign-in failed: {e}")

        with st.form("reset"):
            reset_email = st.text_input("Reset email")
            reset = st.form_submit_button("Send reset email")
        if reset:
            try:
                sb.auth.reset_password_for_email(reset_email.strip())
                st.success("Reset instructions requested.")
            except Exception as e:
                st.error(f"Reset request failed: {e}")

    with sign_up:
        with st.form("signup"):
            name = st.text_input("Your name")
            business = st.text_input("Business name", value="Cool Dudes Window Cleaning")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            create = st.form_submit_button("Create account", type="primary")
        if create:
            try:
                r = sb.auth.sign_up(
                    {
                        "email": email.strip(),
                        "password": password,
                        "options": {"data": {"full_name": name.strip(), "business_name": business.strip()}},
                    }
                )
                if r.session:
                    st.session_state.auth_session = r.session
                    st.session_state.auth_user = r.user
                    st.rerun()
                st.success("Account created. Check your email, then sign in.")
            except Exception as e:
                st.error(f"Account creation failed: {e}")
    st.stop()

if is_demo():
    user_id = "demo"
    profile = st.session_state.profile
else:
    user = current_user()
    user_id = user.id
    profile = get_profile(user_id)

customers = rows("customers")
bookings = rows("bookings", order="service_date")
leads = rows("leads", order="next_followup")
doors = rows("doorsteps")
territories = rows("territories")
expenses = rows("expenses", order="expense_date")

st.markdown(
    """
    <style>
    .block-container{max-width:1500px;padding-top:1.4rem}
    .brand{font-size:1.15rem;font-weight:800;line-height:1.05}
    .brand small{display:block;color:#6b8295;font-size:.64rem;letter-spacing:.08em;margin-top:.25rem}
    .metric-card{border:1px solid #d4e6f5;border-radius:14px;padding:1rem;background:white;min-height:105px}
    .metric-label{color:#58738b;font-size:.77rem}.metric-value{font-size:1.65rem;font-weight:800;margin:.35rem 0}.metric-hint{color:#6b8295;font-size:.7rem}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="brand">Cool Dudes Window Cleaning'
        '<small>WINDOW CLEANING · FIELD DESK</small></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio(
        "Navigation",
        ["Dashboard", "Customers", "Bookings", "Leads", "Territory", "Finances", "Account"],
    )
    st.caption(profile.get("full_name") or "User")
    if not is_demo() and st.button("Sign out", use_container_width=True):
        sign_out()
    st.divider()
    if is_demo():
        st.warning("Demo mode: data is temporary.")
    else:
        st.success("Connected database")

today = date.today()
month_key = today.strftime("%Y-%m")


def month_bookings():
    return [
        b for b in bookings
        if str(b.get("service_date", ""))[:7] == month_key
        and b.get("status") != "Cancelled"
    ]


def month_expenses():
    return [
        e for e in expenses
        if str(e.get("expense_date", ""))[:7] == month_key
    ]


if page == "Dashboard":
    st.markdown(f"## Good day, {profile.get('full_name') or 'there'}")
    st.write("Your business at a glance.")
    mb = month_bookings()
    me = month_expenses()
    revenue = sum(float(b.get("amount", 0) or 0) for b in mb)
    costs = sum(float(e.get("amount", 0) or 0) for e in me)
    goal = float(profile.get("monthly_goal", 1000) or 1000)
    pct = min(1.0, revenue / goal) if goal else 0

    for col, item in zip(
        st.columns(4),
        [
            ("Revenue this month", money(revenue), "Scheduled / completed"),
            ("Booked jobs", str(len(mb)), "This month"),
            ("Open leads", str(sum(l.get("status") not in ("Won", "Lost") for l in leads)), "Need follow-up"),
            ("Monthly goal", money(goal), f"{money(revenue)} booked"),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{item[0]}</div>'
                f'<div class="metric-value">{item[1]}</div><div class="metric-hint">{item[2]}</div></div>',
                unsafe_allow_html=True,
            )

    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Revenue over time")
        start = today - timedelta(days=29)
        chart = []
        for i in range(30):
            d = start + timedelta(days=i)
            v = sum(
                float(b.get("amount", 0) or 0)
                for b in bookings
                if b.get("service_date") == d.isoformat() and b.get("status") != "Cancelled"
            )
            chart.append({"Date": d, "Revenue": v})
        st.line_chart(pd.DataFrame(chart).set_index("Date"), height=260)

    with right:
        st.subheader("Monthly target")
        st.metric("Progress", f"{money(revenue)} / {money(goal)}")
        st.progress(pct)
        st.caption(f"{round(pct * 100)}% of your monthly goal")
        st.subheader("Next jobs")
        upcoming = [
            b for b in bookings
            if b.get("service_date", "") >= today.isoformat()
            and b.get("status") != "Cancelled"
        ][:5]
        if not upcoming:
            st.caption("No upcoming jobs.")
        for b in upcoming:
            st.write(
                f"**{b.get('service_date')}** · {b.get('customer_name') or 'Customer'} · "
                f"{money(b.get('amount', 0))}"
            )

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Expenses this month", money(costs))
    c2.metric("Customers", len(customers))
    c3.metric("Doors marked yes", sum(d.get("status") == "yes" for d in doors))


elif page == "Customers":
    st.markdown("## Customers")
    with st.expander("＋ Add customer"):
        with st.form("customer_add"):
            a, b = st.columns(2)
            with a:
                name = st.text_input("Name")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
            with b:
                address = st.text_input("Address")
                status = st.selectbox("Status", ["Active", "Past", "Do not contact"])
                notes = st.text_area("Notes")
            save_btn = st.form_submit_button("Save customer", type="primary")
        if save_btn:
            if not name.strip():
                st.error("Name is required.")
            else:
                insert(
                    "customers",
                    {
                        "owner_id": user_id,
                        "name": name.strip(),
                        "phone": phone.strip(),
                        "email": email.strip(),
                        "address": address.strip(),
                        "status": status,
                        "notes": notes.strip(),
                    },
                )
                st.success("Customer saved.")
                st.rerun()

    q = st.text_input("Search customers")
    found = [
        c for c in customers
        if q.lower() in (
            f'{c.get("name","")} {c.get("phone","")} {c.get("email","")} {c.get("address","")}'
        ).lower()
    ]
    if found:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": c.get("name", ""),
                        "Phone": c.get("phone", ""),
                        "Email": c.get("email", ""),
                        "Address": c.get("address", ""),
                        "Status": c.get("status", ""),
                    }
                    for c in found
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        choices = {
            f'{c.get("name","Unnamed")} · {c.get("address","")}': c["id"] for c in found
        }
        pick = st.selectbox("Manage customer", [""] + list(choices))
        if pick:
            c = next(x for x in found if x["id"] == choices[pick])
            st.write("### Edit customer")
            with st.form("customer_edit"):
                ename = st.text_input("Name", c.get("name", ""))
                ephone = st.text_input("Phone", c.get("phone", ""))
                eemail = st.text_input("Email", c.get("email", ""))
                eaddress = st.text_input("Address", c.get("address", ""))
                estatus = st.selectbox(
                    "Status",
                    ["Active", "Past", "Do not contact"],
                    index=["Active", "Past", "Do not contact"].index(c.get("status", "Active")),
                )
                enotes = st.text_area("Notes", c.get("notes", ""))
                update_btn = st.form_submit_button("Update customer", type="primary")
            if update_btn:
                update(
                    "customers",
                    c["id"],
                    {
                        "name": ename.strip(),
                        "phone": ephone.strip(),
                        "email": eemail.strip(),
                        "address": eaddress.strip(),
                        "status": estatus,
                        "notes": enotes.strip(),
                    },
                )
                st.success("Customer updated.")
                st.rerun()
            if st.button("Delete customer"):
                remove("customers", c["id"])
                st.rerun()
    else:
        st.info("No customers found.")


elif page == "Bookings":
    st.markdown("## Bookings")
    customer_choices = {"No customer": None}
    customer_choices.update(
        {f'{c.get("name","Unnamed")} · {c.get("address","")}': c["id"] for c in customers}
    )

    with st.expander("＋ New booking", expanded=True):
        with st.form("booking_add"):
            a, b = st.columns(2)
            with a:
                choice = st.selectbox("Customer", list(customer_choices))
                service_date = st.date_input("Service date", today)
                service_time = st.time_input("Start time", datetime.now().time().replace(second=0, microsecond=0))
                service = st.text_input("Service", "Exterior window cleaning")
            with b:
                amount = st.number_input("Expected revenue ($)", 0.0, step=25.0)
                status = st.selectbox(
                    "Status", ["Booked", "Completed", "Needs confirmation", "Cancelled"]
                )
                address = st.text_input("Service address")
                notes = st.text_area("Job notes")
            add = st.form_submit_button("Save booking", type="primary")
        if add:
            customer_id = customer_choices[choice]
            customer = next((c for c in customers if c["id"] == customer_id), None)
            insert(
                "bookings",
                {
                    "owner_id": user_id,
                    "customer_id": customer_id,
                    "customer_name": customer.get("name", "") if customer else "",
                    "service_date": service_date.isoformat(),
                    "service_time": service_time.strftime("%H:%M"),
                    "service": service.strip(),
                    "amount": float(amount),
                    "status": status,
                    "address": address.strip() or (customer.get("address", "") if customer else ""),
                    "notes": notes.strip(),
                },
            )
            st.success("Booking saved.")
            st.rerun()

    filt = st.selectbox("Show", ["All", "Upcoming", "Completed", "Needs confirmation", "Cancelled"])
    shown = []
    for b in bookings:
        keep = filt == "All"
        if filt == "Upcoming":
            keep = b.get("service_date", "") >= today.isoformat() and b.get("status") != "Cancelled"
        elif filt in ("Completed", "Needs confirmation", "Cancelled"):
            keep = b.get("status") == filt
        if keep:
            shown.append(b)

    if shown:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": b.get("service_date", ""),
                        "Time": b.get("service_time", ""),
                        "Customer": b.get("customer_name", ""),
                        "Service": b.get("service", ""),
                        "Address": b.get("address", ""),
                        "Revenue": float(b.get("amount", 0) or 0),
                        "Status": b.get("status", ""),
                    }
                    for b in shown
                ]
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"Revenue": st.column_config.NumberColumn(format="$ %.2f")},
        )
        choices = {
            f'{b.get("service_date")} · {b.get("customer_name","Customer")} · {money(b.get("amount",0))}': b["id"]
            for b in shown
        }
        delete_pick = st.selectbox("Delete booking", [""] + list(choices))
        if delete_pick and st.button("Delete selected booking"):
            remove("bookings", choices[delete_pick])
            st.rerun()
    else:
        st.info("No bookings match this view.")


elif page == "Leads":
    st.markdown("## Leads")
    st.write("Track door-to-door prospects, quotes, and follow-ups.")

    with st.expander("＋ Add lead"):
        with st.form("lead_add"):
            a, b = st.columns(2)
            with a:
                lname = st.text_input("Name")
                lphone = st.text_input("Phone")
                lemail = st.text_input("Email")
                laddress = st.text_input("Address")
            with b:
                source = st.selectbox("Source", ["Door-to-door", "Referral", "Website", "Call", "Other"])
                lstatus = st.selectbox(
                    "Status", ["New", "Contacted", "Follow-up", "Quoted", "Won", "Lost"]
                )
                value = st.number_input("Estimated value ($)", 0.0, step=25.0)
                follow = st.date_input("Next follow-up", today)
            lnotes = st.text_area("Notes")
            save_lead = st.form_submit_button("Save lead", type="primary")
        if save_lead:
            insert(
                "leads",
                {
                    "owner_id": user_id,
                    "name": lname.strip(),
                    "phone": lphone.strip(),
                    "email": lemail.strip(),
                    "address": laddress.strip(),
                    "source": source,
                    "status": lstatus,
                    "estimated_value": float(value),
                    "next_followup": follow.isoformat(),
                    "notes": lnotes.strip(),
                },
            )
            st.success("Lead saved.")
            st.rerun()

    if leads:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": l.get("name", ""),
                        "Address": l.get("address", ""),
                        "Source": l.get("source", ""),
                        "Status": l.get("status", ""),
                        "Follow-up": l.get("next_followup", ""),
                        "Value": float(l.get("estimated_value", 0) or 0),
                    }
                    for l in leads
                ]
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="$ %.2f")},
        )
        choices = {f'{l.get("name","Unnamed")} · {l.get("address","")}': l["id"] for l in leads}
        pick = st.selectbox("Manage lead", [""] + list(choices))
        if pick:
            lead = next(l for l in leads if l["id"] == choices[pick])
            a, b = st.columns(2)
            with a:
                ns = st.selectbox(
                    "Status",
                    ["New", "Contacted", "Follow-up", "Quoted", "Won", "Lost"],
                    index=["New", "Contacted", "Follow-up", "Quoted", "Won", "Lost"].index(lead.get("status", "New")),
                )
            with b:
                nf = st.date_input(
                    "Follow-up",
                    date.fromisoformat(lead["next_followup"]) if lead.get("next_followup") else today,
                )
            if st.button("Save lead update", type="primary"):
                update("leads", lead["id"], {"status": ns, "next_followup": nf.isoformat()})
                st.rerun()
            if st.button("Delete lead"):
                remove("leads", lead["id"])
                st.rerun()
    else:
        st.info("No leads yet.")


elif page == "Territory":
    st.markdown("## Territory")
    st.write("Draw and save service zones, then track doorstep status.")

    fmap = folium.Map(location=[41.433, -96.490], zoom_start=14, control_scale=True)
    colors = {"not": "#71869a", "no": "#d45e55", "maybe": "#dfa52e", "yes": "#23966d"}

    for door in doors:
        if door.get("lat") is None or door.get("lng") is None:
            continue
        folium.CircleMarker(
            [float(door["lat"]), float(door["lng"])],
            radius=7,
            color="white",
            weight=2,
            fill=True,
            fill_color=colors.get(door.get("status"), "#71869a"),
            fill_opacity=.95,
            popup=f'{door.get("address","")} · {door.get("status","")}',
        ).add_to(fmap)

    for territory in territories:
        geo = territory.get("geojson")
        if geo:
            try:
                folium.GeoJson(
                    geo,
                    name=territory.get("name", "Service area"),
                    style_function=lambda _: {
                        "color": "#1769aa", "fillColor": "#1769aa",
                        "fillOpacity": .18, "weight": 3, "dashArray": "7 5",
                    },
                ).add_to(fmap)
            except Exception:
                pass

    Draw(
        export=True,
        draw_options={
            "polygon": True, "rectangle": True, "polyline": False,
            "circle": False, "circlemarker": False, "marker": False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(fmap)

    map_result = st_folium(fmap, height=550, use_container_width=True)
    drawing = map_result.get("last_active_drawing") if map_result else None

    if drawing:
        zone_name = st.text_input(
            "New territory name",
            value=f"Fremont Zone {len(territories)+1}",
            key="new_zone_name",
        )
        if st.button("Save drawn territory", type="primary"):
            insert(
                "territories",
                {"owner_id": user_id, "name": zone_name.strip(), "geojson": drawing},
            )
            st.success("Territory saved.")
            st.rerun()

    st.subheader("Add doorstep")
    with st.form("door_add"):
        address = st.text_input("Address")
        a, b = st.columns(2)
        with a:
            lat = st.number_input("Latitude", value=41.433000, format="%.6f")
        with b:
            lng = st.number_input("Longitude", value=-96.490000, format="%.6f")
        status = st.selectbox(
            "Status", ["not", "no", "maybe", "yes"],
            format_func=lambda x: {"not":"Not knocked","no":"Said no","maybe":"Maybe","yes":"Yes"}[x],
        )
        note = st.text_input("Note")
        add_door = st.form_submit_button("Save doorstep", type="primary")
    if add_door:
        insert(
            "doorsteps",
            {
                "owner_id": user_id,
                "address": address.strip(),
                "lat": float(lat),
                "lng": float(lng),
                "status": status,
                "note": note.strip(),
            },
        )
        st.success("Doorstep saved.")
        st.rerun()

    if doors:
        st.subheader("Tracked doors")
        for d in doors[:40]:
            a, b = st.columns([2.8, 1])
            a.write(f'**{d.get("address","")}** · {d.get("note","")}')
            ns = b.selectbox(
                "Status",
                ["not", "no", "maybe", "yes"],
                index=["not", "no", "maybe", "yes"].index(d.get("status", "not")),
                key=f'status_{d["id"]}',
                label_visibility="collapsed",
            )
            if ns != d.get("status"):
                update("doorsteps", d["id"], {"status": ns})
                st.rerun()


elif page == "Finances":
    st.markdown("## Finances")
    st.write("Revenue, expenses, and simple net tracking.")

    mb = month_bookings()
    me = month_expenses()
    revenue = sum(float(b.get("amount", 0) or 0) for b in mb)
    costs = sum(float(e.get("amount", 0) or 0) for e in me)

    for col, item in zip(
        st.columns(3),
        [("Revenue", revenue), ("Expenses", costs), ("Net before tax", revenue - costs)],
    ):
        col.metric(item[0], money(item[1]))

    with st.expander("＋ Add expense"):
        with st.form("expense_add"):
            a, b = st.columns(2)
            with a:
                edate = st.date_input("Date", today)
                category = st.selectbox(
                    "Category", ["Supplies", "Fuel", "Marketing", "Insurance", "Equipment", "Other"]
                )
            with b:
                amount = st.number_input("Amount ($)", 0.0, step=10.0)
                note = st.text_input("Note")
            add_expense = st.form_submit_button("Save expense", type="primary")
        if add_expense:
            insert(
                "expenses",
                {
                    "owner_id": user_id,
                    "expense_date": edate.isoformat(),
                    "category": category,
                    "amount": float(amount),
                    "notes": note.strip(),
                },
            )
            st.success("Expense saved.")
            st.rerun()

    if expenses:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": e.get("expense_date", ""),
                        "Category": e.get("category", ""),
                        "Amount": float(e.get("amount", 0) or 0),
                        "Notes": e.get("notes", ""),
                    }
                    for e in expenses
                ]
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"Amount": st.column_config.NumberColumn(format="$ %.2f")},
        )


else:
    st.markdown("## Account")
    with st.form("profile_form"):
        a, b = st.columns(2)
        with a:
            full_name = st.text_input("Your name", profile.get("full_name", ""))
            business_name = st.text_input(
                "Business name", profile.get("business_name", "Cool Dudes Window Cleaning")
            )
            phone = st.text_input("Phone", profile.get("phone", ""))
        with b:
            email = st.text_input(
                "Email", profile.get("email", ""), disabled=not is_demo()
            )
            monthly_goal = st.number_input(
                "Monthly revenue goal ($)",
                min_value=1.0,
                value=float(profile.get("monthly_goal", 1000) or 1000),
                step=100.0,
            )
        save_profile = st.form_submit_button("Save profile", type="primary")

    if save_profile:
        payload = {
            "full_name": full_name.strip(),
            "business_name": business_name.strip() or "Cool Dudes Window Cleaning",
            "phone": phone.strip(),
            "monthly_goal": float(monthly_goal),
        }
        if is_demo():
            st.session_state.profile.update(payload)
        else:
            payload["email"] = email.strip()
            update("profiles", user_id, payload)
        st.success("Profile saved.")
        st.rerun()

    if not is_demo():
        with st.expander("Change password"):
            with st.form("password_form"):
                p1 = st.text_input("New password", type="password")
                p2 = st.text_input("Confirm", type="password")
                change = st.form_submit_button("Change password", type="primary")
            if change:
                if len(p1) < 8:
                    st.error("Use at least 8 characters.")
                elif p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        sb.auth.update_user({"password": p1})
                        st.success("Password changed.")
                    except Exception as e:
                        st.error(f"Password change failed: {e}")

    export = {
        "profile": profile,
        "customers": customers,
        "bookings": bookings,
        "leads": leads,
        "doorsteps": doors,
        "territories": territories,
        "expenses": expenses,
        "exported_at": iso_now(),
    }
    st.download_button(
        "Export all business data (JSON)",
        json.dumps(export, indent=2, default=str),
        "cool-dudes-business-export.json",
        "application/json",
    )
    st.caption(
        "Supabase mode uses authenticated requests and row-level security. "
        "The public repository must never contain a Supabase secret/service-role key."
    )
