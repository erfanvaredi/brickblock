from fastapi import APIRouter, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
import types

from typing import Callable, List, Type, Any, List, Optional
import inspect
from functools import wraps
from pydantic import BaseModel


class APIBuilder:
    """
    APIBuilder is a utility class designed to facilitate the dynamic creation and registration of endpoints in a FastAPI application.
    It simplifies the process of defining API routes by automating the handling of request parameters, including query parameters,
    JSON request bodies, and file uploads. The class also supports both synchronous and asynchronous endpoint functions, seamlessly integrating
    them into the FastAPI routing system.

    Attributes:
        router (APIRouter): An instance of FastAPI's APIRouter that holds the dynamically created API routes.

    Methods:
        init() -> APIBuilder:
            Static method to initialize and return a new instance of APIBuilder with a fresh APIRouter instance.

        is_pydantic_model(param_type: Any) -> bool:
            Checks if the given parameter type is a subclass of Pydantic's BaseModel, indicating that it is a Pydantic model.
            This method is used internally to determine the appropriate handling of request parameters based on their type.

        create_endpoint_function(func: Callable, param_details: dict) -> Callable:
            Creates a wrapper function around a user-defined function 'func', dynamically handling its parameters based on the provided
            'param_details' dictionary. The wrapper function is designed to parse and validate request parameters, invoke the user-defined
            function with these parameters, and handle the function's return value appropriately.

        add_endpoint_to_router(list_func: List[Callable]):
            Takes a list of user-defined functions and dynamically creates endpoints for them, adding these endpoints to the APIBuilder's
            APIRouter instance. This method determines the appropriate HTTP method(s) for each endpoint based on the types of parameters
            the user-defined functions expect.

        get_router() -> APIRouter:
            Returns the APIRouter instance associated with this APIBuilder, containing all dynamically created API routes.

        update_fastapi_app(app: FastAPI):
            Includes the APIBuilder's APIRouter into the given FastAPI application instance 'app', effectively registering all dynamically
            created API routes with the application.

        ```

    Note:
        The APIBuilder class abstracts away some of the repetitive aspects of defining FastAPI routes, particularly in scenarios where
        the application requires dynamic route creation based on a set of predefined functions. It is especially useful in applications
        that require flexible or programmatically generated API endpoints.
    """

    def __init__(self):
        self.router: APIRouter = None

    @staticmethod
    def init():
        """Initializes a new APIBuilder instance."""

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

    # def create_endpoint_function(self, func: Callable, param_details: dict):
    #     """
    #     Creates a wrapper function around the user-defined function 'func',
    #     dynamically handling query, body, and file parameters.
    #     """

    #     async def async_wrapper(*args, **kwargs):
    #         if inspect.iscoroutinefunction(func):
    #             return await func(*args, **kwargs)
    #         else:
    #             return func(*args, **kwargs)

    #     @wraps(func)
    #     async def endpoint(*args, **kwargs):
    #         # Prepare parameters (query, body, files) to pass to the actual function
    #         call_params = {}
    #         for name, value in kwargs.items():
    #             if name in param_details:
    #                 # param_type = param_details[name]
    #                 param_type, param_source = param_details[name]

    #                 if param_source == 'body':
    #                     # Body parameters unpacked from kwargs
    #                     call_params.update(value)
    #                 if param_source == 'pydantic' and self.is_pydantic_model(param_type):
    #                     # For Pydantic models, parse and validate the model from the body
    #                     model = param_type.parse_obj(value)
    #                     call_params[name] = model
    #                 else:
    #                     # Query and file parameters directly passed
    #                     call_params[name] = value
    #         __result =  await async_wrapper(*args, **call_params)

    #         # Automatically convert Pydantic models to dictionaries for serialization
    #         if isinstance(__result, BaseModel):
    #             return __result.model_dump()

    #         return __result

    #     return endpoint

    def create_endpoint_function(self, func: Callable, param_details: dict):
        """
        Extends the original method to support functions that return a streaming response.
        """

        async def async_wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        @wraps(func)
        async def endpoint(*args, **kwargs):
            # Existing setup code to prepare parameters
            call_params = {}
            for name, value in kwargs.items():
                if name in param_details:
                    param_type, param_source = param_details[name]

                    if param_source == "body":
                        call_params.update(value)
                    if param_source == "pydantic" and self.is_pydantic_model(
                        param_type
                    ):
                        model = param_type.parse_obj(value)
                        call_params[name] = model
                    else:
                        call_params[name] = value

            # Invoke the function
            __result = await async_wrapper(*args, **call_params)

            # Check if the result is a streaming type; if so, wrap it in a StreamingResponse
            if isinstance(__result, (types.GeneratorType, types.AsyncGeneratorType)):
                return StreamingResponse(__result)
            elif isinstance(__result, BaseModel):
                return __result.model_dump()

            return __result

        return endpoint

    # def add_endpoint_to_router(self, list_func: List[Callable]):
    #     """
    #     Dynamically creates an endpoint from a provided function (sync or async) that may include
    #     query parameters, JSON request body, and file uploads, and adds it to the specified FastAPI router.
    #     """
    #     for func in list_func:
    #         endpoint_path = f"/{func.__name__}"  # Endpoint path derived from the function name
    #         param_details = {}

    #         if_just_POST = False

    #         # Inspect function parameters to determine how to handle them (query, body, file)
    #         sig = inspect.signature(func)
    #         for name, param in sig.parameters.items():
    #             if param.annotation == UploadFile or param.annotation == List[UploadFile]:
    #                 param_details[name] = None, 'file'
    #                 if_just_POST = True
    #             elif param.annotation in [int, float, bool, str]:  # Simple types for query parameters
    #                 param_details[name] = None, 'query'
    #             elif self.is_pydantic_model(param.annotation):
    #                 param_details[name] = (param.annotation, 'pydantic')
    #                 if_just_POST = True
    #             else:
    #                 param_details[name] = None, 'body'
    #                 if_just_POST = True

    #         # Create a dynamic endpoint function
    #         endpoint_func = self.create_endpoint_function(func, param_details)

    #         # Determine methods based on parameter types
    #         # methods = ["POST"] if 'file' in param_details.values() or 'body' in param_details.values() else ["GET", "POST"]
    #         methods = ["POST"] if if_just_POST else ["GET", "POST"]

    #         # Add the dynamic endpoint to the router
    #         self.router.add_api_route(endpoint_path, endpoint_func, methods=methods)

    #     return self

    def add_endpoint_to_router(
        self,
        list_func: List[Callable],
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        """
        Dynamically creates an endpoint from a provided function (sync or async) that may include
        query parameters, JSON request body, and file uploads, and adds it to the specified FastAPI router.

        Parameters:
        - list_func: List of Callable functions to be converted into API endpoints.
        - prefix: Optional string to be prepended to all endpoint paths.
        - tags: Optional list of tags for categorizing the endpoints in the documentation.
        - description: Optional description for the endpoint, providing more details in the documentation.
        """
        for func in list_func:
            # Prepend the prefix to the endpoint path, if provided
            endpoint_path = (
                f"/{prefix}/{func.__name__}" if prefix else f"/{func.__name__}"
            )  # Ensures no double slashes if prefix is empty

            param_details = {}
            if_just_POST = False

            # Inspect function parameters to determine how to handle them (query, body, file)
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if (
                    param.annotation == UploadFile
                    or param.annotation == List[UploadFile]
                ):
                    param_details[name] = None, "file"
                    if_just_POST = True
                elif param.annotation in [
                    int,
                    float,
                    bool,
                    str,
                ]:  # Simple types for query parameters
                    param_details[name] = None, "query"
                elif self.is_pydantic_model(param.annotation):
                    param_details[name] = (param.annotation, "pydantic")
                    if_just_POST = True
                else:
                    param_details[name] = None, "body"
                    if_just_POST = True

            # Create a dynamic endpoint function
            endpoint_func = self.create_endpoint_function(func, param_details)

            # Determine methods based on parameter types
            methods = ["POST"] if if_just_POST else ["GET", "POST"]

            # Add the dynamic endpoint to the router with optional tags and description
            self.router.add_api_route(
                endpoint_path,
                endpoint_func,
                methods=methods,
                tags=tags,
                summary=description,  # 'summary' is used for short descriptions in FastAPI
            )

        return self

    def get_router(self):
        """Returns the APIRouter containing all registered endpoints."""

        return self.router

    def update_fastapi_app(self, app):
        """Includes the APIBuilder's router in the FastAPI application."""

        app.include_router(self.router)
        return self
