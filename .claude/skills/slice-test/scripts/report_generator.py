#!/usr/bin/env python3
"""
Report Generator Module for Creality Print Testing

Generates test reports in HTML and JUnit XML formats.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
from xml.dom import minidom
from pathlib import Path

try:
    from jinja2 import Template
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


@dataclass
class TestResult:
    """Single test result"""
    test_id: str
    name: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float  # seconds
    input_file: str
    output_file: Optional[str] = None
    return_code: Optional[int] = None
    gcode_valid: Optional[bool] = None
    gcode_stats: Optional[Dict] = None
    error_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class TestSuite:
    """Collection of test results"""
    name: str
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == 'passed')

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == 'failed')

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == 'skipped')

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.status == 'error')

    @property
    def duration(self) -> float:
        return sum(r.duration for r in self.results)


# HTML Template for reports
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Creality Print Test Report</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header .timestamp { opacity: 0.8; }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .summary-card .number {
            font-size: 2.5em;
            font-weight: bold;
        }
        .summary-card .label { color: #666; }
        .summary-card.total .number { color: #333; }
        .summary-card.passed .number { color: #28a745; }
        .summary-card.failed .number { color: #dc3545; }
        .summary-card.skipped .number { color: #ffc107; }

        .results-table {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; }
        th {
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            font-weight: 600;
        }
        tr:nth-child(even) { background: #f8f9fa; }
        tr:hover { background: #e9ecef; }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        .status-passed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-skipped { background: #fff3cd; color: #856404; }
        .status-error { background: #e2e3e5; color: #383d41; }

        .tag {
            display: inline-block;
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-right: 4px;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin-top: 5px;
            font-size: 0.9em;
        }

        .gcode-stats {
            background: #e7f3ff;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 0.85em;
            margin-top: 5px;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Creality Print Test Report</h1>
            <div class="timestamp">Generated: {{ timestamp }}</div>
        </div>

        <div class="summary">
            <div class="summary-card total">
                <div class="number">{{ suite.total }}</div>
                <div class="label">Total</div>
            </div>
            <div class="summary-card passed">
                <div class="number">{{ suite.passed }}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card failed">
                <div class="number">{{ suite.failed }}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card skipped">
                <div class="number">{{ suite.skipped }}</div>
                <div class="label">Skipped</div>
            </div>
        </div>

        <div class="results-table">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Input</th>
                        <th>Tags</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {% for result in suite.results %}
                    <tr>
                        <td><code>{{ result.test_id }}</code></td>
                        <td>{{ result.name }}</td>
                        <td>
                            <span class="status-badge status-{{ result.status }}">
                                {{ result.status|upper }}
                            </span>
                        </td>
                        <td>{{ "%.2f"|format(result.duration) }}s</td>
                        <td><small>{{ result.input_file }}</small></td>
                        <td>
                            {% for tag in result.tags %}
                            <span class="tag">{{ tag }}</span>
                            {% endfor %}
                        </td>
                        <td>
                            {% if result.gcode_stats %}
                            <div class="gcode-stats">
                                Lines: {{ result.gcode_stats.get('total_lines', 'N/A') }} |
                                Layers: {{ result.gcode_stats.get('layers', 'N/A') }}
                            </div>
                            {% endif %}
                            {% if result.error_message %}
                            <div class="error-message">{{ result.error_message }}</div>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Creality Print Automated Test Suite | Total Duration: {{ "%.2f"|format(suite.duration) }}s</p>
        </div>
    </div>
</body>
</html>
'''


class ReportGenerator:
    """Generates test reports in various formats"""

    def __init__(self, output_dir: str = '.'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html(self, suite: TestSuite, filename: str = 'test_report.html') -> str:
        """Generate HTML report"""
        output_path = self.output_dir / filename

        if HAS_JINJA2:
            template = Template(HTML_TEMPLATE)
        else:
            # Fallback to simple string formatting
            template = SimpleTemplate(HTML_TEMPLATE)

        html_content = template.render(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            suite=suite
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_path)

    def generate_junit(self, suite: TestSuite, filename: str = 'junit_report.xml') -> str:
        """Generate JUnit XML report for CI integration"""
        output_path = self.output_dir / filename

        testsuites = ET.Element('testsuites')
        testsuite = ET.SubElement(testsuites, 'testsuite')
        testsuite.set('name', suite.name)
        testsuite.set('tests', str(suite.total))
        testsuite.set('failures', str(suite.failed))
        testsuite.set('errors', str(suite.errors))
        testsuite.set('skipped', str(suite.skipped))
        testsuite.set('time', f'{suite.duration:.3f}')
        testsuite.set('timestamp', suite.start_time.isoformat())

        for result in suite.results:
            testcase = ET.SubElement(testsuite, 'testcase')
            testcase.set('name', result.name)
            testcase.set('classname', result.test_id)
            testcase.set('time', f'{result.duration:.3f}')

            if result.status == 'skipped':
                skipped = ET.SubElement(testcase, 'skipped')
                skipped.set('message', result.error_message or 'Test skipped')
            elif result.status == 'failed':
                failure = ET.SubElement(testcase, 'failure')
                failure.set('message', result.error_message or 'Test failed')
                if result.stderr:
                    failure.text = result.stderr
            elif result.status == 'error':
                error = ET.SubElement(testcase, 'error')
                error.set('message', result.error_message or 'Test error')
                if result.stderr:
                    error.text = result.stderr

            # Add properties
            props = ET.SubElement(testcase, 'properties')
            ET.SubElement(props, 'property', name='input_file', value=result.input_file)
            if result.tags:
                ET.SubElement(props, 'property', name='tags', value=','.join(result.tags))
            if result.return_code is not None:
                ET.SubElement(props, 'property', name='return_code', value=str(result.return_code))

        # Pretty print XML
        xml_str = ET.tostring(testsuites, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

        return str(output_path)

    def generate_console(self, suite: TestSuite) -> str:
        """Generate console-friendly summary"""
        lines = [
            '',
            '=' * 60,
            'TEST RESULTS SUMMARY',
            '=' * 60,
            f'Total:   {suite.total}',
            f'Passed:  {suite.passed}',
            f'Failed:  {suite.failed}',
            f'Skipped: {suite.skipped}',
            f'Duration: {suite.duration:.2f}s',
            '=' * 60,
            ''
        ]

        # Show failed tests details
        if suite.failed > 0:
            lines.append('FAILED TESTS:')
            for result in suite.results:
                if result.status == 'failed':
                    lines.append(f'  - {result.test_id}: {result.name}')
                    if result.error_message:
                        lines.append(f'    Error: {result.error_message}')
            lines.append('')

        return '\n'.join(lines)


class SimpleTemplate:
    """Simple template engine fallback when Jinja2 is not available"""

    def __init__(self, template: str):
        self.template = template

    def render(self, **context) -> str:
        result = self.template

        # Handle basic variable substitution
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                result = result.replace('{{ ' + key + ' }}', str(value))
                result = result.replace('{{' + key + '}}', str(value))

        # Handle simple for loops (very basic)
        # This is a simplified implementation
        import re

        # Handle {% for item in list %}...{% endfor %}
        for match in re.finditer(r'\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}', result, re.DOTALL):
            var_name = match.group(1)
            list_name = match.group(2)
            template_content = match.group(3)

            items = context.get(list_name, [])
            replacement = ''
            for item in items:
                item_content = template_content
                if hasattr(item, '__dict__'):
                    for attr, val in vars(item).items():
                        item_content = re.sub(
                            r'\{\{\s*' + var_name + r'\.' + attr + r'\s*\}\}',
                            str(val) if val is not None else '',
                            item_content
                        )
                replacement += item_content

            result = result.replace(match.group(0), replacement)

        return result


if __name__ == '__main__':
    # Demo usage
    suite = TestSuite(name="Demo Test Suite")
    suite.results = [
        TestResult(
            test_id="DEMO-001",
            name="Basic Cube",
            status="passed",
            duration=1.5,
            input_file="cube.stl",
            tags=["smoke", "basic"]
        ),
        TestResult(
            test_id="DEMO-002",
            name="Complex Model",
            status="failed",
            duration=2.3,
            input_file="complex.stl",
            error_message="G-code validation failed",
            tags=["complex"]
        )
    ]

    generator = ReportGenerator('.')
    html_path = generator.generate_html(suite)
    print(f"HTML report generated: {html_path}")

    xml_path = generator.generate_junit(suite)
    print(f"JUnit report generated: {xml_path}")

    print(generator.generate_console(suite))
