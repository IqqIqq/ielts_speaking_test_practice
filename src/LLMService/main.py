import SparkApi
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
    SparkApi.answer = ""
    SparkApi.main(appid, api_key, api_secret, Spark_url, domain, question)
    return templates.TemplateResponse("response.html", {"request": request, "answer": SparkApi.answer})




