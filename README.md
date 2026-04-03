 🧠 Peblo AI: Smart Quiz Generator
   An intelligent FastAPI backend that converts PDFs into adaptive quizzes using LLM integration, making learning personalized and efficient.

 ✨ Features

 📄 PDF to Quiz Pipeline
- Upload any PDF document and get AI-generated questions instantly
- Extracts key concepts and creates context-aware questions
- Supports multiple question formats (MCQ, true/false, descriptive)

🧠 Adaptive Difficulty System
- Questions adjust based on user performance
- Progressive difficulty scaling for optimal learning curve
- Personalized quiz experience for each user

📊 Analytics & Tracking
- Track user responses and quiz attempts
- Performance metrics at question and topic level
- Identify knowledge gaps automatically

🔌 REST API Ready
- Full CRUD operations for quizzes, users, and responses
- Well-documented endpoints with OpenAPI/Swagger
- Easy integration with any frontend

🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11 |
| AI/LLM | OpenAI API, LangChain |
| Database | PostgreSQL, SQLAlchemy |
| Authentication | JWT / OAuth2 |
| Deployment | Render / Docker |
| Version Control | Git, GitHub |

🚀 Installation

1. Clone the repository
```bash
git clone https://github.com/nikita-rathee/quiz-generator-api.git
cd quiz-generator-api
```
 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies
```bash
pip install -r requirements.txt
```
4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your API keys
```
 5. Run the server
```bash
uvicorn main:app --reload
```
 6. Access API docs
Open `http://localhost:8000/docs` in your browser




 📁 Project Structure`

quiz-generator-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── quiz.py
│   │   └── user.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── quiz.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── quiz.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       ├── llm_service.py
│       ├── pdf_parser.py
│       └── quiz_service.py
│
├── requirements.txt
├── .env.example
└── README.md
```

📌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-pdf/` | Upload PDF and generate questions |
| GET | `/quizzes/{id}` | Get quiz by ID |
| POST | `/quiz/attempt/` | Submit answers, get next question |
| GET | `/analytics/{user_id}` | Get user performance stats |
| POST | `/auth/register` | Create new user |
| POST | `/auth/login` | Get access token |

🤝 Contributing

We welcome contributions!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

 🎯 Future Enhancements

- Support for DOCX and PPT files
- RAG-based retrieval from multiple documents
- Multi-language quiz generation
- Frontend dashboard for quiz creators
- Export quizzes to PDF/CSV

 👥 Author

Nikita Rathee

- Email: rathinikki36@gmail.com
- GitHub: [github.com/nikita-rathee](https://github.com/nikita-rathee)
- LinkedIn: [linkedin.com/in/nikita-rathee](https://linkedin.com/in/nikita-rathee)

⭐ Show Your Support

If you find this project helpful, please give it a star on GitHub!



📄 License

This project is licensed under the MIT License.


Built with ❤️ for smarter learning
