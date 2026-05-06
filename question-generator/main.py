from api import create_app
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = create_app()

app.mount("/api/static", StaticFiles(directory="api/static"), name="staic")

@app.get("/")
async def read_index():
    return FileResponse("api/static/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)