from typing import Callable, List, Type, get_type_hints, Union, Any
from pydantic import BaseModel
import types
import inspect
import asyncio

class Pipeline:
    """
    A flexible pipeline system designed to chain together a sequence of synchronous and asynchronous functions
    for data processing. The Pipeline class supports Pydantic models for input and output type validation, 
    facilitating the construction of robust data processing workflows.

    Methods:
        init(name: str): Initializes a new Pipeline instance with a specified name.
        input(input_model: Type[BaseModel]): Sets the input model type for the pipeline.
        output(output_model: Type[BaseModel]): Sets the output model type for the pipeline.
        functions(functions: List[Callable]): Registers a list of functions to the pipeline.
        to_function() -> Callable: Compiles the pipeline into a synchronous callable function.
        to_afunction() -> Callable: Compiles the pipeline into an asynchronous callable function.

    The pipeline infers the input and output types based on the annotations of the first and last functions
    in the pipeline if they are not explicitly set. This feature allows for greater flexibility and ease of use.

    Example usage:
        # Define functions and Pydantic models for your pipeline...
        pipeline = Pipeline.init("example_pipeline")
                    .input(InputModel)
                    .output(OutputModel)
                    .functions([func1, func2, async_func3])
                    .to_function()  # For a synchronous pipeline
        # - OR -
                    .to_afunction()  # For an asynchronous pipeline

    Note:
        - The to_function method returns a synchronous version of the compiled pipeline,
          suitable for standard function calls.
        - The to_afunction method returns an asynchronous version of the compiled pipeline,
          suitable for use in asynchronous contexts with the 'await' keyword.
    """
    
    def __init__(self):
        pass

    @staticmethod
    def init(name:str):
        """Initializes a new Pipeline instance with a specified name."""
        
        __pipeline = Pipeline()
        __pipeline.name = name
        __pipeline.input_model: Type[BaseModel] = None
        __pipeline.output_model: Type[BaseModel] = None
        __pipeline.list_functions: List[Callable] = []
        return __pipeline

    def input(self, input_model: Type[BaseModel]):
        """Sets the input model type for the pipeline."""

        self.input_model = input_model
        return self

    def output(self, output_model: Type[BaseModel]):
        """Sets the output model type for the pipeline."""

        self.output_model = output_model
        return self

    def functions(self, functions: List[Callable]):
        """Registers a list of functions to the pipeline."""

        self.list_functions = functions
        if not self.input_model and self.list_functions:
            # first_func = self.list_functions[0]
            # first_func_type_hints = get_type_hints(first_func)
            # self.input_model = first_func_type_hints.get('return', BaseModel)
            first_func = self.list_functions[0]
            first_func_sig = inspect.signature(first_func)
            first_param_type = list(first_func_sig.parameters.values())[0].annotation
            self.input_model = first_param_type

        if not self.output_model and self.list_functions:
            # last_func = self.list_functions[-1]
            # last_func_type_hints = get_type_hints(last_func)
            # self.output_model = last_func_type_hints.get('return', BaseModel)
            
            # Attempt to infer the output type from the last function
            last_func = self.list_functions[-1]
            last_func_sig = inspect.signature(last_func)
            self.output_model = last_func_sig.return_annotation
        return self

    def to_function(self) -> Callable:
        """Compiles the pipeline into a synchronous callable function."""

        def _pipeline_function(input_data: self.input_model) -> self.output_model:
            data = input_data
            for func in self.list_functions:
                data = func(data)
                
            # Conditionally handle Pydantic model outputs
            return self.output_model(**data.model_dump()) if isinstance(data, BaseModel) else data

        # Dynamically create a function with the specified pipeline name
        pipeline_function = types.FunctionType(
            _pipeline_function.__code__,
            _pipeline_function.__globals__,
            name=self.name,
            argdefs=_pipeline_function.__defaults__,
            closure=_pipeline_function.__closure__,
        )
        pipeline_function.__annotations__ = _pipeline_function.__annotations__

        return pipeline_function

    def to_afunction(self) -> Callable:
        """Compiles the pipeline into an asynchronous callable function."""

        async def _async_pipeline_function(input_data: self.input_model) -> self.output_model:
            data = input_data
            for func in self.list_functions:
                if inspect.iscoroutinefunction(func):
                    data = await func(data)
                else:
                    # If the function is not async, run it in the event loop's default executor
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, func, data)
            return self.output_model(**data.model_dump()) if isinstance(data, BaseModel) else data

        # Dynamically create an async function with the specified pipeline name
        async_pipeline_function = types.FunctionType(
            _async_pipeline_function.__code__,
            _async_pipeline_function.__globals__,
            name=self.name + '_async',
            argdefs=_async_pipeline_function.__defaults__,
            closure=_async_pipeline_function.__closure__,
        )
        async_pipeline_function.__annotations__ = _async_pipeline_function.__annotations__

        return async_pipeline_function
