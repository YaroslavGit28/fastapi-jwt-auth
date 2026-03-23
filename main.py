"""
Main application file.

Инициализирует FastAPI приложение и подключает роутеры.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.configs import settings
from app.routers import auth_router, users_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API с Bearer-аутентификацией и JWT",
    docs_url="/docs",
    redoc_url="/redoc",
)


app.include_router(auth_router)
app.include_router(users_router)

@app.get("/", tags=["Root"])
async def root():
    """
    Корневой эндпоинт.
    Возвращает информацию о API.
    """
    return JSONResponse(
        content={
            "message": "User Authentication API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "endpoints": {
                "login": "POST /auth/login",
                "current_user": "GET /users/me",
            }
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check эндпоинт.
    Проверяет что API работает.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.APP_VERSION
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
