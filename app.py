
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Supply Chain Resilience Simulator",
    layout="wide"
)

st.title("📦 Supply Chain Resilience Simulator")
st.caption("Interactive inventory simulation under demand and supply disruptions")

st.sidebar.header("⚙️ Simulation Parameters")

days = st.sidebar.slider("Simulation days", 30, 365, 120)
initial_inventory = st.sidebar.number_input(
    "Initial inventory", 0, 10000, 500
)
daily_demand = st.sidebar.number_input(
    "Average daily demand", 1, 1000, 40
)

st.sidebar.subheader("🚨 Disruption Settings")

shock = st.sidebar.slider(
    "Demand increase (%)", 0, 300, 50
)

delay = st.sidebar.slider(
    "Additional supplier delay (days)", 0, 30, 5
)

start = st.sidebar.slider(
    "Disruption start day", 1, days, min(30, days)
)

duration = st.sidebar.slider(
    "Disruption duration", 1, days, min(20, days)
)

st.sidebar.subheader("💰 Economic Parameters")

holding_cost = st.sidebar.number_input(
    "Holding cost per unit/day (€)", 0.0, 100.0, 0.05
)

shortage_cost = st.sidebar.number_input(
    "Shortage cost per unit (€)", 0.0, 1000.0, 5.0
)

base_lead_time = st.sidebar.slider(
    "Normal supplier lead time (days)", 1, 30, 3
)

seed = st.sidebar.number_input(
    "Random seed", 0, 100000, 42
)

st.sidebar.info(
    "Fixed: constant inventory target. "
    "Adaptive: increases its target during demand disruptions."
)

rng = np.random.default_rng(seed)

demand = rng.poisson(daily_demand, days)

end = min(days, start - 1 + duration)

demand[start-1:end] = rng.poisson(
    daily_demand * (1 + shock / 100),
    end - (start - 1)
)

def simulate(strategy):

    inventory = initial_inventory
    pipeline = []
    records = []

    total_holding = 0
    total_shortage = 0
    total_fulfilled = 0
    total_demand = 0

    for day in range(1, days + 1):

        active = start <= day < start + duration

        arrivals = sum(
            qty for arrival_day, qty in pipeline
            if arrival_day == day
        )

        pipeline = [
            (arrival_day, qty)
            for arrival_day, qty in pipeline
            if arrival_day > day
        ]

        inventory += arrivals

        actual_demand = int(demand[day-1])

        fulfilled = min(inventory, actual_demand)
        shortage = actual_demand - fulfilled

        inventory -= fulfilled

        total_fulfilled += fulfilled
        total_demand += actual_demand

        total_holding += inventory * holding_cost
        total_shortage += shortage * shortage_cost

        expected_demand = daily_demand

        if strategy == "Adaptive" and active:
            expected_demand *= (1 + shock / 100)

        lead_time = base_lead_time + (delay if active else 0)

        target = expected_demand * (lead_time + 7)

        inventory_position = inventory + sum(
            qty for _, qty in pipeline
        )

        order = max(0, int(np.ceil(target - inventory_position)))

        if order > 0:
            pipeline.append((day + lead_time + 1, order))

        records.append({
            "Day": day,
            "Inventory": inventory,
            "Demand": actual_demand,
            "Fulfilled": fulfilled,
            "Shortage": shortage,
            "Order": order
        })

    df = pd.DataFrame(records)

    fill_rate = (
        total_fulfilled / total_demand
        if total_demand else 1
    )

    return df, {
        "Strategy": strategy,
        "Fill Rate (%)": round(fill_rate * 100, 2),
        "Stockout Days": int((df["Shortage"] > 0).sum()),
        "Average Inventory": round(df["Inventory"].mean(), 2),
        "Holding Cost (€)": round(total_holding, 2),
        "Shortage Cost (€)": round(total_shortage, 2),
        "Total Cost (€)": round(
            total_holding + total_shortage, 2
        )
    }

fixed_df, fixed_kpi = simulate("Fixed")
adaptive_df, adaptive_kpi = simulate("Adaptive")

st.header("📊 Simulation Results")

results = pd.DataFrame([fixed_kpi, adaptive_kpi])

st.dataframe(results, use_container_width=True)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Fixed Strategy Cost",
    f"€{fixed_kpi['Total Cost (€)']:,.2f}"
)

col2.metric(
    "Adaptive Strategy Cost",
    f"€{adaptive_kpi['Total Cost (€)']:,.2f}"
)

savings = (
    fixed_kpi["Total Cost (€)"]
    - adaptive_kpi["Total Cost (€)"]
)

col3.metric(
    "Adaptive Cost Savings",
    f"€{savings:,.2f}"
)

st.subheader("📈 Inventory Levels")

fig, ax = plt.subplots(figsize=(11, 4))

ax.plot(
    fixed_df["Day"],
    fixed_df["Inventory"],
    label="Fixed Strategy"
)

ax.plot(
    adaptive_df["Day"],
    adaptive_df["Inventory"],
    label="Adaptive Strategy"
)

ax.axvspan(
    start,
    min(days, start + duration - 1),
    alpha=0.2,
    color="red",
    label="Disruption Period"
)

ax.set_xlabel("Day")
ax.set_ylabel("Inventory Units")
ax.legend()
ax.grid(alpha=0.3)

st.pyplot(fig)
plt.close(fig)

st.subheader("🚨 Unfulfilled Demand")

fig2, ax2 = plt.subplots(figsize=(11, 4))

ax2.plot(
    fixed_df["Day"],
    fixed_df["Shortage"],
    label="Fixed"
)

ax2.plot(
    adaptive_df["Day"],
    adaptive_df["Shortage"],
    label="Adaptive"
)

ax2.set_xlabel("Day")
ax2.set_ylabel("Unfulfilled Units")
ax2.legend()
ax2.grid(alpha=0.3)

st.pyplot(fig2)
plt.close(fig2)

st.subheader("💰 Cost Comparison")

cost_data = results.set_index("Strategy")[
    ["Holding Cost (€)", "Shortage Cost (€)"]
]

st.bar_chart(cost_data)

st.subheader("📥 Download Simulation Results")

csv = results.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download KPI Comparison",
    csv,
    "simulation_results.csv",
    "text/csv"
)

st.info(
    "Research prototype: simplified periodic-review "
    "inventory simulation with lost sales, deterministic "
    "lead times, and illustrative cost parameters. "
    "The adaptive strategy uses advance knowledge of "
    "the demand shock. Results are not yet validated "
    "research findings."
)
