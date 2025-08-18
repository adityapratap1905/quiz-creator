from flask import Flask, render_template, request, jsonify
import json
import os
import random
from datetime import datetime

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'

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
    random.shuffle(questions)  # shuffle for fairness
    return jsonify(questions)

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
        if i < len(data["answers"]) and q["answer"].strip().lower() == data["answers"][i].strip().lower():
            score += 1

    total = len(questions)

    # Save result with timestamp
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

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

    # Ensure each record has total
    for r in results:
        if "total" not in r:
            r["total"] = "?"

    # Sort: highest score first, then earliest submission wins tie
    results.sort(key=lambda x: (-x["score"], x["timestamp"]))

    return render_template("leaderboard.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)
