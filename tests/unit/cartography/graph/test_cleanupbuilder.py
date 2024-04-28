from typing import List

import pytest

from cartography.graph.cleanupbuilder import _build_cleanup_node_and_rel_queries
from cartography.graph.cleanupbuilder import build_cleanup_queries
from cartography.graph.job import get_parameters
from cartography.models.aws.emr import EMRClusterToAWSAccount
from tests.data.graph.querybuilder.sample_models.asset_with_non_kwargs_tgm import FakeEC2InstanceSchema
from tests.data.graph.querybuilder.sample_models.asset_with_non_kwargs_tgm import FakeEC2InstanceToAWSAccount
from tests.data.graph.querybuilder.sample_models.interesting_asset import InterestingAssetSchema
from tests.data.graph.querybuilder.sample_models.interesting_asset import InterestingAssetToHelloAssetRel
from tests.data.graph.querybuilder.sample_models.interesting_asset import InterestingAssetToSubResourceRel
from tests.data.graph.querybuilder.sample_models.simple_node import SimpleNodeSchema
from tests.unit.cartography.graph.helpers import clean_query_list


def test_cleanup_sub_rel():
    """
    Test that we correctly generate cleanup queries when a selected rel is not specified.
    """
    actual_queries: List[str] = _build_cleanup_node_and_rel_queries(
        InterestingAssetSchema(),
        InterestingAssetToSubResourceRel(),
    )
    expected_queries = [
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        WHERE n.lastupdated <> $UPDATE_TAG
        WITH n LIMIT $LIMIT_SIZE
        DETACH DELETE n;
        """,
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        WHERE s.lastupdated <> $UPDATE_TAG
        WITH s LIMIT $LIMIT_SIZE
        DELETE s;
        """,
    ]
    assert clean_query_list(actual_queries) == clean_query_list(expected_queries)


def test_cleanup_with_selected_rel():
    """
    Test that we correctly generate cleanup queries when a selected rel is specified.
    """
    actual_queries: List[str] = _build_cleanup_node_and_rel_queries(
        InterestingAssetSchema(),
        InterestingAssetToHelloAssetRel(),
    )
    expected_queries = [
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        MATCH (n)-[r:ASSOCIATED_WITH]->(:HelloAsset)
        WHERE n.lastupdated <> $UPDATE_TAG
        WITH n LIMIT $LIMIT_SIZE
        DETACH DELETE n;
        """,
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        MATCH (n)-[r:ASSOCIATED_WITH]->(:HelloAsset)
        WHERE r.lastupdated <> $UPDATE_TAG
        WITH r LIMIT $LIMIT_SIZE
        DELETE r;
        """,
    ]
    assert clean_query_list(actual_queries) == clean_query_list(expected_queries)


def test_cleanup_with_invalid_selected_rel_raises_exc():
    """
    Test that we raise a ValueError if we try to cleanup a node and provide a specified rel but the rel doesn't exist on
    the node schema.
    """
    exc_msg = "EMRClusterToAWSAccount is not defined on CartographyNodeSchema type InterestingAssetSchema"
    with pytest.raises(ValueError, match=exc_msg):
        _build_cleanup_node_and_rel_queries(InterestingAssetSchema(), EMRClusterToAWSAccount())


def test_build_cleanup_queries():
    """
    Test that the full set of cleanup queries generated for a node schema is what we expect. Order matters!
    """
    actual_queries: list[str] = build_cleanup_queries(InterestingAssetSchema())
    expected_queries = [
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        WHERE n.lastupdated <> $UPDATE_TAG
        WITH n LIMIT $LIMIT_SIZE
        DETACH DELETE n;
        """,
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        WHERE s.lastupdated <> $UPDATE_TAG
        WITH s LIMIT $LIMIT_SIZE
        DELETE s;""",
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        MATCH (n)-[r:ASSOCIATED_WITH]->(:HelloAsset)
        WHERE r.lastupdated <> $UPDATE_TAG
        WITH r LIMIT $LIMIT_SIZE
        DELETE r;
        """,
        """
        MATCH (n:InterestingAsset)<-[s:RELATIONSHIP_LABEL]-(:SubResource{id: $sub_resource_id})
        MATCH (n)<-[r:CONNECTED]-(:WorldAsset)
        WHERE r.lastupdated <> $UPDATE_TAG
        WITH r LIMIT $LIMIT_SIZE
        DELETE r;
        """,
    ]
    assert clean_query_list(actual_queries) == clean_query_list(expected_queries)


def test_get_params_from_queries():
    """
    Test that we are able to correctly retrieve parameter names from the generated cleanup queries.
    """
    queries: list[str] = build_cleanup_queries(InterestingAssetSchema())
    assert set(get_parameters(queries)) == {'UPDATE_TAG', 'sub_resource_id', 'LIMIT_SIZE'}


def test_build_cleanup_queries_selected_rels_no_sub_res_raises_exc():
    """
    Test that not specifying the sub resource rel as a selected_relationship in build_cleanup_queries raises exception
    """
    with pytest.raises(ValueError, match='node_schema without a sub resource relationship is not supported'):
        build_cleanup_queries(SimpleNodeSchema())


def test_build_cleanup_node_and_rel_queries_sub_res_tgm_not_validated_raises_exc():
    with pytest.raises(ValueError, match='must have set_in_kwargs=True'):
        _build_cleanup_node_and_rel_queries(FakeEC2InstanceSchema(), FakeEC2InstanceToAWSAccount())
