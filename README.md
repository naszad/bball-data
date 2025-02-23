# College Basketball Data Analysis and Visualization Tool

This Python application collects, analyzes, and visualizes college basketball data through an interactive GUI interface. It provides comprehensive insights into team performance, game statistics, and betting information by leveraging the College Basketball Data API.

The tool offers a user-friendly interface for analyzing basketball statistics with multiple visualization options. Users can explore various aspects of college basketball data including team performance metrics, game outcomes, and betting trends. The application features a modular design with separate data collection and visualization components, making it easy to gather fresh data and analyze it through an intuitive graphical interface.

## Repository Structure
```
.
├── basketball_data.py    # Core data collection module with API integration and progress tracking
├── gui.py               # Data visualization interface with interactive charts and statistics
└── requirements.txt     # Project dependencies and version specifications
```

## Usage Instructions
### Prerequisites
- Python 3.x
- College Basketball Data API key (must be set in `.env` file)
- System with GUI capabilities (Tkinter support)

### Installation
1. Clone the repository
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your API key:
```
API_KEY=your_api_key_here
```

### Quick Start
1. Run the data collection script:
```bash
python basketball_data.py
```
2. Enter the number of teams to analyze when prompted (or leave blank for all teams)
3. Launch the visualization interface:
```bash
python gui.py
```

### More Detailed Examples
#### Analyzing Team Statistics
1. Navigate to the "Team Stats" tab
2. Select a specific team from the dropdown menu
3. View various visualizations including:
   - Win/loss records
   - Points per game distribution
   - Performance trends

#### Exploring Betting Data
1. Open the "Betting Lines" tab
2. Filter data by team or date range
3. Analyze betting trends and distributions

### Troubleshooting
#### API Connection Issues
- **Problem**: "API key not found" error
  - Verify `.env` file exists in project root
  - Confirm API key is correctly formatted
  - Check file permissions

#### Data Loading Errors
- **Problem**: "No data found in data_output directory"
  - Run `basketball_data.py` first to collect data
  - Verify write permissions in project directory
  - Check for error messages in `basketball_data.log`

#### GUI Display Issues
- **Problem**: Graphs not displaying
  - Ensure Tkinter is properly installed
  - Check system's display capabilities
  - Verify data files exist in `data_output` directory

## Data Flow
The application processes data in two main stages: collection and visualization. Data is fetched from the College Basketball Data API, processed into standardized formats, and stored locally for visualization.

```ascii
[API] --> [Data Collection] --> [Local Storage] --> [GUI Visualization]
     basketball_data.py    data_output/*.json         gui.py
```

Key component interactions:
1. `basketball_data.py` authenticates with API using environment variables
2. Data is collected with progress tracking and error handling
3. Processed data is saved as JSON files in `data_output` directory
4. `gui.py` loads data files and creates interactive visualizations
5. User interactions trigger dynamic updates to visualizations
6. Error handling ensures graceful failure if data is missing or corrupt
7. Progress tracking provides feedback during long operations
8. Data transformations maintain consistency across components