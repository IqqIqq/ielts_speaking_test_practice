import SparkApi
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")  # 确保路径正确

#以下密钥信息从控制台获取
appid = "750d6733"     #填写控制台中获取的 APPID 信息
api_secret = "ZGFkNTAwNmNlYTJlNWQwMjU4NTZlNTQ1"   #填写控制台中获取的 APISecret 信息
api_key ="604232ad1d5ab568da8f446e77240ec3"    #填写控制台中获取的 APIKey 信息

#用于配置大模型版本，默认“general/generalv2”
domain = "general"   # v1.5版本
#domain = "generalv2"    # v2.0版本
#云端环境的服务地址
Spark_url = "ws://spark-api.xf-yun.com/v1.1/chat"  # v1.5环境的地址
#Spark_url = "ws://spark-api.xf-yun.com/v2.1/chat"  # v2.0环境的地址

# length = 0

def getText(role,content):
    text =[]
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
    return templates.TemplateResponse("query_form.html", {"request": request})

@app.post("/qa", response_class=HTMLResponse)
async def call_llm(request: Request, query: str = Form(...)):
    question = checklen(getText("user", query))
    SparkApi.answer = ""  # 清空之前的答案

    # 调用 SparkApi 生成答案
    SparkApi.main(appid, api_key, api_secret, Spark_url, domain, question)

    # 生成完整的答案
    answer = generate_answer(query, SparkApi.answer)

    return templates.TemplateResponse("response.html", {"request": request, "answer": answer})

# def generate_answer(query, spark_answer):
#     # 生成完整的答案逻辑
#     prompt = (
#         "You are an IELTS speaking interview with expert English speaking skills. "
#         "Now you need to give the example answer given the hints of keywords input. "
#         "The score criteria is fluency and coherence, lexical resource, grammatical range and accuracy, pronunciation. "
#         f"The question is: {query}. The generated answer is: {spark_answer}."
#     )
    
#     # 这里可以根据需要进一步处理 prompt
#     # 例如，您可以将 prompt 传递给 SparkApi 进行进一步处理
#     return spark_answer  # 返回生成的答案

# 数据库配置
#DATABASE_URL = os.getenv("DATABASE_URL")  # 从环境变量获取连接字符串
#DATABASE_URL = "postgres://default:6uARh4lwMqHC@ep-quiet-feather-a43ccz0v-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require"
DATABASE_URL = "postgres://postgres.plseahzuhkjjozmkpbqs:FTaY7wDwskquSkEA@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require&supa=base-pooler.x"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义模型
class Part1Question(Base):
    __tablename__ = "part_1"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)

class Part2Question(Base):
    __tablename__ = "part_2"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)

class Part3Question(Base):
    __tablename__ = "part_3"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)

# 定义用户模型
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
# 创建数据库表
Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    part1_questions = db.query(Part1Question).all()
    part2_questions = db.query(Part2Question).all()
    part3_questions = db.query(Part3Question).all()

    # 将 Part 2 和 Part 3 的问题按问号分隔，并过滤掉空字符串
    part2_questions_list = [list(filter(None, q.question.split('?'))) for q in part2_questions]
    part3_questions_list = [list(filter(None, q.question.split('?'))) for q in part3_questions]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "part1_questions": part1_questions,
        "part2_questions": part2_questions_list,
        "part3_questions": part3_questions_list
    })

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
        answer = generate_answer(question.question, keywords)

    return templates.TemplateResponse("response.html", {"request": request, "question": question.question, "answer": answer})

def generate_answer(question, keywords):
    prompt = (
        "You are an IELTS speaking student with expert English speaking skills. "
        "Now you need to give the concise and direct answer given the hints of keywords input. "
        "The score criteria is fluency and coherence, lexical resource, grammatical range and accuracy, pronunciation. "
        f"The question is: {question}. My answer is {keywords}, and you need to rephrase the answer to at least 3 sentences."
    )

    SparkApi.answer = ""  # 清空之前的答案
    SparkApi.main(appid, api_key, api_secret, Spark_url, domain, getText("user", prompt))

    return SparkApi.answer

# 注册用户
@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    return templates.TemplateResponse("login.html", {"request": request, "message": "Registration successful! Please log in."})

# 登录用户
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.password):
        return templates.TemplateResponse("index.html", {"request": request, "message": "Login successful!"})
    else:
        raise HTTPException(status_code=400, detail="Invalid username or password")


