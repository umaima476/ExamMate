from fastapi import FastAPI
from .routes.generater import generator_router

def create_app():
    app = FastAPI(
        title="Question Paper Generator"
      )
    
    app.include_router(generator_router)
    
    return app