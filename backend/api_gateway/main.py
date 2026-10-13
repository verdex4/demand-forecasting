import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response

app = FastAPI(title="API Gateway")
MONOLITH_URL = "http://localhost:8000"

@app.get("/")
async def index():
    return {"message": "API Gateway"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_monolith(request: Request, path: str):
    try:
        async with httpx.AsyncClient() as client:
            url = f"{MONOLITH_URL}/{path}"
    
            response = await client.request(
                method=request.method,
                url=url,
                headers=request.headers.raw,
                params=request.query_params,
                content=await request.body(),
                follow_redirects=True,
            )
    
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))