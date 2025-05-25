#!/usr/bin/env python3
"""
EuroMillions Lottery Analysis Tool

This script initializes the database and provides commands for data collection and analysis.
"""
import os
import sys
import logging
import argparse
import platform
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

from app.database import init_db, engine
from app.data_collection.lottery_results_client import LotteryResultsClient
from app.data_collection.processor import DataProcessor
from app.data_collection.historical_importer import import_all_historical_data as import_historical_data
from app.data_collection.kaggle_importer import import_kaggle_data
from app.data_collection.sample_data_generator import generate_sample_data
from app.models.base import Draw
from app.config import Config
from app.analysis.number_analyzer import NumberAnalyzer
from app.analysis.visualizer import AnalysisVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("euro_millions.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize the database with required tables."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

def collect_data(limit: int = 5):
    """Collect EuroMillions draw data from the Lottery Results API."""
    if not Config.LOTTERY_API_TOKEN:
        logger.error("LOTTERY_API_TOKEN is not set in environment variables")
        logger.info("Please register at https://www.lotteryresultsapi.com and set the LOTTERY_API_TOKEN in your .env file")
        return
    
    logger.info("Starting data collection from Lottery Results API...")
    
    client = LotteryResultsClient()
    with DataProcessor() as processor:
        # Get the latest draws (API has a max limit of 5 per request)
        max_limit = min(5, max(1, limit))  # Ensure limit is between 1 and 5
        logger.info(f"Fetching up to {max_limit} latest EuroMillions draws...")
        
        # First try to get the latest draw to check if API is working
        latest_draw = client.get_latest_draw('euromillions')
        if not latest_draw:
            logger.error("Failed to fetch the latest draw. Please check your API token and internet connection.")
            return
            
        logger.info(f"Latest draw date: {latest_draw.get('date')} with numbers: {latest_draw.get('numbers', 'N/A')}")
        
        # Now get the latest batch of draws
        latest_draws = client.get_latest_draws('euromillions', limit=max_limit)
        if not latest_draws:
            logger.error("No draws found in the API response")
            return
        
        logger.info(f"Retrieved {len(latest_draws)} draws from the API")
        
        # Process each draw
        processed_draws = []
        for draw_data in latest_draws:
            parsed_draw = LotteryResultsClient.parse_draw(draw_data)
            if parsed_draw:
                processed_draws.append(parsed_draw)
        
        if not processed_draws:
            logger.error("No valid draws to process after parsing")
            return
        
        logger.info(f"Successfully parsed {len(processed_draws)} draws")
        
        # Process the draws in batches to avoid memory issues
        batch_size = 5  # Small batch size since we have at most 5 draws
        total_processed = 0
        
        for i in range(0, len(processed_draws), batch_size):
            batch = processed_draws[i:i + batch_size]
            try:
                count = processor.process_draws(batch)
                total_processed += count
                logger.info(f"Processed batch of {len(batch)} draws ({total_processed} total so far)")
                
                # Log the first draw in the batch for verification
                if i == 0 and batch:
                    first_draw = batch[0]
                    logger.info(f"Sample processed draw - Date: {first_draw['draw_date']}, "
                                f"Numbers: {first_draw['ball1']} {first_draw['ball2']} {first_draw['ball3']} "
                                f"{first_draw['ball4']} {first_draw['ball5']} | {first_draw['lucky_star1']} {first_draw['lucky_star2']}")
            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)
    
    if total_processed > 0:
        logger.info(f"Data collection completed successfully. Processed {total_processed} draws.")
    else:
        logger.warning("No draws were processed. Check the logs for errors.")

def collect_all_historical_data():
    """Collect all historical EuroMillions draws from the Lottery Results API.
    
    This function attempts to collect all historical EuroMillions draws by making
    multiple requests to the API, fetching 5 draws at a time (API maximum limit).
    """
    if not Config.LOTTERY_API_TOKEN:
        logger.error("LOTTERY_API_TOKEN is not set in environment variables")
        logger.info("Please register at https://www.lotteryresultsapi.com and set the LOTTERY_API_TOKEN in your .env file")
        return
    
    logger.info("Starting historical data collection from Lottery Results API...")
    
    client = LotteryResultsClient()
    with DataProcessor() as processor:
        # First test the API connection with a single request
        latest_draw = client.get_latest_draw('euromillions')
        if not latest_draw:
            logger.error("Failed to connect to the API. Please check your API token and internet connection.")
            return
        
        # Parse the latest draw to get its date
        latest_parsed = LotteryResultsClient.parse_draw(latest_draw)
        if not latest_parsed:
            logger.error("Failed to parse the latest draw data.")
            return
            
        latest_date = latest_parsed['draw_date']
        logger.info(f"Latest draw date: {latest_date}")
        
        # The API allows fetching at most 5 draws at a time
        batch_size = 5
        total_processed = 0
        retry_count = 0
        max_retries = 3
        
        # Start by getting the oldest available data
        # We'll initially fetch multiple batches to get a larger dataset to work with
        initial_batches = 20  # This will get us 100 draws if all successful
        current_offset = 0
        
        logger.info(f"Fetching initial historical data, {batch_size} draws at a time...")
        
        # Fetch initial batches of historical data
        for batch_num in range(initial_batches):
            try:
                # Get a batch of draws with the current offset
                draws = client.get_latest_draws('euromillions', limit=batch_size)
                
                if not draws:
                    logger.warning(f"No draws returned for batch {batch_num}, offset {current_offset}")
                    # Try to continue with next batch
                    current_offset += batch_size
                    continue
                    
                # Parse the draws
                parsed_draws = []
                for draw_data in draws:
                    parsed_draw = LotteryResultsClient.parse_draw(draw_data)
                    if parsed_draw:
                        parsed_draws.append(parsed_draw)
                
                if not parsed_draws:
                    logger.warning(f"No valid draws after parsing in batch {batch_num}")
                    current_offset += batch_size
                    continue
                
                # Process the parsed draws
                count = processor.process_draws(parsed_draws)
                total_processed += count
                
                # Log progress
                logger.info(f"Batch {batch_num+1}/{initial_batches}: Processed {count} draws (total: {total_processed})")
                
                # If we didn't add any new draws, the database might already be up to date
                if count == 0:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.info("No new draws found after multiple attempts. Database may already be up to date.")
                        break
                else:
                    # Reset retry count if we successfully added draws
                    retry_count = 0
                    
                # Increment offset for next batch
                current_offset += batch_size
                
                # Add a small delay to avoid hitting API rate limits
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Maximum retry count reached. Stopping data collection.")
                    break
                # Continue with next batch after an error
                current_offset += batch_size
                time.sleep(2)  # Longer delay after an error
        
        if total_processed > 0:
            logger.info(f"Historical data collection completed. Processed {total_processed} draws.")
        else:
            logger.warning("No historical draws were processed. Check the logs for errors.")
        
        # Display a summary of the database status
        try:
            earliest_draw = processor.db.query(Draw).order_by(Draw.draw_date.asc()).first()
            latest_draw = processor.db.query(Draw).order_by(Draw.draw_date.desc()).first()
            total_draws = processor.db.query(Draw).count()
            
            if earliest_draw and latest_draw:
                logger.info(f"Database summary:")
                logger.info(f"  - Total draws: {total_draws}")
                logger.info(f"  - Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
                print(f"\nDatabase now contains {total_draws} EuroMillions draws")
                print(f"From {earliest_draw.draw_date} to {latest_draw.draw_date}")
        except Exception as e:
            logger.error(f"Error getting database summary: {e}")


def view_latest_draws(limit: int = 10):
    """View the latest EuroMillions draws from the database."""
    from sqlalchemy.orm import Session
    from app.models.base import Draw
    
    logger.info(f"Retrieving the latest {limit} draws from the database...")
    
    with Session(engine) as session:
        # Query the latest draws ordered by date
        draws = session.query(Draw).order_by(Draw.draw_date.desc()).limit(limit).all()
        
        if not draws:
            logger.info("No draws found in the database")
            return
        
        # Display the draws in a table format
        print("\n" + "=" * 80)
        print(f"LATEST {len(draws)} EUROMILLIONS DRAWS")
        print("=" * 80)
        print(f"{'Date':<12} {'Numbers':<25} {'Lucky Stars':<12}")
        print("-" * 80)
        
        for draw in draws:
            numbers = f"{draw.ball1:2d} {draw.ball2:2d} {draw.ball3:2d} {draw.ball4:2d} {draw.ball5:2d}"
            lucky_stars = f"{draw.lucky_star1:2d} {draw.lucky_star2:2d}"
            print(f"{draw.draw_date.strftime('%Y-%m-%d'):<12} {numbers:<25} {lucky_stars:<12}")
        
        print("=" * 80)
        logger.info(f"Successfully displayed {len(draws)} draws")

def analyze_numbers(time_period: str):
    """Analyze EuroMillions numbers for the specified time period.
    
    Args:
        time_period: Time period for analysis ('all', 'year', '6months', '3months')
    """
    logger.info(f"Analyzing EuroMillions numbers for time period: {time_period}")
    
    analyzer = NumberAnalyzer()
    main_numbers_freq, lucky_stars_freq = analyzer.analyze_number_frequency(time_period)
    
    # Display the analysis using the visualizer
    AnalysisVisualizer.print_frequency_analysis(main_numbers_freq, lucky_stars_freq, time_period)

def show_hot_cold_numbers(time_period: str):
    """Show hot and cold EuroMillions numbers for the specified time period.
    
    Args:
        time_period: Time period for analysis ('all', 'year', '6months', '3months')
    """
    logger.info(f"Showing hot and cold EuroMillions numbers for time period: {time_period}")
    
    analyzer = NumberAnalyzer()
    main_numbers_freq, lucky_stars_freq = analyzer.analyze_number_frequency(time_period)
    
    # Get hot and cold numbers
    hot_main = sorted([n for n, data in main_numbers_freq.items() if data['status'] == 'hot'], 
                   key=lambda x: main_numbers_freq[x]['count'], reverse=True)
    cold_main = sorted([n for n, data in main_numbers_freq.items() if data['status'] == 'cold'], 
                    key=lambda x: main_numbers_freq[x]['count'])
                    
    hot_stars = sorted([n for n, data in lucky_stars_freq.items() if data['status'] == 'hot'], 
                     key=lambda x: lucky_stars_freq[x]['count'], reverse=True)
    cold_stars = sorted([n for n, data in lucky_stars_freq.items() if data['status'] == 'cold'], 
                      key=lambda x: lucky_stars_freq[x]['count'])
    
    # Create a summary
    summary = {
        'hottest_main_numbers': hot_main,
        'coldest_main_numbers': cold_main,
        'hottest_lucky_stars': hot_stars,
        'coldest_lucky_stars': cold_stars,
        'total_draws_analyzed': len(analyzer.draws_df),
        'date_range': {
            'first_draw': analyzer.draws_df['draw_date'].min().strftime('%Y-%m-%d'),
            'last_draw': analyzer.draws_df['draw_date'].max().strftime('%Y-%m-%d')
        }
    }
    
    # Display the summary
    AnalysisVisualizer.print_summary(summary)

def visualize_frequencies(time_period: str, open_chart: bool = False):
    """Visualize EuroMillions number frequencies for the specified time period.
    
    Args:
        time_period: Time period for visualization ('all', 'year', '6months', '3months')
        open_chart: Whether to open the chart after creating it
    """
    logger.info(f"Visualizing EuroMillions number frequencies for time period: {time_period}")
    
    analyzer = NumberAnalyzer()
    chart_path = analyzer.visualize_number_frequency(time_period)
    
    print(f"\nVisualization saved to: {chart_path}")
    
    if open_chart and chart_path:
        try:
            # Open the chart file with the default application
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', chart_path])
            elif platform.system() == 'Windows':
                os.startfile(chart_path)
            else:  # Linux
                subprocess.call(['xdg-open', chart_path])
                
            print("Opening chart...")
        except Exception as e:
            logger.error(f"Error opening chart: {e}")
            print(f"Could not open chart automatically. Please open it manually at: {chart_path}")

def get_recommendations(strategy: str, time_period: str, lookback: int = 10):
    """Get EuroMillions number recommendations based on the specified strategy.
    
    Args:
        strategy: Strategy for number selection ('hot', 'cold', 'balanced', 'mixed', 'ml')
        time_period: Time period for analysis ('all', 'year', '6months', '3months')
        lookback: For ML strategy, number of previous draws to use in pattern recognition
    """
    logger.info(f"Getting EuroMillions number recommendations using strategy: {strategy}, time period: {time_period}, lookback: {lookback}")
    
    analyzer = NumberAnalyzer()
    
    if strategy == 'ml':
        # Use machine learning prediction
        prediction = analyzer.generate_prediction_model(lookback_periods=lookback)
        if prediction['success']:
            recommendations = [{
                'main_numbers': prediction['main_numbers'],
                'lucky_stars': prediction['lucky_stars'],
                'strategy': 'Machine Learning',
                'time_period': f"Lookback: {prediction['lookback_periods']} draws",
                'type': 'prediction'
            }]
        else:
            logger.error(f"ML prediction failed: {prediction.get('error', 'Unknown error')}")
            print(f"ML prediction failed: {prediction.get('error', 'Unknown error')}")
            return
    else:
        # Use frequency-based recommendation
        recommendation = analyzer.get_hot_cold_recommendations(time_period, strategy)
        recommendations = [recommendation]
    
    # Display the recommendations
    AnalysisVisualizer.print_recommendations(recommendations)

def run_full_analysis(open_charts: bool = False):
    """Run a full EuroMillions analysis with charts and predictions.
    
    Args:
        open_charts: Whether to open charts after creating them
    """
    logger.info("Running full EuroMillions analysis")
    
    analyzer = NumberAnalyzer()
    analysis_results = analyzer.generate_complete_analysis()
    
    # Display the full analysis
    AnalysisVisualizer.display_full_analysis(analysis_results)
    
    if open_charts:
        try:
            # Open each chart
            for chart_path in analysis_results['charts'].values():
                if chart_path:
                    if platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', chart_path])
                    elif platform.system() == 'Windows':
                        os.startfile(chart_path)
                    else:  # Linux
                        subprocess.call(['xdg-open', chart_path])
            
            print("\nOpening charts...")
        except Exception as e:
            logger.error(f"Error opening charts: {e}")
            print(f"Could not open charts automatically. Please open them manually.")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="EuroMillions Data Analysis Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Initialize database command
    init_parser = subparsers.add_parser("init", help="Initialize the database")
    
    # Data collection command
    collect_parser = subparsers.add_parser("collect", help="Collect latest lottery data")
    collect_parser.add_argument("--limit", type=int, default=5, help="Maximum number of draws to collect (max 5)")
    
    # Historical data collection command
    collect_all_parser = subparsers.add_parser("collect-all", help="Collect all historical EuroMillions draws from API")
    
    # Import historical data command using web scraping
    import_historical_parser = subparsers.add_parser("import-historical", help="Import all historical EuroMillions draws using web scraping")
    
    # Import data from Kaggle dataset
    import_kaggle_parser = subparsers.add_parser("import-kaggle", help="Import EuroMillions data from Kaggle dataset")
    
    # Generate sample data
    generate_data_parser = subparsers.add_parser("generate-data", help="Generate sample EuroMillions data for testing")
    
    # View latest draws command
    view_parser = subparsers.add_parser("view", help="View latest draws from database")
    view_parser.add_argument("--limit", type=int, default=10, help="Maximum number of draws to display")
    
    # Analysis commands
    analyze_parser = subparsers.add_parser("analyze", help="Analyze EuroMillions numbers")
    analyze_parser.add_argument("--time-period", type=str, choices=['3months', '6months', 'year', '10years', 'all'], 
                               default='all', help="Time period for analysis")
    
    # Hot and cold numbers command
    hot_cold_parser = subparsers.add_parser("hot-cold", help="Show hot and cold EuroMillions numbers")
    hot_cold_parser.add_argument("--time-period", type=str, choices=['3months', '6months', 'year', '10years', 'all'], 
                               default='all', help="Time period for analysis")
    
    # Visualize number frequency command
    visualize_parser = subparsers.add_parser("visualize", help="Visualize EuroMillions number frequencies")
    visualize_parser.add_argument("--time-period", type=str, choices=['3months', '6months', 'year', '10years', 'all'], 
                               default='all', help="Time period for visualization")
    visualize_parser.add_argument("--open", action='store_true', help="Open the visualization after creating it")
    
    # Get recommendations command
    recommend_parser = subparsers.add_parser("recommend", help="Get EuroMillions number recommendations")
    recommend_parser.add_argument("--strategy", type=str, choices=['hot', 'cold', 'balanced', 'mixed', 'ml'], 
                                default='balanced', help="Strategy for number selection")
    recommend_parser.add_argument("--time-period", type=str, choices=['3months', '6months', 'year', '10years', 'all'], 
                               default='3months', help="Time period for analysis")
    recommend_parser.add_argument("--lookback", type=int, default=10, 
                               help="For ML strategy only: Number of previous draws to use in pattern recognition (default: 10)")
    
    # Full analysis command
    full_analysis_parser = subparsers.add_parser("full-analysis", help="Run full EuroMillions analysis with charts and predictions")
    full_analysis_parser.add_argument("--open-charts", action='store_true', help="Open charts after creating them")
    
    args = parser.parse_args()
    
    if args.command == "init":
        logger.info("Initializing database...")
        initialize_database()
    elif args.command == "collect":
        collect_data(args.limit)
    elif args.command == "collect-all":
        collect_all_historical_data()
    elif args.command == "import-historical":
        import_historical_data()
    elif args.command == "import-kaggle":
        import_kaggle_data()
    elif args.command == "generate-data":
        generate_sample_data()
    elif args.command == "view":
        view_latest_draws(args.limit)
    elif args.command == "analyze":
        analyze_numbers(args.time_period)
    elif args.command == "hot-cold":
        show_hot_cold_numbers(args.time_period)
    elif args.command == "visualize":
        visualize_frequencies(args.time_period, args.open)
    elif args.command == "recommend":
        get_recommendations(args.strategy, args.time_period, args.lookback)
    elif args.command == "full-analysis":
        run_full_analysis(args.open_charts)
    else:
        parser.print_help()

if __name__ == "__main__":
    from datetime import datetime  # Moved here to avoid circular import
    main()
