from flask import Flask, render_template, request, jsonify
import json
import os
import random
from datetime import datetime
import uuid  # for unique quiz IDs

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'
DEFAULT_QUIZ_DURATION = 300  # default 5 minutes in seconds

# --------------------------
# Login
# --------------------------
@app.route('/')
def login():
    return render_template('login.html')   # login page

# --------------------------
# Teacher (quiz creator)
# --------------------------
@app.route('/creator')
def creator():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_quiz():
    """
    Expect JSON: { "questions": [...], "duration": 5 } 
    duration is in minutes
    """
    data = request.json
    questions = data.get("questions", [])
    duration_minutes = data.get("duration", 5)
    duration_seconds = duration_minutes * 60

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    # Generate a unique quiz ID for each new quiz
    quiz_id = str(uuid.uuid4())

    quiz_data = {
        "quiz_id": quiz_id,
        "questions": questions,
        "duration": duration_seconds
    }

    with open(DATA_FILE, 'w') as f:
        json.dump(quiz_data, f, indent=4)

    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!', 'quiz_id': quiz_id})

# --------------------------
# Student (take quiz)
# --------------------------
@app.route('/take_quiz')
def take_quiz():
    return render_template('take_quiz.html')

@app.route('/get_questions')
def get_questions():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            questions = quiz_data.get("questions", [])
    else:
        questions = []

    random.shuffle(questions)
    return jsonify(questions)

# --------------------------
# Timer API
# --------------------------
@app.route('/get_timer')
def get_timer():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            duration = quiz_data.get("duration", DEFAULT_QUIZ_DURATION)
    else:
        duration = DEFAULT_QUIZ_DURATION

    return jsonify({"duration": duration})

# --------------------------
# Start quiz
# --------------------------
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    data = request.json  # {"student": "Alice"}
    student = data.get("student")

    if not student:
        return jsonify({"error": "Student name required"}), 400

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            duration = quiz_data.get("duration", DEFAULT_QUIZ_DURATION)
            quiz_id = quiz_data.get("quiz_id")
    else:
        duration = DEFAULT_QUIZ_DURATION
        quiz_id = "default"

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    # Check if student already started this quiz
    student_record = next((r for r in results if r["student"] == student and r.get("quiz_id") == quiz_id), None)
    if student_record:
        start_time = student_record["start_time"]
    else:
        start_time = datetime.now().isoformat()
        results.append({
            "student": student,
            "quiz_id": quiz_id,
            "score": None,
            "total": None,
            "start_time": start_time
        })
        with open(RESULT_FILE, "w") as f:
            json.dump(results, f, indent=4)

    return jsonify({
        "start_time": start_time,
        "duration": duration,
        "quiz_id": quiz_id
    })

# --------------------------
# Submit quiz
# --------------------------
@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json  # {"student": "Name", "answers": [...], "quiz_id": "..."}

    quiz_id = data.get("quiz_id")
    student = data.get("student")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            questions = quiz_data.get("questions", [])
    else:
        questions = []

    score = 0
    for i, q in enumerate(questions):
        if i < len(data["answers"]) and q.get("answer", "").strip().lower() == data["answers"][i].strip().lower():
            score += 1

    total = len(questions)

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    # Update or add student record for this quiz
    for r in results:
        if r["student"] == student and r.get("quiz_id") == quiz_id:
            r["score"] = score
            r["total"] = total
            r["timestamp"] = datetime.now().isoformat()
            break
    else:
        results.append({
            "student": student,
            "quiz_id": quiz_id,
            "score": score,
            "total": total,
            "timestamp": datetime.now().isoformat()
        })

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=4)

    return jsonify({"score": score, "total": total})

# --------------------------
# Leaderboard
# --------------------------
@app.route('/leaderboard')
def leaderboard():
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)
    else:
        results = []

    for r in results:
        if "total" not in r:
            r["total"] = "?"

    # Sort by score descending, timestamp ascending
    results.sort(key=lambda x: (-x.get("score", 0), x.get("timestamp", "")))

    return render_template("leaderboard.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)
