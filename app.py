import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="স্বাধীন ফার্মেসী", page_icon="💊", layout="wide"
)

# Database Setup
conn = sqlite3.connect("pharmacy.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    category TEXT,
    quantity INTEGER,
    buy_price REAL,
    sell_price REAL,
    expiry_date DATE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_name TEXT,
    quantity INTEGER,
    total_price REAL,
    sale_date TIMESTAMP
)
""")
conn.commit()

# Custom CSS for Dark UI & Cards
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1726; color: #ffffff; }
    .card {
        background-color: #1b2e4b;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #00d084;
    }
    .card-warning {
        background-color: #1b2e4b;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #ff4b4b;
    }
    .badge-danger {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("💊 স্বাধীন ফার্মেসী — ড্যাশবোর্ড")

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(
    ["📦 স্টক ড্যাশবোর্ড", "🛒 নতুন বিক্রি এন্ট্রি", "➕ নতুন ওষুধ যোগ"]
)

# Tab 1: Stock Dashboard
with tab1:
    st.subheader("দোকানের ওষুধের স্টক অবস্থা")

    search_query = st.text_input("🔍 ওষুধ খুঁজুন...", "")

    df_stock = pd.read_sql_query("SELECT * FROM stock", conn)

    if not df_stock.empty:
        if search_query:
            df_stock = df_stock[
                df_stock["name"]
                .str.lower()
                .str.contains(search_query.lower())
            ]

        for _, row in df_stock.iterrows():
            is_low_stock = row["quantity"] <= 10
            card_class = "card-warning" if is_low_stock else "card"

            badge_html = (
                '<span class="badge-danger">Low Stock!</span>'
                if is_low_stock
                else ""
            )

            st.markdown(
                f"""
            <div class="{card_class}">
                <h3>💊 {row['name']} <small style="color:#888;">({row['category']})</small> {badge_html}</h3>
                <p><b>স্টক:</b> {row['quantity']} পিস | <b>কেনা:</b> ৳{row['buy_price']} | <b>বিক্রি:</b> ৳{row['sell_price']}</p>
                <p style="color:#ffb703;">📅 <b>মেয়াদের তারিখ:</b> {row['expiry_date']}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("এখনো কোনো ওষুধ যোগ করা হয়নি।")

# Tab 2: Sales Entry
with tab2:
    st.subheader("দৈনিক বিক্রি এন্ট্রি করুন")

    med_list = pd.read_sql_query("SELECT name FROM stock", conn)[
        "name"
    ].tolist()

    if med_list:
        selected_med = st.selectbox("ওষুধ নির্বাচন করুন", med_list)
        sale_qty = st.number_input(
            "বিক্রির পরিমাণ (পিস)", min_value=1, value=1
        )

        med_data = pd.read_sql_query(
            "SELECT sell_price, quantity FROM stock WHERE name=?",
            conn,
            params=(selected_med,),
        ).iloc[0]
        total_price = med_data["sell_price"] * sale_qty

        st.write(f"**মোট বিক্রয় মূল্য:** ৳{total_price:.2f}")

        if st.button("💾 বিক্রি জমা দিন"):
            if med_data["quantity"] >= sale_qty:
                cursor.execute(
                    "INSERT INTO sales (medicine_name, quantity, total_price, sale_date) VALUES (?, ?, ?, ?)",
                    (
                        selected_med,
                        sale_qty,
                        total_price,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                cursor.execute(
                    "UPDATE stock SET quantity = quantity - ? WHERE name = ?",
                    (sale_qty, selected_med),
                )
                conn.commit()
                st.success("বিক্রি সফলভাবে সেভ হয়েছে এবং স্টক আপডেট করা হয়েছে!")
                st.rerun()
            else:
                st.error("স্টকে পর্যাপ্ত ওষুধ নেই!")
    else:
        st.warning("আগে ওষুধ স্টক এন্ট্রি করুন।")

# Tab 3: Add New Medicine
with tab3:
    st.subheader("স্টকে নতুন ওষুধ যোগ করুন")

    with st.form("add_med_form"):
        name = st.text_input("ওষুধের নাম")
        category = st.selectbox(
            "ক্যাটাগরি", ["ট্যাবলেট", "ক্যাপসুল", "সিরাপ", "ইনজেকশন", "অন্যান্য"]
        )
        qty = st.number_input("বর্তমান পরিমাণ (পিস)", min_value=1, value=100)
        buy_p = st.number_input("ক্রয় মূল্য (প্রতি পিস)", min_value=0.0, value=2.0)
        sell_p = st.number_input(
            "বিক্রয় মূল্য (প্রতি পিস)", min_value=0.0, value=2.5
        )
        exp_date = st.date_input("মেয়াদের তারিখ")

        submit = st.form_submit_button("স্টকে যোগ করুন")

        if submit and name:
            try:
                cursor.execute(
                    "INSERT INTO stock (name, category, quantity, buy_price, sell_price, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, category, qty, buy_p, sell_p, str(exp_date)),
                )
                conn.commit()
                st.success(f"{name} সফলভাবে যোগ করা হয়েছে!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("এই নামের ওষুধটি অলরেডি আছে!")
