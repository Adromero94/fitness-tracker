# app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import data
import calculations
import charts

st.set_page_config(
    page_title="💪 Fitness Tracker",
    page_icon="💪",
    layout="wide"
)

# ── Load data ─────────────────────────────────────────────────
df = data.load_log()
profile = data.load_profile()

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("💪 Fitness Tracker")

if profile:
    st.sidebar.write(f"👋 Hey, {profile.get('name', 'there')}!")
    current_weight = data.get_latest_weight(df)
    if current_weight:
        st.sidebar.metric("Current Weight", f"{current_weight} lbs")
    streak = data.get_streak(df)
    st.sidebar.metric("🏅 Streak", f"{streak} days")

page = st.sidebar.radio("Navigate", [
    "📋 Log Today",
    "📊 Dashboard",
    "📅 Weekly Report",
    "🧮 Calculators",
    "⚙️ Profile & Settings"
])

# ─────────────────────────────────────────────────────────────
# PAGE 1: LOG TODAY
# ─────────────────────────────────────────────────────────────
if page == "📋 Log Today":
    st.title("📋 Log Today")

    if not profile:
        st.warning("⚠️ Please set up your Profile first before logging!")
        st.stop()

    # Backfill option
    log_past = st.checkbox("📅 Log a past date instead of today?")
    if log_past:
        log_date = st.date_input("Select date", value=date.today() - timedelta(days=1),
                                  max_value=date.today())
    else:
        log_date = date.today()

    st.write(f"**Logging for: {log_date.strftime('%A, %B %d, %Y')}**")

    # Check if entry exists for this date
    existing = None
    if not df.empty:
        match = df[df["date"].dt.date == log_date]
        if not match.empty:
            existing = match.iloc[-1]
            st.info("📝 An entry exists for this date — saving will update it.")

    # ── Live calorie target display ──
    daily_target = float(profile.get("daily_calorie_target") or 2000)
    bmr = float(profile.get("bmr") or 1800)
    current_weight = data.get_latest_weight(df) or float(profile.get("start_weight") or 180)

    st.divider()
# Weight checkbox outside form so it renders immediately
st.subheader("⚖️ Weight")
log_weight = st.checkbox("Log weight today?",
    value=True if existing is not None and existing.get("weight_lbs") else False)
weight_lbs = None
if log_weight:
    last_weight = data.get_latest_weight(df)
    default_w = float(last_weight) if last_weight else float(
        profile.get("start_weight") or 180)
    weight_lbs = st.number_input(
        "Weight (lbs)", min_value=50.0, max_value=500.0,
        value=float(existing["weight_lbs"])
        if existing is not None and existing.get("weight_lbs")
        else default_w,
        step=0.1
    )

st.divider()

with st.form("log_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🍽️ Calories")
            calories_eaten = st.number_input(
                "Calories eaten today",
                min_value=0, max_value=10000,
                value=int(existing["calories_eaten"]) if existing is not None else 2000,
                step=50
            )

            # Live fuel gauge
            remaining = daily_target - calories_eaten
            if remaining >= 0:
                st.success(f"✅ Remaining: **{int(remaining):,} cal** "
                          f"(Target: {int(daily_target):,})")
            else:
                st.error(f"⚠️ Over target by **{abs(int(remaining)):,} cal** "
                        f"(Target: {int(daily_target):,})")

            st.subheader("😴 Sleep")
            sleep_hours = st.number_input(
                "Hours of sleep last night",
                min_value=0.0, max_value=24.0,
                value=float(existing["sleep_hours"])
                if existing is not None and existing.get("sleep_hours") else 7.0,
                step=0.5
            )
            sleep_quality = st.slider(
                "Sleep quality (1=terrible, 5=great)",
                min_value=1, max_value=5,
                value=int(existing["sleep_quality"])
                if existing is not None and existing.get("sleep_quality") else 3
            )

        with col2:
            st.subheader("🏃 Exercise")
            exercise_type = st.selectbox(
                "Exercise type",
                ["None", "Walking", "Running", "Bike"],
                index=["None", "Walking", "Running", "Bike"].index(
                    existing["exercise_type"])
                if existing is not None and existing.get("exercise_type")
                in ["None", "Walking", "Running", "Bike"] else 0
            )
            exercise_minutes = 0
            calories_burned_exercise = 0
            if exercise_type != "None":
                exercise_minutes = st.number_input(
                    "Exercise minutes",
                    min_value=1, max_value=300,
                    value=int(existing["exercise_minutes"])
                    if existing is not None and existing.get("exercise_minutes") else 30,
                    step=5
                )
                calories_burned_exercise = st.number_input(
                    "Calories burned (from your watch/app)",
                    min_value=0, max_value=2000,
                    value=int(existing["calories_burned_exercise"])
                    if existing is not None and existing.get("calories_burned_exercise") else 200,
                    step=10
                )

            st.subheader("👟 Steps")
            steps = st.number_input(
                "Steps today",
                min_value=0, max_value=100000,
                value=int(existing["steps"])
                if existing is not None and existing.get("steps") else 0,
                step=100
            )

            # Live burn estimate
            steps_calories = calculations.calc_steps_calories(steps, current_weight)
            total_burned = calculations.calc_total_burned(
                bmr, steps_calories, calories_burned_exercise
            )
            st.info(f"🔥 Est. total burned today: **{int(total_burned):,} cal**\n\n"
                   f"  BMR: {int(bmr):,} + Steps: {int(steps_calories):,} "
                   f"+ Exercise: {int(calories_burned_exercise):,}")

            st.subheader("📝 Notes")
            notes = st.text_area(
                "Notes (optional)",
                value=existing["notes"]
                if existing is not None and existing.get("notes") else "",
                placeholder="Cheat day, felt great, extra hungry..."
            )

        st.divider()
        submitted = st.form_submit_button(
            "✅ Save Entry", use_container_width=True
        )

    if submitted:
        steps_calories = calculations.calc_steps_calories(steps, current_weight)
        total_burned = calculations.calc_total_burned(
            bmr, steps_calories, calories_burned_exercise
        )
        deficit = calculations.calc_deficit(calories_eaten, total_burned)
        status = calculations.get_day_status(deficit)

        entry = {
            "date": str(log_date),
            "calories_eaten": calories_eaten,
            "calories_burned_exercise": calories_burned_exercise,
            "exercise_type": exercise_type if exercise_type != "None" else "",
            "exercise_minutes": exercise_minutes,
            "steps": steps,
            "steps_calories": steps_calories,
            "total_calories_burned": total_burned,
            "weight_lbs": weight_lbs if weight_lbs else "",
            "sleep_hours": sleep_hours,
            "sleep_quality": sleep_quality,
            "notes": notes,
            "deficit_surplus": deficit,
            "status": status
        }
        data.save_log_entry(entry)
        st.success("✅ Entry saved!")
        st.balloons()

        if deficit > 0:
            st.success(f"{status} Deficit: **{int(deficit):,} cal** — great work!")
        else:
            st.warning(f"{status} Surplus: **{abs(int(deficit)):,} cal**")

# ─────────────────────────────────────────────────────────────
# PAGE 2: DASHBOARD
# ─────────────────────────────────────────────────────────────
elif page == "📊 Dashboard":
    st.title("📊 Dashboard")

    if df.empty:
        st.info("No data yet — go to **Log Today** to add your first entry!")
        st.stop()

    if not profile:
        st.warning("⚠️ Please set up your Profile first!")
        st.stop()

    # ── Date range slider ──
    st.subheader("📅 Date Range")
    days_options = {"Last 7 Days": 7, "Last 14 Days": 14,
                    "Last 30 Days": 30, "All Time": 0}
    days_label = st.select_slider("Show data for:",
                                   options=list(days_options.keys()),
                                   value="Last 30 Days")
    days = days_options[days_label]

    st.divider()

    # ── Goal & prediction ──
    prediction = calculations.calc_goal_prediction(df, profile)
    if prediction and "estimated_date" in prediction:
        st.subheader("🎯 Goal Tracker")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Current Weight",
                  f"{prediction['current_weight']} lbs")
        c2.metric("Goal Weight",
                  f"{prediction['goal_weight']} lbs")
        c3.metric("Still To Lose",
                  f"{prediction['lbs_to_lose']} lbs")
        c4.metric("Avg Weekly Loss",
                  f"{prediction['avg_weekly_loss']} lbs")
        c5.metric("Est. Arrival",
                  prediction['estimated_date'].strftime("%b %d, %Y"))

        pace = prediction.get("pace_status")
        if pace == "ahead":
            st.success("🟢 You are ahead of pace — great work!")
        elif pace == "on_track":
            st.info("🟡 You are on track for your goal date.")
        elif pace == "behind":
            st.warning("🔴 You are behind pace — check the Weekly Report for recommendations.")

        # Plateau detector
        if calculations.calc_plateau(df):
            st.error("⚠️ Plateau detected — your weight has been stable for 10+ days "
                    "despite a deficit. Consider adjusting your targets.")

    elif prediction and "message" in prediction:
        st.info(prediction["message"])

    st.divider()

    # ── Daily target ──
    daily_target = float(profile.get("daily_calorie_target") or 2000)
    streak = data.get_streak(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Daily Calorie Target", f"{int(daily_target):,} cal")
    col2.metric("🏅 Current Streak", f"{streak} days")
    if not df.empty:
        today_entry = df[df["date"].dt.date == date.today()]
        if not today_entry.empty:
            eaten_today = int(today_entry.iloc[-1]["calories_eaten"])
            remaining = int(daily_target - eaten_today)
            col3.metric("🍽️ Remaining Today",
                       f"{remaining:,} cal",
                       delta=f"{eaten_today:,} eaten")

    st.divider()

    # ── Weekly summary cards ──
    weekly = calculations.calc_weekly_summary(df)
    if weekly:
        st.subheader("📅 Last 7 Days Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Calories Eaten",
                  f"{int(weekly['avg_calories_eaten']):,}")
        c2.metric("Avg Calories Burned",
                  f"{int(weekly['avg_calories_burned']):,}")
        c3.metric("Avg Daily Deficit",
                  f"{int(weekly['avg_deficit']):,} cal")
        c4.metric("Avg Steps",
                  f"{int(weekly['avg_steps']):,}")

        if weekly["weight_change"] is not None:
            direction = "🔽" if weekly["weight_change"] < 0 else "🔼"
            st.metric("Weight Change This Week",
                     f"{direction} {weekly['weight_change']} lbs")

    st.divider()

    # ── Charts ──
    st.subheader("📈 Charts")

    goal_weight = profile.get("goal_weight")
    target_date = profile.get("target_date")

    weight_fig = charts.chart_weight(df, days, goal_weight, target_date)
    if weight_fig:
        st.plotly_chart(weight_fig, use_container_width=True)

    cal_fig = charts.chart_calories(df, days)
    if cal_fig:
        st.plotly_chart(cal_fig, use_container_width=True)

    deficit_fig = charts.chart_deficit(df, days)
    if deficit_fig:
        st.plotly_chart(deficit_fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        steps_fig = charts.chart_steps(df, days)
        if steps_fig:
            st.plotly_chart(steps_fig, use_container_width=True)
    with col2:
        exercise_fig = charts.chart_exercise(df, days)
        if exercise_fig:
            st.plotly_chart(exercise_fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        sleep_fig = charts.chart_sleep(df, days)
        if sleep_fig:
            st.plotly_chart(sleep_fig, use_container_width=True)
    with col2:
        breakdown_fig = charts.chart_calories_breakdown(df, days)
        if breakdown_fig:
            st.plotly_chart(breakdown_fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# PAGE 3: WEEKLY REPORT
# ─────────────────────────────────────────────────────────────
elif page == "📅 Weekly Report":
    st.title("📅 Weekly Report")
    st.write("Rolling 7-day analysis with coaching recommendations.")

    if df.empty or not profile:
        st.info("Log at least a few days of data to generate your report!")
        st.stop()

    weekly = calculations.calc_weekly_summary(df)
    prediction = calculations.calc_goal_prediction(df, profile)

    if not weekly:
        st.info("Not enough data yet — keep logging!")
        st.stop()

    # ── Your numbers ──
    st.subheader("📈 Your Numbers This Week")
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Calories Eaten", f"{int(weekly['avg_calories_eaten']):,} /day")
    c2.metric("Avg Calories Burned", f"{int(weekly['avg_calories_burned']):,} /day")
    c3.metric("Avg Daily Deficit", f"{int(weekly['avg_deficit']):,} cal")

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Steps", f"{int(weekly['avg_steps']):,} /day")
    c2.metric("Exercise Minutes", f"{int(weekly['total_exercise_minutes'])} total")
    c3.metric("Avg Sleep", f"{weekly['avg_sleep']} hrs /night")

    st.divider()

    # ── Weight ──
    st.subheader("⚖️ Weight This Week")
    if weekly["weight_change"] is not None:
        direction = "🔽" if weekly["weight_change"] < 0 else "🔼"
        c1, c2, c3 = st.columns(3)
        c1.metric("Start of Week", f"{weekly['weight_start']} lbs")
        c2.metric("End of Week", f"{weekly['weight_end']} lbs")
        c3.metric("Change", f"{direction} {weekly['weight_change']} lbs")
    else:
        st.info("Log your weight at least twice this week to see weight change.")

    st.divider()

    # ── Goal pace ──
    st.subheader("🎯 Goal Pace")
    if prediction and "pace_status" in prediction:
        pace = prediction["pace_status"]
        if pace == "ahead":
            st.success(f"🟢 Ahead of pace — Est. arrival "
                      f"{prediction['estimated_date'].strftime('%b %d, %Y')}")
        elif pace == "on_track":
            st.info(f"🟡 On track — Est. arrival "
                   f"{prediction['estimated_date'].strftime('%b %d, %Y')}")
        elif pace == "behind":
            st.warning(f"🔴 Behind pace — Est. arrival "
                      f"{prediction['estimated_date'].strftime('%b %d, %Y')}")
    elif prediction and "message" in prediction:
        st.info(prediction["message"])

    st.divider()

    # ── Step goal ──
    st.subheader("👟 Step Goal")
    step_days = weekly["step_goal_days"]
    st.write(f"You hit 10,000 steps **{step_days} out of 7 days** this week.")
    st.progress(step_days / 7)

    st.divider()

    # ── Consistency score ──
    score = calculations.calc_consistency_score(weekly)
    st.subheader("⭐ Consistency Score")
    col1, col2 = st.columns([1, 3])
    with col1:
        if score >= 80:
            st.metric("Score", f"{score}/100", delta="Excellent")
        elif score >= 60:
            st.metric("Score", f"{score}/100", delta="Good")
        elif score >= 40:
            st.metric("Score", f"{score}/100", delta="Fair")
        else:
            st.metric("Score", f"{score}/100", delta="Keep going")
    with col2:
        st.progress(score / 100)

    st.divider()

    # ── Recommendation ──
    st.subheader("🤖 This Week's Recommendation")
    rec = calculations.calc_recommendation(weekly, prediction)
    if rec:
        if rec["color"] == "green":
            st.success(f"**{rec['action']}**\n\n{rec['explanation']}")
        elif rec["color"] == "orange":
            st.warning(f"**{rec['action']}**\n\n{rec['explanation']}")
        else:
            st.error(f"**{rec['action']}**\n\n{rec['explanation']}")

    st.divider()

    # ── Best and hardest day ──
    st.subheader("💡 Highlights")
    today = pd.Timestamp(date.today())
    week_df = df[pd.to_datetime(df["date"]) >= today - pd.Timedelta(days=7)].copy()
    week_df["deficit_surplus"] = pd.to_numeric(
        week_df["deficit_surplus"], errors="coerce"
    )
    if not week_df.empty:
        best_idx = week_df["deficit_surplus"].idxmax()
        worst_idx = week_df["deficit_surplus"].idxmin()
        best_day = week_df.loc[best_idx]
        worst_day = week_df.loc[worst_idx]
        col1, col2 = st.columns(2)
        with col1:
            st.success(
                f"🌟 **Best day:** "
                f"{pd.to_datetime(best_day['date']).strftime('%A, %b %d')}\n\n"
                f"Deficit: {int(best_day['deficit_surplus']):,} cal"
            )
        with col2:
            st.warning(
                f"💪 **Hardest day:** "
                f"{pd.to_datetime(worst_day['date']).strftime('%A, %b %d')}\n\n"
                f"{'Surplus' if worst_day['deficit_surplus'] < 0 else 'Deficit'}: "
                f"{abs(int(worst_day['deficit_surplus'])):,} cal"
            )

# ─────────────────────────────────────────────────────────────
# PAGE 4: CALCULATORS
# ─────────────────────────────────────────────────────────────
elif page == "🧮 Calculators":
    st.title("🧮 Calculators")
    st.write("Calculate your BMR, TDEE, and daily calorie target.")

    col1, col2 = st.columns(2)
    with col1:
        gender = st.selectbox("Gender", ["Male", "Female"])
        age = st.number_input("Age", min_value=10, max_value=100, value=30)
        height_ft = st.number_input("Height (feet)", min_value=3,
                                     max_value=8, value=5)
        height_in = st.number_input("Height (inches)", min_value=0,
                                     max_value=11, value=10)
    with col2:
        weight = st.number_input("Current weight (lbs)", min_value=50.0,
                                  max_value=500.0, value=180.0, step=0.5)
        activity = st.selectbox("Activity level",
                                 list(calculations.ACTIVITY_MULTIPLIERS.keys()))
        goal_w = st.number_input("Goal weight (lbs)", min_value=50.0,
                                  max_value=500.0, value=160.0, step=0.5)
        target_d = st.date_input("Target date",
                                  value=date.today() + timedelta(days=90))

    if st.button("🔢 Calculate", use_container_width=True):
        height_inches = (height_ft * 12) + height_in
        bmr = calculations.calc_bmr(gender, weight, height_inches, age)
        tdee = calculations.calc_tdee(bmr, activity)
        target, floored = calculations.calc_daily_target(
            tdee, goal_w, weight, str(target_d)
        )

        st.divider()
        st.subheader("📊 Your Results")

        c1, c2, c3 = st.columns(3)
        c1.metric("🧬 BMR", f"{int(bmr):,} cal",
                  help="Calories burned just staying alive")
        c2.metric("🔥 TDEE", f"{int(tdee):,} cal",
                  help="BMR + your activity level")
        c3.metric("🎯 Daily Target", f"{int(target):,} cal",
                  help="What you should eat to hit your goal")

        if floored:
            st.warning(
                f"⚠️ Your calculated target was below the safe minimum of "
                f"{calculations.MIN_CALORIES} cal/day. "
                "We've set it to the minimum — consider extending your target date."
            )

        days_to_goal = (target_d - date.today()).days
        lbs_to_lose = weight - goal_w
        daily_deficit = tdee - target

        st.divider()
        st.subheader("📋 Breakdown")
        st.write(f"- **Days to goal date:** {days_to_goal} days")
        st.write(f"- **Lbs to lose:** {round(lbs_to_lose, 1)} lbs")
        st.write(f"- **Daily deficit needed:** {int(daily_deficit):,} cal")
        st.write(f"- **Weekly loss rate:** "
                f"{round((daily_deficit * 7) / 3500, 2)} lbs/week")
        st.write(f"- **BMR:** {int(bmr):,} cal (base metabolism)")
        st.write(f"- **TDEE:** {int(tdee):,} cal "
                f"(BMR × {calculations.ACTIVITY_MULTIPLIERS[activity]})")

        st.divider()
        if st.button("💾 Save these to my Profile", use_container_width=True):
            if profile:
                profile["bmr"] = bmr
                profile["tdee"] = tdee
                profile["daily_calorie_target"] = target
                profile["goal_weight"] = goal_w
                profile["target_date"] = str(target_d)
                data.save_profile(profile)
                st.success("✅ Saved to your profile!")

# ─────────────────────────────────────────────────────────────
# PAGE 5: PROFILE & SETTINGS
# ─────────────────────────────────────────────────────────────
elif page == "⚙️ Profile & Settings":
    st.title("⚙️ Profile & Settings")
    st.write("Set this up once — everything else is calculated automatically.")
    st.divider()

    with st.form("profile_form"):
        st.subheader("👤 Personal Info")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your name",
                value=profile.get("name", "") if profile else "")
            age = st.number_input("Age", min_value=10, max_value=100,
                value=int(profile.get("age") or 30) if profile else 30)
            gender = st.selectbox("Gender", ["Male", "Female"],
                index=0 if not profile or profile.get("gender") == "Male" else 1)
        with col2:
            height_ft = st.number_input("Height (feet)", min_value=3,
                max_value=8, value=5)
            height_in_extra = st.number_input("Height (extra inches)",
                min_value=0, max_value=11,
                value=int((float(profile.get("height_inches") or 70)) % 12)
                if profile else 10)
            start_weight = st.number_input("Starting weight (lbs)",
                min_value=50.0, max_value=500.0,
                value=float(profile.get("start_weight") or 180.0)
                if profile else 180.0, step=0.5)

        st.subheader("🎯 Goal")
        col1, col2 = st.columns(2)
        with col1:
            goal_weight = st.number_input("Goal weight (lbs)",
                min_value=50.0, max_value=500.0,
                value=float(profile.get("goal_weight") or 150.0)
                if profile else 150.0, step=0.5)
        with col2:
            target_date = st.date_input("Target date",
                value=datetime.strptime(
                    str(profile.get("target_date")), "%Y-%m-%d").date()
                if profile and profile.get("target_date") else
                date.today() + timedelta(days=90))

        st.subheader("🏃 Activity Level")
        activity_level = st.selectbox("Activity level",
            list(calculations.ACTIVITY_MULTIPLIERS.keys()),
            index=list(calculations.ACTIVITY_MULTIPLIERS.keys()).index(
                profile.get("activity_level"))
            if profile and profile.get("activity_level") in
            calculations.ACTIVITY_MULTIPLIERS else 0)

        saved = st.form_submit_button("💾 Save Profile", use_container_width=True)

    if saved:
        height_inches = (height_ft * 12) + height_in_extra
        bmr = calculations.calc_bmr(gender, start_weight, height_inches, age)
        tdee = calculations.calc_tdee(bmr, activity_level)
        current_w = data.get_latest_weight(df) or start_weight
        daily_target, floored = calculations.calc_daily_target(
            tdee, goal_weight, current_w, str(target_date)
        )
        new_profile = {
            "name": name,
            "age": age,
            "gender": gender,
            "height_inches": height_inches,
            "start_weight": start_weight,
            "goal_weight": goal_weight,
            "target_date": str(target_date),
            "activity_level": activity_level,
            "bmr": bmr,
            "tdee": tdee,
            "daily_calorie_target": daily_target
        }
        data.save_profile(new_profile)

        st.success("✅ Profile saved!")
        if floored:
            st.warning(
                "⚠️ Your target calories were below the safe minimum of "
                f"{calculations.MIN_CALORIES}/day. "
                "Consider choosing a later target date."
            )
        st.subheader("📊 Your Calculated Stats")
        c1, c2, c3 = st.columns(3)
        c1.metric("🧬 BMR", f"{int(bmr):,} cal")
        c2.metric("🔥 TDEE", f"{int(tdee):,} cal")
        c3.metric("🎯 Daily Target", f"{int(daily_target):,} cal")
        st.rerun()            
        