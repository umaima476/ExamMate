from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
import uuid
import aiofiles
import os
import json
import glob
import google.generativeai as genai
from dotenv import load_dotenv
from api.utils.content_extraction import extract_text
from api.utils.general import get_file_hash

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

generator_router = APIRouter()
content_dir = "course_content"
ALLOWED_EXTENSIONS = {"pdf", "ppt", "pptx"}

@generator_router.post("/upload-content")
async def upload_content(file: UploadFile = File(...)):
    # 1. Basic Validations
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")
        
    extension = file.filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file format.")
        
    try:
        os.makedirs(content_dir, exist_ok=True)
        
        # Generate a unique ID and filename
        file_id = str(uuid.uuid4())
        save_filename = f"{file_id}_{file.filename}"
        save_path = os.path.join(content_dir, save_filename)

        file_bytes = await file.read()
        new_file_hash = get_file_hash(file_bytes)
        existing_files = os.listdir(content_dir)
        for existing_file in existing_files:
            file_path = os.path.join(content_dir, existing_file)
            
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    existing_content = f.read()
                    if get_file_hash(existing_content) == new_file_hash:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "status": "error",
                                "message": "This exact content has already been uploaded."
                            }
                        )
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            
        # 2. Save the file locally
        async with aiofiles.open(save_path, "wb") as content_file:
            await content_file.write(file_bytes)

        # Return the file_id so the frontend can use it for the second step
        return JSONResponse({
            "file_id": file_id,
            "original_filename": file.filename,
            "status": "uploaded_successfully"
        })

    except Exception as e:
        print(f"Error during upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@generator_router.post("/generate-questions")
async def generate_questions(
    file_id: str = Form(...), 
    mcq_count: int = Form(...), 
    subjective_count: int = Form(...)
):
    try:
        # 1. Find the file on the server using the file_id
        target_file = None
        for filename in os.listdir(content_dir):
            if filename.startswith(file_id):
                target_file = filename
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found. Please upload again.")

        file_path = os.path.join(content_dir, target_file)
        
        # 2. Read and Extract Text
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        text_content = extract_text(file_bytes, target_file)

        # 3. Configure Gemini and Prompt
        model = genai.GenerativeModel("gemini-flash-latest")
        
        prompt = f"""
        You are an expert academic examiner. Generate a quiz based on the provided text.

        ### CONSTRAINTS:
        1. **COUNTS**: Generate exactly {mcq_count} MCQs and {subjective_count} subjective questions.
        2. **NO META-QUESTIONS**: Do not ask questions about units, chapters, or the document structure.
        3. **NOT MENTION THE DOCUMENT**: Do not refer to the source document in the questions (e.g., "According to the text...", or "according to the lecture notes")
        3. **IGNORE PREFATORY MATERIAL**: Skip titles, cover pages, and tables of contents.
        4. **FORMAT**: Return ONLY a valid JSON list of objects.
        5. **STRUCTURE**: 
           - For MCQs: {{"type": "mcq", "question": "...", "options": ["...", "...", "...", "..."], "answer": "..."}}
           - For Subjective: {{"type": "subjective", "question": "...", "answer": "short hint"}}

        ### TEXT:
        {text_content[:15000]}
        """

        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        quiz_data = json.loads(response.text)

        return JSONResponse({
            "status": "success",
            "quiz": quiz_data
        })

    except Exception as e:
        print(f"Error during generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@generator_router.get("/list-files")
def list_files():
    files_list = []
    try:
        if not os.path.exists(content_dir):
            return JSONResponse({"files":[]})
        
        for filename in os.listdir(content_dir):
            if os.path.isfile(os.path.join(content_dir,filename)):
                
                if "_" in filename:
                    file_id, original_name = filename.split("_", 1)
                else:
                    file_id = filename
                    original_name = filename
                
                files_list.append({
                    'file_id': file_id,
                    'original_name': original_name
                })
        return JSONResponse(content=files_list)
    except Exception as e:
        print(f"Error loading files: {e}")
        return HTTPException(
            status_code=500,
            detail="Failed to lead files."
        )


@generator_router.delete("/delete-file/{file_id}")
def delete_file(file_id: str):
    """
    Locates a file starting with the given file_id and deletes it from the server.
    """
    try:
        if not os.path.exists(content_dir):
            raise HTTPException(status_code=404, detail="content directory not found")

        search_pattern = os.path.join(content_dir, f"{file_id}_*")
        files = glob.glob(search_pattern)

        if not files:
            return JSONResponse(
                status_code=404, 
                content={"detail": "File not found on server"}
            )

        # Delete the file(s) found
        for file_path in files:
            os.remove(file_path)
            print(f"Deleted: {file_path}")

        return JSONResponse(content={"status": "success", "message": "File deleted successfully"})

    except Exception as e:
        print(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=500, 
            content={"detail": f"System error during deletion: {str(e)}"}
        )

@generator_router.get("/download-file/{file_id}")
def download_file(file_id: str):
    """
    Finds the file starting with file_id and sends it to the user's browser.
    """
    try:
        # Search for the file pattern: file_id_filename.ext
        search_pattern = os.path.join(content_dir, f"{file_id}_*")
        files = glob.glob(search_pattern)

        if not files:
            raise HTTPException(status_code=404, detail="File not found on server")

        file_path = files[0]  # Get the first match
        original_filename = os.path.basename(file_path).split("_", 1)[1]

        # Return the file as a download
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type='application/octet-stream'
        )

    except Exception as e:
        print(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving file")