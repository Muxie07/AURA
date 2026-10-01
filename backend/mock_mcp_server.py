
import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine

import app.database.base


def mock_create_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
app.database.base.create_engine = mock_create_engine

if __name__ == "__main__":
    uvicorn.run("app.mcp_main:app", host="127.0.0.1", port=8000, log_level="info")
