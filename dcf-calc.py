import os
import requests
import json
from math import pow

def get_alpha_vantage_data(symbol, function, api_key):
    """
    Fetches data from Alpha Vantage API.
    Handles rate limiting and errors.
    """
    url = f"https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if 'Error Message' in data:
            print(f"Error from API for {symbol} ({function}): {data['Error Message']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None

def calculate_dcf(symbol, api_key):
    """
    Performs a simplified DCF calculation.
    This is a basic template and requires more robust assumptions for accuracy.
    """
    # 1. Fetch data
    income_statement = get_alpha_vantage_data(symbol, "INCOME_STATEMENT", api_key)
    cash_flow_statement = get_alpha_vantage_data(symbol, "CASH_FLOW", api_key)
    balance_sheet = get_alpha_vantage_data(symbol, "BALANCE_SHEET", api_key)
    company_overview = get_alpha_vantage_data(symbol, "OVERVIEW", api_key)

    if not all([income_statement, cash_flow_statement, balance_sheet, company_overview]):
        print("Failed to retrieve all necessary data. Exiting.")
        return None

    # This example uses only the most recent annual data for simplification
    try:
        fcf_data = cash_flow_statement['annualReports'][0]['freeCashFlow']
        revenue_data = income_statement['annualReports'][0]['totalRevenue']
        shares_outstanding = int(company_overview['SharesOutstanding'])
        total_debt = float(balance_sheet['annualReports'][0]['totalLiabilities'])
        cash_and_equivalents = float(balance_sheet['annualReports'][0]['cashAndCashEquivalents'])
        
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing financial data: {e}")
        return None

    # 2. Make future projections (simplistic example)
    # These growth rates and discount rate are crucial assumptions.
    # A real model would require more sophisticated methods (e.g., historical averages, industry analysis)
    revenue_growth_rate = 0.05  # 5% annual growth
    fcf_margin = float(fcf_data) / float(revenue_data)
    
    forecast_years = 5
    discount_rate = 0.09  # Weighted Average Cost of Capital (WACC)
    terminal_growth_rate = 0.025  # Perpetual growth rate

    projected_fcf = []
    for i in range(1, forecast_years + 1):
        if i == 1:
            next_fcf = float(fcf_data) * (1 + revenue_growth_rate)
        else:
            next_fcf = projected_fcf[-1] * (1 + revenue_growth_rate)
        projected_fcf.append(next_fcf)

    # 3. Calculate Present Value of Free Cash Flows
    present_value_fcf = 0
    for i, fcf in enumerate(projected_fcf, 1):
        present_value_fcf += fcf / pow((1 + discount_rate), i)
    
    # 4. Calculate Terminal Value (TV)
    terminal_fcf = projected_fcf[-1] * (1 + terminal_growth_rate)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
    
    # 5. Calculate Present Value of Terminal Value
    present_value_tv = terminal_value / pow((1 + discount_rate), forecast_years)
    
    # 6. Calculate Intrinsic Value per Share
    enterprise_value = present_value_fcf + present_value_tv
    equity_value = enterprise_value + cash_and_equivalents - total_debt
    intrinsic_value_per_share = equity_value / shares_outstanding

    return intrinsic_value_per_share

def main():
    """
    Main function to run the DCF calculation and determine valuation.
    """
    # Use GitHub Actions secrets for API key and stock symbol
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("API key not found. Please set the 'ALPHA_VANTAGE_API_KEY' environment variable.")
        return

    stock_symbol = os.getenv("STOCK_SYMBOL")
    if not stock_symbol:
        print("Stock symbol not found. Please set the 'STOCK_SYMBOL' environment variable.")
        return
        
    print(f"Calculating intrinsic value for {stock_symbol}...")
    intrinsic_value = calculate_dcf(stock_symbol, api_key)
    
    if intrinsic_value:
        # Get the current share price (requires another API call)
        current_price_data = get_alpha_vantage_data(stock_symbol, "GLOBAL_QUOTE", api_key)
        if current_price_data and "Global Quote" in current_price_data:
            current_price = float(current_price_data['Global Quote']['05. price'])
            print(f"Intrinsic Value per Share: ${intrinsic_value:.2f}")
            print(f"Current Market Price: ${current_price:.2f}")
            
            # 7. Compare intrinsic value to current price
            if intrinsic_value > current_price:
                print("Conclusion: The stock appears to be **undervalued** 🟩")
            elif intrinsic_value < current_price:
                print("Conclusion: The stock appears to be **overvalued** 🟥")
            else:
                print("Conclusion: The stock appears to be **fairly valued** 🟨")
        else:
            print("Could not retrieve current stock price.")

if __name__ == "__main__":
    main()
