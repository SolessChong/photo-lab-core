from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

DATABASE_URI = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/jarvis?charset=utf8'

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

class JChat(Base):
    __tablename__ = 'j_chat'
    id = Column(Integer, primary_key=True)
    message = Column(String)

def decode_unicode(unicode_string):
    return bytes(unicode_string, 'utf-8').decode('unicode_escape')

session = Session()

for j_chat_item in session.query(JChat):
    decoded_message = decode_unicode(j_chat_item.message)
    try:
        print(f"ID: {j_chat_item.id}, Message: {decoded_message}")
    except UnicodeEncodeError:
        print(f"ID: {j_chat_item.id}")
    except Exception as e:
        print(f"Error: {e}")

session.close()
