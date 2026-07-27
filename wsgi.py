"""本番デプロイ用のWSGIエントリーポイント（Render / PythonAnywhere などで使用）"""
from task_manager.app import app as application

app = application
