import httpx
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from gateway import config

app = FastAPI(
    title="Hora Model Host API Gateway",
    description="Secure public API gateway for Gemma 4 LLM",
    version="1.0.0"
)

# Enable CORS for convenience in various client environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validates the Bearer token against the configured API_KEY."""
    if not config.API_KEY:
        # If API_KEY is empty/None in config, we bypass auth (not recommended in production)
        return None
    
    if not credentials or credentials.credentials != config.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Access Denied.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Local HTTPX Async Client for proxying
client = httpx.AsyncClient(base_url=config.OLLAMA_BASE_URL, timeout=600.0)

@app.get("/", status_code=200)
async def root_check():
    """Public unauthenticated root check endpoint."""
    return {
        "status": "healthy",
        "gateway": "online",
        "message": "Hora Model Host Gateway is online."
    }

@app.get("/v1", status_code=200)
async def v1_check():
    """Public unauthenticated v1 check endpoint."""
    return {
        "status": "healthy",
        "gateway": "online",
        "message": "Hora Model Host Gateway API v1 is online."
    }

@app.get("/health", status_code=200)
async def health_check():
    """Public unauthenticated health check endpoint."""
    try:
        # Check local Ollama health
        response = await client.get("/")
        ollama_status = "online" if response.status_code == 200 else "degraded"
    except Exception:
        ollama_status = "offline"
        
    return {
        "status": "healthy",
        "gateway": "online",
        "ollama": ollama_status,
        "model": config.GEMMA_MODEL
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_request(request: Request, path: str, api_key: str = Depends(verify_api_key)):
    """Catch-all reverse proxy that forwards all authorized requests to Ollama."""
    url = f"{config.OLLAMA_BASE_URL}/{path}"
    
    # Forward query parameters
    params = dict(request.query_params)
    
    # Read incoming request body
    body = await request.body()
    
    # Prepare outgoing headers (strip host, authorization, etc. to avoid conflicts)
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ["host", "authorization", "content-length"]:
            headers[k] = v
            
    # Create the request to the local Ollama instance
    rp_req = client.build_request(
        method=request.method,
        url=url,
        params=params,
        headers=headers,
        content=body
    )
    
    # Send the request and stream the response back
    try:
        rp_resp = await client.send(rp_req, stream=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to model hosting backend: {str(e)}"
        )

    # Clean up response headers
    resp_headers = {}
    for k, v in rp_resp.headers.items():
        if k.lower() not in ["content-length", "transfer-encoding", "connection"]:
            resp_headers[k] = v

    # Stream the bytes back to the client
    return StreamingResponse(
        rp_resp.aiter_bytes(),
        status_code=rp_resp.status_code,
        headers=resp_headers,
        background=httpx.AsyncClient.clean_up if hasattr(httpx.AsyncClient, "clean_up") else None
    )

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()
