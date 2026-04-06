# calculations.py
import pandas as pd
from datetime import date, timedelta, datetime

# ── BMR & TDEE ────────────────────────────────────────────────

ACTIVITY_MULTIPLIERS = {
    "Sedentary (little or no exercise)": 1.2,
    "Lightly Active (1-3 days/week)": 1.375,
    "Moderately Active (3-5 days/week)": 1.55,
    "Very Active (6-7 days/week)": 1.725,
}

MIN_CALORIES = 1500
CALORIES_PER_LB = 3500

def calc_bmr(gender, weight_lbs, height_inches, age):
    """Mifflin-St Jeor formula."""
    weight_kg = weight_lbs * 0.453592
    height_cm = height_inches * 2.54
    if gender == "Male":
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5, 1)
    else:
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161, 1)

def calc_tdee(bmr, activity_level):
    """TDEE = BMR x activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return round(bmr * multiplier, 1)

def calc_steps_calories(steps, weight_lbs):
    """Estimate calories burned from steps."""
    weight_factor = weight_lbs / 180
    return round(steps * 0.04 * weight_factor, 1)

def calc_daily_target(tdee, goal_weight, current_weight, target_date_str):
    """Calculate daily calorie target to reach goal by target date."""
    if not target_date_str or not goal_weight or not current_weight:
        return tdee, False
    try:
        target_date = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
    except:
        return tdee, False

    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return tdee, False

    lbs_to_lose = current_weight - goal_weight
    if lbs_to_lose <= 0:
        return tdee, False

    total_deficit_needed = lbs_to_lose * CALORIES_PER_LB
    daily_deficit_needed = total_deficit_needed / days_remaining
    target = round(tdee - daily_deficit_needed, 0)

    if target < MIN_CALORIES:
        return MIN_CALORIES, True
    return target, False

def calc_target_weekly_loss(goal_weight, current_weight, target_date_str):
    """Calculate the target weekly loss rate to hit goal by target date."""
    if not target_date_str or not goal_weight or not current_weight:
        return None
    try:
        target_date = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
    except:
        return None
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return None
    lbs_to_lose = float(current_weight) - float(goal_weight)
    if lbs_to_lose <= 0:
        return None
    weeks_remaining = days_remaining / 7
    return round(lbs_to_lose / weeks_remaining, 2)

def calc_total_burned(bmr, steps_calories, exercise_calories):
    """Total calories burned in a day."""
    return round(bmr + steps_calories + exercise_calories, 1)

def calc_deficit(calories_eaten, total_burned):
    """Positive = deficit, Negative = surplus."""
    return round(total_burned - calories_eaten, 1)

def get_day_status(deficit):
    """Color status based on deficit."""
    if deficit >= 300:
        return "🟢"
    elif deficit >= 0:
        return "🟡"
    else:
        return "🔴"

# ── Weekly calculations ───────────────────────────────────────

def calc_actual_weekly_loss(df):
    """
    Calculate actual weekly loss rate from real weight data.
    Requires at least 2 weight entries to be accurate.
    Returns lbs lost per week based on all available weight data.
    """
    weight_df = df[["date", "weight_lbs"]].copy()
    weight_df["weight_lbs"] = pd.to_numeric(
        weight_df["weight_lbs"], errors="coerce"
    )
    weight_df = weight_df.dropna(subset=["weight_lbs"])
    weight_df = weight_df.sort_values("date")

    if len(weight_df) < 2:
        return None

    first = weight_df.iloc[0]
    last = weight_df.iloc[-1]

    days_elapsed = (
        pd.to_datetime(last["date"]) - pd.to_datetime(first["date"])
    ).days

    if days_elapsed < 1:
        return None

    total_lost = float(first["weight_lbs"]) - float(last["weight_lbs"])
    weekly_loss = (total_lost / days_elapsed) * 7
    return round(weekly_loss, 2)

def calc_weekly_summary(df):
    """Summarize the last 7 days."""
    if df.empty:
        return None
    today = pd.Timestamp(date.today())
    week_ago = today - pd.Timedelta(days=7)
    week_df = df[pd.to_datetime(df["date"]) >= week_ago].copy()
    if week_df.empty:
        return None

    summary = {
        "days_logged": len(week_df),
        "avg_calories_eaten": round(week_df["calories_eaten"].mean(), 0),
        "avg_calories_burned": round(week_df["total_calories_burned"].mean(), 0),
        "avg_deficit": round(week_df["deficit_surplus"].mean(), 0),
        "total_steps": int(week_df["steps"].sum()),
        "avg_steps": round(week_df["steps"].mean(), 0),
        "total_exercise_minutes": int(week_df["exercise_minutes"].sum()),
        "avg_exercise_minutes": round(week_df["exercise_minutes"].mean(), 0),
        "avg_sleep": round(week_df["sleep_hours"].mean(), 1)
        if "sleep_hours" in week_df else 0,
        "step_goal_days": int((week_df["steps"] >= 10000).sum()),
    }

    weights = week_df["weight_lbs"].replace("", pd.NA).dropna()
    if len(weights) >= 2:
        summary["weight_start"] = float(weights.iloc[0])
        summary["weight_end"] = float(weights.iloc[-1])
        summary["weight_change"] = round(
            float(weights.iloc[-1]) - float(weights.iloc[0]), 1
        )
    else:
        summary["weight_start"] = None
        summary["weight_end"] = None
        summary["weight_change"] = None

    return summary

def calc_goal_prediction(df, profile):
    """Estimate arrival date based on actual weight loss rate."""
    if df.empty or not profile:
        return None

    goal_weight = profile.get("goal_weight")
    target_date_str = profile.get("target_date")

    weights = df["weight_lbs"].replace("", pd.NA).dropna()
    if weights.empty:
        return None

    current_weight = float(weights.iloc[-1])

    if not goal_weight:
        return None

    if current_weight <= float(goal_weight):
        return {"message": "🎉 You've reached your goal weight!"}

    # Use actual weekly loss if we have enough weight data
    actual_weekly_loss = calc_actual_weekly_loss(df)

    # Fall back to deficit-based estimate if not enough weight data
    if actual_weekly_loss is None or actual_weekly_loss <= 0:
        deficits = df["deficit_surplus"].replace("", pd.NA).dropna()
        if deficits.empty:
            return None
        avg_daily_deficit = deficits.mean()
        if avg_daily_deficit <= 0:
            return {
                "message": "⚠️ No deficit detected yet.",
                "current_weight": current_weight,
                "goal_weight": float(goal_weight)
            }
        actual_weekly_loss = round((avg_daily_deficit * 7) / CALORIES_PER_LB, 2)

    lbs_to_lose = current_weight - float(goal_weight)
    weeks_needed = lbs_to_lose / actual_weekly_loss
    days_needed = int(weeks_needed * 7)
    estimated_date = date.today() + timedelta(days=days_needed)

    # Target weekly loss from profile
    target_weekly_loss = calc_target_weekly_loss(
        goal_weight, current_weight, target_date_str
    )

    # Pace status with ±0.5 lb tolerance
    pace_status = None
    if target_weekly_loss:
        tolerance = 0.5
        if actual_weekly_loss > target_weekly_loss + tolerance:
            pace_status = "too_fast"
        elif actual_weekly_loss < target_weekly_loss - tolerance:
            pace_status = "too_slow"
        else:
            pace_status = "on_track"

    return {
        "current_weight": current_weight,
        "goal_weight": float(goal_weight),
        "lbs_to_lose": round(lbs_to_lose, 1),
        "actual_weekly_loss": actual_weekly_loss,
        "target_weekly_loss": target_weekly_loss,
        "estimated_date": estimated_date,
        "pace_status": pace_status,
        "days_needed": days_needed
    }

def calc_plateau(df):
    """Detect if weight has been stuck for 10+ days despite a deficit."""
    if df.empty:
        return False
    weights = df[["date", "weight_lbs"]].replace("", pd.NA).dropna()
    if len(weights) < 10:
        return False
    recent = weights.tail(10)
    weight_range = float(recent["weight_lbs"].max()) - float(
        recent["weight_lbs"].min()
    )
    avg_deficit = df["deficit_surplus"].replace("", pd.NA).dropna().tail(10).mean()
    return weight_range < 1.0 and avg_deficit > 200

# ── Weekly report & recommendations ──────────────────────────

def calc_consistency_score(summary):
    """Score out of 100."""
    if not summary:
        return 0
    score = 0
    score += min(summary["days_logged"] / 7 * 40, 40)
    if summary["avg_deficit"] > 0:
        score += min(summary["avg_deficit"] / 500 * 30, 30)
    score += min(summary["step_goal_days"] / 7 * 30, 30)
    return round(score)

def calc_recommendation(weekly, prediction):
    """
    Generate calorie-focused recommendation based on actual
    weekly loss vs target weekly loss with ±0.5 lb tolerance.
    Ignores activity level — focuses on calories only.
    """
    if not weekly or not prediction:
        return None

    # Need real weight data for accurate recommendation
    actual_weekly_loss = prediction.get("actual_weekly_loss")
    target_weekly_loss = prediction.get("target_weekly_loss")
    pace = prediction.get("pace_status")
    avg_calories_eaten = weekly.get("avg_calories_eaten", 0)
    avg_calories_burned = weekly.get("avg_calories_burned", 0)

    # Not enough data yet
    if actual_weekly_loss is None or target_weekly_loss is None:
        return {
            "action": "📊 Keep Logging",
            "color": "blue",
            "explanation": (
                "Log your weight each Monday and keep tracking daily calories. "
                "Once we have 2+ weigh-ins we can give you accurate recommendations."
            )
        }

    tolerance = 0.5

    # Losing too fast
    if pace == "too_fast":
        overage = round(actual_weekly_loss - target_weekly_loss, 1)
        cal_adjustment = round((overage * CALORIES_PER_LB) / 7)
        new_target = round(avg_calories_eaten + cal_adjustment)
        return {
            "action": "🍽️ Eat a Little More",
            "color": "orange",
            "explanation": (
                f"You're losing **{actual_weekly_loss} lbs/week** which is "
                f"{overage} lbs faster than your target of "
                f"**{target_weekly_loss} lbs/week** (±{tolerance} lb range).\n\n"
                f"Losing too fast can lead to muscle loss and low energy. "
                f"Try adding **{cal_adjustment} cal/day** this week.\n\n"
                f"📌 Suggested daily target: **{new_target:,} calories**"
            )
        }

    # Losing too slow or not losing
    if pace == "too_slow":
        if actual_weekly_loss <= 0:
            cal_adjustment = round(target_weekly_loss * CALORIES_PER_LB / 7)
            new_target = round(avg_calories_eaten - cal_adjustment)
            new_target = max(new_target, MIN_CALORIES)
            return {
                "action": "🍽️ Reduce Calories",
                "color": "red",
                "explanation": (
                    f"You're not losing weight this week. "
                    f"Your target is **{target_weekly_loss} lbs/week**.\n\n"
                    f"Try reducing by **{cal_adjustment} cal/day** this week.\n\n"
                    f"📌 Suggested daily target: **{new_target:,} calories**"
                )
            }
        shortage = round(target_weekly_loss - actual_weekly_loss, 1)
        cal_adjustment = round((shortage * CALORIES_PER_LB) / 7)
        new_target = max(round(avg_calories_eaten - cal_adjustment), MIN_CALORIES)
        return {
            "action": "🍽️ Reduce Calories Slightly",
            "color": "orange",
            "explanation": (
                f"You're losing **{actual_weekly_loss} lbs/week** which is "
                f"{shortage} lbs slower than your target of "
                f"**{target_weekly_loss} lbs/week** (±{tolerance} lb range).\n\n"
                f"Try reducing by **{cal_adjustment} cal/day** this week.\n\n"
                f"📌 Suggested daily target: **{new_target:,} calories**"
            )
        }

    # On track
    return {
        "action": "✅ Maintain",
        "color": "green",
        "explanation": (
            f"You're losing **{actual_weekly_loss} lbs/week** which is right "
            f"within your target range of "
            f"**{round(target_weekly_loss - tolerance, 1)}–"
            f"{round(target_weekly_loss + tolerance, 1)} lbs/week**.\n\n"
            f"Your current calorie intake of **{int(avg_calories_eaten):,} cal/day** "
            f"is working — keep it up!"
        )
    }
