"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from database import create_tables, engine
from app.routes import router

from app.auto_sync_service import auto_sync_service

from fastapi.middleware.cors import CORSMiddleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    try:
        # Start auto sync service
        auto_sync_service.start_auto_sync()
        print("Auto sync service started on startup")
    except Exception as e:
        print(f"Failed to start auto sync service: {str(e)}")
    
    yield
    
    # Shutdown
    try:
        auto_sync_service.stop_auto_sync()
        print("Auto sync service stopped on shutdown")
    except Exception as e:
        print(f"Failed to stop auto sync service: {str(e)}")


# Tạo FastAPI app với lifespan
app = FastAPI(
    title="Email Sync API",
    description="API để đồng bộ email từ Microsoft Graph API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://outlook-mail.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    """
    Root endpoint
    """
    return JSONResponse({
        "message": "Email Sync API",
        "version": "1.0.0",
        "docs": "/docs"
    })


# @app.post("/init-db")
# def init_database():
#     """
#     Khởi tạo database và tạo các bảng
#     """
#     try:
#         # Test kết nối database trước
#         with engine.connect() as connection:
#             result = connection.execute("SELECT 1")
        
#         # Tạo bảng
#         create_tables()
        
#         # Kiểm tra bảng đã được tạo
#         with engine.connect() as connection:
#             result = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
#             tables = [row[0] for row in result]
        
#         return JSONResponse({
#             "message": "Database initialized successfully",
#             "tables_created": tables,
#             "total_tables": len(tables)
#         })
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 