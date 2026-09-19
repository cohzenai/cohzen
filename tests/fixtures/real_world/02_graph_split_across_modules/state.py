from typing import TypedDict, List

class MultiModuleState(TypedDict):
    query: str
    documents: List[str]
    response: str
