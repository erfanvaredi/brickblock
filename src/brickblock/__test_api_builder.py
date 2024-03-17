from api.api_handler import APIBuilder
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel

# Example function that can handle a mix of parameter types
async def example_func(name: str = Form(...), age: int = Form(...), 
                    #    bio: dict = Body(...), 
                       profile_picture: UploadFile = File(...)):
    # return {"message": f"Name: {name}, Age: {age}, Bio: {bio}, Received file: {profile_picture.filename}"}
    return {"message": f"Name: {name}, Age: {age}, Received file: {profile_picture.filename}"}

# Example synchronous function
def sync_function(name: str, age: int):
    return {"message": f"Hello {name}, you are {age} years old."}

# Example asynchronous function
async def async_function(name: str, age: int):
    # Simulate async I/O operation
    message = await fake_async_io_operation(name, age)
    return {"message": message}

async def fake_async_io_operation(name, age):
    return f"Hello {name}, in async manner, you are {age} years old."

# Example Pydantic model
class UserProfile(BaseModel):
    username: str
    biography: str
    
class UserProfileOutput(BaseModel):
    desc: str
    id: int


# Example function using Pydantic model as input and output
async def user_profile_func(profile: UserProfile) -> UserProfileOutput:
    # Modify the profile as needed
    return UserProfileOutput(
        desc=f'hello {profile.username}: {profile.biography}',
        id=1222
    )


app = FastAPI()

pipeline = Pipe

APIBuilder\
    .init()\
    .add_endpoint_to_router([sync_function, async_function,example_func,user_profile_func])\
    .update_fastapi_app(app)
