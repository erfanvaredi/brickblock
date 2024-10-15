from typing import List, Type, Union, Dict, Any, Coroutine, Callable
from pydantic import BaseModel, create_model
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..pipeline import Pipeline
from ..utils.model_serializer import ModelSerializer

import pickle
import uuid


class Workflow:
    """
    A Workflow class that orchestrates the execution of multiple pipelines in parallel.

    The Workflow class can build and run pipelines asynchronously or synchronously. The input model for the
    workflow is a union of all pipeline input models, and the output is a dictionary with pipeline IDs as keys
    and pipeline results as values.

    Methods:
        __init__(self, pipelines: List[Pipeline]): Initializes the Workflow with a list of Pipeline instances.
        build(self, input_data: dict) -> dict: Synchronously builds and runs all pipelines.
        abuild(self, input_data: dict) -> dict: Asynchronously builds and runs all pipelines.
        run(self, input_data: dict) -> dict: Synchronously runs all pipelines.
        arun(self, input_data: dict) -> dict: Asynchronously runs all pipelines.
        get_input_schema(self) -> dict: Returns the combined input schema for all pipelines in the workflow.
        get_output_schema(self) -> dict: Returns the output schema structure for all pipelines in the workflow.
        to_function(self) -> Callable: Compiles the workflow into a synchronous callable function.
        to_afunction(self) -> Coroutine: Compiles the workflow into an asynchronous callable function.
    """

    def __init__(self, name, id):
        self.name = name
        self.id = id if id else str(uuid.uuid4())
        self.workflow_pipelines: List[Pipeline] = []
        self.input_model: Type[BaseModel] = None
        self.output_model: Type[BaseModel] = None

    @staticmethod
    def init(name: str, pipelines: List[Pipeline] = None, id: str = None):
        """Initializes a new Workflow instance with a specified name."""

        __workflow = Workflow(name=name, id=id)

        if pipelines:
            __workflow = __workflow.pipelines(pipelines)

        return __workflow

    def pipelines(self, pipelines: List[Pipeline]) -> "Workflow":
        """Sets the list of pipelines for the Workflow."""
        self.workflow_pipelines = pipelines
        self.input_model = self._build_input_model()
        self.output_model = self._build_output_model()
        return self

    def _build_input_model(self) -> Type[BaseModel]:
        """
        Constructs a combined input model that includes all fields from all pipeline input models.
        """
        input_fields = {}
        for pipeline in self.workflow_pipelines:
            for field_name, field_type in pipeline.input_model.__annotations__.items():
                # if not isinstance(field_type, dict):

                #     print(f'workflow._build_input_model field_name: {field_name}')
                #     print(f'workflow._build_input_model field_type: {field_type}')
                #     for field_name_inner, field_type_inner in field_type.__annotations__.items():
                #         input_fields[field_name_inner] = (field_type_inner, ...)
                # else:
                input_fields[field_name] = (field_type, ...)

        WorkflowInputModel = create_model("WorkflowInputModel", **input_fields)
        return WorkflowInputModel

    def _build_output_model(self) -> Type[BaseModel]:
        """Constructs an output model that aggregates the outputs of all pipelines."""
        output_fields = {
            pipeline.id: (pipeline.output_model, ...)
            for pipeline in self.workflow_pipelines
        }
        WorkflowOutputModel = create_model("WorkflowOutputModel", **output_fields)
        return WorkflowOutputModel

    def get_input_schema(self) -> dict:
        """Returns the combined input schema for all pipelines in the workflow."""
        # schema = {pipeline.id: pipeline.input_model.schema() for pipeline in self.workflow_pipelines}
        # return schema
        return self.input_model.model_json_schema()

    def get_output_schema(self) -> dict:
        """Returns the output schema structure for all pipelines in the workflow."""
        # schema = {pipeline.id: pipeline.output_model.schema() for pipeline in self.workflow_pipelines}
        # return schema
        return self.output_model.model_json_schema()

    def _process_pipeline(self, pipeline: Pipeline, input_data: dict) -> dict:
        """Helper function to run a pipeline synchronously."""
        return pipeline.build(input_data)

    async def _process_pipeline_async(
        self, pipeline: Pipeline, input_data: dict
    ) -> dict:
        """Helper function to run a pipeline asynchronously."""
        return await pipeline.arun(input_data)

    def build(self, input_data: dict) -> dict:
        """
        Synchronously builds and runs all pipelines in the workflow.

        Args:
            input_data (dict): The input data for the workflow in dictionary form.

        Returns:
            dict: A dictionary with pipeline IDs as keys and pipeline results as values.
        """
        results = {}
        for pipeline in self.workflow_pipelines:
            result = self._process_pipeline(pipeline, input_data)
            results[pipeline.id] = result
        return results

    async def abuild(self, input_data: dict) -> dict:
        """
        Asynchronously builds and runs all pipelines in the workflow.

        Args:
            input_data (dict): The input data for the workflow in dictionary form.

        Returns:
            dict: A dictionary with pipeline IDs as keys and pipeline results as values.
        """
        results = {}
        tasks = []
        for pipeline in self.workflow_pipelines:
            tasks.append(self._process_pipeline_async(pipeline, input_data))

        completed_results = await asyncio.gather(*tasks)
        for i, result in enumerate(completed_results):
            results[self.workflow_pipelines[i].id] = result

        return results

    def run(self, input_data: dict) -> dict:
        """
        Synchronously runs all pipelines in parallel using threading.

        Args:
            input_data (dict): The input data for the workflow in dictionary form.

        Returns:
            dict: A dictionary with pipeline IDs as keys and pipeline results as values.
        """
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._process_pipeline, p, input_data)
                for p in self.workflow_pipelines
            ]
            for i, future in enumerate(futures):
                results[self.workflow_pipelines[i].id] = future.result()

        return results

    async def arun(self, input_data: dict) -> dict:
        """
        Asynchronously runs all pipelines in parallel.

        Args:
            input_data (dict): The input data for the workflow in dictionary form.

        Returns:
            dict: A dictionary with pipeline IDs as keys and pipeline results as values.
        """
        results = {}
        tasks = []

        for pipeline in self.workflow_pipelines:
            tasks.append(self._process_pipeline_async(pipeline, input_data))

        completed_results = await asyncio.gather(*tasks)
        for i, result in enumerate(completed_results):
            results[self.workflow_pipelines[i].id] = result

        return results

    def to_function(self) -> Callable:
        """
        Compiles the workflow into a synchronous callable function.

        Returns:
            Callable: The compiled synchronous function ready to be used.
        """

        def workflow_function(input_data: self.input_model) -> self.output_model:
            return self.build(input_data)

        workflow_function.__name__ = self.name
        workflow_function.__annotations__ = {
            "input_data": self.input_model,
            "return": self.output_model,
        }

        return workflow_function

    def to_afunction(self) -> Coroutine:
        """
        Compiles the workflow into an asynchronous callable function.

        Returns:
            Coroutine: The compiled asynchronous function ready to be used.
        """

        async def async_workflow_function(
            input_data: self.input_model,
        ) -> self.output_model:
            return await self.arun(input_data)

        async_workflow_function.__name__ = "async_" + self.name
        async_workflow_function.__annotations__ = {
            "input_data": self.input_model,
            "return": self.output_model,
        }

        return async_workflow_function

    # def to_dict(self):
    #     return {
    #         "id": self.id,
    #         "name": self.name,
    #         "pipelines": [pipeline.to_dict() for pipeline in self.workflow_pipelines],
    #     }

    # @staticmethod
    # def from_dict(data: dict):
    #     pipelines = [Pipeline.from_dict(pipeline) for pipeline in data['pipelines']]
    #     return Workflow(data['name'], pipelines, data['id'])

    # def __getstate__(self):
    #     """Prepare the object for pickling by converting models to a serializable form."""
    #     state = self.__dict__.copy()
    #     # Convert models to a serializable form (e.g., schemas)
    #     state['input_model_schema'] = self.input_model.schema()
    #     # Remove the dynamically created model from the state
    #     del state['input_model']
    #     return state

    # def __setstate__(self, state):
    #     """Reconstruct the object from its serialized state."""
    #     # Rebuild the dynamic model from its schema
    #     input_model_schema = state.pop('input_model_schema')
    #     fields = {name: (eval(field['type']), ...) for name, field in input_model_schema['properties'].items()}
    #     state['input_model'] = create_model('WorkflowInputModel', **fields)
    #     # Restore the rest of the state
    #     self.__dict__.update(state)

    def save_to_str(self):
        # return dill.dumps(self)
        # return yaml.dump(self, default_flow_style=False)

        self.input_model_schema = self.input_model.model_json_schema()
        self.output_model_schema = self.output_model.model_json_schema()

        del self.input_model
        del self.output_model

        return pickle.dumps(self)

    @staticmethod
    def load_from_str(data: str) -> "Workflow":
        __load: Workflow = pickle.loads(data)

        # Recreate the input model from the schema
        __load.input_model = ModelSerializer.model_from_schema(
            __load.input_model_schema, "WorkflowInputModel"
        )

        # Recreate the output model from the schema
        __load.output_model = ModelSerializer.model_from_schema(
            __load.output_model_schema, "WorkflowOutputModel"
        )

        return __load
