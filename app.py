from flask import Flask, render_template, request, jsonify
import json, os, random, re, uuid
from datetime import datetime

# AI clients
from openai import OpenAI
import google.generativeai as genai

app = Flask(__name__)

# --------------------------
# Configure API keys
# --------------------------
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DATA_FILE = 'data/quizzes.json'
RESULT_FILE = 'data/results.json'
DEFAULT_QUIZ_DURATION = 300  # default 5 minutes

# --------------------------
# Login
# --------------------------
@app.route('/')
def login():
    return render_template('login.html')

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
    prompt = data.get("prompt", "").strip()
    ai_choice = data.get("ai_choice", "openai")
    num_questions = int(data.get("num_questions", 5))

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    instruction = f"""
Generate {num_questions} multiple-choice questions based on the following topic/paragraph:
{prompt}

Output strictly as a JSON array with each question like this:
[
  {{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "answer": "Correct Option"
  }}
]
"""

    quiz_text = None

    # Try OpenAI
    if ai_choice.lower() == "openai":
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful quiz generator."},
                    {"role": "user", "content": instruction}
                ],
                temperature=0.7
            )
            quiz_text = response.choices[0].message.content
        except Exception:
            quiz_text = None

    # Fallback to Gemini
    if ai_choice.lower() == "gemini" or not quiz_text:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            gemini_response = model.generate_content(instruction)
            quiz_text = gemini_response.text
        except Exception as e:
            return jsonify({"error": f"Both AI failed: {str(e)}"}), 500

    # Safely extract JSON
    try:
        match = re.search(r"\[.*\]", quiz_text, re.DOTALL)
        if match:
            quiz_data = json.loads(match.group(0))
        else:
            quiz_data = []
    except Exception:
        quiz_data = []

    # Ensure each question has proper fields
    for q in quiz_data:
        q.setdefault("question", "")
        opts = q.get("options", [])
        q["options"] = (opts + ["", "", "", ""])[:4]
        q.setdefault("answer", "")

    if not quiz_data:
        quiz_data = [{"question": quiz_text or "", "options": ["", "", "", ""], "answer": ""}]

    return jsonify({"quiz": quiz_data})

# --------------------------
# Student routes
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

@app.route('/get_timer')
def get_timer():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            duration = quiz_data.get("duration", DEFAULT_QUIZ_DURATION)
    else:
        duration = DEFAULT_QUIZ_DURATION
    return jsonify({"duration": duration})

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
            total_questions = len(quiz_data.get("questions", []))
    else:
        duration = DEFAULT_QUIZ_DURATION
        quiz_id = "default"
        total_questions = 0

    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            results = json.load(f)

    student_record = next((r for r in results if r["student"] == student and r.get("quiz_id") == quiz_id), None)
    if not student_record:
        start_time = datetime.now().isoformat()
        results.append({
            "student": student,
            "quiz_id": quiz_id,
            "score": 0,
            "total": total_questions,
            "start_time": start_time,
            "timestamp": None
        })
        with open(RESULT_FILE, "w") as f:
            json.dump(results, f, indent=4)
    else:
        start_time = student_record.get("start_time", datetime.now().isoformat())

    return jsonify({
        "start_time": start_time,
        "duration": duration,
        "quiz_id": quiz_id
    })

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    quiz_id = data.get("quiz_id")
    student = data.get("student")
    student_answers = data.get("answers", [])

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            quiz_data = json.load(f)
            questions = quiz_data.get("questions", [])
    else:
        return jsonify({"error": "Quiz not found"}), 404

    # Calculate score
    score = 0
    for i, q in enumerate(questions):
        correct_answer = q.get("answer", "").strip().lower()
        submitted_answer = student_answers[i].strip().lower() if i < len(student_answers) else ""
        if correct_answer == submitted_answer:
            score += 1

    total = len(questions)

    # Save results
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r") as f:
            results = json.load(f)

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

@app.route('/leaderboard')
def leaderboard():
    results = []
    try:
        if os.path.exists(RESULT_FILE):
            with open(RESULT_FILE) as f:
                results = json.load(f)
        # Normalize results
        for r in results:
            r["score"] = int(r.get("score", 0))
            r["total"] = int(r.get("total", 0))
            r["timestamp"] = r.get("timestamp") or ""
            r["quiz_id"] = r.get("quiz_id") or "default"

        latest_quiz_id = results[-1]["quiz_id"] if results else None
        if latest_quiz_id:
            results = [r for r in results if r.get("quiz_id") == latest_quiz_id]

        # Sort by score descending, then timestamp ascending
        results.sort(key=lambda x: (-x["score"], x["timestamp"]))
    except Exception as e:
        print("Leaderboard error:", e)
        results = []

    return render_template("leaderboard.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)
