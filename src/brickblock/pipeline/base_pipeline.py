from typing import (
    Callable,
    List,
    Type,
    get_type_hints,
    Union,
    Any,
    Coroutine,
    AsyncGenerator,AsyncIterator
)
from pydantic import BaseModel
import types
import uuid, pickle
import json

from ..utils.model_serializer import ModelSerializer
import time
from ..function import Function
from ..abstract import BaseModule


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
    def init(name: str, id: str = None, sse: bool = False) -> "Pipeline":
        """Initializes a new Pipeline instance with a specified name."""

        __pipeline = Pipeline()
        __pipeline.name = name

        __pipeline.id = id if id else str(uuid.uuid4())
        __pipeline.sse = sse

        __pipeline.input_model: Type[BaseModel] = None
        __pipeline.output_model: Type[BaseModel] = None
        if sse:
            __pipeline.list_functions: List[BaseModule] = []

        else:
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
            self.list_functions.append(
                f if isinstance(f, Function) else Function.as_Function(f)
            )

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

    # def modules(self, functions: List[BaseModule]):
    #     """Registers a list of functions to the pipeline."""

    #     for f in functions:
    #         if isinstance(f, BaseModule):
    #             raise Exception('The module should be type of BaseModule')

    #         self.list_functions.append(f)

    #     # self.list_functions = functions
    #     if not self.input_model and self.list_functions:
    #         # first_func = self.list_functions[0]
    #         # first_func_sig = inspect.signature(first_func)
    #         # first_param_type = list(first_func_sig.parameters.values())[0].annotation
    #         self.input_model = Function.as_Function(self.list_functions[0]().run)

    #     if not self.output_model and self.list_functions:
    #         # Attempt to infer the output type from the last function
    #         # last_func = self.list_functions[-1]
    #         # last_func_sig = inspect.signature(last_func)
    #         # self.output_model = last_func_sig.return_annotation
    #         self.output_model = Function.as_Function(self.list_functions[-1]().run)

    #     return self

    def modules(self, functions: List[BaseModule]):
        """Registers a list of BaseModules to the pipeline."""

        for f in functions:
            if not issubclass(f, BaseModule):
                raise Exception("The module should be of type BaseModule")

            self.list_functions.append(f)

        # Attempt to infer input and output model types from the BaseModule functions
        if not self.input_model and self.list_functions:
            self.input_model = self.list_functions[0].run.__annotations__["input"]

        if not self.output_model and self.list_functions:
            self.output_model = self.list_functions[-1].run.__annotations__["return"]

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
                    "status": "failed",
                    "result": None,
                    "message": f"Input data validation error: {str(e)}",
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
                output_instance = self.to_function()(input_instance)
            except TypeError as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Type error during pipeline execution: {str(e)}",
                }
            except ValueError as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Value error during pipeline execution: {str(e)}",
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Unexpected error during pipeline execution: {str(e)}",
                }

            # Validate if output instance matches the expected output model
            try:
                if isinstance(output_instance, self.output_model):
                    return {
                        "status": "success",
                        "message": "Pipeline built successfully.",
                        "result": output_instance.model_dump(),
                    }
                else:
                    return {
                        "status": "failed",
                        "result": None,
                        "message": "Output schema mismatch. The output did not match the expected model schema.",
                    }
            except Exception as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Error validating output model: {str(e)}",
                }

        except Exception as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"An unexpected error occurred: {str(e)}",
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
                    "status": "failed",
                    "result": None,
                    "message": f"Input data validation error: {str(e)}",
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
                    "status": "failed",
                    "result": None,
                    "message": f"Type error during pipeline execution: {str(e)}",
                }
            except ValueError as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Value error during pipeline execution: {str(e)}",
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Unexpected error during pipeline execution: {str(e)}",
                }

            # Validate if output instance matches the expected output model
            try:
                if isinstance(output_instance, self.output_model):
                    return {
                        "status": "success",
                        "message": "Pipeline built successfully.",
                        "result": output_instance.model_dump(),
                    }
                else:
                    return {
                        "status": "failed",
                        "result": None,
                        "message": "Output schema mismatch. The output did not match the expected model schema.",
                    }
            except Exception as e:
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Error validating output model: {str(e)}",
                }

        except Exception as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"An unexpected error occurred: {str(e)}",
            }

    def to_function(self) -> Callable:
        """Compiles the pipeline into a synchronous callable function."""

        def _pipeline_function(input_data: self.input_model) -> self.output_model:
            data = input_data
            for func in self.list_functions:
                data = func.to_function()(data)

            # Conditionally handle Pydantic model outputs
            return (
                self.output_model(**data.model_dump())
                if isinstance(data, BaseModel)
                else data
            )

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

    async def sse_generator(self, input_data) -> AsyncGenerator[str, None]:
        """
        Async generator to yield SSE events. It processes the pipeline and sends updates to the client.
        """
        if not self.sse:
            # raise Exception('SSE is not activated')
            yield f"{json.dumps({'message':'SSE is not activated in the pipeline', 'status':'Exception', 'data':None})}"

        data = (
            self.input_model(**input_data)
            if isinstance(input_data, dict)
            else (
                self.input_model.parse_obj(input_data.dict())
                if isinstance(input_data, BaseModel)
                else input_data
            )
        )

        for mod in self.list_functions:

            if issubclass(mod, BaseModule):

                __module = mod()
                
                __function_return_type = __module.run.__annotations__["return"]
                __function_input_type = __module.run.__annotations__["input"]

                start_time = time.perf_counter()

                __on_start_msg = await __module.onProgressStartMessage(data)
                
                
                yield f"{json.dumps({'message':str(__on_start_msg), 'status':'onProgressStartMessage', 'function_type':str(__function_return_type),'data':data.model_dump() if isinstance(data, BaseModel) else str(data)})}"
                
                if issubclass(__function_return_type, AsyncIterator):
                    if isinstance(data, dict):
                        print(f'data: {data}')
                        data = __function_input_type(**data)
                    async for item in await __module.run(data):

                        if 'passed_object' in item:
                            data = item['passed_object']

                        yield f"{json.dumps({'message':item['data'] if 'data' in item else '', 'status':'onFunctionCompleted', 'function_type':str(__function_return_type), 'data':item.model_dump() if isinstance(item, BaseModel) else item if isinstance(item, dict) else str(item)})}"
                
                else:
                    
                    data = await __module.run(__function_input_type(**data)) if isinstance(data, dict) else await __module.run(data)
                    
                    
                # if isinstance(data, dict):
                #     data = __module.run.__annotations__["return"](**data)
                yield f"{json.dumps({'message':'', 'status':'onFunctionCompleted', 'function_type':str(__function_return_type), 'data':data.model_dump() if isinstance(data, BaseModel) else str(data)})}"
                __on_end_msg = await __module.onProgressEndMessage(data)
                yield f"{json.dumps({'message':__on_end_msg, 'status':'onProgressEndMessage', 'function_type':str(__function_return_type), 'data':data.model_dump() if isinstance(data, BaseModel) else str(data)})}"

                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print(
                    f"Function [{mod.__name__}] completed in {elapsed_time:.2f} seconds"
                )
            else:
                yield f"{json.dumps({'message':'Exception: The function type passed to the pipeline should be an instance of BaseModule', 'function_type':str(__function_return_type), 'status':'Exception', 'data':data.model_dump() if isinstance(data, BaseModel) else str(data)})}"

        # Send a final SSE event to indicate the stream is complete
        yield f"{json.dumps({'message':'', 'status':'End', 'function_type':str(__function_return_type), 'data':data.model_dump() if isinstance(data, BaseModel) else str(data)})}"

    async def arun_modules(self, input_data) -> Coroutine:

        data = (
            self.input_model(**input_data)
            if isinstance(input_data, dict)
            else (
                self.input_model.parse_obj(input_data.dict())
                if isinstance(input_data, BaseModel)
                else input_data
            )
        )

        for mod in self.list_functions:

            if issubclass(mod, BaseModule):

                __module = mod()

                start_time = time.perf_counter()

                data = await __module.run(data)
                if isinstance(data, dict):
                    data = __module.run.__annotations__["return"](**data)
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print(
                    f"Function [{mod.__name__}] completed in {elapsed_time:.2f} seconds"
                )
            else:
                raise Exception("The model should be type of BaseModule")

        # Send a final SSE event to indicate the stream is complete
        return data

    def to_afunction(self) -> Coroutine:
        """Compiles the pipeline into an asynchronous callable function."""

        async def _async_pipeline_function(
            input_data: self.input_model,
        ) -> self.output_model:
            data = input_data

            for func in self.list_functions:
                # Record start time
                start_time = time.perf_counter()

                data = await func.to_afunction()(data)

                # Record end time
                end_time = time.perf_counter()

                # Calculate and print elapsed time per iteration
                elapsed_time = end_time - start_time
                print(
                    f"Function [{func.name if func.label == '' else func.label}] completed in {elapsed_time:.2f} seconds"
                )

            return (
                self.output_model(**data.model_dump())
                if isinstance(data, BaseModel)
                else data
            )

        # Dynamically create an async function with the specified pipeline name
        async_pipeline_function = types.FunctionType(
            _async_pipeline_function.__code__,
            _async_pipeline_function.__globals__,
            name="async_" + self.name,
            argdefs=_async_pipeline_function.__defaults__,
            closure=_async_pipeline_function.__closure__,
        )
        async_pipeline_function.__annotations__ = (
            _async_pipeline_function.__annotations__
        )

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

        if self.sse:
            return await self.arun_modules(input_data)

        start_time = time.perf_counter()

        input_instance = (
            self.input_model(**input_data)
            if isinstance(input_data, dict)
            else (
                self.input_model.parse_obj(input_data.dict())
                if isinstance(input_data, BaseModel)
                else input_data
            )
        )
        # print(f' data that is passing to pipeline.arun: {input_instance}')

        output_instance = await self.to_afunction()(input_instance)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Pipeline [{self.name}] completed in {elapsed_time:.2f} seconds")

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
    def load_from_str(data: str) -> "Pipeline":
        __load: Pipeline = pickle.loads(data)

        # # Recreate the input model from the schema
        # __load.input_model = ModelSerializer.model_from_schema(__load.input_model_schema, 'WorkflowInputModel')

        # # Recreate the output model from the schema
        # __load.output_model = ModelSerializer.model_from_schema(__load.output_model_schema, 'WorkflowOutputModel')

        return __load
