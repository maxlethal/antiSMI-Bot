import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

db_user = os.getenv("db_user")
db_pass = os.getenv("db_pass")
db_name = os.getenv("db_name")
db_host = os.getenv("db_host")

asmi = create_engine(f'postgresql+psycopg2://{db_user}:{db_pass}@{db_host}/{db_name}')
gate = os.getenv("gate")
token = os.getenv("token")
