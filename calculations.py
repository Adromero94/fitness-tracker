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

MIN_CALORIES = 1500  # Safety floor

def calc_bmr(gender, weight_lbs, height_inches, age):
    """
    Mifflin-St Jeor formula — most accurate BMR calculation.
    BMR = calories your body burns just staying alive.
    """
    weight_kg = weight_lbs * 0.453592
    height_cm = height_inches * 2.54
    if gender == "Male":
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5, 1)
    else:
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161, 1)

def calc_tdee(bmr, activity_level):
    """TDEE = BMR × activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return round(bmr * multiplier, 1)

def calc_steps_calories(steps, weight_lbs):
    """
    Estimate calories burned from steps.
    Formula: steps × 0.04 × weight adjustment
    A 180lb person burns ~0.04 cal/step.
    """
    weight_factor = weight_lbs / 180
    return round(steps * 0.04 * weight_factor, 1)

def calc_daily_target(tdee, goal_weight, current_weight, target_date_str):
    """
    Calculate the daily calorie target needed to reach goal by target date.
    Returns the target and whether it's above the safety floor.
    """
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

    # 3,500 calories = 1 lb of fat
    total_deficit_needed = lbs_to_lose * 3500
    daily_deficit_needed = total_deficit_needed / days_remaining
    target = round(tdee - daily_deficit_needed, 0)

    if target < MIN_CALORIES:
        return MIN_CALORIES, True  # Hit safety floor
    return target, False

def calc_total_burned(bmr, steps_calories, exercise_calories):
    """Total calories burned in a day."""
    return round(bmr + steps_calories + exercise_calories, 1)

def calc_deficit(calories_eaten, total_burned):
    """
    Positive = deficit (burning more than eating = losing weight)
    Negative = surplus (eating more than burning = gaining weight)
    """
    return round(total_burned - calories_eaten, 1)

def get_day_status(deficit):
    """Return color status based on deficit."""
    if deficit >= 300:
        return "🟢"
    elif deficit >= 0:
        return "🟡"
    else:
        return "🔴"

# ── Weekly calculations ───────────────────────────────────────

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
        "avg_sleep": round(week_df["sleep_hours"].mean(), 1) if "sleep_hours" in week_df else 0,
        "step_goal_days": int((week_df["steps"] >= 10000).sum()),
    }

    weights = week_df["weight_lbs"].replace("", pd.NA).dropna()
    if len(weights) >= 2:
        summary["weight_start"] = float(weights.iloc[0])
        summary["weight_end"] = float(weights.iloc[-1])
        summary["weight_change"] = round(float(weights.iloc[-1]) - float(weights.iloc[0]), 1)
    else:
        summary["weight_start"] = None
        summary["weight_end"] = None
        summary["weight_change"] = None

    return summary

def calc_goal_prediction(df, profile):
    """Estimate arrival date and weekly loss based on current data."""
    if df.empty or not profile:
        return None

    goal_weight = profile.get("goal_weight")
    target_date_str = profile.get("target_date")
    current_weight = None

    weights = df["weight_lbs"].replace("", pd.NA).dropna()
    if not weights.empty:
        current_weight = float(weights.iloc[-1])

    if not current_weight or not goal_weight:
        return None

    if current_weight <= float(goal_weight):
        return {"message": "🎉 You've reached your goal weight!"}

    # Use actual average deficit if we have enough data
    deficits = df["deficit_surplus"].replace("", pd.NA).dropna()
    if deficits.empty:
        return None

    avg_daily_deficit = deficits.mean()
    if avg_daily_deficit <= 0:
        return {
            "message": "⚠️ No deficit detected yet. Try reducing calories or adding exercise.",
            "current_weight": current_weight,
            "goal_weight": float(goal_weight)
        }

    lbs_to_lose = current_weight - float(goal_weight)
    days_needed = (lbs_to_lose * 3500) / avg_daily_deficit
    estimated_date = date.today() + timedelta(days=int(days_needed))
    avg_weekly_loss = round((avg_daily_deficit * 7) / 3500, 2)

    # Compare to target date
    pace_status = None
    if target_date_str:
        try:
            target_date = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
            if estimated_date <= target_date:
                pace_status = "ahead"
            elif (estimated_date - target_date).days <= 14:
                pace_status = "on_track"
            else:
                pace_status = "behind"
        except:
            pass

    return {
        "current_weight": current_weight,
        "goal_weight": float(goal_weight),
        "lbs_to_lose": round(lbs_to_lose, 1),
        "avg_daily_deficit": round(avg_daily_deficit, 0),
        "avg_weekly_loss": avg_weekly_loss,
        "estimated_date": estimated_date,
        "pace_status": pace_status,
        "days_needed": int(days_needed)
    }

def calc_plateau(df):
    """Detect if weight has been stuck for 10+ days despite a deficit."""
    if df.empty:
        return False
    weights = df[["date", "weight_lbs"]].replace("", pd.NA).dropna()
    if len(weights) < 10:
        return False
    recent = weights.tail(10)
    weight_range = float(recent["weight_lbs"].max()) - float(recent["weight_lbs"].min())
    avg_deficit = df["deficit_surplus"].replace("", pd.NA).dropna().tail(10).mean()
    return weight_range < 1.0 and avg_deficit > 200

# ── Weekly report & recommendations ──────────────────────────

def calc_consistency_score(summary):
    """Score out of 100 based on logging, deficit, and steps."""
    if not summary:
        return 0
    score = 0
    score += min(summary["days_logged"] / 7 * 40, 40)   # 40pts for logging
    if summary["avg_deficit"] > 0:
        score += min(summary["avg_deficit"] / 500 * 30, 30)  # 30pts for deficit
    score += min(summary["step_goal_days"] / 7 * 30, 30)    # 30pts for steps
    return round(score)

def calc_recommendation(summary, prediction):
    """Generate a recommendation based on weekly data."""
    if not summary:
        return None

    avg_deficit = summary.get("avg_deficit", 0)
    avg_steps = summary.get("avg_steps", 0)
    weight_change = summary.get("weight_change")
    pace = prediction.get("pace_status") if prediction else None

    # Too aggressive — losing too fast
    if avg_deficit > 1200:
        return {
            "action": "🍽️ Eat More",
            "color": "orange",
            "explanation": (
                f"Your average deficit of {int(avg_deficit)} cal/day is very aggressive. "
                "Losing weight too fast leads to muscle loss and rebound weight gain. "
                "Try adding 200-300 more calories per day to slow to a sustainable pace."
            )
        }

    # Behind pace — not enough deficit
    if pace == "behind" and avg_deficit < 300:
        if avg_steps < 7000:
            return {
                "action": "🏃 Eat Less + Increase Cardio",
                "color": "red",
                "explanation": (
                    f"You're behind your goal pace with only a {int(avg_deficit)} cal/day "
                    f"deficit and averaging {int(avg_steps):,} steps. Try reducing your "
                    "daily calories by 200 and increasing your daily steps to 8,000+."
                )
            }
        return {
            "action": "🍽️ Eat Less",
            "color": "red",
            "explanation": (
                f"You're behind your goal pace. Your deficit of {int(avg_deficit)} cal/day "
                "isn't quite enough. Try reducing daily calories by 150-200 to get back on track."
            )
        }

    # Behind pace — steps low
    if pace == "behind" and avg_steps < 7000:
        return {
            "action": "🚶 Increase Daily Steps",
            "color": "orange",
            "explanation": (
                f"You're behind pace and averaging only {int(avg_steps):,} steps/day. "
                "Increasing to 8,000-10,000 steps adds 200-300 extra calories burned "
                "per day without changing your diet."
            )
        }

    # On track or ahead
    if pace in ("on_track", "ahead") and 300 <= avg_deficit <= 1000:
        return {
            "action": "✅ Maintain",
            "color": "green",
            "explanation": (
                f"You're {'ahead of' if pace == 'ahead' else 'on'} pace with a solid "
                f"{int(avg_deficit)} cal/day deficit. Your approach is sustainable — "
                "keep doing what you're doing!"
            )
        }

    # Default maintain
    return {
        "action": "✅ Maintain",
        "color": "green",
        "explanation": (
            "Your numbers look good this week. Stay consistent with your "
            "calorie targets and step goals."
        )
    }
