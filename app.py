from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import random

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'

# --------------------------
# Ensure data folder exists
# --------------------------
os.makedirs("data", exist_ok=True)

# --------------------------
# Login
# --------------------------
@app.route('/')
def login():
    return render_template('login.html')   # Show login.html

@app.route('/login', methods=['POST'])
def do_login():
    role = request.form.get("role")   # "teacher" or "student"
    name = request.form.get("name")

    if role == "teacher":
        return redirect(url_for("creator"))
    elif role == "student":
        return redirect(url_for("take_quiz", student=name))
    else:
        return "Invalid role!", 400

# --------------------------
# Teacher (quiz creator)
# --------------------------
@app.route('/creator')
def creator():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_quiz():
    questions = request.json
    with open(DATA_FILE, 'w') as f:
        json.dump(questions, f, indent=4)
    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!'})

# --------------------------
# Student (take quiz)
# --------------------------
@app.route('/take_quiz')
def take_quiz():
    student = request.args.get("student", "Anonymous")
    return render_template('take_quiz.html', student=student)

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
    student = data.get("student", "Anonymous")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            questions = json.load(f)
    else:
        questions = []

    score = 0
    for i, q in enumerate(questions):
        if i < len(data["answers"]) and q["answer"].strip().lower() == data["answers"][i].strip().lower():
            score += 1

    # Save result
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    results.append({
        "student": student,
        "score": score,
        "total": len(questions)
    })

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=4)

    return jsonify({"student": student, "score": score, "total": len(questions)})

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
    results.sort(key=lambda x: x["score"], reverse=True)
    return render_template("leaderboard.html", results=results)


if __name__ == '__main__':
    app.run(debug=True)
