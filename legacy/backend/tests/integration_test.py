"""
Integration Tests for T058 RAG Web UI
Tests connectivity and functionality with T036 FastAPI backend

Usage:
    python tests/integration_test.py --host http://localhost:8000
"""

import asyncio
import httpx
import sys
from typing import Optional


class IntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    async def test_health_check(self) -> bool:
        """Test if T036 API is healthy."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            if resp.status_code == 200:
                self.results.append(("✅ Health check", "PASS"))
                return True
            else:
                self.results.append(("❌ Health check", f"FAIL: {resp.status_code}"))
                return False
        except Exception as e:
            self.results.append(("❌ Health check", f"ERROR: {str(e)}"))
            return False

    async def test_query_endpoint(self) -> bool:
        """Test query endpoint with a simple query."""
        try:
            payload = {
                "query": "What is artificial intelligence?",
                "mode": "hybrid",
                "top_k": 3
            }
            resp = httpx.post(
                f"{self.base_url}/api/v1/query",
                json=payload,
                timeout=30.0
            )
            if resp.status_code == 200:
                data = resp.json()
                self.results.append(("✅ Query endpoint", f"PASS: Response received"))
                return True
            else:
                self.results.append(("❌ Query endpoint", f"FAIL: {resp.status_code}"))
                return False
        except Exception as e:
            self.results.append(("❌ Query endpoint", f"ERROR: {str(e)}"))
            return False

    async def test_index_endpoint(self) -> bool:
        """Test document indexing endpoint."""
        try:
            # Create a test text file
            test_content = b"Test document for integration testing"
            files = {"file": ("test.txt", test_content, "text/plain")}
            resp = httpx.post(
                f"{self.base_url}/api/v1/index",
                files=files,
                timeout=60.0
            )
            if resp.status_code in [200, 201]:
                self.results.append(("✅ Index endpoint", "PASS: Document indexed"))
                return True
            else:
                self.results.append(("❌ Index endpoint", f"FAIL: {resp.status_code}"))
                return False
        except Exception as e:
            self.results.append(("❌ Index endpoint", f"ERROR: {str(e)}"))
            return False

    async def test_stats_endpoint(self) -> bool:
        """Test stats endpoint."""
        try:
            resp = httpx.get(f"{self.base_url}/api/v1/stats", timeout=5.0)
            if resp.status_code == 200:
                self.results.append(("✅ Stats endpoint", "PASS"))
                return True
            else:
                self.results.append(("❌ Stats endpoint", f"FAIL: {resp.status_code}"))
                return False
        except Exception as e:
            self.results.append(("❌ Stats endpoint", f"ERROR: {str(e)}"))
            return False

    async def run_all_tests(self) -> dict:
        """Run all integration tests."""
        print("=" * 60)
        print("T058 Integration Tests")
        print(f"Target: {self.base_url}")
        print("=" * 60)

        # Run tests
        await self.test_health_check()
        await self.test_stats_endpoint()
        await self.test_query_endpoint()
        await self.test_index_endpoint()

        # Print results
        print("\n📊 Test Results:")
        print("-" * 40)
        for test, result in self.results:
            print(f"{test}: {result}")

        passed = sum(1 for _, r in self.results if "PASS" in r)
        total = len(self.results)

        print("-" * 40)
        print(f"✅ Passed: {passed}/{total}")

        return {
            "passed": passed,
            "total": total,
            "results": self.results
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="T058 Integration Tests")
    parser.add_argument("--host", default="http://localhost:8000",
                       help="T036 API base URL")
    args = parser.parse_args()

    tester = IntegrationTester(args.host)
    results = await tester.run_all_tests()

    sys.exit(0 if results["passed"] == results["total"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
