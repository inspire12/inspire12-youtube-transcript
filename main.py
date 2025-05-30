from mimetypes import inited

import uvicorn
from fastapi import FastAPI
from transcript_extractor.extractor import run
app = FastAPI()
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/youtube")
async def get_youtube(yid: str):
    extractor = run(yid)

if __name__ == '__main__':
    uvicorn.run(app)