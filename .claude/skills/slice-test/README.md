# Creality Print Slice Test Skill

Automated testing suite for Creality Print, supporting both **CLI** and **GUI** testing modes.

## Features

- **CLI Testing**: Fast command-line slicing validation
- **GUI Testing**: Full UI automation with Page Object Model
- **G-code Validation**: Verify generated G-code structure and content
- **Multiple Report Formats**: HTML, JUnit XML, Console
- **Screenshot Capture**: Automatic screenshots for GUI test debugging

---

## Quick Start

### CLI Testing (Fast)

```bash
# Run all smoke tests
python .claude/skills/slice-test/scripts/run_tests.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --tags smoke

# Run specific test case
python .claude/skills/slice-test/scripts/run_tests.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --test-case .claude/skills/slice-test/config/test_cases/basic_slice.yaml

# Run with HTML report
python .claude/skills/slice-test/scripts/run_tests.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --tags basic \
  --report html
```

### GUI Testing (Full UI Automation)

```bash
# Run GUI smoke tests
python .claude/skills/slice-test/scripts/gui_test_runner.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --test-case .claude/skills/slice-test/config/test_cases/gui_basic.yaml \
  --tags smoke

# Run with verbose output and slow motion (for demo)
python .claude/skills/slice-test/scripts/gui_test_runner.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --tags workflow \
  --verbose \
  --slow-motion 0.5

# Use pyautogui backend only
python .claude/skills/slice-test/scripts/gui_test_runner.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --backend pyautogui
```

### Complete Slice Workflow Test

```bash
# Run the complete slice workflow test
# This tests: Import -> Set Layer Height -> Slice -> Verify G-code
python .claude/skills/slice-test/scripts/run_workflow_test.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --test-file "C:\\TestData\\cube.stl" \
  --verbose

# Run with slow motion for demo
python .claude/skills/slice-test/scripts/run_workflow_test.py \
  --cli "build_unified/package/CrealityPrint.exe" \
  --slow-motion 0.5
```

---

## CLI Commands Reference

### Basic Slicing
```bash
CrealityPrint input.stl --slice --outputdir "output/"
```

### Slicing with Configuration
```bash
CrealityPrint input.3mf --slice --load_settings "config.json" --outputdir "output/"
```

---

## Test Case Format

### CLI Test Cases (YAML)

```yaml
test_cases:
  - id: "TC001"
    name: "Basic Cube Slice"
    input: "tests/data/test_stl/ASCII/20mmbox-LF.stl"
    tags: ["smoke", "basic", "stl"]
    timeout: 120
    expected:
      return_code: 0
      gcode_exists: true
      gcode_keywords:
        - "G28"      # Home
        - "G1"       # Movement
        - "M104"     # Temperature
      min_lines: 100
      max_lines: 100000
```

### GUI Test Cases (YAML)

```yaml
gui_test_cases:
  - id: "GUI-001"
    name: "Basic Workflow"
    description: "Load model and slice"
    tags: ["smoke", "workflow", "gui"]
    timeout: 180
    steps:
      - action: start_app
        params: {}
      - action: add_model
        params:
          file: "tests/data/20mm_cube.obj"
      - action: click_slice
        params: {}
      - action: wait_for_slice
        params:
          timeout: 120
      - action: switch_to_preview
        params: {}
      - action: close_app
        params: {}
```

### Available GUI Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `start_app` | Start the application | - |
| `close_app` | Close the application | - |
| `wait` | Wait for specified seconds | `seconds: int` |
| `click` | Click UI element | `element, page` |
| `type_text` | Type text into element | `element, text, page` |
| `press_key` | Press a keyboard key | `key: str` |
| `hotkey` | Press keyboard shortcut | `keys: [str]` |
| `add_model` | Add model file | `file: path` |
| `remove_model` | Remove model | `index: int` |
| `clear_plate` | Clear all models | - |
| `click_slice` | Click Slice button | - |
| `wait_for_slice` | Wait for slicing to complete | `timeout: int` |
| `cancel_slice` | Cancel slicing | - |
| `switch_to_preview` | Switch to Preview tab | - |
| `switch_to_prepare` | Switch to Prepare tab | - |
| `save_project` | Save project file | `file: path` |
| `export_gcode` | Export G-code | `file: path` |
| `set_setting` | Set print setting | `setting, value` |
| `select_profile` | Select profile | `type, name` |
| `verify_visible` | Verify element visible | `element, page` |
| `verify_enabled` | Verify element enabled | `element, page` |
| `verify_text` | Verify element text | `element, text, page` |
| `screenshot` | Take screenshot | `name: str` |

---

## Error Codes

| Code | Constant | Description |
|------|----------|-------------|
| 0 | CLI_SUCCESS | Success |
| -2 | CLI_INVALID_PARAMS | Invalid parameters |
| -3 | CLI_FILE_NOTFOUND | Input file not found |
| -100 | CLI_SLICING_ERROR | Slicing failed |

---

## Directory Structure

```
slice-test/
├── skill.json              # Skill metadata
├── README.md               # This file
├── config/
│   ├── test_cases/         # Test case definitions
│   │   ├── basic_slice.yaml      # CLI basic tests
│   │   ├── complex_models.yaml   # CLI complex tests
│   │   ├── edge_cases.yaml       # CLI edge cases
│   │   ├── gui_basic.yaml        # GUI basic tests
│   │   └── gui_advanced.yaml     # GUI advanced tests
│   └── profiles/           # Test configurations
│       └── default_profile.json
└── scripts/
    ├── run_tests.py        # CLI test runner
    ├── gui_test_runner.py  # GUI test runner
    ├── gui_automation.py   # GUI automation framework
    ├── page_objects.py     # Page Object Model classes
    ├── gcode_validator.py  # G-code validation
    └── report_generator.py # Report generation
```

---

## Dependencies

### Core (Required)
```bash
pip install pyyaml jinja2
```

### GUI Automation (Optional)
```bash
# Windows native UI automation (recommended)
pip install pywinauto

# Cross-platform visual automation
pip install pyautogui pillow
```

---

## Test Tags

### CLI Tests
- `smoke` - Quick validation tests
- `basic` - Basic functionality tests
- `stl` - STL file format tests
- `obj` - OBJ file format tests
- `3mf` - 3MF file format tests
- `regression` - Full regression suite
- `complex` - Complex model tests
- `edge` - Edge case tests

### GUI Tests
- `lifecycle` - Application startup/shutdown
- `model` - Model loading tests
- `navigation` - Tab navigation tests
- `slice` - Slicing workflow tests
- `settings` - Settings panel tests
- `keyboard` - Keyboard shortcut tests
- `workflow` - Complete workflow tests
- `error` - Error handling tests
- `performance` - Performance tests
- `viewport` - 3D viewport tests
- `accessibility` - Accessibility tests

---

## Automation Backends

### pywinauto (Windows Native)
- Best for Windows applications
- Can identify controls by name, class, automation ID
- More reliable for UI interaction

### pyautogui (Visual)
- Cross-platform support
- Image-based element recognition
- Works when native automation fails

### Hybrid (Recommended)
- Tries pywinauto first
- Falls back to pyautogui
- Best of both worlds

---

## Troubleshooting

### "Application not found"
Ensure the CLI path is correct and the executable exists.

### "pywinauto not available"
Install pywinauto: `pip install pywinauto`

### GUI tests fail randomly
- Increase `--slow-motion` value
- Check if application windows are being blocked by other windows
- Ensure screen resolution is consistent

### Screenshots not captured
- Check `output/screenshots/` directory exists
- Verify `save_screenshots: true` in config
