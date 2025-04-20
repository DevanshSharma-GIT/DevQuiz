document.addEventListener('DOMContentLoaded', () => {
    const options = document.querySelectorAll('.quiz-option');
    const answerInput = document.querySelector('#answer');
    const quizForm = document.querySelector('#quiz-form');

    if (!quizForm || !answerInput) {
        console.error('Quiz form or answer input not found');
        return;
    }

    options.forEach(option => {
        option.addEventListener('click', () => {
            console.log('Option clicked:', option.dataset.answer);
            answerInput.value = option.dataset.answer;
            console.log('Submitting form with answer:', answerInput.value);
            quizForm.submit();
        });
    });
});