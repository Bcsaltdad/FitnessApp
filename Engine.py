import random
from datetime import datetime, timedelta

class WorkoutRecommender:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_daily_recommendation(self, user_id, plan_id=None):
        """
        Generate a personalized daily workout recommendation

        Parameters:
        - user_id: User ID
        - plan_id: Optional plan ID to use as base

        Returns:
        - Dictionary with recommended workout
        """
        # Get user profile and active plans
        user_profile = self.db.get_user_profile(user_id)
        active_plans = self.db.get_active_plans()

        if not plan_id and active_plans:
            plan_id = active_plans[0]['id']

        if not plan_id:
            return self._generate_default_workout(user_profile)

        # Get current date information
        today = datetime.now()
        weekday = today.weekday() + 1  # Convert to 1-7 range (Monday = 1)

        # Calculate which week we're in for this plan
        self.db.cursor.execute(
            "SELECT created_date FROM fitness_plans WHERE id = ?",
            (plan_id,)
        )
        plan_start = self.db.cursor.fetchone()

        if not plan_start:
            return self._generate_default_workout(user_profile)

        start_date = datetime.strptime(plan_start['created_date'], "%Y-%m-%d")
        days_since_start = (today - start_date).days
        current_week = (days_since_start // 7) + 1

        # Get workouts for this day in current week
        self.db.cursor.execute(
            """
            SELECT * FROM plan_workouts 
            WHERE plan_id = ? AND week = ? AND day = ?
            """,
            (plan_id, current_week, weekday)
        )
        workouts = self.db.cursor.fetchall()

        if not workouts:
            # If no workouts scheduled for today, check if we need a recovery focus
            if self._needs_recovery(user_id):
                return self._generate_recovery_workout(user_profile)
            else:
                # Suggest a workout from another day this week
                self.db.cursor.execute(
                    """
                    SELECT * FROM plan_workouts 
                    WHERE plan_id = ? AND week = ?
                    ORDER BY RANDOM() LIMIT 1
                    """,
                    (plan_id, current_week)
                )
                alternative = self.db.cursor.fetchone()

                if alternative:
                    # Find all workouts for this day
                    self.db.cursor.execute(
                        """
                        SELECT * FROM plan_workouts 
                        WHERE plan_id = ? AND week = ? AND day = ?
                        """,
                        (plan_id, current_week, alternative['day'])
                    )
                    alt_workouts = self.db.cursor.fetchall()

                    day_names = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 
                               4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}

                    return {
                        'type': 'alternative',
                        'message': f"No workout scheduled for today. Here's your {day_names[alternative['day']]} workout instead:",
                        'day': day_names[alternative['day']],
                        'workouts': alt_workouts
                    }

        # Check if user has already completed today's workout
        for workout in workouts:
            self.db.cursor.execute(
                """
                SELECT COUNT(*) FROM workout_logs
                WHERE workout_id = ? AND date = date('now')
                """,
                (workout['id'],)
            )
            if self.db.cursor.fetchone()[0] > 0:
                # User already did this workout today
                workouts.remove(workout)

        if not workouts:
            return {
                'type': 'completed',
                'message': "You've completed all scheduled workouts for today! Would you like a bonus workout?",
                'bonus_workout': self._generate_bonus_workout(user_profile, plan_id)
            }

        # Get exercise details for each workout
        result_workouts = []
        for workout in workouts:
            self.db.cursor.execute(
                """
                SELECT * FROM exercises WHERE id = ?
                """,
                (workout['exercise_id'],)
            )
            exercise = self.db.cursor.fetchone()

            if exercise:
                workout_detail = dict(workout)
                workout_detail.update({
                    'exercise_type': exercise['type'],
                    'equipment': exercise['equipment'],
                    'muscle_group': exercise['muscle_group'],
                    'level': exercise['level']
                })
                result_workouts.append(workout_detail)

        # Get progress tracking info
        progress_tracker = self.db.get_progress_tracker()
        recent_workouts = self._get_recent_workouts(user_id)

        # Generate personalized adjustment recommendations
        adjustments = []
        for workout in result_workouts:
            # Check if user has been progressing well on this exercise
            self.db.cursor.execute(
                """
                SELECT progress_rating FROM progression_tracking
                WHERE user_id = ? AND exercise_id = ?
                ORDER BY date DESC LIMIT 1
                """,
                (user_id, workout['exercise_id'])
            )
            rating = self.db.cursor.fetchone()

            if rating and rating[0] > 3:
                # Good progress, recommend increasing weight
                adjustments.append(f"Increase weight for {workout['title']} by 5-10% today")
            elif rating and rating[0] < -2:
                # Poor progress, recommend modifying approach
                adjustments.append(f"Try different rep range for {workout['title']} today (e.g., 5x5 instead of 3x10)")

        return {
            'type': 'scheduled',
            'message': "Here's your workout for today:",
            'workouts': result_workouts,
            'adjustments': adjustments,
            'muscle_recovery': self._get_muscle_recovery_status(user_id)
        }

    def _needs_recovery(self, user_id):
        """Check if user needs a recovery day based on recent workout history"""
        # Get workouts from the last 3 days
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        self.db.cursor.execute(
            """
            SELECT COUNT(*) FROM workout_logs
            WHERE date >= ? AND user_id = ?
            """,
            (three_days_ago, user_id)
        )
        recent_workout_count = self.db.cursor.fetchone()[0]

        # If more than 5 workouts in last 3 days, probably needs recovery
        return recent_workout_count > 5

    def _generate_recovery_workout(self, user_profile):
        """Generate a recovery-focused workout"""
        recovery_options = [
            {
                'title': 'Active Recovery',
                'description': 'Low-intensity movement to promote recovery',
                'exercises': [
                    {'title': 'Light Walking', 'instructions': 'Walk at an easy pace for 20-30 minutes'},
                    {'title': 'Dynamic Stretching', 'instructions': 'Full body dynamic stretches, 30 seconds each movement'},
                    {'title': 'Foam Rolling', 'instructions': 'Roll major muscle groups, 1 minute per area'},
                ]
            },
            {
                'title': 'Mobility Focus',
                'description': 'Improve joint mobility and flexibility',
                'exercises': [
                    {'title': 'Hip Mobility Flow', 'instructions': '5 minutes of hip circles, lunges, and squats'},
                    {'title': 'Shoulder Mobility', 'instructions': 'Arm circles, wall slides, and band pull-aparts'},
                    {'title': 'Ankle Mobility', 'instructions': 'Ankle circles, calf stretches, and toe raises'},
                ]
            },
            {
                'title': 'Light Cardio',
                'description': 'Improve circulation without muscle stress',
                'exercises': [
                    {'title': 'Easy Cycling', 'instructions': '15-20 minutes at low resistance'},
                    {'title': 'Swimming', 'instructions': 'Easy laps for 10-15 minutes, focus on technique'},
                    {'title': 'Elliptical', 'instructions': '10-15 minutes at low intensity'},
                ]
            }
        ]

        selected = random.choice(recovery_options)

        return {
            'type': 'recovery',
            'message': "You've been working hard! Here's a recovery workout:",
            'workout': selected
        }

    def _generate_bonus_workout(self, user_profile, plan_id):
        """Generate a bonus workout after completing scheduled training"""

        # Get plan's goal
        self.db.cursor.execute(
            "SELECT goal FROM fitness_plans WHERE id = ?",
            (plan_id,)
        )
        plan = self.db.cursor.fetchone()
        goal = plan['goal'] if plan else 'General Fitness'

        # Get recently worked muscle groups to avoid
        recent_muscles = self._get_recent_muscle_groups(1)  # User ID 1

        # Determine appropriate bonus workout type
        if 'Body Building' in goal:
            # Get a lagging muscle group that hasn't been hit recently
            potential_groups = ['Arms', 'Shoulders', 'Calves', 'Abs']
            target_group = next((g for g in potential_groups if g not in recent_muscles), 'Arms')

            return {
                'title': f'{target_group} Specialization',
                'description': f'Focus on {target_group} with high volume',
                'exercises': self._get_exercises_for_muscle_group(target_group, 4)
            }
        elif 'Weight Loss' in goal:
            return {
                'title': 'Calorie Burner',
                'description': 'High-intensity interval training to burn extra calories',
                'exercises': [
                    {'title': 'HIIT Circuit', 'instructions': '30 seconds work, 15 seconds rest for 5 exercises, 4 rounds'},
                    {'title': 'Jump Rope', 'instructions': '3 sets of 1 minute fast jumping'},
                    {'title': 'Mountain Climbers', 'instructions': '3 sets of 30 seconds'},
                ]
            }
        else:
            return {
                'title': 'Core & Mobility',
                'description': 'Strengthen your core and improve overall mobility',
                'exercises': [
                    {'title': 'Plank Variations', 'instructions': '3 sets of 30-45 seconds each variation'},
                    {'title': 'Russian Twists', 'instructions': '3 sets of 20 reps'},
                    {'title': 'Hip Mobility Flow', 'instructions': '5 minutes of dynamic hip movements'},
                ]
            }

    def _get_exercises_for_muscle_group(self, muscle_group, count=3):
        """Get exercises targeting a specific muscle group"""
        self.db.cursor.execute(
            """
            SELECT * FROM exercises
            WHERE muscle_group = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (muscle_group, count)
        )
        exercises = self.db.cursor.fetchall()

        # Format exercises for display
        return [{'title': ex['title'], 'instructions': ex.get('instructions', '')} for ex in exercises]

    def _get_recent_muscle_groups(self, user_id, days=2):
        """Get muscle groups worked in the last few days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        self.db.cursor.execute(
            """
            SELECT DISTINCT e.muscle_group
            FROM workout_logs wl
            JOIN plan_workouts pw ON wl.workout_id = pw.id
            JOIN exercises e ON pw.exercise_id = e.id
            WHERE wl.date >= ? AND pw.plan_id IN (
                SELECT id FROM fitness_plans WHERE user_id = ?
            )
            """,
            (cutoff_date, user_id)
        )

        return [row[0] for row in self.db.cursor.fetchall() if row[0]]

    def _get_muscle_recovery_status(self, user_id):
        """Get recovery status of major muscle groups"""
        muscle_groups = ['Chest', 'Back', 'Legs', 'Shoulders', 'Arms', 'Core']
        recovery_status = {}

        for muscle in muscle_groups:
            # Check when this muscle was last trained
            self.db.cursor.execute(
                """
                SELECT MAX(wl.date) 
                FROM workout_logs wl
                JOIN plan_workouts pw ON wl.workout_id = pw.id
                JOIN exercises e ON pw.exercise_id = e.id
                WHERE e.muscle_group = ? AND wl.user_id = ?
                """,
                (muscle, user_id)
            )

            last_trained = self.db.cursor.fetchone()[0]

            if not last_trained:
                recovery_status[muscle] = "Ready"
                continue

            last_date = datetime.strptime(last_trained, "%Y-%m-%d")
            days_since = (datetime.now() - last_date).days
            recovery_status[muscle] = f"{days_since} days"

        return recovery_status
    def _get_recent_workouts(self, user_id):
        pass
    def _generate_default_workout(self, user_profile):
        pass


class WorkoutEngine:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_workout_details(self, workouts, user_id=1):
        """Get detailed workout information with progress tracking"""
        result_workouts = []
        for workout in workouts:
            self.db.cursor.execute(
                """
                SELECT * FROM exercises WHERE id = ?
                """,
                (workout['exercise_id'],)
            )
            exercise = self.db.cursor.fetchone()

            if exercise:
                workout_detail = dict(workout)
                workout_detail.update({
                    'exercise_type': exercise['type'],
                    'equipment': exercise['equipment'],
                    'muscle_group': exercise['muscle_group'],
                    'level': exercise['level']
                })
                result_workouts.append(workout_detail)

        return result_workouts

    def calculate_suggested_progression(self, workout_history):
        """Calculate suggested progression based on workout history"""
        if not workout_history:
            return {
                'sets': 3,
                'reps': '8-12',
                'weight': 0,
                'notes': 'Start with a weight you can handle for all sets'
            }

        last_workout = workout_history[-1]
        completed_all = last_workout['sets_completed'] >= last_workout['target_sets']
        weight_used = last_workout.get('weight', 0)

        if completed_all:
            return {
                'sets': last_workout['sets_completed'],
                'reps': last_workout['reps_completed'],
                'weight': weight_used * 1.05,  # 5% increase
                'notes': 'Increase weight by 5% from last session'
            }
        else:
            return {
                'sets': last_workout['target_sets'],
                'reps': last_workout['target_reps'],
                'weight': weight_used,
                'notes': 'Maintain current weight and focus on form'
            }