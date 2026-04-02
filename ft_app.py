import streamlit as st
import json, datetime
from ft_funcs import *

if "all_results" not in st.session_state:
    st.session_state.all_results = None
if "key_list" not in st.session_state:
    st.session_state.key_list = []
if "main_fig" not in st.session_state:
    st.session_state.main_fig = None
if "ft_ret" not in st.session_state:
    st.session_state.ft_ret = None
if "sp_ret" not in st.session_state:
    st.session_state.sp_ret = None

# Load/save picks
def load_picks():
    try:
        with open("picks.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_picks(picks):
    with open("picks.json", "w") as f:
        json.dump(picks, f)

st.title("FT Stock Picker Tracker")

# Sidebar
with st.sidebar:
    st.header("Add New Picks")
    pick_date = st.date_input("Pick Date", datetime.date.today())
    tickers_input = st.text_area("Tickers & picks (one per line)", 
                                  placeholder="MAB1.L,Buy\nJHD.L,Sell")
    if st.button("Add Picks"):
        picks = load_picks()
        date_str = str(pick_date)
        picks[date_str] = {}
        for line in tickers_input.strip().split("\n"):
            ticker, action = line.split(",")
            picks[date_str][ticker.strip()] = action.strip()
        save_picks(picks)
        st.success(f"Saved picks for {date_str}")

    st.divider()
    
    st.header("Remove Picks")
    picks = load_picks()
    if picks:
        date_to_remove = st.selectbox("Select pick date", options=list(picks.keys()))
        if date_to_remove:
            ticker_to_remove = st.selectbox("Select ticker", 
                                             options=list(picks[date_to_remove].keys()))
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Remove Ticker"):
                    del picks[date_to_remove][ticker_to_remove]
                    if not picks[date_to_remove]:
                        del picks[date_to_remove]
                    save_picks(picks)
                    st.rerun()
            with col2:
                if st.button("Remove Whole Date"):
                    del picks[date_to_remove]
                    save_picks(picks)
                    st.rerun()
    else:
        st.write("No picks to remove")

# Main
picks = load_picks()

if picks:
    st.subheader("Stored Picks")
    st.json(picks)

    if st.button("Run Analysis"):
        key_list = list(picks.keys())
        results_list = []

        for date_str, tickers in picks.items():
            data = data_collector(tickers, date_str, datetime.date.today())
            results = results_summary(data, tickers)
            results_list.append(results)

        all_results = merge_and_evaluate(results_list, key_list, tol=1.0)
    
        fig = plot_all_results(all_results, key_list, 0.4, 0.4, 0.2)
    
        ft_avg_returns = []
        sp_avg_returns = []
        for date in key_list:
            ft_avg_return, avg_sp_return = performance_by_date(all_results, date, 0.4, 0.4, 0.2)
            ft_avg_returns.append(ft_avg_return)
            sp_avg_returns.append(avg_sp_return)

        st.session_state.all_results = all_results
        st.session_state.key_list = key_list
        st.session_state.main_fig = fig
        st.session_state.ft_ret = np.mean(ft_avg_returns)
        st.session_state.sp_ret = np.mean(sp_avg_returns)
    
    if st.session_state.all_results is not None:
        st.dataframe(st.session_state.all_results)
        st.pyplot(st.session_state.main_fig)
        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("FT Return", f"{st.session_state.ft_ret:.2f}%")
        col2.metric("SP Return", f"{st.session_state.sp_ret:.2f}%")
        st.caption(f"Since {st.session_state.key_list[0]}")

    # Plot by date - uses session state so works after Run Analysis
    if st.session_state.all_results is not None:
        st.divider()
        st.subheader("Stock Performance by Date")

        selected_date = st.selectbox("Select pick date", options=st.session_state.key_list)

        if st.button("Plot Stock Performance"):
            pick_date_obj = datetime.date.fromisoformat(selected_date)
            days_since = (datetime.date.today() - pick_date_obj).days

            if days_since <= 10:
                steps = 3
            elif days_since <= 20:
                steps = 5
            elif days_since <= 45:
                steps = 10
            elif days_since <= 90:
                steps = 20
            else:
                steps = 30

            tickers_for_date = picks[selected_date]
            data_for_date = data_collector(tickers_for_date, selected_date, datetime.date.today())

            fig2 = plot_results(data_for_date, tickers_for_date, steps)
            st.pyplot(fig2)
            st.caption(f"Step interval: every {steps} days")