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
            # Sort missing_df by Type first, then by Opcode for consistent display
            missing_df = missing_df.sort_values(by=['Type', 'Opcode'])
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
            
            // Add table sorting functionality
            const table = document.querySelector('#coverageTable');
            const headers = table.querySelectorAll('th');
            
            headers.forEach((header, index) => {
                header.style.cursor = 'pointer';
                header.setAttribute('data-sortable', 'true');
                header.setAttribute('data-sort-direction', 'none');
                header.addEventListener('click', () => {
                    sortTable(table, index);
                });
                
                // Add sort indicators
                const span = document.createElement('span');
                span.className = 'ms-1';
                span.innerHTML = '↕';
                header.appendChild(span);
            });
            
            function sortTable(table, columnIndex) {
                const header = headers[columnIndex];
                const direction = header.getAttribute('data-sort-direction');
                const newDirection = direction === 'asc' ? 'desc' : 'asc';
                
                // Reset all headers
                headers.forEach(h => {
                    h.setAttribute('data-sort-direction', 'none');
                    h.querySelector('span').innerHTML = '↕';
                });
                
                // Set new direction and indicator
                header.setAttribute('data-sort-direction', newDirection);
                header.querySelector('span').innerHTML = newDirection === 'asc' ? '↑' : '↓';
                
                // Get rows and sort
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                const sortedRows = rows.sort((a, b) => {
                    const aVal = a.cells[columnIndex].textContent.trim();
                    const bVal = b.cells[columnIndex].textContent.trim();
                    
                    return newDirection === 'asc' 
                        ? aVal.localeCompare(bVal) 
                        : bVal.localeCompare(aVal);
                });
                
                // Clear and append rows
                while (tbody.firstChild) {
                    tbody.removeChild(tbody.firstChild);
                }
                
                sortedRows.forEach(row => tbody.appendChild(row));
            }
            
            const tableContainer = document.querySelector('#coverageTable').parentNode;
            tableContainer.insertBefore(searchInput, document.querySelector('#coverageTable'));
            tableContainer.insertBefore(filterDiv, document.querySelector('#coverageTable'));
            
            // Setup tabs for opcode group details
            const tabButtons = document.querySelectorAll('.nav-tabs .nav-link');
            const tabContents = document.querySelectorAll('.tab-pane');
            
            tabButtons.forEach(button => {
                button.addEventListener('click', () => {
                    const tabId = button.getAttribute('data-bs-target');
                    
                    // Deactivate all tab buttons and contents
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active', 'show'));
                    
                    // Activate selected tab
                    button.classList.add('active');
                    document.querySelector(tabId).classList.add('active', 'show');
                });
            });
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
            .tabs-container .nav-link {{
                cursor: pointer;
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

            <h2>Opcode Group Analysis</h2>
            <div class="row">
                {'<div class="col-md-6"><div class="card"><div class="card-header"><h3>Average Gas by Opcode Type</h3></div><div class="card-body"><img src="data:image/png;base64,' + plot_data.get('gas_by_type', '') + '" class="plot-img" alt="Average Gas by Opcode Type"></div></div></div>' if 'gas_by_type' in plot_data else ''}
                {'<div class="col-md-6"><div class="card"><div class="card-header"><h3>Frequency by Opcode Type</h3></div><div class="card-body"><img src="data:image/png;base64,' + plot_data.get('count_by_type', '') + '" class="plot-img" alt="Frequency by Opcode Type"></div></div></div>' if 'count_by_type' in plot_data else ''}
            </div>
            
            <div class="row">
                {'<div class="col-12"><div class="card"><div class="card-header"><h3>Coverage by Opcode Type</h3></div><div class="card-body"><img src="data:image/png;base64,' + plot_data.get('coverage_by_type', '') + '" class="plot-img" alt="Coverage by Opcode Type"></div></div></div>' if 'coverage_by_type' in plot_data else ''}
            </div>

            <h2>Gas Usage by Opcode Type</h2>
            <div class="card">
                <div class="card-header">
                    <h3>Gas Usage for Opcodes by Group</h3>
                </div>
                <div class="card-body">
                    <div class="tabs-container">
                        <ul class="nav nav-tabs" role="tablist">
                            {generate_opcode_group_tabs(plot_data)}
                        </ul>
                        
                        <div class="tab-content mt-3">
                            {generate_opcode_group_content(plot_data)}
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
        # Sort the dataframe by Type column first, then by Opcode
        coverage_df = coverage_df.sort_values(by=['Type', 'Opcode'])
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
    
    # 4. Group-based visualizations
    try:
        # Load the opcode types from all_opcodes.csv
        all_opcodes_path = Path('all_opcodes.csv')
        if not all_opcodes_path.exists():
            all_opcodes_path = Path('add/all_opcodes.csv')
            
        if all_opcodes_path.exists():
            # Read the CSV with opcode types
            opcode_types_df = pd.read_csv(all_opcodes_path)
            
            # Ensure the Opcode and Type columns exist
            if 'Opcode' in opcode_types_df.columns and 'Type' in opcode_types_df.columns:
                # Convert opcodes to lowercase for consistent comparison
                opcode_types_df['Opcode'] = opcode_types_df['Opcode'].str.lower()
                
                # Create mapping of opcode to type
                opcode_to_type = dict(zip(opcode_types_df['Opcode'].str.lower(), opcode_types_df['Type']))
                
                # Add type to opcode_stats
                opcode_stats['type'] = opcode_stats.index.map(lambda x: opcode_to_type.get(x.lower(), 'Unknown'))
                
                # 4.1 Average gas by opcode type
                plt.figure(figsize=(10, 6))
                type_gas = opcode_stats.groupby('type')['mean'].mean().sort_values(ascending=False)
                ax = sns.barplot(x=type_gas.index, y=type_gas.values, palette='viridis')
                plt.title('Average Gas Cost by Opcode Type')
                plt.xlabel('Opcode Type')
                plt.ylabel('Average Gas Units')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100)
                buffer.seek(0)
                plot_data['gas_by_type'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()
                
                # 4.2 Count by opcode type
                plt.figure(figsize=(10, 6))
                type_count = opcode_stats.groupby('type')['count'].sum().sort_values(ascending=False)
                ax = sns.barplot(x=type_count.index, y=type_count.values, palette='mako')
                plt.title('Frequency of Opcodes by Type')
                plt.xlabel('Opcode Type')
                plt.ylabel('Count')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100)
                buffer.seek(0)
                plot_data['count_by_type'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()
                
                # 4.3 Coverage by opcode type
                plt.figure(figsize=(10, 6))
                
                # Load coverage data if available
                coverage_path = Path('opcode_coverage.csv')
                if coverage_path.exists():
                    coverage_df = pd.read_csv(coverage_path)
                    coverage_df['Opcode'] = coverage_df['Opcode'].str.lower()
                    
                    # Merge with type information
                    coverage_df['Type'] = coverage_df['Opcode'].map(opcode_to_type)
                    
                    # Group by type and status
                    type_coverage = coverage_df.groupby(['Type', 'Status']).size().unstack(fill_value=0)
                    
                    if 'Benchmarked' in type_coverage.columns and 'Missing' in type_coverage.columns:
                        # Calculate coverage percentage
                        type_coverage['Total'] = type_coverage['Benchmarked'] + type_coverage['Missing']
                        type_coverage['Percentage'] = (type_coverage['Benchmarked'] / type_coverage['Total']) * 100
                        
                        # Sort by percentage
                        type_coverage = type_coverage.sort_values('Percentage', ascending=False)
                        
                        # Plot
                        ax = sns.barplot(x=type_coverage.index, y=type_coverage['Percentage'], palette='RdYlGn')
                        plt.title('Coverage Percentage by Opcode Type')
                        plt.xlabel('Opcode Type')
                        plt.ylabel('Coverage (%)')
                        plt.xticks(rotation=45, ha='right')
                        
                        # Add count labels
                        for i, (_, row) in enumerate(type_coverage.iterrows()):
                            plt.text(i, row['Percentage'] + 2, 
                                    f"{row['Benchmarked']}/{row['Total']}", 
                                    ha='center', va='bottom', fontsize=9)
                        
                        plt.ylim(0, 110)  # Give space for labels
                        plt.tight_layout()
                        buffer = BytesIO()
                        plt.savefig(buffer, format='png', dpi=100)
                        buffer.seek(0)
                        plot_data['coverage_by_type'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        plt.close()
                
                # 4.4 Gas usage for opcodes within each group
                # Get a list of opcode types that have at least one benchmarked opcode
                types_with_benchmarks = opcode_stats[~opcode_stats['type'].isnull() & 
                                              (opcode_stats['type'] != 'Unknown')]['type'].unique()
                
                # For each type, create a graph showing gas usage for its opcodes
                for opcode_type in types_with_benchmarks:
                    # Get opcodes for this type
                    type_opcodes = opcode_stats[opcode_stats['type'] == opcode_type]
                    
                    # Skip if there are no or too few opcodes
                    if len(type_opcodes) < 2:
                        continue
                    
                    # Sort by mean gas
                    type_opcodes_sorted = type_opcodes.sort_values('mean', ascending=False)
                    
                    # Create visualization (limit to top 15 for readability if needed)
                    plt.figure(figsize=(12, 6))
                    
                    # Adjust figure height based on number of opcodes 
                    fig_height = max(6, min(len(type_opcodes_sorted) * 0.4, 12))
                    plt.figure(figsize=(10, fig_height))
                    
                    # Plot
                    ax = sns.barplot(x='mean', y=type_opcodes_sorted.index, 
                                data=type_opcodes_sorted, palette='viridis', orient='h')
                    
                    plt.title(f'Gas Cost for {opcode_type} Opcodes')
                    plt.ylabel('Opcode')
                    plt.xlabel('Average Gas Units')
                    plt.tight_layout()
                    
                    # Add gas value labels 
                    for i, v in enumerate(type_opcodes_sorted['mean']):
                        ax.text(v + v*0.01, i, f"{v:.6f}", va='center')
                    
                    # Save
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=100)
                    buffer.seek(0)
                    plot_data[f'gas_by_{opcode_type.replace(" & ", "_").replace(" ", "_").lower()}'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    plt.close()
    except Exception as e:
        print(f"Error creating group-based visualizations: {e}")
    
    return plot_data

def generate_opcode_group_tabs(plot_data):
    """Generate HTML tabs for opcode groups"""
    tabs = []
    
    # Extract group names from plot_data keys
    group_plots = [k for k in plot_data.keys() if k.startswith('gas_by_')]
    
    # If no group plots are available, return empty string
    if not group_plots:
        return ""
    
    # Add tabs for each group
    for i, plot_key in enumerate(sorted(group_plots)):
        # Extract group name from plot key
        group_name = plot_key.replace('gas_by_', '')
        # Beautify the name for display
        display_name = group_name.replace('_', ' ').title().replace('And', '&')
        
        # Create tab
        active_class = 'active' if i == 0 else ''
        tabs.append(f"""
        <li class="nav-item" role="presentation">
            <button class="nav-link {active_class}" id="tab-{group_name}" data-bs-toggle="tab" 
                    data-bs-target="#content-{group_name}" type="button" role="tab">{display_name}</button>
        </li>
        """)
    
    return '\n'.join(tabs)

def generate_opcode_group_content(plot_data):
    """Generate HTML content for opcode group tabs"""
    contents = []
    
    # Extract group names from plot_data keys
    group_plots = [k for k in plot_data.keys() if k.startswith('gas_by_')]
    
    # If no group plots are available, return empty string
    if not group_plots:
        return "<div class='alert alert-info'>No opcode group data available</div>"
    
    # Add content for each group
    for i, plot_key in enumerate(sorted(group_plots)):
        # Extract group name from plot key
        group_name = plot_key.replace('gas_by_', '')
        
        # Create content
        active_class = 'active show' if i == 0 else ''
        contents.append(f"""
        <div class="tab-pane fade {active_class}" id="content-{group_name}" role="tabpanel">
            <img src="data:image/png;base64,{plot_data[plot_key]}" class="plot-img" 
                 alt="Gas usage for opcodes in {group_name}">
        </div>
        """)
    
    return '\n'.join(contents)

if __name__ == "__main__":
    analyze_gas_profiling() 