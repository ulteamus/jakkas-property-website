from flask_login import LoginManager # type: ignore
from flask_wtf.csrf import CSRFProtect # type: ignore

login_manager = LoginManager()
login_manager.login_view = "auth.admin_login"
login_manager.login_message_category = "warning"

csrf = CSRFProtect()
