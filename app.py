import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "roopshri.db"

SCHOOLS = [
    ("001", "NVJS"), ("002", "GAPS"), ("003", "SURYANSH"), ("004", "UTTAM"),
    ("005", "NARULA"), ("006", "WISDOM"), ("007", "DRON"), ("008", "PRESTIGE"),
    ("009", "INVANSION"), ("010", "ANGEL"), ("011", "VIMALA"), ("012", "MAA KAVERI"),
    ("013", "INDUS"), ("014", "DEEP"), ("015", "ABHIGYAN"), ("016", "ROYAL PUBLIC"),
    ("017", "DRASHTI"), ("018", "KIDS CARE"), ("019", "SSGM"), ("021", "UMADEVI"),
    ("022", "FUTURE CARE"), ("023", "SWAMI VIVEKANAND"), ("024", "GURUKUL BADUD"),
    ("025", "TAIBA"), ("026", "STAR KIDS"), ("027", "GLOBAL SHINE"),
    ("028", "INDIAN PUBLIC"), ("029", "ARDUNO")
]

ITEMS = [
    "Shirt", "Pant", "Jacket", "Skirt", "Halfpant", "Tshirt", "Tracksuit",
    "House Lower", "House T-shirt", "Shoes", "Bag", "Socks", "Belt", "Tie", "Fabric"
]

SIZES = [
    "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", 
    "1", "2", "3", "4", "5", "6", "7", "14", "16", "18", "20", 
    "22", "24", "26", "28", "30", "32", "34", "36", "38", "40"
]

def init_db():
    con = sqlite3.connect(DB_NAME)
    con.execute("CREATE TABLE IF NOT EXISTS schools(code TEXT PRIMARY KEY, name TEXT NOT NULL, barcode TEXT UNIQUE)")
    con.execute("CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, barcode TEXT UNIQUE)")
    con.execute("CREATE TABLE IF NOT EXISTS rates(school_code TEXT, item_id INTEGER, size TEXT, rate REAL, PRIMARY KEY(school_code,item_id,size))")
    con.execute("CREATE TABLE IF NOT EXISTS bills(bill_no INTEGER PRIMARY KEY AUTOINCREMENT, dt TEXT, school_code TEXT, total REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS bill_items(bill_no INTEGER, item_id INTEGER, item_name TEXT, size TEXT, qty REAL, rate REAL, amount REAL)")
    
    for code, name in SCHOOLS:
        con.execute("INSERT OR IGNORE INTO schools(code,name,barcode) VALUES(?,?,?)", (code, name, "SCH-" + code))
    for item in ITEMS:
        con.execute("INSERT OR IGNORE INTO items(name,barcode) VALUES(?,?)", (item, "ITM-" + item.upper().replace(" ", "-")))
    con.commit()
    return con

con = init_db()

if "cart" not in st.session_state:
    st.session_state.cart = []
if "selected_school_code" not in st.session_state:
    st.session_state.selected_school_code = None

st.set_page_config(page_title="Roopshri Uniforms", page_icon="🛍️", layout="centered")
st.title("🛍️ Roopshri Uniform Billing")

tab1, tab2 = st.tabs(["📊 POS Billing", "⚙️ Rate Master"])

# --- TAB 1: POS BILLING ---
with tab1:
    st.subheader("Create Customer Bill")
    school_options = {f"{c} - {n}": c for c, n in SCHOOLS}
    selected_school_str = st.selectbox("Select School / स्कूल चुनें:", ["-- Select School --"] + list(school_options.keys()))
    
    if selected_school_str != "-- Select School --":
        st.session_state.selected_school_code = school_options[selected_school_str]
    else:
        st.session_state.selected_school_code = None

    st.divider()
    st.markdown("### Add Item")
    
    item_options = {}
    rows = con.execute("SELECT id, name FROM items").fetchall()
    for item_id, name in rows:
        item_options[name] = item_id
        
    selected_item_name = st.selectbox("Choose Item / आइटम:", list(item_options.keys()))
    selected_size = st.selectbox("Select Size / साइज:", SIZES, index=SIZES.index("30"))
    quantity = st.number_input("Quantity / मात्रा:", min_value=1, max_value=100, value=1, step=1)

    if st.button("➕ Add Item to Cart (कार्ट में जोड़ें)", use_container_width=True):
        if not st.session_state.selected_school_code:
            st.error("❌ Please select a School first! / पहले स्कूल का चुनाव करें।")
        else:
            item_id = item_options[selected_item_name]
            rate_row = con.execute(
                "SELECT rate FROM rates WHERE school_code=? AND item_id=? AND size=?", 
                (st.session_state.selected_school_code, item_id, selected_size)
            ).fetchone()
            
            rate = rate_row[0] if rate_row else 0.0
            
            if rate == 0:
                st.warning(f"⚠️ Rate not set for {selected_item_name} (Size: {selected_size}). Update it in 'Rate Master' tab.")
            else:
                amount = rate * quantity
                st.session_state.cart.append({
                    "item_id": item_id,
                    "Item": selected_item_name,
                    "Size": selected_size,
                    "Qty": int(quantity),
                    "Rate (₹)": float(rate),
                    "Amount (₹)": float(amount)
                })
                st.success(f"Added {selected_item_name} to cart!")

    st.divider()
    st.markdown("### 🛒 Current Cart / आपका कार्ट")
    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.dataframe(df_cart.drop(columns=["item_id"]), use_container_width=True)
        
        total_amount = df_cart["Amount (₹)"].sum()
        st.markdown(f"## **Total: ₹{total_amount:,.2f}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
        with col2:
            if st.button("💾 Save Bill", use_container_width=True, type="primary"):
                cur = con.cursor()
                cur.execute("INSERT INTO bills(dt, school_code, total) VALUES(?,?,?)", 
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.selected_school_code, total_amount))
                bill_no = cur.lastrowid
                
                for item in st.session_state.cart:
                    cur.execute("INSERT INTO bill_items VALUES(?,?,?,?,?,?,?)", 
                                (bill_no, item["item_id"], item["Item"], item["Size"], item["Qty"], item["Rate (₹)"], item["Amount (₹)"]))
                con.commit()
                
                st.success(f"🎉 Bill #{bill_no} Saved!")
                st.session_state.cart = []
    else:
        st.info("Cart is empty / कार्ट खाली है।")

# --- TAB 2: RATE MASTER ---
with tab2:
    st.subheader("⚙️ Manage Uniform Price/Rates")
    rate_school_str = st.selectbox("Select School for Rates:", list(school_options.keys()), key="rate_school")
    rate_school_code = school_options[rate_school_str]
    
    rate_item_name = st.selectbox("Select Item for Rates:", list(item_options.keys()), key="rate_item")
    rate_item_id = item_options[rate_item_name]
    
    rate_size = st.selectbox("Select Size for Rates:", SIZES, key="rate_size")
    new_rate = st.number_input("Enter Rate (₹):", min_value=0.0, step=5.0, value=0.0)
    
    if st.button("💾 Update Rate", use_container_width=True):
        if new_rate <= 0:
            st.error("Rate must be greater than 0!")
        else:
            cur = con.cursor()
            cur.execute("INSERT OR REPLACE INTO rates(school_code, item_id, size, rate) VALUES(?,?,?,?)",
                        (rate_school_code, rate_item_id, rate_size, new_rate))
            con.commit()
            st.success(f"Updated successfully!")
            
    st.divider()
    st.markdown("### Current Rates Preview")
    rates_query = """
        SELECT s.name as 'School', i.name as 'Item', r.size as 'Size', r.rate as 'Rate (₹)' 
        FROM rates r JOIN schools s ON r.school_code = s.code JOIN items i ON r.item_id = i.id WHERE r.school_code = ?
    """
    df_rates = pd.read_sql_query(rates_query, con, params=(rate_school_code,))
    if not df_rates.empty:
        st.dataframe(df_rates, use_container_width=True)
