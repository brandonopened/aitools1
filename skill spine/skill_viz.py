import pandas as pd
import json
import os
from typing import Dict, List, Optional
import asyncio
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import print as rprint

class LearningProgressionManager:
    def __init__(self, csv_path: str):
        self.console = Console()
        self.data = self._load_and_parse_csv(csv_path)
        
    def _load_and_parse_csv(self, csv_path: str) -> Dict:
        """Load and parse the CSV into a structured dictionary."""
        df = pd.read_csv(csv_path)
        
        # Initialize structure
        domains = {}
        
        current_domain = None
        for _, row in df.iterrows():
            if pd.notna(row['Domain']):
                current_domain = row['Domain']
                if current_domain not in domains:
                    domains[current_domain] = {'subdomains': {}}
                    
            if pd.notna(row['Subdomain']) and current_domain:
                subdomain = row['Subdomain']
                if subdomain not in domains[current_domain]['subdomains']:
                    domains[current_domain]['subdomains'][subdomain] = []
                    
                # Get progression data
                code_columns = ['ATL Code', 'P-SE Code', 'P-LC Code', 'P-LIT Code', 
                              'P-MATH Code', 'P-SCI Code', 'FS Code', 'P-PMP Code']
                
                code = None
                for col in code_columns:
                    if col in row and pd.notna(row[col]):
                        code = row[col]
                        break
                
                if not code:
                    continue
                
                progression = {
                    'code': code,
                    'standard': row['Standard'] if pd.notna(row['Standard']) else None,
                    'skills': {}
                }
                
                # Add skills for each age group
                age_columns = [
                    'Infants (INF 0-3)', 'Infants (INF 3-6)', 'Infants (INF 6-9)',
                    'Infants (INF 9-12)', 'Infants (INF 12-18)', 'Toddler (TOD 18-36)',
                    'Preschool (PRE 36-48)'
                ]
                
                for col in age_columns:
                    if col in row and pd.notna(row[col]):
                        progression['skills'][col] = row[col]
                
                if progression['code']:  # Only add if there's a valid code
                    domains[current_domain]['subdomains'][subdomain].append(progression)
        
        return domains

    def display_structure(self):
        """Display the hierarchical structure of the learning progressions."""
        table = Table(title="Learning Progressions Structure")
        table.add_column("Domain", style="cyan")
        table.add_column("Subdomain", style="green")
        table.add_column("Code", style="yellow")
        table.add_column("Standard", style="magenta")
        
        for domain, domain_data in self.data.items():
            if not domain or pd.isna(domain):  # Skip empty domains
                continue
            for subdomain, progressions in domain_data['subdomains'].items():
                if not subdomain or pd.isna(subdomain):  # Skip empty subdomains
                    continue
                for prog in progressions:
                    table.add_row(
                        domain,
                        subdomain,
                        prog['code'],
                        prog['standard']
                    )
        
        self.console.print(table)

    def display_skills(self, domain: str, subdomain: str, code: str):
        """Display skills for a specific progression."""
        for prog in self.data[domain]['subdomains'][subdomain]:
            if prog['code'] == code:
                skill_table = Table(title=f"Skills for {code}")
                skill_table.add_column("Age Group")
                skill_table.add_column("Skill Description")
                
                for age, skill in prog['skills'].items():
                    skill_table.add_row(age, skill)
                
                self.console.print(skill_table)
                break

    def interactive_session(self):
        """Run an interactive session for viewing skills."""
        while True:
            self.console.clear()
            self.display_structure()
            
            self.console.print("\n[yellow]Options:")
            self.console.print("1. View skills for a specific progression")
            self.console.print("2. Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2"])
            
            if choice == "2":
                break
                
            if choice == "1":
                domain = Prompt.ask("Enter domain name")
                if domain not in self.data:
                    self.console.print("[red]Invalid domain")
                    continue
                    
                subdomain = Prompt.ask("Enter subdomain name")
                if subdomain not in self.data[domain]['subdomains']:
                    self.console.print("[red]Invalid subdomain")
                    continue
                    
                # Display available codes for this subdomain
                codes = [prog['code'] for prog in self.data[domain]['subdomains'][subdomain]]
                self.console.print(f"\nAvailable codes: {', '.join(codes)}")
                
                code = Prompt.ask("Enter code")
                if code not in codes:
                    self.console.print("[red]Invalid code")
                    continue
                
                self.display_skills(domain, subdomain, code)
                Prompt.ask("\nPress Enter to continue")

def main():
    manager = LearningProgressionManager("learning_progressions.csv")
    manager.interactive_session()

if __name__ == "__main__":
    main()