import uvicorn


def main():
    uvicorn.run(
        "sim_atlas_backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
    )
