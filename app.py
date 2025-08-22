from openai import OpenAI
from flask import Flask, render_template, request, jsonify
import json
import os
import random
from datetime import datetime
import uuid  # for unique quiz IDs

app = Flask(__name__)

# Create OpenAI client (reads key from environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    data = request.json
    questions = data.get("questions", [])
    duration_minutes = data.get("duration", 5)
    duration_seconds = duration_minutes * 60

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

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
# AI Quiz Generator
# --------------------------
@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    prompt = data.get("prompt", "")

    if not prompt.strip():
        return jsonify({"error": "Prompt is required"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # lightweight + cheap model
            messages=[
                {"role": "system", "content": "You are a quiz generator AI. Generate 5 MCQs in JSON format."},
                {"role": "user", "content": f"Generate 5 multiple-choice questions with 4 options and 1 correct answer. Topic/Paragraph: {prompt}"}
            ],
            temperature=0.7
        )

        quiz_json = response.choices[0].message.content

        # Try parsing JSON
        quiz_data = json.loads(quiz_json)

        return jsonify({"quiz": quiz_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    data = request.json
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

    student_record = next((r for r in results if r["student"] == student and r.get("quiz_id") == quiz_id), None)
    if student_record:
        start_time = student_record.get("start_time", datetime.now().isoformat())
    else:
        start_time = datetime.now().isoformat()
        results.append({
            "student": student,
            "quiz_id": quiz_id,
            "score": None,
            "total": None,
            "start_time": start_time,
            "timestamp": None
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
    data = request.json
    quiz_id = data.get("quiz_id")
    student = data.get("student")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            questions = quiz_data.get("questions", [])
    else:
        questions = []

    score = sum(
        1 for i, q in enumerate(questions)
        if i < len(data["answers"]) and q.get("answer", "").strip().lower() == data["answers"][i].strip().lower()
    )
    total = len(questions)

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    # Update or add student record
    updated = False
    for r in results:
        if r["student"] == student and r.get("quiz_id") == quiz_id:
            r["score"] = score
            r["total"] = total
            r["timestamp"] = datetime.now().isoformat()
            updated = True
            break
    if not updated:
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
    try:
        if os.path.exists(RESULT_FILE):
            with open(RESULT_FILE) as f:
                results = json.load(f)
        else:
            results = []

        # Ensure all fields exist
        for r in results:
            r["score"] = r.get("score") or 0
            r["total"] = r.get("total") or "?"
            r["timestamp"] = r.get("timestamp") or ""
            r["quiz_id"] = r.get("quiz_id") or "default"

        # Show leaderboard for latest quiz only
        latest_quiz_id = None
        if results:
            latest_quiz_id = results[-1]["quiz_id"]
            results = [r for r in results if r.get("quiz_id") == latest_quiz_id]

        results.sort(key=lambda x: (-x["score"], x["timestamp"]))

    except Exception as e:
        print("Leaderboard load error:", e)
        results = []

    return render_template("leaderboard.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)
