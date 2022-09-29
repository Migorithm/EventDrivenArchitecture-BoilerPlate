from collections import deque

from sqlalchemy import MetaData, event
from sqlalchemy.orm import registry

from app.domain import models

metadata = MetaData()

mapper_registry = registry(metadata=metadata)


def start_mappers():
    pass


@event.listens_for(models.ExampleModel, "load")
def receive_load_review(example_model, _):
    example_model.events = deque()
