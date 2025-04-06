import streamlit as st
import pandas as pd
import json
from exercise_utils import ExerciseDatabase
from datetime import datetime
from workout_planner import WorkoutPlanner

# Initialize exercise database
db = ExerciseDatabase('fitness.db')

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Initialize session state for navigation
if 'view' not in st.session_state:
    st.session_state.view = 'plans'
if 'selected_plan' not in st.session_state:
    st.session_state.selected_plan = None
if 'selected_week' not in st.session_state:
    st.session_state.selected_week = None
if 'selected_day' not in st.session_state:
    st.session_state.selected_day = None


def show_workout_log(workout):
    st.subheader(workout['title'])
    st.write(f"**Description:** {workout['description']}")
    st.write("**Instructions:**")
    if workout.get('instructions'):
        instructions = workout['instructions'].split(',')
        for i, instruction in enumerate(instructions, 1):
            st.write(f"{i}. {instruction.strip()}")

    st.write(
        f"**Target:** {workout['target_sets']} sets × {workout['target_reps']} reps"
    )

    with st.form(f"log_form_{workout['id']}"):
        sets = st.number_input("Sets Completed", 1, 10, workout['target_sets'])
        reps = st.number_input("Reps Completed", 1, 30, workout['target_reps'])
        weight_lbs = st.number_input("Weight (lbs)",
                                     0.0,
                                     1000.0,
                                     0.0,
                                     step=5.0)

        if st.form_submit_button("Save"):
            weight_kg = weight_lbs / 2.20462
            db.log_workout(workout['id'], sets, reps, weight_kg)
            st.success("Workout logged!")
            st.session_state.view = 'day_summary'


# Navigation functions
def go_to_plans():
    st.session_state.view = 'plans'
    st.session_state.selected_plan = None
    st.session_state.selected_week = None
    st.session_state.selected_day = None


def go_to_week_view(plan_id, week):
    st.session_state.view = 'week_summary'
    st.session_state.selected_plan = plan_id
    st.session_state.selected_week = week


def go_to_day_view(plan_id, week, day):
    st.session_state.view = 'day_summary'
    st.session_state.selected_plan = plan_id
    st.session_state.selected_week = week
    st.session_state.selected_day = day


# Main UI
tabs = st.tabs(["My Plans", "Exercise Library", "Create New Plan"])

with tabs[0]:
    if st.session_state.view == 'plans':
        st.header("My Active Plans")
        active_plans = db.get_active_plans()

        if not active_plans:
            st.info("No active plans found. Create a new plan to get started!")

        for plan in active_plans:
            col1, col2, col3 = st.columns([3, 1, 0.5])
            with col1:
                st.subheader(f"📋 {plan['name']}")
            with col2:
                if f"edit_goal_{plan['id']}" not in st.session_state:
                    st.session_state[f"edit_goal_{plan['id']}"] = False

                if st.session_state[f"edit_goal_{plan['id']}"]:
                    new_goal = st.text_input("New Goal",
                                             value=plan['goal'],
                                             key=f"goal_input_{plan['id']}")
                    if st.button("Save", key=f"save_goal_{plan['id']}"):
                        db.update_plan_goal(plan['id'], new_goal)
                        st.session_state[f"edit_goal_{plan['id']}"] = False
                        st.rerun()
                else:
                    st.write(f"Goal: {plan['goal']}")
            with col3:
                if st.button("✏️", key=f"edit_btn_{plan['id']}"):
                    st.session_state[f"edit_goal_{plan['id']}"] = True

            summary = db.get_plan_summary(plan['id'])
            if summary:
                cols = st.columns(4)
                with cols[0]:
                    st.metric("Total Weeks", plan['duration_weeks'])
                with cols[1]:
                    completed_workouts = sum(week['exercises_completed'] or 0
                                             for week in summary)
                    st.metric("Completed Workouts", completed_workouts)
                with cols[2]:
                    avg_weight = sum(
                        week['avg_weight'] or 0
                        for week in summary) / len(summary) if summary else 0
                    st.metric("Avg Weight (lbs)",
                              f"{(avg_weight * 2.20462):.1f}")
                with cols[3]:
                    days_worked = sum(week['days_worked'] or 0
                                      for week in summary)
                    st.metric("Days Worked", days_worked)

            # Show weeks as clickable buttons
            st.write("### Weekly Schedule")
            week_cols = st.columns(4)
            for week in range(1, plan['duration_weeks'] + 1):
                with week_cols[(week - 1) % 4]:
                    if st.button(f"Week {week}",
                                 key=f"week_{plan['id']}_{week}"):
                        go_to_week_view(plan['id'], week)

    elif st.session_state.view == 'week_summary':
        plan = db.get_active_plans()[0]  # Get the selected plan
        st.button("← Back to Plans", on_click=go_to_plans)
        st.header(f"Week {st.session_state.selected_week} Schedule")

        days = {
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday"
        }

        for day_num, day_name in days.items():
            workouts = db.get_plan_workouts(st.session_state.selected_plan,
                                            st.session_state.selected_week,
                                            day_num)
            if workouts:
                if st.button(f"{day_name} ({len(workouts)} workouts)",
                             key=f"day_{day_num}"):
                    go_to_day_view(st.session_state.selected_plan,
                                   st.session_state.selected_week, day_num)

    elif st.session_state.view == 'day_summary':
        st.button(
            "← Back to Week",
            on_click=lambda: go_to_week_view(st.session_state.selected_plan, st
                                             .session_state.selected_week))

        day_names = {
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday"
        }

        st.header(
            f"Week {st.session_state.selected_week} - {day_names[st.session_state.selected_day]}"
        )

        workouts = db.get_plan_workouts(st.session_state.selected_plan,
                                        st.session_state.selected_week,
                                        st.session_state.selected_day)

        for workout in workouts:
            with st.expander(workout['title']):
                show_workout_log(workout)

with tabs[1]:  # Exercise Library
    st.header("Exercise Library")
    goal = st.selectbox("Filter by Goal",
                        ["Strength", "Cardio", "Flexibility"])
    exercises = db.get_exercises_by_goal(goal)

    for exercise in exercises:
        with st.expander(f"📋 {exercise['title']}", expanded=False):
            st.write(f"**Description:** {exercise['description']}")
            st.write(f"**Equipment:** {exercise['equipment']}")
            st.write(f"**Level:** {exercise['level']}")
            if exercise.get('instructions'):
                st.write("**Instructions:**")
                instructions = exercise['instructions'].split(',')
                for i, instruction in enumerate(instructions, 1):
                    st.write(f"{i}. {instruction.strip()}")

with tabs[2]:  # Create New Plan
    st.header("Create Your Personalized Fitness Plan")

    # Two columns for form organization
    col1, col2 = st.columns(2)

    with col1:
        plan_name = st.text_input("Plan Name")
        plan_goal = st.selectbox("What's your primary fitness goal?", [
            "Sports and Athletics", "Body Building", "Body Weight Fitness",
            "Weight Loss", "Mobility Exclusive"
        ])
        experience_level = st.selectbox(
            "Your fitness experience level",
            ["Beginner", "Intermediate", "Advanced"])
        duration = st.number_input("Program duration (weeks)",
                                   min_value=4,
                                   value=8,
                                   max_value=52)

    with col2:
        workouts_per_week = st.selectbox(
            "How many workouts can you commit to per week?",
            options=list(range(1, 8)),
            index=2)
        equipment_access = st.multiselect(
            "What equipment do you have access to?", [
                "Full Gym", "Dumbbells", "Resistance Bands", "Pull-up Bar",
                "No Equipment"
            ],
            default=["Full Gym"])
        limitations = st.multiselect(
            "Do you have any physical limitations or areas to avoid?",
            ["None", "Lower Back", "Knees", "Shoulders", "Neck"],
            default=["None"])

    # More detailed options in an expander
    with st.expander("Advanced Options"):
        preferred_cardio = st.multiselect("Preferred cardio types", [
            "Running", "Cycling", "Swimming", "Rowing", "Jump Rope", "HIIT",
            "None"
        ],
                                          default=["HIIT"])

        specific_focus = st.multiselect(
            "Any specific areas you want to focus on?", [
                "Core Strength", "Upper Body", "Lower Body", "Explosiveness",
                "Endurance", "Balance", "None"
            ],
            default=["None"])

        time_per_workout = st.slider("Time available per workout (minutes)",
                                     min_value=15,
                                     max_value=120,
                                     value=45,
                                     step=5)

    if st.button("Create Personalized Plan"):
        with st.spinner("Creating your personalized workout plan..."):
            # Save user profile first (if you implement this feature)
            # db.update_user_profile(1, experience_level, height, weight, etc.)

            plan_details = {
                "workouts_per_week": workouts_per_week,
                "equipment_access": equipment_access,
                "limitations": limitations,
                "preferred_cardio": preferred_cardio,
                "specific_focus": specific_focus,
                "time_per_workout": time_per_workout,
                "experience_level": experience_level
            }

            plan_id = db.create_fitness_plan(plan_name, plan_goal, duration,
                                             json.dumps(plan_details))

            st.success("Your personalized plan has been created!")

            # Show a preview of the first week
            st.write("### Preview of Week 1")
            workouts = db.get_plan_workouts(plan_id, 1, None)

            # Group by day
            days = {}
            for workout in workouts:
                day_num = workout['day']
                if day_num not in days:
                    days[day_num] = []
                days[day_num].append(workout)

            # Show each day's workouts
            day_names = {
                1: "Monday",
                2: "Tuesday",
                3: "Wednesday",
                4: "Thursday",
                5: "Friday",
                6: "Saturday",
                7: "Sunday"
            }

            for day_num in sorted(days.keys()):
                with st.expander(
                        f"{day_names[day_num]} - {days[day_num][0]['description'].split('-')[0].strip()}"
                ):
                    for workout in days[day_num]:
                        st.write(
                            f"**{workout['title']}**: {workout['target_sets']} sets × {workout['target_reps']} reps"
                        )

            st.button("Go to My Plans", on_click=go_to_plans)

# Add this after your imports
from Engine import WorkoutRecommender

# Add this where your other routes are
if st.sidebar.button("Test Recommendation Engine"):
    recommender = WorkoutRecommender(db)
    test_user_id = 1  # Using default user ID
    recommendation = recommender.get_daily_recommendation(test_user_id)
    
    st.write("### Recommendation Test Results")
    st.json(recommendation)
    
    if recommendation.get('workouts'):
        st.write("### Suggested Workouts")
        for workout in recommendation['workouts']:
            st.write(f"- {workout['title']}: {workout.get('sets', 'N/A')} sets × {workout.get('reps', 'N/A')} reps")
    
    if recommendation.get('adjustments'):
        st.write("### Suggested Adjustments")
        for adjustment in recommendation['adjustments']:
            st.write(f"- {adjustment}")
            
    if recommendation.get('muscle_recovery'):
        st.write("### Muscle Recovery Status")
        for muscle, status in recommendation['muscle_recovery'].items():
            st.write(f"- {muscle}: {status}")



# Close database connection at the very end
if __name__ == "__main__":
    try:
        st.session_state
    finally:
        db.close()
