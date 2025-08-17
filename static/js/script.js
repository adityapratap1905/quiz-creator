let questions = [];

const questionInput = document.getElementById('question');
const optionInputs = document.querySelectorAll('.option');
const answerInput = document.getElementById('answer');
const questionList = document.getElementById('questionList');
const addBtn = document.getElementById('addQuestion');
const saveBtn = document.getElementById('saveQuiz');
const exportCSVBtn = document.getElementById('exportCSV');
const exportPDFBtn = document.getElementById('exportPDF');

// Add Question
addBtn.addEventListener('click', () => {
    const questionText = questionInput.value.trim();
    const options = Array.from(optionInputs).map(input => input.value.trim());
    const answer = answerInput.value.trim();

    if (!questionText || options.includes('') || !answer) {
        Swal.fire({
            icon: 'warning',
            title: 'Oops!',
            text: 'Please fill all fields!'
        });
        return;
    }

    const questionObj = {
        question: questionText,
        options: options,
        answer: answer
    };

    questions.push(questionObj);
    renderQuestions();

    // Clear inputs
    questionInput.value = '';
    optionInputs.forEach(input => input.value = '');
    answerInput.value = '';
});

// Render questions as cards with Delete button
function renderQuestions() {
    questionList.innerHTML = '';

    questions.forEach((q, index) => {
        const li = document.createElement('li');
        li.className = "bg-blue-100 p-3 rounded-lg mb-2 flex justify-between items-center";

        const text = document.createElement('span');
        text.textContent = `${index + 1}. ${q.question} (Answer: ${q.answer})`;

        const delBtn = document.createElement('button');
        delBtn.textContent = 'Delete';
        delBtn.className = 'bg-red-500 hover:bg-red-700 text-white px-3 py-1 rounded-lg';
        delBtn.addEventListener('click', () => {
            questions.splice(index, 1);
            renderQuestions();
        });

        li.appendChild(text);
        li.appendChild(delBtn);
        questionList.appendChild(li);
    });
}

// Save Quiz
saveBtn.addEventListener('click', () => {
    if (questions.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Oops!',
            text: 'Add at least one question!'
        });
        return;
    }

    fetch('/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(questions)
    })
    .then(response => response.json())
    .then(data => {
        Swal.fire({
            icon: 'success',
            title: 'Saved!',
            text: data.message
        });
        questions = [];
        renderQuestions();
    })
    .catch(err => {
        Swal.fire({
            icon: 'error',
            title: 'Error!',
            text: 'Failed to save quiz.'
        });
    });
});

// Export as CSV
exportCSVBtn.addEventListener('click', () => {
    if (questions.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Oops!',
            text: 'No questions to export!'
        });
        return;
    }

    let csvContent = "data:text/csv;charset=utf-8,Question,OptionA,OptionB,OptionC,OptionD,Answer\n";

    questions.forEach(q => {
        const row = [
            `"${q.question}"`,
            `"${q.options[0]}"`,
            `"${q.options[1]}"`,
            `"${q.options[2]}"`,
            `"${q.options[3]}"`,
            `"${q.answer}"`
        ].join(",");
        csvContent += row + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "quiz.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    Swal.fire({
        icon: 'success',
        title: 'Exported!',
        text: 'Quiz has been exported as CSV.'
    });
});

// Export as PDF
exportPDFBtn.addEventListener('click', () => {
    if (questions.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Oops!',
            text: 'No questions to export!'
        });
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    questions.forEach((q, index) => {
        const y = 10 + index * 40; // spacing between questions
        doc.text(`${index + 1}. ${q.question}`, 10, y);
        doc.text(`A: ${q.options[0]}`, 10, y + 7);
        doc.text(`B: ${q.options[1]}`, 10, y + 14);
        doc.text(`C: ${q.options[2]}`, 10, y + 21);
        doc.text(`D: ${q.options[3]}`, 10, y + 28);
        doc.text(`Answer: ${q.answer}`, 10, y + 35);
    });

    doc.save("quiz.pdf");

    Swal.fire({
        icon: 'success',
        title: 'Exported!',
        text: 'Quiz has been exported as PDF.'
    });
});
