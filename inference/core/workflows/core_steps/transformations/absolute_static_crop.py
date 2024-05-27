from dataclasses import replace
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union
from uuid import uuid4

from pydantic import AliasChoices, ConfigDict, Field, PositiveInt

from inference.core.workflows.entities.base import (
    Batch,
    ImageParentMetadata,
    OriginCoordinatesSystem,
    OutputDefinition,
    WorkflowImageData,
)
from inference.core.workflows.entities.types import (
    BATCH_OF_IMAGES_KIND,
    INTEGER_KIND,
    FlowControl,
    StepOutputImageSelector,
    WorkflowImageSelector,
    WorkflowParameterSelector,
)
from inference.core.workflows.prototypes.block import (
    WorkflowBlock,
    WorkflowBlockManifest,
)

LONG_DESCRIPTION = """
Crop a Region of Interest (RoI) from an image, using absolute coordinates.

This is useful when placed after an ObjectDetection block as part of a multi-stage 
workflow. For example, you could use an ObjectDetection block to detect objects, then 
the AbsoluteStaticCrop block to crop objects, then an OCR block to run character 
recognition on each of the individual cropped regions.
"""


class BlockManifest(WorkflowBlockManifest):
    model_config = ConfigDict(
        json_schema_extra={
            "short_description": "Use absolute coordinates for cropping.",
            "long_description": LONG_DESCRIPTION,
            "license": "Apache-2.0",
            "block_type": "transformation",
        }
    )
    type: Literal["AbsoluteStaticCrop"]
    images: Union[WorkflowImageSelector, StepOutputImageSelector] = Field(
        description="Reference at image to be used as input for step processing",
        examples=["$inputs.image", "$steps.cropping.crops"],
        validation_alias=AliasChoices("images", "image"),
    )
    x_center: Union[PositiveInt, WorkflowParameterSelector(kind=[INTEGER_KIND])] = (
        Field(
            description="Center X of static crop (absolute coordinate)",
            examples=[40, "$inputs.center_x"],
        )
    )
    y_center: Union[PositiveInt, WorkflowParameterSelector(kind=[INTEGER_KIND])] = (
        Field(
            description="Center Y of static crop (absolute coordinate)",
            examples=[40, "$inputs.center_y"],
        )
    )
    width: Union[PositiveInt, WorkflowParameterSelector(kind=[INTEGER_KIND])] = Field(
        description="Width of static crop (absolute value)",
        examples=[40, "$inputs.width"],
    )
    height: Union[PositiveInt, WorkflowParameterSelector(kind=[INTEGER_KIND])] = Field(
        description="Height of static crop (absolute value)",
        examples=[40, "$inputs.height"],
    )

    @classmethod
    def describe_outputs(cls) -> List[OutputDefinition]:
        return [
            OutputDefinition(name="crops", kind=[BATCH_OF_IMAGES_KIND]),
        ]


class AbsoluteStaticCropBlock(WorkflowBlock):

    @classmethod
    def get_manifest(cls) -> Type[WorkflowBlockManifest]:
        return BlockManifest

    async def run_locally(
        self,
        images: Batch[Optional[WorkflowImageData]],
        x_center: int,
        y_center: int,
        width: int,
        height: int,
    ) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], FlowControl]]:
        results = [
            {
                "crops": take_static_crop(
                    image=image,
                    x_center=x_center,
                    y_center=y_center,
                    width=width,
                    height=height,
                )
            }
            for image in images.iter_nonempty()
        ]
        return images.align_batch_results(results=results, null_element={"crops": None})


def take_static_crop(
    image: WorkflowImageData,
    x_center: int,
    y_center: int,
    width: int,
    height: int,
) -> WorkflowImageData:
    x_min = round(x_center - width / 2)
    y_min = round(y_center - height / 2)
    x_max = round(x_min + width)
    y_max = round(y_min + height)
    cropped_image = image.numpy_image[y_min:y_max, x_min:x_max]
    workflow_root_ancestor_coordinates = replace(
        image.workflow_root_ancestor_metadata.origin_coordinates,
        left_top_x=image.workflow_root_ancestor_metadata.origin_coordinates.left_top_x
        + x_min,
        left_top_y=image.workflow_root_ancestor_metadata.origin_coordinates.left_top_y
        + y_min,
    )
    workflow_root_ancestor_metadata = ImageParentMetadata(
        parent_id=image.workflow_root_ancestor_metadata.parent_id,
        origin_coordinates=workflow_root_ancestor_coordinates,
    )
    return WorkflowImageData(
        parent_metadata=ImageParentMetadata(
            parent_id=f"absolute_static_crop.{uuid4()}",
            origin_coordinates=OriginCoordinatesSystem(
                left_top_x=x_min,
                left_top_y=y_min,
                origin_width=image.numpy_image.shape[1],
                origin_height=image.numpy_image.shape[0],
            ),
        ),
        workflow_root_ancestor_metadata=workflow_root_ancestor_metadata,
        numpy_image=cropped_image,
    )
