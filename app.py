from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json, os, random, re, uuid, html
from datetime import datetime
from functools import wraps

# AI clients
from openai import OpenAI
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# API keys
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'
DEFAULT_QUIZ_DURATION = 300
TEACHER_PASSWORD = "admin123"

# --------------------------
# Login
# --------------------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                return "Access denied", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form.get("username", "").strip()
    role = request.form.get("role")
    password = request.form.get("password", "").strip()

    if not username or role not in ("teacher", "student"):
        return redirect(url_for("login"))

    if role == "teacher" and password != TEACHER_PASSWORD:
        return "Invalid password for teacher", 403

    session["username"] = username
    session["role"] = role
    return redirect(url_for("creator") if role=="teacher" else url_for("take_quiz"))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------------
# Teacher Routes
# --------------------------
@app.route('/creator')
@login_required(role="teacher")
def creator():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
@login_required(role="teacher")
def save_quiz():
    data = request.json
    questions = data.get("questions", [])
    duration_seconds = int(data.get("duration", 5)) * 60

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    quiz_id = str(uuid.uuid4())
    quiz_data = {"quiz_id": quiz_id, "questions": questions, "duration": duration_seconds}

    with open(DATA_FILE, 'w') as f:
        json.dump(quiz_data, f, indent=4)

    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!', 'quiz_id': quiz_id})

@app.route('/generate_quiz', methods=['POST'])
@login_required(role="teacher")
def generate_quiz():
    data = request.json
    prompt = data.get("prompt", "").strip()
    ai_choice = data.get("ai_choice", "openai")
    num_questions = int(data.get("num_questions", 5))

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    instruction = f"""
Generate {num_questions} multiple-choice questions based on:
{prompt}

Output strictly as JSON array:
[
  {{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "answer": "Correct Option"
  }}
]
"""

    quiz_text = None
    try:
        if ai_choice.lower() == "openai":
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful quiz generator."},
                    {"role": "user", "content": instruction}
                ],
                temperature=0.7
            )
            quiz_text = response.choices[0].message.content
        if ai_choice.lower() == "gemini" or not quiz_text:
            model = genai.GenerativeModel("gemini-1.5-flash")
            quiz_text = model.generate_content(instruction).text
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

    try:
        match = re.search(r"\[.*\]", quiz_text, re.DOTALL)
        quiz_data = json.loads(match.group(0)) if match else []
    except:
        quiz_data = []

    for q in quiz_data:
        q.setdefault("question", "")
        q["options"] = (q.get("options", []) + ["", "", "", ""])[:4]
        q.setdefault("answer", "")

    if not quiz_data:
        quiz_data = [{"question": quiz_text or "", "options": ["", "", "", ""], "answer": ""}]

    return jsonify({"quiz": quiz_data})

# --------------------------
# Student Routes
# --------------------------
@app.route('/take_quiz')
@login_required(role="student")
def take_quiz():
    return render_template('take_quiz.html')

@app.route('/get_questions')
@login_required(role="student")
def get_questions():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            questions = json.load(f).get("questions", [])
    else:
        questions = []
    random.shuffle(questions)
    return jsonify(questions)

@app.route('/get_timer')
@login_required(role="student")
def get_timer():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            duration = json.load(f).get("duration", DEFAULT_QUIZ_DURATION)
    else:
        duration = DEFAULT_QUIZ_DURATION
    return jsonify({"duration": duration})

@app.route('/start_quiz', methods=['POST'])
@login_required(role="student")
def start_quiz():
    data = request.json
    student = data.get("student")
    if not student:
        return jsonify({"error": "Student name required"}), 400

    if os.path.exists(DATA_FILE):
        quiz_data = json.load(open(DATA_FILE))
        quiz_id = quiz_data.get("quiz_id")
        total_questions = len(quiz_data.get("questions", []))
        duration = quiz_data.get("duration", DEFAULT_QUIZ_DURATION)
    else:
        quiz_id = "default"
        total_questions = 0
        duration = DEFAULT_QUIZ_DURATION

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = json.load(open(RESULT_FILE)) if os.path.exists(RESULT_FILE) else []

    student_record = next((r for r in results if r["student"]==student and r.get("quiz_id")==quiz_id), None)
    if not student_record:
        results.append({"student": student, "quiz_id": quiz_id, "score": 0, "total": total_questions, "start_time": datetime.now().isoformat(), "timestamp": None})
        with open(RESULT_FILE, "w") as f:
            json.dump(results, f, indent=4)

    return jsonify({"quiz_id": quiz_id, "duration": duration})

@app.route('/submit_quiz', methods=['POST'])
@login_required(role="student")
def submit_quiz():
    data = request.json
    quiz_id = data.get("quiz_id")
    student = data.get("student")
    student_answers = data.get("answers", [])

    if os.path.exists(DATA_FILE):
        questions = json.load(open(DATA_FILE)).get("questions", [])
    else:
        return jsonify({"error": "Quiz not found"}), 404

    # Normalize answers: strip, lowercase, decode HTML
    def normalize(text):
        return html.unescape(text.strip().lower())

    score = 0
    for i, q in enumerate(questions):
        correct_answer = normalize(q.get("answer", ""))
        submitted = normalize(student_answers[i]) if i < len(student_answers) else ""
        if correct_answer == submitted:
            score += 1

    total = len(questions)

    results = json.load(open(RESULT_FILE)) if os.path.exists(RESULT_FILE) else []

    updated = False
    for r in results:
        if r["student"]==student and r.get("quiz_id")==quiz_id:
            r["score"] = score
            r["total"] = total
            r["timestamp"] = datetime.now().isoformat()
            updated = True
            break

    if not updated:
        results.append({"student": student, "quiz_id": quiz_id, "score": score, "total": total, "timestamp": datetime.now().isoformat()})

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=4)

    return jsonify({"score": score, "total": total})

@app.route('/leaderboard')
@login_required()
def leaderboard():
    results = []
    if os.path.exists(RESULT_FILE):
        results = json.load(open(RESULT_FILE))

    # Normalize types
    for r in results:
        r["score"] = int(r.get("score",0))
        r["total"] = int(r.get("total",0))
        r["quiz_id"] = r.get("quiz_id") or "default"
        r["timestamp"] = r.get("timestamp") or ""

    # Show only latest quiz
    latest_quiz = results[-1]["quiz_id"] if results else None
    if latest_quiz:
        results = [r for r in results if r.get("quiz_id")==latest_quiz]

    results.sort(key=lambda x: (-x["score"], x["timestamp"]))

    return render_template("leaderboard.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)
