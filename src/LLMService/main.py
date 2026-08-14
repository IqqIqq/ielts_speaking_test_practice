#import SparkApi
from src.LLMService import SparkApi
from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

app = FastAPI()
templates = Jinja2Templates(directory="src/LLMService/templates")  # Ensure the path is correct

# The following key information is obtained from the console
appid = APPID     # Fill in the APPID information obtained from the console
api_secret = APISecret  # Fill in the APISecret information obtained from the console
api_key = APIKey    # Fill in the APIKey information obtained from the console

# Used to configure the large model version, default "general/generalv2"
domain = "general"   # v1.5 version
#domain = "generalv2"    # v2.0 version
# Cloud environment service address
Spark_url = "ws://spark-api.xf-yun.com/v1.1/chat"  # v1.5 environment address
#Spark_url = "ws://spark-api.xf-yun.com/v2.1/chat"  # v2.0 environment address

# length = 0

def getText(role, content):
    text = []
    jsoncon = {}
    jsoncon["role"] = role
    jsoncon["content"] = content
    text.append(jsoncon)
    return text

def getlength(text):
    length = 0
    for content in text:
        temp = content["content"]
        leng = len(temp)
        length += leng
    return length

def checklen(text):
    while (getlength(text) > 8000):
        del text[0]
    return text
    
@app.get("/qa", response_class=HTMLResponse)
async def get_query_form(request: Request):
    return templates.TemplateResponse(request,
    "query_form.html",
    {"request": request})

@app.post("/qa", response_class=HTMLResponse)
async def call_llm(request: Request, query: str = Form(...)):
    question = checklen(getText("user", query))
    SparkApi.answer = ""  # Clear the previous answer

    # Call SparkApi to generate the answer
    SparkApi.main(appid, api_key, api_secret, Spark_url, domain, question)

    # Generate the complete answer
    answer = generate_answer(query, SparkApi.answer)

    return templates.TemplateResponse(request,
    "response.html",
    {
        "request": request,
        "answer": answer
    })

# def generate_answer(query, spark_answer):
#     # Logic to generate the complete answer
#     prompt = (
#         "You are an IELTS speaking interview with expert English speaking skills. "
#         "Now you need to give the example answer given the hints of keywords input. "
#         "The score criteria is fluency and coherence, lexical resource, grammatical range and accuracy, pronunciation. "
#         f"The question is: {query}. The generated answer is: {spark_answer}."
#     )
    
#     # You can further process the prompt as needed
#     # For example, you can pass the prompt to SparkApi for further processing
#     return spark_answer  # Return the generated answer

# Database configuration
DATABASE_URL = os.getenv("POSTGRES_URL")  # Get the connection string from environment variables
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define models
class Part1Question(Base):
    __tablename__ = "part_1"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    category = Column(String)  # 新增类别列

class Part2Question(Base):
    __tablename__ = "part_2"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    category = Column(String)  # 新增类别列

class Part3Question(Base):
    __tablename__ = "part_3"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    category = Column(String)  # 新增类别列

# Define user model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

# Create database tables
Base.metadata.create_all(bind=engine)

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db), part: int = Query(1), category: str = Query(None)):
    # 每页显示的问题数量
    page_size = 5
    part1_questions = db.query(Part1Question).all()
    part2_questions = db.query(Part2Question).all()
    part3_questions = db.query(Part3Question).all()

    # 分组问题按类别
    part1_grouped = {}
    for question in part1_questions:
        if question.category not in part1_grouped:
            part1_grouped[question.category] = []
        part1_grouped[question.category].append(question)

    part2_grouped = {}
    for question in part2_questions:
        if question.category not in part2_grouped:
            part2_grouped[question.category] = []
        part2_grouped[question.category].append(question)

    part3_grouped = {}
    for question in part3_questions:
        if question.category not in part3_grouped:
            part3_grouped[question.category] = []
        part3_grouped[question.category].append(question)

    # 默认显示第一个类别的问题
    if category is None and part1_grouped:
        category = list(part1_grouped.keys())[0]

    # 获取当前类别的问题
    part1_questions_to_display = part1_grouped.get(category, [])
    part1_paginated = part1_questions_to_display[(part - 1) * page_size: part * page_size]

    # 处理 Part 2 和 Part 3 的类别
    part2_questions_to_display = part2_grouped.get(category, [])
    part3_questions_to_display = part3_grouped.get(category, [])

    return templates.TemplateResponse(
         request,
        "index.html",
        {
            "request": request,  # 确保旧版本模板渲染也能拿到 request
            "part1_grouped": part1_grouped,
            "part1_questions": part1_paginated,
            "part2_grouped": part2_grouped,
            "part2_questions": part2_questions_to_display,
            "part3_grouped": part3_grouped,
            "part3_questions": part3_questions_to_display,
            "part1_count": len(part1_questions),
            "part2_count": len(part2_questions),
            "part3_count": len(part3_questions),
            "current_part": part,
            "current_category": category,
        }
    )
@app.post("/submit_answer", response_class=HTMLResponse)
async def submit_answer(request: Request, question_id: int = Form(...), keywords: str = Form(...), part: int = Form(...), db: Session = Depends(get_db)):
    if part == 1:
        question = db.query(Part1Question).filter(Part1Question.id == question_id).first()
        answer = generate_answer(question.question, keywords)
    elif part == 2:
        question = db.query(Part2Question).filter(Part2Question.id == question_id).first()
        answer = generate_answer(question.question, keywords)
    else:
        question = db.query(Part3Question).filter(Part3Question.id == question_id).first()
        # 解析小问题
        small_questions = question.question.split('?')  # 假设小问题用 ? 分隔
        for small_question in small_questions:
            if small_question.strip():  # 确保小问题不为空
                answer = generate_answer(small_question.strip(), keywords)

    return templates.TemplateResponse(request,
    "response.html",
    {
        "request": request,
        "question": question.question,
        "answer": answer
    })

def generate_answer(question, keywords):
    prompt = (
        "You are an IELTS speaking student with expert English speaking skills. "
        "Now you need to give the concise and direct answer given the hints of keywords input. "
        "The score criteria is fluency and coherence, lexical resource, grammatical range and accuracy, pronunciation. "
        f"The question is: {question}. My answer is {keywords}, and you need to rephrase the answer to at least 3 sentences and no more than 10 sentences."
    )

    SparkApi.answer = ""  # Clear the previous answer
    SparkApi.main(appid, api_key, api_secret, Spark_url, domain, getText("user", prompt))

    return SparkApi.answer

# Register user
@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    return templates.TemplateResponse(request,
    "login.html",
    {
        "request": request,
        "message": "Registration successful! Please log in."
    })

# Login user
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.password):
        return templates.TemplateResponse(request,
    "index.html",
    {
        "request": request,
        "message": "Login successful!"
    })
    else:
        raise HTTPException(status_code=400, detail="Invalid username or password")
