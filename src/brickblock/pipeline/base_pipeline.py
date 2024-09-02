from typing import Callable, List, Type, get_type_hints, Union, Any, Coroutine
from pydantic import BaseModel
import types
import inspect
import asyncio
import uuid, pickle

from ..utils.model_servializer import ModelSerializer

from ..function import Function

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
    def init(name:str, id:str=None):
        """Initializes a new Pipeline instance with a specified name."""
        
        __pipeline = Pipeline()
        __pipeline.name = name
        
        __pipeline.id = id if id else str(uuid.uuid4())
        
        __pipeline.input_model: Type[BaseModel] = None
        __pipeline.output_model: Type[BaseModel] = None
        __pipeline.list_functions: List[Type[Function]] = []
        
        return __pipeline

    def input(self, input_model: Type[BaseModel]):
        """Sets the input model type for the pipeline."""

        self.input_model = input_model
        return self

    def output(self, output_model: Type[BaseModel]):
        """Sets the output model type for the pipeline."""

        self.output_model = output_model
        return self

    def functions(self, functions: List[Callable | Function | Coroutine]):
        """Registers a list of functions to the pipeline."""
        
        for f in functions:
            self.list_functions.append(f if isinstance(f, Function) else Function.as_Function(f))

        # self.list_functions = functions
        if not self.input_model and self.list_functions:
            # first_func = self.list_functions[0]
            # first_func_sig = inspect.signature(first_func)
            # first_param_type = list(first_func_sig.parameters.values())[0].annotation
            self.input_model = self.list_functions[0].input_model

        if not self.output_model and self.list_functions:
            # Attempt to infer the output type from the last function
            # last_func = self.list_functions[-1]
            # last_func_sig = inspect.signature(last_func)
            # self.output_model = last_func_sig.return_annotation
            self.output_model = self.list_functions[-1].output_model
            
        return self

    # def functions(self, functions: List[Callable]):
    #     """Registers a list of functions to the pipeline."""

    #     self.list_functions = functions
    #     if not self.input_model and self.list_functions:
    #         # first_func = self.list_functions[0]
    #         # first_func_type_hints = get_type_hints(first_func)
    #         # self.input_model = first_func_type_hints.get('return', BaseModel)
    #         first_func = self.list_functions[0]
    #         first_func_sig = inspect.signature(first_func)
    #         first_param_type = list(first_func_sig.parameters.values())[0].annotation
    #         self.input_model = first_param_type

    #     if not self.output_model and self.list_functions:
    #         # last_func = self.list_functions[-1]
    #         # last_func_type_hints = get_type_hints(last_func)
    #         # self.output_model = last_func_type_hints.get('return', BaseModel)
            
    #         # Attempt to infer the output type from the last function
    #         last_func = self.list_functions[-1]
    #         last_func_sig = inspect.signature(last_func)
    #         self.output_model = last_func_sig.return_annotation
    #     return self
    
    def build(self, input_data: dict) -> dict:
        """
        Tests the pipeline by running the given input through the pipeline and 
        checking if the output matches the expected output model schema.

        Args:
            input_data (dict): The input data for the pipeline in dictionary form.

        Returns:
            dict: A dictionary with 'status', 'result', and 'message' keys indicating the success or failure 
                  of the pipeline execution, the resulting data, or the error message.
        """
        try:
            # Convert input data to input model instance
            try:
                input_instance = self.input_model(**input_data)
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Input data validation error: {str(e)}"
                }

            # Determine if pipeline is async or sync
            try:
                # if asyncio.iscoroutinefunction(self.to_afunction()):
                #     # Check if there's an existing event loop
                #     try:
                #         loop = asyncio.get_running_loop()
                #         output_instance = loop.run_until_complete(self.to_afunction()(input_instance))
                #     except RuntimeError:
                #         # If no running loop, use asyncio.run()
                #         output_instance = asyncio.run(self.to_afunction()(input_instance))
                # else:
                #     output_instance = self.to_function()(input_instance)
                output_instance =  self.to_function()(input_instance)
            except TypeError as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Type error during pipeline execution: {str(e)}"
                }
            except ValueError as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Value error during pipeline execution: {str(e)}"
                }
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Unexpected error during pipeline execution: {str(e)}"
                }

            # Validate if output instance matches the expected output model
            try:
                if isinstance(output_instance, self.output_model):
                    return {
                        'status': 'success',
                        'message': 'Pipeline built successfully.',
                        'result': output_instance.model_dump()
                    }
                else:
                    return {
                        'status': 'failed',
                        'result': None,
                        'message': 'Output schema mismatch. The output did not match the expected model schema.'
                    }
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Error validating output model: {str(e)}"
                }

        except Exception as e:
            return {
                'status': 'failed',
                'result': None,
                'message': f"An unexpected error occurred: {str(e)}"
            }
    
    async def abuild(self, input_data: dict) -> dict:
        """
        Tests the pipeline by running the given input through the pipeline and 
        checking if the output matches the expected output model schema.

        Args:
            input_data (dict): The input data for the pipeline in dictionary form.

        Returns:
            dict: A dictionary with 'status', 'result', and 'message' keys indicating the success or failure 
                  of the pipeline execution, the resulting data, or the error message.
        """
        try:
            # Convert input data to input model instance
            try:
                input_instance = self.input_model(**input_data)
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Input data validation error: {str(e)}"
                }

            # Determine if pipeline is async or sync
            try:
                # if asyncio.iscoroutinefunction(self.to_afunction()):
                #     # Check if there's an existing event loop
                #     try:
                #         loop = asyncio.get_running_loop()
                #         output_instance = loop.run_until_complete(self.to_afunction()(input_instance))
                #     except RuntimeError:
                #         # If no running loop, use asyncio.run()
                #         output_instance = asyncio.run(self.to_afunction()(input_instance))
                # else:
                #     output_instance = self.to_function()(input_instance)
                output_instance = await self.to_afunction()(input_instance)
            except TypeError as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Type error during pipeline execution: {str(e)}"
                }
            except ValueError as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Value error during pipeline execution: {str(e)}"
                }
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Unexpected error during pipeline execution: {str(e)}"
                }

            # Validate if output instance matches the expected output model
            try:
                if isinstance(output_instance, self.output_model):
                    return {
                        'status': 'success',
                        'message': 'Pipeline built successfully.',
                        'result': output_instance.model_dump()
                    }
                else:
                    return {
                        'status': 'failed',
                        'result': None,
                        'message': 'Output schema mismatch. The output did not match the expected model schema.'
                    }
            except Exception as e:
                return {
                    'status': 'failed',
                    'result': None,
                    'message': f"Error validating output model: {str(e)}"
                }

        except Exception as e:
            return {
                'status': 'failed',
                'result': None,
                'message': f"An unexpected error occurred: {str(e)}"
            }

    def to_function(self) -> Callable:
        """Compiles the pipeline into a synchronous callable function."""

        def _pipeline_function(input_data: self.input_model) -> self.output_model:
            data = input_data
            for func in self.list_functions:
                data = func.to_function()(data)
                
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

    def to_afunction(self) -> Coroutine:
        """Compiles the pipeline into an asynchronous callable function."""

        async def _async_pipeline_function(input_data: self.input_model) -> self.output_model:
            data = input_data
            for func in self.list_functions:
                # if inspect.iscoroutinefunction(func):
                
                print(f' data that is passing to  pipeline.to_afunction: {data}')
                data = await func.to_afunction()(data)
                # else:
                #     # If the function is not async, run it in the event loop's default executor
                #     loop = asyncio.get_event_loop()
                #     data = await loop.run_in_executor(None, func.to_function(), data)
            return self.output_model(**data.model_dump()) if isinstance(data, BaseModel) else data

        
        # Dynamically create an async function with the specified pipeline name
        async_pipeline_function = types.FunctionType(
            _async_pipeline_function.__code__,
            _async_pipeline_function.__globals__,
            name='async_'+ self.name ,
            argdefs=_async_pipeline_function.__defaults__,
            closure=_async_pipeline_function.__closure__,
        )
        async_pipeline_function.__annotations__ = _async_pipeline_function.__annotations__

        return async_pipeline_function

    async def arun(self, input_data: dict) -> dict:
        """
        Runs the asynchronous pipeline with the given input data and returns the result.

        Args:
            input_data (dict): The input data for the pipeline in dictionary form.

        Returns:
            dict: A dictionary with 'status', 'result', and 'message' keys indicating the success or failure 
                  of the pipeline execution, the resulting data, or the error message.
        """
            
        input_instance = self.input_model(**input_data) if isinstance(input_data, dict) else input_data
        print(f' data that is passing to pipeline.arun: {input_instance}')

        output_instance = await self.to_afunction()(input_instance)
        
        return output_instance
        # try:
        #     # Convert input data to input model instance
        #     try:
        #         input_instance = self.input_model(**input_data)
        #     except Exception as e:
        #         return {
        #             'status': 'failed',
        #             'result': None,
        #             'message': f"Input data validation error: {str(e)}"
        #         }

        #     # Run the asynchronous pipeline
        #     try:
        #         output_instance = await self.to_afunction()(input_instance)
        #     except TypeError as e:
        #         return {
        #             'status': 'failed',
        #             'result': None,
        #             'message': f"Type error during pipeline execution: {str(e)}"
        #         }
        #     except ValueError as e:
        #         return {
        #             'status': 'failed',
        #             'result': None,
        #             'message': f"Value error during pipeline execution: {str(e)}"
        #         }
        #     except Exception as e:
        #         return {
        #             'status': 'failed',
        #             'result': None,
        #             'message': f"Unexpected error during pipeline execution: {str(e)}"
        #         }

        #     # Validate if output instance matches the expected output model
        #     try:
        #         if isinstance(output_instance, self.output_model):
        #             return {
        #                 'status': 'success',
        #                 'message': 'Pipeline executed successfully.',
        #                 'result': output_instance.model_dump()
        #             }
        #         else:
        #             return {
        #                 'status': 'failed',
        #                 'result': None,
        #                 'message': 'Output schema mismatch. The output did not match the expected model schema.'
        #             }
        #     except Exception as e:
        #         return {
        #             'status': 'failed',
        #             'result': None,
        #             'message': f"Error validating output model: {str(e)}"
        #         }

        # except Exception as e:
        #     return {
        #         'status': 'failed',
        #         'result': None,
        #         'message': f"An unexpected error occurred: {str(e)}"
        #     }
            
    def get_input_schema(self) -> dict:
        """Returns the schema of the input model."""
        return self.input_model.schema()

    def get_output_schema(self) -> dict:
        """Returns the schema of the output model."""
        return self.output_model.schema()

    # def to_dict(self):
    #     return {
    #         "id": self.id,
    #         "name": self.name,
    #         "functions": [func.to_dict() for func in self.list_functions],
    #     }
    
    # @staticmethod
    # def from_dict(data: dict):
    #     functions = [Function.from_dict(func) for func in data['functions']]
    #     return Pipeline(data['id'], data['name'], functions)
    
        
    
    def save_to_str(self):
        # return dill.dumps(self)
        # return yaml.dump(self, default_flow_style=False)
        
        # self.input_model_schema = self.input_model.model_json_schema()
        # self.output_model_schema = self.output_model.model_json_schema()
        
        # del self.input_model
        # del self.output_model
        
        return pickle.dumps(self)
    
    @staticmethod
    def load_from_str(data: str) -> 'Pipeline':
        __load: Pipeline = pickle.loads(data)
        
        # # Recreate the input model from the schema
        # __load.input_model = ModelSerializer.model_from_schema(__load.input_model_schema, 'WorkflowInputModel')
        
        # # Recreate the output model from the schema
        # __load.output_model = ModelSerializer.model_from_schema(__load.output_model_schema, 'WorkflowOutputModel')
        
        return __load