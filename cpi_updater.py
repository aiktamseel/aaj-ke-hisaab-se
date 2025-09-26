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
            
            # Find the row containing "Consumer Price Index CPI"
            rows = table.find_all('tr')
            cpi_row = None
            
            for row in rows:
                cells = row.find_all('td')
                if cells and len(cells) >= 5:
                    first_cell = cells[0].get_text(strip=True)
                    if "Consumer Price Index CPI" in first_cell:
                        cpi_row = row
                        break
            
            if not cpi_row:
                raise ValueError("Could not find Consumer Price Index CPI row")
            
            # Extract data from the row
            cells = cpi_row.find_all('td')
            last_value = float(cells[1].get_text(strip=True))
            previous_value = float(cells[2].get_text(strip=True))
            reference_date = cells[4].get_text(strip=True)
            
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
    
    def validate_and_update_monthly_data(self, data, current_month, prev_month, current_value, previous_value):
        """Validate and update monthly CPI data"""
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
    
    def calculate_fiscal_year_average(self, data, current_month):
        """Calculate fiscal year average if current month is June"""
        year, month = map(int, current_month.split('-'))
        
        if month != 6:  # Not June
            return data
        
        print(f"Current month is June {year}. Calculating fiscal year average...")
        
        monthly_data = data.get('monthly', {})
        
        # Fiscal year: July (year-1) to June (year)
        fiscal_year_months = []
        
        # July to December of previous year
        for m in range(7, 13):
            month_key = f"{year-1}-{m:02d}"
            fiscal_year_months.append(month_key)
        
        # January to June of current year
        for m in range(1, 7):
            month_key = f"{year}-{m:02d}"
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
            print("Cannot calculate fiscal year average. Skipping yearly update.")
            return data
        
        # Calculate average
        fiscal_year_average = sum(fiscal_year_values) / len(fiscal_year_values)
        
        # Update yearly data
        yearly_data = data.get('yearly', {})
        yearly_data[str(year)] = round(fiscal_year_average, 4)
        data['yearly'] = yearly_data
        
        print(f"Added fiscal year {year} average: {fiscal_year_average:.4f}")
        print(f"Calculated from {len(fiscal_year_values)} months: July {year-1} to June {year}")
        
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
        
        # Calculate fiscal year average if current month is June
        data = self.calculate_fiscal_year_average(data, current_month)
        
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