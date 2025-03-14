"""
主入口點 - 用於 Railway 部署
整合解決方案，不再依賴 langserve
"""

import uvicorn
import os
import logging
from integrated_solution import app

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # 使用主要的PORT環境變數，這是Railway會設置的
    port = int(os.getenv('PORT', 8080))
    logger.info(f"啟動FastAPI應用於端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
