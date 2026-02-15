"""
Derivatives Calculator Module

Implements Black-Scholes option pricing model and Greeks calculation:
- Delta: Rate of change of option price with respect to underlying price
- Gamma: Rate of change of delta with respect to underlying price
- Vega (per 1%): Sensitivity to a 1-percentage-point change in volatility
- Theta: Time decay (per calendar day)
- Rho (per 1%): Sensitivity to a 1-percentage-point change in interest rate

Supports continuous dividend yield *q* for stocks that pay dividends.
"""

import numpy as np
from scipy.stats import norm
import math

class DerivativesCalculator:
    """Calculate derivatives pricing and Greeks using Black-Scholes model"""
    
    def __init__(self):
        pass
    
    def black_scholes_price(self, S, K, T, r, sigma, option_type='call', q=0.0):
        """
        Calculate Black-Scholes option price

        Parameters:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annual)
        option_type: 'call' or 'put'
        q: Continuous dividend yield (default 0)
        """
        if T <= 0:
            # Option has expired
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = (S * np.exp(-q * T) * norm.cdf(d1)
                     - K * np.exp(-r * T) * norm.cdf(d2))
        else:  # put
            price = (K * np.exp(-r * T) * norm.cdf(-d2)
                     - S * np.exp(-q * T) * norm.cdf(-d1))
        
        return price
    
    def calculate_greeks(self, S, K, T, sigma, r=0.05, option_type='call', q=0.0):
        """
        Calculate all Greeks for an option

        Returns dictionary with:
        - price: Option price
        - delta: Rate of change with respect to underlying
        - gamma: Rate of change of delta
        - vega_per_1pct: Price change for a 1-percentage-point rise in vol
        - theta: Time decay (per calendar day)
        - rho_per_1pct: Price change for a 1-percentage-point rise in rate
        """
        if T <= 0:
            return {
                'price': max(S - K, 0) if option_type == 'call' else max(K - S, 0),
                'delta': 1.0 if (option_type == 'call' and S > K) else 0.0,
                'gamma': 0.0,
                'vega_per_1pct': 0.0,
                'theta': 0.0,
                'rho_per_1pct': 0.0
            }
        
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Price
        price = self.black_scholes_price(S, K, T, r, sigma, option_type, q)
        
        # Delta
        if option_type == 'call':
            delta = np.exp(-q * T) * norm.cdf(d1)
        else:
            delta = -np.exp(-q * T) * norm.cdf(-d1)
        
        # Gamma (same for calls and puts)
        gamma = np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Raw vega (dPrice / dSigma) — used internally by the IV solver
        raw_vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)

        # Vega per 1 percentage-point move in vol  (raw_vega / 100)
        vega_per_1pct = raw_vega / 100.0
        
        # Theta
        common_term = -(S * np.exp(-q * T) * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        if option_type == 'call':
            theta = (common_term
                     + q * S * np.exp(-q * T) * norm.cdf(d1)
                     - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (common_term
                     - q * S * np.exp(-q * T) * norm.cdf(-d1)
                     + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Raw rho (dPrice / dR)
        if option_type == 'call':
            raw_rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            raw_rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        # Rho per 1 percentage-point move in rate  (raw_rho / 100)
        rho_per_1pct = raw_rho / 100.0
        
        return {
            'price': float(price),
            'delta': float(delta),
            'gamma': float(gamma),
            'vega_per_1pct': float(vega_per_1pct),
            'theta': float(theta),
            'rho_per_1pct': float(rho_per_1pct),
            'implied_volatility': float(sigma)
        }
    
    def calculate_implied_volatility(self, market_price, S, K, T, r, option_type='call',
                                     q=0.0,
                                     initial_guess=0.3, tolerance=0.0001, max_iterations=100):
        """
        Calculate implied volatility using Newton-Raphson method

        Parameters:
        market_price: Observed market price of option
        S, K, T, r: Standard Black-Scholes parameters
        option_type: 'call' or 'put'
        q: Continuous dividend yield (default 0)
        initial_guess: Starting volatility guess
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations
        """
        sigma = initial_guess
        
        for i in range(max_iterations):
            price = self.black_scholes_price(S, K, T, r, sigma, option_type, q)
            # Use raw vega (dPrice/dSigma) — NOT the per-1% variant
            d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            raw_vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)
            
            diff = market_price - price
            
            if abs(diff) < tolerance:
                return sigma
            
            if raw_vega == 0:
                return sigma
            
            sigma = sigma + diff / raw_vega
            
            # Keep sigma positive
            if sigma <= 0:
                sigma = 0.01
        
        return sigma
    
    def calculate_option_metrics(self, S, K, T, sigma, r=0.05, option_type='call', q=0.0):
        """
        Calculate comprehensive option metrics including probability analysis
        """
        greeks = self.calculate_greeks(S, K, T, sigma, r, option_type, q)
        
        # Probability of profit
        d2 = (np.log(S / K) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
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
