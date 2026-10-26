"""Runs before the tests: use harmless fake settings so tests never touch real services."""
import os

os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "sb_secret_test"
os.environ["API_KEY"] = "test-key"
os.environ["MAX_UPLOAD_MB"] = "5"
