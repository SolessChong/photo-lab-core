from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import create_engine

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

engine = create_engine('mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab')
