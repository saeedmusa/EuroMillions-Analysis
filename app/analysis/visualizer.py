"""
Terminal-based visualizations for EuroMillions analysis.

This module provides colorful terminal output for analysis results.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from colorama import init, Fore, Back, Style
from tabulate import tabulate

# Initialize colorama for cross-platform colored terminal text
init()

logger = logging.getLogger(__name__)

class AnalysisVisualizer:
    """Terminal-based visualizer for lottery analysis results."""
    
    @staticmethod
    def print_header(title: str):
        """Print a styled header.
        
        Args:
            title: Header title text
        """
        width = 80
        print("\n" + "=" * width)
        print(f"{Fore.CYAN}{Style.BRIGHT}{title.center(width)}{Style.RESET_ALL}")
        print("=" * width)
    
    @staticmethod
    def print_subheader(title: str):
        """Print a styled subheader.
        
        Args:
            title: Subheader title text
        """
        width = 80
        print("\n" + "-" * width)
        print(f"{Fore.YELLOW}{title}{Style.RESET_ALL}")
        print("-" * width)
    
    @staticmethod
    def print_frequency_analysis(main_numbers: Dict[int, Dict], lucky_stars: Dict[int, Dict], time_period: str = 'all'):
        """Print frequency analysis results to terminal.
        
        Args:
            main_numbers: Dictionary of main number frequencies
            lucky_stars: Dictionary of lucky star frequencies
            time_period: Time period used for analysis
        """
        # Create a dictionary mapping status to color
        status_colors = {
            'hot': Fore.RED,
            'warm': Fore.YELLOW,
            'cool': Fore.BLUE,
            'cold': Fore.CYAN
        }
        
        AnalysisVisualizer.print_header(f"EuroMillions Number Frequency Analysis ({time_period})")
        
        # Main Numbers Table
        AnalysisVisualizer.print_subheader("Main Numbers (1-50)")
        
        main_table = []
        for i in range(1, 51):
            data = main_numbers.get(i, {'count': 0, 'percentage': 0, 'status': 'unknown'})
            status = data['status']
            color = status_colors.get(status, '')
            
            main_table.append([
                i,
                f"{color}{data['count']}{Style.RESET_ALL}",
                f"{color}{data['percentage']:.2f}%{Style.RESET_ALL}",
                f"{color}{status.upper()}{Style.RESET_ALL}"
            ])
            
            # Print 10 numbers per row
            if i % 10 == 0 or i == 50:
                print(tabulate(
                    main_table[-10:],
                    headers=["Number", "Count", "Frequency", "Status"],
                    tablefmt="simple"
                ))
                
                if i < 50:
                    print()
        
        # Lucky Stars Table
        AnalysisVisualizer.print_subheader("Lucky Stars (1-12)")
        
        star_table = []
        for i in range(1, 13):
            data = lucky_stars.get(i, {'count': 0, 'percentage': 0, 'status': 'unknown'})
            status = data['status']
            color = status_colors.get(status, '')
            
            star_table.append([
                i,
                f"{color}{data['count']}{Style.RESET_ALL}",
                f"{color}{data['percentage']:.2f}%{Style.RESET_ALL}",
                f"{color}{status.upper()}{Style.RESET_ALL}"
            ])
        
        print(tabulate(
            star_table,
            headers=["Number", "Count", "Frequency", "Status"],
            tablefmt="simple"
        ))
    
    @staticmethod
    def print_recommendations(recommendations: List[Dict[str, Any]]):
        """Print number recommendations to terminal.
        
        Args:
            recommendations: List of recommendation dictionaries
        """
        AnalysisVisualizer.print_header("EuroMillions Number Recommendations")
        
        for i, rec in enumerate(recommendations):
            rec_type = rec.get('type', 'frequency')
            strategy = rec.get('strategy', 'unknown')
            time_period = rec.get('time_period', 'unknown')
            
            print(f"\n{Fore.GREEN}Recommendation #{i+1}: {strategy} ({time_period}){Style.RESET_ALL}")
            
            main_numbers = rec.get('main_numbers', [])
            lucky_stars = rec.get('lucky_stars', [])
            
            # Format numbers
            main_str = ' '.join([f"{Fore.WHITE}{Back.RED}{num:2d}{Style.RESET_ALL}" for num in main_numbers])
            stars_str = ' '.join([f"{Fore.BLACK}{Back.YELLOW}{num:2d}{Style.RESET_ALL}" for num in lucky_stars])
            
            print(f"Main Numbers: {main_str}")
            print(f"Lucky Stars:  {stars_str}")
    
    @staticmethod
    def print_summary(summary: Dict[str, Any]):
        """Print overall analysis summary to terminal.
        
        Args:
            summary: Dictionary with summary information
        """
        AnalysisVisualizer.print_header("EuroMillions Analysis Summary")
        
        date_range = summary.get('date_range', {})
        total_draws = summary.get('total_draws_analyzed', 0)
        
        print(f"\n{Fore.CYAN}Data Overview:{Style.RESET_ALL}")
        print(f"• Total draws analyzed: {total_draws}")
        print(f"• Date range: {date_range.get('first_draw', 'N/A')} to {date_range.get('last_draw', 'N/A')}")
        
        print(f"\n{Fore.CYAN}Hottest Main Numbers:{Style.RESET_ALL}")
        hottest_main = summary.get('hottest_main_numbers', [])
        hottest_main_str = ', '.join([f"{Fore.RED}{num}{Style.RESET_ALL}" for num in hottest_main[:10]])
        print(f"• {hottest_main_str}")
        
        print(f"\n{Fore.CYAN}Coldest Main Numbers:{Style.RESET_ALL}")
        coldest_main = summary.get('coldest_main_numbers', [])
        coldest_main_str = ', '.join([f"{Fore.BLUE}{num}{Style.RESET_ALL}" for num in coldest_main[:10]])
        print(f"• {coldest_main_str}")
        
        print(f"\n{Fore.CYAN}Hottest Lucky Stars:{Style.RESET_ALL}")
        hottest_stars = summary.get('hottest_lucky_stars', [])
        hottest_stars_str = ', '.join([f"{Fore.RED}{num}{Style.RESET_ALL}" for num in hottest_stars])
        print(f"• {hottest_stars_str}")
        
        print(f"\n{Fore.CYAN}Coldest Lucky Stars:{Style.RESET_ALL}")
        coldest_stars = summary.get('coldest_lucky_stars', [])
        coldest_stars_str = ', '.join([f"{Fore.BLUE}{num}{Style.RESET_ALL}" for num in coldest_stars])
        print(f"• {coldest_stars_str}")
        
    @staticmethod
    def display_full_analysis(analysis_results: Dict[str, Any]):
        """Display full analysis results including charts and recommendations.
        
        Args:
            analysis_results: Dictionary with analysis results
        """
        summary = analysis_results.get('summary', {})
        recommendations = analysis_results.get('recommendations', [])
        charts = analysis_results.get('charts', {})
        
        # Print summary
        AnalysisVisualizer.print_summary(summary)
        
        # Print recommendations
        AnalysisVisualizer.print_recommendations(recommendations)
        
        # Print chart file paths
        AnalysisVisualizer.print_subheader("Generated Charts")
        for chart_name, chart_path in charts.items():
            if chart_path:
                print(f"• {chart_name}: {chart_path}")
                
        # Print message about opening chart files
        print(f"\n{Fore.GREEN}Tip: Open the chart image files to view detailed visualizations{Style.RESET_ALL}")
