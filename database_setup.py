
import sqlite3
import pandas as pd
import json

def setup_database():
    # Connect to SQLite database
    conn = sqlite3.connect('fitness.db')
    cursor = conn.cursor()
    
    # Create exercises table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        exercise_type TEXT,
        body_part TEXT,
        equipment TEXT,
        level TEXT,
        rating FLOAT,
        rating_desc TEXT
    )''')
    
    # Create muscles table for target muscles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS target_muscles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id INTEGER,
        muscle_name TEXT,
        is_primary BOOLEAN,
        FOREIGN KEY (exercise_id) REFERENCES exercises (id)
    )''')
    
    # Create instructions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exercise_instructions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id INTEGER,
        step_number INTEGER,
        instruction TEXT,
        FOREIGN KEY (exercise_id) REFERENCES exercises (id)
    )''')

    # Create fitness plans table with plan_details column
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fitness_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        goal TEXT,
        duration_weeks INTEGER,
        plan_details TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create plan workouts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plan_workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        exercise_id INTEGER,
        day_of_week INTEGER,
        week_number INTEGER,
        target_sets INTEGER,
        target_reps INTEGER,
        FOREIGN KEY (plan_id) REFERENCES fitness_plans (id),
        FOREIGN KEY (exercise_id) REFERENCES exercises (id)
    )''')
    
    # Create workout logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workout_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_workout_id INTEGER,
        sets_completed INTEGER,
        reps_completed INTEGER,
        weight FLOAT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_workout_id) REFERENCES plan_workouts (id)
    )''')
    
    # Create progression tracking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS progression_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exercise_id INTEGER,
        progress_rating FLOAT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exercise_id) REFERENCES exercises (id)
    )''')

    conn.commit()
    return conn, cursor

def import_exercise_data(conn, cursor, csv_file):
    # Read CSV file
    df = pd.read_csv(csv_file)
    
    # Insert exercises
    for _, row in df.iterrows():
        cursor.execute('''
        INSERT INTO exercises (title, description, exercise_type, body_part, equipment, level, rating, rating_desc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['Title'],
            row['Desc'],
            row['Type'],
            row['BodyPart'],
            row['Equipment'],
            row['Level'],
            row['Rating'],
            row['RatingDesc']
        ))
        
        exercise_id = cursor.lastrowid
        
        # Handle instructions if they exist
        if isinstance(row.get('instructions'), str):
            try:
                instructions = eval(row['instructions'])
                for i, instruction in enumerate(instructions, 1):
                    cursor.execute('''
                    INSERT INTO exercise_instructions (exercise_id, step_number, instruction)
                    VALUES (?, ?, ?)
                    ''', (exercise_id, i, instruction))
            except:
                pass

    conn.commit()

if __name__ == "__main__":
    conn, cursor = setup_database()
    import_exercise_data(conn, cursor, 'attached_assets/workout_data.csv')
    print("Database setup complete!")
def get_exercises_by_criteria(self, criteria):
    """
    Get exercises based on multiple criteria

    Parameters:
    - criteria: Dict with keys like type, focus, equipment, level, etc.

    Returns:
    - List of exercise dictionaries
    """
    query_parts = []
    params = []

    if 'type' in criteria:
        query_parts.append("type = ?")
        params.append(criteria['type'])

    if 'muscle_group' in criteria:
        query_parts.append("muscle_group = ?")
        params.append(criteria['muscle_group'])

    if 'equipment' in criteria:
        # Handle equipment list
        if isinstance(criteria['equipment'], list):
            placeholders = ', '.join(['?'] * len(criteria['equipment']))
            query_parts.append(f"equipment IN ({placeholders})")
            params.extend(criteria['equipment'])
        else:
            query_parts.append("equipment = ?")
            params.append(criteria['equipment'])

    if 'level' in criteria:
        query_parts.append("level = ?")
        params.append(criteria['level'])

    if 'exclude_limitations' in criteria and criteria['exclude_limitations']:
        limitations = criteria['exclude_limitations']
        if limitations and limitations != ['None']:
            # Exclude exercises that have contraindications for user limitations
            placeholders = ', '.join(['?'] * len(limitations))
            query_parts.append(f"id NOT IN (SELECT exercise_id FROM exercise_contraindications WHERE limitation IN ({placeholders}))")
            params.extend(limitations)

    # Build the WHERE clause
    where_clause = " AND ".join(query_parts) if query_parts else "1=1"

    # Add limit if specified
    limit_clause = f" LIMIT {criteria['limit']}" if 'limit' in criteria else ""

    # Execute query
    query = f"SELECT * FROM exercises WHERE {where_clause}{limit_clause}"
    self.cursor.execute(query, params)
    return self.cursor.fetchall()

def create_fitness_plan(self, name, goal, duration_weeks, details_json, user_id=1):
    """
    Create a new fitness plan with intelligent workout structuring

    Parameters:
    - name: Plan name
    - goal: Primary fitness goal
    - duration_weeks: Program duration in weeks
    - details_json: JSON string with plan preferences
    - user_id: User ID (default 1 if no auth system)

    Returns:
    - plan_id: ID of the newly created plan
    """
    # Insert basic plan info first
    self.cursor.execute(
        "INSERT INTO fitness_plans (user_id, name, goal, duration_weeks, details, created_date) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (user_id, name, goal, duration_weeks, details_json)
    )
    plan_id = self.cursor.lastrowid
    self.conn.commit()

    # Parse details
    details = json.loads(details_json)

    # Get user profile if available (for experience level, age, etc.)
    user_profile = self.get_user_profile(user_id)

    # Initialize workout planner
    planner = WorkoutPlanner(self)

    # Generate the plan
    complete_plan = planner.generate_plan(user_profile, {
        "name": name,
        "goal": goal,
        "duration": duration_weeks,
        "workouts_per_week": details["workouts_per_week"],
        "equipment_access": details["equipment_access"],
        "limitations": details["limitations"]
    })

    # Store workouts in the database
    self._store_plan_workouts(plan_id, complete_plan)

    return plan_id

def _store_plan_workouts(self, plan_id, complete_plan):
    """Store the generated workouts in the database"""
    weekly_schedule = complete_plan["weekly_schedule"]

    for week_data in weekly_schedule:
        week_number = week_data["week"]

        for day_index, workout in enumerate(week_data["workouts"], 1):
            day_number = day_index  # Map to days 1-7 (Mon-Sun)

            for exercise in workout["exercises"]:
                # Convert rep ranges to target reps (use the max of range)
                target_reps = exercise["reps"]
                if isinstance(target_reps, str) and "-" in target_reps:
                    _, max_reps = map(int, target_reps.split("-"))
                    target_reps = max_reps

                # Store the workout in plan_workouts table
                self.cursor.execute(
                    """
                    INSERT INTO plan_workouts 
                    (plan_id, exercise_id, week, day, title, description, target_sets, target_reps, instructions) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id, 
                        exercise["id"],
                        week_number,
                        day_number,
                        exercise["title"],
                        f"{workout['focus']} - {exercise['title']}",
                        exercise["sets"],
                        target_reps,
                        f"{exercise.get('notes', '')} Rest: {exercise['rest']}, Tempo: {exercise['tempo']}"
                    )
                )

    self.conn.commit()

def get_user_profile(self, user_id):
    """Get user profile for personalization"""
    # In a real implementation, this would query a user_profiles table
    # For now, return default values
    return {
        "experience_level": "Beginner",
        "age": 30,
        "weight": 70,  # kg
        "height": 175,  # cm
        "fitness_score": 3  # On a scale of 1-10
    }

def get_plan_summary(self, plan_id):
    """Get detailed plan summary with progress tracking"""
    weeks = []
    self.cursor.execute(
        """
        SELECT MAX(week) FROM plan_workouts WHERE plan_id = ?
        """, 
        (plan_id,)
    )
    max_weeks = self.cursor.fetchone()[0] or 0

    for week in range(1, max_weeks + 1):
        # Get completed workouts for this week
        self.cursor.execute(
            """
            SELECT COUNT(*) FROM workout_logs 
            JOIN plan_workouts ON workout_logs.workout_id = plan_workouts.id
            WHERE plan_workouts.plan_id = ? AND plan_workouts.week = ?
            """,
            (plan_id, week)
        )
        completed = self.cursor.fetchone()[0] or 0

        # Get average weight for this week (convert to kg in DB, display as lbs in UI)
        self.cursor.execute(
            """
            SELECT AVG(weight) FROM workout_logs 
            JOIN plan_workouts ON workout_logs.workout_id = plan_workouts.id
            WHERE plan_workouts.plan_id = ? AND plan_workouts.week = ? AND weight > 0
            """,
            (plan_id, week)
        )
        avg_weight = self.cursor.fetchone()[0] or 0

        # Count unique days worked
        self.cursor.execute(
            """
            SELECT COUNT(DISTINCT day) FROM workout_logs 
            JOIN plan_workouts ON workout_logs.workout_id = plan_workouts.id
            WHERE plan_workouts.plan_id = ? AND plan_workouts.week = ? 
            """,
            (plan_id, week)
        )
        days_worked = self.cursor.fetchone()[0] or 0

        weeks.append({
            "week": week,
            "exercises_completed": completed,
            "avg_weight": avg_weight,
            "days_worked": days_worked,
            "progress_pct": self._calculate_week_progress(plan_id, week)
        })

    return weeks

def _calculate_week_progress(self, plan_id, week):
    """Calculate percentage progress for a specific week"""
    self.cursor.execute(
        """
        SELECT COUNT(*) FROM plan_workouts 
        WHERE plan_id = ? AND week = ?
        """,
        (plan_id, week)
    )
    total = self.cursor.fetchone()[0] or 1  # Avoid division by zero

    self.cursor.execute(
        """
        SELECT COUNT(*) FROM workout_logs 
        JOIN plan_workouts ON workout_logs.workout_id = plan_workouts.id
        WHERE plan_workouts.plan_id = ? AND plan_workouts.week = ?
        """,
        (plan_id, week)
    )
    completed = self.cursor.fetchone()[0] or 0

    return (completed / total) * 100