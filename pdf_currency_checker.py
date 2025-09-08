#!/usr/bin/env python3
"""
PDF Currency Checker Script
Scans PDF files to identify whether amounts are in USD or MMK currency.
"""

import os
import re
import glob
import PyPDF2
from typing import List, Dict, Tuple
import json
from datetime import datetime

class PDFCurrencyChecker:
    def __init__(self):
        # Currency patterns and indicators
        self.usd_patterns = [
            r'\$\s*[\d,]+\.?\d*',  # $1,000.00 or $1000
            r'USD\s*[\d,]+\.?\d*',  # USD 1,000.00
            r'[\d,]+\.?\d*\s*USD',  # 1,000.00 USD
            r'US\$\s*[\d,]+\.?\d*',  # US$ 1,000.00
            r'[\d,]+\.?\d*\s*US\$',  # 1,000.00 US$
            r'[\d,]+\.?\d*\s*\$',  # 1,000.00 $
        ]
        
        self.mmk_patterns = [
            r'MMK\s*[\d,]+\.?\d*',  # MMK 1,000,000
            r'[\d,]+\.?\d*\s*MMK',  # 1,000,000 MMK
            r'Ks\s*[\d,]+\.?\d*',   # Ks 1,000,000 (Myanmar Kyat symbol)
            r'[\d,]+\.?\d*\s*Ks',   # 1,000,000 Ks
            r'Myanmar\s*Kyat\s*[\d,]+\.?\d*',  # Myanmar Kyat 1,000,000
            r'[\d,]+\.?\d*\s*Myanmar\s*Kyat',  # 1,000,000 Myanmar Kyat
            r'[\d,]+\.?\d*\s*kyat',  # 1,000,000 kyat (lowercase)
            r'kyat\s*[\d,]+\.?\d*',  # kyat 1,000,000
        ]
        
        self.currency_keywords = {
            'USD': ['USD', 'US$', '$', 'Dollar', 'Dollars', 'US Dollar', 'US Dollars'],
            'MMK': ['MMK', 'Ks', 'Kyat', 'Myanmar Kyat', 'Myanmar Kyats', 'Burmese Kyat']
        }
        
        self.results = []

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error reading {pdf_path}: {str(e)}")
            return ""

    def find_currency_amounts(self, text: str) -> Dict[str, List[str]]:
        """Find currency amounts in text and categorize by currency type."""
        currencies = {'USD': [], 'MMK': [], 'UNKNOWN': []}
        
        # First, check for table headers to determine the document's primary currency
        table_currency = self.detect_table_currency_headers(text)
        
        # Search for explicit USD patterns
        for pattern in self.usd_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount = match.group().strip()
                if self.is_likely_amount(amount):
                    currencies['USD'].append(amount)
        
        # Search for explicit MMK patterns
        for pattern in self.mmk_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount = match.group().strip()
                if self.is_likely_amount(amount):
                    currencies['MMK'].append(amount)
        
        # Look for amounts in table context if table headers indicate currency
        if table_currency:
            table_amounts = self.extract_table_amounts(text, table_currency)
            currencies[table_currency].extend(table_amounts)
        
        return currencies

    def detect_table_currency_headers(self, text: str) -> str:
        """Detect currency from table headers like 'Amount (USD)' or 'Amount (MMK)'."""
        # Look for table headers that specify currency
        header_patterns = [
            r'Amount\s*\(\s*USD\s*\)',   # Amount (USD)
            r'Amount\s*\(\s*US\$\s*\)',  # Amount (US$)
            r'Amount\s*\(\s*MMK\s*\)',   # Amount (MMK)
            r'Amount\s*\(\s*Ks\s*\)',    # Amount (Ks)
            r'Total\s*\(\s*USD\s*\)',    # Total (USD)
            r'Total\s*\(\s*MMK\s*\)',    # Total (MMK)
            r'Price\s*\(\s*USD\s*\)',    # Price (USD)
            r'Price\s*\(\s*MMK\s*\)',    # Price (MMK)
        ]
        
        for pattern in header_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header_text = match.group().lower()
                if 'usd' in header_text or 'us$' in header_text:
                    return 'USD'
                elif 'mmk' in header_text or 'ks' in header_text:
                    return 'MMK'
        
        return None
    
    def is_likely_amount(self, amount_str: str) -> bool:
        """Check if a string looks like a monetary amount rather than account number, etc."""
        # Remove currency symbols and whitespace
        clean_amount = re.sub(r'[^\d.,]', '', amount_str)
        
        # Skip if it's likely a bank account number or other identifier
        # Bank accounts usually have specific patterns
        if re.match(r'^\d{3,5}\s+\d{3,5}\s+\d{3,5}', amount_str):  # Format: 021 103 021
            return False
        
        if re.match(r'^\d{10,}$', clean_amount.replace(',', '')):  # Very long numbers
            return False
        
        # Must have decimal point or be reasonable amount
        if '.' in clean_amount:
            return True
        
        # For whole numbers, check if reasonable amount range
        try:
            num_value = float(clean_amount.replace(',', ''))
            # Reasonable amount range (not too small like dates, not too big like account numbers)
            return 0.01 <= num_value <= 10000000
        except ValueError:
            return False
    
    def extract_table_amounts(self, text: str, currency: str) -> List[str]:
        """Extract amounts from table rows when currency is known from headers."""
        amounts = []
        
        # Split text into lines to find table rows
        lines = text.split('\n')
        
        # Look for lines that contain amounts (numbers with decimal points or currency formatting)
        amount_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b'  # Pattern for formatted amounts
        
        for line in lines:
            # Skip lines that are clearly headers or bank info
            line_lower = line.lower()
            if any(skip_word in line_lower for skip_word in ['bank', 'account', 'currency', 'beneficiary']):
                continue
                
            # Find potential amounts in the line
            matches = re.findall(amount_pattern, line)
            for match in matches:
                # Additional validation for table context
                if self.is_table_amount_context(line, match):
                    amounts.append(f"{match} (table {currency})")
        
        return amounts
    
    def is_table_amount_context(self, line: str, amount: str) -> bool:
        """Check if an amount appears in a table row context."""
        # Look for common invoice/table row indicators
        table_indicators = [
            'charge', 'fee', 'tax', 'total', 'amount', 'price', 'cost',
            'mrc', 'net', 'subtotal', 'discount', 'payment'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in table_indicators)

    def get_context_around_number(self, text: str, number: str) -> str:
        """Get text context around a number to help determine currency."""
        # Find the position of the number in text
        index = text.find(number)
        if index == -1:
            return ""
        
        # Get 50 characters before and after the number
        start = max(0, index - 50)
        end = min(len(text), index + len(number) + 50)
        return text[start:end]

    def determine_currency_from_context(self, context: str) -> str:
        """Determine currency type from context around a number."""
        context_lower = context.lower()
        
        # Count USD indicators
        usd_count = sum(1 for keyword in self.currency_keywords['USD'] 
                       if keyword.lower() in context_lower)
        
        # Count MMK indicators
        mmk_count = sum(1 for keyword in self.currency_keywords['MMK'] 
                       if keyword.lower() in context_lower)
        
        if usd_count > mmk_count and usd_count > 0:
            return 'USD'
        elif mmk_count > usd_count and mmk_count > 0:
            return 'MMK'
        else:
            return None

    def analyze_currency_dominance(self, currencies: Dict[str, List[str]]) -> str:
        """Analyze which currency is dominant in the document."""
        usd_count = len(currencies['USD'])
        mmk_count = len(currencies['MMK'])
        
        if usd_count > mmk_count:
            return 'USD'
        elif mmk_count > usd_count:
            return 'MMK'
        elif usd_count > 0 and mmk_count > 0:
            return 'MIXED'
        else:
            return 'UNKNOWN'

    def scan_pdf(self, pdf_path: str) -> Dict:
        """Scan a single PDF file for currency information."""
        print(f"Scanning: {pdf_path}")
        
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return {
                'file': pdf_path,
                'status': 'ERROR',
                'dominant_currency': 'UNKNOWN',
                'currencies_found': {'USD': [], 'MMK': [], 'UNKNOWN': []},
                'text_length': 0
            }
        
        currencies = self.find_currency_amounts(text)
        dominant_currency = self.analyze_currency_dominance(currencies)
        
        result = {
            'file': pdf_path,
            'status': 'SUCCESS',
            'dominant_currency': dominant_currency,
            'currencies_found': currencies,
            'text_length': len(text),
            'usd_count': len(currencies['USD']),
            'mmk_count': len(currencies['MMK']),
            'scan_timestamp': datetime.now().isoformat()
        }
        
        return result

    def scan_all_pdfs(self, directory: str = ".") -> List[Dict]:
        """Scan all PDF files in message_ directories only."""
        pdf_files = []
        
        # Find all PDF files only in directories starting with "message_"
        for root, dirs, files in os.walk(directory):
            # Check if current directory or any parent directory starts with "message_"
            path_parts = root.split(os.sep)
            is_message_dir = any(part.startswith('message_') for part in path_parts)
            
            if is_message_dir:
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
        
        print(f"Found {len(pdf_files)} PDF files to scan in message_ directories...")
        
        self.results = []
        for pdf_file in pdf_files:
            result = self.scan_pdf(pdf_file)
            self.results.append(result)
        
        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive report of the scan results."""
        if not self.results:
            return "No PDF files scanned."
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("PDF CURRENCY ANALYSIS REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total files scanned: {len(self.results)}")
        report_lines.append("")
        
        # Summary statistics
        usd_files = [r for r in self.results if r['dominant_currency'] == 'USD']
        mmk_files = [r for r in self.results if r['dominant_currency'] == 'MMK']
        mixed_files = [r for r in self.results if r['dominant_currency'] == 'MIXED']
        unknown_files = [r for r in self.results if r['dominant_currency'] == 'UNKNOWN']
        error_files = [r for r in self.results if r['status'] == 'ERROR']
        
        report_lines.append("SUMMARY:")
        report_lines.append(f"  USD dominant files: {len(usd_files)}")
        report_lines.append(f"  MMK dominant files: {len(mmk_files)}")
        report_lines.append(f"  Mixed currency files: {len(mixed_files)}")
        report_lines.append(f"  Unknown currency files: {len(unknown_files)}")
        report_lines.append(f"  Error reading files: {len(error_files)}")
        report_lines.append("")
        
        # Detailed results
        report_lines.append("DETAILED RESULTS:")
        report_lines.append("-" * 60)
        
        for result in self.results:
            report_lines.append(f"File: {result['file']}")
            report_lines.append(f"  Status: {result['status']}")
            if result['status'] == 'SUCCESS':
                report_lines.append(f"  Dominant Currency: {result['dominant_currency']}")
                report_lines.append(f"  USD amounts found: {result['usd_count']}")
                report_lines.append(f"  MMK amounts found: {result['mmk_count']}")
                
                # Show some examples if found
                if result['currencies_found']['USD']:
                    report_lines.append(f"  USD examples: {', '.join(result['currencies_found']['USD'][:3])}")
                if result['currencies_found']['MMK']:
                    report_lines.append(f"  MMK examples: {', '.join(result['currencies_found']['MMK'][:3])}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)

    def display_summary(self):
        """Display a concise summary of scan results."""
        if not self.results:
            print("No results to summarize.")
            return
        
        # Calculate summary statistics
        usd_files = [r for r in self.results if r['dominant_currency'] == 'USD']
        mmk_files = [r for r in self.results if r['dominant_currency'] == 'MMK']
        mixed_files = [r for r in self.results if r['dominant_currency'] == 'MIXED']
        unknown_files = [r for r in self.results if r['dominant_currency'] == 'UNKNOWN']
        error_files = [r for r in self.results if r['status'] == 'ERROR']
        
        total_files = len(self.results)
        usd_percentage = (len(usd_files) / total_files) * 100
        mmk_percentage = (len(mmk_files) / total_files) * 100
        
        print("\n" + "="*50)
        print("📊 SUMMARY OVERVIEW")
        print("="*50)
        print(f"📁 Total PDFs Scanned: {total_files}")
        print()
        print("💰 Currency Distribution:")
        print(f"  💵 USD Files:     {len(usd_files):2d} ({usd_percentage:5.1f}%)")
        print(f"  🇲🇲 MMK Files:     {len(mmk_files):2d} ({mmk_percentage:5.1f}%)")
        if mixed_files:
            print(f"  🔀 Mixed Files:   {len(mixed_files):2d} ({(len(mixed_files)/total_files)*100:5.1f}%)")
        if unknown_files:
            print(f"  ❓ Unknown Files: {len(unknown_files):2d} ({(len(unknown_files)/total_files)*100:5.1f}%)")
        if error_files:
            print(f"  ❌ Error Files:   {len(error_files):2d} ({(len(error_files)/total_files)*100:5.1f}%)")
        
        print()
        print("🏆 Result: ", end="")
        if len(usd_files) > len(mmk_files):
            print(f"Majority of invoices ({len(usd_files)}/{total_files}) are in USD currency")
        elif len(mmk_files) > len(usd_files):
            print(f"Majority of invoices ({len(mmk_files)}/{total_files}) are in MMK currency")
        else:
            print("Equal distribution of USD and MMK currencies")
        
        # Show MMK files if any
        if mmk_files:
            print(f"\n💰 MMK Currency Files ({len(mmk_files)}):")
            for result in mmk_files:
                filename = os.path.basename(result['file'])
                print(f"  - {filename}")
        
        # Show USD files count
        if usd_files:
            print(f"\n💵 USD Currency Files: {len(usd_files)} files")
        
        print("="*50)

    def rename_folders_with_currency(self):
        """Rename message folders to include currency suffix."""
        if not self.results:
            print("No results to process for folder renaming.")
            return
        
        renamed_count = 0
        print("\n📁 Renaming folders with currency suffix...")
        
        for result in self.results:
            if result['status'] != 'SUCCESS':
                continue
            
            file_path = result['file']
            currency = result['dominant_currency'].lower()
            
            # Extract directory path from the PDF file path
            # file_path looks like: ./message_10600634/attachment_10600634.pdf
            dir_path = os.path.dirname(file_path)
            dir_name = os.path.basename(dir_path)
            parent_dir = os.path.dirname(dir_path)
            
            # Check if directory name starts with 'message_' and doesn't already have currency suffix
            if dir_name.startswith('message_') and not (dir_name.endswith('_usd') or dir_name.endswith('_mmk')):
                new_dir_name = f"{dir_name}_{currency}"
                new_dir_path = os.path.join(parent_dir, new_dir_name)
                
                try:
                    # Rename the directory
                    os.rename(dir_path, new_dir_path)
                    print(f"  ✅ {dir_name} → {new_dir_name}")
                    renamed_count += 1
                    
                    # Update the result to reflect new path
                    result['file'] = result['file'].replace(dir_path, new_dir_path)
                    
                except OSError as e:
                    print(f"  ❌ Failed to rename {dir_name}: {e}")
        
        print(f"\n📊 Folder Renaming Summary: {renamed_count} folders renamed")

    def save_results_json(self, filename: str = "pdf_currency_scan_results.json"):
        """Save detailed results to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"Detailed results saved to: {filename}")

def main():
    """Main function to run the PDF currency checker."""
    checker = PDFCurrencyChecker()
    
    print("Starting PDF Currency Analysis...")
    print("This script will scan all PDF files in message_ directories.")
    print("Looking for USD and MMK currency indicators...")
    print()
    
    # Scan all PDFs
    results = checker.scan_all_pdfs()
    
    # Generate and display report
    report = checker.generate_report()
    print(report)
    
    # Display summary
    checker.display_summary()
    
    # Rename folders with currency suffix
    checker.rename_folders_with_currency()
    
    # Save detailed results (after renaming to have updated paths)
    checker.save_results_json()
    
    # Save text report
    with open("pdf_currency_analysis_report.txt", "w", encoding='utf-8') as f:
        f.write(report)
    
    print("\nAnalysis complete!")
    print("Files generated:")
    print("  - pdf_currency_analysis_report.txt (human-readable report)")
    print("  - pdf_currency_scan_results.json (detailed JSON data)")

if __name__ == "__main__":
    main()
