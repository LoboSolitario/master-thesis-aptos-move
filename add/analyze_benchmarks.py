import os
import pandas as pd
from pathlib import Path
import re
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

def parse_execution_trace(html_file):
    """Parse the Full Execution Trace section from the HTML file"""
    try:
        with open(html_file, 'r') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Find the Full Execution Trace section
            trace_section = None
            for h2 in soup.find_all('h2'):
                if 'Full Execution Trace' in h2.get_text():
                    # Navigate to the pre > code element
                    div = h2.find_next('div')
                    if div:
                        pre = div.find('pre')
                        if pre:
                            trace_section = pre.find('code')
                    break
            
            if not trace_section:
                print(f"No execution trace found in {html_file}")
                return None

            # Extract the text from the code tag
            trace_text = trace_section.get_text()
            
            # Parse each line of the trace
            opcode_data = []
            for line in trace_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Use regex to extract opcode name and gas units
                # Looking for patterns like "opcode_name    0.000588    0.02%"
                # We need to be more flexible with whitespace
                match = re.match(r'^\s*([a-zA-Z0-9_]+)\s+(\d+\.\d+)\s+\d+\.\d+%', line)
                if match:
                    opcode = match.group(1)
                    gas = float(match.group(2))
                    
                    # Skip high-level sections and module/function names
                    if (not opcode.startswith('0x') and 
                        opcode not in ["execution", "intrinsic", "keyless", "dependencies", 
                                     "ledger", "transaction", "events", "state", "state_write_ops"]):
                        opcode_data.append({
                            'opcode': opcode,
                            'gas_units': gas
                        })
            
            return opcode_data

    except Exception as e:
        print(f"Error reading HTML file {html_file}: {e}")
        print(f"Exception details: {str(e)}")
        return None

def analyze_gas_profiling():
    gas_profiling_dir = Path('gas-profiling')
    all_opcode_data = []

    # Check if directory exists
    if not gas_profiling_dir.exists():
        print(f"Gas profiling directory not found at: {gas_profiling_dir}")
        return

    # Iterate through all benchmark directories
    for benchmark_dir in gas_profiling_dir.glob('txn-*'):
        benchmark_name = benchmark_dir.name
        print(f"\nProcessing benchmark: {benchmark_name}")
        
        # Extract operation name from directory name
        operation_match = re.search(r'opcode_benchmark-(\w+)', benchmark_name)
        operation_name = operation_match.group(1) if operation_match else 'unknown'

        # Path to HTML file
        html_file = benchmark_dir / 'index.html'

        if html_file.exists():
            # Get execution trace data
            trace_data = parse_execution_trace(html_file)
            
            if trace_data:
                # Add benchmark information to each opcode entry
                for entry in trace_data:
                    entry['benchmark'] = operation_name
                all_opcode_data.extend(trace_data)
                print(f"Extracted {len(trace_data)} opcode entries from {operation_name}")
            else:
                print(f"Failed to extract opcode data from {html_file}")

    if not all_opcode_data:
        print("\nNo opcode data was collected.")
        return

    # Create DataFrame
    df = pd.DataFrame(all_opcode_data)
    
    # Group by opcode and calculate statistics
    opcode_stats = df.groupby('opcode')['gas_units'].agg([
        'count',
        'mean',
        'min',
        'max',
        'sum'
    ]).round(6)  # More precision for gas units

    # Save raw opcode data to CSV
    output_file = 'opcode_gas_units.csv'
    df.to_csv(output_file, index=False)
    print(f"\nRaw opcode data saved to {output_file}")

    # Save opcode statistics to a separate CSV
    stats_file = 'opcode_statistics.csv'
    opcode_stats.to_csv(stats_file)
    print(f"Opcode statistics saved to {stats_file}")

    # Track opcodes coverage
    track_opcode_coverage(opcode_stats)

    # Print summary
    print("\n=== Opcode Gas Usage Summary ===")
    print(f"\nTotal unique opcodes found: {len(opcode_stats)}")
    if not opcode_stats.empty:
        print("\nTop 10 most gas-intensive opcodes (by average cost):")
        print(opcode_stats.sort_values('mean', ascending=False).head(10))
    
    # Generate HTML report
    generate_html_report(df, opcode_stats)

def track_opcode_coverage(opcode_stats):
    """Track which opcodes have been benchmarked and which are still missing"""
    print("\n=== Opcode Coverage Analysis ===")
    
    try:
        # Load the all_opcodes.csv file
        all_opcodes_path = Path('all_opcodes.csv')
        if not all_opcodes_path.exists():
            print(f"Error: all_opcodes.csv not found at {all_opcodes_path}")
            return
            
        all_opcodes_df = pd.read_csv(all_opcodes_path)
        
        # Convert all opcodes to lowercase for consistent comparison
        all_opcodes_df['Opcode'] = all_opcodes_df['Opcode'].str.lower()
        
        # Get the set of all opcodes from the CSV
        all_opcodes_set = set(all_opcodes_df['Opcode'].values)
        
        # Get the set of benchmarked opcodes (convert to lowercase)
        benchmarked_opcodes = set(opcode.lower() for opcode in opcode_stats.index)
        
        # Calculate the difference to find missing opcodes
        missing_opcodes = all_opcodes_set - benchmarked_opcodes
        
        # Calculate coverage percentage
        total_opcodes = len(all_opcodes_set)
        benchmarked_count = len(benchmarked_opcodes)
        coverage_percentage = (benchmarked_count / total_opcodes) * 100 if total_opcodes > 0 else 0
        
        # Print coverage statistics
        print(f"Total opcodes in spec: {total_opcodes}")
        print(f"Opcodes benchmarked: {benchmarked_count}")
        print(f"Coverage: {coverage_percentage:.2f}%")
        
        # Save coverage data to CSV
        coverage_data = []
        
        for opcode in all_opcodes_df['Opcode']:
            # Create row with coverage info
            opcode_type = all_opcodes_df.loc[all_opcodes_df['Opcode'] == opcode, 'Type'].values[0] if 'Type' in all_opcodes_df.columns else 'Unknown'
            is_benchmarked = opcode.lower() in benchmarked_opcodes
            status = "Benchmarked" if is_benchmarked else "Missing"
            
            coverage_data.append({
                'Opcode': opcode,
                'Type': opcode_type,
                'Status': status
            })
        
        # Create and save coverage DataFrame
        coverage_df = pd.DataFrame(coverage_data)
        coverage_file = 'opcode_coverage.csv'
        coverage_df.to_csv(coverage_file, index=False)
        print(f"Opcode coverage data saved to {coverage_file}")
        
        # Print missing opcodes by type if available
        if 'Type' in all_opcodes_df.columns:
            print("\nMissing opcodes by type:")
            missing_df = coverage_df[coverage_df['Status'] == 'Missing']
            for opcode_type in sorted(missing_df['Type'].unique()):
                type_opcodes = missing_df[missing_df['Type'] == opcode_type]['Opcode'].tolist()
                if type_opcodes:  # Only print if there are missing opcodes of this type
                    print(f"  {opcode_type}: {', '.join(type_opcodes)}")
        else:
            print("\nMissing opcodes:")
            print(", ".join(sorted(missing_opcodes)))
            
    except Exception as e:
        print(f"Error analyzing opcode coverage: {e}")

def generate_html_report(df, opcode_stats):
    """Generate an HTML report with tables and visualizations"""
    print("\nGenerating HTML report...")
    
    # Create directory for plots
    plots_dir = Path('plots')
    plots_dir.mkdir(exist_ok=True)
    
    # Create plots and get their base64 encoded strings
    plot_data = create_visualizations(df, opcode_stats)
    
    # Add coverage chart if opcode_coverage.csv exists
    coverage_chart = ""
    coverage_path = Path('opcode_coverage.csv')
    if coverage_path.exists():
        try:
            coverage_df = pd.read_csv(coverage_path)
            coverage_data = coverage_df['Status'].value_counts()
            coverage_chart = create_coverage_chart(coverage_data)
        except Exception as e:
            print(f"Error creating coverage chart: {e}")
    
    # JavaScript part (written separately to avoid f-string issues)
    js_code = """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Add search and filter functionality
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.placeholder = 'Search opcodes...';
            searchInput.className = 'form-control mb-3';
            searchInput.addEventListener('keyup', function() {
                const searchText = this.value.toLowerCase();
                const rows = document.querySelectorAll('#coverageTable tbody tr');
                
                rows.forEach(row => {
                    const opcode = row.cells[0].textContent.toLowerCase();
                    const type = row.cells[1].textContent.toLowerCase();
                    const status = row.cells[2].textContent.toLowerCase();
                    
                    if (opcode.includes(searchText) || type.includes(searchText) || status.includes(searchText)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
            
            const filterDiv = document.createElement('div');
            filterDiv.className = 'mb-3';
            
            const statusFilter = document.createElement('div');
            statusFilter.className = 'btn-group me-3';
            statusFilter.innerHTML = `
                <button type="button" class="btn btn-outline-primary active" data-filter="all">All</button>
                <button type="button" class="btn btn-outline-success" data-filter="Benchmarked">Benchmarked</button>
                <button type="button" class="btn btn-outline-danger" data-filter="Missing">Missing</button>
            `;
            
            statusFilter.addEventListener('click', function(e) {
                if (e.target.tagName === 'BUTTON') {
                    // Update active button
                    statusFilter.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
                    e.target.classList.add('active');
                    
                    const filter = e.target.getAttribute('data-filter');
                    const rows = document.querySelectorAll('#coverageTable tbody tr');
                    
                    rows.forEach(row => {
                        const status = row.cells[2].textContent;
                        if (filter === 'all' || status === filter) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                }
            });
            
            filterDiv.appendChild(statusFilter);
            
            const tableContainer = document.querySelector('#coverageTable').parentNode;
            tableContainer.insertBefore(searchInput, document.querySelector('#coverageTable'));
            tableContainer.insertBefore(filterDiv, document.querySelector('#coverageTable'));
        });
    </script>
    """
    
    # Create HTML content (without JavaScript part)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Move Opcode Gas Analysis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ padding: 20px; }}
            .plot-img {{ max-width: 100%; height: auto; margin-bottom: 20px; }}
            .table-container {{ margin: 20px 0; overflow-x: auto; }}
            h1, h2, h3 {{ margin-top: 30px; }}
            .card {{ margin-bottom: 20px; }}
            .coverage-indicator {{ 
                height: 20px; 
                border-radius: 10px;
                background: linear-gradient(to right, #28a745 var(--coverage-pct), #dc3545 var(--coverage-pct)); 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">Move Opcode Gas Analysis Report</h1>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h2>Summary</h2>
                        </div>
                        <div class="card-body">
                            <p><strong>Total unique opcodes analyzed:</strong> {len(opcode_stats)}</p>
                            <p><strong>Total benchmarks processed:</strong> {df['benchmark'].nunique()}</p>
                            <p><strong>Analysis generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            
                            {coverage_chart}
                        </div>
                    </div>
                </div>
            </div>

            <h2>Visualizations</h2>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h3>Top Gas-Intensive Opcodes (Average Cost)</h3>
                        </div>
                        <div class="card-body">
                            <img src="data:image/png;base64,{plot_data['top_gas_intensive']}" class="plot-img" alt="Top Gas-Intensive Opcodes">
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h3>Opcode Frequency</h3>
                        </div>
                        <div class="card-body">
                            <img src="data:image/png;base64,{plot_data['opcode_frequency']}" class="plot-img" alt="Opcode Frequency">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h3>Gas Distribution by Opcode</h3>
                        </div>
                        <div class="card-body">
                            <img src="data:image/png;base64,{plot_data['gas_distribution']}" class="plot-img" alt="Gas Distribution by Opcode">
                        </div>
                    </div>
                </div>
            </div>

            <h2>Opcode Statistics</h2>
            <div class="table-container">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Opcode</th>
                            <th>Count</th>
                            <th>Mean Gas</th>
                            <th>Min Gas</th>
                            <th>Max Gas</th>
                            <th>Total Gas</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_table_rows(opcode_stats)}
                    </tbody>
                </table>
            </div>

            <h2>Opcode Coverage</h2>
            <div class="table-container">
                <table class="table table-striped table-hover" id="coverageTable">
                    <thead class="table-dark">
                        <tr>
                            <th>Opcode</th>
                            <th>Type</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_coverage_rows()}
                    </tbody>
                </table>
            </div>
            
            <h2>Raw Data</h2>
            <p>The complete dataset is available in CSV format:</p>
            <ul>
                <li><a href="opcode_gas_units.csv">Raw opcode gas units data</a></li>
                <li><a href="opcode_statistics.csv">Opcode statistics</a></li>
                <li><a href="opcode_coverage.csv">Opcode coverage data</a></li>
            </ul>
        </div>
    """
    
    # Combine HTML content with JavaScript
    full_html = html_content + js_code + "\n    </body>\n</html>"
    
    # Write HTML to file
    html_file = 'opcode_gas_analysis.html'
    with open(html_file, 'w') as f:
        f.write(full_html)
    
    print(f"HTML report generated: {html_file}")

def generate_table_rows(opcode_stats):
    """Generate HTML table rows from the opcode statistics DataFrame"""
    rows = []
    # Sort by mean gas units in descending order
    for opcode, row in opcode_stats.sort_values('mean', ascending=False).iterrows():
        # Check if mean is different from both min and max
        is_variable = row['mean'] != row['min'] and row['mean'] != row['max']
        
        # Apply red text class if gas cost is variable
        mean_class = ' class="text-danger fw-bold"' if is_variable else ''
        
        rows.append(f"""
        <tr>
            <td>{opcode}</td>
            <td>{int(row['count'])}</td>
            <td{mean_class}>{row['mean']:.6f}</td>
            <td>{row['min']:.6f}</td>
            <td>{row['max']:.6f}</td>
            <td>{row['sum']:.6f}</td>
        </tr>
        """)
    return '\n'.join(rows)

def generate_coverage_rows():
    """Generate HTML table rows for opcode coverage"""
    coverage_path = Path('opcode_coverage.csv')
    if not coverage_path.exists():
        return "<tr><td colspan='3'>Coverage data not available</td></tr>"
    
    try:
        coverage_df = pd.read_csv(coverage_path)
        rows = []
        
        for _, row in coverage_df.iterrows():
            status_class = "text-success" if row['Status'] == "Benchmarked" else "text-danger"
            
            rows.append(f"""
            <tr>
                <td>{row['Opcode']}</td>
                <td>{row['Type'] if 'Type' in row else 'Unknown'}</td>
                <td class="{status_class}">{row['Status']}</td>
            </tr>
            """)
        
        return '\n'.join(rows)
    except Exception as e:
        print(f"Error generating coverage rows: {e}")
        return f"<tr><td colspan='3'>Error loading coverage data: {e}</td></tr>"

def create_coverage_chart(coverage_data):
    """Create a visual coverage indicator for the HTML report"""
    total = coverage_data.sum()
    benchmarked = coverage_data.get('Benchmarked', 0)
    coverage_pct = (benchmarked / total) * 100 if total > 0 else 0
    
    return f"""
    <div class="card mb-3">
        <div class="card-header">
            <h4>Opcode Coverage: {coverage_pct:.1f}%</h4>
        </div>
        <div class="card-body">
            <div class="coverage-indicator" style="--coverage-pct: {coverage_pct}%;"></div>
            <div class="d-flex justify-content-between mt-2">
                <div>
                    <span class="badge bg-success">Benchmarked: {benchmarked}</span>
                </div>
                <div>
                    <span class="badge bg-danger">Missing: {total - benchmarked}</span>
                </div>
            </div>
        </div>
    </div>
    """

def create_visualizations(df, opcode_stats):
    """Create visualizations and return them as base64 encoded strings"""
    plot_data = {}
    
    # Set the style for all plots
    plt.style.use('ggplot')
    
    # 1. Top gas-intensive opcodes (by average)
    plt.figure(figsize=(10, 6))
    top_opcodes = opcode_stats.sort_values('mean', ascending=False).head(15)
    ax = sns.barplot(x=top_opcodes.index, y=top_opcodes['mean'], palette='viridis')
    plt.title('Top 15 Gas-Intensive Opcodes (Average Cost)')
    plt.xlabel('Opcode')
    plt.ylabel('Average Gas Units')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    # Convert plot to base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plot_data['top_gas_intensive'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    # 2. Opcode frequency
    plt.figure(figsize=(10, 6))
    top_frequent = opcode_stats.sort_values('count', ascending=False).head(15)
    ax = sns.barplot(x=top_frequent.index, y=top_frequent['count'], palette='mako')
    plt.title('Top 15 Most Frequent Opcodes')
    plt.xlabel('Opcode')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    # Convert plot to base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plot_data['opcode_frequency'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    # 3. Gas distribution by opcode (boxplot)
    plt.figure(figsize=(12, 6))
    # Get top 10 opcodes by mean gas for better visualization
    top_gas_opcodes = opcode_stats.sort_values('mean', ascending=False).head(10).index.tolist()
    # Filter dataframe to only include these opcodes
    df_filtered = df[df['opcode'].isin(top_gas_opcodes)]
    # Create boxplot
    ax = sns.boxplot(x='opcode', y='gas_units', data=df_filtered, palette='Set3')
    plt.title('Gas Unit Distribution for Top 10 Gas-Intensive Opcodes')
    plt.xlabel('Opcode')
    plt.ylabel('Gas Units')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    # Convert plot to base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plot_data['gas_distribution'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return plot_data

if __name__ == "__main__":
    analyze_gas_profiling() 