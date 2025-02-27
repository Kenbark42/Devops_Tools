"""
DevOps Toolkit - Visualization Module

This module provides tools for visualizing monitoring data through
various chart types, dashboards, and export formats.
"""
import os
import json
import csv
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
import base64
from io import BytesIO
import webbrowser
import math

# Local imports
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger
from devops_toolkit.tools import monitoring

# Initialize logger
logger = get_logger(__name__)


class VisualizationError(Exception):
    """Raised when visualization operations encounter an error."""
    pass


class ChartData:
    """
    Class to prepare and format data for charts.
    """

    @staticmethod
    def format_time_series(
        data: List[Dict[str, Any]],
        time_field: str,
        value_fields: List[str],
        time_format: str = "%Y-%m-%dT%H:%M:%S"
    ) -> Dict[str, Any]:
        """
        Format time series data for charts.

        Args:
            data: List of data points
            time_field: Field name for timestamp
            value_fields: List of fields to extract values from
            time_format: Format for parsing time strings (if not already datetime objects)

        Returns:
            Dict with formatted data for charting

        Raises:
            VisualizationError: If data cannot be formatted
        """
        try:
            series = {field: [] for field in value_fields}
            times = []

            for item in data:
                # Extract timestamp
                if time_field in item:
                    time_value = item[time_field]
                    if isinstance(time_value, str):
                        # Parse string to datetime
                        try:
                            time_obj = datetime.strptime(time_value, time_format)
                        except ValueError:
                            # Try different formats if the specified one fails
                            try:
                                # ISO format with timezone
                                time_obj = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                            except ValueError:
                                # Fallback to just the date part
                                time_obj = datetime.strptime(time_value.split('T')[0], "%Y-%m-%d")
                    elif isinstance(time_value, (int, float)):
                        # Assume Unix timestamp
                        time_obj = datetime.fromtimestamp(time_value)
                    elif isinstance(time_value, datetime):
                        # Already a datetime object
                        time_obj = time_value
                    else:
                        # Unsupported type
                        raise VisualizationError(f"Unsupported timestamp type for {time_value}")

                    times.append(time_obj)

                    # Extract values for each field
                    for field in value_fields:
                        if field in item:
                            # Get value
                            value = item[field]
                            
                            # Handle nested dictionaries
                            if isinstance(value, dict) and "value" in value:
                                value = value["value"]
                            
                            # Try to convert to float
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                # Keep as is if cannot convert
                                pass
                            
                            series[field].append(value)
                        else:
                            # Use None for missing values
                            series[field].append(None)

            return {
                "times": times,
                "series": series
            }
        
        except Exception as e:
            raise VisualizationError(f"Error formatting time series data: {str(e)}")

    @staticmethod
    def format_aggregated(
        data: List[Dict[str, Any]],
        category_field: str,
        value_field: str,
        aggregation: str = "sum"
    ) -> Dict[str, Any]:
        """
        Format aggregated data for charts.

        Args:
            data: List of data points
            category_field: Field name for categories
            value_field: Field name for values
            aggregation: Aggregation function (sum, avg, min, max, count)

        Returns:
            Dict with formatted data for charting

        Raises:
            VisualizationError: If data cannot be formatted
        """
        try:
            # Group by category
            categories = {}
            
            for item in data:
                if category_field in item and value_field in item:
                    category = item[category_field]
                    
                    # Get value
                    value = item[value_field]
                    
                    # Handle nested dictionaries
                    if isinstance(value, dict) and "value" in value:
                        value = value["value"]
                    
                    # Try to convert to float
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        # Skip if cannot convert
                        continue
                    
                    # Add to category group
                    if category not in categories:
                        categories[category] = []
                    
                    categories[category].append(value)
            
            # Apply aggregation function
            result = {}
            
            for category, values in categories.items():
                if aggregation == "sum":
                    result[category] = sum(values)
                elif aggregation == "avg":
                    result[category] = sum(values) / len(values) if values else 0
                elif aggregation == "min":
                    result[category] = min(values) if values else 0
                elif aggregation == "max":
                    result[category] = max(values) if values else 0
                elif aggregation == "count":
                    result[category] = len(values)
                else:
                    raise VisualizationError(f"Unsupported aggregation function: {aggregation}")
            
            return {
                "categories": list(result.keys()),
                "values": list(result.values())
            }
        
        except Exception as e:
            raise VisualizationError(f"Error formatting aggregated data: {str(e)}")

    @staticmethod
    def generate_sample_data(
        start_time: Optional[datetime] = None,
        duration: timedelta = timedelta(hours=24),
        interval: timedelta = timedelta(minutes=5),
        metrics: List[str] = ["cpu", "memory", "requests"],
        base_values: Dict[str, float] = None,
        variance: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Generate sample monitoring data for testing visualizations.

        Args:
            start_time: Start time for data (defaults to 24 hours ago)
            duration: Total duration of data
            interval: Interval between data points
            metrics: List of metric names to generate
            base_values: Base values for metrics (defaults to reasonable values)
            variance: Random variance factor for metrics

        Returns:
            List of generated data points
        """
        import random
        
        # Default start time is 24 hours ago
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        
        # Default base values
        if base_values is None:
            base_values = {
                "cpu": 20.0,  # 20% CPU usage
                "memory": 40.0,  # 40% memory usage
                "requests": 100.0,  # 100 requests per interval
                "latency": 50.0,  # 50ms latency
                "errors": 0.5  # 0.5% error rate
            }
        
        # Generate data points
        data = []
        current_time = start_time
        end_time = start_time + duration
        
        # Add some statefulness to simulate trends
        current_values = {k: v for k, v in base_values.items()}
        trends = {k: random.uniform(-0.1, 0.1) for k in base_values}
        
        while current_time <= end_time:
            data_point = {
                "timestamp": current_time.isoformat() + "Z"
            }
            
            # Generate values for each metric
            for metric in metrics:
                if metric in base_values:
                    # Update current value based on trend
                    current_values[metric] += trends[metric]
                    
                    # Apply random variance
                    value = current_values[metric] * (1 + random.uniform(-variance, variance))
                    
                    # Ensure value stays reasonable
                    if metric in ["cpu", "memory"]:
                        value = max(0, min(100, value))  # 0-100%
                    elif metric in ["requests"]:
                        value = max(0, value)  # Positive only
                    elif metric in ["errors"]:
                        value = max(0, min(10, value))  # 0-10%
                    
                    # Occasionally introduce spikes
                    if random.random() < 0.05:
                        value *= 1.5
                    
                    # Format the value
                    data_point[metric] = round(value, 2)
                    
                    # Occasionally change trend direction
                    if random.random() < 0.1:
                        trends[metric] = random.uniform(-0.1, 0.1)
            
            data.append(data_point)
            current_time += interval
        
        return data


class Chart:
    """
    Base class for all chart types.
    """

    def __init__(self, title: str, data: Dict[str, Any]):
        """
        Initialize chart.

        Args:
            title: Chart title
            data: Data for the chart
        """
        self.title = title
        self.data = data
        self.width = 800
        self.height = 400
        self.colors = [
            "#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f",
            "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"
        ]
        self.background_color = "#ffffff"
        self.grid_color = "#e0e0e0"
        self.text_color = "#333333"

    def generate_html(self) -> str:
        """
        Generate HTML for the chart.

        Returns:
            HTML string for the chart
        """
        raise NotImplementedError("Subclasses must implement generate_html()")

    def to_html_file(self, output_path: Optional[str] = None) -> str:
        """
        Save chart as HTML file.

        Args:
            output_path: Path to save HTML file (optional)
                If not provided, will use a temporary file

        Returns:
            Path to saved HTML file
        """
        html = self.generate_html()
        
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".html")
            os.close(fd)
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        return output_path

    def show(self) -> None:
        """
        Open chart in web browser.
        """
        html_file = self.to_html_file()
        webbrowser.open(f"file://{html_file}")

    def to_json(self) -> Dict[str, Any]:
        """
        Export chart configuration as JSON.

        Returns:
            Dict with chart configuration
        """
        return {
            "type": self.__class__.__name__,
            "title": self.title,
            "data": self.data,
            "width": self.width,
            "height": self.height,
            "colors": self.colors,
            "background_color": self.background_color,
            "grid_color": self.grid_color,
            "text_color": self.text_color
        }


class LineChart(Chart):
    """
    Line chart for time series data.
    """

    def __init__(self, title: str, data: Dict[str, Any], x_label: str = "Time", y_label: str = "Value"):
        """
        Initialize line chart.

        Args:
            title: Chart title
            data: Data for the chart (must have 'times' and 'series' keys)
            x_label: Label for X axis
            y_label: Label for Y axis
        """
        super().__init__(title, data)
        self.x_label = x_label
        self.y_label = y_label
        self.show_points = True
        self.line_width = 2
        self.point_radius = 3
        self.smoothing = False

    def generate_html(self) -> str:
        """
        Generate HTML for the line chart using Chart.js.

        Returns:
            HTML string for the chart
        """
        # Extract data
        times = self.data.get("times", [])
        series = self.data.get("series", {})
        
        # Format timestamps for Chart.js
        formatted_times = []
        for t in times:
            if isinstance(t, datetime):
                formatted_times.append(t.isoformat())
            else:
                formatted_times.append(str(t))
        
        # Create dataset for each series
        datasets = []
        color_idx = 0
        
        for name, values in series.items():
            color = self.colors[color_idx % len(self.colors)]
            color_idx += 1
            
            datasets.append({
                "label": name,
                "data": values,
                "borderColor": color,
                "backgroundColor": color + "33",  # Add transparency
                "borderWidth": self.line_width,
                "pointRadius": self.point_radius if self.show_points else 0,
                "tension": 0.4 if self.smoothing else 0
            })
        
        # Create chart config
        config = {
            "type": "line",
            "data": {
                "labels": formatted_times,
                "datasets": datasets
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": self.title,
                        "color": self.text_color,
                        "font": {
                            "size": 16
                        }
                    },
                    "legend": {
                        "position": "top",
                        "labels": {
                            "color": self.text_color
                        }
                    },
                    "tooltip": {
                        "mode": "index",
                        "intersect": False
                    }
                },
                "scales": {
                    "x": {
                        "type": "time",
                        "title": {
                            "display": True,
                            "text": self.x_label,
                            "color": self.text_color
                        },
                        "ticks": {
                            "color": self.text_color
                        },
                        "grid": {
                            "color": self.grid_color
                        }
                    },
                    "y": {
                        "title": {
                            "display": True,
                            "text": self.y_label,
                            "color": self.text_color
                        },
                        "ticks": {
                            "color": self.text_color
                        },
                        "grid": {
                            "color": self.grid_color
                        }
                    }
                }
            }
        }
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.0.0/dist/chart.umd.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/luxon@3.0.1/build/global/luxon.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1.2.0/dist/chartjs-adapter-luxon.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: {self.background_color}; }}
                .chart-container {{ width: {self.width}px; height: {self.height}px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <script>
                const config = {json.dumps(config)};
                new Chart(document.getElementById('chart'), config);
            </script>
        </body>
        </html>
        """
        
        return html


class BarChart(Chart):
    """
    Bar chart for categorical data.
    """

    def __init__(self, title: str, data: Dict[str, Any], x_label: str = "Category", y_label: str = "Value"):
        """
        Initialize bar chart.

        Args:
            title: Chart title
            data: Data for the chart (must have 'categories' and 'values' keys)
            x_label: Label for X axis
            y_label: Label for Y axis
        """
        super().__init__(title, data)
        self.x_label = x_label
        self.y_label = y_label
        self.horizontal = False
        self.bar_width = 0.8
        self.show_values = True

    def generate_html(self) -> str:
        """
        Generate HTML for the bar chart using Chart.js.

        Returns:
            HTML string for the chart
        """
        # Extract data
        categories = self.data.get("categories", [])
        values = self.data.get("values", [])
        
        # Get color for bars
        bar_color = self.colors[0]
        
        # Create dataset
        dataset = {
            "label": self.y_label,
            "data": values,
            "backgroundColor": [self.colors[i % len(self.colors)] for i in range(len(values))],
            "borderColor": [color.replace("33", "") for color in [self.colors[i % len(self.colors)] for i in range(len(values))]],
            "borderWidth": 1
        }
        
        # Create chart config
        config = {
            "type": "bar" if not self.horizontal else "horizontalBar",
            "data": {
                "labels": categories,
                "datasets": [dataset]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": self.title,
                        "color": self.text_color,
                        "font": {
                            "size": 16
                        }
                    },
                    "legend": {
                        "display": False
                    },
                    "tooltip": {
                        "mode": "index",
                        "intersect": False
                    }
                },
                "scales": {
                    "x": {
                        "title": {
                            "display": True,
                            "text": self.x_label,
                            "color": self.text_color
                        },
                        "ticks": {
                            "color": self.text_color
                        },
                        "grid": {
                            "color": self.grid_color
                        }
                    },
                    "y": {
                        "title": {
                            "display": True,
                            "text": self.y_label,
                            "color": self.text_color
                        },
                        "ticks": {
                            "color": self.text_color
                        },
                        "grid": {
                            "color": self.grid_color
                        }
                    }
                }
            }
        }
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.0.0/dist/chart.umd.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: {self.background_color}; }}
                .chart-container {{ width: {self.width}px; height: {self.height}px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <script>
                const config = {json.dumps(config)};
                new Chart(document.getElementById('chart'), config);
            </script>
        </body>
        </html>
        """
        
        return html


class PieChart(Chart):
    """
    Pie chart for categorical data.
    """

    def __init__(self, title: str, data: Dict[str, Any]):
        """
        Initialize pie chart.

        Args:
            title: Chart title
            data: Data for the chart (must have 'categories' and 'values' keys)
        """
        super().__init__(title, data)
        self.donut = False
        self.show_legend = True
        self.show_percentages = True

    def generate_html(self) -> str:
        """
        Generate HTML for the pie chart using Chart.js.

        Returns:
            HTML string for the chart
        """
        # Extract data
        categories = self.data.get("categories", [])
        values = self.data.get("values", [])
        
        # Calculate percentages
        total = sum(values)
        percentages = [round(value / total * 100, 1) if total > 0 else 0 for value in values]
        
        # Create dataset
        dataset = {
            "data": values,
            "backgroundColor": [self.colors[i % len(self.colors)] for i in range(len(values))],
            "borderColor": self.background_color,
            "borderWidth": 2
        }
        
        # Create chart config
        config = {
            "type": "pie",
            "data": {
                "labels": categories,
                "datasets": [dataset]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": self.title,
                        "color": self.text_color,
                        "font": {
                            "size": 16
                        }
                    },
                    "legend": {
                        "display": self.show_legend,
                        "position": "right",
                        "labels": {
                            "color": self.text_color
                        }
                    },
                    "tooltip": {
                        "callbacks": {
                            "label": "function(context) { return context.label + ': ' + context.raw + ' (' + context.parsed + '%)'}"
                            if self.show_percentages else None
                        }
                    }
                },
                "cutout": "50%" if self.donut else 0
            }
        }
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.0.0/dist/chart.umd.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: {self.background_color}; }}
                .chart-container {{ width: {self.width}px; height: {self.height}px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <script>
                const config = {json.dumps(config, default=lambda o: '<Function>' if callable(o) else str(o))};
                
                // Fix for function serialization
                if (config.options.plugins.tooltip.callbacks) {{
                    config.options.plugins.tooltip.callbacks.label = function(context) {{
                        return context.label + ': ' + context.raw + ' (' + 
                            (context.parsed * 100 / context.dataset.data.reduce((a,b) => a+b, 0)).toFixed(1) + '%)'
                    }};
                }}
                
                new Chart(document.getElementById('chart'), config);
            </script>
        </body>
        </html>
        """
        
        return html


class HeatmapChart(Chart):
    """
    Heatmap chart for matrix data.
    """

    def __init__(self, title: str, data: Dict[str, Any]):
        """
        Initialize heatmap chart.

        Args:
            title: Chart title
            data: Data for the chart (must have 'x_labels', 'y_labels', and 'values' keys)
        """
        super().__init__(title, data)
        self.color_scheme = 'blues'  # blues, greens, reds, purples
        self.show_values = True
        self.value_format = ".1f"

    def generate_html(self) -> str:
        """
        Generate HTML for the heatmap chart using Chart.js and chartjs-chart-matrix.

        Returns:
            HTML string for the chart
        """
        # Extract data
        x_labels = self.data.get("x_labels", [])
        y_labels = self.data.get("y_labels", [])
        values = self.data.get("values", [])  # 2D array
        
        # Flatten values for Chart.js
        dataset = []
        min_value = float('inf')
        max_value = float('-inf')
        
        for i, y in enumerate(y_labels):
            for j, x in enumerate(x_labels):
                if i < len(values) and j < len(values[i]):
                    value = values[i][j]
                    min_value = min(min_value, value)
                    max_value = max(max_value, value)
                    dataset.append({
                        "x": j,
                        "y": i,
                        "v": value
                    })
        
        # Set min/max to valid values if not set
        if min_value == float('inf'):
            min_value = 0
        if max_value == float('-inf'):
            max_value = 1
        
        # Choose color scale
        color_scales = {
            'blues': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594'],
            'greens': ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#005a32'],
            'reds': ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#99000d'],
            'purples': ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#4a1486']
        }
        
        color_scale = color_scales.get(self.color_scheme, color_scales['blues'])
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.0.0/dist/chart.umd.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-matrix@1.2.0/dist/chartjs-chart-matrix.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: {self.background_color}; }}
                .chart-container {{ width: {self.width}px; height: {self.height}px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <script>
                // Function to interpolate colors
                function getColor(value, min, max, colorScale) {{
                    if (min === max) return colorScale[colorScale.length - 1];
                    const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));
                    const index = Math.floor(normalized * (colorScale.length - 1));
                    return colorScale[index];
                }}
                
                // Create dataset
                const data = {json.dumps(dataset)};
                const xLabels = {json.dumps(x_labels)};
                const yLabels = {json.dumps(y_labels)};
                const minValue = {min_value};
                const maxValue = {max_value};
                const colorScale = {json.dumps(color_scale)};
                
                const config = {{
                    type: 'matrix',
                    data: {{
                        datasets: [{{
                            label: 'Heatmap',
                            data: data,
                            backgroundColor: function(context) {{
                                const value = context.dataset.data[context.dataIndex].v;
                                return getColor(value, minValue, maxValue, colorScale);
                            }},
                            borderColor: '{self.background_color}',
                            borderWidth: 1,
                            width: function(context) {{
                                return Math.min(
                                    (context.chart.chartArea.right - context.chart.chartArea.left) / xLabels.length,
                                    (context.chart.chartArea.bottom - context.chart.chartArea.top) / yLabels.length
                                ) - 1;
                            }},
                            height: function(context) {{
                                return Math.min(
                                    (context.chart.chartArea.bottom - context.chart.chartArea.top) / yLabels.length,
                                    (context.chart.chartArea.right - context.chart.chartArea.left) / xLabels.length
                                ) - 1;
                            }}
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '{self.title}',
                                color: '{self.text_color}',
                                font: {{
                                    size: 16
                                }}
                            }},
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                callbacks: {{
                                    title: function() {{ return ''; }},
                                    label: function(context) {{
                                        const data = context.dataset.data[context.dataIndex];
                                        return [
                                            'X: ' + xLabels[data.x],
                                            'Y: ' + yLabels[data.y],
                                            'Value: ' + data.v.toFixed({self.value_format.split('.')[1][0]})
                                        ];
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{
                                type: 'category',
                                labels: xLabels,
                                ticks: {{
                                    color: '{self.text_color}'
                                }},
                                grid: {{
                                    display: false
                                }}
                            }},
                            y: {{
                                type: 'category',
                                labels: yLabels,
                                offset: true,
                                ticks: {{
                                    color: '{self.text_color}'
                                }},
                                grid: {{
                                    display: false
                                }}
                            }}
                        }}
                    }}
                }};
                
                new Chart(document.getElementById('chart'), config);
            </script>
        </body>
        </html>
        """
        
        return html


class Dashboard:
    """
    Class for creating multi-chart dashboards.
    """

    def __init__(self, title: str):
        """
        Initialize dashboard.

        Args:
            title: Dashboard title
        """
        self.title = title
        self.charts = []
        self.layout = "grid"  # grid or flow
        self.columns = 2
        self.width = 1200
        self.background_color = "#f7f7f7"
        self.text_color = "#333333"
        self.padding = 20
        self.chart_background = "#ffffff"
        self.chart_border = "#e0e0e0"
        self.chart_shadow = True
        self.auto_refresh = False
        self.refresh_interval = 60  # seconds

    def add_chart(self, chart: Chart) -> None:
        """
        Add a chart to the dashboard.

        Args:
            chart: Chart to add
        """
        self.charts.append(chart)

    def generate_html(self) -> str:
        """
        Generate HTML for the dashboard.

        Returns:
            HTML string for the dashboard
        """
        # Adjust chart sizes to fit dashboard
        chart_width = (self.width - (self.columns + 1) * self.padding) // self.columns
        
        for chart in self.charts:
            chart.width = chart_width
            chart.height = int(chart_width * 0.6)  # Maintain aspect ratio
            chart.background_color = self.chart_background
        
        # Generate HTML for each chart
        chart_htmls = []
        for chart in self.charts:
            chart_html = chart.generate_html()
            # Extract only the canvas and script part
            start = chart_html.find('<div class="chart-container">')
            end = chart_html.find('</body>')
            chart_htmls.append(chart_html[start:end])
        
        # Generate CSS for layout
        if self.layout == "grid":
            layout_css = f"""
                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: repeat({self.columns}, 1fr);
                    gap: {self.padding}px;
                    padding: {self.padding}px;
                }}
                
                .chart-wrapper {{
                    background-color: {self.chart_background};
                    border: 1px solid {self.chart_border};
                    border-radius: 5px;
                    padding: 15px;
                    box-shadow: {box_shadow};
                }}
            """.replace("{box_shadow}", "0 2px 5px rgba(0,0,0,0.1)" if self.chart_shadow else "none")
        else:
            # Flow layout
            layout_css = f"""
                .dashboard-flow {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: {self.padding}px;
                    padding: {self.padding}px;
                }}
                
                .chart-wrapper {{
                    background-color: {self.chart_background};
                    border: 1px solid {self.chart_border};
                    border-radius: 5px;
                    padding: 15px;
                    box-shadow: {box_shadow};
                    flex: 1 1 {chart_width}px;
                    min-width: {chart_width // 2}px;
                }}
            """.replace("{box_shadow}", "0 2px 5px rgba(0,0,0,0.1)" if self.chart_shadow else "none")
        
        # Generate HTML
        refresh_meta = f'<meta http-equiv="refresh" content="{self.refresh_interval}">' if self.auto_refresh else ''
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            {refresh_meta}
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.0.0/dist/chart.umd.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/luxon@3.0.1/build/global/luxon.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1.2.0/dist/chartjs-adapter-luxon.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-matrix@1.2.0/dist/chartjs-chart-matrix.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: {self.background_color};
                    color: {self.text_color};
                }}
                
                .dashboard-header {{
                    text-align: center;
                    padding: {self.padding}px;
                    border-bottom: 1px solid {self.chart_border};
                    margin-bottom: {self.padding // 2}px;
                }}
                
                {layout_css}
                
                .chart-container {{
                    width: 100%;
                    height: 100%;
                }}
                
                @media (max-width: 768px) {{
                    .dashboard-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>{self.title}</h1>
                <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="dashboard-{self.layout}">
                {"".join(f'<div class="chart-wrapper">{chart_html}</div>' for chart_html in chart_htmls)}
            </div>
        </body>
        </html>
        """
        
        return html

    def to_html_file(self, output_path: Optional[str] = None) -> str:
        """
        Save dashboard as HTML file.

        Args:
            output_path: Path to save HTML file (optional)
                If not provided, will use a temporary file

        Returns:
            Path to saved HTML file
        """
        html = self.generate_html()
        
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".html")
            os.close(fd)
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        return output_path

    def show(self) -> None:
        """
        Open dashboard in web browser.
        """
        html_file = self.to_html_file()
        webbrowser.open(f"file://{html_file}")


class MonitoringDashboard:
    """
    Specialized dashboard for monitoring data.
    """

    def __init__(self, title: str, app_name: str, environment: str):
        """
        Initialize monitoring dashboard.

        Args:
            title: Dashboard title
            app_name: Name of the application
            environment: Environment
        """
        self.title = title
        self.app_name = app_name
        self.environment = environment
        self.dashboard = Dashboard(title)
        self.time_range = "24h"  # 1h, 6h, 24h, 7d, 30d
        self.refresh_interval = 60  # seconds
        self.metrics = ["cpu_usage", "memory_usage", "request_rate", "error_rate", "response_time"]
        self.auto_refresh = True

    def _get_monitoring_data(self) -> Dict[str, Any]:
        """
        Get monitoring data for the application.

        Returns:
            Dict with monitoring data
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            
            if self.time_range == "1h":
                start_time = end_time - timedelta(hours=1)
                interval = timedelta(minutes=1)
            elif self.time_range == "6h":
                start_time = end_time - timedelta(hours=6)
                interval = timedelta(minutes=5)
            elif self.time_range == "24h":
                start_time = end_time - timedelta(hours=24)
                interval = timedelta(minutes=15)
            elif self.time_range == "7d":
                start_time = end_time - timedelta(days=7)
                interval = timedelta(hours=1)
            elif self.time_range == "30d":
                start_time = end_time - timedelta(days=30)
                interval = timedelta(hours=4)
            else:
                # Default to 24h
                start_time = end_time - timedelta(hours=24)
                interval = timedelta(minutes=15)
            
            # In a real implementation, this would call monitoring.check_status with
            # history=True to get historical data
            
            # For demonstration, we'll generate sample data
            sample_data = ChartData.generate_sample_data(
                start_time=start_time,
                duration=end_time - start_time,
                interval=interval,
                metrics=self.metrics
            )
            
            return {
                "app_name": self.app_name,
                "environment": self.environment,
                "start_time": start_time,
                "end_time": end_time,
                "data": sample_data
            }
        
        except Exception as e:
            logger.error(f"Error getting monitoring data: {str(e)}", exc_info=True)
            return {
                "app_name": self.app_name,
                "environment": self.environment,
                "start_time": datetime.now() - timedelta(hours=1),
                "end_time": datetime.now(),
                "data": []
            }

    def generate(self) -> Dashboard:
        """
        Generate the monitoring dashboard.

        Returns:
            Dashboard object
        """
        # Get monitoring data
        monitoring_data = self._get_monitoring_data()
        data = monitoring_data["data"]
        
        # Configure dashboard
        self.dashboard.title = f"{self.title} - {self.app_name} ({self.environment})"
        self.dashboard.auto_refresh = self.auto_refresh
        self.dashboard.refresh_interval = self.refresh_interval
        
        # Create resource usage chart
        if "cpu_usage" in self.metrics and "memory_usage" in self.metrics:
            resource_data = ChartData.format_time_series(
                data=data,
                time_field="timestamp",
                value_fields=["cpu_usage", "memory_usage"]
            )
            
            resource_chart = LineChart(
                title="Resource Usage",
                data=resource_data,
                y_label="Percentage (%)"
            )
            
            self.dashboard.add_chart(resource_chart)
        
        # Create request rate chart
        if "request_rate" in self.metrics:
            request_data = ChartData.format_time_series(
                data=data,
                time_field="timestamp",
                value_fields=["request_rate"]
            )
            
            request_chart = LineChart(
                title="Request Rate",
                data=request_data,
                y_label="Requests/sec"
            )
            
            self.dashboard.add_chart(request_chart)
        
        # Create error rate chart
        if "error_rate" in self.metrics:
            error_data = ChartData.format_time_series(
                data=data,
                time_field="timestamp",
                value_fields=["error_rate"]
            )
            
            error_chart = LineChart(
                title="Error Rate",
                data=error_data,
                y_label="Percentage (%)"
            )
            
            error_chart.colors = ["#e15759"]  # Use red for errors
            self.dashboard.add_chart(error_chart)
        
        # Create response time chart
        if "response_time" in self.metrics:
            response_data = ChartData.format_time_series(
                data=data,
                time_field="timestamp",
                value_fields=["response_time"]
            )
            
            response_chart = LineChart(
                title="Response Time",
                data=response_data,
                y_label="Milliseconds"
            )
            
            self.dashboard.add_chart(response_chart)
        
        # Create summary chart (average values)
        summary_categories = []
        summary_values = []
        
        for metric in self.metrics:
            values = [item.get(metric, 0) for item in data if metric in item]
            if values:
                avg_value = sum(values) / len(values)
                summary_categories.append(metric.replace("_", " ").title())
                summary_values.append(avg_value)
        
        summary_data = {
            "categories": summary_categories,
            "values": summary_values
        }
        
        summary_chart = BarChart(
            title="Average Metrics",
            data=summary_data
        )
        
        self.dashboard.add_chart(summary_chart)
        
        return self.dashboard

    def show(self) -> None:
        """
        Generate and show the dashboard in a web browser.
        """
        dashboard = self.generate()
        dashboard.show()

    def to_html_file(self, output_path: str) -> str:
        """
        Generate and save the dashboard as an HTML file.

        Args:
            output_path: Path to save HTML file

        Returns:
            Path to saved HTML file
        """
        dashboard = self.generate()
        return dashboard.to_html_file(output_path)


# Convenience functions for quick chart creation
def create_line_chart(
    title: str, 
    data: List[Dict[str, Any]], 
    time_field: str,
    value_fields: List[str],
    x_label: str = "Time",
    y_label: str = "Value",
    output_path: Optional[str] = None
) -> LineChart:
    """
    Create a line chart from data.

    Args:
        title: Chart title
        data: List of data points
        time_field: Field name for timestamp
        value_fields: List of fields to extract values from
        x_label: Label for X axis
        y_label: Label for Y axis
        output_path: Path to save chart HTML (optional)

    Returns:
        LineChart object
    """
    formatted_data = ChartData.format_time_series(
        data=data,
        time_field=time_field,
        value_fields=value_fields
    )
    
    chart = LineChart(
        title=title,
        data=formatted_data,
        x_label=x_label,
        y_label=y_label
    )
    
    if output_path:
        chart.to_html_file(output_path)
    
    return chart


def create_bar_chart(
    title: str, 
    data: List[Dict[str, Any]], 
    category_field: str,
    value_field: str,
    aggregation: str = "sum",
    x_label: str = "Category",
    y_label: str = "Value",
    output_path: Optional[str] = None
) -> BarChart:
    """
    Create a bar chart from data.

    Args:
        title: Chart title
        data: List of data points
        category_field: Field name for categories
        value_field: Field name for values
        aggregation: Aggregation function (sum, avg, min, max, count)
        x_label: Label for X axis
        y_label: Label for Y axis
        output_path: Path to save chart HTML (optional)

    Returns:
        BarChart object
    """
    formatted_data = ChartData.format_aggregated(
        data=data,
        category_field=category_field,
        value_field=value_field,
        aggregation=aggregation
    )
    
    chart = BarChart(
        title=title,
        data=formatted_data,
        x_label=x_label,
        y_label=y_label
    )
    
    if output_path:
        chart.to_html_file(output_path)
    
    return chart


def create_pie_chart(
    title: str, 
    data: List[Dict[str, Any]], 
    category_field: str,
    value_field: str,
    aggregation: str = "sum",
    output_path: Optional[str] = None
) -> PieChart:
    """
    Create a pie chart from data.

    Args:
        title: Chart title
        data: List of data points
        category_field: Field name for categories
        value_field: Field name for values
        aggregation: Aggregation function (sum, avg, min, max, count)
        output_path: Path to save chart HTML (optional)

    Returns:
        PieChart object
    """
    formatted_data = ChartData.format_aggregated(
        data=data,
        category_field=category_field,
        value_field=value_field,
        aggregation=aggregation
    )
    
    chart = PieChart(
        title=title,
        data=formatted_data
    )
    
    if output_path:
        chart.to_html_file(output_path)
    
    return chart


def create_monitoring_dashboard(
    app_name: str, 
    environment: str, 
    time_range: str = "24h",
    metrics: Optional[List[str]] = None,
    auto_refresh: bool = True,
    refresh_interval: int = 60,
    output_path: Optional[str] = None
) -> Dashboard:
    """
    Create a monitoring dashboard.

    Args:
        app_name: Name of the application
        environment: Environment
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        metrics: List of metrics to display (optional)
        auto_refresh: Whether to auto-refresh the dashboard
        refresh_interval: Refresh interval in seconds
        output_path: Path to save dashboard HTML (optional)

    Returns:
        Dashboard object
    """
    title = f"Monitoring Dashboard"
    
    dashboard = MonitoringDashboard(
        title=title,
        app_name=app_name,
        environment=environment
    )
    
    dashboard.time_range = time_range
    dashboard.auto_refresh = auto_refresh
    dashboard.refresh_interval = refresh_interval
    
    if metrics:
        dashboard.metrics = metrics
    
    result = dashboard.generate()
    
    if output_path:
        result.to_html_file(output_path)
    
    return result
