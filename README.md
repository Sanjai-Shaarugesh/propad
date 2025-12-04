# ProPad

![ProPad Banner](https://raw.githubusercontent.com/Sanjai-Shaarugesh/ProPad/eb5948f967352492a34ee0a7b810811a4336a4c3/icons/hicolor/scalable/apps/io.github.sanjai.ProPad.svg)

A modern, feature-rich Markdown editor built with GTK 4, Python, and Libadwaita. ProPad combines a clean, intuitive interface with powerful features for an exceptional writing experience.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Made with GTK](https://img.shields.io/badge/Made%20with-GTK%204-brightgreen.svg)](https://gtk.org)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org)
[![Flathub](https://img.shields.io/badge/Download-Flathub-blue.svg)](https://flathub.org/apps/io.github.sanjai.ProPad)

## ✨ Features

### 🚀 Core Functionality
- **Live Markdown Preview** - See your formatted document in real-time as you type
- **Synchronized Scrolling** - Editor and preview scroll together seamlessly
- **GPU-Accelerated Rendering** - Smooth, fast performance even with large documents
- **File History Tracking** - Never lose your work with built-in version history

### 📝 Markdown Support
- **Extended Syntax** - Tables, task lists, strikethrough, and more
- **Mermaid Diagrams** - Create flowcharts, sequence diagrams, and more
- **LaTeX Math** - Beautiful mathematical equations and formulas
- **GitHub Alerts** - Note, Tip, Important, Warning, and Caution blocks
- **Syntax Highlighting** - Code blocks with language-specific highlighting

## ***GitHub Alerts Supported Too***

![GitHub Alerts Demo](img2.png)

> [!NOTE]
> ProPad supports all GitHub-style alert types for better documentation!

> [!TIP]
> Use keyboard shortcuts to speed up your workflow!

> [!IMPORTANT]
> Auto-save is enabled by default to protect your work.

> [!WARNING]
> Large documents may require GPU acceleration for optimal performance.

> [!CAUTION]
> Always backup important documents before major edits.

### 🎨 User Interface
- **Adaptive Design** - Works beautifully on desktop, laptop, tablet, and mobile
- **Dark Mode** - Easy on the eyes with automatic theme switching
- **Distraction-Free Mode** - Focus on writing without distractions
- **Rich Formatting Toolbar** - Quick access to common formatting options
- **File Manager Sidebar** - Organize and navigate your documents easily
-
- <img width="1920" height="1080" alt="table" src="https://github.com/user-attachments/assets/ec25f654-9e9a-4c07-bf50-eeca0d38e668" />
<img width="1075" height="756" alt="mermaid-latex" src="https://github.com/user-attachments/assets/cf2bdd34-328f-41bc-a9d4-c75a0a9d4220" />
<img width="1920" height="1080" alt="mermaid" src="https://github.com/user-attachments/assets/1c871aa8-11ed-4466-8e0e-e1f75cac2629" />
<img width="1201" height="872" alt="main-window" src="https://github.com/user-attachments/assets/a4b931f7-1dbb-4d8a-b6f8-ac702f9217dc" />
<img width="1201" height="872" alt="light" src="https://github.com/user-attachments/assets/db838193-faf2-4087-bb89-d563a177ca21" />
<img width="1920" height="1080" alt="latex" src="https://github.com/user-attachments/assets/a904d116-eed4-4789-bc4f-863066a7df11" />
<img width="1080" height="755" alt="keyboard-shorcuts" src="https://github.com/user-attachments/assets/6e90fd69-eb83-4883-a974-eaa6805cf3eb" />
<img width="1080" height="755" alt="formatting" src="https://github.com/user-attachments/assets/2a8b807e-7cc3-404b-9b4c-b5b0ab322e93" />
<img width="1080" height="755" alt="file-manager" src="https://github.com/user-attachments/assets/89ac839e-c63c-4411-866b-b2510888db53" />
<img width="1075" height="756" alt="file-history" src="https://github.com/user-attachments/assets/78dc4f1f-63ed-42eb-bce5-8fa3da2624cc" />

<img width="1201" height="872" alt="dark-mode" src="https://github.com/user-attachments/assets/071a2c55-f2e0-4c91-a32c-400e7857ad86" />
<img width="1080" height="755" alt="file-export" src="https://github.com/user-attachments/assets/e7ecb467-034f-4acf-834b-7d98fa855c31" />

- 

### 🔧 Productivity Tools
- **Advanced Search & Replace** - Find and modify text with regex support
- **Auto-Save** - Never lose your work with automatic saving
- **Export Options** - Save as HTML, PDF, and other formats
- **Template Support** - Start quickly with pre-made templates
- **Keyboard Shortcuts** - Efficient editing with customizable shortcuts

## 📦 Installation

### Flathub (Recommended)

The easiest way to install ProPad is through Flathub:

```bash
flatpak install flathub io.github.sanjai.ProPad
```

Then run:

```bash
flatpak run io.github.sanjai.ProPad
```

### Build from Source

#### Prerequisites

- Python 3.10 or higher
- GTK 4.10+
- Libadwaita 1.4+
- Just

#### Dependencies


**Fedora/RHEL:**
```bash
sudo dnf install python3 gtk4 libadwaita gtksourceview5 just python3-markdown python3-pygments
```

**Ubuntu/Debian:**
```bash
sudo apt install python3 libgtk-4-dev libadwaita-1-dev libgtksourceview-5-dev just python3-markdown python3-pygments
```

**Arch Linux:**
```bash
sudo pacman -S python gtk4 libadwaita gtksourceview5 just python-markdown python-pygments
```

#### Building

> [!NOTE]
> ```bash
> just run
> ```

1. Clone the repository:
```bash
git clone https://github.com/Sanjai-Shaarugesh/propad.git
cd propad
```

2. Build & Install with just:
```bash
  just flatpak-install
```

## 🚀 Quick Start

1. **Create a New Document** - Click the "+" button or press `Ctrl+N`
2. **Start Writing** - Type in Markdown syntax in the left pane
3. **See Live Preview** - Watch your formatted document appear on the right
4. **Save Your Work** - Press `Ctrl+S` or let auto-save handle it
5. **Export** - Use File → Export to save in various formats

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Document | `Ctrl + N` |
| Open File | `Ctrl + O` |
| Save | `Ctrl + S` |
| Save As | `Ctrl + Shift + S` |
| Export | `Ctrl + E` |
| Find | `Ctrl + F` |
| Replace | `Ctrl + H` |
| Bold | `Ctrl + B` |
| Italic | `Ctrl + I` |
| Toggle Preview | `Ctrl + P` |
| Distraction-Free | `F11` |
| Preferences | `Ctrl + ,` |

## 🎯 Use Cases

- **📚 Documentation** - Write technical docs with diagrams and math
- **📝 Note Taking** - Organize your thoughts with rich formatting
- **✍️ Blog Writing** - Draft posts with live preview
- **🎓 Academic Writing** - LaTeX math for papers and assignments
- **💻 README Files** - Create beautiful GitHub documentation
- **📋 Project Planning** - Use Mermaid for flowcharts and diagrams

## 🤝 Contributing

ProPad is a community-built open-source project! We welcome contributions of all kinds.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Areas We Need Help

- 🐛 Bug fixes and testing
- 🌍 Translations (see [po/README.md](po/README.md))
- 📖 Documentation improvements
- ✨ New features and enhancements
- 🎨 UI/UX improvements
- 📝 Code reviews

## 🐛 Reporting Issues

Found a bug? Have a feature request? Please check our [issue tracker](https://github.com/Sanjai-Shaarugesh/propad/issues) first, then:

1. Go to [Issues](https://github.com/Sanjai-Shaarugesh/propad/issues)
2. Click "New Issue"
3. Choose the appropriate template
4. Fill in the details
5. Submit!

## 📖 Documentation

- [User Guide](https://github.com/Sanjai-Shaarugesh/propad/wiki/User-Guide)
- [Keyboard Shortcuts](https://github.com/Sanjai-Shaarugesh/propad/wiki/Shortcuts)
- [Markdown Syntax](https://github.com/Sanjai-Shaarugesh/propad/wiki/Markdown-Syntax)
- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## 🌍 Translations

ProPad is available in multiple languages thanks to our amazing community translators. Want to add your language? Check out our [translation guide](po/README.md).

## 📄 License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

## 💖 Support

If you find ProPad useful, consider supporting the project:

- ⭐ Star the repository
- 🐛 Report bugs and suggest features
- 🔀 Contribute code or documentation
- 💰 [Buy me a coffee](https://buymeacoffee.com/sanjai)
- 📢 Spread the word!

## 🙏 Acknowledgments

- Built with [GTK 4](https://gtk.org) and [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- Markdown rendering powered by [Python-Markdown](https://python-markdown.github.io/)
- Syntax highlighting by [Pygments](https://pygments.org/)
- Diagram support via [Mermaid](https://mermaid.js.org/)
- Math rendering with [MathJax](https://www.mathjax.org/)
- Icons from [Lucide](https://lucide.dev/)

## 📞 Contact

- **Developer**: Sanjai Shaarugesh
- **Email**: shaarugesh6@gmail.com
- **GitHub**: [@Sanjai-Shaarugesh](https://github.com/Sanjai-Shaarugesh)
- **Discussions**: [GitHub Discussions](https://github.com/Sanjai-Shaarugesh/ProPad/discussions)

## 🗺️ Roadmap

- [ ] Plugin system for extensions
- [ ] Cloud sync support
- [ ] Collaborative editing
- [ ] Custom themes
- [ ] PDF annotation
- [ ] Voice dictation
- [ ] Mobile app (GTK for mobile)
- [ ] Git integration
- [ ] AI writing assistance

---

<div align="center">

**Made with ❤️ by the ProPad Community**

[Website](https://github.com/Sanjai-Shaarugesh/propad) • [Report Bug](https://github.com/Sanjai-Shaarugesh/ProPad/issues) • [Request Feature](https://github.com/Sanjai-Shaarugesh/ProPad/issues)

</div>
