# EuroMillions Lottery Analysis

A comprehensive tool for analyzing EuroMillions lottery data, identifying hot and cold numbers, visualizing patterns, and generating predictions using statistical analysis and machine learning.

## Features

- **Data Collection**: Multiple methods to gather EuroMillions draw data:
  - API integration with Lottery Results API
  - Web scraping from euro-millions.com
  - Sample data generation for testing

- **Database Storage**: Persistent SQLite database with SQLAlchemy ORM

- **Advanced Statistical Analysis**:
  - Hot and cold number identification
  - Frequency analysis with customizable time periods
  - Pattern recognition across historical draws

- **Data Visualization**:
  - Frequency charts for main numbers and lucky stars
  - Color-coded visualization of hot/cold numbers
  - Prediction performance analysis

- **Prediction Models**:
  - Multiple prediction strategies (hot, cold, balanced, mixed)
  - Machine learning model with adjustable lookback periods
  - Recommendations based on cross-strategy analysis

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/LotteryAnalysis.git
   cd LotteryAnalysis
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root based on the provided `.env.example`:
   ```
   LOTTERY_API_TOKEN=your_api_token_here
   EUROMILLIONS_MIN_YEAR=2004
   ```

## Usage

### Getting Started

1. Initialize the database:
   ```bash
   python main.py init
   ```

2. Choose a method to populate your database with EuroMillions data:

   ```bash
   # Method 1: Collect recent draws from Lottery Results API (limited to 5 draws)
   python main.py collect
   
   # Method 2: Collect all available API data
   python main.py collect-all
   
   # Method 3: Import historical data via web scraping
   python main.py import-historical
   
   # Method 4: Generate sample data spanning from 2004 to present
   python main.py generate-data
   ```

3. View the collected data:
   ```bash
   # Display the 10 most recent draws
   python main.py view
   
   # Adjust the number of draws displayed
   python main.py view --limit 20
   ```

### Analysis and Prediction

#### Hot and Cold Numbers Analysis
```bash
# Basic hot/cold analysis using all data
python main.py hot-cold

# Analysis for specific time periods
python main.py hot-cold --time-period 3months
python main.py hot-cold --time-period 6months
python main.py hot-cold --time-period year
python main.py hot-cold --time-period 10years
```

#### Detailed Frequency Analysis
```bash
# Detailed frequency analysis for all numbers
python main.py analyze

# Analysis for specific time periods
python main.py analyze --time-period 3months
```

#### Number Frequency Visualization
```bash
# Generate visualization charts
python main.py visualize

# Auto-open the generated chart
python main.py visualize --open

# Customize time period
python main.py visualize --time-period 6months --open
```

#### Number Recommendations
```bash
# Get balanced recommendations (default)
python main.py recommend

# Different recommendation strategies
python main.py recommend --strategy hot
python main.py recommend --strategy cold
python main.py recommend --strategy mixed

# Machine learning predictions
python main.py recommend --strategy ml

# ML with custom lookback period
python main.py recommend --strategy ml --lookback 100

# Combine strategy and time period
python main.py recommend --strategy hot --time-period year
```

#### Comprehensive Analysis
```bash
# Run full analysis with all charts and predictions
python main.py full-analysis

# Open generated charts automatically
python main.py full-analysis --open-charts
```

## Project Structure

```
LotteryAnalysis/
├── app/
│   ├── __init__.py
│   ├── analysis/          # Analysis and prediction modules
│   │   ├── __init__.py
│   │   ├── number_analyzer.py  # Hot/cold analysis and predictions
│   │   └── visualizer.py       # Terminal visualization
│   ├── data_collection/   # Data gathering and processing
│   │   ├── __init__.py
│   │   ├── historical_importer.py  # Web scraping functionality
│   │   ├── kaggle_importer.py      # Kaggle dataset import
│   │   ├── lottery_results_client.py  # API client
│   │   ├── processor.py              # Data processing
│   │   └── sample_data_generator.py  # Sample data generation
│   ├── models/            # Database models
│   │   ├── __init__.py
│   │   └── base.py        # SQLAlchemy models
│   └── database.py        # Database configuration
├── charts/                # Generated visualization charts
├── .env                   # Environment variables (create based on .env.example)
├── .env.example          # Example environment variables
├── .gitignore
├── euro_millions.log     # Application log file
├── main.py               # Main entry point
├── README.md
└── requirements.txt      # Project dependencies
```

## Key Prediction Strategies

### Hot Numbers Strategy
Recommends numbers that appear most frequently in historical draws, based on the theory that frequently drawn numbers might continue to appear often.

### Cold Numbers Strategy
Recommends numbers that appear least frequently, based on the theory of statistical correction (rarely drawn numbers may be "due" to appear).

### Balanced Strategy
Provides a mix of hot, warm, cool, and cold numbers, creating a balanced ticket that combines different frequency patterns.

### Mixed Strategy
Focuses on extreme frequencies only, combining the hottest and coldest numbers while avoiding medium-frequency numbers.

### Machine Learning Strategy
Uses RandomForest algorithm to analyze patterns in previous draws, with customizable lookback periods to adjust the historical window used for pattern recognition.

## Analysis Methodology

Numbers are classified into four categories based on their appearance frequency:

- **Hot Numbers**: Top 20% most frequently drawn numbers
- **Warm Numbers**: Next 30% (21-50% frequency range)
- **Cool Numbers**: Next 30% (51-80% frequency range)
- **Cold Numbers**: Bottom 20% least frequently drawn numbers

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This application is for educational and entertainment purposes only. Lottery games are games of chance, and no prediction system can guarantee winning numbers. The analyses and predictions provided by this tool are based on historical data and statistical methods, but past patterns do not guarantee future results. Please play responsibly and within your means.