# src/mcp/servers/openapi/utils/code_generators/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class CodeGenerator(ABC):
    """Base class for all code generators."""
    
    @abstractmethod
    def generate(self, openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
        """Generate code for the given OpenAPI spec."""
        pass