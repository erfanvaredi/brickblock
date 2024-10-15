from typing import Callable, Type, Any, Coroutine, get_type_hints, Dict
from pydantic import BaseModel, create_model, ValidationError
import uuid, inspect
import pickle

from ..utils.model_serializer import ModelSerializer


class Function:
    """
    A class that constructs a callable function from string representations of Pydantic models
    and function code. The function is designed to be consumed by the Pipeline and can be run
    synchronously or asynchronously.

    Methods:
        to_function(self) -> Callable: Builds and returns a callable synchronous function.
        to_afunction(self) -> Callable: Builds and returns a callable asynchronous function.
        run(self, input_data: dict) -> dict: Runs the function synchronously with the given input data.
        arun(self, input_data: dict) -> dict: Runs the function asynchronously with the given input data.
        build(self, input_data: dict) -> dict: Tests the synchronous function with the given input data.
        abuild(self, input_data: dict) -> dict: Tests the asynchronous function with the given input data.
        get_input_schema(self) -> dict: Returns the schema of the input model.
        get_output_schema(self) -> dict: Returns the schema of the output model.
        as_Function(func: Callable) -> 'Function': Converts a given callable or coroutine into a Function instance.
    """

    def __init__(
        self,
        input_model: Type[BaseModel],
        output_model: Type[BaseModel],
        func: Callable,
        label: str = "",
    ):
        """
        Initializes the Function with input and output Pydantic models and function code.

        Args:
            input_model (Type[BaseModel]): The input Pydantic model.
            output_model (Type[BaseModel]): The output Pydantic model.
            func (Callable): The actual function to wrap.
        """
        self.input_model = input_model
        self.output_model = output_model
        self.function = func
        self.name = func.__name__
        self.label = label
        self.id = str(uuid.uuid4())

    @staticmethod
    def str_to_Function(
        input_model_str: str, output_model_str: str, function_code_str: str
    ):
        """Initializes a new Function instance with input and output models and function code."""

        __input_model = Function.build_model(input_model_str)
        __output_model = Function.build_model(output_model_str)

        # __function_code_str = f'{input_model_str}\n\n{output_model_str}\n\n{function_code_str}'
        __function = Function.build_function(
            function_code_str,
            local_vars={
                __input_model.__name__: __input_model,
                __output_model.__name__: __output_model,
            },
        )
        # print(f'Function.str_to_Function __function: {__function}')

        __instance = Function(__input_model, __output_model, __function)

        return __instance

    @staticmethod
    def build_model(model_str: str) -> Type[BaseModel]:
        """Builds and returns a Pydantic model from a string representation."""
        local_vars = {}
        exec(model_str, globals(), local_vars)
        model_name = list(local_vars.keys())[0]
        return local_vars[model_name]

    @staticmethod
    def build_function(function_code_str: str, local_vars: dict = {}) -> Callable:
        """Builds and returns a callable function from a string representation of function code."""
        exec(function_code_str, globals(), local_vars)
        function_name = list(local_vars.keys())[-1]
        return local_vars[function_name]

    @staticmethod
    def as_Function(func: Callable) -> "Function":
        """
        Converts a given callable or coroutine into a Function instance.

        Args:
            func (Callable): The function or coroutine to be wrapped.

        Returns:
            Function: A new Function instance wrapping the provided function.
        """
        type_hints = get_type_hints(func)
        input_model = Function._create_input_model(func, type_hints)
        output_model = Function._create_output_model(func, type_hints)
        return Function(input_model, output_model, func)

    @staticmethod
    def _create_input_model(
        func: Callable, type_hints: Dict[str, Any]
    ) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model for the input based on the function's type hints.

        Args:
            func (Callable): The function whose input types are used to create the model.
            type_hints (Dict[str, Any]): Type hints extracted from the function.

        Returns:
            Type[BaseModel]: A Pydantic model representing the input.
        """
        # Generate a model name based on the function's name
        model_name = f"{func.__name__.capitalize()}InputModel"

        input_fields = {}
        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            if isinstance(param.annotation, type) and issubclass(
                param.annotation, BaseModel
            ):
                # Directly use the Pydantic model if the parameter is a Pydantic model
                input_model = param.annotation
                return input_model  # If a single Pydantic model is recognized, return it directly
            elif param.annotation != param.empty:
                input_fields[name] = (param.annotation, ...)
            else:
                input_fields[name] = (Any, ...)

        # print(f'function._create_input_model input_fields: {input_fields}')

        # Create and return the Pydantic model if no direct model was detected
        return create_model(model_name, **input_fields)

    @staticmethod
    def _create_output_model(
        func: Callable, type_hints: Dict[str, Any]
    ) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model for the output based on the function's return type hint.

        Args:
            func (Callable): The function whose return type is used to create the model.
            type_hints (Dict[str, Any]): Type hints extracted from the function.

        Returns:
            Type[BaseModel]: A Pydantic model representing the output.
        """
        return_type = type_hints.get("return")
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            # Directly use the Pydantic model if the return type is a Pydantic model
            return return_type

        model_name = f"{func.__name__.capitalize()}OutputModel"
        if return_type and hasattr(return_type, "__annotations__"):
            output_fields = {
                k: (v, ...) for k, v in return_type.__annotations__.items()
            }

            # print(f'function._create_output_model output_fields: {output_fields}')

            return create_model(model_name, **output_fields)
        else:
            # Handle simple return types as a single field output model

            # print(f'function._create_output_model output_fields: {output_fields}')
            return create_model(model_name, result=(return_type, ...))

    # @staticmethod
    # def _create_input_model(model_name: str, func: Callable, type_hints: Dict[str, Any]) -> Type[BaseModel]:
    #     """
    #     Dynamically creates a Pydantic model for the input based on the function's type hints.

    #     Args:
    #         model_name (str): The name of the model.
    #         func (Callable): The function whose input types are used to create the model.
    #         type_hints (Dict[str, Any]): Type hints extracted from the function.

    #     Returns:
    #         Type[BaseModel]: A Pydantic model representing the input.
    #     """
    #     input_fields = {}
    #     sig = inspect.signature(func)
    #     for name, param in sig.parameters.items():
    #         if param.annotation != param.empty:
    #             input_fields[name] = (param.annotation, ...)
    #         else:
    #             input_fields[name] = (Any, ...)
    #     return create_model(model_name, **input_fields)

    # @staticmethod
    # def _create_output_model(model_name: str, return_type: Any) -> Type[BaseModel]:
    #     """
    #     Dynamically creates a Pydantic model for the output based on the function's return type.

    #     Args:
    #         model_name (str): The name of the model.
    #         return_type (Any): The return type hint of the function.

    #     Returns:
    #         Type[BaseModel]: A Pydantic model representing the output.
    #     """
    #     if isinstance(return_type, type) and issubclass(return_type, BaseModel):
    #         return return_type
    #     elif hasattr(return_type, '__annotations__'):
    #         output_fields = {k: (v, ...) for k, v in return_type.__annotations__.items()}
    #         return create_model(model_name, **output_fields)
    #     else:
    #         # Handle simple return types as a single field output model
    #         return create_model(model_name, result=(return_type, ...))

    def to_function(self) -> Callable:
        """
        Compiles the function into a synchronous callable function.

        Returns:
            Callable: The compiled synchronous function ready to be used.
        """
        input_model = self.input_model
        output_model = self.output_model
        function = self.function

        def wrapper(input_data: input_model) -> output_model:
            result = function(input_data)
            return output_model(**result) if isinstance(result, dict) else result

        return wrapper

    def to_afunction(self) -> Coroutine:
        """
        Compiles the function into an asynchronous callable function.

        Returns:
            Coroutine: The compiled asynchronous function ready to be used.
        """

        async def async_wrapper(input_data: self.input_model) -> self.output_model:

            # print(f'func function.to_afunction input_data: {input_data}')
            # print(f'func function.to_afunction input_model: {type(self.input_model)}')

            __input_data = (
                self.input_model(**input_data)
                if isinstance(input_data, dict)
                else (
                    self.input_model.parse_obj(input_data.dict())
                    if isinstance(input_data, BaseModel)
                    else self.input_model(**input_data.__dict__)
                )
            )
            # print(f'parsed input_data function.to_afunction __input_data: {__input_data}')
            # print(f'parsed input_data function.to_afunction type(__input_data): {type(__input_data)}')
            # print(f'parsed input_data function > self.function : {self.function}')
            if inspect.iscoroutinefunction(self.function):
                result = await self.function(__input_data)
            else:
                result = self.function(__input_data)
            return self.output_model(**result) if isinstance(result, dict) else result

        return async_wrapper

    def run(self, input_data: dict) -> dict:
        """
        Runs the function synchronously with the given input data.

        Args:
            input_data (dict): The input data in dictionary form.

        Returns:
            dict: The output data in dictionary form.
        """
        try:
            input_instance = self.input_model(**input_data)
            output_instance = self.to_function()(input_instance)
            return {"status": "success", "result": output_instance.model_dump()}
        except ValidationError as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"Input validation error: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"Unexpected error during function execution: {str(e)}",
            }

    async def arun(self, input_data: dict) -> dict:
        """
        Runs the function asynchronously with the given input data.

        Args:
            input_data (dict): The input data in dictionary form.

        Returns:
            dict: The output data in dictionary form.
        """
        try:
            if isinstance(input_data, BaseModel):
                input_instance = self.input_model.parse_obj(input_data.dict())
            else:
                input_instance = self.input_model.pars(**input_data)
            output_instance = await self.to_afunction()(input_instance)
            return {"status": "success", "result": output_instance.model_dump()}
        except ValidationError as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"Input validation error: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "failed",
                "result": None,
                "message": f"Unexpected error during function execution: {str(e)}",
            }

    def build(self, input_data: dict) -> dict:
        """
        Tests the synchronous function with the given input data.

        Args:
            input_data (dict): The input data in dictionary form.

        Returns:
            dict: The output data in dictionary form or error message.
        """
        return self.run(input_data)

    async def abuild(self, input_data: dict) -> dict:
        """
        Tests the asynchronous function with the given input data.

        Args:
            input_data (dict): The input data in dictionary form.

        Returns:
            dict: The output data in dictionary form or error message.
        """
        return await self.arun(input_data)

    def get_input_schema(self) -> dict:
        """Returns the schema of the input model."""
        return self.input_model.model_json_schema()

    def get_output_schema(self) -> dict:
        """Returns the schema of the output model."""
        return self.output_model.schema()

    # def to_dict(self):
    #     return {
    #         "input_model": self.input_model.schema(),
    #         "output_model": self.output_model.schema(),
    #         "function_code": inspect.getsource(self.function),
    #         "name":self.function.__name__,
    #         "id": self.id,
    #     }

    # @staticmethod
    # def from_dict(data: dict):
    #     __input_model = {}
    #     for name, prop in data['input_model']['properties'].items():
    #         prop_type = prop.get('type')
    #         python_type = type_mapping.get(prop_type, Any)  # Default to Any if type is unknown
    #         __input_model[name] = (python_type, ...)  # Required field
    #     input_model = create_model('InputModel', **data['input_model'])
    #     output_model = create_model('OutputModel', **data['output_model'])
    #     local_vars = {}
    #     exec(data['function_code'], globals(), local_vars)
    #     function_name = list(local_vars.keys())[0]
    #     func = local_vars[function_name]
    #     return Function(input_model, output_model, func)

    def save_to_str(self):
        # return dill.dumps(self)
        # return yaml.dump(self, default_flow_style=False)

        self.input_model_schema = self.input_model.model_json_schema()
        self.output_model_schema = self.output_model.model_json_schema()

        del self.input_model
        del self.output_model

        return pickle.dumps(self)

    @staticmethod
    def load_from_str(data: str) -> "Function":
        __load: Function = pickle.loads(data)

        # Recreate the input model from the schema
        __load.input_model = ModelSerializer.model_from_schema(
            __load.input_model_schema, "InputModel"
        )

        # Recreate the output model from the schema
        __load.output_model = ModelSerializer.model_from_schema(
            __load.output_model_schema, "OutputModel"
        )

        return __load
