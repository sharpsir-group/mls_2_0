# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
OData Query Parser

Converts OData query parameters to SQL clauses.
Supports: $filter, $select, $orderby, $top, $skip, $count
"""
import re
from typing import Optional
from config import get_settings


class ODataParser:
    """Parse OData query parameters into SQL components."""
    
    # OData comparison operators to SQL
    COMPARISON_OPS = {
        " eq ": " = ",
        " ne ": " != ",
        " gt ": " > ",
        " ge ": " >= ",
        " lt ": " < ",
        " le ": " <= ",
    }
    
    # OData logical operators
    LOGICAL_OPS = {
        " and ": " AND ",
        " or ": " OR ",
        " not ": " NOT ",
    }
    
    # OData functions to SQL
    FUNCTIONS = {
        r"contains\((\w+),\s*'([^']+)'\)": r"\1 LIKE '%\2%'",
        r"startswith\((\w+),\s*'([^']+)'\)": r"\1 LIKE '\2%'",
        r"endswith\((\w+),\s*'([^']+)'\)": r"\1 LIKE '%\2'",
        r"toupper\((\w+)\)": r"UPPER(\1)",
        r"tolower\((\w+)\)": r"LOWER(\1)",
        r"trim\((\w+)\)": r"TRIM(\1)",
        r"year\((\w+)\)": r"YEAR(\1)",
        r"month\((\w+)\)": r"MONTH(\1)",
        r"day\((\w+)\)": r"DAY(\1)",
    }
    
    def __init__(self):
        self.settings = get_settings()
    
    def parse_filter(self, filter_expr: Optional[str]) -> str:
        """
        Convert OData $filter to SQL WHERE clause.
        
        Examples:
            "StandardStatus eq 'Active'" -> "StandardStatus = 'Active'"
            "ListPrice gt 100000 and Bedrooms ge 3" -> "ListPrice > 100000 AND Bedrooms >= 3"
            "contains(City,'Miami')" -> "City LIKE '%Miami%'"
        """
        if not filter_expr:
            return ""
        
        sql = filter_expr
        
        # Apply function conversions first
        for pattern, replacement in self.FUNCTIONS.items():
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        
        # Apply comparison operators
        for odata_op, sql_op in self.COMPARISON_OPS.items():
            sql = sql.replace(odata_op, sql_op)
        
        # Apply logical operators
        for odata_op, sql_op in self.LOGICAL_OPS.items():
            sql = re.sub(odata_op, sql_op, sql, flags=re.IGNORECASE)
        
        # Handle null checks
        sql = re.sub(r"(\w+)\s*=\s*null", r"\1 IS NULL", sql, flags=re.IGNORECASE)
        sql = re.sub(r"(\w+)\s*!=\s*null", r"\1 IS NOT NULL", sql, flags=re.IGNORECASE)
        
        return sql
    
    def parse_select(self, select_expr: Optional[str], default_columns: list[str] = None) -> str:
        """
        Convert OData $select to SQL SELECT clause.
        
        Examples:
            "ListingKey,ListPrice,City" -> "ListingKey, ListPrice, City"
            None -> "*" (or default columns if provided)
        """
        if not select_expr:
            if default_columns:
                return ", ".join(default_columns)
            return "*"
        
        # Split and clean column names
        columns = [col.strip() for col in select_expr.split(",")]
        
        # Basic SQL injection prevention - only allow alphanumeric and underscore
        safe_columns = []
        for col in columns:
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                safe_columns.append(col)
        
        return ", ".join(safe_columns) if safe_columns else "*"
    
    def parse_orderby(self, orderby_expr: Optional[str]) -> str:
        """
        Convert OData $orderby to SQL ORDER BY clause.
        
        Examples:
            "ListPrice desc" -> "ListPrice DESC"
            "City asc,ListPrice desc" -> "City ASC, ListPrice DESC"
        """
        if not orderby_expr:
            return ""
        
        parts = []
        for item in orderby_expr.split(","):
            item = item.strip()
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(asc|desc)?$', item, re.IGNORECASE)
            if match:
                col = match.group(1)
                direction = (match.group(2) or "ASC").upper()
                parts.append(f"{col} {direction}")
        
        return ", ".join(parts)
    
    def parse_top(self, top: Optional[int]) -> int:
        """Parse $top parameter with max limit enforcement."""
        if top is None:
            return self.settings.default_page_size
        return min(max(1, top), self.settings.max_page_size)
    
    def parse_skip(self, skip: Optional[int]) -> int:
        """Parse $skip parameter."""
        if skip is None:
            return 0
        return max(0, skip)
    
    def build_query(
        self,
        table_name: str,
        filter_expr: Optional[str] = None,
        select_expr: Optional[str] = None,
        orderby_expr: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
        default_columns: list[str] = None,
        additional_where: Optional[str] = None
    ) -> str:
        """
        Build complete SQL query from OData parameters.
        
        Args:
            table_name: Table name in Databricks
            filter_expr: OData $filter expression
            select_expr: OData $select expression
            orderby_expr: OData $orderby expression
            top: OData $top value
            skip: OData $skip value
            default_columns: Default columns if no $select
            additional_where: Additional SQL WHERE condition (e.g., office filter)
        
        Returns:
            Fully formed SQL query string.
        """
        catalog = self.settings.databricks_catalog
        schema = self.settings.databricks_schema
        
        # Build SELECT clause
        select_clause = self.parse_select(select_expr, default_columns)
        
        # Build FROM clause
        from_clause = f"{catalog}.{schema}.{table_name}"
        
        # Build WHERE clause from OData filter
        odata_where = self.parse_filter(filter_expr)
        
        # Combine OData filter with additional WHERE (e.g., office filter)
        where_parts = []
        if odata_where:
            where_parts.append(f"({odata_where})")
        if additional_where:
            where_parts.append(f"({additional_where})")
        
        where_clause = " AND ".join(where_parts) if where_parts else ""
        
        # Build ORDER BY clause
        orderby_clause = self.parse_orderby(orderby_expr)
        
        # Build LIMIT/OFFSET
        limit = self.parse_top(top)
        offset = self.parse_skip(skip)
        
        # Assemble query
        sql = f"SELECT {select_clause} FROM {from_clause}"
        
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        if orderby_clause:
            sql += f" ORDER BY {orderby_clause}"
        
        sql += f" LIMIT {limit}"
        
        if offset > 0:
            sql += f" OFFSET {offset}"
        
        return sql
    
    def build_count_query(
        self,
        table_name: str,
        filter_expr: Optional[str] = None,
        additional_where: Optional[str] = None
    ) -> str:
        """
        Build COUNT query for $count parameter.
        
        Args:
            table_name: Table name in Databricks
            filter_expr: OData $filter expression
            additional_where: Additional SQL WHERE condition (e.g., office filter)
            
        Returns:
            SQL COUNT query string.
        """
        catalog = self.settings.databricks_catalog
        schema = self.settings.databricks_schema
        
        # Build WHERE clause from OData filter
        odata_where = self.parse_filter(filter_expr)
        
        # Combine OData filter with additional WHERE
        where_parts = []
        if odata_where:
            where_parts.append(f"({odata_where})")
        if additional_where:
            where_parts.append(f"({additional_where})")
        
        where_clause = " AND ".join(where_parts) if where_parts else ""
        
        sql = f"SELECT COUNT(*) as count FROM {catalog}.{schema}.{table_name}"
        
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        return sql


# Singleton instance
_parser: Optional[ODataParser] = None


def get_odata_parser() -> ODataParser:
    """Get or create OData parser instance."""
    global _parser
    if _parser is None:
        _parser = ODataParser()
    return _parser

