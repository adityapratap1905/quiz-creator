from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = 'data/quizzes.json'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_quiz():
    questions = request.json
    # Ensure data folder exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    # Save to JSON
    with open(DATA_FILE, 'w') as f:
        json.dump(questions, f, indent=4)
    return jsonify({'status': 'success', 'message': 'Quiz saved successfully!'})

if __name__ == '__main__':
    app.run(debug=True)
