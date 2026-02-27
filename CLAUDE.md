# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Creality Print 6.0 is an open-source 3D slicer for FDM printers. It is forked from OrcaSlicer, which itself is forked from BambuStudio/PrusaSlicer/Slic3r lineage. The project is written in C++17 and uses CMake as its build system.

## Build Commands

### Windows (Visual Studio 2019+)
```bash
# Build dependencies first (run in x64 Native Tools Command Prompt)
build_release.bat deps

# Build full project (includes deps + slicer)
build_release.bat

# Build only slicer (after deps are built)
build_release.bat slicer

# Debug build
build_release.bat debug
```

### macOS
```bash
# Full release build
./build_release_macos.sh
```

### Linux (Ubuntu)
```bash
# Update and build dependencies (requires sudo)
sudo ./BuildLinux.sh -u

# Build the slicer
./BuildLinux.sh -dsir

# Build with debug info
./BuildLinux.sh -b
```

## Build Configuration Options

Key CMake options:
- `SLIC3R_GUI=1` - Build with GUI components (default: ON)
- `SLIC3R_STATIC=1` - Static linking (default: ON for MSVC/Apple)
- `SLIC3R_BUILD_TESTS=ON` - Build unit tests
- `SLIC3R_BUILD_SANDBOXES=ON` - Build development sandboxes
- `SLIC3R_PCH=1` - Use precompiled headers (default: ON)
- `CMAKE_PREFIX_PATH` - Path to dependencies (set by build scripts)

## Code Architecture

### Core Directories

- **src/libslic3r/** - Core slicing engine library
  - `Print.cpp`, `PrintObject.cpp` - Main print processing logic
  - `GCode.cpp`, `GCodeWriter.cpp` - G-code generation
  - `Layer.cpp`, `LayerRegion.cpp` - Layer-based slicing
  - `PerimeterGenerator.cpp` - Perimeter/outline generation
  - `Fill/` - Infill pattern implementations
  - `Support/`, `TreeSupport.cpp` - Support structure generation
  - `TriangleMesh.cpp`, `TriangleMeshSlicer.cpp` - Mesh handling
  - `Config.cpp`, `PrintConfig.cpp` - Configuration system
  - `Preset.cpp`, `PresetBundle.cpp` - Printer/filament/slice presets
  - `Format/` - File I/O (STL, 3MF, AMF, OBJ, STEP)

- **src/slic3r/GUI/** - wxWidgets-based GUI
  - `GUI_App.cpp` - Main application
  - `MainFrame.cpp` - Main window
  - `GLCanvas3D.cpp`, `3DScene.cpp` - 3D viewport
  - `GCodeViewer.cpp` - G-code preview/visualization
  - `Plater.cpp` - Main plate/workspace view
  - `Tab.cpp` - Settings panels

- **src/CrealityPrint.cpp** - Application entry point

### Key Data Flow

1. **Model Loading**: Files → `Model.cpp` → `ModelObject`/`ModelVolume`
2. **Slicing**: `PrintObject::slice()` → `TriangleMeshSlicer` → `Layer` objects
3. **Path Generation**: `LayerRegion` → `PerimeterGenerator` + `Fill` patterns
4. **G-code Output**: `GCode.cpp` processes layers → `GCodeWriter` → output file

### Important Patterns

- **Config System**: Uses `DynamicPrintConfig` with options defined in `PrintConfig.cpp`
- **Presets**: Hierarchical system (default < system < user presets)
- **Threading**: Uses Intel TBB for parallelization, background slicing via `BackgroundSlicingProcess`
- **Geometry**: Clipper library for 2D polygon operations, Eigen for math

## Dependencies

Dependencies are built separately in `deps/` directory. Key dependencies:
- wxWidgets 3.x (GUI)
- Boost (filesystem, system, thread, etc.)
- Intel TBB (parallelization)
- OpenVDB (spatial data structures)
- OCCT (CAD kernel for STEP import)
- GLEW, OpenGL (3D rendering)
- NLopt (optimization)
- FFmpeg (video recording)

## Tests

Tests use Catch2 framework located in `tests/`. Build with `-DSLIC3R_BUILD_TESTS=ON`:
```bash
cmake .. -DSLIC3R_BUILD_TESTS=ON
cmake --build . --target libslic3r_tests
```

## Localization

Translation files are in `localization/i18n/`. To update translations:
```bash
# Generate pot file
run_gettext.bat  # Windows
./run_gettext.sh # Unix
```

## Code Style

- Uses clang-format with configuration in `.clang-format`
- Column limit: 140 characters
- Indent width: 4 spaces
- Brace wrapping style: Custom (after class, function, struct)
