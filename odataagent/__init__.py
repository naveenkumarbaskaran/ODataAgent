"""ODataAgent — Turn OData services into LLM tools."""

from odataagent.service import ODataService
from odataagent.query import QueryBuilder
from odataagent.metadata import MetadataParser

__version__ = "0.3.0"
__all__ = ["ODataService", "QueryBuilder", "MetadataParser"]
