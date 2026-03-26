<div align="center">

<img src="assets/banner.svg" alt="ODataAgent" width="700">

# 🔗 ODataAgent

**Turn any OData service into an AI-queryable tool — zero boilerplate.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-38%20passed-brightgreen.svg)]()
[![OData V2/V4](https://img.shields.io/badge/OData-V2%20%2B%20V4-purple.svg)]()

*Automatically generates LLM tool schemas from OData `$metadata`, handles query construction, pagination, and error mapping — so your AI agent can talk to SAP, Dynamics, or any OData service.*

</div>

---

## Why?

Building AI agents that query enterprise APIs is painful:
1. **Schema discovery** — Hundreds of entities, thousands of fields
2. **Query construction** — `$filter`, `$expand`, `$select`, `$orderby` syntax is error-prone
3. **Pagination** — `$skip`/`$top` or `@odata.nextLink` handling
4. **Error mapping** — HTTP 403, 404, 500 → useful agent messages

ODataAgent solves all four in one line:

```python
from odataagent import ODataService

sap = ODataService(
    base_url="https://services.odata.org/V4/Northwind/Northwind.svc",
    # For SAP: auth=("user", "pass"), headers={"sap-client": "001"}
)

# Auto-generates LLM tools from $metadata
tools = sap.as_tools()
# → [get_customers, search_orders, get_order_details, ...]
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LLM Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                           │
│  │ as_tools()   │──→ OpenAI function schemas                │
│  └──────┬───────┘                                           │
│         │                                                   │
│  ┌──────▼───────┐   ┌─────────────┐   ┌─────────────────┐  │
│  │ QueryBuilder │──→│ HTTP Client │──→│ OData Service   │  │
│  │ ($filter,    │   │ (retry,     │   │ (SAP, Dynamics, │  │
│  │  $expand,    │   │  auth,      │   │  Northwind)     │  │
│  │  $select)    │   │  timeout)   │   │                 │  │
│  └──────────────┘   └─────────────┘   └─────────────────┘  │
│         │                                                   │
│  ┌──────▼───────┐   ┌─────────────┐                        │
│  │ Paginator    │   │ ErrorMapper │                        │
│  │ (auto $skip  │   │ (HTTP→agent │                        │
│  │  or nextLink)│   │  messages)  │                        │
│  └──────────────┘   └─────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
pip install odataagent
```

### Basic Query

```python
from odataagent import ODataService

svc = ODataService("https://services.odata.org/V4/Northwind/Northwind.svc")

# Query with natural parameters
results = svc.query(
    entity="Customers",
    filter={"Country": "Germany"},
    select=["CustomerID", "CompanyName", "City"],
    top=5,
)
print(results)
# [{"CustomerID": "ALFKI", "CompanyName": "Alfreds Futterkiste", "City": "Berlin"}, ...]
```

### As LLM Tools

```python
tools = svc.as_tools(
    entities=["Customers", "Orders", "Products"],  # subset
    max_results=20,
)

# Returns OpenAI-compatible function schemas
for tool in tools:
    print(f"{tool['function']['name']}: {tool['function']['description']}")
# query_customers: Search Customers by Country, City, CompanyName
# query_orders: Search Orders by CustomerID, OrderDate, ShipCountry
# get_order_by_id: Get a single Order by OrderID with line items
```

### SAP OData (V2)

```python
sap = ODataService(
    base_url="https://my-sap.com/sap/opu/odata/sap/API_MAINTENANCEORDER",
    version="v2",
    auth=("SAP_USER", "SAP_PASS"),
    headers={"sap-client": "001"},
)

orders = sap.query(
    entity="MaintenanceOrder",
    filter={"MaintenancePlanningPlant": "1000", "MaintPriority": "1"},
    expand=["MaintenanceOrderOperation"],
    top=10,
)
```

## Features

| Feature | V2 | V4 | Description |
|---------|:--:|:--:|-------------|
| `$metadata` parsing | ✅ | ✅ | Auto-discover entities and their fields |
| `$filter` builder | ✅ | ✅ | Dict → OData filter string |
| `$expand` | ✅ | ✅ | Nested entity expansion |
| `$select` | ✅ | ✅ | Field projection |
| `$orderby` | ✅ | ✅ | Sort control |
| Pagination | ✅ | ✅ | Auto `$skip/$top` or `@odata.nextLink` |
| Auth (Basic/Bearer) | ✅ | ✅ | Configurable authentication |
| CSRF token | ✅ | — | Auto-fetch for write operations |
| Batch requests | ✅ | ✅ | `$batch` support |
| Error mapping | ✅ | ✅ | HTTP errors → agent-safe messages |
| Tool schema gen | ✅ | ✅ | OpenAI function calling format |

## Documentation

- [Architecture & Flow Diagrams](docs/architecture.md)
- [SAP Integration Guide](docs/sap-guide.md)
- [API Reference](docs/api.md)

## License

MIT
