import logging
from collections import deque
from inspect import isawaitable
from typing import Callable, Type

from tenacity import RetryError, Retrying, stop_after_attempt, wait_exponential

from app.domain import commands, events
from app.domain.commands import Command
from app.domain.events import Event
from app.service_layer import unit_of_work

logger = logging.getLogger(__name__)

Message = Event | Command


class MessageBus:
    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: dict[Type[events.Event], list[Callable]],
        command_handlers: dict[Type[commands.Command], Callable],
    ):
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    async def handle(
        self,
        message: Message,
    ):
        queue: deque = deque([message])  # self.queue?
        results: deque = deque()
        while queue:
            message = queue.popleft()
            match message:
                case Event():
                    await self.handle_event(message, queue)
                case Command():
                    cmd_result = await self.handle_command(message, queue)
                    results.append(cmd_result)
                case _:
                    raise Exception(f"{message} was not an Event or Command")
        return results

    async def handle_event(
        self,
        event: Event,
        queue: deque,
    ):
        for handler in self.event_handlers[type(event)]:
            try:
                for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_exponential()):
                    with attempt:
                        logger.debug("handling event %s with handler %s", event, handler)
                        task = handler(message=event)
                        if isawaitable(task):
                            await task
                        queue.extend(self.uow.collect_new_events())
            except RetryError as retry_failure:
                logger.exception(
                    "Failed to handle event %s times, giving up!",
                    retry_failure.last_attempt.attempt_number,
                )
                continue

    async def handle_command(
        self,
        command: Command,
        queue: deque,
    ):
        logger.debug("handling command %s", command)
        try:
            handler = self.command_handlers[type(command)]
            task = handler(message=command)
            if isawaitable(task):
                res = await task
            else:
                res = task
            queue.extend(self.uow.collect_new_events())
            return res
        except Exception as e:
            logger.exception("Exception handling command %s", command)
            raise e
