# charts.py
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

def filter_by_days(df, days):
    """Filter dataframe to the last N days. 0 = all time."""
    if days == 0 or df.empty:
        return df
    cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=days)
    return df[pd.to_datetime(df["date"]) >= cutoff].copy()

def format_dates(df):
    """Format dates nicely for chart labels."""
    df = df.copy()
    df["date_label"] = pd.to_datetime(df["date"]).dt.strftime("%b %d")
    return df

def chart_weight(df, days=30, goal_weight=None, target_date=None):
    """Weight over time with optional goal pace line."""
    df = filter_by_days(df, days)
    weight_df = df[df["weight_lbs"].replace("", pd.NA).notna()].copy()
    if weight_df.empty:
        return None

    weight_df = format_dates(weight_df)
    weight_df["weight_lbs"] = pd.to_numeric(weight_df["weight_lbs"], errors="coerce")

    fig = go.Figure()

    # Actual weight line
    fig.add_trace(go.Scatter(
        x=weight_df["date_label"],
        y=weight_df["weight_lbs"],
        mode="lines+markers",
        name="Actual Weight",
        line=dict(color="#4CAF50", width=3),
        marker=dict(size=8)
    ))

    # Goal pace line
    if goal_weight and target_date and not weight_df.empty:
        try:
            start_weight = float(weight_df.iloc[0]["weight_lbs"])
            start_date = pd.to_datetime(weight_df.iloc[0]["date"])
            target = pd.Timestamp(str(target_date))
            days_total = (target - start_date).days
            if days_total > 0:
                pace_dates = pd.date_range(start=start_date, end=target, freq="W")
                pace_weights = [
                    start_weight - (start_weight - float(goal_weight)) *
                    (d - start_date).days / days_total
                    for d in pace_dates
                ]
                fig.add_trace(go.Scatter(
                    x=[d.strftime("%b %d") for d in pace_dates],
                    y=pace_weights,
                    mode="lines",
                    name="Goal Pace",
                    line=dict(color="#FFE66D", width=2, dash="dash")
                ))
        except:
            pass

    # Goal weight line
    if goal_weight:
        fig.add_hline(
            y=float(goal_weight),
            line_dash="dot",
            line_color="#FF6B6B",
            annotation_text=f"Goal: {goal_weight} lbs"
        )

    fig.update_layout(
        title="⚖️ Weight Over Time",
        xaxis_title="Date",
        yaxis_title="Weight (lbs)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig

def chart_calories(df, days=30):
    """Calories eaten vs total burned per day."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    df = format_dates(df)
    df["calories_eaten"] = pd.to_numeric(df["calories_eaten"], errors="coerce")
    df["total_calories_burned"] = pd.to_numeric(df["total_calories_burned"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date_label"], y=df["calories_eaten"],
        name="Calories Eaten", marker_color="#FF6B6B"
    ))
    fig.add_trace(go.Bar(
        x=df["date_label"], y=df["total_calories_burned"],
        name="Calories Burned", marker_color="#4ECDC4"
    ))
    fig.update_layout(
        title="🔥 Calories Eaten vs Burned",
        barmode="group",
        xaxis_title="Date",
        yaxis_title="Calories",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig

def chart_deficit(df, days=30):
    """Daily deficit/surplus bar chart with color coding."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    df = format_dates(df)
    df["deficit_surplus"] = pd.to_numeric(df["deficit_surplus"], errors="coerce")
    colors = ["#4CAF50" if v >= 0 else "#FF6B6B"
              for v in df["deficit_surplus"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date_label"],
        y=df["deficit_surplus"],
        marker_color=colors,
        name="Deficit/Surplus"
    ))
    fig.add_hline(y=0, line_color="white", line_width=1)
    fig.update_layout(
        title="📉 Daily Deficit (green) / Surplus (red)",
        xaxis_title="Date",
        yaxis_title="Calories",
        hovermode="x unified"
    )
    return fig

def chart_exercise(df, days=30):
    """Exercise minutes by type stacked bar."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    exercise_df = df[
        pd.to_numeric(df["exercise_minutes"], errors="coerce") > 0
    ].copy()
    if exercise_df.empty:
        return None
    exercise_df = format_dates(exercise_df)
    exercise_df["exercise_minutes"] = pd.to_numeric(
        exercise_df["exercise_minutes"], errors="coerce"
    )
    fig = px.bar(
        exercise_df, x="date_label", y="exercise_minutes",
        color="exercise_type",
        title="🚴 Exercise Minutes by Type",
        labels={"date_label": "Date", "exercise_minutes": "Minutes",
                "exercise_type": "Type"},
        color_discrete_map={
            "Running": "#FF6B6B",
            "Walking": "#4ECDC4",
            "Bike": "#FFE66D"
        }
    )
    fig.update_layout(hovermode="x unified")
    return fig

def chart_steps(df, days=30):
    """Daily steps bar chart with 10k goal line."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    df = format_dates(df)
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce")
    colors = ["#A78BFA" if s >= 10000 else "#7C5CBF"
              for s in df["steps"].fillna(0)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date_label"], y=df["steps"],
        marker_color=colors, name="Steps"
    ))
    fig.add_hline(
        y=10000, line_dash="dash", line_color="gray",
        annotation_text="10,000 step goal"
    )
    fig.update_layout(
        title="👟 Daily Steps",
        xaxis_title="Date",
        yaxis_title="Steps",
        hovermode="x unified"
    )
    return fig

def chart_sleep(df, days=30):
    """Sleep hours and quality over time."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    sleep_df = df[
        pd.to_numeric(df["sleep_hours"], errors="coerce") > 0
    ].copy()
    if sleep_df.empty:
        return None
    sleep_df = format_dates(sleep_df)
    sleep_df["sleep_hours"] = pd.to_numeric(sleep_df["sleep_hours"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sleep_df["date_label"],
        y=sleep_df["sleep_hours"],
        name="Sleep Hours",
        marker_color="#818CF8"
    ))
    fig.add_hline(
        y=7.5, line_dash="dash", line_color="gray",
        annotation_text="7.5 hr target"
    )
    fig.update_layout(
        title="😴 Sleep Hours",
        xaxis_title="Date",
        yaxis_title="Hours",
        hovermode="x unified"
    )
    return fig

def chart_calories_breakdown(df, days=7):
    """Stacked bar showing BMR + steps + exercise calories burned."""
    df = filter_by_days(df, days)
    if df.empty:
        return None
    df = format_dates(df)
    df["steps_calories"] = pd.to_numeric(df["steps_calories"], errors="coerce").fillna(0)
    df["calories_burned_exercise"] = pd.to_numeric(
        df["calories_burned_exercise"], errors="coerce"
    ).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date_label"], y=df["steps_calories"],
        name="Steps Calories", marker_color="#4ECDC4"
    ))
    fig.add_trace(go.Bar(
        x=df["date_label"], y=df["calories_burned_exercise"],
        name="Exercise Calories", marker_color="#FFE66D"
    ))
    fig.update_layout(
        title="🔢 Calories Burned Breakdown",
        barmode="stack",
        xaxis_title="Date",
        yaxis_title="Calories",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig
