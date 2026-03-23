"""Tests for ODataAgent."""

import pytest
from odataagent import ODataService, QueryBuilder, MetadataParser
from odataagent.query import build_filter_string
from odataagent.errors import map_http_error, ODataError
from odataagent.paginator import auto_paginate, paginated_query


# ── QueryBuilder Tests ───────────────────────────────────────────

class TestQueryBuilder:
    def test_simple_entity(self):
        qb = QueryBuilder(entity="Customers")
        assert qb.build_path() == "Customers"

    def test_filter_string(self):
        qb = QueryBuilder(entity="Orders", filter_dict={"Country": "Germany"})
        path = qb.build_path()
        assert "$filter=Country eq 'Germany'" in path

    def test_filter_numeric(self):
        qb = QueryBuilder(entity="Products", filter_dict={"Price": 50})
        path = qb.build_path()
        assert "$filter=Price eq 50" in path

    def test_filter_multiple(self):
        qb = QueryBuilder(entity="Orders", filter_dict={"Country": "US", "Status": "Open"})
        path = qb.build_path()
        assert "Country eq 'US'" in path
        assert "Status eq 'Open'" in path
        assert " and " in path

    def test_filter_list_or(self):
        qb = QueryBuilder(entity="Orders", filter_dict={"Priority": ["1", "2"]})
        path = qb.build_path()
        assert "Priority eq '1' or Priority eq '2'" in path

    def test_filter_operators(self):
        qb = QueryBuilder(entity="Products", filter_dict={"Price": {"gt": 10, "lt": 100}})
        path = qb.build_path()
        assert "Price gt 10" in path
        assert "Price lt 100" in path

    def test_select(self):
        qb = QueryBuilder(entity="Customers", select=["Name", "City"])
        path = qb.build_path()
        assert "$select=Name,City" in path

    def test_expand(self):
        qb = QueryBuilder(entity="Orders", expand=["OrderDetails", "Customer"])
        path = qb.build_path()
        assert "$expand=OrderDetails,Customer" in path

    def test_top_skip(self):
        qb = QueryBuilder(entity="Products", top=10, skip=20)
        path = qb.build_path()
        assert "$top=10" in path
        assert "$skip=20" in path

    def test_orderby(self):
        qb = QueryBuilder(entity="Products", orderby="Price desc")
        path = qb.build_path()
        assert "$orderby=Price desc" in path

    def test_v2_format(self):
        qb = QueryBuilder(entity="Orders", version="v2")
        path = qb.build_path()
        assert "$format=json" in path

    def test_combined(self):
        qb = QueryBuilder(
            entity="MaintenanceOrder",
            version="v2",
            filter_dict={"Plant": "1000", "Priority": "1"},
            select=["OrderID", "Description"],
            expand=["Operations"],
            top=5,
        )
        path = qb.build_path()
        assert "MaintenanceOrder?" in path
        assert "$filter=" in path
        assert "$select=OrderID,Description" in path
        assert "$expand=Operations" in path
        assert "$top=5" in path
        assert "$format=json" in path


# ── Error Mapping Tests ──────────────────────────────────────────

class TestErrorMapping:
    @pytest.mark.parametrize("code,expected_fragment", [
        (400, "Invalid query"),
        (401, "Authentication"),
        (403, "Access denied"),
        (404, "not found"),
        (429, "Rate limited"),
        (500, "Server error"),
    ])
    def test_status_codes(self, code, expected_fragment):
        msg = map_http_error(code)
        assert expected_fragment in msg

    def test_v4_error_body(self):
        body = '{"error": {"code": "0", "message": "Field X not found"}}'
        msg = map_http_error(400, body)
        assert "Field X not found" in msg

    def test_v2_error_body(self):
        body = '{"error": {"message": {"value": "Entity does not exist"}}}'
        msg = map_http_error(404, body)
        assert "Entity does not exist" in msg

    def test_long_message_ignored(self):
        body = '{"error": {"message": "' + "x" * 500 + '"}}'
        msg = map_http_error(500, body)
        # Long messages should NOT be included (>200 chars)
        assert "x" * 200 not in msg

    def test_invalid_json_body(self):
        msg = map_http_error(500, "not json at all")
        assert "Server error" in msg

    def test_odata_exception(self):
        err = ODataError(403, "Forbidden", '{"error":{"message":"No auth"}}')
        assert err.status_code == 403
        assert "Access denied" in err.safe_message


# ── Service Tests ────────────────────────────────────────────────

class TestODataService:
    def test_query_builds_url(self):
        svc = ODataService(base_url="https://example.com/odata/")
        result = svc.query(
            entity="Products",
            filter={"Category": "Food"},
            top=5,
        )
        assert result[0]["_query_url"].startswith("https://example.com/odata/Products")
        assert "Category eq 'Food'" in result[0]["_query_url"]

    def test_get_by_key_string(self):
        svc = ODataService(base_url="https://example.com/odata/")
        result = svc.get_by_key("Customers", "ALFKI")
        assert "Customers('ALFKI')" in result["_query_url"]

    def test_get_by_key_int(self):
        svc = ODataService(base_url="https://example.com/odata/")
        result = svc.get_by_key("Orders", 10248)
        assert "Orders(10248)" in result["_query_url"]

    def test_as_tools_generates_schemas(self):
        svc = ODataService(base_url="https://example.com/odata/")
        svc._entities = {"Product": None, "Customer": None}
        svc._metadata_loaded = True
        tools = svc.as_tools(entities=["Product", "Customer"])
        assert len(tools) == 4  # 2 entities × (query + get_by_id)
        names = [t["function"]["name"] for t in tools]
        assert "query_product" in names
        assert "get_customer_by_id" in names


# ── Paginator Tests ──────────────────────────────────────────────

class TestPaginator:
    def test_v4_pagination(self):
        pages = [
            {"value": [{"id": 1}, {"id": 2}], "@odata.nextLink": "page2"},
            {"value": [{"id": 3}]},
        ]
        call_count = [0]

        def mock_fetch(url):
            result = pages[call_count[0]]
            call_count[0] += 1
            return result

        results = auto_paginate(mock_fetch, "start", version="v4")
        assert len(results) == 3
        assert results[-1]["id"] == 3

    def test_v2_pagination(self):
        pages = [
            {"d": {"results": [{"id": 1}], "__next": "page2"}},
            {"d": {"results": [{"id": 2}]}},
        ]
        call_count = [0]

        def mock_fetch(url):
            result = pages[call_count[0]]
            call_count[0] += 1
            return result

        results = auto_paginate(mock_fetch, "start", version="v2")
        assert len(results) == 2

    def test_max_pages_limit(self):
        def infinite_fetch(url):
            return {"value": [{"id": 1}], "@odata.nextLink": "next"}

        results = auto_paginate(infinite_fetch, "start", max_pages=3)
        assert len(results) == 3  # Limited to 3 pages

    def test_paginated_query_params(self):
        params = paginated_query("Orders", page_size=50, max_results=200)
        assert len(params) == 4
        assert params[0]["$skip"] == "0"
        assert params[1]["$skip"] == "50"
        assert params[3]["$skip"] == "150"
