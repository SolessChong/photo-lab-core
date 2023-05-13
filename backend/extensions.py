from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import create_engine
from .config import mysql_uri

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =  mysql_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

engine = create_engine(mysql_uri)

# shorthand for add, commit and close
def a_c_c(obj, db):
    db.session.add(obj)
    db.session.commit()
    db.session.close()
    return obj