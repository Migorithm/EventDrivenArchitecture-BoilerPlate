import inspect

from app.adapters import persistent_orm
from app.service_layer import handlers, messagebus, unit_of_work


class Bootstrap:
    def __init__(
        self,
        start_orm: bool = False,
        uow: unit_of_work.AbstractUnitOfWork = unit_of_work.SqlAlchemyUnitOfWork(),
    ):
        self.start_orm: bool = start_orm
        self.uow = uow

    def start_mappers(self):
        if self.start_orm:
            persistent_orm.start_mappers()

    def __call__(self):
        dependencies = {"uow": self.uow}
        injected_event_handlers = {
            event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers]
            for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
        }
        injected_command_handlers = {
            command_type: inject_dependencies(handler, dependencies)
            for command_type, handler in handlers.COMMAND_HANDLERS.items()
        }

        return messagebus.MessageBus(
            uow=self.uow,
            event_handlers=injected_event_handlers,
            command_handlers=injected_command_handlers,
        )


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {name: dependency for name, dependency in dependencies.items() if name in params}
    return lambda message: handler(message, **deps)
