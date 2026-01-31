"""
Shared test configuration and fixtures.
"""
import pytest
import os

# Set test environment
os.environ['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL', 'postgresql://homeschool_user:homeschool_pass@localhost:5432/homeschool_test')
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DEBUG'] = 'True'
