from typing import TypedDict


class MultiModuleState(TypedDict):
    query: str
    documents: list[str]
    response: str
