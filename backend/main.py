from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from groq import Groq
import os, json
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
SYSTEM_PROMPTS = {
    "default":    "You are a helpful assistant. Reply in the same language as the user.",
    "coder":      "You are an expert programmer. Provide clean, well-commented code with explanations. Reply in the same language as the user.",
    "translator": "You are a professional translator. Translate accurately while preserving tone and meaning.",
    "teacher":    "You are a patient teacher. Explain concepts clearly with examples. Reply in the same language as the user.",
    "writer":     "You are a creative writer. Help with writing, editing, and storytelling. Reply in the same language as the user.",
}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "llama-3.3-70b-versatile"
    system: Optional[str] = "default"

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    system_content = SYSTEM_PROMPTS.get(req.system, SYSTEM_PROMPTS["default"])

    def generate():
        try:
            stream = client.chat.completions.create(
                model=req.model,
                messages=[
                    {"role": "system", "content": system_content},
                    *[{"role": m.role, "content": m.content} for m in req.messages],
                ],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'content': delta})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/models")
def get_models():
    return {"models": [
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
        {"id": "llama-3.1-8b-instant",    "name": "Llama 3.1 8B (Nhanh)"},
        {"id": "mixtral-8x7b-32768",       "name": "Mixtral 8x7B"},
        {"id": "gemma2-9b-it",             "name": "Gemma 2 9B"},
    ]}

@app.get("/system-prompts")
def get_system_prompts():
    return {"prompts": [
        {"id": "default",    "name": "🤖 Trợ lý"},
        {"id": "coder",      "name": "💻 Lập trình"},
        {"id": "translator", "name": "🌐 Dịch thuật"},
        {"id": "teacher",    "name": "📚 Giảng dạy"},
        {"id": "writer",     "name": "✍️ Viết lách"},
    ]}
