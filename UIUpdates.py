# Add this to your Streamlit app to display detailed progress analytics

def show_progress_analytics():
    st.header("Progress Analytics")

    # Get active plans for selection
    active_plans = db.get_active_plans()

    if not active_plans:
        st.info("No active plans found to analyze.")
        return

    # Let user select a plan to analyze
    selected_plan = st.selectbox(
        "Select plan to analyze",
        options=[plan['name'] for plan in active_plans],
        format_func=lambda x: x
    )

    # Get the plan_id from the name
    plan_id = next((p['id'] for p in active_plans if p['name'] == selected_plan), None)

    if not plan_id:
        return

    # Initialize progress tracker
    progress_tracker = db.get_progress_tracker()

    # Generate report
    with st.spinner("Analyzing your progress..."):
        report = progress_tracker.generate_progress_report(1, plan_id)  # Using user_id 1 as default

    if report['status'] != 'success':
        st.error(report['message'])
        return

    # Show overall progress metrics
    st.subheader("Overall Progress")
    metrics_cols = st.columns(4)

    with metrics_cols[0]:
        trend_value = report['overall_progress']['avg_strength_trend']
        trend_color = "green" if trend_value > 0 else "red" if trend_value < 0 else "gray"
        st.metric("Strength Trend", f"{trend_value:.1f}%", delta_color=trend_color)

    with metrics_cols[1]:
        st.metric("Days Active", report['overall_progress']['days_active'])

    with metrics_cols[2]:
        st.metric("Exercises Tracked", report['overall_progress']['exercise_count'])

    with metrics_cols[3]:
        # Calculate how many weeks into the program
        days = report['overall_progress']['days_active']
        st.metric("Weeks Completed", f"{days // 7}")

    # Show key recommendations
    if report['key_recommendations']:
        st.subheader("Key Recommendations")

        for rec in report['key_recommendations']:
            st.write(f"- {rec}")

    # Exercise-specific progress
    st.subheader("Exercise Progress")

    # Filter to exercises with sufficient data
    valid_exercises = {name: data for name, data in report['exercise_progress'].items() 
                     if data['status'] == 'success' and data['workout_count'] > 1}

    if not valid_exercises:
        st.info("Not enough workout data yet to show detailed exercise progress.")
        return

    # Let user select an exercise to view in detail
    selected_exercise = st.selectbox(
        "Select exercise to analyze in detail",
        options=list(valid_exercises.keys())
    )

    if selected_exercise and selected_exercise in valid_exercises:
        exercise_data = valid_exercises[selected_exercise]

        # Show detailed metrics for this exercise
        detail_cols = st.columns(3)

        with detail_cols[0]:
            st.metric("Current 1RM", f"{exercise_data['current_1rm']:.1f} kg")

        with detail_cols[1]:
            st.metric("Best 1RM", f"{exercise_data['best_1rm']:.1f} kg")

        with detail_cols[2]:
            strength_change = exercise_data['progression']['strength_change_pct']
            st.metric("Strength Change", f"{strength_change:.1f}%", 
                    delta=f"{strength_change:.1f}%", 
                    delta_color="normal")

        # Add placeholder for future chart visualizations
        st.write("### Strength Progression Chart")
        st.info("Strength progression chart will be displayed here. Use Plotly or Streamlit's native charting.")

        # Display exercise-specific recommendations
        if exercise_data.get('recommendations'):
            st.write("### Recommendations")
            for rec in exercise_data['recommendations']:
                st.write(f"- {rec}")

# Add a new tab for progress analytics

tabs = st.tabs(["My Plans", "Exercise Library", "Create New Plan", "Progress Analytics"])

with tabs[0]:
    # Existing Plans tab code...
    pass

with tabs[1]:
    # Existing Exercise Library tab code...
    pass

with tabs[2]:
    # Existing Create New Plan tab code...
    pass

with tabs[3]:
    show_progress_analytics()