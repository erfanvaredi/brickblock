
# Example Pipeline with brickblock [bb-core]

## Overview

This project demonstrates how to build a flexible data processing pipeline using the `bb-core` library. The pipeline is designed to process data through a series of functions or modules, supporting both synchronous and asynchronous execution, with real-time updates via server-sent events (SSE).

## Installation

1. **Install the repository:**

   ```bash
   pip install bb-core
   ```

2. **Set up a virtual environment (optional but recommended):**

   ```bash
   python -m venv venv
   ```

   Activate the virtual environment:

   - **Windows**: 
     ```bash
     .env\Scriptsctivate
     ```
   - **macOS/Linux**: 
     ```bash
     source venv/bin/activate
     ```


## Project Structure

- **Pipeline Class**: Manages the flow of data through a series of functions.
- **BaseModule Class**: Abstract base class that all modules should inherit from. Modules must implement the following methods:
  - `run()`: The main processing function.
  - `onProgressStartMessage()`: Sends a progress start message.
  - `onProgressEndMessage()`: Sends a progress end message.
- **SSE Generator**: Asynchronous generator that sends real-time updates to clients.

## Example Usage

```python
from your_module import Pipeline, BModule, InputModel2

# Initialize the pipeline
pipeline = Pipeline.init(name="example_pipeline", sse=True)

# Add a module to the pipeline
bmodule = BModule()
pipeline.modules([bmodule])

# Input data for the pipeline
input_data = {"c": 5.0}

# Asynchronously run the pipeline and get SSE events
async def test_sse():
    async for event in pipeline.sse_generator(InputModel2(**input_data)):
        print(event)

# Run the asynchronous SSE generator
asyncio.run(test_sse())
```


This project is licensed under the MIT License.
