#!/usr/bin/env python3
"""
Austender Scraper Performance Monitor
------------------------------------
Track scraper performance metrics over time and generate insights.
"""

import os
import json
import glob
import datetime
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Create directories
os.makedirs("monitoring", exist_ok=True)
os.makedirs("monitoring/plots", exist_ok=True)
os.makedirs("monitoring/reports", exist_ok=True)

class ScraperPerformanceMonitor:
    """Monitor and analyze scraper performance over time."""
    
    def __init__(self, 
                 data_dir="test_results",
                 output_dir="monitoring",
                 metrics_file="metrics_history.json"):
        """Initialize the performance monitor."""
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.metrics_file = self.output_dir / metrics_file
        
        # Initialize metrics history
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                self.metrics_history = json.load(f)
        else:
            self.metrics_history = {
                "runs": [],
                "multi_tool": {
                    "success_rate": [],
                    "data_count": [],
                    "duration": []
                },
                "focused": {
                    "success_rate": [],
                    "data_count": [],
                    "duration": []
                },
                "agentic": {
                    "success_rate": [],
                    "data_count": [],
                    "duration": []
                }
            }
    
    def collect_metrics(self):
        """Collect metrics from test result and output files."""
        # Look for test result files
        test_files = list(self.data_dir.glob("*.json"))
        result_files = list(Path("output").glob("*.json"))
        
        # Latest run timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Track metrics for this run
        run_metrics = {
            "timestamp": timestamp,
            "approaches": {}
        }
        
        # Process test harness results
        for file in test_files:
            if file.stem.startswith("test_summary_"):
                try:
                    with open(file, "r") as f:
                        test_data = json.load(f)
                    
                    # Extract metrics from test results
                    if "summary" in test_data and "results_by_approach" in test_data["summary"]:
                        for approach, stats in test_data["summary"]["results_by_approach"].items():
                            run_metrics["approaches"][approach] = {
                                "success_rate": stats.get("success_rate", 0),
                                "data_count": stats.get("average_data_count", 0),
                                "total_data": stats.get("total_data_extracted", 0),
                                "error_rate": stats.get("error_rate", 0)
                            }
                            
                            # Update history for this approach
                            if approach in self.metrics_history:
                                self.metrics_history[approach]["success_rate"].append({
                                    "timestamp": timestamp,
                                    "value": stats.get("success_rate", 0)
                                })
                                self.metrics_history[approach]["data_count"].append({
                                    "timestamp": timestamp,
                                    "value": stats.get("average_data_count", 0)
                                })
                except Exception as e:
                    print(f"Error processing test file {file}: {str(e)}")
        
        # Process individual scraper output files
        for file in result_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                
                # Determine which scraper produced this file
                approach = self._determine_approach(file, data)
                if approach:
                    if approach not in run_metrics["approaches"]:
                        run_metrics["approaches"][approach] = {}
                    
                    run_metrics["approaches"][approach]["file"] = str(file)
                    run_metrics["approaches"][approach]["data_count"] = len(data)
                    
                    # Update history
                    if approach in self.metrics_history:
                        self.metrics_history[approach]["data_count"].append({
                            "timestamp": timestamp,
                            "value": len(data)
                        })
            except Exception as e:
                print(f"Error processing result file {file}: {str(e)}")
        
        # Add this run to history
        self.metrics_history["runs"].append(run_metrics)
        
        # Save updated metrics
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics_history, f, indent=2)
        
        return run_metrics
    
    def _determine_approach(self, file_path, data):
        """Determine which scraper approach produced this file."""
        file_name = file_path.stem.lower()
        
        if "multi_tool" in file_name or "multitool" in file_name:
            return "multi_tool"
        elif "focused" in file_name:
            return "focused"
        elif "agentic" in file_name:
            return "agentic"
        
        # Try to determine from data structure
        if isinstance(data, list) and len(data) > 0:
            sample = data[0]
            if isinstance(sample, dict):
                if "method_used" in sample:
                    return "multi_tool"
                elif "extracted_by" in sample:
                    return "focused"
                elif "source" in sample and sample.get("source") == "agentic_browser":
                    return "agentic"
        
        return None
    
    def generate_plots(self):
        """Generate performance plots over time."""
        # Convert data for plotting
        success_rates = {approach: [] for approach in ["multi_tool", "focused", "agentic"]}
        data_counts = {approach: [] for approach in ["multi_tool", "focused", "agentic"]}
        timestamps = {approach: [] for approach in ["multi_tool", "focused", "agentic"]}
        
        # Extract data for plotting
        for approach in ["multi_tool", "focused", "agentic"]:
            if approach in self.metrics_history:
                for entry in self.metrics_history[approach]["success_rate"]:
                    success_rates[approach].append(entry["value"])
                    timestamps[approach].append(entry["timestamp"])
                
                for entry in self.metrics_history[approach]["data_count"]:
                    data_counts[approach].append(entry["value"])
        
        # Plot success rates
        self._plot_metric(
            metric_name="success_rate",
            title="Success Rate Over Time",
            ylabel="Success Rate (%)",
            data=success_rates,
            timestamps=timestamps
        )
        
        # Plot data counts
        self._plot_metric(
            metric_name="data_count",
            title="Data Items Extracted Over Time",
            ylabel="Number of Items",
            data=data_counts,
            timestamps=timestamps
        )
    
    def _plot_metric(self, metric_name, title, ylabel, data, timestamps):
        """Generate plot for a specific metric."""
        plt.figure(figsize=(12, 6))
        
        # Plot each approach
        for approach, values in data.items():
            if values:  # Only plot if we have data
                # Convert timestamps to datetime objects
                times = [datetime.datetime.fromisoformat(t) for t in timestamps[approach]]
                
                # Create the plot
                plt.plot(times, values, marker='o', linestyle='-', label=approach)
        
        # Set up the plot
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel(ylabel)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # Format x-axis
        plt.gcf().autofmt_xdate()
        
        # Save the plot
        output_path = self.output_dir / "plots" / f"{metric_name}_over_time.png"
        plt.savefig(output_path)
        plt.close()
        
        print(f"Plot saved to {output_path}")
    
    def generate_report(self):
        """Generate a performance report."""
        # Prepare report data
        latest_metrics = {}
        for approach in ["multi_tool", "focused", "agentic"]:
            if approach in self.metrics_history:
                latest_metrics[approach] = {
                    "success_rate": self.metrics_history[approach]["success_rate"][-1]["value"] 
                        if self.metrics_history[approach]["success_rate"] else 0,
                    "data_count": self.metrics_history[approach]["data_count"][-1]["value"]
                        if self.metrics_history[approach]["data_count"] else 0
                }
        
        # Generate markdown report
        now = datetime.datetime.now()
        report_path = self.output_dir / "reports" / f"performance_report_{now.strftime('%Y%m%d_%H%M')}.md"
        
        with open(report_path, "w") as f:
            f.write("# Austender Scraper Performance Report\n\n")
            f.write(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Performance Summary\n\n")
            f.write("| Approach | Success Rate | Data Items |\n")
            f.write("|----------|--------------|------------|\n")
            
            # Add data for each approach
            for approach, metrics in latest_metrics.items():
                f.write(f"| {approach} | {metrics['success_rate']:.2%} | {metrics['data_count']} |\n")
            
            f.write("\n## Recent Runs\n\n")
            
            # List most recent runs (up to 5)
            runs = self.metrics_history.get("runs", [])
            for run in runs[-5:]:
                f.write(f"### Run: {run['timestamp']}\n\n")
                
                for approach, metrics in run.get("approaches", {}).items():
                    f.write(f"#### {approach}\n\n")
                    for key, value in metrics.items():
                        if key != "file":  # Skip file path
                            f.write(f"- {key}: {value}\n")
                    f.write("\n")
            
            f.write("\n## Recommendations\n\n")
            
            # Determine best approach based on metrics
            best_approach = max(latest_metrics.items(), key=lambda x: x[1]['success_rate'])
            most_data = max(latest_metrics.items(), key=lambda x: x[1]['data_count'])
            
            f.write(f"- Best success rate: **{best_approach[0]}** ({best_approach[1]['success_rate']:.2%})\n")
            f.write(f"- Most data extracted: **{most_data[0]}** ({most_data[1]['data_count']} items)\n\n")
            
            if best_approach[0] == most_data[0]:
                f.write(f"**Recommended approach: {best_approach[0]}**\n\n")
            else:
                f.write(f"**Consider {best_approach[0]} for reliability and {most_data[0]} for maximum data extraction**\n\n")
        
        print(f"Report generated: {report_path}")
        return report_path

def main():
    """Main function to run the performance monitor."""
    parser = argparse.ArgumentParser(description="Monitor Austender scraper performance")
    parser.add_argument("--collect", action="store_true", help="Collect metrics from test results")
    parser.add_argument("--plot", action="store_true", help="Generate performance plots")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--all", action="store_true", help="Perform all monitoring tasks")
    
    args = parser.parse_args()
    
    # Default to all if no specific tasks are requested
    if not any([args.collect, args.plot, args.report]):
        args.all = True
    
    # Initialize the monitor
    monitor = ScraperPerformanceMonitor()
    
    # Perform requested tasks
    if args.collect or args.all:
        print("Collecting performance metrics...")
        monitor.collect_metrics()
    
    if args.plot or args.all:
        print("Generating performance plots...")
        monitor.generate_plots()
    
    if args.report or args.all:
        print("Generating performance report...")
        report_path = monitor.generate_report()
        print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
