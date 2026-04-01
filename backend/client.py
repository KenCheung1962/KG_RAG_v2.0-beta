"""
T072 - PostgreSQL Client with Connection Pooling for pgvector Migration
Priority 1: PostgreSQL client implementation
"""

import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import backoff

logger = logging.getLogger(__name__)


class PostgresClient:
    """PostgreSQL client with connection pooling for pgvector operations."""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6432,  # PgBouncer port (use 5432 for direct PostgreSQL)
                 database: str = "kg_rag",
                 user: str = "postgres",
                 password: str = "postgres",
                 min_connections: int = 2,
                 max_connections: int = 20,
                 idle_timeout: int = 30000,
                 connection_timeout: int = 10000,
                 use_pgbouncer: bool = True):
        """
        Initialize PostgreSQL client with connection pooling.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port (6432 for PgBouncer, 5432 for direct)
            database: Database name
            user: Username
            password: Password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            idle_timeout: Connection idle timeout in milliseconds
            connection_timeout: Connection timeout in milliseconds
            use_pgbouncer: Whether connecting through PgBouncer
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.connection_timeout = connection_timeout
        self.use_pgbouncer = use_pgbouncer
        
        self.pool: Optional[asyncpg.Pool] = None
        self.is_connected = False
        
    @backoff.on_exception(backoff.expo, 
                         (asyncpg.PostgresConnectionError, 
                          asyncpg.PostgresError,
                          ConnectionError),
                         max_tries=3)
    async def connect(self):
        """Establish connection pool to PostgreSQL (or via PgBouncer)."""
        try:
            connection_type = "PgBouncer" if self.use_pgbouncer else "PostgreSQL"
            logger.info(f"Connecting to {connection_type} at {self.host}:{self.port}/{self.database}")
            
            # PgBouncer-specific settings:
            # - statement_cache_size=0: Required for transaction pooling mode
            # - server_settings with prepared_transactions off
            pool_settings = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
                "password": self.password,
                "min_size": self.min_connections,
                "max_size": self.max_connections,
                "timeout": self.connection_timeout / 1000,  # Convert to seconds
                "command_timeout": self.connection_timeout / 1000,
                "statement_cache_size": 0,  # Required for PgBouncer transaction mode
            }
            
            self.pool = await asyncpg.create_pool(**pool_settings)
            
            self.is_connected = True
            logger.info(f"{connection_type} connection pool established successfully")
            
            # Verify pgvector extension
            await self._verify_pgvector()
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.is_connected = False
            raise
    
    async def _verify_pgvector(self):
        """Verify pgvector extension is available."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                if not result:
                    logger.warning("pgvector extension not found. It will need to be created.")
                else:
                    logger.info("pgvector extension verified")
        except Exception as e:
            logger.warning(f"Could not verify pgvector extension: {e}")
    
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_connected = False
            logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def acquire_connection(self):
        """
        Acquire a connection from the pool.
        
        Usage:
            async with client.acquire_connection() as conn:
                await conn.execute(...)
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")
        
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.acquire_connection() as conn:
            result = await conn.execute(query, *args)
            return result
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Execute a query and fetch all results."""
        async with self.acquire_connection() as conn:
            result = await conn.fetch(query, *args)
            return result
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a query and fetch a single row."""
        async with self.acquire_connection() as conn:
            result = await conn.fetchrow(query, *args)
            return result
    
    async def fetchval(self, query: str, *args) -> Any:
        """Execute a query and fetch a single value."""
        async with self.acquire_connection() as conn:
            result = await conn.fetchval(query, *args)
            return result
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on PostgreSQL connection."""
        try:
            start_time = datetime.now()
            
            async with self.acquire_connection() as conn:
                # Check connection
                db_version = await conn.fetchval("SELECT version()")
                
                # Check pgvector
                has_pgvector = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                
                # Get connection stats
                connection_count = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                    self.database
                )
                
                end_time = datetime.now()
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "database_version": db_version.split()[0] if db_version else "unknown",
                    "has_pgvector": bool(has_pgvector),
                    "connection_count": connection_count,
                    "latency_ms": round(latency_ms, 2),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def create_schema(self, schema_sql: str) -> Dict[str, Any]:
        """Create database schema from SQL."""
        try:
            async with self.acquire_connection() as conn:
                # Execute schema creation in a transaction
                async with conn.transaction():
                    result = await conn.execute(schema_sql)
                
                return {
                    "success": True,
                    "message": "Schema created successfully",
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def vector_search(self, 
                           table: str,
                           vector_column: str,
                           query_vector: List[float],
                           limit: int = 10,
                           distance_metric: str = "cosine") -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Maximum results
            distance_metric: Distance metric (cosine, l2, inner_product)
            
        Returns:
            List of search results
        """
        if distance_metric == "cosine":
            # Cosine distance: 1 - cosine_similarity
            distance_expr = f"1 - ({vector_column} <=> $1::vector)"
        elif distance_metric == "l2":
            # Euclidean distance (L2)
            distance_expr = f"{vector_column} <-> $1::vector"
        elif distance_metric == "inner_product":
            # Inner product (negative for descending order)
            distance_expr = f"-({vector_column} <#> $1::vector)"
        else:
            raise ValueError(f"Unsupported distance metric: {distance_metric}")
        
        query = f"""
        SELECT *, {distance_expr} as distance
        FROM {table}
        ORDER BY {vector_column} <=> $1::vector
        LIMIT $2
        """
        
        try:
            async with self.acquire_connection() as conn:
                results = await conn.fetch(query, query_vector, limit)
                
                return [
                    {
                        **dict(record),
                        "distance": float(record["distance"])
                    }
                    for record in results
                ]
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise
    
    async def batch_insert(self, 
                          table: str,
                          records: List[Dict[str, Any]],
                          batch_size: int = 1000) -> Dict[str, Any]:
        """
        Insert records in batches.
        
        Args:
            table: Table name
            records: List of records to insert
            batch_size: Batch size for insertion
            
        Returns:
            Insertion statistics
        """
        if not records:
            return {"inserted": 0, "batches": 0}
        
        # Get column names from first record
        columns = list(records[0].keys())
        columns_str = ", ".join(columns)
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        
        query = f"""
        INSERT INTO {table} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
        """
        
        inserted_count = 0
        batch_count = 0
        
        try:
            async with self.acquire_connection() as conn:
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    
                    # Convert batch to list of tuples in correct column order
                    values = [
                        tuple(record[col] for col in columns)
                        for record in batch
                    ]
                    
                    # Execute batch insert
                    result = await conn.executemany(query, values)
                    inserted_count += int(result.split()[-1]) if result else 0
                    batch_count += 1
                    
                    logger.debug(f"Inserted batch {batch_count}: {len(batch)} records")
                
                return {
                    "success": True,
                    "inserted": inserted_count,
                    "batches": batch_count,
                    "total_records": len(records)
                }
                
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "inserted": inserted_count,
                "batches": batch_count
            }


# Global PostgreSQL client instance
_pg_client: Optional[PostgresClient] = None


async def get_postgres_client() -> PostgresClient:
    """Get PostgreSQL client instance (FastAPI dependency style)."""
    global _pg_client
    if _pg_client is None:
        raise RuntimeError("PostgreSQL client not initialized. Call init_postgres_client() first.")
    return _pg_client


async def init_postgres_client(config: Dict[str, Any]) -> PostgresClient:
    """Initialize PostgreSQL client with configuration."""
    global _pg_client
    
    if _pg_client is not None and _pg_client.is_connected:
        await _pg_client.disconnect()
    
    # Default to PgBouncer port (6432) when use_pgbouncer is True
    use_pgbouncer = config.get("use_pgbouncer", True)
    default_port = 6432 if use_pgbouncer else 5432
    
    _pg_client = PostgresClient(
        host=config.get("host", "localhost"),
        port=config.get("port", default_port),
        database=config.get("database", "kg_rag"),
        user=config.get("user", "postgres"),
        password=config.get("password", "postgres"),
        min_connections=config.get("min_connections", 2),
        max_connections=config.get("max_connections", 20),
        idle_timeout=config.get("idle_timeout", 30000),
        connection_timeout=config.get("connection_timeout", 10000),
        use_pgbouncer=use_pgbouncer
    )
    
    await _pg_client.connect()
    return _pg_client


async def close_postgres_client():
    """Close PostgreSQL client connection."""
    global _pg_client
    if _pg_client is not None:
        await _pg_client.disconnect()
        _pg_client = None