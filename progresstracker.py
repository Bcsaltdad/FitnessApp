import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class ProgressTracker:
    def __init__(self, db_connection):
        self.db = db_connection

    def calculate_one_rep_max(self, weight, reps):
        """
        Calculate estimated 1RM using the Brzycki formula
        Formula: 1RM = Weight × (36 / (37 - Reps))

        Parameters:
        - weight: Weight used in kg
        - reps: Number of reps performed

        Returns:
        - Estimated 1RM
        """
        if reps == 1:
            return weight
        elif reps > 36:  # Formula breaks down at very high rep ranges
            return weight * 2  # Rough estimate
        else:
            return weight * (36 / (37 - reps))

    def analyze_workout_history(self, user_id, exercise_id, timeframe_days=90):
        """
        Analyze workout history for a specific exercise

        Parameters:
        - user_id: User ID
        - exercise_id: Exercise ID
        - timeframe_days: Number of days to look back

        Returns:
        - Dictionary with analysis results
        """
        # Get workout logs for this exercise within timeframe
        cutoff_date = (datetime.now() - timedelta(days=timeframe_days)).strftime("%Y-%m-%d")

        query = """
        SELECT wl.*, pw.target_sets, pw.target_reps, pw.week, pw.day
        FROM workout_logs wl
        JOIN plan_workouts pw ON wl.workout_id = pw.id
        JOIN fitness_plans fp ON pw.plan_id = fp.id
        WHERE fp.user_id = ? AND pw.exercise_id = ? AND wl.date >= ?
        ORDER BY wl.date
        """

        self.db.cursor.execute(query, (user_id, exercise_id, cutoff_date))
        logs = self.db.cursor.fetchall()

        if not logs:
            return {"status": "No data", "message": "No workout history found for this exercise"}

        # Convert to pandas DataFrame for easier analysis
        logs_df = pd.DataFrame(logs)

        # Calculate 1RM for each workout
        logs_df['one_rep_max'] = logs_df.apply(
            lambda row: self.calculate_one_rep_max(row['weight'], row['reps']), 
            axis=1
        )

        # Calculate volume for each workout (sets * reps * weight)
        logs_df['volume'] = logs_df['sets'] * logs_df['reps'] * logs_df['weight']

        # Group by date to get daily stats
        daily_stats = logs_df.groupby('date').agg({
            'one_rep_max': 'max',
            'volume': 'sum',
            'sets': 'sum',
            'reps': ['mean', 'sum']
        })

        # Flatten the MultiIndex columns
        daily_stats.columns = ['_'.join(col).strip() for col in daily_stats.columns.values]

        # Calculate trends
        strength_trend = self._calculate_trend(daily_stats['one_rep_max'])
        volume_trend = self._calculate_trend(daily_stats['volume'])

        # Get best workout
        best_workout_idx = daily_stats['one_rep_max'].idxmax()
        best_workout = daily_stats.loc[best_workout_idx].to_dict()

        # Get most recent workout
        recent_workout = daily_stats.iloc[-1].to_dict()

        # Calculate progression
        progression = {
            'strength_change_pct': (recent_workout['one_rep_max'] / daily_stats['one_rep_max'].iloc[0] - 1) * 100 
                if daily_stats['one_rep_max'].iloc[0] > 0 else 0,
            'volume_change_pct': (recent_workout['volume'] / daily_stats['volume'].iloc[0] - 1) * 100
                if daily_stats['volume'].iloc[0] > 0 else 0,
            'strength_trend': strength_trend,
            'volume_trend': volume_trend,
            'consistency': len(daily_stats) / (timeframe_days / 7)  # Workouts per week
        }

        # Save the progression data
        self._save_progression_data(user_id, exercise_id, recent_workout['one_rep_max'], 
                                  recent_workout['volume'], progression)

        # Return comprehensive analysis results
        return {
            'status': 'success',
            'history_length_days': (datetime.strptime(logs_df['date'].max(), "%Y-%m-%d") - 
                                   datetime.strptime(logs_df['date'].min(), "%Y-%m-%d")).days + 1,
            'workout_count': len(daily_stats),
            'current_1rm': recent_workout['one_rep_max'],
            'best_1rm': best_workout['one_rep_max'],
            'best_workout_date': best_workout_idx,
            'average_volume': daily_stats['volume'].mean(),
            'progression': progression,
            'recommendations': self._generate_recommendations(progression, logs_df)
        }

    def _calculate_trend(self, series):
        """Calculate linear trend of a time series"""
        if len(series) < 2:
            return 0

        x = np.arange(len(series))
        y = series.values

        # Linear regression to find slope
        slope, _ = np.polyfit(x, y, 1)

        # Normalize to percentage of initial value
        if series.iloc[0] > 0:
            return (slope / series.iloc[0]) * 100
        return 0

    def _save_progression_data(self, user_id, exercise_id, one_rep_max, volume, progression):
        """Save progression data to database"""
        # Progress rating from -5 to 5 based on trends
        progress_rating = min(5, max(-5, int(progression['strength_trend'] / 5)))

        self.db.cursor.execute(
            """
            INSERT INTO progression_tracking (user_id, exercise_id, date, one_rep_max, volume_total, progress_rating)
            VALUES (?, ?, date('now'), ?, ?, ?)
            """,
            (user_id, exercise_id, one_rep_max, volume, progress_rating)
        )
        self.db.conn.commit()

    def _generate_recommendations(self, progression, logs_df):
        """Generate training recommendations based on progress"""
        recommendations = []

        # Based on strength trend
        if progression['strength_trend'] < -2:
            recommendations.append("Strength is declining. Consider reducing volume and focusing on quality sets.")
        elif progression['strength_trend'] < 0:
            recommendations.append("Strength progress has plateaued. Try varying rep ranges or adding an intensity technique.")
        elif progression['strength_trend'] > 5:
            recommendations.append("Great strength progress! Consider slightly increasing weight on your next session.")

        # Based on volume trend
        if progression['volume_trend'] < -5:
            recommendations.append("Training volume has decreased significantly. Are you getting enough recovery?")
        elif progression['volume_trend'] > 10:
            recommendations.append("Volume is increasing well. Ensure you're maintaining good form with the increased workload.")

        # Based on workout frequency
        if progression['consistency'] < 0.5:  # Less than 0.5 workouts per week targeting this exercise
            recommendations.append("Consider increasing training frequency for better progress.")

        # Based on rep ranges
        if logs_df['reps'].mean() > 15:
            recommendations.append("Your rep ranges are high. For strength, consider including some lower rep sets (4-6 reps).")
        elif logs_df['reps'].mean() < 5:
            recommendations.append("Your rep ranges are low. For muscle growth, include some moderate rep sets (8-12 reps).")

        return recommendations

    def generate_progress_report(self, user_id, plan_id):
        """Generate comprehensive progress report for a training plan"""
        # Get plan details
        self.db.cursor.execute(
            "SELECT * FROM fitness_plans WHERE id = ?",
            (plan_id,)
        )
        plan = self.db.cursor.fetchone()

        if not plan:
            return {"status": "error", "message": "Plan not found"}

        # Get all unique exercises in this plan
        self.db.cursor.execute(
            """
            SELECT DISTINCT exercise_id 
            FROM plan_workouts 
            WHERE plan_id = ?
            """,
            (plan_id,)
        )
        exercise_ids = [row[0] for row in self.db.cursor.fetchall()]

        # Analyze progress for each exercise
        exercise_progress = {}
        for ex_id in exercise_ids:
            # Get exercise details
            self.db.cursor.execute(
                "SELECT title FROM exercises WHERE id = ?",
                (ex_id,)
            )
            exercise = self.db.cursor.fetchone()

            if exercise:
                progress = self.analyze_workout_history(user_id, ex_id)
                exercise_progress[exercise['title']] = progress

        # Calculate overall metrics
        strength_trends = [p['progression']['strength_trend'] for p in exercise_progress.values() 
                          if p['status'] == 'success']

        overall_progress = {
            'avg_strength_trend': sum(strength_trends) / len(strength_trends) if strength_trends else 0,
            'exercise_count': len(exercise_progress),
            'start_date': plan['created_date'],
            'days_active': (datetime.now() - datetime.strptime(plan['created_date'], "%Y-%m-%d")).days
        }

        # Generate key recommendations
        all_recommendations = []
        for exercise, progress in exercise_progress.items():
            if progress['status'] == 'success' and 'recommendations' in progress:
                for rec in progress['recommendations']:
                    all_recommendations.append(f"{exercise}: {rec}")

        # Limit to top 5 recommendations
        key_recommendations = all_recommendations[:5]

        return {
            'status': 'success',
            'plan_name': plan['name'],
            'plan_goal': plan['goal'],
            'overall_progress': overall_progress,
            'exercise_progress': exercise_progress,
            'key_recommendations': key_recommendations
        }

# Then add this to your ExerciseDatabase class
def get_progress_tracker(self):
    """Get progress tracker instance"""
    return ProgressTracker(self)