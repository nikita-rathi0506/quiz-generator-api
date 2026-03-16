# Quiz Generator 
 
A simple API to upload PDFs and generate quizzes. 
 
## Setup 
1. Install requirements: `pip install -r requirements.txt` 
2. Run: `python main.py` 
3. Open: http://localhost:8000 
 
## Endpoints 
- POST /upload - Upload PDF 
- GET /documents - List documents 
- POST /generate/{id} - Generate quiz 
- GET /quiz/{id} - Get quiz 
