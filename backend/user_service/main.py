import fastapi
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import auth

app = fastapi.FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to User Service"}

@app.get("/health")
async def health():
    return {"service": "User Service", "status": "running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)