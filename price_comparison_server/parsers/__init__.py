# price_comparison_server/parsers/__init__.py

from typing import Dict, Type
from .base_parser import BaseChainParser
from .shufersal_parser import ShufersalParser
from .victory_parser import VictoryParser

# Registry of all available parsers
PARSER_REGISTRY: Dict[str, Type[BaseChainParser]] = {
    'shufersal': ShufersalParser,
    'victory': VictoryParser,
}

def get_parser(chain_name: str) -> BaseChainParser:
    """Get parser instance for a specific chain"""
    parser_class = PARSER_REGISTRY.get(chain_name.lower())
    if not parser_class:
        raise ValueError(f"No parser found for chain: {chain_name}")
    return parser_class()

def get_all_parsers() -> Dict[str, BaseChainParser]:
    """Get instances of all registered parsers"""
    return {name: parser_class() for name, parser_class in PARSER_REGISTRY.items()}

# To add a new chain:
# 1. Create a new file: new_chain_parser.py
# 2. Implement class NewChainParser(BaseChainParser)
# 3. Import it here: from .new_chain_parser import NewChainParser
# 4. Add to registry: 'new_chain': NewChainParser