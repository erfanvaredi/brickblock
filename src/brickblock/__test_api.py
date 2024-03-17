from fastapi import FastAPI, APIRouter, Depends, Body, HTTPException
from typing import Callable, get_type_hints
import inspect
from functools import wraps

app = FastAPI()
router = APIRouter()

def add_endpoint_to_router(router: APIRouter, func: Callable, mode: str = 'query'):
    """
    Dynamically creates an endpoint from a provided function (sync or async) and adds it to the specified FastAPI router.
    - The function's name becomes the endpoint's path.
    - Function parameters are converted into query parameters or a JSON request body, based on the mode specified.
    
    Args:
    - router: FastAPI APIRouter instance to add the endpoint to.
    - func: User-defined function (can be async or sync) to base the endpoint on.
    - mode: 'query' to use query parameters, 'body' for JSON request body. Defaults to 'query'.
    """
    endpoint_path = f"/{func.__name__}"  # Endpoint path derived from the function name
    
    async def async_wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    if mode == 'query':
        # Create endpoint using query parameters
        @wraps(func)
        async def endpoint(*args, **kwargs):  # Wraps to preserve metadata
            return await async_wrapper(*args, **kwargs)
        methods = ["GET"]
    elif mode == 'body':
        # Create endpoint using a request body
        @wraps(func)
        async def endpoint(body: dict = Body(...)):  # Wraps to preserve metadata
            return await async_wrapper(**body)
        methods = ["POST"]
    else:
        raise HTTPException(status_code=400, detail="Invalid mode specified. Use 'query' or 'body'.")

    router.add_api_route(endpoint_path, endpoint, methods=methods)

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
add_endpoint_to_router(router, sync_function, mode='query')
add_endpoint_to_router(router, async_function, mode='query')

# Including the router in the FastAPI app
app.include_router(router)

open()