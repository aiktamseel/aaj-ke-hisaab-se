import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar
import os
import sys

class CPIUpdater:
    def __init__(self, json_file_path="pk-cpi.json"):
        self.json_file_path = json_file_path
        self.url = "https://tradingeconomics.com/pakistan/consumer-price-index-cpi"
        
    def load_json_data(self):
        """Load existing JSON data from file"""
        try:
            with open(self.json_file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: JSON file '{self.json_file_path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in '{self.json_file_path}'.")
            sys.exit(1)
    
    def save_json_data(self, data):
        """Save updated data to JSON file"""
        try:
            with open(self.json_file_path, 'w') as file:
                json.dump(data, file, indent=2)
            print(f"Data successfully saved to '{self.json_file_path}'")
        except Exception as e:
            print(f"Error saving JSON file: {e}")
            sys.exit(1)
    
    def scrape_cpi_data(self):
        """Scrape CPI data from Trading Economics website"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(self.url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with CPI data
            table = soup.find('table', class_='table table-hover')
            if not table:
                raise ValueError("Could not find the CPI data table")
            
            # Find header row to identify column positions
            header_row = table.find('thead')
            if not header_row:
                raise ValueError("Could not find table header")
            
            header_cells = header_row.find_all('th')
            column_mapping = {}
            
            for i, cell in enumerate(header_cells):
                header_text = cell.get_text(strip=True).lower()
                if 'last' in header_text:
                    column_mapping['last'] = i
                elif 'previous' in header_text:
                    column_mapping['previous'] = i
                elif 'reference' in header_text:
                    column_mapping['reference'] = i
            
            # Verify we found all required columns
            required_columns = ['last', 'previous', 'reference']
            missing_columns = [col for col in required_columns if col not in column_mapping]
            if missing_columns:
                raise ValueError(f"Could not find columns: {missing_columns}")
            
            print(f"Column mapping: {column_mapping}")
            
            # Find the row containing "Consumer Price Index CPI"
            rows = table.find_all('tr')
            cpi_row = None
            
            for row in rows:
                cells = row.find_all('td')
                if cells and len(cells) > max(column_mapping.values()):
                    first_cell = cells[0].get_text(strip=True)
                    if "Consumer Price Index CPI" in first_cell:
                        cpi_row = row
                        break
            
            if not cpi_row:
                raise ValueError("Could not find Consumer Price Index CPI row")
            
            # Extract data using the identified column positions
            cells = cpi_row.find_all('td')
            last_value = float(cells[column_mapping['last']].get_text(strip=True))
            previous_value = float(cells[column_mapping['previous']].get_text(strip=True))
            reference_date = cells[column_mapping['reference']].get_text(strip=True)
            
            return {
                'last_value': last_value,
                'previous_value': previous_value,
                'reference_date': reference_date
            }
            
        except requests.RequestException as e:
            print(f"Error fetching data from website: {e}")
            print("This might be due to network issues or website changes.")
            print("Please check the website manually and verify the script is working correctly.")
            sys.exit(1)
        except ValueError as e:
            print(f"Error parsing data: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during scraping: {e}")
            sys.exit(1)
    
    def parse_reference_date(self, reference_date):
        """Parse reference date string (e.g., 'Aug 2025') to get current and previous months"""
        try:
            # Parse the reference date
            date_parts = reference_date.split()
            month_str = date_parts[0]
            year = int(date_parts[1])
            
            # Convert month abbreviation to number
            month_num = datetime.strptime(month_str, '%b').month
            
            # Current month
            current_month = f"{year}-{month_num:02d}"
            
            # Calculate previous month
            if month_num == 1:
                prev_month = f"{year-1}-12"
            else:
                prev_month = f"{year}-{month_num-1:02d}"
            
            return current_month, prev_month
            
        except Exception as e:
            print(f"Error parsing reference date '{reference_date}': {e}")
            sys.exit(1)
    
    def validate_cpi_values(self, current_value, previous_value):
        """Validate that CPI values are reasonable"""
        # Check if current value dropped by more than 100 points from previous month
        if current_value < previous_value - 100:
            raise ValueError(
                f"CPI value dropped by {previous_value - current_value:.2f} points "
                f"(from {previous_value} to {current_value}). This seems unrealistic and likely indicates an error."
            )
        
        # Additional validation: check if values are positive
        if current_value <= 0 or previous_value <= 0:
            raise ValueError(f"CPI values must be positive. Got current: {current_value}, previous: {previous_value}")
        
        print(f"CPI values validated: Previous={previous_value}, Current={current_value}")
    
    def validate_and_update_monthly_data(self, data, current_month, prev_month, current_value, previous_value):
        """Validate and update monthly CPI data"""
        # First validate the CPI values for reasonableness
        self.validate_cpi_values(current_value, previous_value)
        
        monthly_data = data.get('monthly', {})
        
        # Check if previous month data exists and validate
        if prev_month in monthly_data:
            existing_prev_value = monthly_data[prev_month]
            if abs(existing_prev_value - previous_value) > 0.01:  # Allow small floating point differences
                raise ValueError(f"Previous month value mismatch: existing {existing_prev_value} vs scraped {previous_value}")
            print(f"Previous month ({prev_month}) value validated: {previous_value}")
        else:
            # Add previous month data
            monthly_data[prev_month] = previous_value
            print(f"Added previous month data: {prev_month} = {previous_value}")
        
        # Check if current month data exists and validate or add
        if current_month in monthly_data:
            existing_current_value = monthly_data[current_month]
            if abs(existing_current_value - current_value) > 0.01:  # Allow small floating point differences
                print(f"Warning: Updating current month value from {existing_current_value} to {current_value}")
        
        # Add/update current month data
        monthly_data[current_month] = current_value
        print(f"Added/updated current month data: {current_month} = {current_value}")
        
        data['monthly'] = monthly_data
        return data
    
    def get_fiscal_year_for_month(self, year, month):
        """Get the fiscal year for a given month. 
        Fiscal year runs from July to June, so:
        - July 2024 to June 2025 is fiscal year 2025
        - January 2025 is part of fiscal year 2025
        - July 2025 is part of fiscal year 2026
        """
        if month >= 7:  # July onwards belongs to next fiscal year
            return year + 1
        else:  # January to June belongs to current fiscal year
            return year
    
    def calculate_fiscal_year_average_if_needed(self, data, current_month):
        """Calculate fiscal year average if the last completed fiscal year data is missing"""
        year, month = map(int, current_month.split('-'))
        yearly_data = data.get('yearly', {})
        
        # Determine which fiscal year we should check for completion
        if month >= 7:  # July onwards - previous fiscal year is complete
            # For July 2025 onwards, fiscal year 2025 (July 2024-June 2025) is complete
            fiscal_year_to_check = self.get_fiscal_year_for_month(year, month) - 1
        else:  # Before July - fiscal year from 2 years ago should be complete
            # For Jan-June 2025, fiscal year 2024 (July 2023-June 2024) is complete
            fiscal_year_to_check = self.get_fiscal_year_for_month(year, month) - 2
        
        print(f"Checking if fiscal year {fiscal_year_to_check} data exists...")
        
        # Check if this fiscal year's data already exists
        if str(fiscal_year_to_check) in yearly_data:
            print(f"Fiscal year {fiscal_year_to_check} data already exists: {yearly_data[str(fiscal_year_to_check)]}")
            return data
        
        print(f"Fiscal year {fiscal_year_to_check} data missing. Calculating...")
        
        # Calculate the fiscal year average
        data = self.calculate_fiscal_year_average(data, fiscal_year_to_check)
        return data
    
    def calculate_fiscal_year_average(self, data, fiscal_year):
        """Calculate fiscal year average for a specific fiscal year"""
        monthly_data = data.get('monthly', {})
        
        # Fiscal year: July (year-1) to June (year)
        fiscal_year_months = []
        
        # July to December of previous year
        for m in range(7, 13):
            month_key = f"{fiscal_year-1}-{m:02d}"
            fiscal_year_months.append(month_key)
        
        # January to June of fiscal year
        for m in range(1, 7):
            month_key = f"{fiscal_year}-{m:02d}"
            fiscal_year_months.append(month_key)
        
        # Collect values for fiscal year
        fiscal_year_values = []
        missing_months = []
        
        for month_key in fiscal_year_months:
            if month_key in monthly_data:
                fiscal_year_values.append(monthly_data[month_key])
            else:
                missing_months.append(month_key)
        
        if missing_months:
            print(f"Warning: Missing data for months: {missing_months}")
            print(f"Cannot calculate fiscal year {fiscal_year} average. Skipping yearly update.")
            return data
        
        if len(fiscal_year_values) != 12:
            print(f"Warning: Expected 12 months of data but found {len(fiscal_year_values)}. Skipping yearly update.")
            return data
        
        # Calculate average
        fiscal_year_average = sum(fiscal_year_values) / len(fiscal_year_values)
        
        # Update yearly data
        yearly_data = data.get('yearly', {})
        yearly_data[str(fiscal_year)] = round(fiscal_year_average, 4)
        data['yearly'] = yearly_data
        
        print(f"Added fiscal year {fiscal_year} average: {fiscal_year_average:.4f}")
        print(f"Calculated from {len(fiscal_year_values)} months: July {fiscal_year-1} to June {fiscal_year}")
        
        return data
    
    def update_metadata(self, data):
        """Update the lastUpdated field in metadata"""
        if 'metadata' not in data:
            data['metadata'] = {}
        
        data['metadata']['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
        return data
    
    def run(self):
        """Main execution function"""
        print("Starting CPI data update...")
        
        # Load existing JSON data
        print("Loading existing JSON data...")
        data = self.load_json_data()
        
        # Scrape new data from website
        print("Scraping data from Trading Economics...")
        scraped_data = self.scrape_cpi_data()
        
        print(f"Scraped data:")
        print(f"  Reference date: {scraped_data['reference_date']}")
        print(f"  Last value: {scraped_data['last_value']}")
        print(f"  Previous value: {scraped_data['previous_value']}")
        
        # Parse reference date to get current and previous months
        current_month, prev_month = self.parse_reference_date(scraped_data['reference_date'])
        print(f"Parsed months - Current: {current_month}, Previous: {prev_month}")
        
        # Validate and update monthly data
        print("Validating and updating monthly data...")
        data = self.validate_and_update_monthly_data(
            data, current_month, prev_month, 
            scraped_data['last_value'], scraped_data['previous_value']
        )
        
        # Calculate fiscal year average if needed (not just for June)
        data = self.calculate_fiscal_year_average_if_needed(data, current_month)
        
        # Update metadata
        data = self.update_metadata(data)
        
        # Save updated data
        self.save_json_data(data)
        
        print("CPI data update completed successfully!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Pakistan CPI data from Trading Economics')
    parser.add_argument('--file', '-f', default='pk-cpi.json', 
                       help='Path to the CPI JSON file (default: pk-cpi.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if not args.verbose:
        # Suppress some output for cleaner GitHub Actions logs
        pass
    
    updater = CPIUpdater(args.file)
    updater.run()

if __name__ == "__main__":
    main()