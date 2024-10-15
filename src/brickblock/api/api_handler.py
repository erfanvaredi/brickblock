from fastapi import APIRouter, UploadFile
from fastapi.responses import StreamingResponse
import types
from typing import Callable, List, Type, Any, Optional, Dict, Coroutine
import inspect
from functools import wraps
from pydantic import BaseModel

from pipeline import Pipeline
from workflow import Workflow
from function import Function


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

        add_endpoint_to_router(list_func: List[Callable], prefix: Optional[str] = None, tags: Optional[List[str]] = None, description: Optional[str] = None):
            Takes a list of user-defined functions and dynamically creates endpoints for them, adding these endpoints to the APIBuilder's
            APIRouter instance. This method determines the appropriate HTTP method(s) for each endpoint based on the types of parameters
            the user-defined functions expect.

        add_pipeline_to_router(pipeline, prefix: Optional[str] = None, tags: Optional[List[str]] = None, description: Optional[str] = None):
            Adds a pipeline to the router with endpoints generated based on each function in the pipeline, including input/output schemas.

        add_workflow_to_router(workflow, prefix: Optional[str] = None, tags: Optional[List[str]] = None, description: Optional[str] = None):
            Adds a workflow to the router with endpoints generated based on each pipeline in the workflow, including input/output schemas.

        __create_schema_endpoint(name: str, schema: dict):
            Creates a schema endpoint that returns the provided schema as a JSON response.

        get_router() -> APIRouter:
            Returns the APIRouter instance associated with this APIBuilder, containing all dynamically created API routes.

        update_fastapi_app(app: FastAPI):
            Includes the APIBuilder's APIRouter into the given FastAPI application instance 'app', effectively registering all dynamically
            created API routes with the application.
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
            return issubclass(param_type, BaseModel)
        except TypeError:
            return False

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

            __result = await async_wrapper(*args, **call_params)

            if isinstance(__result, (types.GeneratorType, types.AsyncGeneratorType)):
                return StreamingResponse(__result)
            elif isinstance(__result, BaseModel):
                return __result.model_dump()

            return __result

        return endpoint

    def add_endpoint_to_router(
        self,
        list_func: List[Function],
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

        list_func = [
            (
                Function.as_Function(func)
                if isinstance(func, Callable) or isinstance(func, Coroutine)
                else func
            )
            for func in list_func
        ]

        for func in list_func:
            __func = func.to_afunction()
            sig = inspect.signature(__func)
            endpoint_path = f"/{prefix}/{func.name}" if prefix else f"/{func.name}"
            param_details = {}
            if_just_POST = False

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

            endpoint_func = self.create_endpoint_function(__func, param_details)

            methods = ["POST"] if if_just_POST else ["GET", "POST"]

            self.router.add_api_route(
                endpoint_path,
                endpoint_func,
                methods=methods,
                tags=tags,
                summary=description,
            )

        return self

    def add_pipeline_to_router(
        self,
        pipeline: Pipeline,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Adds a pipeline to the router with endpoints generated based on each function in the pipeline.
        """
        for func in pipeline.list_functions:
            endpoint_name = f"{pipeline.name}_{func.name}"
            description = f"Function `{func.name}` in the pipeline `{pipeline.name}`."
            self.add_endpoint_to_router(
                [func],
                prefix=prefix + "/functions",
                tags=["Internal Functions"],
                description=description,
            )

            if not isinstance(func, Function):
                func = Function.as_Function(func)

            print(func.__dict__)

            self.__create_schema_endpoint(
                f"schema/functions/{func.name}",
                {
                    "input_schema": func.input_model.schema(),
                    "output_schema": func.output_model.schema(),
                    "functions": [func.name],
                    "name": func.name,
                    "id": func.id,
                },
                tags=["Schema [Functions]"],
            )

        self.add_endpoint_to_router([pipeline.to_afunction()], prefix=prefix, tags=tags)

        # Add an endpoint to get the pipeline schema
        self.__create_schema_endpoint(
            f"schema/pipelines/{pipeline.name}",
            {
                "input_schema": pipeline.input_model.schema(),
                "output_schema": pipeline.output_model.schema(),
                "functions": [func.name for func in pipeline.list_functions],
                "name": pipeline.name,
                "id": pipeline.id,
            },
            tags=["Schema [Pipeline]"],
        )

        return self

    def add_workflow_to_router(
        self,
        workflow: Workflow,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Adds a workflow to the router with endpoints generated based on each pipeline in the workflow.
        """
        for pipeline in workflow.workflow_pipelines:
            self.add_pipeline_to_router(
                pipeline,
                prefix=prefix + "/pipelines",
                tags=["Workflow Internal Pipelines"],
            )

        self.add_endpoint_to_router([workflow.to_afunction()], prefix=prefix, tags=tags)

        # Add an endpoint to get the workflow schema
        self.__create_schema_endpoint(
            f"schema/workflows/{workflow.name}",
            {
                "input_schema": workflow.get_input_schema(),
                "output_schema": workflow.get_output_schema(),
                "pipelines": [
                    pipeline.name for pipeline in workflow.workflow_pipelines
                ],
                "name": workflow.name,
                "id": workflow.id,
            },
            tags=["Schema [Workflow]"],
        )

        return self

    def __create_schema_endpoint(
        self, name: str, schema: dict, methods=["GET"], tags=["Schema"]
    ):
        """
        Creates a schema endpoint that returns the provided schema as a JSON response.
        """

        async def schema_endpoint():
            return schema

        self.router.add_api_route(
            f"/{name}", schema_endpoint, methods=methods, tags=tags
        )

    def get_router(self):
        """Returns the APIRouter containing all registered endpoints."""
        return self.router

    def update_fastapi_app(self, app):
        """Includes the APIBuilder's router in the FastAPI application."""
        app.include_router(self.router)
        return self
