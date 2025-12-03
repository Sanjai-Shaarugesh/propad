import os
import glob


def main():
    print("=" * 70)
    print("📦 Flatpak Manifest Python Dependencies Generator")
    print("=" * 70)
    print()

    # Check for wheel files
    wheels = sorted(glob.glob("python-modules/*.whl"))

    if not wheels:
        print("❌ No wheel files found in python-modules/ directory!")
        print()
        print("📝 Steps to download dependencies:")
        print("   1. Create directory: mkdir -p python-modules")
        print("   2. Download packages:")
        print("      uv pip download --dest python-modules --prefer-binary \\")
        print("         httpx httpcore h11 h2 hpack hyperframe")
        print()
        return

    print(f"✅ Found {len(wheels)} wheel files\n")
    print("=" * 70)
    print("Copy this into your io.github.sanjai.ProPad.yaml manifest:")
    print("=" * 70)
    print()

    # Generate the manifest section
    print("  # Python dependencies for translation")
    print("  - name: python-translation-deps")
    print("    buildsystem: simple")
    print("    build-commands:")
    print(
        '      - pip3 install --verbose --exists-action=i --no-index --find-links="file://${PWD}" --prefix=${FLATPAK_DEST} --no-build-isolation \\'
    )

    # Extract package names from wheel files
    packages = []
    for wheel in wheels:
        basename = os.path.basename(wheel)
        # Extract package name (before the version number)
        package_name = basename.split("-")[0]
        if package_name not in packages:
            packages.append(package_name)

    # Print package names
    packages_str = " ".join(packages)
    print(f"        {packages_str}")

    print("    sources:")

    # Print all wheel files
    for wheel in wheels:
        print(f"      - type: file")
        print(f"        path: {wheel}")

    print()
    print("=" * 70)
    print(f"📊 Summary: {len(wheels)} dependencies, {len(packages)} unique packages")
    print("=" * 70)


if __name__ == "__main__":
    main()
