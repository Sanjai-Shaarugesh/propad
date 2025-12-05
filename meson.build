project('propad', 'python')

py = import('python').find_installation('python3')

# Install Python sources
py.install_sources('propad', subdir: 'propad')

# Install main.py
install_data('main.py',
  install_dir: join_paths(get_option('datadir'), 'propad'))

# Install all .ui files
install_data(
  files([
    'ui/window.ui',
    'ui/shortcuts_window.ui',
    'ui/sidebar.ui',
    'ui/webview.ui',
    'ui/export_dialog.ui',
    'ui/search_replace.ui',
    'ui/formatting_toolbar.ui',
    'ui/file_manager.ui'
  ]),
  install_dir: join_paths(get_option('datadir'), 'propad', 'ui')
)
