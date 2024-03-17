from fastapi import FastAPI, APIRouter, Depends, File, UploadFile, Body, Query, Form, HTTPException
from typing import Callable, List, Type, Any
from fastapi.routing import APIRoute
import inspect
from functools import wraps

app = FastAPI()
router = APIRouter()

def create_endpoint_function(func: Callable, param_details: dict):
    """
    Creates a wrapper function around the user-defined function 'func',
    dynamically handling query, body, and file parameters.
    """
    
    async def async_wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    @wraps(func)
    async def endpoint(*args, **kwargs):
        # Prepare parameters (query, body, files) to pass to the actual function
        call_params = {}
        for name, value in kwargs.items():
            if name in param_details:
                param_type = param_details[name]
                if param_type == 'body':
                    # Body parameters unpacked from kwargs
                    call_params.update(value)
                else:
                    # Query and file parameters directly passed
                    call_params[name] = value
        return await async_wrapper(*args, **call_params)

    return endpoint

def add_endpoint_to_router(router: APIRouter, func: Callable):
    """
    Dynamically creates an endpoint from a provided function (sync or async) that may include
    query parameters, JSON request body, and file uploads, and adds it to the specified FastAPI router.
    """
    endpoint_path = f"/{func.__name__}"  # Endpoint path derived from the function name
    param_details = {}

    # Inspect function parameters to determine how to handle them (query, body, file)
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        if param.annotation == UploadFile or param.annotation == List[UploadFile]:
            param_details[name] = 'file'
        elif param.annotation in [int, float, bool, str]:  # Simple types for query parameters
            param_details[name] = 'query'
        else:
            param_details[name] = 'body'

    # Create a dynamic endpoint function
    endpoint_func = create_endpoint_function(func, param_details)

    # Determine methods based on parameter types
    methods = ["POST"] if 'file' in param_details.values() or 'body' in param_details.values() else ["GET", "POST"]
    
    # Add the dynamic endpoint to the router
    router.add_api_route(endpoint_path, endpoint_func, methods=methods)

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
