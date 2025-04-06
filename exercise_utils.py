import sqlite3
from typing import List, Dict, Any

class ExerciseDatabase:
    def __init__(self, db_path: str = 'fitness.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def get_exercises_by_goal(self, goal: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get exercises based on fitness goal"""
        mapping = {
            'strength': ['Strength', 'Powerlifting'],
            'cardio': ['Cardio', 'Plyometrics'],
            'flexibility': ['Stretching'],
        }

        exercise_types = mapping.get(goal.lower(), ['Strength'])

        query = '''
        SELECT e.*, GROUP_CONCAT(i.instruction) as instructions
        FROM exercises e
        LEFT JOIN exercise_instructions i ON e.id = i.exercise_id
        WHERE e.exercise_type IN ({})
        GROUP BY e.id
        LIMIT ?
        '''.format(','.join(['?'] * len(exercise_types)))

        self.cursor.execute(query, exercise_types + [limit])
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_exercises_by_muscle(self, muscle: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get exercises targeting specific muscle group"""
        query = '''
        SELECT e.*, GROUP_CONCAT(i.instruction) as instructions
        FROM exercises e
        LEFT JOIN exercise_instructions i ON e.id = i.exercise_id
        WHERE e.body_part LIKE ?
        GROUP BY e.id
        LIMIT ?
        '''

        self.cursor.execute(query, (f'%{muscle}%', limit))
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert a database row to a dictionary"""
        columns = [col[0] for col in self.cursor.description]
        return {columns[i]: row[i] for i in range(len(columns))}

    def get_plan_summary(self, plan_id: int):
        """Get summary metrics for a plan"""
        query = '''
        SELECT 
            w.week_number,
            COUNT(DISTINCT w.day_of_week) as days_worked,
            COUNT(l.id) as exercises_completed,
            AVG(l.weight) as avg_weight
        FROM plan_workouts w
        LEFT JOIN workout_logs l ON w.id = l.plan_workout_id
        WHERE w.plan_id = ?
        GROUP BY w.week_number
        ORDER BY w.week_number
        '''
        self.cursor.execute(query, (plan_id,))
        return [self._row_to_dict(row) for row in self.cursor.fetchall()]

    def get_active_plans(self):
        """Get all active fitness plans"""
        self.cursor.execute('SELECT * FROM fitness_plans WHERE is_active = 1')
        return [self._row_to_dict(row) for row in self.cursor.fetchall()]

    def toggle_plan_status(self, plan_id: int, is_active: bool):
        """Toggle plan active status"""
        self.cursor.execute(
            'UPDATE fitness_plans SET is_active = ? WHERE id = ?',
            (is_active, plan_id)
        )
        self.conn.commit()

    def create_fitness_plan(self, name: str, goal: str, duration_weeks: int, plan_details: str = None) -> int:
        self.cursor.execute(
            'INSERT INTO fitness_plans (name, goal, duration_weeks, plan_details) VALUES (?, ?, ?, ?)',
            (name, goal, duration_weeks, plan_details)
        )
        plan_id = self.cursor.lastrowid

        # Generate workouts for the entire duration
        if goal == "Sports and Athletics":
            workout_types = {
                "Power": ["Plyometrics", "Olympic Weightlifting"],
                "Strength": ["Strength"],
                "Agility": ["Plyometrics"],
                "Core": ["Strength"],
                "Conditioning": ["Cardio"]
            }

            for week in range(1, duration_weeks + 1):
                for day in range(1, 9):  # 8 workouts per week
                    # Determine workout focus based on day
                    if day in [1, 5]:  # Power days
                        focus = "Power"
                    elif day in [2, 6]:  # Strength days
                        focus = "Strength"
                    elif day in [3, 7]:  # Agility/Core days
                        focus = "Agility" if week % 2 == 0 else "Core"
                    else:  # Conditioning days
                        focus = "Conditioning"

                    # Get exercises for this focus
                    exercises = []
                    for exercise_type in workout_types[focus]:
                        self.cursor.execute('''
                            SELECT * FROM exercises 
                            WHERE exercise_type = ? 
                            ORDER BY RANDOM() 
                            LIMIT ?''', (exercise_type, 3))
                        exercises.extend(self.cursor.fetchall())

                    # Add exercises to plan
                    for exercise in exercises:
                        sets = 3 if focus in ["Power", "Strength"] else 4
                        reps = 5 if focus == "Power" else 12 if focus == "Strength" else 15

                        self.cursor.execute('''
                            INSERT INTO plan_workouts 
                            (plan_id, exercise_id, day_of_week, week_number, target_sets, target_reps)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (plan_id, exercise[0], day, week, sets, reps))

        self.conn.commit()
        return plan_id

    def add_workout_to_plan(self, plan_id: int, exercise_id: int, day: int, week: int, sets: int, reps: int):
        self.cursor.execute(
            'INSERT INTO plan_workouts (plan_id, exercise_id, day_of_week, week_number, target_sets, target_reps) VALUES (?, ?, ?, ?, ?, ?)',
            (plan_id, exercise_id, day, week, sets, reps)
        )
        self.conn.commit()

    def get_fitness_plans(self):
        self.cursor.execute('SELECT * FROM fitness_plans')
        return [self._row_to_dict(row) for row in self.cursor.fetchall()]

    def get_plan_workouts(self, plan_id: int, week: int, day: int):
        query = '''
        SELECT pw.*, e.title, e.description, e.equipment, e.level
        FROM plan_workouts pw
        JOIN exercises e ON pw.exercise_id = e.id
        WHERE pw.plan_id = ? AND pw.week_number = ? AND pw.day_of_week = ?
        '''
        self.cursor.execute(query, (plan_id, week, day))
        return [self._row_to_dict(row) for row in self.cursor.fetchall()]

    def log_workout(self, plan_workout_id: int, sets: int, reps: int, weight: float):
        self.cursor.execute(
            'INSERT INTO workout_logs (plan_workout_id, sets_completed, reps_completed, weight) VALUES (?, ?, ?, ?)',
            (plan_workout_id, sets, reps, weight)
        )
        self.conn.commit()

    def update_plan_goal(self, plan_id: int, new_goal: str):
        """Update the goal of a fitness plan"""
        self.cursor.execute(
            'UPDATE fitness_plans SET goal = ? WHERE id = ?',
            (new_goal, plan_id)
        )
        self.conn.commit()

    def get_user_profile(self, user_id):
        """Get user profile from database. Returns default if not found."""
        # For now, return default values since we don't have user profiles table yet
        return {
            "experience_level": "Beginner",
            "age": 30,
            "weight": 70,  # kg
            "height": 175,  # cm
            "fitness_score": 3  # On a scale of 1-10
        }

    def close(self):
        """Close the database connection"""
        self.conn.close()