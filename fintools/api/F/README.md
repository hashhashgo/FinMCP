Languages: English | [中文](README.zh_CN.md)

# FinTools · Function Call API (`fintools.api.F`)

This directory provides the **function-call version of the FinTools API**.

This API is intended for users who want to **directly use financial data and analysis tools in Python**.

All functions are located under:

```python
fintools.api.F
```

---

## About Function Documentation

The behavior, parameters, and return values of each function are defined by the function implementation itself.

* Each function’s parameter types, default values, and semantics are clearly specified in its signature and docstring
* This README does not duplicate parameter or return-value documentation
* It is recommended to inspect function definitions directly using your IDE/editor (hover / jump to definition)

---

## Data Types and Enums

Some functions rely on built-in data types or enums (e.g. underlying types, data frequency).

Example:

```python
from fintools.api.F.types import UnderlyingTypes, DataFrequency
```

Please refer to the source code for the complete list of available values.

---

## Errors and Exceptions

* Invalid parameters, missing data, and network errors are raised as Python exceptions
* No silent fallback is performed
* Upstream applications are expected to handle exceptions explicitly

---