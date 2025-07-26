"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from database import create_tables, engine
from app.routes import router

# Tạo FastAPI app
app = FastAPI(
    title="Email Sync API",
    description="API để đồng bộ email từ Microsoft Graph API",
    version="1.0.0"
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


@app.post("/init-db")
def init_database():
    """
    Khởi tạo database và tạo các bảng
    """
    try:
        # Test kết nối database trước
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
        
        # Tạo bảng
        create_tables()
        
        # Kiểm tra bảng đã được tạo
        with engine.connect() as connection:
            result = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result]
        
        return JSONResponse({
            "message": "Database initialized successfully",
            "tables_created": tables,
            "total_tables": len(tables)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 