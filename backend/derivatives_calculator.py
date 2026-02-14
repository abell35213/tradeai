"""
Derivatives Calculator Module

Implements Black-Scholes option pricing model and Greeks calculation:
- Delta: Rate of change of option price with respect to underlying price
- Gamma: Rate of change of delta with respect to underlying price
- Vega: Sensitivity to volatility
- Theta: Time decay
- Rho: Sensitivity to interest rate
"""

import numpy as np
from scipy.stats import norm
import math

class DerivativesCalculator:
    """Calculate derivatives pricing and Greeks using Black-Scholes model"""
    
    def __init__(self):
        pass
    
    def black_scholes_price(self, S, K, T, r, sigma, option_type='call'):
        """
        Calculate Black-Scholes option price
        
        Parameters:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annual)
        option_type: 'call' or 'put'
        """
        if T <= 0:
            # Option has expired
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    def calculate_greeks(self, S, K, T, sigma, r=0.05, option_type='call'):
        """
        Calculate all Greeks for an option
        
        Returns dictionary with:
        - price: Option price
        - delta: Rate of change with respect to underlying
        - gamma: Rate of change of delta
        - vega: Sensitivity to volatility
        - theta: Time decay
        - rho: Sensitivity to interest rate
        """
        if T <= 0:
            return {
                'price': max(S - K, 0) if option_type == 'call' else max(K - S, 0),
                'delta': 1.0 if (option_type == 'call' and S > K) else 0.0,
                'gamma': 0.0,
                'vega': 0.0,
                'theta': 0.0,
                'rho': 0.0
            }
        
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Price
        price = self.black_scholes_price(S, K, T, r, sigma, option_type)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Vega (same for calls and puts)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Divided by 100 for 1% change
        
        # Theta
        if option_type == 'call':
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Rho
        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return {
            'price': float(price),
            'delta': float(delta),
            'gamma': float(gamma),
            'vega': float(vega),
            'theta': float(theta),
            'rho': float(rho),
            'implied_volatility': float(sigma)
        }
    
    def calculate_implied_volatility(self, market_price, S, K, T, r, option_type='call', 
                                     initial_guess=0.3, tolerance=0.0001, max_iterations=100):
        """
        Calculate implied volatility using Newton-Raphson method
        
        Parameters:
        market_price: Observed market price of option
        S, K, T, r: Standard Black-Scholes parameters
        option_type: 'call' or 'put'
        initial_guess: Starting volatility guess
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations
        """
        sigma = initial_guess
        
        for i in range(max_iterations):
            price = self.black_scholes_price(S, K, T, r, sigma, option_type)
            vega = S * norm.pdf((np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / 
                               (sigma * np.sqrt(T))) * np.sqrt(T)
            
            diff = market_price - price
            
            if abs(diff) < tolerance:
                return sigma
            
            if vega == 0:
                return sigma
            
            sigma = sigma + diff / vega
            
            # Keep sigma positive
            if sigma <= 0:
                sigma = 0.01
        
        return sigma
    
    def calculate_option_metrics(self, S, K, T, sigma, r=0.05, option_type='call'):
        """
        Calculate comprehensive option metrics including probability analysis
        """
        greeks = self.calculate_greeks(S, K, T, sigma, r, option_type)
        
        # Probability of profit
        d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option_type == 'call':
            prob_itm = norm.cdf(d2)
        else:
            prob_itm = norm.cdf(-d2)
        
        # Breakeven price
        if option_type == 'call':
            breakeven = K + greeks['price']
        else:
            breakeven = K - greeks['price']
        
        return {
            **greeks,
            'probability_itm': float(prob_itm),
            'breakeven_price': float(breakeven),
            'intrinsic_value': float(max(S - K, 0) if option_type == 'call' else max(K - S, 0)),
            'time_value': float(greeks['price'] - max(S - K, 0) if option_type == 'call' 
                               else greeks['price'] - max(K - S, 0))
        }
