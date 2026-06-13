from fastapi import HTTPException

def raise_error(detail: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=detail)