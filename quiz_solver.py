import os
import logging
import tempfile
from groq import Groq
from docx import Document

logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_text_from_pdf(file_path: str) -> str:
    import fitz
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def solve_quiz(content: str) -> str:
    prompt = f"""Solve this quiz/exam. For each question:
1. Write the question
2. Provide the correct answer
3. Give a brief explanation

Quiz content:
{content}

Format the answer clearly with question numbers."""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.choices[0].message.content

def create_solved_document(original_name: str, solution_text: str) -> str:
    doc = Document()
    doc.add_heading(f"Solved: {original_name}", 0)
    doc.add_paragraph("")
    for line in solution_text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    
    output_path = os.path.join(tempfile.gettempdir(), f"solved_{original_name}.docx")
    doc.save(output_path)
    return output_path

async def solve_quiz_file(file_path: str, file_name: str) -> str:
    logger.info(f"Solving quiz: {file_name}")
    
    if file_name.lower().endswith(".pdf"):
        content = extract_text_from_pdf(file_path)
    else:
        with open(file_path, "r", errors="ignore") as f:
            content = f.read()
    
    if not content.strip():
        raise ValueError("Could not extract text from file")
    
    solution = solve_quiz(content[:10000])
    output_path = create_solved_document(file_name, solution)
    return output_path
