"""Downloads real AdventureWorks OLTP CSV files (published by Microsoft at
github.com/microsoft/sql-server-samples) and loads the inventory/purchasing-relevant
tables into a local DuckDB file. No SQL Server needed.

Safe to run repeatedly - always rebuilds data/adventureworks.duckdb from scratch.
"""
import os
import urllib.request

import duckdb

BASE_URL = "https://raw.githubusercontent.com/microsoft/sql-server-samples/master/samples/databases/adventure-works/oltp-install-script"
DB_PATH = "data/adventureworks.duckdb"

# table_name -> (csv filename, column definitions matching the real AdventureWorks schema)
TABLES = {
    "product_category": ("ProductCategory.csv", [
        "ProductCategoryID INTEGER", "Name VARCHAR", "rowguid VARCHAR", "ModifiedDate TIMESTAMP",
    ]),
    "product_subcategory": ("ProductSubcategory.csv", [
        "ProductSubcategoryID INTEGER", "ProductCategoryID INTEGER", "Name VARCHAR",
        "rowguid VARCHAR", "ModifiedDate TIMESTAMP",
    ]),
    "product": ("Product.csv", [
        "ProductID INTEGER", "Name VARCHAR", "ProductNumber VARCHAR", "MakeFlag INTEGER",
        "FinishedGoodsFlag INTEGER", "Color VARCHAR", "SafetyStockLevel INTEGER", "ReorderPoint INTEGER",
        "StandardCost DOUBLE", "ListPrice DOUBLE", "Size VARCHAR", "SizeUnitMeasureCode VARCHAR",
        "WeightUnitMeasureCode VARCHAR", "Weight DOUBLE", "DaysToManufacture INTEGER", "ProductLine VARCHAR",
        "Class VARCHAR", "Style VARCHAR", "ProductSubcategoryID INTEGER", "ProductModelID INTEGER",
        "SellStartDate TIMESTAMP", "SellEndDate TIMESTAMP", "DiscontinuedDate TIMESTAMP",
        "rowguid VARCHAR", "ModifiedDate TIMESTAMP",
    ]),
    "location": ("Location.csv", [
        "LocationID INTEGER", "Name VARCHAR", "CostRate DOUBLE", "Availability DOUBLE", "ModifiedDate TIMESTAMP",
    ]),
    "product_inventory": ("ProductInventory.csv", [
        "ProductID INTEGER", "LocationID INTEGER", "Shelf VARCHAR", "Bin INTEGER",
        "Quantity INTEGER", "rowguid VARCHAR", "ModifiedDate TIMESTAMP",
    ]),
    "vendor": ("Vendor.csv", [
        "BusinessEntityID INTEGER", "AccountNumber VARCHAR", "Name VARCHAR", "CreditRating INTEGER",
        "PreferredVendorStatus INTEGER", "ActiveFlag INTEGER", "PurchasingWebServiceURL VARCHAR",
        "ModifiedDate TIMESTAMP",
    ]),
    "product_vendor": ("ProductVendor.csv", [
        "ProductID INTEGER", "BusinessEntityID INTEGER", "AverageLeadTime INTEGER", "StandardPrice DOUBLE",
        "LastReceiptCost DOUBLE", "LastReceiptDate TIMESTAMP", "MinOrderQty INTEGER", "MaxOrderQty INTEGER",
        "OnOrderQty INTEGER", "UnitMeasureCode VARCHAR", "ModifiedDate TIMESTAMP",
    ]),
    "purchase_order_header": ("PurchaseOrderHeader.csv", [
        "PurchaseOrderID INTEGER", "RevisionNumber INTEGER", "Status INTEGER", "EmployeeID INTEGER",
        "VendorID INTEGER", "ShipMethodID INTEGER", "OrderDate TIMESTAMP", "ShipDate TIMESTAMP",
        "SubTotal DOUBLE", "TaxAmt DOUBLE", "Freight DOUBLE", "TotalDue DOUBLE", "ModifiedDate TIMESTAMP",
    ]),
    "purchase_order_detail": ("PurchaseOrderDetail.csv", [
        "PurchaseOrderID INTEGER", "PurchaseOrderDetailID INTEGER", "DueDate TIMESTAMP", "OrderQty INTEGER",
        "ProductID INTEGER", "UnitPrice DOUBLE", "LineTotal DOUBLE", "ReceivedQty DOUBLE",
        "RejectedQty DOUBLE", "StockedQty DOUBLE", "ModifiedDate TIMESTAMP",
    ]),
}


def download(csv_name):
    dest = f"data/{csv_name}"
    if not os.path.exists(dest):
        urllib.request.urlretrieve(f"{BASE_URL}/{csv_name}", dest)
    return dest


def main():
    os.makedirs("data", exist_ok=True)
    con = duckdb.connect(DB_PATH)

    for table_name, (csv_name, columns) in TABLES.items():
        path = download(csv_name)
        col_defs = ", ".join(columns)
        col_names = ", ".join(c.split()[0] for c in columns)
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"CREATE TABLE {table_name} ({col_defs})")
        con.execute(f"""
            COPY {table_name} ({col_names}) FROM '{path}'
            (DELIMITER '\t', HEADER false, NULLSTR '', QUOTE '')
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {table_name}: {count} rows")

    con.close()
    print(f"\nBuilt {DB_PATH}")


if __name__ == "__main__":
    main()
