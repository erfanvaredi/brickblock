from fastapi import FastAPI, APIRouter, Depends, File, UploadFile, Body, Query, Form, HTTPException
from typing import Callable, List, Type, Any, Union
from fastapi.routing import APIRoute
from pydantic import BaseModel
import inspect
from functools import wraps

app = FastAPI()
router = APIRouter()

def is_pydantic_model(param_type: Any) -> bool:
    """
    Check if the parameter type is a Pydantic model by checking if it's a subclass of BaseModel.
    This function now safely handles cases where param_type might not be a class.
    """
    try:
        # Check if param_type is a type and is a subclass of BaseModel
        return issubclass(param_type, BaseModel)
    except TypeError:
        # If param_type is not a type (e.g., a typing.Generic), this will prevent the TypeError
        return False

def create_endpoint_function(func: Callable, param_details: dict):
    @wraps(func)
    async def endpoint(*args, **kwargs):
        call_params = {}
        for name, value in kwargs.items():
            if name in param_details:
                param_type, param_source = param_details[name]
                if param_source == 'body' and is_pydantic_model(param_type):
                    # For Pydantic models, parse and validate the model from the body
                    model = param_type.parse_obj(value)
                    call_params[name] = model
                else:
                    call_params[name] = value
        result = await func(**call_params)
        # Automatically convert Pydantic models to dictionaries for serialization
        if isinstance(result, BaseModel):
            return result.dict()
        return result

    return endpoint

def add_endpoint_to_router(router: APIRouter, func: Callable):
    endpoint_path = f"/{func.__name__}"
    param_details = {}

    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        param_annotation = Union[param.annotation, Any]  # Ensure there's always an annotation
        if param_annotation == UploadFile or param_annotation == List[UploadFile]:
            param_details[name] = (param_annotation, 'file')
        elif is_pydantic_model(param_annotation):
            param_details[name] = (param_annotation, 'body')
        elif param_annotation in [int, float, bool, str, Any]:  # Simple types or Any (fallback)
            param_details[name] = (param_annotation, 'query')
        else:
            param_details[name] = (param_annotation, 'body')

    endpoint_func = create_endpoint_function(func, param_details)
    methods = ["POST"] if 'file' in [p[1] for p in param_details.values()] or 'body' in [p[1] for p in param_details.values()] else ["GET", "POST"]
    
    router.add_api_route(endpoint_path, endpoint_func, methods=methods)

# Example Pydantic model
class UserProfile(BaseModel):
    username: str
    biography: str

print(is_pydantic_model(UserProfile))

# Example function using Pydantic model as input and output
async def user_profile_func(profile: UserProfile = Body(...)) -> UserProfile:
    # Modify the profile as needed
    return profile

# Adding the new function as an endpoint
add_endpoint_to_router(router, user_profile_func)


# Example function that can handle a mix of parameter types
async def example_func(name: str = Form(...), age: int = Form(...), 
                    #    bio: dict = Body(...), 
                       profile_picture: UploadFile = File(...)):
    # return {"message": f"Name: {name}, Age: {age}, Bio: {bio}, Received file: {profile_picture.filename}"}
    return {"message": f"Name: {name}, Age: {age}, Received file: {profile_picture.filename}"}

# Adding the example function as an endpoint
add_endpoint_to_router(router, example_func)
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

# Adding endpoints to the router
add_endpoint_to_router(router, sync_function)
add_endpoint_to_router(router, async_function)
# Including the router in the FastAPI app
app.include_router(router)


# Including the router in the FastAPI app
app.include_router(router)
