from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'

# Teacher view: add questions
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_quiz():
    questions = request.json
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(questions, f, indent=4)
    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!'})

# Student view: take quiz
@app.route('/take_quiz')
def take_quiz():
    return render_template('take_quiz.html')

# Fetch questions for students
@app.route('/get_questions')
def get_questions():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            questions = json.load(f)
    else:
        questions = []
    return jsonify(questions)

# Submit student answers
@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json  # Expecting {"answers": [...]}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            questions = json.load(f)
    else:
        questions = []

    score = 0
    for i, q in enumerate(questions):
        if i < len(data["answers"]) and q["answer"].strip().lower() == data["answers"][i].strip().lower():
            score += 1

    return jsonify({"score": score, "total": len(questions)})

if __name__ == '__main__':
    app.run(debug=True)
