"""python -m tools.moodle_ws_stub – chạy máy chủ Moodle mô phỏng (mặc định 127.0.0.1:8091)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("tools.moodle_ws_stub.app:app", host=os.getenv("MOODLE_STUB_HOST", "127.0.0.1"),
                port=int(os.getenv("MOODLE_STUB_PORT", "8091")), log_level="info")
