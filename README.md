Languages: English | [中文](README.zh_CN.md)

***From the current version onward, all external usage should go through `fintools.api`.***

# FinTools

**FinTools** is a financial data and analysis toolkit designed to unify the encapsulation and management of reusable financial tools and data interfaces.

FinTools provides multiple types of historical data, including:

- Historical prices  
- Historical news  
- Historical research reports  

FinTools aims to be a **lightweight, composable, and reusable financial toolkit**.

---

## Unified API Entry Point

Depending on the usage pattern, FinTools provides different API forms:

- [Function-call API](./fintools/api/F/README.md): `fintools.api.F`  
- [MCP API](./fintools/api/mcp/README.md): `fintools.api.mcp`  

Both APIs share the **same underlying functionality** and differ only in how they are invoked.

---

## Supported Tool Types

FinTools currently includes (and continues to expand) the following types of tools:

- Access to historical market data for stocks, indices, futures, FX, and crypto assets  
- Access to news, announcements, and other financial text data  
- [todo] Web search and external information retrieval  
- User-defined financial data and analysis logic  

---

## Installation

FinTools uses **uv** for dependency management and can be installed directly from GitHub:

```bash
uv add https://github.com/hashhashgo/FinTools.git
```

After installation, FinTools can be used in any uv-based project:

```python
import fintools
```

---

## Database and Caching Support

FinTools supports caching downloaded data into a local database (e.g., SQLite).

Set the environment variable:

```toml
FINTOOLS_DB=history.db
```

Create an example SQLite database:

```bash
touch history.db
```

For details on caching strategies and table schemas, refer to the documentation of the corresponding tools.

---

# License

MIT

---
