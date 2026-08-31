from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from database import conn
import bcrypt


app = FastAPI()


@app.get("/")
def home():
    return {"message":"Appointment api is running!"}


class UserCreate(BaseModel):
    name : str
    email : str
    password : str
    role : str = "customer"
    
@app.post("/users")
def create_user(user:UserCreate):
     
    cursor = conn.cursor()
    
    
    try: 
        #In this hashpw using the bytes for hasing the password nad also for decode use the hash
        password_hash = bcrypt.hashpw(user.password.encode("utf-8"),bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            """insert into users (name,email,password_hash,role) values (%s,%s,%s,%s) RETURNING id, name, email, role""",
            (user.name,user.email,password_hash,user.role)
        )
        
        new_user = cursor.fetchone()
        conn.commit()
        
        #you can give the orderno of columns according to returing column orderno
        return{
                "message":"User created succesfully" ,
                "user":{
                    "id": new_user[0],
                    "name": new_user[1],
                    "email": new_user[2],
                    "role": new_user[3],
                }
            }
    
    except Exception as e: 
        cursor.rollback()
        raise HTTPException( status_code = 400, detail = str(e) )
    
    finally:
        cursor.close()
     
     
    
#user Login
class UserLogin(BaseModel):
    email:str
    password:str
    

@app.post("/auth/login")
def login(user:UserLogin):
    
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """select id, name, role, email, password_hash from users where email=%s""",
            (user.email,)    
        )
        
        #fetch row in python using the fetchcone
        exist_user = cursor.fetchone()
        
        if exist_user is None:
            raise HTTPException(status_code=401,detail="Invalid email or password")
        
        #exist_user[3] means the column of 3 where password_hash
        #but you also know what you gave the order in select query 
        password_hash = exist_user[4]
        
        #check the password either passowrd is matching or not with the original password
        if not bcrypt.checkpw(user.password.encode("utf-8"),password_hash.encode("utf-8")):
            raise HTTPException(status_code=401,detail="Invalid email or password")
        
        #in you must the same order which you gave in the while select query
        return{
            "message":"Login successfully",
            "user":{
                "id": exist_user[0],
                "name": exist_user[1],
                "role": exist_user[2],
                "email":exist_user[3], 
            }
        }
    
    finally:
        cursor.close()
            
