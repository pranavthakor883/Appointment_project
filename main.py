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
        
        #fetch exist_user row in python using the fetchcone
        exist_user = cursor.fetchone()
        
        if exist_user is None:
            raise HTTPException(status_code=401,detail="Invalid email or password")
        
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
        

#Provider create
class ProviderCreate(BaseModel):
    user_id: int
    specialization: str
    description: str | None = None
    
@app.post("/providers")
def create_provider(provider: ProviderCreate):

    cursor = conn.cursor()

    try:
        cursor.execute(
            """insert into providers(user_id, specialization, description) values(%s, %s, %s) returning id, user_id, specialization, description, created_at""",
            (provider.user_id, provider.specialization, provider.description)
        )

        new_provider = cursor.fetchone()
        conn.commit()

        return {
            "message": "Provider created successfully",
            "provider": {
                "id": new_provider[0],
                "user_id": new_provider[1],
                "specialization": new_provider[2],
                "description": new_provider[3],
                "created_at": new_provider[4]
            }
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400,detail=str(e))

    finally:
        cursor.close()
        

#Get the providers
@app.get("/providers")
def get_providers():
    
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''
            select p.id,p.user_id,u.name,u.email,p.specialization,p.description,p.created_at 
            from providers p 
            join users u 
            on p.user_id = u.id 
            order by p.id
            '''
            
        )
        
        providers = cursor.fetchall()
        
        return[
            {
                "id": provider[0],
                "user_id": provider[1],
                "name": provider[2],
                "email": provider[3],
                "specialization": provider[4],
                "description": provider[5],
                "created_at": provider[6]
            }
            for provider in providers
        ] 
    finally:
        cursor.close()
    

#Create a Services
class ServiceCreate(BaseModel):
    provider_id:int
    name:str
    description:str | None=None
    duration_minutes:int
    price:float
    
@app.post("/services")
def create_service(service:ServiceCreate):
    
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''insert into services(provider_id,name,description,duration_minutes,price) values(%s,%s,%s,%s,%s) returning id,provider_id,name,description,duration_minutes,price''',
            (service.provider_id,service.name,service.description,service.duration_minutes,service.price)
        )
        
        new_service = cursor.fetchone()
        
        conn.commit()
        
        return{
            "message":"Service Created Successfully",
            "service":{
                "id" : new_service[0],
                "provider_id":new_service[1],
                "name":new_service[2],
                "description":new_service[3],
                "duration_minutes":new_service[4],
                "price":new_service[5]            
            }
        }
    except Exception as e:
        cursor.rollback()
        raise HTTPException(status_code=400,detail=str(e))
    
    finally:   
        cursor.close()
 
    
            
