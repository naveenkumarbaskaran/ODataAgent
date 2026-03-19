"""OData $metadata XML parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyInfo:
    """OData entity property."""
    name: str
    type: str  # "Edm.String", "Edm.Int32", etc.
    nullable: bool = True
    key: bool = False
    max_length: int | None = None


@dataclass
class NavigationProperty:
    """OData navigation property (relationship)."""
    name: str
    target_entity: str
    is_collection: bool = True


@dataclass
class EntityType:
    """Parsed OData entity type."""
    name: str
    properties: list[PropertyInfo] = field(default_factory=list)
    navigation: list[NavigationProperty] = field(default_factory=list)
    key_fields: list[str] = field(default_factory=list)

    @property
    def filterable_fields(self) -> list[str]:
        """Fields that can be used in $filter."""
        return [p.name for p in self.properties if p.type in (
            "Edm.String", "Edm.Int32", "Edm.Int64", "Edm.Boolean",
            "Edm.DateTime", "Edm.DateTimeOffset",
        )]


class MetadataParser:
    """
    Parse OData $metadata XML into structured EntityType objects.

    Supports both V2 (CSDL 1.0-3.0) and V4 (CSDL 4.0+) formats.
    """

    def __init__(self, xml_content: str, version: str = "v4"):
        self.xml_content = xml_content
        self.version = version
        self._entities: dict[str, EntityType] = {}

    def parse(self) -> dict[str, EntityType]:
        """Parse the metadata XML and return entity types."""
        # Simplified parser — production would use xml.etree.ElementTree
        # This demonstrates the interface and data model
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(self.xml_content)
        except ET.ParseError:
            return {}

        # Namespace handling for OData CSDL
        ns = {
            "edmx": "http://docs.oasis-open.org/odata/ns/edmx",
            "edm": "http://docs.oasis-open.org/odata/ns/edm",
        }

        # V2 namespaces differ
        if self.version == "v2":
            ns = {
                "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
                "edm": "http://schemas.microsoft.com/ado/2008/09/edm",
            }

        for entity_type in root.iter():
            if entity_type.tag.endswith("EntityType"):
                name = entity_type.get("Name", "")
                props = []
                keys = []

                for prop in entity_type:
                    if prop.tag.endswith("Property"):
                        props.append(PropertyInfo(
                            name=prop.get("Name", ""),
                            type=prop.get("Type", "Edm.String"),
                            nullable=prop.get("Nullable", "true") == "true",
                        ))
                    elif prop.tag.endswith("Key"):
                        for key_ref in prop:
                            keys.append(key_ref.get("Name", ""))

                entity = EntityType(name=name, properties=props, key_fields=keys)
                self._entities[name] = entity

        return self._entities

    def get_entity(self, name: str) -> EntityType | None:
        """Get a parsed entity type by name."""
        if not self._entities:
            self.parse()
        return self._entities.get(name)

    def list_entities(self) -> list[str]:
        """List all entity type names."""
        if not self._entities:
            self.parse()
        return list(self._entities.keys())
