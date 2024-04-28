import abc
from dataclasses import dataclass
from dataclasses import field
from dataclasses import make_dataclass
from enum import auto
from enum import Enum
from typing import Dict
from typing import List

from cartography.models.core.common import PropertyRef


class LinkDirection(Enum):
    """
    Each CartographyRelSchema has a LinkDirection that determines whether the relationship points toward the original
    node ("INWARD") or away from the original node ("OUTWARD").

    For example the following code creates the path `(:EMRCluster)<-[:RESOURCE]-(:AWSAccount)`:

        class EMRCluster(CartographyNodeSchema):
            label: str = "EMRCluster"
            sub_resource_relationship: CartographyRelSchema = EMRClusterToAWSAccount()
            # ...

        class EMRClusterToAWSAccount(CartographyRelSchema):
            target_node_label: str = "AWSAccount"
            rel_label: str = "RESOURCE"
            direction: LinkDirection = LinkDirection.INWARD
            # ...

    If `EMRClusterToAWSAccount.direction` was LinkDirection.OUTWARD, then the directionality of the relationship would
    be `(:EMRCluster)-[:RESOURCE]->(:AWSAccount)` instead.
    """
    INWARD = auto()
    OUTWARD = auto()


@dataclass(frozen=True)
class CartographyRelProperties(abc.ABC):
    """
    Abstract class that represents the properties on a CartographyRelSchema. This is intended to enforce that all
    subclasses will have a lastupdated field defined on their resulting relationships. These fields are assigned to the
    relationship in the `SET` clause.
    """
    lastupdated: PropertyRef = field(init=False)

    def __post_init__(self):
        """
        Data validation.
        1. Prevents direct instantiation. This workaround is needed since this is a dataclass and an abstract
        class without an abstract method defined. See https://stackoverflow.com/q/60590442.
        2. Stops reserved words from being used as attribute names. See https://github.com/lyft/cartography/issues/1064.
        """
        if self.__class__ == CartographyRelProperties:
            raise TypeError("Cannot instantiate abstract class.")

        if hasattr(self, 'firstseen'):
            raise TypeError(
                "`firstseen` is a reserved word and is automatically set by the querybuilder on cartography rels, so "
                f'it cannot be used on class "{type(self).__name__}(CartographyRelProperties)". Please either choose '
                "a different name for `firstseen` or omit altogether.",
            )


@dataclass(frozen=True)
class TargetNodeMatcher:
    """
    Dataclass used to encapsulate the following mapping:
    Keys: one or more attribute names on the target_node_label used to uniquely identify what node to connect to.
    Values: The value of the target_node_key used to uniquely identify what node to connect to. This is given as a
    PropertyRef.
    This is used to ensure dataclass immutability when composed as part of a CartographyNodeSchema object.
    See `make_target_node_matcher()`.
    """
    pass


def make_target_node_matcher(key_ref_dict: Dict[str, PropertyRef]) -> TargetNodeMatcher:
    """
    :param key_ref_dict: A Dict mapping keys present on the node to PropertyRef objects.
    :return: A TargetNodeMatcher used for CartographyRelSchema to match with other nodes.
    """
    fields = [(key, PropertyRef, field(default=prop_ref)) for key, prop_ref in key_ref_dict.items()]
    return make_dataclass(TargetNodeMatcher.__name__, fields, frozen=True)()


@dataclass(frozen=True)
class CartographyRelSchema(abc.ABC):
    """
    Abstract base dataclass that represents a cartography relationship.

    The CartographyRelSchema contains properties that make it possible to connect the CartographyNodeSchema to other
    existing nodes in the graph.
    """
    @property
    @abc.abstractmethod
    def properties(self) -> CartographyRelProperties:
        """
        :return: The properties of the relationship.
        """
        pass

    @property
    @abc.abstractmethod
    def target_node_label(self) -> str:
        """
        :return: The target node label that this relationship will connect to.
        """
        pass

    @property
    @abc.abstractmethod
    def target_node_matcher(self) -> TargetNodeMatcher:
        """
        :return: A TargetNodeMatcher object used to find what node(s) to attach the relationship to.
        """
        pass

    @property
    @abc.abstractmethod
    def rel_label(self) -> str:
        """
        :return: The string label of the relationship.
        """
        pass

    @property
    @abc.abstractmethod
    def direction(self) -> LinkDirection:
        """
        :return: The LinkDirection of the query. Please see the `LinkDirection` docs for a detailed explanation.
        """
        pass


@dataclass(frozen=True)
class OtherRelationships:
    """
    Encapsulates a list of CartographyRelSchema. This is used to ensure dataclass immutability when composed as part of
    a CartographyNodeSchema object.
    """
    rels: List[CartographyRelSchema]
