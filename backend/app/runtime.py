"""Psycopg async uses a selector loop on Windows."""
import asyncio
import selectors
import sys


def run(coroutine):
    if sys.platform == "win32":
        return asyncio.run(coroutine, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    return asyncio.run(coroutine)
