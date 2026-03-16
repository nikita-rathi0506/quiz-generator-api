import os
import sqlite3
import json
import uuid
import shutil
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import PyPDF2
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Peblo Quiz Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_PATH = "quiz.db"

def init_database():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                grade INTEGER,
                subject TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_chunks INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                topic TEXT,
                text TEXT NOT NULL,
                page_number INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                options TEXT,
                correct_answer TEXT NOT NULL,
                difficulty TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES content_chunks (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT,
                current_difficulty TEXT DEFAULT 'medium',
                performance_score REAL DEFAULT 0.0,
                total_answers INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_answers (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                selected_answer TEXT NOT NULL,
                is_correct BOOLEAN DEFAULT 0,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

init_database()

class PDFProcessor:
    
    def extract_text(self, pdf_path: str) -> str:
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n[Page {page_num + 1}]\n"
                        text += page_text + "\n"
            return self.clean_text(text)
        except Exception as e:
            raise Exception(f"Error extracting PDF: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        # Fixed: Using raw string for regex pattern
        text = re.sub(r'\s+', ' ', text)  # Changed back to raw string
        text = re.sub(r'[^\w\s\.\,\?\!\-]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str, chunk_size: int = 500) -> List[Dict]:
        chunks = []
        pages = re.split(r'\[Page \d+\]', text)
        
        for i, page_content in enumerate(pages):
            if not page_content.strip():
                continue
                
            words = page_content.split()
            current_chunk = []
            current_size = 0
            
            for word in words:
                current_chunk.append(word)
                current_size += len(word) + 1
                
                if current_size >= chunk_size:
                    chunks.append({
                        'index': len(chunks),
                        'text': ' '.join(current_chunk),
                        'page': i
                    })
                    current_chunk = []
                    current_size = 0
            
            if current_chunk:
                chunks.append({
                    'index': len(chunks),
                    'text': ' '.join(current_chunk),
                    'page': i
                })
        
        return chunks
    
    def extract_metadata(self, filename: str) -> Dict:
        metadata = {
            "grade": None,
            "subject": None,
            "topic": None
        }
        
        pattern = r'peblo_pdf_grade(\d+)_([a-z]+)_([a-z_]+)\.pdf'
        match = re.search(pattern, filename.lower())
        
        if match:
            metadata["grade"] = int(match.group(1))
            metadata["subject"] = match.group(2)
            metadata["topic"] = match.group(3).replace('_', ' ')
        
        return metadata

pdf_processor = PDFProcessor()

class MockQuizGenerator:
    
    def generate_questions(self, text: str, chunk_id: str, num_questions: int = 3) -> List[Dict]:
        questions = []
        words = text.split()[:10]
        topic = " ".join(words[:3]) if words else "topic"
        
        questions.append({
            "question": f"What is the main topic of this text?",
            "type": "MCQ",
            "options": [topic, "Mathematics", "Science", "History"],
            "answer": topic,
            "difficulty": "easy",
            "source_chunk_id": chunk_id
        })
        
        questions.append({
            "question": f"Is this text about {topic}?",
            "type": "TRUE_FALSE",
            "options": ["True", "False"],
            "answer": "True",
            "difficulty": "easy",
            "source_chunk_id": chunk_id
        })
        
        first_word = words[0] if words else "The"
        questions.append({
            "question": f"The text discusses _____.",
            "type": "FILL_BLANK",
            "options": None,
            "answer": topic,
            "difficulty": "medium",
            "source_chunk_id": chunk_id
        })
        
        return questions

quiz_generator = MockQuizGenerator()

def generate_id() -> str:
    return str(uuid.uuid4())[:8]

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "Peblo Quiz Engine API",
        "endpoints": {
            "POST /upload": "Upload PDF file",
            "GET /documents": "List all documents",
            "GET /documents/{id}": "Get document details",
            "POST /generate/{id}": "Generate quiz from document",
            "GET /quiz": "Get quiz questions",
            "POST /submit-answer": "Submit answer",
            "GET /students/{id}": "Get student stats"
        },
        "docs": "/docs"
    }

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    metadata = pdf_processor.extract_metadata(file.filename)
    text = pdf_processor.extract_text(file_path)
    chunks = pdf_processor.chunk_text(text)
    
    doc_id = generate_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (id, filename, grade, subject, total_chunks)
            VALUES (?, ?, ?, ?, ?)
        ''', (doc_id, file.filename, metadata['grade'], metadata['subject'], len(chunks)))
        
        for chunk in chunks:
            chunk_id = generate_id()
            cursor.execute('''
                INSERT INTO content_chunks (id, document_id, chunk_index, topic, text, page_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chunk_id, doc_id, chunk['index'], metadata['topic'], chunk['text'], chunk['page']))
        
        conn.commit()
    
    os.remove(file_path)
    
    return {
        "document_id": doc_id,
        "filename": file.filename,
        "chunks_created": len(chunks),
        "grade": metadata['grade'],
        "subject": metadata['subject'],
        "message": "PDF processed successfully"
    }

@app.get("/documents")
async def list_documents():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, grade, subject, upload_date, total_chunks
            FROM documents
            ORDER BY upload_date DESC
        ''')
        documents = [dict(row) for row in cursor.fetchall()]
    
    return {"documents": documents}

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        cursor.execute('''
            SELECT id, chunk_index, topic, text, page_number
            FROM content_chunks
            WHERE document_id = ?
            ORDER BY chunk_index
        ''', (doc_id,))
        chunks = [dict(row) for row in cursor.fetchall()]
        
        result = dict(doc)
        result['chunks'] = chunks
    
    return result

@app.post("/generate/{doc_id}")
async def generate_quiz(doc_id: str):
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, text FROM content_chunks
            WHERE document_id = ?
        ''', (doc_id,))
        chunks = cursor.fetchall()
        
        if not chunks:
            raise HTTPException(404, "No chunks found for document")
        
        questions_generated = 0
        
        for chunk in chunks:
            questions = quiz_generator.generate_questions(
                chunk['text'], 
                chunk['id'],
                num_questions=2
            )
            
            for q in questions:
                cursor.execute('''
                    INSERT INTO questions 
                    (id, chunk_id, question_text, question_type, options, correct_answer, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    generate_id(),
                    chunk['id'],
                    q['question'],
                    q['type'],
                    json.dumps(q.get('options')),
                    q['answer'],
                    q.get('difficulty', 'medium')
                ))
                questions_generated += 1
        
        conn.commit()
    
    return {
        "document_id": doc_id,
        "questions_generated": questions_generated,
        "message": f"Generated {questions_generated} questions"
    }

@app.get("/quiz")
async def get_quiz(
    difficulty: str = "medium",
    student_id: Optional[str] = None,
    count: int = 5
):
    
    if student_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT current_difficulty FROM students WHERE id = ?', (student_id,))
            student = cursor.fetchone()
            if student:
                difficulty = student['current_difficulty']
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM questions
            WHERE difficulty = ?
            ORDER BY RANDOM()
            LIMIT ?
        ''', (difficulty, count))
        
        questions = []
        for row in cursor.fetchall():
            q = dict(row)
            if q['options']:
                q['options'] = json.loads(q['options'])
            questions.append(q)
    
    return {
        "questions": questions,
        "student_id": student_id,
        "current_difficulty": difficulty,
        "count": len(questions)
    }

@app.post("/submit-answer")
async def submit_answer(request: Request):
    data = await request.json()
    
    student_id = data.get('student_id')
    question_id = data.get('question_id')
    selected_answer = data.get('selected_answer')
    
    if not all([student_id, question_id, selected_answer]):
        raise HTTPException(400, "Missing required fields")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        question = cursor.fetchone()
        if not question:
            raise HTTPException(404, "Question not found")
        
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            cursor.execute('''
                INSERT INTO students (id, name)
                VALUES (?, ?)
            ''', (student_id, f"Student_{student_id[:4]}"))
            conn.commit()
            
            cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
            student = cursor.fetchone()
        
        is_correct = selected_answer.strip().lower() == question['correct_answer'].strip().lower()
        
        answer_id = generate_id()
        cursor.execute('''
            INSERT INTO student_answers 
            (id, student_id, question_id, selected_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
        ''', (answer_id, student_id, question_id, selected_answer, is_correct))
        
        cursor.execute('''
            UPDATE students
            SET total_answers = total_answers + 1,
                correct_answers = correct_answers + ?,
                performance_score = (correct_answers + ?) * 1.0 / (total_answers + 1)
            WHERE id = ?
        ''', (1 if is_correct else 0, 1 if is_correct else 0, student_id))
        
        if student['total_answers'] > 0:
            cursor.execute('''
                SELECT 
                    AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) as accuracy
                FROM student_answers
                WHERE student_id = ?
                ORDER BY answered_at DESC
                LIMIT 5
            ''', (student_id,))
            recent = cursor.fetchone()
            
            if recent and recent['accuracy'] is not None:
                accuracy = recent['accuracy']
                
                if accuracy >= 0.8:
                    new_diff = 'hard' if student['current_difficulty'] == 'medium' else 'hard'
                elif accuracy <= 0.3:
                    new_diff = 'easy' if student['current_difficulty'] == 'medium' else 'medium'
                else:
                    new_diff = student['current_difficulty']
                
                if new_diff != student['current_difficulty']:
                    cursor.execute('''
                        UPDATE students
                        SET current_difficulty = ?
                        WHERE id = ?
                    ''', (new_diff, student_id))
        
        conn.commit()
    
    return {
        "answer_id": answer_id,
        "is_correct": is_correct,
        "message": "Correct!" if is_correct else "Incorrect"
    }

@app.get("/students/{student_id}")
async def get_student_stats(student_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            raise HTTPException(404, "Student not found")
        
        cursor.execute('''
            SELECT q.question_text, sa.selected_answer, sa.is_correct, sa.answered_at
            FROM student_answers sa
            JOIN questions q ON sa.question_id = q.id
            WHERE sa.student_id = ?
            ORDER BY sa.answered_at DESC
            LIMIT 10
        ''', (student_id,))
        
        recent = [dict(row) for row in cursor.fetchall()]
        
        result = dict(student)
        result['recent_answers'] = recent
    
    return result

if __name__ == "__main__":
    print("=" * 50)
    print("Peblo Quiz Engine Starting...")
    print("=" * 50)
    print(f"Database: {DATABASE_PATH}")
    print(f"Upload folder: {UPLOAD_DIR}")
    print("\nAPI will be available at:")
    print("  • Main API: http://localhost:8000")
    print("  • Docs: http://localhost:8000/docs")
    print("  • ReDoc: http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)