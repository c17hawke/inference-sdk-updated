# Creating Workflow blocks

Workflows blocks development requires an understanding of the
Workflow Ecosystem. Before diving deeper into the details, let's summarize the 
required knowledge:

Understanding of [Workflow execution](/workflows/workflow_execution/), in particular:
    
* what is the relation of Workflow blocks and steps in Workflow definition

* how Workflow blocks and their manifests are used by [Workflows Compiler](/workflows/workflows_compiler/)

* what is the `dimensionality level` of batch-oriented data passing through Workflow

* how [Execution Engine](/workflows/workflows_execution_engine/) interacts with step, regarding 
its inputs and outputs

* what is the nature and role of [Workflow `kinds`](/workflows/kinds/)

* understanding how [`pydantic`](https://docs.pydantic.dev/latest/) works

## Environment setup

As you will soon see, creating a Workflow block is simply a matter of defining a Python class that implements 
a specific interface. This design allows you to run the block using the Python interpreter, just like any 
other Python code. However, you may encounter difficulties when assembling all the required inputs, which would 
normally be provided by other blocks during Workflow execution.

While it is possible to run your block during development without executing it via the Execution Engine, 
you will likely need to run end-to-end tests in the final stages. This is the most straightforward way to 
validate the functionality.

To get started, build the inference server from your branch
```bash
inference_repo$ docker build \
  -t roboflow/roboflow-inference-server-cpu:test \ 
  -f docker/dockerfiles/Dockerfile.onnx.cpu .
```

Run docker image mounting your code as volume
```bash
inference_repo$ docker run -p 9001:9001 \
  -v ./inference:/app/inference \
  roboflow/roboflow-inference-server-cpu:test
```

Connect your local server to Roboflow UI

<div align="center"><img src="https://media.roboflow.com/inference/workflows_connect_your_local_server.png" width="80%"/></div>

Create your Workflow definition and run preview

<div align="center"><img src="https://media.roboflow.com/inference/workflow_preview.png"/></div>

  
??? Note "Development without Roboflow UI "

    Alternatively, you may create script with your Workflow definition and make requests to your `inference_sdk`.
    Here you may find example script:

    ```python
    from inference_sdk import InferenceHTTPClient

    YOUR_WORKFLOW_DEFINITION = ...
    
    client = InferenceHTTPClient(
        api_url=object_detection_service_url,
        api_key="XXX",  # only required if Workflow uses Roboflow Platform
    )
    result = client.run_workflow(
        specification=YOUR_WORKFLOW_DEFINITION,
        images={
            "image": your_image_np,   # this is example input, adjust it
        },
        parameters={
            "my_parameter": 37,   # this is example input, adjust it
        },
    )
    ```


## Prototypes

To create a Workflow block you need some amount of imports from the core of Workflows library.
Here is the list of imports that you may find useful while creating a block:

```python
from inference.core.workflows.execution_engine.entities.base import (
    Batch,  # batches of data will come in Batch[X] containers
    OutputDefinition,  # class used to declare outputs in your manifest
    WorkflowImageData,  # internal representation of image
    # - use whenever your input kind is image
)

from inference.core.workflows.prototypes.block import (
    BlockResult,  # type alias for result of `run(...)` method
    WorkflowBlock,  # base class for your block
    WorkflowBlockManifest,  # base class for block manifest
)

from inference.core.workflows.execution_engine.entities.types import *  
# module with `kinds` from the core library
```

The most important are:

* `WorkflowBlock` - base class for your block

* `WorkflowBlockManifest` - base class for block manifest

## Block manifest

A manifest is a crucial component of a Workflow block that defines a prototype 
for step declaration that can be placed in a Workflow definition to use the block. 
In particular, it: 

* **Uses `pydantic` to power syntax parsing of Workflows definitions:** 
It inherits from  [`pydantic BaseModel`](https://docs.pydantic.dev/latest/api/base_model/) features to parse and 
validate Workflow definitions. This schema can also be automatically exported to a format compatible with the 
Workflows UI, thanks to `pydantic's` integration with the OpenAPI standard.

* **Defines Data Bindings:** It specifies which fields in the manifest are selectors for data flowing through 
the workflow during execution and indicates their kinds.

* **Describes Block Outputs:** It outlines the outputs that the block will produce.

* **Specifies Dimensionality:** It details the properties related to input and output dimensionality.

* **Indicates Batch Inputs and Empty Values:** It informs the Execution Engine whether the step accepts batch 
inputs and empty values.

* **Ensures Compatibility:** It dictates the compatibility with different Execution Engine versions to maintain 
stability. For more details, see [versioning](/workflows/versioning/).

### Scaffolding for manifest

To understand how manifests work, let's define one step-by-step. The example block that we build here will be 
calculating images similarity. We start from imports and class scaffolding:

```python
from typing import Literal
from inference.core.workflows.prototypes.block import (
    WorkflowBlockManifest,
)

class ImagesSimilarityManifest(WorkflowBlockManifest):
    type: Literal["my_plugin/images_similarity@v1"] 
    name: str
```

This is the minimal representation of a manifest. It defines two special fields that are important for 
Compiler and Execution engine:

* `type` - required to parse syntax of Workflows definitions based on dynamic pool of blocks - this is the 
[`pydantic` type discriminator](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions) that lets the Compiler understand which block manifest is to be verified when 
parsing specific steps in a Workflow definition

* `name` - this property will be used to give the step a unique name and let other steps selects it via selectors

### Adding batch-oriented inputs

We want our step to take two batch-oriented inputs with images to be compared - so effectively
we will be creating SIMD block. 

??? example "Adding batch-oriented inputs"
    
    Let's see how to add definitions of those inputs to manifest: 

    ```{ .py linenums="1" hl_lines="2 6 7 8 9 17 18 19 20 21 22"}
    from typing import Literal, Union
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        # all properties apart from `type` and `name` are treated as either 
        # definitions of batch-oriented data to be processed by block or its 
        # parameters that influence execution of steps created based on block
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
    ```
    
    * in the lines `2-9`, we've added a couple of imports to ensure that we have everything needed
    
    * line `17` defines `image_1` parameter - as manifest is prototype for Workflow Definition, 
    the only way to tell about image to be used by step is to provide selector - we have 
    two specialised types in core library that can be used - `WorkflowImageSelector` and `StepOutputImageSelector`.
    If you look deeper into codebase, you will discover those are type aliases - telling `pydantic`
    to expect string matching `$inputs.{name}` and `$steps.{name}.*` patterns respectively, additionally providing 
    extra schema field metadata that tells Workflows ecosystem components that the `kind` of data behind selector is 
    [image](/workflows/kinds/batch_image/).
  
    * denoting `pydantic` `Field(...)` attribute in the last parts of line `17` is optional, yet appreciated, 
    especially for blocks intended to cooperate with Workflows UI 
  
    * starting in line `20`, you can find definition of `image_2` parameter which is very similar to `image_1`.


Such definition of manifest can handle the following step declaration in Workflow definition:

```json
{
  "type": "my_plugin/images_similarity@v1",
  "name": "my_step",
  "image_1": "$inputs.my_image",
  "image_2": "$steps.image_transformation.image"
}
```

This definition will make the Compiler and Execution Engine:

* select as a step prototype the block which declared manifest with type discriminator being 
`my_plugin/images_similarity@v1`

* supply two parameters for the steps run method:

  * `input_1` of type `WorkflowImageData` which will be filled with image submitted as Workflow execution input
  
  * `imput_2` of type `WorkflowImageData` which will be generated at runtime, by another step called 
  `image_transformation`


### Adding parameter to the manifest

Let's now add the parameter that will influence step execution. The parameter is not assumed to be 
batch-oriented and will affect all batch elements passed to the step.

??? example "Adding parameter to the manifest"

    ```{ .py linenums="1" hl_lines="9 10 11 26 27 28 29 30 31 32"}
    from typing import Literal, Union
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        # all properties apart from `type` and `name` are treated as either 
        # definitions of batch-oriented data to be processed by block or its 
        # parameters that influence execution of steps created based on block
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )
    ```
    
    * line `9` imports `FloatZeroToOne` which is type alias providing validation 
    for float values in range 0.0-1.0 - this is based on native `pydantic` mechanism and
    everyone could create this type annotation locally in module hosting block
    
    * line `10` imports function `WorkflowParameterSelector(...)` capable to dynamically create 
    `pydantic` type annotation for selector to workflow input parameter (matching format `$inputs.param_name`), 
    declaring union of kinds compatible with the field
  
    * line `11` imports [`float_zero_to_one`](/workflows/kinds/float_zero_to_one) `kind` definition which will be used later
  
    * in line `26` we start defining parameter called `similarity_threshold`. Manifest will accept 
    either float values (in range `[0.0-1.0]`) or selector to workflow input of `kind`
    [`float_zero_to_one`](/workflows/kinds/float_zero_to_one). Please point out on how 
    function creating type annotation (`WorkflowParameterSelector(...)`) is used - 
    in particular, expected `kind` of data is passed as list of `kinds` - representing union
    of expected data `kinds`.

Such definition of manifest can handle the following step declaration in Workflow definition:

```{ .json linenums="1" hl_lines="6"}
{
  "type": "my_plugin/images_similarity@v1",
  "name": "my_step",
  "image_1": "$inputs.my_image",
  "image_2": "$steps.image_transformation.image",
  "similarity_threshold": "$inputs.my_similarity_threshold"
}
```

or alternatively:

```{ .json linenums="1" hl_lines="6"}
{
  "type": "my_plugin/images_similarity@v1",
  "name": "my_step",
  "image_1": "$inputs.my_image",
  "image_2": "$steps.image_transformation.image",
  "similarity_threshold": "0.5"
}
```

??? hint "LEARN MORE: Selecting step outputs"

    Our siplified example showcased declaration of properties that accept selectors to
    images produced by other steps via `StepOutputImageSelector`.

    You can use function `StepOutputSelector(...)` creating field annotations dynamically
    to express the that block accepts batch-oriented outputs from other steps of specified
    kinds

    ```{ .py linenums="1" hl_lines="9 10 25"}
    from typing import Literal, Union
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        StepOutputSelector,
        NUMPY_ARRAY_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        # all properties apart from `type` and `name` are treated as either 
        # definitions of batch-oriented data to be processed by block or its 
        # parameters that influence execution of steps created based on block
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        example: StepOutputSelector(kind=[NUMPY_ARRAY_KIND])
    ```

### Declaring block outputs

Our manifest is ready regarding properties that can be declared in Workflow definitions, 
but we still need to provide additional information for the Execution Engine to successfully 
run the block.

??? example "Declaring block outputs"

    Minimal set of information required is outputs description. Additionally, 
    to increase block stability, we advise to provide information about execution engine 
    compatibility.
    
    ```{ .py linenums="1" hl_lines="1 5 13 33-40 42-44"}
    from typing import Literal, Union, List, Optional
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
        OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
        BOOLEAN_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )
        
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="images_match", 
                kind=[BOOLEAN_KIND],
              )
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    ```
    
    * line `1` contains additional imports from `typing`
    
    * line `5` imports class that is used to describe step outputs
  
    * line `13` imports [`boolean`](/workflows/kinds/boolean) `kind` to be used 
    in outputs definitions
  
    * lines `33-40` declare class method to specify outputs from the block - 
    each entry in list declare one return property for each batch element and its `kind`.
    Our block will return boolean flag `images_match` for each pair of images.
  
    * lines `42-44` declare compatibility of the block with Execution Engine -
    see [versioning page](/workflows/versioning/) for more details

As a result of those changes:

* Execution Engine would understand that steps created based on this block 
are supposed to deliver specified outputs and other steps can refer to those outputs
in their inputs

* the blocks loading mechanism will not load the block given that Execution Engine is not in version `v1`

??? hint "LEARN MORE: Dynamic outputs"

    Some blocks may not be able to arbitrailry define their outputs using 
    classmethod - regardless of the content of step manifest that is available after 
    parsing. To support this we introduced the following convention:

    * classmethod `describe_outputs(...)` shall return list with one element of 
    name `*` and kind `*` (aka `WILDCARD_KIND`)

    * additionally, block manifest should implement instance method `get_actual_outputs(...)`
    that provides list of actual outputs that can be generated based on filled manifest data 

    ```{ .py linenums="1" hl_lines="14 35-42 44-49"}
    from typing import Literal, Union, List, Optional
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
        OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
        BOOLEAN_KIND,
        WILDCARD_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )
        outputs: List[str]
        
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="*", 
                kind=[WILDCARD_KIND],
              ),
            ]

        def get_actual_outputs(self) -> List[OutputDefinition]:
            # here you have access to `self`:
            return [
              OutputDefinition(name=e, kind=[BOOLEAN_KIND])
              for e in self.outputs
            ]
    ```


## Definition of block class

At this stage, the manifest of our simple block is ready, we will continue 
with our example. You can check out the [advanced topics](#advanced-topics) section for more details that would just 
be a distractions now.

### Base implementation

Having the manifest ready, we can prepare baseline implementation of the 
block.

??? example "Block scaffolding"

    ```{ .py linenums="1" hl_lines="1 5 6 8-11 56-68"}
    from typing import Literal, Union, List, Optional, Type
    from pydantic import Field
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
        WorkflowBlock,
        BlockResult,
    )
    from inference.core.workflows.execution_engine.entities.base import (
        OutputDefinition,
        WorkflowImageData,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
        BOOLEAN_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )
        
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="images_match", 
                kind=[BOOLEAN_KIND],
              ),
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
        
    class ImagesSimilarityBlock(WorkflowBlock):
      
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return ImagesSimilarityManifest
    
        def run(
            self,
            image_1: WorkflowImageData,
            image_2: WorkflowImageData,
            similarity_threshold: float,
        ) -> BlockResult:
            pass
    ```

    * lines `1`, `5-6` and `8-9` added changes into import surtucture to 
    provide additional symbols required to properly define block class and all
    of its methods signatures

    * line `59` defines class method `get_manifest(...)` to simply return 
    the manifest class we cretaed earlier

    * lines `62-68` define `run(...)` function, which Execution Engine
    will invoke with data to get desired results

### Providing implementation for block logic

Let's now add an example implementation of  the `run(...)` method to our block, such that
it can produce meaningful results.

!!! Note
    
    The Content of this section is supposed to provide examples on how to interact 
    with the Workflow ecosystem as block creator, rather than providing robust 
    implementation of the block.

??? example "Implementation of `run(...)` method"

    ```{ .py linenums="1" hl_lines="3 56-58 70-81"}
    from typing import Literal, Union, List, Optional, Type
    from pydantic import Field
    import cv2
    
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
        WorkflowBlock,
        BlockResult,
    )
    from inference.core.workflows.execution_engine.entities.base import (
        OutputDefinition,
        WorkflowImageData,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
        BOOLEAN_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )
        
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="images_match", 
                kind=[BOOLEAN_KIND],
              ),
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
        
    class ImagesSimilarityBlock(WorkflowBlock):
      
        def __init__(self):
            self._sift = cv2.SIFT_create()
            self._matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
          
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return ImagesSimilarityManifest
    
        def run(
            self,
            image_1: WorkflowImageData,
            image_2: WorkflowImageData,
            similarity_threshold: float,
        ) -> BlockResult:
            image_1_gray = cv2.cvtColor(image_1.numpy_image, cv2.COLOR_BGR2GRAY)
            image_2_gray = cv2.cvtColor(image_2.numpy_image, cv2.COLOR_BGR2GRAY)
            kp_1, des_1 = self._sift.detectAndCompute(image_1_gray, None)
            kp_2, des_2 = self._sift.detectAndCompute(image_2_gray, None)
            matches = self._matcher.knnMatch(des_1, des_2, k=2)
            good_matches = []
            for m, n in matches:
                if m.distance < similarity_threshold * n.distance:
                    good_matches.append(m)
            return {
                "images_match": len(good_matches) > 0,
            }
    ```

    * in line `3` we import OpenCV

    * lines `56-58` defines block constructor, thanks to this - state of block 
    is initialised once and live through consecutive invocation of `run(...)` method - for 
    instance when Execution Engine runs on consecutive frames of video

    * lines `70-81` provide implementation of block functionality - the details are trully not
    important regarding Workflows ecosystem, but there are few details you should focus:
    
        * lines `70` and `71` make use of `WorkflowImageData` abstraction, showcasing how 
        `numpy_image` property can be used to get `np.ndarray` from internal representation of images
        in Workflows. We advise to expole remaining properties of `WorkflowImageData` to discover more.

        * result of workflow block execution, declared in lines `79-81` is in our case just a dictionary 
        **with the keys being the names of outputs declared in manifest**, in line `44`. Be sure to provide all
        declared outputs - otherwise Execution Engine will raise error.
        
You may ask yourself how it is possible that implemented block accepts batch-oriented workflow input, but do not 
operate on batches directly. This is due to the fact that the default block behaviour is to run one-by-one against
all elements of input batches. We will show how to change that in [advanced topics](#advanced-topics) section.

!!! note
    
    One important note: blocks, like all other classes, have constructors that may initialize a state. This state can 
    persist across multiple Workflow runs when using the same instance of the Execution Engine. If the state management 
    needs to be aware of which batch element it processes (e.g., in object tracking scenarios), the block creator 
    should use dedicated batch-oriented inputs. These inputs, provide relevant metadatadata — like the 
    `WorkflowVideoMetadata` input, which is crucial for tracking use cases and can be used along with `WorkflowImage` 
    input in a block implementing tracker.
    
    The ecosystem is evolving, and new input types will be introduced over time. If a specific input type needed for 
    a use case is not available, an alternative is to design the block to process entire input batches. This way, 
    you can rely on the Batch container's indices property, which provides an index for each batch element, allowing 
    you to maintain the correct order of processing.


## Exposing block in `plugin`

Now, your block is ready to be used, but if you declared step using it in your Workflow definition you 
would see an error. This is because no plugin exports the block you just created. Details of blocks bundling 
will be covered in [separate page](/workflows/blocks_bundling/), but the remaining thing to do is to 
add block class into list returned from your plugins' `load_blocks(...)` function:

```python
# __init__.py of your plugin

from my_plugin.images_similarity.v1 import  ImagesSimilarityBlock  
# this is example import! requires adjustment

def load_blocks():
    return [ImagesSimilarityBlock]
```


## Advanced topics

### Blocks processing batches of inputs

Sometimes, performance of your block may benefit if all input data is processed at once as batch. This may
happen for models running on GPU. Such mode of operation is supported for Workflows blocks - here is the example
on how to use it for your block.

??? example "Implementation of blocks accepting batches"

    ```{ .py linenums="1" hl_lines="13 41-43 71-72 75-78 86-87"}
    from typing import Literal, Union, List, Optional, Type
    from pydantic import Field
    import cv2
    
    from inference.core.workflows.prototypes.block import (
        WorkflowBlockManifest,
        WorkflowBlock,
        BlockResult,
    )
    from inference.core.workflows.execution_engine.entities.base import (
        OutputDefinition,
        WorkflowImageData,
        Batch,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputImageSelector,
        WorkflowImageSelector,
        FloatZeroToOne,
        WorkflowParameterSelector,
        FLOAT_ZERO_TO_ONE_KIND,
        BOOLEAN_KIND,
    )
    
    class ImagesSimilarityManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/images_similarity@v1"] 
        name: str
        image_1: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="First image to calculate similarity",
        )
        image_2: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
            description="Second image to calculate similarity",
        )
        similarity_threshold: Union[
            FloatZeroToOne,
            WorkflowParameterSelector(kind=[FLOAT_ZERO_TO_ONE_KIND]),
        ] = Field(
            default=0.4,
            description="Threshold to assume that images are similar",
        )

        @classmethod
        def accepts_batch_input(cls) -> bool:
            return True
        
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="images_match", 
                kind=[BOOLEAN_KIND],
              ),
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
        
    class ImagesSimilarityBlock(WorkflowBlock):
      
        def __init__(self):
            self._sift = cv2.SIFT_create()
            self._matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
          
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return ImagesSimilarityManifest
    
        def run(
            self,
            image_1: Batch[WorkflowImageData],
            image_2: Batch[WorkflowImageData],
            similarity_threshold: float,
        ) -> BlockResult:
            results = []
            for image_1_element, image_2_element in zip(image_1, image_2): 
              image_1_gray = cv2.cvtColor(image_1_element.numpy_image, cv2.COLOR_BGR2GRAY)
              image_2_gray = cv2.cvtColor(image_2_element.numpy_image, cv2.COLOR_BGR2GRAY)
              kp_1, des_1 = self._sift.detectAndCompute(image_1_gray, None)
              kp_2, des_2 = self._sift.detectAndCompute(image_2_gray, None)
              matches = self._matcher.knnMatch(des_1, des_2, k=2)
              good_matches = []
              for m, n in matches:
                  if m.distance < similarity_threshold * n.distance:
                      good_matches.append(m)
              results.append({"images_match": len(good_matches) > 0})
            return results
    ```

    * line `13` imports `Batch` from core of workflows library - this class represent container which is 
    veri similar to list (but read-only) to keep batch elements

    * lines `41-43` define class method that changes default behaviour of the block and make it capable 
    to process batches

    * changes introduced above made the signature of `run(...)` method to change, now `image_1` and `image_2`
    are not instances of `WorkflowImageData`, but rather batches of elements of this type

    * lines `75-78`, `86-87` present changes that needed to be introduced to run processing across all batch 
    elements - showcasing how to iterate over batch elements if needed

    * it is important to note how outputs are constructed in line `86` - each element of batch will be given
    its entry in the list which is returned from `run(...)` method. Order must be aligned with order of batch 
    elements. Each output dictionary must provide all keys declared in block outputs.

### Implementation of flow-control block

Flow-control blocks differs quite substantially from other blocks that just process the data. Here we will show 
how to create a flow control block, but first - a little bit of theory:

* flow-control block is the block that declares compatibility with step selectors in their manifest (selector to step
is defined as `$steps.{step_name}` - similar to step output selector, but without specification of output name)

* flow-control blocks cannot register outputs, they are meant to return `FlowControl` objects

* `FlowControl` object specify next steps (from selectors provided in step manifest) that for given 
batch element (SIMD flow-control) or whole workflow execution (non-SIMD flow-control) should pick up next

??? example "Implementation of flow-control - SIMD block"
    
    Example provides and comments out implementation of random continue block

    ```{ .py linenums="1" hl_lines="10 14 26 28-31 55-56"}
    from typing import List, Literal, Optional, Type, Union
    import random
    
    from pydantic import Field
    from inference.core.workflows.execution_engine.entities.base import (
      OutputDefinition,
      WorkflowImageData,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepSelector,
        WorkflowImageSelector,
        StepOutputImageSelector,
    )
    from inference.core.workflows.execution_engine.v1.entities import FlowControl
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )
    
    
    
    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/random_continue@v1"]
        name: str
        image: Union[WorkflowImageSelector, StepOutputImageSelector] = ImageInputField
        probability: float
        next_steps: List[StepSelector] = Field(
            description="Reference to step which shall be executed if expression evaluates to true",
            examples=[["$steps.on_true"]],
        )
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return []
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class RandomContinueBlockV1(WorkflowBlock):
    
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            image: WorkflowImageData,
            probability: float,
            next_steps: List[str],
        ) -> BlockResult:
            if not next_steps or random.random() > probability:
                return FlowControl()
            return FlowControl(context=next_steps)
    ```

    * line `10` imports type annotation for step selector which will be used to 
    notify Execution Engine that the block controls the flow

    * line `14` imports `FlowControl` class which is the only viable response from
    flow-control block

    * line `26` specifies `image` which is batch-oriented input making the block SIMD - 
    which means that for each element of images batch, block will make random choice on 
    flow-control - if not that input block would operate in non-SIMD mode

    * line `28` defines list of step selectors **which effectively turns the block into flow-control one**

    * lines `55` and `56` show how to construct output - `FlowControl` object accept context being `None`, `string` or 
    `list of strings` - `None` represent flow termination for the batch element, strings are expected to be selectors 
    for next steps, passed in input.

??? example "Implementation of flow-control non-SIMD block"
    
    Example provides and comments out implementation of random continue block

    ```{ .py linenums="1" hl_lines="9 11 24-27 50-51"}
    from typing import List, Literal, Optional, Type, Union
    import random
    
    from pydantic import Field
    from inference.core.workflows.execution_engine.entities.base import (
      OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepSelector,
    )
    from inference.core.workflows.execution_engine.v1.entities import FlowControl
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )
    
    
    
    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/random_continue@v1"]
        name: str
        probability: float
        next_steps: List[StepSelector] = Field(
            description="Reference to step which shall be executed if expression evaluates to true",
            examples=[["$steps.on_true"]],
        )
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return []
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class RandomContinueBlockV1(WorkflowBlock):
    
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            probability: float,
            next_steps: List[str],
        ) -> BlockResult:
            if not next_steps or random.random() > probability:
                return FlowControl()
            return FlowControl(context=next_steps)
    ```

    * line `9` imports type annotation for step selector which will be used to 
    notify Execution Engine that the block controls the flow

    * line `11` imports `FlowControl` class which is the only viable response from
    flow-control block

    * lines `24-27` defines list of step selectors **which effectively turns the block into flow-control one**

    * lines `50` and `51` show how to construct output - `FlowControl` object accept context being `None`, `string` or 
    `list of strings` - `None` represent flow termination for the batch element, strings are expected to be selectors 
    for next steps, passed in input.

### Nested selectors

Some block will require list of selectors or dictionary of selectors to be 
provided in block manifest field. Version `v1` of Execution Engine supports only 
one level of nesting - so list of lists of selectors or dictionary with list of selectors 
will not be recognised properly.

Practical use cases showcasing usage of nested selectors are presented below.

#### Fusion of predictions from variable number of models

Let's assume that you want to build a block to get majority vote on multiple classifiers predictions - then you would 
like your run method to look like that:

```python
# pseud-code here
def run(self, predictions: List[dict]) -> BlockResult:
    predicted_classes = [p["class"] for p in predictions]
    counts = Counter(predicted_classes)
    return {"top_class": counts.most_common(1)[0]}
```

??? example "Nested selectors - models ensemble"

    ```{ .py linenums="1" hl_lines="23-26 50"}
    from typing import List, Literal, Optional, Type
    
    from pydantic import Field
    import supervision as sv
    from inference.core.workflows.execution_engine.entities.base import (
      OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputSelector,
        OBJECT_DETECTION_PREDICTION_KIND,
    )
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )
    
    
    
    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/fusion_of_predictions@v1"]
        name: str
        predictions: List[StepOutputSelector(kind=[OBJECT_DETECTION_PREDICTION_KIND])] = Field(
            description="Selectors to step outputs",
            examples=[["$steps.model_1.predictions", "$steps.model_2.predictions"]],
        )
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(
                name="predictions", 
                kind=[OBJECT_DETECTION_PREDICTION_KIND],
              )
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class FusionBlockV1(WorkflowBlock):
    
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            predictions: List[sv.Detections],
        ) -> BlockResult:
            merged = sv.Detections.merge(predictions)
            return {"predictions": merged}
    ```

    * lines `23-26` depict how to define manifest field capable of accepting 
    list of selectors

    * line `50` shows what to expect as input to block's `run(...)` method - 
    list of objects which are representation of specific kind. If the block accepted 
    batches, the input type of `predictions` field would be `List[Batch[sv.Detections]`

Such block is compatible with the following step declaration:

```{ .json linenums="1" hl_lines="4-7"}
{
  "type": "my_plugin/fusion_of_predictions@v1",
  "name": "my_step",
  "predictions": [
    "$steps.model_1.predictions",
    "$steps.model_2.predictions"  
  ]
}
```

#### Block with data transformations allowing dynamic parameters

Occasionally, blocks may need to accept group of "named" selectors, 
which names and values are to be defined by creator of Workflow definition. 
In such cases, block manifest shall accept dictionary of selectors, where
keys serve as names for those selectors.

??? example "Nested selectors - named selectors"

    ```{ .py linenums="1" hl_lines="23-26 47"}
    from typing import List, Literal, Optional, Type, Any
    
    from pydantic import Field
    import supervision as sv
    from inference.core.workflows.execution_engine.entities.base import (
      OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import (
        StepOutputSelector,
        WorkflowParameterSelector,
    )
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )
    
    
    
    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/named_selectors_example@v1"]
        name: str
        data: Dict[str, StepOutputSelector(), WorkflowParameterSelector()] = Field(
            description="Selectors to step outputs",
            examples=[{"a": $steps.model_1.predictions", "b": "$Inputs.data"}],
        )
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [
              OutputDefinition(name="my_output", kind=[]),
            ]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class BlockWithNamedSelectorsV1(WorkflowBlock):
    
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            data: Dict[str, Any],
        ) -> BlockResult:
            ...
            return {"my_output": ...}
    ```

    * lines `23-26` depict how to define manifest field capable of accepting 
    list of selectors

    * line `47` shows what to expect as input to block's `run(...)` method - 
    dict of objects which are reffered with selectors. If the block accepted 
    batches, the input type of `data` field would be `Dict[str, Union[Batch[Any], Any]]`.
    In non-batch cases, non-batch-oriented data referenced by selector is automatically 
    broadcasted, whereas for blocks accepting batches - `Batch` container wraps only 
    batch-oriented inputs, with other inputs being passed as singular values.

Such block is compatible with the following step declaration:

```{ .json linenums="1" hl_lines="4-7"}
{
  "type": "my_plugin/named_selectors_example@v1",
  "name": "my_step",
  "data": {
    "a": "$steps.model_1.predictions",
    "b": "$inputs.my_parameter"  
  }
}
```

Practical implications will be the following:

* under `data["a"]` inside `run(...)` you will be able to find model's predictions - 
like `sv.Detections` if `model_1` is object-detection model

* under `data["b"]` inside `run(...)`, you will find value of input parameter named `my_parameter`

### Inputs and output dimensionality vs `run(...)` method

The dimensionality of block inputs plays a crucial role in shaping the `run(...)` method’s signature, and that's 
why the system enforces strict bounds on the differences in dimensionality levels between inputs 
(with the maximum allowed difference being `1`). This restriction is critical for ensuring consistency and 
predictability when writing blocks.

If dimensionality differences weren't controlled, it would be difficult to predict the structure of 
the `run(...)` method, making development harder and less reliable. That’s why validation of this property 
is strictly enforced during the Workflow compilation process.

Similarly, the output dimensionality also affects the method signature and the format of the expected output. 
The ecosystem supports the following scenarios:

* all inputs have **the same dimensionality** and outputs **does not change** dimensionality - baseline case

* all inputs have **the same dimensionality** and output **decreases** dimensionality

* all inputs have **the same dimensionality** and output **increases** dimensionality

* inputs have **different dimensionality** and output is allowed to keep the dimensionality of 
**reference input**

Other combinations of input/output dimensionalities are not allowed to ensure consistency and to prevent ambiguity in 
the method signatures.

??? example "Impact of dimensionality on `run(...)` method - batches disabled"

    === "output dimensionality increase"

        In this example, we perform dynamic crop of image based on predictions.

        ```{ .py linenums="1" hl_lines="30-32 65 66-67"}
        from typing import Dict, List, Literal, Optional, Type, Union
        from uuid import uuid4

        from inference.core.workflows.execution_engine.constants import DETECTION_ID_KEY
        from inference.core.workflows.execution_engine.entities.base import (
            OutputDefinition,
            WorkflowImageData,
            ImageParentMetadata,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            IMAGE_KIND,
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_block/dynamic_crop@v1"]
            image: Union[WorkflowImageSelector, StepOutputImageSelector]
            predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND],
            )
        
            @classmethod
            def get_output_dimensionality_offset(cls) -> int:
                return 1
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(name="crops", kind=[IMAGE_KIND]),
                ]
        
            @classmethod
            def get_execution_engine_compatibility(cls) -> Optional[str]:
                return ">=1.0.0,<2.0.0"

        class DynamicCropBlockV1(WorkflowBlock):

            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
            
            def run(
                self,
                image: WorkflowImageData,
                predictions: sv.Detections,
            ) -> BlockResult:
                crops = []
                for (x_min, y_min, x_max, y_max) in predictions.xyxy.round().astype(dtype=int):
                    cropped_image = image.numpy_image[y_min:y_max, x_min:x_max]
                    parent_metadata = ImageParentMetadata(parent_id=f"{uuid4()}")
                    if cropped_image.size:
                        result = WorkflowImageData(
                            parent_metadata=parent_metadata,
                            numpy_image=cropped_image,
                        )
                    else:
                        result = None
                    crops.append({"crops": result})
                return crops
        ```

        * in lines `30-32` manifest class declares output dimensionality 
        offset - value `1` should be understood as adding `1` to dimensionality level
        
        * point out, that in line `65`, block eliminates empty images from further processing but 
        placing `None` instead of dictionatry with outputs. This would utilise the same 
        Execution Engine behaviour that is used for conditional execution - datapoint will
        be eliminated from downstream processing (unless steps requesting empty inputs 
        are present down the line).

        * in lines `66-67` results for single input `image` and `predictions` are collected - 
        it is meant to be list of dictionares containing all registered outputs as keys. Execution
        engine will understand that the step returns batch of elements for each input element and
        create nested sturcures of indices to keep track of during execution of downstream steps.

    === "output dimensionality decrease"
      
        In this example, the block visualises crops predictions and creates tiles
        presenting all crops predictions in single output image.

        ```{ .py linenums="1" hl_lines="31-33 50-51 61-62"}
        from typing import List, Literal, Type, Union

        import supervision as sv
        
        from inference.core.workflows.execution_engine.entities.base import (
            Batch,
            OutputDefinition,
            WorkflowImageData,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            IMAGE_KIND,
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_plugin/tile_detections@v1"]
            crops: Union[WorkflowImageSelector, StepOutputImageSelector]
            crops_predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND]
            )
        
            @classmethod
            def get_output_dimensionality_offset(cls) -> int:
                return -1
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(name="visualisations", kind=[IMAGE_KIND]),
                ]
        
        
        class TileDetectionsBlock(WorkflowBlock):
        
            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
        
            def run(
                self,
                crops: Batch[WorkflowImageData],
                crops_predictions: Batch[sv.Detections],
            ) -> BlockResult:
                annotator = sv.BoundingBoxAnnotator()
                visualisations = []
                for image, prediction in zip(crops, crops_predictions):
                    annotated_image = annotator.annotate(
                        image.numpy_image.copy(),
                        prediction,
                    )
                    visualisations.append(annotated_image)
                tile = sv.create_tiles(visualisations)
                return {"visualisations": tile}
        ```

        * in lines `31-33` manifest class declares output dimensionality 
        offset - value `-1` should be understood as decreasing dimensionality level by `1`

        * in lines `50-51` you can see the impact of output dimensionality decrease
        on the method signature. Both inputs are artificially wrapped in `Batch[]` container.
        This is done by Execution Engine automatically on output dimensionality decrease when 
        all inputs have the same dimensionality to enable access to all elements occupying 
        the last dimensionality level. Obviously, only elements related to the same element 
        from top-level batch will be grouped. For instance, if you had two input images that you 
        cropped - crops from those two different images will be grouped separately.

        * lines `61-62` illustrate how output is constructed - single value is returned and that value 
        will be indexed by Execution Engine in output batch with reduced dimensionality

    === "different input dimensionalities"
        
        In this example, block merges detections which were predicted based on 
        crops of original image - result is to provide single detections with 
        all partial ones being merged.

        ```{ .py linenums="1" hl_lines="32-37 39-41 63-64 70"}
        from copy import deepcopy
        from typing import Dict, List, Literal, Optional, Type, Union
        
        import numpy as np
        import supervision as sv
        
        from inference.core.workflows.execution_engine.entities.base import (
            Batch,
            OutputDefinition,
            WorkflowImageData,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_plugin/stitch@v1"]
            image: Union[WorkflowImageSelector, StepOutputImageSelector]
            image_predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND],
            )
        
            @classmethod
            def get_input_dimensionality_offsets(cls) -> Dict[str, int]:
                return {
                    "image": 0,
                    "image_predictions": 1,
                }
        
            @classmethod
            def get_dimensionality_reference_property(cls) -> Optional[str]:
                return "image"
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(
                        name="predictions",
                        kind=[
                            OBJECT_DETECTION_PREDICTION_KIND,
                        ],
                    ),
                ]
        
        
        class StitchDetectionsNonBatchBlock(WorkflowBlock):
        
            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
        
            def run(
                self,
                image: WorkflowImageData,
                image_predictions: Batch[sv.Detections],
            ) -> BlockResult:
                image_predictions = [deepcopy(p) for p in image_predictions if len(p)]
                for p in image_predictions:
                    coords = p["parent_coordinates"][0]
                    p.xyxy += np.concatenate((coords, coords))
                return {"predictions": sv.Detections.merge(image_predictions)}

        ```

        * in lines `32-37` manifest class declares input dimensionalities offset, indicating
        `image` parameter being top-level and `image_predictions` being nested batch of predictions

        * whenever different input dimensionalities are declared, dimensionality reference property
        must be pointed (see lines `39-41`) - this dimensionality level would be used to calculate 
        output dimensionality - in this particular case, we specify `image`. This choice 
        has an implication in the expected format of result - in the chosen scenario we are supposed
        to return single dictionary with all registered outputs keys. If our choice is `image_predictions`,
        we would return list of dictionaries (of size equal to length of `image_predictions` batch). In other worlds,
        `get_dimensionality_reference_property(...)` which dimensionality level should be associated
        to the output.

        * lines `63-64` present impact of dimensionality offsets specified in lines `32-37`. It is clearly
        visible that `image_predictions` is a nested batch regarding `image`. Obviously, only nested predictions
        relevant for the specific `images` are grouped in batch and provided to the method in runtime.

        * as mentioned earlier, line `70` construct output being single dictionary, as we register output 
        at dimensionality level of `image` (which was also shipped as single element)


??? example "Impact of dimensionality on `run(...)` method - batches enabled"

    === "output dimensionality increase"

        In this example, we perform dynamic crop of image based on predictions.

        ```{ .py linenums="1" hl_lines="31-33 35-37 57-58 72 73-75"}
        from typing import Dict, List, Literal, Optional, Type, Union
        from uuid import uuid4

        from inference.core.workflows.execution_engine.constants import DETECTION_ID_KEY
        from inference.core.workflows.execution_engine.entities.base import (
            OutputDefinition,
            WorkflowImageData,
            ImageParentMetadata,
            Batch,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            IMAGE_KIND,
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_block/dynamic_crop@v1"]
            image: Union[WorkflowImageSelector, StepOutputImageSelector]
            predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND],
            )

            @classmethod
            def accepts_batch_input(cls) -> bool:
                return True
        
            @classmethod
            def get_output_dimensionality_offset(cls) -> int:
                return 1
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(name="crops", kind=[IMAGE_KIND]),
                ]
        
            @classmethod
            def get_execution_engine_compatibility(cls) -> Optional[str]:
                return ">=1.0.0,<2.0.0"

        class DynamicCropBlockV1(WorkflowBlock):

            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
            
            def run(
                self,
                image: Batch[WorkflowImageData],
                predictions: Batch[sv.Detections],
            ) -> BlockResult:
                results = []
                for single_image, detections in zip(image, predictions):
                    crops = []
                    for (x_min, y_min, x_max, y_max) in detections.xyxy.round().astype(dtype=int):
                        cropped_image = single_image.numpy_image[y_min:y_max, x_min:x_max]
                        parent_metadata = ImageParentMetadata(parent_id=f"{uuid4()}")
                        if cropped_image.size:
                            result = WorkflowImageData(
                                parent_metadata=parent_metadata,
                                numpy_image=cropped_image,
                            )
                        else:
                            result = None
                        crops.append({"crops": result})
                    results.append(crops)
                return results
        ```
      
        * in lines `31-33` manifest declares that block accepts batches of inputs

        * in lines `35-37` manifest class declares output dimensionality 
        offset - value `1` should be understood as adding `1` to dimensionality level
        
        * in lines `57-68`, signature of input parameters reflects that the `run(...)` method
        runs against inputs of the same dimensionality and those inputs are provided in batches

        * point out, that in line `72`, block eliminates empty images from further processing but 
        placing `None` instead of dictionatry with outputs. This would utilise the same 
        Execution Engine behaviour that is used for conditional execution - datapoint will
        be eliminated from downstream processing (unless steps requesting empty inputs 
        are present down the line).

        * construction of the output, presented in lines `73-75` indicates two levels of nesting.
        First of all, block operates on batches, so it is expected to return list of outputs, one 
        output for each input batch element. Additionally, this output element for each input batch 
        element turns out to be nested batch - hence for each input iage and prediction, block 
        generates list of outputs - elements of that list are dictionaries providing values 
        for each declared output.

    === "output dimensionality decrease"
      
        In this example, the block visualises crops predictions and creates tiles
        presenting all crops predictions in single output image.

        ```{ .py linenums="1" hl_lines="31-33 35-37 54-55 68-69"}
        from typing import List, Literal, Type, Union

        import supervision as sv
        
        from inference.core.workflows.execution_engine.entities.base import (
            Batch,
            OutputDefinition,
            WorkflowImageData,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            IMAGE_KIND,
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_plugin/tile_detections@v1"]
            images_crops: Union[WorkflowImageSelector, StepOutputImageSelector]
            crops_predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND]
            )

            @classmethod
            def accepts_batch_input(cls) -> bool:
                return True
        
            @classmethod
            def get_output_dimensionality_offset(cls) -> int:
                return -1
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(name="visualisations", kind=[IMAGE_KIND]),
                ]
        
        
        class TileDetectionsBlock(WorkflowBlock):
        
            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
        
            def run(
                self,
                images_crops: Batch[Batch[WorkflowImageData]],
                crops_predictions: Batch[Batch[sv.Detections]],
            ) -> BlockResult:
                annotator = sv.BoundingBoxAnnotator()
                visualisations = []
                for image_crops, crop_predictions in zip(images_crops, crops_predictions):
                    visualisations_batch_element = []
                    for image, prediction in zip(image_crops, crop_predictions):
                        annotated_image = annotator.annotate(
                            image.numpy_image.copy(),
                            prediction,
                        )
                        visualisations_batch_element.append(annotated_image)
                    tile = sv.create_tiles(visualisations_batch_element)
                    visualisations.append({"visualisations": tile})
                return visualisations
        ```
        
        * lines `31-33` manifest that block is expected to take batches as input

        * in lines `35-37` manifest class declares output dimensionality 
        offset - value `-1` should be understood as decreasing dimensionality level by `1`

        * in lines `54-55` you can see the impact of output dimensionality decrease
        and batch processing on the method signature. First "layer" of `Batch[]` is a side effect of the 
        fact that manifest declared that block accepts batches of inputs. The second "layer" comes 
        from output dimensionality decrease. Execution Engine wrapps up the dimension to be reduced into 
        additional `Batch[]` container porvided in inputs, such that programmer is able to collect all nested
        batches elements that belong to specific top-level batch element.

        * lines `68-69` illustrate how output is constructed - for each top-level batch element, block
        aggregates all crops and predictions and creates a single tile. As block accepts batches of inputs,
        this procedure end up with one tile for each top-level batch element - hence list of dictionaries
        is expected to be returned.

    === "different input dimensionalities"
        
        In this example, block merges detections which were predicted based on 
        crops of original image - result is to provide single detections with 
        all partial ones being merged.

        ```{ .py linenums="1" hl_lines="32-34 36-41 43-45 67-68 77-78"}
        from copy import deepcopy
        from typing import Dict, List, Literal, Optional, Type, Union
        
        import numpy as np
        import supervision as sv
        
        from inference.core.workflows.execution_engine.entities.base import (
            Batch,
            OutputDefinition,
            WorkflowImageData,
        )
        from inference.core.workflows.execution_engine.entities.types import (
            OBJECT_DETECTION_PREDICTION_KIND,
            StepOutputImageSelector,
            StepOutputSelector,
            WorkflowImageSelector,
        )
        from inference.core.workflows.prototypes.block import (
            BlockResult,
            WorkflowBlock,
            WorkflowBlockManifest,
        )
        
        
        class BlockManifest(WorkflowBlockManifest):
            type: Literal["my_plugin/stitch@v1"]
            images: Union[WorkflowImageSelector, StepOutputImageSelector]
            images_predictions: StepOutputSelector(
                kind=[OBJECT_DETECTION_PREDICTION_KIND],
            )

            @classmethod
            def accepts_batch_input(cls) -> bool:
                return True
                
            @classmethod
            def get_input_dimensionality_offsets(cls) -> Dict[str, int]:
                return {
                    "image": 0,
                    "image_predictions": 1,
                }
        
            @classmethod
            def get_dimensionality_reference_property(cls) -> Optional[str]:
                return "image"
        
            @classmethod
            def describe_outputs(cls) -> List[OutputDefinition]:
                return [
                    OutputDefinition(
                        name="predictions",
                        kind=[
                            OBJECT_DETECTION_PREDICTION_KIND,
                        ],
                    ),
                ]
        
        
        class StitchDetectionsBatchBlock(WorkflowBlock):
        
            @classmethod
            def get_manifest(cls) -> Type[WorkflowBlockManifest]:
                return BlockManifest
        
            def run(
                self,
                images: Batch[WorkflowImageData],
                images_predictions: Batch[Batch[sv.Detections]],
            ) -> BlockResult:
                result = []
                for image, image_predictions in zip(images, images_predictions):
                    image_predictions = [deepcopy(p) for p in image_predictions if len(p)]
                    for p in image_predictions:
                        coords = p["parent_coordinates"][0]
                        p.xyxy += np.concatenate((coords, coords))
                    merged_prediction = sv.Detections.merge(image_predictions)
                    result.append({"predictions": merged_prediction})
                return result
        ```

        * lines `32-34` manifest that block is expected to take batches as input

        * in lines `36-41` manifest class declares input dimensionalities offset, indicating
        `image` parameter being top-level and `image_predictions` being nested batch of predictions

        * whenever different input dimensionalities are declared, dimensionality reference property
        must be pointed (see lines `43-45`) - this dimensionality level would be used to calculate 
        output dimensionality - in this particular case, we specify `image`. This choice 
        has an implication in the expected format of result - in the chosen scenario we are supposed
        to return single dictionary for each element of `image` batch. If our choice is `image_predictions`,
        we would return list of dictionaries (of size equal to length of nested `image_predictions` batch) for each
        input `image` batch element.

        * lines `67-68` present impact of dimensionality offsets specified in lines `36-41` as well as 
        the declararion of batch processing from lines `32-34`. First "layer" of `Batch[]` container comes 
        from the latter, nested `Batch[Batch[]]` for `images_predictions` comes from the definition of input 
        dimensionality offset. It is clearly visible that `image_predictions` holds batch of predictions relevant
        for specific elements of `image` batch.
        
        * as mentioned earlier, lines `77-78` construct output being single dictionary for each element of `image` 
        batch


### Block accepting empty inputs

As discussed earlier, some batch elements may become "empty" during the execution of a Workflow. 
This can happen due to several factors:

* **Flow-control mechanisms:** Certain branches of execution can mask specific batch elements, preventing them 
from being processed in subsequent steps.

* **In data-processing blocks:** In some cases, a block may not be able to produce a meaningful output for 
a specific data point. For example, a Dynamic Crop block cannot generate a cropped image if the bounding box 
size is zero.

Some blocks are designed to handle these empty inputs, such as block that can replace missing outputs with default 
values. This block can be particularly useful when constructing structured outputs in a Workflow, ensuring 
that even if some elements are empty, the output lacks missing elements making it harder to parse.

??? example "Block accepting empty inputs"

    ```{ .py linenums="1" hl_lines="20-22 41"}
    from typing import Any, List, Literal, Optional, Type

    from inference.core.workflows.execution_engine.entities.base import (
        Batch,
        OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import StepOutputSelector
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )


    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/first_non_empty_or_default@v1"]
        data: List[StepOutputSelector()]
        default: Any
    
        @classmethod
        def accepts_empty_values(cls) -> bool:
            return True
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [OutputDefinition(name="output")]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class FirstNonEmptyOrDefaultBlockV1(WorkflowBlock):
    
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            data: Batch[Optional[Any]],
            default: Any,
        ) -> BlockResult:
            result = default
            for data_element in data:
                if data_element is not None:
                    return {"output": data_element}
            return {"output": result}
    ```

    * in lines `20-22` you may find declaration stating that block acccepts empt inputs 
    
    * a consequence of lines `20-22` is visible in line `41`, when signature states that 
    input `Batch` may contain empty elements that needs to be handled. In fact - the block 
    generates "artificial" output substituting empty value, which makes it possible for 
    those outputs to be "visible" for blocks not accepting empty inputs that refer to the 
    output of this block. You should assume that each input that is substituted by Execution
    Engine with data generated in runtime may provide optional elements.


### Block with custom constructor parameters

Some blocks may require objects constructed by outside world to work. In such
scenario, Workflows Execution Engine job is to transfer those entities to the block, 
making it possible to be used. The mechanism is described in 
[the page presenting Workflows Compiler](/workflows/workflows_compiler/), as this is the 
component responsible for dynamic construction of steps from blocks classes.

Constructor parameters must be:

* requested by block - using class method `WorkflowBlock.get_init_parameters(...)`

* provided in the environment running Workflows Execution Engine:

    * directly, as shown in [this](/workflows/modes_of_running/#workflows-in-python-package) example
    
    * using defaults [registered for Workflow plugin](/workflows/blocks_bundling)

Let's see how to request init parameters while defining block.

??? example "Block requesting constructor parameters"

    ```{ .py linenums="1" hl_lines="30-31 33-35"}
    from typing import Any, List, Literal, Optional, Type

    from inference.core.workflows.execution_engine.entities.base import (
        Batch,
        OutputDefinition,
    )
    from inference.core.workflows.execution_engine.entities.types import StepOutputSelector
    from inference.core.workflows.prototypes.block import (
        BlockResult,
        WorkflowBlock,
        WorkflowBlockManifest,
    )


    class BlockManifest(WorkflowBlockManifest):
        type: Literal["my_plugin/example@v1"]
        data: List[StepOutputSelector()]
    
        @classmethod
        def describe_outputs(cls) -> List[OutputDefinition]:
            return [OutputDefinition(name="output")]
    
        @classmethod
        def get_execution_engine_compatibility(cls) -> Optional[str]:
            return ">=1.0.0,<2.0.0"
    
    
    class ExampleBlock(WorkflowBlock):
      
        def __init__(my_parameter: int):
            self._my_parameter = my_parameter

        @classmethod
        def get_init_parameters(cls) -> List[str]:
            return ["my_parameter"]
        
        @classmethod
        def get_manifest(cls) -> Type[WorkflowBlockManifest]:
            return BlockManifest
    
        def run(
            self,
            data: Batch[Any],
        ) -> BlockResult:
            pass
    ```

    * lines `30-31` declare class constructor which is not parameter-free

    * to inform Execution Engine that block requires custom initialisation, 
    `get_init_parameters(...)` method in lines `33-35` enlists names of all 
    parameters that must be provided
