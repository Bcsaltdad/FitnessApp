class WorkoutPlanner:
  def __init__(self, db_connection):
      self.db = db_connection

  def generate_plan(self, user_details, plan_preferences):
      """
      Generate a comprehensive workout plan based on user details and preferences

      Parameters:
      - user_details: Dict containing user's fitness level, age, weight, limitations
      - plan_preferences: Dict containing goal, duration, equipment, etc.

      Returns: 
      - Complete workout plan structure with exercises, progression, and scheduling
      """
      # Extract key parameters
      goal = plan_preferences['goal']
      duration_weeks = plan_preferences['duration']
      workouts_per_week = plan_preferences['workouts_per_week']
      equipment = plan_preferences['equipment_access']
      limitations = plan_preferences['limitations']
      experience_level = user_details.get('experience_level', 'Beginner')

      # 1. Determine training split based on workouts per week and goal
      training_split = self._determine_training_split(workouts_per_week, goal)

      # 2. Select appropriate exercises for each training day
      workout_schedule = self._create_workout_schedule(training_split, equipment, limitations, experience_level, goal)

      # 3. Apply progressive overload pattern across the weeks
      progressive_plan = self._apply_progression(workout_schedule, duration_weeks, experience_level)

      # 4. Add deload weeks if program is longer than 4 weeks
      if duration_weeks > 4:
          progressive_plan = self._add_deload_weeks(progressive_plan, duration_weeks)

      # 5. Structure the complete plan
      complete_plan = self._structure_complete_plan(progressive_plan, plan_preferences)

      return complete_plan

  def _determine_training_split(self, workouts_per_week, goal):
      """Determine optimal training split based on frequency and goal"""

      training_splits = {
          # Sports and Athletics focused splits
          ("Sports and Athletics", 2): ["Full Body", "Full Body"],
          ("Sports and Athletics", 3): ["Upper Body", "Lower Body", "Full Body"],
          ("Sports and Athletics", 4): ["Upper Body", "Lower Body", "Cardio/Plyometrics", "Sport Specific"],
          ("Sports and Athletics", 5): ["Upper Push", "Lower Pull", "Rest/Recovery", "Upper Pull", "Lower Push"],

          # Body Building focused splits
          ("Body Building", 3): ["Push", "Pull", "Legs"],
          ("Body Building", 4): ["Upper Body", "Lower Body", "Upper Body", "Lower Body"],
          ("Body Building", 5): ["Chest/Triceps", "Back/Biceps", "Legs/Shoulders", "Upper Body", "Lower Body"],
          ("Body Building", 6): ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],

          # Body Weight Fitness focused splits
          ("Body Weight Fitness", 2): ["Upper Body", "Lower Body"],
          ("Body Weight Fitness", 3): ["Push", "Pull", "Legs/Core"],
          ("Body Weight Fitness", 4): ["Horizontal Push/Pull", "Legs", "Vertical Push/Pull", "Core/Conditioning"],

          # Weight Loss focused splits
          ("Weight Loss", 2): ["Full Body + HIIT", "Full Body + Steady Cardio"],
          ("Weight Loss", 3): ["Upper Body + HIIT", "Lower Body + HIIT", "Full Body + Steady Cardio"],
          ("Weight Loss", 4): ["Upper Push + HIIT", "Lower Body + Steady Cardio", "Upper Pull + HIIT", "Full Body Circuit"],

          # Mobility Exclusive focused splits
          ("Mobility Exclusive", 2): ["Upper Body Mobility", "Lower Body Mobility"],
          ("Mobility Exclusive", 3): ["Dynamic Mobility", "Static Stretching", "Joint Mobility"],
          ("Mobility Exclusive", 4): ["Upper Body Mobility", "Lower Body Mobility", "Full Body Flow", "Targeted Rehab"]
      }

      # Default to a balanced split if specific combination not found
      default_splits = {
          1: ["Full Body"],
          2: ["Upper Body", "Lower Body"],
          3: ["Push", "Pull", "Legs"],
          4: ["Upper Body", "Lower Body", "Upper Body", "Lower Body"],
          5: ["Chest/Triceps", "Back/Biceps", "Legs", "Shoulders/Arms", "Full Body"],
          6: ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],
          7: ["Chest", "Back", "Legs", "Shoulders", "Arms", "Full Body", "Active Recovery"]
      }

      # Cap at reasonable maximum
      if workouts_per_week > 7:
          workouts_per_week = 7

      # Get the appropriate split or use default
      split_key = (goal, workouts_per_week)
      if split_key in training_splits:
          return training_splits[split_key]
      else:
          return default_splits.get(workouts_per_week, ["Full Body"] * workouts_per_week)

  def _create_workout_schedule(self, training_split, equipment, limitations, experience_level, goal):
      """Create detailed workout schedule with specific exercises"""
      workout_schedule = []

      intensity_mapping = {
          "Beginner": {"sets": 3, "reps": "8-12", "intensity": 0.7},
          "Intermediate": {"sets": 4, "reps": "8-10", "intensity": 0.75},
          "Advanced": {"sets": 5, "reps": "6-12", "intensity": 0.8}
      }

      # Default to beginner if not specified
      training_params = intensity_mapping.get(experience_level, intensity_mapping["Beginner"])

      # For each day in the split, create a workout
      for day_focus in training_split:
          exercises = self._select_exercises_for_focus(day_focus, equipment, limitations, experience_level, goal)

          workout = {
              "focus": day_focus,
              "exercises": []
          }

          # Structure the exercises with appropriate sets, reps, etc.
          for exercise in exercises:
              # Adjust exercise parameters based on type and focus
              if exercise["type"] == "Compound":
                  sets = training_params["sets"]
                  reps = training_params["reps"] if "Strength" in goal else "8-12"
              elif exercise["type"] == "Isolation":
                  sets = max(3, training_params["sets"] - 1)
                  reps = "10-15" if "Body Building" in goal else "12-15"
              elif exercise["type"] == "Cardio":
                  sets = 1
                  reps = f"{15+5*int(experience_level=='Intermediate') + 10*int(experience_level=='Advanced')} minutes"
              else:  # Mobility/Flexibility
                  sets = 2 if experience_level == "Beginner" else 3
                  reps = "30-60 seconds"

              exercise_config = {
                  "id": exercise["id"],
                  "title": exercise["title"],
                  "sets": sets,
                  "reps": reps,
                  "rest": self._determine_rest_period(exercise["type"], goal),
                  "tempo": self._determine_tempo(exercise["type"], goal),
                  "notes": exercise.get("instructions", "")
              }

              workout["exercises"].append(exercise_config)

          workout_schedule.append(workout)

      return workout_schedule

  def _select_exercises_for_focus(self, focus, equipment, limitations, experience_level, goal):
      """Select appropriate exercises for a specific workout focus"""
      # In a real implementation, this would query the database
      # Here we'll outline the structure for exercise selection logic

      # Define parameters for exercise selection
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

      # Query database for exercises matching criteria
      # For each exercise type, get the appropriate number of exercises
      exercises = []

      # This would be a database query in the real implementation
      # For example:
      # compound_exercises = self.db.get_exercises(
      #     type="Compound", 
      #     focus=focus,
      #     equipment=equipment,
      #     experience_level=experience_level,
      #     exclude_limitations=limitations,
      #     limit=exercise_count["Compound"]
      # )
      # exercises.extend(compound_exercises)

      # Placeholder for now - in real implementation would be DB results
      # Here's the structure each exercise should have
      sample_exercises = [
          {"id": 1, "title": "Barbell Squat", "type": "Compound", "muscle_group": "Legs", 
           "equipment": "Barbell", "level": "Intermediate"},
          {"id": 2, "title": "Push-ups", "type": "Compound", "muscle_group": "Chest", 
           "equipment": "Bodyweight", "level": "Beginner"},
          {"id": 3, "title": "Bicep Curls", "type": "Isolation", "muscle_group": "Arms", 
           "equipment": "Dumbbells", "level": "Beginner"}
      ]

      # In reality, this would be populated from database queries
      return sample_exercises[:sum(exercise_count.values())]

  def _determine_rest_period(self, exercise_type, goal):
      """Determine appropriate rest periods based on exercise type and goal"""
      if exercise_type == "Compound":
          if "Strength" in goal or "Body Building" in goal:
              return "2-3 minutes"
          else:
              return "60-90 seconds"
      elif exercise_type == "Isolation":
          return "60-90 seconds" if "Body Building" in goal else "30-60 seconds"
      elif exercise_type == "Cardio":
          return "Minimal rest"
      else:  # Mobility
          return "30 seconds"

  def _determine_tempo(self, exercise_type, goal):
      """Determine appropriate tempo based on exercise type and goal"""
      if "Strength" in goal:
          return "2-0-2" if exercise_type == "Compound" else "2-0-1"
      elif "Body Building" in goal:
          return "3-1-2"  # Slow eccentric, pause, controlled concentric
      elif "Sports" in goal:
          return "1-0-1" if exercise_type == "Compound" else "2-0-2"
      else:
          return "2-0-2"  # Controlled default tempo

  def _apply_progression(self, workout_schedule, duration_weeks, experience_level):
      """Apply progressive overload pattern across weeks"""
      progressive_plan = []

      # Define progression patterns based on experience level
      progression_patterns = {
          "Beginner": {
              "volume_increase": 0.1,  # 10% volume increase per week
              "intensity_increase": 0.05,  # 5% intensity increase per week
              "deload_frequency": 4,  # Deload every 4 weeks
              "deload_reduction": 0.4,  # Reduce by 40% during deload
          },
          "Intermediate": {
              "volume_increase": 0.07,
              "intensity_increase": 0.07,
              "deload_frequency": 4,
              "deload_reduction": 0.3,
          },
          "Advanced": {
              "volume_increase": 0.05,
              "intensity_increase": 0.1,
              "deload_frequency": 3,
              "deload_reduction": 0.25,
          }
      }

      pattern = progression_patterns.get(experience_level, progression_patterns["Beginner"])

      # For each week, create a modified version of the base workout
      for week in range(1, duration_weeks + 1):
          is_deload = week % pattern["deload_frequency"] == 0
          week_modifier = pattern["deload_reduction"] if is_deload else (
              1 + (week % pattern["deload_frequency"]) * 
              (pattern["volume_increase"] if week <= 2 else pattern["intensity_increase"])
          )

          week_plan = []
          for day_plan in workout_schedule:
              # Create a deep copy of the day's workout
              day_copy = {
                  "focus": day_plan["focus"],
                  "exercises": []
              }

              for exercise in day_plan["exercises"]:
                  # Apply progression
                  exercise_copy = exercise.copy()

                  # For regular weeks, progress either volume or intensity
                  if not is_deload:
                      if week % 2 == 1:  # Odd weeks - increase volume (sets/reps)
                          # Increase sets if compound movement after week 2
                          if week > 2 and exercise["title"].lower() in ["squat", "deadlift", "bench press", "overhead press"]:
                              exercise_copy["sets"] = min(exercise["sets"] + 1, 6)  # Cap at 6 sets

                          # Otherwise manipulate the rep range
                          if isinstance(exercise["reps"], str) and "-" in exercise["reps"]:
                              min_reps, max_reps = map(int, exercise["reps"].split("-"))
                              new_min = min(min_reps + 1, max_reps)
                              new_max = min(max_reps + 2, 20)  # Cap at 20 reps
                              exercise_copy["reps"] = f"{new_min}-{new_max}"
                      else:  # Even weeks - focus on intensity/load
                          exercise_copy["notes"] += f" Increase weight by {5+5*int(experience_level!='Beginner')}% from previous week."
                  else:
                      # Deload week - reduce volume but maintain some intensity
                      if isinstance(exercise_copy["sets"], int):
                          exercise_copy["sets"] = max(2, int(exercise_copy["sets"] * 0.6))

                      if isinstance(exercise["reps"], str) and "-" in exercise["reps"]:
                          min_reps, max_reps = map(int, exercise["reps"].split("-"))
                          exercise_copy["reps"] = f"{min_reps}-{min_reps+2}"

                      exercise_copy["notes"] += " DELOAD WEEK: Reduce weights by 10-15% but maintain good form."

                  day_copy["exercises"].append(exercise_copy)

              week_plan.append(day_copy)

          progressive_plan.append({
              "week": week,
              "is_deload": is_deload,
              "workouts": week_plan
          })

      return progressive_plan

  def _add_deload_weeks(self, progressive_plan, duration_weeks):
      """Add appropriate deload weeks based on program duration"""
      # This is handled in the _apply_progression method now
      return progressive_plan

  def _structure_complete_plan(self, progressive_plan, plan_preferences):
      """Package the complete plan with all necessary details"""
      return {
          "name": plan_preferences.get("name", "Custom Fitness Plan"),
          "goal": plan_preferences["goal"],
          "duration_weeks": plan_preferences["duration"],
          "workouts_per_week": plan_preferences["workouts_per_week"],
          "equipment": plan_preferences["equipment_access"],
          "weekly_schedule": progressive_plan,
          "created_date": datetime.now().strftime("%Y-%m-%d"),
          "last_updated": datetime.now().strftime("%Y-%m-%d")
      }