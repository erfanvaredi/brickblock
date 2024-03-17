from fastapi import FastAPI, APIRouter, Depends, File, UploadFile, Body, Query, Form, HTTPException
from typing import Callable, List, Type, Any, List
from fastapi.routing import APIRoute
import inspect
from functools import wraps
from pydantic import BaseModel

class APIBuilder:
    
    def __init__(self):
        self.router:APIRouter = None
    
    
    @staticmethod
    def init():
        __api = APIBuilder()
        __api.router = APIRouter()
        return __api

    def is_pydantic_model(self, param_type: Any) -> bool:
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
        
    def create_endpoint_function(self, func: Callable, param_details: dict):
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
                    # param_type = param_details[name]
                    param_type, param_source = param_details[name]

                    if param_source == 'body':
                        # Body parameters unpacked from kwargs
                        call_params.update(value)
                    if param_source == 'pydantic' and self.is_pydantic_model(param_type):
                        # For Pydantic models, parse and validate the model from the body
                        model = param_type.parse_obj(value)
                        call_params[name] = model
                    else:
                        # Query and file parameters directly passed
                        call_params[name] = value
            __result =  await async_wrapper(*args, **call_params)
            
            # Automatically convert Pydantic models to dictionaries for serialization
            if isinstance(__result, BaseModel):
                return __result.model_dump()
            
            return __result

        return endpoint

    def add_endpoint_to_router(self, list_func: List[Callable]):
        """
        Dynamically creates an endpoint from a provided function (sync or async) that may include
        query parameters, JSON request body, and file uploads, and adds it to the specified FastAPI router.
        """
        for func in list_func:
            endpoint_path = f"/{func.__name__}"  # Endpoint path derived from the function name
            param_details = {}

            if_just_POST = False
            
            # Inspect function parameters to determine how to handle them (query, body, file)
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if param.annotation == UploadFile or param.annotation == List[UploadFile]:
                    param_details[name] = None, 'file'
                    if_just_POST = True
                elif param.annotation in [int, float, bool, str]:  # Simple types for query parameters
                    param_details[name] = None, 'query'
                elif self.is_pydantic_model(param.annotation):
                    param_details[name] = (param.annotation, 'pydantic')
                    if_just_POST = True
                else:
                    param_details[name] = None, 'body'
                    if_just_POST = True

            # Create a dynamic endpoint function
            endpoint_func = self.create_endpoint_function(func, param_details)

            # Determine methods based on parameter types
            # methods = ["POST"] if 'file' in param_details.values() or 'body' in param_details.values() else ["GET", "POST"]
            methods = ["POST"] if if_just_POST else ["GET", "POST"]
            
            # Add the dynamic endpoint to the router
            self.router.add_api_route(endpoint_path, endpoint_func, methods=methods)
        
        return self
    
    def get_router(self):
        return self.router
    
    def update_fastapi_app(self,app):
        app.include_router(self.router)
        return self
