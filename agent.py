"""Inventory/restocking agent for the real AdventureWorks dataset (Microsoft's official
sample database). Turns a plain-English question into SQL, runs it read-only, and
narrates the result - same 3-step pattern as the NL-to-SQL agent, new domain.

Supports three LLM providers, selected via LLM_PROVIDER env var ("anthropic", "gemini", or "groq").
Defaults to "groq" - best free-tier limits of the three for this demo.
"""
import os
import re

import duckdb

ANTHROPIC_MODEL = "claude-sonnet-4-5"
GEMINI_MODEL = "gemini-flash-latest"
GROQ_MODEL = "llama-3.3-70b-versatile"

SCHEMA_DESCRIPTION = """
Tables in this DuckDB database - real AdventureWorks (Microsoft's sample manufacturing/retail company) data:

product(ProductID, Name, ProductNumber, Color, SafetyStockLevel, ReorderPoint, StandardCost, ListPrice, ProductSubcategoryID)
  - SafetyStockLevel: minimum quantity to keep on hand
  - ReorderPoint: inventory level that should trigger a new purchase order

product_category(ProductCategoryID, Name)
product_subcategory(ProductSubcategoryID, ProductCategoryID, Name)
  - join product.ProductSubcategoryID -> product_subcategory.ProductSubcategoryID
  - join product_subcategory.ProductCategoryID -> product_category.ProductCategoryID

product_inventory(ProductID, LocationID, Shelf, Bin, Quantity)
  - actual on-hand quantity per warehouse location - a single product can have MULTIPLE rows (one per location/shelf/bin)
  - join product_inventory.ProductID -> product.ProductID
  - IMPORTANT: SafetyStockLevel and ReorderPoint are company-wide thresholds, not per-location. When comparing
    inventory to these thresholds, always SUM(Quantity) grouped by ProductID first - never compare a single
    location's row directly, or the same product will appear multiple times with misleading partial quantities.

location(LocationID, Name, CostRate, Availability)
  - join product_inventory.LocationID -> location.LocationID

vendor(BusinessEntityID, AccountNumber, Name, CreditRating, PreferredVendorStatus, ActiveFlag)
  - CreditRating: 1 (best) to 5 (worst)

product_vendor(ProductID, BusinessEntityID, AverageLeadTime, StandardPrice, MinOrderQty, MaxOrderQty, OnOrderQty)
  - AverageLeadTime: days it takes this vendor to deliver this product
  - join product_vendor.ProductID -> product.ProductID
  - join product_vendor.BusinessEntityID -> vendor.BusinessEntityID

purchase_order_header(PurchaseOrderID, Status, VendorID, OrderDate, ShipDate, SubTotal, TaxAmt, Freight, TotalDue)
  - Status: 1=Pending, 2=Approved, 3=Rejected, 4=Complete
  - join purchase_order_header.VendorID -> vendor.BusinessEntityID

purchase_order_detail(PurchaseOrderID, PurchaseOrderDetailID, DueDate, OrderQty, ProductID, UnitPrice, ReceivedQty, RejectedQty)
  - join purchase_order_detail.PurchaseOrderID -> purchase_order_header.PurchaseOrderID
  - join purchase_order_detail.ProductID -> product.ProductID
"""

FORBIDDEN_KEYWORDS = ("insert", "update", "delete", "drop", "alter", "create", "attach", "copy", "pragma")


class LLMClient:
    """Thin wrapper so the agent logic doesn't care which provider is behind it."""

    def __init__(self, provider=None, api_key=None):
        self.provider = provider or os.environ.get("LLM_PROVIDER", "groq")

        if self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        elif self.provider == "gemini":
            from google import genai
            self._client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        elif self.provider == "groq":
            from groq import Groq
            self._client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}")

    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        if self.provider == "anthropic":
            response = self._client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        elif self.provider == "gemini":
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        else:
            response = self._client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()


class InventoryAgent:
    def __init__(self, db_path="data/adventureworks.duckdb", provider=None, api_key=None):
        self.db_path = db_path
        self.llm = LLMClient(provider=provider, api_key=api_key)

    def _generate_sql(self, question: str) -> str:
        prompt = f"""You are a SQL generator for a DuckDB database of a manufacturing/retail company's
inventory and purchasing data. Given the schema below and a user's plain-English question, output
ONLY a single read-only SELECT SQL query that answers it. No explanation, no markdown code fences,
just the raw SQL statement.

{SCHEMA_DESCRIPTION}

Question: {question}

SQL:"""
        sql = self.llm.complete(prompt, max_tokens=500)
        sql = re.sub(r"^```sql\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
        return sql

    def _validate_sql(self, sql: str):
        lowered = sql.lower().lstrip()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise ValueError("Generated query is not a read-only SELECT/CTE statement - refusing to run it.")
        for kw in FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{kw}\b", lowered):
                raise ValueError(f"Generated query contains forbidden keyword '{kw}' - refusing to run it.")

    def _narrate(self, question: str, sql: str, result_df) -> str:
        preview = result_df.head(20).to_csv(index=False)
        prompt = f"""A user asked: "{question}"
This SQL was run: {sql}
The result (CSV, possibly truncated):
{preview}

In exactly one sentence, plainly summarize what this result shows. No preamble."""
        return self.llm.complete(prompt, max_tokens=200)

    def ask(self, question: str) -> dict:
        sql = self._generate_sql(question)
        self._validate_sql(sql)

        con = duckdb.connect(self.db_path, read_only=True)
        try:
            con.execute("PRAGMA threads=1")
            result_df = con.execute(sql).fetchdf()
        finally:
            con.close()

        narration = self._narrate(question, sql, result_df)

        return {"sql": sql, "result": result_df, "narration": narration}
