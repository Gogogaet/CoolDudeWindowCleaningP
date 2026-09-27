import json
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Cool Dudes Window Cleaning — Field Desk",
    page_icon="🧽",
    layout="wide",
)

DEFAULT = {
    "bookings": [],
    "doors": [],
    "goal": 1000.0,
    "profile": {
        "name": "Jacob",
        "business": "Cool Dudes Window Cleaning",
        "email": "",
        "phone": "",
    },
    "territory": None,
}

if "data" not in st.session_state:
    st.session_state.data = json.loads(json.dumps(DEFAULT))
data = st.session_state.data


def money(value):
    return f"${float(value or 0):,.2f}"


def save():
    st.session_state.data = data


def month_revenue():
    today = date.today()
    total = 0.0
    for booking in data["bookings"]:
        try:
            d = date.fromisoformat(booking["date"])
        except (KeyError, ValueError, TypeError):
            continue
        if d.year == today.year and d.month == today.month:
            total += float(booking.get("amount", 0) or 0)
    return total


st.markdown("""
<style>
.brand{font-size:1.2rem;font-weight:800}
.brand small{display:block;color:#6b8295;font-size:.67rem;letter-spacing:.08em;font-weight:500}
.metric-card{border:1px solid #d4e6f5;border-radius:14px;padding:1rem;background:#fff;min-height:105px}
.metric-label{color:#58738b;font-size:.78rem}
.metric-value{font-size:1.7rem;font-weight:800;margin-top:.35rem}
.metric-hint{color:#6b8295;font-size:.7rem}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
        '<div class="brand">Cool Dudes Window Cleaning<small>WINDOW CLEANING · FIELD DESK</small></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio("Navigation", ["Overview", "Bookings", "Territory map", "Goals", "Account"])
    st.info(
        "Working data is kept in this Streamlit session. "
        "Export JSON from Account before closing the app."
    )

profile_name = data["profile"].get("name") or "User"
st.caption(f"👤 {profile_name}")

if page == "Overview":
    st.markdown(f"### Good day, {profile_name}")
    st.write("Here’s your window-cleaning business at a glance.")
    st.divider()

    total = sum(float(b.get("amount", 0) or 0) for b in data["bookings"])
    jobs = len(data["bookings"])
    doors = len(data["doors"])
    goal = float(data.get("goal", 1000) or 0)
    current = month_revenue()
    pct = min(1.0, current / goal) if goal else 0.0

    metrics = [
        ("Revenue booked", money(total), "From saved bookings"),
        ("Jobs booked", str(jobs), "Saved appointments"),
        ("Doors tracked", str(doors), "Across your territory"),
        ("Monthly goal", money(goal), f"{money(current)} this month"),
    ]
    for col, item in zip(st.columns(4), metrics):
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{item[0]}</div>'
                f'<div class="metric-value">{item[1]}</div><div class="metric-hint">{item[2]}</div></div>',
                unsafe_allow_html=True,
            )

    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Revenue over time")
        days = st.selectbox(
            "Range", [30, 90, 365], format_func=lambda x: f"Last {x} days"
        )
        end = date.today()
        start = end - timedelta(days=days - 1)
        points = []
        for i in range(days):
            d = start + timedelta(days=i)
            value = sum(
                float(b.get("amount", 0) or 0)
                for b in data["bookings"]
                if b.get("date") == d.isoformat()
            )
            points.append({"Date": d, "Revenue": value})
        st.line_chart(pd.DataFrame(points).set_index("Date"), height=260)

    with right:
        st.subheader("Monthly target")
        st.metric("Progress", f"{money(current)} / {money(goal)}")
        st.progress(pct)
        st.caption(f"{round(pct * 100)}% of your monthly revenue goal")
        st.subheader("Recent bookings")
        recent = sorted(
            data["bookings"], key=lambda b: b.get("date", ""), reverse=True
        )[:3]
        if not recent:
            st.caption("Your saved bookings will appear here.")
        for b in recent:
            st.write(
                f"**{b.get('name', 'Unnamed')}** · {b.get('date', '')} · "
                f"{money(b.get('amount', 0))}"
            )

elif page == "Bookings":
    st.markdown("### Bookings")
    st.write("Save appointments, customer details, and expected revenue.")
    st.divider()

    with st.form("booking_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            customer = st.text_input("Customer name")
            phone = st.text_input("Phone")
            service_date = st.date_input("Service date", date.today())
        with c2:
            amount = st.number_input("Expected revenue ($)", 0.0, step=25.0)
            status = st.selectbox(
                "Status", ["Booked", "Completed", "Needs confirmation"]
            )
            address = st.text_input("Service address")
        submit = st.form_submit_button("Save booking", type="primary")

    if submit:
        if not customer.strip() or not address.strip():
            st.error("Enter the customer name and service address.")
        else:
            data["bookings"].append({
                "id": str(datetime.now().timestamp()),
                "name": customer.strip(),
                "phone": phone.strip(),
                "date": service_date.isoformat(),
                "amount": float(amount),
                "address": address.strip(),
                "status": status,
            })
            save()
            st.success("Booking saved.")
            st.rerun()

    search = st.text_input("Search name or address")
    filt = st.selectbox("Filter", ["All bookings", "Upcoming", "Completed"])
    matches = []
    for b in data["bookings"]:
        hay = f'{b.get("name","")} {b.get("address","")}'.lower()
        if search.strip() and search.lower() not in hay:
            continue
        if filt == "Completed" and b.get("status") != "Completed":
            continue
        if filt == "Upcoming":
            try:
                if date.fromisoformat(b["date"]) < date.today() or b.get("status") == "Completed":
                    continue
            except (ValueError, KeyError, TypeError):
                continue
        matches.append(b)

    if matches:
        st.dataframe(
            pd.DataFrame([{
                "Customer": b.get("name",""),
                "Service date": b.get("date",""),
                "Address": b.get("address",""),
                "Revenue": float(b.get("amount",0) or 0),
                "Status": b.get("status",""),
            } for b in matches]),
            use_container_width=True,
            hide_index=True,
            column_config={"Revenue": st.column_config.NumberColumn(format="$ %.2f")},
        )
        labels = {
            f'{b.get("name","Unnamed")} · {b.get("date","")} · {money(b.get("amount",0))}': b["id"]
            for b in matches
        }
        pick = st.selectbox("Delete booking", [""] + list(labels))
        if pick and st.button("Delete selected booking"):
            data["bookings"] = [b for b in data["bookings"] if b["id"] != labels[pick]]
            save()
            st.success("Booking deleted.")
            st.rerun()
    else:
        st.caption("No bookings match this view.")

elif page == "Territory map":
    st.markdown("### Territory map")
    st.write("Draw a service zone and track every doorstep by status.")
    st.divider()

    map_col, side_col = st.columns([1.5, 1])
    with map_col:
        fmap = folium.Map(location=[41.433, -96.490], zoom_start=14, control_scale=True)
        colors = {"not": "#71869a", "no": "#d45e55", "maybe": "#dfa52e", "yes": "#23966d"}

        for i, door in enumerate(data["doors"], 1):
            lat, lng = door.get("lat"), door.get("lng")
            if lat is not None and lng is not None:
                folium.CircleMarker(
                    [lat, lng],
                    radius=8,
                    color="white",
                    weight=2,
                    fill=True,
                    fill_opacity=.95,
                    fill_color=colors.get(door.get("status","not")),
                    popup=f"{i}. {door.get('address','')} · {door.get('status','')}",
                ).add_to(fmap)

        if data.get("territory"):
            folium.GeoJson(
                data["territory"],
                style_function=lambda _: {
                    "color": "#1769aa",
                    "fillColor": "#1769aa",
                    "fillOpacity": .18,
                    "weight": 3,
                    "dashArray": "7 5",
                },
            ).add_to(fmap)

        Draw(
            export=True,
            draw_options={
                "polygon": True,
                "polyline": False,
                "rectangle": False,
                "circle": False,
                "circlemarker": False,
                "marker": False,
            },
            edit_options={"edit": True, "remove": True},
        ).add_to(fmap)

        result = st_folium(fmap, height=520, use_container_width=True)
        drawing = result.get("last_active_drawing")
        if drawing and drawing.get("geometry", {}).get("type") == "Polygon":
            data["territory"] = drawing
            save()

        st.caption(
            "Interactive OpenStreetMap map centered on Fremont, Nebraska. "
            "Draw the service territory directly on the map."
        )

    with side_col:
        st.subheader("Door status")
        status_filter = st.selectbox(
            "Show", ["All", "Not knocked", "Said no", "Maybe", "Yes"]
        )
        status_map = {
            "All": None,
            "Not knocked": "not",
            "Said no": "no",
            "Maybe": "maybe",
            "Yes": "yes",
        }
        visible = [
            d for d in data["doors"]
            if status_map[status_filter] is None
            or d.get("status") == status_map[status_filter]
        ]
        if not visible:
            st.caption("No doorsteps in this view.")
        for d in visible:
            st.write(
                f'**{d.get("address","")}** · {d.get("status","")} · '
                f'{d.get("note","")}'
            )

        st.divider()
        st.subheader("Add doorstep")
        with st.form("door_form", clear_on_submit=True):
            address = st.text_input("Home address")
            status = st.selectbox(
                "Status",
                ["not", "no", "maybe", "yes"],
                format_func=lambda x: {
                    "not": "Not knocked",
                    "no": "Said no",
                    "maybe": "Maybe",
                    "yes": "Yes",
                }[x],
            )
            note = st.text_input("Note")
            c1, c2 = st.columns(2)
            with c1:
                latitude = st.number_input(
                    "Latitude", value=41.433000, format="%.6f"
                )
            with c2:
                longitude = st.number_input(
                    "Longitude", value=-96.490000, format="%.6f"
                )
            add = st.form_submit_button("Add doorstep", type="primary")

        if add:
            if not address.strip():
                st.error("Enter an address.")
            else:
                data["doors"].append({
                    "id": str(datetime.now().timestamp()),
                    "address": address.strip(),
                    "status": status,
                    "note": note.strip(),
                    "lat": float(latitude),
                    "lng": float(longitude),
                })
                save()
                st.success("Doorstep added.")
                st.rerun()

        if data.get("territory") and st.button("Clear territory outline"):
            data["territory"] = None
            save()
            st.rerun()

elif page == "Goals":
    st.markdown("### Goals & progress")
    new_goal = st.number_input(
        "Monthly revenue target ($)",
        1.0,
        value=float(data.get("goal", 1000)),
        step=100.0,
    )
    if st.button("Save goal", type="primary"):
        data["goal"] = float(new_goal)
        save()
        st.rerun()

    current = month_revenue()
    progress = min(1.0, current / float(data["goal"])) if data["goal"] else 0.0
    st.metric("This month", money(current))
    st.progress(progress)

    for label, status in [
        ("Doors marked yes", "yes"),
        ("Follow-ups (maybe)", "maybe"),
        ("Not yet knocked", "not"),
        ("Not interested", "no"),
    ]:
        count = sum(d.get("status") == status for d in data["doors"])
        st.write(f"**{label}:** {count}")

else:
    st.markdown("### Account & workspace")
    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input(
                "Your name",
                value=data["profile"].get("name", "Jacob"),
            )
            business = st.text_input(
                "Business name",
                value=data["profile"].get(
                    "business", "Cool Dudes Window Cleaning"
                ),
            )
        with c2:
            email = st.text_input(
                "Email", value=data["profile"].get("email", "")
            )
            phone = st.text_input(
                "Phone", value=data["profile"].get("phone", "")
            )
        update = st.form_submit_button("Save profile", type="primary")

    if update:
        data["profile"] = {
            "name": new_name.strip() or "User",
            "business": business.strip() or "Cool Dudes Window Cleaning",
            "email": email.strip(),
            "phone": phone.strip(),
        }
        save()
        st.success("Profile saved for this session.")
        st.rerun()

    st.info(
        "This Python version does not yet provide secure authentication "
        "or a shared cloud database."
    )
    st.download_button(
        "Export my data (JSON)",
        data=json.dumps(data, indent=2),
        file_name="cool-dudes-data.json",
        mime="application/json",
    )
    if st.button("Clear session data"):
        st.session_state.data = json.loads(json.dumps(DEFAULT))
        st.rerun()
