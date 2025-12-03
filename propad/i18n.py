import gi
import locale
import os
import gettext

gi.require_version("Gtk", "4.0")
from gi.repository import GLib


APP_NAME = "propad"


def _get_locale_dir():
    possible_dirs = [
        "/app/share/locale",
        "/usr/share/locale",
        "/usr/local/share/locale",
    ]

    for dir_path in possible_dirs:
        locale_path = os.path.join(dir_path, APP_NAME, "LC_MESSAGES")
        if os.path.exists(locale_path):
            return dir_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dev_locale = os.path.join(base_dir, "locale")
    if os.path.exists(dev_locale):
        return dev_locale

    return dev_locale


LOCALE_DIR = _get_locale_dir()


_ = lambda s: s


def _detect_system_language():
    detected_lang = None

    for env_var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]:
        lang = os.getenv(env_var)
        if lang:
            lang_clean = lang.split(".")[0].split(":")[0]

            if "_" in lang_clean:
                detected_lang = lang_clean
            else:
                detected_lang = lang_clean.split("_")[0]
            if detected_lang and len(detected_lang) >= 2:
                print(f"🌍 Detected language from {env_var}: {detected_lang}")
                break

    if not detected_lang:
        try:
            default_locale = locale.getdefaultlocale()
            if default_locale and default_locale[0]:
                lang_str = default_locale[0]
                if "_" in lang_str:
                    detected_lang = lang_str
                else:
                    detected_lang = lang_str.split("_")[0]
                print(
                    f"🌍 Detected language from locale.getdefaultlocale(): {detected_lang}"
                )
        except Exception as e:
            print(f"⚠️ Could not get default locale: {e}")

    if not detected_lang:
        try:
            current_locale = locale.getlocale()
            if current_locale and current_locale[0]:
                lang_str = current_locale[0]
                if "_" in lang_str:
                    detected_lang = lang_str
                else:
                    detected_lang = lang_str.split("_")[0]
                print(f"🌍 Detected language from locale.getlocale(): {detected_lang}")
        except Exception as e:
            print(f"⚠️ Could not get current locale: {e}")

    if not detected_lang:
        try:
            glib_langs = GLib.get_language_names()
            if glib_langs and len(glib_langs) > 0:
                for lang in glib_langs:
                    if lang != "C" and len(lang) >= 2:
                        detected_lang = lang.split(".")[0].split("@")[0]
                        print(f"🌍 Detected language from GLib: {detected_lang}")
                        break
        except Exception as e:
            print(f"⚠️ Could not get GLib language: {e}")

    # Fallback to English
    if not detected_lang or detected_lang == "C":
        detected_lang = "en"
        print("🌍 Using fallback language: en")

    return detected_lang


def init_locale():
    """Initialize locale and gettext for translations with auto-detection."""
    global _

    print(f"📂 Locale directory: {LOCALE_DIR}")
    print(f"📦 App name: {APP_NAME}")

    # Set up locale
    try:
        locale.setlocale(locale.LC_ALL, "")
        print(f"✅ System locale set successfully")
    except Exception as e:
        print(f"⚠️ Could not set locale: {e}")
        try:
            locale.setlocale(locale.LC_ALL, "C.UTF-8")
        except:
            pass

    # Detect system language
    detected_lang = _detect_system_language()

    # Get available languages
    available_langs = get_available_languages()
    print(f"📚 Available translations: {', '.join(available_langs)}")

    lang_to_use = None

    # Try exact match first
    if detected_lang in available_langs:
        lang_to_use = detected_lang
        print(f"✅ Exact match found: {lang_to_use}")

    elif "_" in detected_lang:
        base_lang = detected_lang.split("_")[0]
        if base_lang in available_langs:
            lang_to_use = base_lang
            print(f"✅ Base language match found: {lang_to_use} (from {detected_lang})")

    else:
        for avail_lang in available_langs:
            if avail_lang.startswith(detected_lang + "_"):
                lang_to_use = avail_lang
                print(f"✅ Variant match found: {lang_to_use} (from {detected_lang})")
                break

    # Fallback to English
    if not lang_to_use:
        lang_to_use = "en"
        print(f"⚠️ Language '{detected_lang}' not available, using English")

    # Set up gettext
    try:
        # Bind text domain
        locale.bindtextdomain(APP_NAME, LOCALE_DIR)
        locale.textdomain(APP_NAME)

        if lang_to_use != "en":
            try:
                lang = gettext.translation(
                    APP_NAME,
                    localedir=LOCALE_DIR,
                    languages=[lang_to_use],
                    fallback=False,
                )
                lang.install()
                _ = lang.gettext
                print(f"✅ Translations loaded for language: {lang_to_use}")
            except FileNotFoundError:
                print(
                    f"⚠️ Translation file not found for '{lang_to_use}', using English"
                )
                lang = gettext.translation(
                    APP_NAME, localedir=LOCALE_DIR, fallback=True
                )
                lang.install()
                _ = lang.gettext
        else:
            # Use English (fallback)
            lang = gettext.translation(APP_NAME, localedir=LOCALE_DIR, fallback=True)
            lang.install()
            _ = lang.gettext
            print(f"✅ Using English (default)")

        # Store globally in builtins
        import builtins

        builtins._ = _

        print(f"🌐 Active language: {lang_to_use}")
        print(f"📍 LANGUAGE env: {os.getenv('LANGUAGE', 'not set')}")
        print(f"📍 LANG env: {os.getenv('LANG', 'not set')}")

    except Exception as e:
        print(f"⚠️ Translation setup failed: {e}")
        import traceback

        traceback.print_exc()
        # Fallback to English
        import builtins

        builtins._ = lambda s: s
        _ = lambda s: s


def get_current_locale():
    """Get current system locale."""
    try:
        current = locale.getlocale()[0]
        if current:
            return current.split("_")[0]
    except:
        pass

    # Try environment variable
    for env_var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]:
        lang = os.getenv(env_var)
        if lang:
            return lang.split("_")[0].split(".")[0].split(":")[0]

    return "en"


def get_available_languages():
    """Get list of available translations."""
    if not LOCALE_DIR or not os.path.exists(LOCALE_DIR):
        print(f"⚠️ Locale directory not found: {LOCALE_DIR}")
        return ["en"]

    languages = ["en"]
    try:
        for item in os.listdir(LOCALE_DIR):
            item_path = os.path.join(LOCALE_DIR, item)
            if os.path.isdir(item_path):
                mo_file = os.path.join(item_path, "LC_MESSAGES", f"{APP_NAME}.mo")
                if os.path.exists(mo_file):
                    lang_code = item
                    languages.append(lang_code)
                    print(f"  Found translation: {lang_code} ({mo_file})")
    except Exception as e:
        print(f"⚠️ Error scanning languages: {e}")

    return sorted(set(languages))


def set_language(lang_code):
    """Manually set application language."""
    global _

    try:
        lang = gettext.translation(
            APP_NAME, localedir=LOCALE_DIR, languages=[lang_code], fallback=True
        )
        lang.install()

        import builtins

        builtins._ = lang.gettext
        _ = lang.gettext

        print(f"✅ Language manually set to: {lang_code}")
        return True
    except Exception as e:
        print(f"❌ Could not set language to {lang_code}: {e}")
        return False


# Language names
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "zh_CN": "中文 (简体)",
    "zh_TW": "中文 (繁體)",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
    "hi": "हिन्दी",
    "bn": "বাংলা",
    "gu": "ગુજરાતી",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "mr": "मराठी",
    "tr": "Türkçe",
    "pl": "Polski",
    "uk": "Українська",
    "vi": "Tiếng Việt",
    "th": "ไทย",
    "id": "Bahasa Indonesia",
    "nl": "Nederlands",
    "sv": "Svenska",
    "da": "Dansk",
    "fi": "Suomi",
    "no": "Norsk",
    "cs": "Čeština",
    "el": "Ελληνικά",
    "he": "עברית",
    "fa": "فارسی",
    "ur": "اردو",
}


def get_language_name(code):
    """Get display name for language code."""
    return LANGUAGE_NAMES.get(code, code.upper())


def ngettext(singular, plural, n):
    """Handle plural forms for translations."""
    try:
        import builtins

        if hasattr(builtins, "_"):
            # Get the translation object
            lang = gettext.translation(APP_NAME, localedir=LOCALE_DIR, fallback=True)
            return lang.ngettext(singular, plural, n)
    except:
        pass

    # Fallback to simple English pluralization
    return singular if n == 1 else plural
