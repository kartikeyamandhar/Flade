import React from 'react';
import './SuggestedQuestions.css';

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
  disabled?: boolean;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onQuestionClick,
  disabled = false
}) => {
  const questions = [
    "What is this manual about?",
    "What are the main features?",
    "List the technical specifications",
    "What are the safety warnings?",
    "How do I install or set up?",
    "What tools or accessories are needed?"
  ];

  return (
    <div className="suggested-questions">
      <p className="suggested-label">💡 Suggested questions:</p>
      <div className="questions-grid">
        {questions.map((question, idx) => (
          <button
            key={idx}
            className="question-chip"
            onClick={() => onQuestionClick(question)}
            disabled={disabled}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;