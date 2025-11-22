build-ui:
    blueprint-compiler compile lib/window.blp > ui/window.ui
    blueprint-compiler compile lib/sidebar.blp > ui/sidebar.ui
    blueprint-compiler compile lib/webview.blp > ui/webview.ui
    blueprint-compiler compile lib/export_dialog.blp > ui/export_dialog.ui
    blueprint-compiler compile lib/search_replace.blp > ui/search_replace.ui
    blueprint-compiler compile lib/formatting_toolbar.blp > ui/formatting_toolbar.ui
    blueprint-compiler compile lib/file_manager.blp > ui/file_manager.ui

format:build-ui
    uv run ruff format .
    
check-format:format
    uv run ruff format --check
    
run:check-format
    uv run main.py
   