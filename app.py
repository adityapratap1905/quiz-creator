from flask import Flask, render_template, request, jsonify
import json
import os
import random
from datetime import datetime

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'
QUIZ_DURATION = 300  # seconds (5 minutes)

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
    questions = request.json
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(questions, f, indent=4)
    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!'})

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
            questions = json.load(f)
    else:
        questions = []
    random.shuffle(questions)
    return jsonify(questions)

# --------------------------
# Timer API
# --------------------------
@app.route('/get_timer')
def get_timer():
    return jsonify({"duration": QUIZ_DURATION})

# --------------------------
# Start quiz
# --------------------------
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    data = request.json  # {"student": "Alice"}
    student = data.get("student")

    if not student:
        return jsonify({"error": "Student name required"}), 400

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    # Check if this student already started
    student_record = next((r for r in results if r["student"] == student and "start_time" in r), None)
    if student_record:
        start_time = student_record["start_time"]
    else:
        start_time = datetime.now().isoformat()
        results.append({
            "student": student,
            "score": None,
            "total": None,
            "start_time": start_time
        })
        with open(RESULT_FILE, "w") as f:
            json.dump(results, f, indent=4)

    return jsonify({
        "start_time": start_time,
        "duration": QUIZ_DURATION
    })

# --------------------------
# Submit quiz
# --------------------------
@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json  # {"student": "Name", "answers": [...]}

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            questions = json.load(f)
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

    for r in results:
        if r["student"] == data["student"]:
            r["score"] = score
            r["total"] = total
            r["timestamp"] = datetime.now().isoformat()
            break
    else:
        results.append({
            "student": data["student"],
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
