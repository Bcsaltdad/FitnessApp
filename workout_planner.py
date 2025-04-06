import sqlite3

class WorkoutPlanner:
    def __init__(self, db_connection=None):
        if db_connection:
            self.db = db_connection
        else:
            self.db = sqlite3.connect('fitness.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def create_workout_plan(self, days, focus, equipment, limitations, experience_level, goal):
        """Generates a workout plan based on user input."""
        plan = {}
        for day in range(1, days + 1):
            day_focus = focus.get(f"Day {day}", "")  # Handle missing focus for a day
            exercises = self._select_exercises_for_focus(day_focus, equipment, limitations, experience_level, goal)
            plan[f"Day {day}"] = exercises
        return plan

    def _select_exercises_for_focus(self, day_focus, equipment, limitations, experience_level, goal):
        """Select appropriate exercises for a specific workout focus"""
        exercise_count = {
            "Beginner": {"Compound": 2, "Isolation": 2, "Cardio": 1, "Mobility": 1},
            "Intermediate": {"Compound": 3, "Isolation": 3, "Cardio": 1, "Mobility": 1},
            "Advanced": {"Compound": 4, "Isolation": 4, "Cardio": 1, "Mobility": 1}
        }.get(experience_level, {"Compound": 2, "Isolation": 2, "Cardio": 1, "Mobility": 1})

        # Adjust based on goal
        if "Body Building" in goal:
            exercise_count["Isolation"] += 1
        elif "Sports" in goal:
            exercise_count["Compound"] += 1
        elif "Weight Loss" in goal:
            exercise_count["Cardio"] += 1
        elif "Mobility" in goal:
            exercise_count["Mobility"] += 2
            exercise_count["Compound"] -= 1
            exercise_count["Isolation"] -= 1

        exercises = []
        focus_keywords = day_focus.lower().split('/')

        # Get exercises from database based on focus
        for exercise_type in ["Compound", "Isolation", "Cardio", "Mobility"]:
            count = exercise_count[exercise_type]
            if count <= 0:
                continue

            # Query exercises from database
            query = '''
            SELECT e.*, GROUP_CONCAT(i.instruction) as instructions
            FROM exercises e
            LEFT JOIN exercise_instructions i ON e.id = i.exercise_id
            WHERE e.exercise_type = ?
            AND (
                e.body_part LIKE ? 
                OR e.body_part LIKE ?
                OR e.title LIKE ?
            )
            GROUP BY e.id
            ORDER BY RANDOM()
            LIMIT ?
            '''

            # Use focus keywords to find relevant exercises
            params = [
                exercise_type,
                f"%{focus_keywords[0]}%",
                f"%{focus_keywords[-1]}%",
                f"%{focus_keywords[0]}%",
                count
            ]

            self.db.cursor.execute(query, params)
            rows = self.db.cursor.fetchall()

            for row in rows:
                exercise = dict(zip([col[0] for col in self.db.cursor.description], row))
                exercises.append(exercise)

        return exercises

    def close_connection(self):
        self.db.close()


#Example usage (requires a properly setup workout_data.db)

# planner = WorkoutPlanner()
# plan = planner.create_workout_plan(days=3, 
#                                     focus={"Day 1": "Legs/Glutes", "Day 2": "Chest/Shoulders", "Day 3": "Back/Arms"}, 
#                                     equipment=["Barbell", "Dumbbells"], 
#                                     limitations=["Knee Injury"], 
#                                     experience_level="Intermediate", 
#                                     goal="Body Building")
# print(plan)
# planner.close_connection()