import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache




app = Flask(__name__, template_folder='horizontemplates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://gnsbnrljnxfsra:4825a5fc0c327cfbbeca59c5280b12520fdf68efc4ad26c350666a72d5df80f5@ec2-3-210-173-88.compute-1.amazonaws.com:5432/deofa5um7ur7us'
app.config['SECRET_KEY'] = '2411628bb0b13ce0c676dfde280ba245'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
mail = Mail(app)
db.init_app(app)
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 3600
app.config['CACHE_DIR'] = 'cache' # path to your server cache folder
app.config['CACHE_THRESHOLD'] = 100000
cacheen = Cache(app)



from Swapp import routes

