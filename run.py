"""Thin entry point so process managers that need a real file path (PM2,
some systemd unit patterns) can launch the app the same way `python -m
src.api.main` does."""
import runpy

runpy.run_module("src.api.main", run_name="__main__")
