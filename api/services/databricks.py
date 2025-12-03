"""
Databricks SQL HTTP API Connector

Executes SQL queries against Databricks SQL Warehouse via REST API.
"""
import httpx
import asyncio
from typing import Any, Optional
from config import get_settings


class DatabricksConnector:
    """Async connector for Databricks SQL HTTP API."""
    
    def __init__(self):
        self.settings = get_settings()
        # Handle host with or without https:// prefix
        host = self.settings.databricks_host
        if host.startswith("https://"):
            self.base_url = host.rstrip("/")
        else:
            self.base_url = f"https://{host}"
        self.headers = {
            "Authorization": f"Bearer {self.settings.databricks_token}",
            "Content-Type": "application/json"
        }
    
    async def execute_query(
        self,
        sql: str,
        parameters: Optional[list] = None
    ) -> dict[str, Any]:
        """
        Execute a SQL query against Databricks SQL Warehouse.
        
        Args:
            sql: SQL query string
            parameters: Optional list of query parameters
            
        Returns:
            Query results as dict with 'columns' and 'data' keys
        """
        payload = {
            "warehouse_id": self.settings.databricks_warehouse_id,
            "statement": sql,
            "wait_timeout": "30s",  # Must be 5-50 seconds for Databricks SQL API
            "on_wait_timeout": "CANCEL"
        }
        
        if parameters:
            payload["parameters"] = parameters
        
        async with httpx.AsyncClient(timeout=self.settings.query_timeout_seconds + 10) as client:
            # Submit statement
            url = f"{self.base_url}/api/2.0/sql/statements"
            response = await client.post(
                url,
                headers=self.headers,
                json=payload
            )
            
            # Debug: show response if error
            if response.status_code >= 400:
                raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")
            
            response.raise_for_status()
            result = response.json()
            
            # Check status
            status = result.get("status", {}).get("state")
            statement_id = result.get("statement_id")
            
            # Poll for completion if pending
            while status in ("PENDING", "RUNNING"):
                await asyncio.sleep(0.5)
                poll_response = await client.get(
                    f"{self.base_url}/api/2.0/sql/statements/{statement_id}",
                    headers=self.headers
                )
                poll_response.raise_for_status()
                result = poll_response.json()
                status = result.get("status", {}).get("state")
            
            if status == "FAILED":
                error = result.get("status", {}).get("error", {})
                raise Exception(f"Query failed: {error.get('message', 'Unknown error')}")
            
            if status == "CANCELED":
                raise Exception("Query was canceled (timeout)")
            
            # Parse results
            manifest = result.get("manifest", {})
            columns = [col["name"] for col in manifest.get("schema", {}).get("columns", [])]
            
            # Get data from result chunks
            data_array = result.get("result", {}).get("data_array", [])
            
            # Handle pagination if needed
            chunk_info = result.get("result", {}).get("chunk_index")
            next_chunk = result.get("result", {}).get("next_chunk_internal_link")
            
            while next_chunk:
                chunk_response = await client.get(
                    f"{self.base_url}{next_chunk}",
                    headers=self.headers
                )
                chunk_response.raise_for_status()
                chunk_result = chunk_response.json()
                data_array.extend(chunk_result.get("data_array", []))
                next_chunk = chunk_result.get("next_chunk_internal_link")
            
            return {
                "columns": columns,
                "data": data_array,
                "row_count": len(data_array)
            }
    
    async def get_table_schema(self, table_name: str) -> list[dict]:
        """
        Get schema for a table.
        
        Returns list of column definitions with name, type, nullable.
        """
        sql = f"""
            DESCRIBE TABLE {self.settings.databricks_catalog}.{self.settings.databricks_schema}.{table_name}
        """
        result = await self.execute_query(sql)
        
        schema = []
        for row in result["data"]:
            schema.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] != "false" if len(row) > 2 else True
            })
        return schema
    
    async def get_row_count(self, table_name: str, where_clause: str = "") -> int:
        """Get count of rows in table with optional filter."""
        sql = f"""
            SELECT COUNT(*) as cnt 
            FROM {self.settings.databricks_catalog}.{self.settings.databricks_schema}.{table_name}
            {f'WHERE {where_clause}' if where_clause else ''}
        """
        result = await self.execute_query(sql)
        return int(result["data"][0][0]) if result["data"] else 0


# Singleton instance
_connector: Optional[DatabricksConnector] = None


def get_databricks_connector() -> DatabricksConnector:
    """Get or create Databricks connector instance."""
    global _connector
    if _connector is None:
        _connector = DatabricksConnector()
    return _connector

