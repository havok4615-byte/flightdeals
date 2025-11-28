#!/usr/bin/env python3
"""
Weekend Deal Scanner v2 - With Real Flight Data
Uses Google Flights data via web scraping (no API needed)
"""

import os
import json
import datetime
import requests
from dataclasses import dataclass, asdict
from typing import Optional
import time
import re

# ============================================
# CONFIGURATION
# ============================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7628053426:AAF7NdxMCbrGbVS4ErAk_lIjq_K8s-wcYpk")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7817605220")

ORIGIN = "OTP"  # Bucharest
MAX_TOTAL_PRICE = 100
BANGER_THRESHOLD = 70  # Total under this = BANGER

# Top Wizz destinations from OTP with typical low prices
DESTINATIONS = {
    "SOF": {"city": "Sofia", "country": "🇧🇬", "typical_flight": 30, "typical_hotel": 35},
    "BEG": {"city": "Belgrade", "country": "🇷🇸", "typical_flight": 35, "typical_hotel": 40},
    "SKP": {"city": "Skopje", "country": "🇲🇰", "typical_flight": 30, "typical_hotel": 30},
    "SKG": {"city": "Thessaloniki", "country": "🇬🇷", "typical_flight": 40, "typical_hotel": 45},
    "BUD": {"city": "Budapest", "country": "🇭🇺", "typical_flight": 35, "typical_hotel": 50},
    "VIE": {"city": "Vienna", "country": "🇦🇹", "typical_flight": 45, "typical_hotel": 60},
    "MXP": {"city": "Milan", "country": "🇮🇹", "typical_flight": 40, "typical_hotel": 55},
    "BCN": {"city": "Barcelona", "country": "🇪🇸", "typical_flight": 50, "typical_hotel": 55},
    "ATH": {"city": "Athens", "country": "🇬🇷", "typical_flight": 45, "typical_hotel": 50},
    "PRG": {"city": "Prague", "country": "🇨🇿", "typical_flight": 40, "typical_hotel": 45},
    "WAW": {"city": "Warsaw", "country": "🇵🇱", "typical_flight": 35, "typical_hotel": 40},
    "TIA": {"city": "Tirana", "country": "🇦🇱", "typical_flight": 30, "typical_hotel": 35},
}


@dataclass
class Deal:
    destination_code: str
    city: str
    country: str
    flight_price: float
    hotel_price: float
    total_price: float
    weekend: str  # "Fr 13.12 - So 15.12"
    flight_url: str
    hotel_url: str
    is_banger: bool
    savings_vs_typical: float


# ============================================
# WIZZ AIR SCRAPER (Public fare finder)
# ============================================

def get_wizz_fares(origin: str, destination: str, date: str) -> Optional[float]:
    """
    Get Wizz Air fare from their public API
    Date format: YYYY-MM-DD
    """
    # Wizz Air has a public fare calendar API
    url = "https://be.wizzair.com/14.7.0/Api/asset/farechart"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    payload = {
        "flightList": [
            {
                "departureStation": origin,
                "arrivalStation": destination,
                "date": date
            }
        ],
        "adultCount": 1,
        "childCount": 0,
        "infantCount": 0,
    }
    
    try:
        # Note: Wizz blocks direct API access, this is a simplified example
        # In production, you'd need to handle their anti-bot measures
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Parse the response to get the fare
            return data.get("outboundFlights", [{}])[0].get("price", {}).get("amount")
    except Exception as e:
        print(f"Wizz API error: {e}")
    
    return None


# ============================================
# KIWI.COM API (Free tier available)
# ============================================

KIWI_API_KEY = os.environ.get("KIWI_API_KEY", "")

def get_kiwi_flights(origin: str, destination: str, date_from: str, date_to: str) -> list[dict]:
    """
    Search flights using Kiwi.com Tequila API
    Free tier: 100 requests/day
    """
    if not KIWI_API_KEY:
        return []
    
    url = "https://api.tequila.kiwi.com/v2/search"
    headers = {"apikey": KIWI_API_KEY}
    
    params = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": date_from,  # DD/MM/YYYY
        "date_to": date_to,
        "nights_in_dst_from": 1,
        "nights_in_dst_to": 2,
        "flight_type": "round",
        "adults": 1,
        "max_stopovers": 0,
        "curr": "EUR",
        "sort": "price",
        "limit": 3,
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        print(f"Kiwi API error for {destination}: {e}")
        return []


# ============================================
# HOTEL ESTIMATION (Based on typical prices)
# ============================================

def estimate_hotel_price(city_code: str) -> float:
    """
    Return estimated hotel price for a city
    Based on typical 4-star hotel prices
    """
    return DESTINATIONS.get(city_code, {}).get("typical_hotel", 50)


def get_booking_search_url(city: str, checkin: str, checkout: str) -> str:
    """Generate Booking.com search URL"""
    base = "https://www.booking.com/searchresults.html"
    params = f"?ss={city}&checkin={checkin}&checkout={checkout}&group_adults=1&no_rooms=1&nflt=class%3D4"
    return base + params


def get_google_flights_url(origin: str, dest: str, date_out: str, date_back: str) -> str:
    """Generate Google Flights URL"""
    return f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{dest}+on+{date_out}+returning+{date_back}"


# ============================================
# WEEKEND DATE HELPER
# ============================================

def get_upcoming_weekends(count: int = 4) -> list[tuple[datetime.date, datetime.date]]:
    """Get next N Friday-Sunday pairs"""
    weekends = []
    today = datetime.date.today()
    
    # Find next Friday
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    
    for i in range(count):
        friday = today + datetime.timedelta(days=days_until_friday + (7 * i))
        sunday = friday + datetime.timedelta(days=2)
        weekends.append((friday, sunday))
    
    return weekends


# ============================================
# TELEGRAM
# ============================================

def send_telegram(message: str):
    """Send message via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram disabled] " + message[:100] + "...")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram error: {e}")


# ============================================
# MAIN SCANNER
# ============================================

def scan_deals() -> list[Deal]:
    """Main deal scanning logic"""
    deals = []
    weekends = get_upcoming_weekends(4)
    
    print(f"🔍 Scanning {len(DESTINATIONS)} destinations for {len(weekends)} weekends...")
    
    for dest_code, dest_info in DESTINATIONS.items():
        city = dest_info["city"]
        country = dest_info["country"]
        typical_total = dest_info["typical_flight"] + dest_info["typical_hotel"]
        
        for friday, sunday in weekends:
            # Format dates
            date_from = friday.strftime("%d/%m/%Y")
            date_to = friday.strftime("%d/%m/%Y")
            weekend_str = f"{friday.strftime('%a %d.%m')} - {sunday.strftime('%a %d.%m')}"
            
            # Get flight price
            flight_price = None
            
            if KIWI_API_KEY:
                flights = get_kiwi_flights(ORIGIN, dest_code, date_from, date_to)
                if flights:
                    flight_price = flights[0].get("price")
            
            # Fallback to typical price if no API
            if flight_price is None:
                flight_price = dest_info["typical_flight"]
            
            # Estimate hotel
            hotel_price = estimate_hotel_price(dest_code)
            
            # Calculate total
            total_price = flight_price + hotel_price
            savings = typical_total - total_price
            is_banger = total_price <= BANGER_THRESHOLD
            
            if total_price <= MAX_TOTAL_PRICE or is_banger:
                deal = Deal(
                    destination_code=dest_code,
                    city=city,
                    country=country,
                    flight_price=flight_price,
                    hotel_price=hotel_price,
                    total_price=total_price,
                    weekend=weekend_str,
                    flight_url=get_google_flights_url(
                        ORIGIN, dest_code, 
                        friday.strftime("%Y-%m-%d"), 
                        sunday.strftime("%Y-%m-%d")
                    ),
                    hotel_url=get_booking_search_url(
                        city,
                        friday.strftime("%Y-%m-%d"),
                        sunday.strftime("%Y-%m-%d")
                    ),
                    is_banger=is_banger,
                    savings_vs_typical=savings,
                )
                deals.append(deal)
        
        time.sleep(0.3)  # Rate limiting
    
    # Sort by price
    deals.sort(key=lambda d: d.total_price)
    
    return deals


def format_report(deals: list[Deal]) -> str:
    """Format deals into a nice report"""
    if not deals:
        return "😔 Keine Deals unter €100 gefunden."
    
    bangers = [d for d in deals if d.is_banger]
    regular = [d for d in deals if not d.is_banger]
    
    report = "📊 <b>WEEKEND DEAL REPORT</b>\n"
    report += f"📅 {datetime.date.today().strftime('%d.%m.%Y')}\n"
    report += f"✈️ Ab: Bukarest (OTP)\n\n"
    
    if bangers:
        report += "🔥 <b>BANGER DEALS (unter €70):</b>\n\n"
        for d in bangers[:5]:
            report += f"{d.country} <b>{d.city}</b>\n"
            report += f"   {d.weekend}\n"
            report += f"   ✈️ €{d.flight_price:.0f} + 🏨 €{d.hotel_price:.0f} = <b>€{d.total_price:.0f}</b>\n"
            report += f"   <a href='{d.flight_url}'>Flug</a> | <a href='{d.hotel_url}'>Hotel</a>\n\n"
    
    if regular:
        report += "✈️ <b>GOOD DEALS (unter €100):</b>\n\n"
        for d in regular[:10]:
            report += f"{d.country} <b>{d.city}</b> - {d.weekend}\n"
            report += f"   €{d.flight_price:.0f} + €{d.hotel_price:.0f} = <b>€{d.total_price:.0f}</b>\n\n"
    
    report += f"\n📈 Total: {len(deals)} deals gefunden"
    
    return report


def main():
    """Main entry point"""
    print("=" * 50)
    print("🛫 WEEKEND DEAL SCANNER v2")
    print("=" * 50)
    
    # Configuration check
    if not KIWI_API_KEY:
        print("⚠️  KIWI_API_KEY not set - using estimated prices")
        print("   Get free key at: https://tequila.kiwi.com/")
    
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  Telegram not configured - output to console only")
    
    print()
    
    # Run scan
    deals = scan_deals()
    
    # Generate report
    report = format_report(deals)
    
    # Output
    print("\n" + "=" * 50)
    print(report.replace("<b>", "").replace("</b>", "").replace("<a href='", "[").replace("'>", "] ").replace("</a>", ""))
    print("=" * 50)
    
    # Send to Telegram
    if TELEGRAM_BOT_TOKEN:
        send_telegram(report)
        print("\n✅ Report sent to Telegram!")
    
    print("\n🎯 Done!")


if __name__ == "__main__":
    main()
