build-ui:
    blueprint-compiler compile lib/window.blp > ui/window.ui

format:build-ui
    uv run ruff format .
    
check-format:format
    uv run ruff format --check
    
run:check-format
    uv run main.py
   