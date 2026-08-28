"""Supabase client / Postgres façade smoke tests (no live credentials required)."""
from __future__ import annotations

import os
import unittest
from unittest import mock


class TestSupabaseClientFallback(unittest.TestCase):
    def setUp(self):
        # Isolate from developer .env for these cases
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "",
                "SUPABASE_KEY": "",
                "SUPABASE_SERVICE_KEY": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
                "SUPABASE_ANON_KEY": "",
                "SUPABASE_DB_URL": "",
                "USE_SQLITE": "1",
                "STORAGE_BACKEND": "",
            },
            clear=False,
        )
        self._env_patch.start()
        from database import supabase_client as sc

        sc.reset_clients()
        self.sc = sc

    def tearDown(self):
        self.sc.reset_clients()
        self._env_patch.stop()

    def test_api_not_configured_when_empty(self):
        self.assertFalse(self.sc.api_configured())
        self.assertFalse(self.sc.postgres_configured())

    def test_get_client_raises_without_credentials(self):
        with self.assertRaises(RuntimeError):
            self.sc.get_supabase_client()

    def test_storage_bucket_default(self):
        self.assertEqual(self.sc.storage_bucket(), "property-media")

    def test_adapt_sql_postgres_coalesce(self):
        sql = "SELECT IFNULL(a, 0) FROM t WHERE x=%s"
        out = self.sc.adapt_sql_postgres(sql)
        self.assertIn("COALESCE(", out)
        self.assertIn("%s", out)

    def test_public_storage_url_without_base(self):
        url = self.sc.public_storage_url("properties/1/images/a.jpg")
        self.assertEqual(url, "properties/1/images/a.jpg")


class TestSupabaseClientInit(unittest.TestCase):
    def tearDown(self):
        from database import supabase_client as sc

        sc.reset_clients()

    def test_get_client_with_mocked_create(self):
        fake = object()
        with mock.patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "test-key",
                "USE_SQLITE": "1",
            },
            clear=False,
        ):
            from database import supabase_client as sc

            sc.reset_clients()
            with mock.patch("supabase.create_client", return_value=fake) as create:
                client = sc.get_supabase_client()
                self.assertIs(client, fake)
                create.assert_called_once_with(
                    "https://example.supabase.co", "test-key"
                )
                # singleton
                self.assertIs(sc.get_supabase_client(), fake)

    def test_postgres_configured_requires_url_and_sqlite_off(self):
        with mock.patch.dict(
            os.environ,
            {
                "SUPABASE_DB_URL": "postgresql://postgres:x@db.example.supabase.co:5432/postgres",
                "USE_SQLITE": "1",
            },
            clear=False,
        ):
            from database import supabase_client as sc

            self.assertFalse(sc.postgres_configured())

        with mock.patch.dict(
            os.environ,
            {
                "SUPABASE_DB_URL": "postgresql://postgres:x@db.example.supabase.co:5432/postgres",
                "USE_SQLITE": "0",
            },
            clear=False,
        ):
            from database import supabase_client as sc

            self.assertTrue(sc.postgres_configured())


class TestDbFacadeRouting(unittest.TestCase):
    def test_use_postgres_false_when_sqlite_forced(self):
        with mock.patch.dict(
            os.environ,
            {
                "SUPABASE_DB_URL": "postgresql://postgres:x@localhost:5432/postgres",
                "USE_SQLITE": "1",
            },
            clear=False,
        ):
            from database import db as dbmod

            # Reset cached sqlite flag
            dbmod._using_sqlite = None
            self.assertFalse(dbmod.use_postgres())
            self.assertTrue(dbmod.use_sqlite())
            dbmod._using_sqlite = None

    def test_skip_runtime_ddl_when_postgres(self):
        with mock.patch.dict(
            os.environ,
            {
                "SUPABASE_DB_URL": "postgresql://postgres:x@localhost:5432/postgres",
                "USE_SQLITE": "0",
            },
            clear=False,
        ):
            from database import db as dbmod

            dbmod._using_sqlite = None
            self.assertTrue(dbmod.skip_runtime_ddl())
            dbmod._using_sqlite = None


class TestStorageBackendPreference(unittest.TestCase):
    def test_local_preference_skips_remote_flags(self):
        with mock.patch.dict(os.environ, {"STORAGE_BACKEND": "local"}, clear=False):
            from services import storage_service as ss

            self.assertEqual(ss.storage_backend_preference(), "local")
            self.assertFalse(ss._use_supabase_storage())


if __name__ == "__main__":
    unittest.main()
